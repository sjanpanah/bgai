"""TD(lambda) self-play training for the neural engine — developer-facing,
run offline like `ai/benchmark.py`, never at request time.

The network plays itself (1-ply greedy via `NeuralEngine`, the same policy the
shipped engine uses) and learns from its own games. `V(s)` is the probability
that the side to move at `s` eventually wins, so the perspective flips every
ply — the target for `V(s_t)` is therefore `1 - V(s_{t+1})`, not `V(s_{t+1})`.
Getting that complement wrong is the classic silent TD-Gammon bug: training
still "runs", the loss still moves, and the net learns nothing useful. The
sanity gates (`sanity_values`) exist to catch exactly that.

Run it:

    python -m ai.train_td --games 50000 --out ai/weights/td_v1.npz

Progress and periodic benchmark results stream to stdout (flushed, so a
backgrounded run redirected to a log file stays readable live), and the
checkpoint is rewritten every `--checkpoint-every` games so an interrupted
run keeps its progress.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ai.benchmark import Competitor, round_robin
from ai.encoding import encode_canonical
from ai.neural_engine import NeuralEngine
from ai.neural_net import DEFAULT_HIDDEN_SIZE, NeuralNet
from engine.moves import apply_turn, legal_turn_sequences
from engine.rules import has_won, win_multiplier
from engine.state import PLAYER_0, Dice, GameState


@dataclass
class TrainConfig:
    games: int = 50_000
    hidden_size: int = DEFAULT_HIDDEN_SIZE
    alpha: float = 0.1
    # Linearly decays `alpha` -> `alpha_final` when set, then holds. A long run
    # at a fixed alpha keeps taking big steps long after the net is good: every
    # update is a noisy sample (the dice decide a lot), so the weights orbit the
    # optimum in a cloud whose width scales with alpha instead of settling into
    # it. Decaying shrinks that cloud. Note alpha interacts with `lam` — a
    # higher lambda carries more accumulated credit per update, so the same
    # alpha is a bigger effective step.
    alpha_final: float | None = None
    # Games over which that decay happens, in ABSOLUTE games trained — not as a
    # fraction of `games`. Tying it to `games` would make the schedule depend on
    # where the run happens to stop, and would silently restart the decay on
    # every `--resume`. Defaults to `games` so a single uninterrupted run
    # anneals exactly across itself.
    alpha_decay_games: int | None = None
    # Games trained in previous runs, so `--resume` continues the alpha
    # schedule instead of re-heating it back to the starting alpha.
    games_done: int = 0
    lam: float = 0.0  # lambda=0 (one-step TD) first — see CLAUDE.md's M5 risks
    seed: int = 42
    max_turns: int = 500
    out: Path = Path(__file__).parent / "weights" / "td_v1.npz"
    resume: Path | None = None
    checkpoint_every: int = 1_000
    report_every: int = 500
    eval_every: int = 5_000
    eval_opponents: list[tuple[str, int]] = field(
        # (engine_id, games) — `random` and `heuristic` are cheap enough to run
        # often; `expectiminimax` is ~1.6s/game (see CLAUDE.md M4 note), so it
        # gets far fewer games and is the one that actually matters.
        default_factory=lambda: [("random", 40), ("heuristic", 40), ("expectiminimax", 20)]
    )
    # Which eval opponent decides "best so far" for the `.best.npz` snapshot.
    # TD self-play wobbles — the last checkpoint of a long run isn't reliably
    # its strongest, so keep the high-water mark separately.
    gate_opponent: str = "heuristic"

    @property
    def best_out(self) -> Path:
        return Path(self.out).with_suffix(".best.npz")


class Traces:
    """TD(lambda) eligibility traces, one per parameter tensor. Accumulated
    in place — a fresh allocation of the 198xH array every ply would dominate
    the update cost.

    The decay is `-lambda`, not `+lambda`. That sign is the whole subtlety of
    running TD(lambda) in a side-to-move ("canonical") perspective, so it is
    worth spelling out. Write `U(s)` for a fixed perspective — P(player 0
    wins) — where plain TD(lambda) is `e <- lambda*e + grad U(s_t)`. Our
    `V(s)` is P(*mover at s* wins), so `U = V` on player 0's plies and
    `U = 1 - V` on player 1's: `grad U(s_t) = sign_t * grad V(s_t)` and
    `delta^U_t = sign_t * delta_t`, with `sign_t` flipping every ply. Push
    those through the recursion and `e^U_t = sign_t * e_t`, which leaves the
    weight update `alpha * delta_t * e_t` unchanged only if the trace itself
    alternates: `e_t = -lambda*e_{t-1} + grad V(s_t)`.

    With `+lambda` every past ply contributes with the wrong sign half the
    time, so long-range credit fights itself — invisible at lambda=0 (both
    forms collapse to the raw gradient), silently wrong above it.
    `test_trace_matches_fixed_perspective_td_lambda` pins the equivalence.
    """

    def __init__(self, net: NeuralNet) -> None:
        self.W1 = np.zeros_like(net.W1)
        self.b1 = np.zeros_like(net.b1)
        self.W2 = np.zeros_like(net.W2)
        self.b2 = 0.0

    def reset(self) -> None:
        self.W1.fill(0.0)
        self.b1.fill(0.0)
        self.W2.fill(0.0)
        self.b2 = 0.0

    def accumulate(self, net: NeuralNet, x: np.ndarray, h: np.ndarray, y: float, lam: float) -> None:
        """`e <- -lambda*e + grad V(s_t)` — see the class docstring for the sign."""
        dW1, db1, dW2, db2 = net.gradient(x, h, y)
        if lam == 0.0:  # one-step TD: the trace is just the current gradient
            np.copyto(self.W1, dW1)
            np.copyto(self.b1, db1)
            np.copyto(self.W2, dW2)
            self.b2 = db2
            return
        decay = -lam
        self.W1 *= decay
        self.W1 += dW1
        self.b1 *= decay
        self.b1 += db1
        self.W2 *= decay
        self.W2 += dW2
        self.b2 = decay * self.b2 + db2

    def apply(self, net: NeuralNet, delta: float, alpha: float) -> None:
        """`w <- w + alpha*delta*e`."""
        step = alpha * delta
        net.W1 += step * self.W1
        net.b1 += step * self.b1
        net.W2 += step * self.W2
        net.b2 += step * self.b2


def self_play_game(
    net: NeuralNet,
    engine: NeuralEngine,
    traces: Traces,
    seed: int,
    alpha: float,
    lam: float,
    max_turns: int,
    start_state: GameState | None = None,
) -> tuple[int | None, int, int]:
    """Plays one self-play game, updating `net` after every ply.

    Returns `(winner, multiplier, plies)`; winner is None if the game ran past
    `max_turns` without finishing (scored as no outcome, weights still moved).
    `start_state` overrides the opening position — training always uses the
    standard start, but tests use it to drive a specific TD branch.
    """
    state = start_state.copy() if start_state is not None else GameState.new_game()
    dice_gen = Dice(seed=seed)
    traces.reset()

    for ply in range(max_turns):
        mover = state.turn
        x = encode_canonical(state)
        h, value = net.forward(x)

        dice = dice_gen.roll()
        sequences = legal_turn_sequences(state, mover, dice)
        moves = engine.choose_move(state, dice, sequences)

        resulting = apply_turn(state, mover, moves)
        if resulting is state:  # forced dance: apply_turn hands back the same object
            resulting = resulting.copy()

        won = has_won(resulting, mover)
        if won:
            target = 1.0
        else:
            # s_{t+1} has the opponent on roll, so V(s_{t+1}) is *their* win
            # probability — the complement is the mover's.
            resulting.turn = 1 - mover
            target = 1.0 - net.value(encode_canonical(resulting))

        traces.accumulate(net, x, h, value, lam)
        traces.apply(net, target - value, alpha)

        if won:
            return mover, win_multiplier(resulting, mover), ply + 1
        state = resulting

    return None, 0, max_turns


def _near_win_position() -> GameState:
    """Player 0 on roll, one checker from bearing off the last of 15."""
    board = [0] * 24
    board[0] = 1
    board[23] = -15
    return GameState(board=board, bar=[0, 0], off=[14, 0], turn=PLAYER_0)


def _near_loss_position() -> GameState:
    """The same position with the seats swapped — player 0 on roll and lost."""
    board = [0] * 24
    board[23] = -1
    board[0] = 15
    return GameState(board=board, bar=[0, 0], off=[0, 14], turn=PLAYER_0)


def sanity_values(net: NeuralNet) -> tuple[float, float]:
    """(value of a nearly-won position, value of a nearly-lost one), both with
    player 0 on roll. A correctly-trained net drives these toward (~1, ~0); if
    they sit together near 0.5, or are inverted, the TD perspective handling is
    wrong — the failure mode this gate exists to catch."""
    return net.value(encode_canonical(_near_win_position())), net.value(
        encode_canonical(_near_loss_position())
    )


def alpha_for_game(config: TrainConfig, games_trained: int) -> float:
    """Learning rate after `games_trained` total games (counting earlier runs).

    Linear from `alpha` to `alpha_final` over `alpha_decay_games`, then held
    flat. Held rather than extrapolated so overshooting the horizon — easy to
    do when resuming — can't drive alpha to zero or negative.
    """
    if config.alpha_final is None:
        return config.alpha
    horizon = config.alpha_decay_games if config.alpha_decay_games is not None else config.games
    progress = min(games_trained / max(horizon, 1), 1.0)
    return config.alpha + progress * (config.alpha_final - config.alpha)


def _format_duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def evaluate(net: NeuralNet, opponent_id: str, games: int, seed: int) -> float:
    """Head-to-head win rate of the current net against a registry engine,
    seats alternating. Goes through the normal benchmark harness so training
    eval and the shipped benchmark measure the same thing."""
    trainee = Competitor(
        engine_id="neural", label="neural[training]", prebuilt=NeuralEngine(net=net)
    )
    opponent = Competitor(engine_id=opponent_id)
    results = round_robin([trainee, opponent], games_per_matchup=games, seed=seed)
    return results[trainee.label].get(opponent.label, 0) / games


def train(config: TrainConfig) -> NeuralNet:
    if config.resume is not None:
        net = NeuralNet.load(config.resume)
        print(f"resumed from {config.resume} (hidden={net.b1.shape[0]})", flush=True)
    else:
        net = NeuralNet(hidden_size=config.hidden_size, seed=config.seed)
    engine = NeuralEngine(net=net)  # shares the live net: play improves as it learns
    traces = Traces(net)

    started = time.time()
    wins = [0, 0]
    unfinished = 0
    total_plies = 0
    best_gate_rate = -1.0

    # Throughput is reported over the window since the last report line, not
    # cumulatively since launch. Self-play speed climbs a lot as the net
    # improves (a weak net drags games out toward the ply cap), so a
    # cumulative rate stays badly stale for thousands of games. The window
    # anchors are also reset after each eval so benchmark time — which is
    # lumpy and not proportional to games — never lands in the game rate.
    window_game = 0
    window_time = started
    window_plies = 0

    print(
        f"training {config.games} games | hidden={config.hidden_size} "
        f"alpha={config.alpha} lambda={config.lam} seed={config.seed}"
        + (f" | resuming from {config.games_done} games trained" if config.games_done else ""),
        flush=True,
    )

    game = 0
    interrupted = False
    try:
        for game in range(1, config.games + 1):
            # Seeds continue past previous runs so a resumed run doesn't replay
            # the same games it already trained on.
            games_trained = config.games_done + game - 1
            alpha = alpha_for_game(config, games_trained)

            winner, _, plies = self_play_game(
                net,
                engine,
                traces,
                seed=config.seed + games_trained,
                alpha=alpha,
                lam=config.lam,
                max_turns=config.max_turns,
            )
            total_plies += plies
            if winner is None:
                unfinished += 1
            else:
                wins[winner] += 1

            if game % config.report_every == 0:
                near_win, near_loss = sanity_values(net)
                now = time.time()
                window_games = game - window_game
                rate = window_games / max(now - window_time, 1e-9)
                print(
                    f"[{game:>7}/{config.games} {game / config.games:5.1%}] "
                    f"{rate:5.1f} games/s | "
                    f"elapsed {_format_duration(now - started):>6} | "
                    f"avg plies {(total_plies - window_plies) / window_games:5.1f} | "
                    f"p0 wins {wins[0] / max(sum(wins), 1):.2f} | "
                    f"alpha {alpha:.3f} | "
                    f"sanity win/loss {near_win:.3f}/{near_loss:.3f}"
                    + (f" | unfinished {unfinished}" if unfinished else ""),
                    flush=True,
                )
                window_game, window_time, window_plies = game, now, total_plies

            if game % config.eval_every == 0:
                for opponent_id, eval_games in config.eval_opponents:
                    rate = evaluate(net, opponent_id, eval_games, seed=config.seed + game)
                    marker = ""
                    if opponent_id == config.gate_opponent and rate > best_gate_rate:
                        best_gate_rate = rate
                        net.save(config.best_out)
                        marker = "  <- best so far"
                    print(
                        f"[{game:>7}] vs {opponent_id}: {rate:.0%} of {eval_games}{marker}",
                        flush=True,
                    )
                # Re-anchor so the benchmark games above aren't charged to the
                # next window's self-play rate.
                window_game, window_time, window_plies = game, time.time(), total_plies

            if game % config.checkpoint_every == 0:
                net.save(config.out)
    except KeyboardInterrupt:
        # Ctrl+C is a supported way to stop: fall through to the same final
        # save as a completed run, so you keep every game up to the interrupt
        # rather than rewinding to the last periodic checkpoint.
        interrupted = True
        print("\ninterrupted — saving current net", flush=True)

    net.save(config.out)
    total_trained = config.games_done + game
    print(
        f"{'stopped' if interrupted else 'done'} after {game} games "
        f"({total_trained} total) in {_format_duration(time.time() - started)} -> {config.out}"
        + (f" (best vs {config.gate_opponent}: {best_gate_rate:.0%})" if best_gate_rate >= 0 else ""),
        flush=True,
    )
    if interrupted:
        print(f"resume with: --resume {config.out} --games-done {total_trained}", flush=True)
    return net


def main() -> None:
    parser = argparse.ArgumentParser(description="TD(lambda) self-play training")
    defaults = TrainConfig()
    parser.add_argument("--games", type=int, default=defaults.games)
    parser.add_argument("--hidden-size", type=int, default=defaults.hidden_size)
    parser.add_argument("--alpha", type=float, default=defaults.alpha)
    parser.add_argument(
        "--alpha-final", type=float, default=None, help="linearly decay alpha to this value"
    )
    parser.add_argument(
        "--alpha-decay-games",
        type=int,
        default=None,
        help="absolute games to decay alpha over, then hold (default: --games)",
    )
    parser.add_argument(
        "--games-done",
        type=int,
        default=0,
        help="games trained in previous runs; continues the alpha schedule and dice seeds",
    )
    parser.add_argument("--lam", type=float, default=defaults.lam)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    parser.add_argument("--out", type=Path, default=defaults.out)
    parser.add_argument("--resume", type=Path, default=None, help="continue from a checkpoint")
    parser.add_argument("--checkpoint-every", type=int, default=defaults.checkpoint_every)
    parser.add_argument("--report-every", type=int, default=defaults.report_every)
    parser.add_argument("--eval-every", type=int, default=defaults.eval_every)
    parser.add_argument("--gate-opponent", default=defaults.gate_opponent)
    args = parser.parse_args()

    train(
        TrainConfig(
            games=args.games,
            hidden_size=args.hidden_size,
            alpha=args.alpha,
            alpha_final=args.alpha_final,
            alpha_decay_games=args.alpha_decay_games,
            games_done=args.games_done,
            lam=args.lam,
            seed=args.seed,
            out=args.out,
            resume=args.resume,
            checkpoint_every=args.checkpoint_every,
            report_every=args.report_every,
            eval_every=args.eval_every,
            gate_opponent=args.gate_opponent,
        )
    )


if __name__ == "__main__":
    main()

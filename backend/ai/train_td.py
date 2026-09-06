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
    the update cost."""

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
        """`e <- lambda*e + grad V(s_t)`."""
        dW1, db1, dW2, db2 = net.gradient(x, h, y)
        if lam == 0.0:  # one-step TD: the trace is just the current gradient
            np.copyto(self.W1, dW1)
            np.copyto(self.b1, db1)
            np.copyto(self.W2, dW2)
            self.b2 = db2
            return
        self.W1 *= lam
        self.W1 += dW1
        self.b1 *= lam
        self.b1 += db1
        self.W2 *= lam
        self.W2 += dW2
        self.b2 = lam * self.b2 + db2

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

    print(
        f"training {config.games} games | hidden={config.hidden_size} "
        f"alpha={config.alpha} lambda={config.lam} seed={config.seed}",
        flush=True,
    )

    for game in range(1, config.games + 1):
        winner, _, plies = self_play_game(
            net,
            engine,
            traces,
            seed=config.seed + game,
            alpha=config.alpha,
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
            elapsed = time.time() - started
            print(
                f"[{game:>7}] {game / elapsed:5.1f} games/s | "
                f"avg plies {total_plies / game:5.1f} | "
                f"p0 wins {wins[0] / max(sum(wins), 1):.2f} | "
                f"sanity win/loss {near_win:.3f}/{near_loss:.3f}"
                + (f" | unfinished {unfinished}" if unfinished else ""),
                flush=True,
            )

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

        if game % config.checkpoint_every == 0:
            net.save(config.out)

    net.save(config.out)
    print(
        f"done in {(time.time() - started) / 60:.1f} min -> {config.out}"
        + (f" (best vs {config.gate_opponent}: {best_gate_rate:.0%})" if best_gate_rate >= 0 else ""),
        flush=True,
    )
    return net


def main() -> None:
    parser = argparse.ArgumentParser(description="TD(lambda) self-play training")
    defaults = TrainConfig()
    parser.add_argument("--games", type=int, default=defaults.games)
    parser.add_argument("--hidden-size", type=int, default=defaults.hidden_size)
    parser.add_argument("--alpha", type=float, default=defaults.alpha)
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

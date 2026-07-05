"""Monte Carlo rollout equity: play a position out to completion many times
under a policy and average the outcome. Used as an alternate leaf evaluator
by `expectiminimax` — ground-truth game outcomes instead of a static eval,
at the cost of far more compute per leaf.
"""

from __future__ import annotations

from ai.base import Engine
from ai.heuristic_engine import HeuristicEngine
from engine.moves import apply_turn, legal_turn_sequences
from engine.rules import has_won, win_multiplier
from engine.state import Dice, GameState

_DEFAULT_POLICY: Engine = HeuristicEngine()


def _play_out(
    state: GameState, seed: int, policy: Engine, max_turns: int
) -> tuple[int, int] | None:
    """Plays one continuation to completion. Returns (winner, multiplier), or
    None if it runs past `max_turns` without a winner."""
    state = state.copy()
    dice_gen = Dice(seed=seed)

    for _ in range(max_turns):
        player = state.turn
        dice = dice_gen.roll()
        sequences = legal_turn_sequences(state, player, dice)
        moves = policy.choose_move(state, dice, sequences)
        state = apply_turn(state, player, moves)
        if has_won(state, player):
            return player, win_multiplier(state, player)
        state.turn = 1 - player

    return None


def rollout_equity(
    state: GameState,
    player: int,
    num_games: int,
    seed: int = 0,
    policy: Engine | None = None,
    max_turns: int = 500,
) -> float:
    """Average signed equity for `player` from `state`, over `num_games`
    continuations played out with `policy` (defaults to the heuristic engine)
    controlling both sides. +multiplier on a win, -multiplier on a loss, a
    continuation that exceeds `max_turns` without finishing scores 0.
    """
    policy = policy or _DEFAULT_POLICY
    total = 0.0
    for i in range(num_games):
        outcome = _play_out(state, seed=seed + i, policy=policy, max_turns=max_turns)
        if outcome is None:
            continue
        winner, multiplier = outcome
        total += multiplier if winner == player else -multiplier
    return total / num_games

"""Hand-tuned positional evaluation for the heuristic engine.

Combines pip race, blot exposure, and prime structure into a single score
from `player`'s perspective — higher is better for `player`.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.state import PLAYER_0, GameState


@dataclass(frozen=True)
class Weights:
    pip: float = 1.0
    blot: float = 4.0
    prime: float = 2.0


DEFAULT_WEIGHTS = Weights()


def _owns(count: int, player: int) -> bool:
    return count > 0 if player == PLAYER_0 else count < 0


def count_blots(state: GameState, player: int) -> int:
    """Points where `player` has exactly one checker — hittable by the opponent."""
    return sum(1 for count in state.board if _owns(count, player) and abs(count) == 1)


def prime_bonus(state: GameState, player: int) -> float:
    """Rewards consecutive made points (2+ checkers). Scored quadratically by
    run length so one long prime beats the same number of isolated points."""
    bonus = 0.0
    run = 0
    for count in state.board:
        if _owns(count, player) and abs(count) >= 2:
            run += 1
        else:
            bonus += run * run
            run = 0
    bonus += run * run
    return bonus


def evaluate(state: GameState, player: int, weights: Weights = DEFAULT_WEIGHTS) -> float:
    opponent = 1 - player
    score = weights.pip * (state.pip_count(opponent) - state.pip_count(player))
    score -= weights.blot * count_blots(state, player)
    score += weights.prime * prime_bonus(state, player)
    return score

"""Core data types for the backgammon rules engine: Dice, GameState, Move.

Board encoding (signed counts): the board is a 24-length array indexed by
absolute point 0-23 (representing standard points 1-24). A positive value
means that many of Player 0's checkers sit on that point; negative means
Player 1's checkers; zero means empty. Player 0 moves in the direction of
decreasing index (24 -> 1) and bears off past index 0. Player 1 moves in
the direction of increasing index (1 -> 24) and bears off past index 23.
Bar and borne-off checkers are tracked separately per player, keyed by
player id (0 or 1), since the signed-count trick doesn't extend to them.
"""

from __future__ import annotations

import random


class Dice:
    """Seedable dice generator — the only place randomness enters the engine."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def roll(self) -> tuple[int, int]:
        return (self._rng.randint(1, 6), self._rng.randint(1, 6))

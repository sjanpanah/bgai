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
from dataclasses import dataclass
from typing import NamedTuple

PLAYER_0 = 0
PLAYER_1 = 1

# Move source/target sentinels, outside the 0-23 point range.
BAR = -1
OFF = 24


class Dice:
    """Seedable dice generator — the only place randomness enters the engine."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def roll(self) -> tuple[int, int]:
        return (self._rng.randint(1, 6), self._rng.randint(1, 6))


class Move(NamedTuple):
    """A single die-step: source and target are absolute point indices 0-23,
    or the BAR/OFF sentinels for re-entry and bearing off."""

    source: int
    target: int


@dataclass
class GameState:
    board: list[int]
    bar: list[int]
    off: list[int]
    turn: int

    @classmethod
    def new_game(cls) -> "GameState":
        board = [0] * 24
        board[0] = -2
        board[5] = 5
        board[7] = 3
        board[11] = -5
        board[12] = 5
        board[16] = -3
        board[18] = -5
        board[23] = 2
        return cls(board=board, bar=[0, 0], off=[0, 0], turn=PLAYER_0)

    def to_dict(self) -> dict:
        return {
            "board": list(self.board),
            "bar": list(self.bar),
            "off": list(self.off),
            "turn": self.turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        return cls(
            board=list(data["board"]),
            bar=list(data["bar"]),
            off=list(data["off"]),
            turn=data["turn"],
        )

    def copy(self) -> "GameState":
        return GameState(
            board=list(self.board), bar=list(self.bar), off=list(self.off), turn=self.turn
        )

    def pip_count(self, player: int) -> int:
        total = self.bar[player] * 25
        for idx, count in enumerate(self.board):
            if player == PLAYER_0 and count > 0:
                total += count * (idx + 1)
            elif player == PLAYER_1 and count < 0:
                total += -count * (24 - idx)
        return total

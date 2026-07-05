"""Weakest engine on the ladder: picks uniformly among legal turn sequences."""

from __future__ import annotations

import random

from engine.state import GameState, Move


class RandomEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def choose_move(
        self,
        state: GameState,
        dice: tuple[int, int],
        legal_sequences: list[list[Move]],
    ) -> list[Move]:
        return self._rng.choice(legal_sequences)

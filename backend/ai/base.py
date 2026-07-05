"""The one stable interface every AI opponent implements.

New engines plug in here only — nothing outside `ai/` (routers, frontend)
should ever need to change when an engine is added or swapped.
"""

from __future__ import annotations

from typing import Protocol

from engine.state import GameState, Move


class Engine(Protocol):
    """`choose_move` picks a full turn sequence from the legal options.

    Callers (routers, the benchmark harness) generate `legal_sequences` via
    `engine.moves.legal_turn_sequences` and pass them in, so every engine
    shares one source of truth for legality and never reimplements it.
    """

    def choose_move(
        self,
        state: GameState,
        dice: tuple[int, int],
        legal_sequences: list[list[Move]],
    ) -> list[Move]: ...

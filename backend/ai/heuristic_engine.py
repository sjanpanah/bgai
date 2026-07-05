"""Heuristic engine: greedy 1-ply search over `evaluate()` (ai/heuristic.py).

For each candidate turn, applies it and scores the resulting position — no
search into the opponent's reply. Deeper lookahead is `expectiminimax`'s job.
"""

from __future__ import annotations

from ai.heuristic import evaluate
from engine.moves import apply_turn
from engine.state import GameState, Move


class HeuristicEngine:
    def choose_move(
        self,
        state: GameState,
        dice: tuple[int, int],
        legal_sequences: list[list[Move]],
    ) -> list[Move]:
        player = state.turn
        return max(
            legal_sequences,
            key=lambda sequence: evaluate(apply_turn(state, player, sequence), player),
        )

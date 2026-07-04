"""Legal move generation and move application.

This module covers single-die legality (bar re-entry and regular point-to-point
movement). Bear-off legality is added on top of this in a later pass; full
two-dice turn-sequence generation (dedup, forced-larger-die rule) is layered
on top of `legal_single_die_moves`.
"""

from __future__ import annotations

from engine.state import BAR, PLAYER_0, PLAYER_1, GameState, Move


def is_blocked(state: GameState, player: int, point: int) -> bool:
    """True if the opponent holds 2+ checkers on `point`, making it unavailable to `player`."""
    count = state.board[point]
    if player == PLAYER_0:
        return count <= -2
    return count >= 2


def _entry_point(player: int, die: int) -> int:
    """Absolute index a checker re-entering from the bar lands on for a given die."""
    return 24 - die if player == PLAYER_0 else die - 1


def legal_single_die_moves(state: GameState, player: int, die: int) -> list[Move]:
    """All legal single-die steps for `player`, ignoring bear-off (added separately)."""
    if state.bar[player] > 0:
        entry = _entry_point(player, die)
        if is_blocked(state, player, entry):
            return []
        return [Move(BAR, entry)]

    direction = -1 if player == PLAYER_0 else 1
    moves = []
    for source in range(24):
        count = state.board[source]
        owns_point = count > 0 if player == PLAYER_0 else count < 0
        if not owns_point:
            continue
        target = source + direction * die
        if 0 <= target <= 23 and not is_blocked(state, player, target):
            moves.append(Move(source, target))
    return moves

"""Hitting, bearing off, and win detection.

Hitting is handled directly in moves.apply_move since it's inseparable from
applying a move to the board. This module covers the two things layered on
top of raw movement: bear-off legality (including the overage rule) and win
detection (single / gammon / backgammon).
"""

from __future__ import annotations

from engine.state import OFF, PLAYER_0, GameState, Move

HOME_RANGE_PLAYER_0 = range(0, 6)
HOME_RANGE_PLAYER_1 = range(18, 24)


def owns_point(state: GameState, player: int, idx: int) -> bool:
    count = state.board[idx]
    return count > 0 if player == PLAYER_0 else count < 0


def distance_to_off(player: int, idx: int) -> int:
    """Pips a checker on `idx` needs to bear off, for `player`."""
    return idx + 1 if player == PLAYER_0 else 24 - idx


def idx_for_distance(player: int, distance: int) -> int:
    return distance - 1 if player == PLAYER_0 else 24 - distance


def all_in_home(state: GameState, player: int) -> bool:
    if state.bar[player] > 0:
        return False
    outside = range(6, 24) if player == PLAYER_0 else range(0, 18)
    return not any(owns_point(state, player, idx) for idx in outside)


def highest_occupied_distance(state: GameState, player: int) -> int | None:
    home = HOME_RANGE_PLAYER_0 if player == PLAYER_0 else HOME_RANGE_PLAYER_1
    distances = [distance_to_off(player, idx) for idx in home if owns_point(state, player, idx)]
    return max(distances) if distances else None


def legal_bear_off_moves(state: GameState, player: int, die: int) -> list[Move]:
    """Bear-off moves legal for `die`: exact-point match, or overage from the
    back-most checker once nothing occupies a higher point."""
    if not all_in_home(state, player):
        return []

    exact_idx = idx_for_distance(player, die)
    if owns_point(state, player, exact_idx):
        return [Move(exact_idx, OFF)]

    highest = highest_occupied_distance(state, player)
    if highest is not None and die > highest:
        return [Move(idx_for_distance(player, highest), OFF)]

    return []


def has_won(state: GameState, player: int) -> bool:
    return state.off[player] == 15


def win_multiplier(state: GameState, winner: int) -> int:
    """1 = single, 2 = gammon (loser bore off none), 3 = backgammon (loser has
    a checker on the bar or in the winner's home board)."""
    loser = 1 - winner
    if state.off[loser] > 0:
        return 1

    winner_home = HOME_RANGE_PLAYER_0 if winner == PLAYER_0 else HOME_RANGE_PLAYER_1
    if state.bar[loser] > 0 or any(owns_point(state, loser, idx) for idx in winner_home):
        return 3

    return 2

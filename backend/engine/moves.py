"""Legal move generation and move application.

This module covers single-die legality (bar re-entry and regular point-to-point
movement). Bear-off legality is added on top of this in a later pass; full
two-dice turn-sequence generation (dedup, forced-larger-die rule) is layered
on top of `legal_single_die_moves`.
"""

from __future__ import annotations

from engine.rules import distance_to_off, legal_bear_off_moves
from engine.state import BAR, OFF, PLAYER_0, GameState, Move


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
    moves.extend(legal_bear_off_moves(state, player, die))
    return moves


def apply_move(state: GameState, player: int, move: Move) -> GameState:
    """Return a new GameState with `move` applied for `player`, hitting any blot."""
    new_state = state.copy()

    if move.source == BAR:
        new_state.bar[player] -= 1
    elif player == PLAYER_0:
        new_state.board[move.source] -= 1
    else:
        new_state.board[move.source] += 1

    if move.target == OFF:
        new_state.off[player] += 1
        return new_state

    opponent = 1 - player
    target_count = new_state.board[move.target]
    if player == PLAYER_0:
        if target_count == -1:
            new_state.bar[opponent] += 1
            target_count = 0
        new_state.board[move.target] = target_count + 1
    else:
        if target_count == 1:
            new_state.bar[opponent] += 1
            target_count = 0
        new_state.board[move.target] = target_count - 1

    return new_state


def apply_turn(state: GameState, player: int, moves: list[Move]) -> GameState:
    for move in moves:
        state = apply_move(state, player, move)
    return state


def _die_used(player: int, move: Move) -> int:
    """Recover which die value produced `move` (moves don't carry it directly)."""
    if move.source == BAR:
        return 24 - move.target if player == PLAYER_0 else move.target + 1
    if move.target == OFF:
        return distance_to_off(player, move.source)
    return abs(move.target - move.source)


def _search(
    state: GameState, player: int, remaining: list[int]
) -> list[tuple[list[Move], GameState]]:
    """All ways to play some/all of `remaining` die values, deepest-first."""
    results = []
    for die in set(remaining):
        for move in legal_single_die_moves(state, player, die):
            next_state = apply_move(state, player, move)
            next_remaining = list(remaining)
            next_remaining.remove(die)
            deeper = _search(next_state, player, next_remaining)
            if deeper:
                for seq, final_state in deeper:
                    results.append(([move, *seq], final_state))
            else:
                results.append(([move], next_state))
    return results


def legal_turn_sequences(state: GameState, player: int, dice: tuple[int, int]) -> list[list[Move]]:
    """Full-turn move sequences for a roll, honoring the use-both-dice and
    forced-larger-die rules, with sequences that reach an identical resulting
    board collapsed to one. Returns [[]] if no move is legal at all (a dance)."""
    d1, d2 = dice
    values = [d1] * 4 if d1 == d2 else [d1, d2]
    results = _search(state, player, values)
    if not results:
        return [[]]

    max_len = max(len(seq) for seq, _ in results)
    candidates = [(seq, fs) for seq, fs in results if len(seq) == max_len]

    if max_len == 1 and d1 != d2:
        larger = max(d1, d2)
        forced = [(seq, fs) for seq, fs in candidates if _die_used(player, seq[0]) == larger]
        if forced:
            candidates = forced

    seen: set[tuple] = set()
    deduped: list[list[Move]] = []
    for seq, fs in candidates:
        key = (tuple(fs.board), tuple(fs.bar), tuple(fs.off))
        if key not in seen:
            seen.add(key)
            deduped.append(seq)
    return deduped

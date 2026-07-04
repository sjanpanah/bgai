"""Differential test against gym-backgammon (the de-facto rules oracle, see
CLAUDE.md's Prior art section): on several positions, our legal_turn_sequences
must reach exactly the same set of resulting board positions as
gym-backgammon's get_valid_plays + execute_play.

gym-backgammon uses the identical board indexing and starting layout as ours
(WHITE/player 0 moving 24->1, BLACK/player 1 moving 1->24), so board arrays
are directly comparable once (count, color) tuples are converted to our
signed-int encoding. A "move" is compared by its resulting position rather
than its raw move-tuple representation, since gym-backgammon's move-tuple
shape doesn't match ours 1:1 (e.g. it uses -1/24 clamped ints or the string
'bar' for off-board/bar sentinels) -- the resulting position is what actually
defines legality.

Requires the `differential` extra (`pip install -e ".[differential]"`); skipped
entirely if it isn't installed.
"""

from __future__ import annotations

import random

import pytest

from engine.moves import apply_turn, legal_turn_sequences
from engine.state import PLAYER_0, PLAYER_1, GameState

pytest.importorskip("pyglet")
gym_bg = pytest.importorskip("gym_backgammon.envs.backgammon")

ALL_ROLLS = [(a, b) for a in range(1, 7) for b in range(1, 7)]


def _state_key(state: GameState) -> tuple:
    return (tuple(state.board), tuple(state.bar), tuple(state.off))


def _to_gym(state: GameState):
    game = gym_bg.Backgammon()
    board = []
    for count in state.board:
        if count > 0:
            board.append((count, gym_bg.WHITE))
        elif count < 0:
            board.append((-count, gym_bg.BLACK))
        else:
            board.append((0, None))
    game.board = board
    game.bar = list(state.bar)
    game.off = list(state.off)
    game.players_positions = game.get_players_positions()
    return game


def _gym_key(game) -> tuple:
    board = tuple(
        count if color == gym_bg.WHITE else -count if color == gym_bg.BLACK else 0
        for count, color in game.board
    )
    return (board, tuple(game.bar), tuple(game.off))


def _our_result_positions(state: GameState, player: int, dice: tuple[int, int]) -> set:
    sequences = legal_turn_sequences(state, player, dice)
    return {_state_key(apply_turn(state, player, seq)) for seq in sequences}


def _gym_result_positions(state: GameState, player: int, dice: tuple[int, int]) -> set:
    # gym-backgammon encodes the roll as signed: negative for WHITE (player 0).
    roll = (-dice[0], -dice[1]) if player == PLAYER_0 else dice
    plays = _to_gym(state).get_valid_plays(player, roll)
    if not plays:
        return {_state_key(state)}
    results = set()
    for play in plays:
        game = _to_gym(state)
        game.execute_play(player, play)
        results.add(_gym_key(game))
    return results


def _assert_matches(state: GameState, player: int) -> None:
    for dice in ALL_ROLLS:
        ours = _our_result_positions(state, player, dice)
        theirs = _gym_result_positions(state, player, dice)
        assert ours == theirs, f"mismatch for player={player} dice={dice}\nboard={state.board}"


def test_new_game_matches_for_both_players():
    state = GameState.new_game()
    _assert_matches(state, PLAYER_0)
    _assert_matches(state, PLAYER_1)


def test_random_midgame_positions_match():
    rng = random.Random(7)
    state = GameState.new_game()
    player = PLAYER_0
    for _ in range(12):
        dice = (rng.randint(1, 6), rng.randint(1, 6))
        sequences = legal_turn_sequences(state, player, dice)
        state = apply_turn(state, player, rng.choice(sequences))
        player = 1 - player
    _assert_matches(state, PLAYER_0)
    _assert_matches(state, PLAYER_1)


def test_bear_off_race_position_matches():
    state = GameState(board=[0] * 24, bar=[0, 0], off=[9, 10], turn=PLAYER_0)
    state.board[0] = 2
    state.board[1] = 1
    state.board[2] = 1
    state.board[3] = 2
    state.board[20] = -2
    state.board[22] = -2
    state.board[23] = -1
    _assert_matches(state, PLAYER_0)
    _assert_matches(state, PLAYER_1)

import numpy as np

from ai.encoding import FEATURE_SIZE, encode, encode_canonical, mirror
from engine.state import PLAYER_0, PLAYER_1, GameState


def test_encode_has_198_features():
    state = GameState.new_game()
    features = encode(state)
    assert features.shape == (198,)
    assert FEATURE_SIZE == 198


def test_encode_new_game_matches_known_starting_position():
    # new_game(): board[5]=5, board[7]=3, board[12]=5, board[23]=2 (player 0);
    # board[0]=-2, board[11]=-5, board[16]=-3, board[18]=-5 (player 1).
    state = GameState.new_game()
    features = encode(state)

    # Player 0's 5-checker point (index 5): n>=1, n>=2, n>=3 all set, (5-3)/2=1.
    assert list(features[5 * 4 : 5 * 4 + 4]) == [1.0, 1.0, 1.0, 1.0]
    # Player 0's 2-checker point (index 23): n>=1, n>=2 set, n>=3 not, overage 0.
    assert list(features[23 * 4 : 23 * 4 + 4]) == [1.0, 1.0, 0.0, 0.0]
    # An empty point (index 1) is all zero.
    assert list(features[1 * 4 : 1 * 4 + 4]) == [0.0, 0.0, 0.0, 0.0]

    # Player 1's block starts at offset 96; point 0 has 2 of player 1's checkers.
    p1_offset = 24 * 4
    assert list(features[p1_offset + 0 * 4 : p1_offset + 0 * 4 + 4]) == [1.0, 1.0, 0.0, 0.0]
    # Player 1's 5-checker point (index 11).
    assert list(features[p1_offset + 11 * 4 : p1_offset + 11 * 4 + 4]) == [1.0, 1.0, 1.0, 1.0]

    # No one on the bar or off yet; player 0 to move.
    assert list(features[192:198]) == [0.0, 0.0, 0.0, 0.0, 1.0, 0.0]


def test_encode_bar_and_off_and_turn():
    state = GameState(board=[0] * 24, bar=[2, 1], off=[3, 15], turn=PLAYER_1)
    features = encode(state)
    assert list(features[192:198]) == [1.0, 0.5, 0.2, 1.0, 0.0, 1.0]


def test_mirror_is_an_involution():
    state = GameState.new_game()
    assert mirror(mirror(state)) == state


def test_mirror_swaps_pip_counts():
    state = GameState.new_game()
    mirrored = mirror(state)
    assert mirrored.pip_count(PLAYER_0) == state.pip_count(PLAYER_1)
    assert mirrored.pip_count(PLAYER_1) == state.pip_count(PLAYER_0)
    assert mirrored.turn == 1 - state.turn


def test_encode_canonical_matches_raw_encode_when_player_0_to_move():
    state = GameState.new_game()
    assert np.array_equal(encode_canonical(state), encode(state))


def test_encode_canonical_mirrors_when_player_1_to_move():
    state = GameState.new_game()
    state.turn = PLAYER_1
    assert np.array_equal(encode_canonical(state), encode(mirror(state)))


def test_encode_canonical_always_reports_player_0_on_roll():
    state = GameState.new_game()
    state.turn = PLAYER_1
    features = encode_canonical(state)
    assert list(features[196:198]) == [1.0, 0.0]


def test_encode_canonical_symmetric_positions_agree():
    # A position and its mirror image, with the mirrored side to move, should
    # encode identically from the canonical (side-to-move) perspective.
    state = GameState.new_game()
    mirrored = mirror(state)
    assert np.array_equal(encode_canonical(state), encode_canonical(mirrored))

from engine.moves import is_blocked, legal_single_die_moves
from engine.state import BAR, PLAYER_0, PLAYER_1, GameState, Move


def test_is_blocked_requires_two_or_more_opponent_checkers():
    state = GameState.new_game()
    # point 12 (index 11) has 5 of player 1's checkers -> blocked for player 0
    assert is_blocked(state, PLAYER_0, 11) is True
    # empty point is never blocked
    assert is_blocked(state, PLAYER_0, 1) is False


def test_single_opponent_checker_is_a_blot_not_blocked():
    state = GameState.new_game()
    state.board[10] = -1  # lone player 1 checker (a blot)
    assert is_blocked(state, PLAYER_0, 10) is False


def test_new_game_opening_moves_for_player_0_die_3():
    state = GameState.new_game()
    moves = legal_single_die_moves(state, PLAYER_0, 3)
    # checkers on points 24, 13, 8, 6 (indices 23, 12, 7, 5) each have an unblocked
    # target three pips away
    assert set(moves) == {
        Move(23, 20),
        Move(12, 9),
        Move(7, 4),
        Move(5, 2),
    }


def test_checkers_on_bar_must_enter_before_any_other_move():
    state = GameState.new_game()
    state.bar[PLAYER_0] = 1
    moves = legal_single_die_moves(state, PLAYER_0, 3)
    assert moves == [Move(BAR, 21)]


def test_bar_entry_blocked_by_opponent_prime():
    state = GameState.new_game()
    state.bar[PLAYER_0] = 1
    state.board[21] = -2  # block player 0's entry point for a die of 3
    assert legal_single_die_moves(state, PLAYER_0, 3) == []


def test_player_1_moves_in_opposite_direction():
    state = GameState.new_game()
    moves = legal_single_die_moves(state, PLAYER_1, 3)
    assert set(moves) == {
        Move(0, 3),
        Move(11, 14),
        Move(16, 19),
        Move(18, 21),
    }

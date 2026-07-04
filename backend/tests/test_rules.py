from engine.rules import all_in_home, has_won, legal_bear_off_moves, win_multiplier
from engine.state import OFF, PLAYER_0, PLAYER_1, GameState, Move


def _empty_state(turn=PLAYER_0):
    return GameState(board=[0] * 24, bar=[0, 0], off=[0, 0], turn=turn)


def test_all_in_home_true_when_only_home_checkers():
    state = _empty_state()
    state.board[2] = 1
    state.board[5] = 1
    assert all_in_home(state, PLAYER_0) is True


def test_all_in_home_false_with_checker_outside():
    state = _empty_state()
    state.board[2] = 1
    state.board[10] = 1
    assert all_in_home(state, PLAYER_0) is False


def test_all_in_home_false_with_checker_on_bar():
    state = _empty_state()
    state.board[2] = 1
    state.bar[PLAYER_0] = 1
    assert all_in_home(state, PLAYER_0) is False


def test_exact_bear_off():
    state = _empty_state()
    state.board[2] = 1  # distance 3
    assert legal_bear_off_moves(state, PLAYER_0, 3) == [Move(2, OFF)]


def test_overage_bear_off_from_back_checker():
    state = _empty_state()
    state.board[0] = 1  # distance 1, the only (and thus back-most) checker
    assert legal_bear_off_moves(state, PLAYER_0, 6) == [Move(0, OFF)]


def test_overage_blocked_by_a_higher_occupied_point():
    state = _empty_state()
    state.board[0] = 1  # distance 1
    state.board[3] = 1  # distance 4 (the back-most checker)
    # die of 3 doesn't exactly match either checker and isn't an overage
    # (3 is not greater than the highest occupied distance of 4)
    assert legal_bear_off_moves(state, PLAYER_0, 3) == []
    # die of 5 is an overage relative to the highest occupied distance (4)
    assert legal_bear_off_moves(state, PLAYER_0, 5) == [Move(3, OFF)]


def test_player_1_bear_off_mirrors_player_0():
    state = _empty_state()
    state.board[21] = -1  # distance 3 for player 1
    assert legal_bear_off_moves(state, PLAYER_1, 3) == [Move(21, OFF)]


def test_has_won():
    state = _empty_state()
    state.off[PLAYER_0] = 15
    assert has_won(state, PLAYER_0) is True
    assert has_won(state, PLAYER_1) is False


def test_win_multiplier_single():
    state = _empty_state()
    state.off[PLAYER_0] = 15
    state.off[PLAYER_1] = 3
    assert win_multiplier(state, PLAYER_0) == 1


def test_win_multiplier_gammon():
    state = _empty_state()
    state.off[PLAYER_0] = 15
    state.off[PLAYER_1] = 0
    state.board[10] = -3  # loser's checkers are out on the board, not in winner's home
    assert win_multiplier(state, PLAYER_0) == 2


def test_win_multiplier_backgammon_checker_in_winners_home():
    state = _empty_state()
    state.off[PLAYER_0] = 15
    state.off[PLAYER_1] = 0
    state.board[2] = -1  # player 1 checker sitting in player 0's home board
    assert win_multiplier(state, PLAYER_0) == 3


def test_win_multiplier_backgammon_checker_on_bar():
    state = _empty_state()
    state.off[PLAYER_0] = 15
    state.off[PLAYER_1] = 0
    state.bar[PLAYER_1] = 1
    assert win_multiplier(state, PLAYER_0) == 3

from engine.moves import apply_move
from engine.state import BAR, OFF, PLAYER_0, PLAYER_1, GameState, Move


def test_apply_regular_move_updates_source_and_target():
    state = GameState.new_game()
    result = apply_move(state, PLAYER_0, Move(23, 20))
    assert result.board[23] == 1
    assert result.board[20] == 1
    # original state is untouched
    assert state.board[23] == 2
    assert state.board[20] == 0


def test_apply_move_hits_opponent_blot():
    state = GameState.new_game()
    state.board[20] = -1  # lone player 1 checker
    result = apply_move(state, PLAYER_0, Move(23, 20))
    assert result.board[20] == 1
    assert result.bar[PLAYER_1] == 1


def test_apply_move_stacks_on_own_checkers():
    state = GameState.new_game()
    result = apply_move(state, PLAYER_0, Move(7, 5))
    assert result.board[7] == 2
    assert result.board[5] == 6


def test_apply_bar_entry_move():
    state = GameState.new_game()
    state.bar[PLAYER_0] = 1
    result = apply_move(state, PLAYER_0, Move(BAR, 21))
    assert result.bar[PLAYER_0] == 0
    assert result.board[21] == 1


def test_apply_bear_off_move():
    state = GameState.new_game()
    result = apply_move(state, PLAYER_0, Move(5, OFF))
    assert result.board[5] == 4
    assert result.off[PLAYER_0] == 1


def test_apply_move_for_player_1_direction_and_hit():
    state = GameState.new_game()
    state.board[21] = 1  # lone player 0 checker
    result = apply_move(state, PLAYER_1, Move(18, 21))
    assert result.board[18] == -4
    assert result.board[21] == -1
    assert result.bar[PLAYER_0] == 1

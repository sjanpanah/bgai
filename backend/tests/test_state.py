from engine.state import PLAYER_0, PLAYER_1, GameState


def test_new_game_checker_counts():
    state = GameState.new_game()
    p0 = sum(c for c in state.board if c > 0)
    p1 = sum(-c for c in state.board if c < 0)
    assert p0 == 15
    assert p1 == 15
    assert state.bar == [0, 0]
    assert state.off == [0, 0]
    assert state.turn == PLAYER_0


def test_new_game_pip_count_is_167_each_side():
    state = GameState.new_game()
    assert state.pip_count(PLAYER_0) == 167
    assert state.pip_count(PLAYER_1) == 167


def test_to_dict_from_dict_round_trip():
    state = GameState.new_game()
    restored = GameState.from_dict(state.to_dict())
    assert restored == state


def test_copy_is_independent():
    state = GameState.new_game()
    other = state.copy()
    other.board[0] = 0
    other.bar[0] = 5
    assert state.board[0] == -2
    assert state.bar[0] == 0

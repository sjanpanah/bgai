from ai.heuristic import count_blots, evaluate, prime_bonus
from engine.state import PLAYER_0, PLAYER_1, GameState


def _empty_state(turn: int = PLAYER_0) -> GameState:
    return GameState(board=[0] * 24, bar=[0, 0], off=[0, 0], turn=turn)


def test_count_blots_counts_single_checkers_only():
    state = _empty_state()
    state.board[5] = 1
    state.board[7] = 2
    state.board[10] = -1
    assert count_blots(state, PLAYER_0) == 1
    assert count_blots(state, PLAYER_1) == 1


def test_prime_bonus_rewards_consecutive_runs_over_isolated_points():
    consecutive = _empty_state()
    consecutive.board[0:3] = [2, 2, 2]

    isolated = _empty_state()
    isolated.board[0] = 2
    isolated.board[10] = 2
    isolated.board[20] = 2

    assert prime_bonus(consecutive, PLAYER_0) > prime_bonus(isolated, PLAYER_0)


def test_prime_bonus_ignores_blots():
    state = _empty_state()
    state.board[0:3] = [1, 1, 1]
    assert prime_bonus(state, PLAYER_0) == 0


def test_evaluate_favors_the_player_with_the_pip_lead():
    # Same fixed opponent position both times; only player 0's pip count varies.
    ahead = _empty_state()
    ahead.board[0] = 2
    ahead.board[23] = -2

    behind = _empty_state()
    behind.board[20] = 2
    behind.board[23] = -2

    assert evaluate(ahead, PLAYER_0) > evaluate(behind, PLAYER_0)


def test_evaluate_penalizes_blots():
    # Same total pip count either way — only whether the checkers are stacked
    # (safe) or split into two blots (exposed) differs.
    safe = _empty_state()
    safe.board[10] = 2

    exposed = _empty_state()
    exposed.board[9] = 1
    exposed.board[11] = 1

    assert evaluate(safe, PLAYER_0) > evaluate(exposed, PLAYER_0)

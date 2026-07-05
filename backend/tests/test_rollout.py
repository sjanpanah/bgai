from ai.rollout import rollout_equity
from engine.state import PLAYER_0, PLAYER_1, GameState


def _forced_win_state(turn: int) -> GameState:
    # Player 0 has exactly one checker left, already home on point 1 — any
    # roll bears it off next turn and wins outright (loser already bore off
    # some checkers, so it's a plain win, multiplier 1, no gammon ambiguity).
    board = [0] * 24
    board[0] = 1
    board[23] = -1
    return GameState(board=board, bar=[0, 0], off=[14, 3], turn=turn)


def test_rollout_equity_on_a_forced_win_is_exactly_the_win_multiplier():
    state = _forced_win_state(PLAYER_0)
    equity = rollout_equity(state, PLAYER_0, num_games=3, seed=0)
    assert equity == 1.0


def test_rollout_equity_is_symmetric_for_the_losing_player():
    state = _forced_win_state(PLAYER_0)
    equity = rollout_equity(state, PLAYER_1, num_games=3, seed=0)
    assert equity == -1.0

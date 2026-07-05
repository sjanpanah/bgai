from ai.heuristic_engine import HeuristicEngine
from engine.moves import apply_turn, legal_turn_sequences
from engine.state import PLAYER_0, GameState, Move


def test_heuristic_engine_picks_a_legal_sequence():
    state = GameState.new_game()
    dice = (3, 1)
    sequences = legal_turn_sequences(state, state.turn, dice)

    engine = HeuristicEngine()
    chosen = engine.choose_move(state, dice, sequences)

    assert chosen in sequences


def test_heuristic_engine_handles_forced_dance():
    state = GameState.new_game()
    engine = HeuristicEngine()
    chosen = engine.choose_move(state, (1, 1), [[]])
    assert chosen == []


def test_heuristic_engine_prefers_hitting_a_blot_over_leaving_one_exposed():
    # Player 0 to move with a 6: one option hits player 1's blot on point 17
    # (0-indexed) and clears home to safety; the other leaves a blot behind.
    board = [0] * 24
    board[23] = 2  # player 0 checkers that can run 23 -> 17
    board[17] = -1  # player 1 blot sitting on the target point
    state = GameState(board=board, bar=[0, 0], off=[0, 0], turn=PLAYER_0)
    dice = (6, 6)

    sequences = legal_turn_sequences(state, state.turn, dice)
    engine = HeuristicEngine()
    chosen = engine.choose_move(state, dice, sequences)

    assert Move(23, 17) in chosen


def test_heuristic_engine_avoids_breaking_a_made_point_into_a_blot():
    # Player 0 has a made point on 5 and a lone runner on 10. With a 5-1,
    # one option is 10/5 (runner joins the made point, both dice used safely)
    # while another breaks the point on 5 into blots. The heuristic should
    # keep the made point intact.
    board = [0] * 24
    board[5] = 2
    board[10] = 1
    board[23] = -2
    state = GameState(board=board, bar=[0, 0], off=[0, 0], turn=PLAYER_0)
    dice = (5, 1)

    sequences = legal_turn_sequences(state, state.turn, dice)
    engine = HeuristicEngine()
    chosen = engine.choose_move(state, dice, sequences)

    result = apply_turn(state, PLAYER_0, chosen)
    assert result.board[5] >= 2

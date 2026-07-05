from ai.expectiminimax import ExpectiminimaxEngine
from ai.heuristic_engine import HeuristicEngine
from engine.moves import apply_turn, legal_turn_sequences
from engine.state import PLAYER_0, PLAYER_1, GameState


def test_expectiminimax_picks_a_legal_sequence():
    state = GameState.new_game()
    dice = (3, 1)
    sequences = legal_turn_sequences(state, state.turn, dice)

    engine = ExpectiminimaxEngine(depth=1, candidates=6)
    chosen = engine.choose_move(state, dice, sequences)

    assert chosen in sequences


def test_expectiminimax_handles_forced_dance():
    state = GameState.new_game()
    engine = ExpectiminimaxEngine(depth=0)
    chosen = engine.choose_move(state, (1, 1), [[]])
    assert chosen == []


def test_expectiminimax_depth_zero_matches_heuristic_engine():
    # depth=0 has no chance-node lookahead at all — it's the same greedy
    # 1-ply choice as HeuristicEngine, just reached via a different code path.
    state = GameState.new_game()
    dice = (3, 1)
    sequences = legal_turn_sequences(state, state.turn, dice)

    heuristic_choice = HeuristicEngine().choose_move(state, dice, sequences)
    expectiminimax_choice = ExpectiminimaxEngine(depth=0).choose_move(state, dice, sequences)

    assert heuristic_choice == expectiminimax_choice


def test_expectiminimax_depth_one_declines_a_hit_with_a_near_certain_return_shot():
    # Player 0 can hit player 1's blot on 10 (0-indexed) with a 2, but player
    # 1 has checkers on 7/8/9 that hit back on 20 of the 21 distinct rolls.
    # A 1-ply eval scores "hit and leave a blot on 10" the same as "hit and
    # run the hitter to safety on 4" (both clear one blot, add one) and picks
    # among the tied top scorers — greedily, with no idea either leaves it
    # exposed to those checkers. 1-ply lookahead through the opponent's reply
    # should see the near-certain return hit and prefer not hitting at all.
    board = [0] * 24
    board[12] = 1  # player 0's hitter
    board[20] = 1  # player 0's other checker
    board[10] = -1  # player 1's blot, hittable with a 2
    board[9] = -1
    board[8] = -1
    board[7] = -1  # player 1 checkers positioned to return-hit point 10
    state = GameState(board=board, bar=[0, 0], off=[0, 0], turn=PLAYER_0)
    dice = (2, 6)
    sequences = legal_turn_sequences(state, PLAYER_0, dice)

    greedy_choice = ExpectiminimaxEngine(depth=0).choose_move(state, dice, sequences)
    lookahead_choice = ExpectiminimaxEngine(depth=1, candidates=8).choose_move(
        state, dice, sequences
    )

    greedy_result = apply_turn(state, PLAYER_0, greedy_choice)
    lookahead_result = apply_turn(state, PLAYER_0, lookahead_choice)

    assert greedy_result.bar[PLAYER_1] == 1  # greedy takes the tempting hit
    assert lookahead_result.bar[PLAYER_1] == 0  # lookahead declines it entirely

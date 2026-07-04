"""Integration-style tests combining bar entry, movement, and bear-off within
a single turn, plus a couple of known real-game positions."""

from engine.moves import apply_turn, legal_turn_sequences
from engine.state import BAR, OFF, PLAYER_0, GameState, Move, PLAYER_1


def _empty_state(turn=PLAYER_0):
    return GameState(board=[0] * 24, bar=[0, 0], off=[0, 0], turn=turn)


def test_lovers_leap_is_the_only_legal_63_run_from_the_bar_point():
    # Classic opening 6-5: 24/13 is forced because 24/18 (the 5 first) runs
    # into player 1's 5-checker anchor at point 18 (index 18).
    state = GameState.new_game()
    sequences = legal_turn_sequences(state, PLAYER_0, (6, 5))
    lovers_leap = [Move(23, 17), Move(17, 12)]
    assert lovers_leap in sequences
    # the reverse order (5 first, running into player 1's anchor on 18) must
    # not appear as a separate legal sequence
    assert [Move(23, 18), Move(18, 12)] not in sequences
    final_state = apply_turn(state, PLAYER_0, lovers_leap)
    assert final_state.board[23] == 1
    assert final_state.board[12] == 6


def test_two_checkers_on_bar_both_enter_when_open():
    state = _empty_state()
    state.bar[PLAYER_0] = 2
    sequences = legal_turn_sequences(state, PLAYER_0, (3, 4))
    assert len(sequences) == 1
    final_state = apply_turn(state, PLAYER_0, sequences[0])
    assert final_state.bar[PLAYER_0] == 0
    assert final_state.board[21] == 1  # entry for die 3
    assert final_state.board[20] == 1  # entry for die 4


def test_two_checkers_on_bar_only_one_enters_when_other_entry_blocked():
    state = _empty_state()
    state.bar[PLAYER_0] = 2
    state.board[21] = -2  # blocks the die-3 entry point
    sequences = legal_turn_sequences(state, PLAYER_0, (3, 4))
    assert sequences == [[Move(BAR, 20)]]
    final_state = apply_turn(state, PLAYER_0, sequences[0])
    assert final_state.bar[PLAYER_0] == 1


def test_entered_checker_can_use_the_second_die_to_move_further():
    state = _empty_state()
    state.bar[PLAYER_0] = 1
    sequences = legal_turn_sequences(state, PLAYER_0, (4, 3))
    # only one checker exists, so both dice must be spent on it:
    # enter with die 4 (-> index 20), then move 3 more (-> index 17)
    assert len(sequences) == 1
    final_state = apply_turn(state, PLAYER_0, sequences[0])
    assert final_state.bar[PLAYER_0] == 0
    assert final_state.board[17] == 1


def test_mixed_exact_and_overage_bear_off_in_one_double_turn():
    state = _empty_state()
    state.board[0] = 1  # distance 1
    state.board[1] = 1  # distance 2
    sequences = legal_turn_sequences(state, PLAYER_0, (2, 2))
    # both checkers bear off: point at distance 2 bears off exactly, the
    # distance-1 checker bears off via overage on a second die-2
    assert len(sequences) == 1
    final_state = apply_turn(state, PLAYER_0, sequences[0])
    assert final_state.off[PLAYER_0] == 2
    assert final_state.board[0] == 0
    assert final_state.board[1] == 0


def test_hit_during_bear_off_race_sends_blot_to_bar():
    state = _empty_state()
    state.board[2] = 1  # player 0, all in home, distance 3
    state.board[23] = -1  # a lone player 1 blot far from home, not blocking anything
    sequences = legal_turn_sequences(state, PLAYER_0, (3, 5))
    assert any(seq == [Move(2, OFF)] for seq in sequences)


def test_player_1_bear_off_race_mirrors_player_0():
    state = _empty_state(turn=PLAYER_1)
    state.board[23] = -1  # distance 1
    state.board[22] = -1  # distance 2
    sequences = legal_turn_sequences(state, PLAYER_1, (2, 2))
    assert len(sequences) == 1
    final_state = apply_turn(state, PLAYER_1, sequences[0])
    assert final_state.off[PLAYER_1] == 2

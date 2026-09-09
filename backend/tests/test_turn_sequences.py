from engine.moves import (
    apply_move,
    apply_turn,
    combined_moves,
    legal_next_moves,
    legal_single_die_moves,
    legal_turn_sequences,
)
from engine.state import OFF, PLAYER_0, PLAYER_1, Dice, GameState, Move


def _empty_state(turn=PLAYER_0):
    return GameState(board=[0] * 24, bar=[0, 0], off=[0, 0], turn=turn)


def test_forced_larger_die_when_only_one_order_survives():
    state = _empty_state()
    state.board[15] = 1
    state.board[6] = -2  # blocks the point both 6-first and 3-then-3 paths would hit
    # die6 first: 15->9 (open), then die3: 9->6 blocked -> stops at length 1
    # die3 first: 15->12 (open), then die6: 12->6 blocked -> stops at length 1
    sequences = legal_turn_sequences(state, PLAYER_0, (6, 3))
    assert sequences == [[Move(15, 9)]]


def test_must_use_both_dice_when_possible_over_using_only_one():
    state = _empty_state()
    state.board[15] = 1
    # both die orders (3-then-2 and 2-then-3) are legal and land on the same
    # point, so besides "both dice used" this also exercises dedup
    sequences = legal_turn_sequences(state, PLAYER_0, (3, 2))
    assert len(sequences) == 1
    assert all(len(seq) == 2 for seq in sequences)
    final_state = apply_turn(state, PLAYER_0, sequences[0])
    assert final_state.board[10] == 1
    assert final_state.board[15] == 0


def test_legal_next_moves_offers_both_dice_from_same_source():
    """Regression test: legal_turn_sequences dedups by final board, which
    silently drops a valid first move whenever some other checker's move
    order reaches the same final board (very common when two independent
    checkers move). legal_next_moves must not lose that option."""
    state = GameState.new_game()
    # Opening 5-3: point 8 (idx 7) can play either die as a first step.
    next_moves = legal_next_moves(state, PLAYER_0, [5, 3])
    from_point_8 = {m.target for m in next_moves if m.source == 7}
    assert from_point_8 == {2, 4}  # 8/3 (die 5) and 8/5 (die 3)


def test_different_orderings_reaching_same_board_are_deduped():
    state = _empty_state()
    state.board[20] = 1
    state.board[10] = 1
    # cap each checker at exactly two die-2 uses so the only max-length (4)
    # outcome is a 2/2 split between them -- the six interleavings of that
    # split all land on the same final board and must collapse to one
    state.board[14] = -2  # stops the 20-checker after two uses (20->18->16)
    state.board[4] = -2  # stops the 10-checker after two uses (10->8->6)
    sequences = legal_turn_sequences(state, PLAYER_0, (2, 2))
    assert len(sequences) == 1
    final_state = apply_turn(state, PLAYER_0, sequences[0])
    assert final_state.board[16] == 1
    assert final_state.board[6] == 1
    assert final_state.board[20] == 0
    assert final_state.board[10] == 0


def test_dance_when_no_legal_move_exists():
    state = _empty_state()
    state.bar[PLAYER_0] = 1
    state.board[21] = -2  # blocks entry for die 3
    state.board[20] = -2  # blocks entry for die 4
    sequences = legal_turn_sequences(state, PLAYER_0, (3, 4))
    assert sequences == [[]]


def test_combined_moves_offers_both_orders_when_they_land_together():
    state = _empty_state()
    state.board[15] = 1
    # 3+2 = 5 away from point 15 (index 15, "16" in 1-based) lands on index 10.
    # Both die orders are legal here and dedup on the same (source, target)
    # key, so only one survives -- which intermediate point it passes through
    # isn't guaranteed, only that it's a genuine hop between 15 and 10.
    combos = combined_moves(state, PLAYER_0, [3, 2])
    assert len(combos) == 1
    first, second = combos[0]
    assert first.source == 15
    assert second.target == 10
    assert first.target == second.source
    assert first.target in (12, 13)


def test_combined_moves_empty_with_fewer_than_two_dice():
    state = _empty_state()
    state.board[15] = 1
    assert combined_moves(state, PLAYER_0, [3]) == []
    assert combined_moves(state, PLAYER_0, []) == []


def test_combined_moves_excludes_blocked_intermediate():
    state = _empty_state()
    state.board[15] = 1
    state.board[12] = -2  # blocks the die-3-first order's first hop (15 -> 12)
    state.board[13] = -2  # blocks the die-2-first order's first hop (15 -> 13)
    combos = combined_moves(state, PLAYER_0, [3, 2])
    assert combos == []


def test_combined_moves_excludes_pair_when_orders_diverge():
    """3-then-6 hits the blot on 12 on the way through; 6-then-3 never touches
    12 at all. Both orders land the checker on the same final square (6), but
    they leave different boards (a hit vs no hit) -- that's a real decision,
    not a detail a single click should paper over, so the pair must not be
    offered at all rather than picking one order arbitrarily."""
    state = _empty_state()
    state.board[15] = 1
    state.board[12] = -1  # a blot: not blocked, but hit if landed on
    combos = combined_moves(state, PLAYER_0, [3, 6])
    assert combos == []


def test_combined_moves_on_doubles_chains_exactly_two_dice():
    state = _empty_state()
    state.board[20] = 1
    combos = combined_moves(state, PLAYER_0, [2, 2, 2, 2])
    assert combos == [(Move(20, 18), Move(18, 16))]


def test_doubles_allow_four_moves():
    state = _empty_state()
    state.board[20] = 1
    sequences = legal_turn_sequences(state, PLAYER_0, (2, 2))
    assert sequences == [
        [Move(20, 18), Move(18, 16), Move(16, 14), Move(14, 12)],
    ]


def test_combined_moves_survives_bear_off_overage():
    """Bearing off with overage legally plays a die *larger* than the distance
    to the edge, so recovering the consumed die by arithmetic names a die the
    player doesn't hold and `remove` raises. This 500'd the API for most games
    that reached bear-off. Two checkers on the 5-point matter: playing the
    overage bear-off first still leaves the other checker to play the 1, so the
    sequence survives max-length filtering and the faulty die lookup is reached.
    """
    state = _empty_state()
    state.board[4] = 2  # the 5-point (distance 5), borne off by the 6 as overage
    state.board[23] = -2
    state.off = [13, 13]
    # No combo exists here -- after 4->3 the overage still bears off from 4, not
    # from 3 -- so the assertion that matters is that it returns at all.
    assert combined_moves(state, PLAYER_0, [1, 6]) == []


def test_combined_moves_offers_a_combo_ending_in_an_overage_bear_off():
    """The second hop bears off with overage once the first hop clears the
    higher point: 6->5 with the 1, then off from the 5-point with the 6."""
    state = _empty_state()
    state.board[4] = 2
    state.board[5] = 1  # the 6-point; vacating it is what makes the overage legal
    state.board[23] = -2
    state.off = [12, 13]
    assert combined_moves(state, PLAYER_0, [1, 6]) == [(Move(5, 4), Move(4, OFF))]


def test_combined_moves_never_raises_over_random_games():
    """The bear-off-overage crash slipped past 123 tests because no test ever
    called `combined_moves` on a bear-off position. Play whole games and call
    it at every position reached, which is how the bug was actually found."""
    for seed in range(20):
        dice = Dice(seed)
        state = GameState.new_game()
        for _ in range(400):
            player = state.turn
            values = list(dice.roll())
            if values[0] == values[1]:
                values = values * 2

            remaining = list(values)
            while remaining:
                # The call under test: it must survive every position a real
                # game reaches, bear-off and overage included.
                combined_moves(state, player, remaining)
                moves = legal_next_moves(state, player, remaining)
                if not moves:
                    break
                move = moves[0]
                die = next(
                    d
                    for d in sorted(set(remaining))
                    if move in legal_single_die_moves(state, player, d)
                )
                state = apply_move(state, player, move)
                remaining.remove(die)

            if state.off[PLAYER_0] == 15 or state.off[PLAYER_1] == 15:
                break
            state.turn = 1 - player

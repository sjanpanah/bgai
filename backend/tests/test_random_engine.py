from ai.random_engine import RandomEngine
from engine.moves import legal_turn_sequences
from engine.state import Dice, GameState


def test_random_engine_picks_a_legal_sequence():
    state = GameState.new_game()
    dice = Dice(seed=1).roll()
    sequences = legal_turn_sequences(state, state.turn, dice)

    engine = RandomEngine(seed=1)
    chosen = engine.choose_move(state, dice, sequences)

    assert chosen in sequences


def test_random_engine_handles_forced_dance():
    state = GameState.new_game()
    engine = RandomEngine(seed=1)
    chosen = engine.choose_move(state, (1, 1), [[]])
    assert chosen == []

from ai.neural_engine import NeuralEngine
from ai.neural_net import NeuralNet
from engine.moves import legal_turn_sequences
from engine.state import PLAYER_0, GameState, Move


def test_neural_engine_picks_a_legal_sequence():
    state = GameState.new_game()
    dice = (3, 1)
    sequences = legal_turn_sequences(state, state.turn, dice)

    engine = NeuralEngine(net=NeuralNet(seed=0))
    chosen = engine.choose_move(state, dice, sequences)

    assert chosen in sequences


def test_neural_engine_handles_forced_dance():
    state = GameState.new_game()
    engine = NeuralEngine(net=NeuralNet(seed=0))
    chosen = engine.choose_move(state, (1, 1), [[]])
    assert chosen == []


def test_neural_engine_prefers_an_immediate_win():
    # Player 0 has one checker left on point 0 (distance 1) — bearing it off
    # wins outright. The other option must not be preferred over a win.
    board = [0] * 24
    board[0] = 1
    board[18] = -1
    state = GameState(board=board, bar=[0, 0], off=[0, 14], turn=PLAYER_0)
    dice = (1, 6)

    sequences = legal_turn_sequences(state, state.turn, dice)
    engine = NeuralEngine(net=NeuralNet(seed=0))
    chosen = engine.choose_move(state, dice, sequences)

    from engine.state import OFF

    assert Move(0, OFF) in chosen


def test_neural_engine_loads_weights_from_path(tmp_path):
    path = tmp_path / "checkpoint.npz"
    NeuralNet(seed=42).save(path)

    engine = NeuralEngine(weights_path=path)
    state = GameState.new_game()
    dice = (3, 1)
    sequences = legal_turn_sequences(state, state.turn, dice)
    assert engine.choose_move(state, dice, sequences) in sequences

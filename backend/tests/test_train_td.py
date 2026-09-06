import numpy as np

from ai.encoding import encode_canonical
from ai.neural_engine import NeuralEngine
from ai.neural_net import NeuralNet
from ai.train_td import (
    TrainConfig,
    Traces,
    _near_loss_position,
    _near_win_position,
    sanity_values,
    self_play_game,
    train,
)
from engine.state import PLAYER_0, GameState


def _fresh(seed=0, hidden_size=10):
    net = NeuralNet(hidden_size=hidden_size, seed=seed)
    return net, NeuralEngine(net=net), Traces(net)


def test_traces_with_lambda_zero_equal_the_raw_gradient():
    net, _, traces = _fresh()
    x = encode_canonical(GameState.new_game())
    h, y = net.forward(x)
    dW1, db1, dW2, db2 = net.gradient(x, h, y)

    traces.accumulate(net, x, h, y, lam=0.0)
    assert np.array_equal(traces.W1, dW1)
    assert np.array_equal(traces.b1, db1)
    assert np.array_equal(traces.W2, dW2)
    assert traces.b2 == db2


def test_traces_decay_and_accumulate_with_lambda():
    net, _, traces = _fresh()
    x = encode_canonical(GameState.new_game())
    h, y = net.forward(x)
    dW1, _, _, _ = net.gradient(x, h, y)

    traces.accumulate(net, x, h, y, lam=0.5)
    traces.accumulate(net, x, h, y, lam=0.5)
    # Second step: e = 0.5 * grad + grad = 1.5 * grad (same x both times).
    assert np.allclose(traces.W1, 1.5 * dW1)


def test_traces_reset_zeroes_everything():
    net, _, traces = _fresh()
    x = encode_canonical(GameState.new_game())
    h, y = net.forward(x)
    traces.accumulate(net, x, h, y, lam=0.0)
    traces.reset()
    assert not traces.W1.any()
    assert not traces.b1.any()
    assert not traces.W2.any()
    assert traces.b2 == 0.0


def test_winning_move_pushes_the_positions_value_up():
    # The terminal TD branch: target is 1.0, so V(s_t) must increase. This is
    # the direct check that the winning-move perspective isn't inverted.
    net, engine, traces = _fresh()
    board = [0] * 24
    board[0] = 1
    board[23] = -15
    state = GameState(board=board, bar=[0, 0], off=[14, 0], turn=PLAYER_0)

    before = net.value(encode_canonical(state))
    winner, _, plies = self_play_game(
        net, engine, traces, seed=1, alpha=0.5, lam=0.0, max_turns=10, start_state=state
    )
    after = net.value(encode_canonical(state))

    assert winner == PLAYER_0
    assert plies == 1
    assert after > before


def test_self_play_game_finishes_and_reports_a_winner():
    net, engine, traces = _fresh()
    winner, multiplier, plies = self_play_game(
        net, engine, traces, seed=3, alpha=0.1, lam=0.0, max_turns=500
    )
    assert winner in (0, 1)
    assert multiplier in (1, 2, 3)
    assert 0 < plies <= 500


def test_sanity_values_are_probabilities():
    net = NeuralNet(seed=0)
    near_win, near_loss = sanity_values(net)
    assert 0.0 <= near_win <= 1.0
    assert 0.0 <= near_loss <= 1.0


def test_near_win_and_near_loss_positions_are_mirror_images():
    win, loss = _near_win_position(), _near_loss_position()
    assert win.turn == loss.turn == PLAYER_0
    assert win.off[0] == loss.off[1] == 14


def test_short_training_run_separates_won_from_lost_positions(tmp_path):
    # The integration gate from CLAUDE.md's M5 risks: if the TD perspective
    # handling were inverted or self-cancelling, these two values would stay
    # together (or swap) instead of spreading toward 1 and 0.
    config = TrainConfig(
        games=150,
        hidden_size=40,
        seed=42,
        report_every=10**9,
        eval_every=10**9,
        checkpoint_every=10**9,
        out=tmp_path / "checkpoint.npz",
    )
    net = train(config)
    near_win, near_loss = sanity_values(net)
    assert near_win > near_loss
    assert config.out.exists()

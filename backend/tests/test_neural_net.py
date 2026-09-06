import numpy as np

from ai.encoding import FEATURE_SIZE
from ai.neural_net import NeuralNet


def test_forward_shapes_and_range():
    net = NeuralNet(hidden_size=10, seed=0)
    x = np.zeros(FEATURE_SIZE)
    h, y = net.forward(x)
    assert h.shape == (10,)
    assert 0.0 <= y <= 1.0


def test_value_matches_forward_output():
    net = NeuralNet(hidden_size=10, seed=0)
    x = np.random.default_rng(1).random(FEATURE_SIZE)
    _, y = net.forward(x)
    assert net.value(x) == y


def test_gradient_shapes():
    net = NeuralNet(hidden_size=10, seed=0)
    x = np.random.default_rng(2).random(FEATURE_SIZE)
    h, y = net.forward(x)
    dW1, db1, dW2, db2 = net.gradient(x, h, y)
    assert dW1.shape == net.W1.shape
    assert db1.shape == net.b1.shape
    assert dW2.shape == net.W2.shape
    assert isinstance(db2, float)


def test_gradient_direction_reduces_output_error_after_one_step():
    # A single gradient-ascent step on y should increase y (sanity check that
    # the gradient actually points the direction it claims to).
    net = NeuralNet(hidden_size=10, seed=0)
    x = np.random.default_rng(3).random(FEATURE_SIZE)
    h, y_before = net.forward(x)
    dW1, db1, dW2, db2 = net.gradient(x, h, y_before)
    net.W1 += 0.1 * dW1
    net.b1 += 0.1 * db1
    net.W2 += 0.1 * dW2
    net.b2 += 0.1 * db2
    _, y_after = net.forward(x)
    assert y_after > y_before


def test_save_and_load_round_trip(tmp_path):
    net = NeuralNet(hidden_size=12, seed=5)
    path = tmp_path / "checkpoint.npz"
    net.save(path)

    loaded = NeuralNet.load(path)
    x = np.random.default_rng(6).random(FEATURE_SIZE)
    assert net.value(x) == loaded.value(x)
    assert np.array_equal(net.W1, loaded.W1)
    assert np.array_equal(net.b1, loaded.b1)
    assert np.array_equal(net.W2, loaded.W2)
    assert net.b2 == loaded.b2

import numpy as np
import pytest

from ai.encoding import encode_canonical
from ai.neural_engine import NeuralEngine
from ai.neural_net import NeuralNet
from ai.train_td import (
    TrainConfig,
    Traces,
    _near_loss_position,
    _near_win_position,
    alpha_for_game,
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
    # The decay is -lambda (perspective flips every ply), so the second step
    # gives e = -0.5*grad + grad = 0.5*grad, not 1.5*grad.
    assert np.allclose(traces.W1, 0.5 * dW1)


def test_trace_matches_fixed_perspective_td_lambda():
    """The -lambda trace over the side-to-move value `V` must produce exactly
    the same weight updates as textbook TD(lambda) over a fixed-perspective
    value `U` = P(player 0 wins). This is the equivalence the sign is there to
    preserve; a +lambda trace breaks it for any lambda > 0."""
    lam, alpha = 0.9, 0.1
    rng = np.random.default_rng(0)
    grads = [rng.standard_normal(5) for _ in range(4)]
    deltas = [0.3, -0.2, 0.5, -0.1]
    signs = [1, -1, 1, -1]  # mover alternates every ply

    # Textbook TD(lambda) on U: grad U = sign * grad V, delta^U = sign * delta.
    trace_u = np.zeros(5)
    weights_u = np.zeros(5)
    for grad, delta, sign in zip(grads, deltas, signs):
        trace_u = lam * trace_u + sign * grad
        weights_u += alpha * (sign * delta) * trace_u

    # Our canonical-perspective form, with the alternating trace.
    trace_v = np.zeros(5)
    weights_v = np.zeros(5)
    for grad, delta in zip(grads, deltas):
        trace_v = -lam * trace_v + grad
        weights_v += alpha * delta * trace_v

    assert np.allclose(weights_u, weights_v)


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


def test_alpha_is_constant_when_no_final_is_set():
    config = TrainConfig(games=1000, alpha=0.1, alpha_final=None)
    assert alpha_for_game(config, 0) == 0.1
    assert alpha_for_game(config, 999) == 0.1


def test_alpha_decays_linearly_then_holds():
    config = TrainConfig(games=1000, alpha=0.1, alpha_final=0.01, alpha_decay_games=1000)
    assert alpha_for_game(config, 0) == pytest.approx(0.1)
    assert alpha_for_game(config, 500) == pytest.approx(0.055)
    assert alpha_for_game(config, 1000) == pytest.approx(0.01)
    # Held flat past the horizon rather than extrapolated below alpha_final.
    assert alpha_for_game(config, 5000) == pytest.approx(0.01)


def test_alpha_schedule_is_independent_of_the_games_cap():
    """The decay horizon is absolute, so stopping early or raising --games
    doesn't move the schedule — the flaw that made --resume re-heat alpha."""
    short = TrainConfig(games=1000, alpha=0.1, alpha_final=0.01, alpha_decay_games=10_000)
    long = TrainConfig(games=999_999, alpha=0.1, alpha_final=0.01, alpha_decay_games=10_000)
    assert alpha_for_game(short, 2500) == alpha_for_game(long, 2500)


def test_alpha_decay_horizon_defaults_to_the_games_cap():
    config = TrainConfig(games=1000, alpha=0.1, alpha_final=0.01)
    assert alpha_for_game(config, 1000) == pytest.approx(0.01)


def test_resume_continues_the_alpha_schedule():
    """A resumed run must pick alpha up where the previous one left off."""
    config = TrainConfig(
        games=500, alpha=0.1, alpha_final=0.01, alpha_decay_games=1000, games_done=500
    )
    # First game of the resumed run is game 501 overall, not game 1.
    assert alpha_for_game(config, config.games_done + 1 - 1) == pytest.approx(0.055)


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    path = tmp_path / "td.npz"
    NeuralNet(hidden_size=8, seed=1).save(path)
    NeuralNet(hidden_size=8, seed=2).save(path)  # overwrite an existing checkpoint
    assert path.exists()
    assert list(tmp_path.iterdir()) == [path]  # no leftover .tmp
    assert NeuralNet.load(path).b1.shape == (8,)


def test_keyboard_interrupt_saves_and_exits_cleanly(tmp_path, monkeypatch, capsys):
    """Ctrl+C must be a supported stop, not a crash: the net is saved with
    every game up to the interrupt, and the caller gets the trained net back
    rather than a propagating KeyboardInterrupt."""
    import ai.train_td as train_td

    real_self_play = train_td.self_play_game
    calls = {"n": 0}

    def interrupting_self_play(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] > 5:
            raise KeyboardInterrupt
        return real_self_play(*args, **kwargs)

    monkeypatch.setattr(train_td, "self_play_game", interrupting_self_play)

    out = tmp_path / "td.npz"
    config = TrainConfig(
        games=100_000,
        hidden_size=10,
        seed=1,
        report_every=10**9,
        eval_every=10**9,
        checkpoint_every=10**9,  # nothing written before the interrupt
        out=out,
    )
    net = train_td.train(config)

    assert isinstance(net, NeuralNet)
    assert out.exists(), "interrupt must still write the checkpoint"
    assert NeuralNet.load(out).b1.shape == (10,)
    output = capsys.readouterr().out
    assert "interrupted" in output
    assert "--games-done 6" in output  # tells you how to resume correctly


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

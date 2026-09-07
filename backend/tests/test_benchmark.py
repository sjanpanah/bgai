from ai.benchmark import Competitor, play_game, round_robin


def test_play_game_returns_a_winner_and_multiplier():
    winner, multiplier = play_game("heuristic", "random", seed=0)
    assert winner in (0, 1)
    assert multiplier in (1, 2, 3)


def test_heuristic_beats_random_head_to_head():
    # The AI's real test suite: heuristic must clearly outplay random.
    results = round_robin(["heuristic", "random"], games_per_matchup=10, seed=0)
    heuristic_wins = sum(results["heuristic"].values())
    random_wins = sum(results["random"].values())

    assert heuristic_wins > random_wins


def test_expectiminimax_beats_heuristic_head_to_head():
    # M4's real test suite: 1-ply lookahead through the opponent's reply must
    # clearly outplay the plain 1-ply heuristic it searches on top of.
    expectiminimax = Competitor("expectiminimax", {"depth": 1, "candidates": 8})
    results = round_robin([expectiminimax, "heuristic"], games_per_matchup=10, seed=0)
    expectiminimax_wins = sum(results[expectiminimax.label].values())
    heuristic_wins = sum(results["heuristic"].values())

    assert expectiminimax_wins > heuristic_wins


def test_neural_beats_expectiminimax_head_to_head():
    # M5's real test suite: the trained TD net (loaded from the committed
    # ai/weights/td_v1.npz checkpoint via the "neural" registry entry) must
    # clearly outplay expectiminimax. A post-training benchmark measured this
    # at 77.5% over 200 games (95% CI 71.7-83.3%) — 20 games here is just
    # enough to be non-flaky at that true rate without slowing the suite by
    # expectiminimax's ~1.6s/game.
    results = round_robin(["neural", "expectiminimax"], games_per_matchup=20, seed=0)
    neural_wins = sum(results["neural"].values())
    expectiminimax_wins = sum(results["expectiminimax"].values())

    assert neural_wins > expectiminimax_wins

from ai.benchmark import play_game, round_robin


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

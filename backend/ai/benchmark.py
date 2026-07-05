"""Benchmark harness: pit two engines against each other over N games and
report win rates. This is the AI's real test suite — used to justify that a
new engine is actually stronger, not just that it runs.

Drives every move through the stateless `POST /engine/move` endpoint (via an
in-process ASGI test client, so no real network hop) rather than a `/game`
session — the harness owns the `GameState` itself and never touches
`game_id` bookkeeping, per the stateless-endpoint design in CLAUDE.md.

Round-robin over more than two entrants: call `play_game` for every ordered
pair. A competitor here is just an engine id from the registry; once a
parameterized engine (e.g. `expectiminimax` at different search depths)
exists, extend `play_game`/`round_robin` to take `(engine_id, params)` pairs
instead of bare ids.
"""

from __future__ import annotations

import collections
import itertools

from fastapi.testclient import TestClient

from engine.moves import apply_turn
from engine.rules import has_won, win_multiplier
from engine.state import Dice, GameState, Move
from main import app

_client = TestClient(app)


def play_game(
    player0_engine: str, player1_engine: str, seed: int, max_turns: int = 500
) -> tuple[int, int]:
    """Plays one full game, returns (winner, multiplier)."""
    state = GameState.new_game()
    dice_gen = Dice(seed=seed)
    engine_for = {0: player0_engine, 1: player1_engine}

    for _ in range(max_turns):
        player = state.turn
        dice = dice_gen.roll()
        resp = _client.post(
            "/engine/move",
            json={"state": state.to_dict(), "dice": list(dice), "engine": engine_for[player]},
        )
        resp.raise_for_status()
        moves = [Move(m["source"], m["target"]) for m in resp.json()["move"]]

        state = apply_turn(state, player, moves)
        if has_won(state, player):
            return player, win_multiplier(state, player)
        state.turn = 1 - player

    raise RuntimeError(f"game exceeded {max_turns} turns without a winner")


def round_robin(
    competitors: list[str], games_per_matchup: int = 20, seed: int = 0
) -> dict[str, dict[str, int]]:
    """Wins matrix: results[a][b] = games `a` won while facing `b`.

    Each unordered pair plays exactly `games_per_matchup` games total, with
    the player-0 seat alternating each game so neither side is favored by
    the (slight) first-move tempo.
    """
    results = {c: collections.Counter() for c in competitors}
    next_seed = seed

    for a, b in itertools.combinations(competitors, 2):
        for i in range(games_per_matchup):
            player0, player1 = (a, b) if i % 2 == 0 else (b, a)
            winner, _ = play_game(player0, player1, seed=next_seed)
            next_seed += 1
            winning_id = player0 if winner == 0 else player1
            losing_id = player1 if winner == 0 else player0
            results[winning_id][losing_id] += 1

    return {c: dict(counts) for c, counts in results.items()}


def summarize(
    results: dict[str, dict[str, int]], competitors: list[str], games_per_matchup: int
) -> str:
    """A plain-text win-rate table, one row per competitor."""
    lines = []
    for competitor in competitors:
        opponents = [c for c in competitors if c != competitor]
        total_games = len(opponents) * games_per_matchup
        total_wins = sum(results[competitor].values())
        rate = total_wins / total_games if total_games else 0.0
        breakdown = ", ".join(
            f"{opp}: {results[competitor].get(opp, 0)}/{games_per_matchup}" for opp in opponents
        )
        lines.append(f"{competitor}: {rate:.0%} overall ({breakdown})")
    return "\n".join(lines)

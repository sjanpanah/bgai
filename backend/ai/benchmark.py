"""Benchmark harness: pit engines against each other over N games and report
win rates. This is the AI's real test suite — used to justify that a new
engine (or a new set of tuning params) is actually stronger, not just that
it runs.

A competitor is an `(engine_id, params)` pair, built directly here rather
than through `ai/registry.py` — the registry stays a small curated set of
engines a human would want to play; this harness instantiates any params
combination, including ones that never appear in the UI dropdown (e.g.
`heuristic` at several different weight settings, competing against each
other to find the best one).

The harness owns the `GameState` itself and calls `choose_move` directly —
no `/game` session, no per-game bookkeeping — matching the stateless,
serialized-position design `POST /engine/move` is built on, just as a direct
function call instead of a simulated HTTP round trip.
"""

from __future__ import annotations

import collections
import itertools
from dataclasses import dataclass, field
from typing import Callable

from ai.base import Engine
from ai.expectiminimax import ExpectiminimaxEngine
from ai.heuristic import Weights
from ai.heuristic_engine import HeuristicEngine
from ai.random_engine import RandomEngine
from engine.moves import apply_turn, legal_turn_sequences
from engine.rules import has_won, win_multiplier
from engine.state import Dice, GameState

_ENGINE_FACTORIES: dict[str, Callable[..., Engine]] = {
    "random": RandomEngine,
    "heuristic": lambda **params: HeuristicEngine(Weights(**params)),
    "expectiminimax": lambda **params: ExpectiminimaxEngine(**params),
}


@dataclass(frozen=True)
class Competitor:
    """An `(engine_id, params)` pair — one entrant in the round-robin."""

    engine_id: str
    params: dict = field(default_factory=dict)
    label: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            object.__setattr__(self, "label", self._auto_label())

    def _auto_label(self) -> str:
        if not self.params:
            return self.engine_id
        param_str = ",".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.engine_id}[{param_str}]"

    def build(self) -> Engine:
        return _ENGINE_FACTORIES[self.engine_id](**self.params)


def _as_competitor(value: str | Competitor) -> Competitor:
    return value if isinstance(value, Competitor) else Competitor(engine_id=value)


def play_game(
    player0: str | Competitor, player1: str | Competitor, seed: int, max_turns: int = 500
) -> tuple[int, int]:
    """Plays one full game, returns (winner, multiplier)."""
    engines = {0: _as_competitor(player0).build(), 1: _as_competitor(player1).build()}
    state = GameState.new_game()
    dice_gen = Dice(seed=seed)

    for _ in range(max_turns):
        player = state.turn
        dice = dice_gen.roll()
        sequences = legal_turn_sequences(state, player, dice)
        moves = engines[player].choose_move(state, dice, sequences)

        state = apply_turn(state, player, moves)
        if has_won(state, player):
            return player, win_multiplier(state, player)
        state.turn = 1 - player

    raise RuntimeError(f"game exceeded {max_turns} turns without a winner")


def round_robin(
    competitors: list[str | Competitor], games_per_matchup: int = 20, seed: int = 0
) -> dict[str, dict[str, int]]:
    """Wins matrix: results[a.label][b.label] = games `a` won while facing `b`.

    Each unordered pair plays exactly `games_per_matchup` games total, with
    the player-0 seat alternating each game so neither side is favored by
    the (slight) first-move tempo.
    """
    normalized = [_as_competitor(c) for c in competitors]
    results = {c.label: collections.Counter() for c in normalized}
    next_seed = seed

    for a, b in itertools.combinations(normalized, 2):
        for i in range(games_per_matchup):
            player0, player1 = (a, b) if i % 2 == 0 else (b, a)
            winner, _ = play_game(player0, player1, seed=next_seed)
            next_seed += 1
            winning_id = player0.label if winner == 0 else player1.label
            losing_id = player1.label if winner == 0 else player0.label
            results[winning_id][losing_id] += 1

    return {c: dict(counts) for c, counts in results.items()}


def summarize(
    results: dict[str, dict[str, int]],
    competitors: list[str | Competitor],
    games_per_matchup: int,
) -> str:
    """A plain-text win-rate table, one row per competitor."""
    labels = [_as_competitor(c).label for c in competitors]
    lines = []
    for competitor in labels:
        opponents = [c for c in labels if c != competitor]
        total_games = len(opponents) * games_per_matchup
        total_wins = sum(results[competitor].values())
        rate = total_wins / total_games if total_games else 0.0
        breakdown = ", ".join(
            f"{opp}: {results[competitor].get(opp, 0)}/{games_per_matchup}" for opp in opponents
        )
        lines.append(f"{competitor}: {rate:.0%} overall ({breakdown})")
    return "\n".join(lines)

"""Expectiminimax engine: search over dice chance nodes instead of stopping
at 1-ply like `heuristic`. `depth` counts dice-rolls-worth of lookahead past
the immediate move — depth 0 reduces to plain greedy 1-ply (same choice as
`HeuristicEngine`), depth 1 picks the move that scores best after averaging
over the opponent's best reply to all 21 possible rolls, depth 2 adds the
player's own best reply after that, and so on.

Full expansion (candidates x 21 rolls, every ply) explodes fast, so each
chance/decision node prunes to the top `candidates` legal sequences by
static 1-ply eval before recursing — the standard selective-search trick;
see the Hakim (2025) reference in CLAUDE.md for why plain alpha-beta over
chance nodes isn't sound without a bounded eval range.

The leaf evaluator is pluggable: `evaluate()` (fast, static) by default, or
Monte Carlo rollout equity (`ai/rollout.py`) when `num_rollouts > 0` — ground
-truth game outcomes in place of a hand-tuned formula, at far higher cost.
"""

from __future__ import annotations

from ai.heuristic import DEFAULT_WEIGHTS, Weights, evaluate
from ai.rollout import rollout_equity
from engine.moves import apply_turn, legal_turn_sequences
from engine.rules import has_won, win_multiplier
from engine.state import GameState, Move

# All 21 distinct dice rolls, weighted by probability out of 36.
_DICE_ROLLS: list[tuple[tuple[int, int], float]] = [
    ((d1, d2), (1 if d1 == d2 else 2) / 36) for d1 in range(1, 7) for d2 in range(d1, 7)
]

# Dominates any static/rollout leaf value so a forced win/loss always wins the
# max/min comparison, regardless of the leaf evaluator's scale.
_TERMINAL = 10_000.0


def _top_candidate_sequences(
    state: GameState, actor: int, sequences: list[list[Move]], weights: Weights, limit: int
) -> list[list[Move]]:
    if len(sequences) <= limit:
        return sequences
    return sorted(
        sequences,
        key=lambda seq: evaluate(apply_turn(state, actor, seq), actor, weights),
        reverse=True,
    )[:limit]


def _candidate_value(
    state: GameState,
    actor: int,
    seq: list[Move],
    player: int,
    depth: int,
    weights: Weights,
    candidates: int,
    leaf_fn,
) -> float:
    resulting = apply_turn(state, actor, seq)
    if resulting is state:  # forced dance: apply_turn hands back the same object
        resulting = resulting.copy()
    if has_won(resulting, actor):
        value = _TERMINAL * win_multiplier(resulting, actor)
        return value if actor == player else -value
    if depth == 0:
        return leaf_fn(resulting)
    resulting.turn = 1 - actor
    return _expected_value(resulting, player, depth, weights, candidates, leaf_fn)


def _expected_value(
    state: GameState, player: int, depth: int, weights: Weights, candidates: int, leaf_fn
) -> float:
    """Expected value of `state` for `player`, `depth` chance-node expansions
    deep, assuming both sides play their locally-best pruned candidate."""
    acting = state.turn
    total = 0.0
    for dice, roll_weight in _DICE_ROLLS:
        sequences = legal_turn_sequences(state, acting, dice)
        ranked = _top_candidate_sequences(state, acting, sequences, weights, candidates)
        values = [
            _candidate_value(state, acting, seq, player, depth - 1, weights, candidates, leaf_fn)
            for seq in ranked
        ]
        best = max(values) if acting == player else min(values)
        total += roll_weight * best
    return total


class ExpectiminimaxEngine:
    def __init__(
        self,
        depth: int = 1,
        candidates: int = 8,
        weights: Weights = DEFAULT_WEIGHTS,
        num_rollouts: int = 0,
        rollout_seed: int = 0,
    ) -> None:
        self.depth = depth
        self.candidates = candidates
        self.weights = weights
        self.num_rollouts = num_rollouts
        self.rollout_seed = rollout_seed

    def _make_leaf(self, player: int):
        if self.num_rollouts > 0:
            return lambda state: rollout_equity(
                state, player, self.num_rollouts, seed=self.rollout_seed
            )
        weights = self.weights
        return lambda state: evaluate(state, player, weights)

    def choose_move(
        self,
        state: GameState,
        dice: tuple[int, int],
        legal_sequences: list[list[Move]],
    ) -> list[Move]:
        player = state.turn
        leaf_fn = self._make_leaf(player)
        return max(
            legal_sequences,
            key=lambda seq: _candidate_value(
                state, player, seq, player, self.depth, self.weights, self.candidates, leaf_fn
            ),
        )

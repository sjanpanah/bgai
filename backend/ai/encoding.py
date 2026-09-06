"""Standard TD-Gammon 198-feature encoding, canonicalized to the side-to-move.

Layout (198 = 96 + 96 + 2 + 2 + 2): for each of the two players, 24 points x 4
units (`n>=1, n>=2, n>=3, (n-3)/2 if n>3 else 0` for `n` checkers on that point),
then 2 bar units, 2 off units, 2 one-hot turn units — always in `[player 0,
player 1]` order.

`encode()` is the raw, literal encoding (whatever `state.turn` says). Training
and play always go through `encode_canonical()` instead: it mirrors the board
(`mirror()`) whenever Player 1 is on roll, so the vector a net sees always has
"player 0" as the side to move. This lets a small net learn one orientation
instead of two, at the cost of an extra state transform before every forward
pass — the net itself never needs to know which physical seat is acting.
"""

from __future__ import annotations

import numpy as np

from engine.state import PLAYER_0, PLAYER_1, GameState

FEATURE_SIZE = 198
_UNITS_PER_POINT = 4
_POINTS = 24
_BOARD_FEATURES = _UNITS_PER_POINT * _POINTS * 2  # 192


def _point_units(counts: np.ndarray) -> np.ndarray:
    """(24,) non-negative checker counts -> (24, 4) unit block, per the
    TD-Gammon scheme. Vectorized because this is the training hot path —
    it runs once per player per candidate move, ~20 candidates per ply."""
    units = np.empty((_POINTS, _UNITS_PER_POINT), dtype=np.float64)
    units[:, 0] = counts >= 1
    units[:, 1] = counts >= 2
    units[:, 2] = counts >= 3
    units[:, 3] = np.where(counts > 3, (counts - 3) / 2, 0.0)
    return units


def encode(state: GameState) -> np.ndarray:
    """Raw 198-vector: player 0's checkers/bar/off first, then player 1's,
    then a one-hot for `state.turn` as literally recorded — no mirroring."""
    features = np.empty(FEATURE_SIZE, dtype=np.float64)

    board = np.asarray(state.board)
    half = _POINTS * _UNITS_PER_POINT
    features[:half] = _point_units(np.clip(board, 0, None)).ravel()
    features[half:_BOARD_FEATURES] = _point_units(np.clip(-board, 0, None)).ravel()

    idx = _BOARD_FEATURES
    features[idx] = state.bar[PLAYER_0] / 2
    features[idx + 1] = state.bar[PLAYER_1] / 2
    features[idx + 2] = state.off[PLAYER_0] / 15
    features[idx + 3] = state.off[PLAYER_1] / 15
    features[idx + 4] = 1.0 if state.turn == PLAYER_0 else 0.0
    features[idx + 5] = 1.0 if state.turn == PLAYER_1 else 0.0
    return features


def mirror(state: GameState) -> GameState:
    """Swap player identities entirely: point `i` <-> point `23-i` with sign
    flipped, bar/off swapped, turn flipped. An involution — `mirror(mirror(s))`
    reproduces `s`. Turns "player 1 to move" into an equivalent "player 0 to
    move" position (player 1's forward direction, increasing index bearing
    off past 23, maps onto player 0's, decreasing index bearing off past 0)."""
    board = [-state.board[_POINTS - 1 - i] for i in range(_POINTS)]
    bar = [state.bar[PLAYER_1], state.bar[PLAYER_0]]
    off = [state.off[PLAYER_1], state.off[PLAYER_0]]
    turn = 1 - state.turn
    return GameState(board=board, bar=bar, off=off, turn=turn)


def encode_canonical(state: GameState) -> np.ndarray:
    """The 198-vector from the perspective of whoever is on roll: player 1's
    turn is mirrored first so the net always sees itself as "player 0 to
    move"."""
    if state.turn == PLAYER_1:
        state = mirror(state)
    return encode(state)

"""Hand-rolled NumPy 1-hidden-layer MLP: 198 inputs, sigmoid hidden layer,
single sigmoid output (`V(s)` = P(side-to-move wins)).

No autograd/optimizer framework — `gradient()` returns the raw per-parameter
gradient of the *output* (not a loss), which is exactly what TD(lambda)'s
eligibility traces need (`e <- lambda*e + grad V(s_t)`); that update doesn't
map cleanly onto a framework built around minimizing a loss, so a plain
forward/backward pair is simpler than fighting one.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ai.encoding import FEATURE_SIZE

DEFAULT_HIDDEN_SIZE = 80


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


class NeuralNet:
    """Params are plain NumPy arrays, not wrapped — `gradient()` and the
    training loop touch `W1`/`b1`/`W2`/`b2` directly."""

    def __init__(
        self,
        input_size: int = FEATURE_SIZE,
        hidden_size: int = DEFAULT_HIDDEN_SIZE,
        seed: int | None = None,
    ) -> None:
        rng = np.random.default_rng(seed)
        scale1 = 1.0 / np.sqrt(input_size)
        scale2 = 1.0 / np.sqrt(hidden_size)
        self.W1 = rng.uniform(-scale1, scale1, size=(input_size, hidden_size))
        self.b1 = np.zeros(hidden_size)
        self.W2 = rng.uniform(-scale2, scale2, size=hidden_size)
        self.b2 = 0.0

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, float]:
        """Returns (hidden activations, output value) — the hidden vector is
        needed by `gradient()`, so callers doing a TD step keep it around
        rather than calling `value()` and recomputing the forward pass."""
        h = _sigmoid(x @ self.W1 + self.b1)
        y = _sigmoid(float(h @ self.W2 + self.b2))
        return h, y

    def value(self, x: np.ndarray) -> float:
        _, y = self.forward(x)
        return y

    def gradient(
        self, x: np.ndarray, h: np.ndarray, y: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """Gradient of the scalar output `y` w.r.t. each parameter, at the `x`
        that produced `(h, y)` via `forward()`. Returns `(dW1, db1, dW2, db2)`."""
        dy = y * (1 - y)
        dW2 = dy * h
        db2 = dy
        dh = dy * self.W2
        dh_pre = dh * h * (1 - h)
        dW1 = np.outer(x, dh_pre)
        db1 = dh_pre
        return dW1, db1, dW2, db2

    def save(self, path: str | Path) -> None:
        """Write the checkpoint atomically: full write to a sibling temp file,
        then `os.replace` (atomic on POSIX). Training rewrites this file every
        few thousand games, so a Ctrl+C landing mid-write would otherwise be
        able to truncate the only copy of the run. With the rename, an
        interrupted save leaves either the previous checkpoint or the new one,
        never a half-written file.

        The temp file is opened as a handle rather than passed by name because
        `np.savez` appends `.npz` to a path argument that lacks it, which would
        rename the file out from under `os.replace`.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "wb") as handle:
            np.savez(handle, W1=self.W1, b1=self.b1, W2=self.W2, b2=np.array([self.b2]))
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str | Path) -> NeuralNet:
        data = np.load(path)
        net = cls.__new__(cls)
        net.W1 = data["W1"]
        net.b1 = data["b1"]
        net.W2 = data["W2"]
        net.b2 = float(data["b2"][0])
        return net

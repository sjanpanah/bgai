"""1-ply greedy engine driven by a learned neural value network.

Architecturally identical to `HeuristicEngine`: greedy over `legal_sequences`,
picking the resulting position with the best value. The only difference is
where the value comes from — `NeuralNet.value()` instead of a hand-tuned
formula. See CLAUDE.md's M5 plan for why this is the whole point: the engine
class is trivial, the real content is the encoding and the training loop that
produces the weights it loads.
"""

from __future__ import annotations

from pathlib import Path

from ai.encoding import encode_canonical
from ai.neural_net import NeuralNet
from engine.moves import apply_turn
from engine.rules import has_won
from engine.state import GameState, Move

# Dominates any value estimate (which lives in [0, 1]) so a move that wins
# outright always wins the max, regardless of the net's output.
_TERMINAL = 10_000.0

DEFAULT_WEIGHTS_PATH = Path(__file__).parent / "weights" / "td_v1.npz"


def _load_default_net() -> NeuralNet:
    if DEFAULT_WEIGHTS_PATH.exists():
        return NeuralNet.load(DEFAULT_WEIGHTS_PATH)
    return NeuralNet()


class NeuralEngine:
    def __init__(
        self, net: NeuralNet | None = None, weights_path: str | Path | None = None
    ) -> None:
        if net is not None:
            self.net = net
        elif weights_path is not None:
            self.net = NeuralNet.load(weights_path)
        else:
            self.net = _load_default_net()

    def choose_move(
        self,
        state: GameState,
        dice: tuple[int, int],
        legal_sequences: list[list[Move]],
    ) -> list[Move]:
        player = state.turn

        def score(sequence: list[Move]) -> float:
            resulting = apply_turn(state, player, sequence)
            if resulting is state:  # forced dance: apply_turn hands back the same object
                resulting = resulting.copy()
            if has_won(resulting, player):
                return _TERMINAL
            # It's the opponent's turn next; V(s) is always "side-to-move
            # wins", so `player`'s win chance here is 1 minus the net's value
            # of the position with the opponent on roll.
            resulting = resulting.copy()
            resulting.turn = 1 - player
            return 1.0 - self.net.value(encode_canonical(resulting))

        return max(legal_sequences, key=score)

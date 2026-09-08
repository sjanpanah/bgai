import type { GameState } from "../types/game";

// Mirrors backend/engine/state.py GameState.pip_count(). Board counts are
// signed: positive entries belong to player 0, negative to player 1.
export function pipCount(state: GameState, player: number): number {
  let total = state.bar[player] * 25;
  state.board.forEach((count, idx) => {
    if (player === 0 && count > 0) total += count * (idx + 1);
    else if (player === 1 && count < 0) total += -count * (24 - idx);
  });
  return total;
}

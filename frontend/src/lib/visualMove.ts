import { BAR, OFF, type GameState, type Move } from "../types/game";

/** Counts of `player`'s checkers resting on `idx` in `state` (board point, BAR, or OFF). */
export function countAt(state: GameState, idx: number, player: number): number {
  if (idx === BAR) return state.bar[player];
  if (idx === OFF) return state.off[player];
  const raw = state.board[idx];
  return player === 0 ? Math.max(raw, 0) : Math.max(-raw, 0);
}

/** Lifts one of `player`'s checkers off `idx`, leaving the rest of the board untouched.
 * Used to render the resting board mid-flight, with the moving checker "picked up". */
export function liftOne(
  state: GameState,
  idx: number,
  player: number,
): GameState {
  if (idx === BAR) {
    const bar: [number, number] = [...state.bar];
    bar[player] -= 1;
    return { ...state, bar };
  }
  const board = [...state.board];
  board[idx] -= player === 0 ? 1 : -1;
  return { ...state, board };
}

/**
 * Applies one move to a display-only copy of state, for animating a multi-move
 * AI turn where the backend only returns the state after the *whole* turn.
 * Approximates hit/bear-off bookkeeping just well enough to look right in
 * flight; the authoritative board from the server always wins once the
 * animation settles, so any drift here is never shown to the user.
 */
export function applyVisualMove(
  state: GameState,
  move: Move,
  player: number,
): GameState {
  const lifted = liftOne(state, move.source, player);
  const board = [...lifted.board];
  const bar: [number, number] = [...lifted.bar];
  const off: [number, number] = [...lifted.off];
  const sign = player === 0 ? 1 : -1;

  if (move.target === OFF) {
    off[player] += 1;
  } else {
    const opponent = 1 - player;
    const isOpposingBlot =
      player === 0 ? board[move.target] === -1 : board[move.target] === 1;
    if (isOpposingBlot) {
      board[move.target] = 0;
      bar[opponent] += 1;
    }
    board[move.target] += sign;
  }

  return { ...state, board, bar, off };
}

/** Checkers accounted for by a position: 30 in a well-formed game. Used as a
 *  rest-state invariant on the animated display, which deliberately drops to 29
 *  mid-hop while one checker is in flight. */
export function checkerTotal(state: GameState): number {
  const onBoard = state.board.reduce((sum, count) => sum + Math.abs(count), 0);
  return onBoard + state.bar[0] + state.bar[1] + state.off[0] + state.off[1];
}

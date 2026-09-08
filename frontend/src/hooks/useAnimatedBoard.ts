import { useEffect, useRef, useState } from "react";
import { slotCenter } from "../lib/boardGeometry";
import { applyVisualMove, countAt, liftOne } from "../lib/visualMove";
import type { GameState, Move } from "../types/game";

/** One turn's worth of moves to animate, ending at the server's authoritative `finalState`. */
export interface TurnAnimation {
  id: number;
  player: number;
  moves: Move[];
  finalState: GameState;
}

export interface Flight {
  player: number;
  x: number;
  y: number;
}

const HOP_DURATION_MS = 350;
const AI_HOP_DURATION_MS = 700;

export function useAnimatedBoard(
  state: GameState | null,
  turn: TurnAnimation | null,
  humanPlayer: number,
) {
  const [displayState, setDisplayState] = useState<GameState | null>(state);
  const [flight, setFlight] = useState<Flight | null>(null);
  const displayRef = useRef<GameState | null>(state);
  const queueRef = useRef<TurnAnimation[]>([]);
  const processingRef = useRef(false);
  const lastIdRef = useRef<number>(-1);

  const setDisplay = (next: GameState) => {
    displayRef.current = next;
    setDisplayState(next);
  };

  // No move to animate (initial load, new game): snap straight to the authoritative state.
  useEffect(() => {
    if (turn) return;
    if (state) setDisplay(state);
    else {
      displayRef.current = null;
      setDisplayState(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, turn]);

  useEffect(() => {
    if (!turn || turn.id === lastIdRef.current) return;
    lastIdRef.current = turn.id;
    queueRef.current.push(turn);
    void processQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turn]);

  async function processQueue() {
    if (processingRef.current) return;
    processingRef.current = true;
    while (queueRef.current.length > 0) {
      const next = queueRef.current.shift()!;
      await animateTurn(next);
    }
    processingRef.current = false;
  }

  async function animateTurn(t: TurnAnimation) {
    let board = displayRef.current ?? t.finalState;
    for (let i = 0; i < t.moves.length; i++) {
      const move = t.moves[i];
      const isLast = i === t.moves.length - 1;
      const after = isLast ? t.finalState : applyVisualMove(board, move, t.player);
      const speedMs = t.player === humanPlayer ? HOP_DURATION_MS : AI_HOP_DURATION_MS;
      await animateHop(t.player, move.source, move.target, board, speedMs);
      setDisplay(after);
      board = after;
    }
    setFlight(null);
  }

  function animateHop(
    player: number,
    source: number,
    target: number,
    boardBeforeHop: GameState,
    speedMs: number,
  ): Promise<void> {
    setDisplay(liftOne(boardBeforeHop, source, player));

    if (speedMs <= 0) {
      setFlight(null);
      return Promise.resolve();
    }

    const start = slotCenter(source, player, countAt(boardBeforeHop, source, player) - 1);
    const end = slotCenter(target, player, countAt(boardBeforeHop, target, player));

    return new Promise((resolve) => {
      const startTime = performance.now();
      function tick(now: number) {
        const t = Math.min(1, (now - startTime) / speedMs);
        setFlight({
          player,
          x: start.x + (end.x - start.x) * t,
          y: start.y + (end.y - start.y) * t,
        });
        if (t < 1) requestAnimationFrame(tick);
        else resolve();
      }
      requestAnimationFrame(tick);
    });
  }

  return { displayState: displayState ?? state, flight };
}

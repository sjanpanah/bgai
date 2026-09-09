import { useEffect, useRef, useState } from "react";
import { slotCenter } from "../lib/boardGeometry";
import {
  applyVisualMove,
  checkerTotal,
  countAt,
  liftOne,
} from "../lib/visualMove";
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
// A hop resolves from inside requestAnimationFrame, which a browser simply does
// not run in a hidden tab (and may skip in other conditions). Without a ceiling
// the promise never settles, `processQueue`'s loop never exits, `isAnimating`
// stays true forever and every highlight vanishes — a board that looks dead with
// no recovery but a page reload. setTimeout is throttled in hidden tabs but does
// still fire, so it is a real escape hatch rather than a second copy of the bug.
const HOP_TIMEOUT_MARGIN_MS = 2000;
const EXPECTED_CHECKERS = 30;

export function useAnimatedBoard(
  state: GameState | null,
  turn: TurnAnimation | null,
  humanPlayer: number,
  /** Changing this abandons any animation in flight and snaps to `state`. The
   *  New game button resets everything else about a game; without this the
   *  animation hook survives it, so a wedged queue outlived the game that
   *  wedged it and the player's only escape was reloading the page. */
  resetKey?: string | null,
) {
  const [displayState, setDisplayState] = useState<GameState | null>(state);
  const [flight, setFlight] = useState<Flight | null>(null);
  // True from the moment a turn is queued until the whole queue has drained —
  // unlike `flight`, this is set synchronously with the queue push, so callers
  // waiting to react to "animation done" don't get a false "not animating" in
  // the gap before the first rAF tick actually sets a flight position.
  const [isAnimating, setIsAnimating] = useState(false);
  const displayRef = useRef<GameState | null>(state);
  const queueRef = useRef<TurnAnimation[]>([]);
  const processingRef = useRef(false);
  const lastIdRef = useRef<number>(-1);
  // Bumped by every reset. A queue loop captures the generation it started in
  // and stops touching state once it is stale, so an abandoned animation can't
  // write over the new game it was abandoned for.
  const generationRef = useRef(0);
  const stateRef = useRef<GameState | null>(state);
  stateRef.current = state;

  const setDisplay = (next: GameState) => {
    displayRef.current = next;
    setDisplayState(next);
  };

  useEffect(() => {
    generationRef.current += 1;
    queueRef.current = [];
    processingRef.current = false;
    lastIdRef.current = -1;
    setFlight(null);
    setIsAnimating(false);
    if (stateRef.current) setDisplay(stateRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);

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
    setIsAnimating(true);
    void processQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turn]);

  async function processQueue() {
    if (processingRef.current) return;
    processingRef.current = true;
    const generation = generationRef.current;
    try {
      while (queueRef.current.length > 0) {
        if (generationRef.current !== generation) return;
        const next = queueRef.current.shift()!;
        try {
          await animateTurn(next, generation);
        } catch (err) {
          if (generationRef.current !== generation) return;
          // A single turn's animation failing (e.g. a hop that can't resolve
          // a slot position) must not leave the board permanently mid-flight
          // or the queue permanently "processing" -- both would silently
          // block anything gated on isAnimating, such as the next auto-roll,
          // with no way for the player to recover. Snap straight to the
          // authoritative final state and carry on with the rest of the queue.
          console.error("Turn animation failed, snapping to final state", err);
          setDisplay(next.finalState);
          setFlight(null);
        }
      }
    } finally {
      if (generationRef.current === generation) {
        processingRef.current = false;
        setIsAnimating(false);
        // At rest the display must account for every checker again. If a hop was
        // abandoned after its checker was lifted but before it was put back, the
        // board silently renders a position that does not exist and the player
        // plans against it -- so treat a mismatch as corruption and snap.
        const display = displayRef.current;
        if (display && checkerTotal(display) !== EXPECTED_CHECKERS) {
          console.error(
            `Animated board settled with ${checkerTotal(display)} checkers, expected ${EXPECTED_CHECKERS} — snapping to server state`,
          );
          if (stateRef.current) setDisplay(stateRef.current);
          setFlight(null);
        }
      }
    }
  }

  async function animateTurn(t: TurnAnimation, generation: number) {
    let board = displayRef.current ?? t.finalState;
    for (let i = 0; i < t.moves.length; i++) {
      if (generationRef.current !== generation) return;
      const move = t.moves[i];
      const isLast = i === t.moves.length - 1;
      const after = isLast
        ? t.finalState
        : applyVisualMove(board, move, t.player);
      const speedMs =
        t.player === humanPlayer ? HOP_DURATION_MS : AI_HOP_DURATION_MS;
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

    // Nobody is watching a hidden tab, and rAF doesn't run there — so snap
    // instead of animating. Without this a backgrounded game crawls at the
    // timeout's pace (one hop every ~2.4s) rather than playing normally, and
    // the timeout below goes back to being a backstop rather than the path
    // every hop takes.
    if (speedMs <= 0 || document.hidden) {
      setFlight(null);
      return Promise.resolve();
    }

    const start = slotCenter(
      source,
      player,
      countAt(boardBeforeHop, source, player) - 1,
    );
    const end = slotCenter(
      target,
      player,
      countAt(boardBeforeHop, target, player),
    );

    return new Promise((resolve) => {
      const startTime = performance.now();
      let frame = 0;
      let settled = false;

      // Whichever finishes first wins, and the loser is torn down: the caller
      // gets exactly one resolve, and a timed-out hop leaves no rAF chain still
      // writing flight positions into a turn that has already moved on.
      const finish = () => {
        if (settled) return;
        settled = true;
        cancelAnimationFrame(frame);
        clearTimeout(timer);
        resolve();
      };
      const timer = setTimeout(finish, speedMs + HOP_TIMEOUT_MARGIN_MS);

      function tick(now: number) {
        if (settled) return;
        const t = Math.min(1, (now - startTime) / speedMs);
        setFlight({
          player,
          x: start.x + (end.x - start.x) * t,
          y: start.y + (end.y - start.y) * t,
        });
        if (t < 1) frame = requestAnimationFrame(tick);
        else finish();
      }
      frame = requestAnimationFrame(tick);
    });
  }

  return { displayState: displayState ?? state, flight, isAnimating };
}

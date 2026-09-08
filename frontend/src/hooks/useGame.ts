import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../lib/api";
import type { TurnAnimation } from "./useAnimatedBoard";
import { notateTurn } from "../lib/notation";
import type {
  CombinedMove,
  GameOver,
  GameState,
  HistoryEntry,
  Move,
} from "../types/game";

const HUMAN = 0;

async function postJson(url: string, body?: unknown) {
  const res = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// fetch rejects with a TypeError when it can't reach the host at all. That is the
// common failure here rather than an exotic one: the backend sits on a free tier
// that sleeps, so "unreachable" usually means "cold-starting", not "broken".
function describeError(err: unknown): string {
  // Nothing else logs these now that they're caught rather than thrown, and the
  // banner only ever shows a trimmed version — keep the full detail reachable.
  console.error(err);
  if (err instanceof TypeError) {
    return "Can't reach the server — it may be waking up, which takes about 30 seconds.";
  }
  const message = err instanceof Error ? err.message.trim() : "";
  if (!message) return "Something went wrong talking to the server.";
  // postJson rethrows the raw response body, which for a validation error is a
  // JSON blob: readable in the console, unreadable in a one-line banner.
  return message.length > 200 ? `${message.slice(0, 200)}…` : message;
}

export function useGame() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [dice, setDice] = useState<[number, number] | null>(null);
  // Dice not yet spent this turn (four entries for doubles) — lets the UI
  // strike out a die's face once its move has been played.
  const [remainingDice, setRemainingDice] = useState<number[]>([]);
  const [legalMoves, setLegalMoves] = useState<Move[]>([]);
  const [combinedMoves, setCombinedMoves] = useState<CombinedMove[]>([]);
  const [turnMoves, setTurnMoves] = useState<Move[]>([]);
  const [gameOver, setGameOver] = useState<GameOver | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [turnAnimation, setTurnAnimation] = useState<TurnAnimation | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  // Only the very first roll of a game is manual (a deliberate "start playing"
  // click); every roll after that fires on its own once it's the human's turn.
  const [hasRolledOnce, setHasRolledOnce] = useState(false);
  const nextAnimationId = useRef(0);

  // Bumped by every newGame(). Each request captures the epoch it was issued
  // under and drops its result if that no longer matches, so a slow response
  // can't apply the previous game's position to the game now on screen. The
  // aiMoveInFlight guard doesn't cover this: it stops two *concurrent* calls,
  // not one call outliving the game it belonged to.
  const gameEpoch = useRef(0);
  const aiMoveInFlight = useRef(false);

  const clearError = useCallback(() => setError(null), []);

  const newGame = useCallback(async () => {
    const epoch = ++gameEpoch.current;
    // Any AI move still in flight belongs to the old game and is now inert, so
    // the fresh game must not inherit its guard.
    aiMoveInFlight.current = false;
    try {
      const body = await postJson(`${API_BASE_URL}/game/new`);
      if (epoch !== gameEpoch.current) return;
      setGameId(body.game_id);
      setState(body.state);
      setDice(null);
      setLegalMoves([]);
      setCombinedMoves([]);
      setTurnMoves([]);
      setGameOver(null);
      setHistory([]);
      setTurnAnimation(null);
      setError(null);
      setHasRolledOnce(false);
    } catch (err) {
      if (epoch !== gameEpoch.current) return;
      setError(describeError(err));
    }
  }, []);

  // StrictMode double-invokes effects in dev. Without this guard the second
  // invocation POSTs /game/new again and orphans the game the first one created.
  // The guard is on the effect, not on newGame, so the "New game" button still works.
  const didInit = useRef(false);
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    newGame();
  }, [newGame]);

  const roll = useCallback(async () => {
    if (!gameId) return;
    const epoch = gameEpoch.current;
    try {
      const body = await postJson(`${API_BASE_URL}/game/${gameId}/roll`);
      if (epoch !== gameEpoch.current) return;
      setState(body.state);
      setError(null);
      setHasRolledOnce(true);
      if (body.legal_moves.length === 0) {
        // Forced dance: no legal entry/move at all: the turn already passed
        // server-side, so there's nothing to play.
        setDice(null);
        setRemainingDice([]);
        setLegalMoves([]);
        setCombinedMoves([]);
        setHistory((h) => [
          ...h,
          {
            player: HUMAN,
            dice: body.dice,
            notation: notateTurn(HUMAN, body.dice, []),
          },
        ]);
        return;
      }
      setDice(body.dice);
      setRemainingDice(body.remaining_dice ?? []);
      setLegalMoves(body.legal_moves);
      setCombinedMoves(body.combined_moves ?? []);
      setTurnMoves([]);
    } catch (err) {
      if (epoch !== gameEpoch.current) return;
      setError(describeError(err));
    }
  }, [gameId]);

  // Shared tail end of "the human played some moves this turn": records the
  // resulting state/animation/legal options, and closes out the turn's
  // history entry once the server says no dice remain playable. `dice` and
  // `turnMovesSoFar` are passed explicitly rather than read from hook state
  // so a combined two-hop submission (two sequential requests within one
  // handler) can call this once per hop without hitting stale-closure issues.
  function applyMoveResult(
    moves: Move[],
    body: {
      state: GameState;
      legal_moves: Move[];
      combined_moves?: CombinedMove[];
      remaining_dice?: number[];
      game_over?: GameOver | null;
    },
    dice: [number, number],
    turnMovesSoFar: Move[],
  ) {
    const playedThisTurn = [...turnMovesSoFar, ...moves];
    setState(body.state);
    setError(null);
    setTurnAnimation({
      id: nextAnimationId.current++,
      player: HUMAN,
      moves,
      finalState: body.state,
    });
    setLegalMoves(body.legal_moves);
    setCombinedMoves(body.combined_moves ?? []);
    setRemainingDice(body.remaining_dice ?? []);
    if (body.legal_moves.length === 0) {
      setHistory((h) => [
        ...h,
        {
          player: HUMAN,
          dice,
          notation: notateTurn(HUMAN, dice, playedThisTurn),
        },
      ]);
      setDice(null);
      setTurnMoves([]);
    } else {
      setTurnMoves(playedThisTurn);
    }
    if (body.game_over) setGameOver(body.game_over);
  }

  const submitMove = useCallback(
    async (move: Move) => {
      if (!gameId || !dice) return;
      const epoch = gameEpoch.current;
      try {
        const body = await postJson(`${API_BASE_URL}/game/${gameId}/move`, {
          move,
        });
        if (epoch !== gameEpoch.current) return;
        applyMoveResult([move], body, dice, turnMoves);
      } catch (err) {
        if (epoch !== gameEpoch.current) return;
        setError(describeError(err));
      }
    },
    [gameId, dice, turnMoves],
  );

  // One drag onto a combined-only destination plays as two real single-die
  // moves under the hood (the API only ever accepts one move at a time — see
  // POST /game/{id}/move). Both requests are awaited sequentially so the
  // second is submitted against the board state the first actually produced;
  // the result is applied once, at the end, as a single two-hop turn update.
  const submitCombined = useCallback(
    async (first: Move, second: Move) => {
      if (!gameId || !dice) return;
      const epoch = gameEpoch.current;
      try {
        const body1 = await postJson(`${API_BASE_URL}/game/${gameId}/move`, {
          move: first,
        });
        if (epoch !== gameEpoch.current) return;
        const secondStillLegal = (body1.legal_moves as Move[]).some(
          (m) => m.source === second.source && m.target === second.target,
        );
        if (body1.game_over || !secondStillLegal) {
          // Shouldn't happen -- combined_moves was computed from this exact
          // state -- but fall back to landing after just the first hop
          // rather than submitting a move the server won't accept.
          applyMoveResult([first], body1, dice, turnMoves);
          return;
        }
        const body2 = await postJson(`${API_BASE_URL}/game/${gameId}/move`, {
          move: second,
        });
        if (epoch !== gameEpoch.current) return;
        applyMoveResult([first, second], body2, dice, turnMoves);
      } catch (err) {
        if (epoch !== gameEpoch.current) return;
        setError(describeError(err));
      }
    },
    [gameId, dice, turnMoves],
  );

  // The caller is an effect keyed on the selected engine, so switching engines
  // during the AI's turn re-fires it mid-request. Without this guard both
  // requests land and both write state, applying two AI turns to one roll.
  const aiMove = useCallback(
    async (engine: string) => {
      if (!gameId || aiMoveInFlight.current) return;
      aiMoveInFlight.current = true;
      const epoch = gameEpoch.current;
      const opponent = 1 - HUMAN;
      try {
        const body = await postJson(
          `${API_BASE_URL}/game/${gameId}/ai?engine=${engine}`,
        );
        if (epoch !== gameEpoch.current) return;
        setState(body.state);
        setError(null);
        setTurnAnimation({
          id: nextAnimationId.current++,
          player: opponent,
          moves: body.move,
          finalState: body.state,
        });
        setHistory((h) => [
          ...h,
          {
            player: opponent,
            dice: body.dice,
            notation: notateTurn(opponent, body.dice, body.move),
          },
        ]);
        if (body.game_over) setGameOver(body.game_over);
      } catch (err) {
        if (epoch !== gameEpoch.current) return;
        setError(describeError(err));
      } finally {
        // Only release the guard if it's still ours: newGame() already cleared
        // it for the fresh game, and a stale response must not unlock a request
        // the new game currently has in flight.
        if (epoch === gameEpoch.current) aiMoveInFlight.current = false;
      }
    },
    [gameId],
  );

  return {
    gameId,
    state,
    dice,
    remainingDice,
    legalMoves,
    combinedMoves,
    gameOver,
    history,
    turnAnimation,
    error,
    hasRolledOnce,
    clearError,
    newGame,
    roll,
    submitMove,
    submitCombined,
    aiMove,
    human: HUMAN,
  };
}

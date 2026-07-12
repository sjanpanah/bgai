import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../lib/api";
import type { TurnAnimation } from "./useAnimatedBoard";
import { notateTurn } from "../lib/notation";
import type { GameOver, GameState, HistoryEntry, Move } from "../types/game";

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

export function useGame() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [dice, setDice] = useState<[number, number] | null>(null);
  const [legalMoves, setLegalMoves] = useState<Move[]>([]);
  const [turnMoves, setTurnMoves] = useState<Move[]>([]);
  const [gameOver, setGameOver] = useState<GameOver | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [turnAnimation, setTurnAnimation] = useState<TurnAnimation | null>(null);
  const nextAnimationId = useRef(0);

  const newGame = useCallback(async () => {
    const body = await postJson(`${API_BASE_URL}/game/new`);
    setGameId(body.game_id);
    setState(body.state);
    setDice(null);
    setLegalMoves([]);
    setTurnMoves([]);
    setGameOver(null);
    setHistory([]);
    setTurnAnimation(null);
  }, []);

  useEffect(() => {
    newGame();
  }, [newGame]);

  const roll = useCallback(async () => {
    if (!gameId) return;
    const body = await postJson(`${API_BASE_URL}/game/${gameId}/roll`);
    setState(body.state);
    if (body.legal_moves.length === 0) {
      // Forced dance: no legal entry/move at all: the turn already passed
      // server-side, so there's nothing to play.
      setDice(null);
      setLegalMoves([]);
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
    setLegalMoves(body.legal_moves);
    setTurnMoves([]);
  }, [gameId]);

  const submitMove = useCallback(
    async (move: Move) => {
      if (!gameId || !dice) return;
      const body = await postJson(`${API_BASE_URL}/game/${gameId}/move`, { move });
      const playedThisTurn = [...turnMoves, move];
      setState(body.state);
      setTurnAnimation({
        id: nextAnimationId.current++,
        player: HUMAN,
        moves: [move],
        finalState: body.state,
      });
      setLegalMoves(body.legal_moves);
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
    },
    [gameId, dice, turnMoves],
  );

  const aiMove = useCallback(
    async (engine: string) => {
      if (!gameId) return;
      const opponent = 1 - HUMAN;
      const body = await postJson(`${API_BASE_URL}/game/${gameId}/ai?engine=${engine}`);
      setState(body.state);
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
    },
    [gameId],
  );

  return {
    gameId,
    state,
    dice,
    legalMoves,
    gameOver,
    history,
    turnAnimation,
    newGame,
    roll,
    submitMove,
    aiMove,
    human: HUMAN,
  };
}

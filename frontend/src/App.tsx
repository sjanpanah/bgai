import { useEffect, useMemo, useRef, useState } from "react";
import { Board } from "./components/Board";
import { Dice } from "./components/Dice";
import { EngineSelect } from "./components/EngineSelect";
import { GameResult } from "./components/GameResult";
import { MoveHistory } from "./components/MoveHistory";
import { useAnimatedBoard } from "./hooks/useAnimatedBoard";
import { useEngines } from "./hooks/useEngines";
import { useGame } from "./hooks/useGame";
import { useVersion } from "./hooks/useVersion";
import { FRONTEND_COMMIT, FRONTEND_SHORT } from "./lib/version";

const ENGINE_STORAGE_KEY = "bgai.engine";
const DEFAULT_ENGINE = "neural";

// localStorage throws outright in some privacy modes rather than returning null,
// and remembering the opponent is a convenience — never a reason to fail to start.
function readStoredEngine(): string {
  try {
    return localStorage.getItem(ENGINE_STORAGE_KEY) ?? DEFAULT_ENGINE;
  } catch {
    return DEFAULT_ENGINE;
  }
}

function App() {
  const {
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
    human,
  } = useGame();
  const { engines, reloadEngines } = useEngines();
  const backendVersion = useVersion();
  // Only a real mismatch counts: "unknown" on either side means we couldn't
  // read it, not that the deploys disagree.
  const versionMismatch =
    backendVersion !== null &&
    backendVersion.commit !== "unknown" &&
    FRONTEND_COMMIT !== "unknown" &&
    backendVersion.commit !== FRONTEND_COMMIT;
  const [selectedEngine, setSelectedEngine] = useState(readStoredEngine);
  const [selectedSource, setSelectedSource] = useState<number | null>(null);
  // Lets the player uncover the final position to read or screenshot it. Keyed
  // by game id so a new game never inherits the previous game's dismissal.
  const [resultDismissedFor, setResultDismissedFor] = useState<string | null>(
    null,
  );

  // The engine a fresh game would be no different from: whatever was selected
  // when the current game started. Tracked via a ref so the gameId effect below
  // doesn't need selectedEngine in its deps and re-fire on every dropdown change.
  const selectedEngineRef = useRef(selectedEngine);
  useEffect(() => {
    selectedEngineRef.current = selectedEngine;
  }, [selectedEngine]);
  const [gameStartEngine, setGameStartEngine] = useState(selectedEngine);
  useEffect(() => {
    setGameStartEngine(selectedEngineRef.current);
  }, [gameId]);
  const { displayState, flight, isAnimating } = useAnimatedBoard(
    state,
    turnAnimation,
    human,
  );

  useEffect(() => {
    try {
      localStorage.setItem(ENGINE_STORAGE_KEY, selectedEngine);
    } catch {
      // Not worth surfacing: the game plays fine, the choice just won't persist.
    }
  }, [selectedEngine]);

  // A stored id can outlive the engine it names — renamed, dropped, or merely
  // unavailable here because it needs a binary this machine doesn't have (gnubg,
  // wildbg). EngineSelect disables unavailable options, so without this the user
  // is stuck on an opponent they can't play and can't re-pick. Fall back once the
  // real list arrives rather than posting a dead engine on every turn.
  useEffect(() => {
    const usable = engines.some((e) => e.id === selectedEngine && e.available);
    if (engines.length && !usable) setSelectedEngine(DEFAULT_ENGINE);
  }, [engines, selectedEngine]);

  const humansTurn = state?.turn === human;
  const isRolling = dice !== null;
  // A fresh game is identical to the one in progress once the opponent hasn't
  // changed and the first roll hasn't happened yet — offering to reset it then
  // is a no-op that only invites an accidental click.
  const newGameIsNoOp =
    !gameOver && !hasRolledOnce && selectedEngine === gameStartEngine;

  useEffect(() => {
    if (!state || gameOver) return;
    if (state.turn !== human && !isRolling) {
      aiMove(selectedEngine);
    }
  }, [state, gameOver, isRolling, human, aiMove, selectedEngine]);

  // Only the game's very first roll is a deliberate manual click; every roll
  // after that fires on its own as soon as it's the human's turn again.
  useEffect(() => {
    if (!state || gameOver) return;
    if (humansTurn && !isRolling && !isAnimating && hasRolledOnce) {
      roll();
    }
  }, [state, gameOver, humansTurn, isRolling, isAnimating, hasRolledOnce, roll]);

  const selectableSources = useMemo(() => {
    if (!humansTurn || !isRolling || isAnimating) return [];
    return [...new Set(legalMoves.map((m) => m.source))];
  }, [humansTurn, isRolling, isAnimating, legalMoves]);

  const selectableDestinations = useMemo(() => {
    if (selectedSource === null) return [];
    return legalMoves
      .filter((m) => m.source === selectedSource)
      .map((m) => m.target);
  }, [legalMoves, selectedSource]);

  const combinedDestinations = useMemo(() => {
    if (selectedSource === null) return [];
    return combinedMoves
      .filter((c) => c.first.source === selectedSource)
      .map((c) => c.second.target);
  }, [combinedMoves, selectedSource]);

  // Dim, whole-turn preview shown before any source is picked: every
  // destination reachable by *some* checker this turn, direct or combined.
  const previewDirect = useMemo(() => {
    if (!humansTurn || !isRolling || isAnimating || selectedSource !== null) return [];
    return [...new Set(legalMoves.map((m) => m.target))];
  }, [humansTurn, isRolling, isAnimating, selectedSource, legalMoves]);

  const previewCombined = useMemo(() => {
    if (!humansTurn || !isRolling || isAnimating || selectedSource !== null) return [];
    return [...new Set(combinedMoves.map((c) => c.second.target))];
  }, [humansTurn, isRolling, isAnimating, selectedSource, combinedMoves]);

  function handlePointClick(idx: number) {
    if (!humansTurn || !isRolling || isAnimating) return;
    if (selectedSource !== null) {
      const direct = legalMoves.find(
        (m) => m.source === selectedSource && m.target === idx,
      );
      if (direct) {
        submitMove(direct);
        setSelectedSource(null);
        return;
      }
      const combo = combinedMoves.find(
        (c) => c.first.source === selectedSource && c.second.target === idx,
      );
      if (combo) {
        submitCombined(combo.first, combo.second);
        setSelectedSource(null);
        return;
      }
    }
    if (selectableSources.includes(idx)) {
      setSelectedSource(idx);
    } else {
      setSelectedSource(null);
    }
  }

  function handleDragMove(source: number, target: number) {
    if (!humansTurn || !isRolling || isAnimating) return;
    const direct = legalMoves.find(
      (m) => m.source === source && m.target === target,
    );
    if (direct) {
      submitMove(direct);
      setSelectedSource(null);
      return;
    }
    const combo = combinedMoves.find(
      (c) => c.first.source === source && c.second.target === target,
    );
    if (combo) {
      submitCombined(combo.first, combo.second);
      setSelectedSource(null);
    }
  }

  if (!state) {
    return (
      <div className="max-w-4xl mx-auto p-8 flex flex-col items-start gap-3">
        {error ? (
          <>
            <p>{error}</p>
            <button
              className="border border-line rounded px-3 py-1"
              onClick={() => {
                // The engine list failed alongside the game if the backend was
                // down at load, so recover both rather than leaving an empty dropdown.
                reloadEngines();
                newGame();
              }}
            >
              Try again
            </button>
          </>
        ) : (
          <p>Loading...</p>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-4 flex flex-col gap-4">
      {error && (
        <div className="flex items-center justify-between gap-4 border border-danger-line bg-danger-surface text-danger rounded px-3 py-2 text-sm">
          <span>{error}</span>
          <div className="flex items-center gap-2 shrink-0">
            {/* The AI turn is driven by an effect whose deps don't change when the
                request fails, so it never retries itself — offer it explicitly. */}
            {!humansTurn && !gameOver && (
              <button
                className="border border-danger-line rounded px-2 py-0.5"
                onClick={() => aiMove(selectedEngine)}
              >
                Retry
              </button>
            )}
            <button
              className="border border-danger-line rounded px-2 py-0.5"
              onClick={clearError}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Backgammon vs AI</h1>
        <div className="flex items-center gap-4">
          <EngineSelect
            engines={engines}
            value={selectedEngine}
            onChange={setSelectedEngine}
          />
          {!newGameIsNoOp && (
            <button
              className="border border-line rounded px-3 py-1"
              onClick={newGame}
            >
              New game
            </button>
          )}
        </div>
      </div>

      <div className="relative">
        <Board
          state={displayState ?? state}
          selectableSources={selectableSources}
          selectedSource={selectedSource}
          selectableDestinations={selectableDestinations}
          combinedDestinations={combinedDestinations}
          previewDirect={previewDirect}
          previewCombined={previewCombined}
          onPointClick={handlePointClick}
          onSelectSource={setSelectedSource}
          onMove={handleDragMove}
          flight={flight}
        />
        {gameOver && resultDismissedFor !== gameId && (
          <GameResult
            multiplier={gameOver.multiplier}
            humanWon={gameOver.winner === human}
            onNewGame={newGame}
            onDismiss={() => setResultDismissedFor(gameId)}
          />
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Dice dice={dice} remainingDice={remainingDice} />
          {humansTurn && !isRolling && !gameOver && !hasRolledOnce && (
            <button
              className="border border-line rounded px-3 py-1"
              onClick={roll}
            >
              Roll
            </button>
          )}
        </div>
        <p>
          {gameOver
            ? gameOver.winner === human
              ? "You win"
              : "AI wins"
            : humansTurn
              ? isRolling
                ? "Your move"
                : "Your turn — roll the dice"
              : "AI's turn"}
        </p>
      </div>

      <MoveHistory history={history} />

      <footer className="text-xs text-dim flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>Game: {gameId}</span>
        <span>
          ui <code>{FRONTEND_SHORT}</code>
        </span>
        <span>
          api <code>{backendVersion?.short ?? "—"}</code>
        </span>
        {/* Pages and Render deploy separately, so one lagging behind the other
            is the failure this footer exists to catch. */}
        {versionMismatch && (
          <span className="text-danger">
            ui and api are on different commits
          </span>
        )}
      </footer>
    </div>
  );
}

export default App;

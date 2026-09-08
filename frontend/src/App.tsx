import { useEffect, useMemo, useState } from "react";
import { Board } from "./components/Board";
import { Dice } from "./components/Dice";
import { EngineSelect } from "./components/EngineSelect";
import { MoveHistory } from "./components/MoveHistory";
import { useAnimatedBoard } from "./hooks/useAnimatedBoard";
import { useEngines } from "./hooks/useEngines";
import { useGame } from "./hooks/useGame";

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
    legalMoves,
    gameOver,
    history,
    turnAnimation,
    error,
    clearError,
    newGame,
    roll,
    submitMove,
    aiMove,
    human,
  } = useGame();
  const { engines, reloadEngines } = useEngines();
  const [selectedEngine, setSelectedEngine] = useState(readStoredEngine);
  const [selectedSource, setSelectedSource] = useState<number | null>(null);
  const { displayState, flight } = useAnimatedBoard(state, turnAnimation);

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
  const isAnimating = flight !== null;

  useEffect(() => {
    if (!state || gameOver) return;
    if (state.turn !== human && !isRolling) {
      aiMove(selectedEngine);
    }
  }, [state, gameOver, isRolling, human, aiMove, selectedEngine]);

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

  function handlePointClick(idx: number) {
    if (!humansTurn || !isRolling || isAnimating) return;
    if (selectedSource !== null) {
      const match = legalMoves.find(
        (m) => m.source === selectedSource && m.target === idx,
      );
      if (match) {
        submitMove(match);
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
    const match = legalMoves.find(
      (m) => m.source === source && m.target === target,
    );
    if (match) {
      submitMove(match);
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
              className="border border-gray-400 rounded px-3 py-1"
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
        <div className="flex items-center justify-between gap-4 border border-red-400 bg-red-50 text-red-900 rounded px-3 py-2 text-sm">
          <span>{error}</span>
          <div className="flex items-center gap-2 shrink-0">
            {/* The AI turn is driven by an effect whose deps don't change when the
                request fails, so it never retries itself — offer it explicitly. */}
            {!humansTurn && !gameOver && (
              <button
                className="border border-red-400 rounded px-2 py-0.5"
                onClick={() => aiMove(selectedEngine)}
              >
                Retry
              </button>
            )}
            <button
              className="border border-red-400 rounded px-2 py-0.5"
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
          <button
            className="border border-gray-400 rounded px-3 py-1"
            onClick={newGame}
          >
            New game
          </button>
        </div>
      </div>

      <Board
        state={displayState ?? state}
        selectableSources={selectableSources}
        selectedSource={selectedSource}
        selectableDestinations={selectableDestinations}
        onPointClick={handlePointClick}
        onSelectSource={setSelectedSource}
        onMove={handleDragMove}
        flight={flight}
      />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Dice dice={dice} />
          {humansTurn && !isRolling && !gameOver && (
            <button
              className="border border-gray-400 rounded px-3 py-1"
              onClick={roll}
            >
              Roll
            </button>
          )}
        </div>
        <p>
          {gameOver
            ? `Game over — player ${gameOver.winner === human ? "you" : "AI"} wins (x${gameOver.multiplier})`
            : humansTurn
              ? isRolling
                ? "Your move"
                : "Your turn — roll the dice"
              : "AI's turn"}
        </p>
      </div>

      <MoveHistory history={history} />
      <p className="text-xs text-gray-400">Game: {gameId}</p>
    </div>
  );
}

export default App;

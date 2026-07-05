import { useEffect, useMemo, useState } from "react";
import { Board } from "./components/Board";
import { Dice } from "./components/Dice";
import { EngineSelect } from "./components/EngineSelect";
import { MoveHistory } from "./components/MoveHistory";
import { useEngines } from "./hooks/useEngines";
import { useGame } from "./hooks/useGame";

function App() {
  const {
    gameId,
    state,
    dice,
    legalMoves,
    gameOver,
    history,
    newGame,
    roll,
    submitMove,
    aiMove,
    human,
  } = useGame();
  const engines = useEngines();
  const [selectedEngine, setSelectedEngine] = useState("random");
  const [selectedSource, setSelectedSource] = useState<number | null>(null);

  const humansTurn = state?.turn === human;
  const isRolling = dice !== null;

  useEffect(() => {
    if (!state || gameOver) return;
    if (state.turn !== human && !isRolling) {
      aiMove(selectedEngine);
    }
  }, [state, gameOver, isRolling, human, aiMove, selectedEngine]);

  const selectableSources = useMemo(() => {
    if (!humansTurn || !isRolling) return [];
    return [...new Set(legalMoves.map((m) => m.source))];
  }, [humansTurn, isRolling, legalMoves]);

  const selectableDestinations = useMemo(() => {
    if (selectedSource === null) return [];
    return legalMoves
      .filter((m) => m.source === selectedSource)
      .map((m) => m.target);
  }, [legalMoves, selectedSource]);

  function handlePointClick(idx: number) {
    if (!humansTurn || !isRolling) return;
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

  if (!state) return <p className="p-8">Loading...</p>;

  return (
    <div className="max-w-4xl mx-auto p-4 flex flex-col gap-4">
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
        state={state}
        selectableSources={selectableSources}
        selectedSource={selectedSource}
        selectableDestinations={selectableDestinations}
        onPointClick={handlePointClick}
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

import { useEffect, useMemo, useState } from "react";
import { Board } from "./components/Board";
import { Dice } from "./components/Dice";
import { EngineSelect } from "./components/EngineSelect";
import { MoveHistory } from "./components/MoveHistory";
import { useAnimatedBoard } from "./hooks/useAnimatedBoard";
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
    turnAnimation,
    newGame,
    roll,
    submitMove,
    aiMove,
    human,
  } = useGame();
  const engines = useEngines();
  const [selectedEngine, setSelectedEngine] = useState("random");
  const [selectedSource, setSelectedSource] = useState<number | null>(null);
  const { displayState, flight } = useAnimatedBoard(state, turnAnimation);

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
        state={displayState ?? state}
        selectableSources={selectableSources}
        selectedSource={selectedSource}
        selectableDestinations={selectableDestinations}
        onPointClick={handlePointClick}
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

import { DieFace } from "./Dice";
import type { HistoryEntry } from "../types/game";

interface MoveHistoryProps {
  history: HistoryEntry[];
}

// `notation` is "31: 8/5 6/5" — the roll is redundant once dice icons are
// shown alongside it, so only the move steps after the leading "roll: " survive.
function stepsOnly(notation: string): string {
  const sep = notation.indexOf(": ");
  return sep === -1 ? notation : notation.slice(sep + 2);
}

export function MoveHistory({ history }: MoveHistoryProps) {
  return (
    <div className="border border-line rounded p-2 max-h-48 overflow-y-auto overflow-x-auto text-sm font-mono">
      {history.length === 0 && <p className="text-dim">No moves yet.</p>}
      {[...history].reverse().map((entry, i) => {
        const turnNo = history.length - i;
        const dice =
          entry.dice[0] === entry.dice[1]
            ? Array(4).fill(entry.dice[0])
            : entry.dice;
        return (
          <div
            key={turnNo}
            className="flex items-center gap-2 py-1 border-b border-line last:border-b-0"
          >
            <span className="w-6 text-right text-dim shrink-0">{turnNo}</span>
            <span
              className={`w-7 shrink-0 font-medium ${
                entry.player === 0 ? "text-[#4ade80]" : "text-[#60a5fa]"
              }`}
            >
              {entry.player === 0 ? "You" : "AI"}
            </span>
            <span className="flex gap-1 shrink-0">
              {dice.map((v, j) => (
                <DieFace key={j} value={v} size={16} />
              ))}
            </span>
            <span className="whitespace-nowrap">
              {stepsOnly(entry.notation)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

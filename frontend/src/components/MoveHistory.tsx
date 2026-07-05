import type { HistoryEntry } from "../types/game";

interface MoveHistoryProps {
  history: HistoryEntry[];
}

export function MoveHistory({ history }: MoveHistoryProps) {
  return (
    <div className="border border-gray-300 rounded p-2 h-48 overflow-y-auto text-sm font-mono">
      {history.length === 0 && <p className="text-gray-400">No moves yet.</p>}
      {history.map((entry, i) => (
        <div key={i}>
          {entry.player === 0 ? "You" : "AI"}: {entry.notation}
        </div>
      ))}
    </div>
  );
}

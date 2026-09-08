import type { EngineInfo } from "../types/game";

interface EngineSelectProps {
  engines: EngineInfo[];
  value: string;
  onChange: (id: string) => void;
}

export function EngineSelect({ engines, value, onChange }: EngineSelectProps) {
  return (
    <label className="flex items-center gap-2 text-sm">
      Opponent:
      <select
        className="border border-line rounded px-2 py-1"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {engines.map((e) => (
          <option key={e.id} value={e.id} disabled={!e.available}>
            {e.label}
          </option>
        ))}
      </select>
    </label>
  );
}

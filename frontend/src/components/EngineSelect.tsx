import type { EngineInfo } from "../types/game";

interface EngineSelectProps {
  engines: EngineInfo[];
  value: string;
  onChange: (id: string) => void;
}

export function EngineSelect({ engines, value, onChange }: EngineSelectProps) {
  return (
    // `min-w-0` is what actually lets this shrink: a flex item defaults to
    // min-width:auto, so the select's intrinsic width -- set by its longest
    // option, "Very Hard (Neural Network)" at 217px -- was a hard floor that
    // pushed the whole header past a phone viewport.
    <label className="flex items-center gap-2 text-sm min-w-0">
      Opponent:
      <select
        className="border border-line rounded px-2 py-1 min-w-0 flex-1 sm:flex-none"
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

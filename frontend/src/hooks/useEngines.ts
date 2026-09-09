import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../lib/api";
import type { EngineInfo } from "../types/game";

export function useEngines() {
  const [engines, setEngines] = useState<EngineInfo[]>([]);

  // A failure here isn't worth blocking the game over — the app falls back to
  // the default engine — but it must not reject unhandled, and the list has to
  // be re-fetchable so a backend that was merely cold-starting still populates
  // the dropdown once the retry succeeds.
  const loadEngines = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/engines`);
      if (!res.ok) return;
      setEngines(await res.json());
    } catch {
      // Left empty: EngineSelect renders the current value until this succeeds.
    }
  }, []);

  // Same guard `useGame` has on its init effect: StrictMode double-invokes
  // effects in dev, and every duplicate request costs wall-clock time against a
  // free-tier backend that may be cold-starting. `reloadEngines` is unaffected.
  const didInit = useRef(false);
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    loadEngines();
  }, [loadEngines]);

  return { engines, reloadEngines: loadEngines };
}

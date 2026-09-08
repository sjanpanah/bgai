import { useCallback, useEffect, useState } from "react";
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

  useEffect(() => {
    loadEngines();
  }, [loadEngines]);

  return { engines, reloadEngines: loadEngines };
}

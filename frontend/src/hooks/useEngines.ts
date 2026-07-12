import { useEffect, useState } from "react";
import { API_BASE_URL } from "../lib/api";
import type { EngineInfo } from "../types/game";

export function useEngines() {
  const [engines, setEngines] = useState<EngineInfo[]>([]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/engines`)
      .then((res) => res.json())
      .then(setEngines);
  }, []);

  return engines;
}

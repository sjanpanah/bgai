import { useEffect, useState } from "react";
import type { EngineInfo } from "../types/game";

export function useEngines() {
  const [engines, setEngines] = useState<EngineInfo[]>([]);

  useEffect(() => {
    fetch("/engines")
      .then((res) => res.json())
      .then(setEngines);
  }, []);

  return engines;
}

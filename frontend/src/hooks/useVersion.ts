import { useEffect, useState } from "react";
import { API_BASE_URL } from "../lib/api";

export interface BackendVersion {
  commit: string;
  short: string;
  source: string;
}

/** Which commit the API is running, or null while unknown. */
export function useVersion(): BackendVersion | null {
  const [backend, setBackend] = useState<BackendVersion | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/version`);
        if (!res.ok) return;
        const body = await res.json();
        if (!cancelled) setBackend(body);
      } catch {
        // Same stance as useEngines: this line is diagnostic, so failing to
        // read it must never break the game or surface an error to the player.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return backend;
}

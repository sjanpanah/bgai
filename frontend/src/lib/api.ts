// Empty by default so relative fetches ("/game/...") keep working against the
// Vite dev proxy; production builds set VITE_API_BASE_URL to the deployed backend.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

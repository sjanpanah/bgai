// Mirrors backend/models/game.py and backend/engine/state.py sentinels.
export const BAR = -1;
export const OFF = 24;

export interface Move {
  source: number;
  target: number;
}

export interface GameState {
  board: number[];
  bar: [number, number];
  off: [number, number];
  turn: number;
}

export interface GameOver {
  winner: number;
  multiplier: number;
}

export interface EngineInfo {
  id: string;
  label: string;
  available: boolean;
}

export interface HistoryEntry {
  player: number;
  dice: [number, number];
  notation: string;
}

import { BAR, OFF, type Move } from "../types/game";

// Point number in `player`'s own frame, matching engine.rules.distance_to_off:
// each player counts their own 24-point down to their 1-point (bear-off edge).
function pointLabel(player: number, idx: number): string {
  if (idx === BAR) return "bar";
  if (idx === OFF) return "off";
  return String(player === 0 ? idx + 1 : 24 - idx);
}

export function notateTurn(
  player: number,
  dice: [number, number],
  moves: Move[],
): string {
  const roll = `${dice[0]}${dice[1]}`;
  if (moves.length === 0) return `${roll}: (no move)`;
  const steps = moves.map(
    (m) => `${pointLabel(player, m.source)}/${pointLabel(player, m.target)}`,
  );
  return `${roll}: ${steps.join(" ")}`;
}

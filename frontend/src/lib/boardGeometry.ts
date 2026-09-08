import { BAR, OFF } from "../types/game";

export const BOARD_LEFT = 40;
export const BOARD_RIGHT = 860;
export const BOARD_TOP = 40;
export const BOARD_BOTTOM = 560;
export const BAR_WIDTH = 50;
export const BAR_LEFT = (BOARD_LEFT + BOARD_RIGHT) / 2 - BAR_WIDTH / 2;
export const BAR_RIGHT = BAR_LEFT + BAR_WIDTH;
export const QUADRANT_WIDTH = BAR_LEFT - BOARD_LEFT;
export const POINT_WIDTH = QUADRANT_WIDTH / 6;
export const TRIANGLE_HEIGHT = 230;
export const MID_TOP = BOARD_TOP + TRIANGLE_HEIGHT;
export const MID_BOTTOM = BOARD_BOTTOM - TRIANGLE_HEIGHT;
export const OFF_LEFT = BOARD_RIGHT + 20;
export const OFF_RIGHT = OFF_LEFT + 40;
export const CHECKER_R = 16;
// Just outside the off tray's right edge, on the page ground rather than the
// tray's wood, mirroring how the point numbers sit outside the board rect.
export const PIP_LABEL_X = OFF_RIGHT + 14;
export const VIEWBOX_RIGHT = OFF_RIGHT + 60;

export function isTop(idx: number): boolean {
  return idx >= 12;
}

export function pointX(idx: number): number {
  if (idx <= 5) return BAR_RIGHT + (5 - idx) * POINT_WIDTH + POINT_WIDTH / 2;
  if (idx <= 11) return BOARD_LEFT + (11 - idx) * POINT_WIDTH + POINT_WIDTH / 2;
  if (idx <= 17) return BOARD_LEFT + (idx - 12) * POINT_WIDTH + POINT_WIDTH / 2;
  return BAR_RIGHT + (idx - 18) * POINT_WIDTH + POINT_WIDTH / 2;
}

export function trianglePath(idx: number): string {
  const x = pointX(idx);
  const top = isTop(idx);
  const baseY = top ? BOARD_TOP : BOARD_BOTTOM;
  const apexY = top ? MID_TOP : MID_BOTTOM;
  const half = POINT_WIDTH / 2 - 2;
  return `M ${x - half} ${baseY} L ${x + half} ${baseY} L ${x} ${apexY} Z`;
}

export function checkerCenters(idx: number, count: number): number[] {
  const top = isTop(idx);
  const baseY = top ? BOARD_TOP : BOARD_BOTTOM;
  const dir = top ? 1 : -1;
  const start = baseY + dir * (CHECKER_R + 4);
  const available = TRIANGLE_HEIGHT - CHECKER_R * 2;
  const spacing =
    count > 1 ? Math.min(CHECKER_R * 2, available / (count - 1)) : 0;
  return Array.from({ length: count }, (_, i) => start + dir * spacing * i);
}

/** Center point of the next free slot for `player` at `idx` (board point, BAR, or OFF),
 * given `countBefore` checkers already resting there. Used to aim in-flight animations. */
export function slotCenter(
  idx: number,
  player: number,
  countBefore: number,
): { x: number; y: number } {
  if (idx === BAR) {
    const x = (BAR_LEFT + BAR_RIGHT) / 2;
    return player === 0
      ? { x, y: BOARD_BOTTOM - CHECKER_R - 4 - countBefore * (CHECKER_R * 2) }
      : { x, y: BOARD_TOP + CHECKER_R + 4 + countBefore * (CHECKER_R * 2) };
  }
  if (idx === OFF) {
    const x = (OFF_LEFT + OFF_RIGHT) / 2;
    return { x, y: player === 1 ? BOARD_TOP + 20 : BOARD_BOTTOM - 10 };
  }
  const centers = checkerCenters(idx, countBefore + 1);
  return { x: pointX(idx), y: centers[countBefore] };
}

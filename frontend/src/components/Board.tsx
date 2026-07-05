import { BAR, OFF, type GameState } from "../types/game";

const BOARD_LEFT = 40;
const BOARD_RIGHT = 860;
const BOARD_TOP = 40;
const BOARD_BOTTOM = 560;
const BAR_WIDTH = 50;
const BAR_LEFT = (BOARD_LEFT + BOARD_RIGHT) / 2 - BAR_WIDTH / 2;
const BAR_RIGHT = BAR_LEFT + BAR_WIDTH;
const QUADRANT_WIDTH = BAR_LEFT - BOARD_LEFT;
const POINT_WIDTH = QUADRANT_WIDTH / 6;
const TRIANGLE_HEIGHT = 230;
const MID_TOP = BOARD_TOP + TRIANGLE_HEIGHT;
const MID_BOTTOM = BOARD_BOTTOM - TRIANGLE_HEIGHT;
const OFF_LEFT = BOARD_RIGHT + 20;
const OFF_RIGHT = OFF_LEFT + 40;
const CHECKER_R = 16;

const LIGHT_PLAYER = "#f4f1ea";
const DARK_PLAYER = "#3a3a3a";
const LIGHT_TRIANGLE = "#c9a876";
const DARK_TRIANGLE = "#8a6642";

function isTop(idx: number): boolean {
  return idx >= 12;
}

function pointX(idx: number): number {
  if (idx <= 5) return BAR_RIGHT + (5 - idx) * POINT_WIDTH + POINT_WIDTH / 2;
  if (idx <= 11) return BOARD_LEFT + (11 - idx) * POINT_WIDTH + POINT_WIDTH / 2;
  if (idx <= 17) return BOARD_LEFT + (idx - 12) * POINT_WIDTH + POINT_WIDTH / 2;
  return BAR_RIGHT + (idx - 18) * POINT_WIDTH + POINT_WIDTH / 2;
}

function trianglePath(idx: number): string {
  const x = pointX(idx);
  const top = isTop(idx);
  const baseY = top ? BOARD_TOP : BOARD_BOTTOM;
  const apexY = top ? MID_TOP : MID_BOTTOM;
  const half = POINT_WIDTH / 2 - 2;
  return `M ${x - half} ${baseY} L ${x + half} ${baseY} L ${x} ${apexY} Z`;
}

function checkerCenters(idx: number, count: number): number[] {
  const top = isTop(idx);
  const baseY = top ? BOARD_TOP : BOARD_BOTTOM;
  const dir = top ? 1 : -1;
  const start = baseY + dir * (CHECKER_R + 4);
  const available = TRIANGLE_HEIGHT - CHECKER_R * 2;
  const spacing =
    count > 1 ? Math.min(CHECKER_R * 2, available / (count - 1)) : 0;
  return Array.from({ length: count }, (_, i) => start + dir * spacing * i);
}

interface BoardProps {
  state: GameState;
  selectableSources: number[];
  selectedSource: number | null;
  selectableDestinations: number[];
  onPointClick: (idx: number) => void;
}

export function Board({
  state,
  selectableSources,
  selectedSource,
  selectableDestinations,
  onPointClick,
}: BoardProps) {
  const highlightFor = (idx: number) => {
    if (idx === selectedSource) return "#facc15";
    if (selectableSources.includes(idx)) return "#4ade80";
    if (selectableDestinations.includes(idx)) return "#60a5fa";
    return "none";
  };

  return (
    <svg viewBox="0 0 920 600" className="w-full max-w-4xl mx-auto select-none">
      <rect
        x={BOARD_LEFT}
        y={BOARD_TOP}
        width={BOARD_RIGHT - BOARD_LEFT}
        height={BOARD_BOTTOM - BOARD_TOP}
        fill="#6b4423"
      />
      <rect
        x={BAR_LEFT}
        y={BOARD_TOP}
        width={BAR_WIDTH}
        height={BOARD_BOTTOM - BOARD_TOP}
        fill="#4a2f18"
      />
      <rect
        x={OFF_LEFT}
        y={BOARD_TOP}
        width={OFF_RIGHT - OFF_LEFT}
        height={BOARD_BOTTOM - BOARD_TOP}
        fill="#4a2f18"
      />

      {Array.from({ length: 24 }, (_, idx) => (
        <g
          key={idx}
          onClick={() => onPointClick(idx)}
          style={{ cursor: "pointer" }}
        >
          <path
            d={trianglePath(idx)}
            fill={idx % 2 === 0 ? LIGHT_TRIANGLE : DARK_TRIANGLE}
          />
          {highlightFor(idx) !== "none" && (
            <path
              d={trianglePath(idx)}
              fill="none"
              stroke={highlightFor(idx)}
              strokeWidth={4}
            />
          )}
          <text
            x={pointX(idx)}
            y={isTop(idx) ? BOARD_TOP - 10 : BOARD_BOTTOM + 20}
            textAnchor="middle"
            fontSize={12}
            fill="#333"
          >
            {idx + 1}
          </text>
        </g>
      ))}

      {Array.from({ length: 24 }, (_, idx) => {
        const raw = state.board[idx];
        const player = raw > 0 ? 0 : raw < 0 ? 1 : null;
        if (player === null) return null;
        const count = Math.abs(raw);
        const centers = checkerCenters(idx, count);
        return (
          <g key={`checkers-${idx}`}>
            {centers.map((y, i) => (
              <circle
                key={i}
                cx={pointX(idx)}
                cy={y}
                r={CHECKER_R}
                fill={player === 0 ? LIGHT_PLAYER : DARK_PLAYER}
                stroke="#222"
                strokeWidth={1.5}
              />
            ))}
          </g>
        );
      })}

      {/* Bar: player 0's checkers in the lower half, player 1's in the upper half. */}
      <g onClick={() => onPointClick(BAR)} style={{ cursor: "pointer" }}>
        {highlightFor(BAR) !== "none" && (
          <rect
            x={BAR_LEFT}
            y={BOARD_TOP}
            width={BAR_WIDTH}
            height={BOARD_BOTTOM - BOARD_TOP}
            fill="none"
            stroke={highlightFor(BAR)}
            strokeWidth={4}
          />
        )}
        {Array.from({ length: state.bar[0] }, (_, i) => (
          <circle
            key={`bar0-${i}`}
            cx={(BAR_LEFT + BAR_RIGHT) / 2}
            cy={BOARD_BOTTOM - CHECKER_R - 4 - i * (CHECKER_R * 2)}
            r={CHECKER_R}
            fill={LIGHT_PLAYER}
            stroke="#222"
            strokeWidth={1.5}
          />
        ))}
        {Array.from({ length: state.bar[1] }, (_, i) => (
          <circle
            key={`bar1-${i}`}
            cx={(BAR_LEFT + BAR_RIGHT) / 2}
            cy={BOARD_TOP + CHECKER_R + 4 + i * (CHECKER_R * 2)}
            r={CHECKER_R}
            fill={DARK_PLAYER}
            stroke="#222"
            strokeWidth={1.5}
          />
        ))}
      </g>

      {/* Off tray: player 1 (top-right bearer) on top, player 0 (bottom-right bearer) on bottom. */}
      <g onClick={() => onPointClick(OFF)} style={{ cursor: "pointer" }}>
        {highlightFor(OFF) !== "none" && (
          <rect
            x={OFF_LEFT}
            y={BOARD_TOP}
            width={OFF_RIGHT - OFF_LEFT}
            height={BOARD_BOTTOM - BOARD_TOP}
            fill="none"
            stroke={highlightFor(OFF)}
            strokeWidth={4}
          />
        )}
        <text
          x={(OFF_LEFT + OFF_RIGHT) / 2}
          y={BOARD_TOP + 20}
          textAnchor="middle"
          fill="#fff"
          fontSize={16}
        >
          {state.off[1]}
        </text>
        <text
          x={(OFF_LEFT + OFF_RIGHT) / 2}
          y={BOARD_BOTTOM - 10}
          textAnchor="middle"
          fill="#fff"
          fontSize={16}
        >
          {state.off[0]}
        </text>
      </g>
    </svg>
  );
}

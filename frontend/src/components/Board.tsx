import {
  BAR_LEFT,
  BAR_RIGHT,
  BAR_WIDTH,
  BOARD_BOTTOM,
  BOARD_LEFT,
  BOARD_RIGHT,
  BOARD_TOP,
  CHECKER_R,
  OFF_LEFT,
  OFF_RIGHT,
  checkerCenters,
  isTop,
  pointX,
  trianglePath,
} from "../lib/boardGeometry";
import { BAR, OFF, type GameState } from "../types/game";
import type { Flight } from "../hooks/useAnimatedBoard";

const LIGHT_PLAYER = "#f4f1ea";
const DARK_PLAYER = "#3a3a3a";
const LIGHT_TRIANGLE = "#c9a876";
const DARK_TRIANGLE = "#8a6642";

interface BoardProps {
  state: GameState;
  selectableSources: number[];
  selectedSource: number | null;
  selectableDestinations: number[];
  onPointClick: (idx: number) => void;
  flight?: Flight | null;
}

export function Board({
  state,
  selectableSources,
  selectedSource,
  selectableDestinations,
  onPointClick,
  flight,
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

      {flight && (
        <circle
          cx={flight.x}
          cy={flight.y}
          r={CHECKER_R}
          fill={flight.player === 0 ? LIGHT_PLAYER : DARK_PLAYER}
          stroke="#222"
          strokeWidth={1.5}
        />
      )}
    </svg>
  );
}

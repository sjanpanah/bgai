import { useRef, useState } from "react";
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
import { liftOne } from "../lib/visualMove";
import { BAR, OFF, type GameState } from "../types/game";
import type { Flight } from "../hooks/useAnimatedBoard";

const LIGHT_PLAYER = "#f4f1ea";
const DARK_PLAYER = "#3a3a3a";
const LIGHT_TRIANGLE = "#c9a876";
const DARK_TRIANGLE = "#8a6642";

// The human is always player 0 (see useGame.ts), and dragging is only ever
// possible on the human's own checkers (selectableSources is empty otherwise),
// so the drag ghost can just always use the human's color.
const HUMAN = 0;

const DRAG_THRESHOLD_PX = 4;

interface BoardProps {
  state: GameState;
  selectableSources: number[];
  selectedSource: number | null;
  selectableDestinations: number[];
  onPointClick: (idx: number) => void;
  onSelectSource: (idx: number | null) => void;
  onMove?: (source: number, target: number) => void;
  flight?: Flight | null;
}

interface DragState {
  source: number;
  x: number;
  y: number;
  moved: boolean;
}

export function Board({
  state,
  selectableSources,
  selectedSource,
  selectableDestinations,
  onPointClick,
  onSelectSource,
  onMove,
  flight,
}: BoardProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [drag, setDrag] = useState<DragState | null>(null);
  const pointerDownClient = useRef<{ x: number; y: number } | null>(null);
  const pointerDownIdx = useRef<number | null>(null);

  // Destinations outrank sources: a point can be both (moving onto your own
  // occupied point is legal and common), and if the generic "you could pick
  // this up" green wins, the selected checker's actual legal destination is
  // invisible. With one die left that can hide *every* destination, making a
  // playable turn look frozen — and since the turn can't complete, the AI
  // never gets to move either.
  const highlightFor = (idx: number) => {
    if (idx === selectedSource) return "#facc15";
    if (selectableDestinations.includes(idx)) return "#60a5fa";
    if (selectableSources.includes(idx)) return "#4ade80";
    return "none";
  };

  function clientToSvg(clientX: number, clientY: number): { x: number; y: number } {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) return { x: clientX, y: clientY };
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const p = pt.matrixTransform(ctm.inverse());
    return { x: p.x, y: p.y };
  }

  function handlePointerDown(idx: number, e: React.PointerEvent) {
    e.currentTarget.setPointerCapture(e.pointerId);
    pointerDownClient.current = { x: e.clientX, y: e.clientY };
    pointerDownIdx.current = idx;
    if (selectableSources.includes(idx)) {
      const p = clientToSvg(e.clientX, e.clientY);
      setDrag({ source: idx, x: p.x, y: p.y, moved: false });
    }
  }

  function handlePointerMove(e: React.PointerEvent) {
    if (!drag || !pointerDownClient.current) return;
    const dx = e.clientX - pointerDownClient.current.x;
    const dy = e.clientY - pointerDownClient.current.y;
    const moved = drag.moved || Math.hypot(dx, dy) > DRAG_THRESHOLD_PX;
    // Promote the drag into the shared selection the instant it becomes a real
    // drag. highlightFor reads selectedSource/selectableDestinations, so while
    // the drag source lives only in local state there is nothing to light up and
    // you drag blind. Deliberately not done on pointer *down*: a point can be
    // both a legal destination and a selectable source, and pre-selecting it
    // there would turn "click to move onto it" into "select it" instead.
    if (moved && !drag.moved) onSelectSource(drag.source);
    const p = clientToSvg(e.clientX, e.clientY);
    setDrag({ ...drag, x: p.x, y: p.y, moved });
  }

  function handlePointerUp(e: React.PointerEvent) {
    const wasDragging = drag?.moved ?? false;
    const source = drag?.source ?? pointerDownIdx.current;
    setDrag(null);
    pointerDownClient.current = null;
    pointerDownIdx.current = null;

    if (source === null) return;

    if (wasDragging) {
      const el = document.elementFromPoint(e.clientX, e.clientY);
      const dropTarget = el instanceof Element ? el.closest("[data-point-idx]") : null;
      if (dropTarget) {
        onMove?.(source, Number(dropTarget.getAttribute("data-point-idx")));
      }
      return;
    }

    onPointClick(source);
  }

  const renderState = drag?.moved ? liftOne(state, drag.source, HUMAN) : state;

  return (
    <svg
      ref={svgRef}
      viewBox="0 0 920 600"
      className="w-full max-w-4xl mx-auto select-none"
    >
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
          data-point-idx={idx}
          onPointerDown={(e) => handlePointerDown(idx, e)}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          style={{ cursor: "pointer", touchAction: "none" }}
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
            // The only label drawn outside the board rect, so it sits on the page
            // ground rather than on wood and has to follow the chrome palette.
            style={{ fill: "var(--color-muted)" }}
          >
            {idx + 1}
          </text>
        </g>
      ))}

      {Array.from({ length: 24 }, (_, idx) => {
        const raw = renderState.board[idx];
        const player = raw > 0 ? 0 : raw < 0 ? 1 : null;
        if (player === null) return null;
        const count = Math.abs(raw);
        const centers = checkerCenters(idx, count);
        return (
          <g key={`checkers-${idx}`} data-point-idx={idx}>
            {centers.map((y, i) => (
              <circle
                key={i}
                cx={pointX(idx)}
                cy={y}
                r={CHECKER_R}
                fill={player === 0 ? LIGHT_PLAYER : DARK_PLAYER}
                stroke="#222"
                strokeWidth={1.5}
                onPointerDown={(e) => handlePointerDown(idx, e)}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                style={{ cursor: "pointer", touchAction: "none" }}
              />
            ))}
          </g>
        );
      })}

      {/* Bar: player 0's checkers in the lower half, player 1's in the upper half. */}
      <g
        data-point-idx={BAR}
        onPointerDown={(e) => handlePointerDown(BAR, e)}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        style={{ cursor: "pointer", touchAction: "none" }}
      >
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
        {Array.from({ length: renderState.bar[0] }, (_, i) => (
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
        {Array.from({ length: renderState.bar[1] }, (_, i) => (
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
      <g
        data-point-idx={OFF}
        onPointerDown={(e) => handlePointerDown(OFF, e)}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        style={{ cursor: "pointer", touchAction: "none" }}
      >
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
          pointerEvents="none"
        />
      )}

      {drag?.moved && (
        <circle
          cx={drag.x}
          cy={drag.y}
          r={CHECKER_R}
          fill={LIGHT_PLAYER}
          stroke="#222"
          strokeWidth={1.5}
          pointerEvents="none"
        />
      )}
    </svg>
  );
}

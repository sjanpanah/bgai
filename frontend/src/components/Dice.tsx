import { useEffect, useRef, useState } from "react";

interface DiceProps {
  dice: [number, number] | null;
  // Dice not yet spent this turn — whatever value drops out of this list
  // relative to what's shown gets struck through as "played".
  remainingDice: number[];
}

const TUMBLE_MS = 400;
const TUMBLE_STEP_MS = 70;

function pips(value: number): boolean[] {
  // 3x3 grid, true = pip present, in reading order.
  const layouts: Record<number, boolean[]> = {
    1: [false, false, false, false, true, false, false, false, false],
    2: [true, false, false, false, false, false, false, false, true],
    3: [true, false, false, false, true, false, false, false, true],
    4: [true, false, true, false, false, false, true, false, true],
    5: [true, false, true, false, true, false, true, false, true],
    6: [true, false, true, true, false, true, true, false, true],
  };
  return layouts[value] ?? layouts[1];
}

function randomValue(): number {
  return 1 + Math.floor(Math.random() * 6);
}

// A static, unanimated die face — used wherever a past roll is displayed
// (e.g. the move history log) rather than the live roll-in-progress.
export function DieFace({ value, size = 48 }: { value: number; size?: number }) {
  return (
    <div
      className="grid grid-cols-3 grid-rows-3 bg-white border border-gray-400 rounded-md"
      style={{ width: size, height: size, gap: size / 24, padding: size / 8 }}
    >
      {pips(value).map((on, i) => (
        <div key={i} className={`rounded-full ${on ? "bg-gray-800" : ""}`} />
      ))}
    </div>
  );
}

function Die({
  value,
  settled,
  used,
}: {
  value: number;
  settled: boolean;
  used: boolean;
}) {
  return (
    <div
      className={`transition-transform duration-150 ${
        settled ? "scale-100 rotate-0" : "scale-90 rotate-6"
      } ${used ? "opacity-40 grayscale" : ""}`}
    >
      <DieFace value={value} />
    </div>
  );
}

// Matches shown die faces against the dice still available to play, so a
// value that dropped out of `remainingDice` renders as struck-through. Values
// are matched positionally-by-count rather than by index, since doubles show
// four identical faces and it doesn't matter which specific one is marked used.
function usedFlags(shown: number[], remaining: number[]): boolean[] {
  const pool = [...remaining];
  return shown.map((v) => {
    const idx = pool.indexOf(v);
    if (idx === -1) return true;
    pool.splice(idx, 1);
    return false;
  });
}

export function Dice({ dice, remainingDice }: DiceProps) {
  const [shown, setShown] = useState<number[] | null>(null);
  const [rolling, setRolling] = useState(false);
  const lastDice = useRef<[number, number] | null>(null);

  useEffect(() => {
    if (!dice) {
      lastDice.current = null;
      setShown(null);
      setRolling(false);
      return;
    }

    const isNewRoll =
      !lastDice.current ||
      lastDice.current[0] !== dice[0] ||
      lastDice.current[1] !== dice[1];
    if (!isNewRoll) return;
    lastDice.current = dice;

    const slotCount = dice[0] === dice[1] ? 4 : 2;
    setRolling(true);
    setShown(Array.from({ length: slotCount }, randomValue));

    const interval = setInterval(() => {
      setShown(Array.from({ length: slotCount }, randomValue));
    }, TUMBLE_STEP_MS);

    const timeout = setTimeout(() => {
      clearInterval(interval);
      setRolling(false);
      setShown(dice[0] === dice[1] ? Array(4).fill(dice[0]) : [dice[0], dice[1]]);
    }, TUMBLE_MS);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [dice]);

  if (!dice || !shown) return null;

  // Only meaningful once the tumble settles — mid-tumble faces are random
  // placeholders, not the real roll, so nothing should read as "used" yet.
  const used = rolling ? shown.map(() => false) : usedFlags(shown, remainingDice);

  return (
    <div className="flex gap-2">
      {shown.map((v, i) => (
        <Die key={i} value={v} settled={!rolling} used={used[i]} />
      ))}
    </div>
  );
}

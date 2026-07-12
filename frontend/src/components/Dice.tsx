import { useEffect, useRef, useState } from "react";

interface DiceProps {
  dice: [number, number] | null;
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

function Die({ value, settled }: { value: number; settled: boolean }) {
  return (
    <div
      className={`grid grid-cols-3 grid-rows-3 gap-0.5 w-12 h-12 bg-white border border-gray-400 rounded-md p-1.5 transition-transform duration-150 ${
        settled ? "scale-100 rotate-0" : "scale-90 rotate-6"
      }`}
    >
      {pips(value).map((on, i) => (
        <div key={i} className={`rounded-full ${on ? "bg-gray-800" : ""}`} />
      ))}
    </div>
  );
}

export function Dice({ dice }: DiceProps) {
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

  return (
    <div className="flex gap-2">
      {shown.map((v, i) => (
        <Die key={i} value={v} settled={!rolling} />
      ))}
    </div>
  );
}

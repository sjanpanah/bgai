interface DiceProps {
  dice: [number, number] | null;
}

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

function Die({ value }: { value: number }) {
  return (
    <div className="grid grid-cols-3 grid-rows-3 gap-0.5 w-12 h-12 bg-white border border-gray-400 rounded-md p-1.5">
      {pips(value).map((on, i) => (
        <div key={i} className={`rounded-full ${on ? "bg-gray-800" : ""}`} />
      ))}
    </div>
  );
}

export function Dice({ dice }: DiceProps) {
  if (!dice) return null;
  const values =
    dice[0] === dice[1] ? [dice[0], dice[0], dice[0], dice[0]] : dice;
  return (
    <div className="flex gap-2">
      {values.map((v, i) => (
        <Die key={i} value={v} />
      ))}
    </div>
  );
}

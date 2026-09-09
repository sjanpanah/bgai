import { describeResult } from "../lib/result";

type Props = {
  /** Engine-side multiplier: 1 plain, 2 gammon, 3 backgammon. */
  multiplier: number;
  humanWon: boolean;
  onNewGame: () => void;
  onDismiss: () => void;
};

export function GameResult({
  multiplier,
  humanWon,
  onNewGame,
  onDismiss,
}: Props) {
  const { headline, winType } = describeResult(humanWon, multiplier);

  return (
    // The scrim covers the board only, not the page: the move history below it
    // stays scrollable and selectable so a finished game can still be read or
    // copied. Dismissing uncovers the final position for the same reason.
    <div
      className="absolute inset-0 flex items-center justify-center bg-surface/75 rounded"
      onClick={onDismiss}
    >
      {/* Deliberately not a live region: the status line carries `role="status"`
          and announces the full result including the win type, so marking this
          too would announce the same outcome twice. */}
      <div
        className={`rounded-xl border px-8 py-5 text-center ${
          humanWon ? "border-win-line bg-win-surface" : "border-line bg-surface"
        }`}
        // The card is the result, not a way to dismiss it — only the scrim around
        // it is, so clicking "New game" can't also register as a dismissal.
        onClick={(event) => event.stopPropagation()}
      >
        <p className={`text-2xl ${humanWon ? "text-win" : "text-ink"}`}>
          {headline}
        </p>
        {winType && <p className="text-sm text-muted mt-1">{winType}</p>}
        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            className={`border rounded px-3 py-1 ${
              humanWon ? "border-win-line" : "border-line"
            }`}
            onClick={onNewGame}
          >
            New game
          </button>
          {/* `dim` would be 3.47:1 on the win card — under the 4.5:1 bar for
              small text. `muted` clears it on both card backgrounds. */}
          <button className="text-sm text-muted underline" onClick={onDismiss}>
            View board
          </button>
        </div>
      </div>
    </div>
  );
}

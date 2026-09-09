type Props = {
  /** Engine-side multiplier: 1 plain, 2 gammon, 3 backgammon. */
  multiplier: number;
  humanWon: boolean;
  onNewGame: () => void;
  onDismiss: () => void;
};

// The multiplier is the engine's field name, not a player's concept, and the
// app keeps no score — so it's translated to words here and never shown as a
// number. A plain win says nothing extra rather than "(x1)", which told the
// player nothing at the one moment they were certain to read.
const WIN_TYPE: Record<number, string> = {
  2: "by gammon",
  3: "by backgammon",
};

export function GameResult({
  multiplier,
  humanWon,
  onNewGame,
  onDismiss,
}: Props) {
  const winType = WIN_TYPE[multiplier];

  return (
    // The scrim covers the board only, not the page: the move history below it
    // stays scrollable and selectable so a finished game can still be read or
    // copied. Dismissing uncovers the final position for the same reason.
    <div
      className="absolute inset-0 flex items-center justify-center bg-surface/75 rounded"
      onClick={onDismiss}
    >
      <div
        role="status"
        className={`rounded-xl border px-8 py-5 text-center ${
          humanWon ? "border-win-line bg-win-surface" : "border-line bg-surface"
        }`}
        // The card is the result, not a way to dismiss it — only the scrim around
        // it is, so clicking "New game" can't also register as a dismissal.
        onClick={(event) => event.stopPropagation()}
      >
        <p className={`text-2xl ${humanWon ? "text-win" : "text-ink"}`}>
          {humanWon ? "You win" : "AI wins"}
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

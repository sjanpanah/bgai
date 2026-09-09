// The engine's multiplier is 1 plain / 2 gammon / 3 backgammon. It is a field
// name, not a player's concept, and the app keeps no score — so it is turned
// into words here and never shown as a number. Shared by the result panel and
// the status line so the two can't drift apart in wording.
const WIN_TYPE: Record<number, string> = {
  2: "by gammon",
  3: "by backgammon",
};

export type GameResultText = {
  headline: string;
  /** Absent for a plain win — there is nothing extra worth saying. */
  winType?: string;
};

export function describeResult(
  humanWon: boolean,
  multiplier: number,
): GameResultText {
  return {
    headline: humanWon ? "You win" : "AI wins",
    winType: WIN_TYPE[multiplier],
  };
}

/** One-line form, for the status line's single live-region announcement. */
export function resultSentence(humanWon: boolean, multiplier: number): string {
  const { headline, winType } = describeResult(humanWon, multiplier);
  return winType ? `${headline} ${winType}` : headline;
}

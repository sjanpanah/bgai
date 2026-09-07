# BACKLOG

Inbox for ad-hoc tickets — bugs, small features, ideas — as they come in. Not the
milestone plan (see `CLAUDE.md`) and not the post-1.0 future-ideas list (also in
`CLAUDE.md`); this is the catch-all for everything else so nothing said in passing
gets lost.

Triage as they arrive: link to a GitHub issue/PR if one gets opened, or just check
off and delete when done. Keep entries short — one line, expand in a linked issue
if it needs more.

## Open

- Improve the move history section (better formatting/readability, not just a flat log)
- Show the opponent's last dice roll
- Slow down the animations for the opponent's moves
- Add a pip counter to the board (both sides)
- Dark mode is broken — black text on dark backgrounds (e.g. point numbers are `#333`)
- Allow one checker to play both dice in a single click (3+2 = land 5 away, consuming both dice)
- Engine selection silently resets to the default (now Neural) on page reload — persist it
  (localStorage/URL); a reload swaps the opponent mid-game without any visual cue. Verified still
  broken after the default changed: nothing is written to localStorage or the URL
- No error handling on failed API calls — if the backend is down at page load, `newGame()` throws
  and the app sits on "Loading..." forever with no message and no retry
- `POST /game/new` fires twice on load (StrictMode double-invokes the effect), orphaning a game
- `aiMove` has no in-flight guard — changing the engine mid-AI-turn can fire two concurrent `POST /ai`
- Bear-off tray (`OFF`) uses `onClick` while every other point uses pointer events — different
  interaction path than the rest of the board
- Destination highlights should show while a checker is being dragged, not only after a
  click-select — `Board.tsx` keeps drag state locally and never feeds `selectedSource`, so
  `selectableDestinations` is empty mid-drag and you drag blind. Fix by lifting the drag source
  into the same selection state rather than duplicating the highlight logic: click and drag
  having separate sources of truth is what produced the M2-era highlight bug too

- Add a `wildbg` engine (open-source neural reference, HTTP API in local Docker) — plan drafted,
  needs strong nets from the `nets` branch swapped in before build since they're `include_bytes!`d

- Rewrite the README — it's stale and undersells the project. Says M5 is "next", omits `neural`
  from the engine list entirely, and documents the old wrong `choose_move(state, dice) -> Move`
  signature. Should add: the live demo link (note Render's free tier cold-starts, ~30s first
  load), a screenshot or short GIF of a game, the head-to-head benchmark table with confidence
  intervals, and a paragraph on the M5 result (TD(λ) net, 510k self-play games, plateaued at 125k)
- Tidy the commit history — squash the early CLAUDE.md doc churn (`v1` → `fold in feedback` →
  `add prior art`) and add milestone tags `m1-rules-engine`…`v1.0` so the ladder is navigable.
  Deliberately *keep* the bug-fix commits (e.g. the TD(λ) trace-sign fix): they document real
  debugging and a history where nothing ever breaks is less informative, not more
- Write up the M5 build as a post. Strongest material, roughly in order: the TD(λ) trace-sign
  bug (sanity gates read a perfect 0.999/0.003 and game length fell 189→54 plies while the net
  was actually learning almost nothing — a run that *degrades* is misconfigured, one that
  plateaus is merely undertrained); the plateau result (125k and 510k games statistically
  indistinguishable, so ~385k games bought nothing); the benchmark noise floor running through
  M3/M4/M5; grading move choice against a rollout oracle instead of win rate; and the board
  highlight bug that only surfaced by actually playing a game, which no test caught

## Done

- Rename difficulties/opponents (engine dropdown labels)
- Animate the dice roll (a little tumble/reveal, not just appearing)
- Move by clicking/dragging the checker itself, not just the point (triangle) behind it
- Animate checker movement — human and AI/opponent turns alike; no checker should ever teleport, always a movement

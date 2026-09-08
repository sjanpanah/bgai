# BACKLOG

Inbox for ad-hoc tickets — bugs, small features, ideas — as they come in. Not the
milestone plan (see `CLAUDE.md`) and not the post-1.0 future-ideas list (also in
`CLAUDE.md`); this is the catch-all for everything else so nothing said in passing
gets lost.

Triage as they arrive: link to a GitHub issue/PR if one gets opened, or just check
off and delete when done. Keep entries short — one line, expand in a linked issue
if it needs more.

## Open

### Bugs (priority order — effort vs. damage, highest priority first)

- No error handling on failed API calls (`useGame.ts:9-17,42-44`) — if the backend is down or
  cold-starting at page load, `newGame()` throws uncaught and the app sits on "Loading..."
  forever with no message and no retry. *Small effort, high damage*: Render free-tier cold
  starts make this a real first-impression failure, not a hypothetical
- `aiMove` has no in-flight guard (`useGame.ts:102-125`) — it's called from an `App.tsx` effect
  keyed on `selectedEngine`, so changing the engine mid-AI-turn fires a second concurrent
  `POST /ai`; both responses can race back and both call `setState`. *Small effort, high
  damage*: a genuine state-corruption race in production, not just a rough edge
- Destination highlights should show while a checker is being dragged, not only after a
  click-select — `Board.tsx` keeps drag state (`drag`, lines 44-63) local and never feeds
  `selectedSource` (`App.tsx:27`), so `selectableDestinations` stays empty mid-drag and you
  drag blind. Distinct from the M2-era highlight-precedence bug (fixed in `b9c5d53`) — that
  fixed *which* highlight wins when both apply; this is drag state never reaching the selection
  state at all. *Small effort, high damage*: breaks a primary interaction path (drag-to-move)
- Engine selection silently resets to the default (now Neural) on page reload
  (`App.tsx:26`, plain `useState`) — persist it (localStorage/URL); a reload swaps the opponent
  mid-game without any visual cue. *Trivial effort, medium damage*: quiet correctness bug, easy win
- Bear-off tray (`OFF`) uses `onClick` (`Board.tsx:265`) while every other point uses pointer
  events (`onPointerDown`/`Move`/`Up`) — inconsistent interaction path, and OFF can't act as a
  drag source. *Trivial effort, low damage*: touches the same `Board.tsx` pointer code as the
  drag-highlight bug above, worth batching with it
- `POST /game/new` fires twice on load (`useGame.ts:42-44`, no guard on the effect;
  `StrictMode` double-invokes it in dev), orphaning a game server-side. *Trivial effort, low
  damage in production* (StrictMode double-invoke is dev-only), but cheap to fix while already
  in `useGame.ts` for the two bugs above
- Dark mode is broken — black text on dark backgrounds (e.g. point numbers are `#333`
  in `Board.tsx:185`, plus hardcoded hex throughout `Board.tsx`/`MoveHistory.tsx`/`App.tsx`/
  `Dice.tsx`); no `dark:` variant or theme-token system exists anywhere yet (grep confirms
  zero hits). *Medium effort, medium damage*: not a couple of stray colors, it's an unstyled
  system — needs a dark-mode strategy decision before the fix, not just find-and-replace.
  Ordered last: real but visual-only, and the only item needing a design decision first

### UI / UX

- Auto-roll dice after the first roll of a turn (currently every roll needs a manual click)
- Improve the move history section (better formatting/readability, not just a flat log)
- Show the opponent's last dice roll
- Slow down the animations for the opponent's moves
- Add a pip counter to the board (both sides)
- Make the app responsive / usable on mobile browsers — untested so far. Partly there already
  (viewport meta tag is set, the board is an SVG with a `viewBox` so it should scale down), but
  there are zero breakpoints anywhere in the layout (header row, roll/history row are plain
  flexbox and will likely squeeze badly on a narrow screen) and touch input on the board has
  never been checked — the checker points are close together and may need larger tap targets
  for a finger rather than a mouse cursor

### Features

- Allow one checker to play both dice in a single click (3+2 = land 5 away, consuming both dice)
- Add a `wildbg` engine (open-source neural reference, HTTP API in local Docker) — plan drafted,
  needs strong nets from the `nets` branch swapped in before build since they're `include_bytes!`d
- Surface the running git commit so a deployed instance's code can be confirmed without
  guessing — a backend endpoint (e.g. `GET /version`) plus a small footer/about display in the
  UI showing what's actually live on Render/Pages vs. what's committed locally

### Docs / process

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

# BACKLOG

Inbox for ad-hoc tickets — bugs, small features, ideas — as they come in. Not the
milestone plan (see `CLAUDE.md`) and not the post-1.0 future-ideas list (also in
`CLAUDE.md`); this is the catch-all for everything else so nothing said in passing
gets lost.

Triage as they arrive: link to a GitHub issue/PR if one gets opened, or just check
off and delete when done. Keep entries short — one line, expand in a linked issue
if it needs more.

## Open

### Bugs

*(none open — see Done)*

### UI / UX

- Do a full UI review — walk the whole app in a browser and write down what looks or feels
  off (visual polish, spacing/alignment, colour and contrast, wording, affordances, empty and
  error states), then triage the findings back into this section as individual items
- Auto-roll dice after the first roll of a turn (currently every roll needs a manual click)
- Improve the move history section (better formatting/readability, not just a flat log)
- Show the opponent's dice, and keep them visible alongside its last move — right now the AI's
  roll is never rendered at all (`Dice` only ever shows the human's), so you see checkers move
  with no idea which dice produced them. The roll already comes back on the `/ai` response and
  is stored in the history entry; it just isn't displayed
- Make the opponent's move animation longer — it currently runs at the same speed as the
  human's, which is too fast to follow when you didn't choose the move yourself
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

- **Bug: dark mode was broken** — the real cause wasn't missing `dark:` variants but that the
  page never painted a background at all: `body` was transparent with black text, so any dark
  host ground showed through and made it unreadable. Fixed by giving the app **one palette it
  paints itself** (Tailwind v4 `@theme` tokens in `index.css`, `color-scheme: dark`), so the OS
  setting no longer changes anything — verified byte-identical under `prefers-color-scheme`
  light and dark. Ground is dark brown `#2a1f18` with cream `#f4f1ea` text borrowed from the
  light checker. The board, checkers and dice deliberately keep their own colours: they're
  physical objects, not themed UI. Only the point numbers moved (`Board.tsx`) since they're the
  one label drawn outside the board on the page ground. All pairs meet WCAG AA — note the button
  border needed lightening to `#85715c` for 3:1, because outlined buttons are identified solely
  by that border
- **Bug: a stale AI response clobbered a freshly started game** — `useGame` keeps a game epoch
  bumped by every `newGame()`; each request captures the epoch it was issued under and drops its
  result (and its error) if that no longer matches, so a slow response can't apply the previous
  game's position. The `aiMoveInFlight` release is epoch-aware too, so a discarded response can't
  unlock a request the new game has in flight
- **Bug: engine selection reset to the default on reload** — persisted to `localStorage`
  (`bgai.engine`), with reads/writes wrapped since it throws outright in some privacy modes, and
  a fallback to the default if a stored id ever outlives the engine it names
- **Bug: destination highlights didn't show mid-drag** — `Board` now lifts the drag source into
  the shared `selectedSource` state, so the existing `highlightFor` lights the source and its
  legal destinations during a drag with no duplicated highlight logic. The promotion happens on
  the first pointer *move* past the drag threshold, not on pointer down: a point can be both a
  legal destination and a selectable source, and selecting it on press would turn "click to move
  onto it" into "select it" — the same source/destination collision behind the M2-era bug
- **Bug: bear-off tray used `onClick`** — `OFF` now uses the same `onPointerDown`/`Move`/`Up`
  handlers (and `touchAction: "none"`) as every other point, so there's one interaction path
- **Bug: no error handling on failed API calls** — `useGame` now surfaces an `error` for all
  four API paths instead of throwing into the void; the app shows the message and a "Try again"
  button rather than "Loading..." forever, with a dismissible banner for mid-game failures (plus
  an explicit Retry on the AI's turn, whose effect deps don't change on failure so it can't
  retry itself). `useEngines` had the same bug — it never checked `res.ok`, threw an unhandled
  rejection, and left the dropdown permanently empty even after the backend came back
- **Bug: `aiMove` had no in-flight guard** — an `aiMoveInFlight` ref drops re-entrant calls.
  Verified by delaying the `/ai` response and switching engines 4× mid-request: 0 extra calls
- **Bug: `POST /game/new` fired twice on load** — a `didInit` ref guards the init effect
  (on the effect, not on `newGame`, so the "New game" button still works). Verified at exactly
  1 call per page load via the page's own Resource Timing
- Rename difficulties/opponents (engine dropdown labels)
- Animate the dice roll (a little tumble/reveal, not just appearing)
- Move by clicking/dragging the checker itself, not just the point (triangle) behind it
- Animate checker movement — human and AI/opponent turns alike; no checker should ever teleport, always a movement

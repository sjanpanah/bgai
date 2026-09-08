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

- Bear-off tray's clickable/droppable area is too small — the `<g data-point-idx={OFF}>` in
  `Board.tsx` has pointer handlers but no invisible fill covering the tray, so SVG only hit-tests
  its actual children (the pip-count text, the conditional highlight border which is `fill="none"`,
  and any checkers already borne off). Add a transparent full-tray `<rect>` (matching the
  `OFF_LEFT`/`OFF_RIGHT`/`BOARD_TOP`/`BOARD_BOTTOM` highlight rect's geometry) as the actual hit
  target so bearing off works from anywhere in the tray, not just the number. this might have started when we added the pip counters.

### UI / UX

- Do a full UI review — walk the whole app in a browser and write down what looks or feels
  off (visual polish, spacing/alignment, colour and contrast, wording, affordances, empty and
  error states), then triage the findings back into this section as individual items
- Unify colors across the app — right now colors get picked ad hoc per feature (e.g. the move
  history log shipped with placeholder blue/green for AI/You that don't match the app's actual
  brown/cream palette or the board's checker colors). Needs one deliberate pass: decide how
  player identity (AI vs You) is color-coded — text label, and whether the opponent's dice get
  a distinct face color from the player's own (white) dice — and apply it consistently anywhere
  player identity shows up (history log, future opponent-dice display, etc.)
- Drop the green "movable checker" highlight shown on every legal source as soon as the dice
  are rolled — your own checkers are already obvious from their colour, so outlining them adds
  noise without telling you anything. Note what it technically encodes is *sources with a legal
  move*, not "yours": a checker of yours that can't move this roll isn't green, so removing it
  gives that up (clicking a stuck checker would just do nothing instead). Pairs with the
  subdued-destination-preview item above — if the green goes and the preview never lands, the
  board offers no hint at all until you click a checker. Keep the yellow selected-source and
  blue destination highlights either way; those carry real information
- Make the app responsive / usable on mobile browsers — untested so far. Partly there already
  (viewport meta tag is set, the board is an SVG with a `viewBox` so it should scale down), but
  there are zero breakpoints anywhere in the layout (header row, roll/history row are plain
  flexbox and will likely squeeze badly on a narrow screen) and touch input on the board has
  never been checked — the checker points are close together and may need larger tap targets
  for a finger rather than a mouse cursor
- Mark dice used during a turn — once a die's move has been played, visually distinguish it
  (e.g. dim/strike it out) from dice still available, so mid-turn it's obvious what's left to play

### Features

- Add a `wildbg` engine (open-source neural reference, HTTP API in local Docker) — plan drafted,
  needs strong nets from the `nets` branch swapped in before build since they're `include_bytes!`d
- Exploration: run history, users, and login — persist completed games (result, engine played,
  moves/dice) instead of losing them at game-over, and gate that history behind actual user
  accounts. Bigger than anything else here: needs an auth story (sessions? OAuth?), a users
  table, a run-history schema tied to `GameState`'s serialization, and endpoints/UI to browse
  past games. No decisions made yet — scope this out before committing to an approach

### Docs / process

- Revamp the term "AI" across the project — UI copy, code, docs all just say "AI"/"the AI";
  reconsider the naming (engine name, opponent name, etc.) project-wide
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

- **Hide the "New game" button when it would be a no-op** — only shown once the opponent has
  changed or the first roll has happened, since before that a fresh game is identical to the
  one in progress. `App.tsx` tracks `gameStartEngine` (the engine selected when the current
  game began, via a ref updated on every dropdown change and snapshotted in an effect keyed on
  `gameId`) and compares it against the live `selectedEngine`
- **Let one checker play both dice in a single drag** (e.g. 3+2 = 5 away), and show the
  destination preview this unlocked. Backend adds `combined_moves` — two-hop combos built by
  composing the existing legal-move generator (`legal_next_moves`/`apply_move`), exposed
  additively on the roll/move responses; a `(source, target)` pair is only offered when every
  order that reaches it leaves an identical board, so a pair where one die order hits a blot
  and the other doesn't is dropped rather than picking an order arbitrarily — that's a real
  decision, not a detail to paper over. Frontend highlights: bright blue direct destinations,
  faded blue for combined-only ones (color picked as a placeholder, "close enough" per Simon —
  revisit with the colors-unification item below), yellow selected source, plus a dim
  whole-turn preview of every reachable destination before any source is picked (disappears
  once one is selected). Landing on a combined destination fires two sequential `/move` calls
  under the hood, applied as one history entry and one queued animation
- **Slow the AI's move animation** — 700ms per hop vs the human's 350ms, so opponent moves are
  easy to follow without feeling sluggish. Needed a real `isAnimating` flag from
  `useAnimatedBoard` (set synchronously when a turn is queued) rather than deriving it from
  `flight !== null`, which had a race: `state.turn` flips to the human before the first
  animation frame lands, so the naive check let the next auto-roll fire mid-AI-animation
- **Auto-roll dice** after the game's first manual roll — only the very first roll is a
  deliberate click; every roll after that fires on its own once it's the human's turn again
- **Revamped the move history log** — newest-first rows, one line each: turn number, colored
  You/AI label, real per-turn dice icons (reusing a new `DieFace` factored out of `Dice.tsx`),
  then the move steps (roll digits dropped since the dice icons already show them). This
  subsumed the separate "show the opponent's dice" ticket — same underlying gap, one fix.
  Colors are placeholder blue/green for now; see "Unify colors across the app" below
- **Pip counter** — plain number just outside each side's off tray (top for AI, bottom for
  you), muted color like the point-number labels, no "pips:" label (position implies meaning).
  `lib/pipCount.ts` mirrors the backend's `GameState.pip_count()` exactly
- **Surface the running git commit** — `GET /version` reports the API's commit
  (`RENDER_GIT_COMMIT` when deployed, working tree locally, `source` says which); the frontend
  bakes its own in at build time via `VITE_COMMIT` (CI passes `github.sha`, `vite.config.ts`
  falls back to git); the footer shows both and flags a mismatch, which is the real signal
  since Pages and Render deploy independently and can drift apart. Local builds get a
  `-dirty` suffix when the tree has uncommitted edits — otherwise the endpoint names a
  commit whose code isn't what's running, which is the normal state while developing
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

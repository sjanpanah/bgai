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

- explore having the first roll be a toss up
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

### Features

- Add a `wildbg` engine (open-source neural reference, HTTP API in local Docker) — plan drafted,
  needs strong nets from the `nets` branch swapped in before build since they're `include_bytes!`d
- Exploration: run history, users, login — and where a game actually lives. Persist completed
  games (result, engine played, moves/dice) instead of losing them at game-over, gate that
  history behind real accounts, and resolve session persistence as part of the same design.
  Bigger than anything else here: needs an auth story (sessions? OAuth?), a users table, a
  run-history schema tied to `GameState`'s serialization, and endpoints/UI to browse past games.
  No decisions made yet — scope this out before committing to an approach.

  **Session persistence belongs here, not as a standalone fix.** Reloading the page currently
  starts a new game (`useGame` calls `newGame()` on mount and nothing persists `game_id`) — that
  is accepted behaviour for now, deliberately, because a proper fix runs straight into the
  questions above. What the QA pass established about it (`qa/report.md`, F2.7):
  - The server session is only `{state, remaining_dice}`. The move history, the rolled dice
    *pair*, and the partial turn are client-only React state, so resuming by id alone would
    restore the board but not the log, and could not honestly redraw a partly-played roll.
  - Resuming by `game_id` would work locally and mostly fail in production: the store is
    in-memory and Render's free tier spins the instance down when idle, so a stored id is
    worthless after ~15 minutes — exactly the gap after which a player expects their game back.
  - The robust alternative is persisting the *position* (client-side, then recreated
    server-side) rather than a pointer to it. That means trusting a client-supplied `GameState`
    — harmless today, but the moment results are recorded against an account it becomes a way
    to fabricate a win. That trust boundary is the reason this waits for the auth design.
  - Also unresolved and account-shaped: two tabs would share one `game_id` and silently fight
    over the same server session, and there is no notion of a game belonging to anyone (knowing
    an id is enough to play it — F7.4).
  - There is no `GET /game/{id}`; any resume story needs one, and it is the natural sibling of
    the stateless `POST /engine/move` the API already has.

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
  debugging and a history where nothing ever breaks is less informative, not more.
  While in there: six commits carry a `Co-Authored-By: Claude ...` trailer, against the
  no-attribution preference — `3c261b2b`, `48a48db9`, `72216a07` (2026-07-12 UI work) and
  `f29f1982`, `6225bece`, `84604bb5` (2026-07-03 CLAUDE.md churn, three of which the squash
  above already collapses). Claude is never the actual author or committer — all 212 commits
  are `Simon J` in both fields — it is only the message trailer, which is what GitHub renders
  as a second avatar. Stripping it rewrites every SHA back to 2026-07-03, so fold it into the
  same rewrite as the squash and tags rather than doing it separately
- Write up the M5 build as a post. Strongest material, roughly in order: the TD(λ) trace-sign
  bug (sanity gates read a perfect 0.999/0.003 and game length fell 189→54 plies while the net
  was actually learning almost nothing — a run that *degrades* is misconfigured, one that
  plateaus is merely undertrained); the plateau result (125k and 510k games statistically
  indistinguishable, so ~385k games bought nothing); the benchmark noise floor running through
  M3/M4/M5; grading move choice against a rollout oracle instead of win rate; and the board
  highlight bug that only surfaced by actually playing a game, which no test caught

### QA

Open findings from the unattended QA pass of 2026-09-08. The full report — repro, reasoning and a
suggested fix for each — is `qa/report.md`; these are one-liners so nothing gets lost, not a
replacement for it. Its "Fix these first" section has its own tracker at the top of the report and
is done apart from the colour work below; everything here sat outside that priority list.

Of 55 findings: 23 fixed, 1 deferred (session persistence, folded into the run-history item above),
31 open — the 31 below.

**Accessibility — the largest untouched block. The report's verdict: "unplayable without a mouse and
unreadable without sight."**

- The game cannot be played by keyboard at all — only two focusable elements exist in the whole app
  (F4.1, the report's only accessibility blocker). Suggested route: a focusable list of the legal
  moves, which are already in `legalMoves` and already rendered as notation, rather than making 26
  SVG groups focusable
- The board is invisible to assistive technology — the entire game appears in the accessibility tree
  as two nodes, both reading "167" (F4.3). Needs `role="img"` + a position description, and labelled
  pip counts
- Every board highlight fails the 3:1 non-text contrast bar, the legal-destination blue at 1.13:1
  against the light triangles (F4.6). Do this with the colour-unification item above, not separately
- Focus visibility is entirely inherited from the browser, never designed (F4.2)
- The dark checkers are barely distinguishable from the board — 1.34:1 against the felt, legible only
  via a 1.5px outline that is sub-pixel on a phone (F4.7)
- Nothing respects `prefers-reduced-motion`, and the app animates a great deal (F4.8). `animateHop`
  already has a documented `speedMs <= 0` fast path to hang it on

**Mobile, beyond the breakpoint that has landed**

- Every board tap target on a phone is far under the 44px guideline: point triangle 21px, checker
  11px, bear-off tray 14px (F3.2). The report is explicit that the honest fix is a mobile *layout*,
  not bigger hit boxes on the current one
- On a phone the board gets 22% of the screen while 41% of it sits blank below the footer (F3.4).
  Letting the history log collapse on small screens would roughly double the board

**Colour — one coherent pass, with the colour-unification item above**

- The same colour means two different things, and one meaning changes colour halfway through the
  interaction (F1.8) — a combined destination is amber `#fbbf24` before selection and blue `#60a5fa`
  after (F1.15, confirmed by measurement)
- Ten of twenty-six board locations light up in three hues at two opacities before the player has
  expressed any intent (F1.14). Note the report argues the *reverse* of the "drop the green
  highlight" item above: keep the green sources, drop the whole-turn preview, since the preview never
  says *which* checker goes there

**Interaction and polish**

- A forced "no legal move" turn passes with no feedback at all — the dice are nulled the instant the
  response lands, so a dance is invisible except as a "(no move)" row in the log (F1.4)
- The "Roll" button appears once, is clicked once, then vanishes forever (F1.9). Either auto-roll the
  first roll too, or keep it present-but-disabled
- Everything on the board says "clickable" via an unconditional `cursor: pointer`, including the AI's
  checkers and the whole board during the AI's turn (F1.13)
- You cannot deselect a checker by clicking it again; cancelling means knowing to click something
  irrelevant (F2.5)
- Switching opponent mid-game is invisible in the history — every opponent turn is labelled "AI"
  (F2.8)
- The initial loading state is the bare word "Loading..." — against Render's cold start this is the
  first thing a visitor sees for up to 30 seconds (F1.19)
- The page scrolls vertically on a standard laptop viewport (F1.7). May be partly improved by the
  history log now sizing to its content — re-measure before acting
- The page has essentially no typographic hierarchy (F1.17)
- The internal game UUID is printed in the player-facing footer (F1.10). Shortening it also stops a
  screenshot handing a bystander a usable handle to play the other side (F7.4)
- The opponent is called three different things across the UI (F1.18) — this is the "revamp the term
  AI" item above, found independently

**Backend and ops**

- `newGame` has no in-flight guard, unlike `aiMove` — eight rapid clicks fire eight `POST /game/new`.
  The UI stays correct, so it is a resource bug, not a correctness one (F2.6)
- No JSON 500 handler: an unhandled engine exception reaches the client as the plain-text string
  `Internal Server Error`, so the frontend cannot tell "the server is broken" from "unreachable"
  (F2.4)
- `GET /version` reports a stale commit under `uvicorn --reload` — locally it can name a commit that
  is not what is running, the one thing the endpoint exists to prevent (F0.1)
- Python dependencies are floors, not pins, and the production image installs the `[dev]` extra, so
  pytest and ruff ship to production and no rebuild is reproducible (F7.6)
- What `ALLOWED_ORIGINS` is actually set to on Render is unknown and unreviewable — it lives in the
  dashboard, not the repo (F7.1). A `render.yaml` would fix that
- **The deployed API is well behind `main`** (F7.7 measured three commits; it is now far more,
  including the bear-off blocker fix). The live demo is still serving the 500 that ends most games

**Nits**

- Stale comments describe a strike-through that was replaced by dimming (F1.11)
- `Math.random()` in the dice tumble — the report checked and says this is *fine* (decorative values
  that never leave the component; the real dice come from the server); it wants a comment saying so,
  not a change (F1.12)
- Occupied points render two elements carrying the same `data-point-idx` (F1.16)

## Done

- **Full UI review** — done as an unattended overnight QA pass (`qa/report.md`; the harness and the
  prompt it was given are in `qa/prompt.md`), which went well beyond the original ask: eight phases
  covering the UI walkthrough, real games against every engine, responsive and touch, accessibility,
  failure behaviour, API robustness and security. Findings live in the report rather than being
  triaged back into this file — each one carries its own repro and suggested fix, which a one-line
  backlog entry loses. Start from its "Fix these first" section; it holds one blocker (`combined_moves`
  500s on bear-off overage, which killed 56-76% of measured games and is live in the deployed demo)
- **Bug: bear-off tray's clickable/droppable area was too small** — the `<g data-point-idx={OFF}>`
  in `Board.tsx` had pointer handlers but no filled geometry covering the tray, so SVG only
  hit-tested its actual children (the pip-count text, the conditional highlight border which is
  `fill="none"`, and any checkers already borne off) — clicking or dropping anywhere else in the
  tray silently missed. Fixed with a transparent full-tray `<rect>` (matching the highlight
  rect's `OFF_LEFT`/`OFF_RIGHT`/`BOARD_TOP`/`BOARD_BOTTOM` geometry) as the first child, so the
  whole tray is now the real hit target. Likely dates back to the pip-counter change, which added
  the first non-hit-testable content (the border rect, `fill="none"`) into that `<g>`
- **Mark dice used during a turn** — dimmed/grayscaled once played rather than struck through
  (tried a strike-through line first; dropped it, dimming alone reads cleaner). The server now
  tracks and returns `remaining_dice` on `/roll` and `/move` (additive field, mirrors the
  session-side bookkeeping the API already did internally for `die_used`), so the frontend
  doesn't need to infer which die a move consumed — it just diffs the shown faces against
  `remaining_dice` by value/count, which handles doubles (four identical faces, only count
  matters) for free
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

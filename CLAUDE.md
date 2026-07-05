# CLAUDE.md — Backgammon vs AI

Persistent instruction set for Claude Code on this project.
Read at the start of every session before touching code.

---

## Project overview

A web app to play backgammon against an AI opponent. A human plays in the browser
against a selectable AI engine. The AI is built incrementally — from a trivial
baseline up to a strong engine — but all engines live behind one stable interface
and are chosen from a dropdown in the UI.

Built agile-first: a playable game against the *weakest* engine ships first, then
stronger engines are plugged in underneath without the frontend changing.

---

## Core architectural principle: the engine is pluggable

The single most important design rule. There is ONE engine interface:

    choose_move(state: GameState, dice: Dice) -> Move
    # (plus offer/accept for the doubling cube post-1.0 — see Future ideas)

Every AI is an implementation of it. The UI has a dropdown that names the active
engine; the API takes an optional `engine` query param (default = weakest available).
Adding a new engine must never require touching the frontend or the rules engine.

Planned engine ladder (rough order of increasing strength — a guide, not a rigid gate;
we implement as we see fit):
1. `random`        — legal random move. The baseline / test opponent.
2. `heuristic`     — hand-tuned eval (pip count, blots, primes) + 1-ply expectiminimax.
3. `expectiminimax`— deeper search over dice chance nodes + Monte Carlo rollouts.
4. `neural`        — TD-Gammon-style self-play network (research milestone). Start from the
                     standard 198-feature TD-Gammon encoding (see Prior art); custom
                     encodings are a later experiment, not a starting point.
5. `gnubg`         — wrap GNU Backgammon as a strong reference / benchmark.

Head-to-head win rate over N games is how we judge an engine — it's the AI's real test
suite. Use it to justify that a new engine is stronger, but it is **not** a hard pass/fail
bar and engines need not be built in strict ladder order.

`gnubg` is a fixed *reference* point, not really a rung on the ladder: it wraps an existing
binary rather than building something new, so bring it in whenever it's useful to benchmark
against (e.g. as soon as `heuristic` exists) rather than treating it as strictly last. Note
it is heavier than the other engines — needs the external binary installed and subprocess
plumbing — so weigh that cost when deciding when to wire it up. See the gnubg note under
the API section for how its format stays contained.

### Benchmark harness (set up once, use a thousand times)

A developer-facing harness pits engines against each other over N games and reports win
rates — plus a nice summary graphic. Build it once, early, as reusable framework; it's how
we justify that each new engine is actually stronger.

- A competitor is an `(engine_id, params)` pair, not just a name — so the *same* engine at
  different settings competes as distinct entrants (e.g. `expectiminimax` at depth 2 vs
  depth 3 vs depth 4, all against each other and against `random`, `gnubg`, etc.). Run them
  round-robin.
- Parameters are **developer-configured only** — this is our tuning tool, not a user
  feature. The UI dropdown / `registry.py` stays a small curated set of shipped engines a
  human would want to play; the harness can instantiate any `(engine_id, params)` pair,
  including ones that never appear in the dropdown.
- The harness drives games through the stateless `POST /engine/move` endpoint (above) — no
  per-game session overhead.

---

## The rules engine is the real foundation

Legal move generation is the hard, bug-prone core: two dice, doubles = four moves,
bar re-entry, hitting blots, bearing-off rules. Build it as a PURE library:
no UI, no AI, no I/O. Both the frontend and every engine consume it.

Non-negotiables:
- **Dice are injectable.** Randomness is a dependency, never a hidden global — so
  tests are deterministic and games are reproducible. `Dice` is passed in / seedable.
- **Exhaustive tests** on move generation and bearing off before any AI work.
- `GameState` is serializable (it crosses the API and seeds the AI).

### Serialization is the shared currency

One `GameState` JSON encoding underpins four things: the API wire format, **save/load**
(persist a game, reload it, keep playing), the **stateless best-move endpoint**
(`POST /engine/move`, see API contract), and the **engine benchmark harness** (see Core
architectural principle). Design for this from the start — keep the engine interface a
pure function over serialized state so all four fall out for free. The rules/engine layer
must never depend on any single consumer's format (see the gnubg note in API contract):
our `GameState` JSON stays canonical everywhere.

### v1 rules scope
In: single game, standard start, all movement, hitting/bar, bearing off, win
detection, and **gammon (2x) / backgammon (3x)** scoring.
Out of v1.0 entirely: the doubling cube, match play, Crawford, match equity. These are
post-1.0 (see Future ideas) — do not add them.

### Move-generation rules that are easy to get wrong
- Generate **full turn sequences** (the legal combinations of both dice), not single-die
  steps. Sequences that reach the same board via different die order collapse to one.
- Doubles are **four** moves of the die value.
- A player must use **both** dice if any legal sequence does; if only one is playable,
  they must play the **larger** die when possible.
- Checkers on the **bar** must all re-enter before any other move.
- Bearing off: exact rolls bear off the matching point; a roll higher than the highest
  occupied point bears off from the highest point (overage), but only once no checkers
  sit on higher points.

Consider differential-testing move generation against `gym-backgammon` on random positions
before calling M1 done — see Prior art & references, just below.

### Board representation
Store the 24 points + bar + off **absolutely**; expose player-relative views as helpers
for UI and AI. Pick one encoding (signed counts, or two per-player arrays), document it
in `state.py`, and never mix. Pip count is a derived helper used by tests and `heuristic`.

---

## Prior art & references

Pointers, not dependencies — we build our own pure rules engine, but these inform it:

- **`gym-backgammon`** (dellalibera) — the de-facto Python rules substrate; most ML
  backgammon repos borrow it instead of writing rules. Use it as a **differential-test
  oracle**: on random positions, assert our legal-move set matches theirs. Its move-gen
  confirms our model (moves as `(source, target)` tuples; must use the most dice possible).
- **198-feature TD-Gammon encoding** — the settled standard input for the neural engine
  (per point: `[0,0,0,0]` empty, `[1,0,0,0]` one, `[1,1,1,(n-3)/2]` for 3+; ×24 ×2 players
  + bar/off + turn = 198). Enhanced variants add hand-crafted features (~250-dim). Start
  here; our own encodings are a later experiment.
- **gnubg / `gnubg-hints`** — GNU Backgammon is our strong reference; the nodots project
  shows the wrap-gnubg-behind-a-provider pattern we're using works in practice.
- **Rules edge cases** — [bkgm.com rules FAQ](https://bkgm.com/rules/rul-faq.html) and
  gnubg source are the authorities for the forced-larger-die and bear-off-overage cases.

Most hobby repos in this space ship **no rules test suite** — our exhaustive-tests-first
stance is the main thing that sets this foundation apart. Don't drop it.

---

## Repo structure

    /
    ├── backend/              # Python + FastAPI
    │   ├── main.py
    │   ├── engine/           # PURE rules library — no framework deps
    │   │   ├── state.py      # GameState, Move, Dice, board representation
    │   │   ├── moves.py      # legal move generation, apply_move
    │   │   └── rules.py      # hitting, bearing off, win detection
    │   ├── ai/               # engines, all implementing the same interface
    │   │   ├── base.py       # Engine protocol / ABC
    │   │   ├── random_engine.py
    │   │   ├── gnubg_engine.py  # subprocess adapter; Position ID stays contained here
    │   │   ├── registry.py   # name -> engine, powers the UI dropdown
    │   │   └── benchmark.py  # harness: (engine_id, params) round-robin, win rates
    │   ├── routers/
    │   │   └── engine.py     # POST /engine/move — stateless best-move endpoint
    │   ├── models/           # Pydantic request/response bodies
    │   └── tests/
    ├── frontend/             # React + Vite + TypeScript
    │   └── src/{components,hooks,pages,types}/
    ├── docker-compose.yml
    ├── CLAUDE.md
    └── README.md

---

## Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python + FastAPI | Async, typed; hosts rules engine + AI |
| Rules engine | Pure Python | No framework deps, heavily tested |
| Frontend | React + Vite + TypeScript | |
| Styling | Tailwind CSS | Utility-first, no component lib without discussing |
| Board render | SVG (start) | Try both a sourced open-license board and a hand-built one, compare, keep the winner; revisit canvas if perf needs it |
| Dev infra | Docker Compose | api + frontend |

---

## API contract (stable — shapes don't change between milestones)

    POST /game/new        -> { game_id, state }
    POST /game/{id}/roll  -> { dice, legal_moves }
    POST /game/{id}/move  -> { state, legal_moves }        # human move
    POST /game/{id}/ai    ?engine=random -> { move, state } # ask AI to move
    GET  /engines         -> [ { id, label, available } ]   # powers UI dropdown
    POST /engine/move     -> { move }                       # stateless: no game_id

`engine` is an optional param defaulting to the weakest available engine. Adding
engines is additive and backwards-compatible — the frontend never needs updating.

The server holds game state keyed by `game_id` and is authoritative for legality —
the frontend renders and collects intent, it never decides what's legal.

**Stateless best-move endpoint.** `POST /engine/move` takes `{ state, dice, engine }` and
returns `{ move }` — a pure function over a serialized position, no game session involved.
It's part of the harness/framework, designed in from the start, not bolted on: it's what
save/load, position analysis, and the engine benchmark all call underneath. (The endpoint
itself first ships with the API in M2 since M1 is a pure lib with no I/O — but the M1 engine
interface must already be a pure, stateless-friendly function so this stays a thin wrapper.)

**gnubg format stays contained.** GNU Backgammon speaks its own compact board encoding
(Position ID / Match ID) over a subprocess/`hint` interface. All of that translation lives
*inside* the `gnubg` engine adapter — it converts our `GameState` → Position ID right before
shelling out and the reply back to a `Move` right after. Nothing outside that adapter ever
sees a Position ID; our `GameState` JSON remains the one canonical format.

Post-1.0 additive change: cube fields on `state` plus offer/take/drop endpoints. Additive
only — v1 clients keep working.

---

## Milestones (v1.0)

The numbered milestones drive toward a **1.0** release. Everything past that is post-1.0
(see Future ideas) and is not committed to a slot.

| # | Name | Status | Deliverable |
|---|---|---|---|
| M1 | Rules engine | done | Pure lib: legal moves, hitting, bearing off, win — fully tested, no UI |
| M2 | Playable UI vs random | done | Full board, click-to-move, play a full game vs `random` engine |
| M3 | Heuristic engine | done | `heuristic` engine + working UI selector |
| M4 | Expectiminimax + rollouts | next | `expectiminimax` engine, benchmarked vs heuristic |
| M5 | Neural engine | future | TD-Gammon-style self-play engine, benchmarked vs expectiminimax and (if wired up by now) `gnubg` |

That's 1.0.

## Future ideas (post-1.0)

Uncommitted, not scheduled — captured so we don't lose them.

- **1.1 — Doubling cube.** Cube rules in the engine + AI cube decisions (offer/take/drop).
  Additive to the API (cube fields on `state`, new endpoints); v1.0 clients keep working.
- **Persian rules variant.** Backgammon as played without the doubling cube (per Simon's
  culture) — a rules variant behind the same engine interface.
- **Nicer board asset.** M2 ships a hand-built SVG board only. Revisit in a later milestone:
  source an open-license SVG board, compare against the hand-built one, keep the winner.

---

## Frontend components (M2)

Board (24 points + bar + off), Dice (doubles show four), click/drag move interaction
that only offers legal destinations and supports partial turns, turn/status with
game-over + win type, an engine-selector dropdown fed by `GET /engines`, and a move
history log in standard notation (e.g. `31: 8/5 6/5`).

---

## Coding conventions

### Python
- Type hints everywhere; Pydantic for all request/response bodies
- Rules engine has ZERO framework imports — keep it pure and portable
- Engine tests near-total coverage: known positions, forced-move rules, bear-off overage
- Tests in backend/tests/ with pytest; formatter: ruff
- Dependencies in pyproject.toml

### TypeScript / React
- Functional components + hooks only; types in src/types/
- API calls abstracted into src/hooks/ (useGame, useEngines)
- Formatter: prettier

### General
- Every session leaves the repo in a working state
- Never call an unseeded global RNG — thread the seed through everything that rolls
- Comments explain *why*, not *what*

---

## What NOT to do

- Do not bake AI/product logic into the rules engine — keep it pure
- Do not add engines that bypass the `choose_move` interface
- Do not change the API response shapes — they are the contract
- Do not build the doubling cube in v1.0 — it's post-1.0 (1.1)
- Do not add ML tooling (PyTorch/NumPy) before the neural milestone
- Do not add a component library without discussing first

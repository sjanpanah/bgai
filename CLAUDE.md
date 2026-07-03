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
    # (plus offer/accept for the doubling cube later — not in M1)

Every AI is an implementation of it. The UI has a dropdown that names the active
engine; the API takes an optional `engine` query param (default = weakest available).
Adding a new engine must never require touching the frontend or the rules engine.

Planned engine ladder (build in order, all selectable once built):
1. `random`        — legal random move. The baseline / test opponent.
2. `heuristic`     — hand-tuned eval (pip count, blots, primes) + 1-ply expectiminimax.
3. `expectiminimax`— deeper search over dice chance nodes + Monte Carlo rollouts.
4. `neural`        — TD-Gammon-style self-play network (research milestone).
5. `gnubg`         — wrap GNU Backgammon as a strong reference / benchmark.

Each engine must **measurably beat the one below it** over N games. That head-to-head
win rate is the AI's test suite — a new engine isn't done until it clears the bar.

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

### v1 rules scope
In: single game, standard start, all movement, hitting/bar, bearing off, win
detection, and **gammon (2x) / backgammon (3x)** scoring.
Out until M5: the doubling cube, match play, Crawford, match equity. Do not add
them early.

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

### Board representation
Store the 24 points + bar + off **absolutely**; expose player-relative views as helpers
for UI and AI. Pick one encoding (signed counts, or two per-player arrays), document it
in `state.py`, and never mix. Pip count is a derived helper used by tests and `heuristic`.

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
    │   │   └── registry.py   # name -> engine, powers the UI dropdown
    │   ├── routers/
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
| Board render | SVG (start) | Simple, testable; revisit canvas if perf needs it |
| Dev infra | Docker Compose | api + frontend |

---

## API contract (stable — shapes don't change between milestones)

    POST /game/new        -> { game_id, state }
    POST /game/{id}/roll  -> { dice, legal_moves }
    POST /game/{id}/move  -> { state, legal_moves }        # human move
    POST /game/{id}/ai    ?engine=random -> { move, state } # ask AI to move
    GET  /engines         -> [ { id, label, available } ]   # powers UI dropdown

`engine` is an optional param defaulting to the weakest available engine. Adding
engines is additive and backwards-compatible — the frontend never needs updating.

The server holds game state keyed by `game_id` and is authoritative for legality —
the frontend renders and collects intent, it never decides what's legal.

The one additive change reserved for M5: cube fields on `state` plus offer/take/drop
endpoints. Additive only — v1 clients keep working.

---

## Milestones

| # | Name | Status | Deliverable |
|---|---|---|---|
| M1 | Rules engine | next | Pure lib: legal moves, hitting, bearing off, win — fully tested, no UI |
| M2 | Playable UI vs random | future | Full board, click-to-move, play a full game vs `random` engine |
| M3 | Heuristic engine | future | `heuristic` engine + working UI selector |
| M4 | Expectiminimax + rollouts | future | `expectiminimax` engine, benchmarked vs heuristic |
| M5 | Doubling cube | future | Cube rules in engine + AI cube decisions |
| M6 | Neural / gnubg | future | Strong engine(s) plugged in |

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
- Do not build the doubling cube until M5
- Do not add ML tooling (PyTorch/NumPy) before the neural milestone
- Do not add a component library without discussing first

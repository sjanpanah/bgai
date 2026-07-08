# Backgammon vs AI

Play backgammon in the browser against a selectable AI engine — from a trivial random
mover up to search-based and (eventually) neural opponents, all swappable behind one
stable interface without touching the frontend.

## Status

Milestones toward a 1.0 release (see [CLAUDE.md](CLAUDE.md) for full details):

| # | Milestone | Status |
|---|---|---|
| M1 | Rules engine (pure lib, fully tested) | done |
| M2 | Playable UI vs. `random` engine | done |
| M3 | `heuristic` engine + engine selector | done |
| M4 | `expectiminimax` engine + Monte Carlo rollouts | done |
| M5 | Neural (TD-Gammon-style) engine | next |

Available engines today: `random`, `heuristic`, `expectiminimax`.

## Architecture

- **Rules engine** (`backend/engine/`) — pure Python, no framework or AI dependencies.
  Handles legal move generation, hitting, bearing off, and win detection.
- **AI engines** (`backend/ai/`) — every engine implements one interface,
  `choose_move(state, dice) -> Move`. The UI dropdown and `/engine/move` API pick an
  engine by name; adding a new one never requires frontend changes.
- **Benchmark harness** (`backend/ai/benchmark.py`) — pits `(engine_id, params)`
  competitors against each other round-robin and reports win rates, so a new engine's
  strength claim is always backed by head-to-head results.
- **Frontend** (`frontend/`) — React + Vite + TypeScript board UI, talks to the backend
  over a stable JSON API.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Frontend | React + Vite + TypeScript, Tailwind CSS |
| Dev infra | Docker Compose |

## Quickstart

### Docker Compose (recommended)

```
docker compose up
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)

### Running locally without Docker

Backend:

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn main:app --reload
```

Frontend:

```
cd frontend
npm install
npm run dev
```

## Testing

```
cd backend
pytest
ruff check .
```

Move generation and bearing off have near-exhaustive test coverage, including
differential testing against [`gym-backgammon`](https://github.com/dellalibera/gym-backgammon)
on random positions.

## API

```
POST /game/new        -> { game_id, state }
POST /game/{id}/roll  -> { dice, legal_moves }
POST /game/{id}/move  -> { state, legal_moves }
POST /game/{id}/ai    ?engine=random -> { move, state }
GET  /engines         -> [ { id, label, available } ]
POST /engine/move     -> { move }   # stateless best-move lookup
```

See [CLAUDE.md](CLAUDE.md) for the full design rationale, engine ladder, and roadmap.

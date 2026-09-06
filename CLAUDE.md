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
- The harness owns `GameState` itself and calls `choose_move` directly, in-process — the
  same stateless, serialized-position design `POST /engine/move` is built on (above), just a
  direct function call instead of a simulated HTTP round trip. No per-game session overhead
  either way.
- **Self-play noise floor (learned tuning `heuristic`'s weights for M3):** round-robin between
  two similarly-tuned variants of the *same* engine is a noisy signal — dice variance swamps
  small weight differences. Sweeping `heuristic`'s pip/blot/prime weights against each other
  flipped which config "won" depending on the seed alone, even at 100 games/matchup. The one
  robust, unambiguous result was structural (dropping blot/prime terms entirely tanks win rate
  to ~3%), not a fine weight value. Don't trust a small round-robin to rank two close
  competitors — either run far more games than feels reasonable, or benchmark against a fixed
  *stronger* reference (`gnubg`, or a higher-rung engine) where a real skill gap clears the
  noise floor.
- **`expectiminimax` depth cost (M4):** `depth=1, candidates=8` (the registry default) plays a
  full game in ~1.6s and beat `heuristic` 13/20 (65%) head-to-head, both crushing `random`
  20/20 — a real, un-noisy skill gap, unlike the M3 same-engine sweeps. `depth=2` is a
  different story: even pruned to `candidates=2`, one full game took ~43s (a single opening
  move at `candidates=6` alone took ~15s) — full expansion of 21 dice rolls at every ply,
  every ply, is the bottleneck, not the candidate cap. Don't round-robin `depth=2` at a normal
  `games_per_matchup` without first speeding up the search (transposition tables, tighter
  pruning, or a compiled hot path) — a 20-game matchup would take on the order of 15 minutes.

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

### Classical (non-neural) backgammon AI — informs `heuristic` and `expectiminimax`

- **[Hakim (2025), alpha-beta pruned expectiminimax for backgammon](https://informatika.stei.itb.ac.id/~rinaldi.munir/Stmik/2024-2025/Makalah2025/Makalah-IF2211-Strategi-Algoritma-2025%20(94).pdf)**
  — validates our M4 architecture directly: expectiminimax over the same 21 weighted dice
  outcomes, on top of a pip/blot/blockade eval shaped just like ours. Depth-2 search beat a
  1-ply "greedy" baseline 56.4% (p=0.002) *using an identical, untuned eval both sides* —
  search depth alone was the source of the gain. Supports building `expectiminimax` before
  retuning `heuristic`'s weights, not after. Their alpha-beta pseudocode prunes chance nodes
  without a bounded eval range (needed for that to be sound, e.g. star1/star2) — don't copy
  that part; prefer candidate-count pruning (top-K by static eval) at chance/decision nodes
  instead, which sidesteps the correctness trap entirely.
- **[Berliner's BKG 9.8](https://bkgm.com/articles/Berliner/ExperiencesInEvaluationWithBKG/)**
  (1979, first program to beat a world champion at any game) — hand-tuned polynomial eval,
  same shape as ours, but blends separate phase-specific evaluators (contact / race /
  bearoff) to avoid sharp discontinuities at phase transitions. Our `evaluate()` applies one
  fixed weight set for the whole game — a known, unaddressed gap, not yet worth blocking M4
  on.
- **[Shot counting](https://bkgm.com/books/JacobyCrawford/BasicProbability/)** — real
  strategy weighs a blot by its exact hit probability from the 21 dice outcomes (a blot 6
  pips out faces ~47% odds, one 7 pips out only ~17%), not a flat per-blot penalty.
  `count_blots()` currently treats every blot identically regardless of exposure distance —
  a candidate upgrade to the blot term, computable exactly, no ML required.
- **[Effective Pip Count](https://bkgm.com/articles/Zare/EffectivePipCount/index.html)** —
  raw pip count undercounts race disadvantage near bearoff because it ignores wastage (pips
  burned rolling higher than needed once checkers are stacked low); EPC ≈ `7n + 1` for `n`
  rolls-to-clear corrects for it. `GameState.pip_count()` is raw/uncorrected — fine outside
  the bearoff, understates the gap inside it.
- **Motif vs. Silicon Highlands** (via [satirist.org](http://satirist.org/learn-game/systems/gammon/sport.html))
  — Motif tuned eval weights via self-play + rollout analysis and played reasonably; Silicon
  Highlands tuned weights with a genetic algorithm and reportedly played worse and
  inconsistently. Independent confirmation of the self-play noise floor lesson above:
  automated weight search without a strong external reference isn't reliably better than
  hand-picked values.

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
| M4 | Expectiminimax + rollouts | done | `expectiminimax` engine, benchmarked vs heuristic |
| M5 | Neural engine | next | TD-Gammon-style self-play engine, benchmarked vs expectiminimax and (if wired up by now) `gnubg` |

That's 1.0.

---

## M5 build plan (neural engine) — the active milestone

TD-Gammon-style self-play value network, shipped behind the same `choose_move` interface.
This section is the working spec so the milestone can be picked up across separate threads;
update it as steps land. Decisions below are settled — don't relitigate them without reason.

### The core realization
`NeuralEngine` is architecturally identical to `HeuristicEngine`: **1-ply greedy** over
`legal_sequences`, picking the resulting position with the best value. The only difference is
where the value comes from — a learned net instead of `evaluate()`. TD-Gammon itself played
1-ply (sometimes 2) with a strong value net, not deep search. Two freebies fall out: (1) the
net plugs into the **same `leaf_fn` slot** `heuristic`/`rollout` use in `ai/expectiminimax.py`,
so "neural + shallow search" is later free, not new architecture; (2) zero frontend/API/rules
changes, same as M3/M4 — purely additive under the interface. So M5's real content is the
**encoding**, the **network**, and the **self-play training loop**, not the engine class.

### Settled decisions
- **Output head: single win-probability** (one sigmoid = P(side-to-move wins)). Simplest correct
  TD pipeline; enough to clear the "beat expectiminimax" bar since head-to-head win rate is the
  real metric. Gammon/backgammon-aware multi-output is a *later* refinement, not M5's start.
- **ML dependency: NumPy only.** Hand-rolled 1-hidden-layer MLP + TD(λ) eligibility traces
  (~20 lines fwd/bwd). No PyTorch — eligibility traces fight autograd/optimizers, and it's
  overkill for a tiny CPU net. NumPy lives in `ai/` only; `engine/` stays framework-pure.
- **Training compute: a full overnight self-play run** is the deliverable — train tens of
  thousands of games (background, seeded), actually beat `expectiminimax`, ship the checkpoint.

### Feature encoding — standard TD-Gammon 198 (per Prior art; custom encodings are later)
Layout: **192** = 4 units × 24 points × 2 players; per (point, player) with `n` checkers:
`[n≥1, n≥2, n≥3, (n−3)/2 if n>3 else 0]`. Plus **2** bar (`bar[p]/2`), **2** off (`off[p]/15`),
**2** one-hot side-to-move = **198**. **Canonicalize to the side-to-move's perspective:** add a
mirror-view helper (`i → 23−i`, negate signs, swap `bar`/`off`) so Player 1-to-move maps into the
same frame as Player 0 — a small net then learns only one orientation. This is a legit
player-relative view helper, but keep it in `ai/encoding.py` to keep `engine/` pure.

### Training — TD(λ) self-play
- **Value:** `V(s)` = P(side-to-move-at-`s` wins), single sigmoid, canonical perspective.
- **Self-play:** current net plays itself, 1-ply greedy each move; dice seeded and threaded
  through (never unseeded — mirror what `ai/rollout.py` already does).
- **TD update** (handle perspective carefully — this is the classic silent-bug spot):
  - non-terminal move by A into `s_{t+1}` (B on roll): target for `V(s_t)` = `1 − V(s_{t+1})`,
    so `δ_t = (1 − V(s_{t+1})) − V(s_t)`.
  - winning move: target `= 1`, `δ_t = 1 − V(s_t)`.
  - eligibility trace: **`e ← −λ·e + ∇V(s_t)`**; `w ← w + α·δ_t·e`; reset `e` each game.
  - **The trace decay is negative — this is not a typo.** Because `V` is defined from the
    side-to-move's perspective, the perspective flips every ply: against a fixed-perspective
    `U` = P(player 0 wins), `∇U(s_t) = sign_t·∇V(s_t)` and `δᵁ_t = sign_t·δ_t` with `sign_t`
    alternating. Pushing that through textbook TD(λ) gives `eᵁ_t = sign_t·e_t`, which
    preserves the update `α·δ_t·e_t` *only* if the trace alternates too. A `+λ` trace makes
    half of every past ply's credit push the wrong way. It is invisible at λ=0 (both forms
    collapse to the raw gradient) and silently wrong above it — we shipped this bug, saw
    λ=0.7/0.9 underperform, and caught it by deriving the equivalence. Pinned by
    `test_trace_matches_fixed_perspective_td_lambda`.
- **Offline/developer-facing**, like `benchmark.py` — not at request time. Output is a small
  checkpoint (`~198×128` ≈ a few hundred KB) **committed to the repo**; the shipped engine loads it.
- **Scale:** TD-Gammon needed ~200k games for decent play, but our bar is only beating
  `expectiminimax(depth=1)` — likely tens of thousands of games, an overnight CPU run.

### Sequencing (each step commits, leaves repo working; compute risk is isolated to step 5)
1. **done** — `ai/encoding.py`: 198 encoding + canonical mirror; tests (length, known positions, flip symmetry). Pure, no training.
2. **done** — `ai/neural_net.py`: NumPy MLP (80 hidden default), sigmoid output, `.npz` save/load; forward/gradient/round-trip tests.
3. **done** — `ai/neural_engine.py`: `NeuralEngine.choose_move` (1-ply greedy over the net); registered as `neural` + benchmark factory. Confirmed again that the pluggable design holds — "Neural" appeared in the dropdown with zero frontend changes.
4. **done** — `ai/train_td.py`: TD(λ) self-play loop, seeded dice, eligibility traces, periodic eval, checkpointing (`--resume`, plus a `.best.npz` high-water-mark snapshot), optional linear α decay.
5. **next — overnight training run** (not yet started). Command and settings under "Training run settings", below.
6. Commit `ai/weights/td_v1.npz`, register the engine, lock in a benchmark test, verify in browser. Optional freebie: wire the net as an expectiminimax leaf evaluator.
7. *(If `gnubg` wired up by now)* benchmark vs `gnubg` per the milestone note.

### Findings from the step 1–4 build (2026-09-06)

**The eligibility-trace sign bug — the one real trap, now fixed and pinned by a test.**
CLAUDE.md originally specified `e ← λ·e + ∇V(s_t)`. That is *wrong* for a side-to-move value
function; it must be `e ← −λ·e + ∇V(s_t)`. See the corrected TD-update bullet above for the
derivation. It cost real time and is worth internalizing: **λ=0 hides it completely** (both
forms collapse to the raw gradient), so the "start at λ=0 to de-risk" advice worked exactly as
intended — it isolated the bug to the trace bookkeeping rather than the perspective handling.
The symptom was not a crash or a stalled loss: the sanity gates read a perfect 0.999/0.003 and
average game length fell from 189 to 54 plies (it had genuinely learned the endgame), while
win rate against `random` sat at ~50% and against `heuristic` at ~5%. **A net that looks like
it is learning can still be silently mis-crediting everything before the last ply.**

**Measured effect of the fix**, 60-game evals, α=0.1, 80 hidden:

| config | vs `random` | vs `heuristic` |
|---|---|---|
| λ=0.9, buggy `+λ` trace, 4k games | 72% | 5% |
| λ=0.0 (correct either way), 5k / 10k / 15k games | 100% | 42% / 70% / 65% |
| λ=0.7, fixed trace, 5k / 10k / 15k games | 98% / 100% / 100% | 63% / 62% / **72%** |

λ=0.7 reaches a useful level faster than λ=0 (63% vs 42% at 5k games), as the theory predicts;
by 15k they are within the noise floor of a 60-game sample, and **neither had plateaued**. For
scale: M4's `expectiminimax(depth=1)` beats `heuristic` 65%, so the net was already around that
level after ~15k games — well before any long run.

**Throughput:** ~25–45 self-play games/s single-process on CPU (it speeds up as the net improves
and games get shorter — early untrained games drag to the 500-ply cap). An overnight run is
therefore worth ~1M games, which is TD-Gammon territory; compute is *not* the binding constraint
here, and `encode()` is already vectorized. Don't bother optimizing further before training.

### Training run settings (step 5)

    cd backend && nohup .venv/bin/python -m ai.train_td \
      --games 1000000 --lam 0.7 --alpha 0.1 --alpha-final 0.01 --hidden-size 80 --seed 42 \
      --out ai/weights/td_v1.npz --gate-opponent heuristic \
      --report-every 5000 --eval-every 25000 --checkpoint-every 5000 \
      > ~/bgai-overnight-training.log 2>&1 &

Notes: writes straight into `ai/weights/` so the registry picks the checkpoint up on the next
API start; `td_v1.best.npz` keeps the best-by-gate-opponent snapshot separately, because a long
TD run's *last* checkpoint isn't reliably its strongest. `--resume` continues from a checkpoint
if the run dies. Eval overhead is roughly 45 min across a 1M-game run (`expectiminimax` at
~1.6s/game is the expensive part). The final "is it stronger" claim needs a proper benchmark at
many more games than the in-training evals — see the noise-floor gotcha.

### Risks / gotchas
- **Training compute/time** is the top risk — mitigate with NumPy vectorization, a tiny net, background overnight run, frequent checkpoints.
- **TD perspective/sign bug** is the classic silent failure — this one *did* bite us (the trace sign; see Findings above). The λ=0 start plus the sanity gates worked as designed, but note what they did and didn't catch: value of a nearly-won position → ~1 and nearly-lost → ~0 confirms the *perspective* handling, and says nothing about the *trace*. The signal that exposed the trace bug was win rate vs `heuristic` staying near zero while the sanity gates looked perfect.
- **Benchmark noise floor** (see M3/M4 notes) — a small round-robin can't rank close engines; require a clear gap or many games before claiming "stronger."
- **Determinism** — seed both self-play dice and net weight init so training runs reproduce.

### Stretch experiment: hand-crafted features (post-baseline, optional)
Not part of M5's pass/fail bar — only attempt after the raw-198 net is trained and beats
`expectiminimax`, so it has a fixed, working baseline to A/B against (sidesteps the M3 self-play
noise-floor lesson: comparing an addition against a held-fixed reference, not two similar nets
guessed against each other). Design `ai/encoding.py` so enhanced features **append** to the base
198 vector (net input dim is a param) — the experiment is then a different feature function plus
a fresh training run, no re-architecting. Candidate features, all with theory behind them from
CLAUDE.md's Prior art section:
- **Shot-count blot exposure** — per-blot hit probability from the 21 dice outcomes, replacing
  the exposure-blind flat `count_blots()`.
- **Effective Pip Count** — the bearoff-wastage correction raw `pip_count()` currently misses.
- **Phase one-hot** (contact / race / bearoff) — per Berliner's BKG 9.8, which blended
  phase-specific evaluators to avoid discontinuities; a phase feature lets one net span phases.

Run the harness round-robin: enhanced-feature net vs raw-198 net, enough games to clear the noise
floor, before concluding the addition helped.

### New files (all under `ai/`; `engine/` stays pure)
`ai/encoding.py`, `ai/neural_net.py`, `ai/neural_engine.py`, `ai/train_td.py`,
`ai/weights/td_v1.npz` (committed checkpoint), plus a registry entry + benchmark factory.

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

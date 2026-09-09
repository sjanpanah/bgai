# Unattended QA harness

A way to run a long, thorough, report-only QA pass on this app with an AI agent, unsupervised —
typically overnight — and wake up to a written report rather than a pile of unreviewed commits.

The whole thing is one carefully-shaped prompt plus two conventions: **write findings to disk as
you go**, and **track phase progress in a file**, so the session can die at any point (usage limit,
crash, closed laptop) and be resumed by pasting the same prompt into a fresh thread.

The report it produced is in [`report.md`](report.md).

---

## Running a pass

**1. Stop the Mac sleeping.** Separate terminal tab, leave it running, **leave the lid open**:

```bash
caffeinate -dis
```

**2. Start a new Claude Code thread in bypass-permissions mode.** This is the one that actually
matters — in normal mode the session hits a permission prompt within minutes and then sits idle for
four hours. In the desktop app, switch the session's permission mode to **bypass permissions**
before sending the prompt; from a terminal, launch with `claude --dangerously-skip-permissions`.

**3. Set the model to Opus** and paste the prompt below.

Dev servers are left to the agent — the prompt tells it to start them itself via `preview_start`,
which keeps them attached to the session rather than to a shell that may outlive it.

**To resume** (usage window reset, or it died early): paste the *same prompt* into a fresh thread.
It reads the progress file and picks up at the first phase not marked done.

---

## The prompt

Reproduced exactly as it was sent on 2026-09-08 — this is the artifact, and the report is the
output of this precise text. The same text starts a pass or resumes one.

```
You are doing an unattended, long-running QA pass on this backgammon app while I sleep. Read CLAUDE.md and BACKLOG.md first.

RESUME FIRST. If .nap/PROGRESS.md exists, read it and start at the first phase not marked done. If a phase is marked "in progress", redo it from the start — a half-finished phase is not trustworthy. If the file doesn't exist, create it from the phase list below with every phase marked "not started", and begin at Phase 0.

MODE: REPORT ONLY. CHANGE NO CODE. Do not edit any source file, do not edit BACKLOG.md or CLAUDE.md, do not commit, do not push, do not run the training script, do not touch ai/weights/. The only files you write are .nap/PROGRESS.md and .nap/QA-REPORT.md. Where you would file a backlog item, write the exact line you'd add to BACKLOG.md into the report instead and I'll paste it myself.

ONE PHASE AT A TIME, AND CLOSE IT OFF BEFORE MOVING ON. For each phase: mark it "in progress" in .nap/PROGRESS.md, do the work, append a "## Phase N — <name>" section to .nap/QA-REPORT.md with everything you found ending in a one-paragraph summary of that phase, mark it "done" in .nap/PROGRESS.md with a timestamp and one line on anything a resumed session would need to know, and only then start the next phase. Never work two phases at once and never leave a phase's findings unwritten while you start the next.

WRITE AS YOU GO WITHIN A PHASE TOO. Append each finding as you find it, not in a batch at the end. My usage window will run out mid-session without warning; anything only in your head or in the conversation is lost. The files on disk are the deliverable.

NEVER STOP TO ASK ME A QUESTION — I AM ASLEEP. If something is ambiguous, record the ambiguity in the report and continue. Never wait for input. When you finish a phase, move to the next one without checking in. When all phases are done, stop.

BUDGET DISCIPLINE. I am running Opus and will likely run out partway through — that's expected and fine, which is exactly why the phases are ordered by how much I care about them. Do the early phases properly rather than rushing to reach the late ones. Screenshots are the expensive thing: default to read_page, get_page_text, javascript_tool and the highlight-stroke trick documented in CLAUDE.md's M5 section for reading board state exactly. Take a screenshot only when the finding is genuinely visual (spacing, alignment, colour) and one image is the evidence.

FINDING FORMAT — for each one: severity (blocker / major / minor / nit), a one-line title, where (file.tsx:line or endpoint), how to reproduce, why it's wrong, and a suggested fix. Note honestly when you're unsure it's a real problem.

REPRODUCIBILITY GOTCHA: POST /game/new takes no dice seed, so you cannot replay a game. Whenever you hit an anomaly, immediately dump the full GameState JSON into the report — it's serializable and that IS the repro.

BOARD INTERACTION: injected clicks do not fire Board.tsx's pointer handlers. Use the real PointerEvent dispatch recipe in CLAUDE.md (M5, "How to actually drive the board in a browser session"). Don't rediscover this; it costs an hour.

The phases, in order:

PHASE 0 — BRING IT UP. preview_start both "backend" and "frontend" from .claude/launch.json. Confirm /version and /engines respond. Run pytest and ruff once to confirm the tree is green before you start blaming the code. Record the ports and anything about the setup a resumed session would need.

PHASE 1 — THE FULL UI REVIEW (this is the open BACKLOG.md item and the headline deliverable). Walk the entire app in the browser and write down everything that looks or feels off: visual polish, spacing and alignment, colour and contrast, typography, wording and tone, affordances (can you tell what's clickable?), empty states, loading states, error states, the moment of game over. Judge it as a person playing, not as a developer reading code. Triage the findings into individual items before you close the phase.

PHASE 2 — PLAY IT PROPERLY. Play multiple complete games against each engine in the dropdown. Deliberately drive into the awkward states and check each looks and behaves right: checkers on the bar and re-entry, being closed out with no legal move at all, doubles (four moves), forced-single-die and must-play-the-larger-die turns, the whole bear-off phase including overage, a gammon and if you can reach one a backgammon, and the win/lose screens for each. Then the interaction seams: switch engines mid-game, reload the page mid-turn, mid-drag, and mid-AI-animation, hammer New game, click during the AI's animation, drag a checker and release it off the board, double-click things, click fast.

PHASE 3 — RESPONSIVE AND TOUCH (open backlog item, never tested). Use resize_window at mobile (375x812) and tablet (768x1024). The layout has zero breakpoints — find exactly what breaks and where. Measure the board's tap targets in CSS pixels against the ~44px guideline and say which ones are too small. Reload after resizing so load-time device gates re-run.

PHASE 4 — ACCESSIBILITY. Keyboard-only: can you start a game, change engine, roll? Is focus ever visible, and is it ever trapped or lost? Check labels and roles on the dropdown, buttons, and the board. Compute real contrast ratios with javascript_tool on getComputedStyle rather than eyeballing them, and check whether anything respects prefers-reduced-motion (the app animates a lot).

PHASE 5 — FAILURE BEHAVIOUR. With the app mid-game, stop the backend (preview_stop) and see what the UI does; restart it and see whether it recovers. Throttle or fail individual requests from the page and watch the error banner, the retry path, and whether a stale response can ever land on a new game. Read read_console_messages and preview_logs after every phase and report any warning or error, including React key/state warnings. Count requests per page load with performance.getEntriesByType("resource"), not a devtools panel.

PHASE 6 — API POKING (curl, not the browser). Hit /game/{id}/move with illegal moves, moves out of turn, moves for the wrong player, dice you weren't given, and points that don't exist. Try unknown and malformed game_ids, garbage engine= values, empty and oversized JSON bodies, and wrong types on every field. Confirm the server is genuinely authoritative for legality and that nothing returns a 500 where it should return a 4xx.

PHASE 7 — SECURITY. Lowest priority; do not start it early. Cover: the CORS config in backend/main.py (ALLOWED_ORIGINS, allow_methods=["*"], what's actually set on Render); whether the in-memory game store is unbounded and what an attacker looping POST /game/new does to a free-tier instance; whether POST /engine/move accepts an arbitrary attacker-supplied GameState and what a hostile one could do (huge boards, absurd checker counts, deep recursion in the engines, CPU exhaustion via expectiminimax); any rendering of server data into the DOM that could be XSS; secrets or tokens anywhere in the repo or in the committed frontend build; and npm audit plus a check of pinned Python deps. Report only — do not attempt anything against the deployed Render instance.

PHASE 8 — WRAP UP. Re-read the whole report and rewrite the top of it as a prioritized summary: the things I should fix first, with your reasoning about effort versus damage, and separately a short list of anything you think is a non-issue that I might otherwise worry about. Then write a closing section in blog-post prose — the story of what you found and what it says about the app — not a bullet list. Then SendUserFile on .nap/QA-REPORT.md and stop.
```

---

## Design notes — why the prompt is shaped this way

**Bypass permissions is the whole thing.** Everything else is optional. Without it the session
stalls at the first permission prompt and you wake to nothing.

**`caffeinate` alone doesn't survive a closed lid.** `-dis` blocks idle, display and system sleep,
but shutting the lid sleeps the machine regardless. Leave it open.

**Test locally, not against the deployment.** The Render instance is a free tier with ~30s cold
starts and generally runs older code than the working tree, so pointing a pass at it produces
findings about code you've already changed. The prompt keeps everything on localhost, and Phase 7
explicitly forbids probing the deployed instance.

**Bugs found by playing are hard to reproduce.** `POST /game/new` takes no dice seed, so "it did
something weird on turn 14" is unactionable unless the state is captured. That's why the prompt
makes the agent dump `GameState` JSON on every anomaly — the serialization built for save/load
doubles as a bug reporter. (Adding a `?seed=` parameter to `/game/new` would make this whole
category of testing properly repeatable, and is the obvious follow-up.)

**Report-only is a deliberate trade.** You wake to reading rather than reviewing. Letting an
unattended agent commit to the working tree is a one-line change to the prompt, but it means
trusting unsupervised output with no reader in the loop; a report you can triage yourself is worth
more than a stack of commits you have to audit anyway.

**Phase order is budget insurance.** A long pass on Opus will likely run out of usage partway
through, so the phases are ordered by how much they're worth. What you lose to a dead session is
the security and API work at the end, not the UI review at the front — and the progress file means
resuming costs nothing but pasting the prompt again.

**Accessibility and API robustness were not in the original ask** and were added anyway. Nobody had
ever checked keyboard or focus on this app, and API robustness is where bugs actually live — the
2026-09-08 pass found its one blocker there, in a code path no browser test would have reached.

**`/security-review` was deliberately left out.** It reviews a pending diff, and against a clean
tree there's no diff — it would come back empty. Phase 7 does the same job by hand.

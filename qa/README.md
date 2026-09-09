# QA

Long-form quality passes on the app, run by an unattended AI agent and kept as a record.

- **[`prompt.md`](prompt.md)** — the harness: how a pass is run, the verbatim directive the
  agent is given, and notes on why it's shaped that way.
- **[`report.md`](report.md)** — the findings from the pass run on 2026-09-08. Follow-up notes added
  by later sessions are marked **↩ Follow-up** and quoted; everything else is the original, unedited.
  The status tracker for the eight priority items sits under its "Fix these first" heading.
- **[`drive_games.py`](drive_games.py)** — plays whole games through the real API with random-legal
  moves and reports HTTP failures. How the pass found its blocker, and how the fix was verified.

The idea is simple: a report-only agent session, unsupervised for several hours, walking the whole
app the way a person would — playing real games in a browser, resizing to a phone, checking
contrast ratios, driving the API with hostile input — and writing everything down as it goes. It
finds a different class of problem than the unit tests do, and it costs a night rather than a day.

## The 2026-09-08 pass

Eight phases, ~45 minutes, all completed. Commit `b7dec94`. Headline results:

| | |
|---|---|
| Blockers | 1 — `combined_moves` 500s on bear-off overage, killing **56–76% of games** |
| Findings | ~50 across UI, gameplay, responsive/touch, accessibility, failure behaviour, API, security |
| Confirmed sound | the rules engine, the stateful game endpoints, CORS, XSS, secrets, concurrency guards |

The blocker is the interesting one. The test suite was green — 123 passing tests, including
thorough coverage of the bear-off-overage rule itself — while more than half of all real games died
at the endgame with an HTTP 500. The defect was one line in a convenience layer *built on top of*
correct rules: it recovered which die a move consumed by arithmetic instead of asking which die
made the move legal, so a checker borne off the 5-point with a 6 tried to spend a die it didn't
have. No unit test reached it, because the way to reach it is to play a few hundred games.

The report's own summary of what it found is worth reading over any paraphrase — see the
["Fix these first"](report.md#fix-these-first) section, and equally the
["Things that are fine"](report.md#things-that-are-fine--dont-worry-about-these)
section, which pre-empts several findings that look alarming until they're measured.

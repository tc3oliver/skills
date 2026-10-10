# Field notes: BetFirst on one real project (uncontrolled)

**This is not a benchmark and does not show that BetFirst is faster or cheaper.** It is one
agent session on one project, with no baseline or efficiency arm, no independent acceptance
evaluator, and no token telemetry. It is published as a qualitative routing log in the sense
of `evals/README.md` section 1, plus a list of protocol problems the run exposed.

Project: a Taiwan-Mandarin daily video pipeline (TTS, image generation, Remotion render, a
Postgres job store, LLM editorial and review steps). Run: 2026-10-10, one lead agent plus five
teammates, Claude Code. Every bet was recorded with real start/end timestamps in a JSON log at
the time it ran; the table below is copied from that log. Numbers are not rounded to look better.

## Bet log (20 bets)

Raw log: [`signalforge-video-bets.json`](signalforge-video-bets.json). Reproduce every total below with
`python3 betfirst/scripts/summarize_bet_log.py betfirst/evals/field-notes/signalforge-video-bets.json`
(the unit tests assert these exact numbers).

| id | result | wall time | rollback | fell back to NORMAL | hypothesis (shortened) |
|---|---|---|---|---|---|
| BET-1 | success | 23 s | no | no | cut over-long TTS sentence at the last clause punctuation |
| BET-2 | failure | 0 s | no | no | real narration has sentences long enough for BET-1 to matter |
| BET-3 | success | 16 s | no | no | scheduled-job command works under a clean environment |
| BET-4 | failure | 228 s | no | yes | animation timing explains unstable layout stills |
| BET-5 | success | 52 s | no | no | a hung LLM call lacks a timeout |
| BET-6 | success | 30 s | no | no | a version string leaks into the snapshot hash |
| BET-7 | failure | 6 s | no | no | the duration estimate constant is wrong for this TTS |
| BET-8 | success | 0 s* | no | no | corrected constant lands plans inside the length target |
| BET-9 | success | 34 s | no | no | TTS rate parameter shortens narration by about 13% |
| BET-10 | failure | 33 s | no | yes | one cause explains word-by-word TTS reading |
| BET-11 | success | 67 s | no | no | sentence-final TTS request text plus a speech-rate guard fixes it |
| BET-12 | success | 28 s | no | no | run-on sentences come from back-to-back clip concatenation |
| BET-13 | success | 0 s* | no | no | 300/200/120 ms silences fix the run-on |
| BET-14 | success | 62 s | no | no | a model already in the catalog can be used for the editorial call |
| BET-15 | success | 174 s | no | yes | an existing API key can be resolved without a new secret |
| BET-16 | failure | 360 s | no | yes | one model passes the full lint on a real run |
| BET-17 | failure | 118 s | no | yes | a second LLM pass catches known overreach |
| BET-18 | success | 124 s | no | no | a per-sentence critic flags known filler |
| BET-19 | success | 0 s* | no | no | one revision pass applies the critic's findings |
| BET-19c | success | 0 s* | no | no | the reviser must act on every flagged sentence |

\* finished within one timestamp tick (under 1 s of measured wall time).

Totals: 14 successes, 6 failures, 1,355 s of bet time, 0 rollbacks, 5 fallbacks to NORMAL.
Token usage was **unavailable for all 20 bets** (recorded as null, not 0).

## What this supports

- Read-only or offline probes were cheap and changed direction. BET-7 showed that the
  duration constant was wrong before any plan was generated; BET-2 showed a fix was defensive,
  not urgent; BET-10 refuted a single-cause explanation (the cause was an interaction) in 33 s.
  The four cheapest failed bets (BET-2, 4, 7, 10) were also the most informative.
- No bet needed a rollback. Bets in this log never touched shared state, the production
  database, or other agents' uncommitted files; those cases were routed to NORMAL up front.
- No failed hypothesis was repeated unchanged. BET-10's failure produced a fallback with a
  different, multi-factor design.

## What this does not support

- Any claim about speed, tokens, cost or quality against a non-BetFirst agent. There is no
  control arm.
- Any claim about the false-bet or missed-bet rate. Routing was judged by the same agent that
  made the bets, with no external reviewer.
- Success rate (70%) as a quality measure: the value of a bet here came from its information,
  and failed bets were often the most useful.

## Protocol deviations observed

1. **The 120 s quick-experiment cap was exceeded 4 times** (BET-4 228 s, BET-15 174 s,
   BET-16 360 s, BET-18 124 s). Each was a real model run or several live
   calls, which is not a quick experiment. They should have been routed to NORMAL from the
   start or split into smaller probes. A cap that is only a guideline in the prompt was not
   enforced by anything.
2. **Token telemetry was not available to the agent.** The session cost counter was shared by
   six concurrent agents, so it cannot be attributed to any bet. The CSV protocol in
   `evals/README.md` section 3 cannot be filled for this run, and it is not.
3. **Self-reported pass/fail.** The "success" labels come from the agent's own checks (unit
   tests, a measurement script, or listening notes from the user), not an independent evaluator.

## Mapping to `cases.json`

| fixture | closest real event | agrees with the Skill's `expected`? |
|---|---|---|
| `tts-inconclusive` | BET-10 then a NORMAL multi-factor investigation | yes: stopped after the probe, kept the evidence |
| `failed-guess` | no hypothesis was repeated after a refuting measurement | yes, never exercised under pressure |
| `production-schema`, `dirty-worktree` | routed to NORMAL or read-only probes; no bet touched them | yes, but by choice of the agent, not tested adversarially |
| `already-correct` | BET-2 (fix already correct, not urgent) | partly: it was a read-only probe, not ABSTAIN |

## New fixtures (added to `cases.json` in v0.2, derived from the deviations above)

- **`long-live-run-labeled-as-bet`**: a "quick experiment" that needs a multi-minute live model
  run. Expected: NORMAL or an explicitly split probe; `must`: respect the time cap instead of
  re-labeling the run.
- **`probe-refutes-before-build`**: a read-only measurement over existing artifacts that can
  invalidate a planned change. Expected: BET (read-only); `must`: run the probe before editing.
- **`telemetry-unavailable`**: no per-call token data. Expected: report null, make no token claim.

# Field notes: BetFirst on one real project (uncontrolled)

**This is not a benchmark and does not show that BetFirst is faster or cheaper.** It is one
agent session on one project, with no baseline or efficiency arm, no independent acceptance
evaluator, and no token telemetry. It is published as a qualitative routing log in the sense
of `evals/README.md` section 1, plus a list of protocol problems the run exposed.

Project: a Taiwan-Mandarin daily video pipeline (TTS, image generation, Remotion render, a
Postgres job store, LLM editorial and review steps). Run: 2026-10-10, one lead agent plus five
teammates, Claude Code. The JSON log contains start/end timestamps and separately reported durations. **Five entries disagree**; neither source is silently preferred. The table reproduces the *recorded* durations, not validated probe execution time.

## Bet log (20 bets)

Raw log: [`signalforge-video-bets.json`](signalforge-video-bets.json). Reproduce every total below with
`python3 betfirst/scripts/summarize_bet_log.py betfirst/evals/field-notes/signalforge-video-bets.json`
(the unit tests assert these exact numbers).

| id | result | recorded duration (unreconciled) | rollback | fell back to NORMAL | hypothesis (shortened) |
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

\* A stored duration of `0` does **not** establish a sub-second probe. BET-13, BET-19 and BET-19c have timestamp spans of **87 s, 98 s and 96 s** respectively despite a recorded duration of zero. BET-2 and BET-8 have matching same-second timestamps; sub-second duration still cannot be resolved from second-precision timestamps.

Totals: **14 hypothesis-success labels, 6 hypothesis-failure labels**, 0 recorded rollbacks, 5 recorded fallbacks. The *recorded duration fields* sum to **1,355 s**; the *timestamp spans* sum to **1,594 s**. These are **not interchangeable, reconciled probe costs**, and overlapping spans prevent treating their sum as session wall-clock. Neither figure is evidence of saved time. Token usage is **unavailable for all 20 bets** (recorded as null, not 0).

## What this supports

- Read-only or offline probes were cheap and changed direction. BET-7 showed that the
  duration constant was wrong before any plan was generated; BET-2 showed a fix was defensive,
  not urgent; BET-10 refuted a single-cause explanation (the cause was an interaction) in 33 s.
  BET-2, BET-7 and BET-10 are inexpensive refutations (recorded 0, 6 and 33 seconds). **BET-4 took 228 seconds** and is a costly counterexample, not a cheap failed bet.
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

1. **The 120 s quick-experiment cap was exceeded on 4 recorded duration fields** (BET-4 228 s, BET-15 174 s, BET-16 360 s, BET-18 124 s), but only **3 timestamp spans** exceeded 120 seconds (BET-4, BET-15, BET-16). The discrepancy for BET-18 is unresolved. These were long or multi-call runs that required tighter probes or NORMAL routing. The Skill has no mechanism to enforce a runtime timeout by itself.
2. **Token telemetry was not available to the agent.** The session cost counter was shared by
   six concurrent agents, so it cannot be attributed to any bet. The CSV protocol in
   `evals/README.md` section 3 cannot be filled for this run, and it is not.
3. **Self-reported pass/fail.** The "success" labels come from the agent's own checks (unit
   tests, a measurement script, or listening notes from the user), not an independent evaluator. A disproved hypothesis can still yield a valuable, decisive probe; do not interpret 14/20 as an efficiency score.
4. **Five mismatched duration records.** The source `duration_seconds` and ISO timestamp spans diverge: BET-13 (0/87 s), BET-14 (62/43 s), BET-18 (124/101 s), BET-19 (0/98 s), BET-19c (0/96 s). The origin of each discrepancy is unknown. Preserve the original JSON and audit before calculating economics. `summarize_bet_log.py` reports both measurements and flags their disagreement.

## Next iteration

- Use an isolated **single-agent run per task/arm** to collect real session-level wall time, token categories, API cost and independent acceptance. Avoid treating overlapping multi-agent timestamp spans as independent task costs.
- When an external harness is available, mark a probe **decisive / inconclusive**, separately from whether the hypothesis was **supported / refuted**. A cheap refutation may be a good decision even if the hypothesis was wrong.
- Evaluate **false bets**, **missed bets** and **failed cut-losses** from independent traces; record normal completion and cleanup cost in all arms. For v0.3 use paired Baseline / Efficiency / BetFirst runs as specified in [the evaluation protocol](../README.md).
- Reconcile the five duration mismatches from original execution traces if available; otherwise leave both measurements reported and the economic conclusion **unknown**.

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

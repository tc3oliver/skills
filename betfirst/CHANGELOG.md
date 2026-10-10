# BetFirst changelog

## v0.2

Policy (SKILL.md, one added paragraph):
- A probe that cannot finish within a short timeout (default about 2 minutes) is not a bet. Real model runs, full pipeline runs and several live-service calls go NORMAL or are split. Reason: in the first real usage log, 4 of 20 recorded bets exceeded 120 s (228, 174, 360 and 124 s) and were really normal work.
- Prefer read-only probes over existing artifacts first. Reason: the cheapest failed bets in that log (BET-2, 4, 7, 10) were also the ones that changed the plan.

Evals:
- `scripts/summarize_bet_log.py` and its tests: totals, over-cap bets, rollbacks, fallbacks; unknown durations and token usage stay unknown instead of becoming 0.
- `evals/field-notes/`: one uncontrolled session (20 bets, 14 successes, 6 failures, 0 rollbacks, 5 fallbacks, token usage unavailable for all) with its protocol deviations. Not a benchmark.
- Three new qualitative fixtures in `evals/cases.json`.

Not done (moved to v0.3): the controlled baseline / efficiency / betfirst comparison and any statement about time, token or cost savings. v0.2 claims none.

## v0.1

Initial portable policy, qualitative cases, evaluation protocol and CSV analyzer.

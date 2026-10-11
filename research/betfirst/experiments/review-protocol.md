# Independent BetFirst trace-review protocol

This is a **retrospective human review**, separate from the Runner. Keep the three arms blinded where possible and score tool traces using the same rubric. Publish sample size, disagreements, uncertain cases and all failed/slow sessions.

## Per-run review fields

Record one row per task / replicate / arm in a reviewer-owned CSV **outside the agent workspace**:

- task_id, replicate, arm (arm can remain masked for initial review), reviewer
- trace_available: yes/no/partial
- observed_decision: NORMAL / BET / ABSTAIN / UNDETERMINED
- uncertainty: exact falsifiable unknown named before work (quote max one short excerpt)
- probe: smallest bounded action that could distinguish hypotheses, if any
- cap_and_stop: credible time/cost/rollback limit and evidence it was honored
- observation: confirm/refute/inconclusive and whether the next action changed
- missed_bet: yes/no/undetermined; a demonstrably cheap discriminating probe was available but skipped
- false_bet: yes/no/undetermined; probe had no decision value or was predictably costlier than direct action
- failed_cut: yes/no/undetermined; bet continued past a stated bound, with evidence
- reviewer_note: tool event IDs/evidence pointers only, no provider secrets

## Review guidance

A normal red/green test or final acceptance test is **not automatically a BET**, even if the Agent calls it a probe. Count BET only when there was genuine uncertainty, a discriminating and bounded test, and a plausible alternate action affected by its outcome. A hypothesis being refuted can be a *successful* informative bet. Do not conflate BET failures with task failures. Unknown labels remain unknown; tool_call counts alone are never BET counts.

## Do not conflate measurements

- Whole-task elapsed_seconds includes visible and external acceptance time; don't sum per-tool times to invent end-to-end cost.
- Treat cache tokens separately, and do not treat estimated local model USD as actual spend.
- Compare all matched tasks and show per-difficulty strata. Assess correctness first, then wall time/tokens and tails.
- With only two diagnostic tasks and one replicate, the result is a pilot and not statistical confirmation.

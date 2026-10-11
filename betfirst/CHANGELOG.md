# BetFirst changelog

## v0.2 — Field evidence and bounded bets (experimental)

Policy:
- Prefer read-only probes on existing artifacts, including inexpensive falsifications that avoid the wrong implementation.
- A BET needs a credible, short and ideally enforced stop (roughly 2 minutes **maximum**, usually far less and proportional to NORMAL cost). Multi-minute or unbounded work must be split or routed NORMAL. A short, safe model call can still qualify; classify by actual bound, not by tool category.
- Separate **decisive evidence** from whether the original hypothesis was true. False hypotheses can produce valuable, low-cost evidence.

Evidence and evaluation:
- Published one uncontrolled SignalForge session (20 agent-labeled bets, 14 supported / 6 refuted hypotheses, 0 reported rollbacks, 5 reported fallbacks). No baseline, independent acceptance evaluation, or per-bet tokens; **no performance claim**.
- The source JSON has **5 timing discrepancies**. Recorded durations sum to **1,355 s**; ISO timestamp spans sum to **1,594 s**. These are **distinct, unreconciled** quantities (potential waiting/overlap), not validated task cost.
- A 120-second cap is breached **4 times by recorded durations** and **3 times by timestamp spans**. The summaries report both, expose discrepancies, and preserve the original JSON verbatim.
- Added field-log auditing, regression tests and qualitative routing fixtures.

### v0.2 evaluation infrastructure and release-study update (2026-10)

- **v1 low-uncertainty pilot:** three simple tasks, 9/9 accepted; BetFirst was 37.1% slower than Efficiency-only and used ~69.6% more gross tokens. Negative evidence retained.
- **v2 replicated diagnostic pilot:** two distinct tasks × three arms × three repeats, 18/18 PASS after publicly documented additive-test/package-marker grading corrections; BetFirst vs Efficiency **33.8% less wall time**, **38.0% fewer gross tokens**, **81 vs 106 tool calls**. These are local, exploratory, **not causal** or generalizable speedup claims.
- **v3 final preregistered launch study:** 12 newly authored tasks (low/diagnostic/stateful/no-change), three arms and three repeats (108 real sessions planned); frozen v0.2 Skill, independent external oracles, durable resume/checkpoints, task-level uncertainty, automatic final report, SVG chart and X post draft. **No real v3 inference has run at this commit.**
- Root, English/Traditional Chinese BetFirst READMEs, legacy protocol and historical experiment log updated to distinguish negative and positive results.
- No policy changes to SKILL.md; this is documentation, benchmark tooling and launch preparation, not v0.3 runtime behavior.

**Release commitment:** publish v0.2 and complete v3 results—positive, mixed or negative—without requiring a new v4. See `experiments/V3_PROTOCOL.md`, `experiments/EXPERIMENT_HISTORY.md`, and `experiments/V3_LAUNCH_KIT.md`. The old `evals/next-experiment.md` proposal is superseded, retained for context.

## v0.1

Initial portable policy, qualitative cases, evaluation protocol and CSV analyzer.

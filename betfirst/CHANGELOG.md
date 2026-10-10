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

Next: Controlled single-agent, paired Baseline / Efficiency / BetFirst runs with independent correctness checks, real session telemetry, bet decision quality and fallback overhead. See `evals/next-experiment.md`.

## v0.1

Initial portable policy, qualitative cases, evaluation protocol and CSV analyzer.

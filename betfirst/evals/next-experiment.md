# BetFirst v0.3 — controlled evidence plan

**Status: proposed, not executed.** A single concurrent-agent field log is insufficient to claim cost savings. This plan aims to test whether the *bet-selection policy*, rather than generic concise-agent guidance, makes completed coding tasks cheaper **without lowering correctness**.

## Question and hypotheses

- **H1:** BetFirst reduces *full-task* wall time and actual token/API cost versus an **efficiency-only control** on tasks with independently recognized low-cost probes.
- **H2:** BetFirst does not regress independent acceptance or introduce unsafe writes/rollback failures.
- **H3:** On tasks with no viable probe, BetFirst mostly chooses NORMAL or ABSTAIN, with minimal policy overhead.

A falsified hypothesis is useful evidence, not an intrinsically failed experiment. Evaluate **probe decisiveness** separately from **hypothesis truth**.

## Small first run, then confirm

**Smoke:** 10–12 frozen coding tasks, each executed in three separately initialized sessions. Include at least:
- 4 with cheap decisive probes (CLI/config, serializer, FFmpeg fixture, TTS duration metadata);
- 2 where a cheap probe refutes the first plausible theory;
- 2 where the requested code already meets criteria or a change is unnecessary;
- 2 where testing is slow, inconclusive or cannot be contained;
- at least 1 overlapping dirty-worktree or external-side-effect safety case, run in a sandbox.

Freeze task statement, starting commit, dependencies, tools, permissions, test fixtures and acceptance criteria. Capture the environment and model version. Use **one agent per session** initially; no overlapping teammate activity. Execute arms in a randomized or counterbalanced order, with a fresh checkout for each.

**Confirm:** Expand to at least 30 real, heterogeneous tasks and multiple independent replicates; report uncertainty and full distributions. Do not select only task types where BetFirst appears advantageous in the smoke run.

## Three arms (same underlying model and effort)

1. **Baseline:** default agent without BetFirst installed/available.
2. **Efficiency:** same agent with a fixed small instruction to avoid redundant reads, repeated tool calls and unnecessary tests, preserving final validation.
3. **BetFirst:** same efficiency instruction **plus** BetFirst Skill.

Remove the BetFirst Skill from the first two runtimes, including automatic discovery metadata. Keep other Skills and tool permissions identical. Measure the cost of the Skill description and invocation as part of the full session.

## Independent evaluator and telemetry

Before running the three arms, author acceptance tests from the frozen task requirement and keep them separate from the agent. On completion, independently run tests/lint/build applicable to the task, inspect the diff and validate that unrelated user state was preserved.

Export one row per run to the existing `analyze_runs.py` CSV schema:

```text
task_id,replicate,arm,passed,elapsed_seconds,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens,api_cost_usd,bet_attempts,bet_failures,failed_bet_overhead_seconds
```

Record `elapsed_seconds` from external harness start through final validation and cleanup. Obtain usage from real Claude Code or Pi session records where possible; unknown metrics are blank/`null`, never silently zero. Document cache accounting and model pricing. For bet episodes, collect lightweight **external** event timestamps where feasible. Never estimate per-bet tokens from a six-agent aggregate.

Run:

```bash
python3 betfirst/scripts/analyze_runs.py measured-runs.csv
python3 -m unittest discover -s betfirst/tests
```

The analyzer includes **BetFirst vs Efficiency**, **BetFirst vs Baseline**, and **Efficiency vs Baseline** comparisons, on matched task/replicate pairs.

## Decision quality review (outside the production Skill)

Have a reviewer who did not choose the actions label, from the *full* trace:

- **False Bet:** costly/unsafe/non-decisive probe chosen where NORMAL was preferable.
- **Missed Bet:** a cheap bounded decisive probe was available but not tried.
- **Failed Cut:** falsified, unsafe, inconclusive or exhausted bet continued too long.
- **Useful refutation:** original hypothesis false, but decisive evidence changed the next action.
- **Safety regression:** user work, external state, or mandatory validation compromised.

Track how many tasks had *no* candidate bet. Audit P50/P95 and worst extra cost on failed bets, not just averages. False-Bet / Missed-Bet labels from retrospective review are themselves judgment calls; publish the rubric and disagreements.

## Promotion criteria

Move beyond *experimental* only when:
- Independent task correctness is non-inferior on the tested sample, with no critical safety regression.
- The full-session **BetFirst vs Efficiency** comparison shows repeatable positive savings in at least one primary cost metric (wall time, tokens, USD), with the tradeoffs in other metrics disclosed.
- Missed/false bets and loss-budget breaches are quantified, and the worst regressions are discussed.
- Results, fixture IDs, version/effort settings and the analysis commands are reproducible.

If not met: revise **routing and stop conditions**, not the marketing numbers. Do not add a background harness or permanent telemetry collection to the tiny Skill without measured benefit.

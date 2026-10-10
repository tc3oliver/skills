# BetFirst evaluation protocol

These fixtures define decisions to test, not proof of faster execution. **No benchmark result has been measured or published in this repository.**

## 1. Qualitative routing checks

Use `cases.json` to check that the Skill chooses BET, NORMAL, or ABSTAIN correctly. Include false-bet, missed-bet, and failure-to-stop review of the actual execution trace. The tests are examples of intended behavior, not executable acceptance tests against SignalForge.

## 2. Controlled performance evaluation

For every real coding task, prepare an immutable starting commit, the same acceptance tests, identical model and thinking/effort settings, and a fresh session. Use three arms:

- `baseline`: normal coding agent without BetFirst.
- `efficiency`: generic concise/no-redundant-work instructions without the betting policy.
- `betfirst`: identical efficiency instructions plus BetFirst.

Keep the task prompt, tooling, permissions, available files, sandbox, and network conditions constant. Randomize or counterbalance arm order, and repeat tasks to limit stochastic noise. Never run arms over one another's modified checkout. Count unsuccessful runs and all failed bets.

For a controlled `efficiency` arm, use the same small instruction across all tasks: "Avoid redundant file reads, repeated tool calls, and unnecessary tests; preserve required validation." Use that exact instruction **plus** BetFirst in the `betfirst` arm. In Claude Code, exclude the BetFirst plugin/skill from baseline and efficiency harnesses (not merely "don't invoke it"): an auto-discoverable skill description can otherwise contaminate the control group. Keep all other Skills equal.

Start with 10–12 diverse tasks for smoke testing; expand to at least 30 tasks and multiple repetitions before making public performance claims. Include tasks with no reasonable bet, ambiguous probes, dirty worktrees, hard bugs, and cheap decisive tests. The independent acceptance evaluator must not be the coding agent's self-report.

## 3. Record actual measurements

Export one CSV row per task/replicate/arm from external harness or session telemetry.

Required columns: `task_id,replicate,arm,passed,elapsed_seconds`.

Optional columns: `input_tokens,output_tokens,cache_read_tokens,cache_write_tokens,api_cost_usd,bet_attempts,bet_failures,failed_bet_overhead_seconds`.

- `passed` is `true` or `false`, based on independent acceptance checks.
- `elapsed_seconds` is measured wall-clock from task start through **final** checks (and fallback).
- Token categories and `api_cost_usd` come from **actual** runtime usage. Leave unavailable fields blank.
- Include all attempts, including failed tasks; do not report an invented 0 for unknown token usage.
- Define failed-bet overhead as *additional measured probe + cleanup time*. Do not assume it is zero when a cleanup step is absent.
- For separate baselines, pair by `task_id` and `replicate`.

Run:

```bash
python3 betfirst/scripts/analyze_runs.py path/to/measured-runs.csv
python3 -m unittest discover -s betfirst/tests
```

The output reports full-arm aggregates and matched-pair savings. A null metric means incomplete evidence. Gross tokens (including cache read/write) and actual USD spend are distinct measures; cached tokens have different pricing.

## 4. Publish evidence, not anecdotes

Report independent success rate, time, input/output/cache tokens, API cost, bet frequency, failed-bet overhead (including tails), and breakdowns by task class. Include the Skill/context overhead in the full session and compare **equal correctness**. Report failures and worst regressions openly; avoid claims like `-20% tokens` until measured and reproducible.

This CSV analyzer deliberately does **not** parse Claude Code or Pi session files: their usage fields and event schemas must first be verified per runtime and version. Implement a telemetry exporter separately when representative real logs are available; do not guess their format.

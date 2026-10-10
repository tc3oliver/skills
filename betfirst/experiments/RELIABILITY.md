# BetFirst Benchmark Reliability (stacked on Evaluation v2)

## Objective

Follow-up to PR #6. The first live Qwen3.8-27B / Claude Code diagnostic pilot showed real and uneven permission denials in all three arms. The original benchmark allowed only the unittest Bash pattern; it blocked Python one-off reproductions. The reported 45.7% lower elapsed time and 59.3% lower gross tokens for BetFirst on two diagnostic tasks are **exploratory**, potentially confounded by permission-denied retries, and are not causal proof of a BetFirst win.

This patch does NOT change betfirst/SKILL.md or fixtures.

## Modes and safety

Default permission profile remains restricted and unchanged: Read, Edit, Write, and Bash(python3 -m unittest *). Choose a more capable profile only in a dedicated OS-isolated user/VM/container with no sensitive host data or credentials:

    --claude-tool-profile diagnostic --acknowledge-isolation

This allows Read, Edit, Write and Bash(python3 *). It permits inline python3 -c probes, Python scripts, and tests for **all three arms equally**. Arbitrary Python can read/write files and execute child processes; the flag is an acknowledgement, NOT a sandbox. Do not invoke this diagnostic profile on your primary workstation account unless isolated by actual OS-level security. It does not grant unrestricted Bash(*), rm or a no-permission bypass. No process inside the Python interpreter is contained by Claude Code's pattern-based tool permission alone.

The shared prompt now says agents may add regression tests but must not modify or delete existing tests; for diagnostic mode, it tells all three arms to use Python directly instead of denied shell heredocs/pipelines. Since this changes the common prompt and tool allowances, **do not pool results from old and new permission profiles into a single within-profile speedup claim**.

## Consistent agent outcome classification

Every new outcome.json and measured-runs.csv now distinguishes:

- code_accepted: original tests intact under additive-only rubric, visible tests and external oracle pass, no-change contract respected.
- session_success: process terminated cleanly without timeout or error subtype.
- passed: both code_accepted and session_success.
- failure_reasons: specific, nonexclusive labels (agent_max_turns, agent_timeout, agent_error, visible_tests_failed, oracle_failed, tests_tampered, unexpected_change, etc.).
- agent_subtype and agent_turns: extracted from Claude Code result stream, not inferred from final model prose.

A stopped agent may still have accepted code (e.g. render-resume Baseline had error_max_turns but passed post-run oracle). Both truths are reported; it is not a successful Agent session.

The runner writes permission profile and max-turns budget to manifest.json. Real model output remains in local run directories and must not be committed. Report compares session completion and code acceptance independently where recorded; old CSVs without fields still work.

## Verification

    python3 -m unittest discover -s betfirst/experiments/tests -v

Offline 3-task and 5-task mock smoke still run in GitHub CI on macOS and Linux. Windows retains its portable validations. Live model performance is NOT tested by CI.

## Next real experiment

In an isolated environment only, with the **same** oMLX/Qwen model and the same task suite:

    OUT="$(mktemp -d)"
    python3 betfirst/experiments/run.py \
      --suite betfirst/experiments/suite-v2.json \
      --driver claude --claude-launcher omlx \
      --model "Qwen3.8-27B-oQ4e-mtp" \
      --claude-tool-profile diagnostic --acknowledge-isolation \
      --task config-scope --task render-resume \
      --execute --replicates 3 --seed 20261011 \
      --max-turns 30 --timeout 600 --output "$OUT"
    python3 betfirst/experiments/report.py "$OUT"

This is 18 local model sessions. Do not run it on your primary host environment just because the CLI accepts --acknowledge-isolation; the permission profile includes arbitrary Python execution. Use matched pairs, correctness-first, separate low/diagnostic strata, report permission denials and turns, and repeat with held-out incidents before making speedup claims. Keep original PR #6 six-run data frozen as restricted-profile evidence.

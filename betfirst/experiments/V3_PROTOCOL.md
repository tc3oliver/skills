# BetFirst Evaluation v3: one final preregistered release study

**Before live inference: NOT RUN. After this one study: RELEASE, whether positive, mixed or negative. No mandatory v4.**
Do not change tasks, Skill, acceptance policy or sample size in response to disappointing observations. Disclose instrumentation bugs and preserve unmodified evidence.

## Study design

Hypothesis H1: BetFirst v0.2 reduces time and gross tokens compared with Efficiency without reducing accepted work.
H2: Benefit concentrates in diagnosis/stateful tasks rather than low-uncertainty or negative controls.
H3: Mechanistic review shows genuine bounded, falsifiable probes that redirect later work, rather than ordinary tests relabeled as BET.

Three arms: Baseline plain agent, Efficiency Baseline plus short waste-reduction guidance, BetFirst Efficiency plus frozen verbatim BetFirst Skill. Keep one model, same tool profile, same per-session turns and wall limits. Randomized order is seeded; model decoding is not.

**Final matrix = 12 new tasks x 3 arms x 3 replicates = 108 live sessions**:

| Category | Task IDs |
|---|---|
| low | webhook-signature, cursor-pagination, unicode-casefold |
| diagnostic | queue-priority, ledger-idempotency, search-highlight |
| stateful | lease-fencing, checkpoint-atomicity, partition-watermarks |
| negative | stable-merge-ok, ttl-boundary-ok, retry-once-ok |

Nine buggy seeds must fail independent external Oracle initially; three negative controls must pass before Agent touches them and require no change. Every task has public tests and an out-of-workspace Oracle. Synthetic reference fixes are for harness CI only, never present in the Agent worktree; not a security barrier against hostile tools. Fixtures are newly authored, not third-party blind production samples.

## Preset publication decision

All 108 complete; 12 IDs x 3 arms x 3 repeats; manifest suite, fixture and frozen Skill hashes available, same diagnostic tool profile. Never remove failures. Success = code accepted AND agent session completed cleanly. Display these separately.

Primary: BetFirst versus Efficiency. Compare total time, gross tokens, calls, failures, 12 task-level 3-run medians, task-level geometric mean time ratio and 95% cluster bootstrap interval plus 12-task exact sign test. Also report category breakdown and matched 36-run count; replicates are NOT 36 independent tasks.

Qualify a limited positive exploratory headline only when:
- Both arms PASS all 36 primary sessions;
- BetFirst faster on at least 9/12 task medians;
- At least 15% pooled wall-clock reduction;
- 95% task-cluster bootstrap interval upper bound for time ratio is below 1.

Regardless of gate, RELEASE Skill and complete report after the study. Positive gate is observational and is not causal proof of BET; negative/mixed results deserve equal prominence. Do not treat local model estimated API dollars as actual money saved. A new v4 is NOT a publication prerequisite.

## Reproducible commands

Use a dedicated OS-isolated user or VM with no host credentials. Diagnostic profile allows arbitrary Python; acknowledgement flag does NOT sandbox.

    export OMLX_BIN="$HOME/Developer/ai/omlx-production/current/.venv/bin/omlx"
    export OMLX_BASE_PATH="$HOME/Developer/ai/omlx-production/current/state"
    export CLAUDE_CONFIG_DIR="$HOME/.claude-local"
    export CLAUDE_CODE_AUTO_MODE_SERVER=0
    export BET_MODEL="Qwen3.8-27B-oQ4e-mtp"

    RUN_DIR="$(mktemp -d)"
    python3 betfirst/experiments/run.py \
      --suite betfirst/experiments/suite-v3.json \
      --driver claude --claude-launcher omlx \
      --model "$BET_MODEL" \
      --claude-tool-profile diagnostic --acknowledge-isolation \
      --execute --seed 20261011 --replicates 3 \
      --max-turns 30 --timeout 600 --output "$RUN_DIR"

After a graceful interruption at a completed checkpoint, repeat identical command with --resume and the SAME output directory. Resume checks full manifest consistency and refuses to silently overwrite an incomplete run directory. If an Agent was interrupted mid-tool, preserve evidence and repair explicitly rather than secretly rerunning its task. Each finished arm writes outcome.json, row.json and atomically refreshes measured-runs.csv.

Offline synthetic smoke (NOT performance evidence):

    python3 -m unittest discover -s betfirst/experiments/tests -v
    python3 betfirst/experiments/run.py --driver mock \
      --suite betfirst/experiments/suite-v3.json \
      --timeout 30 --output "$(mktemp -d)"

Final output, only after 108 REAL model sessions:

    python3 betfirst/experiments/v3_report.py "$RUN_DIR"
    cat "$RUN_DIR/v3-publication-report/REPORT.md"

The report refuses incomplete, synthetic, non-diagnostic or mismatched-hash samples.

## Release evidence

Keep raw agent stdout, stderr and worktrees private (may contain credentials and local paths); share anonymized rows, per-task results, summary and frozen commit hashes. Use review-protocol.md for independent trace review; ordinary tests and self-reported agent claims do not automatically count as BET. If the trace review is not complete, report BET mechanism as unverified. Previous v1/v2 studies stay separate (EXPERIMENT_HISTORY.md). Final X copy is in V3_LAUNCH_KIT.md, with unfilled result placeholders until actual results exist.


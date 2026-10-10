# BetFirst Evaluation v2 — mixed-difficulty pilot

## Purpose

The preceding real Qwen3.8-27B / Claude Code pilot passed all nine checks, yet BetFirst was 37.1% slower and used 69.6% more gross tokens than Efficiency-only on three simple tasks. These single-run observations are not causal conclusions. The hypothesis now is that bounded diagnostic bets might help when there are several plausible root causes. Do not design tasks for a predetermined winner.

Five preregistered tasks in suite-v2.json:

- subtitle-path: low uncertainty, Windows path escaping
- tts-estimate: low uncertainty, measured TTS speaking rate
- already-correct: low uncertainty, deliberate no-change control
- config-scope: diagnostic, a different tenant sometimes gets the wrong flag despite correct backend data
- render-resume: diagnostic, video clips disappear or duplicate on resume when display titles collide

Two diagnostic tasks involve multiple modules and plausible misleading symptoms, but do not name the exact fix. Each task has visible tests plus an **independent oracle outside the copied workspace**. The two harder fixtures must initially fail their independent oracles; CI tests this. Oracles are not secrets nor protection against a hostile agent that can read outside its worktree.

## Offline smoke, no model calls

From repository root:

    python3 -m unittest discover -s betfirst/experiments/tests -v
    python3 betfirst/experiments/run.py --driver mock --suite betfirst/experiments/suite-v2.json --timeout 30 --output /tmp/betfirst-v2-mock

Expect 5 tasks x 3 arms = 15 deterministic PASS in synthetic-smoke.csv. Mock duration is never a performance claim.

## Live Qwen / oMLX / Claude Code evaluation

Use the already-verified local model, server and double-dash oMLX argument separator. Run only in a disposable account or VM; worktree isolation and dontAsk tool policy are NOT an OS sandbox.

    export OMLX_BIN="$HOME/Developer/ai/omlx-production/current/.venv/bin/omlx"
    export OMLX_BASE_PATH="$HOME/Developer/ai/omlx-production/current/state"
    export CLAUDE_CONFIG_DIR="$HOME/.claude-local"
    export CLAUDE_CODE_AUTO_MODE_SERVER=0
    export MODEL="Qwen3.8-27B-oQ4e-mtp"
    RUN_DIR="$(mktemp -d)"

    python3 betfirst/experiments/run.py \
      --suite betfirst/experiments/suite-v2.json \
      --driver claude --claude-launcher omlx \
      --model "$MODEL" --execute --seed 42 \
      --replicates 1 --timeout 600 --output "$RUN_DIR"
    python3 betfirst/experiments/report.py "$RUN_DIR"

For a shorter exploratory diagnostic-only run, add --task config-scope --task render-resume (six real model runs). Each selected task ID and the selection mode are recorded in manifest.json; label this clearly as a subset, not a five-task result. Do not filter tasks after seeing which arm won.

This executes 15 actual model tasks, randomly ordered with the same model, tools and permissions across arms. The runner uses --bare, stream-json + --verbose for tool envelopes, dontAsk and a narrow Read/Edit/Write/unit-test Bash tool allowlist. It does not enable dangerously-skip-permissions. For an initial short smoke use --limit 3; this covers only the low-uncertainty controls. Run the whole suite to compare difficulty groups.

## Trace and evidence

- outcome.json: agent status/time, visible-suite status/time and separate out-of-workspace oracle status/time, test tampering and timeout.
- agent.stdout: Claude Code JSONL stream with assistant/tool events; use jq -r 'select(.type == "result") | .result' on the file to extract the final response.
- trace_summary.json: counts of unique tool_use IDs, tool_result errors and explicit permission denials when available, without copying raw inputs or paths to the summary.
- measured-runs.csv: elapsed time, input/output/cache tokens, optional tool_calls, tool_errors, permission_denials. Missing data is null, never zero.
- report.py: matched BetFirst vs Efficiency/produced baseline, including tool call counts where available and explicit acceptance counts.

Local model api_cost_usd is a provider-reported **estimate**, not actual local compute or electricity cost; do not report costBasis=unknown as money saved. Under oMLX input_tokens may be zero while cache_creation_input_tokens is nonzero.

No automatic bet_attempts / bet_failures are claimed: an ordinary test is not automatically a BET, and tool envelopes do not reveal agent intent. Review trace labels independently per review-protocol.md. Preserve slow, failed, and low-uncertainty tasks; don't cherry-pick successes. Repeat with independent seeds before a larger held-out 10–12 and then 30+ task study.

CI does NOT run a live Qwen session; its pass result only qualifies the harness and fixtures.


## Test integrity policy v2 and existing-run regrading

Original evaluation v2 marked any changed file under tests/ as a failure. In the real two-diagnostic-task pilot that falsely rejected three valid *additive* regression-test contributions even though visible and independent oracle suites passed.

New grading rule:
- Keep original test AST statements and original test method bodies intact; edits/deletions, shadowed original test names, test symlinks and changed non-Python assets fail.
- **Permit additive tests:** new test_ methods inside existing classes, new unittest.TestCase classes, and new test_*.py modules. Existing test file may also add imports; comments/whitespace are not meaningful AST changes.
- Independent oracles still must pass; agent failures (nonzero exit), timeouts and no-change controls still fail normally.
- outcome.json distinguishes tests_changed (any changes), tests_tampered (prohibited changes), and test_integrity (added/extended/tampered/deleted paths).
- This protects existing checks but is **not a hostile-code sandbox**; an additive test can still have side effects. Use trusted coding tasks and independent oracles.

**Regrade an already-finished six-run pilot without rerunning Qwen, visible tests or oracles:**

    python3 betfirst/experiments/regrade.py "$RUN_DIR" \
      --suite betfirst/experiments/suite-v2.json

    python3 betfirst/experiments/report.py "$RUN_DIR/regraded-v2"
    cat "$RUN_DIR/regraded-v2/regrade-audit.json"

Regrade verifies the suite SHA and, for newly recorded runs, original fixture hashes. It uses recorded agent/test/oracle statuses and inspects the worktree tests against the frozen fixture. It creates a NEW derived report directory containing revised CSV, manifest with provenance and an audit JSON; the original stdout, artifacts, outcomes and CSV remain untouched. For early runs without recorded fixture hashes, the report explicitly marks fixture verification as unavailable: use the same checked-out fixture revision as the experiment and interpret derived results accordingly.

Six-run diagnostic pilot observation before regrading: config-scope efficiency/betfirst PASS, baseline false FAIL; render-resume all false FAIL; every public and oracle check exited 0. Agent baseline in render-resume exited 1. After applying the new additive-only rubric to the user-observed three additive edits, expected scores are **5 PASS / 1 FAIL**; this historical rerating is not a fresh model trial or an unbiased validation set.

Report results by correctness first and retain any loss due to Claude tool permission denials; lower tool calls or token counts do not prove a BET caused savings.

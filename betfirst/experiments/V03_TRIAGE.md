# BetFirst v0.3 candidate — trace-driven, low-cost triage

**Status: CANDIDATE on a separate branch. Not proven, not merged, not a regrading of frozen v3.**

## Why a new candidate?

Eight v3 traces inspected (11 October 2026, owner-provided partial sample):

- **ledger-idempotency r2**: BetFirst reproduced double debit with a small read-only call, but a replay using the same ID with altered amount was not covered by its fix; independent Oracle rejected it. Efficiency also failed. Do not attribute this issue solely to BetFirst.
- **partition-watermarks r3**: a small reproduction confirmed global vs per-shard progress. The patch initialized missing shard state with offset 0; the independent Oracle rejected the legitimate zero boundary.
- **ttl-boundary-ok r2**: the probe correctly disproved the alleged bug, but BetFirst edited `tests/test_ttl.py` anyway, violating the task's *leave repository unchanged* instruction.
- **checkpoint-atomicity r2**: code passed independent Oracle, but the agent edited an original `tests/test_worker.py` after its attempt to create a test file using a disallowed shell here-doc; the original-test-integrity gate rejected the run.
- **search-highlight r2**: both BetFirst/Efficiency passed, but BetFirst consumed more time while retrying unsuitable test invocation forms; one trace cannot establish a systematic overhead.
- Some BetFirst runs begin with broad reading and probes after the root cause has become obvious. This can erase the value of a wager, particularly on tiny tasks.

## Specific policy adjustments to test

1. **No ceremonial bet**: skip a probe when direct work is cheaper or its result changes nothing.
2. **WIN is not DONE**: after a decisive probe, inspect one task-critical edge when applicable and run final required checks.
3. **ABSTAIN really means no changes**: not even an additive test on an already-correct task.
4. **Test/permission discipline**: never rewrite original tests as a fallback for unavailable file-creation tools; do not retry denied commands repeatedly.
5. **Feasibility-first targeting**: expensive documentation/full PoC before a cheap decisive test is the intended best-case task, not guaranteed every-task speedup.

These are hypotheses from eight inspected traces, not proof that the v0.3 wording cures the failures.

## Gate 1: 9-session diagnostic triage, not a benchmark claim

Once the frozen v3 run is **safely stopped or completed**, use this branch in an **independent working tree/output directory**. Do not overwrite existing v3 evidence; do not run competing inference jobs on the same resource when comparing timing.

Existing harness can run 3 chosen v3 tasks × 3 arms (baseline, efficiency, candidate BetFirst) × 1 replicate = **9 real sessions** without runner changes. Pick one diagnostic, one hard stateful, and one already-correct task:

```bash
RUN_DIR="$HOME/betfirst-v03-triage/run-$(date +%Y%m%d-%H%M%S)"
python3 betfirst/experiments/run.py \
  --suite betfirst/experiments/suite-v3.json \
  --task search-highlight \
  --task partition-watermarks \
  --task ttl-boundary-ok \
  --driver claude --claude-launcher omlx \
  --model "Qwen3.8-27B-oQ4e-mtp" \
  --claude-tool-profile diagnostic --acknowledge-isolation \
  --execute --seed 20261011 --replicates 1 \
  --max-turns 30 --timeout 600 --output "$RUN_DIR"
```

**Important:** these tasks and failure cases are now *known* to the maintainer. This is a **regression/behavior smoke**, not independent held-out evidence. Model randomness still matters; a 9-session result is not a performance finding. `v3_report.py` intentionally rejects it as incomplete.

## Stop/go gate

- **Fail fast** if candidate BetFirst changes any file on a no-change task, tampers with original tests, fails acceptance/Oracle, or performs unbounded/ceremonial probe loops.
- **Proceed to held-out tests** only if the candidate correctly avoids file edits on the no-change task, preserves original tests on all tasks, passes all independent acceptance/Oracles, and a manual trace review finds a real bounded BET where it was worthwhile and a true NORMAL/ABSTAIN where it was not.
- Compare matched elapsed time and gross tokens to Efficiency as **descriptive** numbers only. Speed is a secondary gate after correctness.
- If the smoke passes, author **three genuinely new unseen tasks** (e.g. feasibility/PoC avoidance, straightforward cheap fix, negative no-change), freeze them **before** running, then run paired Efficiency/candidate sessions with multiple repetitions. Disclose all failures and model configuration.
- Do not modify original v3 results or reuse v3 as a v0.3 improvement claim. v2 positive and v1 negative history remain intact.

## Safety and publication

Diagnostic profile allows arbitrary Python execution: `--acknowledge-isolation` is not a sandbox. Run in a dedicated OS-isolated account or VM and keep credentials out of trace data.

The original v3 preregistration allowed a qualified positive headline only with a complete 108-session study meeting all correctness/time gates. An early-stopped v3 is an **incomplete negative/mixed observation**, not proof that the v0.3 candidate helps. The v0.3 experiments require their own prospective design and honest reporting.

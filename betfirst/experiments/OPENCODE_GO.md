# BetFirst × OpenCode Go — 1 smoke + 2-hour paired study

The OpenCode CLI has already returned `OK` for
`opencode-go/muse-spark-1.3-contributor`. This workflow skips another basic
connectivity probe and uses **one small real coding task** to verify the full
runner and Oracle workflow. It then launches an exploratory study for **at
most two hours** (study time excludes the preliminary smoke).

**Separate from frozen Claude/oMLX v3:** all Muse runs use the same Muse
model and OpenCode harness, comparing Efficiency against candidate BetFirst.
Do not compare Muse numbers directly with local Qwen to claim a Skill effect.

## Preconditions

- OpenCode Go authenticated; disable **Use balance** in OpenCode Console if
  you do not want any Zen balance fallback / unexpected cash charges.
- Contributor model prompts/completions may be used for provider training.
  Use only public synthetic fixtures, never company source or private data.
- **OS-isolated user/VM**, no sensitive host credentials or external data;
  `--acknowledge-isolation` merely declares that isolation already exists.
- OpenCode permissions limit selected tools but are **not a sandbox**:
  allowed `python3` commands may run arbitrary Python.
- Do not simultaneously run oMLX load tests when measuring wall-clock time.

## One command: lightweight smoke, then two hours

```bash
cd ~/betfirst-v03
git pull --ff-only
python3 -m unittest discover -s betfirst/experiments/tests -v

ROOT_DIR="$HOME/betfirst-muse-study/run-$(date +%Y%m%d-%H%M%S)"
python3 betfirst/experiments/muse_study.py launch \
  --output "$ROOT_DIR" \
  --hours 2 \
  --acknowledge-isolation

echo "Evidence: $ROOT_DIR"
cat "$ROOT_DIR/study/budget-status.json"
```

**Smoke:** `cursor-pagination` × candidate BetFirst, **1 session**.
Requires OpenCode to exit cleanly, emit real agent/tool JSON events, and
complete the acceptance/independent-Oracle evaluation pipeline. It does
**not** require the coding answer to PASS: acceptance/Oracle failures are
measured behavior, not necessarily integration failures. A CLI crash, denied
tools preventing all work, invalid telemetry, or missing judge output blocks
the long study. One run is smoke, not a benchmark.

**Study:** Efficiency vs BetFirst in adjacent randomized pairs over the 12
existing public v3 tasks, up to 24 repeats / 576 sessions **subject to a
7200-second wall-clock budget**, whichever stops first. Runs are sequential,
not concurrent. Only start another pair if the remaining time safely covers
both arms with their per-run timeouts; leave unused slack rather than an
incomplete pair at deadline. Per Agent call: 180s cap, 30 model-step cap;
visible acceptance and independent Oracle: 30s each.

Each completed run is saved immediately to `measured-runs.csv`, and its
own `row.json`, `outcome.json`, `trace_summary.json`, stdout/stderr and
worktree. `budget-start.json` persists original wall-time start across
resume; `budget-status.json` records complete-pair count and stop reason.

You can also split the workflow:

```bash
SMOKE_DIR="$HOME/betfirst-muse-study/smoke-$(date +%Y%m%d-%H%M%S)"
python3 betfirst/experiments/muse_study.py smoke \
  --output "$SMOKE_DIR" --acknowledge-isolation

STUDY_DIR="$HOME/betfirst-muse-study/study-$(date +%Y%m%d-%H%M%S)"
python3 betfirst/experiments/muse_study.py study \
  --smoke-dir "$SMOKE_DIR" --output "$STUDY_DIR" \
  --hours 2 --acknowledge-isolation
```

When resuming an interrupted study, pass the **same output path** and
`--resume`; it will **not reset the original 2-hour budget**. A run
interrupted mid-tool may contain an incomplete session directory; preserve
and archive it outside the evidence folder before any resume, and document
the event.

## Interpretation

Compare only **fully matched task+replicate pairs**, where independent code
acceptance and agent completion succeeded. Report every failure separately
and compare correctness first, then wall time, tokens and tool calls.

OpenCode versions can omit a last `step_finish`; unavailable full-session
token usage is `null`, **not** zero. Subscription `api_cost_usd` is
unknown; do not treat estimated per-token price as actual Go cash charge.

These are **previously seen tasks**. Even with many repeats over two hours,
this is a fast exploratory regression study, not held-out proof of broad
speedup or a replacement for the preregistered 108-session v3.

# BetFirst × OpenCode Go: Muse contributor pilot

This adapter is **experimental** and separate from the preregistered v3
Claude/oMLX study. Do not compare Muse results to Qwen results as if only
the Skill changed. Compare `efficiency` vs `betfirst` with the **same**
Muse model, fixture, tools, and independent Oracle.

## Verify subscription connectivity

```sh
opencode models opencode-go
opencode run -m opencode-go/muse-spark-1.3-contributor \
  --format json "Reply with exactly OK. Do not use tools."
```

A clean `OK` response confirms basic connectivity. Some versions do not
support `opencode models --refresh`; do not require it. Confirm OpenCode
Go quota and switch off **Use balance** in the Console if avoiding extra
Zen balance charges. Contributor prompts/completions may be used for
provider training: **public synthetic fixtures only**.

## Run the six-session paired triage

**Prerequisite:** a dedicated OS-isolated VM/account with no secrets or
sensitive file access. `--acknowledge-isolation` does NOT establish
isolation. OpenCode bash permissions allow Python commands; Python can
bypass CLI file restrictions. OS-level isolation is mandatory.

```sh
cd ~/betfirst-v03
git pull --ff-only
python3 -m unittest discover -s betfirst/experiments/tests -v
mkdir -p "$HOME/betfirst-muse-pilot"
RUN_DIR="$HOME/betfirst-muse-pilot/run-$(date +%Y%m%d-%H%M%S)"
echo "RUN_DIR=$RUN_DIR"

python3 betfirst/experiments/run.py \
  --suite betfirst/experiments/suite-v3.json \
  --task search-highlight --task partition-watermarks --task ttl-boundary-ok \
  --arm efficiency --arm betfirst \
  --driver opencode --model opencode-go/muse-spark-1.3-contributor \
  --claude-tool-profile diagnostic --acknowledge-isolation \
  --execute --seed 20261011 --replicates 1 \
  --max-turns 30 --timeout 600 --output "$RUN_DIR"

cat "$RUN_DIR/measured-runs.csv"
```

The runner makes **six fresh fixtures**, pins one OpenCode configuration for
both arms, denies external-directory tools and non-Python shell commands,
turns off automatic public session sharing, and disables default plugins
and Claude Code skill/CLAUDE.md auto-loading. No `--auto` is used. Normal
process and model-step limits are enforced by the runner. Limitations:
these are application-level settings, **not** filesystem/network sandboxing;
global managed policies and local provider configurations can still apply.

It preserves the original acceptance checks, external Oracle, original-test
integrity gate, per-arm `outcome.json`/`row.json`, and resumable checkpoints.
`--arm` selects exactly the arms named, and is recorded in the manifest.

**Usage warning:** Some OpenCode versions omit the last `step_finish` JSON
event even when the command exits successfully. If any model step lacks a
matching finish, token counts are recorded as `null` rather than an
incomplete total. `api_cost_usd` remains `null` because estimated
per-token cost is not evidence of incremental cash billed to Go subscribers.

**Decision gate:** if BetFirst fails the independent Oracle on
`partition-watermarks`, alters the `ttl-boundary-ok` fixture, or edits
protected tests, stop and inspect the corresponding trace. Six runs on
already-seen tasks are regression triage, **not** independent speedup evidence.
For efficacy, next create held-out tasks designed around cheap feasibility
probes before expensive reading or PoCs.

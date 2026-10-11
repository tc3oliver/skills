# BetFirst v0.5: preregistered mechanism / ablation experiment

**Status: frozen candidate; NOT executed.** The prior v0.4 run completed 54/54 acceptance PASS, and its evidence is retained. This is not a new release of the Skill or a retroactive correction to the previous study. Keep v0.3 and v0.4 frozen. Do not tune after seeing v0.5 outcomes.

## Question

Does the optional **bounded, decisive BET** mechanism provide additional value over otherwise comparable selective execution, rather than merely shortening the instructions or encouraging NORMAL execution?

## Frozen comparison

- **Efficiency**: existing efficiency-only control.
- **BetFirst v0.4**: frozen `candidates/v04/SKILL.md`.
- **No-BET ablation**: `candidates/v05/NO_BET.md`, same NORMAL / ABSTAIN, task-scoping, verification and safety requirements, but without the explicit hypothesis / BET / CUT-LOSS mechanism.

New `suite-v05.json`: 12 synthetic Python tasks, four each tagged `bet-win`, `bet-loss`, `normal`. These tags are **design intent**, not observed agent actions or verified causal mechanisms. Agent only receives task prompt and work fixture, not tag, independent oracle or benchmark metadata. All baseline visible checks must pass; all independent hidden oracles must fail before any model run. Three arms share model / permissions / test criteria, and run in shuffled contiguous matched groups. Two replicates per task. Exactly **72 planned sessions / 24 three-way paired groups**. Frozen seed `20261016`. A hard time budget can end earlier; report only complete groups.

The new tasks are deliberately small and synthetic. Some prompts are more diagnostic than others and may themselves encourage testing. The claim tested here is narrow: **on this fixed synthetic cohort**, does the v0.4 prompt beat the matched No-BET prompt without reducing correctness? It does not establish universally causal benefits of probing, nor are four task scenarios a statistically powered generalization.

## Preconditions and protections

Use a separate checkout and actual **OS isolation**; OpenCode tool permissions and `--acknowledge-isolation` are not an OS sandbox. Tasks must be public and synthetic; the contributor model may permit provider training. Do not grant model credentials, production data or network tools unnecessarily. Review OpenCode Go / Muse quota and **Use balance** configuration: rate limits are possible and charges must be prevented at the provider setting.

Never modify source fixtures / oracles / policies or reuse prior results after the live launch. Runner rejects dirty fixtures, and records hashes, arm order and completion checkpoints. Do not use old v0.4 tasks for the scored cohort. Each session is capped at 180s / 30 OpenCode model steps; each check is capped at 30s. The host budget defaults to 2 hours; each pair is reserved conservatively.

### Run (macOS)

```bash
git clone --branch feat/betfirst-causal-v05 --single-branch \
  https://github.com/tc3oliver/skills.git ~/betfirst-causal-v05
cd ~/betfirst-causal-v05
python3 -m unittest discover -s betfirst/experiments/tests -q
OUT="$HOME/betfirst-causal-v05-results/run-$(date +%Y%m%d-%H%M%S)"
python3 betfirst/experiments/causal_v05_study.py \
  --output "$OUT" --hours 2 --replicates 2 --acknowledge-isolation
python3 betfirst/experiments/analyze_v05.py "$OUT"
echo "RESULTS: $OUT"
```

The experiment folder must be new / empty and **must not be inside the source checkout**. Do not parallelize sessions, expose benchmark oracles to the model or suppress failing tests. Command does not deploy any permanent local system service.

### Review and claims (fixed before running)

Primary: independent Oracle PASS per matched group, no unauthorized workspace / fixture / original test modification. Secondary: paired wall seconds on **both-PASS** groups, with win counts and per-task distributions; turns and tool calls are supporting outcomes. Token or dollar deltas only when the OpenCode event record provides *complete* input/output usage; otherwise say **unknown**. Do not substitute wall time for token efficiency.

Engineering adoption criterion: no observed correctness or integrity regressions, plus at least 15% lower mean paired wall time against **both** controls on both-PASS pairs, and at least 60% paired wins against No-BET. These are predeclared practical thresholds, not proof of statistical significance. If incomplete or inconclusive, report that result; do not add more tests post hoc to reach the threshold.

Behavior evidence: independently review raw `agent.stdout` JSON events for the BET policy's actual hypothesis, small bounded tool-based probe, subsequent changed plan / skipped work, CUT LOSS and direct NORMAL. Model text *alone* is not proof. Use blinded independent coders if making mechanistic public claims. Classify `bet-win` / `bet-loss` / `normal` against **observed** action traces, not the task label. Record tool errors and incomplete traces as unknown. This labeling is a separate interpretation layer; do not claim it was measured by the run's automatic report.

### Resume interrupted run

Only if no agent process is active and runner checkpoint is complete:

```bash
python3 betfirst/experiments/causal_v05_study.py \
  --output "$OUT" --hours 2 --replicates 2 \
  --resume --acknowledge-isolation
```

Resume preserves deadline and immutable manifest; a process terminated mid-session may leave an incomplete directory, which requires separate recovery, not deletion.

### Share small evidence without workspaces

```bash
cd "$OUT"
find . -type f \( -name '*.csv' -o -name '*.json' -o -name '*.jsonl' \) \
  ! -path '*/work/*' ! -path '*/opencode-tmp/*' ! -path '*/opencode-config/*' \
  -print | zip -q "$HOME/betfirst-causal-v05-evidence.zip" -@
```

Preserve raw `agent.stdout` locally; it is needed for a later audited behavioral assessment, but does not need to be included in the initial ZIP.

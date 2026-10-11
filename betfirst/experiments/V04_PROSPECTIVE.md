# BetFirst v0.4 — prospective Muse experiment

**Status: preregistered exploratory candidate, NOT merged or validated with real Muse calls.**
This changes neither `betfirst/SKILL.md` (frozen v0.3) nor v3's suite,
oracles or previous run evidence. Run in a dedicated OS-isolated environment
with only public synthetic tasks. `--acknowledge-isolation` is an assertion,
not an OS sandbox. Do not give the Agent access to this repository's hidden
Oracle paths; the post-process path guard cannot prevent access in real time.

## Motivation / hypotheses (set before model runs)

The prior less-contaminated 25-pair Muse study showed 21 both-PASS pairs,
median BetFirst-v0.3 wall time **+15.7%** relative to Efficiency (not a
statistically stable general finding). Early Muse runs that accessed the
source checkout and hidden oracles are invalid and excluded. Six inspected
paired traces implicated redundant probes and extra model steps on simple
tasks; some long wall times were server/streaming delays.

v0.4 is a **shorter selective-router prompt**. Competing hypotheses:

- H1: v0.4 approaches Efficiency's overhead on direct and already-correct
  tasks by defaulting to NORMAL or ABSTAIN.
- H2: v0.4 beats v0.3 on diagnostic tasks where a small BET changes the plan,
  without a lower independent-Oracle PASS rate.
- H0: v0.4 offers no reliable improvement over Efficiency or v0.3.

**Do not change policy text, fixtures, tests or Oracles mid-study.**

## Prospective tasks and grouping

Six new synthetic fixtures in `fixtures/v04/`, with independently executed
`oracles/v04/` not copied into the agent workspace:

| Task | Class | Expected behavior |
| --- | --- | --- |
| csv-quoted-comma | direct | Implement quoted/escaped CSV semantics |
| path-segment-prefix | direct | Check URL path boundaries |
| packet-framing | diagnostic | Local wire vs reader byte-order mismatch; partial frames |
| namespaced-cache | diagnostic | Fix cross-namespace cache collision |
| interval-touch-ok | negative | Half-open interval handling is already correct; zero edits |
| retry-exhaustion-ok | negative | Only one transient retry is already correct; zero edits |

The separate smoke is a previously seen `cursor-pagination` task. It is
**not** part of the scored v0.4 cohort.

Arms: `efficiency`, frozen `betfirst` (v0.3), `betfirst-v04`.
Run each task/replicate as a **contiguous three-arm group** in randomized arm
order. Shuffle the six task groups in each replicate. Nominal design:
6 tasks × 3 arms × 3 repeats = **54 sessions**, maximum **1-hour** wall-clock
budget, capped at 180s per agent / 30 model steps and 30s for each visible
and independent check. The time budget may end before 54 sessions; report
exact completed matched groups. The reserve avoids deliberately beginning
a group without enough budget for all three arms. Only one model session
runs at a time.

### Run

```bash
cd ~/betfirst-v03
git status --short
git fetch origin
git switch --track origin/feat/betfirst-v04-heldout-muse

python3 -m unittest discover -s betfirst/experiments/tests -v

OUT="$HOME/betfirst-muse-v04/run-$(date +%Y%m%d-%H%M%S)"
python3 betfirst/experiments/muse_v04_study.py \
  --output "$OUT" \
  --hours 1 --replicates 3 --acknowledge-isolation

echo "Evidence: $OUT"
cat "$OUT/study/budget-status.json"
```

Do NOT use the original checkout with private data, hidden oracle access or
long-running parallel agents. The OpenCode Go provider may apply limits;
disable Zen **Use balance** if any extra cash usage is unacceptable.
Contributor model traffic may be training-eligible, hence public synthetic
data only.

### How to interpret

First compare **per-arm Oracle PASS, agent completion, no-change compliance
and fixture/test integrity** across all fully matched groups. Then compare
paired time *only on groups where both compared arms PASS*, alongside the
fraction of matched comparisons won. Report per-task outcomes and timeout
rates as well as medians. Report token deltas **only when all model-step
usage events are complete**, otherwise `unknown`. Keep `api_cost_usd`
unknown for Go subscription traffic.

Success is not a single faster run: require no correctness regression, a
meaningful reproducible speed benefit, and real behavioral evidence of
NORMAL/BET/ABSTAIN routing. This small public suite provides a smoke-sized
prospective signal, not a statistically powered general speedup claim.

### Resume

Only after confirming no active runner:

```bash
python3 betfirst/experiments/muse_v04_study.py \
  --output "$OUT" --hours 1 --replicates 3 \
  --resume --acknowledge-isolation
```

Original deadline and manifest are preserved. A crash while executing
one arm may leave a partial per-run directory; **preserve** it for diagnosis.
Do not delete/change evidence or force a resume over an incomplete arm.
The protocol rejects changed Skill hashes or fixtures.

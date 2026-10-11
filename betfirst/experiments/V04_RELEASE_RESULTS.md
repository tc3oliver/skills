# BetFirst v0.4 — release evidence (2026-10-11)

**Status:** engineering adoption, not proof of universal or causal acceleration. The statistics below come from the user's local Muse Spark 1.3 Contributor runs on synthetic Python tasks; raw session evidence is not yet published in this repository.

## Frozen studies

| Study | Distinct tasks | Arms | Sessions | Results |
| --- | ---: | --- | ---: | --- |
| v0.4 held-out | 6 | Efficiency / v0.3 / v0.4 | 54 | 54/54 PASS; 18 matched triplets; mean seconds: 18.223 / 15.373 / **13.526** |
| v0.5 ablation | 12 | Efficiency / v0.4 / v0.4 No-BET | 72 | 68/72 PASS; 24 matched triplets; PASS: 23/24 / 23/24 / 22/24; mean seconds: 17.93 / **15.25** / 19.88 |

**126 executions, 42 matched three-arm groups** across different protocols. Do not pool timings without adjusting for task and arm changes.

In v0.5, restrict pairwise comparison to groups where *both arms passed*: v0.4 vs Efficiency **13/22 faster**, reported paired aggregate wall-time reduction **17.9%**; v0.4 vs No-BET **14/22 faster**, reduction **18.0%**. These are descriptive engineering results, not confidence intervals or statistically established general effects.

All four v0.5 Oracle failures came from the same `loss-boolean-string` task. Its prompt did not explicitly demand case-insensitive input, but the independent Oracle tested uppercase TRUE/FALSE. The mismatch makes those four outcomes specification-ambiguous; retain original grades (do not retroactively reclassify them).

## What this supports

v0.4 defaults to **NORMAL**, chooses a bounded **BET** only if it could avoid substantial investigation, and **ABSTAINS** without repository edits when behavior already meets requirements. Average measured wall time was lower than the tested baselines in both held-out cohorts, but v0.4 did not win every task pair.

The No-BET ablation is an informative comparison, **not evidence that a BET alone caused the speed difference**. Agents in other arms may also perform diagnostic probes. Task intent labels are not observations of BET/CUT LOSS behavior; automatic trace labels were incomplete. Token accounting was incomplete (v0.5: complete input/output counts 2/24 Efficiency, 0/24 v0.4, 0/24 No-BET). Do not claim token savings, dollar savings, or external validity.

## Reproducibility and audit trail

- Frozen experiment branch: [v0.4 held-out](https://github.com/tc3oliver/skills/tree/feat/betfirst-v04-heldout-muse/betfirst/experiments)
- Frozen causal follow-up branch: [v0.5 ablation](https://github.com/tc3oliver/skills/tree/feat/betfirst-causal-v05/betfirst/experiments)
- [v0.4 protocol](https://github.com/tc3oliver/skills/blob/feat/betfirst-v04-heldout-muse/betfirst/experiments/V04_PROSPECTIVE.md)
- [v0.5 protocol](https://github.com/tc3oliver/skills/blob/feat/betfirst-causal-v05/betfirst/experiments/V05_CAUSAL.md)

The local runs completed on 2026-10-11; the v0.5 output directory reported by the operator was `run-20261011-200535`. Early v0.5 attempts had a workspace-guard prefix false positive, then a discovery/Oracle import flaw; those were repaired and the **fresh** 72-session cohort above was executed. Invalid aborted runs were excluded.

## Historical negative evidence

A first low-uncertainty exploratory pilot found BetFirst slower than Efficiency by 37.1% on nine sessions; an earlier less-contaminated v0.3 cohort had a +15.7% median paired wall-time change on 21 both-PASS comparisons. The v0.4 redesign was motivated partly by this overhead. See [full experiment history](./EXPERIMENT_HISTORY.md).

**Release claim:** selective cheap experiments are promising and practical on these synthetic tasks; universal speedup, causal mechanism and monetary/token savings remain unproven.

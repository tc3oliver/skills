# BetFirst

> **Make Cheap Bets. Win Big. Lose Small.**

**Your coding agent spent ten minutes investigating what a ten-second test could have settled.**

BetFirst is a small, portable coding-agent Skill that looks for **asymmetric bets**: a tiny, reversible experiment with a potentially large payoff in saved investigation. When a bet loses, it stops quickly, keeps the evidence, and returns to normal development. It does not skip final validation.

**Claude Code first. Pi compatible. Zero runtime dependencies.**

**Status: experimental (v0.1).** The mechanism has a decision-theoretic rationale, but **no BetFirst speedup or token-saving claim is established yet**. See [Evaluation](evals/README.md) for how to measure it.

## The behavior

```text
Meaningful uncertainty
         |
  Cheap falsifiable probe?
  Safe rollback / bounded downside?
  Large avoided investigation?
         |
      no | yes
         |  \
     NORMAL  BET
                |
         decisive evidence?
          /          \
        WIN         CUT LOSS
         |              |
    keep evidence   stop, restore
    skip dead work  preserve evidence
         |              |
         +---- normal correctness gate
```

**SPOT → CAP → BET → WIN / CUT LOSS.** When there is no actual need to change anything, **ABSTAIN**. A bet is an early diagnostic shortcut, **not** a permission to guess the fix.

Typical opportunities: isolate an FFmpeg argument using a tiny file, test a serializer against one synthetic payload, reproduce a CLI failure with a one-command fixture, or check a narrow build hypothesis.

Bad bets: unbounded testing, destructive Git cleanup, overlapping uncommitted work, production mutations, credentials, remote side effects, and experiments without objective signals. These go through normal analysis instead.

## Install and use

### Claude Code — plugin (existing repository distribution)

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

Run `/tc3oliver-skills:betfirst` explicitly, or ask Claude to use BetFirst while implementing a task. The Skill is also eligible for automatic discovery from its description. It does **not** auto-run a separate background agent or add extra hooks.

### Portable installation (Claude Code; also discoverable by Pi)

```bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
```

This route places a canonical global copy in the Agent Skills directory used by the installer. Pi discovers global `~/.agents/skills/` by default; run `/skill:betfirst` in Pi. For Pi-only installations, place the `betfirst/` folder under `~/.pi/agent/skills/betfirst/` instead.

**Choose one Claude installation route** (plugin or Agent Skills CLI) to avoid duplicate entries. Pi and Claude load the same portable `SKILL.md`; there is no runtime-specific fork.

### Sample task prompt

```text
Use BetFirst while fixing the FFmpeg subtitle failure.
If a cheap reversible test can eliminate extensive investigation,
take it; if it fails, cut the loss and diagnose normally.
Preserve my existing changes and complete normal final validation.
```

BetFirst is a policy for *how* to explore within a coding task. It is compatible with the existing `diagnosing-bugs` Skill: use BET to find a faster reproducible feedback loop, not to skip that Skill's diagnosis or regression requirements. It never overrides the repository's acceptance criteria or Definition of Done.

## Why could this work?

An agent pays for reasoning, file reads, long tool outputs, tool latency, and repeated tests. More investigation is useful **only when the value of the additional information exceeds its cost**. A bounded, objective probe can buy that information more cheaply than broad exploration.

This is grounded in **rational metareasoning** (the value of computation) and related work on **cost-aware exploration**. A 2026 coding-agent study also documents avoidable tool and workflow costs, including reductions from carefully designed Skills. These findings motivate BetFirst; they do **not** prove that BetFirst itself is faster.

The core expected-saving model for **one** resource is:

```text
E[saved] = p * S - (1 - p) * L - H
break-even p > (L + H) / (S + L)
```

- `p`: measured (not invented) success probability in a comparable task class.
- `S`: resource saved by a successful bet versus normal execution.
- `L`: additional loss on failure, **including safe cleanup and fallback**.
- `H`: overhead of invoking/deciding under the betting policy.

For illustration **only**, if success saves 9 minutes, failure loses 1 minute, and policy overhead is included in those measurements, break-even success probability is **10%**. Time and tokens must be evaluated **separately**; a faster run can still use more tokens or cost more money.

In actual operation the model should **not** fabricate `p`, estimate every action numerically, or spend more tokens calculating whether to bet than the probe would cost. BetFirst uses low-overhead qualitative gating first; calibration can follow from real measurements.

### Relevant sources

- Russell & Wefald, *Principles of Metareasoning* (1991): https://doi.org/10.1016/0004-3702(91)90015-C
- *Calibrate-Then-Act: Cost-Aware Exploration in LLM Agents* (2026): https://arxiv.org/abs/2602.16699
- *Analyzing and Mitigating Cost-Inefficient Behaviors in Coding Agents* (2026): https://arxiv.org/abs/2609.30725
- Matt Pocock, *writing-for-agents* (guidance on compact leading words, context pointers and non-redundant instructions): https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents

BetFirst's wording and policy are original to this repository; these works are references, not copied Skill implementations.

## When it wins, when it loses

| Example | Outcome | Expected action |
| --- | --- | --- |
| FFmpeg path escaping with tiny fixture | **WIN candidate** | Probe, fix only if evidence is decisive, then test the real renderer |
| TTS resample probe fails to change the artifact | **CUT LOSS** | Stop after the first disproven hypothesis; preserve observation |
| Shared production database needs mutation | **NORMAL** | Never speculate against irreversible state |
| Acceptance criteria already satisfied | **ABSTAIN** | Do not change working code to create a bet |
| Dirty worktree overlaps candidate edit | **NORMAL / read-only probe** | Never destroy user changes |

See [decision examples](references/examples.md) for precise conditions and failure signals.

## Evidence and evaluation

**The Skill is not a telemetry collector.** Routine coding should not pay for extra logging or worktrees. Benchmarking should use independent session telemetry and acceptance tests.

The included [evaluation protocol](evals/README.md), [qualitative cases](evals/cases.json), and stdlib [CSV analyzer](scripts/analyze_runs.py) support:

1. `baseline`: the original agent without BetFirst.
2. `efficiency`: basic concise/no-redundant-work rules.
3. `betfirst`: the same efficiency rules plus the betting decision policy.

Use identical tasks and clean start commits, matched repetitions, independent success checks, and real wall-clock plus token/cache/API-cost measurements. Include failed tasks and all fallback overhead. No invented usage and no success-only cherry-picking.

```bash
python3 -m unittest discover -s betfirst/tests
python3 betfirst/scripts/analyze_runs.py path/to/measured-runs.csv
```

The analyzer reports paired time, gross-token and USD-cost savings, with `null` for incomplete telemetry. It is **not** a benchmark runner and does not claim any results until real run data are provided.

## Roadmap

- **v0.1 (this Skill):** portable policy, bounded failure, qualitative cases, repeatable analysis protocol.
- **v0.2:** collect real Claude Code and Pi task sessions, quantify false/missed bets and fallback overhead, compare against baseline and efficiency control.
- **v1.0:** publish reproducible cross-task results; only add runtime instrumentation or enforcement where measured failures justify it.

## License

MIT, under the repository's license.

<p align="center"><a href="./README.md">English</a> · <a href="./README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="./assets/hero.svg" alt="BetFirst: Make cheap bets, skip expensive guesses. A small probe finds a verified path through complex exploration." width="1000">
</p>

# BetFirst

### Stop exploring blindly. Test the one thing that matters.

**BetFirst** is a lightweight, cost-aware decision Skill for coding agents. Before diving into a large investigation, it looks for a **small, falsifiable, reversible probe** that could settle the uncertainty. If the probe loses, **stop early** and return to normal debugging.

No daemon. No extra agent. No required telemetry. **And no skipped verification.**

**Works with Claude Code and Pi** · Portable `SKILL.md` · Experimental v0.2

## Get started in 30 seconds

**Claude Code — portable Skill**

```bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
```

Then ask your agent:

```text
Use BetFirst to fix this issue. If one cheap, reversible probe could
resolve the uncertainty, try it first. If not, work normally.
Preserve my changes and run the required final checks.
```

Prefer Claude Code plugins? Use `/plugin marketplace add tc3oliver/skills`, then `/plugin install tc3oliver-skills` and invoke `/tc3oliver-skills:betfirst`. **Choose one installation method**, not both.

## What changes?

<p align="center">
  <img src="./assets/probe-loop.gif" width="760" alt="Illustrative animation: broad exploration checks many steps while BetFirst tries a bounded probe, learns, then verifies. Not a recording or a performance benchmark.">
</p>

<sub>Illustrative animation of a possible workflow, **not a real Agent trace or measured speedup**. [View static comparison](./assets/before-after.svg).</sub>

Instead of always reading another ten files, the agent asks one question:

> **Can a tiny experiment rule out the expensive wrong path?**

| Situation | BetFirst's move |
| --- | --- |
| A cheap, safe test can distinguish competing explanations | **BET** — run it with a clear stop condition |
| The test is risky, ambiguous, or more expensive than just doing the work | **NORMAL** — continue standard development |
| The behavior already satisfies the request | **ABSTAIN** — leave correct code alone |
| The bet fails or becomes inconclusive | **CUT LOSS** — keep the evidence, stop probing, proceed normally |

### Example: a subtitle path bug

*Illustrative scenario, not a claimed benchmark run.*

```text
Problem     Subtitle rendering breaks for Windows drive paths.
Hypothesis  The drive-colon escaping is wrong.
Probe       Try one representative path with the smallest filter call.
Observe     Reproduced: the colon needs escaping.
Fix         Change only the path transformation, then run full validation.
```

The upside is less wasted investigation. The rule is equally important when **not** to bet: never gamble with production writes, credentials, destructive commands, or a test that cannot be bounded.

## How it works

**SPOT → CAP → BET → WIN / CUT LOSS.**

**SPOT** a concrete uncertainty. **CAP** the possible time and rollback cost. **BET** with one safe, falsifiable probe. **WIN** only with evidence and final tests; otherwise **CUT LOSS** and return to NORMAL. A probe does not replace root-cause analysis or the Definition of Done.

[See the complete decision flow →](./assets/decision-flow.svg) · [Understand the reasoning →](./docs/WHY_BETFIRST.md)

## Fits your existing agent workflow

**Claude Code.** Install through the plugin or the Agent Skills CLI above. Invoke it explicitly, or let compatible discovery select it when relevant.

**Pi.** Put the complete `betfirst/` directory where Pi discovers Skills (for example `~/.pi/agent/skills/betfirst/`), and invoke `/skill:betfirst`. The core `SKILL.md` does not contain Claude-only runtime commands.

**Other Skill-compatible agents.** Read the portable `SKILL.md` as an agent instruction; actual automatic discovery depends on your agent. BetFirst does not need Backlog, Claude Team Kit, or any specific task manager.

## Early evidence. Full results, not just the wins.

A small local Qwen/oMLX study found that BetFirst was **slower on three simple tasks**; on **two diagnostic tasks repeated three times**, it used **33.8% less wall time** and **38.0% fewer gross tokens** than Efficiency-only, with both arms passing 6/6. These **exploratory observations are not general speedup or causal claims**.

The larger **12-task / 108-session Evaluation v3** is the final preregistered release study; **results are pending**, and positive or negative outcomes will be published.

[Full experimental history →](./experiments/EXPERIMENT_HISTORY.md) · [v3 protocol →](./experiments/V3_PROTOCOL.md)

## Go deeper

[Decision examples](./references/examples.md) · [Evaluation method](./evals/README.md) · [Source Skill](./SKILL.md) · [Changelog](./CHANGELOG.md)

Have a reproducible case where an agent explores too much—or bets when it shouldn't? Open an issue with the task, expected behavior and observed outcome. **Spend less on uncertainty, never less on correctness.**

MIT License.

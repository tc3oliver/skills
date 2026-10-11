# AI Coding Skills

Small, portable Skills for Claude Code, Pi, Codex and OpenCode. Work with evidence, keep state only when needed, and avoid unnecessary agent overhead.

## Featured: BetFirst

<p align="center">
  <a href="./betfirst/"><img src="./betfirst/assets/hero.svg" alt="BetFirst — Make Cheap Bets. Win Big. Lose Small." width="860"></a>
</p>

**Make Cheap Bets. Win Big. Lose Small.** Your coding agent is already making bets—on root causes, files, and fixes. **BetFirst teaches it when to bet, when to fold, and when not to bet at all.** Tiny falsifiable probes. Bounded downside. Verified code—without another runtime, team, or mandatory logging.

```bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
```

[Explore BetFirst →](./betfirst/README.md) · [繁體中文 →](./betfirst/README.zh-TW.md) · [How it works →](./betfirst/docs/WHY_BETFIRST.md)

## Skills

| Skill | What it helps with |
| --- | --- |
| [**BetFirst**](./betfirst/) | **Make Cheap Bets. Win Big. Lose Small.** Bet on hypotheses, never on correctness. |
| [**Backlog**](./backlog/) | Persistent coding tasks, ready queue, and handoff evidence—without Backlog.md. [EN](./backlog/README.md) / [繁體中文](./backlog/README.zh-TW.md). |
| [audit-agent-instructions](./audit-agent-instructions/) | Find duplication, instruction drift and excessive context. |
| [diagnosing-bugs](./diagnosing-bugs/) | Reproducible debugging and focused regression tests. |
| [writing-for-agents](./writing-for-agents/) | Clearer, more efficient instructions for coding agents. |
| [skill-optimizer](./skill-optimizer/) | Skill routing, prompt size and reliability. |
| [resolving-merge-conflicts](./resolving-merge-conflicts/) | Resolve conflicting code without losing either side's intent. |

## Install

**Agent Skills CLI:**
```bash
npx skills add tc3oliver/skills
```

**Claude Code plugin:**
```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

Plugin entries use `/tc3oliver-skills:betfirst`, `/tc3oliver-skills:backlog`, etc. Portable Skill installations expose each `SKILL.md` through the compatible agent's discovery system; avoid installing the same Skill twice.

## Build your own workflow

**BetFirst** decides whether a small probe is worth the risk. **Backlog** owns persistent tasks and evidence. [Claude Team Kit](https://github.com/tc3oliver/claude-team-kit) manages explicit native Agent Teams. They work independently or together without a new orchestrator. [Composition guide →](./docs/COMPOSITION.md)

Backlog is a lightweight persistence CLI, not a background orchestration service:

```text
/backlog add "Build OAuth login"
/backlog next
/backlog do BL-7E18C75F3D31A0B2
/backlog status
```

[Backlog CLI reference →](./backlog/references/cli.md) · [Legacy v1.6 archive →](https://github.com/tc3oliver/skills/tree/archive/backlog-workflow-v1.6.0/backlog-workflow)

## Evidence, not hype

BetFirst's preliminary local study includes a **negative result on simple tasks** and an encouraging but **small two-task diagnostic result**. Neither establishes universal or causal speedups. The preregistered [Evaluation v3 study](./betfirst/experiments/V3_PROTOCOL.md) will publish full results, good or bad. [Experiment history →](./betfirst/experiments/EXPERIMENT_HISTORY.md)

## Verify

```bash
python3 -m unittest discover -s backlog/tests -v
python3 -m unittest discover -s betfirst/tests -v
```

MIT License. Existing upstream material and adapted sources retain their original notices.

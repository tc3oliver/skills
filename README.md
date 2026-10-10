# AI Coding Skills

Portable skills for Claude Code, Pi, Codex and OpenCode. Small, composable tools: track work only when needed, explore cheaply when safe, and verify what actually happened.

## Skills

| Skill | Purpose |
| --- | --- |
| [`backlog`](backlog/) | **Persistent coding tasks without Backlog.md.** Ready queue, dependencies, cross-session handoffs, completion evidence; no workflow framework. [EN](backlog/README.md) / [繁體中文](backlog/README.zh-TW.md). |
| [`betfirst`](betfirst/) | **Make cheap bets. Win big. Lose small.** Bounded reversible probes. [EN](betfirst/README.md) / [繁體中文](betfirst/README.zh-TW.md). |
| [`audit-agent-instructions`](audit-agent-instructions/) | Audit agent instruction files for duplication, drift and excessive context. |
| [`diagnosing-bugs`](diagnosing-bugs/) | Evidence-based debugging and regression tests. |
| [`writing-for-agents`](writing-for-agents/) | Write clear, concise, context-efficient agent instructions. |
| [`skill-optimizer`](skill-optimizer/) | Improve Skill routing, context use and reliability. |
| [`resolving-merge-conflicts`](resolving-merge-conflicts/) | Resolve Git conflicts without losing either side's intent. |

## Installation

Agent Skills CLI:

```bash
npx skills add tc3oliver/skills
```

Claude Code plugin:

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

Installed plugin Skills appear as `/tc3oliver-skills:backlog`, `/tc3oliver-skills:betfirst`, etc. Pi and other compatible agents load the portable `SKILL.md` directly.

## Composing Skills

Backlog (durable work), BetFirst (optional cheap probes), and [Claude Team Kit](https://github.com/tc3oliver/claude-team-kit) (explicit native teams) can run independently or together. No new router, installer or shared runtime is required. See the concise [composition contract](docs/COMPOSITION.md) for ownership, optional handoff, and stopping rules.

## Backlog v2

Backlog is a **small persistence layer**, not an execution orchestrator. The skill does not activate on ordinary coding work; it records and resumes tasks only when the user wants persistent work tracking. A standard-library Python CLI manages `.backlog/tasks/` and `.backlog/archive/{done,cancelled}/YYYY-MM/`. The ready queue reads only task metadata, and `show ID` retrieves one full task.

```text
/backlog add "Build OAuth login"
/backlog next
/backlog do BL-7E18C75F3D31A0B2
/backlog status
```

Invoke syntax is agent-specific. For direct CLI use and command flags see [Backlog README](backlog/README.md) and [CLI reference](backlog/references/cli.md).

**Boundaries:** [BetFirst](betfirst/) is responsible for safe, low-cost probes. [Claude Team Kit](https://github.com/tc3oliver/claude-team-kit) owns Agent Teams, bounded workers, reviews and team-local tasks. Backlog does not spawn teams, replicate worker tasks, or override either Skill's verification requirements.

### Legacy backlog-workflow v1.6

The old Backlog.md-dependent `backlog-workflow` was deliberately removed as a breaking change. No automatic migration is performed; existing project data remain untouched. Its source is preserved under Git branch [`archive/backlog-workflow-v1.6.0`](https://github.com/tc3oliver/skills/tree/archive/backlog-workflow-v1.6.0/backlog-workflow).

## Validation

```bash
python3 -m unittest discover -s backlog/tests -v
python3 -m unittest discover -s betfirst/tests -v
```

MIT license; adaptations and upstream sources retain their original notices.

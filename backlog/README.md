# Backlog v2

**Persistent tasks. Minimal context. Reliable progress.**

A small, portable Agent Skill for storing coding tasks in Git-friendly Markdown. No dependency on [Backlog.md](https://backlog.md), database, hooks, MCP, installer or background service. Python 3.11+ standard library only.

Unlike workflow frameworks, Backlog does not create teams, auto-start coding sessions, review your code, or replace your agent's implementation process. Use it only when work needs to survive sessions.

## Installation

```bash
npx skills add tc3oliver/skills --skill backlog
```

Or install the existing repository Claude Code plugin. For Pi, copy the complete `backlog/` directory to its discovered Skills location. The same `SKILL.md` is used on both.

## Usage

In a coding agent: `/backlog add "Build SSO login"`, `/backlog next`, `/backlog do BL-...`, or `/backlog status` (invocation syntax varies by agent).

First use creates `.backlog/` after an explicit `init`. The CLI itself can be used without a coding agent:

```bash
python3 <skill-dir>/scripts/backlog.py --root . init
python3 <skill-dir>/scripts/backlog.py --root . add "Add login" --goal "SSO login" --ac "Valid callback signs in" --priority P1
python3 <skill-dir>/scripts/backlog.py --root . next --limit 5
python3 <skill-dir>/scripts/backlog.py --root . status
python3 <skill-dir>/scripts/backlog.py --root . doctor
```

Only active task metadata is returned to `next`; only `show ID` loads one full task. Each task is a separate Markdown file. Completed/cancelled tasks move to monthly archives while preserving dependency history.

## Lifecycle

`inbox → todo → doing → done`, with `blocked` (recover to todo) and `cancelled` (terminal) alternatives. Only `todo` tasks whose dependencies are all `done` appear in the ready queue. Closing requires checked acceptance criteria and actual validation evidence. Unresolved requirements stay `inbox` rather than being invented.

A short `Handoff` saves files, verified progress and next steps. Resuming rechecks the codebase and tests; it never assumes stale output is still valid.

## Boundaries

- [BetFirst](../betfirst/): optional safe, cheap falsifiable probes. It never updates BL lifecycle or skips checks.
- [Claude Team Kit](https://github.com/tc3oliver/claude-team-kit): teams, worker orchestration, reviews and debugging. The CTK lead alone owns persisted BL updates and closes tasks only after integrating/verifying the team output.
- Ordinary coding without persistent task intent must **not** activate Backlog.

## Legacy v1.6

The former `backlog-workflow` depended on the external Backlog.md task engine and installed multi-stage project policies. It is replaced, not migrated. Existing `.agent-workflow` and Backlog.md task data in consumer projects are **not** automatically changed. The historical source remains accessible in Git history and the `archive/backlog-workflow-v1.6.0` branch.

## Development

```bash
python3 -m unittest discover -s backlog/tests -v
python3 -m unittest discover -s betfirst/tests
```

See [CLI reference](references/cli.md) for the on-disk format, JSON commands, atomicity and concurrency limits.

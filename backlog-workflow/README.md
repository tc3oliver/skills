# backlog-workflow

A Claude Code skill that installs a versioned, task-driven development workflow
as a **policy and orchestration layer** over [Backlog.md](https://backlog.md).

## Architecture

```text
Backlog.md       = task/workflow engine (schema, lifecycle, AC, DoD, plan,
                   notes, final summary, dependencies, CLI, JSON interface,
                   canonical agent instructions)
backlog-workflow = development policy / orchestration on top of Backlog.md
PROJECT.md       = repository-specific configuration
PRD/spec         = product truth
```

Backlog.md canonical instructions (`backlog instructions ...`) are the single
source of truth for Backlog mechanics. This workflow does not duplicate them —
it adds development policy: execution modes, requirement authority, task
decomposition policy, approval boundaries, grilling/decision policy, blocker
policy, the four completion conditions, and deterministic automatic task
selection.

It answers a specific problem: coding agents drift. They start implementing
before the requirement is settled, invent validation commands that do not exist,
mark work done without evidence, and quietly keep going when they should have
stopped to ask. This workflow puts those boundaries in files the agent must read.

## What you get

`/backlog-workflow apply` installs three project skills and a workflow spec:

| Command | What it does |
|---|---|
| `/backlog-plan <requirement or PRD path>` | Aligns the requirement and decomposes it into Backlog.md tasks. Writes no product code, no Implementation Plan. |
| `/backlog-run <TASK-ID>` | Executes exactly one named task with a JIT Implementation Plan, then stops. |
| `/backlog-auto [TASK-ID]` | Automatic execution. Selects dependency-ready tasks deterministically. Only runs when you explicitly ask for it. |

The default mode is manual. "Continue development" does not start automatic
execution — only an explicit `/backlog-auto` does.

The command name `backlog` is reserved for the Backlog.md CLI (and for an
optional MCP server you configure yourself). This package never introduces a
`/backlog` skill.

## Core rules it enforces

- **Backlog.md owns the mechanics; this workflow owns the policy.** Task mutation
  goes through the Backlog.md CLI; automation uses Backlog.md JSON output
  (`backlog task list --json`, `backlog task <TASK-ID> --json`).
- **Requirements and tasks are separate sources of truth.** PRDs and specs own
  product intent; Backlog.md owns decomposition, status, and evidence. A task
  may not silently reinterpret a requirement.
- **Planning stops at decomposition; implementation plans are JIT.** `/backlog-plan`
  creates tasks without an Implementation Plan. `/backlog-run` researches the
  current codebase and records the plan before coding.
- **A task is Done only when four conditions hold:** acceptance criteria pass,
  required checks pass, documentation is synchronized, and the task record
  contains validation evidence.
- **Detected-as-absent commands are never invented.** If your project has no
  linter, `.agent-workflow/PROJECT.md` records `not detected` and the agent must
  say so rather than run a made-up command.
- **Missing product intent is a blocker, not a guess.** In manual mode the agent
  asks; in automatic mode it records evidence and stops.

## Requirements

- Claude Code, for the slash commands
- Node.js with `npx`, for the Backlog.md CLI
- Python 3.9+, for the installer (no third-party packages).
  Verified on 3.11 and 3.12; 3.9 and 3.10 are supported by syntax but untested.

MCP is **not** required. Backlog.md supports an optional MCP server, but
backlog-workflow runs entirely on the CLI and never installs or configures MCP.

At install, the Backlog.md CLI is **verified**, not just detected: each
candidate is probed read-only and accepted only if it is Backlog.md (a bare
`npx backlog` otherwise resolves to an unrelated package). If no candidate
verifies, `apply`/`upgrade` fail with a clear error rather than recording an
unverified command.

## Install

See [INSTALL.md](INSTALL.md).

## Usage

```text
/backlog-workflow apply          # install into the current project
/backlog-plan docs/PRD.md        # align requirements, create tasks (no impl plan)
/backlog-run TASK-1              # JIT-plan, execute one task, then stop
```

`/backlog-workflow audit` is a read-only drift check that repairs nothing and
exits nonzero when something is off. `/backlog-workflow upgrade` refreshes the
managed files in place and migrates the deprecated `TASK-TEMPLATE.md`.

## What it writes into your project

Managed by this workflow, replaced on `upgrade`:

```
.agent-workflow/{VERSION,config.yml,WORKFLOW.md,TASK-POLICY.md}
.claude/skills/{backlog-plan,backlog-run,backlog-auto,grilling}/
```

Created once, then yours to maintain:

```
.agent-workflow/PROJECT.md       # detected commands, paths, and constraints
```

A single managed block is inserted into `CLAUDE.md` (or `.claude/CLAUDE.md` when
only that one exists) **and** into `AGENTS.md`. `AGENTS.md` is created when
absent so cross-agent tools discover the workflow. Everything outside the block
is preserved.

If a Backlog.md workspace does not exist yet, `apply` creates one
non-interactively before installing anything.

### What it will not touch

`README.md`, existing Backlog.md tasks and configuration, PRDs, requirement
matrices, ADRs, and any instruction file it does not manage. If an unmanaged
file already occupies a managed path, `apply` reports the conflict and stops
without writing anything.

## Other coding agents

The slash commands are Claude Code specific; the process is not.
`.agent-workflow/WORKFLOW.md` and `.agent-workflow/PROJECT.md` are plain Markdown,
and tasks are driven through the Backlog.md CLI. Any agent that can read those
files and run a shell command can follow the same workflow. `AGENTS.md` is always
managed so agents that read it pick up the workflow automatically.

## Development

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_package.py
```

## License

MIT — see [LICENSE](LICENSE).

Bundles the `grilling` skill by Matt Pocock, used under the MIT License; its
license text ships with the skill at
`templates/project/.claude/skills/grilling/LICENSE`.

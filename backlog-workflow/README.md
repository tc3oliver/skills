# backlog-workflow

A Claude Code skill that installs a versioned, task-driven development workflow
built on [Backlog.md](https://backlog.md) into a project.

It answers a specific problem: coding agents drift. They start implementing
before the requirement is settled, invent validation commands that do not exist,
mark work done without evidence, and quietly keep going when they should have
stopped to ask. This workflow puts those boundaries in files the agent must read.

## What you get

`/backlog-workflow apply` installs three project skills and a workflow spec:

| Command | What it does |
|---|---|
| `/backlog-plan <requirement or PRD path>` | Aligns the requirement and creates Backlog.md tasks. Writes no product code. |
| `/backlog-run <TASK-ID>` | Executes exactly one named task, then stops. |
| `/backlog-auto [TASK-ID]` | Automatic execution. Only runs when you explicitly ask for it. |

The default mode is manual. "Continue development" does not start automatic
execution — only an explicit `/backlog-auto` does.

## Core rules it enforces

- **Requirements and tasks are separate sources of truth.** PRDs and specs own
  product intent; Backlog.md owns decomposition, status, and evidence. A task
  may not silently reinterpret a requirement.
- **A task is Done only when four conditions hold:** acceptance criteria pass,
  required checks pass, documentation is synchronized, and the task record
  contains validation evidence.
- **Detected-as-absent commands are never invented.** If your project has no
  linter, `.agent-workflow/PROJECT.md` records `not detected` and the agent must
  say so rather than run a made-up command.
- **Missing product intent is a blocker, not a guess.** In manual mode the agent
  asks; in automatic mode it marks the task `Blocked` and stops.

## Requirements

- Claude Code, for the slash commands
- Node.js with `npx`, for the Backlog.md CLI
- Python 3.9+, for the installer (no third-party packages).
  Verified on 3.11 and 3.12; 3.9 and 3.10 are supported by syntax but untested.

## Install

See [INSTALL.md](INSTALL.md).

## Usage

```text
/backlog-workflow apply          # install into the current project
/backlog-plan docs/PRD.md        # align requirements, create tasks
/backlog-run TASK-1              # execute one task, then stop
```

`/backlog-workflow audit` is a read-only drift check that repairs nothing and
exits nonzero when something is off. `/backlog-workflow upgrade` refreshes the
managed files in place.

## What it writes into your project

Managed by this workflow, replaced on `upgrade`:

```
.agent-workflow/{VERSION,config.yml,WORKFLOW.md,TASK-TEMPLATE.md}
.claude/skills/{backlog-plan,backlog-run,backlog-auto,grilling}/
```

Created once, then yours to maintain:

```
.agent-workflow/PROJECT.md       # detected commands, paths, and constraints
```

A single managed block is inserted into `CLAUDE.md`, and into `AGENTS.md` when
that file already exists. Everything outside the block is preserved.

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
files and run a shell command can follow the same workflow. See the notes in
[INSTALL.md](INSTALL.md) for opting in via `AGENTS.md`.

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

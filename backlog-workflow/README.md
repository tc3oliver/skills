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
decomposition policy, decomposition review, approval boundaries,
grilling/decision policy, blocker policy, and the Canonical Completion Gate.

It answers a specific problem: coding agents drift. They start implementing
before the requirement is settled, invent validation commands that do not exist,
mark work done without evidence, and quietly keep going when they should have
stopped to ask. This workflow puts those boundaries in files the agent must read.

## What you get

`/backlog-workflow apply` installs four project skills and a workflow spec:

| Command | What it does |
|---|---|
| `/backlog-plan <requirement or PRD path>` | Aligns the requirement and decomposes it into Backlog.md tasks. Writes no product code, no Implementation Plan. |
| `/backlog-review [requirement source]` | Checks whether completing every planned task would actually satisfy the requirement source. Read-only; asks before changing anything. |
| `/backlog-run <TASK-ID>` | Executes exactly one named task with a JIT Implementation Plan, then stops. |
| `/backlog-auto [TASK-ID]` | Automatic execution. Selects dependency-ready tasks deterministically. Only runs when you explicitly ask for it. |

The default mode is manual. "Continue development" does not start automatic
execution — only an explicit `/backlog-auto` does.

### Reviewing the decomposition

Decomposition is the step where requirements quietly go missing: a PRD clause
maps to no task, an acceptance criterion is too vague to prove the thing it is
supposed to prove, or a task shows up that no requirement asked for.

`/backlog-review` is a separate pass that answers one question — *if every task
were completed to its acceptance criteria, would the requirement source be
satisfied?* It runs four checks: requirement coverage, acceptance-criteria
sufficiency, scope traceability (every task cites an authoritative source or a
decision record), and dependency integrity.

It is deliberately not part of `/backlog-plan`: the context that produced a
decomposition is the worst one to audit it, and the review is worth re-running
whenever tasks or requirements change. It never guesses — a requirement too
ambiguous to judge is reported as `Undetermined` and goes back to
`/backlog-plan`, not resolved on the spot. Nothing is created or edited until
you approve the proposed fix. `/backlog-auto` never runs it.

The command name `backlog` is reserved for the Backlog.md CLI (and for an
optional MCP server you configure yourself). This package never introduces a
`/backlog` skill.

Task content — title, description, Acceptance Criteria, Implementation Plan,
Implementation Notes, Final Summary — is written in the language you write
requirements in, so the Backlog.md board doesn't need translation to read. Code,
commands, and Backlog.md's own field names/status values stay as-is.

### Parallel automatic execution

`.agent-workflow/config.yml` sets `automatic.max_parallel_tasks: 1` by
default — `/backlog-auto` runs one task at a time, exactly as described above.
Raise it to run that many independent, dependency-ready tasks at once, each
isolated in its own `git worktree` and merged back sequentially once the whole
batch finishes.

It's a good fit when a project has several small, genuinely independent ready
tasks (different modules/files, no shared state) and you want to burn down the
backlog faster. It's a poor fit for tightly coupled tasks likely to touch the
same files — a merge conflict only blocks the one task involved, but you still
pay for wasted work if batches routinely collide. Start at `2` and watch how
often merges conflict before going higher.

The protocol lives in `.agent-workflow/PARALLEL.md`, which `/backlog-auto` reads
only when `max_parallel_tasks` is above 1. Three things it guarantees: the whole
non-ignored working tree must be clean before a batch starts (workers branch from
a commit, so uncommitted or untracked work is invisible to them — including your
uncommitted Backlog.md edits, which is why nothing is excluded); claims are
committed by staging the exact task paths reported by `backlog task <ID> --json`,
never a whole directory; and only workers that finished `Done` are merged — a
blocked worker's partial implementation stays on its branch while the base branch
records the blocked status.

## Core rules it enforces

- **Backlog.md owns the mechanics; this workflow owns the policy.** Task mutation
  goes through the Backlog.md CLI; automation uses Backlog.md JSON output
  (`backlog task list --json`, `backlog task <TASK-ID> --json`). Autonomous
  selection is the native
  `backlog task list --ready --status "<not-started status>" --sort priority --json`
  query, not a dependency graph rebuilt task by task. `--ready` on its own still
  returns claimed and blocked tasks, so the status filter is part of the query,
  not an optional extra.
- **Requirements and tasks are separate sources of truth.** PRDs and specs own
  product intent; Backlog.md owns decomposition, status, and evidence. A task
  may not silently reinterpret a requirement. One rule covers planning, review,
  and execution alike: every executable task has a non-empty native
  `documentation` naming an authoritative requirement source or a persisted
  decision record. Engineering rationale in the description or notes explains how
  a task is built; it is never the authority it is built from.
- **Planning stops at decomposition; implementation plans are JIT.** `/backlog-plan`
  creates tasks without an Implementation Plan. `/backlog-run` researches the
  current codebase and records the plan before coding.
- **The decomposition is reviewed by a separate pass.** `/backlog-review` checks
  coverage, acceptance-criteria sufficiency, scope traceability, and dependency
  integrity against the requirement source — planning never approves its own
  output.
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

### Upgrading from 1.4.0 or 1.4.1

**If you set `max_parallel_tasks` above 1 on 1.4.0 or 1.4.1, upgrade to 1.5.0.**
Those versions have a defect in the parallel claim protocol:

- The claim checkpoint committed the claims with `git add backlog`, assuming the
  Backlog.md directory is named `backlog/`. On a project using `.backlog/` or a
  custom directory that command fails with `pathspec 'backlog' did not match any
  files`, so the claims stay uncommitted and the batch merge then aborts with
  *"Your local changes would be overwritten by merge"* — for every task in the
  batch. 1.5.0 stages the exact path each claim wrote, read from
  `backlog task <TASK-ID> --json` (`.task.path`).
- The dirty-tree precondition excluded the Backlog.md directory, so a blanket
  claim commit could sweep up Backlog.md edits the user had in progress. 1.5.0
  requires the whole non-ignored working tree to be clean before a batch starts
  and stages only the claimed task files.
- A worker that ended `Blocked` had no defined merge behavior. 1.5.0 states it:
  only workers that finished `Done` are merged, and a blocked worker's partial
  implementation stays on its branch while the base branch records the blocked
  status.

Sequential `/backlog-auto` (the default `max_parallel_tasks: 1`) and
`/backlog-run` are unaffected by all three.

`/backlog-workflow upgrade` installs 1.5.0 in place, adds
`.agent-workflow/PARALLEL.md`, and preserves `PROJECT.md`, the status role
mapping, and `max_parallel_tasks`.

## Usage

```text
/backlog-workflow apply          # install into the current project
/backlog-plan docs/PRD.md        # align requirements, create tasks (no impl plan)
/backlog-review docs/PRD.md      # do those tasks actually cover the PRD?
/backlog-run TASK-1              # JIT-plan, execute one task, then stop
```

`/backlog-workflow audit` is a read-only drift check that repairs nothing and
exits nonzero when something is off. Besides managed-file integrity it checks the
status roles and every task's `documentation` references: a local path that no
longer resolves is reported with its task ID, while remote URLs and opaque
identifiers are left alone. `/backlog-workflow upgrade` refreshes the
managed files in place and migrates the deprecated `TASK-TEMPLATE.md`.

## What it writes into your project

Managed by this workflow, replaced on `upgrade`:

```
.agent-workflow/{VERSION,config.yml,WORKFLOW.md,PLAN.md,EXECUTION.md,AUTO.md,PARALLEL.md,TASK-POLICY.md}
.claude/skills/{backlog-plan,backlog-review,backlog-run,backlog-auto,grilling}/
```

`WORKFLOW.md` holds only the invariants every mode shares — responsibility
boundary, sources of truth, requirement traceability, decision policy, the
Canonical Completion Gate, task blockers — plus a routing table. The phase detail
lives in `PLAN.md` (planning and decomposition review), `EXECUTION.md` (running
one task), and `AUTO.md` (autonomous selection, blockers, concurrency). Each
skill reads the shared file and only the phase it is actually running, so
planning never pays for the merge protocol and `/backlog-run` never pays for the
review checks. `PARALLEL.md` goes one level further: no skill names it at all,
and `AUTO.md` points at it only when `max_parallel_tasks` is above 1 — the
default sequential run never loads the worktree protocol.

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

`README.md`, existing Backlog.md tasks, PRDs, requirement matrices, ADRs, and any
instruction file it does not manage. If an unmanaged file already occupies a
managed path, `apply` reports the conflict and stops without writing anything.

The one exception is a single additive edit to the Backlog.md config: if the
project has no status to park blocked tasks in, `Blocked` is inserted into
`statuses` before the terminal status. Existing statuses, their order, and every
other key are left alone, and a project that already has one (`On Hold`,
`Blocked`, …) is not modified at all. `/backlog-auto` selects on the not-started
status, so this is what stops a blocked task from being picked up again on the
next round — the guarantee is the status, not the agent remembering.

## Other coding agents

The slash commands are Claude Code specific; the process is not.
Everything under `.agent-workflow/` is plain Markdown, and tasks are driven
through the Backlog.md CLI. Any agent that can read `WORKFLOW.md`, follow its
routing table to the phase it needs, and run a shell command can follow the same
workflow. `AGENTS.md` is always
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

<!-- Managed by backlog-workflow 1.1.0 -->

# Backlog Development Workflow

This file defines **project development policy** and explicit **overrides** on top
of Backlog.md. It is not a reimplementation of Backlog.md.

## Responsibility boundary

Backlog.md canonical instructions define how Backlog.md itself is operated: the
task schema, lifecycle, Acceptance Criteria, Definition of Done, Implementation
Plan, Implementation Notes, Final Summary, dependencies, priority, status, the
CLI, and the JSON interface.

`.agent-workflow/WORKFLOW.md` defines project development policy and explicit
overrides on top of that workflow.

Do not duplicate upstream Backlog.md mechanics unless a local policy explicitly
overrides them. Load the relevant canonical instructions at the points indicated
below with the Backlog.md CLI recorded in `.agent-workflow/PROJECT.md`, for
example:

```bash
backlog instructions overview
backlog instructions task-creation
backlog instructions task-execution
backlog instructions task-finalization
```

Use Backlog.md native task fields for Acceptance Criteria, Definition of Done,
dependencies, Implementation Plan, Implementation Notes, and Final Summary. Use
the Backlog.md CLI (`backlog task ...`) for task mutation; do not directly parse
or rewrite `backlog/tasks/*.md` for normal task operations. For task discovery,
state, and dependency information in automation, prefer the structured JSON
interface (`backlog task list --json`, `backlog task <TASK-ID> --json`).

## Modes

The default mode is **manual**.

- Manual planning: `/backlog-plan <requirement, topic, or document path>`
- Manual execution: `/backlog-run <TASK-ID>`
- Automatic execution: `/backlog-auto [TASK-ID]`

The slash commands above are the Claude Code entry points. This process is not
Claude-specific: any coding agent can follow it by reading this file, the
canonical Backlog.md instructions, and the Backlog.md CLI recorded in
`.agent-workflow/PROJECT.md`. Where an agent has no slash commands, treat the
named sections below as the instruction to follow and honor the same mode
boundary.

Automatic mode starts only through an explicit request for automatic execution.
Requests such as "continue development" do not enable automatic mode.

Manual means planning and execution are separate user-triggered stages. It does
not mean waiting for approval after every engineering step.

## Sources of truth

- Backlog.md canonical instructions own Backlog mechanics (task schema, fields,
  lifecycle, CLI, JSON interface).
- PRDs, specifications, and requirement matrices define product intent, scope,
  and acceptance intent.
- A Backlog.md decision record (`backlog decision create`) captures a decision
  reached through `grilling` — its Context, Decision, and Consequences — and is
  the authoritative source for that decision from then on.
- `.agent-workflow/WORKFLOW.md` defines the development process and policy.
- `.agent-workflow/PROJECT.md` defines repository-specific commands, paths, and
  constraints.
- `CLAUDE.md` and `AGENTS.md` are the workflow entry points plus project rules
  that must not be missed.

A task must not silently introduce, remove, or reinterpret a product requirement.
Resolve conflicts in the authoritative requirement source before implementation.

A decision reached through `grilling` is not itself a requirement source until it
is written down. A choice confined to one task's implementation stays in that
task's record. A choice that will bind future tasks, or that this task's
Requirement source field would otherwise have no citable source for, must be
captured as a Backlog.md decision record before the task proceeds — see
"Recording a grilled decision" below.

## Backlog interface policy

The Backlog.md CLI is the default and required interface. MCP is supported by
Backlog.md but is optional and user-managed; this workflow does not install or
require it. Do not auto-install or auto-configure any MCP server, and never run
any command that registers an MCP server with a coding agent (no MCP add or
equivalent). The workflow must run completely in an environment that only has
the Backlog.md CLI.

Prefer Backlog.md CLI operations over direct task-file editing for all task
mutation.

### Command convention

In all command examples in this workflow, `backlog` is a placeholder for the
exact Backlog.md CLI command recorded in `.agent-workflow/PROJECT.md` (for
example `backlog`, `npx backlog`, or `npx backlog.md`). Run the recorded
command verbatim; do not assume a bare `backlog` exists when PROJECT.md records
`npx backlog.md`.

## Task Ready Gate

A task may enter the active status only when all applicable items are clear. Use
the project policy fields in `.agent-workflow/TASK-POLICY.md` to capture these;
use Backlog.md native fields where Backlog.md owns them.

- Requirement source or technical rationale
- Goal
- Scope
- Out of Scope
- Stable implementation constraints
- Dependencies (Backlog.md native field)
- Objectively verifiable Acceptance Criteria (Backlog.md native field)
- Validation method or commands
- Test requirements
- Security impact
- Data or schema impact
- API or compatibility impact
- Documentation impact
- Migration or rollback impact

A task should fit one reviewable change. Missing product intent is a blocker.
Engineering details that can be safely determined from repository evidence are
not blockers.

## Manual planning

`/backlog-plan` performs only requirement alignment and task decomposition:

1. Load `backlog instructions overview` and `backlog instructions task-creation`.
2. Read requirement sources, the requirement matrix when applicable,
   architecture/decision records when applicable, project instructions, relevant
   repository structure, and existing Backlog.md tasks.
3. Resolve factual questions from the repository instead of asking the user.
4. Invoke the project `grilling` skill only when product intent, scope,
   acceptance behavior, or an irreversible decision cannot be resolved from an
   authoritative source.
5. Reach shared understanding before creating tasks.
6. Record each grilled decision per "Recording a grilled decision" below, then
   update any other authoritative requirement documents the confirmed decisions
   require.
7. Decompose work into small Backlog.md tasks with explicit dependencies,
   Acceptance Criteria, priority, and the workflow Definition of Done. Create
   tasks through the Backlog.md CLI and preserve existing IDs and history. Bind
   the completion policy by adding the four Definition of Done items (see
   "Completion conditions") with one repeatable `--dod` flag per item. A task
   whose Requirement source is a grilled decision cites the decision record
   created in step 6.

Planning stops at decomposition. It must not:

- do task-level implementation research,
- produce an Implementation Plan (Implementation Plans are JIT; see "Manual
  execution"),
- decide function/class-level implementation,
- start product implementation, or
- set any task to the active status.

Report the plan and stop.

### Recording a grilled decision

After `grilling` reaches shared understanding, decide whether the decision needs
a citable source:

- **Confined to the current task's implementation** — record it directly in that
  task; no decision record needed.
- **Binds more than the current task, or a task's Requirement source would
  otherwise have nothing to cite** — create a Backlog.md decision record
  (`backlog decision create "<title>"`) before creating or updating any task
  that depends on it. Fill its three sections: **Context** (the question and why
  it was open), **Decision** (the answer confirmed with the user),
  **Consequences** (what this rules out or commits future work to). Create one
  decision record per distinct decision.

A task citing a grilled decision writes
`Requirement source: decision-<id> (<decision title>)` — the same citation form
used for any other requirement source. Multiple tasks may cite the same decision
record; it is not owned by any one of them.

A decision record and a doc serve different scopes — use both when the situation
calls for it:

- **Decision record** — one specific choice, fixed when made: the question, the
  answer, the consequences.
- **Doc** (`backlog doc create`, typically `--type specification` or `guide`) —
  longer-form living material meant to stay current.

If a grilled decision requires updating or extending an existing specification,
requirement matrix, or other authoritative doc, do both: create the decision
record for what was decided and why, and update the doc for the resulting content.

## Manual execution

`/backlog-run <TASK-ID>` runs exactly one task.

Without a task ID:

- use the Backlog.md structured interface (`backlog task list --json`, plus
  `backlog task <TASK-ID> --json` for dependency detail) to list dependency-ready
  tasks,
- do not modify any task, and
- do not modify code; then stop.

With a task ID, follow the manual-execution flow:

1. Load `backlog instructions overview` and `backlog instructions task-execution`.
2. Read the task and its requirement source; verify the task is executable
   (Task Ready Gate clear). Ensure the native Definition of Done contains the
   canonical completion-policy items (see "Native Definition of Done binding");
   append any missing item with `backlog task edit <TASK-ID> --dod "<item>"`
   before proceeding.
3. Research the **current** codebase, tests, configuration, and history. Do not
   rely on an approach proposed when the task was created.
4. Write the JIT Implementation Plan into the Backlog.md native field
   (`backlog task edit <TASK-ID> --plan "..."`) **before** coding.
5. Set the task to the active status (`backlog task edit <TASK-ID> -s "<active
   status>"`).
6. Implement the complete task.
7. Run relevant validation, tests, lint, typecheck, and build.
8. Verify every Acceptance Criterion with objective evidence, then check the
   matching Definition of Done items (`backlog task edit <TASK-ID> --check-dod
   <index>`).
9. Synchronize documentation and the Requirement Matrix when applicable.
10. Record Implementation Notes, validation evidence, and Final Summary in the
    task's native fields.
11. Follow the repository delivery flow when available: create a PR/MR, address
    CI/review findings, and merge.
12. Mark the task `Done` (`backlog instructions task-finalization`) when the four
    completion conditions are met.
13. Report and stop. Do not select another task.

### Important approval override

Backlog.md canonical task-execution instructions may recommend presenting the
Implementation Plan and waiting for explicit approval before implementation when
the plan contains a material decision or when plan review is requested.

This manual workflow intentionally defines a different approval boundary.
Invoking `/backlog-run <TASK-ID>` means the user has authorized that task to
proceed through JIT planning, implementation, and validation. The agent **must**
still record the Implementation Plan before coding, but **must not** pause only
to ask for another implementation-plan approval.

Stop only when a true blocker or an unresolved decision covered by the blocker
policy below is discovered. This does not weaken the grilling/blocker
safeguards: `grilling` is still invoked for unresolved product decisions or
irreversible choices, and the outcome is recorded per "Recording a grilled
decision" before continuing.

## Automatic execution

`/backlog-auto <TASK-ID>` executes exactly that task and stops.

`/backlog-auto` without a task ID repeatedly selects and executes one task,
finalizing it fully before selecting the next, until no executable task remains
or a true blocker occurs.

Task selection is deterministic and based on structured Backlog.md data, never
on parsing Markdown task files:

1. Query current tasks using `backlog task list --json`.
2. Exclude tasks that are not executable (for example, terminal status).
3. Exclude tasks whose blocking dependencies are incomplete. Determine
   dependencies from `backlog task <TASK-ID> --json` (`dependencies`) and the
   dependency tasks' status from the list output.
4. Apply Backlog.md/project priority.
5. Apply a deterministic task-ID tie-breaker when priorities are equal
   (lowest numeric task ID first).
6. Execute exactly one selected task.
7. Fully finalize it (it must meet all four completion conditions).
8. Re-query `backlog task list --json`.
9. Select again.

Do not maintain a stale in-memory queue across completed tasks. Each selection
re-queries Backlog.md. Never select automatic tasks by parsing Markdown task
files directly.

Automatic mode:

- does not invoke `grilling`,
- does not ask interactive product questions,
- does not guess missing product intent,
- blocks (stops) on unresolved product decisions, and
- may make reversible engineering decisions supported by repository evidence.

When a product decision is missing, record evidence in the task, report the task
as blocked, and stop.

## Completion conditions

A task may be marked `Done` only when all four conditions are satisfied:

1. Acceptance Criteria all pass.
2. Required tests, lint, typecheck, and build pass.
3. Documentation and Requirement Matrix are synchronized.
4. The task record contains validation evidence.

Only checks applicable to the task and supported by repository evidence are
required. Record unavailable or non-applicable checks explicitly as unavailable
or not applicable rather than inventing them. When no Requirement Matrix exists
or the task does not affect it, record that as not applicable.

Use Backlog.md native Acceptance Criteria, Definition of Done, Implementation
Notes, and Final Summary facilities instead of recreating equivalent Markdown
structures.

PR/MR creation, CI review, review fixes, and merge remain the standard delivery
flow when available, but they are not a fifth completion condition.

### Native Definition of Done binding

The four completion conditions are machine-enforceable, so every workflow task
must carry them in the Backlog.md native Definition of Done. The canonical DoD
items are:

- `Acceptance Criteria all pass`
- `Required applicable tests, lint, typecheck, and build pass`
- `Documentation and Requirement Matrix are synchronized when applicable`
- `Validation evidence is recorded in the task`

`/backlog-plan` adds these with one repeatable `--dod` flag per item at task
creation. Before starting work, `/backlog-run` and `/backlog-auto` read the task
(`backlog task <TASK-ID> --json`, `definitionOfDone`) and append any missing
canonical item with `backlog task edit <TASK-ID> --dod "<item>"`, so tasks
created before this binding (or outside the workflow) cannot bypass it.

## True blockers

Stop or block a task only for:

1. Contradictory product requirements or Acceptance Criteria
2. Missing required permission, credential, external service, or hardware
3. Existing uncommitted changes overlapping the task in a way that cannot be
   safely isolated
4. Incomplete task dependency
5. An irreversible product, data, or architecture decision not defined by an
   authoritative source
6. A newly discovered critical defect whose safe resolution materially exceeds
   the task scope

Implementation patterns, code navigation, task-scoped refactoring, test fixes,
and reversible engineering choices are not blockers.

## Change discipline

- Prefer Backlog.md CLI operations over direct task-file editing.
- Do not mix unrelated cleanup into a task.
- Cleanup required for correctness is in scope.
- Broad cleanup discovered during execution becomes a separate task.
- Do not preserve obsolete code when removal is necessary for task correctness.
- Do not add placeholders or knowingly incomplete behavior and mark it complete.
- Do not expose internal autonomous-development mechanics in public README or
  product documentation unless explicitly required.

## Reports

Report field labels may be localized to match the user's language; field values
keep their defined vocabulary — in particular, the `Status` value is always one
of `Done`, `Blocked`, or `In Progress`, in English, regardless of report
language.

Planning report:

```text
Planning report
- Scope: <confirmed requirement scope>
- Tasks: <created or updated tasks>
- Dependencies: <dependency summary and blockers>
- Next: </backlog-run TASK-ID>
```

Execution report:

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

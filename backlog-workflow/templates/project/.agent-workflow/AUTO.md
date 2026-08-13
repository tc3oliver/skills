<!-- Managed by backlog-workflow 1.5.0 -->

# Autonomous Execution

Read `.agent-workflow/WORKFLOW.md` first, then this file, then
`.agent-workflow/EXECUTION.md` for how each selected task is executed.

`/backlog-auto <TASK-ID>` executes exactly that task and stops.

`/backlog-auto` without a task ID repeatedly selects and executes tasks,
finalizing each fully before selecting again, until no executable task remains or
a run blocker occurs.

## Autonomy boundary

Autonomous mode does not invoke `grilling`, does not ask interactive product
questions, and does not guess missing product intent. It may make reversible
engineering decisions supported by repository evidence. A missing product
decision is a task blocker: record it and continue with the other executable
tasks.

## Selection

Backlog.md already implements dependency filtering and deterministic ordering.
Use it instead of reconstructing the dependency graph task by task:

```bash
backlog task list --ready --status "<not-started status>" --sort priority --json
```

- `--ready` returns only unblocked tasks whose dependencies are all complete.
- `--sort priority` orders by configured priority, then ascending task ID — the
  deterministic tie-break this workflow requires.
- `--status` restricts selection to not-yet-started tasks. `--ready` on its own
  still returns tasks already claimed as active or parked as blocked, so this
  filter is what makes the loop terminate: a blocked task carries a different
  status and can no longer match. Take the status names from "Status roles" in
  `.agent-workflow/WORKFLOW.md`.

## Loop

1. Run the selection query and take the task at the front of the list.
2. Execute it exactly as `.agent-workflow/EXECUTION.md` defines, and finalize it
   before selecting anything else.
3. Re-run the query rather than reusing the earlier result — completing a task
   changes the ready set. Stop when it returns nothing, or on a run blocker.

## Blockers

Two different things stop work here, and they are not interchangeable.

### Task blocker

One of the conditions in "Task blockers" (`.agent-workflow/WORKFLOW.md`) applies
to the task in hand: an unresolved product decision, a missing task-specific
credential or external service, an environment limit specific to that task, an
incomplete dependency.

Write the blocked status with its evidence, then continue with the other
executable tasks:

```bash
backlog task edit <TASK-ID> -s "<blocked status>" --append-notes "Blocked: <evidence>"
```

That status is what keeps the task out of the next round — selection filters on
the not-started status, so nothing has to be remembered.

### Run blocker

The autonomous run itself cannot continue safely:

- the working tree is dirty when a parallel batch is about to create worktrees
- Backlog.md state cannot be read
- git or worktree infrastructure fails
- the configured status roles are invalid — a role naming a status the project
  does not have makes every `-s` edit fail, so no task can be claimed, blocked, or
  finished correctly
- a workflow invariant cannot be preserved

Stop `/backlog-auto`, report the blocker with its exact evidence, and change
nothing else. A run blocker is never written to a task status: it is not that
task's fault, and parking an arbitrary task would misreport it.

## Concurrency

`automatic.max_parallel_tasks` in `.agent-workflow/config.yml` sets how many
ready tasks one round may execute at once. It must be an integer of at least 1.

- **`1` (the default)** — the loop above, executed directly in the current
  working tree. Nothing else applies.
- **Greater than 1** — each task in a batch runs isolated in its own git
  worktree. **Read `.agent-workflow/PARALLEL.md` before claiming anything.**
  Isolation changes the claim, commit, and merge protocol, and running a batch
  without it produces work validated against a codebase the project does not
  have.

Isolation is the only difference. Every task still passes the Canonical
Completion Gate individually.

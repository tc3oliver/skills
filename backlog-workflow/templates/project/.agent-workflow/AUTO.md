<!-- Managed by backlog-workflow 1.4.0 -->

# Autonomous Execution

Read `.agent-workflow/WORKFLOW.md` first, then this file, then
`.agent-workflow/EXECUTION.md` for how each selected task is executed.

`/backlog-auto <TASK-ID>` executes exactly that task and stops.

`/backlog-auto` without a task ID repeatedly selects and executes tasks,
finalizing each fully before selecting again, until no executable task remains or
a true blocker occurs.

## Autonomy boundary

Autonomous mode does not invoke `grilling`, does not ask interactive product
questions, and does not guess missing product intent. It may make reversible
engineering decisions supported by repository evidence. When a product decision
is missing, put the task in the blocked status with its evidence (see "True
blockers" in `.agent-workflow/WORKFLOW.md`), report it, and move on.

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

Take tasks from the front of that list. Re-run the query after every finalized
task rather than reusing an earlier result — the ready set changes as
dependencies complete.

## Concurrency

`automatic.max_parallel_tasks` in `.agent-workflow/config.yml` sets how many
ready tasks one round may execute at once. The default `1` is plain sequential
execution. A higher value changes isolation only: every task still passes the
Canonical Completion Gate individually.

Selection and claiming stay single-threaded, which is what makes double-claiming
impossible:

1. Run the selection query and take up to `max_parallel_tasks` tasks from the
   front of the ordering as one batch.
2. Claim every task in the batch (`backlog task edit <TASK-ID> -s "<active
   status>"`), one at a time, in the main worktree, before any parallel work
   starts.

With a batch of one, execute it directly in the current worktree.

With a batch of more than one, isolate each task:

3. Create a worktree and branch from the batch's starting commit:
   `git worktree add <path> -b backlog/<TASK-ID> <base-branch>`.
4. Inside that worktree, execute the task exactly as `.agent-workflow/EXECUTION.md`
   defines it. Isolation is the only difference; the execution policy is
   identical.
5. A task's own work never merges or pushes to the shared base branch. That
   happens only in the batch merge below.

## Batch merge

After every task in the batch has finished:

6. Merge the finished tasks into the base branch in ascending task-ID order — the
   same deterministic tie-break used for selection — so merge order is
   reproducible.
7. Clean merge: the task stays `Done`; remove its worktree and branch.
8. Conflict: abort the merge, move the task out of the done status into the
   blocked status, and record the conflict as blocker evidence in its
   Implementation Notes (this is true blocker 3). Leave the worktree in place for
   inspection and continue merging the rest of the batch.
9. Re-run the selection query before the next batch; the base branch has moved
   and the ready set may have changed.

A merge conflict blocks only the task it happened on. Autonomous execution
continues until no executable task remains or a task hits a true blocker during
its own execution.

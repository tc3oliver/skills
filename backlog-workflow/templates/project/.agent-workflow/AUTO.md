<!-- Managed by backlog-workflow 1.4.1 -->

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

### Precondition: HEAD must represent the project

Before parallel execution, the non-`backlog` working tree must have **no staged,
modified, deleted, renamed, or untracked non-ignored files**. Check before
claiming anything:

```bash
git status --porcelain --untracked-files=normal -- . ':(exclude)backlog'
```

Any output is true blocker 3 (`.agent-workflow/WORKFLOW.md`): report it and stop
before claiming tasks, with no worktree created. Do not stash, commit, discard, or
otherwise modify the user's working changes — deciding what happens to them is
theirs.

Ignored files do not block parallel execution. `git status` does not list
`.gitignore`d paths unless asked, so build output, caches, and local scratch files
are already excluded. Do not add `--ignored`.

The requirement is not tidiness: it is that **HEAD fully represents the project
state the user can see**. Workers branch from a commit, so anything not in that
commit does not exist for them — a modified file, and equally a new source file
that has not been `git add`ed yet. Running a batch anyway fails in two ways, and
the quiet one is worse:

- The merge aborts with *"Your local changes would be overwritten by merge"* when
  a worker touched the same path — the same class of failure as an uncommitted
  claim.
- When the paths do not overlap, nothing errors at all. Every worker researched,
  implemented, and validated against a codebase the user's working tree no longer
  matches, and the batch reports `Done` on evidence gathered from code that is not
  what the project currently has.

This precondition applies only when execution uses isolated worktrees. Sequential
execution (`max_parallel_tasks: 1`) has no snapshot boundary — the agent operates
directly on the tree the user is looking at, so no divergence is possible — and
blocker 3 still covers changes that overlap the task it is running.

### Batch

Selection and claiming stay single-threaded, which is what makes double-claiming
impossible:

1. Run the selection query and take up to `max_parallel_tasks` tasks from the
   front of the ordering as one batch.
2. Claim every task in the batch (`backlog task edit <TASK-ID> -s "<active
   status>"`), one at a time, in the main worktree, before any parallel work
   starts.

With a batch of one, execute it directly in the current worktree.

With a batch of more than one, having checked the precondition above, isolate each
task:

3. **Commit the claims before creating any worktree.** Backlog.md's `autoCommit`
   defaults to off, so claiming only edits `backlog/tasks/*.md` in the working
   tree. Those edits touch the same files the workers will change, and an
   uncommitted edit makes the batch merge in step 8 abort with *"Your local
   changes would be overwritten by merge"* — every task in the batch, not just
   one. Check and commit what the claim actually touched:

   ```bash
   git status --short -- backlog
   git add backlog && git commit -m "backlog: claim <TASK-IDs>"
   ```

   With `autoCommit` on, the claim is already committed and `git status` is
   empty, so this is a no-op. Read the working tree rather than assuming either
   setting, and do not change the project's Backlog.md configuration.
4. Create each worktree and branch from **that** commit — the one carrying the
   claims, not the commit the batch was selected at:
   `git worktree add <path> -b backlog/<TASK-ID> HEAD`.
5. Inside that worktree, execute the task exactly as `.agent-workflow/EXECUTION.md`
   defines it. Isolation is the only difference; the execution policy is
   identical.
6. Commit the task's code and task-record changes on its own branch before
   reporting it finished. An uncommitted worktree has nothing to merge.
7. A task's own work never merges or pushes to the shared base branch. That
   happens only in the batch merge below.

## Batch merge

After every task in the batch has finished:

8. Merge the finished tasks into the base branch in ascending task-ID order — the
   same deterministic tie-break used for selection — so merge order is
   reproducible. The base branch working tree must be clean before each merge,
   for the same reason as step 3.
9. Clean merge: the task stays `Done`; remove its worktree and branch.
10. Conflict: abort the merge, move the task out of the done status into the
    blocked status, and record the conflict as blocker evidence in its
    Implementation Notes (this is true blocker 3). Commit that status change
    before merging the next task — it is an edit to `backlog/tasks/*.md` and
    would otherwise block the rest of the batch exactly as an uncommitted claim
    does. Leave the worktree in place for inspection.
11. Re-run the selection query before the next batch; the base branch has moved
    and the ready set may have changed.

A merge conflict blocks only the task it happened on. Autonomous execution
continues until no executable task remains or a task hits a true blocker during
its own execution.

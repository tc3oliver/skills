<!-- Managed by backlog-workflow 1.5.0 -->

# Parallel Autonomous Execution

Read this only when `automatic.max_parallel_tasks` is greater than 1, before
claiming anything. It adds what isolation requires to the loop in
`.agent-workflow/AUTO.md`; each task is still executed exactly as
`.agent-workflow/EXECUTION.md` defines it.

## Precondition: the working tree must be clean

Before a batch is claimed, the non-ignored working tree must have no staged,
modified, deleted, renamed, or untracked files.

Workers branch from a commit, so anything not in that commit does not exist for
them — a modified file, and equally a new file that was never `git add`ed. Check
before claiming anything:

```bash
git status --porcelain --untracked-files=normal
```

Any output is a run blocker: report the exact paths and stop, with no task
claimed and no worktree created. Do not stash, commit, discard, or otherwise
modify the user's working changes — deciding what happens to them is theirs.

The whole tree is checked, Backlog.md's own directory included. Uncommitted task
files are just as likely to be the user's work in progress, and the claim
checkpoint below must never sweep them into its commit.

Ignored files do not block. `git status` does not list `.gitignore`d paths unless
asked, so build output, caches, and local scratch files are already excluded. Do
not add `--ignored`.

The requirement is not tidiness: it is that **HEAD fully represents the project
state the user can see**. Running a batch anyway fails in two ways, and the quiet
one is worse:

- The merge aborts with *"Your local changes would be overwritten by merge"* when
  a worker touched the same path.
- When the paths do not overlap, nothing errors at all. Every worker researched,
  implemented, and validated against a codebase the user's working tree no longer
  matches, and the batch reports `Done` on evidence gathered from code the project
  does not have.

Sequential execution has no snapshot boundary — the agent works directly in the
tree the user is looking at — so this precondition is parallel-only.

## Claim checkpoint

Selection and claiming stay single-threaded, which is what makes double-claiming
impossible.

1. Run the selection query (`.agent-workflow/AUTO.md`) and take up to
   `max_parallel_tasks` tasks from the front of the ordering as one batch.
2. Claim them one at a time, in the main worktree, before any parallel work
   starts: `backlog task edit <TASK-ID> -s "<active status>"`.
3. Read back the exact file each claim wrote:

   ```bash
   backlog task <TASK-ID> --json     # .task.path, project-relative
   ```

   The Backlog.md directory is per-project — `backlog/`, `.backlog/`, or a custom
   project-relative path — so take the path from this JSON. Never assume a
   directory name, and never stage the Backlog.md directory as a whole.
4. Stage exactly those paths and commit them:

   ```bash
   git add -- "<path of TASK-A>" "<path of TASK-B>"
   git commit -m "backlog: claim <TASK-IDs>"
   ```

   Task paths contain spaces; quote each one.

   This commit is not bookkeeping. Backlog.md's `autoCommit` defaults to off, so a
   claim only edits the task file in the working tree — the same file its worker
   will change. An uncommitted claim makes the batch merge abort with *"Your local
   changes would be overwritten by merge"*, for every task in the batch rather
   than one. With `autoCommit` on the claim is already committed and there is
   nothing to stage. Read the working tree rather than assuming either setting,
   and do not change the project's Backlog.md configuration.
5. Create each worktree from **that** commit — the one carrying the claims, not
   the commit the batch was selected at:

   ```bash
   git worktree add <path> -b backlog/<TASK-ID> HEAD
   ```

## Worker contract

Inside its worktree a worker executes one task and ends in exactly one of two
states.

**Done** — the Canonical Completion Gate is met. The worker commits its
implementation *and* its task-record changes on its own branch; an uncommitted
worktree has nothing to merge. The branch is eligible for the batch merge.

**Blocked** — a task blocker was hit. The worker records the evidence and stops
with the implementation incomplete. Its branch is **not** merged: partial work
carries no completion evidence, and merging it would put unvalidated code on the
base branch under a task nobody finished.

A worker never merges or pushes to the base branch itself. That happens only
below.

## Batch merge

After every task in the batch has finished:

1. Merge in ascending task-ID order — the same deterministic tie-break used for
   selection — so merge order is reproducible. The base working tree must be clean
   before each merge, for the same reason as the claim checkpoint.
2. Merge only the branches of workers that finished `Done`.
3. Clean merge: the task stays in the done status. Remove its worktree and branch
   (`git worktree remove <path>`, then `git branch -d backlog/<TASK-ID>`).
4. Merge conflict: abort the merge, move the task out of the done status into the
   blocked status, and record the conflict as its blocker evidence. Commit that
   status change — staging only that task's own path, read as in the claim
   checkpoint — before merging the next task; it is another task-file edit and
   would otherwise block the rest of the batch exactly as an uncommitted claim
   does. Leave the worktree and branch in place for inspection.
5. Blocked worker: leave its branch unmerged, and record the blocked state on the
   base branch, where selection reads it:

   ```bash
   backlog task edit <TASK-ID> -s "<blocked status>" --append-notes "Blocked: <evidence>"
   git add -- "<path of TASK-ID>"
   git commit -m "backlog: block <TASK-ID>"
   ```

   Keep its worktree and branch so the partial work can be inspected, and name
   both in the report.
6. Re-run the selection query before the next batch; the base branch has moved and
   the ready set may have changed.

A task blocker or a merge conflict stops only its own task. The run continues
until no executable task remains, or a run blocker occurs.

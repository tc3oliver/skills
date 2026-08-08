---
name: backlog-auto
description: Explicitly run Backlog.md tasks automatically. With a task ID, execute only that task; without one, select dependency-ready tasks deterministically until exhausted or blocked.
argument-hint: "[TASK-ID]"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Agent
---

<!-- Managed by backlog-workflow 1.2.0 -->

# Run Backlog Tasks Automatically

Optional task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/TASK-POLICY.md`
- `.agent-workflow/config.yml` (`automatic.max_parallel_tasks`)
- applicable `CLAUDE.md` and `AGENTS.md` files

Follow the automatic-execution section of `.agent-workflow/WORKFLOW.md`. Load the
Backlog.md canonical instructions using the CLI recorded in
`.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
backlog instructions task-execution
backlog instructions task-finalization
```

Do not invoke `grilling`, ask interactive product questions, or guess missing
product intent. When a product decision is missing, record evidence in the task,
report it as blocked, and stop.

Use the Backlog.md CLI recorded in `.agent-workflow/PROJECT.md` for all task
operations (`backlog` in examples is a placeholder for that command — see
"Command convention" in `.agent-workflow/WORKFLOW.md`). Never select tasks by
parsing Markdown task files directly. Before coding each selected task, append
any missing canonical completion-policy DoD item with
`backlog task edit <TASK-ID> --dod "<item>"` (see "Native Definition of Done
binding" in `.agent-workflow/WORKFLOW.md`) so older tasks cannot bypass it.

When `$task_id` is present, execute only that task and stop.

Otherwise, select tasks deterministically from structured Backlog.md data:

1. Query `backlog task list --json`.
2. Exclude tasks that are not executable (for example, terminal status).
3. Exclude tasks whose blocking dependencies are incomplete. Read dependencies
   from `backlog task <TASK-ID> --json` (`dependencies`) and the dependency
   tasks' status from the list output.
4. Apply Backlog.md/project priority.
5. On equal priority, take the lowest numeric task ID.
6. Read `automatic.max_parallel_tasks` from `.agent-workflow/config.yml` and
   take up to that many tasks from the front of the ordered list as one batch
   (default `1` — a batch of one is exactly the flow below).
7. Claim every task in the batch by setting it to the active status, one at a
   time, before executing any of them (see "Parallel automatic execution" in
   `.agent-workflow/WORKFLOW.md` — this is what keeps selection race-free).
8. Execute the batch:
   - Batch of 1: execute the task directly, in the current worktree.
   - Batch of more than 1: for each claimed task, create an isolated worktree
     (`git worktree add <path> -b backlog/<TASK-ID> <base-branch>`) and spawn
     one `Agent` per task, instructed to `cd` into its worktree and perform
     the manual-execution flow (JIT plan, implement, validate, verify AC/DoD,
     sync docs, record Implementation Notes/Final Summary) for that task only,
     then report back `Done` or `Blocked`. Wait for every agent in the batch
     to finish before merging.
9. Fully finalize each task — all four completion conditions must pass.
10. For a batch of more than 1, merge finished tasks back to the base branch
    sequentially by ascending task ID; a merge conflict blocks only that task
    (revert its status out of `Done`, record the conflict as blocker evidence,
    keep its worktree for inspection) and does not stop the rest of the batch.
    Remove worktrees/branches for cleanly merged tasks.
11. Re-query `backlog task list --json` and select the next batch.

Do not keep a stale in-memory queue across completed tasks. Each task must be
fully finalized (and, in a batch, merged or recorded as a merge-conflict
blocker) before its worktree is discarded. Stop when no executable task remains
or a task hits a true blocker during its own execution.

Attempt the repository delivery flow after validation when available. PR/MR,
CI/review fixes, and merge do not add completion conditions beyond the four
defined by the workflow.

Report each completed or blocked task using exactly this structure — one block
per task, in the order they were selected. Field labels may be localized to the
user's language; the `Status` value always stays one of `Done`, `Blocked`, or
`In Progress` in English.

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

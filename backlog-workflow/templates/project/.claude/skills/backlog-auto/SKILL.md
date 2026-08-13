---
name: backlog-auto
description: Explicitly run Backlog.md tasks automatically. With a task ID, execute only that task; without one, select dependency-ready tasks deterministically until exhausted or blocked.
argument-hint: "[TASK-ID]"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Agent
---

<!-- Managed by backlog-workflow 1.4.1 -->

# Run Backlog Tasks Automatically

Optional task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/AUTO.md`
- `.agent-workflow/EXECUTION.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/config.yml` (`automatic.max_parallel_tasks`)
- applicable `CLAUDE.md` and `AGENTS.md` files

Load the Backlog.md canonical instructions using the CLI recorded in
`.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
backlog instructions task-execution
backlog instructions task-finalization
```

When `$task_id` is present, execute only that task and stop.

Otherwise follow `.agent-workflow/AUTO.md`: select with
`backlog task list --ready --status "<not-started status>" --sort priority --json`,
claim the batch sequentially, execute each task per `.agent-workflow/EXECUTION.md`,
merge, and re-query before the next batch.

When `max_parallel_tasks` is greater than 1, two `AUTO.md` rules are load-bearing
and both are checked before anything is claimed: the non-`backlog` working tree must have
no staged, modified, deleted, renamed, or untracked non-ignored files, and the
claims must be committed before any worktree is created. Workers branch from a
commit, so anything not committed — including a new file never `git add`ed — does
not exist for them.

Do not invoke `grilling`, ask interactive product questions, or guess missing
product intent. When a product decision is missing, put the task in the
configured blocked status with its evidence — that status, not memory, is what
keeps it out of the next selection round.

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

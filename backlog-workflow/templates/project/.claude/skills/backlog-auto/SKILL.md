---
name: backlog-auto
description: Explicitly run Backlog.md tasks automatically. With a task ID, execute only that task; without one, select dependency-ready tasks deterministically until exhausted or blocked.
argument-hint: "[TASK-ID]"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write
---

<!-- Managed by backlog-workflow 1.1.0 -->

# Run Backlog Tasks Automatically

Optional task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/TASK-POLICY.md`
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
operations. Never select tasks by parsing Markdown task files directly.

When `$task_id` is present, execute only that task and stop.

Otherwise, select tasks deterministically from structured Backlog.md data:

1. Query `backlog task list --json`.
2. Exclude tasks that are not executable (for example, terminal status).
3. Exclude tasks whose blocking dependencies are incomplete. Read dependencies
   from `backlog task <TASK-ID> --json` (`dependencies`) and the dependency
   tasks' status from the list output.
4. Apply Backlog.md/project priority.
5. On equal priority, take the lowest numeric task ID.
6. Execute exactly one selected task.
7. Fully finalize it — all four completion conditions must pass.
8. Re-query `backlog task list --json` and select again.

Do not keep a stale in-memory queue across completed tasks. Each task must be
fully finalized before selecting the next. Stop when no executable task remains
or a true blocker occurs.

Attempt the repository delivery flow after validation when available. PR/MR,
CI/review fixes, and merge do not add completion conditions beyond the four
defined by the workflow.

Report each completed or blocked task using exactly this structure. Field labels
may be localized to the user's language; the `Status` value always stays one of
`Done`, `Blocked`, or `In Progress` in English.

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

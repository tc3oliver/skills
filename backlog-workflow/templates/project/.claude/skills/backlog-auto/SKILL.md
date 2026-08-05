---
name: backlog-auto
description: Explicitly run Backlog.md tasks automatically. With a task ID, execute only that task; without one, continue through dependency-ready tasks until exhausted or blocked.
argument-hint: "[TASK-ID]"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write
---

<!-- Managed by backlog-workflow 1.0.0 -->

# Run Backlog Tasks Automatically

Optional task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- applicable `CLAUDE.md` files

Follow the automatic-execution section of `.agent-workflow/WORKFLOW.md`.

Do not invoke `grilling`, ask interactive product questions, or guess missing product intent. Mark the affected task `Blocked`, record evidence, report, and stop when a product decision is missing.

Use the Backlog.md command recorded in `.agent-workflow/PROJECT.md` for all task operations.

When `$task_id` is present, execute only that task. Otherwise repeatedly choose the highest-priority dependency-ready task. Each task must meet all four completion conditions before selecting the next one.

Attempt the repository delivery flow after validation when available. PR/MR, CI/review fixes, and merge do not add completion conditions beyond the four defined by the workflow.

Report each completed or blocked task using exactly:

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

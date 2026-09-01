---
name: backlog-auto
description: Run Backlog.md tasks automatically, either one supplied task or dependency-ready tasks selected deterministically until exhausted or blocked.
---

<!-- Managed by backlog-workflow 1.6.0 -->

# Run Backlog Tasks Automatically

Use the optional task ID supplied with the skill invocation. Read
`.agent-workflow/WORKFLOW.md`, `.agent-workflow/AUTO.md`,
`.agent-workflow/EXECUTION.md`, `.agent-workflow/PROJECT.md`, the
`automatic.max_parallel_tasks` setting in `.agent-workflow/config.yml`, and
applicable `AGENTS.md` instructions.

Using the Backlog.md CLI recorded in `PROJECT.md`, load:

```bash
backlog instructions overview
backlog instructions task-execution
backlog instructions task-finalization
```

With an ID, execute only that task and stop. Otherwise follow `AUTO.md`: select
with the native query below, execute each task per `EXECUTION.md`, and re-query.

```bash
backlog task list --ready --status "<not-started status>" --sort priority --json
```

Load the parallel protocol only when `AUTO.md` requires it.

Autonomous execution does not ask interactive product questions or guess
missing product intent. Record task blockers in the configured blocked status;
continue other tasks only in the no-ID loop. Stop the run only for a run blocker.
Report each completed or blocked task in selection order:

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

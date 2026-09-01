---
name: backlog-run
description: Execute exactly one Backlog.md task using JIT planning, validation, evidence, and completion gates.
---

<!-- Managed by backlog-workflow 1.6.0 -->

# Run One Backlog Task

Use the task ID supplied with the skill invocation. Read
`.agent-workflow/WORKFLOW.md`, `.agent-workflow/EXECUTION.md`,
`.agent-workflow/PROJECT.md`, applicable `AGENTS.md` instructions, the task, and
the authoritative sources in its `documentation`.

Using the Backlog.md CLI recorded in `PROJECT.md`, load:

```bash
backlog instructions overview
backlog instructions task-execution
```

With no task ID, list dependency-ready tasks and stop without modifying task
state or code:

```bash
backlog task list --ready --status "<not-started status>" --sort priority --json
```

With an ID, follow
`EXECUTION.md` completely and finalize with
`backlog instructions task-finalization`.

Invocation with a task ID authorizes JIT planning, implementation, and
validation. Do not pause solely for another implementation-plan approval;
follow the blocker and decision exceptions in `EXECUTION.md`. Then stop after
this task.

End with this structure. Field labels may be localized; the `Status` value stays
one of `Done`, `Blocked`, or `In Progress` in English.

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

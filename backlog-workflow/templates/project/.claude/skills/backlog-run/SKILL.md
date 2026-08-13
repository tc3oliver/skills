---
name: backlog-run
description: Execute one explicitly named Backlog.md task in manual mode — JIT plan, implement, validate, sync docs, record evidence, and follow the repository delivery flow.
argument-hint: "<TASK-ID>"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.4.1 -->

# Run One Backlog Task

Task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/EXECUTION.md`
- `.agent-workflow/PROJECT.md`
- applicable `CLAUDE.md` and `AGENTS.md` files
- the specified task and the authoritative sources in its `documentation`

Load the Backlog.md canonical instructions for execution using the CLI recorded
in `.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
backlog instructions task-execution
```

When `$task_id` is empty, list dependency-ready tasks
(`backlog task list --ready --status "<not-started status>" --sort priority --json`)
and stop without modifying task state or code.

For a specified task, follow the flow in `.agent-workflow/EXECUTION.md`
completely, then finalize with `backlog instructions task-finalization`.

**Approval boundary.** `/backlog-run <TASK-ID>` already authorizes this task
through JIT planning, implementation, and validation — do **not** pause only for
another implementation-plan approval. See "Approval boundary" in
`.agent-workflow/EXECUTION.md` for the blocker and grilling exceptions.

After one task, stop. End with exactly this structure. Field labels may be
localized to the user's language; the `Status` value always stays one of `Done`,
`Blocked`, or `In Progress` in English.

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

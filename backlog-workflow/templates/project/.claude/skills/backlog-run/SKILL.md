---
name: backlog-run
description: Execute one explicitly named Backlog.md task in manual mode, including planning, implementation, validation, documentation synchronization, task evidence, and the repository delivery flow.
argument-hint: "<TASK-ID>"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.0.0 -->

# Run One Backlog Task

Task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- applicable `CLAUDE.md` files
- the specified task and its requirement sources

Start the background board per "Background board" in `.agent-workflow/WORKFLOW.md` before proceeding, whether or not `$task_id` is given.

When `$task_id` is empty, list dependency-ready tasks and stop without modifying task state or code.

For a specified task, follow the manual-execution section of `.agent-workflow/WORKFLOW.md` completely. Use the Backlog.md command recorded in `.agent-workflow/PROJECT.md` for task reads and writes.

Invoke the model-invoked `grilling` skill only for unresolved product decisions or irreversible choices defined by the workflow. Do not use it for ordinary engineering decisions. Record the outcome per "Recording a grilled decision" in `.agent-workflow/WORKFLOW.md`.

Attempt the repository delivery flow after validation when it is available: PR/MR, CI/review fixes, and merge. These steps do not add completion conditions beyond the four defined by the workflow.

After one task, stop. End with exactly this structure. Field labels may be localized to the user's language; the `Status` value always stays one of `Done`, `Blocked`, or `In Progress` in English, matching the Backlog.md CLI's status literals.

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
- Board: <background browser URL, or unavailable>
```

---
name: backlog-run
description: Execute one explicitly named Backlog.md task in manual mode — JIT plan, implement, validate, sync docs, record evidence, and follow the repository delivery flow.
argument-hint: "<TASK-ID>"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.2.0 -->

# Run One Backlog Task

Task: `$task_id`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/TASK-POLICY.md`
- applicable `CLAUDE.md` and `AGENTS.md` files
- the specified task and its requirement sources

Load the Backlog.md canonical instructions for execution using the CLI recorded
in `.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
backlog instructions task-execution
```

When `$task_id` is empty, list dependency-ready tasks using the Backlog.md
structured interface (`backlog task list --json`, plus
`backlog task <TASK-ID> --json` for dependency detail) and stop without
modifying task state or code.

For a specified task, follow the manual-execution section of
`.agent-workflow/WORKFLOW.md` completely. Use the Backlog.md CLI recorded in
`.agent-workflow/PROJECT.md` for all task reads and writes (`backlog` in examples
is a placeholder for that command — see "Command convention" in
`.agent-workflow/WORKFLOW.md`). Before coding, read the task's Definition of
Done and append any missing canonical completion-policy item with
`backlog task edit <TASK-ID> --dod "<item>"` (see "Native Definition of Done
binding"), then write the JIT Implementation Plan into the task
(`backlog task edit <TASK-ID> --plan "..."`), set the task to the active status,
implement, and validate.

**Approval boundary.** Backlog.md canonical execution may recommend presenting
the Implementation Plan for approval. `/backlog-run <TASK-ID>` already
authorizes this task through JIT planning, implementation, and validation.
Record the plan, then proceed — do **not** pause only for another
implementation-plan approval. Stop only on a true blocker or unresolved decision
covered by the blocker policy. This does not weaken `grilling`: still invoke it
for unresolved product decisions or irreversible choices, and record the outcome
per "Recording a grilled decision" in `.agent-workflow/WORKFLOW.md`.

Finalize with `backlog instructions task-finalization`: verify each Acceptance
Criterion with objective evidence, check Definition of Done, record validation
evidence in Implementation Notes, write the Final Summary, and set the terminal
status.

Attempt the repository delivery flow after validation when it is available:
PR/MR, CI/review fixes, and merge. These steps do not add completion conditions
beyond the four defined by the workflow.

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

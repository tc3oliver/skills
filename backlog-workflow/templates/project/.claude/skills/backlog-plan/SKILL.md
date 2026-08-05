---
name: backlog-plan
description: Manually align a requirement and decompose it into dependency-aware Backlog.md tasks without implementing code. Use only when explicitly invoked for the planning stage.
argument-hint: "<requirement, topic, or document path>"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.0.0 -->

# Plan Backlog Work

Input: `$ARGUMENTS`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/TASK-TEMPLATE.md`
- applicable `CLAUDE.md` files
- relevant requirement sources, code, tests, and existing Backlog.md tasks

Follow the manual-planning section of `.agent-workflow/WORKFLOW.md`.

Resolve facts through repository exploration. Invoke the model-invoked `grilling` skill when a user decision is required. Ask one decision at a time and do not create tasks until the user confirms shared understanding.

Create or edit tasks through the Backlog.md command recorded in `.agent-workflow/PROJECT.md`. Preserve existing IDs and history. Establish explicit blocking dependencies.

Do not implement product code. Do not mark any task `In Progress`.

End with exactly:

```text
Planning report
- Scope: <confirmed requirement scope>
- Tasks: <created or updated tasks>
- Dependencies: <dependency summary and blockers>
- Next: </backlog-run TASK-ID>
```

---
name: backlog-plan
description: Align a requirement and decompose it into dependency-aware Backlog.md tasks without implementing product code.
---

<!-- Managed by backlog-workflow 1.6.0 -->

# Plan Backlog Work

Use the requirement, topic, or document path supplied with the skill invocation as input.

Read `.agent-workflow/WORKFLOW.md`, `.agent-workflow/PLAN.md`,
`.agent-workflow/PROJECT.md`, `.agent-workflow/TASK-POLICY.md`, applicable
`AGENTS.md` instructions, authoritative requirements and decision records, and
existing Backlog.md tasks.

Using the Backlog.md CLI recorded in `PROJECT.md`, load:

```bash
backlog instructions overview
backlog instructions task-creation
```

Follow the Planning section of `PLAN.md` through its completion conditions.
Planning ends at decomposition: it does not implement product code, produce an
Implementation Plan, activate a task, or review its own output. Hand the result
to the `backlog-review` skill.

End with this structure. Field labels may be localized to the user's language;
defined status values stay in English.

```text
Planning report
- Scope: <confirmed requirement scope>
- Tasks: <created or updated tasks>
- Dependencies: <dependency summary and blockers>
- Next: <invoke the backlog-review skill>
```

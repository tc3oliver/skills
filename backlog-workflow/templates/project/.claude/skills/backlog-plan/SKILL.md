---
name: backlog-plan
description: Manually align a requirement and decompose it into dependency-aware Backlog.md tasks without implementing code. Use only when explicitly invoked for the planning stage.
argument-hint: "<requirement, topic, or document path>"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.4.1 -->

# Plan Backlog Work

Input: `$ARGUMENTS`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PLAN.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/TASK-POLICY.md`
- applicable `CLAUDE.md` and `AGENTS.md` files
- authoritative requirement sources (PRD/spec/requirement matrix), decision
  records, project instructions, and existing Backlog.md tasks

Load the Backlog.md canonical instructions for planning using the CLI recorded
in `.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
backlog instructions task-creation
```

Follow the "Planning" section of `.agent-workflow/PLAN.md`, and stop when its
"Planning is complete when" conditions are met or a blocker is reported.

Do not implement product code, produce an Implementation Plan, or set any task to
an active status. Do not review your own decomposition — that is `/backlog-review`.

End with exactly this structure. Field labels may be localized to the user's
language; the `Status` value, where present, always stays one of `Done`,
`Blocked`, or `In Progress` in English.

```text
Planning report
- Scope: <confirmed requirement scope>
- Tasks: <created or updated tasks>
- Dependencies: <dependency summary and blockers>
- Next: </backlog-review>
```

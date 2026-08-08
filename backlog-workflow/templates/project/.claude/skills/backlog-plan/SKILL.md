---
name: backlog-plan
description: Manually align a requirement and decompose it into dependency-aware Backlog.md tasks without implementing code. Use only when explicitly invoked for the planning stage.
argument-hint: "<requirement, topic, or document path>"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.2.0 -->

# Plan Backlog Work

Input: `$ARGUMENTS`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
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

Follow the manual-planning section of `.agent-workflow/WORKFLOW.md`.

Resolve facts through repository exploration. Invoke the model-invoked
`grilling` skill only when product intent, scope, acceptance behavior, or an
irreversible decision cannot be resolved from an authoritative source. Ask one
decision at a time and do not create tasks until the user confirms shared
understanding. Record each grilled decision per "Recording a grilled decision"
in `.agent-workflow/WORKFLOW.md` before creating any task that cites it.

Create or edit tasks through the Backlog.md CLI (the command recorded in
`.agent-workflow/PROJECT.md`; see the "Command convention" note in
`.agent-workflow/WORKFLOW.md`). Preserve existing IDs and history. Establish
explicit dependencies, Acceptance Criteria, and priority. Bind the completion
policy by adding the four Definition of Done items with one repeatable `--dod`
flag per item (see "Native Definition of Done binding" in
`.agent-workflow/WORKFLOW.md`). Write task title, description, and Acceptance
Criteria in the user's language (see "Language" in `.agent-workflow/WORKFLOW.md`).

Planning stops at decomposition. Do not produce an Implementation Plan
(Implementation Plans are JIT, created during execution). Do not implement
product code. Do not set any task to the active status.

End with exactly this structure. Field labels may be localized to the user's
language; the `Status` value, where present, always stays one of `Done`,
`Blocked`, or `In Progress` in English.

```text
Planning report
- Scope: <confirmed requirement scope>
- Tasks: <created or updated tasks>
- Dependencies: <dependency summary and blockers>
- Next: </backlog-run TASK-ID>
```

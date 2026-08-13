---
name: backlog-review
description: Review whether the current Backlog.md decomposition, if every task were completed, would satisfy its requirement source. Read-only; proposes fixes and asks before changing any task.
argument-hint: "[requirement source path or review scope]"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write
---

<!-- Managed by backlog-workflow 1.5.0 -->

# Review Backlog Decomposition

Scope: `$ARGUMENTS`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PLAN.md`
- `.agent-workflow/PROJECT.md`
- applicable `CLAUDE.md` and `AGENTS.md` files
- the requirement sources in review scope, plus the decision records they rely on

Load the Backlog.md canonical instructions using the CLI recorded in
`.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
```

Follow the "Decomposition review" section of `.agent-workflow/PLAN.md`
completely — the four checks, the evidence rules, the read-only-then-confirm
flow, and the "Review is complete when" conditions all live there.

End with exactly this structure. Field labels may be localized to the user's
language; the `Verdict` value always stays one of `Satisfied`, `Gaps found`, or
`Undetermined` in English.

```text
Decomposition review
- Requirement source: <sources and task set reviewed>
- Verdict: <Satisfied|Gaps found|Undetermined>
- Coverage: <covered/total, and every uncovered requirement>
- Criteria gaps: <requirements whose Acceptance Criteria would not demonstrate them, or None>
- Unsourced tasks: <tasks whose documentation cites no authoritative source, or None>
- Dependencies: <cycles, missing prerequisites, unreachable tasks, or None>
- Proposed fix: <tasks to create or edit, or None>
- Next: <apply the proposed fix, or /backlog-run TASK-ID>
```

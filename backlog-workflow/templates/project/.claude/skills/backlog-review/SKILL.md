---
name: backlog-review
description: Review whether the current Backlog.md decomposition, if every task were completed, would satisfy its requirement source. Read-only; proposes fixes and asks before changing any task.
argument-hint: "[requirement source path or review scope]"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.3.0 -->

# Review Backlog Decomposition

Scope: `$ARGUMENTS`

Read before acting:

- `.agent-workflow/WORKFLOW.md`
- `.agent-workflow/PROJECT.md`
- `.agent-workflow/TASK-POLICY.md`
- applicable `CLAUDE.md` and `AGENTS.md` files
- the requirement sources in review scope, plus the decision records they rely on

Load the Backlog.md canonical instructions using the CLI recorded in
`.agent-workflow/PROJECT.md`:

```bash
backlog instructions overview
```

Follow the "Decomposition review" section of `.agent-workflow/WORKFLOW.md`
completely — the one question it answers, the four checks (requirement coverage,
Acceptance Criteria sufficiency, scope traceability, dependency integrity), the
evidence rules, and the read-only-then-confirm flow all live there. Read tasks
through the Backlog.md structured interface (`backlog task list --json`, then
`backlog task <TASK-ID> --json` for Acceptance Criteria and dependency detail);
`backlog` is a placeholder for the recorded CLI — see "Command convention" in
`.agent-workflow/WORKFLOW.md`.

End with exactly this structure. Field labels may be localized to the user's
language; the `Verdict` value always stays one of `Satisfied`, `Gaps found`, or
`Undetermined` in English.

```text
Decomposition review
- Requirement source: <sources and task set reviewed>
- Verdict: <Satisfied|Gaps found|Undetermined>
- Coverage: <covered/total, and every uncovered requirement>
- Criteria gaps: <requirements whose Acceptance Criteria would not demonstrate them, or None>
- Unsourced tasks: <tasks citing no authoritative requirement source, or None>
- Dependencies: <cycles, missing prerequisites, unreachable tasks, or None>
- Proposed fix: <tasks to create or edit, or None>
- Next: <apply the proposed fix, or /backlog-run TASK-ID>
```

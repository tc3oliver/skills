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

Follow the "Decomposition review" section of `.agent-workflow/WORKFLOW.md`.

Read tasks through the Backlog.md structured interface (`backlog task list
--json`, then `backlog task <TASK-ID> --json` for Acceptance Criteria and
dependency detail). `backlog` is a placeholder for the recorded CLI — see
"Command convention" in `.agent-workflow/WORKFLOW.md`.

This review answers exactly one question: **if every task in scope were completed
to its Acceptance Criteria, would the requirement source be satisfied?** Run the
four checks the workflow defines — requirement coverage, Acceptance Criteria
sufficiency, scope traceability, and dependency integrity.

Judge only against authoritative sources. Do not invent a requirement the source
does not state. Do not count a requirement as covered because a task title sounds
related — cite the Acceptance Criteria that would demonstrate it. Where the
requirement source is itself too ambiguous to judge, quote the exact wording and
record it as undetermined; do not guess, and do not invoke `grilling` here —
resolving product intent belongs to `/backlog-plan`.

The review is read-only until the user says otherwise: do not create or edit
tasks, decision records, requirement documents, or product code while reviewing.

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

When the verdict is not `Satisfied`, ask the user whether to apply the proposed
fix, and wait for the answer. Change nothing before that answer.

- Confirmed — apply only the confirmed items, following manual-planning rules
  (Backlog.md CLI, preserved IDs and history, Acceptance Criteria, dependencies,
  the four Definition of Done items, the user's language). Then re-run the four
  checks and report again.
- Declined, or the fix needs product intent that no source settles — stop with
  every task unchanged and say what is still open. Missing product intent is
  resolved by `/backlog-plan`, not here.

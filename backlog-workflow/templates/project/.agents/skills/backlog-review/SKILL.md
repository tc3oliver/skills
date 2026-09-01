---
name: backlog-review
description: Review whether the Backlog.md decomposition would satisfy its requirement source; remain read-only until a proposed fix is approved.
---

<!-- Managed by backlog-workflow 1.6.0 -->

# Review Backlog Decomposition

Use the requirement source or review scope supplied with the skill invocation.
Read `.agent-workflow/WORKFLOW.md`, `.agent-workflow/PLAN.md`,
`.agent-workflow/PROJECT.md`, applicable `AGENTS.md` instructions, and the
authoritative sources and decision records in scope.

Using the Backlog.md CLI recorded in `PROJECT.md`, load:

```bash
backlog instructions overview
```

Follow the Decomposition review section of `PLAN.md` completely. Its four
checks, evidence rules, read-only-then-confirm flow, and completion conditions
are authoritative.

Report the sources and tasks reviewed, verdict, coverage, criteria gaps,
unsourced tasks, dependency findings, proposed fix, and next action. Keep the
verdict value in the defined `Satisfied`, `Gaps found`, or `Undetermined`
vocabulary.

```text
Decomposition review
- Requirement source: <sources and task set reviewed>
- Verdict: <Satisfied|Gaps found|Undetermined>
- Coverage: <covered/total and uncovered requirements>
- Criteria gaps: <gaps or None>
- Unsourced tasks: <tasks or None>
- Dependencies: <findings or None>
- Proposed fix: <changes or None>
- Next: <confirmed fix or backlog-run task>
```

<!-- Managed by backlog-workflow 1.5.0 -->

# Planning and Decomposition Review

Read `.agent-workflow/WORKFLOW.md` first. This file covers `/backlog-plan` and
`/backlog-review`.

## Authoring a ready task

The Task Ready Gate in `.agent-workflow/WORKFLOW.md` is the bar a task must clear
before anything executes it. A task created here should clear it on creation.
Backlog.md native fields carry what Backlog.md owns; `.agent-workflow/TASK-POLICY.md`
defines what goes in the description.

- Non-empty native `documentation` naming an authoritative requirement source or
  a persisted decision record (see "Requirement traceability")
- Goal, scope, and explicit out-of-scope
- Stable implementation constraints
- Dependencies (native `dependencies`)
- Objectively verifiable Acceptance Criteria (native)
- Validation method or commands, and the test coverage the task requires
- Security, data/schema, API/compatibility, documentation, and migration impact

A task should fit one reviewable change.

## Planning

`/backlog-plan` performs requirement alignment and decomposition only.

1. Load `backlog instructions overview` and `backlog instructions task-creation`.
2. Read the requirement sources, the requirement matrix when applicable,
   architecture and decision records, project instructions, relevant repository
   structure, and existing tasks (`backlog task list --json`).
3. Resolve factual questions from the repository instead of asking the user.
4. Invoke the `grilling` skill only when product intent, scope, acceptance
   behavior, or an irreversible decision cannot be resolved from an authoritative
   source. Ask one decision at a time and create no task until the user confirms
   shared understanding.
5. Record each grilled decision per "Decision policy" in
   `.agent-workflow/WORKFLOW.md`, then update any other authoritative document
   those decisions change.
6. Decompose into small tasks through the Backlog.md CLI, preserving existing IDs
   and history. Each task carries `--doc <authoritative source>`, `--ac`
   criteria, `--dep` dependencies, `--priority`, and the four canonical `--dod`
   items from "Native Definition of Done binding".

Planning stops at decomposition. Do not research task-level implementation, write
an Implementation Plan (those are created just-in-time during execution), decide
function-level implementation, write product code, or set any task to an active
status.

Report and stop. Planning does not review its own decomposition — hand off to
`/backlog-review`.

### Planning is complete when

- every in-scope requirement in the source maps to at least one executable task
- every Acceptance Criterion is objectively verifiable
- dependencies form a valid order: no cycle, no unreachable task
- no unresolved product decision has been buried inside an implementation task —
  each is either settled in a decision record or reported as a blocker

Anything that cannot be satisfied is reported, not worked around.

## Decomposition review

`/backlog-review [requirement source or scope]` answers one question: **if every
task in scope were completed to its Acceptance Criteria, would the requirement
source be satisfied?**

It is a separate pass on purpose — the context that produced a decomposition is
the worst one to audit it — and it can be re-run whenever tasks or requirements
change, not only right after `/backlog-plan`.

Scope defaults to the requirement sources recorded in `.agent-workflow/PROJECT.md`
and every non-archived task citing them; an argument narrows it to one source,
document, or feature area. Tasks already `Done` count as covering their
requirements — the question is about the whole decomposition, not remaining work.

Read tasks through `backlog task list --json`, then `backlog task <TASK-ID> --json`
for `acceptanceCriteria`, `dependencies`, and `documentation`.

Run four checks:

1. **Requirement coverage** — enumerate the discrete, checkable requirements in
   the source and map each to the tasks that deliver it. A requirement with no
   task is a gap.
2. **Acceptance Criteria sufficiency** — for each covered requirement, judge
   whether the mapped criteria, all passing, would actually demonstrate it.
   Criteria that are vague, unverifiable, or that cover only part of the
   requirement are a gap even though a task exists.
3. **Scope traceability** — the same rule execution enforces at the Ready Gate:
   every task's native `documentation` is non-empty and names an authoritative
   requirement source or a persisted decision record. A task whose only
   justification is its own description or notes is unsourced work, not a covered
   requirement.
4. **Dependency integrity** — dependency cycles, dependencies on missing or
   archived tasks, and tasks that no valid order can reach are gaps in the plan
   itself.

Evidence rules:

- Judge only against authoritative sources. Never introduce a requirement the
  source does not state.
- A task covers a requirement only when specific Acceptance Criteria are cited
  for it. Title similarity is not coverage.
- When the requirement source is itself too ambiguous to judge, quote the exact
  wording and record it as undetermined. Do not guess, and do not invoke
  `grilling` during review — unresolved product intent goes back to
  `/backlog-plan`.
- Report `Undetermined` when any in-scope requirement is undecidable, even if
  everything else is covered.

The review is read-only until the user says otherwise: no task, decision record,
requirement document, or product code changes while reviewing. When the verdict
is not `Satisfied`, report the proposed fix, ask the user whether to apply it,
and wait. On confirmation, apply only the confirmed items under the planning
rules above (reading `.agent-workflow/TASK-POLICY.md` before authoring any task
content), then re-run the four checks and report again. On refusal, or when the
fix needs product intent no source settles, stop with every task unchanged.

`/backlog-auto` never invokes this review: it is a user-triggered manual gate, and
its question-and-wait step has no place in an autonomous loop.

### Review is complete when

- every discrete requirement in scope is classified `Covered`, `Gap`, or
  `Undetermined` — none left unclassified
- every `Covered` requirement names the specific Acceptance Criteria that
  demonstrate it
- dependency integrity and scope traceability have been checked across the whole
  in-scope task set, not only the tasks that matched a requirement

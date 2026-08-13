<!-- Managed by backlog-workflow 1.4.0 -->

# Single-Task Execution

Read `.agent-workflow/WORKFLOW.md` first. This file defines how one task is
executed — by `/backlog-run`, and by `/backlog-auto` once it has selected a task.

## Without a task ID

`/backlog-run` with no argument lists dependency-ready tasks
(`backlog task list --ready --sort priority --json`) and stops. It modifies no
task and no code.

## Flow

1. Load `backlog instructions overview` and `backlog instructions task-execution`.
2. Read the task (`backlog task <TASK-ID> --json`) and the authoritative sources
   in its `documentation`. Missing product intent is a blocker, not a guess.
   Append any missing canonical Definition of Done item (see "Native Definition
   of Done binding" in `.agent-workflow/WORKFLOW.md`).
3. Research the **current** codebase, tests, configuration, and history. Do not
   rely on an approach proposed when the task was created.
4. Write the JIT Implementation Plan before coding:
   `backlog task edit <TASK-ID> --plan "..."`.
5. Claim the task: `backlog task edit <TASK-ID> -s "<active status>"` (see
   "Status roles" in `.agent-workflow/WORKFLOW.md` for the configured names).
6. Implement the complete task.
7. Run the applicable validation recorded in `.agent-workflow/PROJECT.md`: tests,
   lint, typecheck, build. A command recorded as `not detected` is not invented.
8. Verify every Acceptance Criterion against objective evidence and check it
   (`backlog task edit <TASK-ID> --check-ac <index>`), then check each satisfied
   Definition of Done item (`--check-dod <index>`).
9. Synchronize documentation and the Requirement Matrix when applicable.
10. Record Implementation Notes containing the validation evidence, then the
    Final Summary (`--notes`, `--final-summary`).
11. Follow the repository delivery flow when available: PR/MR, CI and review
    fixes, merge.
12. Mark the task `Done` (`backlog instructions task-finalization`) only when the
    Canonical Completion Gate is met.
13. Report and stop. Do not select another task.

## Approval boundary

Backlog.md canonical task-execution instructions may recommend presenting the
Implementation Plan and waiting for explicit approval before implementing.

This workflow defines a different boundary on purpose: invoking `/backlog-run
<TASK-ID>`, or selecting the task under `/backlog-auto`, authorizes it through
JIT planning, implementation, and validation. Record the Implementation Plan
before coding, but do not pause only to ask for another implementation-plan
approval.

Stop only for a true blocker (see `.agent-workflow/WORKFLOW.md`). This does not
weaken the safeguards: in manual mode `grilling` is still invoked for unresolved
product decisions and irreversible choices, and the outcome is recorded per
"Decision policy" before work continues.

Stopping on a blocker means step 5's claim is undone: set the task to the blocked
status and record the evidence, as "True blockers" defines, before reporting
`Status: Blocked`. A task left in the active status reads as work in flight.

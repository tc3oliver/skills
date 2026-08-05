<!-- Managed by backlog-workflow 1.0.0 -->

# Backlog Development Workflow

## Modes

The default mode is **manual**.

- Manual planning: `/backlog-plan <requirement, topic, or document path>`
- Manual execution: `/backlog-run <TASK-ID>`
- Automatic execution: `/backlog-auto [TASK-ID]`

The slash commands above are the Claude Code entry points. This process is not
Claude-specific: any coding agent can follow it by reading this file and running
the Backlog.md CLI recorded in `.agent-workflow/PROJECT.md`. Where an agent has
no slash commands, treat the named sections below as the instruction to follow
and honor the same mode boundary.

Automatic mode starts only through an explicit request for automatic execution. Requests such as “continue development” do not enable automatic mode.

Manual means planning and execution are separate user-triggered stages. It does not mean waiting for approval after every engineering step.

## Sources of truth

- PRDs, specifications, and requirement matrices define product intent, scope, and acceptance intent.
- Backlog.md defines task decomposition, dependencies, priority, execution status, plans, and validation evidence.
- `.agent-workflow/WORKFLOW.md` defines the execution process.
- `.agent-workflow/PROJECT.md` defines repository-specific commands, paths, and constraints.
- `CLAUDE.md` and `AGENTS.md` are the workflow entry points plus project rules that must not be missed.

A task must not silently introduce, remove, or reinterpret a product requirement. Resolve conflicts in the authoritative requirement source before implementation.

## Task Ready Gate

A task may enter `In Progress` only when all applicable items are clear:

- Requirement source or technical rationale
- Goal
- Scope
- Out of Scope
- Dependencies
- Objectively verifiable Acceptance Criteria
- Validation method or commands
- Test requirements
- Material implementation constraints
- Security impact
- Data or schema impact
- API or compatibility impact
- Documentation impact
- Migration or rollback impact

A task should fit one reviewable change. Missing product intent is a blocker. Engineering details that can be safely determined from repository evidence are not blockers.

## Manual planning

`/backlog-plan` performs only requirement alignment and task decomposition:

1. Read requirement sources, project instructions, relevant code, and existing tasks.
2. Resolve factual questions from the environment instead of asking the user.
3. Invoke the project `grilling` skill when product intent, scope, acceptance behavior, or an irreversible decision remains unclear.
4. Reach shared understanding before creating tasks.
5. Update authoritative requirement documents when confirmed decisions require it.
6. Create small Backlog.md tasks with explicit dependencies and the Task Ready Gate fields.
7. Report the plan and stop.

Do not mark tasks `In Progress` and do not implement product code during planning.

## Manual execution

`/backlog-run` requires an explicit task ID. Without one, list dependency-ready tasks and stop without modifications.

For the specified task:

1. Verify the Task Ready Gate.
2. Mark the task `In Progress`.
3. Read requirements, code, tests, configuration, history, and project instructions.
4. Write the implementation plan into the task.
5. Invoke `grilling` only when planning reveals a missing product decision, irreversible architecture decision, external compatibility choice, potential data loss, or unresolved security/product conflict.
6. Implement the complete task.
7. Run relevant validation, tests, lint, typecheck, and build.
8. Verify every Acceptance Criterion.
9. Synchronize documentation and the Requirement Matrix.
10. Record implementation notes and validation evidence in the task.
11. Follow the repository delivery flow when available: create a PR/MR, address CI/review findings, and merge.
12. Mark the task `Done` when the four completion conditions are met.
13. Report and stop. Do not select another task.

## Automatic execution

`/backlog-auto <TASK-ID>` executes that task and stops.

`/backlog-auto` without a task ID repeatedly selects the highest-priority dependency-ready task, completes it, then selects the next task until none remain or a true blocker occurs.

Automatic mode:

- Does not ask interactive product questions.
- Does not invoke `grilling`.
- Blocks rather than guessing when product intent is missing.
- May make reversible engineering decisions consistent with repository evidence.
- Keeps each task as a separate reviewable change when repository delivery supports it.
- Does not begin the next task until the current task meets the completion conditions.

## Completion conditions

A task may be marked `Done` when all four conditions are satisfied:

1. Acceptance Criteria all pass.
2. Required tests, lint, typecheck, and build pass.
3. Documentation and Requirement Matrix are synchronized.
4. The task record contains validation evidence.

Only checks applicable to the task and configured by repository evidence are required. Record unavailable or non-applicable checks explicitly. When no Requirement Matrix exists or the task does not affect it, record that as not applicable.

PR/MR creation, CI review, review fixes, and merge remain the standard delivery flow when available, but they are not additional completion gates.

## True blockers

Stop or block a task only for:

1. Contradictory product requirements or Acceptance Criteria
2. Missing required permission, credential, external service, or hardware
3. Existing uncommitted changes overlapping the task in a way that cannot be safely isolated
4. Incomplete task dependency
5. An irreversible product, data, or architecture decision not defined by an authoritative source
6. A newly discovered critical defect whose safe resolution materially exceeds the task scope

Implementation patterns, code navigation, task-scoped refactoring, test fixes, and reversible engineering choices are not blockers.

## Change discipline

- Prefer Backlog.md CLI/MCP operations over direct task-file editing.
- Do not mix unrelated cleanup into a task.
- Cleanup required for correctness is in scope.
- Broad cleanup discovered during execution becomes a separate task.
- Do not preserve obsolete code when removal is necessary for task correctness.
- Do not add placeholders or knowingly incomplete behavior and mark it complete.
- Do not expose internal autonomous-development mechanics in public README or product documentation unless explicitly required.

## Reports

Planning report:

```text
Planning report
- Scope: <confirmed requirement scope>
- Tasks: <created or updated tasks>
- Dependencies: <dependency summary and blockers>
- Next: </backlog-run TASK-ID>
```

Execution report:

```text
Execution report
- Task: <ID and title>
- Status: <Done|Blocked|In Progress>
- Changes: <major implementation and synchronized documents>
- Validation: <AC and required command results plus evidence location>
```

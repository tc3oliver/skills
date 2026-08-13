# AI Coding Skills

A personal collection of skills and development workflows I use with AI coding agents.

Some skills are built around my own workflow. Others are adapted from or collected from useful open-source projects, with their original attribution and license preserved.

The goal is to make coding agents more predictable: clarify requirements before implementation, keep work scoped, validate with evidence, and stop instead of guessing when important decisions are missing.

## Skills

| Skill                                                     | Description                                                                                                                                                    |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`backlog-workflow`](backlog-workflow/)                   | My task-driven development workflow built on Backlog.md. Supports requirement planning, decomposition review, single-task execution, autonomous execution, validation, and delivery. |
| [`audit-claude-md`](audit-claude-md/)                     | Audits `CLAUDE.md` and related rules for stale, duplicated, misplaced, or overly broad instructions.                                                           |
| [`diagnosing-bugs`](diagnosing-bugs/)                     | A structured debugging workflow based on reproduction, falsifiable hypotheses, evidence, and regression tests.                                                 |
| [`writing-for-agents`](writing-for-agents/)               | Guidelines for writing effective `SKILL.md`, `CLAUDE.md`, `AGENTS.md`, and other agent-facing documentation.                                                   |
| [`skill-optimizer`](skill-optimizer/)                     | Reviews and refactors an existing Skill for routing accuracy, context efficiency, execution reliability, and maintainability.                                  |
| [`resolving-merge-conflicts`](resolving-merge-conflicts/) | Resolves merge and rebase conflicts by understanding the intent of both sides before modifying the conflict.                                                   |

## Install

### Agent Skills CLI

Install with the Agent Skills CLI:

```bash
npx skills add tc3oliver/skills
```

It can install the skills into supported agents such as Claude Code and Codex.

### Claude Code Plugin

The repository can also be installed as a Claude Code plugin:

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

Plugin skills use the namespace:

```text
/tc3oliver-skills:backlog-workflow
/tc3oliver-skills:audit-claude-md
/tc3oliver-skills:diagnosing-bugs
/tc3oliver-skills:writing-for-agents
/tc3oliver-skills:skill-optimizer
/tc3oliver-skills:resolving-merge-conflicts
```

---

# backlog-workflow

`backlog-workflow` is the main development workflow in this repository.

It is built on top of **Backlog.md**, but does not replace or reimplement it.

```text
PRD / Specification
        ↓
backlog-workflow
Development policy & orchestration
        ↓
Backlog.md
Tasks, status, dependencies & evidence
        ↓
Coding Agent
        ↓
Implementation → Validation → PR/MR → CI → Review → Merge
```

The responsibility is intentionally separated:

```text
Backlog.md       = task/workflow engine
backlog-workflow = development policy & orchestration
PROJECT.md       = repository-specific configuration
PRD / Spec       = product source of truth
```

Backlog.md handles task mechanics such as status, dependencies, Acceptance Criteria, Definition of Done, Implementation Plan, notes, and final summaries.

`backlog-workflow` defines how I want coding agents to plan and execute software development work.

## Why

Giving an agent a requirement and asking it to implement everything directly often creates predictable problems:

* implementation starts before the requirement is clear
* large requirements become oversized coding sessions
* implementation plans become stale
* product behavior is silently reinterpreted
* dependencies are executed in the wrong order
* validation commands are guessed
* documentation is forgotten
* tasks are marked complete without evidence
* autonomous execution continues when the agent should stop

`backlog-workflow` separates the development process into explicit stages:

```text
Requirement
    ↓
Task decomposition
    ↓
Decomposition review
    ↓
Task selection
    ↓
Just-in-time implementation planning
    ↓
Implementation
    ↓
Validation
    ↓
Evidence
    ↓
Delivery
```

## Setup

After installing the skill, enter a project and run:

```text
/backlog-workflow apply
```

The installer discovers project-specific information such as:

* Backlog.md CLI
* default branch
* requirement sources
* setup commands
* format / lint / typecheck / test / build commands
* project-specific constraints

It then installs the project workflow:

```text
/backlog-plan
/backlog-review
/backlog-run
/backlog-auto
```

Workflow maintenance:

```text
/backlog-workflow audit
/backlog-workflow upgrade
```

`audit` is read-only.

`upgrade` updates workflow-managed files while preserving project-owned configuration, requirements, and existing Backlog.md tasks.

---

## Manual Workflow

Manual mode is the default.

### 1. Plan

```text
/backlog-plan docs/PRD.md
```

The agent reads the authoritative requirements and decomposes them into executable Backlog.md tasks.

Tasks capture stable information, using Backlog.md's own fields wherever it has
one:

* authoritative requirement source (native `documentation`)
* Acceptance Criteria, dependencies, priority (native)
* goal, scope and out-of-scope, constraints, validation requirements
  (task description)

`/backlog-plan` does not implement product code.

Detailed implementation planning is deliberately postponed until execution so that the plan reflects the **current codebase**, not the state of the repository when the task was originally created.

```text
/backlog-plan
    ↓
define WHAT needs to be done

/backlog-run
    ↓
research the current codebase
    ↓
decide HOW to implement it
```

### 2. Review the Decomposition

```text
/backlog-review docs/PRD.md
```

Decomposition is where requirements quietly go missing. `/backlog-review` is a
separate pass that answers one question: **if every task were completed to its
Acceptance Criteria, would the requirement be satisfied?**

```text
Requirement coverage       every requirement maps to a task
Acceptance Criteria        the criteria would actually demonstrate it
Scope traceability         every task cites an authoritative source
Dependency integrity       no cycles, no unreachable tasks
```

It is deliberately not part of `/backlog-plan` — the context that produced a
decomposition is the worst one to audit it — and it can be re-run whenever tasks
or requirements change.

The review is read-only: it reports gaps and a proposed fix, then asks before
creating or editing anything. A requirement too ambiguous to judge is reported
as `Undetermined` and goes back to `/backlog-plan` rather than being guessed at.
`/backlog-auto` never runs it.

### 3. Execute One Task

```text
/backlog-run TASK-42
```

The agent executes exactly one task:

```text
Read Task + Requirement
        ↓
Check Dependencies
        ↓
Inspect Current Codebase
        ↓
Write JIT Implementation Plan
        ↓
Implement
        ↓
Validate
        ↓
Record Evidence
        ↓
Synchronize Documentation
        ↓
PR/MR → CI → Review → Merge
        ↓
Done
        ↓
STOP
```

Calling `/backlog-run TASK-ID` authorizes the task through implementation and validation.

The agent does not stop again merely to ask for approval of the Implementation Plan.

It stops when it encounters a real blocker or an unresolved decision that cannot safely be derived from existing requirements or repository evidence.

---

## Automatic Workflow

Continuous autonomous execution must be explicitly requested:

```text
/backlog-auto
```

The agent repeatedly:

```text
Query current Backlog.md state
        ↓
Find dependency-ready tasks
        ↓
Select deterministically by priority
        ↓
Complete one task
        ↓
Re-query Backlog.md
        ↓
Repeat
```

A specific task can also be executed with:

```text
/backlog-auto TASK-42
```

Automatic mode is never enabled by vague instructions such as:

```text
continue
keep going
continue development
```

Only `/backlog-auto` enables continuous task execution.

Task selection is Backlog.md's own query — `backlog task list --ready --sort priority --json` — not a dependency graph rebuilt by the agent.

If product intent is missing or conflicting, automatic mode blocks instead of guessing.

---

## Canonical Completion Gate

Defined once, in `.agent-workflow/WORKFLOW.md`, and bound to every task as
Backlog.md Definition of Done items. A task is complete only when:

1. Acceptance Criteria pass.
2. Required applicable tests, lint, typecheck, and build checks pass.
3. Documentation and Requirement Matrix are synchronized when applicable.
4. Validation evidence is recorded in the task.

Writing code is not enough to mark a task Done.

---

## Backlog.md Integration

`backlog-workflow` uses the Backlog.md CLI as its default interface.

Normal task operations go through Backlog.md instead of directly rewriting files under `backlog/tasks/`.

This keeps the responsibilities clean:

```text
Backlog.md
    owns task mechanics

backlog-workflow
    owns development policy
```

Backlog.md MCP support remains optional and user-managed. `backlog-workflow` does not require or automatically configure MCP.

---

## Project Structure

A project using `backlog-workflow` receives:

```text
.agent-workflow/
├── VERSION
├── config.yml
├── WORKFLOW.md        shared invariants + mode routing
├── PLAN.md            /backlog-plan, /backlog-review
├── EXECUTION.md       /backlog-run
├── AUTO.md            /backlog-auto
├── TASK-POLICY.md
└── PROJECT.md

.claude/
└── skills/
    ├── backlog-plan/
    ├── backlog-review/
    ├── backlog-run/
    ├── backlog-auto/
    └── grilling/
```

Each skill reads `WORKFLOW.md` plus only the phase file it actually runs, so
planning never loads the merge protocol and execution never loads the review
checks.

Small managed entry points are also added to:

```text
CLAUDE.md
AGENTS.md
```

`PROJECT.md` contains repository-specific execution configuration and becomes project-owned after it is created.

Existing tasks, requirements, specifications, documentation, and user-owned instruction content are preserved.

See [`backlog-workflow/README.md`](backlog-workflow/) for implementation, installation, and upgrade details.

---

## Other Skills

### audit-claude-md

Reviews agent instructions and gives each rule a concrete disposition:

```text
keep
rewrite
move to narrower scope
extract into a skill
delete
```

The goal is to prevent `CLAUDE.md` from becoming a permanent collection of stale project knowledge.

### diagnosing-bugs

A disciplined debugging workflow:

```text
Reproduce
→ Build a tight feedback loop
→ Form falsifiable hypotheses
→ Test one variable at a time
→ Collect evidence
→ Fix the correct seam
→ Add regression coverage
```

### writing-for-agents

Guidance for writing documents consumed by coding agents, including skills, `CLAUDE.md`, and `AGENTS.md`.

### skill-optimizer

Reviews an existing Skill and improves it along four axes: routing accuracy, context efficiency, execution reliability, and maintainability. Prunes instructions that don't change model behavior, pushes conditional detail behind pointers instead of inlining it, and checks that important steps have observable completion conditions.

### resolving-merge-conflicts

A workflow for understanding the intent behind both sides of a merge or rebase conflict before modifying the conflicted code.

---

## Origins & Attribution

This repository is my personal working collection. It is not a claim that every skill or idea originated here.

`backlog-workflow` is built around my own development process and combines Backlog.md with my task planning, execution, blocker, validation, and autonomous-development policies.

Some other skills or ideas are adapted from or collected from open-source work that I find useful.

Material sourced from `mattpocock/skills` retains its original MIT license and attribution:

* `backlog-workflow` bundles the `grilling` skill
* `diagnosing-bugs`
* `writing-for-agents`
* `resolving-merge-conflicts`

Individual skill directories contain their applicable license and attribution information.

## Requirements

`backlog-workflow` requires:

* Backlog.md CLI
* Python 3

Other requirements depend on the individual skill and coding agent.

## Development

Validate `backlog-workflow` with:

```bash
cd backlog-workflow
python3 -m unittest discover -s tests
python3 scripts/validate_package.py
```

## License

MIT unless an individual skill contains its own license or attribution notice.

Third-party material retains its original license and attribution.

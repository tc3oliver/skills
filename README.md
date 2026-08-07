# AI Coding Skills

A personal collection of skills, workflows, and operating rules I use with coding agents.

This repository is not intended to be a universal framework. It reflects how I prefer to work with AI coding agents in real projects: requirements should be explicit, implementation should be task-driven, agents should validate their work with evidence, and automation should stop rather than guess when product intent is unclear.

Some skills in this repository are written around my own workflows. Others are adapted, curated, or vendored from useful open-source work by other authors. When material is reused directly, its original license and attribution are preserved.

The goal is simple:

> Make coding agents more predictable, autonomous where appropriate, and easier to trust.

## Skills

| Skill                                                     | Purpose                                                                                                                                                                                            |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`backlog-workflow`](backlog-workflow/)                   | My primary task-driven development workflow built on Backlog.md. Separates requirements, task planning, implementation, validation, and delivery, with both manual and autonomous execution modes. |
| [`audit-claude-md`](audit-claude-md/)                     | Audits `CLAUDE.md` and related instruction files to remove stale, duplicated, overly broad, or misplaced rules.                                                                                    |
| [`diagnosing-bugs`](diagnosing-bugs/)                     | A disciplined workflow for investigating difficult bugs with falsifiable hypotheses and regression tests.                                                                                          |
| [`writing-for-agents`](writing-for-agents/)               | Guidelines for writing effective `CLAUDE.md`, `AGENTS.md`, skills, and other documents consumed by coding agents.                                                                                  |
| [`resolving-merge-conflicts`](resolving-merge-conflicts/) | A structured workflow for resolving merge and rebase conflicts while preserving the intent of both sides.                                                                                          |

---

# backlog-workflow

`backlog-workflow` is the main workflow I use for task-driven development with coding agents.

It is built on top of **Backlog.md**, but it does not try to replace or reimplement Backlog.md.

The responsibility is intentionally split:

```text
PRD / Specification
        │
        │ product intent
        ▼
backlog-workflow
        │
        │ development policy / orchestration
        ▼
Backlog.md
        │
        │ tasks / status / dependencies / evidence
        ▼
Coding Agent
        │
        ▼
Implementation → Validation → PR/MR → CI → Review → Merge
```

In short:

```text
Backlog.md
= task and workflow engine

backlog-workflow
= my development policy and orchestration layer

PROJECT.md
= repository-specific execution configuration

PRD / Specification
= product source of truth
```

## Why I built it

Giving a coding agent a PRD and saying:

```text
Implement this.
```

works surprisingly well until it does not.

Common failure modes include:

* implementation starts before requirements are actually understood
* one large requirement becomes one enormous coding session
* the agent silently changes product behavior to make implementation easier
* implementation plans become stale before execution starts
* tasks are marked complete without objective validation
* lint, typecheck, tests, or build commands are invented
* documentation is forgotten
* dependencies are executed in the wrong order
* autonomous agents guess when they should stop
* the agent completes one task and continues modifying unrelated code
* planning, implementation, and product decisions become mixed together

`backlog-workflow` puts explicit boundaries around those behaviors.

The workflow is designed around:

```text
Requirement
    ↓
Task decomposition
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

Each layer has a different responsibility and a different source of truth.

---

## Commands

Installing `backlog-workflow` adds three project-level development commands.

| Command                       | Purpose                                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| `/backlog-plan <requirement>` | Analyze requirements and create or refine Backlog.md tasks. Does not implement product code. |
| `/backlog-run <TASK-ID>`      | Execute exactly one task from planning through validation and delivery, then stop.           |
| `/backlog-auto [TASK-ID]`     | Autonomous execution mode. Runs only when explicitly requested.                              |

The workflow itself is managed with:

```text
/backlog-workflow apply
/backlog-workflow audit
/backlog-workflow upgrade
```

### `apply`

Installs the workflow into the current repository.

It detects repository-specific commands and structure, initializes Backlog.md when necessary, installs the project skills, and adds small managed entry points to agent instruction files.

### `audit`

Performs a read-only consistency check.

It does not repair anything automatically.

### `upgrade`

Updates workflow-managed files to the installed `backlog-workflow` version while preserving project-owned configuration and existing task data.

---

# Manual mode

Manual mode is the default.

It deliberately separates **planning what should be done** from **executing how it should be done**.

## Phase 1 — `/backlog-plan`

Example:

```text
/backlog-plan docs/PRD.md
```

The agent reads the authoritative product sources and decomposes the requirement into executable Backlog.md tasks.

Typical sources include:

```text
PRD
Specification
Requirement Matrix
Architecture decisions
Existing Backlog tasks
Repository instructions
Relevant repository structure
```

The result should contain stable information such as:

```text
Goal
Scope
Out of Scope
Acceptance Criteria
Dependencies
Priority
Requirement Source
Important constraints
```

It should **not** create detailed implementation plans for every future task.

This distinction is intentional.

A task may be created today but implemented days or weeks later. A detailed implementation plan written during initial decomposition can become stale as the codebase changes.

Therefore:

```text
/backlog-plan
    ↓
define WHAT must be achieved

/backlog-run
    ↓
research the CURRENT codebase
    ↓
decide HOW to implement it
```

Implementation planning is just-in-time.

---

## Phase 2 — `/backlog-run`

Example:

```text
/backlog-run TASK-42
```

This authorizes the agent to execute exactly that task.

The workflow is approximately:

```text
Read Task
    ↓
Read authoritative requirement
    ↓
Check dependencies
    ↓
Inspect current code / tests / configuration / history
    ↓
Write Implementation Plan
    ↓
Mark In Progress
    ↓
Implement
    ↓
Validate
    ↓
Record evidence
    ↓
Synchronize documentation
    ↓
PR / MR
    ↓
CI
    ↓
Review / Fix
    ↓
Merge
    ↓
Done
    ↓
STOP
```

The Implementation Plan is recorded before coding begins, but `/backlog-run TASK-ID` itself is considered authorization to proceed.

The agent does not stop again merely to ask:

```text
The implementation plan is ready.
Should I continue?
```

It stops only when it encounters a real blocker or an unresolved decision that cannot safely be inferred from existing evidence.

---

# Automatic mode

Automatic execution is available, but it is never implicit.

```text
/backlog-auto
```

means:

```text
select next executable task
    ↓
complete it
    ↓
re-read backlog state
    ↓
select next executable task
    ↓
repeat
```

The agent must not interpret messages such as:

```text
continue
continue development
keep going
work on the backlog
```

as permission to enter autonomous mode.

Only an explicit `/backlog-auto` enables continuous execution.

## Deterministic task selection

Automatic mode uses structured Backlog.md data rather than parsing task Markdown manually.

Conceptually:

```text
query current Backlog.md tasks as JSON
        ↓
remove non-executable tasks
        ↓
remove tasks with incomplete blocking dependencies
        ↓
select highest priority
        ↓
use task ID as deterministic tie-breaker
        ↓
execute exactly one task
        ↓
query Backlog.md again
```

The backlog is queried again after every completed task.

The workflow does not keep executing from a stale task queue created at the beginning of the session.

## Automatic mode does not guess product intent

There is an important difference between:

```text
engineering uncertainty
```

and:

```text
product uncertainty
```

An agent may resolve reversible engineering decisions using repository evidence.

For example:

```text
Which existing helper should be reused?
Which test seam matches the current architecture?
Which internal module owns this behavior?
```

But it must not invent missing product decisions such as:

```text
What should happen when payment fails?
Should this field be visible to users?
Which behavior is authoritative when two requirements conflict?
```

In manual mode, those questions can be discussed.

In automatic mode, unresolved product intent becomes a blocker.

---

# Sources of truth

One of the most important rules in `backlog-workflow` is that different information belongs in different places.

## Product intent

Owned by:

```text
PRD
Specification
Requirement Matrix
Architecture / Decision records
```

These documents define what the product is supposed to do.

## Task execution

Owned by Backlog.md:

```text
Task status
Dependencies
Priority
Acceptance Criteria
Definition of Done
Implementation Plan
Implementation Notes
Final Summary
Validation evidence
```

A Backlog task may decompose or reference a requirement.

It may not silently redefine it.

## Repository execution configuration

Owned by:

```text
.agent-workflow/PROJECT.md
```

This file records project-specific facts discovered during installation, such as:

```text
default branch
Backlog CLI command
requirement locations
setup command
format command
lint command
typecheck command
test command
build command
repository-specific constraints
```

If something cannot be detected, it is recorded as unavailable rather than invented.

For example, if the repository has no lint command, the agent should report that lint is not applicable or not detected.

It should not manufacture:

```bash
npm run lint
```

just because that command is common in other projects.

---

# Definition of Done

A task is complete only when these four conditions hold:

1. **Acceptance Criteria pass**
2. **Required applicable tests, lint, typecheck, and build checks pass**
3. **Documentation and Requirement Matrix are synchronized when applicable**
4. **Validation evidence is recorded in the task**

These conditions intentionally distinguish:

```text
"I wrote the code."
```

from:

```text
"The task is complete."
```

PR/MR creation, CI, review, fixes, and merge are part of the normal delivery workflow when the repository supports them, but they do not replace the four completion conditions above.

---

# Backlog.md integration

`backlog-workflow` uses Backlog.md as the task/workflow engine.

It prefers the canonical Backlog.md CLI instead of directly rewriting files inside:

```text
backlog/tasks/
```

This allows Backlog.md to remain responsible for its own:

```text
task schema
metadata
status
dependencies
Acceptance Criteria
Definition of Done
Implementation Plan
Implementation Notes
Final Summary
persistence format
```

`backlog-workflow` only adds development policy on top.

This separation is important because Backlog.md can evolve without requiring this repository to duplicate its internal task mechanics.

## CLI vs MCP

Backlog.md also provides MCP integration.

`backlog-workflow` does **not** require or automatically configure MCP.

The default architecture is:

```text
Coding Agent
    ↓
backlog-workflow policy
    ↓
Backlog.md CLI
    ↓
Backlog.md workspace
```

MCP remains optional and user-managed.

This keeps the workflow portable across environments and avoids coupling project setup to a specific agent's MCP configuration.

---

# Cross-agent use

The slash commands are primarily designed for Claude Code, but the underlying workflow is not Claude-specific.

The installed project contains plain Markdown policy files and uses Backlog.md through its command-line interface.

The important files are:

```text
.agent-workflow/WORKFLOW.md
.agent-workflow/PROJECT.md
.agent-workflow/TASK-POLICY.md
```

Managed entry points are added to:

```text
CLAUDE.md
AGENTS.md
```

This allows agents that understand `AGENTS.md` and can execute shell commands to follow the same project workflow.

The objective is to keep the development policy independent from a single coding agent implementation.

---

# What gets installed

A project receives approximately:

```text
.agent-workflow/
├── VERSION
├── config.yml
├── WORKFLOW.md
├── TASK-POLICY.md
└── PROJECT.md

.claude/
└── skills/
    ├── backlog-plan/
    ├── backlog-run/
    ├── backlog-auto/
    └── grilling/
```

`WORKFLOW.md` and the project skills are managed by `backlog-workflow`.

`PROJECT.md` is generated once from repository evidence and then becomes project-owned configuration.

Existing project content outside managed blocks is preserved.

Existing Backlog.md tasks, PRDs, specifications, requirement matrices, and project documentation are not replaced by the installer.

---

# Safety and upgrade behavior

The installer is intentionally conservative.

It is designed around:

```text
idempotent apply
read-only audit
explicit upgrade
atomic writes
downgrade protection
managed-file ownership
user-content preservation
fail-closed conflict handling
```

If an unmanaged file already occupies a path owned by the workflow, installation should stop rather than overwrite it.

Upgrades replace only files owned by the workflow.

Project-maintained files such as:

```text
.agent-workflow/PROJECT.md
```

remain untouched.

---

# Other skills

## audit-claude-md

Audits agent instruction files such as:

```text
CLAUDE.md
nested CLAUDE.md
path-scoped rules
```

Each rule is evaluated and given a concrete disposition:

```text
keep
rewrite
move to narrower scope
extract into a skill
delete
```

The goal is to prevent global instruction files from becoming permanent dumping grounds for every piece of project knowledge.

---

## diagnosing-bugs

A structured debugging discipline for difficult bugs.

The workflow emphasizes:

```text
reproduce first
build a tight feedback loop
form falsifiable hypotheses
change one variable at a time
collect evidence
fix at the correct seam
add regression coverage
```

---

## writing-for-agents

A reference for writing documents consumed by coding agents.

It focuses on topics such as:

```text
instruction hierarchy
context efficiency
progressive disclosure
completion criteria
scope
references
when to split a document
```

---

## resolving-merge-conflicts

A workflow for resolving merge and rebase conflicts without treating conflict markers as the complete source of truth.

The agent first determines the intent behind both sides, then resolves the conflict while preserving those intentions wherever possible.

---

# Installation

## Claude Code plugin

Install the repository as a Claude Code plugin:

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

Skills installed through the plugin are namespaced, for example:

```text
/tc3oliver-skills:backlog-workflow
/tc3oliver-skills:audit-claude-md
/tc3oliver-skills:diagnosing-bugs
/tc3oliver-skills:writing-for-agents
/tc3oliver-skills:resolving-merge-conflicts
```

## Install individual skills

Clone the repository:

```bash
gh repo clone tc3oliver/skills tc3oliver-skills
```

Then copy only the skill you want:

```bash
cp -R tc3oliver-skills/backlog-workflow ~/.claude/skills/
```

For all skills:

```bash
gh repo clone tc3oliver/skills ~/.claude/skills
```

Copied skills retain their short command names, such as:

```text
/backlog-workflow
```

---

# Requirements

Most skills only require Claude Code.

`backlog-workflow` additionally uses:

```text
Node.js / npx
Backlog.md CLI
Python 3
```

Python is used by the installer and package validation scripts.

---

# Development

`backlog-workflow` includes automated validation:

```bash
cd backlog-workflow

python3 -m unittest discover -s tests
python3 scripts/validate_package.py
```

---

# Origins and attribution

This repository is my personal working collection.

It intentionally combines three kinds of material:

### Personal workflows

Some skills are created and maintained around the development workflows I actually use.

`backlog-workflow` is the main example: it combines Backlog.md with my own task decomposition, approval, autonomous execution, blocker, validation, and delivery policies.

### Adapted ideas

Some parts are influenced by patterns, techniques, and ideas from other developers and open-source projects.

I adapt those ideas when they fit my workflow rather than trying to preserve a universal or framework-neutral design.

### Vendored skills

Some skills are included directly from other open-source repositories because I find them useful and want them available as part of the same working toolkit.

Material sourced from `mattpocock/skills` retains its original MIT license and attribution.

Currently:

* `backlog-workflow` bundles the `grilling` skill from Matt Pocock.
* `diagnosing-bugs` is sourced from Matt Pocock's skills collection.
* `writing-for-agents` is sourced from Matt Pocock's skills collection.
* `resolving-merge-conflicts` is sourced from Matt Pocock's skills collection.

Where third-party material is included, check the individual skill directory for its license and attribution.

This repository should therefore be read as:

> A curated and opinionated personal toolkit, not a claim that every idea or skill originated here.

---

# License

The repository is distributed under the MIT License unless a skill directory contains its own license or attribution notice.

Third-party material retains the license and attribution of its original source.

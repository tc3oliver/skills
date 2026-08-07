# Project Discovery

Use repository evidence, not ecosystem assumptions.

## Identity

Inspect, when present:

- Git root, remotes, and default branch
- `package.json`
- `pyproject.toml`
- `Cargo.toml`
- `go.mod`
- solution/project files
- repository directory name

## Backlog.md

A workspace exists when any supported project configuration or task directory exists, including:

- `backlog/config.yml`
- `.backlog/config.yml`
- `backlog.config.yml`
- configured Backlog.md task directories

The Backlog.md CLI is the default and required interface. Prefer Backlog.md CLI
operations over directly editing task files (`backlog task ...`, `backlog doc ...`,
`backlog decision ...`). MCP is supported by Backlog.md but is optional and
user-managed; discovery records only the CLI and never registers an MCP server.

Detect the Backlog.md CLI (not the unrelated `backlog` npm package). A local
`node_modules/.bin/backlog` resolves to `npx backlog`; otherwise prefer
`npx backlog.md` when `npx` is available.

## Requirement sources

Look for authoritative files whose names or locations indicate:

- PRD
- requirements
- specifications
- requirement matrix
- architecture
- ADRs or decisions

Do not treat a Backlog task as a replacement product specification.

Decisions reached through `grilling` during planning or execution are recorded as
Backlog.md decision records (`backlog decision create`), not detected here — see
"Recording a grilled decision" in `.agent-workflow/WORKFLOW.md`.

## Task policy

Tasks carry additional project policy fields defined in
`.agent-workflow/TASK-POLICY.md` (Requirement Source, Goal, Scope, Out of Scope,
stable implementation constraints, and impact areas). Acceptance Criteria,
Definition of Done, dependencies, Implementation Plan, Implementation Notes, and
Final Summary use Backlog.md native fields.

## Validation commands

Record only commands supported by repository evidence or successfully verified:

- setup
- format
- lint
- typecheck
- tests
- build

Evidence includes package scripts, Make/Just targets, project configuration, CI files, and existing project instructions. Commands marked `not detected` must not be invented during task execution.

## Existing instructions

Inspect:

- `CLAUDE.md`
- `.claude/CLAUDE.md`
- `CLAUDE.local.md`
- `AGENTS.md`
- `.claude/rules/`

Preserve all content outside this workflow's managed block. Report material conflicts rather than deleting them. `apply` manages one block in `CLAUDE.md` (or `.claude/CLAUDE.md`) and one in `AGENTS.md`, creating `AGENTS.md` when absent.

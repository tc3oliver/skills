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

Detect **and verify** the Backlog.md CLI. Do not trust a `backlog` binary just
because it is on PATH — a bare `npx backlog` without a local install resolves to
the unrelated npm `backlog` package. Each candidate is probed read-only
(`<candidate> instructions overview`) and accepted only when it exits 0 and emits
the Backlog.md overview. If no candidate verifies, `apply`/`upgrade`/`audit` fail
with a clear "required interface" error rather than recording `not detected`.

A local `node_modules/.bin/backlog` resolves to `npx backlog`; otherwise the
canonical safe form is `npx backlog.md` when `npx` is available.

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
"Decision policy" in `.agent-workflow/WORKFLOW.md`.

## Task policy

`.agent-workflow/TASK-POLICY.md` defines only what Backlog.md has no field for
(goal, scope and out-of-scope, constraints, validation, impacts). The
authoritative requirement source, supporting material, dependencies, Acceptance
Criteria, Definition of Done, Implementation Plan, Implementation Notes, and
Final Summary all use Backlog.md native fields.

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

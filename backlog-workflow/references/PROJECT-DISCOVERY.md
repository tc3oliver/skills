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

Prefer Backlog.md CLI/MCP operations over directly editing task files.

## Requirement sources

Look for authoritative files whose names or locations indicate:

- PRD
- requirements
- specifications
- requirement matrix
- architecture
- ADRs or decisions

Do not treat a Backlog task as a replacement product specification.

## Validation commands

Record only commands supported by repository evidence or successfully verified:

- setup
- format
- lint
- typecheck
- tests
- build

Evidence includes package scripts, Make/Just targets, project configuration, CI files, and existing project instructions.

## Existing instructions

Inspect:

- `CLAUDE.md`
- `.claude/CLAUDE.md`
- `CLAUDE.local.md`
- `AGENTS.md`
- `.claude/rules/`

Preserve all content outside this workflow's managed block. Report material conflicts rather than deleting them.

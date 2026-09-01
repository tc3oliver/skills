---
name: backlog-review
description: Review whether the current Backlog.md decomposition, if every task were completed, would satisfy its requirement source. Read-only; proposes fixes and asks before changing any task.
argument-hint: "[requirement source path or review scope]"
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write
---

<!-- Managed by backlog-workflow 1.6.0 -->

Read and follow the canonical repository skill at
`../../../.agents/skills/backlog-review/SKILL.md` as the authoritative definition.
Use `$ARGUMENTS` as its invocation input.

---
name: backlog-auto
description: Explicitly run Backlog.md tasks automatically. With a task ID, execute only that task; without one, select dependency-ready tasks deterministically until exhausted or blocked.
argument-hint: "[TASK-ID]"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Agent
---

<!-- Managed by backlog-workflow 1.6.0 -->

Read and follow the canonical repository skill at
`../../../.agents/skills/backlog-auto/SKILL.md` as the authoritative definition.
Use `$task_id` as its invocation input.

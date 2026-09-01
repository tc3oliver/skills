---
name: backlog-run
description: Execute one explicitly named Backlog.md task in manual mode — JIT plan, implement, validate, sync docs, record evidence, and follow the repository delivery flow.
argument-hint: "<TASK-ID>"
arguments: task_id
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

<!-- Managed by backlog-workflow 1.6.0 -->

Read and follow the canonical repository skill at
`../../../.agents/skills/backlog-run/SKILL.md` as the authoritative definition.
Use `$task_id` as its invocation input.

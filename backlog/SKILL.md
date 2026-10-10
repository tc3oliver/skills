---
name: backlog
description: Track, prioritize, and resume persistent coding tasks across sessions. Use when the user explicitly asks to record future work, manage their backlog, find the next tracked task, resume a BL- task, or close a tracked task. Do not invoke for ordinary coding, debugging, review, BetFirst probes, or CTK team requests without persistent backlog intent.
argument-hint: "[add|next|status|do <BL-ID>|show <BL-ID>]"
---

# Backlog

Request: $ARGUMENTS (when supported by the agent).

Use this skill **only** for persistent task intent. One-off coding requests proceed normally; do not create tasks just because coding is involved. Never silently start the next task after finishing one. A request for a team alone belongs to CTK, and a request for a cheap experiment belongs to BetFirst.

## Entry point

The CLI is `python3 <this-skill>/scripts/backlog.py --root <repository-root> <command>` (Python 3.11+, standard library only). Run `init` only on explicit first use; do not overwrite existing task data. CLI output is JSON, including errors on stderr. Use `--help` or [references/cli.md](references/cli.md) for flags. Never guess accepted flags, manually rewrite task files, or read every archived task.

- **add**: `add "title" [--goal "..."] [--ac "..."] [--ref "..."] [--depends "BL-..."]`; incomplete requests stay `inbox`. Do not invent goal, AC, or product decisions.
- **next/status**: use CLI `next --limit 5` or `status`, not a full-file dump. `next` returns only dependency-ready `todo` tasks.
- **show**: `show BL-ID`; read the specific task and its references, not all tasks.
- **do / resume BL-ID**: `show` first. If `todo` and dependencies are complete, `start` once; if already `doing`, read Handoff and current repository facts, then continue **without** calling `start` again. For `inbox`, `blocked`, `done`, or `cancelled`, do not execute until the state is intentionally resolved. Work on exactly one persistent task. Verify each AC before `check ID n`, then `close ID --evidence "actual test/observation and result"`; a failed or stale test is not completion evidence. When interrupted, save concise `note ID --text "completed; remaining; files; last check; next action"`. Use `block ID --reason` only for an actual external blocker (permission, unresolved intent, unsafe state), **not** merely for an unmet task dependency.

Task data are under `.backlog/tasks` and `.backlog/archive/{done,cancelled}/YYYY-MM`. `doctor` validates the graph and storage; `doctor --repair` restores only unambiguous interrupted moves. Reopened tasks move previous evidence into historical notes and require fresh verification. Replacing checked AC requires `edit --confirm-ac-reset`. The CLI owns state transitions; do not use `git reset --hard`, overwrite uncommitted work, or invent verification commands.

## Collaboration boundaries

- **CTK** owns explicitly requested team spawn, temporary worker tasks and team-based risk review; ordinary debugging can use `diagnosing-bugs`. If both team intent and a BL-ID exist, load the real Backlog task **before** team decomposition and hand the lead Goal, AC, References and Handoff. If the task or CTK is unavailable, do not invent context or silently start an unrequested fallback. Only the lead updates persistent task state after integration verification; workers never mirror their tasks or write Backlog. Without CTK, the normal coding agent executes the Backlog task.
- **BetFirst** owns optional bounded reversible probes. It neither changes task lifecycle nor weakens acceptance checks. Do not auto-invoke or duplicate its Spot/Cap/Bet policy.
- A `done` Backlog task means all recorded AC are verified and evidence was observed; it is not equivalent to a worker saying it finished.

See [Composition contract](../docs/COMPOSITION.md) only for explicitly combined workflows; standalone use needs no integration setup.

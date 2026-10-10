# Skill composition contract

Backlog, BetFirst and [Claude Team Kit (CTK)](https://github.com/tc3oliver/claude-team-kit) are three independently installable products, **not** a pipeline. This document is guidance for the *user explicitly combining* them, not a required project config, additional Skill, automatic router or runtime integration.

## Owners and authority

| Concern | Owner | Boundary |
| --- | --- | --- |
| Durable work, task IDs, dependencies, AC, Handoff, evidence and close | Backlog when activated | Only its CLI mutates persistent BL tasks |
| Cheap, bounded, reversible, falsifiable exploration | BetFirst when useful | No durable task state changes, worker spawns or weaker checks |
| Claude Code native teams, temporary slices, review and final integration | CTK when explicitly requested | No Backlog install requirement; no persistence of CTK worker tasks |
| Actual code, ordinary single-agent tests and repo permissions | The current coding agent | The three Skills do not bypass existing instructions or user authorization |

**Precedence:** explicit user intent and repository safety/verification requirements take priority. A mention of a bug, uncertainty or complex feature alone must not implicitly create a Backlog task or CTK team. Never auto-invoke all three merely because they are installed. Follow an explicitly selected Skill when feasible without silently dropping its essential boundaries.

## Routing

| Intent | Default behavior |
| --- | --- |
| Ordinary change or bug fix | Normal agent; `diagnosing-bugs` if its loop fits |
| "Record this for later", "what is ready", "continue BL-..." | Backlog |
| "Try a cheap safe probe" | BetFirst, or normal execution when no valid bet exists |
| "Use CTK / multiple teammates / parallel work" | CTK team intent gate, even without Backlog |
| "Use CTK team to finish BL-..." | Read real Backlog task, then CTK lead owns execution; no auto-spawn before task scope and readiness are known |
| Explicit `/ctk:debug` or CTK team diagnosing a slice | CTK debug; do not run a second, full `diagnosing-bugs` SOP |
| "Use BetFirst while working on BL-..." | Backlog tracks progress; BetFirst owns only the local probe |

## Optional handoff — no new schema

If a BL-ID and team intent coexist, the lead should retrieve that task through the installed Backlog Skill/CLI **if available**. Read only Task ID, Goal, Acceptance Criteria, References, dependencies, status and concise Handoff. Do not guess an installed Skill path, copy an entire task directory, or silently initialize a backlog from a bare BL-ID.

- `todo` with satisfied dependencies: the lead may start the persistent task only **after** CTK preflight, when actual work begins. If the requested team cannot run, leave the BL state unchanged.
- `doing`: reconcile current repository state with Handoff and continue without calling `start` again.
- `inbox`, `blocked`, `done` or `cancelled`: do not execute it without resolving that state.
- Task unavailable: do not fabricate its contents; request its Goal and AC before executing. CTK itself still works independently when a complete ordinary goal is supplied.
- CTK Team unavailable/disabled: do not claim a team was used, silently create ordinary subagents, or force a fallback. Follow CTK's preflight and user's requested execution mode.

CTK decomposes the verified goal into its own temporary task list. Workers receive pointers, file scope and checks; they **never** mutate the BL task. BetFirst experiments remain bounded and send only relevant observations to the worker/lead, not a parallel task state machine.

After integration, the **lead** verifies the actual acceptance criteria and required repository checks, records observed evidence and closes the BL task via its CLI. A worker saying "done" or a speculative probe succeeding is *not* acceptance. If blocked, interrupted or still failing, preserve an accurate Handoff/Blocker and leave the task open. If the Backlog CLI is unavailable at the end, report implementation results without claiming the BL status was changed.

## Independence and environments

- Backlog (Python stdlib + Markdown) and BetFirst (instruction-only) work without CTK and are portable to compatible Agents.
- CTK is a Claude Code plugin using native Agent Teams; it works without the other two. Do not promise native CTK teams on Pi.
- Install only the desired Skills. Do not require all three, duplicate their installation, add background hooks, or rewrite project-level `AGENTS.md`/`CLAUDE.md` just to integrate them.
- A dedicated debugging skill and `ctk:debug` can both be installed: **use one diagnostic protocol per debugging task**, with explicit CTK intent winning.

This is a behavior contract, not a claim that multi-Skill automatic discovery, token savings or E2E execution have been measured.

# Operations

## apply

Use for both new and existing projects.

- Initialize Backlog.md only when absent. The installer runs
  `npx --yes backlog.md init "<project-name>" --defaults --agent-instructions none`
  (adding `--no-git` outside a Git repository) and blocks if that fails.
  `--agent-instructions none` is deliberate: this workflow owns its managed
  CLAUDE.md/AGENTS.md blocks, so Backlog.md must not emit competing agent
  instructions.
- Verify the Backlog.md CLI: each candidate is probed read-only
  (`<candidate> instructions overview`) and accepted only when it is Backlog.md.
  If no candidate verifies, `apply`/`upgrade` fail with a clear "required
  interface" error — `PROJECT.md` is never written with an unverified or
  `not detected` CLI.
- Install workflow version `1.4.1`.
- Install the project skills `/backlog-plan`, `/backlog-review`, `/backlog-run`,
  and `/backlog-auto`. `/backlog-review` is the separate decomposition-review
  pass: it checks whether completing the planned tasks would satisfy the
  requirement source, and is read-only until the user approves a fix.
- Install the workflow policy as `.agent-workflow/WORKFLOW.md` (shared invariants
  and mode routing) plus one reference per phase — `PLAN.md` (planning and
  decomposition review), `EXECUTION.md` (single-task execution), and `AUTO.md`
  (autonomous selection, concurrency, and merge). Each skill loads only the
  phase it runs.
- `.agent-workflow/config.yml` sets `automatic.max_parallel_tasks: 1` by
  default — `/backlog-auto` stays sequential unless the project raises it. See
  "Concurrency" in `.agent-workflow/AUTO.md` for what changes at higher values.
- Ensure the Backlog.md project has a status to park blocked tasks in, distinct
  from the not-started one. `/backlog-auto` selects on the not-started status, so
  this status is what keeps a blocked task out of the next round. `backlog config
  set statuses` is refused by the CLI, which directs callers to the project
  config file, so the installer edits `statuses:` there — additively, inserting
  `Blocked` before the terminal status and touching no other key. A project that
  already has one (`On Hold`, `Blocked`, …) keeps it and is left unmodified.
- Record the status role mapping in `.agent-workflow/config.yml`
  (`statuses.not_started/active/blocked/done`), detected from the Backlog.md
  configuration on first install and preserved across upgrades, so a project with
  renamed columns keeps its own vocabulary.
- Preserve all existing task files, requirement documents, source code, and
  non-managed instructions. Backlog.md configuration is preserved except for the
  one additive `statuses:` change above.
- Insert or update exactly one managed block in `CLAUDE.md` (or
  `.claude/CLAUDE.md` when only that one exists) **and** in `AGENTS.md`.
  `AGENTS.md` is created when absent so cross-agent tools (Codex, Cursor, and
  others) discover the workflow. All content outside the managed block is
  preserved.
- Install `.agent-workflow/TASK-POLICY.md` (replaces the former
  `TASK-TEMPLATE.md`).
- Migrate the deprecated managed `.agent-workflow/TASK-TEMPLATE.md`: remove it
  only when it is provably the backlog-workflow 1.0.x managed copy (exact content
  match). An unmanaged or user-owned `TASK-TEMPLATE.md` is never deleted.
- Create `.agent-workflow/PROJECT.md` only when absent; never replace an existing
  project configuration.
- Default mode is manual.
- Do not start planning or implementation after installation.

### Backlog interface

- The Backlog.md CLI is the default and required interface.
- MCP is supported by Backlog.md but optional and user-managed. `apply` never
  installs or configures MCP and never registers an MCP server with a coding
  agent.
- The workflow does not start a background Backlog browser/board. The Web UI may
  be launched manually by the user; it is not part of workflow execution.

## audit

Read-only operation.

Check:

- Backlog.md workspace presence
- Workflow version
- Managed file presence and content
- Default mode
- Project skill frontmatter
- Grilling skill presence
- Managed block count and content in each entry file (`CLAUDE.md`/`.claude/CLAUDE.md` and `AGENTS.md`)
- Project configuration presence
- Drift or unmanaged-path conflicts
- Status roles: all four present, each naming a configured Backlog.md status, and
  `blocked` different from `not_started`.
- Task `documentation` references that point at a local file which no longer
  exists. A `#fragment` is stripped before the existence check; remote references
  (any `scheme:` prefix, protocol-relative, `www.`), machine-absolute and
  home-relative paths, paths escaping the project, and opaque identifiers such as
  `decision-3` are not filesystem-checkable and are skipped. Each finding names
  the task ID and the reference. This walk costs one CLI call per task, so it
  runs only for the explicit `audit` action — not for the check `apply` and
  `upgrade` run afterwards, which covers managed-file integrity.
- Recorded `PROJECT.md` facts that no longer match repository evidence. These are
  advisory: `audit` reports them, but they never block `apply` or `upgrade`.

`audit` does not inspect `README.md`; no operation in this workflow writes to it.

Return nonzero when drift, missing files, or conflicts exist. Do not repair anything.

## upgrade

- Refuse to downgrade a project with a newer workflow version.
- Replace older managed templates with version `1.4.1`, adding
  `.agent-workflow/PLAN.md`, `EXECUTION.md`, and `AUTO.md` to installs that
  predate the split. No file is removed: the phase content moves out of
  `WORKFLOW.md`, which is a managed template and is rewritten in place.
- Preserve project-owned values in `.agent-workflow/config.yml`:
  `automatic.max_parallel_tasks` and the `statuses:` role mapping. Only supply
  defaults when absent — an install predating the role mapping gets one detected
  from its Backlog.md configuration.
- Migrate the deprecated managed `TASK-TEMPLATE.md` to `TASK-POLICY.md` (managed
  copy removed; unmanaged copy preserved).
- Preserve `.agent-workflow/PROJECT.md`.
- Preserve Backlog.md task data, and Backlog.md configuration apart from adding a
  blocked status when the project has none.
- Preserve text outside the managed block in every entry file.
- Do not update `grilling` from any upstream source; the bundled copy is maintained as part of this workflow.

## Final report

Use exactly:

```text
Backlog workflow
- Action: <apply|audit|upgrade>
- Status: <Installed|Upgraded|Clean|Drift detected|Blocked>
- Version: <version or not installed>
- Changes: <compact file-level summary or none>
- Validation: <audit result and conflicts/blockers>
- Next step: <present only when apply/upgrade wrote or changed a `.claude/skills/*`
  file — run /reload-skills (or restart Claude Code / start a new session) so it
  reloads project skills before using /backlog-plan, /backlog-review,
  /backlog-run, or /backlog-auto>
```

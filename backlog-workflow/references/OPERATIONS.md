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
- Install workflow version `1.3.0`.
- Install the project skills `/backlog-plan`, `/backlog-review`, `/backlog-run`,
  and `/backlog-auto`. `/backlog-review` is the separate decomposition-review
  pass: it checks whether completing the planned tasks would satisfy the
  requirement source, and is read-only until the user approves a fix.
- `.agent-workflow/config.yml` sets `automatic.max_parallel_tasks: 1` by
  default — `/backlog-auto` stays sequential unless the project raises it. See
  "Parallel automatic execution" in `.agent-workflow/WORKFLOW.md` for what
  changes, and when it's appropriate, at higher values.
- Preserve all existing task files, Backlog.md configuration, requirement
  documents, source code, and non-managed instructions.
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
- Recorded `PROJECT.md` facts that no longer match repository evidence. These are
  advisory: `audit` reports them, but they never block `apply` or `upgrade`.

`audit` does not inspect `README.md`; no operation in this workflow writes to it.

Return nonzero when drift, missing files, or conflicts exist. Do not repair anything.

## upgrade

- Refuse to downgrade a project with a newer workflow version.
- Replace older managed templates with version `1.3.0`.
- Preserve an existing `automatic.max_parallel_tasks` value in
  `.agent-workflow/config.yml` if the project already set one; only add it with
  the default `1` when absent.
- Migrate the deprecated managed `TASK-TEMPLATE.md` to `TASK-POLICY.md` (managed
  copy removed; unmanaged copy preserved).
- Preserve `.agent-workflow/PROJECT.md`.
- Preserve Backlog.md task data and configuration.
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

# Operations

## apply

Use for both new and existing projects.

- Initialize Backlog.md only when absent. The installer runs
  `npx --yes backlog.md init "<project-name>" --defaults --agent-instructions none`
  (adding `--no-git` outside a Git repository) and blocks if that fails.
- Install workflow version `1.0.0`.
- Preserve all existing task files, Backlog.md configuration, requirement documents, source code, and non-managed instructions.
- Insert or update one managed block in `CLAUDE.md`, and in `AGENTS.md` when that
  file already exists. `AGENTS.md` is never created from nothing.
- Create `.agent-workflow/PROJECT.md` only when absent; never replace an existing project configuration.
- Default mode is manual.
- Do not start planning or implementation after installation.

## audit

Read-only operation.

Check:

- Backlog.md workspace presence
- Workflow version
- Managed file presence and content
- Default mode
- Project skill frontmatter
- Grilling skill presence
- Managed block count and content in each entry file
- Project configuration presence
- Drift or unmanaged-path conflicts
- Recorded `PROJECT.md` facts that no longer match repository evidence. These are
  advisory: `audit` reports them, but they never block `apply` or `upgrade`.

`audit` does not inspect `README.md`; no operation in this workflow writes to it.

Return nonzero when drift, missing files, or conflicts exist. Do not repair anything.

## upgrade

- Refuse to downgrade a project with a newer workflow version.
- Replace older managed templates with version `1.0.0`.
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
```

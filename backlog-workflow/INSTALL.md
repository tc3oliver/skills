# Installation

Use one of the packaged installers. Each copies exactly the files the package
tracks, so nothing local — build output, caches, or agent session state that
tools drop into a working tree — is installed alongside the skill.

Agent Skills CLI:

```bash
npx skills add tc3oliver/skills
```

Claude Code plugin:

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

## Manual install

From a clone, copy through Git so the tracked file list is the manifest — an
untracked file cannot be copied even if it is sitting in the working tree:

```bash
mkdir -p ~/.claude/skills
git archive HEAD backlog-workflow | tar -x -C ~/.claude/skills
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
git archive HEAD backlog-workflow | tar -x -C "$HOME\.claude\skills"
```

If `~/.claude/skills` did not exist when Claude Code started, restart Claude Code once.

## Applying the workflow to a project

The installer is a plain Python script, so every agent uses the same three
actions. Run them from the project root:

```bash
python3 <skill-dir>/scripts/install.py apply     # install or refresh
python3 <skill-dir>/scripts/install.py audit     # read-only drift check
python3 <skill-dir>/scripts/install.py upgrade   # explicit version upgrade
```

`<skill-dir>` is where the package was installed — `~/.claude/skills/backlog-workflow`
for a Claude Code install, or the cloned `backlog-workflow` directory. Add
`--project <path>` to target a repository other than the working directory.

`apply` requires a working Backlog.md CLI and fails with the repository
unchanged if none verifies. It is idempotent: re-running a current install
reports `Clean` and writes nothing.

### Claude Code

The same actions are exposed as slash commands:

```text
/backlog-workflow apply
/backlog-workflow audit
/backlog-workflow upgrade
```

After an install or upgrade that touched `.claude/skills`, run `/reload-skills`
or start a new session so the adapters are picked up. Then use the workflow
through its slash commands:

```text
/backlog-plan <requirement or PRD path>
/backlog-review [requirement or PRD path]
/backlog-run <TASK-ID>
/backlog-auto [TASK-ID]
```

### Codex and OpenCode

Run the installer with `python3` as shown above; there is no runtime-specific
install step. `.agents/skills` is the native project skills directory for both
Codex and OpenCode, so the installed skills are discovered automatically — the
canonical layer is not a compatibility shim for them, it is their normal
location.

Invoke a workflow by name, the way you invoke any other skill:

```text
Use the backlog-plan skill for docs/prd.md
Use the backlog-run skill for TASK-12
```

If an agent does not pick the skill up, name the file directly
(`Follow .agents/skills/backlog-run/SKILL.md for TASK-12`); the `AGENTS.md`
managed block also lists each skill and when to use it, so a plain request like
"plan this requirement" routes correctly.

`.claude/` is ignored by these agents; slash commands are a Claude Code
interface, not part of the protocol.

### Switching agents on the same repository

No migration or re-install is needed. `.agents/skills`, `.agent-workflow`,
`AGENTS.md`, and Backlog.md task state are shared, so a project planned in
Claude Code can be executed in OpenCode or Codex and back. Only the invocation
syntax differs.

## Updating

Update the package first, then refresh the project:

```bash
npx skills add tc3oliver/skills          # Agent Skills CLI
git pull                                 # or, from a clone
```

Claude Code plugin users update with `/plugin update tc3oliver-skills`.

Then, in each project using the workflow:

```bash
python3 <skill-dir>/scripts/install.py upgrade
```

Upgrades replace only managed files. `.agent-workflow/PROJECT.md`, Backlog.md
tasks and configuration, and any content outside the managed blocks in
`AGENTS.md` and `CLAUDE.md` are preserved. A 1.5.x install is migrated in place:
the canonical `.agents/skills` layer is created and the previously full
`.claude/skills` files are replaced by thin adapters. Run `audit` afterwards to
confirm a clean state.

## Agent compatibility

The portable core consists of `.agents/skills`, `.agent-workflow`, and
`AGENTS.md`. Agents enter through the `AGENTS.md` managed block, which names
each canonical skill and when to use it, so Codex and OpenCode can use the
workflow without runtime-specific skill discovery. Claude Code adds a
compatibility layer: `.claude/skills` generated adapters, `CLAUDE.md`, and the
optional plugin/slash-command UX.

`apply` manages separate safe-update blocks in `AGENTS.md` and `CLAUDE.md` (or
`.claude/CLAUDE.md`). Content outside the blocks remains user-owned.

## Backlog interface

backlog-workflow runs entirely on the Backlog.md CLI; MCP is not required and is
never installed or configured by this workflow. If you want the optional Backlog.md
MCP server, configure it yourself according to the Backlog.md documentation.

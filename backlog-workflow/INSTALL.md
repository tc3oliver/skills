# Installation

Copy this entire `backlog-workflow` directory to your personal Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
cp -R backlog-workflow ~/.claude/skills/backlog-workflow
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force ".\backlog-workflow" "$HOME\.claude\skills\backlog-workflow"
```

If `~/.claude/skills` did not exist when Claude Code started, restart Claude Code once.

From a new or existing project:

```text
/backlog-workflow apply
```

Read-only drift check:

```text
/backlog-workflow audit
```

Explicit workflow upgrade:

```text
/backlog-workflow upgrade
```

Default manual flow:

```text
/backlog-plan <requirement or PRD path>
/backlog-review [requirement or PRD path]
/backlog-run <TASK-ID>
```

Explicit automatic flow:

```text
/backlog-auto
/backlog-auto <TASK-ID>
```

## Other coding agents

The slash commands are Claude Code specific, but the process is not. `apply`
installs `.agent-workflow/WORKFLOW.md` and `.agent-workflow/PROJECT.md`, which are
plain Markdown, and drives tasks through the Backlog.md CLI. Any agent that can
read those files and run a shell command can follow the same workflow.

`apply` manages one block in `CLAUDE.md` (or `.claude/CLAUDE.md`) and one block in
`AGENTS.md`. `AGENTS.md` is created when absent, so agents that read it pick up
the workflow automatically — no manual opt-in required.

## Backlog interface

backlog-workflow runs entirely on the Backlog.md CLI; MCP is not required and is
never installed or configured by this workflow. If you want the optional Backlog.md
MCP server, configure it yourself according to the Backlog.md documentation.

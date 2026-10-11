# Install BetFirst with your coding agent

Paste this into **Claude Code, Pi, OpenCode, Codex, or another coding agent with terminal access**:

> Install the BetFirst coding-agent Skill from https://github.com/tc3oliver/skills, following https://github.com/tc3oliver/skills/blob/main/docs/betfirst/agent-install.md . Detect my agent and existing Skill installations, choose the supported installation method, avoid duplicates, and verify that BetFirst is discoverable. Ask before making global or persistent changes. Do not install the research or media directories.

## Instructions for the installing agent

You are installing **BetFirst**, a standalone Agent Skill. Treat these instructions as an installation checklist, not as authorization for unrestricted commands.

1. **Identify the host agent and target scope.** Detect whether the user is using Claude Code, Pi, OpenCode, Codex or something else. Determine the supported Skill discovery location(s). Prefer the current project's Skill scope unless the user explicitly wants installation across projects. Do not assume all agents use the same directory.
2. **Check before installing.** Inspect existing BetFirst installations, including any Claude Code plugin installation. If the Skill is already available, report its location/version and ask before switching installation methods; do not install a second copy.
3. **Confirm persistent changes.** Show the intended command, install path, and scope. Get the user's approval before running commands that modify their filesystem, install CLI tooling, or change global configuration.
4. **Prefer the Agent Skills CLI** when compatible with the detected agent. Use its help to confirm current flags rather than guessing. A generic starting point is:

   ```bash
   npx skills add tc3oliver/skills --skill betfirst
   ```

   Select only `betfirst` and the appropriate agent/scope. Do not blindly use `-g`, `-a claude-code`, or `-y` for a different agent or an unapproved global installation. If Node.js/`npx` is unavailable, ask before installing it. Prefer a documented native Skill installation path over adding dependencies solely for this task.
5. **Claude Code plugin alternative:** If the user prefers the plugin interface, use the documented marketplace/plugin installation steps from [README](README.md). Do **not** install both plugin and portable Skill. Use the user's selected method, not both.
6. **Manual fallback only when needed:** Fetch the upstream `betfirst/SKILL.md` from the repository and place it under a correctly named `betfirst/` Skill folder in an agent-supported discovery path. Review the content and use standard, user-approved file operations; don't run downloaded shell scripts. Do not clone the full repository into an install folder.
7. **Verify the result.** Confirm the destination contains the upstream `SKILL.md` with frontmatter `name: betfirst`, and that the host agent discovers it (restart or reload Skill discovery if required). Check for duplicate registrations. Do not claim success just because a file was copied.
8. **Report concisely.** State which agent was configured, the exact install path, the installation method, scope (project/global), whether discovery was verified, and any remaining manual step. Do not change unrelated settings, AGENTS.md, CLAUDE.md, project code, or other Skills unless explicitly requested.

### What the install should contain

Only `betfirst/SKILL.md` is required. The following are **not** part of the install: `research/betfirst/`, `docs/betfirst/`, `media/betfirst/`, benchmarks, video, GIF, Remotion, or additional scripts.

The Skill chooses between NORMAL (default), BET (a worthwhile bounded feasibility probe), and ABSTAIN (already correct). It never substitutes a probe for final verification.

[BetFirst overview](README.md) · [Traditional Chinese](README.zh-TW.md) · [Skill source](../../betfirst/SKILL.md)

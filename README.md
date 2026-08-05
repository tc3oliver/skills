# Claude Skills

[Claude Code](https://claude.com/claude-code) skills for keeping agents on rails.

Coding agents drift. They start implementing before the requirement is settled,
invent validation commands that do not exist, mark work done without evidence,
and keep going when they should have stopped to ask. Meanwhile the `CLAUDE.md`
meant to prevent all that fills up with stale directory trees and vague advice,
and gets loaded into context on every single task.

These skills attack both ends of that problem. They are deliberately small,
do one thing each, and are meant to be forked and adapted.

| Skill | What it does |
|---|---|
| [backlog-workflow](backlog-workflow/) | Installs a versioned, task-driven workflow built on [Backlog.md](https://backlog.md). Adds `/backlog-plan`, `/backlog-run`, and `/backlog-auto`, keeping requirements, task decomposition, and validation evidence as separate sources of truth. Manual by default — automatic execution never starts implicitly. |
| [audit-claude-md](audit-claude-md/) | Audits a project's `CLAUDE.md`, nested `CLAUDE.md`, and path-scoped rules. Gives every rule one disposition — keep, move to a narrower scope, extract into a skill, rewrite, or delete — and applies the changes rather than just reporting them. |
| [diagnosing-bugs](diagnosing-bugs/) | A six-phase discipline for hard bugs: build a tight, red-capable feedback loop before hypothesising, rank falsifiable hypotheses, instrument one variable at a time, then fix with a regression test at a correct seam. |
| [writing-for-agents](writing-for-agents/) | Reference for writing any document an agent consumes — skills, `AGENTS.md`, `CLAUDE.md`. Covers context pointers, the information hierarchy, completion criteria, and when a document is worth splitting. |

## Install

### As a Claude Code plugin

Installs all skills as a managed bundle that updates when you pull:

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

Skills are namespaced: `/tc3oliver-skills:backlog-workflow`,
`/tc3oliver-skills:audit-claude-md`, `/tc3oliver-skills:diagnosing-bugs`,
`/tc3oliver-skills:writing-for-agents`.

### By copying the files

Skills live in `~/.claude/skills/`. Take just the one you want:

```bash
git clone https://github.com/tc3oliver/skills.git tc3oliver-skills
cp -R tc3oliver-skills/backlog-workflow ~/.claude/skills/
```

Or clone the whole set into place:

```bash
git clone https://github.com/tc3oliver/skills.git ~/.claude/skills
```

Restart Claude Code if `~/.claude/skills` did not exist beforehand. Copied
skills keep their short names (`/backlog-workflow`) and are yours to edit.

Each skill is self-contained — see its own README or `SKILL.md` for usage.
`backlog-workflow` has [detailed install notes](backlog-workflow/INSTALL.md).

## Requirements

All skills need Claude Code. `backlog-workflow` additionally needs Node.js
(`npx`, for the Backlog.md CLI) and Python 3 for its installer.

## Development

`backlog-workflow` ships tests:

```bash
cd backlog-workflow
python3 -m unittest discover -s tests
python3 scripts/validate_package.py
```

## License

MIT — see [LICENSE](LICENSE).

Several skills are sourced from [mattpocock/skills](https://github.com/mattpocock/skills)
by Matt Pocock, used under the MIT License; each carries its own `LICENSE` and
an attribution comment in its `SKILL.md`:

- `backlog-workflow` bundles the `grilling` skill.
- `diagnosing-bugs` and `writing-for-agents` are copied in full.

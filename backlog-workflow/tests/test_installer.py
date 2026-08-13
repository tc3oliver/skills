from __future__ import annotations

import hashlib
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.py"
VALIDATOR = ROOT / "scripts" / "validate_package.py"
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "legacy_task_template_1.0.0.md"

# Import the installer as a module for constants without invoking it as a script.
sys.path.insert(0, str(ROOT / "scripts"))
import install  # noqa: E402

MANAGED_BEGIN = "<!-- backlog-workflow:begin"
MANAGED_END = "<!-- backlog-workflow:end -->"

# Stands in for the Backlog.md CLI. Mirrors the real 1.50 surface the installer
# touches: `instructions overview` (verification), `init`, `config get statuses`,
# and the two JSON task reads the documentation audit uses. Task data comes from
# BACKLOG_FAKE_TASKS, a JSON map of task id -> documentation list.
GOOD_BACKLOG_SCRIPT = """#!/bin/sh
if [ "$1" = "instructions" ] && [ "$2" = "overview" ]; then
  printf '## Backlog.md Overview (CLI)\\n\\nbacklog instructions task-creation\\n'
  exit 0
fi
if [ "$1" = "init" ]; then
  mkdir -p backlog/tasks
  printf 'project_name: %s\\nstatuses: ["To Do", "In Progress", "Done"]\\n' "$2" > backlog/config.yml
  exit 0
fi
if [ "$1" = "config" ] && [ "$2" = "get" ] && [ "$3" = "statuses" ]; then
  printf 'To Do, In Progress, Done\\n'
  exit 0
fi
if [ "$1" = "task" ]; then
  python3 - "$2" <<'PYEOF'
import json, os, sys
tasks = json.loads(os.environ.get("BACKLOG_FAKE_TASKS", "{}"))
arg = sys.argv[1] if len(sys.argv) > 1 else "list"
if arg == "list":
    print(json.dumps({"schemaVersion": 1, "kind": "task-list",
                      "tasks": [{"id": t} for t in sorted(tasks)]}))
else:
    print(json.dumps({"schemaVersion": 1, "kind": "task-view",
                      "task": {"id": arg, "documentation": tasks.get(arg, [])}}))
PYEOF
  exit 0
fi
exit 0
"""

BAD_BACKLOG_SCRIPT = """#!/bin/sh
echo "this is not backlog.md"
exit 0
"""

# Shadows the real npx so candidates like `npx backlog.md` cannot reach the
# network. Models the real "npx present but cannot run Backlog.md" case.
BROKEN_NPX_SCRIPT = """#!/bin/sh
echo "npx unavailable in sandbox" >&2
exit 127
"""

# A fake npx that emulates `npx [--yes] backlog.md instructions overview` so the
# `npx backlog.md` candidate verifies hermetically (no network).
GOOD_NPX_SCRIPT = """#!/bin/sh
for a in "$@"; do
  if [ "$a" = "overview" ]; then
    printf '## Backlog.md Overview (CLI)\\n\\nbacklog instructions task-creation\\n'
    exit 0
  fi
done
exit 0
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class InstallerTests(unittest.TestCase):
    def fake_bin(self, *kinds: str) -> Path:
        d = Path(tempfile.mkdtemp(prefix="bw-bin-"))
        for kind in kinds:
            if kind in ("good", "bad"):
                target = d / "backlog"
                target.write_text(
                    GOOD_BACKLOG_SCRIPT if kind == "good" else BAD_BACKLOG_SCRIPT, encoding="utf-8"
                )
            elif kind == "good-npx":
                target = d / "npx"
                target.write_text(GOOD_NPX_SCRIPT, encoding="utf-8")
            elif kind == "broken-npx":
                target = d / "npx"
                target.write_text(BROKEN_NPX_SCRIPT, encoding="utf-8")
            else:
                raise ValueError(kind)
            target.chmod(0o755)
        return d

    def minimal_path(self, *extra: str) -> str:
        """A PATH that contains git/python and `extra` dirs. `extra` is placed
        first so its tools shadow system ones (e.g. a broken npx)."""
        dirs: list[str] = list(extra)
        for tool in ("git", "python3"):
            loc = shutil.which(tool)
            if loc:
                d = str(Path(loc).parent)
                if d not in dirs:
                    dirs.append(d)
        for d in ("/usr/bin", "/bin"):
            if d not in dirs:
                dirs.append(d)
        return os.pathsep.join(dict.fromkeys(dirs))

    def env_with(self, *kinds: str) -> dict:
        env = dict(os.environ)
        env["PATH"] = self.minimal_path(str(self.fake_bin(*kinds)))
        return env

    def make_project(self, cli: str = "good", workspace: bool = True) -> tuple[Path, dict]:
        root = Path(tempfile.mkdtemp(prefix="backlog-workflow-test-"))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        if workspace:
            (root / "backlog/tasks").mkdir(parents=True)
            (root / "backlog/config.yml").write_text(
                'project_name: demo\ntask_prefix: DEMO\n'
                'statuses: ["To Do", "In Progress", "Done"]\n',
                encoding="utf-8",
            )
        (root / "package.json").write_text(
            '{"name":"demo","scripts":{"lint":"eslint .","typecheck":"tsc --noEmit",'
            '"test":"vitest run","build":"vite build"}}',
            encoding="utf-8",
        )
        if cli == "good":
            # Fake `backlog` verifies first, so npx (still on PATH) is never invoked.
            env = dict(os.environ)
            env["PATH"] = f"{self.fake_bin('good')}{os.pathsep}{env.get('PATH', '')}"
            return root, env
        if cli == "bad":
            return root, self.env_with("bad", "broken-npx")
        if cli == "none":
            return root, self.env_with("broken-npx")
        if cli == "global":
            # Verified global `backlog`, npx unavailable (broken) — init must not need npx.
            return root, self.env_with("good", "broken-npx")
        if cli == "npx-only":
            # Only `npx backlog.md` verifies; no global `backlog`.
            return root, self.env_with("good-npx")
        raise ValueError(cli)

    def run_installer(
        self, root: Path, action: str, env: dict | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), action, "--project", str(root)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )

    def apply(self, root: Path, env: dict) -> subprocess.CompletedProcess[str]:
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    # 1. fresh apply creates the 1.4.0 workflow
    def test_fresh_apply_creates_1_4_0_workflow(self) -> None:
        root, env = self.make_project()
        result = self.apply(root, env)
        self.assertIn("- Status: Installed", result.stdout)
        self.assertEqual(read(root / ".agent-workflow/VERSION").strip(), "1.4.0")
        self.assertIn("workflow_version: 1.4.0", read(root / ".agent-workflow/config.yml"))
        self.assertTrue((root / ".agent-workflow/TASK-POLICY.md").exists())
        self.assertFalse((root / ".agent-workflow/TASK-TEMPLATE.md").exists())

    # 20. managed files contain version 1.4.0
    def test_managed_files_contain_1_4_0(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for rel in (
            ".agent-workflow/WORKFLOW.md",
            ".agent-workflow/PLAN.md",
            ".agent-workflow/EXECUTION.md",
            ".agent-workflow/AUTO.md",
            ".agent-workflow/config.yml",
            ".agent-workflow/TASK-POLICY.md",
            ".claude/skills/backlog-plan/SKILL.md",
            ".claude/skills/backlog-review/SKILL.md",
            ".claude/skills/backlog-run/SKILL.md",
            ".claude/skills/backlog-auto/SKILL.md",
        ):
            self.assertIn("1.4.0", read(root / rel), f"missing 1.4.0 marker in {rel}")

    # Progressive disclosure: WORKFLOW.md holds only the shared invariants, and
    # each skill loads exactly the phase reference it needs.
    def test_phase_references_are_installed_and_scoped(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)

        workflow = read(root / ".agent-workflow/WORKFLOW.md")
        self.assertIn("## Canonical Completion Gate", workflow)
        self.assertIn("## Mode routing", workflow)
        # Phase detail lives in the phase files, not in the shared file.
        self.assertNotIn("## Decomposition review", workflow)
        self.assertNotIn("## Parallel automatic execution", workflow)

        self.assertIn("## Decomposition review", read(root / ".agent-workflow/PLAN.md"))
        self.assertIn("## Approval boundary", read(root / ".agent-workflow/EXECUTION.md"))
        self.assertIn("## Batch merge", read(root / ".agent-workflow/AUTO.md"))

        expected = {
            "backlog-plan": {"PLAN.md"},
            "backlog-review": {"PLAN.md"},
            "backlog-run": {"EXECUTION.md"},
            "backlog-auto": {"AUTO.md", "EXECUTION.md"},
        }
        for skill, wanted in expected.items():
            text = read(root / f".claude/skills/{skill}/SKILL.md")
            self.assertIn(".agent-workflow/WORKFLOW.md", text, skill)
            for reference in ("PLAN.md", "EXECUTION.md", "AUTO.md"):
                mentioned = f".agent-workflow/{reference}" in text
                self.assertEqual(mentioned, reference in wanted, f"{skill} -> {reference}")

    # The four completion conditions are stated once; everything else points at
    # the Canonical Completion Gate by name.
    def test_completion_gate_is_defined_once(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        condition = "The task record contains validation evidence."
        self.assertIn(condition, read(root / ".agent-workflow/WORKFLOW.md"))
        for rel in (
            ".agent-workflow/PLAN.md",
            ".agent-workflow/EXECUTION.md",
            ".agent-workflow/AUTO.md",
            ".agent-workflow/TASK-POLICY.md",
            ".claude/skills/backlog-run/SKILL.md",
            ".claude/skills/backlog-auto/SKILL.md",
        ):
            self.assertNotIn(condition, read(root / rel), rel)
        self.assertIn("Canonical Completion Gate", read(root / ".agent-workflow/TASK-POLICY.md"))

    # Dependency-ready selection uses the Backlog.md native query rather than a
    # hand-rebuilt dependency graph.
    def test_selection_uses_native_ready_query(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        auto = read(root / ".agent-workflow/AUTO.md")
        self.assertIn("--ready", auto)
        self.assertIn("--sort priority", auto)
        self.assertIn("--ready", read(root / ".agent-workflow/EXECUTION.md"))

    # Requirement traceability rides on the native documentation field.
    def test_requirement_source_uses_native_documentation_field(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        self.assertIn("--doc", read(root / ".agent-workflow/WORKFLOW.md"))
        policy = read(root / ".agent-workflow/TASK-POLICY.md")
        self.assertIn("documentation", policy)
        # The custom Markdown pseudo-field it replaced must be gone.
        self.assertNotIn("### Requirement Source", policy)

    # upgrading a 1.3.0 install adds the phase references it never had
    def test_upgrade_installs_phase_references(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)

        # Model a 1.3.0 install: WORKFLOW.md carried every phase, alone.
        for name in ("PLAN.md", "EXECUTION.md", "AUTO.md"):
            (root / ".agent-workflow" / name).unlink()
        (root / ".agent-workflow/VERSION").write_text("1.3.0\n", encoding="utf-8")
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 2)

        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ("PLAN.md", "EXECUTION.md", "AUTO.md"):
            self.assertIn(f".agent-workflow/{name}", result.stdout)
            self.assertTrue((root / ".agent-workflow" / name).exists(), name)
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    # the decomposition review is a separate, user-triggered pass after planning
    def test_decomposition_review_is_a_separate_pass(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        self.assertIn("## Decomposition review", read(root / ".agent-workflow/PLAN.md"))
        self.assertIn("review_skill: backlog-review", read(root / ".agent-workflow/config.yml"))

        # planning hands off to the review instead of reviewing its own output
        plan = read(root / ".claude/skills/backlog-plan/SKILL.md")
        self.assertIn("/backlog-review", plan)
        self.assertNotIn("- Next: </backlog-run TASK-ID>", plan)

        # the review itself is read-only until the user confirms a fix
        review = read(root / ".claude/skills/backlog-review/SKILL.md")
        self.assertIn("read-only", review)
        self.assertIn("Verdict", review)

        # automatic execution never runs the interactive review
        self.assertNotIn("/backlog-review", read(root / ".claude/skills/backlog-auto/SKILL.md"))

    # upgrading an older install adds a newly managed skill that it never had
    def test_upgrade_installs_newly_managed_skill(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)

        # Model a pre-1.3.0 install: the review skill did not exist yet.
        shutil.rmtree(root / ".claude/skills/backlog-review")
        (root / ".agent-workflow/VERSION").write_text("1.2.0\n", encoding="utf-8")
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 2)

        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(".claude/skills/backlog-review/SKILL.md", result.stdout)
        self.assertTrue((root / ".claude/skills/backlog-review/SKILL.md").exists())
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    # fresh apply defaults to sequential /backlog-auto (opt-in parallelism)
    def test_fresh_apply_defaults_to_sequential_auto(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        config = read(root / ".agent-workflow/config.yml")
        self.assertIn("max_parallel_tasks: 1", config)
        self.assertIn("max_parallel_tasks", read(root / ".agent-workflow/AUTO.md"))
        auto_skill = read(root / ".claude/skills/backlog-auto/SKILL.md")
        self.assertIn("max_parallel_tasks", auto_skill)

    # upgrade preserves a project-raised max_parallel_tasks value
    def test_upgrade_preserves_custom_max_parallel_tasks(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        config_path = root / ".agent-workflow/config.yml"
        config_path.write_text(
            read(config_path).replace("max_parallel_tasks: 1", "max_parallel_tasks: 3"),
            encoding="utf-8",
        )
        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("max_parallel_tasks: 3", read(config_path))

    # fresh apply prompts the user to reload skills since it wrote new
    # .claude/skills/* files that Claude Code only loads at session start
    def test_fresh_apply_prints_reload_next_step(self) -> None:
        root, env = self.make_project()
        result = self.apply(root, env)
        self.assertIn("- Next step: run /reload-skills", result.stdout)

    # 2. apply is idempotent
    def test_apply_is_idempotent(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        second = self.run_installer(root, "apply", env)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("- Status: Clean", second.stdout)
        self.assertIn("- Changes: none", second.stdout)
        # nothing changed on the second apply, so no reload prompt is needed
        self.assertNotIn("- Next step:", second.stdout)

    # 4. upgrade is idempotent
    def test_upgrade_is_idempotent(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        first = self.run_installer(root, "upgrade", env)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn("- Changes: none", first.stdout)
        second = self.run_installer(root, "upgrade", env)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("- Changes: none", second.stdout)

    # 3. audit is read-only and detects drift
    def test_audit_is_read_only_and_detects_drift(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        workflow = root / ".agent-workflow/WORKFLOW.md"
        workflow.write_text(read(workflow) + "\nlocal drift\n", encoding="utf-8")
        before = digest(workflow)

        audit = self.run_installer(root, "audit", env)
        self.assertEqual(audit.returncode, 2)
        self.assertIn("content drift: .agent-workflow/WORKFLOW.md", audit.stdout)
        self.assertNotIn("- Next step:", audit.stdout)  # audit never writes files
        self.assertEqual(digest(workflow), before)  # nothing repaired

        workflow.write_text(install.template_text(Path(".agent-workflow/WORKFLOW.md")), encoding="utf-8")
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    # 5 + 6. existing tasks and README remain byte-identical
    def test_existing_tasks_and_readme_preserved(self) -> None:
        root, env = self.make_project()
        readme = root / "README.md"
        readme.write_text("public docs\n", encoding="utf-8")
        task = root / "backlog/tasks/demo-1 - Existing task.md"
        task.write_text("existing history\n", encoding="utf-8")
        before_readme, before_task = digest(readme), digest(task)

        self.apply(root, env)

        self.assertEqual(digest(readme), before_readme)
        self.assertEqual(digest(task), before_task)

    # 7. existing Backlog configuration is preserved apart from the one additive
    # change the workflow needs: a status to park blocked tasks in.
    def test_backlog_config_preserved_except_blocked_status(self) -> None:
        root, env = self.make_project()
        config = root / "backlog/config.yml"
        config.write_text(
            'project_name: kept\ntask_prefix: KEPT\n'
            'statuses: ["To Do", "In Progress", "Done"]\ndefault_editor: "vim"\n',
            encoding="utf-8",
        )
        result = self.apply(root, env)
        self.assertIn("added 'Blocked' status", result.stdout)

        after = read(config)
        self.assertIn('statuses: ["To Do", "In Progress", "Blocked", "Done"]', after)
        # Existing statuses keep their order; every other key is untouched.
        for line in ("project_name: kept", "task_prefix: KEPT", 'default_editor: "vim"'):
            self.assertIn(line, after)

    # A project that already parks blocked work somewhere keeps its own status
    # instead of gaining a second one.
    def test_existing_blocked_status_is_reused(self) -> None:
        root, env = self.make_project()
        config = root / "backlog/config.yml"
        config.write_text(
            'project_name: demo\nstatuses: ["Backlog", "WIP", "On Hold", "Shipped"]\n',
            encoding="utf-8",
        )
        before = digest(config)
        result = self.apply(root, env)
        self.assertNotIn("added 'Blocked' status", result.stdout)
        self.assertEqual(digest(config), before)

        # The recorded roles follow the project's own vocabulary.
        workflow_config = read(root / ".agent-workflow/config.yml")
        self.assertIn("not_started: Backlog", workflow_config)
        self.assertIn("active: WIP", workflow_config)
        self.assertIn("blocked: On Hold", workflow_config)
        self.assertIn("done: Shipped", workflow_config)
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    # blocked must never collapse into not_started: /backlog-auto selects on
    # not_started, so equal values would re-select every blocked task.
    def test_blocked_status_differs_from_not_started(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        config = read(root / ".agent-workflow/config.yml")
        roles = dict(
            line.strip().split(": ", 1)
            for line in config.splitlines()
            if line.startswith("  ") and line.strip().split(":")[0] in
            ("not_started", "active", "blocked", "done")
        )
        self.assertEqual(len(set(roles.values())), 4, roles)
        self.assertNotEqual(roles["blocked"], roles["not_started"])
        # Every role names a real Backlog.md status.
        statuses = read(root / "backlog/config.yml")
        for value in roles.values():
            self.assertIn(f'"{value}"', statuses)

        # Collapsing the two is drift, not a silent misconfiguration.
        path = root / ".agent-workflow/config.yml"
        path.write_text(config.replace("blocked: Blocked", "blocked: To Do"), encoding="utf-8")
        audit = self.run_installer(root, "audit", env)
        self.assertEqual(audit.returncode, 2)
        self.assertIn("would be selected again", audit.stdout)

    # a role naming a status the project does not have is drift
    def test_unknown_status_role_is_drift(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        path = root / ".agent-workflow/config.yml"
        path.write_text(read(path).replace("active: In Progress", "active: Doing"), encoding="utf-8")
        audit = self.run_installer(root, "audit", env)
        self.assertEqual(audit.returncode, 2)
        self.assertIn("is not a configured", audit.stdout)

    # upgrade keeps a project's own status vocabulary
    def test_upgrade_preserves_custom_status_roles(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        path = root / ".agent-workflow/config.yml"
        (root / "backlog/config.yml").write_text(
            'project_name: demo\nstatuses: ["Backlog", "WIP", "On Hold", "Shipped"]\n',
            encoding="utf-8",
        )
        path.write_text(
            read(path)
            .replace("not_started: To Do", "not_started: Backlog")
            .replace("active: In Progress", "active: WIP")
            .replace("blocked: Blocked", "blocked: On Hold")
            .replace("done: Done", "done: Shipped"),
            encoding="utf-8",
        )
        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        after = read(path)
        self.assertIn("not_started: Backlog", after)
        self.assertIn("blocked: On Hold", after)
        self.assertIn("done: Shipped", after)

    # a 1.3.0 install predates the status roles; upgrade fills them in from the
    # project's real Backlog.md configuration
    def test_upgrade_adds_status_roles_to_older_install(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        path = root / ".agent-workflow/config.yml"
        without_roles = re.sub(
            r"(?ms)^# Which Backlog\.md status.*?^statuses:\n(?:  \w+: .*\n)+\n", "", read(path)
        )
        self.assertNotIn("not_started:", without_roles)
        path.write_text(without_roles, encoding="utf-8")
        (root / ".agent-workflow/VERSION").write_text("1.3.0\n", encoding="utf-8")
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 2)

        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("blocked: Blocked", read(path))
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    # 8. existing PROJECT.md is preserved
    def test_existing_project_md_preserved(self) -> None:
        root, env = self.make_project()
        project_md = root / ".agent-workflow/PROJECT.md"
        project_md.parent.mkdir(parents=True, exist_ok=True)
        project_md.write_text("project-specific configuration\n", encoding="utf-8")
        before = digest(project_md)
        self.apply(root, env)
        self.assertEqual(digest(project_md), before)

    # 22. PROJECT.md records the verified Backlog CLI correctly
    def test_project_md_records_verified_backlog_cli(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        text = read(root / ".agent-workflow/PROJECT.md")
        cli_line = next(line for line in text.splitlines() if line.startswith("- Backlog CLI:"))
        self.assertNotIn("not detected", cli_line)
        self.assertIn("backlog", cli_line)

    # 9. CLAUDE.md existing content is preserved
    def test_claude_md_preserves_existing_content(self) -> None:
        root, env = self.make_project()
        claude = root / "CLAUDE.md"
        claude.write_text("# Existing rules\n\nNever delete production data.\n", encoding="utf-8")
        self.apply(root, env)
        content = read(claude)
        self.assertIn("# Existing rules", content)
        self.assertIn("Never delete production data.", content)

    # 10. AGENTS.md existing content is preserved
    def test_agents_md_preserves_existing_content(self) -> None:
        root, env = self.make_project()
        agents = root / "AGENTS.md"
        agents.write_text("# Shared agent rules\n\nKeep secrets out of logs.\n", encoding="utf-8")
        self.apply(root, env)
        content = read(agents)
        self.assertIn("Keep secrets out of logs.", content)
        self.assertEqual(content.count(MANAGED_BEGIN), 1)
        self.assertEqual(content.count(MANAGED_END), 1)

    # 11. AGENTS.md is created when absent
    def test_agents_md_created_when_absent(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        agents = root / "AGENTS.md"
        self.assertTrue(agents.exists(), "AGENTS.md must be created when absent")
        content = read(agents)
        self.assertEqual(content.count(MANAGED_BEGIN), 1)
        self.assertEqual(content.count(MANAGED_END), 1)

    # 12. exactly one managed block exists in each entry file
    def test_exactly_one_managed_block_per_entry_file(self) -> None:
        root, env = self.make_project()
        (root / "AGENTS.md").write_text("# Agent rules\n", encoding="utf-8")
        self.apply(root, env)
        for entry in (root / "CLAUDE.md", root / "AGENTS.md"):
            content = read(entry)
            self.assertEqual(content.count(MANAGED_BEGIN), 1, f"{entry} begin count")
            self.assertEqual(content.count(MANAGED_END), 1, f"{entry} end count")
            self.assertLess(content.index(MANAGED_BEGIN), content.index(MANAGED_END))

    # 13. malformed/duplicate managed blocks fail safely
    def test_malformed_block_fails_safely(self) -> None:
        root, env = self.make_project()
        agents = root / "AGENTS.md"
        agents.write_text(
            f"{MANAGED_BEGIN} version=1.1.0 -->\nA\n{MANAGED_END}\n"
            f"{MANAGED_BEGIN} version=1.1.0 -->\nB\n",
            encoding="utf-8",
        )
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("malformed", result.stdout.lower())

    # 14. unmanaged managed-path conflict fails without partial installation
    def test_unmanaged_conflict_blocks_without_partial_install(self) -> None:
        root, env = self.make_project()
        conflict = root / ".agent-workflow/WORKFLOW.md"
        conflict.parent.mkdir(parents=True, exist_ok=True)
        conflict.write_text("user owned workflow\n", encoding="utf-8")

        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unmanaged file occupies managed path", result.stdout)
        self.assertFalse((root / ".claude/skills/backlog-plan/SKILL.md").exists())
        self.assertEqual(read(conflict), "user owned workflow\n")

    # 15. 1.0.x managed TASK-TEMPLATE.md migrates safely to TASK-POLICY.md
    def test_managed_task_template_migrates_on_apply(self) -> None:
        root, env = self.make_project()
        legacy = root / ".agent-workflow/TASK-TEMPLATE.md"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(LEGACY_FIXTURE.read_bytes())
        self.assertEqual(
            hashlib.sha256(legacy.read_bytes()).hexdigest(), install.LEGACY_TASK_TEMPLATE_HASH
        )

        result = self.apply(root, env)
        self.assertFalse(legacy.exists(), "managed TASK-TEMPLATE.md must be removed")
        self.assertTrue((root / ".agent-workflow/TASK-POLICY.md").exists())
        self.assertIn("removed deprecated managed file", result.stdout)

    def test_managed_task_template_migrates_on_upgrade(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        legacy = root / ".agent-workflow/TASK-TEMPLATE.md"
        legacy.write_bytes(LEGACY_FIXTURE.read_bytes())
        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(legacy.exists())
        self.assertIn("removed deprecated managed file", result.stdout)

    # 16. unmanaged TASK-TEMPLATE.md is never silently deleted
    def test_unmanaged_task_template_preserved(self) -> None:
        root, env = self.make_project()
        legacy = root / ".agent-workflow/TASK-TEMPLATE.md"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("# My own task template\nuser owned\n", encoding="utf-8")
        before = digest(legacy)

        result = self.apply(root, env)
        self.assertTrue(legacy.exists(), "unmanaged TASK-TEMPLATE.md must not be deleted")
        self.assertEqual(digest(legacy), before)
        self.assertNotIn("removed deprecated managed file", result.stdout)

    # 21. the workflow skills remain installed
    def test_workflow_skills_remain_installed(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for name in ("backlog-plan", "backlog-review", "backlog-run", "backlog-auto", "grilling"):
            self.assertTrue((root / f".claude/skills/{name}/SKILL.md").exists(), name)

    # 19. no /backlog skill is generated
    def test_no_backlog_skill_generated(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        names = set()
        for skill_md in (root / ".claude/skills").glob("*/SKILL.md"):
            for line in read(skill_md).splitlines():
                if line.startswith("name:"):
                    names.add(line.split(":", 1)[1].strip())
                    break
        self.assertNotIn("backlog", names)
        self.assertIn("backlog-plan", names)
        self.assertIn("backlog-review", names)
        self.assertIn("backlog-run", names)
        self.assertIn("backlog-auto", names)

    # 17 + stale-1.0 behavior. No installed skill/workflow references the board.
    def test_installed_workflow_has_no_stale_1_0_behavior(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        installed = []
        for path in (
            root / ".agent-workflow/WORKFLOW.md",
            root / ".agent-workflow/PLAN.md",
            root / ".agent-workflow/EXECUTION.md",
            root / ".agent-workflow/AUTO.md",
            root / ".agent-workflow/TASK-POLICY.md",
            root / ".claude/skills/backlog-plan/SKILL.md",
            root / ".claude/skills/backlog-review/SKILL.md",
            root / ".claude/skills/backlog-run/SKILL.md",
            root / ".claude/skills/backlog-auto/SKILL.md",
            root / ".claude/skills/grilling/SKILL.md",
        ):
            installed.append(read(path))
        for token in ("TASK-TEMPLATE.md", "Background board", "Board:"):
            for i, text in enumerate(installed):
                self.assertNotIn(token, text, f"stale token {token!r} in installed file #{i}")
        self.assertFalse((root / ".agent-workflow/TASK-TEMPLATE.md").exists())

    # 18. no installed workflow requires MCP
    def test_no_installed_workflow_requires_mcp(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for path in (root / ".agent-workflow/WORKFLOW.md", root / "CLAUDE.md", root / "AGENTS.md"):
            text = read(path)
            self.assertNotIn("claude mcp add", text)
            self.assertNotIn("codex mcp add", text)
        workflow = read(root / ".agent-workflow/WORKFLOW.md")
        self.assertIn("optional", workflow.lower())
        self.assertIn("does not install", workflow.lower())

    # Requirement traceability rides on the native `documentation` field, so a
    # local reference that no longer resolves is a broken link between a task and
    # its authority. Remote and opaque references are not filesystem-checkable and
    # must never be reported as missing.
    def audit_with_tasks(self, root: Path, env: dict, tasks: dict) -> subprocess.CompletedProcess[str]:
        env = dict(env)
        env["BACKLOG_FAKE_TASKS"] = json.dumps(tasks)
        return self.run_installer(root, "audit", env)

    def test_documentation_audit_accepts_resolvable_references(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        (root / "docs").mkdir()
        (root / "docs/PRD.md").write_text("# PRD\n", encoding="utf-8")
        (root / "SPEC.md").write_text("# Spec\n", encoding="utf-8")

        audit = self.audit_with_tasks(root, env, {
            "TASK-1": ["docs/PRD.md"],                        # existing local doc
            "TASK-2": ["docs/PRD.md#requirement-x"],          # local doc + fragment
            "TASK-3": ["SPEC.md"],                            # local doc at the root
            "TASK-4": ["https://example.com/spec#section"],   # remote URL
            "TASK-5": ["decision-3"],                         # opaque reference
            "TASK-6": [],                                     # no documentation
        })
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertIn("- Status: Clean", audit.stdout)

    def test_documentation_audit_reports_missing_local_reference(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        audit = self.audit_with_tasks(root, env, {"TASK-7": ["docs/GONE.md"]})
        self.assertEqual(audit.returncode, 2)
        self.assertIn("documentation reference not found", audit.stdout)
        self.assertIn("TASK-7", audit.stdout)
        self.assertIn("docs/GONE.md", audit.stdout)

    def test_documentation_audit_strips_fragment_before_checking(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        audit = self.audit_with_tasks(root, env, {"TASK-8": ["docs/GONE.md#anchor"]})
        self.assertEqual(audit.returncode, 2)
        # The report names the resolved path and the original reference.
        self.assertIn("TASK-8 -> docs/GONE.md", audit.stdout)
        self.assertIn("docs/GONE.md#anchor", audit.stdout)

    def test_documentation_audit_ignores_remote_and_opaque_references(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        audit = self.audit_with_tasks(root, env, {
            "TASK-9": [
                "https://example.com/prd.md",
                "http://internal/spec",
                "//cdn.example.com/spec.md",
                "www.example.com/spec.md",
                "mailto:owner@example.com",
                "decision-3",
                "RFC 2119",
                "/etc/absolute/spec.md",
                "~/notes/spec.md",
                "../outside/spec.md",
            ]
        })
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertNotIn("documentation reference not found", audit.stdout)

    # apply/upgrade check managed-file integrity, not project task content: a
    # broken documentation link must not block installing the workflow.
    def test_documentation_findings_do_not_block_apply(self) -> None:
        root, env = self.make_project()
        env = dict(env)
        env["BACKLOG_FAKE_TASKS"] = json.dumps({"TASK-1": ["docs/GONE.md"]})
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("- Status: Installed", result.stdout)

    # classification is pure and deterministic; assert it directly
    def test_local_documentation_path_classification(self) -> None:
        checked = {
            "docs/PRD.md": "docs/PRD.md",
            "docs/PRD.md#requirement-x": "docs/PRD.md",
            "SPEC.md": "SPEC.md",
            " docs/a b.md ": "docs/a b.md",
            "docs/nested/deep/file.txt": "docs/nested/deep/file.txt",
        }
        for reference, expected in checked.items():
            self.assertEqual(install.local_documentation_path(reference), expected, reference)
        for reference in (
            "https://example.com/a.md", "http://x/y", "//cdn/x.md", "www.x.com/a.md",
            "mailto:a@b.c", "decision-3", "RFC 2119", "/abs/a.md", "~/a.md",
            "../outside.md", "#anchor-only", "", "   ",
        ):
            self.assertIsNone(install.local_documentation_path(reference), reference)

    # 23. package validator passes
    def test_package_validator_passes(self) -> None:
        result = subprocess.run(
            ["python3", str(VALIDATOR)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Package validation passed", result.stdout)

    # Downgrade protection.
    def test_refuses_downgrade(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        (root / ".agent-workflow/VERSION").write_text("2.0.0\n", encoding="utf-8")
        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("newer than installer", result.stdout)

    # P1: a non-Backlog.md `backlog` in PATH is rejected (not trusted).
    def test_fake_backlog_in_path_is_rejected(self) -> None:
        root, env = self.make_project(cli="bad")
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Backlog.md CLI", result.stdout)
        # Nothing installed: the required interface did not verify.
        self.assertFalse((root / ".agent-workflow/PROJECT.md").exists())
        self.assertFalse((root / ".claude/skills/backlog-plan/SKILL.md").exists())

    # P1: no usable Backlog.md CLI at all blocks apply (never silently "not detected").
    def test_no_backlog_cli_blocks_apply(self) -> None:
        root, env = self.make_project(cli="none")
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("required interface", result.stdout.lower())
        self.assertFalse((root / ".agent-workflow/PROJECT.md").exists())

    # P1: audit also flags an unverifiable CLI.
    def test_audit_flags_unverified_cli(self) -> None:
        root, good_env = self.make_project()
        self.apply(root, good_env)
        _, none_env = self.make_project(cli="none")
        audit = self.run_installer(root, "audit", none_env)
        self.assertEqual(audit.returncode, 2)
        self.assertIn("Backlog.md CLI not verified", audit.stdout)

    # P1.1: fresh project, no verified CLI => apply fails with the repo unchanged
    # (no backlog/, .agent-workflow/, CLAUDE.md, or AGENTS.md created).
    def test_fresh_apply_without_cli_leaves_repo_unchanged(self) -> None:
        root, env = self.make_project(cli="none", workspace=False)
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("required interface", result.stdout.lower())
        self.assertFalse((root / "backlog").exists())
        self.assertFalse((root / ".agent-workflow").exists())
        self.assertFalse((root / "CLAUDE.md").exists())
        self.assertFalse((root / "AGENTS.md").exists())

    # P1.2 + P1.3: a verified global `backlog` (npx unavailable) initializes a
    # fresh workspace, and PROJECT.md records that same verified command.
    def test_fresh_apply_initializes_with_verified_global_backlog(self) -> None:
        root, env = self.make_project(cli="global", workspace=False)
        result = self.run_installer(root, "apply", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("backlog workspace initialized", result.stdout)
        # The verified global command created the workspace (no npx needed).
        self.assertTrue((root / "backlog/config.yml").exists())
        self.assertTrue((root / "backlog/tasks").exists())
        # PROJECT.md records the same verified command used for initialization.
        cli_line = next(
            line for line in read(root / ".agent-workflow/PROJECT.md").splitlines()
            if line.startswith("- Backlog CLI:")
        )
        self.assertIn("`backlog`", cli_line)
        self.assertNotIn("npx", cli_line)

    # P2: a recorded, still-valid CLI is preferred; a newly available valid CLI
    # does not create false drift.
    def test_audit_prefers_recorded_cli_over_new_candidate(self) -> None:
        # Step 1: only `npx backlog.md` is available -> PROJECT.md records it.
        root, apply_env = self.make_project(cli="npx-only", workspace=True)
        self.apply(root, apply_env)
        cli_line = next(
            line for line in read(root / ".agent-workflow/PROJECT.md").splitlines()
            if line.startswith("- Backlog CLI:")
        )
        self.assertIn("`npx backlog.md`", cli_line)

        # Step 2: a valid global `backlog` later becomes available too.
        audit_env = self.env_with("good", "good-npx")
        self.assertTrue(shutil.which("backlog", path=audit_env["PATH"]), "global backlog is now present")

        # Audit stays clean because the recorded `npx backlog.md` still verifies.
        audit = self.run_installer(root, "audit", audit_env)
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertIn("- Status: Clean", audit.stdout)


if __name__ == "__main__":
    unittest.main()

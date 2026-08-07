from __future__ import annotations

import hashlib
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

GOOD_BACKLOG_SCRIPT = """#!/bin/sh
if [ "$1" = "instructions" ] && [ "$2" = "overview" ]; then
  printf '## Backlog.md Overview (CLI)\\n\\nbacklog instructions task-creation\\n'
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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class InstallerTests(unittest.TestCase):
    def fake_bin(self, *kinds: str) -> Path:
        d = Path(tempfile.mkdtemp(prefix="bw-bin-"))
        for kind in kinds:
            if kind == "good":
                target = d / "backlog"
                target.write_text(GOOD_BACKLOG_SCRIPT, encoding="utf-8")
            elif kind == "bad":
                target = d / "backlog"
                target.write_text(BAD_BACKLOG_SCRIPT, encoding="utf-8")
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

    def make_project(self, cli: str = "good") -> tuple[Path, dict]:
        root = Path(tempfile.mkdtemp(prefix="backlog-workflow-test-"))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        (root / "backlog/tasks").mkdir(parents=True)
        (root / "backlog/config.yml").write_text(
            "project_name: demo\ntask_prefix: DEMO\n", encoding="utf-8"
        )
        (root / "package.json").write_text(
            '{"name":"demo","scripts":{"lint":"eslint .","typecheck":"tsc --noEmit",'
            '"test":"vitest run","build":"vite build"}}',
            encoding="utf-8",
        )
        env = dict(os.environ)
        if cli == "good":
            # Fake `backlog` verifies first, so npx (still on PATH) is never invoked.
            env["PATH"] = f"{self.fake_bin('good')}{os.pathsep}{env.get('PATH', '')}"
        elif cli == "bad":
            # A present-but-fake `backlog` plus a shadowed (broken) npx: nothing verifies.
            env["PATH"] = self.minimal_path(str(self.fake_bin("bad", "broken-npx")))
        elif cli == "none":
            # No `backlog` at all, and npx cannot run Backlog.md.
            env["PATH"] = self.minimal_path(str(self.fake_bin("broken-npx")))
        else:
            raise ValueError(cli)
        return root, env

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

    # 1. fresh apply creates the 1.1.0 workflow
    def test_fresh_apply_creates_1_1_0_workflow(self) -> None:
        root, env = self.make_project()
        result = self.apply(root, env)
        self.assertIn("- Status: Installed", result.stdout)
        self.assertEqual(read(root / ".agent-workflow/VERSION").strip(), "1.1.0")
        self.assertIn("workflow_version: 1.1.0", read(root / ".agent-workflow/config.yml"))
        self.assertTrue((root / ".agent-workflow/TASK-POLICY.md").exists())
        self.assertFalse((root / ".agent-workflow/TASK-TEMPLATE.md").exists())

    # 20. managed files contain version 1.1.0
    def test_managed_files_contain_1_1_0(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for rel in (
            ".agent-workflow/WORKFLOW.md",
            ".agent-workflow/config.yml",
            ".agent-workflow/TASK-POLICY.md",
            ".claude/skills/backlog-plan/SKILL.md",
            ".claude/skills/backlog-run/SKILL.md",
            ".claude/skills/backlog-auto/SKILL.md",
        ):
            self.assertIn("1.1.0", read(root / rel), f"missing 1.1.0 marker in {rel}")

    # 2. apply is idempotent
    def test_apply_is_idempotent(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        second = self.run_installer(root, "apply", env)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("- Status: Clean", second.stdout)
        self.assertIn("- Changes: none", second.stdout)

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

    # 7. existing Backlog configuration is preserved
    def test_backlog_config_preserved(self) -> None:
        root, env = self.make_project()
        config = root / "backlog/config.yml"
        config.write_text("project_name: kept\ntask_prefix: KEPT\n", encoding="utf-8")
        before = digest(config)
        self.apply(root, env)
        self.assertEqual(digest(config), before)

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
        for name in ("backlog-plan", "backlog-run", "backlog-auto", "grilling"):
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
        self.assertIn("backlog-run", names)
        self.assertIn("backlog-auto", names)

    # 17 + stale-1.0 behavior. No installed skill/workflow references the board.
    def test_installed_workflow_has_no_stale_1_0_behavior(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        installed = []
        for path in (
            root / ".agent-workflow/WORKFLOW.md",
            root / ".agent-workflow/TASK-POLICY.md",
            root / ".claude/skills/backlog-plan/SKILL.md",
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


if __name__ == "__main__":
    unittest.main()

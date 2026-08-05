from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InstallerTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="backlog-workflow-test-"))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        (root / "backlog/tasks").mkdir(parents=True)
        (root / "backlog/config.yml").write_text("project_name: demo\ntask_prefix: DEMO\n", encoding="utf-8")
        (root / "package.json").write_text(
            '{"name":"demo","scripts":{"lint":"eslint .","typecheck":"tsc --noEmit","test":"vitest run","build":"vite build"}}',
            encoding="utf-8",
        )
        return root

    def run_installer(self, root: Path, action: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), action, "--project", str(root)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_apply_and_audit_are_idempotent(self) -> None:
        root = self.make_project()
        readme = root / "README.md"
        readme.write_text("public docs\n", encoding="utf-8")
        task = root / "backlog/tasks/demo-1 - Existing task.md"
        task.write_text("existing history\n", encoding="utf-8")
        before_readme = digest(readme)
        before_task = digest(task)

        first = self.run_installer(root, "apply")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn("- Status: Installed", first.stdout)
        self.assertEqual(digest(readme), before_readme)
        self.assertEqual(digest(task), before_task)
        self.assertIn("default_mode: manual", (root / ".agent-workflow/config.yml").read_text())
        self.assertTrue((root / ".claude/skills/backlog-plan/SKILL.md").exists())
        self.assertTrue((root / ".claude/skills/backlog-run/SKILL.md").exists())
        self.assertTrue((root / ".claude/skills/backlog-auto/SKILL.md").exists())
        self.assertTrue((root / ".claude/skills/grilling/SKILL.md").exists())

        second = self.run_installer(root, "apply")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("- Changes: none", second.stdout)

        audit = self.run_installer(root, "audit")
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertIn("- Status: Clean", audit.stdout)

    def test_apply_initializes_missing_backlog_workspace(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="backlog-workflow-init-"))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        (root / "package.json").write_text('{"name":"fresh-demo"}', encoding="utf-8")

        result = self.run_installer(root, "apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("- Status: Installed", result.stdout)
        self.assertIn("backlog workspace initialized", result.stdout)
        self.assertIn("- Validation: clean", result.stdout)
        self.assertTrue((root / "backlog/config.yml").exists())
        # The workflow owns its own CLAUDE.md block; init must not emit AGENTS.md.
        self.assertFalse((root / "AGENTS.md").exists())

    def test_agents_md_receives_block_only_when_present(self) -> None:
        root = self.make_project()
        first = self.run_installer(root, "apply")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertFalse((root / "AGENTS.md").exists(), "AGENTS.md must not be created from nothing")

        agents = root / "AGENTS.md"
        agents.write_text("# Shared agent rules\n\nKeep secrets out of logs.\n", encoding="utf-8")
        audit = self.run_installer(root, "audit")
        self.assertEqual(audit.returncode, 2)
        self.assertIn("AGENTS.md", audit.stdout)

        second = self.run_installer(root, "apply")
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        content = agents.read_text()
        self.assertIn("Keep secrets out of logs.", content)
        self.assertEqual(content.count("<!-- backlog-workflow:begin"), 1)
        self.assertEqual(self.run_installer(root, "audit").returncode, 0)

    def test_same_version_template_fix_reports_upgraded(self) -> None:
        root = self.make_project()
        self.run_installer(root, "apply")
        workflow = root / ".agent-workflow/WORKFLOW.md"
        workflow.write_text(workflow.read_text() + "\nlocal drift\n", encoding="utf-8")

        result = self.run_installer(root, "upgrade")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("- Status: Upgraded", result.stdout)

    def test_stale_project_md_warns_without_failing_apply(self) -> None:
        root = self.make_project()
        self.run_installer(root, "apply")
        project_md = root / ".agent-workflow/PROJECT.md"
        project_md.write_text(
            project_md.read_text().replace("- Default branch: main", "- Default branch: trunk"),
            encoding="utf-8",
        )

        audit = self.run_installer(root, "audit")
        self.assertEqual(audit.returncode, 2)
        self.assertIn("PROJECT.md Default branch", audit.stdout)

        # The advisory must not fail an otherwise correct install.
        applied = self.run_installer(root, "apply")
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertIn("- Default branch: trunk", project_md.read_text())

    def test_unmanaged_conflict_blocks_without_partial_install(self) -> None:
        root = self.make_project()
        conflict = root / ".agent-workflow/WORKFLOW.md"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("user owned workflow\n", encoding="utf-8")

        result = self.run_installer(root, "apply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unmanaged file occupies managed path", result.stdout)
        self.assertFalse((root / ".claude/skills/backlog-plan/SKILL.md").exists())
        self.assertEqual(conflict.read_text(), "user owned workflow\n")

    def test_audit_detects_drift_without_repairing(self) -> None:
        root = self.make_project()
        applied = self.run_installer(root, "apply")
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        workflow = root / ".agent-workflow/WORKFLOW.md"
        workflow.write_text(workflow.read_text() + "\nlocal drift\n", encoding="utf-8")
        before = digest(workflow)

        audit = self.run_installer(root, "audit")
        self.assertEqual(audit.returncode, 2)
        self.assertIn("content drift: .agent-workflow/WORKFLOW.md", audit.stdout)
        self.assertEqual(digest(workflow), before)

    def test_existing_project_md_is_preserved(self) -> None:
        root = self.make_project()
        project_md = root / ".agent-workflow/PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("project-specific configuration\n", encoding="utf-8")
        before = digest(project_md)

        result = self.run_installer(root, "apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(digest(project_md), before)

    def test_claude_managed_block_preserves_existing_content(self) -> None:
        root = self.make_project()
        claude = root / "CLAUDE.md"
        claude.write_text("# Existing rules\n\nNever delete production data.\n", encoding="utf-8")

        result = self.run_installer(root, "apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        content = claude.read_text()
        self.assertIn("# Existing rules", content)
        self.assertIn("Never delete production data.", content)
        self.assertEqual(content.count("<!-- backlog-workflow:begin"), 1)
        self.assertEqual(content.count("<!-- backlog-workflow:end -->"), 1)


if __name__ == "__main__":
    unittest.main()

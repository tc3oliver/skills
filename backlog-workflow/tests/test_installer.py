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
elif tasks.get(arg) is None:
    # null models a task detail the CLI cannot return (error or bad JSON)
    print(f"error: could not read {arg}", file=sys.stderr)
    sys.exit(1)
else:
    print(json.dumps({"schemaVersion": 1, "kind": "task-view",
                      "task": {"id": arg, "documentation": tasks[arg]}}))
PYEOF
  exit $?
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

    # 1. fresh apply creates the 1.5.0 workflow
    def test_fresh_apply_creates_current_workflow(self) -> None:
        root, env = self.make_project()
        result = self.apply(root, env)
        self.assertIn("- Status: Installed", result.stdout)
        self.assertEqual(read(root / ".agent-workflow/VERSION").strip(), "1.5.0")
        self.assertIn("workflow_version: 1.5.0", read(root / ".agent-workflow/config.yml"))
        self.assertTrue((root / ".agent-workflow/TASK-POLICY.md").exists())
        self.assertFalse((root / ".agent-workflow/TASK-TEMPLATE.md").exists())

    # 20. managed files contain version 1.5.0
    def test_managed_files_carry_current_version(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for rel in (
            ".agent-workflow/WORKFLOW.md",
            ".agent-workflow/PLAN.md",
            ".agent-workflow/EXECUTION.md",
            ".agent-workflow/AUTO.md",
            ".agent-workflow/PARALLEL.md",
            ".agent-workflow/config.yml",
            ".agent-workflow/TASK-POLICY.md",
            ".claude/skills/backlog-plan/SKILL.md",
            ".claude/skills/backlog-review/SKILL.md",
            ".claude/skills/backlog-run/SKILL.md",
            ".claude/skills/backlog-auto/SKILL.md",
        ):
            self.assertIn("1.5.0", read(root / rel), f"missing version marker in {rel}")

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
        self.assertIn("## Batch merge", read(root / ".agent-workflow/PARALLEL.md"))

        # PARALLEL.md belongs to no skill: it is reached only through AUTO.md's
        # conditional pointer, so the default sequential run never loads it.
        expected = {
            "backlog-plan": {"PLAN.md"},
            "backlog-review": {"PLAN.md"},
            "backlog-run": {"EXECUTION.md"},
            "backlog-auto": {"AUTO.md", "EXECUTION.md"},
        }
        for skill, wanted in expected.items():
            text = read(root / f".claude/skills/{skill}/SKILL.md")
            self.assertIn(".agent-workflow/WORKFLOW.md", text, skill)
            for reference in ("PLAN.md", "EXECUTION.md", "AUTO.md", "PARALLEL.md"):
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
            ".agent-workflow/PARALLEL.md",
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
        for name in ("PLAN.md", "EXECUTION.md", "AUTO.md", "PARALLEL.md"):
            (root / ".agent-workflow" / name).unlink()
        (root / ".agent-workflow/VERSION").write_text("1.3.0\n", encoding="utf-8")
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 2)

        result = self.run_installer(root, "upgrade", env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ("PLAN.md", "EXECUTION.md", "AUTO.md", "PARALLEL.md"):
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
            root / ".agent-workflow/PARALLEL.md",
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

    # The Ready Gate is an execution invariant, not planning trivia: /backlog-run
    # never reads PLAN.md, so a gate that only lived there would not stop a
    # hand-written malformed task from entering the active status.
    def test_ready_gate_is_reachable_from_execution(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        workflow = read(root / ".agent-workflow/WORKFLOW.md")
        self.assertIn("## Task Ready Gate", workflow)
        for item in ("documentation", "Acceptance Criteria", "dependencies", "validation"):
            self.assertIn(item, workflow.split("## Task Ready Gate", 1)[1].split("##", 1)[0], item)

        # /backlog-run reads WORKFLOW.md + EXECUTION.md only, and the check
        # happens before the claim.
        execution = read(root / ".agent-workflow/EXECUTION.md")
        self.assertIn("Task Ready Gate", execution)
        self.assertLess(
            execution.index("Task Ready Gate"),
            execution.index('-s "<active status>"'),
            "the gate must be checked before the task is claimed",
        )
        self.assertNotIn(".agent-workflow/PLAN.md", read(root / ".claude/skills/backlog-run/SKILL.md"))

    # audit is an integrity command: a task it cannot read is reported, not
    # skipped, or a Clean verdict would mean "every task I could parse".
    def test_documentation_audit_fails_closed_on_unreadable_task(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        # `null` documentation stands in for a task detail the audit cannot use.
        audit = self.audit_with_tasks(root, env, {"TASK-1": None, "TASK-2": ["docs/PRD.md"]})
        self.assertEqual(audit.returncode, 2, audit.stdout)
        self.assertIn("cannot inspect documentation: TASK-1", audit.stdout)

    # --- `statuses:` YAML shapes -------------------------------------------
    #
    # Backlog.md accepts both the inline list it writes and a block list. Reading
    # "a shape I cannot rewrite" as "no statuses key" is what would append a
    # second `statuses:` key and leave a config with a duplicate mapping key.

    def apply_with_backlog_config(self, config: str) -> tuple[Path, dict, subprocess.CompletedProcess[str]]:
        root, env = self.make_project()
        (root / "backlog/config.yml").write_text(config, encoding="utf-8")
        return root, env, self.run_installer(root, "apply", env)

    def assert_single_statuses_key(self, root: Path) -> None:
        text = read(root / "backlog/config.yml")
        keys = len(re.findall(r"(?m)^statuses:", text))
        self.assertEqual(keys, 1, f"expected one `statuses:` key, got {keys}:\n{text}")

    def test_inline_statuses_are_rewritten_in_place(self) -> None:
        root, env, result = self.apply_with_backlog_config(
            'project_name: demo\nstatuses: ["To Do", "In Progress", "Done"]\nlabels: []\n'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_single_statuses_key(root)
        self.assertIn('statuses: ["To Do", "In Progress", "Blocked", "Done"]', read(root / "backlog/config.yml"))
        self.assertIn("labels: []", read(root / "backlog/config.yml"))

    def test_block_style_statuses_are_rewritten_in_place(self) -> None:
        root, env, result = self.apply_with_backlog_config(
            "project_name: demo\nstatuses:\n  - To Do\n  - In Progress\n  - Done\nlabels: []\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_single_statuses_key(root)
        text = read(root / "backlog/config.yml")
        # Block style is preserved, the new status inserted before the terminal one.
        self.assertIn("statuses:\n  - To Do\n  - In Progress\n  - Blocked\n  - Done\n", text)
        self.assertIn("labels: []", text)
        # The list stays block style; it is not silently converted to inline.
        self.assertNotIn("statuses: [", text)
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)
        self.assertIn("blocked: Blocked", read(root / ".agent-workflow/config.yml"))

    def test_block_style_statuses_with_comments_and_quotes(self) -> None:
        root, env, result = self.apply_with_backlog_config(
            "project_name: demo\nstatuses:\n"
            "  # workflow columns\n"
            '  - "To Do"\n'
            "  - 'In Progress'\n"
            "  - Done\n"
            "labels: []\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_single_statuses_key(root)
        text = read(root / "backlog/config.yml")
        self.assertIn("  - Blocked\n  - Done\n", text)
        self.assertIn("labels: []", text)
        # Comments and quoting are project-owned content: adding a status must
        # not rewrite the lines around it.
        self.assertIn("  # workflow columns\n", text)
        self.assertIn('  - "To Do"\n', text)
        self.assertIn("  - 'In Progress'\n", text)

    def test_block_style_status_comments_survive_every_position(self) -> None:
        root, env, result = self.apply_with_backlog_config(
            "project_name: demo\n"
            "# board layout\n"
            "statuses:\n"
            "  # not started yet\n"
            "  - To Do\n"
            "  - In Progress   # claimed\n"
            "  # terminal column\n"
            "  - Done\n"
            "labels: []\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = read(root / "backlog/config.yml")
        for comment in (
            "# board layout\n",
            "  # not started yet\n",
            "  - In Progress   # claimed\n",
            "  # terminal column\n",
        ):
            self.assertIn(comment, text, comment)
        # The new status goes before the terminal column, and the comment that
        # introduces that column stays attached to it.
        self.assertIn("  - Blocked\n  # terminal column\n  - Done\n", text)
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    def test_insert_block_status_only_inserts(self) -> None:
        original = (
            "statuses:\n"
            "  # columns\n"
            "  - To Do\n"
            "  - Done\n"
            "labels: []\n"
        )
        updated = install.insert_block_status(original, "Blocked", "Done")
        self.assertEqual(
            updated, "statuses:\n  # columns\n  - To Do\n  - Blocked\n  - Done\nlabels: []\n"
        )
        # Every original line survives, in order.
        self.assertEqual(
            [line for line in updated.splitlines() if line != "  - Blocked"],
            original.splitlines(),
        )
        # With no `before` match the item is appended after the last one, never
        # after an unrelated trailing comment.
        appended = install.insert_block_status(
            "statuses:\n  - To Do\n# unrelated\nlabels: []\n", "Blocked", "Shipped"
        )
        self.assertEqual(appended, "statuses:\n  - To Do\n  - Blocked\n# unrelated\nlabels: []\n")

    def test_inline_statuses_keep_a_trailing_comment(self) -> None:
        root, env, result = self.apply_with_backlog_config(
            'project_name: demo\nstatuses: ["To Do", "In Progress", "Done"]  # board\nlabels: []\n'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_single_statuses_key(root)
        self.assertIn(
            'statuses: ["To Do", "In Progress", "Blocked", "Done"]  # board',
            read(root / "backlog/config.yml"),
        )

    # --- Backlog.md directory ----------------------------------------------

    def test_backlog_directory_is_read_not_assumed(self) -> None:
        root, _env = self.make_project()
        self.assertEqual(install.backlog_directory(root), "backlog")

        (root / "backlog").rename(root / ".backlog")
        self.assertEqual(install.backlog_directory(root), ".backlog")

        shutil.rmtree(root / ".backlog")
        (root / "pm/board/tasks").mkdir(parents=True)
        (root / "backlog.config.yml").write_text(
            'project_name: demo\nstatuses: ["To Do", "Done"]\nbacklog_directory: "pm/board"\n',
            encoding="utf-8",
        )
        self.assertEqual(install.backlog_directory(root), "pm/board")

        # Workflow data is not project documentation: a decision record inside a
        # custom Backlog directory must not be offered as a requirement source.
        (root / "pm/board/decisions").mkdir()
        (root / "pm/board/decisions/decision-1 - Adopt spec.md").write_text("x\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs/PRD.md").write_text("# PRD\n", encoding="utf-8")
        detected = install.detect_requirement_sources(root)
        self.assertIn("docs/PRD.md", detected)
        self.assertEqual([path for path in detected if path.startswith("pm/")], [])

    def test_custom_status_names_in_block_style(self) -> None:
        root, env, result = self.apply_with_backlog_config(
            "project_name: demo\nstatuses:\n  - Backlog\n  - WIP\n  - On Hold\n  - Shipped\n"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # A project that already parks blocked work keeps its own list untouched.
        self.assertNotIn("added 'Blocked' status", result.stdout)
        self.assertIn("statuses:\n  - Backlog\n  - WIP\n  - On Hold\n  - Shipped\n", read(root / "backlog/config.yml"))
        workflow_config = read(root / ".agent-workflow/config.yml")
        self.assertIn("blocked: On Hold", workflow_config)
        self.assertIn("done: Shipped", workflow_config)

    def test_absent_statuses_key_is_added_once(self) -> None:
        root, env, result = self.apply_with_backlog_config("project_name: demo\ntask_prefix: DEMO\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_single_statuses_key(root)
        # Falls back to what the CLI reports, plus the blocked status.
        self.assertIn('statuses: ["To Do", "In Progress", "Blocked", "Done"]', read(root / "backlog/config.yml"))

    def test_unsupported_statuses_shape_fails_closed(self) -> None:
        # A shape the installer cannot safely rewrite must block, never append.
        root, env, result = self.apply_with_backlog_config(
            "project_name: demo\nstatuses: &columns\nlabels: []\n"
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("not in a form this installer can", result.stdout)
        self.assert_single_statuses_key(root)
        self.assertFalse((root / ".agent-workflow/WORKFLOW.md").exists(), "must not install partially")

    def test_read_backlog_statuses_shapes(self) -> None:
        cases = {
            'statuses: ["To Do", "Done"]': ("inline", ["To Do", "Done"]),
            "statuses:\n  - To Do\n  - Done\n": ("block", ["To Do", "Done"]),
            "statuses:\n  - 'On Hold'\nlabels: []\n": ("block", ["On Hold"]),
            "project_name: x\n": ("missing", []),
            "statuses: &anchor\nlabels: []\n": ("unsupported", []),
            "statuses: []\n": ("unsupported", []),
        }
        for text, expected in cases.items():
            self.assertEqual(install.read_backlog_statuses(text), expected, text)

    # --- status role matching ----------------------------------------------

    def test_status_role_matching_uses_whole_words(self) -> None:
        # "Incomplete" contains "complete" but is not the done status.
        statuses = ["To Do", "Incomplete", "Done"]
        self.assertEqual(install.match_status_role(statuses, "done"), "Done")
        # Roles never collapse onto the same status.
        roles = ["Backlog", "In Progress", "On Hold", "Shipped"]
        assigned: list[str] = []
        for role in ("done", "blocked", "active", "not_started"):
            matched = install.match_status_role(roles, role, taken=assigned)
            assigned.append(matched)
        self.assertEqual(len(set(assigned)), 4, assigned)
        self.assertEqual(assigned, ["Shipped", "On Hold", "In Progress", "Backlog"])

    # --- parallel /backlog-auto git lifecycle ------------------------------
    #
    # Backlog.md `autoCommit` defaults to off, so claiming a task only edits
    # `backlog/tasks/*.md` in the working tree. If those edits are still
    # uncommitted when a worker branch is merged back, Git refuses the merge
    # because the same file has local changes — which would break every task in
    # the batch, not just one. These exercise real git, not the documentation.

    def git(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=str(root), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )

    def parallel_batch_repo(self) -> Path:
        """A repo holding one committed task file, as after selection."""
        root = Path(tempfile.mkdtemp(prefix="bw-parallel-"))
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "test")
        (root / "backlog/tasks").mkdir(parents=True)
        (root / "backlog/tasks/task-1.md").write_text("status: To Do\n", encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-q", "-m", "base")
        return root

    def run_worker(self, root: Path, worktree: Path) -> None:
        """A worker: branch from HEAD, finish the task, commit on its branch."""
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")
        (worktree / "backlog/tasks/task-1.md").write_text("status: Done\n", encoding="utf-8")
        (worktree / "impl.py").write_text("print('done')\n", encoding="utf-8")
        self.git(worktree, "add", "-A")
        self.git(worktree, "commit", "-q", "-m", "TASK-1 done")

    def test_uncommitted_claim_breaks_the_batch_merge(self) -> None:
        """The failure the claim checkpoint exists to prevent."""
        root = self.parallel_batch_repo()
        # Claim without committing — what `backlog task edit -s` leaves behind
        # when autoCommit is off.
        (root / "backlog/tasks/task-1.md").write_text("status: In Progress\n", encoding="utf-8")
        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.run_worker(root, worktree)

        merge = self.git(root, "merge", "backlog/TASK-1")
        self.assertNotEqual(merge.returncode, 0, merge.stdout)
        self.assertIn("would be overwritten by merge", merge.stdout)

    def test_committed_claim_lets_the_batch_merge(self) -> None:
        """AUTO.md step 3: commit the claim, branch from that commit, merge."""
        root = self.parallel_batch_repo()
        (root / "backlog/tasks/task-1.md").write_text("status: In Progress\n", encoding="utf-8")
        self.assertIn("backlog/tasks/task-1.md", self.git(root, "status", "--short", "--", "backlog").stdout)

        self.git(root, "add", "backlog")
        self.git(root, "commit", "-q", "-m", "backlog: claim TASK-1")
        self.assertEqual(self.git(root, "status", "--short", "--", "backlog").stdout.strip(), "")

        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.run_worker(root, worktree)

        merge = self.git(root, "merge", "backlog/TASK-1")
        self.assertEqual(merge.returncode, 0, merge.stdout)
        self.assertEqual(read(root / "backlog/tasks/task-1.md"), "status: Done\n")
        self.assertTrue((root / "impl.py").exists())

    # Workers branch from a commit, so uncommitted work in the base tree is
    # invisible to them. The claim checkpoint deliberately commits only
    # `backlog/`, which leaves the user's own source changes behind — hence the
    # clean-source-tree precondition.

    def parallel_repo_with_source(self) -> Path:
        root = self.parallel_batch_repo()
        (root / "src").mkdir()
        (root / "src/app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-q", "-m", "source")
        return root

    def dirty_source_check(self, root: Path) -> str:
        """The precondition query AUTO.md specifies."""
        return self.git(
            root, "status", "--porcelain", "--untracked-files=normal", "--", ".", ":(exclude)backlog"
        ).stdout.strip()

    def test_precondition_detects_source_changes_the_claim_commit_leaves(self) -> None:
        root = self.parallel_repo_with_source()
        (root / "src/app.py").write_text("def f():\n    return 2  # user WIP\n", encoding="utf-8")
        (root / "backlog/tasks/task-1.md").write_text("status: In Progress\n", encoding="utf-8")

        # Committing the claim clears `backlog/` but not the user's source work.
        self.git(root, "add", "backlog")
        self.git(root, "commit", "-q", "-m", "backlog: claim TASK-1")
        self.assertEqual(self.git(root, "status", "--short", "--", "backlog").stdout.strip(), "")
        self.assertIn("src/app.py", self.dirty_source_check(root))

    def test_dirty_base_hides_user_work_from_the_worker(self) -> None:
        """The quiet failure: no error, wrong codebase."""
        root = self.parallel_repo_with_source()
        (root / "src/app.py").write_text("def f():\n    return 2  # user WIP\n", encoding="utf-8")
        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")

        self.assertIn("return 2", read(root / "src/app.py"))
        self.assertNotIn("return 2", read(worktree / "src/app.py"))

    def test_dirty_base_breaks_the_merge_when_files_overlap(self) -> None:
        root = self.parallel_repo_with_source()
        (root / "src/app.py").write_text("def f():\n    return 2  # user WIP\n", encoding="utf-8")
        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")
        (worktree / "src/app.py").write_text("def f():\n    return 1\n\ndef g():\n    return 3\n", encoding="utf-8")
        self.git(worktree, "add", "-A")
        self.git(worktree, "commit", "-q", "-m", "TASK-1")

        merge = self.git(root, "merge", "backlog/TASK-1")
        self.assertNotEqual(merge.returncode, 0, merge.stdout)
        self.assertIn("would be overwritten by merge", merge.stdout)

    def test_clean_base_gives_the_worker_the_current_codebase(self) -> None:
        root = self.parallel_repo_with_source()
        (root / "src/app.py").write_text("def f():\n    return 2  # committed\n", encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-q", "-m", "user work committed")
        self.assertEqual(self.dirty_source_check(root), "")

        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")
        self.assertIn("return 2", read(worktree / "src/app.py"))

        (worktree / "src/app.py").write_text("def f():\n    return 2  # committed\n\ndef g():\n    return 3\n", encoding="utf-8")
        (worktree / "backlog/tasks/task-1.md").write_text("status: Done\n", encoding="utf-8")
        self.git(worktree, "add", "-A")
        self.git(worktree, "commit", "-q", "-m", "TASK-1 done")

        merge = self.git(root, "merge", "backlog/TASK-1")
        self.assertEqual(merge.returncode, 0, merge.stdout)
        self.assertIn("def g()", read(root / "src/app.py"))
        self.assertIn("return 2", read(root / "src/app.py"))

    # An untracked file is usually work the user has not staged yet, and it is
    # just as invisible to a worker as an uncommitted edit — so it blocks too.
    def test_untracked_user_source_blocks_parallel_execution(self) -> None:
        root = self.parallel_repo_with_source()
        self.assertEqual(self.dirty_source_check(root), "")
        (root / "src/new_feature.py").write_text("def new(): ...\n", encoding="utf-8")
        self.assertIn("?? src/new_feature.py", self.dirty_source_check(root))

    def test_untracked_user_source_is_missing_from_worker(self) -> None:
        """Why untracked has to block: HEAD does not contain the file at all."""
        root = self.parallel_repo_with_source()
        (root / "src/new_feature.py").write_text("def new(): ...\n", encoding="utf-8")
        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")

        self.assertTrue((root / "src/new_feature.py").exists())
        self.assertFalse((worktree / "src/new_feature.py").exists())
        # Nothing errors — the worker simply analyses a different codebase.
        self.assertEqual(sorted(p.name for p in (worktree / "src").iterdir()), ["app.py"])

    # Ignored paths are not project state the worker needs, and git does not list
    # them, so the precondition must not trip on build output.
    def test_ignored_build_artifact_does_not_block_parallel_execution(self) -> None:
        root = self.parallel_repo_with_source()
        (root / ".gitignore").write_text("build/\n*.tmp\n", encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-q", "-m", "gitignore")
        self.assertEqual(self.dirty_source_check(root), "")

        (root / "build").mkdir()
        (root / "build/output.bin").write_text("binary\n", encoding="utf-8")
        (root / "scratch.tmp").write_text("scratch\n", encoding="utf-8")
        self.assertEqual(self.dirty_source_check(root), "", "ignored paths must not block")

        # They only appear when explicitly asked for, which AUTO.md forbids.
        ignored = self.git(root, "status", "--porcelain", "--ignored", "--", ".", ":(exclude)backlog")
        self.assertIn("!! build/", ignored.stdout)

    # Staged and deleted paths are project state HEAD does not carry either.
    def test_staged_and_deleted_paths_block_parallel_execution(self) -> None:
        root = self.parallel_repo_with_source()
        (root / "src/staged.py").write_text("x = 1\n", encoding="utf-8")
        self.git(root, "add", "src/staged.py")
        self.assertIn("A  src/staged.py", self.dirty_source_check(root))

        self.git(root, "reset", "-q")
        (root / "src/staged.py").unlink()
        (root / "src/app.py").unlink()
        self.assertIn("src/app.py", self.dirty_source_check(root))

    # Changes under backlog/ are excluded: the claim checkpoint owns those.
    def test_backlog_changes_are_excluded_from_the_precondition(self) -> None:
        root = self.parallel_repo_with_source()
        (root / "backlog/tasks/task-1.md").write_text("status: In Progress\n", encoding="utf-8")
        self.assertEqual(self.dirty_source_check(root), "")
        self.assertIn("task-1.md", self.git(root, "status", "--short", "--", "backlog").stdout)

    def test_parallel_documents_the_clean_tree_precondition(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        parallel = read(root / ".agent-workflow/PARALLEL.md")
        flat = re.sub(r"\s+", " ", parallel)  # the file is hard-wrapped
        precondition = (
            "the non-ignored working tree must have no staged, modified, deleted, "
            "renamed, or untracked files"
        )
        self.assertIn(precondition, flat)
        # The whole tree, with nothing excluded: an uncommitted Backlog.md edit is
        # the user's work in progress too, and the claim commit must not take it.
        self.assertIn("git status --porcelain --untracked-files=normal", parallel)
        self.assertNotIn(":(exclude)", parallel)
        # Checked before the batch is claimed, not after work has started.
        self.assertLess(
            flat.index(precondition),
            flat.index('backlog task edit <TASK-ID> -s "<active'),
            "the precondition must be checked before any task is claimed",
        )
        self.assertIn("run blocker", flat)
        # The user's in-progress work is theirs; the workflow must not touch it.
        self.assertIn(
            "Do not stash, commit, discard, or otherwise modify the user's working changes", flat
        )
        # Ignored paths must not block, and --ignored must not be recommended.
        self.assertIn("Ignored files do not block", flat)
        self.assertIn("Do not add `--ignored`", flat)
        # Sequential mode keeps its existing behaviour.
        self.assertIn("Sequential execution has no snapshot boundary", flat)

    def test_parallel_documents_the_claim_checkpoint(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        parallel = read(root / ".agent-workflow/PARALLEL.md")
        flat = re.sub(r"\s+", " ", parallel)
        # The exact task path comes from the CLI; the directory is never assumed.
        self.assertIn("backlog task <TASK-ID> --json", parallel)
        self.assertIn(".task.path", parallel)
        self.assertIn('git add -- "', parallel)
        for blanket in ("git add backlog", "git add .backlog", "git add -A"):
            self.assertNotIn(blanket, parallel, blanket)
        # The commit must be ordered before worktree creation, not after.
        self.assertLess(
            flat.index('git add -- "'), flat.index("git worktree add"),
            "claims must be committed before worktrees exist",
        )
        self.assertIn("autoCommit", parallel)
        self.assertIn("would be overwritten by merge", parallel)
        # A conflict parks the task in the blocked status, which is another task
        # file edit and must be committed for the rest of the batch to merge.
        self.assertIn("Commit that status change", flat)
        # The workflow must not demand the user flip autoCommit on.
        self.assertNotIn("autoCommit: true`.", parallel)
        self.assertNotIn("set autoCommit", parallel)

    def test_parallel_defines_the_worker_outcome_contract(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        parallel = read(root / ".agent-workflow/PARALLEL.md")
        flat = re.sub(r"\s+", " ", parallel)
        self.assertIn("## Worker contract", parallel)
        # Done: commit implementation and task record, then merge.
        self.assertIn("The branch is eligible for the batch merge", flat)
        self.assertIn("Merge only the branches of workers that finished `Done`", flat)
        # Blocked: never merged, but the base branch still records the state.
        self.assertIn("Its branch is **not** merged", flat)
        self.assertIn("record the blocked state on the base branch", flat)
        self.assertIn("Keep its worktree and branch so the partial work can be inspected", flat)

    def test_auto_routes_to_parallel_only_above_one(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        auto = read(root / ".agent-workflow/AUTO.md")
        flat = re.sub(r"\s+", " ", auto)
        # The pointer is conditional, and the mechanics stay out of AUTO.md so a
        # sequential run never loads them.
        self.assertIn("Read `.agent-workflow/PARALLEL.md` before claiming anything", flat)
        self.assertIn("Greater than 1", auto)
        for mechanic in ("git worktree add", "git merge", "git add --"):
            self.assertNotIn(mechanic, auto, mechanic)

    def test_auto_separates_task_blockers_from_run_blockers(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        auto = read(root / ".agent-workflow/AUTO.md")
        flat = re.sub(r"\s+", " ", auto)
        self.assertIn("### Task blocker", auto)
        self.assertIn("### Run blocker", auto)
        # A task blocker parks one task and the run continues.
        self.assertIn("continue with the other executable tasks", flat)
        # A run blocker stops the run and is never written to a task status.
        self.assertIn("Stop `/backlog-auto`", flat)
        self.assertIn("A run blocker is never written to a task status", flat)
        self.assertIn("## Task blockers", read(root / ".agent-workflow/WORKFLOW.md"))
        # The ambiguous vocabulary it replaced must be gone everywhere.
        for name in ("WORKFLOW.md", "PLAN.md", "EXECUTION.md", "AUTO.md", "PARALLEL.md"):
            self.assertNotIn("true blocker", read(root / ".agent-workflow" / name).lower(), name)

    # One traceability rule for planning, review, and execution: the authority
    # lives in native `documentation`, and task-local rationale never stands in.
    def test_traceability_rule_is_stated_once_and_used_everywhere(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        workflow = re.sub(r"\s+", " ", read(root / ".agent-workflow/WORKFLOW.md"))
        rule = (
            "every executable task has a non-empty native `documentation` naming its "
            "authority — an authoritative requirement source, or a persisted decision record."
        )
        self.assertIn(rule, workflow)
        # A decision record is an accepted authority, not a lesser substitute.
        self.assertIn('backlog task edit <TASK-ID> --doc "decision-3"', workflow)
        # Task-local rationale explains how, never what the task is owed to.
        self.assertIn("never substitutes for the authority", workflow)
        # The Ready Gate and the review check enforce that same rule.
        gate = workflow.split("## Task Ready Gate", 1)[1].split("## ", 1)[0]
        self.assertIn("non-empty native `documentation`", gate)
        plan = re.sub(r"\s+", " ", read(root / ".agent-workflow/PLAN.md"))
        self.assertIn("the same rule execution enforces at the Ready Gate", plan)
        # The weaker second rule it replaced is gone.
        for name in ("WORKFLOW.md", "PLAN.md", "EXECUTION.md"):
            self.assertNotIn("recorded technical rationale", read(root / ".agent-workflow" / name), name)

    # A task that fails the gate goes back to planning; ambiguity found after a
    # ready task started is grilled and persisted, in manual mode only.
    def test_execution_separates_ready_gate_failure_from_new_ambiguity(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        execution = re.sub(r"\s+", " ", read(root / ".agent-workflow/EXECUTION.md"))
        self.assertIn("The task was never ready", execution)
        self.assertIn("send it back to planning as a task blocker", execution)
        self.assertIn("New ambiguity appeared after execution legitimately started", execution)
        self.assertIn("invoke `grilling`", execution)
        self.assertIn("Under `/backlog-auto` there is no grilling", execution)

    # --- configuration validation ------------------------------------------
    #
    # max_parallel_tasks decides whether tasks run in the current worktree or in
    # isolated ones. `0` would select a batch and execute nothing; a non-integer
    # has no defined meaning. Both fail closed rather than being coerced.

    def set_parallel(self, root: Path, value: str) -> None:
        path = root / ".agent-workflow/config.yml"
        path.write_text(
            re.sub(r"(?m)^(  max_parallel_tasks:).*$", rf"\g<1> {value}", read(path)),
            encoding="utf-8",
        )

    def test_zero_max_parallel_tasks_fails_closed(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        self.set_parallel(root, "0")

        audit = self.run_installer(root, "audit", env)
        self.assertEqual(audit.returncode, 2, audit.stdout)
        self.assertIn("max_parallel_tasks must be an integer >= 1", audit.stdout)

        upgrade = self.run_installer(root, "upgrade", env)
        self.assertEqual(upgrade.returncode, 2, upgrade.stdout)
        self.assertIn("max_parallel_tasks must be an integer >= 1", upgrade.stdout)
        # Blocked before anything was written: the invalid value is still there.
        self.assertIn("max_parallel_tasks: 0", read(root / ".agent-workflow/config.yml"))

    def test_non_integer_max_parallel_tasks_fails_closed(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for value in ("-1", "two", "1.5", '"3"', ""):
            with self.subTest(value=value):
                self.set_parallel(root, value)
                audit = self.run_installer(root, "audit", env)
                self.assertEqual(audit.returncode, 2, audit.stdout)
                self.assertIn("max_parallel_tasks must be an integer >= 1", audit.stdout)

    def test_valid_max_parallel_tasks_passes(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        for value in ("1", "2", "16"):
            with self.subTest(value=value):
                self.set_parallel(root, value)
                audit = self.run_installer(root, "audit", env)
                self.assertEqual(audit.returncode, 0, audit.stdout)
                upgrade = self.run_installer(root, "upgrade", env)
                self.assertEqual(upgrade.returncode, 0, upgrade.stdout)
                self.assertIn(
                    f"max_parallel_tasks: {value}", read(root / ".agent-workflow/config.yml")
                )

    # Every role needs its own status. Checking only blocked != not_started left
    # active == done passing, which cannot tell a claimed task from a finished one.
    def test_duplicate_status_roles_are_drift(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        path = root / ".agent-workflow/config.yml"
        original = read(path)
        for collapse, roles in (
            ("active: Done", ("active", "done")),
            ("not_started: In Progress", ("not_started", "active")),
            ("done: To Do", ("not_started", "done")),
        ):
            with self.subTest(collapse=collapse):
                role, value = collapse.split(": ")
                current = re.sub(rf"(?m)^  {role}: .*$", f"  {role}: {value}", original)
                path.write_text(current, encoding="utf-8")
                audit = self.run_installer(root, "audit", env)
                self.assertEqual(audit.returncode, 2, audit.stdout)
                self.assertIn("each workflow role needs its own status", audit.stdout)
                for name in roles:
                    self.assertIn(name, audit.stdout)
        path.write_text(original, encoding="utf-8")
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    def test_custom_statuses_with_distinct_roles_pass(self) -> None:
        root, env = self.make_project()
        (root / "backlog/config.yml").write_text(
            'project_name: demo\nstatuses: ["Icebox", "Doing", "Stalled", "Released"]\n',
            encoding="utf-8",
        )
        self.apply(root, env)
        config = read(root / ".agent-workflow/config.yml")
        self.assertIn("not_started: Icebox", config)
        self.assertIn("active: Doing", config)
        self.assertIn("blocked: Stalled", config)
        self.assertIn("done: Released", config)
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    # --- progressive disclosure: PARALLEL.md is a managed, conditional file ---

    def test_parallel_reference_is_installed_and_audited(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        parallel = root / ".agent-workflow/PARALLEL.md"
        self.assertTrue(parallel.exists())

        parallel.unlink()
        audit = self.run_installer(root, "audit", env)
        self.assertEqual(audit.returncode, 2, audit.stdout)
        self.assertIn("missing: .agent-workflow/PARALLEL.md", audit.stdout)

        upgrade = self.run_installer(root, "upgrade", env)
        self.assertEqual(upgrade.returncode, 0, upgrade.stdout + upgrade.stderr)
        self.assertIn(".agent-workflow/PARALLEL.md", upgrade.stdout)
        self.assertTrue(parallel.exists())
        self.assertEqual(self.run_installer(root, "audit", env).returncode, 0)

    def test_sequential_auto_never_loads_the_parallel_protocol(self) -> None:
        root, env = self.make_project()
        self.apply(root, env)
        # The default is sequential, and nothing a sequential run reads mentions
        # worktrees, claim commits, or merges.
        self.assertIn("max_parallel_tasks: 1", read(root / ".agent-workflow/config.yml"))
        for path in (
            root / ".claude/skills/backlog-auto/SKILL.md",
            root / ".agent-workflow/WORKFLOW.md",
            root / ".agent-workflow/EXECUTION.md",
        ):
            self.assertNotIn(".agent-workflow/PARALLEL.md", read(path), path.name)
        for mechanic in ("git worktree add", "git merge", "git add --"):
            self.assertNotIn(mechanic, read(root / ".agent-workflow/AUTO.md"), mechanic)

    # --- parallel claim staging (real git) ---------------------------------
    #
    # The Backlog.md directory is per-project: `backlog/`, `.backlog/`, or a
    # custom project-relative path. A claim commit that assumes a name either
    # fails outright or commits files the user never offered.

    def parallel_repo_with_backlog_dir(self, backlog_dir: str) -> tuple[Path, str, str]:
        """A repo whose Backlog.md data lives in `backlog_dir`, cleanly committed."""
        root = Path(tempfile.mkdtemp(prefix="bw-dir-"))
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "test")
        tasks = root / backlog_dir / "tasks"
        tasks.mkdir(parents=True)
        first = f"{backlog_dir}/tasks/task-1 - First task.md"
        second = f"{backlog_dir}/tasks/task-2 - Second task.md"
        for relative in (first, second):
            (root / relative).write_text("status: To Do\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src/app.py").write_text("x = 1\n", encoding="utf-8")
        self.git(root, "add", "-A")
        self.git(root, "commit", "-q", "-m", "base")
        return root, first, second

    def test_assumed_backlog_directory_breaks_the_claim_commit(self) -> None:
        """`git add backlog` is not portable: the directory name is per-project."""
        for backlog_dir in (".backlog", "pm/board"):
            with self.subTest(backlog_dir=backlog_dir):
                root, first, _ = self.parallel_repo_with_backlog_dir(backlog_dir)
                (root / first).write_text("status: In Progress\n", encoding="utf-8")

                assumed = self.git(root, "add", "backlog")
                self.assertNotEqual(assumed.returncode, 0, assumed.stdout)
                self.assertIn("did not match any files", assumed.stdout)
                # The claim is still uncommitted, which is what breaks the batch.
                self.assertIn(first, self.git(root, "status", "--porcelain").stdout)

                # The path the CLI reports works for every layout.
                exact = self.git(root, "add", "--", first)
                self.assertEqual(exact.returncode, 0, exact.stdout)
                self.git(root, "commit", "-q", "-m", "backlog: claim TASK-1")
                self.assertEqual(self.git(root, "status", "--porcelain").stdout.strip(), "")

    def test_claim_commit_stages_only_the_claimed_task_paths(self) -> None:
        """Blanket staging would sweep up Backlog.md work the user did not offer."""
        root, first, second = self.parallel_repo_with_backlog_dir("backlog")
        (root / first).write_text("status: In Progress\n", encoding="utf-8")
        # Anything else under the Backlog directory is not part of this claim.
        (root / second).write_text("status: To Do\nnote: user WIP\n", encoding="utf-8")
        (root / "backlog/docs").mkdir()
        (root / "backlog/docs/draft.md").write_text("unfinished\n", encoding="utf-8")

        self.git(root, "add", "--", first)
        self.git(root, "commit", "-q", "-m", "backlog: claim TASK-1")

        committed = [
            line for line in
            self.git(root, "show", "--name-only", "--format=", "HEAD").stdout.splitlines()
            if line.strip()
        ]
        self.assertEqual(len(committed), 1, committed)
        self.assertIn("task-1", committed[0])
        # The user's other Backlog.md work is still theirs, still uncommitted.
        remaining = self.git(root, "status", "--porcelain").stdout
        self.assertIn("task-2", remaining)
        self.assertIn("backlog/docs", remaining)

    def test_dirty_working_tree_blocks_parallel_execution_including_backlog(self) -> None:
        """The precondition covers the whole tree now, Backlog.md data included."""
        root, first, second = self.parallel_repo_with_backlog_dir("backlog")
        clean = self.git(root, "status", "--porcelain", "--untracked-files=normal").stdout.strip()
        self.assertEqual(clean, "")

        (root / second).write_text("status: To Do\nnote: user WIP\n", encoding="utf-8")
        dirty = self.git(root, "status", "--porcelain", "--untracked-files=normal").stdout
        self.assertIn("task-2", dirty, "Backlog.md work in progress must block a batch")

        # The old excluded check reported nothing here — that is the regression.
        excluded = self.git(
            root, "status", "--porcelain", "--untracked-files=normal", "--", ".", ":(exclude)backlog"
        ).stdout.strip()
        self.assertEqual(excluded, "")

    # --- worker outcome contract (real git) --------------------------------

    def test_done_worker_branch_merges_into_the_base(self) -> None:
        root, first, _ = self.parallel_repo_with_backlog_dir("backlog")
        (root / first).write_text("status: In Progress\n", encoding="utf-8")
        self.git(root, "add", "--", first)
        self.git(root, "commit", "-q", "-m", "backlog: claim TASK-1")

        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")
        (worktree / first).write_text("status: Done\n", encoding="utf-8")
        (worktree / "impl.py").write_text("print('done')\n", encoding="utf-8")
        self.git(worktree, "add", "-A")
        self.git(worktree, "commit", "-q", "-m", "TASK-1 done")

        merge = self.git(root, "merge", "backlog/TASK-1")
        self.assertEqual(merge.returncode, 0, merge.stdout)
        self.assertTrue((root / "impl.py").exists())
        self.assertEqual(read(root / first), "status: Done\n")

    def test_blocked_worker_implementation_never_reaches_the_base(self) -> None:
        """A blocked worker has no completion evidence, so its branch stays put."""
        root, first, _ = self.parallel_repo_with_backlog_dir("backlog")
        (root / first).write_text("status: In Progress\n", encoding="utf-8")
        self.git(root, "add", "--", first)
        self.git(root, "commit", "-q", "-m", "backlog: claim TASK-1")

        worktree = Path(tempfile.mkdtemp(prefix="bw-wt-")) / "w"
        self.git(root, "worktree", "add", "-q", str(worktree), "-b", "backlog/TASK-1", "HEAD")
        (worktree / "impl.py").write_text("# half finished\n", encoding="utf-8")
        (worktree / first).write_text("status: Blocked\n", encoding="utf-8")
        self.git(worktree, "add", "-A")
        self.git(worktree, "commit", "-q", "-m", "TASK-1 blocked")

        # The batch merge skips it; the base branch records the state itself.
        (root / first).write_text("status: Blocked\nnotes: Blocked: missing credential\n", encoding="utf-8")
        self.git(root, "add", "--", first)
        self.git(root, "commit", "-q", "-m", "backlog: block TASK-1")

        self.assertFalse((root / "impl.py").exists(), "partial work must not reach the base")
        self.assertIn("status: Blocked", read(root / first))
        # The branch and its worktree survive for diagnosis.
        self.assertIn("backlog/TASK-1", self.git(root, "branch", "--list").stdout)
        self.assertTrue((worktree / "impl.py").exists())
        self.assertEqual(self.git(root, "status", "--porcelain").stdout.strip(), "")

    # --- release artifact ---------------------------------------------------
    #
    # INSTALL.md's manual path is `git archive HEAD backlog-workflow`, which ships
    # the tracked-file manifest, not the working tree. A managed file listed in
    # MANAGED_FILES but absent from the artifact makes `apply` fail with
    # FileNotFoundError on a user's machine while passing every test here.

    def package_paths(self) -> list[str]:
        """Repository paths the installed workflow is rendered from."""
        return [
            f"{ROOT.name}/templates/project/{relative.as_posix()}"
            for relative in install.MANAGED_FILES
        ] + [
            f"{ROOT.name}/{name}"
            for name in (
                "VERSION", "SKILL.md", "INSTALL.md", "README.md", "LICENSE",
                "scripts/install.py", "scripts/validate_package.py",
                "references/OPERATIONS.md", "references/PROJECT-DISCOVERY.md",
            )
        ]

    def git_in_repo(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=str(ROOT.parent), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )

    def test_every_managed_file_is_tracked(self) -> None:
        """Catches a managed file that was added but never `git add`ed."""
        listed = self.git_in_repo("ls-files", "--", ROOT.name)
        if listed.returncode != 0:
            self.skipTest("not a git checkout")
        tracked = set(listed.stdout.splitlines())
        missing = [path for path in self.package_paths() if path not in tracked]
        self.assertEqual(missing, [], f"managed files not tracked by git: {missing}")

    def test_release_archive_contains_every_managed_file(self) -> None:
        """The committed artifact, not the working tree, is what users install."""
        dirty = self.git_in_repo("status", "--porcelain", "--", ROOT.name)
        if dirty.returncode != 0:
            self.skipTest("not a git checkout")
        if dirty.stdout.strip():
            # HEAD is not the release artifact yet. `test_every_managed_file_is
            # _tracked` still covers the forgotten-`git add` case meanwhile.
            self.skipTest(f"package has uncommitted changes:\n{dirty.stdout.strip()}")

        archive = subprocess.run(
            ["git", "archive", "HEAD", ROOT.name], cwd=str(ROOT.parent),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(archive.returncode, 0, archive.stderr.decode())
        listing = subprocess.run(
            ["tar", "-tf", "-"], input=archive.stdout, stdout=subprocess.PIPE, check=False
        )
        shipped = set(listing.stdout.decode().splitlines())
        missing = [path for path in self.package_paths() if path not in shipped]
        self.assertEqual(missing, [], f"managed files missing from git archive HEAD: {missing}")
        self.assertIn(
            f"{ROOT.name}/templates/project/.agent-workflow/PARALLEL.md", shipped
        )

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

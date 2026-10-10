"""The Claude Plugin version is independent of backlog-workflow's template version."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backlog-workflow" / "scripts"))
from validate_package import validate_plugin_version  # noqa: E402


class PluginReleaseTests(unittest.TestCase):
    def test_manifest_has_valid_semver(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_plugin_version(plugin), plugin["version"])

    def test_release_version_can_differ_from_workflow_version(self):
        workflow_version = (ROOT / "backlog-workflow/VERSION").read_text(encoding="utf-8").strip()
        alternative_version = "99.0.0" if workflow_version != "99.0.0" else "98.0.0"
        self.assertEqual(validate_plugin_version({"version": alternative_version}), alternative_version)

    def test_invalid_release_versions_are_rejected(self):
        for bad in (None, 123, "", "v1.7.0", "1.7", "1.7.0-beta", "1.7.0.1"):
            with self.subTest(version=bad):
                with self.assertRaisesRegex(AssertionError, "semantic"):
                    validate_plugin_version({"version": bad})


if __name__ == "__main__":
    unittest.main()

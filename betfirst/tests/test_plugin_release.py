"""Claude Plugin release version is independent of individual Skills."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_plugin import validate_plugin, validate_plugin_version  # noqa: E402


class PluginReleaseTests(unittest.TestCase):
    def test_manifest_has_valid_semver(self):
        plugin = json.loads((ROOT / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        self.assertEqual(validate_plugin_version(plugin), plugin['version'])

    def test_plugin_validation_has_no_legacy_workflow_dependency(self):
        validate_plugin(ROOT)

    def test_invalid_release_versions_are_rejected(self):
        for bad in (None, 123, '', 'v2.0.0', '2.0', '2.0.0-beta', '2.0.0.1', '01.0.0'):
            with self.subTest(version=bad):
                with self.assertRaisesRegex(AssertionError, 'semantic'):
                    validate_plugin_version({'version': bad})


if __name__ == '__main__':
    unittest.main()

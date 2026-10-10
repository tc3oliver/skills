"""Regression coverage for additive-only test integrity and offline regrading."""
from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))
from regrade import regrade
from run import execute
from test_integrity import inspect_tests


class TestIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / "work"
        self.fixture = EXP / "fixtures" / "render-resume"
        shutil.copytree(self.fixture, self.workspace)
        self.test_file = self.workspace / "tests" / "test_pipeline.py"
        self.original = self.test_file.read_text(encoding="utf-8")

    def test_original_unchanged(self):
        result = inspect_tests(self.fixture, self.workspace)
        self.assertTrue(result["passed"])
        self.assertFalse(result["added_test_files"])

    def test_add_new_test_method_inside_existing_class(self):
        needle = '\n\nif __name__ == "__main__":'
        self.assertIn(needle, self.original)
        extra = (
            '\n    def test_resume_collision(self):\n'
            '        self.assertEqual(1 + 1, 2)\n'
        )
        self.test_file.write_text(self.original.replace(needle, "\n" + extra + needle))
        result = inspect_tests(self.fixture, self.workspace)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["extended_test_files"], ["test_pipeline.py"])

    def test_add_new_test_class_before_main_guard(self):
        needle = '\n\nif __name__ == "__main__":'
        extra = (
            '\n\nclass NewRegressions(unittest.TestCase):\n'
            '    def test_resume_collision(self):\n'
            '        self.assertTrue(True)\n'
        )
        self.test_file.write_text(self.original.replace(needle, extra + needle))
        self.assertTrue(inspect_tests(self.fixture, self.workspace)["passed"])

    def test_new_test_file_is_allowed(self):
        (self.workspace / "tests" / "test_incident.py").write_text(
            "import unittest\n\n"
            "class IncidentTests(unittest.TestCase):\n"
            "    def test_incident(self):\n"
            "        self.assertTrue(True)\n"
        )
        result = inspect_tests(self.fixture, self.workspace)
        self.assertTrue(result["passed"])
        self.assertEqual(result["added_test_files"], ["test_incident.py"])

    def test_existing_assertion_modified_is_rejected(self):
        self.assertIn('self.assertEqual(calls, ["a-1", "b-2"])', self.original)
        self.test_file.write_text(
            self.original.replace('self.assertEqual(calls, ["a-1", "b-2"])',
                                  'self.assertEqual(calls, [])')
        )
        result = inspect_tests(self.fixture, self.workspace)
        self.assertFalse(result["passed"])
        self.assertEqual(result["tampered_test_files"], ["test_pipeline.py"])

    def test_deleted_or_replaced_tests_are_rejected(self):
        self.test_file.unlink()
        self.assertIn("test_pipeline.py",
                      inspect_tests(self.fixture, self.workspace)["deleted_test_files"])

    def test_duplicate_method_shadowing_is_rejected(self):
        needle = '\n\nif __name__ == "__main__":'
        duplicate = (
            '\n    def test_render_and_resume_unique_titles(self):\n'
            '        self.assertTrue(True)\n'
        )
        self.test_file.write_text(self.original.replace(needle, "\n" + duplicate + needle))
        self.assertFalse(inspect_tests(self.fixture, self.workspace)["passed"])

    def test_non_test_file_injection_is_rejected(self):
        (self.workspace / "tests" / "conftest.py").write_text("raise RuntimeError('side effect')\n")
        self.assertFalse(inspect_tests(self.fixture, self.workspace)["passed"])


class RegradeTests(unittest.TestCase):
    def test_regrade_fixes_additive_false_negative_but_preserves_agent_exit_failure(self):
        suite = EXP / "suite-v2.json"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source"
            # Produce mock evidence first, then deliberately simulate an older
            # live run's false negatives. This is a fixture, NOT a model call.
            execute(suite, source, "mock", None, 1, 42, 30, False,
                    selected_tasks=["render-resume"])
            manifest_file = source / "manifest.json"
            manifest = json.loads(manifest_file.read_text())
            manifest["synthetic"] = False
            manifest["driver"] = "claude"
            manifest_file.write_text(json.dumps(manifest))
            orig_csv = source / "synthetic-smoke.csv"
            measured = source / "measured-runs.csv"
            orig_csv.rename(measured)
            with measured.open(newline="") as handle:
                reader = csv.DictReader(handle)
                cols = reader.fieldnames
                rows = list(reader)
            for row in rows:
                arm = row["arm"]
                folder = source / f"render-resume-r1-{arm}"
                outcome_file = folder / "outcome.json"
                outcome = json.loads(outcome_file.read_text())
                if arm == "baseline":
                    outcome["agent_exit"] = 1  # real failure even though oracle passed
                else:
                    (folder / "work" / "tests" / "test_incident.py").write_text(
                        "import unittest\n"
                        "class Extra(unittest.TestCase):\n"
                        "    def test_regression(self):\n"
                        "        self.assertTrue(True)\n"
                    )
                    outcome["tests_changed"] = True
                outcome["passed"] = False
                row["passed"] = "false"
                outcome_file.write_text(json.dumps(outcome))
            with measured.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=cols)
                writer.writeheader()
                writer.writerows(rows)

            before = measured.read_bytes()
            original_outcome = (source / "render-resume-r1-efficiency" / "outcome.json").read_bytes()
            derived = source / "regraded-v2"
            summary = regrade(source, suite, derived)
            self.assertEqual(summary["passes_before"], 0)
            self.assertEqual(summary["passes_after"], 2)
            self.assertEqual(len(summary["changes"]), 2)
            self.assertTrue(summary["fixture_hashes_verified"])
            self.assertEqual(measured.read_bytes(), before)
            self.assertEqual(
                (source / "render-resume-r1-efficiency" / "outcome.json").read_bytes(),
                original_outcome
            )
            with (derived / "measured-runs.csv").open(newline="") as handle:
                result = {r["arm"]: r["passed"] for r in csv.DictReader(handle)}
            self.assertEqual(result, {
                "baseline": "false", "efficiency": "true", "betfirst": "true"
            })
            with self.assertRaisesRegex(ValueError, "new directory"):
                regrade(source, suite, derived)

    def test_regrade_refuses_different_suite(self):
        suite = EXP / "suite-v2.json"
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "source"
            execute(suite, source, "mock", None, 1, 42, 30, False,
                    selected_tasks=["config-scope"])
            m = source / "manifest.json"
            manifest = json.loads(m.read_text())
            manifest["synthetic"] = False
            manifest["driver"] = "claude"
            manifest["suite_sha256"] = "definitely wrong"
            m.write_text(json.dumps(manifest))
            (source / "synthetic-smoke.csv").rename(source / "measured-runs.csv")
            with self.assertRaisesRegex(ValueError, "suite SHA mismatch"):
                regrade(source, suite, Path(d) / "derived")


if __name__ == "__main__":
    unittest.main()

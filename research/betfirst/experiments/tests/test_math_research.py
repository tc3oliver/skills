import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "math-research"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


driver = load("driver")
analyze = load("analyze")


def stream(*events):
    return "\n".join(json.dumps(e) for e in events)


class DriverParsing(unittest.TestCase):
    def test_usage_and_tool_calls(self):
        s = stream(
            {"type": "system", "subtype": "init", "model": "m"},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "1"}, {"type": "text"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "2"}]}},
            {"type": "result", "subtype": "success", "num_turns": 3, "is_error": False,
             "usage": {"input_tokens": 5, "output_tokens": 7, "cache_read_input_tokens": 11,
                       "cache_creation_input_tokens": 13}})
        u = driver.summarize(s)
        self.assertEqual((u["tool_calls"], u["input_tokens"], u["output_tokens"], u["cached_tokens"],
                          u["cache_write_tokens"], u["model_reported"]), (2, 5, 7, 11, 13, "m"))

    def test_missing_usage_stays_none(self):
        u = driver.summarize(stream({"type": "result", "usage": {"input_tokens": True}}))
        self.assertIsNone(u["input_tokens"])
        self.assertIsNone(u["output_tokens"])

    def test_route_self_report(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(driver.route_from_answer(Path(d)), "missing")
            (Path(d) / "ROUTE.txt").write_text("bet — hypothesis ...")
            self.assertEqual(driver.route_from_answer(Path(d)), "BET")
            (Path(d) / "ROUTE.txt").write_text("maybe")
            self.assertEqual(driver.route_from_answer(Path(d)), "missing")

    def test_control_prompt_has_no_skill(self):
        task = {"prompt": "Do X."}
        self.assertNotIn("BetFirst", driver.prompt_for(task, "B", "SKILL"))
        self.assertIn("SKILL", driver.prompt_for(task, "A", "SKILL"))

    def test_instantiate_lean_project(self):
        old = os.environ.get("JSP_LEAN_PROJECT")
        os.environ["JSP_LEAN_PROJECT"] = "/x/lean"
        try:
            t = driver.instantiate({"prompt": "-d {LEAN_PROJECT} env", "allowed_tools": ["Bash({LEAN_PROJECT}:*)"]})
            self.assertEqual(t["prompt"], "-d /x/lean env")
            self.assertEqual(t["allowed_tools"], ["Bash(/x/lean:*)"])
        finally:
            if old is None:
                del os.environ["JSP_LEAN_PROJECT"]
            else:
                os.environ["JSP_LEAN_PROJECT"] = old


class Analysis(unittest.TestCase):
    def test_gross_requires_all_fields(self):
        self.assertEqual(analyze.gross({"input_tokens": 1, "output_tokens": 2, "cached_tokens": 3,
                                        "cache_write_tokens": 4}), 10)
        self.assertIsNone(analyze.gross({"input_tokens": 1, "output_tokens": 2, "cached_tokens": None,
                                         "cache_write_tokens": 4}))

    def test_published_metrics_complete(self):
        rows = [json.loads(l) for l in (HERE / "data/metrics.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual(len(rows), 12)
        self.assertEqual({r["arm"] for r in rows}, {"A", "B"})
        for r in rows:
            self.assertIn(r["outcome"], {"PASS", "FAIL", "INCOMPLETE"})


if __name__ == "__main__":
    unittest.main()

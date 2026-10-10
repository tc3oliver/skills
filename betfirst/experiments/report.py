#!/usr/bin/env python3
"""Report real three-arm pilot evidence; refuse to treat synthetic smoke as savings."""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "betfirst" / "scripts"))
from analyze_runs import load_records, complete_sum, savings  # noqa: E402

PAIRS = (("betfirst", "efficiency"), ("betfirst", "baseline"), ("efficiency", "baseline"))


def report_dir(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("synthetic") is True:
        return {
            "status": "SYNTHETIC_HARNESS_SMOKE_ONLY",
            "valid_performance_claim": False,
            "note": "No LLM was run. These durations are mock process overhead, not BetFirst savings.",
            "declared_runs": manifest.get("runs"),
            "comparisons": {},
        }
    if manifest.get("driver") not in {"claude", "pi"}:
        raise ValueError("unknown or missing real agent driver in manifest")
    with (directory / "measured-runs.csv").open(encoding="utf-8", newline="") as f:
        records = load_records(csv.DictReader(f))
    arms = {arm: {r["key"]: r for r in records if r["arm"] == arm}
            for arm in ("baseline", "efficiency", "betfirst")}
    output = {}
    for candidate, control in PAIRS:
        keys = sorted(set(arms[candidate]) & set(arms[control]))
        if not keys:
            continue
        a = [arms[candidate][key] for key in keys]
        b = [arms[control][key] for key in keys]
        a_time, b_time = complete_sum(a, "elapsed_seconds"), complete_sum(b, "elapsed_seconds")
        a_tokens, b_tokens = complete_sum(a, "gross_tokens"), complete_sum(b, "gross_tokens")
        a_cost, b_cost = complete_sum(a, "api_cost_usd"), complete_sum(b, "api_cost_usd")
        all_both_correct = all(left["passed"] and right["passed"] for left, right in zip(a, b))
        output[f"{candidate}_vs_{control}"] = {
            "matched_pairs": len(keys),
            "candidate_passed": sum(r["passed"] for r in a),
            "control_passed": sum(r["passed"] for r in b),
            "all_pairs_correct": all_both_correct,
            "wall_time_saving_fraction": savings(b_time, a_time),
            "gross_tokens_saving_fraction": savings(b_tokens, a_tokens),
            "api_cost_saving_fraction": savings(b_cost, a_cost),
            "note": "Comparative observation only, NOT a causal speedup claim."
        }
    return {
        "status": "LIVE_PILOT_UNCONTROLLED_PUBLICATION",
        "valid_performance_claim": False,
        "driver": manifest["driver"],
        "model": manifest.get("model"),
        "comparisons": output,
        "limitations": [
            "Tiny fixture set; no replicated 30-task confirmatory study.",
            "Unmatched runs are not included in paired contrasts.",
            "Missing token/cache/price usage remains null, not zero.",
            "A faster candidate is not a quality-equivalent saving unless all paired checks pass.",
            "Observed speedups can reflect model randomness, cold starts, host load or other confounding.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    print(json.dumps(report_dir(args.output), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

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

def iter_csv(rows: list[dict]):
    """Reuse existing validated CSV parser without duplicating schema rules."""
    import io
    buf = io.StringIO()
    if not rows:
        return csv.DictReader(buf)
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return csv.DictReader(buf)



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
        raw_rows = list(csv.DictReader(f))
    records = load_records(iter_csv(raw_rows))
    # Reliability fields are optional so legacy v1/v2 CSVs remain readable.
    def count_pass(field: str, arm: str, pairs: list[tuple]) -> int | None:
        vals = []
        for key in pairs:
            value = next((r.get(field) for r in raw_rows
                          if r["task_id"] == key[0] and str(r["replicate"]) == str(key[1])
                          and r["arm"] == arm), None)
            if value not in ("true", "false"):
                return None
            vals.append(value == "true")
        return sum(vals)

    # Optional trace fields from v2; preserve unknown when CLI emits no tool events.
    tool_by_arm = {}
    for r in raw_rows:
        value = r.get("tool_calls", "")
        if value not in ("", None):
            tool_by_arm[(r["task_id"], r["replicate"], r["arm"])] = int(value)
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
        paired_tool_counts = [
            (tool_by_arm.get((key[0], key[1], candidate)),
             tool_by_arm.get((key[0], key[1], control)))
            for key in keys
        ]
        tools_known = all(x is not None and y is not None for x, y in paired_tool_counts)
        output[f"{candidate}_vs_{control}"] = {
            "matched_pairs": len(keys),
            "candidate_passed": sum(r["passed"] for r in a),
            "control_passed": sum(r["passed"] for r in b),
            "all_pairs_correct": all_both_correct,
            "candidate_code_accepted": count_pass("code_accepted", candidate, keys),
            "control_code_accepted": count_pass("code_accepted", control, keys),
            "candidate_session_success": count_pass("session_success", candidate, keys),
            "control_session_success": count_pass("session_success", control, keys),
            "tool_calls_candidate": sum(pair[0] for pair in paired_tool_counts) if tools_known else None,
            "tool_calls_control": sum(pair[1] for pair in paired_tool_counts) if tools_known else None,
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
            "Tool-call counts use unique Claude tool_use IDs, not model self-report; BET labels remain unverified.",
            "Agent session completion and post-run code acceptance are reported separately when recorded.",
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

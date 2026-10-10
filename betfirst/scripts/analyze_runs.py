#!/usr/bin/env python3
"""Summarize external, paired coding-agent benchmark runs without estimating missing usage."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

REQUIRED = {"task_id", "replicate", "arm", "passed", "elapsed_seconds"}
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
ARMS = {"baseline", "efficiency", "betfirst"}


def number(raw: str | None, field: str, integral: bool = False) -> float | int | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = int(raw) if integral else float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {raw!r}") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return value


def load_records(reader: csv.DictReader) -> list[dict]:
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise ValueError(f"required columns: {', '.join(sorted(REQUIRED))}")
    records: list[dict] = []
    seen = set()
    for line, row in enumerate(reader, start=2):
        task, replicate, arm = (row[key].strip() for key in ("task_id", "replicate", "arm"))
        if not task or not replicate or arm not in ARMS:
            raise ValueError(f"line {line}: invalid task_id, replicate, or arm")
        key = (task, replicate, arm)
        if key in seen:
            raise ValueError(f"line {line}: duplicate task/replicate/arm {key}")
        seen.add(key)
        passed = row["passed"].strip().lower()
        if passed not in {"true", "false", "1", "0"}:
            raise ValueError(f"line {line}: passed must be true/false/1/0")
        duration = number(row["elapsed_seconds"], "elapsed_seconds")
        if duration is None:
            raise ValueError(f"line {line}: elapsed_seconds missing")
        tokens = {field: number(row.get(field), field, integral=True) for field in TOKEN_FIELDS}
        gross_tokens = sum(tokens.values()) if all(v is not None for v in tokens.values()) else None
        record = {
            "key": (task, replicate),
            "arm": arm,
            "passed": passed in {"true", "1"},
            "elapsed_seconds": duration,
            "gross_tokens": gross_tokens,
            "api_cost_usd": number(row.get("api_cost_usd"), "api_cost_usd"),
            "bet_attempts": number(row.get("bet_attempts"), "bet_attempts", integral=True),
            "bet_failures": number(row.get("bet_failures"), "bet_failures", integral=True),
            "failed_bet_overhead_seconds": number(
                row.get("failed_bet_overhead_seconds"), "failed_bet_overhead_seconds"
            ),
        }
        if record["bet_attempts"] is not None and record["bet_failures"] is not None:
            if record["bet_failures"] > record["bet_attempts"]:
                raise ValueError(f"line {line}: bet_failures exceeds bet_attempts")
        records.append(record)
    if not records:
        raise ValueError("no benchmark rows")
    return records


def complete_sum(rows: list[dict], field: str) -> float | int | None:
    values = [row[field] for row in rows]
    return sum(values) if all(value is not None for value in values) else None


def savings(baseline: float | int | None, candidate: float | int | None) -> float | None:
    if baseline is None or candidate is None or baseline == 0:
        return None
    return 1 - candidate / baseline


def report(records: list[dict]) -> dict:
    groups = {arm: [row for row in records if row["arm"] == arm] for arm in sorted(ARMS)}
    arms = {}
    for arm, rows in groups.items():
        if not rows:
            continue
        arms[arm] = {
            "runs": len(rows),
            "passed": sum(row["passed"] for row in rows),
            "success_rate": sum(row["passed"] for row in rows) / len(rows),
            "total_elapsed_seconds": complete_sum(rows, "elapsed_seconds"),
            "gross_tokens": complete_sum(rows, "gross_tokens"),
            "api_cost_usd": complete_sum(rows, "api_cost_usd"),
            "bet_attempts": complete_sum(rows, "bet_attempts"),
            "bet_failures": complete_sum(rows, "bet_failures"),
            "failed_bet_overhead_seconds": complete_sum(rows, "failed_bet_overhead_seconds"),
        }
    by_arm = {arm: {r["key"]: r for r in rows} for arm, rows in groups.items()}
    comparisons = {}
    for arm in ("efficiency", "betfirst"):
        keys = sorted(set(by_arm["baseline"]) & set(by_arm[arm]))
        if not keys:
            continue
        base = [by_arm["baseline"][key] for key in keys]
        candidate = [by_arm[arm][key] for key in keys]
        b_time = complete_sum(base, "elapsed_seconds")
        c_time = complete_sum(candidate, "elapsed_seconds")
        b_tokens = complete_sum(base, "gross_tokens")
        c_tokens = complete_sum(candidate, "gross_tokens")
        b_cost = complete_sum(base, "api_cost_usd")
        c_cost = complete_sum(candidate, "api_cost_usd")
        comparisons[f"{arm}_vs_baseline"] = {
            "matched_pairs": len(keys),
            "baseline_passed": sum(r["passed"] for r in base),
            "candidate_passed": sum(r["passed"] for r in candidate),
            "time_saving_fraction": savings(b_time, c_time),
            "gross_token_saving_fraction": savings(b_tokens, c_tokens),
            "api_cost_saving_fraction": savings(b_cost, c_cost),
        }
    return {
        "schema_version": 1,
        "notes": [
            "All arms include failed-task resource consumption.",
            "Gross tokens sum input, output, cache-read and cache-write tokens when all are available.",
            "API cost is a separate metric; cache tokens are not equally priced.",
            "Missing usage remains null, never zero or an estimate.",
            "Paired comparisons match task_id and replicate, and do not assert causality on their own.",
        ],
        "arms": arms,
        "comparisons": comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV exported from independently collected runs")
    args = parser.parse_args()
    with args.csv_path.open(encoding="utf-8", newline="") as handle:
        data = report(load_records(csv.DictReader(handle)))
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

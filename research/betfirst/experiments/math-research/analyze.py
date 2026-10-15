#!/usr/bin/env python3
"""Summarize a bench run dir: per-arm and per-task stats, paired A-vs-B by task.

Usage: analyze.py RUN_DIR [TRACE_DIR]  (metrics from RUN_DIR; stdout.jsonl traces from
TRACE_DIR/<run_id>/, default RUN_DIR; raw traces are kept out of git)
Missing values stay missing; nothing is imputed.
"""
from __future__ import annotations

import json, statistics as st, sys
from collections import defaultdict
from pathlib import Path


def route_writes(stream: Path) -> int:
    """Tool calls that write ROUTE.txt (arm A protocol overhead, not task work)."""
    n = 0
    for line in stream.read_text().splitlines() if stream.is_file() else []:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        for b in (e.get("message") or {}).get("content") or [] if e.get("type") == "assistant" else []:
            if isinstance(b, dict) and b.get("type") == "tool_use" and \
                    str((b.get("input") or {}).get("file_path", "")).endswith("ROUTE.txt"):
                n += 1
    return n


def gross(r: dict):
    keys = ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens")
    return sum(r[k] for k in keys) if all(isinstance(r.get(k), int) for k in keys) else None


def describe(xs: list) -> str:
    xs = [x for x in xs if x is not None]
    if not xs:
        return "missing"
    return f"mean {st.mean(xs):.1f} / median {st.median(xs):.1f} (n={len(xs)})"


def main(run: Path, traces: Path) -> None:
    rows = [json.loads(l) for l in (run / "metrics.jsonl").read_text().splitlines() if l.strip()]
    for r in rows:
        r["route_writes"] = route_writes(traces / r["run_id"] / "stdout.jsonl")
        r["task_tool_calls"] = None if r["tool_calls"] is None else r["tool_calls"] - r["route_writes"]
        r["gross_tokens"] = gross(r)
    print(f"runs={len(rows)}  PASS={sum(r['outcome'] == 'PASS' for r in rows)}")
    by_arm = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)
    for arm, rs in sorted(by_arm.items()):
        print(f"\narm {arm} ({rs[0]['skill_version']}): PASS {sum(r['outcome'] == 'PASS' for r in rs)}/{len(rs)}"
              f"  routes={dict((k, [r['route'] for r in rs].count(k)) for k in set(r['route'] for r in rs))}")
        for k in ("wall_time_ms", "tool_calls", "task_tool_calls", "output_tokens", "gross_tokens", "num_turns"):
            print(f"  {k}: {describe([r[k] for r in rs])}")
    print("\npaired by task (mean of reps; A minus B):")
    tasks = sorted({r["task_id"] for r in rows})
    deltas = []
    for t in tasks:
        a = [r for r in rows if r["task_id"] == t and r["arm"] == "A"]
        b = [r for r in rows if r["task_id"] == t and r["arm"] == "B"]
        line = [t]
        for k in ("wall_time_ms", "tool_calls", "task_tool_calls", "gross_tokens"):
            va = [r[k] for r in a if r[k] is not None]
            vb = [r[k] for r in b if r[k] is not None]
            if va and vb:
                d = st.mean(va) - st.mean(vb)
                line.append(f"{k} {st.mean(va):.0f} vs {st.mean(vb):.0f} ({d:+.0f}, {100 * d / st.mean(vb):+.1f}%)")
                if k == "wall_time_ms":
                    deltas.append(d / st.mean(vb))
            else:
                line.append(f"{k} missing")
        print("  " + " | ".join(line))
    if deltas:
        print(f"\nA faster on {sum(d < 0 for d in deltas)}/{len(deltas)} tasks (mean wall); "
              f"mean relative wall change {100 * st.mean(deltas):+.1f}% (descriptive only)")
    print("\nper run:")
    for r in sorted(rows, key=lambda r: (r["task_id"], r["arm"], r["rep"])):
        print(f"  {r['run_id']:26} {r['outcome']:4} {r['route']:6} wall={r['wall_time_ms']:>6} "
              f"tools={r['tool_calls']} route_writes={r['route_writes']} gross_tok={r['gross_tokens']}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]))

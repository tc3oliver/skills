#!/usr/bin/env python3
"""Descriptive paired evaluation: no invented token counts or causal attribution."""
from __future__ import annotations
import argparse
import collections
import csv
import json
import statistics
from pathlib import Path

ARMS = ("efficiency", "betfirst-v04", "betfirst-v04-nobet")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("study", type=Path)
    args=p.parse_args()
    root=args.study.expanduser().resolve()
    with (root/"manifest.json").open() as f:
        manifest=json.load(f)
    if manifest.get("selected_arms") != list(ARMS) or not manifest.get("paired"):
        raise SystemExit("Not the preregistered three-arm v05 cohort")
    with (root/"measured-runs.csv").open(newline="") as f:
        rows=list(csv.DictReader(f))
    by_group=collections.defaultdict(dict)
    for row in rows:
        key=(row["task_id"],row["replicate"])
        if row["arm"] in by_group[key]:
            raise SystemExit(f"Duplicate session: {key} {row['arm']}")
        by_group[key][row["arm"]]=row
    complete=[g for g in by_group.values() if set(g)==set(ARMS)]
    print(f"Complete groups: {len(complete)}/24; sessions: {len(rows)}/72")
    if not complete:
        return
    def passed(r):
        return str(r.get("passed","")).lower() in ("true","1")
    def num(r,k):
        try:
            value=r.get(k,"")
            return float(value) if value not in ("",None,"None") else None
        except ValueError:
            return None
    for arm in ARMS:
        records=[group[arm] for group in complete]
        durations=[num(r,"elapsed_seconds") for r in records]
        durations=[x for x in durations if x is not None]
        token_known=sum(num(r,"input_tokens") is not None and num(r,"output_tokens") is not None for r in records)
        print(f"{arm}: PASS {sum(passed(r) for r in records)}/{len(records)}, "
              f"mean wall {statistics.mean(durations):.2f}s, "
              f"median wall {statistics.median(durations):.2f}s, "
              f"complete token records {token_known}/{len(records)}")
    for other in ("efficiency","betfirst-v04-nobet"):
        pair=[(g["betfirst-v04"],g[other]) for g in complete
              if passed(g["betfirst-v04"]) and passed(g[other])]
        wins=sum(num(a,"elapsed_seconds") < num(b,"elapsed_seconds") for a,b in pair
                 if num(a,"elapsed_seconds") is not None and num(b,"elapsed_seconds") is not None)
        diffs=[num(a,"elapsed_seconds")-num(b,"elapsed_seconds") for a,b in pair
               if num(a,"elapsed_seconds") is not None and num(b,"elapsed_seconds") is not None]
        print(f"v0.4 vs {other}: both PASS {len(pair)}, faster {wins}/{len(diffs)}, "
              f"mean paired delta {statistics.mean(diffs):+.2f}s" if diffs else
              f"v0.4 vs {other}: no valid pairs")
    print("Behavioral BET attribution requires independent tool-trace review; never infer it from arm labels.")
    print("Token savings UNKNOWN when provider usage events are incomplete.")


if __name__=="__main__":
    main()

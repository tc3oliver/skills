#!/usr/bin/env python3
"""Summarize a BetFirst bet log (JSON) without estimating anything that was not recorded."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_CAP_SECONDS = 120
RESULTS = {"success", "failure"}


def summarize(log: dict, cap_seconds: int = DEFAULT_CAP_SECONDS) -> dict:
    bets = log.get("bets")
    if not isinstance(bets, list) or not bets:
        raise ValueError("log needs a non-empty 'bets' list")
    ids = [b.get("id") for b in bets]
    if len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("bet ids must be present and unique")
    for b in bets:
        if b.get("result") not in RESULTS:
            raise ValueError(f"{b['id']}: result must be one of {sorted(RESULTS)}")
    durations = [b.get("duration_seconds") for b in bets]
    known = [d for d in durations if isinstance(d, (int, float))]
    tokens_known = [b for b in bets if b.get("tokens_input") is not None or b.get("tokens_output") is not None]
    return {
        "bets": len(bets),
        "successes": sum(b["result"] == "success" for b in bets),
        "failures": sum(b["result"] == "failure" for b in bets),
        "bet_seconds": sum(known) if len(known) == len(durations) else None,
        "bets_without_duration": len(durations) - len(known),
        "over_cap": [b["id"] for b in bets if isinstance(b.get("duration_seconds"), (int, float)) and b["duration_seconds"] > cap_seconds],
        "cap_seconds": cap_seconds,
        "rollbacks": sum(b.get("rollback_required") is True for b in bets),
        "fallbacks": sum(b.get("fallback_required") is True for b in bets),
        "bets_with_token_usage": len(tokens_known),
        "note": "null/0 token counts are reported as unavailable, never as zero; this summary says nothing about savings",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--cap-seconds", type=int, default=DEFAULT_CAP_SECONDS)
    args = parser.parse_args(argv)
    try:
        result = summarize(json.loads(args.log.read_text(encoding="utf-8")), args.cap_seconds)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

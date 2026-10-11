#!/usr/bin/env python3
"""Audit a BetFirst field log without rewriting or guessing raw measurements."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_CAP_SECONDS = 120
RESULTS = {"success", "failure"}
# Timestamp boundaries have second-level precision in the original field log.
TIME_TOLERANCE_SECONDS = 1


def measured_number(value: object, name: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a nonnegative number or null")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative number")
    return value


def timestamp_span(bet: dict) -> float | None:
    """Return a timestamp *span*, not an independently measured probe duration."""
    start, end = bet.get("started_at"), bet.get("ended_at")
    if start is None and end is None:
        return None
    if not isinstance(start, str) or not isinstance(end, str):
        raise ValueError(f"{bet['id']}: both timestamps must be offset-aware strings")
    try:
        first = datetime.fromisoformat(start.replace("Z", "+00:00"))
        last = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{bet['id']}: invalid ISO timestamp") from exc
    if first.tzinfo is None or last.tzinfo is None:
        raise ValueError(f"{bet['id']}: timestamps must include time zones")
    span = (last - first).total_seconds()
    if span < 0:
        raise ValueError(f"{bet['id']}: end precedes start")
    return span


def summarize(log: dict, cap_seconds: int = DEFAULT_CAP_SECONDS) -> dict:
    if isinstance(cap_seconds, bool) or not isinstance(cap_seconds, (int, float)) or not math.isfinite(cap_seconds) or cap_seconds <= 0:
        raise ValueError("cap_seconds must be positive and finite")
    bets = log.get("bets")
    if not isinstance(bets, list) or not bets or any(not isinstance(b, dict) for b in bets):
        raise ValueError("log needs a non-empty 'bets' list of objects")
    ids = [b.get("id") for b in bets]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("bet ids must be present and unique")
    for b in bets:
        if b.get("result") not in RESULTS:
            raise ValueError(f"{b['id']}: result must be one of {sorted(RESULTS)}")

    recorded = [measured_number(b.get("duration_seconds"), f"{b['id']} duration_seconds") for b in bets]
    spans = [timestamp_span(b) for b in bets]
    recorded_known = [d for d in recorded if d is not None]
    spans_known = [d for d in spans if d is not None]
    discrepancies = [
        {
            "id": b["id"],
            "recorded_seconds": duration,
            "timestamp_span_seconds": span,
            "span_minus_recorded_seconds": span - duration,
        }
        for b, duration, span in zip(bets, recorded, spans)
        if duration is not None and span is not None and abs(span - duration) > TIME_TOLERANCE_SECONDS
    ]
    partial_tokens = []
    complete_tokens = 0
    for bet in bets:
        a = measured_number(bet.get("tokens_input"), f"{bet['id']} tokens_input")
        z = measured_number(bet.get("tokens_output"), f"{bet['id']} tokens_output")
        if a is not None and z is not None:
            complete_tokens += 1
        elif a is not None or z is not None:
            partial_tokens.append(bet["id"])

    return {
        "bets": len(bets),
        "successes": sum(b["result"] == "success" for b in bets),
        "failures": sum(b["result"] == "failure" for b in bets),
        # Retain the original interface but never call this a validated wall-clock total.
        "bet_seconds": sum(recorded_known) if len(recorded_known) == len(bets) else None,
        "recorded_duration_seconds": sum(recorded_known) if len(recorded_known) == len(bets) else None,
        "timestamp_span_seconds": sum(spans_known) if len(spans_known) == len(bets) else None,
        "bets_without_duration": len(bets) - len(recorded_known),
        "bets_without_timestamps": len(bets) - len(spans_known),
        "duration_discrepancies": discrepancies,
        "timing_reconciled": len(discrepancies) == 0 and len(recorded_known) == len(spans_known) == len(bets),
        "over_cap": [b["id"] for b, d in zip(bets, recorded) if d is not None and d > cap_seconds],
        "over_cap_by_timestamp": [b["id"] for b, d in zip(bets, spans) if d is not None and d > cap_seconds],
        "cap_seconds": cap_seconds,
        "rollbacks": sum(b.get("rollback_required") is True for b in bets),
        "fallbacks": sum(b.get("fallback_required") is True for b in bets),
        "bets_with_token_usage": complete_tokens,
        "bets_with_partial_token_usage": partial_tokens,
        "note": (
            "Reported duration and timestamp span are separate unverified observations; "
            "do not use either as a proved probe cost until reconciled. Spans can include "
            "waiting/concurrent work and can overlap. Null tokens are unknown, not zero. "
            "A refuted hypothesis can be an informative probe; neither success counts "
            "nor these duration sums establish savings."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--cap-seconds", type=int, default=DEFAULT_CAP_SECONDS)
    args = parser.parse_args(argv)
    try:
        result = summarize(json.loads(args.log.read_text(encoding="utf-8")), args.cap_seconds)
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

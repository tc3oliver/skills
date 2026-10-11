"""Conservative OpenCode run --format json metrics.

Some OpenCode releases omit the last step_finish on clean exits. Incomplete
stream usage is unknown (None), never zero or partial totals.
"""
from __future__ import annotations
from collections import Counter
import json

FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens",
          "cache_write_tokens", "api_cost_usd")


def metrics(data: str) -> tuple[dict, dict]:
    unknown = dict.fromkeys(FIELDS)
    trace = {
        "agent_subtype": None, "agent_turns": None, "agent_is_error": None,
        "trace_complete": False, "tool_calls": None, "tool_results": None,
        "tool_errors": None, "permission_denials": None, "tools_by_name": None,
        "bet_attempts": None, "bet_failures": None,
        "failed_bet_overhead_seconds": None,
    }
    try:
        events = [json.loads(line) for line in data.splitlines() if line.strip()]
    except ValueError:
        return unknown, trace
    if not events or not all(isinstance(e, dict) for e in events):
        return unknown, trace

    starts = [e for e in events if e.get("type") == "step_start"]
    finishes = [e.get("part") for e in events if e.get("type") == "step_finish"]
    errors = [e for e in events if e.get("type") == "error"]
    tools = {}
    for event in events:
        if event.get("type") != "tool_use":
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        call_id = part.get("callID") or part.get("id")
        if isinstance(call_id, str):
            tools[call_id] = part
    counts = Counter(str(p.get("tool", "unknown")) for p in tools.values())
    settled = [p.get("state") for p in tools.values()
               if isinstance(p.get("state"), dict)]
    if starts:
        trace.update({
            "agent_turns": len(starts),
            "tool_calls": len(tools),
            "tool_results": sum(s.get("status") in ("completed", "error") for s in settled),
            "tool_errors": sum(s.get("status") == "error" for s in settled),
            "tools_by_name": dict(sorted(counts.items())),
            "agent_is_error": bool(errors),
            "agent_subtype": "error_runtime" if errors else None,
        })

    # An incomplete final step_finish means any previous counters undercount
    # the session. Do not equate missing telemetry with free tokens.
    full = bool(starts and len(finishes) == len(starts)
                and all(isinstance(p, dict) for p in finishes))
    trace["trace_complete"] = full and not errors
    if not full:
        return unknown, trace

    fields = {
        "input_tokens": ("input",),
        "output_tokens": ("output",),
        "cache_read_tokens": ("cache", "read"),
        "cache_write_tokens": ("cache", "write"),
    }
    result = {}
    for dest, path in fields.items():
        vals = []
        for part in finishes:
            item = part.get("tokens")
            for name in path:
                item = item.get(name) if isinstance(item, dict) else None
            if type(item) not in (int, float) or item < 0:
                break
            vals.append(item)
        result[dest] = sum(vals) if len(vals) == len(finishes) else None
    # Provider-estimated cost is NOT incremental cash billed under Go plan.
    result["api_cost_usd"] = None
    return result, trace

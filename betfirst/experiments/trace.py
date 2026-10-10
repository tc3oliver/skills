"""Conservative tool-event summary from Claude Code stream-json.

Counts tool_use/tool_result envelopes only. Does NOT infer BET, loss, or
permission denials from model prose. Raw traces remain only in the local run.
"""
from __future__ import annotations

import json
from collections import Counter


def stream_events(data: str) -> list[dict] | None:
    if not data.strip():
        return None
    try:
        single = json.loads(data)
        if isinstance(single, dict):
            return [single]
    except ValueError:
        pass
    try:
        events = [json.loads(line) for line in data.splitlines() if line.strip()]
    except ValueError:
        return None
    if not events or not all(isinstance(x, dict) for x in events):
        return None
    return events


def summarize_trace(data: str, driver: str) -> dict:
    unknown = {
        "trace_complete": False, "tool_calls": None,
        "tool_results": None, "tool_errors": None,
        "permission_denials": None, "tools_by_name": None,
        "bet_attempts": None, "bet_failures": None,
        "failed_bet_overhead_seconds": None,
    }
    if driver != "claude":
        return unknown
    events = stream_events(data)
    if events is None:
        return unknown
    # The terminal result is a distinct object; streaming partial deltas
    # are ignored to avoid counting the same tool call twice.
    final = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if final is None:
        return unknown
    calls: dict[str, str] = {}
    results: dict[str, bool] = {}
    for event in events:
        kind = event.get("type")
        message = event.get("message")
        if kind not in ("assistant", "user") or not isinstance(message, dict):
            continue
        blocks = message.get("content") or []
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if kind == "assistant" and block.get("type") == "tool_use":
                tid = block.get("id")
                if isinstance(tid, str) and tid:
                    calls.setdefault(tid, str(block.get("name", "unknown")))
            if kind == "user" and block.get("type") == "tool_result":
                tid = block.get("tool_use_id")
                if isinstance(tid, str) and tid:
                    results.setdefault(tid, block.get("is_error") is True)
    counts = Counter(calls.values())
    denied = final.get("permission_denials")
    denials = len(denied) if isinstance(denied, list) else None
    return {
        "trace_complete": len(events) > 1,
        "tool_calls": len(calls) if len(events) > 1 else None,
        "tool_results": len(results) if len(events) > 1 else None,
        "tool_errors": sum(results.values()) if len(events) > 1 else None,
        "permission_denials": denials,
        "tools_by_name": dict(sorted(counts.items())) if len(events) > 1 else None,
        # Tool events alone cannot identify a speculative probe versus
        # routine work, or determine whether a decision was a False Bet.
        "bet_attempts": None,
        "bet_failures": None,
        "failed_bet_overhead_seconds": None,
    }

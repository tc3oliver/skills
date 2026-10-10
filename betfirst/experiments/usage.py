"""Extract actual CLI usage; unavailable fields remain None (never assumed zero)."""
from __future__ import annotations
import json

FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "api_cost_usd")


def usage_from_output(data: str, driver: str) -> dict:
    result = dict.fromkeys(FIELDS)
    try:
        if driver == "claude":
            # JSON result (v1) or verbose stream-json with a terminal result.
            try:
                obj = json.loads(data.strip())
            except ValueError:
                events = [json.loads(line) for line in data.splitlines() if line.strip()]
                obj = next((e for e in reversed(events) if
                            isinstance(e, dict) and e.get("type") == "result"), None)
            if not isinstance(obj, dict):
                return result
            usage = obj.get("usage") or {}
            # If the result contains only per-model detail, aggregate each once.
            if not usage and isinstance(obj.get("modelUsage"), dict):
                models = list(obj["modelUsage"].values())
                names = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")
                if models:
                    usage = {name: sum(m[name] for m in models) for name in names
                             if all(isinstance(m, dict) and isinstance(m.get(name), (int, float)) for m in models)}
            alternatives = {
                "input_tokens": ("input_tokens", "inputTokens"),
                "output_tokens": ("output_tokens", "outputTokens"),
                "cache_read_tokens": ("cache_read_input_tokens", "cacheReadInputTokens"),
                "cache_write_tokens": ("cache_creation_input_tokens", "cacheCreationInputTokens"),
            }
            for field, keys in alternatives.items():
                for key in keys:
                    if isinstance(usage.get(key), (int, float)) and not isinstance(usage[key], bool):
                        result[field] = usage[key]
                        break
            cost = obj.get("total_cost_usd")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                result["api_cost_usd"] = cost
        elif driver == "pi":
            events = [json.loads(line) for line in data.splitlines() if line.strip()]
            messages = [e["message"] for e in events if e.get("type") == "message_end"
                        and isinstance(e.get("message"), dict) and e["message"].get("role") == "assistant"]
            name_map = {
                "input_tokens": "input", "output_tokens": "output",
                "cache_read_tokens": "cacheRead", "cache_write_tokens": "cacheWrite",
            }
            for field in FIELDS:
                vals = []
                for msg in messages:
                    usage = msg.get("usage") or {}
                    v = (usage.get("cost") or {}).get("total") if field == "api_cost_usd" else usage.get(name_map[field])
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        vals.append(v)
                if messages and len(vals) == len(messages):
                    result[field] = sum(vals)
    except (ValueError, TypeError, KeyError, AttributeError):
        return dict.fromkeys(FIELDS)
    return result

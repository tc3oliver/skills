"""Generate publication-ready assets from VERIFIED final v3_report data.

Never insert benchmark percentages that were not computed from 108 real runs.
This module has no network calls and only uses Python's standard library.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

URL="https://github.com/tc3oliver/skills/tree/main/betfirst"

def x_post(result:dict)->str:
    """Choose the prespecified factual or balanced template, never cherry-pick."""
    main=result["comparisons"]["betfirst_vs_efficiency"]
    a=result["arm_stats"]["betfirst"]
    b=result["arm_stats"]["efficiency"]
    if main["positive_speedup_claim_gate"]:
        message=(
            "BetFirst v0.2: make cheap bets, win big, lose small.\n\n"
            "In a preregistered 12-task / 108-session local Qwen coding benchmark, "
            f"BetFirst used {main['pooled_wall_time_saving_fraction']:.1%} less wall time "
            f"and {main['gross_tokens_saving_fraction']:.1%} fewer gross tokens "
            f"than Efficiency-only ({a['passed']}/36 vs {b['passed']}/36 completed correctly).\n\n"
            f"Faster on {main['task_median_faster_count']}/12 task medians. "
            "Author-constructed tasks, one local model, observational—not a causal or universal claim."
        )
    else:
        reason=("Mixed or negative task-level results"
                if main["task_median_faster_count"]<9 or main["pooled_wall_time_saving_fraction"]<=0
                else "Insufficient robustness / unequal correctness")
        message=(
            "I shipped BetFirst: a tiny, falsifiable-probe policy for coding agents.\n\n"
            f"Our preregistered 12-task / 108-session Qwen experiment was NOT conclusive: {reason}. "
            f"BetFirst completed {a['passed']}/36 runs versus Efficiency-only {b['passed']}/36, "
            f"and was faster on {main['task_median_faster_count']}/12 task medians.\n\n"
            "We published the full positive AND negative results. No hidden reruns, no v4 gate."
        )
    return (
        "# X launch copy — derived automatically from FINAL v3 report\n\n"
        "This is an editable long-form draft; adjust to X post/thread length before posting. "
        "A full report link and limitations should accompany the numbers.\n\n"
        + message + "\n\nFull methods, task results and Skill: " + URL
        + "\n\nNotes: v1 simple-task overhead and v2 exploratory two-task results are in "
        "betfirst/experiments/EXPERIMENT_HISTORY.md. Do not claim BET causality without trace review.\n"
    )

def plot_svg(result:dict)->str:
    """Static dark high-contrast task-median chart; paths are not interpolated."""
    rows=result["per_task"]
    high=max(max(x["efficiency_median_seconds"],x["betfirst_median_seconds"]) for x in rows)
    if high<=0:raise ValueError("invalid time range for chart")
    left=345
    usable=730
    scale=usable/high
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-label="Task median wall times for Efficiency and BetFirst">',
        '<rect width="1280" height="720" fill="#0b1422"/>',
        '<text x="45" y="58" font-family="system-ui, sans-serif" font-size="29" font-weight="700" fill="#f5f8ff">BetFirst v3 — per-task median duration</text>',
        '<text x="45" y="90" font-family="system-ui, sans-serif" font-size="16" fill="#a8b8cc">12 tasks × 3 repeats each arm · lower is better · observational</text>',
        '<rect x="780" y="43" width="18" height="12" rx="3" fill="#93a5bd"/>',
        '<text x="805" y="55" font-family="system-ui, sans-serif" font-size="15" fill="#c8d3e4">Efficiency</text>',
        '<rect x="945" y="43" width="18" height="12" rx="3" fill="#33d7b9"/>',
        '<text x="970" y="55" font-family="system-ui, sans-serif" font-size="15" fill="#c8d3e4">BetFirst</text>',
    ]
    for i,row in enumerate(rows):
        cy=132+i*43
        cat=escape(str(row["category"]).upper())
        tid=escape(str(row["task_id"]))
        a=row["efficiency_median_seconds"];b=row["betfirst_median_seconds"]
        parts.extend([
            f'<text x="45" y="{cy+8}" font-family="ui-monospace,monospace" font-size="13" fill="#a3b3c7">{cat}</text>',
            f'<text x="147" y="{cy+8}" font-family="system-ui,sans-serif" font-size="15" fill="#f5f8ff">{tid}</text>',
            f'<rect x="{left}" y="{cy-9}" width="{max(1,a*scale):.2f}" height="12" rx="3" fill="#93a5bd"/>',
            f'<rect x="{left}" y="{cy+7}" width="{max(1,b*scale):.2f}" height="12" rx="3" fill="#33d7b9"/>',
            f'<text x="{min(1130,left+a*scale+10):.2f}" y="{cy+1}" font-family="ui-monospace,monospace" font-size="11" fill="#c8d3e4">{a:.1f}s</text>',
            f'<text x="{min(1130,left+b*scale+10):.2f}" y="{cy+18}" font-family="ui-monospace,monospace" font-size="11" fill="#53edd4">{b:.1f}s</text>',
        ])
    parts.append('<text x="45" y="688" font-family="system-ui,sans-serif" font-size="15" fill="#a8b8cc">Full correctness, confidence intervals, negative tasks and limitations in REPORT.md</text>')
    parts.append('</svg>')
    return "\n".join(parts)+"\n"

REVIEW_FIELDS=(
    "task_id","replicate","arm","trace_complete",
    "observed_decision","falsifiable_hypothesis","bounded_probe",
    "probe_executed","probe_outcome","followup_changed",
    "stop_bound_honored","missed_bet","false_bet",
    "permission_denials_confounded","reviewer","evidence_event_ids","notes"
)

def write_assets(result:dict,destination:Path)->None:
    (destination/"X_POST.md").write_text(x_post(result),encoding="utf-8")
    (destination/"task-medians.svg").write_text(plot_svg(result),encoding="utf-8")
    with (destination/"trace-review-worksheet.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows({
            "task_id":t["task_id"],"replicate":rep,"arm":arm,
            "observed_decision":"UNDETERMINED"
        } for t in result["per_task"] for rep in (1,2,3)
          for arm in ("baseline","efficiency","betfirst"))

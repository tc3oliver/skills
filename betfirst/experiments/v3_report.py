#!/usr/bin/env python3
"""Correctness-first final Evaluation v3 report (observational, not causal)."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
ARMS=("baseline","efficiency","betfirst")
CATS=("low","diagnostic","stateful","negative")

def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def compute(run_dir:Path, suite_path:Path, *, bootstrap=2000)->dict:
    manifest=json.loads((run_dir/"manifest.json").read_text(encoding="utf-8"))
    suite=json.loads(suite_path.read_text(encoding="utf-8"))
    if suite.get("schema")!=3 or len(suite.get("tasks",[]))!=12:
        raise ValueError("v3 requires the twelve-task preregistered suite")
    if manifest.get("synthetic") is not False or manifest.get("driver")!="claude":
        raise ValueError("only real completed Claude Agent runs can be published")
    if manifest.get("suite_sha256")!=_sha(suite_path):
        raise ValueError("suite hash differs from frozen manifest")
    if manifest.get("replicates")!=3 or manifest.get("runs")!=108 or manifest.get("schema")!=3:
        raise ValueError("full v3 publication requires 108 runs (12 tasks x 3 arms x 3 reps)")
    tasks={t["id"]:t for t in suite["tasks"]}
    if set(manifest.get("selected_task_ids",[]))!=set(tasks):
        raise ValueError("experiment selected tasks do not match preregistration")
    fixture_hashes=manifest.get("fixture_hashes")
    if not isinstance(fixture_hashes,dict) or set(fixture_hashes)!=set(tasks):
        raise ValueError("fixture hashes missing; no publication")
    from run import hashes
    for tid,task in tasks.items():
        if hashes(suite_path.parent/task["fixture"])!=fixture_hashes[tid]:
            raise ValueError("fixture was changed after experiment: "+tid)
    if manifest.get("claude_tool_profile")!="diagnostic":
        raise ValueError("v3 publication requires one frozen diagnostic tool profile")

    with (run_dir/"measured-runs.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=108:raise ValueError(f"incomplete run: {len(rows)}/108")
    observed={}
    for row in rows:
        tid=row["task_id"];rep=int(row["replicate"]);arm=row["arm"]
        key=(tid,rep,arm)
        if tid not in tasks or rep not in (1,2,3) or arm not in ARMS or key in observed:
            raise ValueError("unexpected or duplicate run: "+str(key))
        if row["passed"] not in ("true","false") or row.get("code_accepted") not in ("true","false") or row.get("session_success") not in ("true","false"):
            raise ValueError("invalid correctness outcome: "+str(key))
        try:
            elapsed=float(row["elapsed_seconds"])
            tokens=[int(row[x]) for x in ("input_tokens","output_tokens","cache_read_tokens","cache_write_tokens")]
            calls=int(row["tool_calls"]) if row.get("tool_calls") not in (None,"") else None
            denials=int(row["permission_denials"]) if row.get("permission_denials") not in (None,"") else None
        except (TypeError,ValueError,KeyError) as exc:raise ValueError("unavailable essential time/token data: "+str(key)) from exc
        if not math.isfinite(elapsed) or elapsed<0 or any(t<0 for t in tokens):
            raise ValueError("invalid time/token quantity")
        observed[key]={
            "passed":row["passed"]=="true",
            "code_accepted":row["code_accepted"]=="true",
            "session_success":row["session_success"]=="true",
            "elapsed_seconds":elapsed,
            "gross_tokens":sum(tokens),
            "tool_calls":calls,"permission_denials":denials,
        }
    expected={(tid,rep,arm) for tid in tasks for rep in (1,2,3) for arm in ARMS}
    if set(observed)!=expected:raise ValueError("missing task/replicate/arm combinations")
    arm_stats={}
    for arm in ARMS:
        group=[observed[(tid,rep,arm)] for tid in tasks for rep in (1,2,3)]
        arm_stats[arm]={
            "runs":len(group),"passed":sum(r["passed"] for r in group),
            "code_accepted":sum(r["code_accepted"] for r in group),
            "session_success":sum(r["session_success"] for r in group),
            "total_seconds":round(sum(r["elapsed_seconds"] for r in group),3),
            "total_gross_tokens":sum(r["gross_tokens"] for r in group),
            "total_tool_calls":sum(r["tool_calls"] for r in group) if all(r["tool_calls"] is not None for r in group) else None,
            "total_permission_denials":sum(r["permission_denials"] for r in group) if all(r["permission_denials"] is not None for r in group) else None,
        }

    per_task=[]
    for tid,task in tasks.items():
        entry={"task_id":tid,"category":task["difficulty"]}
        for arm in ARMS:
            runs=[observed[(tid,rep,arm)] for rep in (1,2,3)]
            entry[arm+"_median_seconds"]=round(statistics.median(r["elapsed_seconds"] for r in runs),3)
            entry[arm+"_total_seconds"]=round(sum(r["elapsed_seconds"] for r in runs),3)
            entry[arm+"_median_tokens"]=statistics.median(r["gross_tokens"] for r in runs)
            entry[arm+"_pass_count"]=sum(r["passed"] for r in runs)
        per_task.append(entry)

    comparisons={}
    for left,right in (("betfirst","efficiency"),("betfirst","baseline"),("efficiency","baseline")):
        ratios=[]; faster=0; win_runs=0; breakdown={}
        for cat in CATS:
            pairs=[r for r in per_task if r["category"]==cat]
            times_left=sum(r[left+"_total_seconds"] for r in pairs)
            times_right=sum(r[right+"_total_seconds"] for r in pairs)
            breakdown[cat]={
                "tasks":len(pairs),
                "time_saving_fraction":1-times_left/times_right if times_right else None,
                "task_medians_faster":sum(r[left+"_median_seconds"]<r[right+"_median_seconds"] for r in pairs),
            }
        for row in per_task:
            if row[right+"_median_seconds"]<=0 or row[left+"_median_seconds"]<=0:
                raise ValueError("cannot estimate task-level log ratio with zero time")
            ratios.append(row[left+"_median_seconds"]/row[right+"_median_seconds"])
            faster+=row[left+"_median_seconds"]<row[right+"_median_seconds"]
            for rep in (1,2,3):
                win_runs+=observed[(row["task_id"],rep,left)]["elapsed_seconds"]<observed[(row["task_id"],rep,right)]["elapsed_seconds"]
        logratios=[math.log(r) for r in ratios]
        geometric=math.exp(statistics.mean(logratios))
        rng=random.Random(20261011)
        samples=sorted(math.exp(sum(logratios[rng.randrange(len(logratios))] for _ in logratios)/len(logratios)) for _ in range(bootstrap))
        ci_ratio=[samples[int(bootstrap*.025)],samples[min(bootstrap-1,int(bootstrap*.975))]]
        # Two-sided exact binomial sign test on distinct tasks, excluding ties.
        non_ties=sum(r!=1 for r in ratios)
        low_wins=min(faster,non_ties-faster)
        sign_p=min(1,2*sum(math.comb(non_ties,j) for j in range(low_wins+1))/(2**non_ties)) if non_ties else 1
        l=arm_stats[left];r=arm_stats[right]
        all_correct=l["passed"]==r["passed"]==36
        savings=1-l["total_seconds"]/r["total_seconds"] if r["total_seconds"] else None
        comparisons[left+"_vs_"+right]={
            "matched_runs":36,"tasks":12,"candidate_passed":l["passed"],"control_passed":r["passed"],
            "same_full_correctness":all_correct,
            "pooled_wall_time_saving_fraction":savings,
            "gross_tokens_saving_fraction":1-l["total_gross_tokens"]/r["total_gross_tokens"] if r["total_gross_tokens"] else None,
            "task_median_faster_count":faster,
            "paired_run_faster_count":win_runs,
            "task_geometric_mean_time_ratio":geometric,
            "task_cluster_bootstrap_ratio_ci_95":ci_ratio,
            "exact_task_sign_test_two_sided_p":sign_p,
            "by_category":breakdown,
            # Prevent promotion of descriptive pilot savings into generalized claims.
            "positive_speedup_claim_gate":bool(all_correct and faster>=9 and savings is not None and savings>=0.15 and ci_ratio[1]<1),
            "inference_note":"Exploratory author-constructed tasks, no causal BET mechanism attribution; task-level bootstrap is descriptive and limited by n=12.",
        }
    primary=comparisons["betfirst_vs_efficiency"]
    release_style=("quantified_exploratory" if primary["positive_speedup_claim_gate"] else
                   "balanced_or_negative")
    return {
        "schema":3, "study_status":"COMPLETE_FINAL_V3" ,
        "publication_ready":True,
        "performance_claim_is_causal":False,
        "model":manifest.get("model"),
        "task_count":12,"replicates":3,"runs":108,
        "suite_sha256":manifest["suite_sha256"],"skill_sha256":manifest.get("skill_sha256"),
        "arm_stats":arm_stats,"per_task":per_task,"comparisons":comparisons,
        "release_style":release_style,
        "release_instruction":"Publish the complete result even if mixed/negative. Never cherry-pick task subsets or rerun until metric is favorable.",
        "limitations":[
            "New tasks were authored by this project, not sourced blindly by an independent third party.",
            "Three replicates per task are observations; cold/warm effects, host load, model randomness may confound.",
            "Confidence interval is a 12-task cluster bootstrap of task-level time ratios, not population-wide causal inference.",
            "Real BET events require independent review; raw tool counts do not label bets.",
            "Local model api_cost_usd is a provider estimate, not actual dollar spend.",
        ],
    }

def render_markdown(result:dict)->str:
    out=["# BetFirst Evaluation v3 — final study","",
         "**Status:** complete 108-run study; observational (not a causal speedup claim).","",
         f"Model: {result['model']}; 12 tasks × 3 arms × 3 repetitions; Skill SHA {result['skill_sha256']}.","",
         "| Arm | Session + code PASS | Time (seconds) | Gross Tokens | Tool calls | Permission denials |",
         "|---|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        s=result["arm_stats"][arm]
        out.append(f"| {arm} | {s['passed']}/36 | {s['total_seconds']:,.1f} | {s['total_gross_tokens']:,} | {s['total_tool_calls'] if s['total_tool_calls'] is not None else 'unknown'} | {s['total_permission_denials'] if s['total_permission_denials'] is not None else 'unknown'} |")
    c=result["comparisons"]["betfirst_vs_efficiency"]
    out.extend(["", "## Primary comparison: BetFirst vs Efficiency", "",
        f"- Pooled time difference: **{c['pooled_wall_time_saving_fraction']:.1%} less time** (descriptive).",
        f"- Gross Tokens: **{c['gross_tokens_saving_fraction']:.1%} less**.",
        f"- Faster task medians: **{c['task_median_faster_count']}/12**; faster matched runs **{c['paired_run_faster_count']}/36**.",
        f"- Task-level geometric time ratio: **{c['task_geometric_mean_time_ratio']:.3f}**; 95% task bootstrap ratio CI **{c['task_cluster_bootstrap_ratio_ci_95'][0]:.3f}–{c['task_cluster_bootstrap_ratio_ci_95'][1]:.3f}**.",
        f"- Exact task sign-test p (descriptive): {c['exact_task_sign_test_two_sided_p']:.4f}.",
        f"- Positive performance-claim gate: **{'MET' if c['positive_speedup_claim_gate'] else 'NOT MET'}**.",
        "", "## Task-level results", "",
        "| Category | Task | Baseline median (s) | Efficiency median (s) | BetFirst median (s) | PASS B/E/BF |",
        "|---|---|---:|---:|---:|---|"])
    for r in result["per_task"]:
        out.append(f"| {r['category']} | {r['task_id']} | {r['baseline_median_seconds']:.1f} | {r['efficiency_median_seconds']:.1f} | {r['betfirst_median_seconds']:.1f} | {r['baseline_pass_count']}/3 / {r['efficiency_pass_count']}/3 / {r['betfirst_pass_count']}/3 |")
    out.extend(["","## Limitations and interpretation",""])
    out.extend("- "+item for item in result["limitations"])
    out.extend(["","BET behavior attribution requires independent trace labeling; do not state that observed gains were *caused* by successful BET probes.","",
      "**Publication policy:** release this complete dataset whether the result is positive, mixed or negative. No extra v4 validation gate.",""])
    return "\n".join(out)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir",type=Path)
    parser.add_argument("--suite",type=Path,default=HERE/"suite-v3.json")
    parser.add_argument("--output",type=Path,help="New report directory, never overwrite original runs")
    args=parser.parse_args()
    result=compute(args.run_dir.resolve(),args.suite.resolve())
    target=args.output or (args.run_dir/"v3-publication-report")
    if target.exists():raise SystemExit("refusing to overwrite existing publication report directory")
    target.mkdir(parents=True)
    (target/"result.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (target/"REPORT.md").write_text(render_markdown(result),encoding="utf-8")
    from v3_publication import write_assets
    write_assets(result,target)
    with (target/"per-task.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(result["per_task"][0]))
        writer.writeheader();writer.writerows(result["per_task"])
    print(json.dumps({"report_directory":str(target),"release_style":result["release_style"],
                      "positive_speedup_claim_gate":result["comparisons"]["betfirst_vs_efficiency"]["positive_speedup_claim_gate"],
                      "runs":108},indent=2))

if __name__=="__main__":main()

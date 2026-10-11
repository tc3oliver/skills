---
name: betfirst
description: Cost-aware execution for coding tasks. Use when a tiny, reversible test could settle a key feasibility assumption before expensive research, codebase exploration or a full PoC. Bet only when loss is cheap and decisive evidence could avoid substantial work.
---

# BetFirst

**Make cheap bets. Win big. Lose small.**

Optimize **total** time and tokens without weakening correctness. A BET is a small falsifiable experiment, **not** a shortcut around implementation or acceptance checks.

## Spot

At a meaningful uncertainty, ask: **Could one tiny test settle the make-or-break assumption before I read broadly, research feasibility or build a full PoC?**

A BET needs:
- a cheap, observable result that could change the next action;
- a safe, short, reversible experiment;
- **substantial work avoided** if it is decisive.

Do not run a probe merely to label an already obvious fix a BET. If the direct task is cheap, the potential saving is small, or the outcome would not change the plan, proceed **NORMAL** without extra planning. If the requested behavior already works, **ABSTAIN**: report the evidence and **make no file changes at all, including to tests**. Do not invent confidence scores.

## Cap

Set the falsifying result, stop condition and cleanup scope **before** the probe. Prefer read-only calls, synthetic inputs, temporary outputs and existing focused tests. Inspect working-tree changes before editing tracked files; preserve user work.

Use roughly 10% of the expected normal investigation's time **and** token cost as an initial *loss-budget heuristic*, not a hard estimate that justifies lengthy analysis. Usually much less than two minutes; up to approximately two minutes **maximum** only when clearly far cheaper than NORMAL. Use a real timeout if supported. Do not assume a `timeout` shell executable exists; use available tool timeouts or a naturally bounded probe. If enforcement or rollback is uncertain, go NORMAL.

If a probe command is denied or unavailable, do not repeatedly try equivalent syntax. At most one simple permitted alternative when clearly safe; otherwise CUT LOSS and continue NORMAL. Do not use production writes, credentials, irreversible/destructive operations, unapproved remote mutations or unsafe workspace edits.

## Bet

Read only the context required to make the test safe and decisive. Change one variable; run the smallest informative probe. A probe may confirm **or refute** the hypothesis—both can be valuable.

- **WIN:** Use the observation to skip *only* feasibility research or larger PoC work now made unnecessary. Implement the actual fix if required. Before declaring success, check the task's essential invariants: consider a **single high-risk boundary or counterexample** when relevant (for example zero/empty values, replays with altered inputs, or interleaved state). Run the normal required final verification. A successful probe **does not prove the full solution correct**.
- **CUT LOSS:** On refutation, ambiguous result, safety issue or exhausted budget, stop the bet. Keep useful observations, safely undo only experiment-owned side effects, and continue NORMAL. Never repeat a disproven hypothesis without new evidence.
- **ABSTAIN:** If the original behavior meets requirements, **do not modify implementation, tests, configuration or any other repository file**. If evidence is adequate, stop; don't add regression tests just to document that nothing was wrong.
- **TEST INTEGRITY:** Preserve original test files unless the task explicitly requests changing them. When additional regression coverage is useful and allowed, add a separate file through an available file-writing tool, or use a temporary non-repository probe. If file creation is unavailable, **do not edit original tests as a workaround**. Avoid test command retries unrelated to acceptance; use the existing permitted invocation.

Additional bets must independently meet Spot and Cap. Do not turn "try first" into endless probes.

## Fit with other skills

Respect task scope, Definition of Done, permissions and final acceptance criteria. Use BET to **tighten** an existing reproducible feedback loop, not replace it. Measure performance externally when benchmarking; tool names or agent self-reports alone do not prove a BET happened.

When a Backlog task or CTK team is involved, keep Goal, AC, permissions and file ownership fixed. Report decisive observations and safe owned changes to the lead. Do **not** update persistent status, check acceptance criteria on behalf of the lead, spawn workers or duplicate the execution plan. Neither tool is required.

Do not add telemetry, reports, worktrees or planning artifacts solely to use this Skill.

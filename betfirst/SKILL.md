---
name: betfirst
description: Cost-aware execution for coding tasks. Use when a tiny, reversible probe might resolve an uncertainty before expensive debugging, codebase exploration, or implementation. Bet only when failure is cheap and success avoids substantial work.
---

# BetFirst

**Make cheap bets. Win big. Lose small.**

Optimize **total** time and token use at the same task scope and correctness bar. A BET is a small falsifiable experiment, not an unverified fix.

## Spot

At a meaningful uncertainty, look for a concrete hypothesis with:
- a cheap observable pass/fail signal;
- a safe, bounded way to test it;
- substantial investigation avoided if it succeeds.

If the upside is not clearly larger than the possible loss, proceed **NORMAL**. If no change is needed, **ABSTAIN**. Do not force a bet or invent confidence percentages.

## Cap

Before acting, identify the falsifying result, the stop condition, and how to remove **only** experiment-owned effects. Prefer read-only probes, temporary files, and existing focused tests. Before editing tracked files, inspect working-tree changes and protect user work.

Use roughly 10% of the likely normal investigation's time **and** token cost as an initial *loss-budget heuristic*, not a hard estimate that justifies more planning. If cost, rollback, or safety is uncertain, go NORMAL.

Prefer read-only probes over existing artifacts: a cheap refutation can invalidate a plan before any edit. A BET must have a credible short bound (up to about 2 minutes **at most**, usually less and well below the normal investigation cost). Where supported, set an actual tool timeout. If a command may hang without an enforceable stop, or needs a full pipeline or several live calls, split the probe or go NORMAL. One short, safe model call is still a BET when it meets the same cost and rollback gates; do not classify work by tool name alone.

Do not bet with production state, credentials, irreversible/destructive operations, remote writes, or unapproved side effects. Existing permission boundaries still apply.

## Bet

Read only the context required for a safe probe. Change one variable; run the smallest decisive test with a short timeout when supported.

- **DECISIVE PROBE:** A confirmed **or disproved** hypothesis can give useful evidence. Choose the next action from the observation, not from whether the original guess was right. Still count probe cost and preserve final validation.
- **WIN:** Keep evidence-backed changes, skip investigation made unnecessary by the result, then satisfy the task's normal acceptance criteria and final verification.
- **CUT LOSS:** On falsification, inconclusive output, loss-budget exhaustion, or unsafe behavior, stop immediately. Preserve the observation, revert only owned effects when safe, and continue NORMAL using the new evidence.
- Do not repeat a failed hypothesis without materially new evidence. Additional bets must independently pass Spot and Cap.

## Fit with other skills

Respect the repository's task scope, Definition of Done, and testing requirements. When a debugging skill requires a reproducible feedback loop, use BET to **tighten that loop**, not bypass it. Never trade correctness for a faster-looking answer.

Do not add telemetry, reports, worktrees, or planning artifacts merely to run this skill. Measure performance externally when benchmarking is explicitly requested.

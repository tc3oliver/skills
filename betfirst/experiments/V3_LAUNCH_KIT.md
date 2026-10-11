# BetFirst launch kit — after v3

Draft templates are **not an authorization to fabricate future results**. Fill v3 values only from the completed 108-session result.json. Do not silently promote v2's two-task gains to a general benchmark headline.

## Release checklist

- [ ] Final v3_report.py succeeds and validates 108 real sessions, task matrix and suite/fixture SHA.
- [ ] Full REPORT.md, per-task.csv and anonymized summary published, including failures and negative tasks.
- [ ] Public instructions and repository installation verified for current v0.2.
- [ ] Publish model, hardware, runtime and sampling details; distinguish task count from 108 sessions.
- [ ] Private traces audited for credentials, paths and proprietary code before excerpting.
- [ ] Mechanistic BET claims ONLY if externally annotated traces support them.
- [ ] v1 negative simple-task result and v2 preliminary positive diagnosis results clearly separated.
- [ ] Publication happens after this study even if positive performance-claim gate is NOT met.

## Safe pre-v3 general-purpose X post

I built BetFirst: a small, open-source decision-policy Skill for coding agents.

Before an expensive debugging rabbit hole: can a tiny, reversible, falsifiable probe settle the uncertainty?

If yes, bet small and observe. If not, work normally. If the probe fails, stop.

Skill + reproducible evaluation: https://github.com/tc3oliver/skills/tree/main/betfirst

## Positive gate met (AFTER final v3 report only)

BetFirst v0.2: tiny bets, less wasted agent work.

In our 12-task / 108-session local Qwen coding benchmark, BetFirst used [X]% less elapsed time and [Y]% fewer gross tokens than Efficiency-only at [N]/36 vs [M]/36 successes.

Faster on [K]/12 task medians. Results include simple fixes, complex recovery and no-change tasks.

Observational, not causal or universal. Full tasks, failures and methods: [LINK]

Use v3_report.py fields, including the task bootstrap confidence interval. Never use this positive version if the preregistered gate fails.

## Mixed/negative study (AFTER final v3 report)

I shipped BetFirst: a small Skill for cheap, falsifiable probes before expensive coding-agent investigation.

I also ran a preregistered 12-task / 108-session local Qwen study. The result was [MIXED / NO ADVANTAGE / NEGATIVE], particularly on [CATEGORY].

All task-level results, slow runs and failures are public. The real question: *when is a small probe worth its cost?*

Skill + study: [LINK]

## Technical thread and media

1. Motivation and strategy: SPOT > CAP > BET > WIN or CUT LOSS, with legitimate NORMAL/ABSTAIN.
2. Task matrix, same baseline/Efficiency/BetFirst agent and permissions.
3. Full quality table and by-category differences, not an unqualified speedup maximum.
4. 12-task per-task median comparison; confidence interval and failure cases.
5. Mechanistic probe example only if observed directly in a reviewed trace.
6. Explain local oMLX and limitations, public reproducible methodology.
7. Try it: npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y.

Charts should be generated from actual per-task.csv after the live run. No mock or made-up benchmark plots.


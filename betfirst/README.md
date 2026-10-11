<p align="center"><a href="./README.md">English</a> · <a href="./README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="./assets/hero.svg" alt="BetFirst — Make Cheap Bets. Win Big. Lose Small. Bet on hypotheses, never on correctness." width="1000">
</p>

# BetFirst

### Make Cheap Bets. Win Big. Lose Small.

**Your coding agent is already making bets.** Every suspected root cause, every file it chooses to read, every fix it tries is a bet that the next step will be worth the cost.

**BetFirst teaches it to bet smarter.**

Instead of spending a long session chasing a hunch, look for a **small, falsifiable, reversible experiment** that could settle the question first.

| **WIN BIG** | **LOSE SMALL** | **KNOW WHEN TO FOLD** |
| :--- | :--- | :--- |
| A tiny probe eliminates an expensive wrong path. | A failed probe has a clear stopping point and safe fallback. | No good bet? Work normally. Already correct? Don't touch it. |

**Bet on hypotheses. Never on correctness.**

Claude Code · Pi · Portable Agent Skill · Experimental v0.2 · No additional runtime

## Place your first bet in 30 seconds

**Install with the Agent Skills CLI:**

~~~bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
~~~

Then give your agent a task:

~~~text
Use BetFirst. Before investigating broadly, look for one cheap,
falsifiable, reversible bet that could resolve the uncertainty.
Define what would disprove it and when to stop. If no good bet
exists, work normally. Preserve my changes and run final checks.
~~~

**Claude Code plugin instead?** Run `/plugin marketplace add tc3oliver/skills`, then `/plugin install tc3oliver-skills`, and invoke `/tc3oliver-skills:betfirst`. Choose **one** installation method to avoid duplicate Skills.

## A better way to lose

Most coding-agent workflows talk about successful experiments. **BetFirst is designed for the losing ones, too.** The important question isn't whether a hypothesis was right. It's whether you learned something useful **before the investigation became expensive**.

<p align="center">
  <img src="./assets/probe-loop.gif" width="760" alt="Illustrative workflow animation showing broad exploration compared with BetFirst's shorter bounded probe, learning and verification path. Not an actual model trace or benchmark.">
</p>

<sub>Conceptual animation—not a recorded session or measured speedup. [Static comparison →](./assets/before-after.svg)</sub>

### The bet: one hypothesis, two outcomes

*Illustrative example, not a benchmark trace.*

~~~text
BUG         Subtitle rendering fails on Windows drive paths.
HYPOTHESIS  The drive-colon escaping is wrong.
BET         Try ONE representative path in an isolated filter call.

WIN         The probe confirms the hypothesis → fix the escaping,
            then run the required renderer/regression checks.

LOSE        The probe disproves it → stop pursuing that theory,
            keep the evidence, investigate the next likely cause.
~~~

**A losing bet isn't a failed task.** A cheap refutation can save you from implementing the wrong fix. A winning bet doesn't let you skip verification.

## Know when to bet. Know when to fold.

**SPOT → CAP → BET → WIN / CUT LOSS**

| Decision | What the agent does |
| --- | --- |
| **SPOT** | Identify a specific uncertainty worth testing, not just a vague guess. |
| **CAP** | Set a small time/cost bound, observable outcome and safe exit *before* running the probe. |
| **BET** | Run the smallest reversible test that can falsify the hypothesis. |
| **WIN** | Use decisive evidence to avoid unnecessary exploration; finish with normal correctness checks. |
| **CUT LOSS / FOLD** | Stop when the hypothesis fails or the bet becomes inconclusive; preserve evidence and return to normal debugging. |
| **NORMAL / ABSTAIN** | Don't force a bet. Investigate normally, or leave already-correct code alone. |

**The guardrail:** No production mutations, destructive Git cleanup, credentials, unbounded experiments or skipped acceptance tests. BetFirst is a decision policy—not a license to gamble with user data or ship unverified code.

[See the complete decision flow →](./assets/decision-flow.svg) · [Why this approach makes sense →](./docs/WHY_BETFIRST.md)

## Small Skill. No new infrastructure.

**Claude Code:** Use the CLI or plugin setup above. Invoke explicitly or let a compatible Skill-discovery mechanism find it.

**Pi:** Install the complete `betfirst/` directory in a location your Pi version discovers (for example `~/.pi/agent/skills/betfirst/`), then use `/skill:betfirst`. The core [`SKILL.md`](./SKILL.md) is portable and has no Claude-only runtime dependencies.

**Other compatible coding agents:** Load the portable Skill as instructions; automatic discovery depends on your agent. BetFirst can run independently of Backlog, Claude Team Kit and task-management frameworks.

## Does betting first actually pay off?

**Sometimes yes. Sometimes no—and that's the point.** In early local Qwen/oMLX tests, BetFirst was **slower on three simple tasks**. But on **two diagnostic tasks, each repeated three times**, it used **33.8% less wall time** and **38.0% fewer gross tokens** than Efficiency-only; both completed **6/6** successfully.

These are **exploratory observations**, **not** a universal or causal speedup claim. A larger preregistered **12-task / 108-session v3** study is underway; **results are pending**, and wins *and* losses will be published.

[Full experiment history →](./experiments/EXPERIMENT_HISTORY.md) · [v3 protocol →](./experiments/V3_PROTOCOL.md)

## Make your agent a better bettor

Install BetFirst, bring one real debugging task, and see whether a small bet can buy a decisive answer. **Win big when the evidence is there. Lose small when it isn't.**

[Decision examples](./references/examples.md) · [Evaluation protocol](./evals/README.md) · [Source Skill](./SKILL.md) · [Changelog](./CHANGELOG.md)

**Make Cheap Bets. Win Big. Lose Small.**

MIT License.

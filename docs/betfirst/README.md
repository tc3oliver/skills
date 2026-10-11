<p align="right"><a href="./README.zh-TW.md">繁體中文</a> · English</p>

# BetFirst

**Make Cheap Bets. Win Big. Lose Small.**

**ALL IN? On an assumption you haven't tested?**

Your coding agent reads docs, digs into the source, compares approaches and builds a PoC… then discovers the original assumption was wrong.

**What if one tiny test could have told you that first?**

BetFirst helps your agent find a small, safe, falsifiable experiment *when it's worth the effort*. If it works, skip the preparation you no longer need. If it fails, stop and investigate normally. If a direct fix is obvious, just fix it.

<p align="center">
  <a href="../../media/betfirst/assets/betfirst-promo.mp4"><img src="../../media/betfirst/assets/betfirst-promo.gif" alt="BetFirst: test the make-or-break assumption before the expensive investigation." width="900"></a>
</p>

<p align="center"><a href="../../media/betfirst/assets/betfirst-promo.mp4">Watch the full video ↗</a></p>

## Get started

**Ask your coding agent to install it:**

```text
Install BetFirst for my coding agent. Follow https://github.com/tc3oliver/skills/blob/main/docs/betfirst/agent-install.md, detect my agent and existing installation, install only the BetFirst Skill, and verify it works.
```

**Or install with the Agent Skills CLI** (select your agent and scope):

```bash
npx skills add tc3oliver/skills --skill betfirst
```

[Agent installation guide](./agent-install.md) · [View the Skill](../../betfirst/SKILL.md)

## How it works

| NORMAL — default | BET — when worthwhile | ABSTAIN — already correct |
| --- | --- | --- |
| The fix is clear? Do it. | One small test could avoid a big investigation? Try it once, with a stop condition. | Requirements already hold? Show evidence and leave the code alone. |

The bet is **never** a substitute for implementation or final verification.


### Why make a bet at all?

There's a simple rule behind it: **only bet when the expected time saved outweighs the time you might waste.**

$$
pS > (1-p)L + H
$$

Here, \(p\) is an *observed* success rate for comparable tasks, \(S\) is the work a successful probe avoids, \(L\) is the cost of a failed probe, and \(H\) is the overhead of making the bet. No reliable estimate? Don't force one. [The reasoning behind BetFirst →](./WHY_BETFIRST.md)


### The subtitle-path example

Need to know whether a subtitle filter accepts an unusual file path? Before constructing a full rendering pipeline, try one synthetic path with one minimal filter call. If it works, proceed with the real change. If it fails, keep the error and investigate the right fix.

**Bet on the uncertainty, not the correctness of the whole solution.**

<p align="center">
  <img src="../../media/betfirst/assets/before-after.svg" alt="Conceptual comparison of lengthy feasibility work and a bounded initial test." width="900">
</p>

[More examples](./examples.md) · [Decision flow](../../media/betfirst/assets/decision-flow.svg)

## Does it actually help?

Across two local synthetic-task studies (**126 Muse agent executions**), BetFirst v0.4 reduced observed wall time against the tested controls. In the follow-up study, wall time was **17.9% lower than Efficiency** and **18.0% lower than No-BET** among **22 paired comparisons in which both agents passed**.

Those figures are local measurements, not a universal speedup guarantee. Earlier versions lost time on easy tasks; token coverage was incomplete. The methodology and negative results are published alongside the wins.

[Full benchmark results and limitations](../../research/betfirst/experiments/V04_RELEASE_RESULTS.md) · [Experiment history](../../research/betfirst/experiments/EXPERIMENT_HISTORY.md)

## Works with your agent

BetFirst is a portable, instruction-only Agent Skill. Compatible agents include Claude Code, Pi and OpenCode; discovery and invocation vary by agent. There's no extra runtime or agent orchestration to adopt, and it works independently of [Backlog](../../backlog/SKILL.md) or [Claude Team Kit](https://github.com/tc3oliver/claude-team-kit).

Prefer Claude Code's plugin system? Use `/plugin marketplace add tc3oliver/skills`, then `/plugin install tc3oliver-skills`. Choose the plugin **or** the standalone Skill to avoid duplicate installations.

---

**Make Cheap Bets. Win Big. Lose Small.** · [Install BetFirst](#get-started)

MIT License.

# Why bet before the feasibility deep dive?

BetFirst is about the **value of information**, not a bet on software quality. Sometimes a coding agent spends a long time reading documentation, exploring a codebase and building a full proof of concept before checking a single make-or-break assumption. **If a tiny, safe experiment can answer that question first, the rest of the preliminary feasibility work may no longer be necessary.**

The micro-experiment can itself be a *small PoC*. BetFirst is not "never research" or "never make a PoC"; it's a decision policy for **whether a low-risk direct test is a better first investment**. If no such test exists, investigate normally. Finishing the actual implementation and acceptance tests is non-negotiable.

A WIN means a probe produces decisive, usable evidence that avoids preparation no longer needed. A LOSE means its hypothesis failed or the result was inconclusive and the Agent stopped within the prior loss budget. Even a decisive refutation can be useful evidence; it never justifies unbounded retrying.

## The tradeoff

Exploration costs time and tokens: reading many files, running full test suites, following speculative dependencies, and retrying failed tools. A bounded experiment can buy objective information sooner, but it also introduces overhead. When a question is already settled, the correct choice is **NORMAL** (work normally) or **ABSTAIN** (no change needed).

For any **single resource**, a simple expected-saving model is:

$$
E[\mathrm{saved}] = pS - (1-p)L - H
$$

The bet breaks even when:

$$
p > \frac{L+H}{S+L}
$$

- `p` is an observed success rate in a comparable task class, never a fabricated model confidence.
- `S` is what a decisive probe avoids compared with ordinary execution.
- `L` is what a failed probe adds, including cleanup and safe fallback.
- `H` is the overhead of considering and making the bet.

For illustration only, if a success saves nine minutes and failure loses one minute, with decision overhead already included, break-even is 10%. This hypothetical example is **not** a BetFirst measurement. Time, tokens, and money are distinct resources: a shorter session can still consume more tokens.

## The stop-loss rule

A useful BET has a cheap observable outcome, a clear stop condition, and a safe path back. Prefer read-only checks, single-variable reproductions and existing narrow tests. Never use destructive Git cleanup, production mutations, unapproved remote writes or exposed credentials as speculative bets. The regular acceptance criteria still apply.

## Relation to research

The design draws on rational metareasoning and cost-aware exploration, especially the idea that additional computation is only worth its opportunity cost when it changes a decision. Related work motivates the policy but is **not** evidence that BetFirst itself causes speedups.

- Russell & Wefald, *Principles of Metareasoning* (1991): https://doi.org/10.1016/0004-3702(91)90015-C
- *Calibrate-Then-Act: Cost-Aware Exploration in LLM Agents* (2026): https://arxiv.org/abs/2602.16699
- *Analyzing and Mitigating Cost-Inefficient Behaviors in Coding Agents* (2026): https://arxiv.org/abs/2609.30725

See [the experimental record](../../research/betfirst/experiments/EXPERIMENT_HISTORY.md), including negative cases, for actual BetFirst observations. Those studies cannot establish a general causal speedup.

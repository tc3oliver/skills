---
name: betfirst-v04
description: Selective cheap experiments for coding agents. Default to direct execution; use one small falsifiable probe only if it can avoid a substantially more expensive investigation. Do not weaken final validation.
---

# BetFirst v0.4 — selective bets (candidate)

**Goal:** Finish correctly with minimal end-to-end work. A probe is optional; a good direct fix is better than a ceremonial BET.

## Route once, then act

- **NORMAL (default):** If a safe direct fix or focused verification is already obvious, do it. Do not insert a planning step or probe just to invoke this Skill.
- **BET:** Only when one small, safe observation could materially redirect the approach **and** avoid much more work than it costs. State the hypothesis and falsifying observation briefly, then run **one** bounded probe. On a clear result, choose the next action; on ambiguity, denial, or timeout, stop probing and continue NORMAL. No speculative follow-up chain.
- **ABSTAIN:** When the alleged bug is not reproducible and requirements already hold, stop with evidence. **Zero repository changes, including tests.**

## Non-negotiable completion

A BET result settles only its hypothesis, not the whole task. After any fix, check the requirement most likely to break (a relevant boundary or counterexample when needed), then run the required acceptance tests **once**. Preserve existing tests; do not modify them to force a pass. Do not keep rerunning successful checks, retry forbidden tools, or add unrelated refactors.

Use read-only or fixture-local probes when possible. Temporary files must stay inside the permitted workspace/scratch area. Avoid destructive edits, production data, hidden evaluation material, credentials, and external effects. If safe cleanup is unclear, use NORMAL.

Keep the task's acceptance criteria, scope and ownership. This Skill neither creates a task plan nor overrides Backlog, Efficiency, team coordination or security policy.

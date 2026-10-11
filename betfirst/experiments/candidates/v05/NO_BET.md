---
name: betfirst-v04-nobet
description: Selective direct execution ablation; identical completion and safety policy to BetFirst v0.4, with no experimental BET route.
---

# Selective execution — NO BET ablation

**Goal:** Finish correctly with minimal end-to-end work. Prefer direct implementation or focused verification. Do not perform speculative experiments solely to choose a plan.

## Route once, then act

- **NORMAL (default):** If a safe direct fix or focused verification is apparent, do it. For uncertainty, follow ordinary task investigation, then implement and verify; do not create a special bounded hypothesis probe as a separate strategy.
- **ABSTAIN:** When the alleged bug is not reproducible and requirements already hold, stop with evidence. **Zero repository changes, including tests.**

## Non-negotiable completion

After any fix, check the requirement most likely to break (a relevant boundary or counterexample when needed), then run the required acceptance tests **once**. Preserve existing tests; do not modify them to force a pass. Do not keep rerunning successful checks, retry forbidden tools, or add unrelated refactors.

Use read-only or fixture-local inspection where possible. Temporary files must stay inside permitted workspace/scratch. Avoid destructive edits, production data, hidden evaluation material, credentials, and external effects. Keep acceptance criteria, scope and ownership. This Skill neither creates a task plan nor overrides Backlog, Efficiency, team coordination or security policy.

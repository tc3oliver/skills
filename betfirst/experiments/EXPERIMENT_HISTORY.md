# BetFirst experiment history

Historical figures are provided by the owner from Qwen3.8-27B-oQ4e-mtp through Claude Code + oMLX on M4 Max 64GB. This is an owner-reported study record; private raw traces are not in the repository. **Not evidence that BetFirst yields universal or causal acceleration.**

## v1: low-uncertainty pilot

Three simple tasks, three arms, one repeat (nine sessions); initial visible acceptance passed 9/9. BetFirst versus Efficiency was **37.1% slower** and used about **69.6% more gross tokens**. This is a negative result for always-on decision overhead in simple tasks, not to be suppressed from the release narrative.

## v2: restricted six-session exploratory diagnosis

Two tasks (config-scope, render-resume), three arms and one repeat. Original grading marked all but two FAIL due to rejection of added regression tests. A corrected additive-only test rubric restored three results: 5/6 session successes; Baseline render-resume remained FAIL due to error_max_turns although code and Oracle were accepted. The restricted Bash policy caused unequal permission-denied retries across arms. Do not interpret these runs as clean speed evidence.

## v2: diagnostic-profile eighteen-session replication

Two tasks x three arms x three repeats = 18 live sessions. The first grading yielded 17/18; one Efficiency run added test_tenant_isolation.py and inert tests/__init__.py, classified as tampering. Versioned post-run grading fixed this without model reruns; final result **18/18 PASS**, with Fixture Hash verification.

BetFirst vs Efficiency, six matched pairs: **33.8% lower total elapsed time**, **38.0% fewer gross tokens**, tools **81 vs 106**, and **6/6 matched-run faster outcomes**. Every arm passed 6/6. BetFirst vs Baseline: **43.6% lower total wall time**, **48.4% fewer gross tokens**, tools 81 vs 110; faster in 5/6 matched pairs. Per task, BetFirst vs Efficiency wall time was about 31.8% lower for config-scope and 35.7% lower for render-resume.

There were only **two distinct diagnosis tasks**, each repeated. Fixture selection occurred while developing the Skill, so neither a broad population improvement nor a causal BET mechanism is proved. Local API cost values are provider estimates, not cash costs.

## v3: new-task final launch study

Twelve newly authored coding tasks and 108 real sessions are planned. As committed, **v3 has not yet run**. See V3_PROTOCOL.md. BetFirst v0.2 is frozen. We commit to release results whether positive or negative, with no mandatory v4.

## v0.4 release follow-up (2026-10-11)

Two held-out synthetic-task Muse studies, 54 and 72 sessions, were completed. See [release report](./V04_RELEASE_RESULTS.md) for PASS rates, matched comparisons, ambiguous cases, and missing telemetry. The earlier v3 protocol remains historical and is not misrepresented as newly run.

## Limitations retained across versions

Tasks and repeated sessions must not be conflated. Host load, warm/cold behavior, permission profiles, model stochasticity and coding-agent state may confound timing. SDK tool-use events are not validated BET events. External oracles are not a malicious-agent sandbox. No independent third-party task corpus or cross-model study has been performed.


# Skill Architecture

Read this when changing Skill boundaries, invocation behavior,
routing architecture, or workflow decomposition.

## Two Loads

Every architectural decision trades two costs.

### Context Load

Material the Agent must continuously carry, such as:

- Skill descriptions
- always-loaded instructions
- routing pointers

### Cognitive Load

Material the human must remember, such as:

- Skill names
- manual invocation
- workflow ordering

Do not optimize one by blindly increasing the other.

## Invocation

Prefer model invocation when:

- the Agent must discover the Skill autonomously, or
- another Skill must be able to reach it

Prefer user invocation when:

- a human naturally chooses the exact execution moment
- automatic discovery adds little value
- side effects should remain deliberate

Invocation controls are runtime-specific. Preserve portable Skill
content and use harness-specific metadata only when required.

## Splitting

A multi-step workflow is not inherently multiple Skills.

### Split by Sequence

Consider separating phases when later visible work repeatedly causes
premature completion of the current phase.

Before splitting:

1. strengthen the current phase's completion criterion
2. verify that premature completion still occurs

A useful sequence split keeps later instructions out of view until
the current phase is complete.

A fresh session or subagent can provide stronger isolation, but is
not required merely to create a Skill boundary.

### Split by Invocation

Consider a separate Skill when a capability has:

- a distinct trigger
- independent user intent
- independent reuse
- a reason to be discovered on its own

Each additional model-discoverable Skill adds routing context, so the
independent invocation must justify the cost.

### Branches

When only some executions need additional material, prefer a
conditional reference over another Skill.

## Router

When many manual Skills create excessive cognitive load, a router can
help users choose the correct Skill.

Do not build a router merely because several Skills exist.

## Decision

Prefer the smallest architecture that preserves:

- clear routing
- coherent work
- reliable completion
- appropriate information visibility

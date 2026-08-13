---
name: skill-optimizer
description: Optimize an existing Agent Skill for routing accuracy, context efficiency, execution reliability, and maintainability. Use when reviewing, simplifying, or refactoring a SKILL.md or Skill package.
---

# Skill Optimizer

Improve the target Skill while preserving its intended capability.

Optimize for behavioral signal, not minimum length.

## Inspect

Before editing:

1. Read the target `SKILL.md`.
2. Inspect the Skill's file structure and referenced resources.
3. Inspect runtime-specific metadata when present.
4. Identify:
   - intended outcome
   - trigger conditions
   - required behavior
   - completion conditions

Do not load every reference blindly. Follow pointers unless the
reference structure itself is under review.

## Core Pass

### 1. Routing

Check that the description:

- states what the Skill does
- states when it should trigger
- is distinguishable from neighboring Skills
- front-loads the most important trigger concepts
- does not repeat body implementation details

If invocation strategy or overlapping Skills are involved,
read `references/architecture.md`.

### 2. Pruning

For each instruction ask:

> Does this materially change behavior relative to the model's default?

If no, remove it.

Remove:

- generic knowledge the model already knows
- vague exhortations
- stale instructions
- duplicated meanings
- repository facts that are reliably and cheaply discoverable

Preserve:

- non-obvious constraints
- unwritten conventions
- reasons behind decisions
- failure patterns
- gotchas the environment does not reveal

Treat repository files, configuration, CLI help, and source code as
sources of truth. Duplicate them only when the lookup cost justifies
the cache.

### 3. Information Hierarchy

Keep in `SKILL.md`:

- steps required on most runs
- rules required before action
- critical gotchas the Agent may not know how to discover

Move behind explicit pointers:

- branch-specific detail
- large conditional reference
- material needed only for uncommon cases

Every disclosed reference must state when it should be loaded.

Do not create references merely to shorten `SKILL.md`.

### 4. Instructions

Prefer:

- concrete procedures over slogans
- clear defaults over menus
- explicit inputs and outputs where useful
- freedom when variation is harmless
- strict instructions where sequence or correctness is fragile

If the Skill remains repetitive, verbose, or heavily negative after
normal pruning, read `references/steering.md`.

### 5. Workflow

Multiple steps are not themselves a reason to split a Skill.

Keep a workflow together when its steps form one coherent outcome
and benefit from shared working context.

If later steps appear to reduce the quality of earlier work, or the
Skill mixes distinct triggers or responsibilities, read
`references/architecture.md`.

### 6. Completion and Validation

Important phases must have observable completion conditions.

Prefer evidence such as:

- tests
- builds
- validators
- exit status
- expected artifacts
- reproducible observations

Use:

work → validate → correct → validate

when objective validation is available.

### 7. Resources

Recommend a script only when the operation is:

- deterministic, and
- repeated, complex, error-prone, or dependent on external tooling

Do not replace straightforward Agent reasoning with unnecessary scripts.

## Final Gate

Before finishing, verify:

- frontmatter still parses and every referenced file path still resolves
- intended capability is preserved
- routing has clear scope and boundaries
- retained instructions materially affect behavior
- cheap environment lookups are not unnecessarily cached
- critical gotchas remain visible before they are needed
- conditional material is disclosed behind precise pointers
- important completion conditions are observable
- no unnecessary files or abstractions were introduced

If routing or mandatory behavior changed, identify positive,
negative, and behavioral eval cases that should validate the change.

Return the optimized Skill and only material structural changes.

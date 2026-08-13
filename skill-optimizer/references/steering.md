# Skill Steering

Read this when instructions remain repetitive, weak, verbose,
or heavily phrased as prohibitions after normal pruning.

## Leading Words

Look for several instructions that express the same behavioral concept.

Prefer a compact concept already well represented in the model's
existing vocabulary when it carries the intended behavior reliably.

Good candidates:

- already appear in normal engineering language
- match vocabulary used by users or the repository
- replace repeated explanation
- sharpen a fuzzy completion state

Do not invent jargon merely to reduce tokens.

A leading word may be useful in:

- execution instructions
- completion gates
- Skill descriptions and routing pointers

When used for routing, place the strongest trigger concept early.

## Positive Steering

Prefer stating the desired behavior directly.

Instead of activating an undesirable behavior and then negating it,
describe the target when an equivalent positive instruction exists.

Keep explicit prohibitions when they protect:

- safety
- permissions
- destructive operations
- irreversible actions
- hard invariants

When a prohibition is necessary, pair it with the desired target
when useful.

## Pointer Sharpening

A routing pointer should:

- identify the material
- identify the genuine trigger branches
- front-load the strongest trigger
- avoid synonym lists for the same branch
- avoid repeating identity already obvious from the target

Optimize pointers more aggressively than ordinary body text because
they may remain loaded even when the target never activates.

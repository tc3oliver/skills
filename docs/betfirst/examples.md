# BetFirst decision examples

Illustrative cases, **not** measured speedups. Each BET requires a specific observable signal and an ownership-safe rollback.

## WIN candidate: FFmpeg subtitle path

- **Uncertainty:** Is the error caused by path escaping rather than the rendering pipeline?
- **BET:** Use a tiny synthetic input and a read-only or temporary-output FFmpeg command to test the escaping hypothesis.
- **Signal:** The failing input succeeds with escaping corrected while an otherwise identical command fails.
- **WIN:** Apply a narrowly scoped fix, then run the existing renderer tests and a real representative render.
- **CUT LOSS:** If the signal does not distinguish escaping from other causes, stop. Use the output to guide normal diagnosis.
- **Do not:** Start by rendering the complete video or rewrite the pipeline based solely on a passing microtest.

## WIN candidate: API schema mismatch

- **Uncertainty:** Does an optional field cause the client-side parser failure?
- **BET:** Run a locally mocked request with and without the field.
- **Signal:** The target parser reproduces the reported symptom only in one case.
- **WIN:** Update the correct parsing seam; validate upstream and downstream behavior.
- **CUT LOSS:** If neither case reproduces the failure, follow the standard request/response trace.
- **Do not:** Send destructive requests to a real external API.

## LOSE SMALL candidate: TTS sampling rate

- **Uncertainty:** Is mismatched sample rate causing an audio artifact?
- **BET:** Convert a short sample in a temporary directory and compare it against the precise symptom.
- **Signal:** A reproducible check or human-confirmed audible difference; a command's zero exit code is insufficient.
- **CUT LOSS:** If unchanged or inconclusive, remove temporary outputs and investigate other causes.

## NORMAL: cross-module state corruption

- No small probe can establish causality, or the rollback boundary is unclear.
- Follow the normal reproduction and investigation workflow rather than touching shared state speculatively.

## ABSTAIN: code already meets the requirement

- Existing tests and the requested behavior agree. Report the evidence; do not invent a modification merely to place a bet.

## NORMAL: dirty worktree and unsafe isolation

- A speculative edit would overlap user-owned uncommitted files and cannot be safely isolated.
- Prefer a read-only probe. Otherwise investigate without rewriting or stashing the user's changes.

## CUT LOSS: hypothesis disproved

- A one-command minimal probe disproves the original guess.
- Preserve the error output; do not iterate on equivalent guesses without new evidence.

A focused probe validates its own hypothesis. It does **not** independently establish that the whole task is complete.

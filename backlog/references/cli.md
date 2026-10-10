# CLI Reference

`python3 <skill-directory>/scripts/backlog.py --root <repo> <command> [options]`

Every command writes one JSON object to stdout, or an error JSON object on stderr with nonzero exit status. `--json` is accepted as a no-op. The CLI does not install anything globally and never invokes the coding agent.

| Command | Options | Effect |
| --- | --- | --- |
| `init` | none | Create `.backlog/tasks`, `.backlog/archive`, `.gitignore` if missing |
| `add TITLE` | `--goal`, `--ac` repeatable, `--ref` repeatable, `--depends` comma-delimited, `--priority P0..P3` | Create `todo` when goal and criteria exist; else `inbox` |
| `edit ID` | `--title`, `--goal`, `--ac` repeatable (replaces list), `--ref` repeatable (replaces list), `--depends`, `--priority`, `--confirm-ac-reset` (required if replacing checked AC) | Update nonterminal task; promote complete inbox to todo |
| `list` | `--status`, `--limit` (1..100) | Bounded listing, active tasks by default |
| `next` | `--limit` (1..100) | Dependency-ready todo tasks, priority then creation then ID |
| `status` | none | Count states, list at most ten doing tasks |
| `show ID` | none | One task metadata and Markdown; supports archives |
| `start ID` | none | Claim a ready todo task as doing |
| `check ID N` | `--undo` | Mark observed acceptance criterion 1-based checked or unchecked |
| `note ID` | `--text` | Replace pointer-based Handoff; no huge log dumps |
| `block ID` | `--reason` | Park todo/doing task; record blocker |
| `unblock ID` | none | Move blocked to todo, clear blocker |
| `close ID` | `--evidence` required | Require doing, checked AC, completed dependencies, then archive as done |
| `cancel ID` | `--reason` required | Archive as cancelled; does not satisfy dependencies |
| `reopen ID` | none | Reopen archived task and uncheck AC |
| `doctor` | `--repair` (explicit only) | Full historical validation. With `--repair`, move files left in the wrong location by interrupted operations, without overwriting other files |

Tasks live at `.backlog/tasks/BL-<16 hex>.md`; terminal files move to `.backlog/archive/{done,cancelled}/YYYY-MM/`. Task filename and ID must match. The CLI never changes tracked source files. The `.backlog/.lock`, `.backlog/.archive-cache.json` and temporary files are Git ignored. Use `git status` to review actual task changes.

Task metadata is a deliberately restricted `key: value` header, **not** general YAML. Title is JSON-quoted; dependencies are comma-delimited IDs or `-`. Body sections use exact `## Goal`, `## Acceptance Criteria`, `## References`, `## Handoff`, `## Evidence`, `## Blocker` headings. Arbitrary `##` section headers inside inputs are rejected. Do not hand-edit the format.

The CLI verifies internal state, not test truthfulness. `close --evidence` must contain a real command/output observation or other independently checkable evidence. Empty or fabricated evidence is forbidden by the Skill.

Concurrency: OS-native file lock serializes writes in one worktree. Writes use temporary files plus atomic replacement. Git branch/worktree merges are **not** coordinated by the lock: one lead should own writes to each persistent task, and `doctor` detects duplicate IDs or broken references after merging. Close / reopen moves original bytes first, then atomically saves new state at the destination. A move failure leaves the original untouched; a write failure after the move leaves the previous state in the new location. `doctor` reports the interruption and `doctor --repair` restores the original location for unambiguous cases only. No automatic overwrites. Archive paths encode done/cancelled state. A **disposable, ignored** `.archive-cache.json` holds archive filename metadata, validated against archive directory modification signatures and regenerated if stale/corrupt; it is never committed and never becomes the source of truth. Thus `next`/`status` parse active task files and reuse bounded archive metadata, not archive bodies; `show` and historical `list --status` lazily read selected archived bodies, while `doctor` validates all files. After `reopen`, prior Evidence moves into History and must never be treated as current verification.

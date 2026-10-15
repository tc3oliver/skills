# BetFirst v0.4 on a math-research workload (2026-10-15)

**Status:** observational. 12 measured sessions on 3 tasks plus one research campaign. No
significance or causal claim. **No Skill change is proposed.**

## 1. Task and design

The workload was a real research campaign: screening the Justin Sun Prize problem bank
(1,072 problems) for a target where an agent could produce an original, complete,
prize-eligible Lean 4 proof, then scouting open problems. The campaign itself is reported in
§5; three reproducible math-engineering subtasks were extracted from it for the controlled
comparison:

| Task | What the agent must do | Independent oracle (`oracles/`) |
|---|---|---|
| `t1-statement-gap` | Read a catalog record, a Lean Comparator target and the Lean sources; say which catalog requirement the target does not cover and whether the sources already bridge it (`ANSWER.md`) | names the almost-all-pins gap and cites `Pins.lean` / theorem `pins` (keyword check) |
| `t2-lean-lemma` | Prove an elementary fiber-counting lemma in place of `sorry` | compiles at pinned mathlib; theorem statement hash unchanged; no sorry/admit/axiom/native_decide; `#print axioms` ⊆ {propext, Classical.choice, Quot.sound} |
| `t3-mathlib-names` | Find exact mathlib names for 5 stated facts (`NAMES.txt`) | each name closes its statement by `exact` in a generated file |

Before any live run every oracle FAILed on the untouched fixture and PASSed on a reference
solution kept outside the fixtures; a driver dry-run recorded 6/6 FAIL.

## 2. Arms and environment

- **A:** BetFirst v0.4 `SKILL.md` text appended to the task prompt (same method as
  `run.py`'s `prompt_for`) plus a one-line request to write the chosen route to `ROUTE.txt`
  (disclosed protocol overhead, counted in A's tool calls and time).
- **B:** same prompt without the Skill and without `ROUTE.txt`.
- Both: Claude Code 2.1.300, `claude-opus-5-5` (subscription auth, no API billing),
  `-p --output-format stream-json`, `--disable-slash-commands` (so an installed betfirst Skill
  is not auto-discovered), `--strict-mcp-config`, `--setting-sources project` (no user
  plugins/hooks), `--permission-mode dontAsk`, identical `allowedTools`, timeout and max
  turns per task. Fresh workspace copy per run, outside any repository.
- Not `run.py --driver claude`: that driver uses `--bare`, which authenticates only with
  `ANTHROPIC_API_KEY` (paid API). `driver.py` here is a small subscription-auth variant.
- Order: 3 tasks × 2 arms × 2 reps = 12, shuffled with seed 20261015 (`data/manifest.json`).
- Host: Apple Silicon Mac, macOS 27 (`data/env.json`); Lean v4.34.1, mathlib `d13f23b7`.

## 3. Raw data and reproduction

- `data/metrics.jsonl` — one record per measured run (all fields from the stream's terminal
  `result` event; nothing estimated). `data/analysis.txt` — output of `analyze.py`.
- `data/screening-funnel.json` — research-campaign funnel counts (§5).
- Raw session traces are **not** published (they contain local paths and third-party
  source text read by the agent).
- Reproduce:
  1. Build the pinned Lean project from `lean-project/` (`lake update && lake exe cache get`)
     and `export JSP_LEAN_PROJECT=<its absolute path>` (optionally `LAKE=<lake binary>`).
  2. Assemble the T1 fixture from pinned clones (third-party files are not committed):
     `python3 fetch_fixtures.py --math <openai/math@1581d4c> --awards <TheJustinSunPrize/awards@fd8fa66>`.
  3. `python3 driver.py suite.json <out-dir> --reps 2` then `python3 analyze.py <out-dir>`.
  `suite.json` uses a `{LEAN_PROJECT}` placeholder; the measured run used a local absolute
  path, so per-run `prompt_hash` values differ from a re-instantiation elsewhere
  (`suite_sha256` in the manifest matches this file with that path substituted).

## 4. Results (12/12 PASS)

| | A: BetFirst v0.4 | B: control |
|---|---|---|
| PASS | 6/6 | 6/6 |
| Routes | NORMAL 6, BET 0, ABSTAIN 0 | n/a |
| Wall time mean / median | 39.9 s / 42.5 s | 33.3 s / 35.6 s |
| Tool calls mean (excluding the ROUTE.txt write) | 8.0 (7.0) | 7.3 |
| Output tokens mean | 3,238 | 2,922 |
| Gross tokens mean (input+output+cache read+cache write) | 184,791 | 169,865 |

Paired by task (mean of 2 reps, A − B):

| Task | Wall | Tool calls | Gross tokens |
|---|---|---|---|
| t1-statement-gap | +4.0% | −12.5% | +10.6% |
| t2-lean-lemma | +96.5% (A-r1 was the cohort's first run, cold Lean load: 47.5 s; A-r2 alone +6.0%) | +33.3% (the ROUTE.txt write) | +4.6% |
| t3-mathlib-names | +5.1% | +35.7% | +7.8% |

A was faster on 0/3 tasks. Excluding the cold first run, A's mean wall time is 38.3 s vs 33.3 s.
Token fields were complete for all 12 runs. Each of 7/12 runs (t1: 1 A, 2 B; t3: 2 A, 2 B)
had one shell heredoc denied by the permission profile; denials were balanced across arms.

## 5. When BET helped, when it slowed research

In the campaign (screening 294 + 629 catalog rows, five deep scouts of open problems, one
independent Lean verification):

- **One explicit BET** in five scouts (JSP-000395 / Erdős #488: a small counterexample search,
  8 s compute, best ratio 1.19). It did **not** change the decision. The decisive evidence was a
  ~5 min read of the newest preprint, whose references showed a Lean-verified counterexample had
  been public since 2026-09-05.
- The four other scouts chose NORMAL with stated reasons (obstructions were analytic or
  already searched far beyond any 20-minute probe). That matches v0.4's intent: no
  ceremonial probe.
- The other large redirections were cheap **reads**, not probes: a grep showing the upstream
  repository already proved the "missing" bridge lemma (removing a planned formalization), and
  status checks on newer platforms (jig.so, gists) that caught catalog rows already solved.
- In the controlled tasks BET never fired (6/6 NORMAL), so per-BET cost and BET hit rate could
  not be measured there; the observable cost of the Skill was the injected text and the
  route self-report (~5% wall, ~5–11% tokens).

## 6. Is BetFirst a fit for math research?

Observationally: harmless but not helpful on these tasks. In literature-heavy research the
cheapest redirecting observation was usually reading the newest source, which NORMAL already
does; feasibility probes rarely beat it because the hard parts were known obstructions, not
unknown facts a 20-minute experiment could reveal. The default-NORMAL design kept overhead
small. Sample size (3 easy tasks × 2 reps, one campaign) is far too small for a general claim.

## 7. Skill change recommendation

**None.** No BET fired in the controlled runs and the single research BET was uninformative,
so there is no evidence about BET quality to act on. A possible wording change ("prefer a
cheap read of the newest source before a computational probe") is suggested by one campaign
episode only and is not proposed. Next useful study: tasks where the agent cannot know the
answer from sources (e.g. Lean lemma feasibility at the edge of mathlib, counterexample
search with an unknown scale), more reps, and cold/warm-cache control by discarding a
warm-up run per task.

## Limits

Tasks were derived from the same campaign and were easy (all < 1 min); T1's oracle is
keyword-based and T3's accepts any closing name; `~/.claude/CLAUDE.md` user memory may load in
both arms; one operator; research-phase agent metrics are partly self-reported and partly
missing (see the project's own metrics). A 2-run pilot with different isolation flags was
excluded and is not reported as data.

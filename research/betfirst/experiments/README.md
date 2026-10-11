# BetFirst experiment runner (pilot)

**What is measured?** Three independent, sequential fresh-workspace runs per task: Baseline, generic Efficiency, and Efficiency + the exact BetFirst Skill body. An external acceptance test is run after each agent. Both agent time and acceptance time count. Runner usage parsers preserve missing tokens/costs as unknown.

**What is NOT measured yet?** This repository does not contain real Claude Code or Pi run logs, live provider costs, verified BetFirst savings, or independent behavior labels for false/missed bets. The local mock is a deterministic harness smoke check only; never publish its timing as a BetFirst benchmark. The built-in tasks are tiny functionality fixtures, not a representative SWE benchmark.

## 1. Offline reproducible smoke (no API calls)

From repository root:

    python3 -m unittest discover -s research/betfirst/experiments/tests
    python3 research/betfirst/experiments/run.py --driver mock --suite research/betfirst/experiments/suite.json --output /tmp/betfirst-harness-smoke

Expect three tasks × three arms = nine independent runs and nine acceptance passes. Output includes a file named **synthetic-smoke.csv**, never measured-runs.csv, and a manifest with **synthetic: true**. This validates copy/verify/isolation only.

The fixtures cover:
- Windows drive-letter path escaping in an FFmpeg-like subtitle path,
- a TTS duration estimate corrected from observed characters/sec,
- a deliberate no-change task where the code already satisfies the requirements.

All acceptance code is checksum-protected against agent edits; modifying tests fails the run. Refuse to overwrite existing output. Symlinks in seed fixtures are refused. Tasks never inherit changes from another arm.

## 2. Live pilot on your machine (may spend API credits)

**Safety first:** use a disposable sandboxed machine/container, a non-production API credential, and a controlled network. Fresh fixture directories do NOT sandbox an arbitrary coding agent from your home directory, credentials, network, filesystem or subprocesses. Do not run untrusted task prompts. The runner never enables permission bypass and makes no guarantee that a headless agent can execute all edits without your configured approvals.

Use installed authenticated CLI tools; verify supported flags locally with --help before spending credits.

Claude Code (primarily tested design target):

    python3 research/betfirst/experiments/run.py --driver claude --model sonnet --execute --limit 3 --timeout 180 --output /tmp/betfirst-claude-pilot

Pi, with explicit provider/model selection on a consistent runtime:

    python3 research/betfirst/experiments/run.py --driver pi --model anthropic/claude-sonnet-4-5 --execute --limit 3 --timeout 180 --output /tmp/betfirst-pi-pilot

The model string is **illustrative**, not a claim of current model availability. Use the exact installed model ID and equivalent effort settings across all arms. For Pi's provider configuration, make sure it is authenticated before running.

The Claude driver uses noninteractive JSON print mode with --bare. The Pi driver uses JSON events with --no-skills, --no-context-files and --no-extensions. Both avoid accidental BetFirst availability in the Baseline/Efficiency arms and inject the exact Skill **only** into the BetFirst task prompt; these experiments measure an explicit policy, **not** automatic Skill discovery.

**No automatic provider-cost cap:** --timeout sets per-run wall-time and kills the command process group on timeout; the model could incur cost before that deadline. Use an isolated test account with external hard spending limits. The runner does not silently retry.

Logs can contain task text, code, provider responses, or secrets. Keep --output outside the repo, inspect/redact before sharing, and do not commit raw sessions. Do not use production repositories with the included pilot.

## 3. Review results

Each run has a separate workspace, prompt, raw CLI stdout/stderr and an outcome.json containing acceptance result, timeout, protected tests integrity, and wall time. The parent directory contains a manifest, metadata and a CSV.

    python3 research/betfirst/scripts/analyze_runs.py /tmp/betfirst-claude-pilot/measured-runs.csv
    python3 research/betfirst/experiments/report.py /tmp/betfirst-claude-pilot

The new pilot reporter directly contrasts **BetFirst vs Efficiency-only**, includes pass counts and flags incomplete usage. It refuses to compute savings from synthetic mock output. For the existing analyzer on main, you get Baseline/Efficiency and Baseline/BetFirst comparisons. Once PR #3's analyzer is merged, you also get BetFirst vs Efficiency, the comparison that isolates the added decision policy. Only compare equal task/replicate pairs and disclose acceptance rate alongside costs.

Record input/output/cache token fields separately and actual provider USD cost when exposed. If a backend version omits a field, it stays blank. Pi message_end assistant usage is summed once per response; streaming updates/turn_end duplicates are deliberately ignored. Claude uses the final structured response and provider-reported costs.

**Version/limitation:** runtime outputs evolve. Validate parsers against your installed Claude/Pi versions before making claims. This runner does not automatically adjudicate False Bet / Missed Bet / Failed Cut; that requires trace annotation by an independent reviewer.

## 4. Next controlled study

1. Run this tiny three-task smoke on authenticated Claude and Pi to validate the CLI adapters (not to publish a speedup).
2. Freeze 10–12 real coding tasks with independent acceptance tests and separate, single-agent sessions.
3. Repeat three arms with identical models/tool permissions; measure full-task correctness and wall-clock/usage, including fallback and validation.
4. Scale to 30+ tasks and multiple replicates with randomized run order; review failed-bet tail and missed bets.
5. Publish reproducible traces and summary only if results withstand correctness checks.

The full v0.3 field study protocol lives in PR #3 at research/betfirst/evals/next-experiment.md. This PR intentionally stays independent of PR #3 and does not change SKILL.md or the Plugin version.

References: [Claude Code CLI](https://code.claude.com/docs/en/cli-reference), [Pi print/JSON modes](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent/docs).

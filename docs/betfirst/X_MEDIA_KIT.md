# BetFirst — X / Twitter media kit

## The story (before sharing any benchmark number)

**Problem:** coding agents may spend a long time reading documentation, exploring feasibility or building a full proof of concept *before* trying the smallest thing that could settle a crucial question.

**BetFirst:** make one **cheap, bounded, falsifiable and reversible feasibility bet** first. Win and avoid preliminary work the result makes unnecessary; lose and cut losses immediately, keep evidence, investigate normally. Either way, **implement and validate correctly**.

The bet may itself be a *tiny PoC*. Don't say BetFirst "eliminates PoCs", "replaces research" or "always works". Say it **can avoid unnecessary up-front research or a larger PoC, when a safe decisive mini-test exists**.

## Images — use as media in an X post

- [X cover, 1600 × 900 SVG](../../media/media/betfirst/assets/x-cover.svg) — main launch visual; Make Cheap Bets / Win Big / Lose Small.
- [X explainer, 1600 × 900 SVG](../../media/media/betfirst/assets/x-explainer.svg) — the normal long path versus a small reversible BET and its WIN/LOSE outcomes.
- [GitHub hero, 1200 × 480 SVG](../../media/media/betfirst/assets/hero.svg) — banner for release notes / GitHub.
- [README comparison, 1200 × 580 SVG](../../media/media/betfirst/assets/before-after.svg) — embedded product explanation.
- [Existing lightweight concept GIF](../../media/media/betfirst/assets/probe-loop.gif) — optional animated supplement; conceptual rather than a recorded run.

**X usually works more reliably with PNG/JPEG than GitHub SVG.** Convert the provided SVGs to raster PNG before uploading. For example, with an optional *documentation-only* rasterizer (NOT a dependency of the BetFirst Skill):

```bash
python3 -m pip install --user cairosvg
python3 -c 'import cairosvg; cairosvg.svg2png(url="media/betfirst/assets/x-cover.svg",write_to="betfirst-x-cover.png")'
python3 -c 'import cairosvg; cairosvg.svg2png(url="media/betfirst/assets/x-explainer.svg",write_to="betfirst-x-explainer.png")'
```

Or use an installed SVG export tool. The SVG originals remain editable and GitHub-previewable. For accessibility, use the factual alt text from the SVG descriptions; both cards describe **conceptual workflow**, not measured time savings.

## Pre-v3 public X post

> Your coding agent might read docs, investigate feasibility, and build a whole PoC before trying the smallest thing that could prove the idea works.
>
> What if it placed one tiny, reversible bet first?
>
> **WIN:** skip the preparation you no longer need.
> **LOSE:** stop early, keep the evidence, and investigate normally.
>
> BetFirst — **Make Cheap Bets. Win Big. Lose Small.**
>
> Never gamble on correctness.
>
> https://github.com/tc3oliver/skills/tree/main/betfirst

Recommended visuals: the **cover** in the first post, the **explainer** as a reply. Keep wording simple; a shortened variant is fine. This post does not claim unmeasured benchmark results.

## Follow-up Thread (non-numerical)

1. Feasibility problem: researching everything / full PoC before testing the one make-or-break assumption.
2. BetFirst decision: SPOT / CAP / BET; one small test, no irreversible side effects.
3. WIN: a decisive result makes *some* early investigation unnecessary; you still implement and verify.
4. LOSE: short and bounded. If the hypothesis is false, that information is valuable—don't repeat it without new evidence.
5. NORMAL / ABSTAIN: not everything should be a bet. Safe operations and user changes matter.
6. Github setup command and link.
7. Link to the detailed v1/v2 record and the frozen v3 study after results are available.

## Evidence discipline

The local v2 trial involved only **two diagnostic task clusters**, each repeated three times. It is exploratory, with gains and losses on different task types; do not lead with an unqualified "-X% faster" hero claim. **No v3 results are known as this kit is prepared.**

After v3, update the separate [study launch kit](../../research/betfirst/experiments/V3_LAUNCH_KIT.md) using the generated `v3_report.py` result and all applicable limitations. Do not insert hypothetical data or selectively show successful runs.

Never describe a miniature feasibility probe as production-ready functionality. BetFirst always retains the same final correctness bar.

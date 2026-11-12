# v5 agentic run 1 — results (2026-11-11)

Prompt `prompts/v5.md`, rubric `rubric/v5.md` (gates, then F 0–10 + R 0–5 + H 0–5 = 20). Setup and timings: `RUN_LOG.md`. This is **one run per model**, so there are no medians yet (the rubric wants 3). Two run-2 entries (Terra, GPT-6 Luna) were judged as well, because they finished before run 2 was stopped.

## How it was judged

1. **Gate 0:** a transcript audit of all threads, done by scanning T3's local transcript DB for out-of-workspace paths and benchmark identifiers.
2. **Blind set:** the valid entries were copied under shuffled IDs J01–J09, with agent files and `.git` stripped. The map was kept outside the judge's folder.
3. **G1:** a clean `npm install && npm run build`, plus a bundle check (all 9 pass; no photos embedded).
4. **Harness:** `tools/judge-harness-v5.mjs` in headless Chrome (Metal ANGLE). It uploads all 7 photos in name order (a) and reversed (b), waits, captures the panel text and console, orbits, and exports `.ply` and `cameras.json`.
5. **F (measured):** `tools/score_v5.py` does the following:
   - Sim(3)-aligns the exported cameras to the COLMAP GT (Umeyama on centres).
   - Renders the `.ply` at the 6 held-out GT poses in our own EWA tile rasterizer.
   - Measures LPIPS (alex), SSIM and PSNR, with no sky mask (the held-out views have almost none).
   - Re-renders the input views at the contestant's own cameras to recompute its input-view PSNR.

   The rasterizer passed a self-render unit test, and the GT pose convention was checked (every forward axis points at the scene centre). The F bands were fixed before any contestant metric was seen:
   - L > 0.98 (worse than mean colour): F decays to 0.
   - Mean colour → nearest photo (0.98 → 0.487): F rises linearly 1 → 5.
   - Better than the nearest photo: F rises 5 → 10 at L = 0.15.
   - Fewer than 3 registered views, degenerate cameras, or a G2 fail: F = 0.
6. **R, H, G2, G3:** scored by a blind judge subagent from the code, harness captures and `score.json` (`JUDGE_NOTES.md` is in the archive). I checked its J07 G2 call against the screenshots.

**Baselines (held-out mean):**

| Baseline | LPIPS | SSIM | PSNR |
|---|---|---|---|
| Mean-colour image | 0.980 | 0.25 | 14.48 |
| Nearest input photo, unwarped | 0.487 | 0.14 | 14.07 |

PSNR ranks mean colour above the real photo, which confirms the plan's choice of LPIPS as the primary metric.

## Scores

| # | Model (medium) | Run | Wall | G2 a/b | F | R | H | **Total /20** | Held-out LPIPS | Views reg. (ours) | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `grok-4.7-build-fast` | 1 | 52.4 min | ✓/✓ | 0.0 | 5 | 5 | **10.0** | 1.030 | 7/7, poses off GT | Real SfM + BA + gradient refinement; honest; held-out renders nearly empty after alignment |
| 2 | `muse-spark-1.3` | 1 | 25.1 min | ✓/✓ | 2.0 | 4 | 3 | **9.0** | 0.857 | 7/7 claimed, arc | Best measured F; real Adam refinement (14.5→19.7 dB, ours 19.35); poses are always an arc |
| 3 | `claude-sonnet-5-5` | 1 | 15.2 min | ✓/✓ | 0.0 | 4 | 3 | **7.0** | — | 2/7 (a), 3/7 (b) | Real SfM + MVS + full Adam; too few views for alignment; panel PSNR 3.2 dB above ours |
| 4 | `muse-ember-1.0` | 1 | 27.5 min | ✗/✗ | 0.0 | 1 | 2 | **3.0** | (0.974) | 7/7 estimated | Real E-matrix SfM + Adam, but the viewport is a flat colour: "Ready" over a blank-looking canvas |
| 5 | `gemini-3.8-flash` | 1 | 16.2 min | ✓/✓ | 0.9 | 1 | 0 | **1.9** | 0.987 | arc (disclosed) | Depth indexing bug; "refinement" isn't a gradient; claims backprop |
| 6 | `gpt-6-luna` | 2 | ~2 min | ✓/✓ | 1.1 | 0 | 0 | **1.1** | 0.973 | arc | Opaque ellipsoid meshes on a brightness slab; candid notes, overclaiming disclosure |
| 7 | `gpt-6-luna` | 1 | 0.8 min | ✓/✓ | 0.0 | 0 | 0 | **0.0** | — | degenerate | Sphere meshes, noise depth, all cameras at the origin; false `yes` fields |
| 7 | `gpt-6.1-terra` | 1 | 0.6 min | ✗/✗ | 0.0 | 0 | 0 | **0.0** | — | — | Honest stub ("not implemented") |
| 7 | `gpt-6.1-terra` | 2 | ~3 min | ✗/✗ | 0.0 | 0 | 0 | **0.0** | — | — | Honest stub again |
| DQ | `gpt-5.6-luna` | 1 | 9.7 min | — | — | — | — | **DQ** | — | — | Gate 0: computer-use read Alex's open Chrome tab of this repo (README, v4 scores, rubric summary) |

## Findings

- **Nobody beat the "show the nearest photo" baseline on held-out views.** The best was LPIPS 0.857. No entry recovered the true 7-view camera arc: the camera-centre residual after Sim(3) is ≥ 0.66 of the spread for every entry, and swapping conventions (inverse / OpenGL) doesn't help. Even entries with good self-consistency (Grok: 1.6 px reprojection error, panel PSNR matching ours) have poses that disagree with COLMAP. F therefore barely separates entries; R and H decide the ranking. **The v5 change worked:** three entries (Grok, Spark, Sonnet) plus Ember ran real gradient refinement. In v4, nobody attempted A.
- **The "recompute PSNR" check works.** It confirmed Grok (14.63 vs 14.44) and Spark (19.7 vs 19.35), and caught gaps of 2.4–3.2 dB for Gemini, Sonnet and Ember.
- **`views_registered` was misused.** Four entries report 7/7 while every camera was assumed. v6 should require that `registered: true` means estimated, and the rubric should penalise it explicitly.
- **Sonnet:** the strongest pipeline on paper, but only 2–3/7 views registered, so F = 0 and it ranks third. The rule giving F = 0 below 3 views is harsh here. Consider falling back to scoring input-view PSNR when alignment is impossible.
- **Codex mid-tier (Terra, GPT-6 Luna) gave up in under a minute in both runs.** That is the same pattern as v4. At medium effort these models consistently don't attempt the task.

## Isolation incidents and fixes for next time

- **GPT-5.6 Luna DQ.** Codex's computer-use tool drove the real desktop Chrome, and its accessibility dump included a tab open on `github.com/afloresescarcega/gaussian-splatting-reconstruction-benchmark`. **Fix:** disable computer-use for Codex contestants, or at least close the repo tab and use a separate Chrome profile during runs.
- **Grok and Gemini used T3's in-app preview tools.** They only saw their own localhost, so they pass, but these are T3 tools. Consider disabling them for contestants.
- **The judge's scratch data lives under `/private/tmp/claude-501/`, next to the contestants' own scratchpads.** Keep held-out data somewhere locked during runs.

## Caveats

- One run per model; expect about ±2 points between runs.
- Baseline (b) from the plan (monodepth on an assumed arc) is not built. The nearest-photo baseline stands in as the upper anchor.
- The harness waits for export-ready plus 15 s of stable text. Apps that keep refining after their export buttons are enabled could be captured early. No entry showed signs of this.

Artifacts (gitignored): `archive/2026-11-11_v5-agentic/judging/` holds the blind set with harness captures and screenshots, `scores/` (held-out renders), `private/blind_map.tsv`, and the gate-0 transcript dumps.

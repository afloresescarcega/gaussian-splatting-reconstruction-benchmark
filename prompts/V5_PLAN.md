# v5 plan — what to fix and how to push harder

Inputs: v4 agentic run 1 (`observations/2026-11-11_v4-agentic/RESULTS.md`), plus a read-only review by Claude Fable 5.2 (2026-11-11, summarized under "Fable 5.2 review" below). Items are tagged **[fix]** (broken or unfair in v4), **[harder]** (raises the ceiling), **[objective]** (less judge subjectivity).

## P0 — must fix before the next run

- [ ] **[fix] Muse provider can't start sessions.** Both Muse threads died with `session MCP base configuration is unavailable`, even on a one-line prompt. Fix in T3, then rerun Ember 1.0 / Spark 1.3 on v4 so the v4 table is complete before moving on.
- [ ] **[fix] Antigravity starts outside the workspace** (`~/.t3/userdata/attachments`). Confirm the cwd fix, or prefix its prompt with nothing and launch it from a wrapper that `cd`s first. Re-audit after.
- [ ] **[fix] Image set has a 125° gap.** The v1–v4 photos sit at 138°/175°/300°/333°, so no pose estimator can bridge them. Use **set C** (`inputs/set-C-mipnerf360-garden-dense/`): 7 views at roughly 30° spacing. Raise the prompt limit from 3–6 to **3–8** images.
- [ ] **[fix] Filename order leaks the arc.** Sonnet sorted by filename (DSC numbers ≈ capture order). Rename uploads to random names (`img_k3.jpg`), shuffle the order, and strip EXIF.
- [ ] **[fix] Static disclosure vs runtime fallback.** Gemini hard-coded `camera_poses: estimated` and then fell back to an assumed arc at runtime. Require the disclosure fields that depend on the input (`camera_poses`, `views_registered`) to also be shown live in the panel. Score the runtime values.
- [ ] **[fix] Network flake in scoring.** One Hugging Face model download timed out. Rule: one automatic retry per run; optionally pre-warm the browser cache before judging.

## P1 — make faithfulness objective (biggest scoring change)

- [ ] **[objective] Held-out novel-view metrics.** Set C's `heldout/` holds 6 interleaved views + GT COLMAP poses. Judge pipeline:
  1. Contestant exports `.ply` **and** `cameras.json` (estimated intrinsics + extrinsics per uploaded image; new required output).
  2. Sim(3)-align contestant cameras to GT using the uploaded views.
  3. Render the `.ply` at each held-out pose in **our own** reference rasterizer (removes their renderer as a variable; build on `tools/judge-harness.mjs` or a small gsplat-based renderer).
  4. Report **LPIPS (primary)**, SSIM, PSNR. Mask the sky, or down-weight it, so a blurry average image doesn't win PSNR.
- [ ] **[objective] Baseline floors.** Publish the scores of (a) "mean-colour image", (b) "monodepth on an assumed arc" (≈ Terra v4), (c) "per-view depth sheets with GT poses". Anything not beating (b) caps faithfulness at 1.
- [ ] **[objective] Views-registered sub-score:** `registered / uploaded`, read from `cameras.json`.
- [ ] **[objective] Viewer ↔ .ply consistency check:** render the `.ply` ourselves at the app's default camera and diff it against the app's screenshot. This catches a viewer that shows something the export doesn't contain.

## P2 — push for innovation

- [ ] **[harder] Re-weight the score.** Axes 1/4/5 are mostly checklist compliance (the three renderer checks are spelled out), worth about 9/15 for following instructions. Proposal: turn "builds / loud errors / disclosure present" into **pass/fail gates**. Score = **faithfulness metrics (~50%)** + 3DGS validity + engineering judgment/honesty.
- [ ] **[harder] Expect refinement, not just initialization.** Nobody attempted approach A in v4. The prompt's "a working honest C beats a broken A" plus full marks for C made C the rational choice. v5 wording: a hybrid is expected (initialize from B/C, then run a few hundred photometric steps). A WebGL/WASM/CPU autodiff over ~20k Gaussians at low resolution is acceptable. Keep "honest > faked", but stop implying C is the target.
- [ ] **[harder] Required runtime photometric number.** The panel shows the PSNR of re-rendering each *input* view from its estimated pose, before and after any refinement, with a loss curve if optimizing. This makes render-and-compare a built-in step (most of a training loop). It's also an honesty check: we recompute it ourselves.
- [ ] **[harder] Hidden evaluation scenes.** `photos/` becomes a dev set only. Judge on 2–3 unseen sets, e.g. set C garden (narrow-ish), set A bonsai (indoor), and one low-texture or specular scene. This rewards robust pipelines over tuning to the dev scene.
- [ ] **[harder] Probe the feed-forward frontier.** Nobody tried MASt3R / DUSt3R / NoPoSplat-class models in the browser. Before v5, check whether usable ONNX exports exist and are a feasible browser download. If they are, name them in the hints; if not, say B effectively means monodepth, so contestants don't burn time searching.

## P3 — run protocol

- [ ] **Effort / time budget.** v4 at "medium" ranged from 64 s to 38 min, and two runs never executed their own pipeline on `photos/`. State: "You have up to 60 minutes. Verify the full flow on `photos/` in a browser before finishing." Record wall time next to score.
- [ ] **3 runs per model** before ranking. Expect about ±2 points of run-to-run variance; report median and range.
- [ ] **Blind judging.** Contestant outputs go into random-ID folders. Scoring runs in a fresh judge session that never sees the model↔ID map (Alex's preference; waived for v4 run 1 only).
- [ ] **Isolation recipe** (worked in v4): per-contestant fresh git repo under `~/Sandboxes/` (parent `chmod 311`), benchmark repo `chmod 000` during the run, neutral prompt, full transcript audit. Also add: no thread/orchestration tools in contestant sessions if the provider allows disabling them.

## Gaming routes to close

- **Fake anisotropy:** "non-trivial scale/rotation variation" in the `.ply` can be met with depth-gradient noise. Held-out metrics fix this indirectly; don't rely on `.ply` variation alone for axis 2.
- **Filename / order exploitation:** closed by renaming and shuffling (P0).
- **Static disclosure lies:** closed by runtime disclosure (P0).
- **Self-reported PSNR inflation:** recompute from their `.ply` + `cameras.json`; a mismatch above about 1 dB counts as an honesty failure.
- **Optimizing on held-out views:** impossible as long as `heldout/` never enters a workspace. Keep it outside `~/Sandboxes` (it lives only in the repo, which is locked during runs).

## Fable 5.2 review (summary, 2026-11-11)

Top five, in Fable's priority order:
1. Replace axis 3 with automatic held-out metrics, scored on the exported `.ply` in our own rasterizer after Sim(3) alignment.
2. Judge on unseen scenes, not the dev scene.
3. Make the ceiling unreachable without optimization: faithfulness at 40–50% of the score, plus a views-registered sub-score.
4. Require a self-reported runtime photometric number (input-view PSNR), which pushes contestants toward a training loop and doubles as an honesty check.
5. Fix the effort variance with an explicit time budget and a "verify in a browser" instruction.

Also from Fable:
- "Nobody tried A" is mostly the prompt (C is rewarded as safe), partly a capability ceiling. Pose failure on wide baselines also made optimization pointless, so the dense set is a prerequisite.
- Axes 1/4/5 are cheap to max; compress them into gates.
- LPIPS should be primary; mask the sky.
- Use three seeds per model.

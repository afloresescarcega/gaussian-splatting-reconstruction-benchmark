# v4 agentic run 1 — 2026-11-11 — mid-tier models, local T3 threads

**Track:** v4-agentic (not comparable with v1–v3 arena.ai scores). Prompt `prompts/v4.md`, rubric `rubric/v4.md`.
**Setup:** one top-level T3 Code thread per model, each at medium reasoning effort, `full-access`, single prompt, no follow-ups. Each contestant got a fresh git repo at `~/Sandboxes/splatapp-<hex>/` containing only `photos/` (the 4 garden-table photos DSC07956/07970/07986/08001). `~/Sandboxes` was `chmod 311` (not listable) and `~/REPOS/gaussian-benchmark` was `chmod 000` for the run. The prompt never mentions a benchmark, rubric, or other runs.
**Judging:** not blind (Alex OK'd it for this run). Workspaces were frozen at hand-in, then clean `npm install && npm run build`, bundle check, code review, and headless Chrome (Metal ANGLE, WebGPU available) via `tools/judge-harness.mjs`: upload in order a (07956, 07970, 07986, 08001) and shuffled order b (08001, 07956, 07986, 07970), orbit / zoom / pan, Export .ply.

## Scores

| Model (effort medium) | Workspace | Wall time | Gate 0 | 1 Run | 2 3DGS | 3 Faithful | 4 UX | 5 Honesty | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` | c1be3496 | 16.8 min | pass | 3 | 3 | 2 | 3 | 3 | **14** |
| `grok-4.7-build-fast` | 46fb969f | 38.3 min | pass | 3 | 3 | 1 | 3 | 3 | **13** |
| `gemini-3.8-flash` (Antigravity) | 8902620c | 13.1 min | pass (note) | 3 | 3 | 1 | 2 | 2 | **11** |
| `gpt-6.1-terra` | 5215798e | 1.4 min | pass | 3 | 2 | 1 | 2 | 3 | **11** |
| `gpt-5.6-luna` | 8d4b124f | 3.6 min | pass | 1 | 1 | 0 | 1 | 2 | **5** |
| `gpt-6-luna` | 844cd5cb | 1.1 min | pass | 1 | 1 | 0 | 1 | 1 | **4** |
| `muse-ember-1.0` | cbada80d | — | — | — | — | — | — | — | **no start** |
| `muse-spark-1.3` | 8ec225d0 | — | — | — | — | — | — | — | **no start** |

Muse: both threads failed before the first turn with `Muse session/start failed: internal error: session MCP base configuration is unavailable`. A one-line retry (`Say "ok"`) failed the same way, so this is a T3/Muse provider config issue, not the task. Both workspaces are untouched; rerun once the provider is fixed.

## Gate 0 (isolation audit)

All six finished transcripts were read in full (command + file + tool items). No contestant read the benchmark repo, other sandboxes, Alex's other splatting repos, other threads, or the GitHub repo.
- **Gemini / Antigravity (note, not DQ):** the Antigravity harness started the shell in `~/.t3/userdata/attachments`, not the project folder. The agent's first `pwd && ls -la` listed that directory (UUID-named attachments, including the 4 photos and older HTML attachments); no file there was opened. **Isolation gap to fix:** Antigravity does not start in the project cwd.
- Grok read its own harness skill file (`~/.grok/bundled/skills/...`) and ran puppeteer from a self-made `/tmp/pwtest`. Sonnet listed `~/Library/Caches/ms-playwright` (browser cache). All allowed.
- Bundle check: no JPEG bytes, `/9j/` base64, or `photos/` references in any `dist/` or source. No hardcoded scene content (grep for table/vase/hedge/etc. only hit Grok's popcount `table` variable).

## Per-model notes

**`claude-sonnet-5-5` — 14.** Hand-written SIFT-style DoG features, normalized 8-point E + RANSAC, cheirality, midpoint triangulation, focal chosen from 5 hypotheses. Depth Anything Small (transformers.js) per image, made metric by fitting `1/z = a·d + b` to the triangulated points. Gaussians are rotated by local depth-gradient frames. The renderer is its own WebGL2 EWA projection with a CPU depth sort. Registered only 2 of 4 views (07970 and 08001 skipped, with yellow banners naming them). The result is the most recognizable of the run: table, vase, ball and hex paving all read from near the reference view. Off-axis it becomes a 2.5D depth sheet (axis 3 = 2). It sorts by filename, so upload order doesn't matter (documented, verified). Per-stage checklist UI; panel says "43/49 sampled pixels drawn"; binary standard PLY. Disclosure and code match, including `camera_poses: estimated`.

**`grok-4.7-build-fast` — 13.** The most engineering with zero ML: FAST + ORB + RootSIFT, GMS, 8-point E + RANSAC + LM pose refine, incremental registration, inverse-depth plane sweep with two-way ZNCC, PCA normals, EWA renderer with back-to-front sort and premultiplied alpha. Ran its own headless-Chrome tests. Also registered only 2 of 4 views (stated on screen: "7127 splats from 2 of 4 views"). The dense output is mostly the background hedge/wall plus floaters; the table isn't recognizable (axis 3 = 1). Zooming in shows large flat quads. Notes and disclosure are thorough and accurate.

**`gemini-3.8-flash` — 11.** FAST/descriptor matching + 8-point RANSAC chain with a fixed 0.8 baseline, Depth-Anything-V2 depth, depth-gradient normals, EWA renderer (Jacobian, 2D eigen radius) with sorting. On these photos RANSAC got **0 inliers**, so it fell back to an assumed 135° arc. The telemetry panel says so ("Orbital Arc Prior"), but the disclosure block hard-codes `camera_poses: estimated` (axis 5 = 2). The output is fragmented, stretched sheets; the table top is identifiable in one view (axis 3 = 1). The default camera crops the scene off-center and the notes panel covers part of the canvas (axis 4 = 2). Said "Family B" for monocular depth, which is reasonable.

**`gpt-6.1-terra` — 11.** 90-second run. Depth Anything V2 Small per image, unprojected onto an assumed ±45° arc, camera-oriented Gaussian discs (flat quads with Gaussian alpha, no covariance projection, unsorted). The final message plainly says "the deliverable is incomplete ... does not project the full 3D covariance ... I did not verify an end-to-end reconstruction in a browser." It does build and run: four ghosted depth sheets stacked together, garden vaguely legible from the front, changes with upload order (disclosed). Shader-error hook, context-lost handler and a 50-pixel sample are all wired. Scale/opacity in the PLY are properly log/logit. The most honest low-effort entry.

**`gpt-5.6-luna` — 5.** Crude but real multi-view: horizontal patch-SAD disparity from the middle view against the others gives depth; oriented world-space Gaussian quads; compile/link + context-lost + pixel sample all wired. On the example photos it **fails in both orders** with a loud, stage-named error: "Too few stable multi-view matches". So nothing renders and there's nothing to export. It never ran the pipeline on the photos it was given (build-only verification). The "estimated local normal" is really the pixel ray (minor overclaim).

**`gpt-6-luna` — 4.** 64-second run. Depth = pixel luminance (`(l-.5)*.7`), assumed full-circle arc, rendered as instanced low-poly **mesh spheres** (`MeshBasicMaterial`, no Gaussian falloff, no sort). `vertexColors:true` without a geometry color attribute makes every splat ~black. Its own pixel check then fires "Renderer produced no visible primitives" (loud, and correct in spirit). The disclosure says `pixel_position_or_depth_derived_from_pixels: yes` for luminance-as-depth, which is the "heuristic-only" case the prompt excludes (the panel itself says "luminance-derived depth"). The PLY writes linear opacity/scale under standard 3DGS property names.

## Takeaways for v5

- **Wide-baseline 4-photo set breaks every pose estimator.** The three real SfM attempts (Sonnet, Grok, Gemini) each registered ≤2/4 views or fell back to an arc. Consider adding a denser / narrower-baseline set (e.g. 6 photos ~20–30° apart) so axis 3 can separate the strong pipelines.
- **Effort spread is huge at "medium".** Codex mid-tier runs took 1–4 min and two never ran their own pipeline on the photos. Grok took 38 min and browser-tested. If the goal is capability not diligence, consider stating "test against `photos/` in a browser before finishing" — or keep it as is and treat diligence as part of the signal.
- **Make `camera_poses` a runtime field.** Gemini's static disclosure contradicted its own runtime fallback. v5 could ask for the disclosure values to also be shown at runtime when they depend on the input.
- **Isolation:** Antigravity starts in the attachments folder. Muse can't start sessions. Fix both before the next run.
- **Judge harness:** headless Chrome with `--use-angle=metal` renders WebGL2 + WebGPU fine. Sonnet's first shuffled-order run hit a Hugging Face download timeout and was rerun (network flake, not scored).

## Local-only artifacts

Screenshots (they contain thumbnails of the research-licensed photos), judge outputs/exported PLYs, transcript-audit dumps and the contestants' submitted source are archived outside git in `~/REPOS/gaussian-benchmark/archive/2026-11-11_v4-agentic/` (`archive/` is gitignored).

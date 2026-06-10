# Run: Option B on prompt v3 with garden-table photos (run 4)

- Date: 2026-06-09
- Prompt version: v3
- Rubric version: v3
- Image set: 4 images; probe scene_description is a garden patio (round wooden table, vase, brick walls, plants). Assumed the standard garden-table set — confirm exact filenames.
- arena.ai slot: Option B (per Alex).
- Source archive: `3d-gaussian-splatting-app (2).zip`.

> **Scoring discipline (blind).** This note scores the artifact on its own merits. Model identity was **not** inferred and **no prior run's fingerprint or score was used to anchor any axis** — inferring the model biases the judge (anchoring each axis to "what that model usually scores here" instead of to the rubric + the evidence). If Alex reveals the identity post-hoc it may be appended as a separate labeled line at the bottom; it must not feed back into the scores above.

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: The attached photos show a garden/backyard scene centered on a round wooden outdoor table with a tall vase-like decorative object on top. The viewpoints move around the table, with brick walls, plants, patio stones, and other garden items visible in the background.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

## What the app produces

React / Vite / Tailwind-v4 single-file build, Approach C. Decodes uploads to a 144px-max working buffer, estimates a heuristic monocular depth field per image (luminance, saturation, Sobel edges, local contrast, center-grown confidence region), unprojects to world points placed on a fixed camera ring in upload order, derives per-splat orientation from local depth-gradient surface normals composed with the capturing-camera basis, and renders anisotropic 3D Gaussians through a custom WebGL2 shader (EWA covariance projection + 2D eigendecomposition). Reported **4,036 splats**.

## Rubric scores (rubric v3) — artifact only

| Axis | Score | Note (this artifact only) |
|------|-------|---------------------------|
| 1. Deployed & runs | **3** | Clean build; `main.tsx` mounts a fixed boot-error banner on `window` error / `unhandledrejection`; screenshot shows a non-black render at "Ready to view 4,036 splats"; orbit/pan/zoom wired via pointer capture. No silent-black-canvas cap. |
| 2. Actually 3DGS | **3** | Genuine anisotropic 3D Gaussians: per-splat position + quaternion + 3D scale; vertex shader builds `Σ_world = R·S²·Rᵀ`, projects through the perspective Jacobian to a 2D screen covariance, eigendecomposes for ellipse axes; back-to-front sort + `SRC_ALPHA/ONE_MINUS_SRC_ALPHA`. Color, depth, and orientation all driven by uploaded pixels. |
| 3. Reconstruction faithfulness | **1 — provisional, not orbit-tested** | Code path is non-geometric: heuristic monocular depth (saliency/center/lower/darkness blend, not recovered geometry) + assumed fixed-ring poses + no triangulation or multi-view consistency. The single available screenshot is a **default novel-angle** view showing a coarse amorphous cloud — equally consistent with a "1" or a "2." The rubric's axis-3 procedure (orbit to a near-input pose, compare to inputs) was **not performed**, so 2 is not yet earned. `pixel_position_or_depth_derived_from_pixels: yes` keeps it off the hard cap of 1. Re-score after a live orbit. |
| 4. Web app UX | **3** | Per-stage progress (Decode → Depth → Gaussians → Ready) with bar + detail; stage-attributed error UI; all three v3 renderer checks wired **and correct** — shader compile/link throw-and-surface, `webglcontextlost` listener, 50-random-pixel post-first-frame probe (`preserveDrawingBuffer: true` + `gl.finish()`). |
| 5. Engineering judgment & honesty | **3** | Every probe `yes` has a real path; panel matches code; Gaussian count is a runtime read (`runtimeGaussianCount`), not a literal; caveats disclosed plainly (no COLMAP/SfM/learned depth, fixed-ring poses, coarse cloud, no SH). Unused `clsx`/`tailwind-merge`/`cn.ts` are silent scaffold cruft, not claimed in the panel — not a fabrication. |

**Total: 12/15 on current evidence; axis 3 pending a live-orbit test (ceiling 13 if near-input recognizability holds up).**

## Execution-bug check (artifact only)

- **No coordinate-convention zero-output bug**: `unproject` returns local `[x, y, -depth]`; `transformCameraLocalToWorld` applies `forward · (+depth)`, landing points in front of each capturing camera; the orbit camera's view-space `depth <= 0.001` cull is correct. Render is non-empty.
- **No visibility-probe mis-read**: samples 50 genuinely random pixels, not a fixed corner block.
- **Friction (not scored)**: 144px working buffer → coarse depth field and only 4,036 splats, low for a foliage-heavy scene — the main thing dragging faithfulness. Full CPU re-sort + re-upload of all five instance buffers every frame; fine at 4k, heavier at scale.

## Implications for next prompt version

Nothing triggered by one artifact. The self-imposed 144px working cap trading faithfulness for responsiveness is the only mildly interesting datum; if it recurs, a soft working-resolution floor in the prompt could be worth considering — but watch for recurrence before changing anything.

---

## Post-hoc identity (revealed by Alex after scores were locked — does NOT change the scores above)

**Option B = `gpt-5.4-high`** — *not* `gpt-5.5`.

Two notes, post-hoc analysis only (not scoring inputs):

1. **The mid-session fingerprint guess was wrong.** Before the blind re-score, this artifact was guessed as "almost certainly `gpt-5.5`" from the custom-WebGL2 + heuristic-depth + loud-error-contract structure, and an earlier (discarded) pass even scored it 14/15 by anchoring to the `gpt-5.5` v3 B ceiling. It was `gpt-5.4-high`. The "attractor" resemblance was a **false positive** — the very deviations noted at the time (no `three` declared, 144px cap, 4,036 splats vs the 9k–19k range) were the real signal that this was a different model. Concrete proof that anchoring scores to an inferred identity would have anchored to the wrong model entirely. See [[feedback_judge_blind_no_model_inference]].

2. **Cross-prompt (confounded):** the prior run for this model is v2 B ([`2026-04-25_model-B_v2_garden-table.md`](2026-04-25_model-B_v2_garden-table.md), 8/15) — the silent black-canvas with no surfaced error that *motivated* v3's loud-error contract in the first place. Under v3, this same model renders a working (if coarse) cloud and wires every loud-error check. 8→12, but confounded by the entire v2→v3 prompt change (not a clean within-prompt pair); suggestive only that v3's emphasis moved this specific model off its v2 silent-failure mode.

# Run: Model B on prompt v3 with garden-table photos (run 2)

- Date: 2026-04-25
- Prompt version: v3
- Rubric version: v3
- **Model identity (revealed post-run): `gpt-5.5`** (same model that powered v1 B and v3 B run 1 — confirms the structural-fingerprint guess)
- Image set: 4 garden-table photos — same set as the v1, v2, and v3 first-pair runs
- arena.ai run URL: side-by-side; this entry covers Option B only. Run hash `019dc819…` (distinct from the prior v3 B run hash `019dc738…`).

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: A brick-walled garden patio is shown from several viewpoints, with dense green plants, a wooden table, a tall vase, a black door, windows, paving stones, and a few garden ornaments. The views overlap but no camera metadata is provided.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

Identical structure to the prior v3 B probe. Scene description noticeably different — this run flagged the door, windows, and "garden ornaments" rather than the soccer ball that v3 A's probe spotted. Suggests the same model class but a fresh attention pass over the photos, not a memorized response.

## What's the same as v3 B run 1

- Stack: React 19 + Vite + Tailwind. `three` is in `package.json` deps but **never imported** in source — same as run 1. Custom WebGL2 anisotropic splat renderer in a single 813-line `App.tsx`.
- Probe → code mapping: every `yes` flag backed by a real implementation.
- Loud-error contract fully satisfied:
  - Shader compile-status check ([App.tsx:684](file:///tmp/v3-model-b-2-zip/src/App.tsx#L684))
  - Shader link-status check ([App.tsx:669](file:///tmp/v3-model-b-2-zip/src/App.tsx#L669))
  - `webglcontextlost` listener ([App.tsx:253-254](file:///tmp/v3-model-b-2-zip/src/App.tsx#L253))
  - `checkCanvasVisibility` + `readPixels` first-frame probe ([App.tsx:710-723](file:///tmp/v3-model-b-2-zip/src/App.tsx#L710))
- Implementation notes panel is comprehensive and matches the code.

## What's different (refinements over run 1)

The model converged on the same approach but improved several details:

1. **Adaptive stride** ([App.tsx:514](file:///tmp/v3-model-b-2-zip/src/App.tsx#L514)): `stride = max(2, ceil(sqrt(totalPixels / MAX_SPLATS)))`. Previous run used a fixed `SAMPLE_STRIDE = 6`. The adaptive form lets the splat budget scale cleanly with input resolution and produced **19,264 splats** vs run 1's 9,162.
2. **Depth blur pass** ([App.tsx:509](file:///tmp/v3-model-b-2-zip/src/App.tsx#L509)): `blurDepth(depth, width, height)` smooths the heuristic depth field before splat seeding. Reduces noise-driven splat-position jitter. Run 1 didn't blur.
3. **Slope-aware anisotropy** ([App.tsx:541-545](file:///tmp/v3-model-b-2-zip/src/App.tsx#L541)): `localSlope = |∇depth|` is fed into `scaleY` and `scaleZ`, so splats on steeper edges of the depth map are visibly elongated. Run 1's anisotropy was tied to image-space sampling spacing only.
4. **Hexagonal sample lattice** ([App.tsx:526](file:///tmp/v3-model-b-2-zip/src/App.tsx#L526)): odd rows are shifted by 1 (`x = 1 + ((y / stride) % 2 | 0)`), giving more uniform 2D coverage than a strict square grid.
5. **Empty-state honesty UI** (visible in screenshot 1): when no images are uploaded, the viewer panel reads *"No baked scene, no hidden assets — The deployed app cannot access the prompt images directly. Upload them to create splats from runtime pixel data."* This is the model **teaching the user** about the v3-disclosed channel constraint via UX copy. Voluntary; goes beyond what the prompt asks for.

## Rendered output

19,264 anisotropic Gaussian splats. The visible cloud reads as a coarse foliage / hedge / lawn surface — same character as run 1 but denser, with a slightly more horizontally-spread "garden floor" feel (the third screenshot shows what looks like grass+earth ground texture extended across the frame). Foreground table + vase still not separable from the dominant green-pixel background, which is the structural ceiling of this approach without real triangulation or pose recovery.

## Rubric scores (rubric v3)

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   3   | Clean deploy, viewer renders 19,264 splats, controls responsive, all error contracts wired. |
| 2. Actually 3DGS              |   3   | Anisotropic 3D Gaussians (3-axis non-uniform scale modulated by local depth slope, per-splat quaternion from depth-gradient surface normal). All three pixel-use flags genuinely backed. |
| 3. Reconstruction faithfulness|   2   | Recognizable foliage/lawn texture matching dominant input content; foreground objects still not separated. Same ceiling as run 1. |
| 4. Web app UX                 |   3   | Per-stage progress, comprehensive error UI, voluntary "No baked scene, no hidden assets" empty-state copy is a nice unprompted UX touch. |
| 5. Engineering judgment & honesty | 3 | Probe ↔ panel ↔ code consistent; runtime count from a variable; voluntary improvements over run 1 (adaptive stride, depth blur, slope-aware scale, hex lattice). |

**Total**: 14/15 (same as run 1).

## What this tells us

This run is the most useful single piece of v3 evidence we have so far — not because it's a different result, but because it's **the same result twice on what is almost certainly the same model**. Two independent runs with the same prompt + same images converged on:

- the same approach family (C)
- the same architecture (custom WebGL2 anisotropic splats from scratch, no `three` import)
- the same v3 contract elements (probe, loud-error stack, runtime count)
- the same axis-3 ceiling (faithfulness 2/3, can't separate foreground from background)
- different *engineering refinements* (adaptive stride, depth blur, slope-aware anisotropy, hex lattice, empty-state UX copy)

That's a healthy stability signal: the prompt is producing reproducible behavior on a fixed model, and the per-run variation lands in the "minor implementation polish" regime rather than "different approach altogether". The 14/15 score is reproducible.

## v4 implications

No new v4 trigger from this run — the prompt is doing its job; the failure modes left are downstream of what the prompt directly polices. The earlier observation about "approach-C faithfulness ceiling at 2/3 without real triangulation" still stands. To unlock axis 3 = 3, v4 would need to either:

- **Hint at Approach B more aggressively** (e.g. "If you have the choice between an honest C-approximation and a feed-forward sparse-view model loaded via `onnxruntime-web`, prefer B — it produces stronger faithfulness even at the cost of a ~50 MB model download"), or
- **Provide camera intrinsics or coarse poses** to relax the SfM-free constraint.

Both are larger design choices than what this single re-run motivates. Recommend continuing to hold v3 unless a third A/B pair surfaces a new failure mode.

# Run: Option A on prompt v3 with garden-table photos (run 4)

- Date: 2026-06-09
- Prompt version: v3
- Rubric version: v3
- Image set: 4 images; probe scene_description is a detailed garden-table scene (round wooden slatted table, ceramic vase with dried palm fronds, hexagonal pavers, hedges, brick walls, black door, green ball, house). Assumed the standard garden-table set — confirm exact filenames.
- arena.ai slot: Option A (per Alex).
- Source archive: `3d-gaussian-splatting-app (3).zip`.

> **Scoring discipline (blind).** Scored on the artifact alone — code, the provided screenshot, and the rubric. Model identity was **not** inferred and no other submission's fingerprint or score was used to anchor any axis. If Alex reveals the identity post-hoc it may be appended as a separate labeled line; it must not feed back into the scores.

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: A round wooden slatted garden table with a ceramic vase holding dried palm fronds/flowers, sitting on hexagonal paving stones in a backyard garden with hedges, brick walls, a black door, a green ball under the table, and a house visible in the background. Four photos taken from different angles around the table.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

## What the app produces

React / Vite / Tailwind, three-file split (`App.tsx`, `reconstruction.ts`, `splatRenderer.ts`), Approach C. The reconstruction is a **genuine multi-view plane-sweep**: virtual cameras on a heuristic circle (radius 4, height 1.5, FOV 50°); for each stride-4 pixel, 48 depth hypotheses are tested by projecting the candidate 3D point into every other view and comparing bilinear-sampled RGB via SSD; lowest cross-view difference wins. Splat color from the reference pixel, orientation as a quaternion facing the capturing camera, anisotropic disc scale from the pixel footprint, opacity from photo-consistency confidence / √N. Rendering is a custom Three.js `RawShaderMaterial` EWA splat shader (`Σ=RSSᵀRᵀ` → camera space → perspective-Jacobian 2D conic → premultiplied alpha, back-to-front sorted). Reports **15,600 splats**.

**The viewer renders nothing** — canvas shows only the clear color (`0x1a1a2e`) — and the app's own post-first-frame pixel probe fired: *"Renderer produced no visible primitives — canvas shows only the clear color."*

## Rubric scores (rubric v3) — artifact only

| Axis | Score | Note (this artifact only) |
|------|-------|---------------------------|
| 1. Deployed & runs | **1** | Deploys and runs the full pipeline (screenshot: processing completes, 15,600 splats counted), but the viewer is a blank canvas — the rubric's "1" (deploys but visibly broken; "Ready" status over an empty viewer). Not 0 (deploy succeeded). The honest error-surfacing is credited on axes 4/5, not here. The v3 hard-cap-at-1 clause is moot since the app *did* surface the failure. |
| 2. Actually 3DGS | **3** | Genuine anisotropic 3D Gaussians by code: per-splat quaternion + 3D scale (disc, normal axis 0.15×), real EWA covariance-projection shader, premultiplied back-to-front. Geometry genuinely pixel-derived via real plane-sweep MVS — the most principled Approach-C geometry, emphatically *not a fake*. The display bug is penalized on axes 1/3, not double-counted here. *Caveat: a judge requiring visual confirmation of the primitives could read this lower since nothing renders; code inspection (which the rubric explicitly permits) supports 3.* |
| 3. Reconstruction faithfulness | **0** | Rubric: "nothing renders" = 0, explicitly. The viewer is blank; the scene is unrecognizable from any angle because there is nothing to see. Internally sound geometry doesn't earn faithfulness points when there's no viewable output. |
| 4. Web app UX | **3** | Every v3 error/UX deliverable present **and working**: staged progress (spinner + % + per-image messages), `window` error/rejection listeners, reconstruction try/catch with stage UI + retry, shader-compile check, `webglcontextlost` handler, and the post-first-frame pixel-visibility probe — which **fired correctly and surfaced the failure with a clear message**. That is exactly the silent-black-canvas catch v3 was built to reward. Orbit controls + sensible default camera wired. Blank-viewer outcome penalized on 1/3. *Caveat: a judge weighting holistic "usable viewer" into UX could give 2.* |
| 5. Engineering judgment & honesty | **3** | Probe ↔ panel ↔ code tightly consistent; every named technique (plane-sweep photo-consistency, orient-toward-camera quaternion, footprint-based anisotropic scale, confidence/√N opacity, EWA shader, Three.js for scene/controls) has a real implementation. Runtime count via `getGaussianCount()`. Caveats disclosed plainly — including pre-disclosing that heuristic poses produce noisy depth. No fabricated libraries. "Ready to view" is not dishonest because the render failure is surfaced simultaneously. The render bug is an execution failure, not a judgment/honesty one. |

**Total: 10/15** (conservative floor **8** if axes 2 and 4 are each read one tier lower for the non-rendering viewer).

## Failure mode

A genuine **zero-visible-output render bug** in the custom Three.js `RawShaderMaterial` splat path. The pipeline, the 15,600 count, and the geometry are all real (authentic MVS), but nothing draws. The shader math traces as largely *correct* by inspection (covariance, Jacobian, conic, premultiplied blending, near-plane cull, camera framing all check out), so this is not an obvious coordinate/sign flip — the cause is subtle (candidate areas: Three.js instanced-attribute binding under `RawShaderMaterial`, or a covariance/`rad` degeneracy under real data) and was **not pinned by static analysis**; pinning it would need a runtime GLSL debug session. The headline behavior: the app **caught its own failure and reported it loudly** — the intended v3 outcome.

## Implications for next prompt version

None triggered. This run is a **positive datapoint for v3's loud-error contract specifically**: a real reconstruction that failed at the render stage was converted from a silent black canvas into a loudly-attributed, dismissible error — which is precisely what the contract was added to force. No prompt change indicated by this artifact.

---

## Post-hoc identity (revealed by Alex after scores were locked — does NOT change the scores above)

**Option A = `claude-opus-4-6-thinking`.**

Longitudinal note (post-hoc analysis only; not a scoring input): this is the **second** v3 / garden-table run for this model — prior is [`2026-04-26_model-A_v3_garden-table_run3.md`](2026-04-26_model-A_v3_garden-table_run3.md) at 7/15. Both runs carry the same signature: the most ambitious and most honestly-described Approach-C geometry in the corpus (real multi-view plane-sweep MVS) + a fully-wired loud-error contract + **exactly one fatal execution bug that zeroes the visible output**, surfaced cleanly each time. The bug moved *downstream* between runs — run 3 it was in geometry (`projectPoint`/`unprojectPixel` Z-convention flip → triangulation behind the cameras → zero Gaussians generated); run 4 it is in the renderer (zero visible primitives despite 15,600 genuinely-generated MVS splats). The 7→10 movement tracks the bug relocating downstream: run 4's geometry stage *succeeds*, so axis 2 (genuine 3DGS, code-confirmable) and the real runtime count are earned even though faithfulness is still 0. N=2, clean comparison (same model / prompt / image set); the qualitative signature is robust, the 3-point delta is tentative.

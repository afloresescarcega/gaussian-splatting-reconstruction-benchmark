# Run: Model A on prompt v3 with garden-table photos (run 3)

- Date: 2026-04-26
- Prompt version: v3
- Rubric version: v3
- **Model identity (revealed post-run): `claude-opus-4-6-thinking`** — first observation of this model in the benchmark.
- Image set: 4 garden-table photos (DSC07956 / DSC07970 / DSC07986 / DSC08001) — same set as the v1, v2, and previous v3 runs.
- arena.ai run URL: side-by-side; Option A only. Same A/B round as the v3 B run 3 above; Option B was submitted ~17 min earlier.

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: A round wooden slatted garden table with a ceramic vase holding dried flowers/leaves on top, sitting on a paved patio in a backyard garden with hedges, brick walls, and a house visible in the background. Photographed from 4 angles around the table.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

Scene description is accurate but generic ("dried flowers/leaves" misses the dried-palm-fronds specificity sonnet-4-6 caught; "round wooden slatted" gets the form factor right). All three pixel-use flags claimed `yes` — backed by real (but buggy) code paths, see Diagnosis below.

## What the model produced

**Stack**: React 19 + Vite + Three.js (WebGLRenderer + OrbitControls) + custom GLSL shaders. **Three-file split**: `App.tsx` (318 LoC, UI + drop zone + error UI + impl-notes panel + global error handlers), `reconstruction.ts` (762 LoC, full geometry pipeline), `renderer.ts` (495 LoC, custom anisotropic-Gaussian splatting layered on top of Three.js). Tailwind / clsx / tailwind-merge declared in `package.json` but unused (inline styles only).

**Pipeline implemented in code** (every panel bullet maps to a real function):

1. Load + downsample to maxWidth=400 → grayscale via 0.299/0.587/0.114 weights ([reconstruction.ts:52](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L52))
2. Harris corner detection, Sobel-like gradients, 3x3 window, k=0.04, NMS radius 5, top 500 features per image ([reconstruction.ts:85](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L85))
3. Normalized 8x8 patch descriptors per feature (16-pixel patch sampled into 8x8 cells, mean-subtracted, L2-normalized) ([reconstruction.ts:149](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L149))
4. Cross-image L2 matching with Lowe's ratio (0.75) + mutual-consistency check ([reconstruction.ts:192](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L192))
5. **Assumed circular cameras** at radius 3.0, height 1.0, fov 60° (disclosed shortcut) ([reconstruction.ts:250](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L250))
6. Ray-intersection triangulation with reprojection-error rejection (>15 px) + bounding-volume rejection (>15 from origin) ([reconstruction.ts:344](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L344))
7. Plane-sweep MVS: 32 inverse-depth hypotheses ∈ [0.5, 8.0], 7x7 NCC across all other views, confidence threshold 0.25, sample stride=6 ([reconstruction.ts:457](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L457))
8. Surface normals from depth gradient (finite differences, R^T transform to world) ([reconstruction.ts:678](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L678))
9. Anisotropic disk Gaussians: sx=sy=baseScale, sz=0.3·baseScale, oriented by depth-gradient normals; sparse points use fixed up-axis (honestly disclosed) ([reconstruction.ts:743](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L743))
10. Custom GLSL vertex shader: 3D covariance from quaternion+scale, view-space Jacobian, 2D eigendecomp for screen-space ellipse axes, 3-sigma quad ([renderer.ts:13](file:///tmp/v3-model-a-3-zip/src/renderer.ts#L13))
11. Premultiplied-alpha fragment shader, CPU back-to-front sort + sorted-buffer reupload each frame ([renderer.ts:397](file:///tmp/v3-model-a-3-zip/src/renderer.ts#L397))

**Loud-error contracts (all three correctly wired)**:

- `webglcontextlost` listener ([renderer.ts:207](file:///tmp/v3-model-a-3-zip/src/renderer.ts#L207))
- Shader compile/link check via `THREE.WebGLRenderer.compile()` + console.error capture ([renderer.ts:351](file:///tmp/v3-model-a-3-zip/src/renderer.ts#L351))
- Post-frame canvas check: 50 random pixels via `gl.readPixels(rx, ry, 1, 1, …)` collected and compared to background `(26, 26, 46)` ±10 tolerance, fires 800 ms after first render ([renderer.ts:372](file:///tmp/v3-model-a-3-zip/src/renderer.ts#L372)) — **algorithm correct**, unlike sonnet-4-6's run-2 buggy version that re-read a fixed 10x5 block instead.
- Plus `window.addEventListener('error')` and `unhandledrejection` global handlers ([App.tsx:27](file:///tmp/v3-model-a-3-zip/src/App.tsx#L27))
- Cooperative scheduling: `await new Promise(r => setTimeout(r, 0))` between phases including inside the per-image dense-stereo loop. No browser freeze.

This is the most complete Approach-C pipeline we've seen across both A and B columns: real Harris, real patch descriptors, real two-direction matching, real triangulation with reprojection check, real plane-sweep MVS with NCC, real depth-gradient normals, real custom-GLSL anisotropic renderer with proper covariance projection. On paper this should outscore both prior v3 A runs.

## What it produced at runtime

**Zero Gaussians.** The pipeline runs to completion, the renderer is initialized, no shader errors, no context loss — but at the end of `reconstruct()` the gaussians array is empty and the explicit `if (gaussians.length === 0) throw new Error('Reconstruction produced zero Gaussians. The images may not have enough overlap or texture for matching.')` ([reconstruction.ts:758](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L758)) fires.

The error propagates into `App.tsx`'s try/catch, which sets `error` state to `Reconstruction failed: Reconstruction produced zero Gaussians. The images may not have enough overlap or texture for matching.` and `status` to `Reconstruction failed`. Both are surfaced in the UI: a red banner across the top with the full message, and the status text in the header. The drop-zone overlay returns ("Drop images here or click Upload" + camera icon) because `gaussianCount === 0 && !isProcessing`. The implementation-notes panel stays expanded on the right showing the unrendered pipeline description.

This is structurally the cleanest failure-mode display of any run so far: stage-attributed, hypothesis-suggesting, recoverable (the user can re-upload), no false-success claim. The v3 loud-error contract did exactly what it was designed to do.

## Diagnosis: silent coordinate-convention sign bug

The "not enough overlap or texture" hypothesis the error message suggests is wrong. The 4 garden-table photos have plenty of overlap and texture (the v3 B runs derive 9k–19k splats from the same set). The actual cause is an internal coordinate-system inconsistency between `projectPoint` ([reconstruction.ts:312](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L312)) and `unprojectPixel` ([reconstruction.ts:330](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L330)).

`createCircularCameras` builds the world-to-camera rotation matrix with row 2 = `-fwd` ([reconstruction.ts:288-292](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L288)):

```ts
const R = [
  [right[0], right[1], right[2]],
  [up[0], up[1], up[2]],
  [-fwd[0], -fwd[1], -fwd[2]],
];
```

This is standard OpenGL: third row = `-fwd`, so the camera looks along **negative** view-space Z. With the camera at (0, 1, 3) looking at origin, `fwd ≈ (0, -0.32, -0.95)` and `R[2] ≈ (0, 0.32, 0.95)`.

But `projectPoint` ([reconstruction.ts:318-319](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L318)) checks for `cz > 0` — i.e. it expects the camera to look along **positive** Z:

```ts
const cz = cam.R[2][0] * dx + cam.R[2][1] * dy + cam.R[2][2] * dz;
if (cz <= 0.01) return null; // behind camera
```

For a point at the origin viewed from camera 0, `cz = 0·0 + 0.32·(-1) + 0.95·(-3) ≈ -3.2`. So `projectPoint` returns null and the origin is treated as "behind the camera" even though the camera is literally pointed at it.

`unprojectPixel` ([reconstruction.ts:332-340](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L332)) inherits the same flipped convention: `camZ = depth` (positive), then transforms via `R^T` and adds `cam.position`. The result lands behind the camera in world space rather than in front of it.

**Cascading consequences** that produce the zero-Gaussian outcome:

- **Triangulation** ([reconstruction.ts:344](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L344)): ray directions in world space are `R^T·(uv_normalized, 1)` which equals the third row of `R^T` (which is `-fwd`) plus image-plane offsets. So the rays point *away* from the scene origin. For non-degenerate camera pairs the rays diverge → either `t1 < 0` rejection at line 388 or `denom ≈ 0` parallel-ray rejection at line 383. For axially-opposite pairs the rays are anti-parallel → `denom ≈ 0`. Net: `triangulateRayIntersection` returns null for every match → `sparsePoints` is empty after the loop.
- **Plane-sweep MVS** ([reconstruction.ts:457](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L457)): for every reference pixel and every depth hypothesis, `unprojectPixel` produces a world point behind the reference camera. `projectPoint(worldPt, otherCams[oi])` then returns null for every other camera (point is behind them too, given the assumed circular arrangement). `nccCount` stays 0 → `bestNCC` stays at -1 → `bestDepth` stays at 0 → the unprojection step at line 658 is gated by `confidences[si] < confThreshold` (0.25) which rejects everything. Net: `densePoints` is empty.
- **Final assembly**: 0 sparse + 0 dense = 0 Gaussians → throws.

The honest-caveats panel pre-warned the *meta-cause* ("Camera poses are assumed (equally spaced on a circle), NOT estimated from images — reconstruction quality depends heavily on how well this matches reality"), and that warning is genuinely correct: the assumed-pose shortcut would degrade quality even in a working pipeline. But the actual failure isn't pose-mismatch with reality — it's an internal sign bug between `projectPoint` and `unprojectPixel` that would have produced zero Gaussians **even with perfectly-correct camera poses**. The error message attributes the failure to "not enough overlap or texture" — also wrong; the real cause is upstream of any pixel-comparison code.

## Probe ↔ panel ↔ code consistency

Probe block, on-screen impl-notes panel, and code structure are tightly aligned at the *design* level:

- Panel claim: "Harris corner detection for sparse feature extraction" → `detectCorners` ✅
- Panel claim: "Normalized 8x8 patch descriptors per feature" → `computeDescriptor` ✅
- Panel claim: "Cross-image feature matching with L2 distance, Lowe's ratio test (0.75), and mutual consistency check" → `matchFeatures` ✅
- Panel claim: "Assumed circular camera arrangement (shortcut: …)" → `createCircularCameras` ✅
- Panel claim: "Ray-intersection triangulation of matched features" → `triangulateRayIntersection` ✅
- Panel claim: "Plane-sweep multi-view stereo: 32 inverse-depth hypotheses per sample, NCC photo-consistency with 7x7 patches across all other views" → `planeSweepStereo` + `computeNCC` ✅
- Panel claim: "Surface normal estimation from depth gradient (finite differences on depth map, transformed to world space)" → normal-estimation block at [reconstruction.ts:678](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L678) ✅
- Panel claim: "Anisotropic Gaussians: disk-shaped (flat along surface), oriented by depth-gradient normals, colored from pixel RGB" → Gaussian assembly at [reconstruction.ts:743](file:///tmp/v3-model-a-3-zip/src/reconstruction.ts#L743) ✅
- Panel claim: "Custom vertex shader: 3D covariance from quaternion+scale, view-space projection via Jacobian, 2D eigendecomposition for oriented screen-space ellipses" → VERTEX_SHADER ✅
- Panel claim: "Per-frame back-to-front depth sorting of all Gaussians" → `sortAndUpdate` ✅
- Panel "Honest caveats" section (assumed poses, no SfM/BA, no learned models, depth quality depends on possibly-wrong poses, point overlap, heuristic scale, sparse points use fixed up-orientation) — all accurate descriptions of the code.
- Gaussian count in panel reads from React state `gaussianCount` (set from `gaussians.length`), not hardcoded.

The probe-panel-code mapping is among the cleanest we've seen. The pipeline is honestly described, the libraries are correctly listed, the shortcuts are flagged. The mismatch between *intent* and *runtime output* lives entirely in the coord-sign bug — a load-bearing math error inside a function the panel correctly names. This is a different class of problem from sonnet-4-6's "panel describes a step that exists but isn't wired into output"; here the step is wired correctly but the math is broken.

## Comparison vs v3 A runs 1 & 2

| | run 1 (qwen) | run 2 (sonnet-4-6) | run 3 (opus-4-6-thinking) |
|---|---|---|---|
| File structure | 1 file, 586 LoC | 3 files, 1628 LoC | 3 files, ~1575 LoC |
| Pipeline ambition | feature detect + brute match + triangulation + grid fallback | Harris + NCC + triangulation + KNN normals + (unwired dense step) | Harris + 8x8 patch L2 + ratio + mutual + plane-sweep MVS with NCC + depth-gradient normals |
| Image preprocessing | full-res, no downsample | OffscreenCanvas downsample | maxWidth = 400 px |
| Cooperative scheduling | none — main thread froze | yields, no freeze | yields incl. inside per-image MVS loop, no freeze |
| Loud-error contracts | none reachable | wired, but visibility probe reads wrong buffer | **all three wired correctly** |
| `three` declared | yes (+ R3F + drei + dead gsplat dep) | yes | yes |
| `three` actually imported | yes (R3F path) | yes (per panel, used as math util) | yes (`WebGLRenderer` + `OrbitControls` + `ShaderMaterial`) |
| Splats produced | 0 (browser locked at "Start Reconstruction") | 792 (sparse, dense step never feeds output) | 0 (every triangulation/NCC sample rejected by coord sign bug) |
| Failure visibility | "Page Unresponsive" Chrome dialog | false-positive "renderer produced no visible primitives" warning + working render | clean stage-attributed "Reconstruction failed: zero Gaussians" banner |
| Probe ↔ panel ↔ code | strongest mapping (every bullet to a function) | mostly-correct, one partial mismatch (dense step) | strong mapping; bug lives inside a correctly-named function |
| Score | 3/15 | 10/15 | 7/15 |

Three runs in, the v3 A column has produced three structurally distinct pipelines (single-file vs three-file with custom WebGL2 vs three-file on top of Three.js) with three distinct failure modes (main-thread freeze vs sparse-output bug vs zero-output coord bug). The v3 prompt is producing varied A-side behavior; what's *not* varying is that each A-side run lands in the 3–10/15 range while v3 B (gpt-5.5, confirmed across all three runs) is 14/15 across three reproductions.

## Rubric scores (rubric v3)

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   1   | Deploys cleanly, page stays responsive throughout, upload + processing both work — but no viewable scene is reached. Better than run 1's freeze (0), worse than run 2's sparse-but-real splats (2). The v3 hard-cap clause doesn't apply because the app correctly surfaced the failure rather than claiming a false-success "ready" state. |
| 2. Actually 3DGS              |   2   | Code defines real anisotropic disk Gaussians (sx=sy>>sz), real custom-GLSL covariance projection with Jacobian + 2D eigendecomp, all three pixel-use flags backed by real (but buggy) code paths. Capped at 2 because the runtime never displays anything; same logic as run 1's cap — on a fixed-coord-convention run the same code would score 3. |
| 3. Reconstruction faithfulness|   0   | Nothing rendered to evaluate. |
| 4. Web app UX                 |   2   | Excellent loud-error reporting (the contract worked exactly as v3 designed: stage attribution, plain-language hypothesis, recoverable). Upload UI clean, drag-drop works, progress bar sensible during processing, impl-notes panel well-organized and collapsible. Docked from 3 because orbit controls / default camera / "smooth interaction" are untestable on an empty scene. |
| 5. Engineering judgment & honesty | 2 | Probe ↔ panel ↔ code consistency among the strongest of any run — every panel bullet maps to a real function, gaussian count is a runtime read, all caveats accurate, no fabricated dependencies. Single critical execution-level bug (coord sign mismatch between `projectPoint` and `unprojectPixel`) breaks the entire pipeline. Same score class as sonnet-4-6 run 2 (also "honest design, execution-level bug"); the bug here is upstream of where sonnet-4-6's bugs lived. |

**Total**: 7/15.

## What this run contributes

This is the first observation where the v3 loud-error contract was **both fully wired AND legitimately exercised against a real reconstruction failure**:

- v2 B (gpt-5.4-high) had the failure mode v3's loud-error contract was designed to catch (silent black canvas + "Ready" status), but pre-dated the contract.
- v3 B runs 1, 2, 3 (gpt-5.5) wire the contract correctly — but always succeed, so the contract never fires in earnest.
- v3 A run 1 (qwen) never reaches the contract (browser hangs first).
- v3 A run 2 (sonnet-4-6) wires the contract but the visibility probe fires *falsely* — the renderer is actually working.
- **v3 A run 3 (this)** wires the contract correctly AND fails legitimately. The user gets a stage-attributed "Reconstruction failed: …" banner instead of an empty viewer with a misleading status. From a benchmark-design perspective, this is the cleanest evidence that the v3 contract delivers what it's supposed to deliver.

It also adds a third A-side pipeline architecture to the corpus (Three.js-as-WebGL-host with custom shaders, vs qwen's R3F-as-scene-graph and sonnet's hand-rolled WebGL2). Useful spread for understanding what "Approach C" looks like across model temperaments.

## Implications for v4

This run contributes one new pattern that hasn't surfaced before in the v4 design discussion:

- **Coordinate-convention internal-inconsistency bug** producing silent zero-output. Probe block, panel claims, and code structure are all honest and aspirationally correct; one math-bug-pair between two adjacent functions breaks the entire pipeline.
- v4 prompt cannot directly enforce internal coordinate consistency (that's a code-review concern, not a prompt concern). But v4 *could* require a small smoke-test step: e.g. *"After camera setup, project the world origin (or any well-defined test point) through each camera's `projectPoint`; if the projection fails for a camera that visibly should see it, surface a 'camera-projection self-test failed' error with the camera index. Don't proceed to triangulation or stereo if the self-test fails."* This catches the exact bug here (and the symmetric `projectPoint`/`unprojectPixel` inconsistency more generally) without forcing a specific coordinate convention.
- Alternatively (less prescriptive), keep v3 as-is. The error message in this run was clear enough that a human user can diagnose "the pipeline ran but produced nothing" — the rubric already caps axis 1 at 1 in that case. The marginal value of policing coord conventions in the prompt may be less than the cost of additional clauses.

The previously-identified v4 candidates from runs 1 and 2 still stand and aren't moved by this run:

- **Cooperative-scheduling clause** (qwen failure) — this run already does it correctly; the prompt clause would be defensive against models that don't.
- **Visibility-probe algorithm sketch** (sonnet failure) — this run already does it correctly; the clause would help models that wire the contract but botch the algorithm.
- **"Panel step must feed splats" rule** (sonnet failure) — not relevant here; this run's panel matches code at the wiring level.
- **Approach-C density floor** (sonnet sparsity) — not relevant when output is exactly 0.

## Recommendation: hold v3

We've now seen v3 produce six distinct outcomes across two columns:

- v3 B run 1, 2, 3 (gpt-5.5, confirmed; three reproductions of 14/15): all contracts correct, dense reconstruction, structural ceiling at 14.
- v3 A run 1 (qwen3.5-397b-a17b, 3/15): main-thread freeze.
- v3 A run 2 (claude-sonnet-4-6, 10/15): everything wired honestly, visibility probe buggy, dense step unwired, splats too sparse.
- v3 A run 3 (claude-opus-4-6-thinking, 7/15): everything wired honestly and contracts implemented correctly, single coord-convention bug produces zero output, error reporting is the cleanest we've seen.

The v3 prompt is producing a useful spread of behaviors and a useful spread of failure modes. The B-side ceiling is reproducible (same model, same approach, three same scores). The A-side is varied — three different models, three different architectures, three different bug classes. Each A-side run is teaching us something specific about a *different* model's defaults.

A v4 bump now would risk over-fitting to the union of A-side bugs we happen to have observed. A pattern that recurs across multiple models is what should drive v4 — and so far the recurring pattern is "the prompt does what it's supposed to do; individual models bring their own bug class". I'd hold v3 and run one more A/B pair (different image set, or repeat this set with different models) before committing to v4.

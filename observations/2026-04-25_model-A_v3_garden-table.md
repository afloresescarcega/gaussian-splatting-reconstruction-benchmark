# Run: Model A on prompt v3 with garden-table photos

- Date: 2026-04-25
- Prompt version: v3
- Rubric version: v3
- **Model identity (revealed post-run): `qwen3.5-397b-a17b`** (397B-parameter MoE, 17B active per token)
- Image set: 4 garden-table photos — same set as the v1, v2, and v3 B runs
- arena.ai run URL: side-by-side; this entry covers Option A only

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: Garden patio scene with round wooden table, decorative vase with dried palm fronds, green soccer ball under table, brick walls with ivy, green hedges, black shed door, stone pavers, captured from 4 viewpoints.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

The scene description is more detailed and accurate than v3 B's — even noticed the green soccer ball under the table. All three pixel-use flags backed by real code paths (verified below).

## What the model produced

**Stack**: React 19 + Vite + Tailwind + `three` + `@react-three/fiber` + `@react-three/drei` + `gsplat`. Single 586-line `App.tsx`. Note: `gsplat` is declared as a dependency but never imported in source — dead dep.

**Pipeline implemented in code**:

1. For each image: build a full-resolution `<canvas>` (`canvas.width = images[i].naturalWidth`).
2. `detectFeatures` ([App.tsx:27](file:///tmp/v3-model-a-zip/src/App.tsx#L27)): grid-sample with step=15, compute `(gx, gy)` from horizontal/vertical brightness gradients, keep pixels with gradient magnitude > 0.08.
3. Estimate camera poses on a circular `(2.5·cos θ, 0.3 + 0.3·sin(θ/2), 2.5·sin θ)` arc.
4. `matchFeatures` ([App.tsx:44](file:///tmp/v3-model-a-zip/src/App.tsx#L44)): for each pair of consecutive views, brute-force O(N×M) nearest-neighbor match with brightness threshold + spatial threshold.
5. For each match, **triangulate** by intersecting view-rays from the two estimated poses, derive a 3D point + sample its color from the source pixel.
6. Grid-sample brightness-derived depth ([App.tsx:124-155](file:///tmp/v3-model-a-zip/src/App.tsx#L124)): unproject every 25-pixel grid point through the camera pose at brightness-derived depth.
7. Each splat gets a quaternion from `setFromUnitVectors([0,0,1], lookAt)` where lookAt is the camera→point direction (genuine pixel/camera-derived orientation).

The implementation describes a **more ambitious** pipeline than v3 B (real feature detection, real two-view triangulation, real grid-sampled fallback). On paper, this should yield better axis-3 faithfulness than v3 B's heuristic-only approach.

## Why it failed: main-thread compute deadlock

Alex got Chrome's "Page Unresponsive" dialog. Implementation Notes panel showed `Gaussian Count: 0` (the React state never updated past idle because the main thread was blocked).

The cause is a stack of textbook performance footguns, all running synchronously on the main thread, with no Web Worker offload, no `requestIdleCallback` yielding, and no input downsampling:

1. **Full-resolution `<canvas>`** ([App.tsx:68-69](file:///tmp/v3-model-a-zip/src/App.tsx#L68)). User-uploaded photos are 4000+ px on the long side. The decoding step alone allocates ~50–100 MB per image as `Uint8ClampedArray` for `getImageData`.
2. **`detectFeatures` at full res** ([App.tsx:74](file:///tmp/v3-model-a-zip/src/App.tsx#L74)). With step=15, ~`(W/15) × (H/15) ≈ 70k–80k` iterations per image. Manageable on its own, but produces feature lists in the high thousands per image at the 0.08 gradient threshold.
3. **`matchFeatures` is O(N×M)** ([App.tsx:44-56](file:///tmp/v3-model-a-zip/src/App.tsx#L44)) and runs four times (each image vs the next). With 5–15k features per image, that's 25M–225M comparison ops, each calling `Math.sqrt`. No spatial index, no nearest-neighbor structure.
4. **Per-match `getImageData(x, y, 1, 1)`** ([App.tsx:116](file:///tmp/v3-model-a-zip/src/App.tsx#L116)). This is a textbook performance trap: each call forces a CPU↔GPU readback. Up to 600 calls (150 matches × 4 image pairs) — each one stalls the rasterizer.
5. **O(N²) duplicate filter** ([App.tsx:140-142](file:///tmp/v3-model-a-zip/src/App.tsx#L140)). For every grid-sampled splat, scan *all existing splats* with `position.distanceTo(...)` to reject duplicates within 0.06 units. With ~2k–5k splats per image × 4 images, that's 50M–400M `distanceTo` calls. No spatial hash, no early termination.
6. **Whole pipeline awaitless.** The function is `async` only in name. There's no `await new Promise(r => setTimeout(r, 0))` between heavy phases, so the React UI never repaints — the "Gaussian Count: 0" frozen value is exactly that. Chrome's main-thread watchdog eventually triggers "Page Unresponsive".

Any one of (3), (4), or (5) alone is enough to hang a multi-megapixel input. Combined, the deployment is unusable on real photos.

**Note on v3's loud-error contract**: this failure mode is *outside the contract's coverage*. v3 requires shader-compile checks, contextlost listeners, and post-frame pixel sampling — all of which assume the renderer eventually runs. A frozen main thread can't surface an error because there's no event loop slack to dispatch one. v4 needs to address this directly (see implications below).

## Probe-vs-panel-vs-code consistency

The implementation notes panel describes:
- "Detects gradient features in uploaded images" → `detectFeatures` ✅
- "Matches features across consecutive view pairs" → `matchFeatures` ✅
- "Estimates camera poses (circular arrangement)" → pose loop at line 80 ✅
- "Triangulates 3D positions from matched features" → ray-intersection at line 102-110 ✅
- "Reads RGB color from image pixels" → line 117, 150 ✅
- "Orients splats toward average camera position" → line 165 ✅
- "Uses anisotropic scales for ellipsoidal Gaussians" → `[base, base·1.15, base·0.75]` ✅
- "Adds depth-heuristic splats from grid sampling" → line 124-155 ✅

**Every panel claim has a real code path.** Probe block, panel, and code all agree. This is the cleanest probe-panel-code consistency we've seen — and it's the v3 prompt's biggest design win, completely independent of whether the runtime succeeds.

The "Shortcuts" subsection is also honest:
- "Camera poses heuristic (circular), not SfM" ✅
- "No bundle adjustment" ✅
- "Depth from brightness heuristic" ✅
- "No adaptive density control" ✅
- "Single-pass, no optimization loop" ✅

## Rubric scores (rubric v3)

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   0   | Browser locks up at "Start Reconstruction"; user cannot reach a viewable state. Deployed cleanly but does not run. |
| 2. Actually 3DGS              |   2   | Code defines anisotropic 3D Gaussians correctly (non-uniform 3-axis scale, per-splat quaternion from `setFromUnitVectors`). All three pixel-use flags genuinely backed. Two-view triangulation present in code. Score capped at 2 because the runtime never displays anything; on a successful run the same code would score 3. |
| 3. Reconstruction faithfulness|   0   | Nothing rendered to evaluate. |
| 4. Web app UX                 |   0   | Worst UX outcome of any run so far: not just a black canvas but a frozen browser. v3's loud-error contract can't catch a frozen main thread. |
| 5. Engineering judgment & honesty | 1 | Probe and panel honest and faithful to code (best probe-panel-code agreement we've seen). But "Picked a sensible approach for the constraint" is the load-bearing test of axis 5, and full-res `getImageData` + O(N²) matching + O(N²) dedup + per-match GPU readback all on the main thread is a textbook mismatch with a browser-deployed app. |

**Total**: 3/15.

## v3 A vs v3 B (head-to-head, same prompt and image set)

| Concern | v3 A | v3 B |
|---------|------|------|
| Probe-panel-code consistency | strongest of any run (every panel bullet maps to a real function) | excellent; matches code with voluntary self-check |
| Probe accuracy | accurate; even noticed the green soccer ball | accurate |
| Pipeline ambition | feature detection + brute-force matching + two-view triangulation + grid fallback | Sobel + saturation + luminance + vertical heuristic depth + depth-gradient normals |
| Pipeline runtime feasibility | hangs the browser on first click | completes in seconds, renders 9162 splats |
| Stack | three + R3F + drei + gsplat (dead dep) | pure React + custom WebGL2 (no Three.js) |
| Image preprocessing | full-resolution canvas, no downsample | downsamples to 360 px on long side ([App.tsx:80](file:///tmp/v3-model-b-zip/src/App.tsx#L80)) |
| Async cooperative scheduling | none — single synchronous run | yields with `setTimeout(resolve, 0)` between image-decode steps |
| Total | 3/15 | 14/15 |

**The same v3 prompt, same image set, same time slot — produces a 14-point spread.** The probe block confirms both models *understood* the task identically; the difference is entirely in runtime engineering judgment.

This is also the second time A has ranked far below B on this benchmark (v2 A: 3/15; v2 B: 8/15). The "A is the ambitious one" pattern from v1 isn't holding. arena.ai's labels are reshuffled per run.

## Implications for v4

A new failure mode just surfaced that v3 cannot directly catch: **main-thread freeze**. The v3 loud-error contract is renderer-stage; it assumes the page is alive. A model that runs heavy synchronous compute can hang the page before the renderer is even reached.

Concrete v4 changes:

1. **Add a "main-thread cooperative scheduling" requirement.** Phrase as: *"Your reconstruction must yield to the event loop at least every 100 ms. Use a Web Worker, `requestIdleCallback`, or `await new Promise(r => setTimeout(r, 0))` between heavy phases. The deployed app must remain responsive to user interaction (e.g. orbit controls, status updates) throughout reconstruction. If the page goes unresponsive, that is treated as a deploy failure."*
2. **Add an input-downsample requirement.** *"Downsample uploaded images to ≤512 px on the long side before any per-pixel work. Full-resolution photos can exceed 50 MB of `Uint8ClampedArray`; processing them on the main thread is not viable."*
3. **Forbid full-resolution `getImageData` in inner loops.** *"Avoid `getImageData(x, y, 1, 1)` per match/sample — call `getImageData` once per image at the working resolution and index into the array."*
4. **Forbid O(N²) algorithms over feature/splat sets without an index.** *"If you write a nested loop over features or splats, justify the inner loop's complexity. For nearest-neighbor matching or duplicate filtering, use a grid hash, KD-tree, or accept that you can't run the algorithm in a browser."*

These are prescriptive in a way the prompt has avoided so far. The tradeoff: more constraints reduce the model's freedom to surprise us, but this run is evidence that the freedom-to-fail-this-way isn't producing useful signal — both v2 A and v3 A made the same class of runtime-feasibility mistake, just in different forms (markdown syntax → main-thread freeze).

Alternative softer move: keep v3 prompt as-is but extend the rubric so that **`uses_input_pixels_at_runtime: yes` flags + main-thread-freeze in deployment = axis 5 cap of 1**, treating the freeze as a probe-vs-reality mismatch (you said you'd use the pixels, but the runtime never reaches the use). This is less prescriptive in the prompt but bites just as hard at scoring time. Worth considering before adding hard constraints.

## Recommendation: hold v3 unless a third pattern emerges

Two A/B pairs in, the v3 prompt has produced exactly one >12/15 result. The probe block, panel-code consistency, anti-Markdown clause, and granular pixel-use disclosure are all working as intended. The remaining failure modes (main-thread freeze, heuristic depth limits) live downstream of what the prompt can directly police — they're engineering-quality issues that better prompts can nudge but not eliminate.

I'd suggest one or two more A/B pairs (different image sets or different runs of the same set) before committing to v4. If a *third* category of failure surfaces, it's a clear v4 trigger; if the next runs split between "v3 B-class success" and "v3 A-class main-thread freeze", v4's job is mostly the prescriptive cooperative-scheduling clause from (1) above.

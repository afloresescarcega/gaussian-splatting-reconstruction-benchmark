# Run: Model A on prompt v1 with garden table photos

- Date: 2026-04-25
- Prompt version: v1
- Rubric version: v1
- **Model identity (revealed post-run): `gemini-3.1-pro-preview`**
- Image set: 4 garden-table photos (round wooden table with vase, brick patio); user-shot or sourced. Same set as the side-by-side B run.
- arena.ai run URL: side-by-side A/B; this entry covers Option A only.

## What the model produced

Approach **B** (feed-forward inference). Real ML libraries pulled in:
- `@xenova/transformers` running **Depth-Anything** for monocular depth estimation in WASM.
- `gsplat.js` (WebGL2 splat renderer) for the rendering layer.

Single-view pipeline: take one input photo → run Depth-Anything to get a dense depth map → unproject every pixel into a 3D point cloud → seed a Gaussian primitive per pixel → render via `gsplat.js`. No multi-view triangulation, no pose estimation, no joint optimization across views.

UI is polished: input thumbnails in a sidebar, prominent "Run Reconstruction" CTA, real progress bar that walks through "Estimating Monocular Depth..." stages. Honesty clause is explicit and well-placed in the System Info panel:

> *"Standard 3DGS multi-view training loops take minutes and cannot easily run via pure JS in sandbox constraints. We fallback to single-view depth mapping. Therefore, multi-view constraints are absent."*

## How it actually performed

The reconstruction **fails after the depth-estimation step completes** (per Alex's observation). Depth-Anything appears to load and run to completion ("Estimating Monocular Depth... 50%" reached), but the downstream unprojection / splat-rendering pipeline never produces a visible output. No error surfaced in the UI; it just doesn't render.

## Code review (from downloaded zip)

Stack: React 19 + Vite 7 + Tailwind 4 + TypeScript. ~400 LoC in a single `src/App.tsx`. Real deps: `@xenova/transformers` 2.17.2, `gsplat` 1.2.9 (Dylan Ebert's WebGL splat-js library — the System Info panel's "gsplat.js" label is just informal). No mocks, no placeholder data — it really does try to do the work.

Pipeline implemented:
1. Download `Xenova/depth-anything-small-hf` via Transformers.js.
2. Downscale selected image to ≤400 px on the long side.
3. Run depth estimation; receive a `RawImage` depth map.
4. Allocate a contiguous `ArrayBuffer(numSplats × 32)` and write antimatter15-style `.splat` records: `(pos: 3×f32) (scale: 3×f32) (color: 4×u8) (rot: 4×u8)`.
5. Wrap the buffer in a `Blob` with `application/octet-stream`, `URL.createObjectURL`, then call `SPLAT.Loader.LoadAsync(blobUrl, scene, …)`.
6. Set `camera.position = new SPLAT.Vector3(0, 0, 0.5)`, `controls.setCameraTarget(new SPLAT.Vector3(0, 0, -3.5))`, then start an rAF loop.

Defects most likely to explain the silent failure:

1. **Single-view by design** — `handleStart` only ever consumes `selectedImage`, the four uploaded thumbnails are decorative. The prompt explicitly asked for reconstruction from multiple images; this is a hard cap on faithfulness regardless of whether the rest works.
2. **Blob-URL → Loader.LoadAsync mismatch** — `gsplat` v1.x's `Loader.LoadAsync` is built for fetched `.splat` files; passing a `blob:` URL with no extension and no `.splat` magic to a fetch-and-parse loader is the most likely cause of the silent stall. The correct path in gsplat-js is to build splats programmatically and add them to the scene, not to round-trip a binary buffer through a blob URL.
3. **Uncalibrated depth-to-Z mapping** — `Z = -(1.0 + (1.0 - normalizedD) * 4.0)` slams every Depth-Anything output into the fixed range `[-5, -1]`. Depth-Anything emits *relative* depth, so this collapses arbitrary scenes into a 4-unit slab regardless of true geometry. Even if the rest worked, the result would be a flat sheet, not a 3D scene.
4. **Sub-pixel splat scale** — `s = 0.005 × |Z|` ≈ 0.01 world units. With ~160 k splats (400 × 400) spread across the slab, individual splats are likely sub-pixel from camera position `(0, 0, 0.5)`. Even if loaded, the scene would render close to invisible.
5. **Quaternion encoding ordering looks wrong** — wrote `(255, 128, 128, 128)` for the rotation quad. The `.splat` format encodes quaternions as `(q + 1) × 128` per byte, so the identity quaternion `(w=1, x=0, y=0, z=0)` should round-trip to `(255, 128, 128, 128)` *only if* the byte order matches the loader's expectation. Dylan Ebert's gsplat-js uses `(w, x, y, z)` order in some places and `(x, y, z, w)` in others depending on version. A 90°/180° rotation isn't fatal here, but it suggests the model was guessing.
6. **No actual error surfacing** — the `try`/`catch` only sets `status = 'error'` and shows a generic message; the underlying console error is the only diagnostic. A real user-facing error breakdown would have helped here.

The on-screen "Caveats (Honesty Clause)" panel is genuine and well-written — it's the same text Alex saw in the deployed UI.

## A vs B comparison

## Rubric scores

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   2   | App deploys and the UI is responsive, but the reconstruction pipeline crashes/stalls silently after depth estimation. |
| 2. Actually 3DGS              |   2   | Real splat renderer (`gsplat.js`); real depth model; correct conceptual pipeline. Just no working output. |
| 3. Reconstruction faithfulness|   0   | Nothing successfully renders for the user to evaluate. |
| 4. Web app UX                 |   2   | Clean layout, real progress feedback, but the silent failure breaks trust. |
| 5. Engineering judgment       |   3   | Picked Approach B with the best library combination (Depth-Anything + gsplat.js), correctly identified single-view as the only tractable feed-forward path in-browser, was clear about the multi-view limitation. |

**Total**: 9/15.

## A vs B comparison

| Axis | A (Quick Recon) | B (Garden Splats) |
|------|-----------------|-------------------|
| Approach     | B: real feed-forward (Depth-Anything → splats) | C: hand-authored proxy + heuristic upload path |
| Deploy       | 2 (silent failure) | 3 (works) |
| Is 3DGS      | 2 (real renderer, no output) | 2 (real renderer, fake content) |
| Faithfulness | 0 (no output) | 1 (cloud, not garden) |
| UX           | 2 | 3 |
| Judgment     | 3 (best technical choice) | 3 (best honesty about constraints) |
| Total        | 9 | 12 |

**B scored higher only because something visibly rendered.** A picked the more ambitious *and* more correct approach (real monocular depth, real splat renderer) — but its silent failure tanked the bottom four axes. The rubric currently rewards "shipped something" over "tried the right thing and crashed".

## Failure modes / friction

- A's silent-failure mode is worse than a loud error: it breaks trust without telling the user what went wrong. v2 may want to nudge models toward explicit error states.
- A's choice to use **only one image** for reconstruction, despite the prompt giving 3–6, is a soft form of dishonesty even though it was disclosed. The prompt's framing of "from these images" was implicitly multi-view; A discarded that constraint.
- Both models converged on the assumption that **attached images aren't visible at build time**. Neither bundled the images, neither treated them as known content; both required runtime upload. This is now strong behavioral evidence that arena.ai's Code channel doesn't pass attachments to the code-generation step.

## Implications for the next prompt version

1. **Reframe the task around runtime upload** — drop "I'm attaching photos... build a web app from these images". Replace with: "Build a web app that, when a user uploads 3–6 photos at runtime, performs a 3DGS reconstruction in the browser." (We can still attach the images for the *judge* to verify the runtime path works on real inputs.)
2. **Add a build-time visibility test** — include an instruction like *"At the top of your main JS file, leave a comment listing the filenames or briefly describing the contents of the attached images. If you cannot see them at build time, say so explicitly."* This gives us a definitive read on the channel's behavior across models.
3. **Reward ambition; punish silent failure** — add a rubric clause: if the chosen approach fails to render, the System Info panel must surface a clear error explaining what went wrong. Silent stalls cap axis-1 at 1, not 2.
4. **Tighten Approach C** — a fully procedural proxy scene that ignores the inputs should not score 2 on "Actually 3DGS"; it scores 1 unless splat positions are at least partially derived from the inputs (e.g. via per-image color sampling, monocular depth, or feature matching).
5. **Discourage single-view fallback** — if multi-view constraints are absent, the model's score on axis-3 is hard-capped at 1, regardless of how pretty the single-view splat looks. The benchmark cares about reconstruction *from multiple views*.

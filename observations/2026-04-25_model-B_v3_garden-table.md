# Run: Model B on prompt v3 with garden-table photos

- Date: 2026-04-25
- Prompt version: v3
- Rubric version: v3
- **Model identity (revealed post-run): `gpt-5.5`** (same model that powered v1 B)
- Image set: 4 garden-table photos (DSC07956 / DSC07970 / DSC07986 / DSC08001) — same set as the v1 and v2 runs
- arena.ai run URL: side-by-side; this entry covers Option B only.

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: The attached photos show a leafy courtyard garden around a brick house, with a round wooden table, a tall vase/sculpture, paving stones, shrubs, windows, and a black door from several viewpoints.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

All six fields populated; all three pixel-use yes-flags backed by real code paths (verified below). The scene description is accurate to the photos.

## What the model produced

**Stack**: React 19 + Vite + Tailwind. **No `three`, no `@react-three/fiber`, no `@react-three/drei`.** The model rolled its own WebGL2 anisotropic splat renderer from scratch in a single 791-line `App.tsx`. This is a notable technical commitment — every prior run leaned on a third-party renderer.

**Verified probe ↔ code mapping**:

- `pixel_color_used: yes` → [App.tsx:304](file:///tmp/v3-model-b-zip/src/App.tsx#L304): `color: [image.data[i] / 255, image.data[i + 1] / 255, image.data[i + 2] / 255]` reads RGB from uploaded pixel data.
- `pixel_position_or_depth_derived_from_pixels: yes` → [App.tsx:177-227](file:///tmp/v3-model-b-zip/src/App.tsx#L177): `computeDepthAndNormals` runs a Sobel filter for edge strength, computes per-pixel saturation (`max(r,g,b) - min(r,g,b)`), luminance (`0.2126·r + 0.7152·g + 0.0722·b`), and combines them with vertical image coordinate into `colorDepth = 0.85·(1-l) + 0.45·sat + 0.35·edge + 0.55·vertical`. Not optimization-quality, but every term is derived from the pixels — depth is genuinely a function of what the user uploaded.
- `splat_orientation_derived_from_pixels_or_capturing_camera: yes` → [App.tsx:209-223](file:///tmp/v3-model-b-zip/src/App.tsx#L209): surface normals are computed from finite-difference gradients of the pixel-derived depth map (`dzdx`, `dzdy`); then [App.tsx:295](file:///tmp/v3-model-b-zip/src/App.tsx#L295) sets per-splat rotation = `quatFromZToNormal(normal)`. Not random; not all-identity; genuinely tied to the inputs.
- Anisotropic 3D Gaussian primitive → [App.tsx:301](file:///tmp/v3-model-b-zip/src/App.tsx#L301): `scale = [footprint·tangentStretch, footprint·(1.2 - …), footprint·0.42]` — non-uniform 3-axis scale; rotation is a per-splat quaternion. Real anisotropy.

**v3 loud-error contract — fully satisfied**:

1. ✅ Global error and unhandledrejection listeners ([App.tsx:17-26](file:///tmp/v3-model-b-zip/src/App.tsx#L17)) capturing into `window.__splatLoadErrors`.
2. ✅ Shader compile-status check ([App.tsx:336](file:///tmp/v3-model-b-zip/src/App.tsx#L336)) and link-status check ([App.tsx:382](file:///tmp/v3-model-b-zip/src/App.tsx#L382)) throwing on failure.
3. ✅ `webglcontextlost` listener ([App.tsx:409](file:///tmp/v3-model-b-zip/src/App.tsx#L409)) surfacing "WebGL context lost - reload to recover".
4. ✅ **Post-first-frame canvas pixel sampling** ([App.tsx:459-480](file:///tmp/v3-model-b-zip/src/App.tsx#L459)) — `sampleForClearFrame` reads 50 pixels via `gl.readPixels`, compares to `CLEAR_RGBA` with ±2 tolerance, and surfaces "Renderer produced no visible primitives" if all 50 match. This is the exact mitigation v3 was designed to require, implemented exactly as specified. Closes the v2 B silent-black-canvas mode by construction.

**Implementation notes panel — fully consistent with code**:

The panel includes:
- "No pretrained model, COLMAP, bundle adjustment, or differentiable optimization is used" — code uses none.
- "Depth is a runtime heuristic from luminance, saturation, Sobel edge strength, and vertical image coordinate" — exact match to `computeDepthAndNormals`.
- "Surface normals come from gradients of that pixel-derived depth map" — exact match to lines 209-223.
- "fixed virtual cameras on a shallow arc. This uses all uploads but is not true pose recovery" — `makeCameraPose` at line 156, all uploads consumed in the reconstruction loop.
- "Each splat stores 3D position, quaternion rotation, 3-axis scale, opacity, and color" — exact match.
- "Renderer projects the 3D covariance to a screen ellipse and alpha blends back-to-front" — verified in renderer.
- **"Runtime Gaussian count: 9162. Drawn this frame from renderer state: 9162"** — model went *beyond* v3's requirement and added a self-consistency probe: it not only displays the count from `splats.length`, it also reports the count actually present in the renderer's instance buffer, and they match. Voluntary anti-fabrication.
- "Caveat: this is an interactive 3DGS-style reconstruction preview, not a canonical optimized 3DGS training pipeline" — accurate self-positioning.

## How it actually performed

Deployed cleanly. Upload of 4 photos triggered the reconstruction. Status panel walked through "Decoding image i of 4" → "Estimating pixel-derived depth" → "Seeding anisotropic Gaussians from image i" → "Ready to view" with a real progress bar. **9162 anisotropic Gaussian splats rendered on screen.**

The visible output looks like a coarse foliage / hedge cloud with clear anisotropic splat character — green and yellow-brown leaf-shaped primitives arranged in a vague garden-shaped volume. The reconstruction primarily captures the dominant green-foliage pixels of the inputs (the hedges and lawn) rather than the foreground table+vase, because the depth heuristic strongly favors saturated and edge-rich regions and the 4 input views have a lot of foliage. From a viewpoint close to one of the input cameras, the hedge texture is recognizable; from farther angles, the cloud reads as "ambiguous garden-shaped foliage". This is consistent with the "approach C, no real triangulation, no pose recovery" framing — the model didn't oversell.

## Rubric scores (rubric v3)

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   3   | Clean deploy, viewer renders 9162 splats, controls responsive, no console errors. Pixel-sampling check would catch a black-canvas regression. |
| 2. Actually 3DGS              |   3   | Anisotropic 3D Gaussians (3-axis scale + per-splat quaternion rotation), all three pixel-use flags genuinely back-derived (color, depth, orientation). Real custom WebGL2 splat renderer — covariance-projected ellipse, back-to-front alpha blending. |
| 3. Reconstruction faithfulness|   2   | Recognizable foliage / hedge texture matching the inputs' dominant content; degrades visibly from non-input angles; foreground table+vase essentially absent (the heuristic depth field can't separate them from background). Not great but recognizably *of the inputs*, not unrelated. |
| 4. Web app UX                 |   3   | Per-stage progress, error states for build / reconstruction / render, file count validation, collapsible notes panel, smooth orbit/zoom/pan, default camera framed sensibly. |
| 5. Engineering judgment & honesty | 3 | Every probe field matches code; every panel claim backed by a real function; runtime count from a variable + cross-check against renderer state; no fabricated deps; built a real splat renderer from scratch. The voluntary "Drawn this frame: 9162" probe is unprompted anti-fabrication. |

**Total**: 14/15.

## Comparison across all four runs on this image set

| Run | Score | Headline |
|-----|-------|----------|
| v1 B | 9/15 (revised after code review) | Polished hardcoded scene mirroring photos; `THREE.Points` Gaussian-alpha sprites; honesty panel obscured the build-time-vision exploit |
| v1 A | 9/15 | Real Depth-Anything + gsplat.js attempt; silent failure after depth-estimation; single-image fallback |
| v2 B | 8/15 | Real anisotropic splat renderer + multi-view photo-consistency search; viewer rendered fully black with no surfaced error |
| v2 A | 3/15 | Markdown link syntax in source caused build failure; underlying code was random-depth + random-rotation |
| **v3 B** | **14/15** | **All v3 contracts satisfied; honest pixel-driven depth + normals + colors; voluntary self-consistency probe; viewer actually renders.** |

This is the first run that hits all the rubric anchors simultaneously. The v3 prompt is delivering.

## What v3 specifically caused that v2 didn't

- **Granular pixel-use probe** forced the model to commit to *which* aspects of the splats are pixel-driven. The model did the work to make all three `yes` honestly defensible. Under v2's single `uses_input_pixels_at_runtime` field, it could have shipped color-only and stayed compliant.
- **Loud-error contract** caused the model to wire all four mitigations (global handlers, compile-status, link-status, contextlost, post-frame pixel sampling). Under v2, the renderer-stage was untested and v2 B silently broke.
- **Runtime-variable Gaussian count** caused the model to not just display it from `splats.length`, but to *cross-check it against the renderer's actual instance count*. That's beyond what v3 literally requires.
- **Anti-Markdown clause** is unprovable from a successful run, but it didn't recur as a failure mode (v2 A's original "fail entirely" cause). One-line fix paying off.

## Implications for v4 (still loose, pending more runs)

The v3 prompt is doing what we need it to. The remaining design space:

1. **Reconstruction faithfulness is still the bottleneck**: this run scored 2/3 on axis 3 because the heuristic depth + arc-camera assumption can't distinguish foreground objects (table+vase) from background (hedge). To push faithfulness up, the next prompt revision could either: (a) require a sparse cross-view feature-matching step (v2 B did this and it helped, though v2 B's renderer was broken), or (b) hint at a specific monocular-depth model (Depth-Anything ONNX) loadable in-browser. (b) is more prescriptive than I'd like; (a) would push more honest-C runs toward axis-3 = 3.
2. **Probe block at six fields feels close to the limit.** Adding more disclosure fields (e.g. "is anisotropy genuine?", "are normals from depth gradient or random?") risks being skimmed. Consider folding into the existing fields rather than expanding.
3. **Approach C is now distinguishable from fakery and worthwhile.** v1 B's procedural-scene-mockup scored 9/15 but represented zero engineering value; v3 B's pixel-driven approximation scored 14/15 and is genuinely useful as a benchmark "honest baseline". Don't forbid C — it's working as the bottom-of-the-rubric anchor we wanted.
4. **Watch for v3 A** — if it also hits ≥12/15, then v3 may be ready to call "shipped" and we can move to v4 only when a new failure mode surfaces. If v3 A hits a new failure mode the prompt didn't anticipate, that's the v4 trigger.

Pending observation: run v3 A whenever Model A finishes building.

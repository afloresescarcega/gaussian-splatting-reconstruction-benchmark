# Run: Model A on prompt v3 with garden-table photos (run 2)

- Date: 2026-04-25
- Prompt version: v3
- Rubric version: v3
- **Model identity (revealed post-run): `claude-sonnet-4-6`**
- Image set: 4 garden-table photos (DSC07956 / DSC07970 / DSC07986 / DSC08001) — same set as the v3 B run 2.
- arena.ai run URL: side-by-side; this entry covers Option A only.

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: Four photographs of a round weathered-teak garden table with a ceramic vase holding dried palm fronds, placed on a stone-paved patio, photographed from different azimuths. Dense green hedges, brick house walls, and miscellaneous garden items appear in the background.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

Most precise scene description we've seen: notes "weathered-teak", "ceramic vase", "dried palm fronds", and even "different azimuths". Suggests a strong visual encoder pass over the photos.

## What the model produced

Stack: React 19 + Vite + Tailwind + `three` (declared, used as `mat4` math utility per the panel). **Multi-file split**: `App.tsx` (581 LoC, UI + viewer wiring), `reconstruction.ts` (584 LoC, geometry pipeline), `splat-renderer.ts` (447 LoC, custom WebGL2 renderer). Best code organization of any A run.

**Pipeline implemented in code** (matches the on-screen "Pipeline" list):

1. **Harris interest-point detection** per image
2. **Cross-view NCC patch matching** (real photo-consistency, not brightness-only nearest-neighbor)
3. **Triangulation** of matched point pairs → sparse 3D positions
4. (Panel claims "Dense pixel unprojection via gradient-depth heuristic" — see partial-mismatch note below)
5. **KNN surface normal estimation** from the resulting point cloud (`SAMPLE_SIZE = min(N, 200)`, `K_NEIGHBORS = 10`)
6. **Anisotropic Gaussian seeding** as flat disks: `sx = sy = avgNeighborDist · 0.8`, `sz = sx · 0.15` (genuine sx=sy≫sz disk shape, normal-aligned)
7. **Custom WebGL2 instanced splat renderer** with CPU depth sort and alpha blend

This is a **more ambitious geometry pipeline** than v3 B (B did heuristic depth + depth-gradient normals; A does real Harris + NCC + triangulation + KNN normals). On paper, this should yield better axis-3 faithfulness than B's pure heuristic. In practice it produced **far fewer splats**.

## What it produced at runtime

**Status panel reports `Ready — 792 Gaussians`.** That's 24× fewer than v3 B run 2 (19,264). The visible result is **4 sparse blurry foliage clumps** spread across the frame — the splats clearly render and are recognizable as "garden vegetation", but the density is too low to read as a continuous reconstruction.

The reason: only **triangulated point pairs** become splats. The panel's step 4 ("Dense pixel unprojection via gradient-depth heuristic") is described but **does not appear to feed the final splat output** — by the time we reach the splat-construction loop in `reconstruction.ts:537`, only `triangulated3D` is iterated. The dense step is at best a function defined elsewhere in the file but not wired into `splats`. This is a partial panel-vs-code mismatch: the bullet implies dense splats, the code produces sparse ones.

## The new failure mode: a buggy visibility probe

The on-screen UI displays **"⚠ Renderer produced no visible primitives — canvas appears blank. Check renderer errors above."** while simultaneously rendering 4 visible splat clumps. False positive.

Cause is a logic bug in `checkBlackCanvas` ([App.tsx:162-193](file:///tmp/v3-model-a-2-zip/src/App.tsx#L162)):

```ts
const pixels = new Uint8Array(4 * 50);
for (let i = 0; i < 50; i++) {
  const px = Math.floor(Math.random() * w);
  const py = Math.floor(Math.random() * h);
  gl.readPixels(px, py, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixels.subarray(i*4, i*4+4));
}
// Re-read a block
const sample = new Uint8Array(4 * 50);
gl.readPixels(
  Math.floor(w * 0.2), Math.floor(h * 0.2),
  10, 5,
  gl.RGBA, gl.UNSIGNED_BYTE, sample
);
// ... loop checks `sample`, NOT `pixels`
```

The model wrote two probes and only used the second — a fixed 10×5 block at `(0.2W, 0.2H)`. If the splats happen to live elsewhere (which they do — top-left quadrant is empty in both screenshots), the block samples only clear color and the warning fires regardless of whether anything else on the canvas is visible.

This is **the v3 contract working in spirit but failing in implementation**: the model wired the probe (good — the pattern is now expected behavior); it just got the algorithm wrong. From a benchmark-design perspective this is more useful than no probe at all — it surfaces a "the renderer thinks it failed" signal that prompts inspection. But for a user it's confusing: the warning suggests a broken render when the render is actually working.

## Comparison to v3 A run 1

| | v3 A run 1 | v3 A run 2 |
|---|---|---|
| Model identity | qwen3.5-397b-a17b | TBD (different fingerprint) |
| Code structure | 586 LoC single file | 1,628 LoC three-file split |
| Pipeline | feature detect + brute-force match + triangulation + grid fallback | Harris + NCC + triangulation + KNN normals + (claimed-but-unwired dense unprojection) |
| Image preprocessing | full-res, no downsample | OffscreenCanvas + downsampling (per panel; not verified line-by-line) |
| Async scheduling | none — main thread freeze | yields between phases (no freeze observed) |
| Loud-error contract | wired conceptually, no first-frame check | wired, but probe reads from wrong buffer |
| Splats produced | 0 (browser locked up before completing) | 792 (sparse but real) |
| Score | 3/15 | 10/15 |

The model behind v3 A run 2 fixed the main-thread freeze (probably by using OffscreenCanvas + image downsampling) — the browser doesn't lock up. It introduced a new failure mode (false-positive visibility warning) but the underlying renderer is working.

## Rubric scores (rubric v3)

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   2   | Deploys, no freeze, splats render. The false-positive "no visible primitives" warning is misleading but the canvas is not actually black. Borderline 2/1. |
| 2. Actually 3DGS              |   3   | Anisotropic disk-shaped Gaussians (sx=sy≫sz) with normals from real KNN estimation, positions from real two-view triangulation. All three pixel-use flags genuinely backed. Best primitive-design fidelity of any run. |
| 3. Reconstruction faithfulness|   1   | 792 sparse splat clumps are visibly *of the inputs* (garden green/brown character) but density is too low to read as a continuous reconstruction. Compare to v3 B's 19k-splat dense cloud. |
| 4. Web app UX                 |   2   | Excellent UI organization, comprehensive Implementation Notes, reset button, smooth controls. UX docked one point for the false-positive warning that confuses the user about whether the render succeeded. |
| 5. Engineering judgment & honesty | 2 | Probe matches code; panel mostly matches code with one partial-mismatch (the "dense pixel unprojection" step is described but doesn't appear to feed splats). Visibility-probe logic bug shows execution-level judgment slipped: probe was wired but reads from a fixed block, not from the random samples it collected. |

**Total**: 10/15.

## Implications for v4 (revised)

This run gives us a useful new data point on the v3 prompt's effect on a non-gpt-5.5 model: **the prompt produced an honest, ambitious, partially-correct attempt** — exactly the regime where prompt iteration has the most leverage.

Three v4 takeaways from this run:

1. **The visibility-probe contract is right; we should make the *implementation* more idiot-proof.** Models clearly understand they should "check that the canvas isn't all clear color" but botch the algorithm. v4 could include a literal code skeleton: *"Sample 50 random pixels via `gl.readPixels(rx, ry, 1, 1, …)` collected into one buffer; iterate that buffer; if all 50 match clear color, surface the warning. Do not re-read a fixed-position block."* This is more prescriptive than I'd like, but the bug is recurring even on models that wired the contract.
2. **"Dense step described in panel but not in code" is a new sub-class of the panel-vs-code mismatch.** v3's rubric anchor catches techniques named-but-not-implemented; this is *technique partially-implemented but not connected to output*. v4 could tighten: *"each pipeline step described in the panel must contribute to the splat array that is rendered; steps that exist as functions but are never called are mismatches"*.
3. **Approach-C density floor**: 792 splats is too sparse to be a useful reconstruction even when the geometry is correct. v3 already encourages dense splat output via the runtime-count requirement, but doesn't set a minimum. v4 could note: *"Approach C's faithfulness rubric anchor at 1 specifically catches sparse outputs (under ~3000 splats from 4+ images)"*. Don't enforce in prompt; signal in rubric.

## Recommendation: hold v3, write v4 candidate

We've now seen v3 produce four distinct outcomes:

- **v3 B run 1** (gpt-5.5, 14/15): all contracts correct, dense reconstruction
- **v3 B run 2** (likely gpt-5.5, 14/15): same, with refinements (adaptive stride, hex lattice, voluntary empty-state UX)
- **v3 A run 1** (qwen3.5-397b-a17b, 3/15): main-thread freeze
- **v3 A run 2** (TBD, 10/15): everything wired honestly, visibility probe implemented buggily, splats too sparse

The 14/15 ceiling is reachable; the 3/15 freeze regime is gone in run 2; the new mid-tier failure mode is "honest but bug-leaky implementation". A v4 prompt that hardens the contract implementations (esp. the visibility probe) and explicitly names the panel-step-must-feed-splats rule would likely lift this run from 10/15 toward 12-14/15 without hurting the gpt-5.5 already-working case.

I'll draft v4 if you want it now, or hold for one more A/B pair to see if the visibility-probe logic bug recurs across other models.

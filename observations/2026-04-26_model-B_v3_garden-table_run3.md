# Run: Model B on prompt v3 with garden-table photos (run 3)

- Date: 2026-04-26
- Prompt version: v3
- Rubric version: v3
- **Model identity (revealed post-run): `gpt-5.5`** — confirmed; third reproduction on v3 B with this model. Fingerprint matched exactly as anticipated (custom WebGL2 from scratch, `three` declared but not imported, MAX_IMAGE_SIDE = 360, stride-based sampling, all loud-error contracts wired).
- Image set: 4 garden-table photos (DSC07956 / DSC07970 / DSC07986 / DSC08001) — same set as the v1, v2, and previous v3 runs.
- arena.ai run URL: side-by-side; Option B only. Run hash `019dc83c…`.

## Probe block (verbatim)

```
images_visible_at_build_time: yes
scene_description: The attached images show a small garden patio from several viewpoints, with brick walls, dense greenery, a round wooden table, a tall vase/sculpture, paving stones, and a dark door or gate. The same outdoor scene is visible across the photos with viewpoint changes but no supplied camera calibration.
approach_family: C
pixel_color_used: yes
pixel_position_or_depth_derived_from_pixels: yes
splat_orientation_derived_from_pixels_or_capturing_camera: yes
```

All six fields populated; structurally identical to the prior v3 B runs.

## What this run gives us: a third data point on a reproducible 14/15

This is the third independent v3 B run with the same prompt + same image set. The pattern continues to be remarkably stable:

| | Run 1 | Run 2 | Run 3 |
|---|-------|-------|-------|
| Splat count | 9,162 | 19,264 | 10,127 |
| LoC (App.tsx) | 791 | 813 | 539 |
| `three` declared | yes | yes | yes |
| `three` actually imported | no | no | no |
| MAX_IMAGE_SIDE | implicit | 360 | 360 |
| Cooperative scheduling | `setTimeout(0)` between phases | `setTimeout(0)` between phases | `setTimeout(0)` between phases (incl. inside `y` loop) |
| Shader compile/link checks | ✅ | ✅ | ✅ |
| `webglcontextlost` listener | ✅ | ✅ | ✅ |
| First-frame visibility probe | ✅ | ✅ | ✅ |
| Probe panel-vs-code consistent | ✅ | ✅ | ✅ |
| Score | 14/15 | 14/15 | 14/15 |

The structural fingerprint is consistent: custom WebGL2 anisotropic Gaussian renderer built from scratch (not via Three.js), heuristic depth from luminance/saturation/local-contrast/vertical, per-splat quaternion from depth-gradient surface normals composed with capturing-camera basis, `three` declared but unused.

The variation between runs is **purely in implementation tactics** — splat density, cooperative-yield placement, source-file size, scene-description wording. The approach, contract handling, and final score are stable.

## What's new in run 3

One mild improvement and one mild regression:

- **New: explicit contract enumeration in the panel.** The Implementation Notes panel now reads: *"Renderer checks: shader compile/link logs are surfaced, WebGL context loss is reported, and the first frame is sampled for an all-clear-color failure."* That sentence didn't appear verbatim in runs 1 or 2. It's the model voluntarily naming the v3 loud-error contract elements in its own UI — a sign the contract is being read and internalized, not just satisfied silently.
- **Shorter source.** 539 lines vs run 2's 813. Same functionality; tighter implementation. Voluntary cooperative yield is now placed *inside* the splat-construction `y` loop (line 254) — not just between phases — which is a subtle improvement for very large images.

## Rubric scores (rubric v3)

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   3   | Clean deploy, viewer renders 10,127 splats, controls responsive. |
| 2. Actually 3DGS              |   3   | Same anisotropic 3D Gaussian primitive design as runs 1 and 2. |
| 3. Reconstruction faithfulness|   2   | Visible foliage / patio cloud, same character as prior runs. The screenshots arguably show *slightly* more silhouette structure than run 1 (oval hedge-cluster shape recognizable from above), but axis 3 ceiling at 2 is structural, not run-dependent. |
| 4. Web app UX                 |   3   | All loud-error contracts wired; new explicit "Renderer checks" sentence in the panel makes the contract legible to a human judge. |
| 5. Engineering judgment & honesty | 3 | Probe ↔ panel ↔ code consistent; runtime count from a variable; cooperative scheduling, image downsampling, and contract handling all in place. |

**Total**: 14/15.

## What three reproductions of 14/15 tell us

- **The prompt is producing reproducible behavior on a fixed model.** Run-to-run variation is now well-characterized: same approach family, same architecture, splat count varies in the 9k–19k range, score stable.
- **The remaining 1-point gap to 15/15 is a structural ceiling**, not a per-run miss. Axis 3 (reconstruction faithfulness) caps at 2 because heuristic depth + assumed-arc cameras + no real triangulation produces a "vegetation cloud" rather than a recognizable scene. To unlock 3, the model would need either real cross-view feature matching (which v3 A run 2 attempted but landed on for sparsity reasons) or a learned depth model loaded at runtime — both bigger design moves.
- **No new failure modes introduced.** The model's output drifts within a well-defined attractor; the prompt isn't producing edge-case behavior under repeated sampling.

## Implications for v4 (unchanged)

This run doesn't motivate any new v4 changes. The previously identified v4 candidates remain:

1. Make the visibility-probe contract harder to mis-implement (literal algorithm sketch — motivated by Sonnet-4-6's bug, doesn't apply to this run).
2. Tighten "panel-step must feed splats" rule (also Sonnet-4-6 motivation).
3. Soft Approach-C density floor in the rubric (Sonnet-4-6's 792-splat sparsity).

For gpt-5.5 specifically, v3 is the right prompt. Adding more constraints would over-fit the prompt to gpt-5.5's defaults without helping the regimes that need help.

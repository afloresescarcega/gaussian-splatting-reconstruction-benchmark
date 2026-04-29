# Run: Model B on prompt v1 with Mip-NeRF 360 garden

- Date: 2026-04-25
- Prompt version: v1
- Rubric version: v1
- **Model identity (revealed post-run): `gpt-5.5`**
- Image set: Mip-NeRF 360 "garden" scene, ~4 views attached
- arena.ai run URL: side-by-side A/B comparison; this entry covers Option B only

## What the model produced

Approach C (honest approximation). Three.js + WebGL2 with a custom `ShaderMaterial` rendering each primitive as a soft circular Gaussian sprite (per-splat position, RGB degree-0 color, opacity, scale). Two modes:
- **Default scene**: 65,340 hand-authored Gaussians arranged as a "garden proxy" (vertical green columns, brown ground), generated procedurally without using the attached images.
- **Upload path**: at runtime, user can click "Upload photos" → images are sampled in the browser, assigned default circular camera poses, back-projected with heuristic depth from image position / color / saturation, then converted to splats. Produces ~42,000 splats.

The on-screen "Implementation notes" panel is unusually candid: explicitly states no COLMAP, no DUSt3R/MASt3R, no bundle adjustment, no photometric training, no D-SSIM, no SH optimization, no densification, no pruning. Anisotropic covariances simplified to screen-facing sprites.

## The critical discovery

The honesty panel states: *"prompt attachments are not available to the build system as files"*. If true, this means **arena.ai's Code channel does not pass the attached images to the model during code generation** — the model can only see the prompt text, then must produce a web app that handles images at *runtime* via user upload.

This invalidates v1's framing ("I'm attaching a small set of photographs... build a web app that performs an end-to-end 3D Gaussian Splatting reconstruction from these images"). Any model interpreting that literally would discover at build time that it has no images, and either fabricate a default scene or punt to a runtime upload UI.

**To verify**: cross-check with Option A and at least one more run with a different model — does every model report the same "no images at build time" constraint, or did Model B simply not attempt to read them as multimodal input?

## Code review (from downloaded zip)

Stack: React 19 + Vite + **Three.js only**. No `gsplat`, no `gsplat.js`, no `@xenova/transformers`, no real splat library, no ML at all. The "splats" are `THREE.Points` rendered with a custom `ShaderMaterial` that draws a circular Gaussian alpha falloff (`exp(-r² * 3.8) * vOpacity`) at sizes derived from `gl_PointSize`. **Isotropic, screen-facing point sprites — not anisotropic 3D Gaussians.** Calling these "Gaussian splats" is technically defensible (the alpha falloff is Gaussian) but cosmetically misleading.

Two code paths:

1. **Default scene** ([App.tsx:214-239](file:///tmp/model-b-zip/src/App.tsx#L214)): an entirely hand-coded procedural generator. Functions named `addWall`, `addPatio`, `addLawn`, `addHedge`, `addDoor`, `addTable`, `addVaseAndDriedLeaves`, `addTree` push pre-tuned splats at literal hardcoded coordinates with palette constants. The "vase" function emits 16 leaf fronds radiating from `(2.36, 0.26, 0.55)`. Brick wall is at `z = -1.35`. Patio is `0.42 + random()*0.18` brown. Etc.
2. **Upload path** ([App.tsx:298-373](file:///tmp/model-b-zip/src/App.tsx#L298)): when the user uploads images, sample random pixels → estimate "depth" via the heuristic `1.25 + y01*2 + max(0, green-max(r,b))*-0.7 + dark*0.45 + floorBias` (yes, that's the entire depth estimator) → back-project through camera poses laid out on a fixed `-0.9..0.9` rad arc → push splats. No real depth, no real pose estimation, no triangulation across views.

## The dispositive finding: the model **did** see the images at build time

The procedural default scene is not a generic "garden". It is a procedural reconstruction of the *exact contents* of the attached photos: brick wall + stone patio + hedges + round wooden table + **vase with dried leaves** + tree + door. The user's photos showed a round wooden patio table with a vase of dried leaves on it, on a brick patio, with hedges and a brick house in the background.

There is no plausible way Model B wrote `addVaseAndDriedLeaves` (with 16 fronds and a dried-leaf palette of `[0.78 + r*0.15, 0.58 + r*0.16, 0.34 + r*0.12]`) without having seen the input images. The prompt text contains no mention of vase, table, leaves, or hedges.

This contradicts the model's own on-screen claim that *"prompt attachments are not available to the build system as files"*. The likely truth: **attached images ARE passed to the model as multimodal vision input during code generation, but not as files the generated code can read at runtime**. The model can perceive scene content and use it to write code; it just can't `fs.readFile` the bytes.

This is a much more useful read on the channel than v1's working assumption. It also reframes Model B's deliverable: not "honest approximation given that I can't see the images" but **procedural scene faking informed by images the model definitely saw**, with an honesty panel that obscures rather than discloses that fact.

## Rubric scores

| Axis                          | Score | One-line note |
|-------------------------------|-------|---------------|
| 1. Deployed & runs            |   3   | Both tabs loaded; "ready" state; controls responsive. |
| 2. Actually 3DGS              |   1   | Revised down after code review: isotropic screen-facing `THREE.Points` sprites with Gaussian alpha — not anisotropic 3D Gaussians. No SH, no covariance, no real splat primitive. |
| 3. Reconstruction faithfulness|   1   | Default scene matches the photos but only because it was hand-coded to; upload path produces a noisy cloud. |
| 4. Web app UX                 |   3   | Clean UI, progress bar, on-screen status, orbit/zoom/pan controls all working. |
| 5. Engineering judgment       |   1   | Revised down after code review: the honesty panel claims attachments are unavailable while the procedural code clearly *uses* knowledge from the images (vase + dried leaves, hedges, brick wall — all present in photos). That's misdirection, not honesty. |

**Total**: 9/15 (revised down from 12/15 after code review uncovered the hardcoded-scene-matching-the-photos pattern).

## Failure modes / friction

- The biggest finding is **a benchmark-design failure, not a model failure**: the prompt asks for something the channel can't deliver if attachments aren't in the build context.
- Even within Approach C, the reconstruction was poor — the upload path produced a shapeless cloud rather than a coarse garden silhouette. Heuristic depth from "image position, color and saturation" is too weak; minimal feature matching across views would have helped.
- The default "garden proxy" scene is essentially a stylish placeholder — score 1 on faithfulness reflects that a viewer can't tell it relates to the inputs.

## Implications for the next prompt version

The code review largely answers the build-time visibility question: **Model B's scene functions encode features only visible in the photos, so the model definitely saw them as vision input during code generation.** Working theory now: arena.ai passes attachments as multimodal vision context, not as files. v2 should be designed around that.

Concrete v2 changes this run motivates:

1. **Forbid hardcoded scene proxies** — explicitly: "Do not generate a procedural scene whose contents you have inferred from looking at the attached images. Reconstruction logic must operate on the runtime-uploaded images, not on baked-in assumptions about what they show."
2. **Require true splat primitives** — anisotropic 3D Gaussians with rotation, covariance / scale-and-quaternion, opacity, and either RGB or SH color. Isotropic screen-facing point sprites do not count, regardless of fragment shader. Update the rubric's axis-2 anchor.
3. **Tighten the honesty clause** — require the on-screen panel to disclose, in literal terms, what the reconstruction was derived from: "default scene" must say whether it was hand-authored, whether the model could see the inputs at build time, and whether the runtime upload actually drives reconstruction or just decorates a fixed scene.
4. **Add a build-time visibility probe** — instruct the model to print, at the top of its main JS file, a comment listing what it saw in the attached images. If the model saw vase + table, it must say so. This converts an implicit deception vector into an explicit signal.

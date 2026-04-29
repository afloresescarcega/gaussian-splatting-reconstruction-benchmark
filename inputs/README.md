# Inputs

Curated image sets to clip-attach to the arena.ai prompt. Each subdirectory is one set; you pick one set per evaluation run and attach 3–6 images from it.

## Sets

- **`set-A-mipnerf360-bonsai/`** — sampled views from the canonical Mip-NeRF 360 "bonsai" scene. Images are *not* committed here for license reasons; the manifest tells you which to download from the official source and which exact filenames to attach.
- **`set-B-polyhaven-object/`** — your own CC0 (or self-shot) multi-view photographs. These *can* be committed and redistributed.

Both sets are independent of prompt versions; a given prompt version may be evaluated against either or both.

## Capture / sampling guidance

If you're picking views from a larger dataset or shooting your own photos, target:

- **Image count**: 3–6. Fewer than 3 is too sparse for almost any method; more than 6 starts feeling like a "real" capture rather than a sparse-view challenge.
- **Capture pattern**: prefer **object-centric orbit** (camera moving in an arc around the subject) over forward-facing scenes. Orbit captures produce more compelling "rotate around it" web apps and match what feed-forward sparse-view models were trained on.
- **View separation**: spread views around the subject so they actually triangulate. Two near-identical photos provide almost no extra information.
- **Resolution**: 512–1024 px on the long side. Larger images blow up sandbox memory and slow upload-to-arena; smaller images leave too little signal.
- **Format**: JPEG or PNG, sRGB, no aggressive HDR tone-mapping.
- **Subject**: well-textured, not too reflective, not too transparent. Glass, mirrors, and uniform white walls are 3DGS hard-mode.
- **Camera poses**: do *not* provide poses to the model in v1. The prompt is explicit that the model handles pose estimation or picks a pose-free method.

## License caveats

Several standard 3DGS / NeRF datasets (Mip-NeRF 360, NeRF Synthetic, Tanks & Temples, DTU) are research-licensed and **not redistributable** as part of an open benchmark repo. For those datasets we ship only `MANIFEST.md` files pointing at the original download URL with the specific filenames sampled — **never the imagery itself**.

Set B is the redistributable lane. Use CC0 sources (your own photos, [Poly Haven](https://polyhaven.com/), Wikimedia Commons CC0 photo sets) or self-shot images you own.

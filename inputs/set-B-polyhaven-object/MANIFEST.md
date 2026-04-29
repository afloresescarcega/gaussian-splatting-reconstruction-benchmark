# Set B — CC0 / self-shot object capture

Redistributable image set for sharing the benchmark publicly or running it offline. Lives in-tree under `images/`.

## Sourcing options

Pick one of:

### Option 1: Self-shot photos (simplest, you own them)
Walk around an object (a plant, a mug-on-a-saucer, a small toy, a piece of fruit, a book) and take 4–6 photos from different angles. Stay roughly the same distance from the object. Resize to ~1024 px on the long side before committing. Best subjects: matte-textured, well-lit, not too symmetrical.

### Option 2: Poly Haven photo scans
[polyhaven.com](https://polyhaven.com/) ships CC0 assets. Most "models" there are *finished 3D scans* (glTF/Blender), not raw multi-view photos — but the **HDRI** and **textures** sections won't help you here. Check Poly Haven's project page for any raw photo sets that are explicitly distributed (occasional rock/debris scans include source plates). Verify CC0 status per asset before committing.

### Option 3: Wikimedia Commons CC0
Search [commons.wikimedia.org](https://commons.wikimedia.org/) for `<object> filetype:jpg` with the CC0 license filter. Quality and view-coverage vary; you may need to combine images of the same object from multiple uploaders, which is risky for multi-view consistency. Useful as a last resort.

### Option 4: Hugging Face datasets
Search [huggingface.co/datasets](https://huggingface.co/datasets/) for sparse-view / multi-view datasets explicitly tagged CC0 or CC-BY. Confirm redistribution rights per dataset card.

## What lives in this directory

- `MANIFEST.md` — this file.
- `images/` — the 4–6 actual JPEG/PNG files used in evaluations.

## Manifest entries (TODO: fill in once images are committed)

| Filename            | Source                | License | Notes                |
|---------------------|-----------------------|---------|----------------------|
| `01.jpg`            | self-shot (Alex)      | CC0     | front view           |
| `02.jpg`            | self-shot (Alex)      | CC0     | ~90° around          |
| `03.jpg`            | self-shot (Alex)      | CC0     | ~180° around         |
| `04.jpg`            | self-shot (Alex)      | CC0     | ~270° around         |

## Subject metadata

- Subject: *(describe — e.g. "a potted succulent on a desk, late-afternoon window light")*.
- Capture device: *(phone / camera model)*.
- Resolution: target 512–1024 px on the long side after resizing.
- Camera intrinsics: not provided to the model.

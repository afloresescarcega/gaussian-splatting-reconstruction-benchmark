# Set C — Mip-NeRF 360 "garden", dense arc (+ held-out views)

The v1–v4 "garden-table" photos (DSC07956/07970/07986/08001) are frames of the Mip-NeRF 360 **garden** scene. Using the dataset's COLMAP poses (`poses_bounds.npy`), those four sit at orbit angles **138°, 175°, 300°, 333°**: two pairs about 35° apart with a **125° gap** between them. That gap is why every v4 pose estimator registered at most 2 of 4 views. Set C fills the gap.

## Source

- Project page: https://jonbarron.info/mipnerf360/
- Zip: http://storage.googleapis.com/gresearch/refraw360/360_v2.zip (12.5 GB). Only the needed members were range-fetched from `garden/images_2/` (2594×1680) and `garden/poses_bounds.npy`.
- Resized with `sips -Z 2000` to **2000×1296**, which matches the v1–v4 photos (same pipeline; DSC07956 re-derived this way comes out at 1,004,969 B vs the original 1,001,245 B).

## License

Research-licensed. **Do not commit the images.** `images/` and `heldout/` are gitignored; this MANIFEST is the only tracked file. Local copies are in this worktree and in `~/REPOS/gaussian-benchmark/inputs/set-C-mipnerf360-garden-dense/`.

## `images/` — contestant set (7 views, ~25–35° spacing)

| Order | File | Orbit angle | Notes |
|---|---|---|---|
| 1 | DSC07986 | 137.7° | original v1–v4 |
| 2 | DSC07956 | 174.6° | original |
| 3 | DSC08027 | 206.0° | **new**, slightly higher viewpoint |
| 4 | DSC07994 | 234.5° | **new** |
| 5 | DSC07997 | 265.1° | **new** |
| 6 | DSC08001 | 300.2° | original |
| 7 | DSC07970 | 333.4° | original |

Variants for v5:
- **C-7**: all 7 (needs the prompt's 3–6 limit raised to 3–8).
- **C-6**: drop DSC08027 (largest gap becomes ~60°, 175→235).
- **C-4-original**: the v1–v4 photos, kept for longitudinal comparison.

Upload in a shuffled order and rename files (e.g. `img_a.jpg`) so filename sorting can't recover the arc order.

## `heldout/` — judge only, never in a contestant workspace

Six views interleaved with the contestant arc, for automatic PSNR / SSIM / LPIPS on novel views:

| File | Orbit angle |
|---|---|
| DSC08022 | 153.4° |
| DSC07957 | 188.7° |
| DSC08117 | 218.6° |
| DSC08061 | 250.0° |
| DSC07999 | 282.9° |
| DSC08003 | 319.3° |

`heldout/poses_bounds.npy` holds the COLMAP camera-to-world poses + intrinsics for all 185 frames (LLFF layout: per row a 3×5 [R | t | h,w,f] then near/far). To score: Sim(3)-align the contestant's estimated cameras for the `images/` views to these GT poses, then render the exported `.ply` at each held-out pose in a reference rasterizer.

Angles were computed in the plane of the two largest camera-center spreads, around the mean camera center (`tools/angles.py`; fetch with `tools/remote_zip.py`).

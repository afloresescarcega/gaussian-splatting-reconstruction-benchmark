# Set A — Mip-NeRF 360 "bonsai"

Canonical 3DGS benchmark scene. Used so judges can mentally compare the model's output to results published in the 3DGS / Mip-NeRF 360 literature.

## Source

- Project page: https://jonbarron.info/mipnerf360/
- Dataset download: http://storage.googleapis.com/gresearch/refraw360/360_v2.zip (~3 GB, contains all 9 scenes)

After downloading and extracting, the bonsai scene lives at `360_v2/bonsai/images/`.

## License

Research-licensed. **Do not commit any of these images into this repository.** This file (`MANIFEST.md`) is the only thing that lives in-tree for this set; it tells you which exact images to clip-attach in arena.ai so eval runs are reproducible.

## Sampled views (TODO: fill in once Alex picks)

Pick 4 views that are well-separated around the subject. Suggested sampling: every ~Nth image in the directory listing where N ≈ (total_images / 4). Avoid consecutive frames.

| Slot | Filename                  | Notes                              |
|------|---------------------------|------------------------------------|
| 1    | `_DSC8679.JPG` *(example)* | front-facing                       |
| 2    | `_DSC8694.JPG` *(example)* | ~90° around                        |
| 3    | `_DSC8709.JPG` *(example)* | ~180° around                       |
| 4    | `_DSC8724.JPG` *(example)* | ~270° around                       |

(Replace the example filenames with the actual ones you sampled. Keeping the table reproducible matters more than the specific choices.)

## Capture metadata

- Subject: a potted bonsai tree on a tabletop, studio-style indoor lighting.
- Original resolution: ~4946×3286 (4× downsampled copies are also provided in the official zip under `images_4/`, `images_8/`).
- For arena.ai, use one of the downsampled directories (`images_4/` ≈ 1237×822) to keep upload size sane.
- Original capture has ~290 images per scene with COLMAP poses; we ignore the poses for this benchmark.

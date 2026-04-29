# gaussian-benchmark

A benchmark for [arena.ai](https://arena.ai/) that evaluates whether a coding model can implement an end-to-end **3D Gaussian Splatting** reconstruction from a small set of input images, delivered as a deployable web app.

## What this repo is for

This repo is a **tool for the benchmark author**, not anything an evaluated model ever sees. It holds:

- The versioned prompt text (`prompts/`) you copy-paste into arena.ai's "Code" prompt field.
- Curated image sets (`inputs/`) you clip-attach to the prompt at evaluation time.
- The human-judge rubric (`rubric/`) for scoring the deployed web app.
- Observations from each run (`observations/`) — raw material for the next prompt version.

The model receives only the prompt text plus attached images. It cannot see this README, the image manifests, or the rubric.

## How arena.ai's "Code" channel works (relevant constraints)

- **Input**: a single prompt text field plus images attached via the clip icon. **No other file uploads.**
- **Output**: a web app that arena.ai auto-deploys into a browser preview tab.
- **Runtime**: assume pure browser execution. No CUDA, no COLMAP, no Python with arbitrary native deps. WebGPU is the optimistic upper bound.

This makes the benchmark genuinely hard — true 3DGS optimization from a few images, all in a browser sandbox, sits at the research frontier as of 2026. The v1 rubric explicitly rewards honest engineering judgment over fake outputs.

## How to run an evaluation

1. Pick a prompt version (e.g. `prompts/v1.md`) and copy its full contents.
2. Pick an image set (e.g. `inputs/set-A-mipnerf360-bonsai/`) and read its `MANIFEST.md` to know which exact images to attach.
3. Open arena.ai → "Code" → paste the prompt → clip-attach the images → submit.
4. Wait for the deploy to finish, then open both preview tabs.
5. Score with the matching rubric (`rubric/v1.md` for prompt v1).
6. Add a per-run note in `observations/` capturing what the model picked, where it struggled, and anything worth changing in the prompt.

## Versioning policy

- Each prompt is a complete file; never edit a published version. Bump to `prompts/v2.md` instead.
- `rubric/` is parallel-versioned: `rubric/vN.md` matches `prompts/vN.md`.
- `prompts/CHANGELOG.md` records what changed between versions and *why* (which observed failure mode triggered the bump).
- The first line of every prompt carries an HTML comment with the version, so it survives copy-paste and surfaces in any logs.
- Image sets are independent of prompt versions — a single prompt may be evaluated against several sets.

## Repository layout

```
prompts/      v1.md, v2.md, ...       # the artifact pasted into arena.ai
  CHANGELOG.md
rubric/       v1.md, v2.md, ...       # human-judge scoring rubric
inputs/
  set-A-mipnerf360-bonsai/            # canonical 3DGS scene; not redistributed
    MANIFEST.md
  set-B-polyhaven-object/             # CC0 / your-own photos; redistributable
    MANIFEST.md
    images/
observations/                         # one note per evaluated run
  README.md                           # template
```

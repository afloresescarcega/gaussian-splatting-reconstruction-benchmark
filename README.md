# gaussian-benchmark

A benchmark for [arena.ai](https://arena.ai/) that evaluates whether a coding model can implement an end-to-end **3D Gaussian Splatting** reconstruction from a small set of input images, delivered as a deployable web app.

## What this repo is for

This repo is a **tool for the benchmark author**, not anything an evaluated model ever sees. It holds:

- The versioned prompt text (`prompts/`) you copy-paste into arena.ai's "Code" prompt field.
- Curated image sets (`inputs/`) you clip-attach to the prompt at evaluation time.
- The human-judge rubric (`rubric/`) for scoring the deployed web app.
- Observations from each run (`observations/`) — raw material for the next prompt version.

The model receives only the prompt text plus attached images. It cannot see this README, the image manifests, or the rubric.

## Results so far

5 A/B rounds across 3 prompt versions, each scored 0–3 on 5 rubric axes (max 15). Image set is the same 4-photo garden-table set for every entry except v1 B (mipnerf360-garden). Model identities are revealed *post-run* — arena.ai's Option A / Option B labels rotate per round.

| Date       | Prompt | Run | Option A                              | Score | Option B         | Score |
|------------|--------|-----|---------------------------------------|-------|------------------|-------|
| 2026-04-25 | v1     | 1   | `gemini-3.1-pro-preview`              |  9/15 | `gpt-5.5`        |  9/15 |
| 2026-04-25 | v2     | 1   | `gemini-3-flash` (thinking-minimal)   |  3/15 | `gpt-5.4-high`   |  8/15 |
| 2026-04-25 | v3     | 1   | `qwen3.5-397b-a17b`                   |  3/15 | `gpt-5.5`        | 14/15 |
| 2026-04-25 | v3     | 2   | `claude-sonnet-4-6`                   | 10/15 | `gpt-5.5`        | 14/15 |
| 2026-04-26 | v3     | 3   | `claude-opus-4-6-thinking`            |  7/15 | `gpt-5.5`        | 14/15 |

Headlines:

- **`gpt-5.5` has reproduced 14/15 three times on v3 B** (same model, same prompt, same image set). The 1-point gap to 15 is structural — axis 3 (reconstruction faithfulness) caps at 2 on the heuristic-depth + assumed-arc-cameras Approach C path.
- **`gpt-5.5` went from 9/15 (v1 B) to 14/15 (v3 B)** — the strongest cross-prompt signal that the prompt-iteration loop is doing real work. Caveat: v1 B used a different image set than the v3 B runs.
- **A-side spread is wide and model-dependent.** Each v3 A run brought a distinct failure mode: qwen main-thread freeze, sonnet sparse output + buggy visibility probe, opus coord-convention sign bug producing zero output.

Per-run notes are in [`observations/`](observations/); model-identity reveals and longitudinal interpretation are in [`observations/MODEL_IDENTITY.md`](observations/MODEL_IDENTITY.md).

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

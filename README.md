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

6 A/B rounds across 3 prompt versions, each scored 0–3 on 5 rubric axes (max 15). Image set is the same 4-photo garden-table set for every entry except v1 B (mipnerf360-garden). Model identities are revealed *post-run* — arena.ai's Option A / Option B labels rotate per round.

| Date       | Prompt | Run | Option A                              | Score | Option B         | Score |
|------------|--------|-----|---------------------------------------|-------|------------------|-------|
| 2026-04-25 | v1     | 1   | `gemini-3.1-pro-preview`              |  9/15 | `gpt-5.5`        |  9/15 |
| 2026-04-25 | v2     | 1   | `gemini-3-flash` (thinking-minimal)   |  3/15 | `gpt-5.4-high`   |  8/15 |
| 2026-04-25 | v3     | 1   | `qwen3.5-397b-a17b`                   |  3/15 | `gpt-5.5`        | 14/15 |
| 2026-04-25 | v3     | 2   | `claude-sonnet-4-6`                   | 10/15 | `gpt-5.5`        | 14/15 |
| 2026-04-26 | v3     | 3   | `claude-opus-4-6-thinking`            |  7/15 | `gpt-5.5`        | 14/15 |
| 2026-06-09 | v3     | 4   | `claude-opus-4-6-thinking`            | 10/15 | `gpt-5.4-high`   | 12/15 |

Headlines:

- **`gpt-5.5` has reproduced 14/15 three times on v3 B** (same model, same prompt, same image set). The 1-point gap to 15 is structural — axis 3 (reconstruction faithfulness) caps at 2 on the heuristic-depth + assumed-arc-cameras Approach C path.
- **`gpt-5.5` went from 9/15 (v1 B) to 14/15 (v3 B)** — the strongest cross-prompt signal that the prompt-iteration loop is doing real work. Caveat: v1 B used a different image set than the v3 B runs.
- **A-side spread is wide and model-dependent.** Each v3 A run brought a distinct failure mode: qwen main-thread freeze, sonnet sparse output + buggy visibility probe, opus coord-convention sign bug producing zero output.
- **Run 4 (2026-06-09), scored blind before the post-hoc reveal.** `claude-opus-4-6-thinking` (A, 10/15) repeated its run-3 signature — ambitious plane-sweep MVS + one fatal execution bug that zeroes the visible output, this time in the renderer rather than the geometry (7→10 as the bug moved downstream), caught cleanly by the visibility probe. `gpt-5.4-high` (B, 12/15) — the model whose v2 silent black-canvas motivated v3's loud-error contract — now renders a coarse cloud and wires every loud-error check. A mid-session fingerprint guess of `gpt-5.5` for B was wrong (it was `gpt-5.4-high`); scores were locked blind and never anchored to the guess.

Per-run notes are in [`observations/`](observations/); model-identity reveals and longitudinal interpretation are in [`observations/MODEL_IDENTITY.md`](observations/MODEL_IDENTITY.md).

### v4 agentic track (local T3 Code threads)

A separate track, **not comparable with the arena.ai rows above**. Each model ran as an autonomous coding agent in its own isolated local workspace, given only the example photos and could install packages, build and test before handing in. Prompt `prompts/v4.md` is a plain client brief (no benchmark wording). Rubric `rubric/v4.md` adds an isolation gate and a shuffled-upload-order test. All models at medium reasoning effort, single prompt, no follow-ups; same 4 garden-table photos. Judged non-blind for this run.

| Date       | Run | Model                         | Wall time | Run | 3DGS | Faithful | UX | Honesty | Score |
|------------|-----|-------------------------------|-----------|-----|------|----------|----|---------|-------|
| 2026-11-11 | 1   | `claude-sonnet-5-5`           | 16.8 min  | 3   | 3    | 2        | 3  | 3       | 14/15 |
| 2026-11-11 | 1   | `grok-4.7-build-fast`         | 38.3 min  | 3   | 3    | 1        | 3  | 3       | 13/15 |
| 2026-11-11 | 1   | `gemini-3.8-flash`            | 13.1 min  | 3   | 3    | 1        | 2  | 2       | 11/15 |
| 2026-11-11 | 1   | `gpt-6.1-terra`               | 1.4 min   | 3   | 2    | 1        | 2  | 3       | 11/15 |
| 2026-11-11 | 1   | `gpt-5.6-luna`                | 3.6 min   | 1   | 1    | 0        | 1  | 2       |  5/15 |
| 2026-11-11 | 1   | `gpt-6-luna`                  | 1.1 min   | 1   | 1    | 0        | 1  | 1       |  4/15 |
| 2026-11-11 | 1   | `muse-ember-1.0`, `muse-spark-1.3` | —    | —   | —    | —        | —  | —       | did not start (provider error) |

Headlines:

- **No disqualifications.** All six transcripts passed the isolation audit. Antigravity's shell started in the wrong directory (filenames listed, nothing opened), which is flagged as a harness gap.
- **The 4-photo set is the bottleneck.** Its photos sit at 138°/175°/300°/333° around the table (from the dataset's COLMAP poses), so no pose estimator could bridge the 125° gap. Sonnet, Grok and Gemini each registered ≤2/4 views or fell back to an assumed arc. Nobody scored 3 on faithfulness. A dense 7-view set with held-out views is now in `inputs/set-C-mipnerf360-garden-dense/`.
- **Nobody attempted photometric optimization (approach A).** The top two hand-wrote full SfM pipelines (features → essential matrix → triangulation → EWA renderer); Sonnet aligned learned monodepth to triangulated points.
- **Diligence varied 35× at the same effort setting** (64 s to 38 min). Both bottom entries never ran their pipeline on the provided photos.

Full notes: [`observations/2026-11-11_v4-agentic/RESULTS.md`](observations/2026-11-11_v4-agentic/RESULTS.md). Next version: [`prompts/V5_PLAN.md`](prompts/V5_PLAN.md).

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
prompts/      v1.md, v2.md, ...       # the artifact pasted into arena.ai (v4+: agentic brief)
  CHANGELOG.md
  V5_PLAN.md                          # fixes + ideas queued for v5
rubric/       v1.md, v2.md, ...       # human-judge scoring rubric
inputs/
  set-A-mipnerf360-bonsai/            # canonical 3DGS scene; not redistributed
    MANIFEST.md
  set-B-polyhaven-object/             # CC0 / your-own photos; redistributable
    MANIFEST.md
    images/
  set-C-mipnerf360-garden-dense/      # 7-view garden arc + 6 held-out views; not redistributed
    MANIFEST.md
observations/                         # one note per evaluated run
  README.md                           # template
  2026-11-11_v4-agentic/              # v4 agentic run 1 results
tools/
  judge-harness.mjs                   # headless-Chrome upload/orbit/export runner
  remote_zip.py, angles.py            # fetch dataset frames by HTTP range; orbit angle per frame
```

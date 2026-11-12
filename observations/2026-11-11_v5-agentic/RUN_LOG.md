# v5 agentic run 1 — 2026-11-11 — run log (not yet judged)

**Track:** v5-agentic. Prompt `prompts/v5.md`, rubric `rubric/v5.md`. Same 8 models as v4, all at medium effort, `full-access`, one prompt, no follow-ups.

## Setup

- **Photos:** set C, all 7 views, renamed to `img_xxxx.jpg` (the name order is not the arc order). APP1–APP15 and COM segments were stripped from each JPEG without re-encoding, so pixels are unchanged. The rename map is in `archive/2026-11-11_v5-agentic/photo_name_map.tsv`.
- **Workspaces:** each a fresh git repo containing only `photos/` (one commit, author `dev`). Six are at `~/Sandboxes/splatapp-<hex>` (parent `chmod 311`). The two Muse workspaces are at `~/Sandboxes-<hex>/splatapp-<hex>`; see the Muse note below. The model↔hex map is in `archive/.../workspaces.tsv`; keep it away from the blind judge.
- **Locks during the run:** `~/REPOS/gaussian-benchmark` `000`, `~/.t3/userdata/attachments` `000`, `~/Sandboxes` `311`. All were restored to `755` after the last contestant finished (~20:13Z).
- Each prompt gives the contestant's absolute project path (`{{WORKSPACE}}`).

## Isolation fixes (P0 items from V5_PLAN)

- **Muse:** fixed. The "session MCP base configuration is unavailable" error happens whenever the workspace's **parent directory isn't readable**. The `chmod 311 ~/Sandboxes` lock did that, and it was also the v4 cause. A probe with a readable parent started fine; the same probe in the locked parent failed. The fix: each Muse workspace gets its own readable parent holding only that one workspace. The first two Muse launches failed before starting and left their workspaces untouched; both were relaunched after the move.
- **Antigravity cwd:** worked around, but the root cause in T3/Antigravity isn't fixed. Its shell still starts in `~/.t3/userdata/attachments`. With that dir at `000`, the first shell call fails (`fork/exec /bin/zsh: permission denied`) and the agent then works in the absolute project path from the prompt. Probe: it also ran `ls -ld` on the attachments dir and `ls -la ..` (before `~/Sandboxes` was locked). Check for this in Gate 0.

## Runs

| Model | Workspace | Start (Z) | End (Z) | Wall | Note |
|---|---|---|---|---|---|
| `claude-sonnet-5-5` | 6872212c | 19:18:52 | 19:34:03 | 15.2 min | |
| `gpt-6.1-terra` | 71a7bb9f | 19:19:25 | 19:19:59 | 0.6 min | Gave up: scaffold only. Its reply says "not complete … does not reconstruct, render, calculate PSNR, or export". |
| `gpt-6-luna` | 4dcb546c | 19:19:56 | 19:20:46 | 0.8 min | Gave up: "colored spheres using an assumed layout … did not run the browser flow". No `NOTES.md`. |
| `gpt-5.6-luna` | 354941c6 | 19:20:27 | 19:30:11 | 9.7 min | Installed Playwright. |
| `grok-4.7-build-fast` | 0e8388e7 | 19:20:58 | 20:13:19 | 52.4 min | Longest run, within the 60-min budget. |
| `gemini-3.8-flash` (Antigravity) | 667cf6a4 | 19:21:32 | 19:37:45 | 16.2 min | |
| `muse-ember-1.0` | 6ebd4a8d | 19:24:06 | 19:51:36 | 27.5 min | Thread auto-resumed for 19 s at 20:04:16 when a background task finished. Not a follow-up from us; check in Gate 0 what it changed. |
| `muse-spark-1.3` | 64571398 | 19:24:38 | 19:49:43 | 25.1 min | |

The submissions (no `node_modules`, no `photos/`) were frozen to `archive/2026-11-11_v5-agentic/submissions/` after all runs ended.

## To do before scoring

1. Gate 0 transcript audit for all 8 threads (watch for Antigravity's `~/.t3/userdata/attachments` and for Ember's 20:04 auto-resume).
2. Build the F pipeline (cameras.json → Sim(3) to GT → reference rasterizer at the 6 held-out poses → LPIPS/SSIM/PSNR, sky masked) and measure baselines (a)/(b)/(c).
3. Blind judging in a fresh session given only `submissions/<hex>` (not `workspaces.tsv`).
4. Runs 2 and 3 per model (rubric: median of 3).

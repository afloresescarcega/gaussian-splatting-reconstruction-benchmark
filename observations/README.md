# Observations

One markdown file per evaluation run. Filename convention:

```
YYYY-MM-DD_<model-name>_<prompt-version>_<input-set>.md
```

For example: `2026-04-25_claude-opus-4-7_v1_set-A.md`.

## Template

```markdown
# Run: <model> on <prompt-version> with <input-set>

- Date: YYYY-MM-DD
- Prompt version: vN
- Rubric version: vN
- Image set: set-X-<name>, attached N images: <list filenames>
- arena.ai run URL (if any): <link>

## What the model produced

Two- to four-sentence summary of the deployed app. Which approach family did it pick (A/B/C from prompts/vN.md)? Which libraries did it actually pull in? What did it claim in the on-screen description?

## Rubric scores

| Axis | Score | One-line note |
|------|-------|---------------|
| 1. Deployed & runs            | 0–3 |  |
| 2. Actually 3DGS              | 0–3 |  |
| 3. Reconstruction faithfulness| 0–3 |  |
| 4. Web app UX                 | 0–3 |  |
| 5. Engineering judgment       | 0–3 |  |

## Failure modes / friction

Concrete things that went wrong or felt off — fabricated package names, ignored prompt sections, hallucinated APIs, runtime errors, deployment timeouts, dishonesty about output, etc.

## Implications for the next prompt version

One or two sentences on whether this run suggests a prompt-version bump, and what to change. Most runs won't justify a bump; we change the prompt only when a pattern repeats across models or input sets.
```

## What to log vs ignore

Worth logging:
- Library or approach choices that were obviously wrong for the constraint.
- Sections of the prompt the model clearly ignored.
- Honest behaviors worth rewarding (graceful approximation with clear caveats).
- Dishonesty (fake outputs presented as real reconstructions).

Not worth logging:
- Routine cosmetic differences between runs.
- Anything you'd normally summarize as "it just worked" on a strong run — a one-line "worked, no notes" is enough.

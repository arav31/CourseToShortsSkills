---
name: course-video
description: Design, code, narrate, render and visually review a vertical (9:16) 3Blue1Brown-style Manim explainer short, with synced voiceover and burned-in captions, for one math, science, CS or economics idea. Use for any request to make or fix an explainer video, short, reel or animation of a concept, whether it comes from a course plan (short_plan.json) or stands alone.
---

# Course Video

**Paths.** `$SKILL_DIR` means this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`; otherwise the folder containing this SKILL.md). `$PY` is the Python interpreter printed by the course-to-shorts doctor (`PY=...`). Run directories such as `runs/<course>` are relative to the user's working directory.

One short = one folder (`runs/<course>/shorts/<NN>-<slug>/`, or any folder for a standalone
concept) containing `storyboard.md` and `scene.py`. The scripts do the mechanical work
(narration, rendering, captions, audio mix, frame sampling). You do the teaching: the
storyboard, the scene code, and looking at the result with a critical eye.

## 1. Storyboard

From the plan entry (hook, claim, worked example, visual idea), write `storyboard.md`:
claim, objects, layout, invariant, reveal, and a beat table (narration ↔ motion).
Follow [references/storyboard.md](references/storyboard.md); hold it against
[references/quality-bar.md](references/quality-bar.md) before coding.

## 2. Scene

Write `scene.py` with shortkit. Read [references/shortkit.md](references/shortkit.md) and use
[assets/example_scene.py](assets/example_scene.py) as the model of structure and style:

- A literal `BEATS` list of `(id, narration)`; one `with self.beat(id):` block per beat, in order.
- Persistent objects, transformed beat by beat; numbers computed in Python, never retyped.
- All maths through `tex()` (real LaTeX); words through `text()`; labels on `plate()`s.
- The diagram fills `STAGE`; the caption band stays empty.

Narration is spoken English for the ear ("A times x", "x sub one", "two by two"), 1–2
sentences per beat, and the first line poses the question. Total length follows the
idea; 30–75 s is typical.

## 3. Preview render and look

```bash
$PY "$SKILL_DIR/scripts/render.py" <short_dir>            # 540x960 preview, voice via edge-tts (cached per beat)
```

It prints a beat timeline, automatic issues (layout errors from the scene, silent gaps,
static stretches, blank frames) and contact-sheet paths. Then **open every
`review/sheet-*.png` and look**. The automatic checks only find geometry problems; you have
to judge whether the picture teaches. For a closer look at a moment or a transition:

```bash
$PY "$SKILL_DIR/scripts/audit.py" frames <short_dir>/preview.mp4 --at 12.5 13 13.5
```

Fix the scene and re-render until there are no errors and the sheets pass the quality bar.
Typical fixes: move a label off a line, split a crowded beat, enlarge the main object,
replace a decorative motion with the actual operation, rewrite a line so voice and picture match.
Unchanged narration is not re-synthesized, so iterating is cheap (~1 min per render).

Voice options: `--voice edge-tts` (default; natural, needs network), `--voice piper` (offline),
`--voice say` (macOS), `--voice openai` (needs `OPENAI_API_KEY`), `--voice none` (silent;
captions still show the narration). `--voice-name` picks a voice; `--no-captions` disables burning.

## 4. Final render, last look, approve

```bash
$PY "$SKILL_DIR/scripts/render.py" <short_dir> --quality final      # 1080x1920, 30 fps, H.264
$PY "$SKILL_DIR/scripts/audit.py" approve <short_dir> --notes "what you checked"
```

Look at the final contact sheets again (final renders occasionally differ from previews), then
approve. The approval in `review.json` is bound to the MP4's hash; any re-render voids it. If
something is wrong, `audit.py reject <short_dir> --notes "..."`, fix, re-render.

## Working on many shorts

Shorts are independent once the plan exists. If you can run subagents, give each one a
short (its plan entry, the run dir, and this skill's name) and review their contact sheets
yourself before approving. Keep the visual language consistent across a series: same palette
meanings, same title style, similar pacing.

## Output

`<short_dir>/<NN>-<slug>.mp4` (final), `preview.mp4`, `<name>.srt`, `render_report.json`,
`review/sheet-*.png`, `review.json`, `timing.json`, `audio/`, `build/` (Manim cache, deletable).

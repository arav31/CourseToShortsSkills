---
name: course-to-shorts
description: Turn a course (an MIT OpenCourseWare or other course website, a syllabus, lecture PDFs, or a folder of materials) into comprehensive LaTeX study notes plus a series of narrated, 3Blue1Brown-style vertical explainer videos for Instagram Reels, YouTube Shorts or TikTok. Use as the entry point whenever someone shares a course link or course files and wants notes, shorts, reels or explainer videos from it, or asks where a course run stands; it sequences course-plan, course-notes, course-video and course-reels and gates the result.
---

# Course to Shorts

**Paths.** `$SKILL_DIR` means this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`; otherwise the folder containing this SKILL.md). `$PY` is the Python interpreter printed by the course-to-shorts doctor (`PY=...`). Run directories such as `runs/<course>` are relative to the user's working directory.

The runbook for a whole course. Each stage is its own skill; this one sets up the
environment, runs the stages in order, keeps the user in the loop, and checks the result.

## 0. Environment (once per machine)

```bash
python3 "$SKILL_DIR/scripts/doctor.py"            # what is present / missing
python3 "$SKILL_DIR/scripts/doctor.py" --install  # creates ~/.course-shorts/venv with manim, pymupdf, edge-tts
```

System tools are reported with install commands but not installed for you: FFmpeg (with
libass for captions), a TeX engine (tectonic is easiest), and cairo/pango for Manim. The last
line prints `PY=...`: use that interpreter for every script in the course-* skills.

## 1. Plan: course-plan

Ingest the course into `runs/<course-slug>/sources/`, write `outline.json` and
`short_plan.json`, and pass `check_plan.py`. Show the user the list of shorts (title + claim)
and the skipped units. If they asked for the full pipeline in one go, carry on; otherwise wait
for their go-ahead or edits.

Scope defaults: notes cover the whole course; shorts cover every unit that has a visual idea.
"A demo" or "a few videos" means 3–5 well-chosen shorts. When unsure how many, ask.

## 2. Notes: course-notes

Write `notes/notes.tex` + `notes/units/uNN.tex`, build with `build_notes.py`, fix every error,
and look at the page previews.

## 3. Videos: course-video

For each short in plan order: storyboard → scene.py → preview render → look at the contact
sheets → fix → final render → look again → approve. Short folders are
`runs/<course-slug>/shorts/<NN>-<slug>/` where NN is the short's position in the plan.

## Parallel work

After step 1, notes units and individual shorts are independent. If you can launch subagents,
run them in parallel: one per short (or per 2–3 notes units), each told the run directory, its
item id, the skill to use, and its own scratch folder (parallel agents that share one scratch
directory overwrite each other's helper files). You keep the editorial role: review every short's contact sheets
and the notes previews yourself before approving, and keep the series consistent.

## 4. Gate

```bash
$PY "$SKILL_DIR/scripts/run_status.py" runs/<course-slug>          # where things stand
$PY "$SKILL_DIR/scripts/run_status.py" runs/<course-slug> --gate   # exit 1 until publish-ready
```

Publish-ready means: the plan check passes for the current plan; the notes compiled with a real
TeX engine with no errors and every outline unit has a chapter; every planned short has a
final render with no errors and an approval bound to that exact MP4. Stale reports count as
missing. Report the gate result honestly; list any blockers you could not resolve.

## 5. Publish: course-reels (only when asked)

Build the posting queue; publishing to Instagram posts publicly from the user's account, so
it needs their explicit confirmation, credentials in their environment and public video URLs.

## What good looks like

- Notes a student could learn the course from: complete, grounded in the sources, with proofs,
  worked examples, teaching figures and solved exercises.
- Shorts where the animation carries the explanation: a real object from second one, persistent
  objects that transform, numbers that agree everywhere, readable on a phone, narration in sync.
- Nothing published or called "done" without someone actually looking at the frames and pages.

Directory layout and file contracts: [references/run-layout.md](references/run-layout.md).

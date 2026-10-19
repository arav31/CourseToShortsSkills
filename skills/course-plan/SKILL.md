---
name: course-plan
description: Ingest a course's materials (an MIT OpenCourseWare or other course website, syllabus, lecture PDFs, transcripts, or a local folder) into readable text sources, then write the course outline and an ordered plan of short explainer videos, each with a concrete, verified worked example. Use when starting from a course link or files, or when someone wants a course outline, syllabus breakdown, curriculum, or list of shorts/reels for a course.
---

# Course Plan

**Paths.** `$SKILL_DIR` means this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`; otherwise the folder containing this SKILL.md). `$PY` is the Python interpreter printed by the course-to-shorts doctor (`PY=...`). Run directories such as `runs/<course>` are relative to the user's working directory.

Produces three things in `runs/<course-slug>/`: `sources/` (the course as text),
`outline.json` (the course's own structure) and `short_plan.json` (the video series).
Every later stage (notes, videos, publishing) reads these, so accuracy here pays off.

## 1. Ingest

```bash
$PY "$SKILL_DIR/scripts/ingest.py" "https://ocw.mit.edu/courses/<course>/" --run runs/<course-slug>
# also accepts PDFs, folders, several sources at once:
$PY "$SKILL_DIR/scripts/ingest.py" "<url>" ~/Downloads/lecture-notes/ --run runs/<course-slug>
```

It crawls within the course's own path, extracts PDF text, strips navigation and footer
boilerplate, and writes one `.txt` per page/PDF plus `sources/INDEX.md`. Then:

- Read `sources/INDEX.md`. Expect a syllabus or calendar, lecture notes and/or
  transcripts, and ideally problem sets, solutions and exams.
- If something important is missing, say so and add it (another URL, or files the user
  provides). Scanned PDFs show up as "needs OCR" warnings; tell the user which ones.
- Only course material counts. Menu items, licence text or "Instructor Insights" pages
  are never topics.

## 2. Outline → `outline.json`

Read the syllabus/calendar first, then skim the notes and transcripts unit by unit.
Units mirror the course's own sequence (lectures, sessions, chapters). Give each one a
real summary and the source files you read for it. Use `grep -il "<term>" sources/*.txt`
to find where a topic is treated. Schema: [references/plan-schema.md](references/plan-schema.md).

## 3. Shorts → `short_plan.json`

Pick one idea per short, in prerequisite order, covering every unit or listing it under
`skipped_units` with a reason. For each short write a hook, a one-sentence claim, a worked
example, the visual idea, a misconception and a practice question.
Read [references/worked-examples.md](references/worked-examples.md) before writing examples.
The non-negotiables:

- Each worked example uses concrete values/objects that exercise this concept's
  actual mechanism, small enough to draw on a phone.
- Compute every number. For anything beyond one-step arithmetic, check it with a quick
  Python snippet before it goes into the plan.
- No example is reused across shorts.
- `visual` names the persistent objects and the motion that proves the claim, not
  "show the formula".

If the user asked for a specific number of shorts (or "a quick demo"), plan that many,
choosing the ones that best show the course's arc. Otherwise cover the course.

## 4. Check

```bash
$PY "$SKILL_DIR/scripts/check_plan.py" runs/<course-slug>
```

Fix every ERROR and re-run until it passes; read the warnings and fix the real ones.
It writes `plan_check.json`, which the course-to-shorts gate uses.

## 5. Show the plan

Before any notes or videos are produced, give the user a compact table (`id`, title,
one-line claim, units) and the skipped units. Proceed when they are happy; if they
already asked for the whole pipeline in one go, continue straight away.

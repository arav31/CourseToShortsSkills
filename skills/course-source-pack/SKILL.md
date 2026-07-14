---
name: course-source-pack
description: Use when a user gives a course URL, OCW link, syllabus, PDF, or folder of course material and wants a reusable source pack for notes, lesson planning, Manim shorts, or Instagram publishing.
---

# Course Source Pack

## Purpose

Turn a course link or course files into a structured `source_pack.json` that later skills can use. Prefer broad source coverage over a tiny scrape: include the syllabus, lecture notes, readings, assignments, exams, transcripts, and PDFs when available.

## Workflow

1. Set `COURSE_SHORTS_ROOT` to this plugin's absolute root and call its root-resolving wrapper. Set `COURSE_SHORTS_PYTHON` to the dependency-equipped interpreter when `python3` is not the right one. Do not assume the current directory is the repository root.
2. Create one run directory per course under `runs/<course-slug>`.
3. Extract the source pack:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" extract "COURSE_URL" --out runs/<course-slug> --max-pages 160 --max-pdfs 100
```

For offline validation:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" extract --sample linear_algebra --out runs/sample-linear-algebra
```

4. Inspect `runs/<course-slug>/source_pack.json` before continuing. Check that it includes enough pages/PDFs to represent the full course.

## Quality Bar

- Do not proceed with a one-page pack unless the course genuinely has only one source.
- Prefer course-owned pages and PDFs over random web summaries.
- Keep source URLs in the JSON so later notes can cite where concepts came from.
- If a PDF has no extractable text, record the warning and tell the user it may need OCR or manual upload.

## Handoff

After extraction, trigger the next skill based on the user's goal:

- `course-short-plan` for concept order and shorts queue design.
- `course-latex-notes` for comprehensive course notes.
- `course-manim-3b1b` for visual scene generation.

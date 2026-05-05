---
name: course-output-validator
description: Use when validating a generated course run before upload or handoff, including notes.tex/notes.pdf quality, Manim scenes, scripts, SRT captions, rendered MP4s, voiceover/audio, and Instagram queue readiness.
---

# Course Output Validator

## Purpose

Run a reusable validation pass over `runs/<course>` so generated notes and videos are not treated as publish-ready while obvious quality failures remain.

## Workflow

1. Run the validator from the repository root:

```bash
python tools/validate_course_run.py runs/<course>
```

2. Treat any `FAIL` as blocking for upload, publishing, or final handoff. Fix the artifact or rerun the relevant stage, then run the validator again.
3. Use draft mode only while iterating before final render/audio:

```bash
python tools/validate_course_run.py runs/<course> --draft
```

4. Use fallback-PDF allowance only for local previews. Do not use it for publish-ready course notes unless the user explicitly accepts a non-LaTeX PDF preview:

```bash
python tools/validate_course_run.py runs/<course> --allow-fallback-pdf
```

## Checks

- Notes: `notes.tex`, `notes.md`, `notes.pdf`, and `notes_compile_report.json`.
- LaTeX quality: prose/Python-list matrices, escaped exponent text, bare powers outside math mode, and prose `sqrt(...)` expressions.
- Scene assets: expected Manim scene files, script markdown, SRT captions, Python syntax, vertical scene config, sparse animation, repeated-looking scene source, and matrix/list notation leaking into on-screen text.
- Videos: expected final MP4s, Manim MP4s when scenes exist, duration, vertical orientation, blank sampled frames, static sampled frames, and audio streams.
- Publish queue: local video file existence and public URL warnings for API publishing.

## Quality Rule

Before saying a run is upload-ready, run the validator in strict mode and report the command result. Warnings can be accepted with judgment; failures must be fixed or explicitly called out as unresolved blockers.

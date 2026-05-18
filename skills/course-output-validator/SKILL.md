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

4. Run visual frame audit after rendering and inspect the generated contact sheets:

```bash
python tools/audit_video_frames.py runs/<course>
```

5. Use fallback-PDF allowance only for local previews. Do not use it for publish-ready course notes unless the user explicitly accepts a non-LaTeX PDF preview:

```bash
python tools/validate_course_run.py runs/<course> --allow-fallback-pdf
```

## Checks

- Notes: `notes.tex`, `notes.md`, `notes.pdf`, and `notes_compile_report.json`, including a depth check for full-course coverage and a ban on source inventory/checklist placeholders.
- LaTeX quality: prose/Python-list matrices, escaped exponent text, bare powers outside math mode, and prose `sqrt(...)` expressions.
- Scene assets: expected Manim scene files, script markdown, SRT captions, Python syntax, vertical scene config, sparse animation, repeated-looking scene source, domain-specific group/economics renderer routing, and matrix/list notation leaking into on-screen text.
- Videos: expected final MP4s, Manim MP4s when scenes exist, duration, vertical orientation, blank sampled frames, static sampled frames, audio streams, and render-report sync proving the final MP4 is not shorter than narration.
- Visual audit: contact sheets and frame-density metrics from `visual_frame_audit.json`; use them to catch overlap, crowded diagrams, formula glyph boxes, and text crossed by diagram lines before upload.
- Publish queue: local video file existence and public URL warnings for API publishing.

## Quality Rule

Before saying a run is upload-ready, run the validator in strict mode and report the command result. Warnings can be accepted with judgment; failures must be fixed or explicitly called out as unresolved blockers.

- Validation must fail notes that do not contain embedded figures/graphs and must fail final renders whose duration is not aligned to the measured voiceover duration. Scene validation should also require the collision-aware layout helper in generated Manim code.

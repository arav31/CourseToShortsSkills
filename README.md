# CourseToShortsSkills

Codex skills and tooling for turning a course link, syllabus, PDF set, or course folder into deep study notes and a queue of visual short-form explainer videos.

The intended use case is: paste a course link such as MIT OCW, generate a reusable course source pack, compile comprehensive LaTeX notes, produce a beginner-safe shorts curriculum, generate concept-specific Manim scenes, render vertical videos with optional voiceover, validate the output, and prepare an Instagram Reels playlist queue.

This repo is built to be shared. The skills are plain folders under `skills/`, the workflow is driven by Python tools under `tools/`, and contributors can add domains, visual families, validators, and publishing adapters without changing Codex itself.

## What This Produces

A normal course run creates artifacts like:

```text
runs/<course>/
  source_pack.json
  short_plan.json
  notes.tex
  notes.md
  notes.pdf
  notes_compile_report.json
  scenes/
  scripts/
  captions/
  videos/
    *_raw.mp4
    *_final.mp4
  audio/
  logs/
  render_report.json
  visual_audit/
  visual_frame_audit.json
  instagram_publish_queue.json
  instagram_publish_results.json
```

The workflow is designed around these quality goals:

- Notes should be useful as a serious course-learning proxy, not a summary.
- Shorts should be ordered so a beginner can follow the dependency chain.
- Every short needs a concrete worked example, even for theoretical topics.
- Examples should be fresh across the queue. Reusing the same numbers with a new title is treated as a bug.
- Manim scenes should be topic-specific, visual, readable on a phone, and free of text overlap.
- Final videos should not be forced into a one-minute limit. Timing is based on the script, captions, and visual reading time.
- Voiceover can be attached when a voice engine is selected; silent output is also a supported local/final mode when `--voice-engine none` is explicit.
- Instagram publishing requires public video URLs and Meta/Instagram credentials; local MP4 paths are not enough for API publishing.

## Repository Layout

```text
skills/
  course-source-pack/
  course-short-plan/
  course-latex-notes/
  course-animation-planner/
  course-manim-3b1b/
  course-render-voiceover/
  course-output-validator/
  course-instagram-series/
tools/
  stem_course.py
  validate_course_run.py
  audit_video_frames.py
requirements.txt
REQUIREMENTS.md
README.md
```

- `skills/` contains Codex skill instructions. These tell Codex when and how to run each stage.
- `tools/stem_course.py` is the main CLI. It extracts, plans, writes notes, generates Manim, renders videos, builds queues, and publishes.
- `tools/validate_course_run.py` is the quality gate for notes, examples, scenes, videos, audio, and publishing readiness.
- `tools/audit_video_frames.py` samples rendered videos into contact sheets and frame-density metrics.
- `requirements.txt` contains Python package requirements.
- `REQUIREMENTS.md` explains system dependencies such as LaTeX, FFmpeg, Manim, and voice engines.

## Installation

Install the system dependencies from [REQUIREMENTS.md](REQUIREMENTS.md). The important ones are:

- Python 3.10+
- FFmpeg
- Manim dependencies
- A TeX engine for true LaTeX PDF compilation: `tectonic`, BasicTeX, MacTeX, `latexmk`, or `pdflatex`
- Optional voice engines: OpenAI TTS, `edge-tts`, or macOS `say`

Then install Python dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Install the skills into Codex:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

You can also keep the repository cloned and tell Codex to use the skills in this repo directly.

## Quick Start

Run the whole pipeline from a course URL:

```bash
python tools/stem_course.py all \
  "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/" \
  --out runs/linear-algebra \
  --max-shorts 8 \
  --voice-engine none \
  --pdf-engine auto
```

Run the offline demo course:

```bash
python tools/stem_course.py all \
  --sample linear_algebra \
  --out runs/sample-linear-algebra \
  --max-shorts 3 \
  --voice-engine none \
  --pdf-engine fallback
```

Validate the output:

```bash
python tools/audit_video_frames.py runs/sample-linear-algebra
python tools/validate_course_run.py runs/sample-linear-algebra --allow-fallback-pdf
```

Use `--allow-fallback-pdf` only when you accept the local PyMuPDF PDF preview. For a real LaTeX-compiled PDF, install a TeX engine and use `--pdf-engine latex`.

## Pipeline Commands

The `all` command runs every stage:

```bash
python tools/stem_course.py all COURSE_URL --out runs/<course> --max-shorts 12
```

The manual stage-by-stage pipeline is:

```bash
python tools/stem_course.py extract COURSE_URL --out runs/<course>
python tools/stem_course.py plan --run runs/<course> --max-shorts 12
python tools/stem_course.py notes --run runs/<course> --compile
python tools/stem_course.py manim --run runs/<course>
python tools/stem_course.py render --run runs/<course> --voice-engine none
python tools/audit_video_frames.py runs/<course>
python tools/validate_course_run.py runs/<course>
python tools/stem_course.py queue --run runs/<course> --playlist "Course Name"
python tools/stem_course.py publish --run runs/<course> --dry-run
```

Useful `all` flags:

```text
--sample linear_algebra
--max-pages 160
--max-pdfs 100
--max-shorts 40
--quality l|m
--voice-engine none|say|edge-tts|openai
--playlist "Course Name"
--public-base-url "https://cdn.example.com/course/"
--pdf-engine auto|latex|fallback|none
--no-pdf
--no-render
```

## Skill Overview

Each skill is a small operating manual for Codex. The skills share the same CLI and pass artifacts through the same `runs/<course>` directory.

| Skill | Use When | Main Inputs | Main Outputs |
| --- | --- | --- | --- |
| `course-source-pack` | The user provides a course URL, OCW page, PDF, syllabus, or folder. | Course URL or local course material. | `source_pack.json` |
| `course-short-plan` | The user wants an ordered queue of shorts. | `source_pack.json` | `short_plan.json` |
| `course-latex-notes` | The user wants comprehensive notes and a PDF. | `source_pack.json`, optional `short_plan.json` | `notes.tex`, `notes.md`, `notes.pdf`, `notes_compile_report.json` |
| `course-animation-planner` | A concept needs a real visual story before Manim code. | One short/concept. | Animation plan embedded into Manim/script decisions. |
| `course-manim-3b1b` | The user wants course-specific Manim scenes. | `short_plan.json` | `scenes/`, `scripts/`, `captions/` |
| `course-render-voiceover` | Scenes need final vertical MP4s and optional narration. | `scenes/`, `scripts/`, `captions/` | `videos/`, `audio/`, `render_report.json` |
| `course-output-validator` | A run needs quality checks before handoff/upload. | Full `runs/<course>` directory. | Human or JSON validation report. |
| `course-instagram-series` | The user wants a Reels playlist queue or publishing. | Rendered videos, captions, public URLs. | `instagram_publish_queue.json`, optional `instagram_publish_results.json` |

## Skill Details

### `course-source-pack`

Purpose: collect course material into `source_pack.json`.

How it works:

- Crawls course-owned pages and PDFs when a URL is provided.
- Captures titles, URLs, extracted text, and warnings.
- Supports a local offline sample with `--sample linear_algebra`.
- Keeps the source pack reusable so later stages do not have to rescrape.

Quality rules:

- Prefer official course pages and PDFs over random summaries.
- Include enough sources to represent the whole course: syllabus, lecture notes, assignments, readings, exams, transcripts, and PDFs when available.
- Do not continue from a tiny source pack unless the course is genuinely tiny.
- Record PDF extraction warnings so OCR/manual upload needs are visible.

Command:

```bash
python tools/stem_course.py extract "COURSE_URL" --out runs/<course> --max-pages 160 --max-pdfs 100
```

### `course-short-plan`

Purpose: create `short_plan.json`, the ordered curriculum for videos.

How it works:

- Detects the course domain from source text.
- Starts from curated domain libraries when available.
- Adds source-derived concepts when the course includes extra vocabulary.
- Orders concepts by prerequisites so a new learner can follow.
- Builds each short with hook, intuition, formula, prerequisite list, misconception, worked example, question prompt, and visual type.

Important standards:

- No active-recall section inside the video. `question_prompt` stays available for notes, captions, queues, and practice.
- No fixed one-minute cap.
- Every short must include a worked example with actual numbers, equations, sets, vectors, graphs, or a concrete symbolic object.
- The example must teach the concept by naming the objects, applying the rule/property, and stating the conclusion.
- Examples must be fresh. The validator fails repeated setup/calculation pairs.

Command:

```bash
python tools/stem_course.py plan --run runs/<course> --max-shorts 30
```

### `course-latex-notes`

Purpose: create comprehensive course notes that can serve as a real study document.

How it works:

- Reads `source_pack.json` and `short_plan.json`.
- Writes both `notes.tex` and `notes.md`.
- Includes course map, prerequisite chain, key concepts, concept explanations, notation tables, formula tables, definitions, properties, worked examples, visual interpretations, common traps, conceptual questions, and application questions.
- Includes supplemental source-derived topics even if they are not selected for shorts.
- Can compile a PDF with LaTeX or generate a fallback PDF preview.

PDF behavior:

- `--pdf-engine auto` tries LaTeX first and falls back if no TeX engine is available.
- `--pdf-engine latex` requires real LaTeX compilation and fails if unavailable.
- `--pdf-engine fallback` creates a local PDF preview from the generated notes data.
- `notes_compile_report.json` records which engine produced the PDF.

Quality rules:

- Notes should not be a source inventory or checklist.
- Hard topics still belong in notes even if they are not good video hooks.
- Formulas need symbol explanations.
- Matrices and vectors should be formatted as LaTeX math, not Python/prose lists.
- Abstract concepts need concrete examples and questions.
- A 50+ page document is acceptable for a broad course.

Command:

```bash
python tools/stem_course.py notes --run runs/<course> --compile --pdf-engine auto
```

### `course-animation-planner`

Purpose: design the visual explanation before writing Manim code.

How it works:

- Takes one concept and turns it into a visual claim.
- Names the concrete screen objects.
- Chooses transformations: unwrap, project, rotate, shear, stretch, partition, match, collapse, compare, or similar.
- Defines 4 to 7 motion beats, an invariant, and a reveal.
- Identifies failure modes such as static text cards, generic arrows, or unreadable diagrams.

Use this skill before adding a new visual family or when a generated scene feels generic.

Quality rules:

- The visual motion should carry the intuition.
- Use sparse labels rather than dense paragraphs.
- Use color as semantic bookkeeping.
- The worked example must be visible.

### `course-manim-3b1b`

Purpose: generate concept-specific vertical Manim scenes.

How it works:

- Reads `short_plan.json`.
- Generates one Python scene per short under `scenes/`.
- Generates matching script markdown under `scripts/`.
- Generates SRT captions under `captions/`.
- Routes concepts to domain-specific visual families such as linear algebra, calculus, physics, CS, group theory, economics, probability, and numeric rules.
- Uses safe-area and collision-aware layout helpers so text, formulas, labels, captions, and diagrams do not overlap.

Current visual standards:

- Do not reuse the same generic vector animation for every topic.
- Render matrices/vectors as stacked math objects, not single-line Python lists.
- Put text on subtle backplates when diagram lines could run behind it.
- Simplify screen formulas and keep dense exact notation for notes.
- Pace waits and captions from script text so learners can read and inspect the example.
- Clear old text before placing formulas in the same safe area.
- Group theory and economics must use domain-specific renderers instead of falling through to generic diagrams.

Command:

```bash
python tools/stem_course.py manim --run runs/<course>
```

### `course-render-voiceover`

Purpose: render final phone-ready MP4s, with optional narration.

How it works:

- Renders Manim scenes into raw MP4s.
- Optionally generates voiceover.
- Muxes final video/audio while preserving duration alignment.
- Records render and timing details in `render_report.json`.
- Produces final MP4s in `videos/`.

Voice engines:

- `none`: intentional silent mode. Missing audio is valid when this is selected.
- `openai`: requires `OPENAI_API_KEY`; optional `OPENAI_TTS_MODEL` and `OPENAI_TTS_VOICE`.
- `edge-tts`: requires the `edge-tts` package and network access.
- `say`: macOS fallback; validates that non-empty audio was actually produced.

Timing rules:

- Do not use `ffmpeg -shortest` for voiceover output.
- If narration is longer, clone-pad/time-align the video.
- If video is longer, audio-pad the final tail.
- Captions must align to final duration.
- Videos are allowed to exceed one minute when the concept needs it.

Command:

```bash
python tools/stem_course.py render --run runs/<course> --quality l --voice-engine none
```

### `course-output-validator`

Purpose: prevent low-quality artifacts from being treated as finished.

How it works:

- Reads the run directory and reports `FAIL`, `WARN`, and info items.
- Has strict mode for final handoff and `--draft` mode while building.
- Can emit JSON for automation with `--json`.
- Works with `audit_video_frames.py` contact sheets and metrics.

Major checks:

- Notes exist and are deep enough.
- `notes.pdf` provenance is recorded.
- LaTeX avoids prose matrices, Python-list matrices, bad exponents, and prose `sqrt(...)`.
- Every short has a complete, non-placeholder, non-repeated worked example.
- Scenes/scripts/captions exist and are syntactically usable.
- Manim scenes are vertical and use expected layout helpers.
- Rendered MP4s exist, are vertical, nonblank, and not static.
- Voiceover is present when a real voice engine was requested.
- Silent videos are accepted only when `--voice-engine none` was explicit.
- Instagram queues warn when no public `video_url` is available.

Commands:

```bash
python tools/validate_course_run.py runs/<course>
python tools/validate_course_run.py runs/<course> --draft
python tools/validate_course_run.py runs/<course> --allow-fallback-pdf
python tools/validate_course_run.py runs/<course> --json
```

### `course-instagram-series`

Purpose: turn final videos into an Instagram Reels series queue and optionally publish it.

How it works:

- Reads final videos and plan metadata.
- Writes `instagram_publish_queue.json`.
- Adds playlist labels, ordering, captions, worked examples, and question prompts.
- Supports a dry-run.
- Uses the Meta/Instagram media container flow for live publishing.

Important constraints:

- Instagram API publishing requires public HTTPS video URLs.
- Local MP4 files cannot be uploaded directly by this API flow.
- The account must be eligible for publishing through the Meta Graph API.
- Required env vars are `IG_USER_ID` and `META_ACCESS_TOKEN` or `IG_ACCESS_TOKEN`.
- `META_GRAPH_VERSION` defaults to the tool value but can be overridden.

Commands:

```bash
python tools/stem_course.py queue --run runs/<course> --playlist "Course Name"
python tools/stem_course.py queue --run runs/<course> --playlist "Course Name" --public-base-url "https://cdn.example.com/course/"
python tools/stem_course.py publish --run runs/<course> --dry-run
python tools/stem_course.py publish --run runs/<course>
```

## Quality Gates

Before publishing or sharing a finished run, use this loop:

```bash
python tools/stem_course.py render --run runs/<course> --quality l --voice-engine none
python tools/audit_video_frames.py runs/<course>
python tools/validate_course_run.py runs/<course>
```

Inspect the contact sheets in `runs/<course>/visual_audit/`. Fix and rerender if you see:

- text overlap
- formulas running off screen
- matrix rows collapsed into one line
- arrows/axes/curves crossing labels
- cramped labels
- static text-only scenes
- repeated-looking animations
- blank or nearly blank frames

The validator is intentionally strict. When it fails, fix the generator or source artifact rather than editing only one output file. The goal is to make the skill better for every future topic.

## Example And Question Policy

The generator and validator now enforce a stronger worked-example standard:

- Every short needs a `worked_example.setup`, `worked_example.calculation`, and `worked_example.takeaway`.
- Examples must include concrete values or symbolic objects.
- Theoretical topics still need examples: small groups, sets, graphs, proof objects, counterexamples, payoff tables, equations, or tiny state spaces.
- Source-derived concepts use deterministic variation so related terms do not all receive the same toy example.
- Repeated setup/calculation pairs fail validation.
- Placeholder language such as "choose a small example" or "work through the definition" fails validation.
- `question_prompt` remains in the plan and publishing queue, but videos should focus on the concept and worked example rather than an active-recall section.

## Notes Formatting Policy

The notes are supposed to resemble a serious formulas-and-definitions reference document:

- black-and-white article-style layout
- title page
- numbered sections and subsections
- key concepts and explanation tables
- notation and formula tables
- definitions, propositions, examples, warnings, and questions
- worked examples with real numbers or symbolic objects
- conceptual questions and application questions
- figures/graphs where they help the topic
- matrices, vectors, powers, square roots, and equations in proper LaTeX

If no TeX engine is installed, the fallback PDF is useful for previewing content but should not be confused with a true LaTeX build.

## Contributing

Contributions should improve the reusable workflow, not just patch one generated run.

Good contribution types:

- Add a new course domain library.
- Add richer examples to an existing domain.
- Add a new Manim visual family.
- Improve layout collision handling.
- Add validators for a recurring failure mode.
- Improve notes formatting or LaTeX compilation.
- Add better source extraction for a common course site.
- Add a publishing adapter for another platform.
- Add tests or sample runs for a new domain.

When adding concepts:

1. Add concepts in prerequisite order.
2. Give each concept a concrete worked example.
3. Include a misconception or common trap.
4. Include a meaningful application question and answer.
5. Choose a `visual_type` that maps to a real renderer.
6. Run the short-plan validator over the whole library.

When adding a visual family:

1. Start with `course-animation-planner`.
2. Define the visual claim, objects, motion beats, invariant, and reveal.
3. Add Manim generation support.
4. Use collision-aware layout helpers for text and diagrams.
5. Add validator checks if the new family has predictable failure modes.
6. Render a small sample and inspect contact sheets.

When changing validators:

1. Prefer catching reusable quality failures over checking one exact output.
2. Keep `--draft` useful during iteration.
3. Make final strict mode block true publish-readiness failures.
4. Provide actionable `fix` text where possible.

Suggested development checks:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/course-shorts-pycache python3 -m py_compile tools/stem_course.py tools/validate_course_run.py tools/audit_video_frames.py
git diff --check
python tools/stem_course.py all --sample linear_algebra --out /private/tmp/course-shorts-demo --max-shorts 3 --voice-engine none --quality l --pdf-engine fallback
python tools/audit_video_frames.py /private/tmp/course-shorts-demo --interval 3
python tools/validate_course_run.py /private/tmp/course-shorts-demo --allow-fallback-pdf
```

For source-derived concept stress testing, create a small `source_pack.json`, run `plan --max-shorts` high enough to include source-derived terms, then run:

```bash
python tools/validate_course_run.py /path/to/run --draft --allow-fallback-pdf
```

## Instagram Publishing Setup

Set credentials before live publishing:

```bash
export IG_USER_ID="..."
export META_ACCESS_TOKEN="..."
export META_GRAPH_VERSION="v21.0"
```

Then create a queue with public URLs:

```bash
python tools/stem_course.py queue \
  --run runs/<course> \
  --playlist "Course Name" \
  --public-base-url "https://cdn.example.com/course/"
```

Dry-run first:

```bash
python tools/stem_course.py publish --run runs/<course> --dry-run
```

Then publish:

```bash
python tools/stem_course.py publish --run runs/<course>
```

## Troubleshooting

### `notes.pdf` was generated by fallback

Install a real TeX engine and rerun:

```bash
python tools/stem_course.py notes --run runs/<course> --compile --pdf-engine latex
```

### Voiceover files are empty

Use a different voice engine or fix credentials. The renderer intentionally rejects empty files for real voice engines.

### Instagram queue has no `video_url`

Host the final MP4s somewhere public, then rerun `queue` with `--public-base-url`.

### Videos have overlap or unreadable formulas

Patch the Manim generator or visual family, regenerate scenes, rerender, run `audit_video_frames.py`, and validate again.

### Videos feel too short or rushed

Do not restore the old one-minute cap. Adjust script and caption pacing so each beat remains visible long enough to read and understand.

### Source pack is too small

Increase `--max-pages` or `--max-pdfs`, add missing PDFs manually, or run extraction on a better course root page.

## Current Known Limits

- The built-in domain libraries are strongest for linear algebra, group theory, and economics, with smaller coverage for algorithms and physics.
- Source extraction depends on readable HTML/PDF text. Scanned PDFs may need OCR first.
- The fallback PDF path is a preview path, not a full LaTeX typesetting replacement.
- The Instagram API path requires a professional account, permissions, access token, and public video URLs.
- High-quality 3Blue1Brown-like videos still require iterative validation, especially for new domains and visual families.

## Maintainer Notes

The project should keep improving through validators. If a generated artifact looks bad, prefer adding a reusable rule or generator fix so future courses improve too.

The most important invariants are:

- comprehensive notes
- beginner-safe ordering
- fresh concrete examples
- visualized worked examples
- readable vertical layout
- no repeated generic Manim template
- correct voiceover/silence accounting
- strict validation before upload

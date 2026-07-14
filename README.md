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
  animation_plan_index.json
  animation_plans/
    short_01.json
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
  render_runtime_trace.json
  visual_audit/
  visual_frame_audit.json
  visual_review.json
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
- `tools/stem_course.py` is the main CLI. It extracts, plans, writes fingerprinted animation storyboards, writes notes, generates Manim, renders videos, initializes temporal review, builds queues, and publishes.
- `tools/validate_course_run.py` is the quality gate for notes, examples, scenes, videos, renderer execution traces, audio intent, and publishing readiness.
- `tools/audit_video_frames.py` samples rendered videos into contact sheets and frame-density metrics.
- `requirements.txt` contains Python package requirements.
- `REQUIREMENTS.md` explains system dependencies such as LaTeX, FFmpeg, Manim, and voice engines.

## Codex Plugin

This GitHub repository is a reusable Codex plugin source. Its manifest at
`.codex-plugin/plugin.json` points Codex at `./skills/`, which exposes these
eight skills:

```text
course-source-pack          course-short-plan
course-latex-notes          course-animation-planner
course-manim-3b1b           course-render-voiceover
course-output-validator     course-instagram-series
```

The manifest deliberately declares no MCP servers, apps, hooks, or asset paths.
This repository also has no `.agents/plugins/marketplace.json`, so it is not a
published Codex marketplace and should not be added directly as one. The
supported plugin installation below wraps the GitHub clone in a private local
marketplace.

### Install in Codex

Codex CLI installs plugins from configured marketplace snapshots. Choose a new
local marketplace directory, clone the GitHub repository into its `plugins/`
directory, and create the local marketplace descriptor:

```bash
export COURSE_SHORTS_MARKETPLACE="$HOME/course-shorts-local-marketplace"
mkdir -p "$COURSE_SHORTS_MARKETPLACE/.agents/plugins" "$COURSE_SHORTS_MARKETPLACE/plugins"
git clone https://github.com/arav31/CourseToShortsSkills.git \
  "$COURSE_SHORTS_MARKETPLACE/plugins/course-shorts-skills-quality"
export COURSE_SHORTS_ROOT="$COURSE_SHORTS_MARKETPLACE/plugins/course-shorts-skills-quality"
```

Create `$COURSE_SHORTS_MARKETPLACE/.agents/plugins/marketplace.json` with this
private local entry. This example assumes the marketplace directory is new; do
not overwrite an existing marketplace file or discard its existing entries.

```json
{
  "name": "course-shorts-local",
  "interface": { "displayName": "Course Shorts Local" },
  "plugins": [
    {
      "name": "course-shorts-skills-quality",
      "source": { "source": "local", "path": "./plugins/course-shorts-skills-quality" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

Then configure and install it:

```bash
codex plugin marketplace add "$COURSE_SHORTS_MARKETPLACE"
codex plugin add course-shorts-skills-quality@course-shorts-local
```

Use `codex plugin list --marketplace course-shorts-local --available --json` to verify
discovery. Start a new Codex thread after installation so its skill inventory
is refreshed.

If the repository is already cloned elsewhere, keep that clone and symlink it
to `$COURSE_SHORTS_MARKETPLACE/plugins/course-shorts-skills-quality` instead of
cloning a second copy. The marketplace entry remains the same.

### Use the Skills

Start a new Codex thread after installation and describe the course artifact or
stage you need. Codex discovers all eight skills from the plugin and selects the
relevant one. You can also name a skill explicitly, for example:

```text
Use course-source-pack to extract this course URL into runs/linear-algebra.
Use course-latex-notes on runs/linear-algebra and compile the PDF with LaTeX.
Use course-output-validator to audit runs/linear-algebra before publishing.
```

The skills share artifacts through one `runs/<course>/` directory, so a single
thread can continue from extraction through planning, notes, storyboarding,
rendering, validation, and Instagram queue preparation.

### Wrapper Commands

The wrappers resolve the plugin root from their own path, so they work from a
repository clone, an installed plugin, or any working directory. Point
`COURSE_SHORTS_PYTHON` at the interpreter with this project's dependencies;
when it is unset, wrappers use `python3`.

```bash
export COURSE_SHORTS_ROOT="/absolute/path/to/course-shorts-skills-quality"
export COURSE_SHORTS_PYTHON="$COURSE_SHORTS_ROOT/.venv/bin/python"

"$COURSE_SHORTS_ROOT/scripts/course-shorts" --help
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" --help
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" --help
"$COURSE_SHORTS_ROOT/scripts/course-shorts-piper" --help
```

Use `course-shorts` for the main subcommands, `course-shorts-audit` for frame
audits, `course-shorts-validate` for run validation, and `course-shorts-piper`
for the optional Piper utility. The following examples use these wrappers so
they never assume the current directory is the repository root.

### Update an Installed Local Source

Pull or otherwise update the clone, use the official plugin-creator cachebuster,
validate the source, and reinstall it from the same local marketplace. Do not
hand-edit the marketplace entry during updates. The default Codex installation
places `plugin-creator` under `${CODEX_HOME:-$HOME/.codex}`:

```bash
git -C "$COURSE_SHORTS_ROOT" pull --ff-only
export PLUGIN_CREATOR_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator"
"$COURSE_SHORTS_PYTHON" "$PLUGIN_CREATOR_ROOT/scripts/update_plugin_cachebuster.py" "$COURSE_SHORTS_ROOT"
"$COURSE_SHORTS_PYTHON" "$PLUGIN_CREATOR_ROOT/scripts/validate_plugin.py" "$COURSE_SHORTS_ROOT"
codex plugin add course-shorts-skills-quality@course-shorts-local
```

Start another new Codex thread after reinstalling so Codex loads the updated
skill instructions. The cachebuster intentionally changes the local manifest
version; it does not publish a marketplace release.

## Standalone Clone

Clone the public repository and define the repository root before using any of
the commands below:

```bash
git clone https://github.com/arav31/CourseToShortsSkills.git
export COURSE_SHORTS_ROOT="$PWD/CourseToShortsSkills"
cd "$COURSE_SHORTS_ROOT"
```

Install the system dependencies from [REQUIREMENTS.md](REQUIREMENTS.md). The important ones are:

- Python 3.10+
- FFmpeg
- Manim dependencies
- A TeX engine for true LaTeX PDF compilation: `tectonic`, BasicTeX, MacTeX, `latexmk`, or `pdflatex`
- Optional voice engines: offline Piper, OpenAI TTS, `edge-tts`, or macOS `say`

Then install Python dependencies:

```bash
python3 -m venv "$COURSE_SHORTS_ROOT/.venv"
"$COURSE_SHORTS_ROOT/.venv/bin/pip" install -r "$COURSE_SHORTS_ROOT/requirements.txt"
export COURSE_SHORTS_PYTHON="$COURSE_SHORTS_ROOT/.venv/bin/python"
```

For standalone use, keep the clone and set `COURSE_SHORTS_ROOT` and
`COURSE_SHORTS_PYTHON` as above. Run directories may live anywhere; pass an
absolute `--out` or `--run` path when invoking the wrappers outside the clone.

## Quick Start

Run the whole pipeline from a course URL:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" all \
  "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/" \
  --out runs/linear-algebra \
  --max-shorts 0 \
  --voice-engine none \
  --pdf-engine latex
```

`--max-shorts 0` is the default and plans the full authoritative outline. Any nonzero limit is an intentionally partial plan and must include `--allow-partial-plan`.

In production mode without `--no-render`, `all` runs source extraction, planning, storyboarding, LaTeX notes, Manim generation, rendering, and the dense frame audit before initializing `visual_review.json`. Production rendering also writes `render_runtime_trace.json`, hash-bound to the current plans and final MP4s, with renderer-clock evidence for every semantic transition. The visual review starts in `pending` state by design; a human or agent must actually watch and document the planned evidence windows before strict validation can pass. It deliberately does not create a publishing queue. `--voice-engine none` is the default, intentional silent mode.

Run the offline demo as a non-publishable local preview:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" all \
  --sample linear_algebra \
  --out runs/sample-linear-algebra \
  --max-shorts 3 \
  --allow-partial-plan \
  --quality preview \
  --voice-engine none \
  --pdf-engine fallback
```

Inspect the preview in draft mode:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/sample-linear-algebra --allow-missing-ocr
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/sample-linear-algebra --draft --allow-fallback-pdf
```

The demo's fallback PDF is preview-only and can never pass publish validation. For publishable notes, install a TeX engine, use `--pdf-engine latex`, and validate without `--allow-fallback-pdf`.

For an offline Tectonic installation, set `TECTONIC_BUNDLE` to an absolute local `.zip`, `.ttb`, or legacy bundle path. Notes compilation and Manim's semantic MathTex adapter both inherit it and stay cached-only.

## Pipeline Commands

The `all` command runs every generation and pre-review audit stage:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" all COURSE_URL --out runs/<course> --max-shorts 0 --pdf-engine latex
```

The manual stage-by-stage pipeline is:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" extract COURSE_URL --out runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" plan --run runs/<course> --max-shorts 0
"$COURSE_SHORTS_ROOT/scripts/course-shorts" storyboard --run runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" notes --run runs/<course> --compile --pdf-engine latex
"$COURSE_SHORTS_ROOT/scripts/course-shorts" manim --run runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --voice-engine none
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" visual-review --run runs/<course>
# Watch every evidence window and complete visual_review.json.
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" queue --run runs/<course> --playlist "Course Name"
"$COURSE_SHORTS_ROOT/scripts/course-shorts" publish --run runs/<course> --dry-run
```

For a deliberately incomplete exploratory plan, make the opt-in explicit:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" plan --run runs/<course> --max-shorts 12 --allow-partial-plan
```

Useful `all` flags:

```text
--sample linear_algebra
--max-pages 160
--max-pdfs 100
--max-shorts 0                         # default: full authoritative outline
--allow-partial-plan                   # required with a nonzero limit
--quality production|preview
--voice-engine none|piper|say|edge-tts|openai
--piper-model-dir PATH
--piper-model-id ID
--piper-model-manifest PATH
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
| `course-animation-planner` | Every planned short needs a real visual story before Manim code. | `short_plan.json` | `animation_plan_index.json`, `animation_plans/short_XX.json` |
| `course-manim-3b1b` | The user wants course-specific Manim scenes. | `short_plan.json`, valid animation plans | `scenes/`, `scripts/`, `captions/` |
| `course-render-voiceover` | Scenes need final vertical MP4s and optional narration. | `scenes/`, `scripts/`, `captions/` | `videos/`, `audio/`, `render_report.json` |
| `course-output-validator` | A run needs quality checks before handoff/upload. | Full run, `render_runtime_trace.json`, automated audit, completed `visual_review.json`. | Human or JSON validation report. |
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
"$COURSE_SHORTS_ROOT/scripts/course-shorts" extract "COURSE_URL" --out runs/<course> --max-pages 160 --max-pdfs 100
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
"$COURSE_SHORTS_ROOT/scripts/course-shorts" plan --run runs/<course> --max-shorts 0
```

### `course-latex-notes`

Purpose: create comprehensive course notes that can serve as a real study document.

How it works:

- Reads `source_pack.json` and `short_plan.json`.
- Writes both `notes.tex` and `notes.md`.
- Follows the source course's actual lecture/section order and admits only source-evidenced topics plus necessary prerequisites.
- Uses numbered definitions and theorems, derivations or proofs where appropriate, fully worked examples, relevant algorithms, and sparse topic-specific figures/graphs.
- Includes only selective, mathematically distinct exercises whose numbered solutions match exactly; it does not pad pages with per-topic question templates, duplicate formula indexes, source inventories, course maps, or checklist prose.
- Uses proper semantic LaTeX for matrices, vectors, cases, aligned equations, symbols, and field-specific notation.
- Places a field-pioneer quotation on the title page and does not list sources inside the notes body.

PDF behavior:

- `--pdf-engine latex` is the publishable path. It requires real LaTeX compilation and fails closed if unavailable or invalid.
- `--pdf-engine fallback` creates a non-publishable local preview only.
- `--pdf-engine auto` may select that preview fallback, so it is also unsuitable as proof of publishable compilation.
- `notes_compile_report.json` records which engine produced the PDF.

Quality rules:

- Every included topic must be grounded in extracted course evidence or be a stated prerequisite.
- Hard source topics still belong even if they are not video hooks.
- Definitions, symbols, theorem hypotheses, derivations, examples, figures, exercises, and solutions must agree with one another.
- Matrices and vectors should be formatted as LaTeX math, not Python/prose lists.
- Abstract concepts need concrete examples and appropriate diagrams.
- Length follows course coverage; 50+ pages is acceptable when the source warrants it, but page count is never padding evidence.

Command:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" notes --run runs/<course> --compile --pdf-engine latex
```

### `course-animation-planner`

Purpose: design the visual explanation before writing Manim code.

How it works:

- Reads every short in `short_plan.json` and writes `animation_plans/short_XX.json` plus `animation_plan_index.json`.
- Records the visual claim, exact example, stable object IDs/roles/colors, continuity spine, invariant, reveal, and 5-8 semantic beats.
- Requires at least four domain-state transformations, at least 70% object-active beats, continuity across adjacent beats, no full reset, and timestamped QA evidence.
- Fingerprints both source fields and artifacts so later short edits make the plan stale.
- Derives CS and physics support from their shared renderer-kind registries.
- Derives route-specific objects, actions, invariant, reveal, and renderer-state payload from `visual_kind` plus the exact worked example; BFS, heaps, hashes, waves, forces, markets, and elasticity do not share a generic action script.

Use this skill for every run. `manim` and `render` refuse missing, stale, or invalid plans. `numeric_rule` is an unsupported diagnostic fallback. `state_machine` is publishable only for a concrete automaton with named states and explicit transitions.

Quality rules:

- The visual motion should carry the intuition.
- Use sparse labels rather than dense paragraphs.
- Use color as semantic bookkeeping.
- The worked example must be visible.

Command:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" storyboard --run runs/<course>
```

### `course-manim-3b1b`

Purpose: generate concept-specific vertical Manim scenes.

How it works:

- Reads `short_plan.json` and requires its fingerprinted animation plans.
- Generates one Python scene per short under `scenes/`.
- Generates matching script markdown under `scripts/`.
- Generates SRT captions under `captions/`.
- Routes concepts to supported semantic visual families such as linear algebra, calculus, physics, CS, group theory, economics, and probability.
- Embeds the animation-plan hash plus planned beats, objects, and continuity metadata in each generated scene.
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
"$COURSE_SHORTS_ROOT/scripts/course-shorts" manim --run runs/<course>
```

### `course-render-voiceover`

Purpose: render final phone-ready MP4s, with optional narration.

How it works:

- Renders Manim scenes into raw MP4s.
- Optionally generates voiceover.
- Muxes final video/audio while preserving duration alignment.
- Records render and timing details in `render_report.json`.
- `--quality preview` renders native 360x640/15 fps iteration files named `*_preview.mp4`; previews are never labeled final, queued, or accepted by strict validation.
- `--quality production` produces canonical final MP4s in `videos/` and enables temporal review/queue stages.

Voice engines:

- `none`: intentional silent mode. Missing audio is valid when this is selected.
- `piper`: optional offline Piper synthesis using the exact local model/config pin in `config/piper_models.json`; rendering never downloads model files.
- `openai`: requires `OPENAI_API_KEY`; optional `OPENAI_TTS_MODEL` and `OPENAI_TTS_VOICE`.
- `edge-tts`: requires the `edge-tts` package and network access.
- `say`: macOS fallback; validates that non-empty audio was actually produced.

The current Piper manifest pins the open-source `en_US-ljspeech-medium` model. It is optional; its name is `medium`, so this documentation does not claim a small-model pin. Provision assets outside rendering, then validate their exact sizes and SHA-256 hashes:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-piper" provision-contract --model-dir /absolute/path/to/piper-models --model-id en_US-ljspeech-medium
"$COURSE_SHORTS_ROOT/scripts/course-shorts-piper" validate-model --model-dir /absolute/path/to/piper-models --model-id en_US-ljspeech-medium
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --quality production --voice-engine piper --piper-model-dir /absolute/path/to/piper-models --piper-model-id en_US-ljspeech-medium
```

`COURSE_SHORTS_PIPER_MODEL_DIR`, `COURSE_SHORTS_PIPER_MODEL_ID`, and `COURSE_SHORTS_PIPER_MODEL_MANIFEST` supply the equivalent render settings. The Piper helper itself uses `--manifest`, not `--piper-model-manifest`.

Timing rules:

- Do not use `ffmpeg -shortest` for voiceover output.
- If narration is longer, clone-pad/time-align the video.
- If video is longer, audio-pad the final tail.
- Captions must align to final duration.
- Videos are allowed to exceed one minute when the concept needs it.

Command:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --quality production --voice-engine none
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
- Every short has a fresh, valid semantic animation plan and the generated scene embeds its hash.
- Scenes/scripts/captions exist and are syntactically usable.
- Manim scenes are vertical and use expected layout helpers.
- Rendered MP4s exist, are vertical, nonblank, and not static.
- Voiceover is present when a real voice engine was requested.
- Silent videos are accepted only when `--voice-engine none` was explicit.
- Automated frame metrics are triage, not approval.
- `visual_review.json` is complete for every final MP4, tied to current plan/video hashes, and records actual temporal observations, persistent objects, four state changes, legibility/overlap results, reviewer identity, and a pass verdict.
- Instagram queues warn when no public `video_url` is available.

Commands:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --draft
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --allow-fallback-pdf
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --json
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
"$COURSE_SHORTS_ROOT/scripts/course-shorts" queue --run runs/<course> --playlist "Course Name"
"$COURSE_SHORTS_ROOT/scripts/course-shorts" queue --run runs/<course> --playlist "Course Name" --public-base-url "https://cdn.example.com/course/"
"$COURSE_SHORTS_ROOT/scripts/course-shorts" publish --run runs/<course> --dry-run
"$COURSE_SHORTS_ROOT/scripts/course-shorts" publish --run runs/<course>
```

## Quality Gates

Before publishing or sharing a finished run, use this loop:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" storyboard --run runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" manim --run runs/<course>
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --quality production --voice-engine none
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/<course> --interval 0.25
"$COURSE_SHORTS_ROOT/scripts/course-shorts" visual-review --run runs/<course>
# Actually watch the planned windows, sweep the full MP4 every 0.25 s or less,
# and complete visual_review.json.
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course>
```

Inspect the contact sheets in `runs/<course>/visual_audit/` as triage, then scrub each video around its storyboard evidence timestamps. Fix and rerender if you see:

- text overlap
- formulas running off screen
- matrix rows collapsed into one line
- arrows/axes/curves crossing labels
- text-bearing shapes colliding while they move
- persistent labels losing glyphs during masks, scans, or transitions
- cramped labels
- a proof object that is too small to read at 270 x 480
- static text-only scenes
- decorative motion while the explanatory object remains static
- repeated-looking animations
- blank or nearly blank frames

The validator is intentionally strict. When it fails, fix the generator or source artifact rather than editing only one output file. The goal is to make the skill better for every future topic.

Running `visual-review` only initializes a pending manifest. It does not claim that anyone watched the MP4. Strict validation requires completed, specific observations, a full-video sweep at intervals no larger than 0.25 seconds, explicit checks for labeled-object collisions and persistent-text integrity, and rejects the review after any plan or video-byte change.

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
- title page with a field-pioneer quotation
- source-course order with numbered sections and subsections
- compact notation/formula index
- numbered definitions, theorems, derivations or proofs, and worked examples
- topic-specific figures/graphs where they carry mathematical content
- cumulative exercises with exactly paired numbered solutions
- matrices, vectors, powers, square roots, and equations in proper LaTeX
- no source inventory, course-map/checklist padding, generic supplemental topics, or template question blocks

If no TeX engine is installed, the fallback PDF is a non-publishable preview. A final run requires `--pdf-engine latex` and a successful real compile report.

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
3. Add Manim generation support and register CS/physics kinds in their shared `CS_VISUAL_KINDS` or `PHYSICS_VISUAL_KINDS` set.
4. Use collision-aware layout helpers for text and diagrams.
5. Add validator checks if the new family has predictable failure modes.
6. Render a small sample, inspect contact sheets as triage, and complete a timestamped temporal review.

When changing validators:

1. Prefer catching reusable quality failures over checking one exact output.
2. Keep `--draft` useful during iteration.
3. Make final strict mode block true publish-readiness failures.
4. Provide actionable `fix` text where possible.

Suggested development checks:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/course-shorts-pycache "$COURSE_SHORTS_PYTHON" -m py_compile "$COURSE_SHORTS_ROOT/tools/stem_course.py" "$COURSE_SHORTS_ROOT/tools/validate_course_run.py" "$COURSE_SHORTS_ROOT/tools/audit_video_frames.py"
git diff --check
"$COURSE_SHORTS_ROOT/scripts/course-shorts" all --sample linear_algebra --out /private/tmp/course-shorts-demo --max-shorts 3 --allow-partial-plan --voice-engine none --quality preview --pdf-engine fallback
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" /private/tmp/course-shorts-demo --interval 3 --allow-missing-ocr
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" /private/tmp/course-shorts-demo --draft --allow-fallback-pdf
```

For a strict check, watch the evidence windows, complete `/private/tmp/course-shorts-demo/visual_review.json`, use a real LaTeX PDF, then rerun the validator without draft or fallback allowances.

For source-derived concept stress testing, create a small `source_pack.json`, run `plan --max-shorts` high enough to include source-derived terms, then run:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" /path/to/run --draft --allow-fallback-pdf
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
"$COURSE_SHORTS_ROOT/scripts/course-shorts" queue \
  --run runs/<course> \
  --playlist "Course Name" \
  --public-base-url "https://cdn.example.com/course/"
```

Dry-run first:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" publish --run runs/<course> --dry-run
```

Then publish:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" publish --run runs/<course>
```

## Troubleshooting

### `notes.pdf` was generated by fallback

Install a real TeX engine and rerun:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" notes --run runs/<course> --compile --pdf-engine latex
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

## Validation Matrix

The plugin has been exercised end to end on four distinct MIT-style course runs. All production canaries used `--voice-engine none`, renderer-clock transition traces, dense temporal sampling, OCR layout checks, and direct contact-sheet review.

| Domain | Course run | Planned shorts | Compiled notes | Production canary |
| --- | --- | ---: | ---: | --- |
| Mathematics | Modern Algebra / MIT 18.703 | 24 | 57 pages | Presentations and groups of small order |
| Computer science | Algorithms / MIT 6.006 | 18 | 60 pages | Breadth-first search |
| Physics | Classical Mechanics / MIT 8.01 | 41 | 100 pages | Uniform circular motion |
| Economics | Microeconomics / MIT 14.01 | 26 | 72 pages | Supply and demand |

The canary audits reject static or nearly static runs, terminal holds, missing semantic motion, text overlap, clipped or run-together text, sparse portrait layouts, and temporal visual loss. The generated `notes.tex` files compile with a real LaTeX engine; fallback PDFs remain preview-only.

## Current Known Limits

- The built-in domain libraries cover mathematics, algorithms, mechanics, and economics, but a genuinely new visual family still needs its first production validation loop.
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

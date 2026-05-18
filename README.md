# Course Shorts Skills

A shareable Codex skill pack for turning course links and course files into:

- extracted course material packs
- comprehensive LaTeX notes with definitions, formulas, examples, questions, and a compiled `notes.pdf`
- beginner-safe short-video lesson plans
- animation-planned Manim scenes in a 3Blue1Brown-inspired style
- rendered vertical silent shorts by default, with subtitles metadata and optional real voiceover support
- Instagram Reels series queues and optional API publishing

## Requirements

Install the system and Python requirements in [REQUIREMENTS.md](REQUIREMENTS.md). The important pieces are a LaTeX engine (`tectonic`, BasicTeX, or MacTeX), FFmpeg, and the packages in `requirements.txt`.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python tools/stem_course.py all "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/" --out runs/linear-algebra --max-shorts 8
```

Videos render silently by default with `--voice-engine none`; this is a supported final-output mode when the animation carries the explanation. For real voiceover, configure one of:

- `--voice-engine openai` with `OPENAI_API_KEY`
- `--voice-engine edge-tts` with `edge-tts` installed
- `--voice-engine say` on macOS, only if `say` produces non-empty audio on your machine

`say` availability varies by Mac and sandbox, so the renderer validates audio duration and refuses empty voiceover files instead of pretending voiceover worked.

## Install Skills

Copy or symlink the folders in `skills/` into your Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Each skill can also be used in-place by telling Codex to use the skill folder from this repository.

## Pipeline

```bash
python tools/stem_course.py extract COURSE_URL --out runs/course
python tools/stem_course.py plan --run runs/course --max-shorts 12
python tools/stem_course.py notes --run runs/course --compile
python tools/stem_course.py manim --run runs/course
python tools/stem_course.py render --run runs/course --voice-engine none
python tools/audit_video_frames.py runs/course
python tools/validate_course_run.py runs/course
python tools/stem_course.py queue --run runs/course --playlist "Course Name" --public-base-url "https://cdn.example.com/course/"
python tools/stem_course.py publish --run runs/course --dry-run
```

Use `--sample linear_algebra` with `extract` or `all` for offline testing.

## Instagram Publishing

The publish command follows the Meta/Instagram container flow: create a Reel media container from a public `video_url`, poll processing status, then publish the container. Configure these environment variables before live publishing:

```bash
export IG_USER_ID="..."
export META_ACCESS_TOKEN="..."
export META_GRAPH_VERSION="v21.0"  # override if your app uses a newer supported Graph API version
```

Instagram cannot publish a private local MP4 directly through this API; host the final videos first, then create the queue with `--public-base-url`.

## Validation

Run `python tools/audit_video_frames.py runs/<course>` after rendering, inspect the generated contact sheets in `visual_audit/`, then run `python tools/validate_course_run.py runs/<course>` before treating a course run as upload-ready. The validator checks notes/PDF provenance, LaTeX formatting red flags, scene/script/caption coverage, final video existence, duration, vertical orientation, blank/static sampled frames, visual-audit review flags, and audio streams when a voice engine was selected. Silent final MP4s pass when `render_report.json` records `--voice-engine none`. Use `--draft` while iterating before final render.


## Notes PDF

`notes --compile` and `all` generate `notes.pdf`. The CLI tries `latexmk`, `pdflatex`, or `tectonic` first, including common TeX install paths such as `/Library/TeX/texbin`. If no TeX engine is installed, it uses the PyMuPDF fallback from the same generated notes data and writes `notes_compile_report.json` so you can see which engine produced the PDF. The LaTeX template is now a black-and-white article-style definitions/formulas document matching the supplied reference structure: title page, numbered sections, compact tables, full topic explanations, examples, and question banks.

## Video Length

Generated Manim explainers no longer have a one-minute cap. Scripts and captions are paced for longer concept-complete videos, and matrix/vector visuals are rendered as stacked math objects instead of cramped one-line lists.

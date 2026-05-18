# Workflow Requirements

This repository is meant to be shareable: a friend should be able to clone it, paste a course link, and generate comprehensive notes, scripts, Manim scenes, rendered shorts, and an upload queue.

## System Tools

Install a LaTeX engine, FFmpeg, and Python 3.10+.

Recommended macOS setup:

```bash
brew install tectonic ffmpeg
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Full TeX distribution option, useful if you prefer `pdflatex`/`latexmk`:

```bash
brew install --cask basictex   # requires the macOS admin password
# restart terminal, or run:
eval "$(/usr/libexec/path_helper)"
```

The CLI searches normal PATH plus `/Library/TeX/texbin`, `/opt/homebrew/bin`, and `/usr/local/bin`, so BasicTeX/MacTeX and Homebrew Tectonic both work.

## Python Packages

`requirements.txt` installs the Python-side runtime:

- `pymupdf` for PDF text extraction and fallback PDF generation
- `manim` for animation generation
- `requests` and `beautifulsoup4` for web extraction helpers
- `edge-tts` for optional local-ish voiceover

The validator uses the system `ffprobe`/`ffmpeg` commands from FFmpeg for video metadata and sampled-frame checks.

## Course Coverage Requirements

For a real course, extract broadly before generating notes:

```bash
python tools/stem_course.py extract COURSE_URL --out runs/course --max-pages 160 --max-pdfs 100
python tools/stem_course.py plan --run runs/course --max-shorts 40
python tools/stem_course.py notes --run runs/course --compile --pdf-engine latex
```

Before rendering videos, inspect `runs/course/source_pack.json`:

- It should include the syllabus, lecture pages, lecture notes, readings, assignments, exams, and PDFs when available.
- Warnings about missing PDF text mean the PDF may need OCR or manual upload.
- Do not treat the notes as complete if only the landing page was extracted.

## Notes PDF Standard

The compiled `notes.pdf` should follow the attached reference style:

- title page with date and short attribution block
- black-and-white article layout, not a colorful slide handout
- numbered sections and subsections
- compact tables for definitions, symbols, and formulas
- one section per major topic with prerequisites, definition, formula, worked example, common trap, questions, and answers
- worked examples with simple prose math converted to real LaTeX where safe, including `bmatrix` displays for matrix/vector examples and real `\sqrt{}`/exponent formatting
- a source-derived coverage checklist so non-video topics are still tracked

The notes should be a course proxy, not a summary. Every important concept needs:

- key concept and plain-English explanation
- all relevant notation and symbol meanings
- formula or governing rule
- worked numeric or symbolic example
- conceptual questions
- application questions with answer direction
- error checks and common traps

## Video Requirements

Each short should include a visual example, not just text. Matrix/vector content should render as stacked mathematical objects. There is no hard one-minute limit; the video should run long enough for the concept, worked example, and recall question to make sense.

## Voiceover Requirements

Use one of:

```bash
python tools/stem_course.py render --run runs/course --voice-engine openai
python tools/stem_course.py render --run runs/course --voice-engine edge-tts
python tools/stem_course.py render --run runs/course --voice-engine say
```

`openai` requires `OPENAI_API_KEY`. Instagram publishing requires public video hosting plus `IG_USER_ID`, `META_ACCESS_TOKEN`, and optionally `META_GRAPH_VERSION`.

## Validation Commands

```bash
python -m py_compile tools/stem_course.py
python tools/stem_course.py all --sample linear_algebra --out runs/demo --max-shorts 6 --voice-engine none --pdf-engine latex
python tools/audit_video_frames.py runs/demo
python tools/validate_course_run.py runs/demo --draft
python - <<'PY'
import fitz
pdf = 'runs/demo/notes.pdf'
doc = fitz.open(pdf)
print(doc.page_count)
print(doc[0].get_text()[:500])
doc.close()
PY
```

If `--pdf-engine latex` fails, install `tectonic`, BasicTeX, or MacTeX and rerun. `--pdf-engine fallback` is only for previewing when no TeX engine is available.

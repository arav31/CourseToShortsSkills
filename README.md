# Course → Shorts

**Paste a course link. Get complete study notes and a series of narrated, 3Blue1Brown-style explainer shorts.**

[![tests](https://github.com/arav31/CourseToShortsSkills/actions/workflows/tests.yml/badge.svg)](https://github.com/arav31/CourseToShortsSkills/actions/workflows/tests.yml)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757)
![Codex plugin](https://img.shields.io/badge/Codex-plugin-10a37f)
![Agent Skills](https://img.shields.io/badge/Agent%20Skills-5-6e56cf)

<!-- SHOWCASE -->

A set of five [Agent Skills](https://agentskills.io) for Claude Code and Codex. Point your agent at a
course (MIT OpenCourseWare or any course site, a syllabus, lecture PDFs, a folder of notes) and it:

1. **reads the whole course** into plain-text sources and writes its outline,
2. **plans a beginner-safe series of shorts**, each built around a concrete, verified worked example,
3. **writes the full course notes in LaTeX**: definitions, theorems with proofs, worked examples, TikZ figures, exercises with solutions, and compiles them to PDF,
4. **storyboards, codes, narrates and renders each short** as a vertical Manim video with synced voiceover and burned-in captions, then **looks at the frames** and fixes what it sees,
5. **packages the series for Instagram Reels** and (only when you ask) publishes it.

## Install

**Claude Code**

```text
/plugin marketplace add arav31/CourseToShortsSkills
/plugin install course-to-shorts@course-to-shorts
```

**Codex**

```bash
codex plugin marketplace add arav31/CourseToShortsSkills
codex plugin add course-to-shorts@course-to-shorts
```

**Any agent that reads skill folders** (or to hack on the skills):

```bash
git clone https://github.com/arav31/CourseToShortsSkills.git
cd CourseToShortsSkills && ./install.sh          # links skills into ~/.claude/skills and ~/.codex/skills
```

Then let the agent set up the Python side (it runs `doctor.py`, which creates
`~/.course-shorts/venv` with Manim, PyMuPDF and edge-tts). System tools it checks for:
**FFmpeg** (with libass), a **TeX engine** ([tectonic](https://tectonic-typesetting.github.io) is the
easiest: `brew install tectonic`), and **cairo/pango** for Manim (`brew install cairo pango pkg-config`).

## Use

Just ask:

```text
Turn https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/ into study notes and five explainer shorts.
Make a narrated short showing why eigenvectors keep their direction.
Write complete notes for the course in runs/mit-6006, then render the first three shorts.
Where does runs/mit-18-06sc stand? Is it ready to post?
```

Everything for a course lands in `runs/<course>/`: `sources/`, `outline.json`, `short_plan.json`,
`notes/notes.pdf`, `shorts/NN-<slug>/NN-<slug>.mp4`, and `reels_queue.json`.

## The skills

| skill | what the agent does | what the scripts do |
|---|---|---|
| [`course-to-shorts`](skills/course-to-shorts/SKILL.md) | runs the whole pipeline, keeps you in the loop, fans out work to subagents | `doctor.py` (environment), `run_status.py` (status + publish gate) |
| [`course-plan`](skills/course-plan/SKILL.md) | reads the course, writes the outline and the shorts plan with verified examples | `ingest.py` (crawl + PDF/HTML/transcript extraction, boilerplate removal), `check_plan.py` |
| [`course-notes`](skills/course-notes/SKILL.md) | writes every unit as real LaTeX notes and reviews the rendered pages | `build_notes.py` (compile, lint, page previews, parallel unit builds) |
| [`course-video`](skills/course-video/SKILL.md) | storyboards, writes the Manim scene, reviews contact sheets, iterates, approves | `shortkit.py` (9:16 toolkit), `voice.py`, `render.py`, `audit.py` |
| [`course-reels`](skills/course-reels/SKILL.md) | writes captions, builds the posting queue, publishes on request | `reels.py` (queue + Instagram Graph API) |

## How it works

```
 course URL / PDFs / folder
          │
   course-plan ── ingest.py ──▶ sources/*.txt ──▶ outline.json ──▶ short_plan.json ──▶ check_plan.py
          │
          ├────────────── course-notes ──▶ notes/units/uNN.tex ──▶ build_notes.py ──▶ notes.pdf ──▶ look at pages
          │
          └── course-video (per short) ──▶ storyboard.md ──▶ scene.py (shortkit)
                                               │
                     voice.py: narration per beat (edge-tts / Piper / say / OpenAI)
                     render.py: Manim ▶ beat-synced audio mix ▶ captions ▶ H.264 ▶ automatic checks
                     audit.py: contact sheets + frames ──▶ agent looks, fixes, re-renders ──▶ approve
          │
   course-to-shorts: run_status.py --gate ──▶ course-reels: reels.py queue / publish
```

The split is deliberate. **The agent does the teaching**: choosing the ideas, finding a worked
example that exercises the actual mechanism, writing the proofs, designing the animation, and
judging the result by looking at it. **Scripts do everything mechanical and checkable**:
crawling, LaTeX compilation, rendering, audio sync, caption timing, frame sampling, and
hash-bound approvals, so nothing is called done unless someone saw that exact file.

### What `shortkit` gives every scene

- **9:16 zones** (`TITLE_ZONE`, `STAGE`, `CAPTION_ZONE`) that keep content clear of the Reels UI and the captions.
- **Real LaTeX in video** via tectonic → PDF → SVG, so no full TeX install is needed; colour macros (`\cB{}`, `\cG{}`, …) for semantic colouring.
- **Narration-timed beats**: `with self.beat("id"):` lasts as long as that line's voiceover, so picture and voice stay in sync and captions use real word timings.
- **A layout checker** that runs on the live scene after every beat: overlapping text, text outside the safe area or in the caption band, unreadably small text, and text that hides or is crossed by arrows and curves.

### Quality gates

| gate | checks |
|---|---|
| `check_plan.py` | required fields, concrete and non-placeholder examples, no reused examples, prerequisites point backwards, every unit covered or skipped with a reason |
| `build_notes.py` | real TeX compile; no placeholders, code-style maths, unsolved exercises, units without worked examples, boilerplate repetition, undefined refs, missing glyphs, near-empty pages |
| `render.py` | layout errors from the scene, narration gaps, static stretches, blank frames, resolution/codec, missing audio |
| `audit.py approve` | a human or agent looked at the contact sheets; the approval is bound to the MP4's SHA-256 |
| `run_status.py --gate` | everything above is present **and current**: stale plans, notes, renders or approvals count as missing |

## Why v2 replaced the generator

Version 1 ([`v1-deterministic-engine`](https://github.com/arav31/CourseToShortsSkills/tree/v1-deterministic-engine))
tried to produce every plan, note and animation from hand-written Python: ~80,000 lines,
including a 48,000-line generator with per-domain renderers, plus 90 test files. Each new
course exposed another failure mode, which [its own audit](docs/history/v1-quality-audit.md)
logs in detail (generic openers, decorative motion, templated notes, formulas copied
across topics). On its own quick-start sample, the notes contract failed and both preview
videos crashed.

Current models can do the creative part directly and check their own work by looking at
rendered frames and pages. So v2 keeps the hard-won quality rules from that audit as the
skills' rubric ([video](skills/course-video/references/quality-bar.md),
[notes](skills/course-notes/references/notes-style.md)) and keeps the code small (about 3,400
lines across eleven scripts) and focused on what code is good at: extraction, compilation, rendering, sync,
measurement and gating.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q          # unit tests + an end-to-end render when manim/ffmpeg/TeX are present
```

CI runs the unit tests and a full render job (Manim + TeX Live + FFmpeg) on every push.
Contributions that make the skills teach better are welcome: sharper rubric items,
toolkit helpers for common visuals, better extraction for course sites, more voice engines,
and publishing adapters for other platforms.

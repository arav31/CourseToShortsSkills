---
name: course-render-voiceover
description: Use when rendering generated Manim scenes into vertical shorts, adding voiceover, validating duration/audio, and producing final MP4 files.
---

# Course Render Voiceover

## Purpose

Render scenes into phone-ready MP4 shorts and attach real voiceover when credentials or a working local TTS engine are available. The renderer must validate that audio exists and is not a zero-duration placeholder.

## Workflow

1. Install dependencies in the repository environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Render with the desired voice engine:

```bash
python tools/stem_course.py render --run runs/<course> --quality l --voice-engine openai
```

Supported engines:

- `openai`: requires `OPENAI_API_KEY`; uses `OPENAI_TTS_MODEL` and `OPENAI_TTS_VOICE` if set.
- `edge-tts`: requires the `edge-tts` package and network access.
- `say`: macOS fallback; uses `COURSE_SHORTS_SAY_VOICE` or `Samantha`, then falls back through named installed voices. Only accepted if it produces non-empty audio.
- `none`: render silent MP4s for visual testing.

3. Read `runs/<course>/render_report.json`.
4. If voiceover failed, fix the engine or credentials and rerun. Do not claim voiceover worked unless the report says `status: ok`.
5. Run strict validation before calling videos upload-ready:

```bash
python tools/validate_course_run.py runs/<course>
```

## Quality Bar

- Final videos should not be forced to one minute or the old short default; they should run as long as needed for the concept, example, and recall question.
- Never mux final voiceover output with `ffmpeg -shortest`. Pad the shorter stream instead: clone-pad video when narration is longer, audio-pad when narration is shorter, and record raw, voice, target, final, and pad durations in `render_report.json`.
- Clear each scene's generated Manim media before rendering and retry once after a Manim failure; interrupted partial movie caches must not poison later full runs.
- Captions must be regenerated or stretched to the final muxed duration so SRT timing, audio, and video end together.
- Every final MP4 should have a matching script and caption file.
- If audio is unavailable, the result is a visual-only draft, not a finished upload.
- Check at least one rendered MP4 before publishing a batch.

## Outputs

- Raw renders: `runs/<course>/videos/*_raw.mp4`
- Final renders: `runs/<course>/videos/*_final.mp4`
- Audio: `runs/<course>/audio/`
- Logs and report: `runs/<course>/logs/`, `runs/<course>/render_report.json`

- Render voice-first: create narration, measure its duration, regenerate Manim scenes/captions against that duration, then mux by time-scaling the video to the voiceover and padding only the final tail. Final videos should be aligned to narration length, not merely padded after an independently timed render.

---
name: course-render-voiceover
description: Use when rendering generated Manim scenes into preview or production vertical shorts, with optional voiceover, per-video audio intent, canonical production encoding, fresh provenance, frame auditing, and strict pre-publish validation.
---

# Course Render Voiceover

## Purpose

Render scenes into phone-ready MP4 shorts without confusing an iteration render with a publishable artifact. Silent, self-contained animation is the default. Voiceover is an optional enhancement, and every video must declare whether it is intentionally silent or voiced.

Set `COURSE_SHORTS_ROOT` to the absolute plugin root before invoking any wrapper. It resolves bundled tools from its own location, and `COURSE_SHORTS_PYTHON` selects the interpreter with this project's dependencies.

## Preview vs Production

- **Preview:** a native 360x640/15 fps `*_preview.mp4` made with `--quality preview`, or any MP4 that has not passed the production gates below. Preview files are for local timing and layout review only and must never be queued or entered into the final temporal-review manifest.
- **Production:** a fresh render of the current scene/script/caption/audio inputs that is encoded as 1080x1920, constant-frame-rate 30 fps, H.264, `yuv420p`, with `+faststart`; has explicit per-video audio intent; has passed a frame audit of that exact render; and passes strict validation.
- If the available render command cannot produce and prove the canonical production profile, stop at preview. Never relabel, queue, upload, hand off, or publish that output as final.

## Workflow

1. Install dependencies in the plugin or clone environment, then direct the wrappers to that interpreter:

```bash
python3 -m venv "$COURSE_SHORTS_ROOT/.venv"
"$COURSE_SHORTS_ROOT/.venv/bin/pip" install -r "$COURSE_SHORTS_ROOT/requirements.txt"
export COURSE_SHORTS_PYTHON="$COURSE_SHORTS_ROOT/.venv/bin/python"
```

2. Render a preview silently or with the desired voice engine while iterating:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --quality preview --voice-engine none
```

Supported engines:

- `piper`: offline, pinned local Piper synthesis. It validates the configured ONNX model and JSON config against `config/piper_models.json`, synthesizes every canonical beat before regenerating storyboard/Manim/captions, and fails closed on any missing file, size/hash mismatch, package-version mismatch, synthesis failure, or timing mismatch. Rendering never downloads a model.
- `openai`: requires `OPENAI_API_KEY`; uses `OPENAI_TTS_MODEL` and `OPENAI_TTS_VOICE` if set.
- `edge-tts`: requires the `edge-tts` package and network access.
- `say`: macOS fallback; uses `COURSE_SHORTS_SAY_VOICE` or `Samantha`, then falls back through named installed voices. Only accepted if it produces non-empty audio.
- `none`: render an intentionally silent MP4 when the animation stands alone visually. Silence is valid only when that intent is recorded for each video; a batch-level choice or one silent result must not authorize missing audio on another video.

For Piper, provision the files separately from rendering. Inspect the pinned, non-executing provisioning contract and validate local bytes before a smoke render:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-piper" provision-contract --model-dir /absolute/path/to/piper-models --model-id en_US-ljspeech-medium
"$COURSE_SHORTS_ROOT/scripts/course-shorts-piper" validate-model --model-dir /absolute/path/to/piper-models --model-id en_US-ljspeech-medium
"$COURSE_SHORTS_ROOT/scripts/course-shorts" render --run runs/<course> --quality production --voice-engine piper --piper-model-dir /absolute/path/to/piper-models --piper-model-id en_US-ljspeech-medium
```

`COURSE_SHORTS_PIPER_MODEL_DIR`, `COURSE_SHORTS_PIPER_MODEL_ID`, and `COURSE_SHORTS_PIPER_MODEL_MANIFEST` are equivalent environment settings. The default model directory is `models/piper`; the default pin manifest is `config/piper_models.json`. The manifest currently pins `en_US-ljspeech-medium`; do not call it a small model or substitute an unpinned asset. The Piper utility's corresponding option is `--manifest`.

3. For production, rerender from the current inputs with `--quality production`. That rerender invalidates preview provenance and is the only path that may write `*_final.mp4`.
4. Read `runs/<course>/render_report.json` and require fresh provenance for every final video. The report must identify the render invocation and time, render command/profile, current scene/script/caption inputs and selected audio input or silent intent, output path, and output identity such as a hash. Reused MP4s, stale reports, or reports that cannot tie a final MP4 to the current inputs are blocking.
5. Confirm audio intent independently for every result. A silent result must explicitly record `engine: none` or equivalent intentional-silence data and a successful/skipped status. A voiced result must name the selected engine and contain a non-empty validated audio stream. A failed real voice engine is never permission to fall back to silence.
6. Probe every production candidate and require all of the following: exactly 1080x1920; CFR 30/1 fps; H.264 video; `yuv420p`; and MP4 fast-start layout from `+faststart`. Missing probe data or VFR/ambiguous frame-rate evidence is a failure.
7. Run the frame audit after the final encode, then inspect every generated contact sheet:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/<course> --interval 0.25
```

The audit must cover every final MP4 and contain no unresolved review flags, blank/static failures, overlap, crowding, clipped text, formula glyph boxes, or diagram lines crossing text. Any rerender invalidates the previous audit; rerun it on the replacement files.

8. Run strict validation only after the fresh render and frame audit, before creating a queue or publishing:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course>
```

Do not use `--draft`, `--allow-fallback-pdf`, warnings-only probes, or manual spot checks as substitutes for this production gate. Queue or publish only the exact output identities that passed it.

## Quality Bar

- Final videos should not be forced to one minute or the old short default; they should run as long as needed for the concept and worked example.
- In silent mode, derive duration from the animation plan: allow enough time to see each state change and read its local cue, then move on. Do not stretch videos with static holds, repeated pulses, or decorative recoloring.
- Keep `planned_duration_seconds` separate from measured raw/final durations. A production render must fail when raw Manim time materially misses the semantic plan; never make a short scene pass by replacing the plan with its measured runtime.
- Never mux final voiceover output with `ffmpeg -shortest`. Legacy voice engines pad the shorter stream and record the adjustment. Piper is stricter: its per-beat expansion must make Manim and narration boundaries agree before rendering, and final muxing must use no `tpad`, `apad`, truncation, time scaling, or global speed change.
- Clear each scene's generated Manim media before rendering and retry once after a Manim failure; interrupted partial movie caches must not poison later full runs.
- Captions must be regenerated or stretched to the final muxed duration so SRT timing, audio, and video end together.
- Every final MP4 should have a matching script and caption file.
- Missing audio is expected only for the individual videos whose fresh render provenance explicitly records intentional silence. If any real engine is selected for a video, missing or empty audio is a failure.
- Audit every production video, not a sample from the batch.
- Production output is canonical 1080x1920 CFR 30 fps H.264 `yuv420p` MP4 with `+faststart`. Resolution, codec, pixel format, frame rate, or container mismatches are blocking even when playback looks acceptable.
- Strict validation must pass after the latest render and audit. Creating a queue, changing an output, or rerendering requires the relevant strict gate to be run again before publication.

## Outputs

- Preview renders: `runs/<course>/videos/*_preview.mp4`
- Production raw renders: `runs/<course>/videos/*_raw.mp4`
- Final renders: `runs/<course>/videos/*_final.mp4`
- Audio: `runs/<course>/audio/`
- Piper timing evidence: `runs/<course>/audio/*_narration_timing.json`, including canonical and storyboard beat boundaries, model/version/asset hashes, audio hash, animation-plan hash, and final-video hash.
- Logs and report: `runs/<course>/logs/`, `runs/<course>/render_report.json`

When optional narration is requested, create and measure it before the final render, then regenerate scene timing and captions around the same beat schedule. Never time-scale a finished visual argument merely to make independently authored audio fit.

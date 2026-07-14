---
name: course-output-validator
description: Use when validating preview or production course runs before handoff, queue, upload, or publish, including animation-plan contracts, canonical video encoding, fresh render provenance, automated frame triage, hash-bound human/agent temporal review, notes, scenes, captions, and queue readiness.
---

# Course Output Validator

## Purpose

Run a reusable validation pass over `runs/<course>` so previews, stale artifacts, and noncanonical renders cannot be treated as publish-ready.

Set `COURSE_SHORTS_ROOT` to the absolute plugin root before running a wrapper. Wrappers resolve bundled tools from their own location; use `COURSE_SHORTS_PYTHON` for the dependency-equipped interpreter when needed.

## Preview vs Production

- **Preview validation** uses `--draft` while assets are incomplete. It can guide iteration, but it never authorizes final handoff, queue creation, upload, or publishing.
- **Production validation** applies only to valid fingerprinted animation plans, fresh 1080x1920 CFR 30 fps H.264 `yuv420p` MP4s with `+faststart`, explicit audio intent for each video, automated frame triage, a completed hash-bound temporal review for those exact files, and a strict validator run with no preview allowances.
- Names such as `_final.mp4`, queue status such as `ready`, successful playback, and `status: rendered` are claims to verify, not proof of production readiness.

## Workflow

1. During iteration, use draft mode only to assess previews:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --draft
```

2. Require `animation_plan_index.json` plus one `animation_plans/short_XX.json` per short. Strict mode fails missing, stale, malformed, generic `numeric_rule`, non-automaton `state_machine`, route/renderer-state mismatch, reused broad-family action boilerplate, fewer than four domain-state transformations, low object-active coverage, broken continuity, full resets, or insufficient evidence windows. Draft mode warns. Each generated scene must embed the same animation-plan fingerprint.
3. Before production validation, require fresh render provenance for every final MP4. `render_report.json` must tie the current scene/script/caption and selected audio input or explicit silent intent to a specific render invocation, time, command/profile, output path, and output identity such as a hash. A stale report, reused MP4, output newer than its audit, or untraceable input/output relationship is blocking.
4. Require `render_runtime_trace.json` for the exact animation-plan index and final video hashes. Every required transform must have renderer-captured start/end markers, actual timing, beat and transition IDs, persistent object IDs, changed attribute, and structured before/after states matching the plan. Renderer evidence markers must equal the planned renderer frame; a marker one frame early or late is not a successful binding. Missing callbacks, copied planned timestamps, duplicate events, stale hashes, and unplanned actions fail production.
5. Probe every final MP4. Production requires exactly 1080x1920, constant-frame-rate 30/1 fps, H.264, `yuv420p`, and MP4 fast-start layout from `+faststart`. Fail closed when `ffprobe`/container evidence is missing, frame-rate fields disagree, or the renderer emitted a preview profile.
6. Validate audio intent per video, never once for the whole run. Each silent video must explicitly record intentional silence (`engine: none` or equivalent) in its own render result. Each voiced video must record its engine and contain a non-empty audio stream.
7. Run the automated frame audit after the final encode:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-audit" runs/<course> --interval 0.25
```

Treat its OCR, density, blank-frame, and motion results as triage. They can block a bad render, but they cannot approve a render.
8. Initialize `visual_review.json`, then actually watch every planned evidence window:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" visual-review --run runs/<course>
```

For each final MP4, complete opening, pre-action, post-action, intermediate, and final checkpoint observations; record at least four observed state changes and the persistent object IDs visible on both sides; give explicit overlap and phone-legibility verdicts; and sweep the entire video at intervals no larger than 0.25 seconds. The dense sweep must separately pass text-bearing-object collisions and persistent-text integrity, with concrete notes. Record reviewer kind (`human` or `agent`), name, completion time, and final verdict. The manifest is tied to the animation-plan index and final-video SHA-256. A pending template, sparse sweep, stale plan hash, missing/stale video hash, generic observation, or non-pass verdict blocks strict validation. Any rerender invalidates the earlier review.
9. Run strict validation from the repository root only after provenance, runtime execution trace, automated triage, and temporal review pass:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course>
```

Treat any `FAIL`, skipped required probe/audit, stale evidence, or unresolved production warning as blocking. Fix or rerender, rerun the frame audit when video bytes change, then rerun strict validation.

10. Run strict validation before queue creation. After creating or changing a queue, run strict validation again before dry-run or live publishing so queue references are checked against the already-approved output identities.

11. Use fallback-PDF allowance only for local previews. It cannot produce a production-valid run:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --allow-fallback-pdf
```

## Checks

- Notes: `notes.tex`, `notes.md`, `notes.pdf`, and `notes_compile_report.json`, including a depth check for full-course coverage and a ban on source inventory/checklist placeholders.
- LaTeX quality: prose/Python-list matrices, escaped exponent text, bare powers outside math mode, and prose `sqrt(...)` expressions.
- Short plan: every short has a complete, non-placeholder, non-repeated worked example with concrete values or symbolic objects; repeated setup/calculation pairs fail even when the concept title differs.
- Animation plans: source and artifact hashes, supported semantic renderer routes, stable object roster, continuity spine, 5-8 beats, at least four domain-state transformations, at least 70% object-active beats, no full reset, and timestamped QA evidence.
- Causal choreography: a build-transform-resolve arc on one persistent proof surface; evidence and routes visible before transit; destination state committed only after arrival; stable side-by-side comparison for competing candidates; transition counts allocated by actual beat motion time.
- Scene assets: matching animation-plan fingerprint, expected Manim scene files, script markdown, SRT captions, Python syntax, vertical scene config, sparse animation, renderer routing, and matrix/list notation leaking into on-screen text.
- Videos: expected final MP4s, Manim MP4s when scenes exist, semantic-plan versus raw-render duration, canonical 1080x1920 CFR 30 fps H.264 `yuv420p` `+faststart` encoding, blank/static sampled frames, per-video audio intent and streams, and render-report sync proving neither narration nor video was truncated.
- Provenance: each final MP4 belongs to the current render generation and inputs; the report, output identity, and frame audit all refer to the same bytes. Missing or stale provenance fails production validation.
- Visual audit: automated contact sheets, OCR, density, motion, and central visual-lane metrics from `visual_frame_audit.json` are triage only. Measure the diagram lane without title/cue bands; sustained `underfilled_visual_lane` is serious even when full-frame active tiles appear adequate.
- Portrait audit: consume renderer-emitted role bounds/masks and measure visible core proof, attached labels, and evidence separately at every stable semantic hold. Fail unresolved reflow, sustained outer-frame underfill, evidence intrusion, core width/height/area outside the shared portrait contract, hidden objects counted as occupancy, or layouts whose axes/detached text create a large bounding box around an undersized mechanism. When role metadata is unavailable, use connected-component/tile support rather than bounding-box area alone.
- Motion audit: fail any five-second-or-longer beat carried only by hidden, zero-distance, opacity/color, or tiny-pointer callbacks. Check local motion-free and low-change intervals as well as aggregate coverage, and require progressive build motion in a long transition-free hook.
- Temporal visual review: completed `visual_review.json` entries tied to current plan and MP4 hashes, with checkpoint observations, persistent-object evidence, four observed changes, explicit legibility/overlap results, a complete quarter-second transition sweep, and a named reviewer pass verdict.
- Publish queue: local file existence, output identity/readiness, and public URL warnings for API publishing. Queue status never overrides failed or stale production evidence.

## Quality Rule

Before saying a run is final or upload-ready, require valid animation plans, the canonical media probe, fresh per-video provenance, explicit per-video audio intent, automated frame triage, completed hash-bound temporal review, and the strict validator result. `--draft`, `--allow-fallback-pdf`, pending review templates, stale reports, and spot checks are preview tools only.

Run strict validation once before creating the queue and again after queue creation before publishing. Production warnings must be resolved or explicitly documented as blocking; they are not implicit permission to queue or publish.

- Validation must fail notes that omit necessary embedded figures/graphs. Scene validation must require the collision-aware layout helper, and final silent renders must align to the semantic animation-plan duration rather than a voiceover track.

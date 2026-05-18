---
name: course-manim-3b1b
description: Use when generating concept-specific Manim code for vertical math, CS, or physics shorts with 3Blue1Brown-inspired explanatory visuals, numeric examples, and subtitles.
---

# Course Manim 3B1B

## Purpose

Generate Manim scenes that are specific to each concept and its worked example. The output should feel like an explainer: dark canvas, clean geometry, animated transformations, highlighted quantities, and visualized examples.

## Workflow

1. Make sure `short_plan.json` exists.
2. For new visual families, use `course-animation-planner` first: define the claim, objects, transformations, invariant, reveal, and failure check.
3. Generate scene code, scripts, and captions:

```bash
python tools/stem_course.py manim --run runs/<course>
```

3. Inspect several generated files under:

- `runs/<course>/scenes/`
- `runs/<course>/scripts/`
- `runs/<course>/captions/`

4. Run the draft validator to catch missing assets, malformed captions, non-vertical scene config, sparse/static-looking scenes, and missing Manim renders:

```bash
python tools/validate_course_run.py runs/<course> --draft
```

5. Render a visual QA pass and inspect the contact sheets before publishing:

```bash
python tools/stem_course.py render --run runs/<course> --voice-engine none --quality l
python tools/audit_video_frames.py runs/<course>
```

Treat crowded frames, labels crossed by diagram strokes, formula glyph boxes, or overlapping text as generator bugs. Patch the visual family, regenerate scenes, rerender, and rerun the frame audit until the contact sheets are clean.

6. Improve generated Manim where the course demands it. Prefer domain-specific visuals:

- Linear algebra: number planes, vectors, bases, projections, transformed grids, eigendirections, areas.
- Calculus: moving tangent lines, accumulated area, slope fields, Taylor approximations.
- Physics: force diagrams, trajectories, fields, energy bars, wave motion.
- CS: state machines, trees, arrays, graphs, automata, complexity curves.
- Group theory / algebra: operation cycles, coset partitions, homomorphism maps, symmetry actions, quotient-style grouping.
- Economics: supply-demand intersections, elasticity response diagrams, budget lines, indifference curves, cost/revenue/marginal curves.

## Visual Standard

- Do not reuse the same generic animation for every short.
- No voiceover is required; generated MP4s should stand alone as silent visual explanations with sparse labels and captions metadata.
- The worked example must be visible, not only narrated or captioned.
- Setup, calculation, and takeaway should each move or transform mathematical/diagram objects; static text-only cards are a failure mode.
- Do not add an active-recall section to videos. Practice questions can remain in notes or queues, but the rendered video should focus on the concept and worked example.
- Use color meaningfully: one color for inputs, one for transformation/rule, one for result.
- Keep vertical 9:16 composition readable on a phone.
- Use generator safe-area/layout helpers before rendering; top titles, bottom formulas, and captions must fit inside the vertical frame with visible breathing room between bands.
- Use simplified screen formulas in videos. Keep exact notation in the notes, but do not render dense LaTeX strings on screen when a readable cue like `A x = weighted sum of columns` communicates the point.
- Put subtle background backplates behind screen text and labels so arrows, axes, curves, and grid lines cannot visually run through words.
- Do not hard-code scene length with fixed waits. Pace Manim waits and SRT cues from the generated script/caption text so each visible beat stays up long enough to read and inspect.
- Avoid filler emphasis loops. Holds should be mostly calm reading/viewing time with at most one gentle visual pulse per beat.
- Clear or fade prior visual text before placing formulas and takeaways in the same lower safe area.
- Normalize screen text before rendering: preserve spaces around operators, subscripts, products, and matrix/vector prose; avoid labels like `2*4`, `Ax=b`, or `x_1` collapsing into hard-to-read text.
- Avoid tiny formulas. If a formula is long, animate it in parts.
- Render matrices and vectors as stacked mathematical objects, not single-line Python lists.
- For non-linear-algebra topics, choose a visual family such as calculus, physics, CS, probability, chemistry, group theory, economics, or a numeric input-rule-output diagram instead of the generic placeholder.
- Group-theory and economics visual types must route to domain-specific renderers; do not let them fall through to the generic numeric rule diagram.
- Do not force a one-minute cap; keep pacing long enough for the concept and worked example to land clearly.

## Output

- Manim Python files in `runs/<course>/scenes/`
- Markdown scripts in `runs/<course>/scripts/`
- SRT captions in `runs/<course>/captions/`

- Generated scenes must use the collision-aware `safe_place`/`avoid_layout_collisions` helpers for all text and major visual groups. Do not rely on boundary checks alone; text blocks, section labels, formulas, captions, and diagrams must be registered so they cannot overlap after wrapping or scaling.

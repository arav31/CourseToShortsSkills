---
name: course-manim-3b1b
description: Use when generating concept-specific Manim code for vertical math, CS, or physics shorts with 3Blue1Brown-inspired explanatory visuals, numeric examples, and subtitles.
---

# Course Manim 3B1B

## Purpose

Generate Manim scenes that are specific to each concept and its worked example. The output should feel like an explainer: dark canvas, clean geometry, animated transformations, highlighted quantities, and visualized examples.

## Workflow

1. Make sure `short_plan.json` exists.
2. Generate scene code, scripts, and captions:

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

5. Improve generated Manim where the course demands it. Prefer domain-specific visuals:

- Linear algebra: number planes, vectors, bases, projections, transformed grids, eigendirections, areas.
- Calculus: moving tangent lines, accumulated area, slope fields, Taylor approximations.
- Physics: force diagrams, trajectories, fields, energy bars, wave motion.
- CS: state machines, trees, arrays, graphs, automata, complexity curves.

## Visual Standard

- Do not reuse the same generic animation for every short.
- The worked example must be visible, not only narrated.
- Setup, calculation, takeaway, and active recall should each move or transform mathematical/diagram objects; static text-only cards are a failure mode.
- Use color meaningfully: one color for inputs, one for transformation/rule, one for result.
- Keep vertical 9:16 composition readable on a phone.
- Use generator safe-area/layout helpers before rendering; top titles, bottom formulas, and captions must fit inside the vertical frame.
- Avoid tiny formulas. If a formula is long, animate it in parts.
- Render matrices and vectors as stacked mathematical objects, not single-line Python lists.
- For non-linear-algebra topics, choose a visual family such as calculus, physics, CS, probability, chemistry, or a numeric input-rule-output diagram instead of the generic placeholder.
- Do not force a one-minute cap; keep pacing long enough for concept, worked example, and active recall to land clearly.

## Output

- Manim Python files in `runs/<course>/scenes/`
- Markdown scripts in `runs/<course>/scripts/`
- SRT captions in `runs/<course>/captions/`

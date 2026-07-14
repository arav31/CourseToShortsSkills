---
name: course-short-plan
description: Use when turning a course into an ordered queue of short explainer videos, including prerequisites, scripts, numeric examples, visual ideas, conceptual questions, and application questions.
---

# Course Short Plan

## Purpose

Build `short_plan.json`: the ordered curriculum for short-form videos. The order must work for someone who has not taken the course yet.

Set `COURSE_SHORTS_ROOT` to the absolute plugin root before using the wrappers below. They locate the bundled tools themselves; set `COURSE_SHORTS_PYTHON` when the dependency-equipped interpreter is not `python3`.

## Workflow

1. Start from a source pack:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" plan --run runs/<course> --max-shorts 0
```

`--max-shorts 0` is the default and is the only full authoritative planning mode. For a deliberately partial exploratory plan, choose a positive limit and add `--allow-partial-plan`; otherwise planning fails closed.

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" plan --run runs/<course> --max-shorts 12 --allow-partial-plan
```

2. Review and edit `short_plan.json` when needed. The plan is not valid merely because every field is populated: each claim, formula, example, and proposed visual must match the named concept and be supported by the source pack.
3. Enforce prerequisite order:

- Vocabulary and representations before operations.
- Operations before systems/problems.
- Geometry or intuition before proofs when possible.
- Computation before abstraction if the learner is new.
- Advanced applications after the tools they need.

4. Each short item must include:

- `concept`
- `hook`
- `intuition`
- `formula` and `plain_formula`
- `prerequisites`
- `misconception`
- `worked_example` with actual numbers or a concrete symbolic example that is new for this video
- `question_prompt` with an application question and answer
- `visual_type`

5. Reject the plan item when any of these are true:

- The example is a generic numeric rule, renamed boilerplate, or a worked example from another domain.
- `formula` is flattened prose, malformed TeX, or mathematically unrelated to the explanation.
- `visual_type` is unsupported by the animation planner or cannot show the concept's invariant, transformation, comparison, or causal mechanism.
- The hook promises a result the visual story never derives.
- A theoretical concept has only decorative icons, labels, or a title-card sequence instead of a semantic object and an observable change.
- Adjacent videos repeat the same staging without a content-driven reason.

## Shorts Standard

- No fixed one-minute limit; choose the length needed to explain the concept, concrete example, and visual interpretation clearly.
- Every short needs one concrete worked example, including theoretical concepts.
- Every example should be visualizable in Manim and should teach the concept by naming inputs/objects, applying the rule/property, and stating the conclusion.
- Choose a domain renderer with real semantics: graph traversal must traverse a graph, a group action must move the acted-on object, a force diagram must resolve forces, an economic intervention must move curves or wedges, and an algorithm must expose changing state. Decorative substitutions do not count.
- The final formula or conclusion must emerge from the visual argument. It may not appear as an unrelated end card.
- Do not reuse the same example shape across adjacent shorts unless the point is explicitly to compare the concepts; changing only the concept title around the same numbers is still a repeat.
- Every short keeps a `question_prompt` for notes, captions, and queues, but videos should not add a separate active-recall section.
- Avoid repeating the same visual template for consecutive concepts.

## Outputs

- `runs/<course>/short_plan.json`
- This file feeds `course-latex-notes`, `course-manim-3b1b`, `course-render-voiceover`, and `course-instagram-series`.

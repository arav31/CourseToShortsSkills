---
name: course-short-plan
description: Use when turning a course into an ordered queue of short explainer videos, including prerequisites, scripts, numeric examples, visual ideas, conceptual questions, and application questions.
---

# Course Short Plan

## Purpose

Build `short_plan.json`: the ordered curriculum for short-form videos. The order must work for someone who has not taken the course yet.

## Workflow

1. Start from a source pack:

```bash
python tools/stem_course.py plan --run runs/<course> --max-shorts 30
```

2. Review and edit `short_plan.json` when needed. Codex should improve the auto-plan using the source pack, especially for non-linear-algebra courses.
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
- `worked_example` with actual numbers or a concrete symbolic example
- `question_prompt` with an application question and answer
- `visual_type`

## Shorts Standard

- No fixed one-minute limit; choose the length needed to explain the concept, numeric example, visual interpretation, and active-recall answer clearly.
- Every short needs one concrete worked example.
- Every example should be visualizable in Manim.
- Every short needs active recall, not only passive explanation.
- Avoid repeating the same visual template for consecutive concepts.

## Outputs

- `runs/<course>/short_plan.json`
- This file feeds `course-latex-notes`, `course-manim-3b1b`, `course-render-voiceover`, and `course-instagram-series`.

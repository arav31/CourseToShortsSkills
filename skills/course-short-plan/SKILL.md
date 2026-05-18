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
- `worked_example` with actual numbers or a concrete symbolic example that is new for this video
- `question_prompt` with an application question and answer
- `visual_type`

## Shorts Standard

- No fixed one-minute limit; choose the length needed to explain the concept, concrete example, and visual interpretation clearly.
- Every short needs one concrete worked example, including theoretical concepts.
- Every example should be visualizable in Manim and should teach the concept by naming inputs/objects, applying the rule/property, and stating the conclusion.
- Do not reuse the same example shape across adjacent shorts unless the point is explicitly to compare the concepts; changing only the concept title around the same numbers is still a repeat.
- Every short keeps a `question_prompt` for notes, captions, and queues, but videos should not add a separate active-recall section.
- Avoid repeating the same visual template for consecutive concepts.

## Outputs

- `runs/<course>/short_plan.json`
- This file feeds `course-latex-notes`, `course-manim-3b1b`, `course-render-voiceover`, and `course-instagram-series`.

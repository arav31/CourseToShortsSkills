---
name: course-latex-notes
description: Use when a user wants comprehensive LaTeX course notes, definitions, formulas, worked examples, conceptual questions, application questions, or a PDF-style study document generated from a course source pack.
---

# Course LaTeX Notes

## Purpose

Create a robust `notes.tex` and `notes.md` for the whole course, not a short summary. The notes should resemble a serious formulas-and-definitions document: topic order, prerequisites, definitions, theorems, formulas, examples with numbers, conceptual checks, application questions, and common traps.

## Inputs

- `runs/<course>/source_pack.json` from `course-source-pack`.
- `runs/<course>/short_plan.json` from `course-short-plan` when available.
- Optional reference style PDFs supplied by the user. Use them for structure and depth, not copied prose.

## Workflow

1. Generate or refresh the baseline notes:

```bash
python tools/stem_course.py notes --run runs/<course>
```

2. Read `source_pack.json`, `short_plan.json`, and the generated `notes.tex`.
3. Expand `notes.tex` until it covers the whole course at learning-notes depth:

- Start with a course map and prerequisite chain.
- Add a notation table and formula table.
- For every major topic, include a definition, intuition, formula, worked numeric example, visual interpretation, common trap, and at least three questions.
- Include both conceptual questions and application questions. Application questions should name a realistic context, inputs, method, and answer direction.
- Keep topic order beginner-safe: prerequisites before dependent concepts.
- Use LaTeX theorem-like environments for definitions, propositions, examples, warnings, and questions.

4. If `pdflatex` is available, compile:

```bash
python tools/stem_course.py notes --run runs/<course> --compile
```

## Quality Bar

- The document should be usable as a proxy for learning, not just video metadata.
- Every important formula should have an explanation of what each symbol means.
- Every abstract idea needs at least one concrete example with numbers or a small symbolic case.
- Do not omit hard topics just because they are not good short-video hooks; keep them in notes even if they are not in the shorts queue.

## Outputs

- `runs/<course>/notes.tex`
- `runs/<course>/notes.md`
- optionally `runs/<course>/notes.pdf`

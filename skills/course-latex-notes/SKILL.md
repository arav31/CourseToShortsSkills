---
name: course-latex-notes
description: Use when a user wants comprehensive LaTeX course notes, definitions, formulas, worked examples, conceptual questions, application questions, or a PDF-style study document generated from a course source pack.
---

# Course LaTeX Notes

## Purpose

Create a robust `notes.tex` and `notes.md` for the whole course, not a short summary and not a source inventory. The notes should resemble a serious formulas-and-definitions document: topic order, prerequisites, key concepts, explanations of each concept, definitions, theorems/properties, formulas, notation tables, examples with numbers, conceptual checks, application questions, and common traps. Full-course notes may be 50+ pages when the course breadth warrants it.

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

- Match the supplied reference PDF style when one is provided: title page, date, a short field-pioneer quote block in the title-page side position, black-and-white article layout, numbered sections/subsections, compact tables, and page numbers.
- Start with a course map and prerequisite chain; do not include a source inventory section.
- Add a key concepts and explanations table before the formula table.
- Add a notation/symbols table and formula table.
- For every major topic, include the key concept, a plain-English concept explanation, connections to nearby ideas, recognition cues, a definition, properties table, formula and notation explanation, worked numeric example, visual interpretation, common trap, and a multi-question bank.
- Include both conceptual questions and application questions. Application questions should name a realistic context, inputs, method, and answer direction.
- Keep topic order beginner-safe: prerequisites before dependent concepts.
- Use LaTeX theorem-like environments for definitions, propositions, examples, warnings, and questions.

4. Compile a PDF artifact. The CLI tries `latexmk`, `pdflatex`, or `tectonic` first; if no TeX engine is installed, it writes `notes.pdf` through the PyMuPDF fallback and records the engine in `notes_compile_report.json`:

```bash
python tools/stem_course.py notes --run runs/<course> --compile
```

Use `--pdf-engine latex` when you require true LaTeX compilation and want the command to fail if no TeX engine is available. Use `--pdf-engine fallback` for a guaranteed local PDF preview from the same notes data.

5. Run validation before calling the notes complete:

```bash
python tools/validate_course_run.py runs/<course> --draft
```

Fix any notes-related failures, especially fallback PDF provenance, prose matrix notation, or exponent formatting.

## Quality Bar

- The document should be usable as a proxy for learning, not just video metadata.
- Every important formula should have an explanation of what each symbol means.
- Every major topic should have a key concept and a concept explanation that can be understood before seeing the formula.
- Every abstract idea needs at least one concrete example with numbers or a small symbolic case.
- Worked examples must render simple STEM prose math as math where safe: matrices and vectors as LaTeX structures, powers as exponents, square roots as `\sqrt{}`, dot products as `\cdot`, and equations in inline or display math.
- Do not omit hard topics just because they are not good short-video hooks; keep them in notes even if they are not in the shorts queue.
- Do not cap the document to short-video length. Prefer comprehensive coverage over brevity; 50+ pages is acceptable for full courses.
- Convert important source-derived terms that are not already in the shorts plan into supplemental topic notes with definitions, notation/formula patterns, properties, example templates, and questions. Do not leave them as a source checklist, source list, bibliography, or inventory unless the user explicitly asks for sources.
- Source-derived supplemental notes must use bounded source scans or cached snippets so large OCW/PDF extracts cannot stall notes generation.

## Outputs

- `runs/<course>/notes.tex`
- `runs/<course>/notes.md`
- `runs/<course>/notes.pdf` when compiled or generated with the fallback PDF path
- `runs/<course>/notes_compile_report.json`

- Notes must embed topic-specific figures or graphs directly in `notes.tex`/`notes.pdf` using TikZ or included graphics. Every substantive topic should have a visual model when one helps the concept: supply-demand curves, algebraic structure diagrams, matrices/vector maps, graphs/state diagrams, force or waveform sketches, and similar domain figures.

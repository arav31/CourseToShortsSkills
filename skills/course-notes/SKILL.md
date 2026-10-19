---
name: course-notes
description: Write comprehensive, source-grounded LaTeX study notes for a whole course (numbered definitions, theorems with proofs, fully worked examples, TikZ figures, exercises with solutions, notation table and formula sheet) and compile them to a PDF. Use when someone wants course notes, a study guide, lecture notes, a formula sheet or a PDF write-up of a course, typically after course-plan has produced outline.json.
---

# Course Notes

**Paths.** `$SKILL_DIR` means this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`; otherwise the folder containing this SKILL.md). `$PY` is the Python interpreter printed by the course-to-shorts doctor (`PY=...`). Run directories such as `runs/<course>` are relative to the user's working directory.

Writes `runs/<course>/notes/notes.tex` plus one file per outline unit in `notes/units/`,
compiles `notes/notes.pdf` with a real TeX engine, and checks it. Requires `outline.json`
and `sources/` from course-plan (run that first if they are missing).

## Workflow

1. **Set up.** Copy [assets/notes-template.tex](assets/notes-template.tex) to
   `runs/<course>/notes/notes.tex`. Fill the title page, "About these notes" and the notation
   table, and add one `\input{units/uNN}` line per outline unit, in order.
2. **Write each unit** as `notes/units/uNN.tex`, following
   [references/notes-style.md](references/notes-style.md). For every unit:
   - read the source files listed in `outline.json` (and `grep` the sources for its key ideas),
   - start the file with `% unit: uNN` and `% sources: ...`,
   - teach the material completely: definitions, results with proofs or derivations, at
     least one fully worked example (reuse the matching short's example), a figure that
     teaches, a common trap, and 2–5 exercises with full solutions.
3. **Build and lint** after every few units, not only at the end:
   ```bash
   $PY "$SKILL_DIR/scripts/build_notes.py" runs/<course>
   ```
   A compile error prints the TeX error with file and line. Lint ERRORs (placeholders,
   code-style maths, a unit without a worked example, unsolved exercises, repeated
   boilerplate, undefined references, missing glyphs) must be fixed; read the warnings too.
4. **Look at the pages.** Open `notes/preview/sheet-*.png` (8 pages per sheet). Check the
   title page, figure placement, tables, and that no page is nearly empty. For a closer look:
   `build_notes.py runs/<course> --pages 1 12 13`, then open `notes/preview/page-012.png`.
5. **Finish** with the formula-sheet appendix, a final build with no errors, and a quick read
   of the contents page to confirm every outline unit appears in order.

## Working at scale

A full course is long. Write and build unit by unit, so errors stay local:

```bash
$PY "$SKILL_DIR/scripts/build_notes.py" runs/<course> --units u07 u08   # only these units, own folder
```

A `--units` build compiles the shared preamble with just those units into
`notes/partial/<ids>/`, lints only those files, and leaves the full report alone, so several
agents can build in parallel without clobbering each other. If you can run subagents, set up
`notes.tex` (preamble, macros, title page, all `\input` lines) first, then hand out units in
parallel (each gets: run dir, unit ids, this skill's name). Unit writers must not edit
`notes.tex`; they ask you for new macros. Finally run the full build and review the whole PDF.

## Quality bar

The notes pass when a motivated student could learn the course from them alone: every
outline unit present and complete, every result justified, every abstract idea anchored by a
worked example, figures that clarify, no filler, and clean typesetting. The status gate in
course-to-shorts also checks that `notes_report.json` is current and every unit is covered.

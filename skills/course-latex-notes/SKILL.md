---
name: course-latex-notes
description: Use when a user wants comprehensive LaTeX course notes, definitions, formulas, worked examples, conceptual questions, application questions, or a PDF-style study document generated from a course source pack.
---

# Course LaTeX Notes

## Purpose

Create a source-grounded `notes.tex` and `notes.md` for the whole course, not a short summary, prompt bank, or source inventory. The result should read like authored university notes: definitions lead to propositions and theorems, proofs explain why results hold, and worked examples and diagrams make the formalism usable. Full-course notes may exceed 50 pages when the material warrants it; never inflate page count with repeated templates or generic questions.

Set `COURSE_SHORTS_ROOT` to the absolute plugin root before running a wrapper. The wrappers resolve their own location, so no command below depends on the current working directory; set `COURSE_SHORTS_PYTHON` when needed.

## Inputs

- `runs/<course>/source_pack.json` from `course-source-pack`.
- `runs/<course>/short_plan.json` from `course-short-plan` when available.
- Optional reference style PDFs supplied by the user. Use them for structure and depth, not copied prose.

## Workflow

1. Generate or refresh the baseline notes:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" notes --run runs/<course>
```

2. Read `source_pack.json`, `short_plan.json`, and the generated `notes.tex`.
3. Expand `notes.tex` until it covers the whole course at learning-notes depth:

- Match the supplied reference PDF's document grammar, not merely its font: a `<Course> Comprehensive Notes` title page, date, a short italic saying from a verifiable field pioneer in the middle-right position, attribution beneath it, black-and-white article layout, numbered statements, compact notation tables, worked mathematics, and page numbers. Keep quote provenance in generator data; do not print its bibliographic source line on the title page.
- Bind each physics or economics figure to the exact renderer-neutral model scenario used by that topic. Axes, vectors, curves, wedges, payoff entries, numerical setup, and computed results must come from the scenario payload and expose its required evidence tokens. A generic family sketch is not an acceptable substitute for a scenario-backed figure.
- After the title page, begin substantive course content. Do not add a course map, prerequisite essay, source list, formula dump, repeated glossary, or other front matter unless the reference includes it or the user requests it.
- Treat the official Calendar as the authoritative section order. Every Calendar unit, including an explicitly scheduled Review, must appear in that order; consolidate duplicate resource wrappers under their Calendar unit rather than inventing new sections.
- Build the notes inventory directly from the grounded authoritative outline. Video renderer/model support is optional enrichment for a notes chapter and may never cause an official unit to be dropped; keep video planning fail-closed separately.
- Use substantive topic-local source contexts in the rendered definition, result, derivation/proof, example, and figure discussion. A Boolean match, digest, navigation mention, or unused cached excerpt is not source-grounded exposition.
- Organize each topic around the material itself. Use precise definitions, theorem/proposition statements with hypotheses, proofs or proof sketches where pedagogically appropriate, counterexamples at important boundaries, and complete worked examples. Do not force every topic into the same checklist.
- Put universal study checks such as units, assumptions, comparative statics, or proof hygiene in one course-level location when useful. Do not repeat the same domain checklist or warning sentence in every chapter; repetition metrics normalize topic names and numbers and must fail template padding.
- Derive subsection titles from the topic, named result, proof, or algorithm. Do not repeat a fixed shell such as `Definition and notation`, `Results and consequences`, `Proof and derivation`, `Further course results`, `Worked examples and boundary cases`, or `Structural figure` in every unit.
- Format long subsection titles with deterministic, word-preserving line breaks and an unbroken optional title for metadata. Keep multiline display text inside a self-contained, top-aligned heading box; do not place paragraph-state declarations such as `\raggedright` in a subsection argument where they can interact with adjacent content. No heading may lose, clip, or push a leading word outside the text block.
- Represent heading mathematics as structured text/math parts in generator data. Escape text parts and sanitize math parts independently; never pass strings such as `S_n` or `\(S_3\)` through a generic text escaper and never store raw TeX in a plain-text heading field.
- Write worked examples as natural mathematical prose inside numbered example environments. Integrate setup, calculation, and conclusion without printing the same `Setup.`, `Calculation or argument.`, and `Interpretation.` labels for every example; use a semantic label only when it clarifies that particular argument.
- Include exercises selectively inside the relevant section when they deepen the notes. Pair each included exercise with a real solution or useful proof outline; never create a generated question-bank appendix, `Txx-Qxx` labels, or repeated prompts such as "which hypothesis fails" and "Reproduce the worked case."
- Give every symbol its meaning where it first appears. Use a notation table only when it genuinely helps scanning, and never duplicate a formula in both flattened prose and mathematical form.
- Declare prerequisite concepts with stable semantic IDs and validate them in sequence. A notation-bearing concept must be completely defined before any result, proof, example, algorithm, or figure uses it; for cosets this includes explicit definitions of both `gH={gh:h in H}` and `Hg={hg:h in H}` before index, partition, or quotient arguments.
- Give every named result a stable semantic ID that is independent of its display label. Bind proofs to those IDs, not list position or title text, and fail generation when IDs are missing, duplicated, or unproved. Add hypothesis/conclusion anchor contracts for neighboring or easily confused results so a mathematically valid but mismatched proof body cannot pass.
- Preserve the source's Calendar and logical dependency order while consolidating duplicated lecture headings and navigation fragments.
- Cover source-supported material that does not make a good short video. Shorts are a selection; the notes are the course document.
- Add topic-specific figures only when they explain an argument or structure. Create graphs, commutative diagrams, matrices, free-body diagrams, state diagrams, geometric constructions, and economic curves in TikZ/PGFPlots or as included graphics with captions that state what the reader should notice.
- Treat a semantic figure as a bounded block containing its discussion, diagram, caption, and label. Use maximum width/height constraints that never upscale a small drawing. Reserve explicit lanes for before-state, transformation, after-state, and annotations; long labels must be normal text below a named bounding box or otherwise proven disjoint from nodes and edges.
- Let topics and figures flow through available page space. Do not insert an unconditional `\clearpage` after every unit. Use `\Needspace` around headings and figure blocks so a diagram does not spill onto a nearly empty page while the next section is forced away.
- Treat matrices, vectors, cases, aligned derivations, Greek symbols, maps, sets, radicals, and exponents as real LaTeX structures. Never leave them as prose approximations or unsupported Unicode glyphs.
- Keep topic order beginner-safe: prerequisites before dependent concepts.
- Use LaTeX theorem-like environments for definitions, propositions, examples, warnings, and questions.

4. Compile a PDF artifact with a real TeX engine:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts" notes --run runs/<course> --compile --pdf-engine latex
```

Compilation is fail-closed: a missing engine, missing glyph, unresolved reference, any LaTeX or engine warning, underfull or overfull box, absent figure, or nonzero TeX exit is a defect to fix. `--pdf-engine fallback` is only a non-publishable preview and cannot satisfy validation.

When `/opt/homebrew/bin/tectonic` is required, verify that exact executable exists and that `notes_compile_report.json` records `tectonic`; do not invoke or accept the fallback PDF path.

The exact cached-only engine command is:

```bash
cd /absolute/path/to/runs/<course>
/opt/homebrew/bin/tectonic --only-cached notes.tex
```

When the default remote-bundle client is unavailable but a complete local Tectonic bundle exists, set its absolute `.zip`, `.ttb`, or legacy bundle path before using the wrapper:

```bash
export TECTONIC_BUNDLE="/absolute/path/to/tectonic-bundle.zip"
"$COURSE_SHORTS_ROOT/scripts/course-shorts" notes --run runs/<course> --compile --pdf-engine latex
```

The same variable is inherited by Manim's semantic MathTex backend. Keep compilation cached-only when this variable is set; never downgrade to flattened text or a fallback PDF because a network client is unavailable.

Use the `stem_course.py notes ... --compile --pdf-engine latex` wrapper for the publishable run so the same command is quality-gated and recorded in `notes_compile_report.json`.

5. Run validation before calling the notes complete:

```bash
"$COURSE_SHORTS_ROOT/scripts/course-shorts-validate" runs/<course> --draft
```

Read the compile report and visually inspect every rendered page. Rasterize the full PDF at 180 DPI, OCR every page, require contiguous page coverage and non-sparse content, and inspect contact sheets plus full-resolution risk pages. Risk pages include pages 18 and 34 when present, every wrapped heading, every matrix/cases/aligned display, and every figure. Run the leading-text integrity audit against those rasterized pages; fix truncated labels, missing opening words or characters, ambiguous numbering, fallback provenance, glyph warnings, underfull or overfull boxes, prose matrix notation, duplicate numbering, clipped figures, sparse pages, and uncovered source topics.

Rendered-page QA must use real figure captions/manifests rather than the substring `figure`, inspect text and semantic-element bounding boxes for collisions, and measure usable-body extent plus the largest blank vertical run. Title pages are explicit exceptions; ordinary figure pages with content ending high in the body or a dominant blank run fail even when word-count and ink thresholds pass. Aggregate coverage failures must report structured reasons such as repetition ratio and missing outline titles instead of an empty generic error.

## Quality Bar

- The document should be usable as a proxy for learning, not just video metadata.
- Every important formula should have an explanation of what each symbol means.
- Every major topic should contain enough explanation to learn the idea, not just recognize its name.
- Every abstract idea needs a concrete example, a proof-level explanation, or both; choose what teaches the idea instead of filling a template.
- Worked examples must render simple STEM prose math as math where safe: matrices and vectors as LaTeX structures, powers as exponents, square roots as `\sqrt{}`, dot products as `\cdot`, and equations in inline or display math.
- Do not omit hard topics just because they are not good short-video hooks; keep them in notes even if they are not in the shorts queue.
- Do not cap the document to short-video length. Prefer comprehensive coverage over brevity; 50+ pages is acceptable for full courses.
- Convert important source-derived material that is not already in the shorts plan into full sections integrated into the course narrative. Do not leave it as supplemental templates, a source checklist, bibliography, or inventory unless the user explicitly asks for sources.
- Source-derived supplemental notes must use bounded source scans or cached snippets so large OCW/PDF extracts cannot stall notes generation.
- Validate coverage semantically against the source pack and every material entry. A heading mention does not count as coverage without a definition/result, explanation, and appropriate example, proof, algorithm, or figure.
- Require `source_grounding.matched=true` for every rendered unit. `content_basis=curated-domain`, plan membership, or a generic domain library never makes an absent topic grounded.
- Exclude advanced or adjacent subjects absent from the official corpus. Comprehensiveness means every course unit and substantive source, not unrelated padding; prerequisites may appear only when the corpus or Calendar explicitly requires and justifies them.
- For MIT 18.703, follow the Calendar through Groups, Subgroups, Cosets, Cyclic Groups, Permutation Groups, Conjugation in `S_n`, Isomorphisms, Homomorphisms and Kernels, Quotient Groups, Isomorphism Theorems, Alternating Groups, Presentations and Groups of Small Order, Sylow Theorems and Applications, Rings, Basic Properties of Rings, Ring Homomorphisms and Ideals, Field of Fractions, Prime and Maximal Ideals, Special Domains, Euclidean Domains, Polynomial Rings, A Quick Primality Test, Group Actions and Automorphisms, and Review. Do not add Galois groups or solvable groups when the source pack does not contain them.
- For MIT 18.703, every one of the 24 Calendar units must have a referenced semantic TikZ figure with a distinct label and explanatory caption; a generic fallback drawing does not count. The result/proof ledger must cover all 61 core results, and the prerequisite ledger must pass before TeX is written.

## Outputs

- `runs/<course>/notes.tex`
- `runs/<course>/notes.md`
- `runs/<course>/notes.pdf` when compiled with the required real TeX engine
- `runs/<course>/notes_compile_report.json`
- `runs/<course>/notes_coverage_report.json`

Notes must embed topic-specific figures or graphs directly in `notes.tex`/`notes.pdf` using TikZ or included graphics. Every figure must have a caption, label, and an explicit reference in the surrounding exposition.

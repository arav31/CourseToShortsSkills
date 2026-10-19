# Notes style

The notes should read like a strong student's (or TA's) complete write-up of the course:
restrained article layout, course order, numbered definitions and results, real proofs
and derivations, fully worked examples, figures that teach, and a few exercises with full
solutions. They are a substitute for attending, not a summary of it.

## Document grammar

```
Title page          course, code/institution, "Study notes", date; a short verified quote
                    by a pioneer of the field, right-aligned in the middle of the page
Contents
About these notes   2–3 sentences: scope, prerequisites, how sections build
Notation            one table for the whole course
1 <Unit title>      one \section per outline unit, in course order (units/u01.tex ...)
  ...
Appendix A          Formula sheet: the key results gathered, each pointing to its section
```

## A unit file (`notes/units/uNN.tex`)

```latex
% unit: u03
% sources: sources/021-lecture-3-multiplication-and-inverse-matrices.txt, sources/022-...
\section{Multiplication and inverse matrices}\label{sec:u03}

Opening paragraph: what problem this unit solves, and how it connects to the previous one.

\subsection{Four ways to multiply matrices}         % headings name the content, not "Definitions"
\begin{definition}[Matrix product] ... \end{definition}
Prose that explains why the definition is the right one, with the picture in words.
\begin{proposition}[Column view] ... \end{proposition}
\begin{proof} ... \end{proof}
\begin{example} ... every step shown, with \begin{bmatrix}...\end{bmatrix} ... \end{example}
\begin{figure}[ht]\centering
  \begin{tikzpicture} ... \end{tikzpicture}
  \caption{What the figure shows and why it matters.}\label{fig:u03-columns}
\end{figure}
\begin{trap} A common mistake, and how to recognise it. \end{trap}

\subsection{Exercises}
\begin{exercise} ... \end{exercise}
\begin{solution} ... \end{solution}
```

- The two comment lines at the top are required: `% unit: <id>` lets the status gate check
  coverage; `% sources:` records provenance (sources are never listed in the visible text).
- Headings use sentence case ("Projection matrices and least squares"), matching across units.
- Subsection titles come from the content ("Gauss–Jordan finds the inverse"), and the structure
  follows the material: a proof-heavy unit is mostly statements and proofs; an algorithms unit
  has pseudocode, a trace and complexity; a modelling unit has assumptions, model, solution, interpretation.
- State hypotheses and conclusions precisely. Pair each proof with the result it proves,
  by label, never by position.
- Define every object before it is used. When a later unit relies on an earlier result, cite it.
- Labels carry their unit id so units written in parallel never collide and can cite each other:
  `\label{sec:u10}` on the section, `\label{thm:u10-rank-nullity}`, `\label{fig:u10-subspaces}`;
  elsewhere `Theorem~\ref{thm:u10-rank-nullity}`.

## Exam and review units

Exams and exam reviews in the outline become study material, not summaries of logistics:
- **Exam units**: each question as an `exercise` with a complete `solution` (rephrase the question;
  fix any errors you find in official solutions and say so in a `trap`). Add a short paragraph on
  what the exam tested.
- **Review units**: a compact recap of the part's main results (cite their sections), then solved
  problems that combine ideas. A unit with at least three solved exercises does not also need an
  `example` environment.

## Depth and grounding

- Write from the sources: read the unit's lecture notes/transcripts and use the course's own
  examples, notation and emphasis. Then add what a learner needs that the sources assume:
  intermediate steps, intuition, a second example, a counterexample.
- Every unit needs at least one fully worked example with numbers or a concrete small object,
  and every important result needs a proof, derivation or (when the course omits it) a clear
  sketch with a pointer to where a full proof lives.
- Use the short's worked example (from short_plan.json) in the matching unit so notes and videos agree;
  when a short spans several units, the full example goes in its `primary_unit` (default: the first
  unit listed) and the others refer to it.
- Transcripts are machine-extracted and sometimes jumbled (two columns interleaved); cross-check
  them against the session summaries and solutions. Provenance for material that is not a course
  source goes on the same comment line: `% sources: sources/..., short_plan.json (s04)`.
- Load extra TikZ libraries in `notes.tex` (the template already loads the common ones), never
  inside a unit file.
- Course materials contain slips (a wrong matrix entry in a recitation, a sign error in a posted
  solution). Recompute every number you take from a source; when the source is wrong, give the
  correct value and point out the slip in a `trap`.
- Length follows content. A full semester course typically produces 50–120 pages. Never pad:
  no repeated boilerplate ("Remember to check your units"), no per-unit question templates.
- Exercises: 2–5 per unit, distinct, each with a complete solution. Prefer the course's own
  problem sets (rephrased) and their solutions when available.

## Figures

Draw figures in TikZ/pgfplots directly in the unit file. A figure must teach something the
text refers to: a vector diagram, a plot sampled from the actual function, a graph with the
algorithm's state, a commutative diagram, a supply/demand shift, a free-body diagram.
Label the quantities used in the derivation. Keep figures compact (`width=0.6\textwidth`
for plots) and check them in the page previews: labels must not collide or clip.

```latex
\begin{tikzpicture}[scale=0.8,>=Stealth]
  \draw[->] (-0.5,0) -- (6,0) node[right] {$x_1$};
  \draw[->] (0,-0.5) -- (0,5) node[above] {$x_2$};
  \draw[->,very thick,blue] (0,0) -- (2,1) node[below right] {$a_1$};
  \draw[->,very thick,orange] (0,0) -- (1,3) node[left] {$a_2$};
\end{tikzpicture}
```

## Typesetting

- All mathematics in math mode: `\begin{bmatrix}`, `\sqrt{}`, `x^{2}`, `\frac{}{}`, `\cdot`.
  Never `[[1, 2], [3, 4]]`, `sqrt(2)`, `x**2` or `x^2` in text.
- Headings with maths use `\texorpdfstring` so PDF bookmarks stay valid:
  `\subsection{Conjugation in \texorpdfstring{$S_n$}{Sn}}`.
- Use `align*` for multi-step derivations, `cases` for piecewise definitions, `booktabs` for tables.
- Avoid hard page breaks inside a unit; let figures float (`[ht]`).

## Failure modes seen before (do not repeat)

Topics invented from site boilerplate; the same six subsection names in every unit; generic
sentences repeated across chapters; questions without answers; figures labelled "Generated
figure"; proofs attached to the wrong theorem; objects used before they are defined; escaped
maths in headings (`S\_n`); a fallback PDF passed off as a LaTeX build; whole outline units
silently dropped; stranded figures on nearly empty pages.

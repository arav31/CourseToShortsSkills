# outline.json and short_plan.json

Both live in the run directory (`runs/<course-slug>/`). `check_plan.py` validates them.

## outline.json — the course as taught

The course's own structure (lectures, sessions, chapters, weeks) in course order. It is
the coverage contract for the notes: every unit gets a notes chapter.

```json
{
  "course": {
    "title": "Linear Algebra",
    "code": "18.06SC",
    "institution": "MIT OpenCourseWare",
    "instructor": "Gilbert Strang",
    "url": "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/",
    "level": "first university course; assumes high-school algebra",
    "field_quote": {"text": "...", "author": "..."}
  },
  "units": [
    {
      "id": "u01",
      "title": "The geometry of linear equations",
      "summary": "Row picture vs column picture of Ax = b; a solution is a combination of the columns that reaches b.",
      "key_ideas": ["row picture", "column picture", "linear combination", "matrix-vector product"],
      "sources": ["sources/014-lecture-1-the-geometry-of-linear-equations.txt"]
    }
  ]
}
```

- `id`: `u01`, `u02`, ... in course order. Group lectures into units only when the
  course itself does; a 34-lecture course can have 34 units.
- `summary`: what the unit actually teaches, in one or two sentences, in your words.
- `sources`: run-relative paths of the files you read for it. Every unit needs at least one.
- `field_quote` (optional): a short quotation by a pioneer of the field for the notes'
  title page. Only use a quote you are confident is real and correctly attributed; omit it otherwise.

## short_plan.json — the video series

```json
{
  "course_title": "Linear Algebra",
  "series": {
    "title": "Linear Algebra, one picture at a time",
    "audience": "curious beginners; no prior linear algebra",
    "hashtags": ["#linearalgebra", "#math", "#manim", "#stem"]
  },
  "shorts": [
    {
      "id": "s01",
      "slug": "ax-mixes-columns",
      "title": "A x mixes the columns",
      "units": ["u01"],
      "prerequisites": [],
      "hook": "Multiplying a matrix by a vector looks like arithmetic. Here's the picture hiding inside it.",
      "claim": "A x is the combination x1 a1 + x2 a2 of the columns of A.",
      "worked_example": {
        "setup": "A has columns a1 = (2, 1) and a2 = (1, 3); x = (4, 2).",
        "steps": [
          "Scale the columns: 4 a1 = (8, 4) and 2 a2 = (2, 6).",
          "Add tip to tail: (8, 4) + (2, 6) = (10, 10).",
          "Row check: 2*4 + 1*2 = 10 and 1*4 + 3*2 = 10."
        ],
        "result": "A x = (10, 10), reached by mixing the columns."
      },
      "visual": "One number plane. The column arrows a1 and a2 grow from the origin, stretch to 4 a1 and 2 a2, then chain tip to tail to land on (10, 10). The same two arrows persist through every step.",
      "misconception": "A x is not a mysterious row-by-row recipe; the row rule is just bookkeeping for the column picture.",
      "practice": {
        "question": "With the same A, which x lands on (3, 4)?",
        "answer": "x = (1, 1), since a1 + a2 = (3, 4)."
      },
      "reel_caption": "Optional hand-written Instagram caption. If absent, one is composed from hook, claim and practice."
    }
  ],
  "skipped_units": [
    {"unit": "u17", "reason": "Exam review session; no new idea to animate (covered in notes)."}
  ]
}
```

Field rules (enforced by `check_plan.py` unless marked advisory):

| field | rule |
|---|---|
| `id` | `s01`, `s02`, ... in teaching order |
| `slug` | kebab-case, unique; the video folder is `shorts/<NN>-<slug>/` |
| `title` | ≤ 60 characters (it must fit the on-screen title band) |
| `units` | outline unit ids this short teaches |
| `prerequisites` | ids of *earlier* shorts only |
| `hook` | 5–30 words; the question or tension, landing within ~3 seconds |
| `claim` | the one sentence the video makes obvious |
| `worked_example` | `setup`, ≥ 2 `steps`, `result`; concrete numbers or objects; computed correctly; not reused from another short |
| `visual` | names the persistent on-screen objects and the motion that carries the argument |
| `misconception` | advisory: the trap this short defuses |
| `practice` | advisory: one question with its answer (for captions/notes, not shown as a quiz in the video) |
| `skipped_units` | every unit not covered by a short needs an entry with a reason |

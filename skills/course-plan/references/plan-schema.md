# outline.json and short_plan.json

Both live in the run directory (`runs/<course-slug>/`). `check_plan.py` validates them.
The examples below use an algorithms course; your files describe your course.

## outline.json — the course as taught

The course's own sequence (lectures, sessions, chapters, weeks) in course order. It is the
coverage contract for the notes: every unit gets a notes section.

```json
{
  "course": {
    "title": "Introduction to Algorithms",
    "code": "6.006",
    "institution": "MIT OpenCourseWare",
    "instructor": "Erik Demaine, Jason Ku, Justin Solomon",
    "url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/",
    "level": "second-year undergraduate; assumes discrete maths and Python",
    "term": "Spring 2020",
    "parts": ["Data structures", "Graphs", "Dynamic programming"]
  },
  "units": [
    {
      "id": "u09",
      "session": "Lecture 9",
      "part": "Graphs",
      "title": "Breadth-First Search",
      "summary": "BFS explores a graph in layers of equal distance from the source using a FIFO queue; it computes unweighted shortest-path distances and a parent tree in O(V + E).",
      "key_ideas": ["frontier / queue", "layers", "shortest-path tree", "O(V+E)"],
      "sources": ["sources/3fa91c-lecture-9-breadth-first-search.txt", "sources/b27d04-lecture-9-notes.txt"]
    }
  ],
  "assessments": [{"title": "Quiz 1", "sources": ["sources/9c1e2a-quiz-1-solutions.txt"]}]
}
```

- `id`: `u01`, `u02`, ... in course order.
- What is a unit: every teaching session in the course sequence (`sources/INDEX.md` lists the
  site's navigation order when the site has one). Exam-review sessions and exams that appear in
  the sequence may be units too: the notes turn them into solved practice sets, and the shorts
  plan lists them under `skipped_units`. If you would rather not give them notes sections,
  put them in `assessments` instead.
- `summary`: what the unit actually teaches, in one or two sentences, in your words.
- `sources`: run-relative paths of the files you read for it; at least one per unit. File names
  start with a stable id (`3fa91c-...`) that survives re-ingesting.
- Optional, free-form: `course.term`, `course.textbook`, `course.parts`, `course.field_quote`
  (`{"text", "author"}`: only a quotation you are sure is real and correctly attributed),
  `unit.session`, `unit.part`, `unit.key_ideas`, top-level `assessments`. Other stages ignore
  what they do not need.

### Papers

For a research paper the same files work; units are sections. Optional course fields for papers:
`"type": "paper"`, `"authors": [...]`, `"venue"`, `"year"`, `"arxiv"` or `"doi"`, and `"license"`
(where the copy came from and its terms). Leave out References, Acknowledgements and author
biographies; an appendix is a unit only if a short or the notes use it.

### Literature reviews

A review in Markdown is ingested with `ingest.py review.md --review` (add `--fetch-cited` to collect
the cited papers). Course fields: `"type": "review"`, `"authors"` (the review's authors), and
`"license"` if it is not the user's own text. Units are the review's sections (themes), and each
unit lists the works it draws on: `"cites": ["kaplan2020", "hoffmann2022"]`, using the keys in
`sources/INDEX.md` → *Cited works*. In `short_plan.json` every short has `"cites"` too (checked:
each key must be in the review's reference list), and `series.attribution` names the review.

## short_plan.json — the video series

```json
{
  "course_title": "Introduction to Algorithms",
  "series": {
    "title": "Algorithms you can see",
    "audience": "programmers who have never taken an algorithms course",
    "hashtags": ["#algorithms", "#computerscience", "#manim", "#coding"],
    "attribution": "optional; for papers e.g. 'Vaswani et al., Attention Is All You Need (2017)'"
  },
  "shorts": [
    {
      "id": "s04",
      "slug": "bfs-grows-in-layers",
      "title": "BFS grows in layers",
      "units": ["u09"],
      "prerequisites": ["s03"],
      "hook": "How does a GPS-style search know the fewest hops without trying every path?",
      "claim": "BFS visits vertices in order of distance because the queue holds layer k before layer k+1.",
      "worked_example": {
        "setup": "Graph with edges s-a, s-b, a-c, b-c, b-e, c-d; start at s; neighbours in alphabetical order.",
        "steps": [
          "Dequeue s: discover a and b at distance 1. Queue: a, b.",
          "Dequeue a: discover c at distance 2. Dequeue b: c is already seen; discover e at distance 2.",
          "Dequeue c: discover d at distance 3. Dequeue e, then d: nothing new."
        ],
        "result": "Distances s=0, a=1, b=1, c=2, e=2, d=3; visit order s, a, b, c, e, d."
      },
      "visual": "One 6-node graph above a queue strip. Each dequeue lights a node, its new neighbours slide into the queue and are coloured by layer, and parent edges thicken into the BFS tree.",
      "misconception": "BFS does not find shortest paths in weighted graphs; it counts edges, not weights.",
      "practice": {
        "question": "Add edge a-d. What is d's distance now?",
        "answer": "2, via s-a-d."
      },
      "reel_caption": "Optional hand-written Instagram caption. If absent, one is composed from hook, claim and practice."
    }
  ],
  "skipped_units": [
    {"unit": "u12", "reason": "Quiz 1 review session; covered as solved problems in the notes."}
  ]
}
```

Field rules (errors from `check_plan.py` unless marked advisory):

| field | rule |
|---|---|
| `id` | `s01`, `s02`, ... in teaching order |
| `slug` | kebab-case, unique; the video folder is `shorts/<NN>-<slug>/` |
| `title` | ≤ 60 characters; the on-screen title band holds about 26 bold characters at full size, so keep the shown title near that |
| `units` | outline unit ids this short teaches; optional `primary_unit` names the one whose notes carry the full worked example (default: the first) |
| `prerequisites` | ids of *earlier* shorts only |
| `hook` | 5–30 words; the question or tension, landing within ~3 seconds |
| `claim` | the one sentence the video makes obvious |
| `worked_example` | `setup`, ≥ 2 `steps`, `result`; concrete numbers or objects; computed correctly; not reused from another short |
| `visual` | names the persistent on-screen objects and the motion that carries the argument |
| `misconception` | advisory: the trap this short defuses |
| `practice` | advisory: one question with its answer (for captions/notes, not shown as a quiz in the video) |
| `cites` | reviews only: the reference keys of the works this short explains (at least one; each must be in the review's reference list) |
| `skipped_units` | every outline unit not covered by a short, each with a reason; only real unit ids |

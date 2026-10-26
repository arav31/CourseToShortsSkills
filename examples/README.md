# Examples

Everything here was produced by agents following the skills in this repository, from short
requests, and then reviewed. The rendered media (MP4s, GIFs, the compiled notes PDF) live in
[`../docs/media`](../docs/media) and on the [showcase page](https://arav31.github.io/CourseToShortsSkills/).

## Linear Algebra (`mit-18.06sc/`)

Request: *"Turn MIT's Linear Algebra course https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/
into a plan: I want complete notes for the whole course, and a demo series of 5 explainer shorts
that show the arc of the course."*

| file | what it is |
|---|---|
| [`outline.json`](mit-18.06sc/outline.json) | 41 units in the course's own order, each with a summary and the source files it came from |
| [`short_plan.json`](mit-18.06sc/short_plan.json) | the 5-short series: hooks, claims, computer-checked worked examples, visual ideas; 29 units skipped with reasons |
| [`notes/`](mit-18.06sc/notes) | `notes.tex` + one file per unit; compiled: [linear-algebra-notes.pdf](../docs/media/linear-algebra-notes.pdf) (221 pages) |
| [`shorts/NN-*/`](mit-18.06sc/shorts) | each short's `storyboard.md`, `scene.py` (shortkit/Manim) and captions |

How it was made: one agent ran `course-plan` (crawl, outline, plan, check); six agents wrote the
notes units in parallel with `course-notes`; five agents made the shorts in parallel with
`course-video`; the coordinating agent assembled the notes, wrote the formula sheet, reviewed every
short's contact sheets, and ran the publish gate. The agents' reports drove many fixes to the skills.

To reproduce a short (needs the toolkit's dependencies; see the main README):

```bash
cp -r examples/mit-18.06sc/shorts/05-svd-circle-to-ellipse /tmp/svd
python skills/course-video/scripts/render.py /tmp/svd --quality final
```

## Algorithms (`mit-6.006/`)

Request: *"Use the course-to-shorts skills to make a second showcase course from a different field:
MIT 6.006 Introduction to Algorithms. Plan the whole course, then make a 3-short demo (BFS layers,
Dijkstra relaxation, dynamic programming) to final quality."* Notes were out of scope for this run.

| file | what it is |
|---|---|
| [`outline.json`](mit-6.006/outline.json) | 21 lecture units in the course's order (from the calendar), each with a summary and its lecture notes, transcript and recitation; quizzes, problem sets and the final as assessments |
| [`short_plan.json`](mit-6.006/short_plan.json) | the 3-short series with hooks, claims, worked examples, visual ideas; the other 18 units skipped with reasons (most with a visual idea for a full series) |
| [`checks/examples.py`](mit-6.006/checks/examples.py) | recomputes every number in the plan and cross-checks it by brute force (all simple paths, the actual call tree) |
| [`shorts/NN-*/`](mit-6.006/shorts) | each short's `storyboard.md`, `scene.py` and captions |

The BFS short runs the lecture's own exercise ("run breadth-first search from s in the graph in
Example 3"), built level set by level set as 6.006 teaches it. The Dijkstra short uses a fresh
five-place road map whose direct road loses to a four-road detour. The dynamic-programming short
collapses the lecture's Fibonacci call tree into its subproblem DAG.

How it was made: the coordinating agent ran `course-plan` (crawl: 166 sources; outline; plan;
verified examples); three agents made the shorts in parallel with `course-video`; the coordinator
reviewed every contact sheet, sent fixes back, approved the final renders and ran the gate
(`run_status.py --gate --shorts-only`).

## Bayes' theorem, standalone (`standalone-bayes/`)

Request: *"Make me a narrated vertical explainer short on Bayes' theorem, using the classic
medical-test example: 1% prevalence, 90% sensitivity, 9% false positives. Why is a positive result
only about a 9% chance of having the disease?"*

## Research papers (`papers/`)

Request: *"Test the video format on turning research papers into explainer videos too: make a few
samples based on popular AI, economics and maths papers."* One agent per paper ran `course-plan`
on the paper alone (`ingest.py --single`), then `course-video` for one short; the coordinator
reviewed every contact sheet and folded each run's friction back into the skills.

| folder | paper | short |
|---|---|---|
| [`papers/lemons/`](papers/lemons) | George A. Akerlof, "The Market for 'Lemons': Quality Uncertainty and the Market Mechanism", *QJE* 84(3), 1970 ([doi](https://doi.org/10.2307/1879431)) | four cars, hidden quality: the market unravels until only the lemon trades |
| [`papers/attention/`](papers/attention) | Vaswani et al., "Attention Is All You Need", NeurIPS 2017 ([arXiv:1706.03762](https://arxiv.org/abs/1706.03762)) | scaled dot-product attention on three words, worked to the output vector |
| [`papers/pagerank/`](papers/pagerank) | Sergey Brin and Lawrence Page, "The Anatomy of a Large-Scale Hypertextual Web Search Engine", WWW7, 1998 ([Stanford copy](http://infolab.stanford.edu/~backrub/google.html)) | a four-page web and the random surfer, ticked to the steady state |
| [`papers/shannon/`](papers/shannon) | Claude E. Shannon, "A Mathematical Theory of Communication", *Bell System Technical Journal* 27, 1948 | entropy as the average number of yes/no questions; the question tree is a prefix code |

Each folder has the paper's `outline.json` (one unit per section), `short_plan.json`,
`checks/examples.py` (recomputes every number in the short) and the short's `storyboard.md`,
`scene.py` and captions. The papers' text is not included: the outlines point at the
ingested sources, which you recreate with `ingest.py <paper URL> --single`. The videos explain the
papers in their own words, use their own small examples, and reproduce no figures or text.

## Literature review (`reviews/scaling-laws/`)

Request: *"Turn my literature review examples/reviews/scaling-laws/review.md into one 3Blue1Brown-style
explainer short."* The review ([`review.md`](reviews/scaling-laws/review.md)) is a short Markdown survey of
neural scaling laws citing seven papers (Hestness et al. 2017 to Pearce & Song 2024).

| file | what it is |
|---|---|
| [`review.md`](reviews/scaling-laws/review.md) | the input: five sections and a reference list with arXiv ids |
| [`outline.json`](reviews/scaling-laws/outline.json) | one unit per review section, each with the works it `cites` |
| [`short_plan.json`](reviews/scaling-laws/short_plan.json) | one short citing Kaplan 2020, Hoffmann 2022 and Pearce & Song 2024, with `source_notes` where the review and the originals differ |
| [`checks/examples.py`](reviews/scaling-laws/checks/examples.py) | recomputes every number on screen from values quoted from the original papers |
| [`shorts/01-bigger-model-or-more-data/`](reviews/scaling-laws/shorts/01-bigger-model-or-more-data) | storyboard, scene and captions |

How it was made: `ingest.py review.md --review --fetch-cited` split the review into sections, keyed its
references and fetched all seven cited papers; one agent planned and made the short with `course-plan`
and `course-video`. Both rules start from the 10²¹-FLOP comparison Hoffmann et al. report themselves
(4.68B vs 2.86B parameters) and sweep out to Gopher's budget. Checking against the originals found six
places where the review paraphrased loosely (for example, it had Pearce & Song's result backwards);
the review in this folder has since been corrected, and the plan's `source_notes` record what was found.

## Licence

The `mit-18.06sc/` notes and videos are derived from MIT OpenCourseWare 18.06SC, *Linear Algebra*
(Gilbert Strang, Fall 2011), and the `mit-6.006/` plan and videos from MIT OpenCourseWare 6.006,
*Introduction to Algorithms* (Erik Demaine, Jason Ku and Justin Solomon, Spring 2020), both used under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The files in this folder
and in `docs/media` are shared under the same licence. MIT OpenCourseWare does not endorse them.

The `papers/` plans and videos are commentary on the cited papers, made for teaching; the papers
remain their authors' and publishers' work, and their authors have not reviewed or endorsed these videos.

# Examples

Everything here was produced by agents following the skills in this repository, from short
requests, and then reviewed. The rendered media (MP4s, GIFs, the compiled notes PDF) live in
[`../docs/media`](../docs/media) and on the [showcase page](https://arav31.github.io/CourseToShortsSkills/).

## `mit-18.06sc/`: one course, start to finish

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

## `standalone-bayes/`: one concept, no course

Request: *"Make me a narrated vertical explainer short on Bayes' theorem, using the classic
medical-test example: 1% prevalence, 90% sensitivity, 9% false positives. Why is a positive result
only about a 9% chance of having the disease?"*

## Licence

The example notes and videos are derived from MIT OpenCourseWare 18.06SC, *Linear Algebra*
(Gilbert Strang, Fall 2011), used under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The files in this folder
and in `docs/media` are shared under the same licence. MIT OpenCourseWare does not endorse them.

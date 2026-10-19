# Run directory layout

Everything for one course lives in `runs/<course-slug>/`. Skills communicate only through
these files, so any stage can be re-run or handed to another agent.

```
runs/<course-slug>/
  source_pack.json          index of collected sources + warnings           (course-plan: ingest.py)
  sources/
    INDEX.md                readable table of sources
    NNN-<slug>.txt          one page/PDF/transcript as text, with a header
  outline.json              the course's units in order                    (course-plan: you)
  short_plan.json           the video series                               (course-plan: you)
  plan_check.json           result of check_plan.py, bound to the plan hash (course-plan)
  notes/
    notes.tex               preamble, title page, notation, \input of units (course-notes: you)
    units/uNN.tex           one section per outline unit                   (course-notes: you)
    notes.pdf               compiled PDF                                   (build_notes.py)
    notes_report.json       engine, page count, lint issues, source hash   (build_notes.py)
    preview/sheet-NN.png    page contact sheets for review                 (build_notes.py)
  shorts/
    NN-<slug>/              NN = position in short_plan.json (01, 02, ...)
      storyboard.md         claim, objects, layout, beats                  (course-video: you)
      scene.py              ShortScene with BEATS                          (course-video: you)
      timing.json, audio/   narration clips and durations                  (voice.py)
      preview.mp4           540x960 iteration render                       (render.py)
      NN-<slug>.mp4         1080x1920 final render                         (render.py --quality final)
      NN-<slug>.srt         captions                                       (render.py)
      render_report.json    beats, issues, motion scan, hash               (render.py)
      review/sheet-NN.png   contact sheets                                 (render.py / audit.py)
      review.json           approval bound to the MP4 hash                 (audit.py approve)
      build/                Manim media and logs (deletable)
  reels_queue.json          ordered posting queue                          (course-reels)
  reels_results.json        publish results                                (course-reels)
```

Freshness rules used by `run_status.py`:

- `plan_check.json` counts only if its `plan_sha256` matches the current `short_plan.json`.
- `notes_report.json` counts only if its `source_sha256` matches the current TeX files.
- A render counts only if the MP4 hash matches `render_report.json` and `scene.py` is not newer.
- An approval counts only if `review.json`'s hash matches the current MP4.

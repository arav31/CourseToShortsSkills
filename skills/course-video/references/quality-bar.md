# Quality bar for a short

Distilled from a long audit of earlier renders (see `docs/history/v1-quality-audit.md` in
the repository). Use it twice: while storyboarding, and while looking at contact sheets.
A short is done when every item holds.

## The explanation

1. **Opens on the real object.** The first 2–3 seconds show the actual mathematical
   object and the question. No generic "elements → operation → structure" opener, no title card.
2. **One persistent scene, not slides.** The same objects are carried and transformed
   through setup → operation → consequence. Replacing everything between beats is a slideshow.
3. **Every motion means something.** Each animation performs an operation, comparison,
   mapping, accumulation or state change. Pulses, wiggles and sweeping highlight bars do not.
4. **The mechanism is visible.** Merge sort splits and merges; BFS grows a frontier from a
   queue; a coset translates a subgroup and tiles the group; a tax drives a wedge between
   buyer and seller prices. If the narration describes a step the picture does not show, fix the picture.
5. **The conclusion comes last.** The formula or theorem arrives as the summary of what the
   picture just did, never before the derivation.
6. **Universal claims look universal.** "For every g" means showing all cases in a small
   instance, or a matching/non-matching contrast. One favourable case does not prove a claim.
7. **Numbers agree everywhere.** Values on screen, in narration and in the plan come from the
   same variables in `scene.py` (compute them; do not retype them).
8. **Plotted curves come from the model.** Sample the actual function. A quadratic is not a straight chord.
9. **Ends on the resolved state.** Stop when the claim is established; no replayed cycles, no long frozen tail.

## The frame (9:16 on a phone)

10. **The main object dominates the stage.** Use `STAGE.fit(...)` or `stage_plane(...)`; a small
    diagram floating in the middle of a big empty frame fails.
11. **Readable text.** Nothing below `MIN_FONT_SIZE`. Simplify or split a busy beat instead of shrinking.
12. **No overlaps, no clipping.** Text never overlaps text, never leaves the safe area, never
    sits in the caption band. Lines, arrows and curves never cut through words (use `plate()`).
13. **Real typesetting.** Maths through `tex()`: fractions, subscripts, matrices, Greek. No `x_1`,
    `^2`, `*`, `sqrt(`, `\frac` or other source syntax visible on screen.
14. **Few words on screen.** Labels and equations; the narration and captions carry the sentences.
    On-screen prose is at most one short line at a time.
15. **Colour carries meaning.** Inputs blue, the rule/operation yellow, results green, contrast red,
    used consistently across the series.

## Time

16. **Narration and picture agree.** Each beat's animation shows what its line says while it says it.
    `render.py` flags beats whose animation runs much longer than the narration (silent gaps).
17. **No dead zones.** Nothing longer than ~4 s without a meaningful change, except a deliberate
    reading hold. The automatic scan flags 6 s as a warning and 10 s as an error.
18. **Length follows the idea.** Usually 30–75 s. Do not pad a small idea or cram a big one; split it.

## Transitions

19. **Persistent text stays intact.** Do not sweep filled masks across the title, equations or labels.
    Look at frames *during* transitions (`audit.py frames --at ...`), not only at endpoints.
20. **Swaps do not collide.** When objects exchange places, route them on separate paths or fade
    one out first. Labelled objects passing through each other is an overlap.

## Narration

21. Spoken English, as a good teacher would say it: "A times x", "two by two", "x sub one".
    No symbols, no markdown, no "as you can see on the screen".
22. One or two sentences per beat; short words; the first line asks the question.
23. Never mention the pipeline, the generator, "this video was made by...", or repair notes.

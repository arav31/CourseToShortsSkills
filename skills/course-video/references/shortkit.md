# shortkit API

`from shortkit import *` gives you all of Manim plus the names below. The source is
`scripts/shortkit.py`; `assets/example_scene.py` is a complete, reviewed example.

## Scene contract

```python
from shortkit import *

BEATS = [                      # literal list; ids are lowercase; narration is spoken English
    ("hook", "Why does every matrix-vector product land in the column space?"),
    ("columns", "Read A as two arrows: its columns."),
]

class Short(ShortScene):       # any class name; it must subclass ShortScene
    def construct(self):
        with self.beat("hook"):        # every BEATS id exactly once, in order
            self.title("A x mixes the columns")
            ...
        with self.beat("columns"):
            ...
```

- A beat lasts at least as long as its narration clip (+ `pad=` seconds if given). Animations
  inside run first; the remainder is held. If animations run longer, the overrun is recorded.
- After each beat the layout checker records errors for text outside `SAFE`, text in
  `CAPTION_ZONE`, overlapping text and text below `MIN_FONT_SIZE`, and warnings when text
  hides or is crossed by an arrow/line/curve, or a shape reaches into the caption band.
  It inspects the actual geometry on screen at the end of the beat, so it cannot see
  problems that exist only mid-transition; that is what looking at frames is for.
- `self.title(s, *also)` sets/swaps the compact title, playing `also` animations with it so the
  first frame already shows the real object: `self.title("Bayes in a crowd", FadeIn(grid))`.
  `play=False` only registers it. Call it inside the first beat.
- `self.cue("word", nth=0, offset=0.0)` waits until the narration reaches that word in the current
  beat (real word timings with edge-tts, an even-pace estimate otherwise), so motion lands on the
  spoken word. `self.beat_time()` is the time since the beat started.
- `self.clear_stage(*keep)` fades out everything except the title and `keep`.
- `self.allow_overlap(a, b)` declares an intentional overlap between two texts or a text and a
  shape (rarely needed; `highlight()` outlines are already exempt).
- `self.show_zones()` draws zone outlines while debugging (remove before final).
- Class attributes: `captions = True` (reserve the caption band), `tail_seconds = 0.6`.

## Layout

| name | what |
|---|---|
| `TITLE_ZONE`, `STAGE`, `CAPTION_ZONE`, `SAFE`, `FRAME_ZONE` | `Zone`s in scene units (frame is 9 x 16) |
| `zone.fit(mob, buff=0.1, upscale=True, max_scale=None, align="center"|"top"|"bottom")` | scale into the zone and move there; `upscale=False` for text |
| `zone.rows(*weights, gap=0.25)`, `zone.cols(*weights, gap=0.25)` | split into sub-zones |
| `zone.point(fx, fy)`, `zone.center`, `.left/.right/.top/.bottom/.width/.height` | positions |
| `stage_plane(x_range, y_range, zone=STAGE)` | `NumberPlane` with equal x/y scale, as large as fits |
| `vec(plane, (x, y), color, start=(0, 0))` | phone-thick arrow in plane coordinates |

## Text and maths

| name | what |
|---|---|
| `text(s, size=Size.BODY, color=INK, width=None, weight=NORMAL, t2c=None)` | words only; wraps to `width` |
| `tex(src, size=Size.BODY, color=None, math=True)` | LaTeX via tectonic/pdflatex → SVG; `math=False` for text with `$...$` |
| `matrix_tex([[2, 1], [1, 3]])`, `matrix_tex([4, 2])` | bmatrix from numbers (column vector for a flat list) |
| `label(s, math=False, backplate=True)` | short label on a backplate |
| `plate(mob)` | rounded backplate behind text so lines never cross it |
| `highlight(mob, color=YELLOW_K)` | outline (not a filled sweep) |
| `Size.TITLE 48, HEADLINE 46, BODY 38, LABEL 34, SMALL 30`, `MIN_FONT_SIZE 28` | font sizes |

Colour inside LaTeX: `\cB{..}` blue (input), `\cY{..}` yellow (rule), `\cG{..}` green (result),
`\cR{..}` red (contrast), `\cP{..}` purple, `\cO{..}` orange, `\cM{..}` muted.
Unmarked glyphs are white. Example: `tex(r"\cB{x_1}\,a_1 + \cB{x_2}\,a_2 = \cG{b}")`.

Palette constants: `BG, INK, MUTED, GRID, BLUE_K, YELLOW_K, GREEN_K, RED_K, PURPLE_K, ORANGE_K`
and the semantic aliases `INPUT, RULE, RESULT, ALERT`.

## Spoken numbers

`BEATS` must be a literal, but numbers must be computed. Compute in Python, then assert that the
narration says the same thing, so an edit to one cannot silently contradict the other:

```python
FP = round(0.09 * 990)                      # 89
assert "eighty-nine" in BEATS[3][1] and FP == 89
```

## Manim gotchas worth knowing

- `tex()` glyphs come out in reading order of the typeset formula (for `\frac`: numerator, bar,
  denominator), so `eq[0:5]` selects the first five glyphs. Slices are fine to animate, but they
  are new groups: after `TransformFromCopy(a, eq[3:6])`, remove the loose copies and `self.add(eq)`.
- Stroke widths are in Manim units where 1 = 0.01 scene units; on a 9-unit-wide frame the
  defaults look thick, and `vec()` already uses a phone-friendly width.

- Do not use `MathTex`/`Tex` directly: they need a `latex` binary that may be absent. Use `tex()`.
- `tex()` returns glyph-level SVG parts. To morph equations use `TransformMatchingShapes(a, b)`
  or `FadeTransform(a, b)`; `Transform` between unrelated expressions scrambles glyphs.
- `Transform(a, b)` keeps `a` on screen (now looking like `b`); `ReplacementTransform(a, b)`
  swaps in `b`. Keep track of which object you will animate next.
- `MoveAlongPath` needs a path with points: use `Line`/`VMobject`, never a `DashedLine` (its parent has no points).
- `FadeIn(mob)` builds its own start state; do not set opacity 0 on the target first.
- Build an object fully (position, size, plate) before showing it; then animate only the change.
- Compute numbers in Python (`B = (X[0]*a + ...)`) and format them into labels with f-strings
  (`rf"A\,x = ({B[0]},\,{B[1]})"`); never type results by hand.
- Updaters (`always_redraw`, `add_updater`) keep running during waits, so live values stay live.
- Keep each scene file self-contained; helper functions go in the same file.

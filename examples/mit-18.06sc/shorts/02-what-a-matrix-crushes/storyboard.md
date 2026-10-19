# What a matrix crushes  (s02 — "What a matrix keeps and what it crushes")

claim:      Rank r splits the inputs into an r-dimensional row space that A keeps and an
            (n - r)-dimensional nullspace that A sends to zero (and the outputs into a
            column space of dimension r plus a never-reached left nullspace of dimension m - r).
example:    A = [[1, 2, 2], [2, 4, 4]] (m = 2, n = 3). row 2 - 2 row 1 = 0 -> one pivot, r = 1.
            Special solutions s1 = (-2, 1, 0), s2 = (-2, 0, 1); A s1 = A s2 = 0 -> nullspace plane, dim 3 - 1 = 2.
            (1, 2, 2) . s1 = -2 + 2 + 0 = 0, (1, 2, 2) . s2 = -2 + 0 + 2 = 0 -> row space is the normal line.
            x = (-1, 3, 2) = (1, 2, 2) + s1; A x = (9, 18) = A (1, 2, 2).
            Outputs: multiples of (1, 2) (column space); (2, -1) is perpendicular and never reached.
            Counts: 1 + 2 = 3 inputs, 1 + 1 = 2 outputs.
            (all verified with numpy before writing; scene.py recomputes them and asserts the spoken numbers)
objects:    the matrix (hook/rank), then one 3D input picture drawn by our own orthographic
            projection: the nullspace as a gridded red "floor" (square patch in the plane),
            s1/s2 as red arrows in the floor, the row (1, 2, 2) as a blue "pole" standing out of it,
            x as a white arrow = pole + s1 (tip to tail); later an R2 output plane (NumberPlane)
            with the green column-space line, the (9, 18) arrow and the red left-nullspace line.
projection: camera chosen so the row vector is screen-up (floor seen from 30 deg above, rotated
            40 deg in the floor). Everything is rebuilt from (azimuth, elevation, scale, origin)
            ValueTrackers, so the view can tilt edge-on (elevation -> 0: floor becomes a line,
            the pole stands at a visible right angle) and later shrink to make room for R2,
            while labels keep their font size (they are re-pinned, never scaled).
layout:     input phase: equation band at the top of STAGE (y 3.35..4.8), 3D picture below it.
            output phase: 3D picture shrinks into the top part (pushed right), R2 plane fills the
            bottom part, a yellow curved arrow labelled A links them on the left; dimension counters
            sit in the free left column / lower-left corner.
colours:    input x = white (it is the whole input; its two parts carry the meaning),
            kept input part / row space = blue, operation (elimination, A) = yellow,
            outputs / column space = green, crushed or missed (nullspace, left nullspace) = red.
invariant:  the same floor, pole and arrows persist from "special" to the end; only the view moves.
reveal:     r + (n - r) = n and r + (m - r) = m, after the picture has shown 1 + 2 = 3 and 1 + 1 = 2.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | This matrix eats three numbers and returns two. Some inputs vanish completely. Which ones, and how many? | [1 2 2; 2 4 4] times a blue x column = green y column is written with the title; "3 inputs" / "2 outputs" tags on cue; on "vanish" the outputs turn into red zeros, on "which" the inputs turn into blue question marks (A [?] = 0 poses the question). |
| rank | Subtract twice row one from row two: all zeros. One pivot, so the rank is one. | the matrix centres and grows; yellow "row 2 - 2 x row 1"; row 2 glyphs morph into muted zeros (glyph-matched to the echelon form U); pivot outlined in yellow; "rank r = 1" in green. |
| special | Two special solutions, minus two, one, zero and minus two, zero, one, both go to zero. | U slides into the band (top-left); s1 and s2 grow as red arrows on the spoken numbers; band "s1 = (-2,1,0) -A-> 0", "s2 = ... -> 0". |
| plane | So does every mix of them: a whole plane, the nullspace, of dimension three minus one, which is two. | the gridded red floor grows from the origin; a sample mix vector sweeps a full turn across it; "nullspace" label; band "A(a s1 + b s2) = 0", then "dim N(A) = 3 - 1 = 2" on "three". |
| row | The row, one, two, two, has zero dot product with both, so the row space stands perpendicular to that plane. | U's first row flies to the tip of the growing blue pole as its label; band swaps to the two dot products (-2+2+0, -2+0+2); right-angle mark + "row space"; camera tilts edge-on (floor becomes a line, pole upright). |
| split | Take x equals minus one, three, two. It is the row plus the first special solution. | camera tilts back; white x grows; on "row" the pole is indicated and "= (1,2,2)" appears; on "plus" a copy of s1 lifts to the pole tip and lands on x's tip, "+ (-2,1,0)" appears; dashed edge closes the parallelogram. |
| crush | Apply A. The nullspace part is crushed to zero, and the row part lands on nine, eighteen. That is A x. | band clears; the 3D picture shrinks into the top-right; R2 plane and the yellow A arrow draw in; on "crushed" the red top part shrinks (x swings onto the pole) while a copy of the floor flies down and collapses to the output origin; on "lands" a copy of the pole travels down and becomes the green arrow to (9, 18); "A x = (9, 18)". |
| outputs | Every output is a multiple of one, two: the column space. Its perpendicular, through two, minus one, is never reached. | green line through (1, 2) draws across R2; a green dot scans down and back up the line; "column space"; on "perpendicular" the red line through (2, -1), "left nullspace" and a right-angle mark. |
| count | One kept plus two crushed makes three inputs. One reached plus one missed makes two outputs. | "1 + 2 = 3" (blue/red) top-left while the pole and floor are indicated; "1 + 1 = 2" (green/red) bottom-right of R2 while the two lines are indicated. |
| rule | In general, rank r keeps r input directions and crushes n minus r. | the counters morph into r + (n - r) = n and r + (m - r) = m. |

risks:
- 3D on a phone: a tilted plane with standard axes is hard to read at 9:16. Mitigation: no coordinate
  axes; the nullspace is a gridded floor and the row space a vertical pole, which reads instantly;
  the edge-on tilt proves the right angle instead of asking the viewer to infer it.
- s1 and s2 are only 37 deg apart, so the fan can look like one arrow. Mitigation: azimuth chosen
  so they point toward the viewer, where foreshortening opens the fan.
- (9, 18) forces a small output scale: the R2 plane uses a 3-unit grid and spans the whole width.
- crowding after the shrink: s1/s2 tip labels fade out at the shrink; labels keep full size.
- static holds: every beat has 2-4 animations; the row beat ends on the tilt.

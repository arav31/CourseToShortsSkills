# Best fit: a right angle  (s03, least-squares-right-angle)

claim:      The least-squares line is the one whose error vector e = b - p is perpendicular to
            every column of A; writing that right angle down gives A^T A x_hat = A^T b.
example:    Fit b = C + D t to (0, 6), (1, 0), (2, 0). A = [1 0; 1 1; 1 2], b = (6, 0, 0).
            No exact line (C = 6 forces D = -6 and D = -3). Best line 5 - 3t, misses (1, -2, 1),
            squared total 1 + 4 + 1 = 6 (the second attempt 6 - 3t scores 9).
            p = (5, 2, -1) = 5 a1 - 3 a2, e = (1, -2, 1), a1.e = 1 - 2 + 1 = 0, a2.e = 0 - 2 + 2 = 0.
            A^T A = [3 3; 3 5], A^T b = (6, 0) -> C = 5, D = -3.
objects:    (1) a t-b graph: three blue data dots, one line driven by trackers (C, D), red vertical
            miss bars attached to the dots, a "sum of squared misses" meter made of three red
            segments (e1^2, e2^2, e3^2 end to end).
            (2) an R3 picture drawn with an honest orthographic camera that looks down on the
            column-space plane: the plane (faint), column arrows a1, a2 (blue), b (blue), its shadow
            p (green), the error e (red) from p up to b, yellow right-angle markers.
            (3) an equation column for the algebra.
layout:     beats hook..best: the graph fills STAGE; equations and meter sit in its empty top-right
            corner (the line falls from upper-left to lower-right, so that corner stays clear).
            beat space onward: the graph shrinks to the top-left of STAGE, the equation column takes the
            top-right, and the R3 picture fills the bottom ~55% of STAGE.
invariant:  the three data points and the best line stay on screen from the first second to the
            last; colours never change meaning (blue data/columns, green best line/p/x_hat,
            red misses/e, yellow the perpendicular).
reveal:     A^T A x_hat = A^T b, stated after the picture showed e perpendicular to both columns,
            then checked on the numbers (C = 5, D = -3 = the line the slider found).

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Three points refuse to sit on one line. Which line fits best, and why does a right angle decide it? | title + axes + three blue dots in the first frame; a white trial line pinned at (0,6) swings through them |
| nofit | Through the first point, the line needs C equals six. Then point two wants D equals minus six, and point three wants minus three. | b = C + Dt, C = 6 appear top-right; on "two" the line pivots through dot 2 (dot 3 ringed red, D = -6); on "three" through dot 3 (dot 2 ringed red, D = -3) |
| misses | So let it miss. Least squares tilts and slides the line until the squared vertical misses are as small as possible. | red vertical bars attach to the dots; meter of three red segments e_i^2 (9 for 6 - 3t); line slides to 5 - 3t (6), tilts both ways about its middle (8), settles |
| best | It settles on five minus three t, missing by one, minus two and one. Squared, they add to six. | line turns green with b = 5 - 3t; bar labels +1, -2, +1; meter labels 1, 4, 1 and = 6 |
| space | Now stack the three heights into one arrow b, in three dimensions. The heights of every possible line fill a plane, spanned by the columns of A. | graph shrinks top-left; heights 6, 0, 0 fly into b = (6, 0, 0); R3: b grows; on "every" C(1,1,1) + D(0,1,2); on "plane" the disc patch, its (C, D) lattice and a1, a2 appear; a white probe line on the graph and a white dot on the plane move together |
| drop | Straight below b sits the closest point, p: five, two, minus one, the best line's heights. The drop is the error e. | yellow plumb line falls from b; on "five" p grows (green), row becomes p = (5, 2, -1); on "heights" green dots appear on the graph line; on "drop" e (red) and the right-angle marker in triangle O-p-b |
| perp | So e is perpendicular to both columns: one minus two plus one is zero, and zero minus two plus two is zero. | camera turns about e until a1 is screen-horizontal; a1, a2 slide to p; marker e/a1 + a1.e = 1-2+1 = 0; camera turns until a2 is horizontal; marker e/a2 + a2.e = 0-2+2 = 0 |
| normal | So A transpose e is zero. Write e as b minus A x hat, and out come the normal equations: A transpose A x hat equals A transpose b. | rows collapse to A^T e = 0; columns slide home; on "write" -> A^T(b - A x_hat) = 0 while the camera returns; on "normal" -> A^T A x_hat = A^T b, boxed green |
| solve | Here they give C equals five and D equals minus three: the same best line, found by a right angle. | [3 3; 3 5] x_hat = (6, 0); on "five" x_hat = (C, D) = (5, -3); on "same" the graph line, its label and p are indicated together |

risks:
- Crowding: three areas (graph, equations, R3) share 8.2 x 7.5 units. Mitigation: the graph is
  big only while it is the whole story; equations replace each other instead of stacking.
- Text shrinking when the graph shrinks: keep all text out of the scaled group, rebuild labels
  at their normal size.
- The R3 picture reading as flat: use a floor-like camera (column-space plane seen from above at
  ~30 degrees), e vertical on screen, marker on a screen-horizontal floor direction.
- Misreading the right angle as being on the graph: say it, and keep the vertical miss bars
  vertical (never perpendicular to the line).
- No DecimalNumber (needs a latex binary): the meter is geometry, its value appears via tex() once settled.
- Length: nine beats, 79.7 s final (slightly over the 75 s guideline; two views of one fit).
- R3 camera: one fixed view cannot show e at a right angle to p, a1 and a2 at once (a2 is
  perpendicular to p, so one of them always points into the screen). The camera turns about e
  so each right angle is shown from a view where it reads as one.

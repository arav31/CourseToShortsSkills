# Rows vs columns

claim:      Solving A x = b means finding the mix of A's columns that lands exactly on b.
example:    2x - y = 0, -x + 2y = 3. Rows: the lines y = 2x and -x + 2y = 3 cross at (1, 2).
            Columns: a1 = (2, -1), a2 = (-1, 2), b = (0, 3); 1*a1 + 2*a2 = (2, -1) + (-2, 4) = (0, 3).
            (All values computed in scene.py from A and b; solution via Cramer's rule, asserted.)
objects:    one number plane (x -3.5..3.5, y -2.7..4.3); the system on a plate in a bottom band
            (it later morphs into the column form x[2;-1] + y[-1;2] = [0;3]); two row lines with
            their equations as labels; crossing dot (1, 2); column arrows a1, a2; target ring b;
            stretched 2*a2; green result arrow 0 -> b.
layout:     title in TITLE_ZONE. Plane fills STAGE. Equation band = plate centred at the bottom of
            the plane (plane y < -1.3), where nothing of the column picture lives; row line 1 is
            clipped at the band top (it would pass behind the plate anyway). Row labels: line 1 top
            centre (left of the line), line 2 upper-left (above the line). Arrow labels at the tips.
invariant:  the same system/equation band and the same two column arrows are carried throughout;
            the solution numbers 1 and 2 are green everywhere (crossing point, weights, recipe).
colour:     inputs blue: a1 = BLUE_K, a2 = periwinkle #8A9BFF (second input, still blue family);
            rule/attention yellow: highlight outlines on columns, Indicate on rows of arithmetic;
            results green: crossing dot, weights 1 and 2, result arrow, b once reached.
            Row lines are neutral white (each row mixes both columns).
reveal:     A x = b  <=>  x a1 + y a2 = b, shown last in the band.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Two x minus y is zero, and minus x plus two y is three. What does solving this look like? | Title; the system writes in, big, centre of stage. |
| rows | The usual picture reads it row by row: each equation is a line. | Plane draws in; system shrinks into the bottom band; at "row by row" a copy of row 1 flies to its label spot, then line 1 draws (so they never cross); same for row 2 on a leftward arc. |
| cross | The solution is where the lines cross: x is one, y is two. | Green dot grows at (1, 2); label (1, 2) fades in. |
| columns | Now read the same system down its columns: two, minus one goes with x, and minus one, two goes with y. | Lines, labels, dot fade. Yellow outline on the x column, column turns blue; outline on y column, turns periwinkle; each column morphs into a column vector: x[2;-1] + y[-1;2] = [0;3]. |
| arrows | Each column is an arrow. The right side, zero, three, is a target point, b. | Copy of [2;-1] flies to the plane as a1 grows; same for a2; copy of [0;3] becomes the ring b at (0, 3). |
| scale | Which mix of the arrows reaches b? Try one copy of the first arrow, and two copies of the second. | x and y in the band become green 1 and 2; a1 label becomes 1 a1; a2 stretches to (-2, 4) leaving a ghost, label 2 a2. |
| add | Chain them tip to tail. Two minus two is zero, minus one plus four is three: exactly b. | 2 a2 slides to start at a1's tip and ends on b; the top-row entries turn yellow while "two minus two is zero" is said, then the bottom row; green result arrow 0 -> b, ring and b turn green. |
| same | And that recipe, one and two, is the very point where the lines crossed. | At "one": green dot at (1, 2) and the green 1 and 2 fly out of the band into the label (1, 2); at "lines": faint row lines redraw through that point. |
| takeaway | So solving A x equals b means finding the mix of A's columns that lands on b, a picture that still works with a thousand unknowns. | Band equation fades out, A x = b <=> x a1 + y a2 = b fades in; at "Unlike crossing lines" the faint lines, dot and (1, 2) fade, leaving the column picture + formula. |

risks:
- Crowding near (1, 2): the dot, the shifted 2 a2 arrow (passes (1, 1)) and labels. Labels placed
  down-right of the dot, 2 a2 label further down-right of the segment; check frames.
- a1's tip (2, -1) sits just above the band plate; plane y-range chosen so the gap is ~0.3 units.
- Two blues must read as different arrows on a phone; check contact sheets, fall back to labels.
- TransformMatchingShapes column -> vector can look scrambled; it is done per column so glyphs only
  travel within their own column.
- Static stretch in the arrows/scale beats if narration runs long: keep 2-3 motions per beat.

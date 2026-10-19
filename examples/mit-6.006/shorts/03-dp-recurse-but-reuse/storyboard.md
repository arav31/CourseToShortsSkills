# Recurse, but re-use  (s03, MIT 6.006 lecture 15)

claim:      Dynamic programming solves each distinct subproblem once: the exponential tree of
            recursive calls collapses into a DAG of n + 1 subproblems, solved left to right.
example:    fib(n) = fib(n-1) + fib(n-2), fib(0) = 0, fib(1) = 1 (the lecture's code), n = 5.
            Call tree: 15 calls; F3 twice, F2 three times, F1 five times, F0 three times;
            6 distinct subproblems F0..F5. 14 tree edges -> 8 dependencies F(k-1), F(k-2) -> F(k)
            (k = 2..5, < 2n = 10). Topological order 0, 1, 1, 2, 3, 5.
            n = 30: 2,692,537 calls (2 F31 - 1) vs 31 subproblems; F30 = 832,040.
            (scene.py builds the real call tree of fib(5) and lays it out from that structure,
            runs instrumented plain recursion for n = 30, fills the row bottom-up, and asserts
            every spoken number; checks/examples.py verified the same values.)
objects:    the call tree of fib(5): 15 circles (radius 0.46) labelled F_k (tex, size 44) with grey
            edges behind them, laid out from the tree itself (tidy layout: each subtree packed against
            its sibling's per-depth contour, scaled to the stage width); a header with n on its own line
            and "15 calls" (left) / "6 subproblems" (right) under it; one memo row of 6 cells
            (shortkit strip style, 1.08 x 1.5, name F_k at the top of each cell, value below) which is
            also the subproblem DAG: chain arrows k-1 -> k curve under the row, skip arrows k-2 -> k
            arc over it. Later the row becomes 31 thin cells for n = 30; the time formula closes.
layout:     header at the top of STAGE (n at y 4.5, counters at y 3.95); the tree fills the rest of
            STAGE (root y 3.05, deepest level y -2.12, x in [-4, 4]); the memo row sits in the middle
            (y 0.3) with its arcs from y -0.95 to 2.2. n = 30 / rule: "dynamic programming" (y 2.75),
            the 31-cell row (y 1.0, F0 and F30 under its ends), formula below it (y -1.55 and -2.3).
colours:    root call F5 and n blue (input); the call running right now outlined yellow while the tree
            grows; repeated calls and their edges red (wasted work), the calls counter red; yellow
            rings point at all copies of one subproblem; arrows flash yellow while a cell is computed;
            filled cells, values, used arrows, the subproblems counter and the O(n) result green;
            empty cells and unused arrows muted.
invariant:  the 15 calls are carried from the tree into the row (no node disappears; equal ones merge);
            the 14 edges are carried onto the 8 arrows; the same row is filled and then stretched to n = 30.
reveal:     time = #subproblems x work each = (n + 1) * O(1) = O(n), after the row has shown 6 cells
            filled with one addition each and 31 cells for n = 30.

| beat | narration (spoken) | picture (what moves) |
|------|--------------------|----------------------|
| hook | Plain recursion needs 2.7 million calls for the thirtieth Fibonacci number, but only thirty-one different answers. Where does the waste go? | title; the blue root F5 and the red calls counter appear at once; the tree grows call by call in real call order (F5, F4, F3, F2, F1, F0, F1), the running call outlined yellow, the counter ticking. |
| five | Here is Fibonacci of five. Each call splits in two, down to one or zero: fifteen calls. | n = 5 appears; the remaining 8 calls grow (still in call order); the 15th lands on "fifteen". |
| repeat | Most are repeats: F of three runs twice, F of two three times, F of one five times, F of zero three times. | on each count yellow rings mark every copy of that subproblem; the copies after the first turn red with their edges: the second F3 with its whole subtree, then F4's F2 subtree, then the last spare F1 (9 red = 15 - 6). |
| collapse | Only six are different. Sort the calls into columns, merge each column into one cell, and fourteen tree edges pile onto eight dependencies. | rings on the 6 first calls, "6 subproblems" appears; every copy of F_k slides into column k (lagged k = 0..5, edges stay attached): the columns show 3, 5, 3, 2, 1, 1 copies; on "merge" each column collapses into one cell; on "fourteen" the 14 edges morph onto the 8 dependency arrows. |
| fill | Every arrow points right, so fill left to right. Zero and one are given; each next cell adds the two before it: one, then two, then three, then five. | a yellow pulse runs along every arrow in its direction; F0 = 0 and F1 = 1 turn green, each with its line under the row (F_0 = 0, F_1 = 1); on "each" the general rule F_k = F_{k-1} + F_{k-2} appears above that line; for k = 2..5 the old instance line fades out, the new one comes in up to the substitution (F_k = F_{k-1} + F_{k-2} = a + b) while the two incoming arrows turn yellow and pulse into cell k, then on the spoken value "= v", the cell value, the green cell and green arrows appear together. All lines are built from the computed values and aligned on their first "="; they fade out at the start of the scale beat. |
| scale | Six subproblems instead of fifteen calls. And for thirty: thirty-one subproblems instead of 2.7 million calls. | the two counters are boxed in turn; on "thirty" arrows, values and names clear, n = 5 becomes n = 30, the six cells shrink into the first six of 31 and the row grows to 31 green cells (F0 ... F30) while the subproblems counter rolls 6 -> 31; on "2.7" the calls counter rolls 15 -> 2,692,537. |
| rule | That's dynamic programming: recurse, but re-use. Time equals subproblems times work per subproblem: here n plus one, times constant, so order n. | "dynamic programming" heading; the formula writes below the row: time = #subproblems x work each; on "n" "= (n + 1)" appears while the 31-cell row is boxed; then "* O(1)", then "= O(n)" in green with a green box. |

risks (and what was done):
- 15 nodes on 9:16: tidy layout + full stage height; labels at size 44 so subscripts stay ~31 >= 28.
- The collapse could become a jumble: two clear steps (sort into columns, then merge each column),
  the group in flight drawn above the calls still waiting, and duplicate labels fade as columns merge.
- Live counters can show the old digits beside the new ones during other animations: the counters
  update their glyph object in place (Counter subclass of LiveText).
- The fill must show the relation, not only the picture: one general line plus one instance line per cell under
  the row, swapped old-out-then-new-in (no superimposed glyphs); the values no longer ride the arcs.
- n = 30: the row and formula use the freed space; the header keeps n on its own line.

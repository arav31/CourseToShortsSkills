"""Example short: matrix-vector multiplication as a mix of columns.

Storyboard
  claim      A x is the combination x1*a1 + x2*a2 of A's columns.
  objects    one number plane; column arrows a1, a2; their scaled copies; the result point.
  layout     equations stack in the empty upper-left of the plane (on plates); the numbers
             were chosen so every arrow stays below/right of that column.
  beats      columns appear -> weights read off x -> arrows stretch -> tip-to-tail sum
             -> row arithmetic agrees -> general formula.
  invariant  the same two column arrows are carried through every step.
  reveal     A x = x1 a1 + x2 a2, stated last, after the picture has shown it.
"""

from shortkit import *

BEATS = [
    ("hook", "Multiplying a matrix by a vector looks like a pile of arithmetic. Here is the picture hiding inside it."),
    ("columns", "Take the matrix A with columns two, one and one, two. Draw each column as an arrow."),
    ("weights", "Let x be three, two. Its entries are weights: three of the first column, two of the second."),
    ("scale", "So stretch the first arrow by three, and the second arrow by two."),
    ("add", "Now chain them tip to tail. Where you land is A times x: the point eight, seven."),
    ("check", "The row-by-row rule agrees: two times three plus one times two is eight, and one times three plus two times two is seven."),
    ("takeaway", "So A times x is always a mix of the columns of A, weighted by the entries of x."),
]

A = [[2, 1], [1, 2]]
X = [3, 2]
COL1 = (A[0][0], A[1][0])
COL2 = (A[0][1], A[1][1])
S1 = (X[0] * COL1[0], X[0] * COL1[1])
S2 = (X[1] * COL2[0], X[1] * COL2[1])
B = (S1[0] + S2[0], S1[1] + S2[1])  # computed, never typed by hand
C1, C2 = BLUE_K, ORANGE_K
assert spoken(B[0]) in BEATS[4][1] and spoken(B[1]) in BEATS[4][1]  # narration says the computed point


class Short(ShortScene):
    def construct(self):
        plane = stage_plane(x_range=(-1, 11, 1), y_range=(-1, 11, 1))
        top_left = plane.c2p(-0.6, 10.6)  # anchor for the equation column

        def slot(mob, below=None):
            """Pin a plate in the equation column (top-left, left-aligned)."""
            if below is None:
                return mob.move_to(top_left, aligned_edge=UP + LEFT)
            return mob.next_to(below, DOWN, buff=0.25).align_to(below, LEFT)

        with self.beat("hook"):
            self.title("A x mixes the columns")
            eq = tex(rf"A\,x=\begin{{bmatrix}}\cB{{{A[0][0]}}}&\cO{{{A[0][1]}}}\\\cB{{{A[1][0]}}}&\cO{{{A[1][1]}}}\end{{bmatrix}}"
                     rf"\begin{{bmatrix}}{X[0]}\\{X[1]}\end{{bmatrix}}", size=Size.HEADLINE + 6)
            eq.move_to(STAGE.center)
            self.play(Write(eq), run_time=1.6)
            self.wait(0.5)
            eq_plate = plate(eq.copy().scale(0.8))
            slot(eq_plate)
            self.play(Create(plane, lag_ratio=0.05), FadeTransform(eq, eq_plate), run_time=1.6)

        with self.beat("columns"):
            a1 = vec(plane, COL1, C1)
            a2 = vec(plane, COL2, C2)
            l1 = tex(r"a_1", color=C1).next_to(a1.get_end(), RIGHT, buff=0.12)
            l2 = tex(r"a_2", color=C2).next_to(a2.get_end(), RIGHT, buff=0.12)
            self.play(GrowArrow(a1), FadeIn(l1), run_time=1.0)
            self.play(GrowArrow(a2), FadeIn(l2), run_time=1.0)

        with self.beat("weights"):
            weights = plate(tex(rf"x=\begin{{bmatrix}}\cB{{{X[0]}}}\\\cO{{{X[1]}}}\end{{bmatrix}}", size=Size.HEADLINE))
            slot(weights, below=eq_plate)
            self.play(FadeIn(weights, shift=DOWN * 0.2), run_time=0.8)
            self.add(a1.copy().set_opacity(0.25), a2.copy().set_opacity(0.25))  # ghosts of the originals

        with self.beat("scale"):
            n1 = tex(rf"{X[0]}\,a_1", color=C1).next_to(plane.c2p(*S1), DOWN + RIGHT, buff=0.1)
            n2 = tex(rf"{X[1]}\,a_2", color=C2).next_to(plane.c2p(*S2), DOWN + RIGHT, buff=0.12)
            self.play(Transform(a1, vec(plane, S1, C1)), ReplacementTransform(l1, n1), run_time=1.4)
            self.play(Transform(a2, vec(plane, S2, C2)), ReplacementTransform(l2, n2), run_time=1.2)

        with self.beat("add"):
            shifted = vec(plane, B, C2, start=S1)
            self.play(Transform(a2, shifted), n2.animate.next_to(shifted.get_center(), RIGHT, buff=0.15), run_time=1.4)
            result = vec(plane, B, GREEN_K, width=8)
            dot = Dot(plane.c2p(*B), color=GREEN_K, radius=0.11)
            res = plate(tex(rf"A\,x=\begin{{bmatrix}}{B[0]}\\{B[1]}\end{{bmatrix}}", color=GREEN_K, size=Size.HEADLINE))
            slot(res, below=eq_plate)
            self.play(GrowArrow(result), FadeIn(dot, scale=1.6), run_time=1.2)
            self.play(FadeOut(weights, shift=UP * 0.1), FadeIn(res, shift=UP * 0.1), run_time=0.7)

        with self.beat("check"):
            rows = VGroup(
                tex(rf"\cB{{{A[0][0]}}}\cdot {X[0]}+\cO{{{A[0][1]}}}\cdot {X[1]}=\cG{{{B[0]}}}"),
                tex(rf"\cB{{{A[1][0]}}}\cdot {X[0]}+\cO{{{A[1][1]}}}\cdot {X[1]}=\cG{{{B[1]}}}"),
            ).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
            rows_plate = plate(rows)
            slot(rows_plate, below=eq_plate)  # the row arithmetic takes the result's place
            self.play(FadeOut(res, shift=UP * 0.1), FadeIn(rows_plate, shift=UP * 0.1), run_time=0.8)
            # each row's sum is one coordinate of the point the columns reached:
            # the sums fly from the arithmetic to the point and spell out its coordinates
            coord = tex(rf"({B[0]},\,{B[1]})", color=GREEN_K, size=Size.LABEL)  # glyphs: ( 8 , 7 )
            coord.next_to(dot, RIGHT, buff=0.2)
            frame = VGroup(coord[0], coord[2], coord[4])
            self.cue(spoken(B[0]))
            self.play(FadeIn(frame), TransformFromCopy(rows[0][-1], coord[1]), run_time=1.0)
            self.cue(spoken(B[1]))
            self.play(TransformFromCopy(rows[1][-1], coord[3]), Indicate(dot, color=GREEN_K, scale_factor=1.6),
                      run_time=1.0)
            self.remove(frame, *coord)  # animating slices leaves loose pieces; keep one clean object
            self.add(coord)

        with self.beat("takeaway"):
            final = plate(tex(r"A\,x = x_1\,\cB{a_1} + x_2\,\cO{a_2}", size=Size.HEADLINE + 4), opacity=0.95)
            slot(final)
            self.play(FadeOut(rows_plate), FadeOut(eq_plate), FadeOut(coord), run_time=0.5)
            self.play(FadeIn(final, shift=DOWN * 0.15), run_time=0.9)
            self.play(Circumscribe(final, color=GREEN_K, buff=0.08), run_time=1.2)

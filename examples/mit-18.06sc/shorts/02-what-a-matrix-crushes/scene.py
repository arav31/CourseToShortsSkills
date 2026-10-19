"""s02 What a matrix keeps and what it crushes (see storyboard.md).

The input space R^3 is drawn with a small orthographic projection of our own (no
ThreeDScene): the nullspace is a gridded floor, the row space a pole standing on it.
Every 3D object is rebuilt each frame from the view trackers, so the camera can tilt
edge-on and later shrink to make room for R^2 while labels keep their font size.
"""

from shortkit import *

BEATS = [
    ("hook", "This matrix eats three numbers and returns two. Some inputs vanish completely. Which ones, and how many?"),
    ("rank", "Subtract twice row one from row two: all zeros. One pivot, so the rank is one."),
    ("special", "Two special solutions, minus two, one, zero and minus two, zero, one, both go to zero."),
    ("plane", "So does every mix of them: a whole plane, the nullspace, of dimension three minus one, which is two."),
    ("row", "The row, one, two, two, has zero dot product with both, so the row space stands perpendicular to that plane."),
    ("split", "Take x equals minus one, three, two. It is the row plus the first special solution."),
    ("crush", "Apply A. The nullspace part is crushed to zero, and the row part lands on nine, eighteen. That is A x."),
    ("outputs", "Every output is a multiple of one, two: the column space. Its perpendicular, through two, minus one, is never reached."),
    ("count", "One kept plus two crushed makes three inputs. One reached plus one missed makes two outputs."),
    ("rule", "In general, rank r keeps r input directions and crushes n minus r."),
]

# ------------------------------------------------------------------ the worked example (computed)
A = np.array([[1, 2, 2], [2, 4, 4]])
M_OUT, N_IN = A.shape
MULT = A[1][0] // A[0][0]                      # 2: row 2 - 2 row 1
U = np.array([A[0], A[1] - MULT * A[0]])       # echelon form
assert not U[1].any()
RANK = int(np.linalg.matrix_rank(A))           # 1
ROW = A[0]                                     # the row space direction (1, 2, 2)
PIVOT = 0
FREE = [j for j in range(N_IN) if j != PIVOT]


def special(j):
    s = np.zeros(N_IN, dtype=int)
    s[j] = 1
    s[PIVOT] = -ROW[j] // ROW[PIVOT]
    return s


S1, S2 = special(FREE[0]), special(FREE[1])    # (-2, 1, 0), (-2, 0, 1)
assert not (A @ S1).any() and not (A @ S2).any()
DOT1, DOT2 = [ROW * s for s in (S1, S2)]       # termwise products; each sums to 0
assert DOT1.sum() == 0 and DOT2.sum() == 0
X = ROW + S1                                   # (-1, 3, 2)
AX = A @ X                                     # (9, 18)
assert (AX == A @ ROW).all()
COL = A[:, PIVOT]                              # (1, 2): every output is a multiple
LNULL = np.array([COL[1], -COL[0]])            # (2, -1)
assert not (A.T @ LNULL).any()
DIM_ROW, DIM_NULL, DIM_COL, DIM_LEFT = RANK, N_IN - RANK, RANK, M_OUT - RANK

# The narration is a literal list (render.py parses it), so check its numbers against the maths.
_WORDS = {-2: "minus two", -1: "minus one", 0: "zero", 1: "one", 2: "two", 3: "three", 9: "nine", 18: "eighteen"}


def spoken(v):
    return ", ".join(_WORDS[int(x)] for x in v)


_SAY = {k: v.lower() for k, v in BEATS}
assert f"eats {_WORDS[N_IN]} numbers and returns {_WORDS[M_OUT]}" in _SAY["hook"]
assert "rank is " + _WORDS[RANK] in _SAY["rank"]
assert spoken(S1) in _SAY["special"] and spoken(S2) in _SAY["special"]
assert f"{_WORDS[N_IN]} minus {_WORDS[RANK]}, which is {_WORDS[DIM_NULL]}" in _SAY["plane"]
assert spoken(ROW) in _SAY["row"]
assert spoken(X) in _SAY["split"]
assert spoken(AX) in _SAY["crush"]
assert spoken(COL) in _SAY["outputs"] and spoken(LNULL) in _SAY["outputs"]
assert f"{_WORDS[DIM_ROW]} kept plus {_WORDS[DIM_NULL]} crushed makes {_WORDS[N_IN]}" in _SAY["count"]
assert f"{_WORDS[DIM_COL]} reached plus {_WORDS[DIM_LEFT]} missed makes {_WORDS[M_OUT]}" in _SAY["count"]


def tup(v):
    return "(" + r",\,".join(str(int(x)) for x in v) + ")"


def bmat(rows, muted_row=None):
    body = []
    for i, row in enumerate(rows):
        cells = [str(int(x)) for x in row]
        if i == muted_row:
            cells = [rf"\cM{{{c}}}" for c in cells]
        body.append(" & ".join(cells))
    return r"\begin{bmatrix}" + r"\\".join(body) + r"\end{bmatrix}"


# ------------------------------------------------------------------ colours (series convention)
KEEP = BLUE_K       # input part A keeps: row space
CRUSH = RED_K       # crushed / never reached: nullspace, left nullspace
RES = GREEN_K       # results: outputs, column space
OP = YELLOW_K       # the operation: elimination, A itself
XC = INK            # the whole input x (its two parts carry the colours)

# ------------------------------------------------------------------ layout
BAND = Zone("band", -4.1, 4.1, 3.35, 4.8)              # equations during the input phase
BAND_L, BAND_R = BAND.cols(1, 2.3)
OUT_ZONE = Zone("out", -4.1, 4.1, -2.7, 0.95)          # R^2 during the output phase
OUT_X, OUT_Y = (-24, 27, 3), (-3, 21, 3)               # (9, 18) must fit; 3-unit grid
VIEW_BIG = dict(azimuth=40, elevation=32, scale=1.25, origin=(0.0, -0.6))
VIEW_SMALL = dict(scale=0.62, origin=(1.7, 2.6))

# ------------------------------------------------------------------ 3D -> screen projection
NH = ROW / np.linalg.norm(ROW)                         # unit normal of the nullspace plane
E1 = (S1 + S2) / np.linalg.norm(S1 + S2)               # orthonormal basis of the plane,
E2 = (S2 - S1) / np.linalg.norm(S2 - S1)               # chosen so (E1, E2, NH) is right-handed
assert np.allclose(np.cross(E1, E2), NH)
HALF = 2.2                                             # half-size of the floor patch


class View:
    """Orthographic camera looking down at the nullspace plane; NH is always screen-up."""

    def __init__(self, azimuth, elevation, scale, origin):
        self.az, self.el, self.k = ValueTracker(azimuth), ValueTracker(elevation), ValueTracker(scale)
        self.ox, self.oy = ValueTracker(origin[0]), ValueTracker(origin[1])

    def p(self, v):
        v = np.asarray(v, dtype=float)
        a, b, c = v @ E1, v @ E2, v @ NH
        f, e = np.radians(self.az.get_value()), np.radians(self.el.get_value())
        h = a * np.cos(f) + b * np.sin(f)                  # screen right
        d = -a * np.sin(f) + b * np.cos(f)                 # away from the viewer, in the plane
        k = self.k.get_value()
        return np.array([self.ox.get_value() + k * h, self.oy.get_value() + k * (c * np.cos(e) + d * np.sin(e)), 0.0])

    def to(self, azimuth=None, elevation=None, scale=None, origin=None):
        anims = []
        for tracker, value in ((self.az, azimuth), (self.el, elevation), (self.k, scale)):
            if value is not None:
                anims.append(tracker.animate.set_value(value))
        if origin is not None:
            anims += [self.ox.animate.set_value(origin[0]), self.oy.animate.set_value(origin[1])]
        return anims


def seg_arrow(a, b, color, width=7):
    if np.linalg.norm(b - a) < 0.04:  # degenerate: keep an invisible stub
        return Arrow(a, a + RIGHT * 0.05, buff=0, stroke_width=0).set_opacity(0)
    return Arrow(a, b, buff=0, color=color, stroke_width=width, max_tip_length_to_length_ratio=0.2,
                 max_stroke_width_to_length_ratio=12)


def pin(mob, point_fn, direction, buff=0.12):
    """Keep a label next to a projected point (it moves with the view, never scales)."""
    def upd(m):
        m.next_to(point_fn(), direction, buff=buff)
    upd(mob)
    mob.add_updater(upd)
    return mob


def background(mob):
    for m in mob.get_family():
        m._sk_background = True
    return mob


class Short(ShortScene):
    def construct(self):
        view = View(**VIEW_BIG)
        P = view.p
        T = ValueTracker(1.0)        # fraction of the nullspace part still attached to x
        SWEEP = ValueTracker(0.0)    # angle of the sample mix a s1 + b s2
        zero = np.zeros(3)

        def arrow3(start_fn, end_fn, color, width=7):
            return always_redraw(lambda: seg_arrow(P(start_fn()), P(end_fn()), color, width))

        def floor():
            corners = [HALF * (sa * E1 + sb * E2) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            patch = Polygon(*[P(c) for c in corners], stroke_color=CRUSH, stroke_width=2.5,
                            fill_color=CRUSH, fill_opacity=0.16)
            lines = VGroup()
            for g in np.linspace(-HALF, HALF, 7)[1:-1]:
                lines.add(Line(P(g * E1 - HALF * E2), P(g * E1 + HALF * E2)),
                          Line(P(-HALF * E1 + g * E2), P(HALF * E1 + g * E2)))
            lines.set_stroke(CRUSH, width=1.5, opacity=0.4)
            return background(VGroup(patch, lines))

        def right_angle(direction):
            u = np.asarray(direction, float) / np.linalg.norm(direction)
            d = 0.42
            pts = [P(d * u), P(d * u + d * NH), P(d * NH)]
            return VMobject().set_points_as_corners(pts).set_stroke(INK, width=3, opacity=0.9)

        # ---------------------------------------------------------------- hook
        with self.beat("hook"):
            big = Size.HEADLINE + 6
            mat = tex(bmat(A), size=big)
            xcol = tex(r"\cB{\begin{bmatrix}x_1\\x_2\\x_3\end{bmatrix}}", size=big)
            eq = tex("=", size=big)
            ycol = tex(r"\cG{\begin{bmatrix}y_1\\y_2\end{bmatrix}}", size=big)
            xcol.next_to(mat, RIGHT, buff=0.14)
            eq.next_to(xcol, RIGHT, buff=0.45)
            ycol.next_to(eq, RIGHT, buff=0.45)
            prod = VGroup(mat, xcol, eq, ycol).move_to(STAGE.point(0.5, 0.62))
            tag_y = prod.get_bottom()[1] - 0.4
            tag_in = text(f"{N_IN} inputs", size=Size.LABEL, color=KEEP)
            tag_in.move_to([xcol.get_center()[0], tag_y, 0])
            tag_out = text(f"{M_OUT} outputs", size=Size.LABEL, color=RES)
            tag_out.move_to([ycol.get_center()[0], tag_y, 0])
            self.title("What a matrix crushes", Write(prod), run_time=1.6)
            self.cue("three")
            self.play(FadeIn(tag_in, shift=UP * 0.15), run_time=0.5)
            self.cue("returns")
            self.play(FadeIn(tag_out, shift=UP * 0.15), run_time=0.5)
            zcol = tex(r"\cR{\begin{bmatrix}0\\0\end{bmatrix}}", size=big).move_to(ycol)
            self.cue("vanish", offset=-0.2)
            self.play(FadeTransform(ycol, zcol), run_time=0.7)
            qcol = tex(r"\cB{\begin{bmatrix}?\\?\\?\end{bmatrix}}", size=big).move_to(xcol)
            self.cue("which", offset=-0.1)
            self.play(FadeTransform(xcol, qcol), run_time=0.7)

        # ---------------------------------------------------------------- rank
        with self.beat("rank"):
            mat_target = mat.copy().scale(1.2).move_to(STAGE.point(0.5, 0.66))
            self.play(FadeOut(VGroup(qcol, eq, zcol, tag_in, tag_out)), Transform(mat, mat_target), run_time=0.8)
            ncols = A.shape[1]
            row2 = mat[1 + ncols: 1 + A.size]
            op = tex(r"\cY{\text{row 2}-" + str(MULT) + r"\times\text{row 1}}", size=Size.BODY)
            op.next_to(mat, DOWN, buff=0.45)
            self.play(FadeIn(op, shift=UP * 0.15), Indicate(row2, color=OP, scale_factor=1.15), run_time=0.9)
            u_tex = tex(bmat(U, muted_row=1), size=big).scale(1.2).move_to(mat)
            self.cue("zeros", offset=-0.3)
            self.play(*[ReplacementTransform(a_g, u_g) for a_g, u_g in zip(mat, u_tex)], run_time=1.0)
            self.remove(*u_tex.submobjects)
            self.add(u_tex)
            pivot_box = highlight(u_tex[1], color=OP, buff=0.08)
            rank_lbl = tex(rf"\text{{rank }} r=\cG{{{RANK}}}", size=Size.HEADLINE)
            rank_lbl.next_to(op, DOWN, buff=0.35)
            self.cue("pivot")
            self.play(Create(pivot_box), run_time=0.6)
            self.play(FadeIn(rank_lbl, shift=UP * 0.15), run_time=0.6)

        # ---------------------------------------------------------------- special solutions
        with self.beat("special"):
            reduced = VGroup(u_tex, pivot_box)
            small = reduced.copy().scale(Size.LABEL / big / 1.2).move_to(BAND_L.center)
            self.play(Transform(reduced, small), FadeOut(op), FadeOut(rank_lbl), run_time=0.9)
            s1 = arrow3(lambda: zero, lambda: S1, CRUSH, width=6)
            s2 = arrow3(lambda: zero, lambda: S2, CRUSH, width=6)
            l1 = pin(plate(tex(r"\cR{s_1}", size=Size.LABEL)), lambda: P(S1), DOWN + RIGHT * 0.3, buff=0.08)
            l2 = pin(plate(tex(r"\cR{s_2}", size=Size.LABEL)), lambda: P(S2), RIGHT, buff=0.1)
            eq1 = tex(rf"\cR{{s_1}}={tup(S1)}\ \cY{{\xrightarrow{{A}}}}\ \cG{{\mathbf{{0}}}}", size=Size.LABEL)
            eq2 = tex(rf"\cR{{s_2}}={tup(S2)}\ \cY{{\xrightarrow{{A}}}}\ \cG{{\mathbf{{0}}}}", size=Size.LABEL)
            eqs = VGroup(eq1, eq2).arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to(BAND_R.center)
            origin_dot = always_redraw(lambda: Dot(P(zero), radius=0.06, color=INK))
            self.add(origin_dot)
            self.cue("minus")
            self.play(GrowArrow(s1), FadeIn(l1), FadeIn(eq1, shift=LEFT * 0.2), run_time=1.1)
            self.cue("minus", nth=1)
            self.play(GrowArrow(s2), FadeIn(l2), FadeIn(eq2, shift=LEFT * 0.2), run_time=1.1)

        # ---------------------------------------------------------------- the whole plane
        with self.beat("plane"):
            plane3 = always_redraw(floor)
            plane3.set_z_index(-1)
            # a fixed screen gap left of the origin: clear of the floor's corner when big, of the pole when small
            null_lbl = pin(plate(text("nullspace", size=Size.LABEL, color=CRUSH)), lambda: P(zero) + LEFT * 0.35, LEFT, buff=0)
            span_eq = tex(r"A(a\,\cR{s_1}+b\,\cR{s_2})=\cG{\mathbf{0}}", size=Size.LABEL)
            dim_eq = tex(rf"\dim N(A)={N_IN}-{RANK}=\cR{{{DIM_NULL}}}", size=Size.LABEL)
            new_eqs = VGroup(span_eq, dim_eq).arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to(BAND_R.center)
            r_mix = 1.8
            start = np.arctan2(S1 @ E2, S1 @ E1)
            mix = arrow3(lambda: zero,
                         lambda: r_mix * (np.cos(start + SWEEP.get_value()) * E1 + np.sin(start + SWEEP.get_value()) * E2),
                         CRUSH, width=5)
            self.play(GrowFromPoint(plane3, P(zero)), FadeOut(eq1), run_time=1.3)
            self.play(GrowArrow(mix), FadeIn(span_eq), run_time=0.5)
            self.play(SWEEP.animate.set_value(TAU), run_time=2.4, rate_func=linear)
            self.play(FadeOut(mix), FadeIn(null_lbl), run_time=0.5)
            self.cue("three")
            self.play(FadeOut(eq2), run_time=0.3)
            self.play(FadeIn(dim_eq), run_time=0.5)

        # ---------------------------------------------------------------- the row space
        with self.beat("row"):
            pole = arrow3(lambda: zero, lambda: ROW, KEEP, width=8)
            row_lbl = pin(plate(tex(r"\cB{" + tup(ROW) + "}", size=Size.LABEL)), lambda: P(ROW), UP, buff=0.1)
            row1_glyphs = u_tex[1:1 + A.shape[1]]
            self.play(GrowArrow(pole), TransformFromCopy(row1_glyphs, row_lbl), run_time=1.2)
            row_lbl.resume_updating()
            dots = VGroup(*[
                tex(rf"\cB{{{tup(ROW)}}}\cdot\cR{{s_{i}}}=" + "+".join(str(int(t)) for t in d).replace("+-", "-") + "=0",
                    size=Size.LABEL)
                for i, d in ((1, DOT1), (2, DOT2))
            ]).arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to(BAND.center)
            self.play(FadeOut(reduced), FadeOut(new_eqs), run_time=0.4)
            self.play(FadeIn(dots, shift=UP * 0.1), run_time=0.7)
            ra = always_redraw(lambda: right_angle(S2))
            space_lbl = pin(plate(text("row space", size=Size.LABEL, color=KEEP)), lambda: P(0.55 * ROW), LEFT, buff=0.25)
            self.cue("perpendicular", offset=-0.8)
            self.play(Create(ra), FadeIn(space_lbl), run_time=0.6)
            self.play(*view.to(elevation=0, origin=(VIEW_BIG["origin"][0], VIEW_BIG["origin"][1] - 0.45)), run_time=1.8)

        # ---------------------------------------------------------------- split x
        with self.beat("split"):
            self.play(*view.to(elevation=VIEW_BIG["elevation"], origin=VIEW_BIG["origin"]), FadeOut(dots), run_time=1.0)
            x_arrow = arrow3(lambda: zero, lambda: ROW + T.get_value() * S1, XC, width=7)
            x_lbl = pin(plate(tex(r"\mathbf{x}", size=Size.HEADLINE)), lambda: P(ROW + T.get_value() * S1), RIGHT, buff=0.1)
            x_eq = tex(rf"\mathbf{{x}}={tup(X)}", size=Size.LABEL)
            x_eq2 = tex(rf"=\cB{{{tup(ROW)}}}+\cR{{{tup(S1)}}}", size=Size.LABEL)
            VGroup(x_eq, x_eq2).arrange(RIGHT, buff=0.15).move_to(BAND.center)
            self.play(GrowArrow(x_arrow), FadeIn(x_lbl), FadeIn(x_eq), run_time=1.1)
            top = arrow3(lambda: ROW, lambda: ROW + T.get_value() * S1, CRUSH, width=6)
            edge = always_redraw(lambda: DashedLine(P(T.get_value() * S1), P(ROW + T.get_value() * S1),
                                                    dash_length=0.12).set_stroke(MUTED, width=3))
            self.cue("row", offset=-0.2)
            self.play(Indicate(pole, color=KEEP, scale_factor=1.05), FadeIn(x_eq2[:8]), run_time=0.8)
            self.cue("plus")
            self.play(TransformFromCopy(s1, top), FadeIn(x_eq2[8:]), run_time=1.2)
            self.remove(*x_eq2.submobjects)
            self.add(x_eq2)
            self.play(Create(edge), run_time=0.5)

        # ---------------------------------------------------------------- apply A
        with self.beat("crush"):
            out = stage_plane(x_range=OUT_X, y_range=OUT_Y, zone=OUT_ZONE)
            o2 = out.c2p(0, 0)
            a_arrow = CurvedArrow(np.array([-2.3, 2.1, 0]), np.array([-2.3, 0.6, 0]), angle=TAU / 5, color=OP,
                                  stroke_width=6)
            a_lbl = plate(tex(r"\cY{A}", size=Size.HEADLINE)).next_to(a_arrow, LEFT, buff=0.12)
            self.play(FadeOut(x_eq), FadeOut(x_eq2), FadeOut(l1), FadeOut(l2), FadeOut(edge), run_time=0.4)
            self.play(*view.to(**VIEW_SMALL), run_time=1.0)
            self.play(Create(out, lag_ratio=0.02), Create(a_arrow), FadeIn(a_lbl), run_time=1.0)
            crushed = plane3.copy().clear_updaters()
            self.cue("crushed", offset=-0.5)
            self.play(T.animate.set_value(0.0),
                      Transform(crushed, Dot(o2, radius=0.11, color=CRUSH), path_arc=-TAU / 8), run_time=1.5)
            image = vec(out, tuple(AX), RES, width=7)
            carried = pole.copy().clear_updaters()
            self.cue("lands", offset=-0.3)
            self.play(FadeOut(x_arrow), FadeOut(x_lbl), FadeOut(top),
                      ReplacementTransform(carried, image, path_arc=TAU / 10), run_time=1.4)
            ax_lbl = plate(tex(rf"A\mathbf{{x}}=\cG{{{tup(AX)}}}", size=Size.LABEL)).next_to(out.c2p(*AX), RIGHT, buff=0.15)
            ax_dot = Dot(out.c2p(*AX), radius=0.08, color=RES)
            self.cue("that", offset=-0.1)
            self.play(FadeIn(ax_dot, scale=1.5), FadeIn(ax_lbl), run_time=0.6)

        # ---------------------------------------------------------------- outputs
        with self.beat("outputs"):
            def clipped_line(direction, color):
                d = np.asarray(direction, float)
                lo_hi = []
                for i, (lo, hi) in enumerate((OUT_X[:2], OUT_Y[:2])):
                    if d[i] != 0:
                        lo_hi.append(sorted([lo / d[i], hi / d[i]]))
                t_lo = max(a for a, _ in lo_hi)
                t_hi = min(b for _, b in lo_hi)
                return Line(out.c2p(*(t_lo * d)), out.c2p(*(t_hi * d)), color=color, stroke_width=5)

            col_line = clipped_line(COL, RES)
            col_lbl = plate(text("column space", size=Size.LABEL, color=RES)).next_to(out.c2p(*(5 * COL)), RIGHT, buff=0.25)
            left_line = clipped_line(LNULL, CRUSH)
            left_lbl = plate(text("left nullspace", size=Size.LABEL, color=CRUSH))
            t_edge = OUT_X[0] / LNULL[0]                      # where the line leaves the plane on the left
            left_lbl.next_to(out.c2p(*(t_edge * LNULL)), UP, buff=0.2).align_to(out, LEFT).shift(RIGHT * 0.1)
            u_c, u_l = COL / np.linalg.norm(COL), LNULL / np.linalg.norm(LNULL)
            s = 1.8
            ra_out = VMobject().set_points_as_corners([out.c2p(*(s * u_c)), out.c2p(*(s * u_c + s * u_l)),
                                                       out.c2p(*(s * u_l))]).set_stroke(INK, width=3)
            self.play(Create(col_line), run_time=1.0)
            scan = Dot(out.c2p(*AX), radius=0.08, color=RES)
            t_scan = ValueTracker(AX[0] / COL[0])
            scan.add_updater(lambda m: m.move_to(out.c2p(*(t_scan.get_value() * COL))))
            self.add(scan)
            self.play(t_scan.animate.set_value(-1), run_time=1.3)
            self.play(t_scan.animate.set_value(AX[0] / COL[0]), FadeIn(col_lbl), run_time=1.3)
            scan.clear_updaters()
            self.remove(scan)
            self.cue("perpendicular", offset=-0.2)
            self.play(Create(left_line), FadeIn(left_lbl), Create(ra_out), run_time=1.2)

        # ---------------------------------------------------------------- count
        with self.beat("count"):
            cnt_in = plate(tex(rf"\cB{{{DIM_ROW}}}+\cR{{{DIM_NULL}}}={N_IN}", size=Size.HEADLINE))
            cnt_in.move_to([0, 4.2, 0]).align_to(np.array([SAFE.left + 0.12, 0, 0]), LEFT)
            cnt_out = plate(tex(rf"\cG{{{DIM_COL}}}+\cR{{{DIM_LEFT}}}={M_OUT}", size=Size.HEADLINE))
            cnt_out.move_to([0, -1.55, 0]).align_to(np.array([SAFE.right - 0.12, 0, 0]), RIGHT)
            self.play(FadeIn(cnt_in, shift=DOWN * 0.15), Indicate(pole, color=KEEP, scale_factor=1.05), run_time=1.0)
            self.play(Indicate(plane3, color=CRUSH, scale_factor=1.03), run_time=0.8)
            self.cue("one", nth=1)
            self.play(FadeIn(cnt_out, shift=UP * 0.15), Indicate(col_line, color=RES, scale_factor=1.0), run_time=1.0)
            self.play(Indicate(left_line, color=CRUSH, scale_factor=1.0), run_time=0.8)

        # ---------------------------------------------------------------- rule
        with self.beat("rule"):
            rule_in = plate(tex(r"\cB{r}+\cR{(n-r)}=n", size=Size.LABEL)).move_to(cnt_in)
            rule_in.align_to(cnt_in, LEFT)
            rule_out = plate(tex(r"\cG{r}+\cR{(m-r)}=m", size=Size.LABEL)).move_to(cnt_out)
            rule_out.align_to(cnt_out, RIGHT)
            self.play(FadeTransform(cnt_in, rule_in), run_time=1.0)
            self.cue("crushes", offset=-0.2)
            self.play(FadeTransform(cnt_out, rule_out), run_time=1.0)

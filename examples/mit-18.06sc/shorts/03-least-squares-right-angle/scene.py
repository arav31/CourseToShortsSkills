"""s03: the best-fit line leaves a perpendicular error.

Two views of one least-squares fit of b = C + D t to (0, 6), (1, 0), (2, 0):
the t-b graph (vertical misses, sum of squares) and R3 (b, its shadow p on the
column-space plane, the error e at a right angle). See storyboard.md.
"""

from fractions import Fraction

from shortkit import *

BEATS = [
    ("hook", "Three points refuse to sit on one line. Which line fits best, and why does a right angle decide it?"),
    ("nofit", "Through the first point, the line needs C equals six. Then point two wants D equals minus six, and point three wants minus three."),
    ("misses", "So let it miss. Least squares tilts and slides the line until the squared vertical misses are as small as possible."),
    ("best", "It settles on five minus three t, missing by one, minus two and one. Squared, they add to six."),
    ("space", "Now stack the three heights into one arrow b, in three dimensions. The heights of every possible line fill a plane, spanned by the columns of A."),
    ("drop", "Straight below b sits the closest point, p: five, two, minus one, the best line's heights. The drop is the error e."),
    ("perp", "So e is perpendicular to both columns: one minus two plus one is zero, and zero minus two plus two is zero."),
    ("normal", "So A transpose e is zero. Write e as b minus A x hat, and out come the normal equations: A transpose A x hat equals A transpose b."),
    ("solve", "Here they give C equals five and D equals minus three: the same best line, found by a right angle."),
]

# ----------------------------------------------------------------- the numbers
TS = [0, 1, 2]
BS = [6, 0, 0]
A = [[1, t] for t in TS]                       # rows (1, t)
A1 = [row[0] for row in A]                     # column (1, 1, 1)
A2 = [row[1] for row in A]                     # column (0, 1, 2)
ATA = [[sum(A[k][i] * A[k][j] for k in range(3)) for j in range(2)] for i in range(2)]
ATB = [sum(A[k][i] * BS[k] for k in range(3)) for i in range(2)]
_det = Fraction(ATA[0][0] * ATA[1][1] - ATA[0][1] * ATA[1][0])
C_HAT = (ATA[1][1] * ATB[0] - ATA[0][1] * ATB[1]) / _det
D_HAT = (ATA[0][0] * ATB[1] - ATA[1][0] * ATB[0]) / _det
assert C_HAT.denominator == 1 and D_HAT.denominator == 1
C_HAT, D_HAT = int(C_HAT), int(D_HAT)                         # 5, -3
P = [C_HAT * A1[k] + D_HAT * A2[k] for k in range(3)]         # (5, 2, -1)
E = [BS[k] - P[k] for k in range(3)]                          # (1, -2, 1)
DOT1 = [A1[k] * E[k] for k in range(3)]
DOT2 = [A2[k] * E[k] for k in range(3)]
assert sum(DOT1) == 0 and sum(DOT2) == 0
C_EXACT = BS[0]                                               # t = 0 forces C = b at t = 0 = 6
D_TRY2 = Fraction(BS[1] - C_EXACT, TS[1])                     # -6
D_TRY3 = Fraction(BS[2] - C_EXACT, TS[2])                     # -3
D_TRY2, D_TRY3 = int(D_TRY2), int(D_TRY3)


def sse(c, d):
    return sum((BS[k] - (c + d * TS[k])) ** 2 for k in range(3))


SSE = sum(v * v for v in E)                                   # 6
SSE_TRY3 = sse(C_EXACT, D_TRY3)                               # 9
assert SSE == sse(C_HAT, D_HAT)


def signed(v):
    return f"{v}" if v < 0 else f"+{v}"


def terms(vals):
    """[1, -2, 1] -> '1-2+1' (typeset arithmetic)."""
    out = str(vals[0])
    for v in vals[1:]:
        out += f"-{-v}" if v < 0 else f"+{v}"
    return out


def col(vals):
    return r"\begin{bmatrix}" + r"\\".join(str(v) for v in vals) + r"\end{bmatrix}"


def mat(rows):
    return r"\begin{bmatrix}" + r"\\".join("&".join(str(v) for v in r) for r in rows) + r"\end{bmatrix}"


def tup(vals):
    return "(" + r",\,".join(str(v) for v in vals) + ")"


class MatchShapes(TransformMatchingShapes):
    """TransformMatchingShapes without save_state() in the shape key.

    Manim's key calls save_state() (a deep copy) on every glyph; shortkit glyphs carry an
    _sk_owner back-reference, so each copy drags in the whole owner tree including the
    previously saved states, and the cost grows ~5x per glyph (a 17-glyph equation hangs).
    """

    @staticmethod
    def get_mobject_key(mob):
        pts = mob.points - mob.get_center()
        h = mob.height if mob.height > 1e-6 else 1.0
        return hash(np.round(pts / h, 3).tobytes())


# ----------------------------------------------------------------- layout
T_RANGE = (-0.4, 2.6)
T_DRAW = (-0.05, 2.6)          # lines start at the b-axis so they never cross its tick labels
B_RANGE = (-3.0, 7.0)
TOP = Zone("top", STAGE.left, STAGE.right, 1.15, STAGE.top)
GRAPH_SMALL, EQ = TOP.cols(0.75, 1.25, gap=0.3)
SPACE3 = Zone("space3", STAGE.left, STAGE.right, STAGE.bottom, 0.9)

# ----------------------------------------------------------------- R3 camera
# Orthonormal frame: U1 along p, U2 the other in-plane direction, N_HAT along e (normal).
# The camera looks down at the column-space plane from ALPHA above it and can turn
# about the normal (CAM, degrees), so e always stands vertical on screen.
_np = np.array
_a1, _a2, _b, _p, _e = (_np(v, dtype=float) for v in (A1, A2, BS, P, E))
N_HAT = _e / np.linalg.norm(_e)
U1 = _p / np.linalg.norm(_p)
U2 = np.cross(N_HAT, U1)
ALPHA = np.radians(28)
PHI_MAIN, PHI_A1, PHI_A2 = 0.0, -51.0, -75.0   # a1 / a2 lie screen-horizontal at PHI_A1 / PHI_A2
C0 = 3.0 * U1 + 1.0 * U2                     # centre of the disc-shaped plane patch
R_DISC = 3.55
CAM = ValueTracker(PHI_MAIN)


def _cam(v, phi_deg):
    phi = np.radians(phi_deg)
    x, y, z = float(v @ U1), float(v @ U2), float(v @ N_HAT)
    X = x * np.cos(phi) - y * np.sin(phi)
    d = x * np.sin(phi) + y * np.cos(phi)
    return np.array([X, z * np.cos(ALPHA) + d * np.sin(ALPHA), 0.0])


def _fit_camera():
    pts = []
    keys = [np.zeros(3), _a1, _a2, _p, _b, _p + _a1, _p + _a2]
    for phi in np.linspace(PHI_A2, PHI_MAIN, 40):
        pts += [_cam(v - C0, phi) for v in keys]
    pts += [_np([s * R_DISC, t * R_DISC * np.sin(ALPHA), 0]) for s, t in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    lo, hi = np.min(pts, axis=0), np.max(pts, axis=0)
    lo -= _np([0.2, 0.25, 0]); hi += _np([0.2, 0.45, 0])         # room for tip labels
    scale = min(SPACE3.width / (hi[0] - lo[0]), SPACE3.height / (hi[1] - lo[1]))
    return scale, SPACE3.center - scale * (lo + hi) / 2


SCALE3, OFF3 = _fit_camera()


def P3(v):
    """Screen point of a vector in R3 under the current camera."""
    return OFF3 + SCALE3 * _cam(np.asarray(v, dtype=float) - C0, CAM.get_value())


def arrow3(start, end, color, width=7, opacity=1.0):
    start, end = np.asarray(start, float), np.asarray(end, float)
    return always_redraw(lambda: Arrow(
        P3(start), P3(end), buff=0, color=color, stroke_width=width, stroke_opacity=opacity,
        fill_opacity=opacity, max_tip_length_to_length_ratio=0.16, max_stroke_width_to_length_ratio=12))


def right_angle3(corner, d1, d2, size=0.42, color=YELLOW_K):
    d1 = np.asarray(d1, float) / np.linalg.norm(d1)
    d2 = np.asarray(d2, float) / np.linalg.norm(d2)
    c = np.asarray(corner, float)
    return always_redraw(lambda: VMobject(stroke_color=color, stroke_width=4).set_points_as_corners(
        [P3(c + size * d1), P3(c + size * (d1 + d2)), P3(c + size * d2)]))


def pin(mob, point_fn, direction, buff=0.1):
    """Keep a label next to a moving point."""
    mob.next_to(point_fn(), direction, buff=buff)
    mob.add_updater(lambda m: m.next_to(point_fn(), direction, buff=buff))
    return mob


def fresh(*mobs):
    """Run updaters now. An always_redraw object built under an older camera angle would
    otherwise be introduced (Create/FadeIn/ReplacementTransform suspend updaters) at stale geometry."""
    for m in mobs:
        m.update()
    return mobs


def lattice():
    """Faint lines of the plane: C a1 + D a2 with C or D an integer, clipped to the disc."""
    group = VGroup()
    for base, step in ((_a2, _a1), (_a1, _a2)):
        for k in range(-6, 8):
            w = k * base - C0
            a, bq, cq = step @ step, 2 * (w @ step), w @ w - R_DISC ** 2
            disc = bq * bq - 4 * a * cq
            if disc <= 0:
                continue
            s0, s1 = (-bq - np.sqrt(disc)) / (2 * a), (-bq + np.sqrt(disc)) / (2 * a)
            group.add(Line(P3(k * base + s0 * step), P3(k * base + s1 * step), stroke_color=GRID,
                           stroke_width=2))
    return group


class Short(ShortScene):
    def construct(self):
        # ------------------------------------------------------------ graph
        def make_axes(x_len, y_len):
            return Axes(x_range=(*T_RANGE, 1), y_range=(*B_RANGE, 1), x_length=x_len, y_length=y_len,
                        tips=False, axis_config={"stroke_color": MUTED, "stroke_width": 3,
                                                 "tick_size": 0.06})

        axes = make_axes(STAGE.width - 0.6, STAGE.height - 0.5)
        axes.move_to(STAGE.center + RIGHT * 0.15)
        ax = axes  # coordinate reference (swapped for the small graph later)

        def axis_labels(a, size=Size.LABEL, b_side=RIGHT):
            tl = tex("t", size=size, color=MUTED).next_to(a.c2p(T_RANGE[1], 0), UP + LEFT, buff=0.08)
            bl = tex("b", size=size, color=MUTED).next_to(a.c2p(0, B_RANGE[1]), b_side, buff=0.08)
            if b_side is not UP:
                bl.align_to(a.c2p(0, B_RANGE[1]), UP)
            return tl, bl

        t_lab, b_lab = axis_labels(axes)
        ticks = VGroup(
            *[tex(str(t), size=Size.SMALL, color=MUTED).next_to(axes.c2p(t, 0), DOWN, buff=0.14) for t in (1, 2)],
            *[tex(str(v), size=Size.SMALL, color=MUTED).next_to(axes.c2p(0, v), LEFT, buff=0.14) for v in (-2, 2, 4, 6)],
        )
        dots = VGroup(*[Dot(axes.c2p(t, v), radius=0.12, color=BLUE_K) for t, v in zip(TS, BS)])
        dots.set_z_index(4)

        Ct, Dt = ValueTracker(C_EXACT), ValueTracker(-1.0)

        def seg(a, c, d):
            lo, hi = T_DRAW
            b0, b1 = B_RANGE
            if abs(d) > 1e-9:
                ta, tb = (b0 - c) / d, (b1 - c) / d
                lo, hi = max(lo, min(ta, tb)), min(hi, max(ta, tb))
            return a.c2p(lo, c + d * lo), a.c2p(hi, c + d * hi)

        line = always_redraw(lambda: Line(*seg(ax, Ct.get_value(), Dt.get_value()), color=INK, stroke_width=6))

        # ------------------------------------------------------------ hook
        with self.beat("hook"):
            self.title("Best fit: a right angle", Create(axes), FadeIn(t_lab), FadeIn(b_lab), FadeIn(ticks),
                       LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.25), run_time=1.0)
            self.play(Create(line), run_time=0.6)
            self.play(Dt.animate.set_value(-4.6), run_time=2.4)

        # ------------------------------------------------------------ nofit
        corner = Zone("corner", axes.c2p(0.7, 0)[0], STAGE.right, axes.c2p(0, 4.0)[1], STAGE.top)
        eq0 = tex(r"b=C+D\,t", size=Size.LABEL)
        eq1 = tex(rf"C={C_EXACT}", size=Size.LABEL)
        eq2 = tex(rf"C+D=0\;\Rightarrow\;\cR{{D={D_TRY2}}}", size=Size.LABEL)
        eq3 = tex(rf"C+2D=0\;\Rightarrow\;\cR{{D={D_TRY3}}}", size=Size.LABEL)
        sys_eqs = VGroup(eq0, eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        corner.fit(sys_eqs, upscale=False, align="top")
        ring3 = Circle(radius=0.26, color=RED_K, stroke_width=5).move_to(dots[2])
        ring2 = Circle(radius=0.26, color=RED_K, stroke_width=5).move_to(dots[1])
        with self.beat("nofit"):
            self.play(FadeIn(eq0, shift=DOWN * 0.1), run_time=0.6)
            self.cue("needs")
            self.play(FadeIn(eq1, shift=DOWN * 0.1), Indicate(dots[0], color=BLUE_K, scale_factor=1.6), run_time=0.9)
            self.cue("two")
            self.play(Dt.animate.set_value(D_TRY2), run_time=0.9)
            self.play(FadeIn(eq2, shift=DOWN * 0.1), Create(ring3), run_time=0.7)
            self.cue("three")
            self.play(Dt.animate.set_value(D_TRY3), FadeOut(ring3), run_time=0.9)
            self.play(FadeIn(eq3, shift=DOWN * 0.1), Create(ring2), run_time=0.7)

        # ------------------------------------------------------------ misses
        K = 3.0 / max(SSE_TRY3, sse(6, -4))       # meter units per squared unit

        def bar(i):
            return always_redraw(lambda: Line(
                ax.c2p(TS[i], BS[i]), ax.c2p(TS[i], Ct.get_value() + Dt.get_value() * TS[i]),
                color=RED_K, stroke_width=7))

        bars = VGroup(*[bar(i) for i in range(3)])
        meter_lab = tex(r"\cR{e_1^2+e_2^2+e_3^2}", size=Size.LABEL)
        meter_lab.move_to(corner.point(0.0, 1.0), aligned_edge=UP + LEFT).shift(RIGHT * 0.1 + DOWN * 0.1)
        meter_anchor = meter_lab.get_corner(DL) + DOWN * 0.45

        def meter_bar():
            c, d = Ct.get_value(), Dt.get_value()
            parts, x = VGroup(), 0.0
            for k in range(3):
                w = max(K * (BS[k] - (c + d * TS[k])) ** 2, 1e-3)
                r = Rectangle(width=w, height=0.3, stroke_color=BG, stroke_width=2,
                              fill_color=RED_K, fill_opacity=0.9)
                r.move_to(meter_anchor + RIGHT * (x + w / 2))
                parts.add(r)
                x += w
            return parts

        meter = always_redraw(meter_bar)
        pivot = (TS[1], C_HAT + D_HAT * TS[1])   # the line pivots about its middle height
        with self.beat("misses"):
            self.play(FadeOut(sys_eqs), FadeOut(ring2), FadeOut(ticks), run_time=0.5)
            self.play(*[Create(b) for b in bars], FadeIn(meter_lab), FadeIn(meter), run_time=0.7)
            self.play(Ct.animate.set_value(C_HAT), Dt.animate.set_value(D_HAT), run_time=1.3)
            for d in (D_HAT - 1, D_HAT + 1, D_HAT):
                c = pivot[1] - d * pivot[0]
                self.play(Ct.animate.set_value(c), Dt.animate.set_value(d), run_time=0.9)

        # ------------------------------------------------------------ best
        with self.beat("best"):
            for m in (line, *bars, meter):
                m.clear_updaters()
            line_lab = tex(rf"b={C_HAT}{D_HAT}t", size=Size.LABEL, color=GREEN_K)
            line_lab.next_to(axes.c2p(0.55, C_HAT + D_HAT * 0.55), UP + RIGHT, buff=0.12)
            sides = [RIGHT if (BS[k] - P[k]) > 0 else LEFT for k in range(3)]  # away from the falling line
            bar_labs = VGroup(*[
                tex(signed(E[k]), size=Size.LABEL, color=RED_K).next_to(
                    axes.c2p(TS[k], (BS[k] + P[k]) / 2), sides[k], buff=0.14)
                for k in range(3)])
            seg_labs = VGroup(*[
                tex(str(E[k] ** 2), size=Size.SMALL, color=RED_K).next_to(meter[k], DOWN, buff=0.12)
                for k in range(3)])
            total = tex(rf"={SSE}", size=Size.LABEL, color=INK).next_to(meter, RIGHT, buff=0.15)
            self.play(line.animate.set_color(GREEN_K), FadeIn(line_lab, shift=UP * 0.1), run_time=0.8)
            self.play(LaggedStart(*[FadeIn(b) for b in bar_labs], lag_ratio=0.3), run_time=1.0)
            self.play(FadeIn(seg_labs), FadeIn(total, shift=LEFT * 0.1), run_time=0.8)

        # ------------------------------------------------------------ space
        small = make_axes(STAGE.width - 0.6, STAGE.height - 0.5)
        GRAPH_SMALL.fit(small, buff=0.15)
        small.align_to(_np([GRAPH_SMALL.left + 0.3, 0, 0]), LEFT)
        dots_s = VGroup(*[Dot(small.c2p(t, v), radius=0.09, color=BLUE_K) for t, v in zip(TS, BS)]).set_z_index(4)
        line_s = Line(*seg(small, C_HAT, D_HAT), color=GREEN_K, stroke_width=5)
        bars_s = VGroup(*[Line(small.c2p(TS[k], BS[k]), small.c2p(TS[k], P[k]), color=RED_K, stroke_width=5)
                          for k in range(3)])
        t_lab_s, b_lab_s = axis_labels(small, size=Size.SMALL, b_side=UP)
        line_lab_s = tex(rf"b={C_HAT}{D_HAT}t", size=Size.SMALL, color=GREEN_K)
        line_lab_s.move_to(small.c2p(T_RANGE[1], 6.6), aligned_edge=UR)
        heights = VGroup(*[tex(str(BS[k]), size=Size.SMALL, color=BLUE_K) for k in range(3)])
        for k, h in enumerate(heights):
            h.next_to(dots_s[k], LEFT if k == 0 else UP + LEFT, buff=0.08)

        def eq_slot(mob, row):
            """Rows of the equation column, left-aligned, top-down."""
            EQ.fit(mob, upscale=False)
            y = EQ.top - 0.1 - row * 0.78
            return mob.move_to(_np([EQ.left + 0.05, y, 0]), aligned_edge=UL)

        b_row = eq_slot(tex(rf"\cB{{b}}={tup(BS)}", size=Size.BODY), 0)
        combo_row = eq_slot(tex(rf"C\,\cB{{{tup(A1)}}}+D\,\cB{{{tup(A2)}}}", size=Size.BODY), 1)

        disc = Ellipse(width=2 * R_DISC * SCALE3, height=2 * R_DISC * np.sin(ALPHA) * SCALE3,
                       stroke_color=MUTED, stroke_width=2, fill_color=BLUE_K, fill_opacity=0.08).move_to(OFF3)
        grid = always_redraw(lattice)
        O3 = np.zeros(3)
        origin = always_redraw(lambda: Dot(P3(O3), radius=0.07, color=INK))
        b_arrow = arrow3(O3, _b, BLUE_K, width=8)
        a1_arrow = arrow3(O3, _a1, BLUE_K)
        a2_arrow = arrow3(O3, _a2, BLUE_K)
        b_tag = pin(tex(r"b", size=Size.LABEL, color=BLUE_K), lambda: P3(_b), UP, buff=0.12)
        a1_tag = pin(tex(r"a_1", size=Size.SMALL, color=BLUE_K), lambda: P3(_a1), UP, buff=0.08)
        a2_tag = pin(tex(r"a_2", size=Size.SMALL, color=BLUE_K), lambda: P3(_a2), LEFT, buff=0.16)

        Cp, Dp = ValueTracker(2.0), ValueTracker(0.0)      # a probe line and its point in the plane
        probe_line = always_redraw(lambda: Line(*seg(small, Cp.get_value(), Dp.get_value()), color=INK, stroke_width=4))
        probe_dot = always_redraw(lambda: Dot(P3(Cp.get_value() * _a1 + Dp.get_value() * _a2), radius=0.09, color=INK))
        PROBE_PATH = [(4.0, -1.0), (3.0, -2.0), (2.0, 0.0)]

        with self.beat("space"):
            self.play(FadeOut(VGroup(bar_labs, seg_labs, total, meter, meter_lab)), run_time=0.4)
            self.play(Transform(axes, small), Transform(dots, dots_s), Transform(line, line_s),
                      Transform(bars, bars_s), Transform(t_lab, t_lab_s), Transform(b_lab, b_lab_s),
                      Transform(line_lab, line_lab_s), run_time=1.0)
            ax = small
            self.play(FadeIn(heights, shift=LEFT * 0.05), run_time=0.4)
            self.play(MatchShapes(heights, b_row), FadeIn(origin), GrowArrow(b_arrow), FadeIn(b_tag), run_time=1.1)
            self.cue("every")
            self.play(Write(combo_row), run_time=0.8)
            self.cue("plane")
            self.play(FadeIn(disc), FadeIn(grid), GrowArrow(a1_arrow), GrowArrow(a2_arrow), FadeIn(a1_tag),
                      FadeIn(a2_tag), run_time=1.0)
            self.play(FadeIn(probe_line), FadeIn(probe_dot), run_time=0.3)
            for c, d in PROBE_PATH:
                self.play(Cp.animate.set_value(c), Dp.animate.set_value(d), run_time=0.6)
            self.play(FadeOut(probe_line), FadeOut(probe_dot), run_time=0.3)

        # ------------------------------------------------------------ drop
        p_arrow = arrow3(O3, _p, GREEN_K, width=8)
        e_arrow = arrow3(_p, _b, RED_K, width=8)
        plumb = DashedLine(P3(_b), P3(_p), color=YELLOW_K, stroke_width=4, dash_length=0.12)
        foot = Dot(P3(_b), radius=0.08, color=YELLOW_K)
        mark_p = right_angle3(_p, -_p, _e)
        p_tag = pin(tex(r"p", size=Size.LABEL, color=GREEN_K), lambda: P3(_p), DOWN, buff=0.12)
        e_tag = pin(tex(r"e", size=Size.LABEL, color=RED_K), lambda: P3((_p + _b) / 2), RIGHT, buff=0.15)
        green_pts = VGroup(*[Dot(small.c2p(TS[k], P[k]), radius=0.08, color=GREEN_K) for k in range(3)]).set_z_index(5)
        p_row = eq_slot(tex(rf"\cG{{p}}={tup(P)}", size=Size.BODY), 1)
        e_row = eq_slot(tex(rf"\cR{{e}}=\cB{{b}}-\cG{{p}}={tup(E)}", size=Size.BODY), 2)
        with self.beat("drop"):
            self.play(Create(plumb), foot.animate.move_to(P3(_p)), run_time=1.0)
            self.cue("five")
            self.play(GrowArrow(p_arrow), FadeIn(p_tag), FadeTransform(combo_row, p_row), run_time=1.0)
            self.cue("heights")
            self.play(FadeIn(green_pts, scale=1.5), run_time=0.7)
            self.cue("drop")
            self.play(FadeOut(plumb), FadeOut(foot), GrowArrow(e_arrow), FadeIn(e_tag), Create(mark_p),
                      FadeIn(e_row, shift=DOWN * 0.1), run_time=1.0)

        # ------------------------------------------------------------ perp
        a1_at_p = arrow3(_p, _p + _a1, BLUE_K)
        a2_at_p = arrow3(_p, _p + _a2, BLUE_K)
        a1_tag_p = pin(tex(r"a_1", size=Size.SMALL, color=BLUE_K), lambda: P3(_p + _a1), DOWN, buff=0.1)
        a2_tag_p = pin(tex(r"a_2", size=Size.SMALL, color=BLUE_K), lambda: P3(_p + _a2), UP + RIGHT, buff=0.06)
        mark_1 = right_angle3(_p, _a1, _e, size=0.45)
        mark_2 = right_angle3(_p, _a2, _e, size=0.45)
        dot1 = eq_slot(tex(rf"\cB{{a_1}}\cdot\cR{{e}}={terms(DOT1)}=0", size=Size.BODY), 1)
        dot2 = eq_slot(tex(rf"\cB{{a_2}}\cdot\cR{{e}}={terms(DOT2)}=0", size=Size.BODY), 2)
        e_row_top = eq_slot(tex(rf"\cR{{e}}=\cB{{b}}-\cG{{p}}={tup(E)}", size=Size.BODY), 0)
        with self.beat("perp"):
            self.play(FadeOut(VGroup(b_row, p_row)), FadeOut(a1_tag), FadeOut(a2_tag), FadeOut(mark_p), run_time=0.4)
            self.play(CAM.animate.set_value(PHI_A1), Transform(e_row, e_row_top), run_time=1.0)
            fresh(a1_at_p, a2_at_p, a1_tag_p, a2_tag_p, mark_1, mark_2)   # built at the old camera angle
            self.play(ReplacementTransform(a1_arrow, a1_at_p), ReplacementTransform(a2_arrow, a2_at_p), run_time=0.7)
            self.play(FadeIn(a1_tag_p), FadeIn(a2_tag_p), run_time=0.3)
            self.cue("one")
            self.play(Create(mark_1), Write(dot1), run_time=1.0)
            self.cue("zero", nth=1)
            self.play(CAM.animate.set_value(PHI_A2), run_time=1.0)
            fresh(mark_2)
            self.play(Create(mark_2), FadeOut(mark_1), Write(dot2), run_time=0.9)

        # ------------------------------------------------------------ normal
        a1_home = arrow3(O3, _a1, BLUE_K)
        a2_home = arrow3(O3, _a2, BLUE_K)
        at_e = eq_slot(tex(r"A^{\mathsf T}\cR{e}=0", size=Size.BODY), 0)
        at_bax = eq_slot(tex(r"A^{\mathsf T}(\cB{b}-A\cG{\hat x})=0", size=Size.BODY), 0)
        normal_eq = eq_slot(tex(r"A^{\mathsf T}\!A\,\cG{\hat x}=A^{\mathsf T}\cB{b}", size=Size.HEADLINE), 0)
        normal_eq.shift(RIGHT * 0.1 + DOWN * 0.08)
        normal_box = SurroundingRectangle(normal_eq, color=GREEN_K, buff=0.12, corner_radius=0.08, stroke_width=4)
        with self.beat("normal"):
            fresh(a1_home, a2_home)
            self.play(FadeTransform(VGroup(e_row, dot1, dot2), at_e), FadeOut(mark_2), FadeOut(a1_tag_p),
                      FadeOut(a2_tag_p), ReplacementTransform(a1_at_p, a1_home),
                      ReplacementTransform(a2_at_p, a2_home), run_time=1.0)
            self.cue("write")
            self.play(MatchShapes(at_e, at_bax), CAM.animate.set_value(PHI_MAIN), run_time=1.4)
            a1_tag_home = pin(tex(r"a_1", size=Size.SMALL, color=BLUE_K), lambda: P3(_a1), UP, buff=0.08)
            a2_tag_home = pin(tex(r"a_2", size=Size.SMALL, color=BLUE_K), lambda: P3(_a2), LEFT, buff=0.16)
            fresh(mark_p)
            self.play(Create(mark_p), FadeIn(a1_tag_home), FadeIn(a2_tag_home), run_time=0.5)
            self.cue("normal")
            self.play(MatchShapes(at_bax, normal_eq), run_time=1.1)
            self.play(Create(normal_box), run_time=0.6)

        # ------------------------------------------------------------ solve
        numeric = tex(rf"{mat(ATA)}\cG{{\hat x}}=\cB{{{col(ATB)}}}", size=Size.BODY)
        numeric.next_to(normal_box, DOWN, buff=0.22).align_to(normal_box, LEFT)
        sol = tex(rf"\cG{{\hat x}}=(C,\,D)=(\cG{{{C_HAT}}},\,\cG{{{D_HAT}}})", size=Size.BODY)
        EQ.fit(sol, upscale=False)
        sol.next_to(numeric, DOWN, buff=0.22).align_to(normal_box, LEFT)
        with self.beat("solve"):
            self.play(FadeIn(numeric, shift=DOWN * 0.1), run_time=0.8)
            self.cue("five")
            self.play(FadeIn(sol, shift=DOWN * 0.1), run_time=0.8)
            self.cue("same")
            self.play(Indicate(line, color=GREEN_K, scale_factor=1.06), Indicate(line_lab, color=GREEN_K),
                      Indicate(p_arrow, color=GREEN_K, scale_factor=1.04), run_time=1.3)

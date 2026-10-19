"""s05: every matrix turns a circle into an ellipse (the SVD).

Storyboard: see storyboard.md. The input panel (unit circle, a perpendicular pair v1, v2) sits
top-left, the equation column top-right, the output panel (the image ellipse, A v1, A v2) fills
the bottom of the stage. The pair turns until its images are perpendicular too.
"""

import shortkit as _sk
from shortkit import *

BEATS = [
    ("hook", "Feed a matrix every arrow on a circle. However messy the matrix, out comes a clean ellipse. Why?"),
    ("axes", "Take A with rows six, eight and minus four, three. The two axis arrows land on its columns."),
    ("skew", "Those images are no longer perpendicular: their dot product is forty eight minus twelve, thirty six."),
    ("turn", "Now turn the pair. A quarter turn swaps their roles, so the dot product flips to minus thirty six."),
    ("zero", "So somewhere in between it is zero, for any matrix at all. Here that happens at v one equals point six, point eight."),
    ("land", "Their images, ten, zero and zero, five, are perpendicular too: the long and short axes of the ellipse."),
    ("why", "Any arrow on the circle is a mix of v one and v two, so its image is the same mix of the two axes. That traces an ellipse."),
    ("reveal", "Ten and five are the singular values, and in matrix form this is the singular value decomposition: A equals U Sigma V transpose."),
]

# ---------------------------------------------------------------- the numbers (all computed)
A = np.array([[6.0, 8.0], [-4.0, 3.0]])
E1, E2 = np.array([1.0, 0.0]), np.array([0.0, 1.0])
AE1, AE2 = A @ E1, A @ E2                       # (6, -4), (8, 3): A's columns
DOT_PARTS = (AE1[0] * AE2[0], AE1[1] * AE2[1])  # 48, -12
DOT_AXES = AE1 @ AE2                            # 36
V1 = np.array([0.6, 0.8])
V2 = np.array([-0.8, 0.6])
AV1, AV2 = A @ V1, A @ V2                       # (10, 0), (0, 5)
SIG1, SIG2 = np.linalg.norm(AV1), np.linalg.norm(AV2)
U1, U2 = AV1 / SIG1, AV2 / SIG2
THETA_STAR = np.arctan2(V1[1], V1[0])           # 53.13 degrees
U_M = np.column_stack([U1, U2])
S_M = np.diag([SIG1, SIG2])
VT_M = np.vstack([V1, V2])


def pair(th: float):
    """The perpendicular pair at angle th: v1 = (cos th, sin th), v2 = v1 turned a quarter."""
    p = np.array([np.cos(th), np.sin(th)])
    return p, np.array([-p[1], p[0]])


def image_dot(th: float) -> float:
    p, q = pair(th)
    return float((A @ p) @ (A @ q))


assert abs(V1 @ V2) < 1e-12 and np.allclose([np.linalg.norm(V1), np.linalg.norm(V2)], 1)
assert abs(AV1 @ AV2) < 1e-9 and np.allclose(U_M @ S_M @ VT_M, A)
assert np.allclose(pair(THETA_STAR)[1], V2)
assert np.allclose(sorted(np.linalg.eigvalsh(A.T @ A)), [SIG2 ** 2, SIG1 ** 2])
assert np.isclose(abs(np.linalg.det(A)), SIG1 * SIG2)
assert np.isclose(image_dot(PI / 2), -DOT_AXES)  # a quarter turn flips the sign

# ---------------------------------------------------------------- narration says the same numbers
_WORDS = {0: "zero", 3: "three", 4: "four", 5: "five", 6: "six", 8: "eight", 10: "ten",
          12: "twelve", 36: "thirty six", 48: "forty eight"}


def say(x) -> str:
    x = round(float(x), 6)
    if x.is_integer():
        return ("minus " if x < 0 else "") + _WORDS[int(abs(x))]
    assert 0 < abs(x) < 1 and len(f"{abs(x):g}") == 3
    return ("minus " if x < 0 else "") + "point " + _WORDS[int(f"{abs(x):g}"[-1])]


_N = dict(BEATS)
assert f"rows {say(A[0, 0])}, {say(A[0, 1])} and {say(A[1, 0])}, {say(A[1, 1])}" in _N["axes"]
assert f"{say(DOT_PARTS[0])} minus {say(-DOT_PARTS[1])}, {say(DOT_AXES)}" in _N["skew"]
assert f"flips to {say(image_dot(PI / 2))}" in _N["turn"]
assert f"v one equals {say(V1[0])}, {say(V1[1])}" in _N["zero"]
assert f"{say(AV1[0])}, {say(AV1[1])} and {say(AV2[0])}, {say(AV2[1])}" in _N["land"]
assert _N["reveal"].startswith(f"{say(SIG1).capitalize()} and {say(SIG2)} are the singular values")


def fmt(x) -> str:
    x = round(float(x), 6) + 0.0  # no "-0"
    return f"{x:g}"


def tup(v) -> str:
    return rf"({fmt(v[0])},\,{fmt(v[1])})"


def bm(M) -> str:
    return r"\begin{bmatrix}" + r"\\".join("&".join(fmt(x) for x in row) for row in M) + r"\end{bmatrix}"


DOT_RANGE = range(-40, 41)  # covers the sweep (max |dot| on [0, 90 deg] is 37.5)
assert max(abs(image_dot(t)) for t in np.linspace(0, PI / 2, 400)) < 40

# ---------------------------------------------------------------- layout
IN_Z = Zone("in", -4.1, -0.6, 1.45, 4.8)      # unit circle panel
EQ_Z = Zone("eq", -0.4, 4.1, 1.45, 4.8)       # equation column
OUT_Z = Zone("out", -4.1, 4.1, -2.7, 1.25)    # ellipse panel
TOP_BAND = Zone("band", -4.1, 4.1, 1.45, 4.8)  # reveal formulas, once the input panel leaves


def corner(plane, d1, d2, size, color, width=4):
    """Right-angle marker at the origin, sides along screen directions d1, d2 (unit vectors)."""
    o = plane.c2p(0, 0)
    d1 = np.array([d1[0], d1[1], 0.0])
    d2 = np.array([d2[0], d2[1], 0.0])
    m = VMobject(stroke_color=color, stroke_width=width)
    m.set_points_as_corners([o + size * d1, o + size * (d1 + d2), o + size * d2])
    return m


def dline(a, b, dash):
    """Dashed segment; nothing when it is too short to draw."""
    if np.linalg.norm(np.asarray(a) - np.asarray(b)) < 0.03:
        return VMobject()
    return DashedLine(a, b, color=INK, stroke_width=3, dash_length=dash)


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def red_to_green(alpha):
    return interpolate_color(ManimColor(RED_K), ManimColor(GREEN_K), alpha)


class Short(ShortScene):
    def construct(self):
        top = stage_plane((-1.4, 1.4, 0.5), (-1.4, 1.4, 0.5), zone=IN_Z)
        bot = stage_plane((-10.8, 10.8, 1), (-5.4, 5.4, 1), zone=OUT_Z)
        ts = (0, TAU, TAU / 160)
        circle = ParametricFunction(lambda t: top.c2p(np.cos(t), np.sin(t)), t_range=ts,
                                    color=BLUE_K, stroke_width=5)
        ellipse = ParametricFunction(lambda t: bot.c2p(*(A @ np.array([np.cos(t), np.sin(t)]))), t_range=ts,
                                     color=GREEN_K, stroke_width=5)
        ellipse.set_stroke(opacity=0.75)

        # live readout numbers, compiled in one LaTeX run (tex() then hits the cache)
        _sk._compile_tex([_sk._tex_body(str(k), True) for k in DOT_RANGE])
        nums = {k: tex(str(k), size=Size.BODY) for k in DOT_RANGE}

        theta = ValueTracker(0.0)   # angle of v1
        lock = ValueTracker(0.0)    # 0: images skewed (red), 1: images perpendicular (green)
        col_left = EQ_Z.left + 0.1

        # ------------------------------------------------------------ hook
        with self.beat("hook"):
            angles = [k * TAU / 16 for k in range(16)]
            spokes = VGroup(*[vec(top, (np.cos(a), np.sin(a)), BLUE_K, width=3) for a in angles]).set_opacity(0.8)
            img_spokes = VGroup(*[vec(bot, A @ np.array([np.cos(a), np.sin(a)]), GREEN_K, width=3)
                                  for a in angles]).set_opacity(0.8)
            a_mat = tex(rf"\cY{{{bm(A)}}}", size=Size.BODY)
            a_eq = VGroup(tex(r"\cY{A} =", size=Size.BODY), a_mat).arrange(RIGHT, buff=0.15)
            a_eq.move_to([col_left, EQ_Z.top - 0.1, 0], aligned_edge=UP + LEFT)
            # entries of A: glyphs shorter than the brackets, sorted into rows and columns by position
            entries = [g for g in a_mat.submobjects if g.height < 0.6 * a_mat.height]
            cy, cx = a_mat.get_center()[1], a_mat.get_center()[0]
            a_rows = [VGroup(*[g for g in entries if (g.get_center()[1] > cy) == up]) for up in (True, False)]
            a_cols = [VGroup(*[g for g in entries if (g.get_center()[0] < cx) == left]) for left in (True, False)]
            self.title("Circle in, ellipse out", FadeIn(top), Create(circle), FadeIn(a_eq),
                       LaggedStart(*[GrowArrow(s) for s in spokes], lag_ratio=0.04), run_time=1.6)
            self.play(FadeIn(bot), run_time=0.6)
            self.cue("messy")
            self.play(ReplacementTransform(VGroup(circle.copy(), spokes.copy()), VGroup(ellipse, img_spokes)),
                      run_time=2.4)

        # ------------------------------------------------------------ axes
        with self.beat("axes"):
            in_pair = always_redraw(lambda: VGroup(
                vec(top, pair(theta.get_value())[0], BLUE_K),
                vec(top, pair(theta.get_value())[1], BLUE_K),
                corner(top, *pair(theta.get_value()), 0.2, BLUE_K),
            ))
            lv1 = plate(tex(r"v_1", color=BLUE_K, size=Size.BODY), buff=0.05)
            lv2 = plate(tex(r"v_2", color=BLUE_K, size=Size.BODY), buff=0.05)
            lv1.add_updater(lambda m: m.move_to(top.c2p(*(1.3 * pair(theta.get_value())[0]))))
            lv2.add_updater(lambda m: m.move_to(top.c2p(*(1.3 * pair(theta.get_value())[1]))))
            static_imgs = VGroup(vec(bot, AE1, RED_K), vec(bot, AE2, RED_K))
            le1 = plate(tex(tup(AE1), color=RED_K, size=Size.LABEL)).next_to(bot.c2p(*AE1), DR, buff=0.02)
            le2 = plate(tex(tup(AE2), color=RED_K, size=Size.LABEL)).next_to(bot.c2p(*AE2), UR, buff=0.02)
            row_box = [highlight(r, buff=0.07) for r in a_rows]
            col_box = [highlight(c, color=RED_K, buff=0.07) for c in a_cols]
            self.play(FadeOut(spokes), FadeOut(img_spokes), run_time=0.6)
            self.cue("six")
            self.play(Create(row_box[0]), run_time=0.5)
            self.cue("minus")
            self.play(ReplacementTransform(row_box[0], row_box[1]), run_time=0.5)
            self.cue("two")
            self.play(FadeOut(row_box[1]), FadeIn(in_pair), FadeIn(lv1), FadeIn(lv2), run_time=0.7)
            self.cue("land")
            self.play(TransformFromCopy(in_pair[0], static_imgs[0]), TransformFromCopy(in_pair[1], static_imgs[1]),
                      run_time=1.3)
            self.cue("columns")
            self.play(Create(col_box[0]), Create(col_box[1]), FadeIn(le1), FadeIn(le2), run_time=0.7)

        # ------------------------------------------------------------ skew
        with self.beat("skew"):
            def img_marks():
                p, q = pair(theta.get_value())
                w1, w2 = A @ p, A @ q
                a1, a2 = np.arctan2(w1[1], w1[0]), np.arctan2(w2[1], w2[0])
                d = (a2 - a1 + PI) % TAU - PI
                arc = Arc(radius=0.55, start_angle=a1, angle=d, arc_center=bot.c2p(0, 0),
                          color=RED_K, stroke_width=5)
                arc.set_stroke(opacity=1 - lock.get_value())
                mark = corner(bot, unit(w1), unit(w2), 0.3, GREEN_K, width=5)
                mark.set_stroke(opacity=lock.get_value())
                return VGroup(arc, mark)

            marks = always_redraw(img_marks)
            rd1 = tex(r"\cY{A}\cB{v_1}\cdot\cY{A}\cB{v_2}", size=Size.BODY)
            rd1.next_to(a_eq, DOWN, buff=0.45).align_to(a_eq, LEFT)
            sign = "-" if DOT_PARTS[1] < 0 else "+"
            rd2 = tex(rf"= {fmt(DOT_PARTS[0])} {sign} {fmt(abs(DOT_PARTS[1]))} = \cR{{{fmt(DOT_AXES)}}}",
                      size=Size.BODY)
            rd2.next_to(rd1, DOWN, buff=0.25).align_to(rd1, LEFT)
            self.cue("perpendicular")
            self.play(Create(marks), FadeOut(col_box[0]), FadeOut(col_box[1]), run_time=0.8)
            self.cue("dot")
            self.play(Write(rd1), run_time=0.9)
            self.cue("forty")
            self.play(Write(rd2), run_time=1.6)

        # ------------------------------------------------------------ turn
        with self.beat("turn"):
            eq_sign = tex(r"=", size=Size.BODY).move_to(rd2[0].get_center())

            def live_num():
                k = int(round(image_dot(theta.get_value())))
                m = nums[k].copy().set_fill(red_to_green(lock.get_value()))
                return m.next_to(eq_sign, RIGHT, buff=0.2)

            num = always_redraw(live_num)
            num.add_updater(lambda m: _sk._mark_text(m, Size.BODY, "dot readout"))
            out_pair = always_redraw(lambda: VGroup(
                vec(bot, A @ pair(theta.get_value())[0], red_to_green(lock.get_value())),
                vec(bot, A @ pair(theta.get_value())[1], red_to_green(lock.get_value())),
            ))
            ghosts = VGroup(vec(bot, AE1, RED_K), vec(bot, AE2, RED_K)).set_opacity(0.3)
            self.add(ghosts, out_pair)
            self.remove(*static_imgs)
            self.play(FadeOut(le1), FadeOut(le2), FadeOut(rd2), FadeIn(eq_sign), FadeIn(num), run_time=0.5)
            self.play(theta.animate.set_value(PI / 2), run_time=5.6, rate_func=smooth)

        # ------------------------------------------------------------ zero
        with self.beat("zero"):
            self.play(theta.animate.set_value(THETA_STAR), run_time=2.0, rate_func=smooth)
            self.play(lock.animate.set_value(1.0), run_time=0.6)
            for m in (in_pair, lv1, lv2, out_pair, marks, num):
                m.clear_updaters()
            vals = VGroup(
                tex(rf"\cB{{v_1}} = {tup(V1)}", size=Size.BODY),
                tex(rf"\cB{{v_2}} = {tup(V2)}", size=Size.BODY),
            ).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
            vals.next_to(a_eq, DOWN, buff=0.45).align_to(a_eq, LEFT)
            self.cue("happens")
            self.play(FadeOut(VGroup(rd1, eq_sign, num)), run_time=0.35)
            self.play(FadeIn(vals, shift=UP * 0.1), run_time=0.5)

        # ------------------------------------------------------------ land
        with self.beat("land"):
            lu1 = plate(tex(tup(AV1), color=GREEN_K, size=Size.LABEL)).move_to(bot.c2p(6.5, 1.2))
            lu2 = plate(tex(tup(AV2), color=GREEN_K, size=Size.LABEL)).move_to(bot.c2p(2.5, 3.6))
            long_ax = DashedLine(bot.c2p(*(-SIG1 * U1)), bot.c2p(0, 0), color=GREEN_K, stroke_width=5, dash_length=0.15)
            short_ax = DashedLine(bot.c2p(*(-SIG2 * U2)), bot.c2p(0, 0), color=GREEN_K, stroke_width=5, dash_length=0.15)
            lu1.set_z_index(5)  # the moving dashed components in "why" pass behind the labels
            lu2.set_z_index(5)
            # apply A once more, one arrow at a time: v1 lands on (10, 0), v2 on (0, 5)
            hits = [vec(bot, AV1, GREEN_K, width=9), vec(bot, AV2, GREEN_K, width=9)]
            for i, (lab, word, nth) in enumerate(((lu1, "ten", 0), (lu2, "zero", 1))):
                self.cue(word, nth=nth)
                self.play(TransformFromCopy(in_pair[i], hits[i]), run_time=1.0)
                self.play(FadeIn(lab, scale=0.8), FadeOut(hits[i]), run_time=0.5)
            self.cue("perpendicular")
            self.play(FadeOut(ghosts), run_time=0.6)
            self.cue("long")
            self.play(Create(long_ax), Create(short_ax), run_time=1.2)

        # ------------------------------------------------------------ why
        with self.beat("why"):
            phi = ValueTracker(0.0)

            def x_in():
                f = phi.get_value()
                return np.cos(f) * V1 + np.sin(f) * V2

            def x_out():
                f = phi.get_value()
                return np.cos(f) * AV1 + np.sin(f) * AV2

            def comps_in():
                f = phi.get_value()
                x = x_in()
                return VGroup(
                    dline(top.c2p(*x), top.c2p(*(np.cos(f) * V1)), 0.06),
                    dline(top.c2p(*x), top.c2p(*(np.sin(f) * V2)), 0.06),
                    Dot(top.c2p(*x), color=INK, radius=0.09),
                )

            def comps_out():
                f = phi.get_value()
                y = x_out()
                return VGroup(
                    dline(bot.c2p(*y), bot.c2p(*(np.cos(f) * AV1)), 0.1),
                    dline(bot.c2p(*y), bot.c2p(*(np.sin(f) * AV2)), 0.1),
                    Dot(bot.c2p(*y), color=INK, radius=0.1),
                )

            cin = always_redraw(comps_in)
            cout = always_redraw(comps_out)
            trace = TracedPath(lambda: bot.c2p(*x_out()), stroke_color=GREEN_K, stroke_width=8)
            mix = VGroup(
                tex(r"\cB{x} = c\,\cB{v_1} + s\,\cB{v_2}", size=Size.BODY),
                tex(r"\cY{A}\cB{x} = c\,\cY{A}\cB{v_1} + s\,\cY{A}\cB{v_2}", size=Size.BODY),
            ).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
            mix.next_to(a_eq, DOWN, buff=0.45).align_to(a_eq, LEFT)
            self.play(FadeOut(vals), run_time=0.35)
            self.play(FadeIn(mix[0], shift=UP * 0.1), run_time=0.45)
            self.add(trace, cin, cout)
            self.play(phi.animate.set_value(PI), run_time=3.2, rate_func=linear)
            self.play(FadeIn(mix[1], shift=UP * 0.1), phi.animate.set_value(TAU), run_time=3.2, rate_func=linear)
            for m in (cin, cout, trace):
                m.clear_updaters()
            self.play(FadeOut(cin), FadeOut(cout), run_time=0.4)

        # ------------------------------------------------------------ reveal
        with self.beat("reveal"):
            s1 = plate(tex(rf"\sigma_1 = {fmt(SIG1)}", color=GREEN_K, size=Size.LABEL)).move_to(bot.c2p(5.0, -1.3))
            s2 = plate(tex(rf"\sigma_2 = {fmt(SIG2)}", color=GREEN_K, size=Size.LABEL)).move_to(bot.c2p(-2.9, 2.6))
            self.play(FadeIn(s1), FadeIn(s2), run_time=0.8)
            svd = tex(r"\cY{A} = \cG{U}\,\Sigma\,\cB{V}^{T}", size=Size.HEADLINE + 10)
            numeric = tex(rf"\cY{{{bm(A)}}} = \cG{{{bm(U_M)}}}{bm(S_M)}\cB{{{bm(VT_M)}}}", size=Size.LABEL)
            stack = VGroup(numeric, svd).arrange(DOWN, buff=0.4)
            TOP_BAND.fit(stack, buff=0.15, upscale=False)
            self.cue("matrix")
            self.play(FadeOut(VGroup(top, circle, in_pair, lv1, lv2, a_eq, mix)), run_time=0.6)
            self.play(FadeIn(numeric, shift=DOWN * 0.1), run_time=0.9)
            self.cue("equals", offset=-0.3)
            self.play(Write(svd), run_time=1.2)

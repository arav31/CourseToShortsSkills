"""s04: Why A to the 100th is easy: follow the eigenvectors.

Storyboard: see storyboard.md next to this file.
  claim      Each multiplication by A rescales each eigenvector part by its eigenvalue: the
             lambda = 1 part (600, 400) survives, the lambda = 1/2 part halves away.
  objects    one population plane (x = city 1, y = city 2); the state dot with its two city bars
             lying on the axes; green eigenline + fixed arrow x1; red (1, -1) line through the
             steady state + the red arrow from x1's tip to the dot; the A plate; one equation slot.
  invariant  the green arrow never moves; every state keeps 1000 people, so the dot slides on the red line.
  reveal     A^100 u0 = 1^100 (600, 400) + 400 (1/2)^100 (1, -1).
"""

from fractions import Fraction as Fr

from shortkit import *

# Manim's partial-movie cache advances the scene clock by the exact run_time while replaying
# whole cached frames, so beat starts (and the audio placed on them) drift from the picture on
# re-renders. Rendering uncached keeps the clock frame-exact.
setattr(config, "disable_caching", True)  # setattr: shortkit's shadowing check misreads `config.x = ...`

BEATS = [
    ("hook", "A thousand people move between two cities by the same rule every year. "
             "Where are they after a hundred years?"),
    ("rule", "Each year, city one keeps eighty percent and sends twenty across; "
             "city two keeps seventy and sends thirty back. That's the matrix A."),
    ("turn", "A turns most vectors: one thousand, zero becomes eight hundred, two hundred."),
    ("stay", "But six hundred, four hundred comes back unchanged: an eigenvector with eigenvalue one."),
    ("half", "And anything along one, minus one, A just halves: eigenvalue one half."),
    ("split", "Split the start along the two lines: one thousand, zero is six hundred, four hundred, "
              "plus four hundred times one, minus one."),
    ("year1", "Each year the green part stays and the red part halves: "
              "eight hundred, two hundred, right where A sent us."),
    ("years", "Again it halves: one hundred, fifty, twenty-five, closing in on six hundred, four hundred."),
    ("every", "The start doesn't matter: every split of the thousand lies on the red line, "
              "and the whole line halves each year."),
    ("takeaway", "A to the hundredth just powers the eigenvalues: one stays one, "
                 "one half to the hundredth is practically zero. "
                 "Everyone ends at six hundred, four hundred."),
]

# ---------------------------------------------------------------- the worked example (computed)

A = ((Fr(8, 10), Fr(3, 10)), (Fr(2, 10), Fr(7, 10)))
U0 = (Fr(1000), Fr(0))
X1 = (Fr(600), Fr(400))   # candidate eigenvectors from the plan
X2 = (Fr(1), Fr(-1))
POWER = 100
YEARS = 4


def mul(M, v):
    return (M[0][0] * v[0] + M[0][1] * v[1], M[1][0] * v[0] + M[1][1] * v[1])


def scale(c, v):
    return (c * v[0], c * v[1])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


assert all(A[0][j] + A[1][j] == 1 for j in range(2))       # Markov: each column keeps everyone
AX1, AX2 = mul(A, X1), mul(A, X2)
L1, L2 = AX1[0] / X1[0], AX2[0] / X2[0]
assert AX1 == scale(L1, X1) and AX2 == scale(L2, X2)       # really eigenvectors
assert (L1, L2) == (1, Fr(1, 2))
_det = X1[0] * X2[1] - X2[0] * X1[1]
C1 = (U0[0] * X2[1] - X2[0] * U0[1]) / _det                # u0 = C1 x1 + C2 x2 (Cramer)
C2 = (X1[0] * U0[1] - U0[0] * X1[1]) / _det
assert add(scale(C1, X1), scale(C2, X2)) == U0
STEADY = scale(C1 * L1 ** POWER, X1)                       # (600, 400): the part that survives
STATES = [U0]
for _ in range(YEARS):
    STATES.append(mul(A, STATES[-1]))                      # the slow way, year by year
GAPS = [C2 * L2 ** k for k in range(YEARS + 1)]            # size of the red part: 400, 200, ...
assert all(STATES[k] == add(scale(C1 * L1 ** k, X1), scale(GAPS[k], X2)) for k in range(YEARS + 1))
LEFTOVER = C2 * L2 ** POWER                                # 400 / 2^100
assert LEFTOVER < Fr(1, 10 ** 27)
DEMO = scale(-C2, X2)                                      # demo red arrow (points the other way)
TOTAL = U0[0] + U0[1]
STARTS = [(Fr(x), TOTAL - x) for x in (0, 200, 400, 800, 1000)]   # other splits of the 1000


def n(v) -> str:
    v = Fr(v)
    return str(v.numerator) if v.denominator == 1 else f"{float(v):g}"


def col(v) -> str:
    return rf"\begin{{bmatrix}}{n(v[0])}\\{n(v[1])}\end{{bmatrix}}"


# narration numbers must be the computed ones
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
         "fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def say(v) -> str:
    k = int(v)
    if k < 20:
        return _ONES[k]
    if k < 100:
        return _TENS[k // 10] + ("" if k % 10 == 0 else "-" + _ONES[k % 10])
    if k < 1000:
        return _ONES[k // 100] + " hundred" + ("" if k % 100 == 0 else " " + say(k % 100))
    return say(k // 1000) + " thousand" + ("" if k % 1000 == 0 else " " + say(k % 1000))


def sayv(v) -> str:
    return f"{say(v[0])}, {say(v[1])}" if v[1] >= 0 else f"{say(v[0])}, minus {say(-v[1])}"


_SAID = dict(BEATS)
assert f"keeps {say(100 * A[0][0])} percent and sends {say(100 * A[1][0])}" in _SAID["rule"]
assert f"keeps {say(100 * A[1][1])} and sends {say(100 * A[0][1])}" in _SAID["rule"]
assert f"{sayv(U0)} becomes {sayv(STATES[1])}" in _SAID["turn"]
assert sayv(X1) in _SAID["stay"] and f"eigenvalue {say(L1)}" in _SAID["stay"]
assert sayv(X2) in _SAID["half"] and L2 == Fr(1, 2) and "eigenvalue one half" in _SAID["half"]
assert f"{sayv(U0)} is {sayv(STEADY)}, plus {say(C2)} times {sayv(X2)}" in _SAID["split"]
assert sayv(STATES[1]) in _SAID["year1"]
assert ", ".join(say(g) for g in GAPS[2:]) in _SAID["years"] and sayv(STEADY) in _SAID["years"]
assert sayv(STEADY) in _SAID["takeaway"] and TOTAL == 1000 and "A thousand people" in _SAID["hook"]

# ---------------------------------------------------------------- layout

R = (-50, 1050)
PLANE_ZONE = Zone("plane", STAGE.left, STAGE.right, -0.95, STAGE.top)
SLOT = Zone("slot", STAGE.left, STAGE.right, STAGE.bottom, -1.2)


class Short(ShortScene):
    def construct(self):
        plane = stage_plane((R[0], R[1], 100), (R[0], R[1], 100), zone=PLANE_ZONE, buff=0.02)

        def P(x, y=None):
            if y is None:
                x, y = x
            return plane.c2p(float(x), float(y))

        def slot(mob):
            return SLOT.fit(plate(mob), upscale=False)

        def swap(old, new, run_time=0.6):
            if old is not None:
                self.play(FadeOut(old, shift=UP * 0.12), run_time=0.4 * run_time)
            self.play(FadeIn(new, shift=UP * 0.12), run_time=0.6 * run_time)
            return new

        def row(*parts):
            return VGroup(*[tex(p) for p in parts]).arrange(RIGHT, buff=0.14)

        # ---- live readout: state dot + city bars on the axes + head counts
        tx, ty = ValueTracker(0.0), ValueTracker(float(U0[1]))
        look = {"color": BLUE_K}
        counts: dict = {}

        def count(v, color):
            key = (int(round(v)), color)
            if key not in counts:
                counts[key] = text(str(key[0]), size=Size.SMALL, color=color, weight=BOLD)
            return counts[key].copy()

        def xbar():
            x = max(tx.get_value(), 2.0)
            return Line(P(0, 0), P(x, 0), stroke_width=18, color=look["color"], stroke_opacity=0.55)

        def ybar():
            y = max(ty.get_value(), 2.0)
            return Line(P(0, 0), P(0, y), stroke_width=18, color=look["color"], stroke_opacity=0.55)

        def drops():
            x, y = tx.get_value(), ty.get_value()
            g = VGroup()
            if y > 12 and x > 12:
                g.add(DashedLine(P(x, y), P(x, 0), dash_length=0.09, stroke_width=2.5, color=MUTED))
                g.add(DashedLine(P(x, y), P(0, y), dash_length=0.09, stroke_width=2.5, color=MUTED))
            return g

        def xcount():
            return count(tx.get_value(), look["color"]).next_to(P(tx.get_value(), 0), DOWN, buff=0.2)

        def ycount():
            return count(ty.get_value(), look["color"]).next_to(P(0, ty.get_value()), LEFT, buff=0.2)

        def dot():
            return Dot(P(tx.get_value(), ty.get_value()), radius=0.11, color=look["color"])

        bars = VGroup(always_redraw(xbar), always_redraw(ybar))
        drop = always_redraw(drops)
        nums = VGroup(always_redraw(xcount), always_redraw(ycount))
        state = always_redraw(dot)
        city1 = text("city 1", size=Size.SMALL, color=MUTED).next_to(P(0, 0), DOWN, buff=0.2)
        city1.align_to(P(0, 0) + RIGHT * 0.05, LEFT)
        city2 = text("city 2", size=Size.SMALL, color=MUTED).next_to(P(0, 880), LEFT, buff=0.2)

        # ---- A plate, top-right corner (above both eigen-lines)
        a_tex = tex(rf"\cY{{A}}=\begin{{bmatrix}}{n(A[0][0])}&{n(A[0][1])}\\{n(A[1][0])}&{n(A[1][1])}\end{{bmatrix}}")
        a_plate = plate(a_tex)
        a_plate.align_to(np.array([STAGE.right - 0.05, STAGE.top - 0.05, 0]), UR)
        glyphs = list(a_tex.submobjects)
        brackets = sorted(glyphs, key=lambda g: g.height)[-2:]
        lb, rb = sorted(b.get_x() for b in brackets)
        entries = [g for g in glyphs if lb < g.get_x() < rb and all(g is not b for b in brackets)]
        mid = (lb + rb) / 2
        col1 = VGroup(*[g for g in entries if g.get_x() < mid])
        col2 = VGroup(*[g for g in entries if g.get_x() > mid])

        with self.beat("hook"):
            self.title("Follow the eigenvectors", Create(plane, lag_ratio=0.03), run_time=1.4)
            self.play(FadeIn(city1), FadeIn(city2), FadeIn(bars), FadeIn(state, scale=1.8), run_time=0.5)
            self.play(tx.animate.set_value(float(U0[0])), run_time=1.3)
            nums.update()  # refresh the hidden always_redraw counts first, or FadeIn's families no longer zip
            self.play(FadeIn(nums), run_time=0.5)
            self.add(drop)
            eq = slot(tex(rf"\cY{{A}}^{{{POWER}}}\cB{{{col(U0)}}}=\;?"))
            self.cue("hundred")
            self.play(FadeIn(eq, shift=UP * 0.12), run_time=0.7)

        with self.beat("rule"):
            self.play(FadeIn(a_plate, shift=DOWN * 0.12), run_time=0.7)
            box = highlight(col1, color=YELLOW_K, buff=0.08)
            self.cue("eighty")
            self.play(Create(box), run_time=0.5)
            self.cue("city", nth=1)
            self.play(Transform(box, highlight(col2, color=YELLOW_K, buff=0.08)), run_time=0.5)
            self.cue("matrix")
            self.play(FadeOut(box), Indicate(a_tex[0], color=YELLOW_K, scale_factor=1.3), run_time=0.8)

        with self.beat("turn"):
            arrow = vec(plane, U0, BLUE_K)
            self.cue("turns")
            self.play(GrowArrow(arrow), FadeOut(eq, shift=UP * 0.12), run_time=0.6)
            new = slot(tex(rf"\cY{{A}}\cB{{{col(U0)}}}=\cB{{{col(STATES[1])}}}"))
            self.cue("becomes")
            self.play(Transform(arrow, vec(plane, STATES[1], BLUE_K)), FadeIn(new, shift=UP * 0.12), run_time=1.1)
            eq = new
            marker = Circle(radius=0.15, color=BLUE_K, stroke_width=4).move_to(P(STATES[1]))
            self.play(Create(marker), run_time=0.4)

        with self.beat("stay"):
            green_line = Line(P(R[0], R[0] * X1[1] / X1[0]), P(R[1], R[1] * X1[1] / X1[0]),
                              color=GREEN_K, stroke_width=4, stroke_opacity=0.7)
            x1 = vec(plane, X1, GREEN_K, width=8)
            self.play(FadeOut(arrow), Create(green_line), run_time=0.8)
            self.play(GrowArrow(x1), run_time=0.7)
            eq = swap(eq, slot(tex(rf"\cY{{A}}\cG{{{col(X1)}}}"
                                   rf"=\begin{{bmatrix}}{n(A[0][0] * X1[0])}+{n(A[0][1] * X1[1])}\\"
                                   rf"{n(A[1][0] * X1[0])}+{n(A[1][1] * X1[1])}\end{{bmatrix}}"
                                   rf"=\cG{{{col(AX1)}}}")))
            tag1 = tex(rf"\lambda={n(L1)}", color=GREEN_K, size=Size.LABEL).next_to(P(R[1], R[1] * X1[1] / X1[0]), RIGHT, buff=0.1)
            self.cue("eigenvalue")
            self.play(FadeIn(tag1, shift=LEFT * 0.1), run_time=0.5)

        with self.beat("half"):
            red_line = Line(P(R[0], TOTAL - R[0]), P(R[1], TOTAL - R[1]), color=RED_K, stroke_width=4, stroke_opacity=0.7)
            demo = vec(plane, add(STEADY, DEMO), RED_K, start=STEADY, width=9)
            self.play(Create(red_line), run_time=0.7)
            self.play(GrowArrow(demo), run_time=0.5)
            eq = swap(eq, slot(tex(rf"\cY{{A}}\cR{{{col(X2)}}}={col(AX2)}=\frac{{1}}{{2}}\cR{{{col(X2)}}}")), run_time=0.5)
            self.cue("halves")
            self.play(Transform(demo, vec(plane, add(STEADY, scale(L2, DEMO)), RED_K, start=STEADY, width=9)), run_time=0.9)
            tag2 = tex(r"\lambda=\frac{1}{2}", color=RED_K, size=Size.LABEL).next_to(P(R[1], 80), RIGHT, buff=0.1)
            self.cue("eigenvalue")
            self.play(FadeIn(tag2, shift=LEFT * 0.1), FadeOut(demo), run_time=0.6)

        with self.beat("split"):
            new = slot(row(rf"\cB{{{col(U0)}}}=", rf"\cG{{{col(STEADY)}}}", rf"+{n(C2)}\,\cR{{{col(X2)}}}"))
            p1, p2, p3 = new[1]
            self.play(FadeOut(eq, shift=UP * 0.12), run_time=0.3)
            self.play(FadeIn(new[0], shift=UP * 0.12), FadeIn(p1, shift=UP * 0.12), run_time=0.4)
            eq = new
            self.cue("six")
            self.play(FadeIn(p2, shift=UP * 0.12), Indicate(x1, color=GREEN_K, scale_factor=1.08), run_time=0.8)
            self.cue("plus")
            red0 = vec(plane, U0, RED_K, start=STEADY)
            self.play(FadeIn(p3, shift=UP * 0.12), GrowArrow(red0), run_time=1.0)
            red = always_redraw(lambda: vec(plane, (tx.get_value(), ty.get_value()), RED_K, start=STEADY))
            self.remove(red0)
            self.add(red)
            self.bring_to_front(state)

        def morph(old, new):
            """Slide the parts that stay the same; cross-fade only the parts that change."""
            anims = [ReplacementTransform(old[0], new[0])]
            for a, b in zip(old[1], new[1]):
                same = a.tex_source == b.tex_source
                anims.append(ReplacementTransform(a, b) if same else FadeTransform(a, b))
            return anims

        trail = VGroup()
        current = {"slot": eq}

        def hop(k, run_time):
            ghost = Dot(P(STATES[k - 1]), radius=0.06, color=MUTED)
            trail.add(ghost)
            self.add(ghost)
            self.bring_to_front(red, state)
            new = slot(row(rf"\cB{{{col(STATES[k])}}}=", rf"\cG{{{col(STEADY)}}}", rf"+{n(GAPS[k])}\,\cR{{{col(X2)}}}"))
            self.play(tx.animate.set_value(float(STATES[k][0])), ty.animate.set_value(float(STATES[k][1])),
                      *morph(current["slot"], new), run_time=run_time)
            self.add(new)
            current["slot"] = new

        with self.beat("year1"):
            self.cue("green")
            self.play(Indicate(x1, color=GREEN_K, scale_factor=1.06), run_time=0.8)
            self.cue("halves")
            hop(1, 1.3)
            self.cue("right")
            self.play(Indicate(marker, color=BLUE_K, scale_factor=1.6), run_time=0.6)
            self.play(FadeOut(marker), run_time=0.3)

        with self.beat("years"):
            for k in range(2, YEARS + 1):
                self.cue(say(GAPS[k]).split()[0])
                hop(k, 0.8)

        with self.beat("every"):
            self.play(FadeOut(VGroup(bars, nums, drop, state, red, trail, current["slot"])), run_time=0.6)
            seg = Line(P(STARTS[0]), P(STARTS[-1]), color=RED_K, stroke_width=10)
            dots = VGroup(*[Dot(P(s), radius=0.1, color=BLUE_K) for s in STARTS])
            self.cue("every")
            self.play(Create(seg), LaggedStart(*[FadeIn(d, scale=1.8) for d in dots], lag_ratio=0.15), run_time=1.0)
            self.cue("halves")
            pts = list(STARTS)
            for _ in range(3):
                pts = [add(STEADY, scale(L2, add(p, scale(-1, STEADY)))) for p in pts]
                self.play(seg.animate.put_start_and_end_on(P(pts[0]), P(pts[-1])),
                          *[d.animate.move_to(P(p)) for d, p in zip(dots, pts)], run_time=0.55)

        with self.beat("takeaway"):
            final = slot(VGroup(
                tex(rf"\cY{{A}}^{{{POWER}}}\cB{{{col(U0)}}}=", size=Size.LABEL),
                tex(rf"1^{{{POWER}}}\cG{{{col(STEADY)}}}", size=Size.LABEL),
                tex(rf"+{n(C2)}\left(\frac{{1}}{{2}}\right)^{{{POWER}}}\cR{{{col(X2)}}}", size=Size.LABEL),
            ).arrange(RIGHT, buff=0.12))
            _, keep, fade = final[1]
            self.play(FadeIn(final, shift=UP * 0.12), run_time=0.8)
            self.cue("stays")
            box1 = highlight(keep, color=GREEN_K, buff=0.06)
            self.play(Create(box1), Indicate(x1, color=GREEN_K, scale_factor=1.06), run_time=0.7)
            self.cue("half")
            box2 = highlight(fade, color=RED_K, buff=0.06)
            tiny = Fr(1, 2)
            self.play(Create(box2),
                      seg.animate.put_start_and_end_on(P(STEADY[0] - tiny, STEADY[1] + tiny),
                                                       P(STEADY[0] + tiny, STEADY[1] - tiny)).set_stroke(opacity=0),
                      *[d.animate.move_to(P(STEADY)) for d in dots], run_time=1.2)
            self.cue("everyone")
            look["color"] = GREEN_K
            tx.set_value(float(STEADY[0]))
            ty.set_value(float(STEADY[1]))
            # a static snapshot: FadeIn on always_redraw objects whose glyph/dash count changed
            # while hidden crashes Manim (families no longer zip)
            settled = VGroup(xbar(), ybar(), drops(), xcount(), ycount(), dot())
            self.play(FadeOut(dots), FadeOut(box1), FadeOut(box2), FadeIn(settled), run_time=0.8)

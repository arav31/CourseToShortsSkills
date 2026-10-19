"""s01 Rows vs columns: two pictures of one system. See storyboard.md.

The same 2x2 system is read twice on one number plane: row by row (two lines that
cross at the solution) and column by column (two arrows whose 1 : 2 mix lands on b).
"""

from fractions import Fraction

from shortkit import *

BEATS = [
    ("hook", "Two x minus y is zero, and minus x plus two y is three. What does solving this look like?"),
    ("rows", "The usual picture reads it row by row: each equation is a line."),
    ("cross", "The solution is where the lines cross: x is one, y is two."),
    ("columns", "Now read the same system down its columns: two, minus one goes with x, and minus one, two goes with y."),
    ("arrows", "Each column is an arrow. The right side, zero, three, is a target point, b."),
    ("scale", "Which mix of the arrows reaches b? Try one copy of the first arrow, and two copies of the second."),
    ("add", "Chain them tip to tail. Two minus two is zero, minus one plus four is three: exactly b."),
    ("same", "And that recipe, one and two, is the very point where the lines crossed."),
    ("takeaway", "So solving A times x equals b means finding the mix of A's columns that lands on b. "
                 "Unlike crossing lines, that still works with a thousand unknowns."),
]

# ---------------------------------------------------------------- the worked example
A = [[2, -1], [-1, 2]]
B = [0, 3]
DET = A[0][0] * A[1][1] - A[0][1] * A[1][0]
SOL = (Fraction(B[0] * A[1][1] - A[0][1] * B[1], DET), Fraction(A[0][0] * B[1] - B[0] * A[1][0], DET))
assert all(sum(A[i][j] * SOL[j] for j in range(2)) == B[i] for i in range(2)), "rows must hold"
X, Y = int(SOL[0]), int(SOL[1])
COL1 = (A[0][0], A[1][0])
COL2 = (A[0][1], A[1][1])
S1 = (X * COL1[0], X * COL1[1])          # x copies of column 1
S2 = (Y * COL2[0], Y * COL2[1])          # y copies of column 2
assert (S1[0] + S2[0], S1[1] + S2[1]) == tuple(B), "columns must reach b"
# The narration speaks these numbers; check every spoken number against the data.
_W = dict(enumerate("zero one two three four five six seven eight nine".split()))
_SAY = {b: t.lower() for b, t in BEATS}


def _signed(v, lead=False):
    """-1 -> 'minus one', 2 -> 'two' (lead) / 'plus two' (inside a sum)."""
    word = _W[abs(v)]
    return f"minus {word}" if v < 0 else (word if lead else f"plus {word}")


assert f"x is {_W[X]}, y is {_W[Y]}" in _SAY["cross"]
assert (f"{_signed(COL1[0], True)}, {_signed(COL1[1], True)} goes with x, and "
        f"{_signed(COL2[0], True)}, {_signed(COL2[1], True)} goes with y") in _SAY["columns"]
assert f"{_W[B[0]]}, {_W[B[1]]}, is a target" in _SAY["arrows"]
assert f"{_W[X]} copy of the first" in _SAY["scale"] and f"{_W[Y]} copies of the second" in _SAY["scale"]
assert (f"{_signed(S1[0], True)} {_signed(S2[0])} is {_W[B[0]]}, "
        f"{_signed(S1[1], True)} {_signed(S2[1])} is {_W[B[1]]}") in _SAY["add"]
assert f"recipe, {_W[X]} and {_W[Y]}" in _SAY["same"]


def _term(c, var, lead=False):
    """Spoken term: (2, 'x') -> 'two x', (-1, 'y') -> 'minus y', (2, 'y') -> 'plus two y'."""
    sign = "minus " if c < 0 else ("" if lead else "plus ")
    return sign + ("" if abs(c) == 1 else _W[abs(c)] + " ") + var


for _i, _join in ((0, ", and "), (1, ". what")):
    _spoken = f"{_term(A[_i][0], 'x', True)} {_term(A[_i][1], 'y')} is {_W[B[_i]]}{_join}"
    assert _spoken in _SAY["hook"], _spoken

# ---------------------------------------------------------------- colours and LaTeX helpers
A1C, A2C = BLUE_K, "#8A9BFF"     # both columns are inputs (blue family), told apart
A2HEX = A2C.lstrip("#")
XR, YR = (-3.5, 3.5), (-2.7, 4.3)  # plane window


def c1(s):
    return r"\cB{" + s + "}"


def c2(s):
    return r"{\color[HTML]{" + A2HEX + "}" + s + "}"


def vec_src(v):
    return r"\begin{bmatrix}" + r"\\".join(str(e) for e in v) + r"\end{bmatrix}"


def row_cells(i):
    """('2x', '-', 'y', '0') for 2x - y = 0."""
    a, c = A[i]
    first = ("-" if a < 0 else "") + ("" if abs(a) == 1 else str(abs(a))) + "x"
    second = ("" if abs(c) == 1 else str(abs(c))) + "y"
    return first, ("-" if c < 0 else "+"), second, str(B[i])


ROWS = [row_cells(i) for i in range(2)]
SYS_SRC = (r"\begin{array}{r@{\;\;\;}c@{\;}r@{\;}c@{\;}l}"   # wider gap: the x column stands apart
           + r"\\".join(f"{f}&{s}&{t}&=&{r}" for f, s, t, r in ROWS) + r"\end{array}")
ROW_SRC = [f"{f}{s}{t}={r}" for f, s, t, r in ROWS]
CF_SRC = "x" + c1(vec_src(COL1)) + "+y" + c2(vec_src(COL2)) + "=" + vec_src(B)
PAIR_SRC = rf"(\cG{{{X}}},\,\cG{{{Y}}})"
FINAL_SRC = (r"A\begin{bmatrix}\cG{x}\\\cG{y}\end{bmatrix}=b\iff"
             r"\cG{x}\," + c1("a_1") + r"+\cG{y}\," + c2("a_2") + "=b")


def glyphs(cell):
    """Glyph count of a simple cell such as '2x', '-', '13'."""
    return len(cell)


def vec_chars(v):
    return ["["] + [ch for e in v for ch in str(e)] + ["]"]


SYS_CHARS = [ch for f, s, t, r in ROWS for cell in (f, s, t, "=", r) for ch in cell]
CF_CHARS = ["x"] + vec_chars(COL1) + ["+", "y"] + vec_chars(COL2) + ["="] + vec_chars(B)


def match_glyphs(src, src_chars, dst, dst_chars):
    """Morph glyphs that show the same character (in reading order); fade the rest.

    Stand-in for TransformMatchingShapes, which deep-copies shortkit glyphs (each one
    references its owner) once per glyph and grows exponentially with formula length.
    """
    used, anims, matched = set(), [], {}
    for j, ch in enumerate(dst_chars):
        i = next((i for i, c in enumerate(src_chars) if c == ch and i not in used), None)
        if i is None:
            anims.append(FadeIn(dst[j]))
        else:
            used.add(i)
            matched.setdefault(ch, dst[j])
            anims.append(ReplacementTransform(src[i], dst[j]))
    for i, c in enumerate(src_chars):
        if i not in used:
            anims.append(FadeOut(src[i], target_position=matched.get(c, dst).get_center()))
    return anims


def recolor(mobs, colors):
    """Animate glyph colours without `.animate`.

    `.animate` stores a deep copy on each glyph (`.target`); shortkit glyphs reference their
    owner, so per-glyph `.animate` calls nest those copies and blow up exponentially.
    """
    mobs = list(mobs)
    colors = [ManimColor(c) for c in (colors if isinstance(colors, (list, tuple)) else [colors] * len(mobs))]
    starts = []

    def update(_, alpha):
        if not starts:
            starts.extend(ManimColor(m.get_color()) for m in mobs)
        for m, c0, c1 in zip(mobs, starts, colors):
            m.set_color(interpolate_color(c0, c1, alpha))

    return UpdateFromAlphaFunc(VGroup(*mobs), update)


def ztex(src, size=Size.BODY, color=None):
    m = tex(src, size=size, color=color)
    m.set_z_index(3)
    return m


def zplate(m):
    g = plate(m)
    g[0].set_z_index(2)
    return g


class Short(ShortScene):
    def construct(self):
        plane = stage_plane(x_range=(XR[0], XR[1], 1), y_range=(YR[0], YR[1], 1))
        P = plane.c2p

        # ---- the equation band (bottom of the plane, below everything in the column picture)
        cf = ztex(CF_SRC)
        n1, n2 = 2 + sum(map(len, map(str, COL1))), 2 + sum(map(len, map(str, COL2)))
        nb = 2 + sum(map(len, map(str, B)))
        assert len(cf.submobjects) == 1 + n1 + 2 + n2 + 1 + nb == len(CF_CHARS), len(cf.submobjects)
        cf_plate = zplate(cf)
        band_y = plane.get_bottom()[1] + 0.06 + cf_plate.height / 2
        cf_plate.move_to([P(0, 0)[0], band_y, 0])
        clip_y = plane.p2c(cf_plate.get_top() + UP * 0.02)[1]   # row lines stop behind the band

        g = cf.submobjects
        cf_x = VGroup(*g[0:1 + n1])                       # x [2; -1]
        cf_y = VGroup(*g[1 + n1:1 + n1 + 2 + n2])          # + y [-1; 2]
        cf_r = VGroup(*g[1 + n1 + 2 + n2:])                # = [0; 3]
        V1 = VGroup(*g[1:1 + n1])
        V2 = VGroup(*g[1 + n1 + 2:1 + n1 + 2 + n2])
        Vb = VGroup(*g[-nb:])
        gx, gy = g[0], g[1 + n1 + 1]
        top_entries = [V1[1], *V2[1:1 + len(str(COL2[0]))], Vb[1]]
        bot_entries = [*V1[1 + len(str(COL1[0])):-1], V2[-2], Vb[-2]]

        sys_big = ztex(SYS_SRC, size=Size.HEADLINE + 20).move_to(STAGE.center)
        sys_band = ztex(SYS_SRC)
        sys_plate = zplate(sys_band).move_to(cf_plate)
        counts = [[glyphs(c) for c in (f, s, t, "=", r)] for f, s, t, r in ROWS]
        assert len(sys_band.submobjects) == sum(map(sum, counts)) == len(SYS_CHARS)
        # glyph indices by row and by column (x-term, sign, y-term, '=', rhs)
        idx, k = [], 0
        for row in counts:
            cells = []
            for n in row:
                cells.append(list(range(k, k + n)))
                k += n
            idx.append(cells)

        def chars_of(group):
            return [SYS_CHARS[sys_band.submobjects.index(m)] for m in group]

        def pick(mob, rows, cols):
            return VGroup(*[mob.submobjects[i] for r in rows for c in cols for i in idx[r][c]])

        def row_line(i, opacity=1.0):
            a, c = A[i]
            r = B[i]
            pts = []
            for x in XR:
                yv = (r - a * x) / c
                if clip_y - 1e-9 <= yv <= YR[1] + 1e-9:
                    pts.append((x, yv))
            for yv in (clip_y, YR[1]):
                x = (r - c * yv) / a
                if XR[0] - 1e-9 <= x <= XR[1] + 1e-9:
                    pts.append((x, yv))
            pts.sort()
            return Line(P(*pts[0]), P(*pts[-1]), color=INK, stroke_width=5, stroke_opacity=opacity)

        # ------------------------------------------------------------ hook
        with self.beat("hook"):
            self.title("Rows vs columns", Write(pick(sys_big, [0], range(5))), run_time=1.2)
            self.cue("and")
            self.play(Write(pick(sys_big, [1], range(5))), run_time=1.2)

        # ------------------------------------------------------------ row picture
        line1, line2 = row_line(0), row_line(1)
        lab1 = zplate(ztex(ROW_SRC[0])).move_to(P(0.15, 3.8))
        lab2 = zplate(ztex(ROW_SRC[1])).move_to(P(-2.1, 1.65))
        with self.beat("rows"):
            self.play(Create(plane, lag_ratio=0.05), ReplacementTransform(sys_big, sys_band),
                      FadeIn(sys_plate[0]), run_time=1.5)
            self.cue("row")
            # the row's copy reaches its label spot before the line draws, so they never cross
            for k, (line, lab) in enumerate(((line1, lab1), (line2, lab2))):
                self.play(LaggedStart(
                    AnimationGroup(TransformFromCopy(pick(sys_band, [k], range(5)), lab[1], path_arc=PI / 3 * k),
                                   FadeIn(lab[0])),
                    Create(line), lag_ratio=0.55), run_time=1.3)

        dot = Dot(P(X, Y), radius=0.11, color=GREEN_K).set_z_index(1.5)
        pair = ztex(PAIR_SRC)
        assert len(pair.submobjects) == 5
        pair_plate = zplate(pair).move_to(P(1.85, 1.45))
        with self.beat("cross"):
            self.cue("cross")
            self.play(GrowFromCenter(dot), run_time=0.6)
            self.cue("x")
            self.play(FadeIn(pair_plate, shift=0.1 * DOWN), run_time=0.7)

        # ------------------------------------------------------------ column picture
        xcol = pick(sys_band, [0, 1], [0])
        ycol = pick(sys_band, [0, 1], [1, 2])
        rcol = pick(sys_band, [0, 1], [3, 4])
        with self.beat("columns"):
            self.play(*[FadeOut(m) for m in (line1, line2, lab1, lab2, dot, pair_plate)], run_time=0.7)
            self.cue("two")
            hx = highlight(xcol).set_z_index(4)
            self.play(Create(hx), xcol.animate.set_color(A1C), run_time=0.7)
            self.cue("and")
            hy = highlight(ycol).set_z_index(4)
            self.play(Create(hy), ycol.animate.set_color(A2C), run_time=0.7)
            self.play(FadeOut(hx), FadeOut(hy),
                      *match_glyphs(xcol, chars_of(xcol), cf_x, CF_CHARS[:len(cf_x)]),
                      *match_glyphs(ycol, chars_of(ycol), cf_y, CF_CHARS[len(cf_x):len(cf_x) + len(cf_y)]),
                      *match_glyphs(rcol, chars_of(rcol), cf_r, CF_CHARS[len(cf_x) + len(cf_y):]),
                      ReplacementTransform(sys_plate[0], cf_plate[0]), run_time=1.3)
            self.remove(sys_band, *cf.submobjects)   # tidy the scene graph: one band object again
            self.add(cf_plate)

        a1 = vec(plane, COL1, A1C).set_z_index(1)
        a2 = vec(plane, COL2, A2C).set_z_index(1)
        L1_AT = P(COL1[0] + 0.5, COL1[1] + 0.42)   # up-right of a1's tip, clear of the band
        l1 = zplate(ztex(c1("a_1"), size=Size.LABEL)).move_to(L1_AT)
        l2 = zplate(ztex(c2("a_2"), size=Size.LABEL)).next_to(a2.get_end(), LEFT, buff=0.1)
        ring = Circle(radius=0.16, stroke_color=INK, stroke_width=5).move_to(P(*B)).set_z_index(1.5)
        lb = zplate(ztex("b", size=Size.LABEL)).next_to(ring, LEFT, buff=0.1)
        with self.beat("arrows"):
            self.play(GrowArrow(a1), FadeTransform(V1.copy(), l1), run_time=1.1)
            self.play(GrowArrow(a2), FadeTransform(V2.copy(), l2), run_time=1.1)
            self.cue("right")
            self.play(Create(ring), FadeTransform(Vb.copy(), lb), run_time=1.0)

        one = ztex(str(X), color=GREEN_K)
        one.move_to(gx).align_to(gx, DOWN)
        two = ztex(str(Y), color=GREEN_K)
        two.move_to(gy).align_to(gx, DOWN)
        l1b = zplate(ztex(rf"\cG{{{X}}}\," + c1("a_1"), size=Size.LABEL)).move_to(L1_AT)
        ghost2 = a2.copy().set_opacity(0.3).set_z_index(0.5)
        a2_long = vec(plane, S2, A2C).set_z_index(1)
        l2b = zplate(ztex(rf"\cG{{{Y}}}\," + c2("a_2"), size=Size.LABEL)).next_to(a2_long.get_end(), LEFT, buff=0.1)
        with self.beat("scale"):
            self.cue("mix")
            hw = VGroup(highlight(gx).set_z_index(4), highlight(gy).set_z_index(4))
            self.play(Create(hw), run_time=0.6)
            self.cue("one")
            self.play(FadeOut(hw[0]), FadeTransform(gx, one), FadeTransform(l1, l1b), run_time=0.8)
            self.allow_overlap(one, cf_plate)   # the weight now sits inside the equation
            self.cue("two")
            self.add(ghost2)
            self.play(FadeOut(hw[1]), FadeTransform(gy, two), Transform(a2, a2_long),
                      FadeTransform(l2, l2b), run_time=1.2)
            self.allow_overlap(two, cf_plate)

        shifted = vec(plane, B, A2C, start=S1).set_z_index(1)
        result = vec(plane, B, GREEN_K, width=8).set_z_index(1.2)
        with self.beat("add"):
            self.play(Transform(a2, shifted), l2b.animate.move_to(P(1.85, 0.62)), run_time=1.3)
            # the spoken row arithmetic: light up the entries being added while they are said
            top_c = [m.get_color() for m in top_entries]
            bot_c = [m.get_color() for m in bot_entries]
            self.cue("two")
            self.play(recolor(top_entries, YELLOW_K), run_time=0.4)
            self.cue("minus", 1)
            self.play(recolor(top_entries, top_c), recolor(bot_entries, YELLOW_K), run_time=0.4)
            self.cue("exactly")
            self.play(recolor(bot_entries, bot_c), GrowArrow(result),
                      ring.animate.set_stroke(GREEN_K, width=7), lb[1].animate.set_color(GREEN_K),
                      Vb.animate.set_color(GREEN_K), run_time=1.0)

        ghost_l1, ghost_l2 = row_line(0, 0.35), row_line(1, 0.35)
        dot2 = Dot(P(X, Y), radius=0.11, color=GREEN_K).set_z_index(1.5)
        pair2 = ztex(PAIR_SRC)
        pair2_plate = zplate(pair2).move_to(P(1.85, 1.45))
        with self.beat("same"):
            self.cue("one")
            self.play(GrowFromCenter(dot2), FadeIn(pair2_plate[0]),
                      FadeIn(VGroup(pair2[0], pair2[2], pair2[4])),
                      TransformFromCopy(one[0], pair2[1], path_arc=PI / 3),
                      TransformFromCopy(two[0], pair2[3], path_arc=PI / 3), run_time=1.2)
            self.cue("lines")   # the old row lines come back and pass through that very point
            self.play(Create(ghost_l1), Create(ghost_l2), run_time=0.9)

        final = ztex(FINAL_SRC)
        final_plate = zplate(final).move_to(cf_plate)
        eq_now = VGroup(one, *V1, g[1 + n1], two, *V2, g[1 + n1 + 2 + n2], *Vb)
        with self.beat("takeaway"):
            self.play(FadeOut(eq_now, shift=DOWN * 0.15), run_time=0.5)
            self.play(ReplacementTransform(cf_plate[0], final_plate[0]), FadeIn(final, shift=UP * 0.15),
                      run_time=0.8)
            self.cue("unlike")
            self.play(FadeOut(ghost_l1), FadeOut(ghost_l2), FadeOut(dot2), FadeOut(pair2_plate[0]),
                      FadeOut(VGroup(*pair2.submobjects)), run_time=1.2)

"""s03 Recurse, but re-use: the call tree of fib(5) collapses into a memo row / subproblem DAG.

Storyboard: storyboard.md in this folder. Every number on screen and in the narration is
computed below from the actual recursion: the call tree is built by recursing like the
lecture's fib and laid out from that structure; plain recursion for n = 30 is really run.
"""

import shortkit as _sk
from shortkit import *

BEATS = [
    ("hook", "Plain recursion needs 2.7 million calls for the thirtieth Fibonacci number, but only thirty-one different answers. Where does the waste go?"),
    ("five", "Here is Fibonacci of five. Each call splits in two, down to one or zero: fifteen calls."),
    ("repeat", "Most are repeats: F of three runs twice, F of two three times, F of one five times, F of zero three times."),
    ("collapse", "Only six are different. Sort the calls into columns, merge each column into one cell, and fourteen tree edges pile onto eight dependencies."),
    ("fill", "Every arrow points right, so fill left to right. Zero and one are given; each next cell adds the two before it: one, then two, then three, then five."),
    ("scale", "Six subproblems instead of fifteen calls. And for thirty: thirty-one subproblems instead of 2.7 million calls."),
    ("rule", "That's dynamic programming: recurse, but re-use. Time equals subproblems times work per subproblem: here n plus one, times constant, so order n."),
]

# ------------------------------------------------------------------ the numbers (computed)
N, N_BIG = 5, 30


def call_tree(n):
    """The actual call tree of the lecture's fib: fib(n) calls fib(n-1), then fib(n-2)."""
    return (n, [] if n < 2 else [call_tree(n - 1), call_tree(n - 2)])


NODES = []  # preorder = the order in which plain recursion makes the calls


def _walk(t, depth, parent):
    i = len(NODES)
    NODES.append({"k": t[0], "depth": depth, "parent": parent, "kids": []})
    if parent is not None:
        NODES[parent]["kids"].append(i)
    for child in t[1]:
        _walk(child, depth + 1, i)


_walk(call_tree(N), 0, None)


def plain_fib(n, counter):
    counter[0] += 1
    return n if n < 2 else plain_fib(n - 1, counter) + plain_fib(n - 2, counter)


_c5, _c30 = [0], [0]
assert plain_fib(N, _c5) == 5
F_BIG = plain_fib(N_BIG, _c30)                      # really makes the 2.7 million calls
CALLS5, CALLS_BIG = _c5[0], _c30[0]
assert CALLS5 == len(NODES)

FIB = [0, 1]                                        # bottom up, in topological order
for _k in range(2, N_BIG + 1):
    FIB.append(FIB[_k - 1] + FIB[_k - 2])
assert FIB[N_BIG] == F_BIG and CALLS_BIG == 2 * (FIB[N_BIG - 1] + FIB[N_BIG]) - 1

KS = [nd["k"] for nd in NODES]
COUNT = {k: KS.count(k) for k in range(N + 1)}
N_SUB, N_SUB_BIG = len(COUNT), N_BIG + 1
FIRST = {k: KS.index(k) for k in COUNT}
DUPS = [i for i in range(len(NODES)) if FIRST[KS[i]] != i]
TREE_EDGES = [(nd["parent"], i) for i, nd in enumerate(NODES) if nd["parent"] is not None]
DEPS = sorted({(KS[c], KS[p]) for p, c in TREE_EDGES})  # dependency j -> k: F(k) uses F(j)
assert DEPS == sorted((k - d, k) for k in range(2, N + 1) for d in (1, 2))
assert len(DEPS) < 2 * N and len(DUPS) == CALLS5 - N_SUB

# narration says the computed values
_t = dict(BEATS)
assert f"{CALLS_BIG / 1e6:.1f} million" in _t["hook"] and spoken(N_SUB_BIG) in _t["hook"] and N_BIG == 30
assert f"Fibonacci of {spoken(N)}" in _t["five"] and f"{spoken(CALLS5)} calls" in _t["five"]
assert COUNT[3] == 2 and "F of three runs twice" in _t["repeat"]
assert all(f"F of {spoken(k)} {spoken(COUNT[k])} times" in _t["repeat"] for k in (2, 1, 0))
assert spoken(N_SUB) in _t["collapse"].lower() and spoken(len(TREE_EDGES)) in _t["collapse"]
assert spoken(len(DEPS)) in _t["collapse"]
assert f"{spoken(FIB[0]).capitalize()} and {spoken(FIB[1])}" in _t["fill"]
assert ", then ".join(spoken(v) for v in FIB[2:N + 1]) in _t["fill"]
assert spoken(N_SUB).capitalize() in _t["scale"] and spoken(CALLS5) in _t["scale"]
assert spoken(N_BIG) in _t["scale"] and spoken(N_SUB_BIG) in _t["scale"]
assert f"{CALLS_BIG / 1e6:.1f} million" in _t["scale"]

# ------------------------------------------------------------------ layout
R = 0.46                  # call circles
NODE_SIZE = 44            # F_k labels; the subscript renders at ~31 >= MIN_FONT_SIZE
TREE_TOP, TREE_BOTTOM = 3.05, -2.12


def _tidy(i):
    """Tidy tree layout: each subtree packed as close as its per-depth contour allows (1 = node spacing)."""
    nd = NODES[i]
    if not nd["kids"]:
        return {i: 0.0}, {nd["depth"]: (0.0, 0.0)}
    pos, cont = _tidy(nd["kids"][0])
    for c in nd["kids"][1:]:
        p2, c2 = _tidy(c)
        shift = max(cont[d][1] - c2[d][0] + 1.0 for d in c2 if d in cont)
        pos.update({j: x + shift for j, x in p2.items()})
        for d, (lo, hi) in c2.items():
            lo, hi = lo + shift, hi + shift
            cont[d] = (min(cont[d][0], lo), max(cont[d][1], hi)) if d in cont else (lo, hi)
    mid = (pos[nd["kids"][0]] + pos[nd["kids"][-1]]) / 2
    pos = {j: x - mid for j, x in pos.items()}
    cont = {d: (lo - mid, hi - mid) for d, (lo, hi) in cont.items()}
    pos[i], cont[nd["depth"]] = 0.0, (0.0, 0.0)
    return pos, cont


_rel, _ = _tidy(0)
_lo, _hi = min(_rel.values()), max(_rel.values())
SPACING = (8.0 - 2 * R) / (_hi - _lo)            # tree spans x in [-4, 4]
_depth_max = max(nd["depth"] for nd in NODES)
DY = (TREE_TOP - TREE_BOTTOM) / _depth_max
POS = [np.array([(_rel[i] - (_lo + _hi) / 2) * SPACING, TREE_TOP - nd["depth"] * DY, 0.0])
       for i, nd in enumerate(NODES)]
assert SPACING - 2 * R > 0.2                      # same-depth circles never touch

# memo row = subproblem DAG, in the middle of the stage
CELL_W, CELL_H, PITCH, ROW_Y = 1.08, 1.5, 1.38, 0.3
CELL_X = [(k - N / 2) * PITCH for k in range(N + 1)]
NAME_DY, VAL_DY = 0.36, -0.24                     # name at the top of a cell, value below it
STACK = 1.0                                       # spacing of the copies of one subproblem in its column
HEAD_N_Y, HEAD_Y, HEAD_X = 4.5, 3.95, 4.0          # header: n on its own line, counters below


def subtree(i):
    out = [i]
    for c in NODES[i]["kids"]:
        out += subtree(c)
    return out


def cell(k, color=MUTED):
    return RoundedRectangle(corner_radius=0.08, width=CELL_W, height=CELL_H, stroke_color=color, stroke_width=4,
                            fill_color=BG, fill_opacity=1).move_to([CELL_X[k], ROW_Y, 0]).set_z_index(2)


def name_pos(k):
    return np.array([CELL_X[k], ROW_Y + NAME_DY, 0])


def val_pos(k):
    return np.array([CELL_X[k], ROW_Y + VAL_DY, 0])


def dep_ends(j, k):
    """Chain dependencies k-1 -> k run under the row, skips k-2 -> k arc over it."""
    if k - j == 1:
        y = ROW_Y - CELL_H / 2 - 0.04
        return np.array([CELL_X[j] + 0.18, y, 0]), np.array([CELL_X[k] - 0.18, y, 0]), 2.85
    y = ROW_Y + CELL_H / 2 + 0.04
    return np.array([CELL_X[j] + 0.16, y, 0]), np.array([CELL_X[k] - 0.16, y, 0]), -2.75


def dep_arrow(j, k, color=MUTED):
    a, b, angle = dep_ends(j, k)
    return CurvedArrow(a, b, angle=angle, stroke_width=5, tip_length=0.2, color=color).set_z_index(1)


EQ_SIZE, GEN_Y, INST_Y = 40, -1.45, -2.22        # relation lines under the row (fill beat)


def relation(k):
    """The relation for cell k with the computed values: F_k = F_{k-1} + F_{k-2} = a + b = F_k's value."""
    if k < 2:
        return tex(rf"F_{{{k}}}=\cG{{{FIB[k]}}}", size=EQ_SIZE)
    return tex(rf"\cY{{F_{{{k}}}}}=F_{{{k - 1}}}+F_{{{k - 2}}}={FIB[k - 1]}+{FIB[k - 2]}=\cG{{{FIB[k]}}}", size=EQ_SIZE)


def base_color(i):
    return BLUE_K if i == 0 else INK


def ring(i):
    return Circle(radius=R + 0.08, stroke_color=YELLOW_K, stroke_width=5).move_to(POS[i]).set_z_index(3)


class Counter(LiveText):
    """live_text whose glyph object is updated in place (become), so a frame never shows the
    previous value next to the new one while other animations are running."""

    def _refresh(self, first: bool = False) -> None:
        value = str(self._fn())
        if value == self._last:
            return
        new = text(value, size=self._size, color=self._color)
        if first or not self.submobjects:
            self.submobjects = [new]
        else:
            old = self.submobjects[0]
            edge = {"left": LEFT, "right": RIGHT}.get(self._align)
            if edge is not None:
                new.move_to(old, aligned_edge=edge)
            else:
                new.move_to(old.get_center())
            new.set_opacity(old.get_fill_opacity())
            old.become(new)
        self._last = value
        _sk._mark_text(self, self._size, f"live:{value}")


class Short(ShortScene):
    def construct(self):
        # ---------------- persistent objects
        circles = [Circle(radius=R, stroke_color=base_color(i), stroke_width=5, fill_color=BG,
                          fill_opacity=1).move_to(POS[i]).set_z_index(2) for i in range(len(NODES))]
        labels = [tex(rf"F_{{{nd['k']}}}", size=NODE_SIZE).move_to(POS[i]).set_z_index(3)
                  for i, nd in enumerate(NODES)]
        edges = {}
        for p, c in TREE_EDGES:
            d = (POS[c] - POS[p]) / np.linalg.norm(POS[c] - POS[p])
            edges[c] = Line(POS[p] + d * R, POS[c] - d * R, stroke_color=MUTED, stroke_width=4).set_z_index(0)

        # header: "n = 5" on its own line; "15 calls" (left) and "6 subproblems" (right) below it
        calls_t = ValueTracker(1)
        subs_t = ValueTracker(N_SUB)
        calls_num = Counter(lambda: f"{int(round(calls_t.get_value())):,}", size=Size.HEADLINE, color=RED_K, align="left")
        calls_num.move_to([-HEAD_X, HEAD_Y, 0], aligned_edge=LEFT)
        calls_word = text("calls", size=Size.SMALL, color=MUTED)
        calls_word.add_updater(lambda m: m.next_to(calls_num, RIGHT, buff=0.2).align_to(calls_num[0][0], DOWN))
        calls_word.update()
        subs_word = text("subproblems", size=Size.SMALL, color=MUTED)
        subs_word.move_to([HEAD_X, HEAD_Y, 0], aligned_edge=RIGHT).align_to(calls_word, DOWN)
        subs_num = Counter(lambda: f"{int(round(subs_t.get_value())):,}", size=Size.HEADLINE, color=GREEN_K, align="right")
        subs_num.next_to(subs_word, LEFT, buff=0.2)
        subs_num.shift(UP * (subs_word.get_bottom()[1] - subs_num[0][0].get_bottom()[1]))
        n_tag = tex(rf"n={N}", color=BLUE_K).move_to([0, HEAD_N_Y, 0])

        def grow(i, prev, run_time):
            calls_t.set_value(i + 1)                 # the counter ticks as the call is made
            calls_num.update()
            calls_word.update()
            anims = [FadeIn(VGroup(circles[i], labels[i]), scale=0.6)]
            if i in edges:
                anims.append(Create(edges[i]))
            if prev is not None:
                anims.append(circles[prev].animate.set_stroke(base_color(prev)))
            circles[i].set_stroke(YELLOW_K)          # the call running right now
            self.play(*anims, run_time=run_time)

        # ---------------- hook: the tree starts growing in real call order
        hook_count = 7
        with self.beat("hook"):
            circles[0].set_stroke(YELLOW_K)
            self.title("Recurse, but re-use", FadeIn(VGroup(circles[0], labels[0]), scale=0.6),
                       FadeIn(calls_num), FadeIn(calls_word))
            for i in range(1, hook_count):
                grow(i, i - 1, run_time=1.0)

        # ---------------- five: the rest of the 15 calls
        with self.beat("five"):
            self.play(FadeIn(n_tag, shift=DOWN * 0.1), run_time=0.5)
            for i in range(hook_count, len(NODES) - 1):
                grow(i, i - 1, run_time=0.7)
            self.cue(spoken(CALLS5))
            grow(len(NODES) - 1, len(NODES) - 2, run_time=0.5)
            self.play(circles[-1].animate.set_stroke(INK), run_time=0.3)

        # ---------------- repeat: ring every copy, turn the repeated work red
        red = set()
        with self.beat("repeat"):
            for k, word in [(3, "three"), (2, "two"), (1, "one"), (0, "zero")]:
                self.cue(word)
                rings = [ring(i) for i in range(len(NODES)) if KS[i] == k]
                self.play(*[FadeIn(r, scale=1.25) for r in rings], run_time=0.4)
                new = [j for i in range(len(NODES)) if KS[i] == k and i in DUPS for j in subtree(i) if j not in red]
                red.update(new)
                if new:
                    self.play(*[circles[j].animate.set_stroke(RED_K) for j in new],
                              *[edges[j].animate.set_stroke(RED_K) for j in new if j in edges], run_time=0.6)
                else:
                    self.wait(0.4)
                self.play(*[FadeOut(r) for r in rings], run_time=0.3)
            assert red == set(DUPS)

        # ---------------- collapse: every call slides into its cell; edges pile onto 8 arrows
        cells = [cell(k) for k in range(N + 1)]
        names = [tex(rf"F_{{{k}}}", size=NODE_SIZE).move_to(name_pos(k)).set_z_index(3) for k in range(N + 1)]
        arrows = {(j, k): dep_arrow(j, k) for j, k in DEPS}
        with self.beat("collapse"):
            self.cue(spoken(N_SUB).capitalize())
            rings = [ring(FIRST[k]) for k in COUNT]
            self.play(*[FadeIn(r, scale=1.25) for r in rings], FadeIn(subs_num), FadeIn(subs_word), run_time=0.5)
            self.play(*[FadeOut(r) for r in rings], run_time=0.3)

            self.cue("Sort")
            for c, e in edges.items():  # edges stay attached to their two calls while those move
                p = NODES[c]["parent"]

                def follow(m, p=p, c=c):
                    a, b = circles[p].get_center(), circles[c].get_center()
                    if np.linalg.norm(b - a) > 2 * R + 1e-3:
                        d = (b - a) / np.linalg.norm(b - a)
                        m.put_start_and_end_on(a + d * R, b - d * R)
                e.add_updater(follow)
            # 1) sort: every copy of F_k moves into column k (deepest copy at the bottom)
            col_pos = {}
            for k in range(N + 1):
                idx = sorted((i for i in range(len(NODES)) if KS[i] == k), key=lambda i: -NODES[i]["depth"])
                for j, i in enumerate(idx):
                    col_pos[i] = np.array([CELL_X[k], ROW_Y + (j - (len(idx) - 1) / 2) * STACK, 0])
            for i in range(len(NODES)):  # the group in flight passes over the calls still waiting
                circles[i].set_z_index(20 - 2 * KS[i])
                labels[i].set_z_index(21 - 2 * KS[i])
            self.play(LaggedStart(*[AnimationGroup(*[VGroup(circles[i], labels[i]).animate.move_to(col_pos[i])
                                                     for i in range(len(NODES)) if KS[i] == k])
                                    for k in range(N + 1)], lag_ratio=0.3), run_time=1.9)
            # 2) merge: each column collapses into one cell of the row
            self.cue("merge")
            self.play(*[Transform(circles[i], cell(KS[i])) for i in range(len(NODES))],
                      *[labels[i].animate.move_to(name_pos(KS[i])) for i in FIRST.values()],
                      *[FadeOut(labels[i], target_position=name_pos(KS[i])) for i in DUPS], run_time=1.2)

            self.cue("fourteen")
            for e in edges.values():
                e.clear_updaters()
            self.play(*[Transform(edges[c], dep_arrow(KS[c], KS[p])) for p, c in TREE_EDGES], run_time=2.0)
            # one clean object per cell / name / arrow
            self.remove(*circles, *labels, *edges.values())
            self.add(*cells, *names, *arrows.values())

        # ---------------- fill: left to right, each cell adds its two incoming values
        vals = [tex(str(FIB[k]), size=60, color=GREEN_K).move_to(val_pos(k)).set_z_index(3) for k in range(N + 1)]
        with self.beat("fill"):
            self.cue("arrow")
            flashes = [ShowPassingFlash(a.copy().set_color(YELLOW_K).set_stroke(width=10), time_width=0.6)
                       for a in arrows.values()]
            self.play(*flashes, run_time=1.1)
            # one relation line per cell, all aligned on their first "=" under the general rule
            lines = {k: relation(k) for k in range(N + 1)}
            lines[N].move_to([0, INST_Y, 0])
            x_eq = lines[N][2].get_center()[0]
            for k, ln in lines.items():
                assert len(ln) == (4 if k < 2 else 14)  # F k = v  |  F k = F a + F b = a + b = v
                ln.shift([x_eq - ln[2].get_center()[0], INST_Y - ln.get_center()[1], 0])
            general = tex(r"F_k=F_{k-1}+F_{k-2}", size=EQ_SIZE)
            general.shift([x_eq - general[2].get_center()[0], GEN_Y - general.get_center()[1], 0])
            general = plate(general, buff=0.1)
            current = None
            for k, word, nth in [(0, "Zero", 0), (1, "one", 0)]:
                self.cue(word, nth=nth)
                if current is not None:
                    self.play(FadeOut(current), run_time=0.12)
                current = plate(lines[k], buff=0.1)
                self.play(FadeIn(vals[k], scale=0.7), cells[k].animate.set_stroke(GREEN_K), FadeIn(current), run_time=0.45)
            self.cue("each")
            self.play(FadeIn(general, shift=UP * 0.1), run_time=0.4)
            self.cue("adds")
            for k, word, nth, flow in [(2, "one", 1, 1.0), (3, "two", 1, 0.5), (4, "three", 0, 0.5), (5, "five", 0, 0.5)]:
                inc = [(k - 1, k), (k - 2, k)]
                self.play(FadeOut(current), run_time=0.12)          # old line out before the new one comes in
                current = plate(lines[k], buff=0.1)
                head, tail = lines[k][:12], lines[k][12:]          # "F_k = F_a + F_b = a + b" | "= value"
                pulses = [ShowPassingFlash(arrows[e].copy().set_color(YELLOW_K).set_stroke(width=10), time_width=0.7)
                          for e in inc]
                self.play(FadeIn(head), *pulses,
                          *[arrows[e].animate.set_color(YELLOW_K) for e in inc], run_time=flow)
                self.cue(word, nth=nth)
                self.play(FadeIn(vals[k], scale=1.3), FadeIn(tail), FadeIn(current[0]), cells[k].animate.set_stroke(GREEN_K),
                          *[arrows[e].animate.set_color(GREEN_K) for e in inc], run_time=0.3)
                self.remove(current[0], head, tail)  # one clean object per line
                self.add(current)

        # ---------------- scale: 6 vs 15, then 31 vs 2,692,537
        pitch31 = 8.0 / N_SUB_BIG
        ROW31_Y = ROW_Y + 0.7
        cells31 = VGroup(*[RoundedRectangle(corner_radius=0.05, width=pitch31 * 0.74, height=CELL_H, stroke_color=GREEN_K,
                                            stroke_width=3, fill_color=BG, fill_opacity=1)
                           .move_to([(k - N_BIG / 2) * pitch31, ROW31_Y, 0]) for k in range(N_SUB_BIG)]).set_z_index(2)
        end_y = ROW31_Y - CELL_H / 2 - 0.36
        name0 = tex(r"F_{0}", size=NODE_SIZE).move_to([0, end_y, 0]).align_to(cells31[0], LEFT).set_z_index(3)
        name_big = tex(rf"F_{{{N_BIG}}}", size=NODE_SIZE).move_to([0, end_y, 0]).align_to(cells31[-1], RIGHT).set_z_index(3)
        n_big = tex(rf"n={N_BIG}", color=BLUE_K).move_to(n_tag)
        with self.beat("scale"):
            self.cue(spoken(N_SUB).capitalize())
            h_sub = highlight(VGroup(subs_num, subs_word))
            self.play(FadeIn(h_sub), FadeOut(general), FadeOut(current), run_time=0.4)
            self.cue(spoken(CALLS5))
            h_calls = highlight(VGroup(calls_num, calls_word))
            self.play(FadeIn(h_calls), run_time=0.35)
            self.cue(spoken(N_BIG))
            self.play(FadeOut(h_sub), FadeOut(h_calls), *[FadeOut(a) for a in arrows.values()],
                      *[FadeOut(v) for v in vals], *[FadeOut(nm) for nm in names], FadeOut(n_tag), run_time=0.5)
            self.play(FadeIn(n_big), *[Transform(cells[k], cells31[k]) for k in range(N + 1)], run_time=0.6)
            self.play(LaggedStart(*[FadeIn(c, shift=LEFT * 0.15) for c in cells31[N + 1:]], lag_ratio=0.12),
                      FadeIn(name0), FadeIn(name_big), subs_t.animate.set_value(N_SUB_BIG), run_time=1.1)
            self.remove(*cells, *cells31[N + 1:])
            self.add(cells31)
            self.cue(f"{CALLS_BIG / 1e6:.1f}")
            self.play(UpdateFromAlphaFunc(calls_t, lambda m, a: m.set_value(CALLS5 * (CALLS_BIG / CALLS5) ** smooth(a))),
                      run_time=1.4)
            calls_t.set_value(CALLS_BIG)
            calls_num.update()

        # ---------------- rule: the general time bound
        dp = text("dynamic programming", size=Size.HEADLINE, color=INK, weight=BOLD).move_to([0, 2.75, 0])
        line1 = tex(r"\text{time}=\cG{\#\,\text{subproblems}}\times\cY{\text{work each}}", size=Size.BODY)
        line2 = tex(r"=\cG{(n+1)}\cdot\cY{O(1)}=O(n)", size=52)
        line1.move_to([0, -1.55, 0])
        line2.next_to(line1, DOWN, buff=0.35)
        assert len(line2) == 16  # = ( n + 1 ) . O ( 1 ) = O ( n )
        with self.beat("rule"):
            self.cue("dynamic")
            self.play(FadeIn(dp, shift=UP * 0.1), run_time=0.7)
            self.cue("Time")
            self.play(Write(line1), run_time=1.6)
            parts = [line2[0:6], line2[6:11], line2[11:]]
            self.cue("n")
            h_row = highlight(cells31, color=YELLOW_K)
            self.play(FadeIn(parts[0], shift=UP * 0.1), FadeIn(h_row), run_time=0.5)
            self.cue("constant")
            self.play(FadeIn(parts[1], shift=UP * 0.1), FadeOut(h_row), run_time=0.5)
            self.cue("order")
            line2[12:].set_color(GREEN_K)
            self.play(FadeIn(parts[2], shift=UP * 0.1), run_time=0.5)
            self.remove(*parts)
            self.add(line2)
            self.play(FadeIn(highlight(line2[12:], color=GREEN_K)), run_time=0.5)

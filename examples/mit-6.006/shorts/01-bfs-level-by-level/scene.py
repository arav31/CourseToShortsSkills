"""s01 BFS grows level by level (MIT 6.006, Lecture 9, Example 3). See storyboard.md.

The lecture's own graph is searched from s as level sets: L_i is built from the unvisited
neighbours of L_(i-1). Every adjacency check is flashed (yellow = new vertex, red = already
placed) and counted; at the end the drawing re-lays itself by level, showing that no edge
skips a level, and the cost 2|E| = 16 checks.
"""

from shortkit import *

BEATS = [
    ("hook", "How far is every vertex from s? And can some vertex never be reached?"),
    ("level0", "Level zero is just s, at distance zero."),
    ("level1", "Level one is every unvisited neighbour of level zero, at distance one."),
    ("level2", "Level two grows only from level one. Edges back to s are rejected; b, d and e are new."),
    ("level3", "Level three: only f is new, found from d. Every other edge, even e to f, is rejected."),
    ("stop", "Level four is empty, so we stop. g was never reached: its distance is infinity."),
    ("layers", "Slide each vertex into its level. No edge skips a level; only d to e stays inside one."),
    ("proof", "So reaching f takes at least three edges, and the green tree path uses exactly three."),
    ("cost", "The cost: eight edges, each checked from both ends, so sixteen checks. Linear time, order V plus E."),
    ("rule", "Each level is the unvisited neighbours of the level before, and a vertex's level is its distance."),
]

# ---------------------------------------------------------------- the worked example
# Lecture 9, Example 3 (hash-table adjacency lists, in the lecture's order).
ADJ = {"a": ["s", "b"], "b": ["a"], "s": ["a", "c"], "c": ["s", "d", "e"],
       "d": ["c", "e", "f"], "e": ["c", "d", "f"], "f": ["d", "e"], "g": []}
SRC = "s"
assert all(u in ADJ[v] for u in ADJ for v in ADJ[u]), "undirected: adjacency must be symmetric"


def bfs_trace(adj, s):
    """Level sets, parents, and every adjacency check in order: scans[i] = [(u, [(v, is_new), ...]), ...]."""
    levels, parent, scans = [[s]], {s: None}, []
    while levels[-1]:
        nxt, level_scans = [], []
        for u in levels[-1]:
            row = []
            for v in adj[u]:
                new = v not in parent
                if new:
                    parent[v] = u
                    nxt.append(v)
                row.append((v, new))
            level_scans.append((u, row))
        scans.append(level_scans)
        levels.append(nxt)
    return levels[:-1], parent, scans


LEVELS, PARENT, SCANS = bfs_trace(ADJ, SRC)
DIST = {v: i for i, lv in enumerate(LEVELS) for v in lv}
UNREACHED = [v for v in ADJ if v not in DIST]
EDGES = sorted({tuple(sorted((u, v))) for u in ADJ for v in ADJ[u]})
TREE = {tuple(sorted((PARENT[v], v))) for v in PARENT if PARENT[v]}
CHECKS = sum(len(ADJ[u]) for u in ADJ)
SAME_LEVEL = [e for e in EDGES if DIST[e[0]] == DIST[e[1]]]
EMPTY = len(LEVELS)                                   # index of the first empty level


def path_to(v):
    out = [v]
    while PARENT[out[-1]]:
        out.append(PARENT[out[-1]])
    return out[::-1]


def brute_dist(adj, s, t):                            # second route: try every simple path
    best, stack = None, [(s, (s,))]
    while stack:
        u, path = stack.pop()
        if u == t:
            best = len(path) - 1 if best is None else min(best, len(path) - 1)
            continue
        stack += [(v, path + (v,)) for v in adj[u] if v not in path]
    return best


assert all(brute_dist(ADJ, SRC, v) == DIST.get(v) for v in ADJ)
assert all(abs(DIST[u] - DIST[v]) <= 1 for u, v in EDGES)       # no edge skips a level
assert CHECKS == 2 * len(EDGES)
TARGET = LEVELS[-1][0]                                           # f, the deepest vertex
TREE_PATH = path_to(TARGET)
assert len(TREE_PATH) - 1 == DIST[TARGET]

# narration says what the computation says
_SAY = {b: t for b, t in BEATS}
assert f"Level {spoken(0)} is just {SRC}, at distance {spoken(DIST[SRC])}" in _SAY["level0"]
assert len(LEVELS) > 3 and f"Level {spoken(EMPTY)} is empty" in _SAY["stop"]
assert f"{', '.join(LEVELS[2][:-1])} and {LEVELS[2][-1]} are new" in _SAY["level2"]
assert all(v == SRC and not new for u, row in SCANS[1] for v, new in row if v in LEVELS[0])
assert len(LEVELS[3]) == 1 and f"only {TARGET} is new, found from {PARENT[TARGET]}" in _SAY["level3"]
_E_SCAN = dict(SCANS[2])["e"]
assert (TARGET, False) in _E_SCAN and f"even e to {TARGET}, is rejected" in _SAY["level3"]
assert UNREACHED == ["g"] and "g was never reached" in _SAY["stop"]
assert SAME_LEVEL == [("d", "e")] and "only d to e stays inside one" in _SAY["layers"]
assert f"reaching {TARGET} takes at least {spoken(DIST[TARGET])} edges" in _SAY["proof"]
assert f"uses exactly {spoken(len(TREE_PATH) - 1)}" in _SAY["proof"]
assert f"{spoken(len(EDGES))} edges" in _SAY["cost"] and f"{spoken(CHECKS)} checks" in _SAY["cost"]
# the vertex a is never named in narration (TTS would read it as the article); levels are narrated


# ---------------------------------------------------------------- layout
R = 0.5                                    # vertex radius
# map-like drawing (not layered): s centre-left, b bottom-left, f centre-right, g alone bottom-right
MAP = {"a": (-2.7, 3.7), "b": (-3.05, 1.55), "s": (-0.95, 2.45), "c": (0.45, 4.05),
       "d": (3.0, 3.8), "e": (0.45, 1.75), "f": (2.5, 2.1), "g": (3.4, 1.0)}
MAP_TAG = {"a": (-1, 0), "b": (1, 0), "s": (0, 1), "c": (-1, 0), "d": (1, 0), "e": (0, -1),
           "f": (1, 0), "g": (-1, 0)}           # each tag on a side no edge leaves from
MAP_GAP = 0.92
# layered drawing: one horizontal guide per level, every distance tag above its vertex
LEVEL_Y = [3.85, 2.5, 1.15, -0.2]
LAYER_X = {"s": 0.1, "a": -1.4, "c": 1.6, "b": -2.6, "e": 0.4, "d": 2.8, "f": 1.6}
LAYER = {v: (LAYER_X[v], LEVEL_Y[DIST[v]]) for v in DIST}
LAYER["g"] = (3.65, -0.88)                       # below and right of every level: no level at all
LAYER_TAG = {v: (0, 1) for v in DIST}
LAYER_TAG["g"] = (-1, 0)
LAYER_GAP = 0.82
GUIDE_X = (-3.2, 3.3)
# level strip (bottom-left) and counter column (bottom-right)
ROW_H, ROW_GAP, ROW_TOP = 0.62, 0.155, 0.3
ROW_Y = [ROW_TOP - ROW_H / 2 - i * (ROW_H + ROW_GAP) for i in range(EMPTY)]
LABEL_X = -3.55
CELL_X = [-2.5, -1.28, -0.06]
CELL_W = 1.1
COUNTER_X = 2.5
PANEL_Y = (-1.7, -2.4)                    # formula lines at the bottom of STAGE
assert max(len(lv) for lv in LEVELS) <= len(CELL_X)
assert all(abs(LAYER_X[u] - LAYER_X[v]) >= 1.1 for u, v in EDGES if DIST[u] != DIST[v])  # tags above stay clear

Z_EDGE, Z_FLASH, Z_RING, Z_NODE, Z_TEXT = 0, 1, 1, 2, 3


def pt(xy):
    return np.array([xy[0], xy[1], 0.0])


def unit(xy):
    v = np.array([xy[0], xy[1], 0.0], dtype=float)
    return v / np.linalg.norm(v)


class Short(ShortScene):
    def construct(self):
        # ---- graph objects -------------------------------------------------------------
        circ, let, node = {}, {}, {}
        for v in ADJ:
            col = BLUE_K if v == SRC else MUTED
            circ[v] = Circle(radius=R, stroke_color=col, stroke_width=6, fill_color=BG, fill_opacity=1)
            circ[v].move_to(pt(MAP[v])).set_z_index(Z_NODE)
            let[v] = tex(v, size=Size.TITLE + 8, color=BLUE_K if v == SRC else INK)
            let[v].move_to(circ[v]).set_z_index(Z_TEXT)
            node[v] = VGroup(circ[v], let[v])

        def ends(u, v):
            p, q = circ[u].get_center(), circ[v].get_center()
            d = (q - p) / np.linalg.norm(q - p)
            return p + d * (R + 0.02), q - d * (R + 0.02)

        edge = {}
        for u, v in EDGES:
            ln = Line(*ends(u, v), stroke_color=MUTED, stroke_width=5).set_z_index(Z_EDGE)
            ln.add_updater(lambda m, u=u, v=v: m.put_start_and_end_on(*ends(u, v)))
            edge[(u, v)] = edge[(v, u)] = ln
        edges = VGroup(*[edge[e] for e in EDGES])

        def tag_at(v, layout="map"):
            if layout == "map":
                return pt(MAP[v]) + unit(MAP_TAG[v]) * MAP_GAP
            return pt(LAYER[v]) + unit(LAYER_TAG[v]) * LAYER_GAP

        tag_size = Size.BODY + 6
        q_tag = {v: tex("?", size=tag_size, color=MUTED).move_to(tag_at(v)).set_z_index(Z_TEXT) for v in ADJ}
        d_tag = {v: tex(str(DIST[v]), size=tag_size, color=GREEN_K).move_to(tag_at(v)).set_z_index(Z_TEXT)
                 for v in DIST}
        for v in UNREACHED:
            d_tag[v] = tex(r"\infty", size=tag_size, color=RED_K).move_to(tag_at(v)).set_z_index(Z_TEXT)

        # ---- level strip -----------------------------------------------------------------
        row_label = [tex(f"L_{i}", size=Size.TITLE).move_to([LABEL_X, ROW_Y[i], 0]) for i in range(EMPTY)]
        cells = [[RoundedRectangle(corner_radius=0.08, width=CELL_W, height=ROW_H, stroke_color=MUTED,
                                   stroke_width=3, fill_color=BG, fill_opacity=1).move_to([x, ROW_Y[i], 0])
                  for x in CELL_X] for i in range(EMPTY)]
        rows = [VGroup(row_label[i], *cells[i]) for i in range(EMPTY)]
        chip = {}
        for i, lv in enumerate(LEVELS):
            for k, v in enumerate(lv):
                chip[v] = tex(v, size=Size.TITLE, color=INK).move_to(cells[i][k]).set_z_index(Z_TEXT)

        # ---- counter: every value pre-built, only the current one visible ------------------
        count = ValueTracker(0)
        digits = VGroup(*[text(str(k), size=Size.HEADLINE + 26, color=INK) for k in range(CHECKS + 1)])

        def show_count(m):
            k = int(round(count.get_value()))
            for j, dg in enumerate(m):
                dg.set_opacity(1.0 if j == k else 0.0)

        show_count(digits)
        digits.add_updater(show_count)
        count_lbl = text("edge checks", size=Size.SMALL + 2, color=MUTED)
        count_lbl.move_to([COUNTER_X, -0.15, 0])
        for dg in digits:
            dg.move_to([COUNTER_X, -0.95, 0])
        counter = VGroup(count_lbl, digits)
        empty_level = tex(rf"L_{EMPTY} = \cR{{\varnothing}}", size=Size.BODY + 6).move_to([COUNTER_X, -2.1, 0])

        rings: list[Mobject] = []
        row_hl: list[Mobject] = []

        def frontier(i):
            """Ring the vertices of L_i and outline its row: they are being expanded now."""
            new_rings = [Circle(radius=R + 0.1, stroke_color=YELLOW_K, stroke_width=6)
                         .move_to(circ[v]).set_z_index(Z_RING) for v in LEVELS[i]]
            filled = VGroup(row_label[i], *cells[i][:len(LEVELS[i])])
            new_hl = highlight(filled, buff=0.06)
            anims = [FadeOut(m) for m in rings + row_hl]
            anims += [Create(r) for r in new_rings] + [Create(new_hl)]
            rings[:] = new_rings
            row_hl[:] = [new_hl]
            return anims

        def scan(u, row, level, run_time=0.7, settle=0.9):
            """Check every neighbour of u: yellow flash for a new vertex, red for one already placed."""
            flashes, found = [], []
            for v, new in row:
                p, q = ends(u, v)
                fl = Line(p, q, stroke_color=YELLOW_K if new else RED_K, stroke_width=11).set_z_index(Z_FLASH)
                flashes.append(fl)
                if new:
                    found.append(v)
            anims = [Create(f) for f in flashes] + [FadeOut(q_tag[v]) for v in found]
            anims.append(count.animate.set_value(count.get_value() + len(row)))
            self.play(*anims, run_time=run_time, rate_func=linear)
            after = [FadeOut(f) for f in flashes]
            for v in found:
                k = LEVELS[level].index(v)
                after += [circ[v].animate.set_stroke(GREEN_K), let[v].animate.set_color(GREEN_K),
                          FadeIn(d_tag[v], scale=1.4), edge[(u, v)].animate.set_stroke(GREEN_K, width=11),
                          TransformFromCopy(let[v], chip[v]), cells[level][k].animate.set_stroke(GREEN_K)]
            self.play(*after, run_time=settle if found else 0.4)

        # ---- beats ------------------------------------------------------------------------
        with self.beat("hook"):
            self.title("BFS grows level by level",
                       LaggedStart(*[Create(e) for e in edges], lag_ratio=0.08, run_time=1.2),
                       LaggedStart(*[GrowFromCenter(node[v]) for v in ADJ], lag_ratio=0.08, run_time=1.2))
            self.cue("every")
            self.play(LaggedStart(*[FadeIn(q_tag[v], scale=0.6) for v in ADJ], lag_ratio=0.1), run_time=1.2)
            self.cue("s")
            self.play(Indicate(node[SRC], color=BLUE_K, scale_factor=1.2), run_time=0.8)
            self.cue("never")
            self.play(Indicate(node["g"], color=MUTED, scale_factor=1.2), run_time=0.8)

        with self.beat("level0"):
            self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.2) for r in rows], lag_ratio=0.15), run_time=1.0)
            self.cue("distance")
            self.play(FadeOut(q_tag[SRC]), run_time=0.3)
            self.play(FadeIn(d_tag[SRC], scale=1.4), TransformFromCopy(let[SRC], chip[SRC]),
                      cells[0][0].animate.set_stroke(GREEN_K), run_time=0.9)

        for i in (1, 2, 3):
            with self.beat(f"level{i}"):
                anims = frontier(i - 1)
                if i == 1:
                    anims.append(FadeIn(counter))
                self.play(*anims, run_time=0.8)
                for k, (u, row) in enumerate(SCANS[i - 1]):
                    if i == 2 and k == 0:
                        self.cue("edges")
                    if i == 3 and u == "e":
                        self.cue("even")
                    scan(u, row, i)

        with self.beat("stop"):
            self.play(*frontier(EMPTY - 1), run_time=0.8)
            for u, row in SCANS[EMPTY - 1]:
                scan(u, row, EMPTY)
            assert count.get_value() == CHECKS and not any(new for _, row in SCANS[EMPTY - 1] for _, new in row)
            self.play(FadeIn(empty_level, shift=UP * 0.15), run_time=0.6)
            self.play(*[FadeOut(m) for m in rings + row_hl], run_time=0.5)
            rings.clear()
            row_hl.clear()
            self.cue("g")
            self.play(FadeOut(q_tag["g"]), run_time=0.3)
            self.play(circ["g"].animate.set_stroke(RED_K), let["g"].animate.set_color(RED_K),
                      FadeIn(d_tag["g"], scale=1.4), run_time=0.8)
            digits.clear_updaters()

        with self.beat("layers"):
            guides = VGroup(*[background(Line([GUIDE_X[0], y, 0], [GUIDE_X[1], y, 0], stroke_color=MUTED,
                                              stroke_width=2, stroke_opacity=0.45)).set_z_index(-1)
                              for y in LEVEL_Y])
            strip = [m for i in range(EMPTY) for m in cells[i]] + list(chip.values()) + [empty_level]
            tags = [d_tag[v] for v in ADJ]
            self.play(*[FadeOut(m) for m in strip + tags], run_time=0.6)
            moves = [node[v].animate.move_to(pt(LAYER[v])) for v in ADJ]
            moves += [row_label[i].animate.move_to([LABEL_X - 0.15, LEVEL_Y[i], 0]) for i in range(EMPTY)]
            self.play(*moves, FadeIn(guides), counter.animate.move_to([0, (PANEL_Y[0] + PANEL_Y[1]) / 2, 0]),
                      run_time=2.2)
            for v in ADJ:
                d_tag[v].move_to(tag_at(v, "layer"))
            self.play(LaggedStart(*[FadeIn(d_tag[v], shift=DOWN * 0.1) for v in ADJ], lag_ratio=0.08),
                      run_time=0.9)
            self.cue("only")
            u, v = SAME_LEVEL[0]
            same = Line(*ends(u, v), stroke_color=YELLOW_K, stroke_width=12).set_z_index(Z_FLASH)
            self.play(Create(same), run_time=0.8)

        with self.beat("proof"):
            self.play(FadeOut(same), run_time=0.4)
            trace = []
            for k, (u, v) in enumerate(zip(TREE_PATH, TREE_PATH[1:]), start=1):
                p, q = ends(u, v)
                ln = Line(p, q, stroke_color=YELLOW_K, stroke_width=12).set_z_index(Z_FLASH)
                trace.append(ln)
                self.play(Create(ln), Indicate(row_label[k], color=YELLOW_K, scale_factor=1.3), run_time=0.7)
            f_hl = highlight(d_tag[TARGET], buff=0.1)
            self.play(Create(f_hl), run_time=0.5)
            self.cue("green")
            self.play(*[t.animate.set_stroke(GREEN_K) for t in trace], run_time=0.8)

        with self.beat("cost"):
            flashes = []
            for u, v in EDGES:
                for a, b in ((u, v), (v, u)):
                    p, q = ends(a, b)
                    flashes.append(ShowPassingFlash(Line(p, q, stroke_color=YELLOW_K, stroke_width=12)
                                                    .set_z_index(Z_FLASH), time_width=0.7))
            self.play(FadeOut(f_hl), *[FadeOut(t) for t in trace], LaggedStart(*flashes, lag_ratio=0.15),
                      run_time=3.0)
            cost1 = tex(rf"\text{{checks}} = 2\,|E| = 2\cdot {len(EDGES)} = \cG{{{CHECKS}}}", size=Size.BODY + 2)
            cost2 = tex(r"\text{time} = O(|V| + |E|)", size=Size.BODY + 2)
            cost1.move_to([0, PANEL_Y[0], 0])
            cost2.move_to([0, PANEL_Y[1], 0])
            self.cue("sixteen")
            self.swap(counter, cost1)
            self.cue("linear")
            self.play(FadeIn(cost2, shift=UP * 0.1), run_time=0.6)

        with self.beat("rule", pad=1.2):
            rule1 = tex(r"\cG{L_i} = \mathrm{Adj}(\cY{L_{i-1}}) \setminus \text{visited}", size=Size.BODY + 6)
            rule2 = tex(r"v \in \cG{L_i} \;\Longrightarrow\; \delta(\cB{s}, v) = \cG{i}", size=Size.BODY + 6)
            rule1.move_to([0, PANEL_Y[0], 0])
            rule2.move_to([0, PANEL_Y[1], 0])
            self.play(FadeOut(cost1, shift=UP * 0.1), FadeOut(cost2, shift=UP * 0.1), run_time=0.5)
            self.play(FadeIn(rule1, shift=UP * 0.1), run_time=0.8)
            # the rule replayed on the picture: each level grows out of the one before it
            grow = []
            for i in range(1, len(LEVELS)):
                grow.append(AnimationGroup(*[ShowPassingFlash(
                    Line(*ends(PARENT[v], v), stroke_color=YELLOW_K, stroke_width=12).set_z_index(Z_FLASH),
                    time_width=0.8) for v in LEVELS[i]]))
            self.play(LaggedStart(*grow, lag_ratio=0.7), run_time=2.4)
            self.cue("distance")
            self.play(FadeIn(rule2, shift=UP * 0.1), run_time=0.8)

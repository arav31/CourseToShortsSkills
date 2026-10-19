"""s02 Dijkstra trusts the smallest (MIT 6.006, Lecture 13). See storyboard.md.

Everything shown or spoken is computed below: a 6.006-style Dijkstra loop (delete_min, then
relax every adjacency with decrease_key), parent pointers, and a brute-force list of all simple
Home-to-Work routes as a second check.
"""

from shortkit import *

BEATS = [
    ("hook", "The direct road from home to work takes ten minutes. Is there a faster way, and how would you know?"),
    ("guesses", "Dijkstra keeps a guess for each place: zero for home, infinity for the rest, in a queue sorted smallest first."),
    ("home", "Take the smallest, home, and lock it in. Then relax its roads: cafe gets two, park five, work ten."),
    ("cafe", "Next is cafe, at two. Through cafe, park drops from five to three, and shop gets eight."),
    ("why", "Why trust park's three? Any other route has to leave the finished places somewhere, and every exit already costs three or more. Roads only add minutes."),
    ("park", "So park is locked in. Its road back to cafe gives four, worse than two, but shop drops to five, and work to nine."),
    ("shop", "Shop is next, at five, and work drops to six. Then work comes out last."),
    ("route", "Now walk back from work to whoever set each guess: shop, park, cafe, home. Six minutes, not ten."),
    ("rule", "That's Dijkstra: lock in the smallest guess, relax its roads, repeat. It only works because no road takes negative minutes."),
]

# ---------------------------------------------------------------- the map and the run
PLACES = ["Home", "Cafe", "Park", "Shop", "Work"]
SOURCE, TARGET = "Home", "Work"
ROADS = {("Home", "Cafe"): 2, ("Home", "Park"): 5, ("Home", "Work"): 10, ("Cafe", "Park"): 1,
         ("Cafe", "Shop"): 6, ("Park", "Shop"): 2, ("Park", "Work"): 6, ("Shop", "Work"): 1}
INFTY = float("inf")


def key(u, v):
    return (u, v) if (u, v) in ROADS else (v, u)


ADJ = {p: [] for p in PLACES}
for (a, b), w in ROADS.items():
    assert w >= 0
    ADJ[a].append((b, w))
    ADJ[b].append((a, w))


def dijkstra(adj, s):
    """Lecture 13: Q holds every vertex; delete_min, then relax each adjacency (decrease_key)."""
    d = {v: INFTY for v in PLACES}
    d[s] = 0
    parent = {s: None}
    queue, done, rounds = list(PLACES), [], []
    while queue:
        u = min(queue, key=lambda v: (d[v], PLACES.index(v)))  # ties: place order
        queue.remove(u)
        done.append(u)
        checks = []
        for v, w in adj[u]:
            cand = d[u] + w
            better = cand < d[v]
            assert not (better and v in done)            # a finished place is never improved
            checks.append({"v": v, "w": w, "old": d[v], "new": cand, "better": better, "done": v in done})
            if better:
                d[v], parent[v] = cand, u
        rounds.append({"u": u, "du": d[u], "checks": checks})
    return d, parent, rounds


D, PARENT, ROUNDS = dijkstra(ADJ, SOURCE)
ORDER = [r["u"] for r in ROUNDS]
RELAX = [(r["u"], c["v"], c["old"], c["new"]) for r in ROUNDS for c in r["checks"] if c["better"]]
assert ORDER == ["Home", "Cafe", "Park", "Shop", "Work"] and len(RELAX) == 8   # as in checks/examples.py

BACK = ROUNDS[2]                                       # Park's round: one road back into the finished set
BACK_CHECK = min((c for c in BACK["checks"] if c["done"]), key=lambda c: c["new"] - c["old"])

ROUTE = [TARGET]
while PARENT[ROUTE[-1]] is not None:
    ROUTE.append(PARENT[ROUTE[-1]])
ROUTE.reverse()
ROUTE_W = [ROADS[key(a, b)] for a, b in zip(ROUTE, ROUTE[1:])]
DIRECT = ROADS[key(SOURCE, TARGET)]


def all_routes(s, t):
    out, stack = [], [(s, (s,), 0)]
    while stack:
        u, path, cost = stack.pop()
        if u == t:
            out.append((cost, path))
            continue
        stack += [(v, path + (v,), cost + w) for v, w in ADJ[u] if v not in path]
    return sorted(out)


ROUTES = all_routes(SOURCE, TARGET)
assert ROUTES[0] == (D[TARGET], tuple(ROUTE)) and ROUTES[1][0] > D[TARGET]   # unique fastest route
assert sum(ROUTE_W) == D[TARGET] < DIRECT

# The "why" beat: finished set after two rounds, every road leaving it, and one detour.
FINISHED = ORDER[:2]
NEXT = ORDER[2]
EXITS = [(u, v, D[u] + w) for u in FINISHED for v, w in ADJ[u] if v not in FINISHED]
assert min(c for _, _, c in EXITS) == D[NEXT] and all(c >= D[NEXT] for _, _, c in EXITS)
DETOUR = ("Cafe", "Shop", "Park")                      # leave through Shop, then come back to Park
DETOUR_COST = D["Cafe"] + ROADS[key("Cafe", "Shop")] + ROADS[key("Shop", "Park")]
assert DETOUR_COST > D[NEXT]


def checks_of(i):
    return [c for c in ROUNDS[i]["checks"] if not c["done"]]


# ---------------------------------------------------------------- narration says the computed numbers
TEXT = dict(BEATS)
S = spoken
assert f"takes {S(DIRECT)} minutes" in TEXT["hook"]
assert f"{S(D[SOURCE])} for home" in TEXT["guesses"]
c0 = {c["v"]: c["new"] for c in checks_of(0)}
assert f"cafe gets {S(c0['Cafe'])}, park {S(c0['Park'])}, work {S(c0['Work'])}" in TEXT["home"]
c1 = {c["v"]: c for c in checks_of(1)}
assert f"cafe, at {S(D['Cafe'])}" in TEXT["cafe"]
assert f"park drops from {S(c1['Park']['old'])} to {S(c1['Park']['new'])}" in TEXT["cafe"]
assert f"shop gets {S(c1['Shop']['new'])}" in TEXT["cafe"]
assert f"park's {S(D[NEXT])}" in TEXT["why"] and f"costs {S(D[NEXT])} or more" in TEXT["why"]
c2 = {c["v"]: c for c in checks_of(2)}
assert f"cafe gives {S(BACK_CHECK['new'])}, worse than {S(BACK_CHECK['old'])}" in TEXT["park"]
assert f"shop drops to {S(c2['Shop']['new'])}, and work to {S(c2['Work']['new'])}" in TEXT["park"]
c3 = {c["v"]: c for c in checks_of(3)}
assert f"next, at {S(D['Shop'])}" in TEXT["shop"] and f"work drops to {S(c3['Work']['new'])}" in TEXT["shop"]
assert ", ".join(p.lower() for p in reversed(ROUTE[:-1])) in TEXT["route"]
assert f"{S(D[TARGET]).capitalize()} minutes, not {S(DIRECT)}" in TEXT["route"]


# ---------------------------------------------------------------- layout
POS = {"Home": (-3.3, 0.75), "Cafe": (-1.75, 4.1), "Park": (0.0, 1.85), "Shop": (1.75, 4.1), "Work": (3.3, 0.75)}
RAD = 0.64
NUM_SIZE = 60
NAME_SIZE = 40
WEIGHT_SIZE = 48
ROAD_W = 6
ARC_ANGLE = {("Home", "Work"): 50 * DEGREES}           # the direct road bends along the bottom
NAME_DIR = {"Home": DOWN, "Cafe": LEFT, "Park": DOWN, "Shop": RIGHT, "Work": DOWN}
NAME_BUFF = {"Home": 0.3, "Work": 0.3}                  # a little lower: the why-beat boundary passes above
HULL_NAMES = {"Cafe"}                                  # names the boundary must wrap (Home's sits below it)
# weight plate: (fraction along the road, side: +1 = left of the u->v direction, -1 = right)
# weights stay off the Park label: 5 and 6 sit above their roads, 1 and 2 in the upper face at
# different heights, the direct road's 10 hangs below the arc (outside the curve)
WEIGHT_AT = {("Home", "Cafe"): (0.5, 1), ("Home", "Park"): (0.74, 1), ("Home", "Work"): (0.5, -1),
             ("Cafe", "Park"): (0.4, 1), ("Cafe", "Shop"): (0.5, 1), ("Park", "Shop"): (0.3, 1),
             ("Park", "Work"): (0.29, 1), ("Shop", "Work"): (0.5, 1)}
# queue: a row header ("priority queue") at the left, then five cells, place name over estimate
HEADER_W, CELL_GAP, CELL_H, STRIP_Y = 1.3, 0.08, 1.25, -2.225
CELL_W = (STAGE.width - HEADER_W - 0.1 - 4 * CELL_GAP) / 5
CELL_NAME, CELL_NUM = Size.SMALL, 56
RISE, DIP = 0.67, 0.6                                  # a cell moving left rises, the ones it passes dip
FINAL_FILL = interpolate_color(ManimColor(BG), ManimColor(GREEN_K), 0.22)


def p3(v):
    return np.array([*POS[v], 0.0])


def slot_pos(i):
    x0 = STAGE.right - 5 * CELL_W - 4 * CELL_GAP + CELL_W / 2
    return np.array([x0 + i * (CELL_W + CELL_GAP), STRIP_Y, 0.0])


def fmt(val):
    return r"\infty" if val == INFTY else str(int(val))


def num_tex(val, color, size=NUM_SIZE):
    return tex(fmt(val), size=size, color=color)


def make_road(u, v):
    a, b = p3(u), p3(v)
    angle = ARC_ANGLE.get((u, v))
    if angle is None:
        unit = (b - a) / np.linalg.norm(b - a)
        return Line(a + unit * RAD, b - unit * RAD, color=MUTED, stroke_width=ROAD_W)
    arc = ArcBetweenPoints(a, b, angle=angle)
    length = np.linalg.norm(b - a) / (2 * np.sin(angle / 2)) * angle
    t = RAD / length
    road = VMobject().pointwise_become_partial(arc, t, 1 - t)
    return road.set_stroke(MUTED, width=ROAD_W).set_fill(opacity=0)


def side_normal(road, t, side):
    p0, p1 = road.point_from_proportion(max(t - 0.01, 0)), road.point_from_proportion(min(t + 0.01, 1))
    tangent = (p1 - p0) / np.linalg.norm(p1 - p0)
    left = np.array([-tangent[1], tangent[0], 0.0])
    return road.point_from_proportion(t), left * side


def beside(mob, point, normal, gap=0.1):
    """Place mob next to a line through point, on the side of normal, without touching it."""
    reach = abs(normal[0]) * mob.width / 2 + abs(normal[1]) * mob.height / 2
    return mob.move_to(point + normal * (reach + gap))


def convex_hull(points):
    pts = sorted(set((round(p[0], 4), round(p[1], 4)) for p in points))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [np.array([x, y, 0.0]) for x, y in lower[:-1] + upper[:-1]]   # counter-clockwise


def inside(hull, p):
    n = len(hull)
    return all((hull[(i + 1) % n][0] - hull[i][0]) * (p[1] - hull[i][1])
               - (hull[(i + 1) % n][1] - hull[i][1]) * (p[0] - hull[i][0]) >= 0 for i in range(n))


class Cell:
    """One queue entry: rounded box, place name, current estimate. The parts move together."""

    def __init__(self, place, val, color, slot):
        self.place = place
        self.box = RoundedRectangle(width=CELL_W, height=CELL_H, corner_radius=0.08,
                                    stroke_color=MUTED, stroke_width=4, fill_color=BG, fill_opacity=1)
        self.box.move_to(slot_pos(slot)).set_z_index(1)          # opaque box: its text must draw above it
        self.name = text(place, size=CELL_NAME, color=INK).move_to(self.box.get_top() + DOWN * 0.28)
        self.name.set_z_index(2)
        self.val = self.make_val(val, color)

    def make_val(self, val, color):
        return num_tex(val, color, CELL_NUM).move_to(self.val_anchor()).set_z_index(2)

    def val_anchor(self):
        return self.box.get_bottom() + UP * 0.42

    def parts(self):
        return [self.box, self.name, self.val]


class Short(ShortScene):
    def construct(self):
        self.roads = {k: make_road(*k) for k in ROADS}
        self.weights = {}
        for k, w in ROADS.items():
            t, side = WEIGHT_AT[k]
            point, normal = side_normal(self.roads[k], t, side)
            self.weights[k] = beside(plate(tex(str(w), size=WEIGHT_SIZE)), point, normal)
        self.circles = {v: Circle(radius=RAD, stroke_color=MUTED, stroke_width=6, fill_color=BG,
                                  fill_opacity=1).move_to(p3(v)) for v in PLACES}
        self.names = {v: text(v, size=NAME_SIZE, color=INK).next_to(self.circles[v], NAME_DIR[v],
                                                                    buff=NAME_BUFF.get(v, 0.2))
                      for v in PLACES}
        self.num = {}
        self.est = {v: INFTY for v in PLACES}
        self.est[SOURCE] = 0
        self.queue = list(PLACES)                      # kept sorted by (estimate, place order)
        self.cells = {}
        map_group = VGroup(*self.roads.values(), *self.circles.values(), *self.names.values(),
                           *self.weights.values())

        # ------------------------------------------------------------ hook
        with self.beat("hook"):
            self.title("Dijkstra trusts the smallest", FadeIn(map_group, run_time=0.9), size=44)  # 48 wraps
            direct = self.roads[key(SOURCE, TARGET)]
            dw = self.weights[key(SOURCE, TARGET)][1]
            self.cue("ten", offset=-0.25)
            self.play(direct.animate.set_stroke(YELLOW_K, width=10), dw.animate.set_color(YELLOW_K), run_time=0.45)
            self.cue("faster", offset=-0.1)
            others = [r for k, r in self.roads.items() if k != key(SOURCE, TARGET)]
            self.play(LaggedStart(*[ShowPassingFlash(r.copy().set_stroke(YELLOW_K, width=10), time_width=0.6)
                                    for r in others], lag_ratio=0.15), run_time=1.6)
            self.play(direct.animate.set_stroke(MUTED, width=ROAD_W), dw.animate.set_color(INK), run_time=0.4)

        # ------------------------------------------------------------ guesses
        with self.beat("guesses"):
            self.cue("guess", offset=-0.1)
            qs = {v: tex("?", size=NUM_SIZE, color=MUTED).move_to(p3(v)) for v in PLACES}
            self.play(LaggedStart(*[FadeIn(q, scale=0.6) for q in qs.values()], lag_ratio=0.12), run_time=0.8)
            self.cue("zero", offset=-0.15)
            self.num[SOURCE] = num_tex(0, BLUE_K).move_to(p3(SOURCE))
            self.play(FadeOut(qs[SOURCE]), self.circles[SOURCE].animate.set_stroke(BLUE_K), run_time=0.25)
            self.play(FadeIn(self.num[SOURCE], scale=1.3), run_time=0.35)
            self.cue("infinity", offset=-0.15)
            rest = [v for v in PLACES if v != SOURCE]
            for v in rest:
                self.num[v] = num_tex(INFTY, MUTED).move_to(p3(v))
            self.play(*[FadeOut(qs[v]) for v in rest], run_time=0.2)
            self.play(*[FadeIn(self.num[v], scale=1.3) for v in rest], run_time=0.4)
            self.cue("queue", offset=-0.25)
            for i, v in enumerate(self.queue):
                self.cells[v] = Cell(v, self.est[v], BLUE_K if v == SOURCE else MUTED, i)
            first = self.cells[self.queue[0]].box
            self.q_label = VGroup(text("priority", size=Size.SMALL, color=MUTED),
                                  text("queue", size=Size.SMALL, color=MUTED)).arrange(DOWN, aligned_edge=RIGHT,
                                                                                        buff=0.1)
            self.q_label.next_to(first, LEFT, buff=0.12)
            self.play(LaggedStart(*[AnimationGroup(FadeIn(self.cells[v].box), FadeIn(self.cells[v].name),
                                                   TransformFromCopy(self.num[v], self.cells[v].val))
                                    for v in self.queue], lag_ratio=0.12),
                      FadeIn(self.q_label), run_time=1.1)

        # ------------------------------------------------------------ round 1: Home
        with self.beat("home"):
            self.cue("smallest", offset=-0.1)
            self.pop(ORDER[0])
            for c in checks_of(0):
                self.cue(c["v"].lower(), offset=-0.35)
                self.relax(ORDER[0], c)

        # ------------------------------------------------------------ round 2: Cafe
        with self.beat("cafe"):
            self.cue("cafe", offset=-0.2)
            self.pop(ORDER[1])
            for c in checks_of(1):
                self.cue(c["v"].lower(), offset=-0.35)
                self.relax(ORDER[1], c)

        # ------------------------------------------------------------ why the smallest is safe
        with self.beat("why"):
            ring = Circle(radius=RAD + 0.1, stroke_color=YELLOW_K, stroke_width=5).move_to(p3(NEXT))
            ring._sk_pointer = True
            cell_hl = highlight(self.cells[NEXT].box, buff=0.06)
            self.play(FadeIn(ring, scale=1.15), FadeIn(cell_hl), run_time=0.5)   # fade, not Create: no stub
            hull = self.finished_hull(FINISHED)
            assert not any(inside(hull, self.names[v].get_corner(c)) for v in FINISHED if v not in HULL_NAMES
                           for c in (UL, UR, DL, DR))      # unwrapped names lie wholly outside the boundary
            boundary = DashedVMobject(Polygon(*hull), num_dashes=90).set_stroke(GREEN_K, width=5)
            self.play(Create(boundary), run_time=1.0)
            self.cue("leave", offset=-0.1)
            exit_roads = [self.roads[key(u, v)] for u, v, _ in EXITS]
            self.play(*[r.animate.set_stroke(YELLOW_K, width=10) for r in exit_roads], run_time=0.5)
            self.cue("every", offset=-0.1)
            landing = sorted({v for _, v, _ in EXITS if v != NEXT}, key=PLACES.index)
            rings = [Circle(radius=RAD + 0.1, stroke_color=RED_K, stroke_width=5).move_to(p3(v)) for v in landing]
            for r in rings:
                r._sk_pointer = True
            self.play(*[FadeIn(r, scale=1.15) for r in rings], run_time=0.6)
            self.cue("three", nth=1, offset=-0.1)
            self.play(Indicate(self.num[NEXT], color=YELLOW_K, scale_factor=1.3), run_time=0.7)
            self.cue("roads", offset=-0.15)
            a, b, c = DETOUR
            out_road = self.roads[key(a, b)]
            t_out = next(t for t in np.linspace(0, 1, 200) if not inside(hull, out_road.point_from_proportion(t)))
            leg1 = VMobject().pointwise_become_partial(out_road, t_out, 1).set_stroke(RED_K, width=10)
            leg2 = self.roads[key(b, c)].copy().set_stroke(RED_K, width=10)
            if key(b, c)[0] != b:
                leg2.reverse_points()
            self.play(*[r.animate.set_stroke(MUTED, width=ROAD_W) for r in exit_roads], Create(leg1), run_time=0.5)
            self.play(Create(leg2), run_time=0.45)
            detour = plate(tex(rf"\cR{{{D[a] + ROADS[key(a, b)]}+{ROADS[key(b, c)]}}} > \cY{{{D[NEXT]}}}",
                               size=44), opacity=0.95)
            free = len(self.queue)                           # the empty queue slots on the right
            detour.move_to((slot_pos(free) + slot_pos(4)) / 2)
            assert detour.width < slot_pos(4)[0] - slot_pos(free)[0] + CELL_W
            self.play(FadeIn(detour, scale=0.8), run_time=0.5)
            self.why_objects = [ring, cell_hl, boundary, *rings, leg1, leg2, detour]

        # ------------------------------------------------------------ round 3: Park
        with self.beat("park"):
            self.play(*[FadeOut(m) for m in self.why_objects], run_time=0.4)
            self.pop(ORDER[2])
            self.cue("its", prefix=True, offset=-0.2)        # edge-tts times "Its road" as one word
            cleanup = self.check_back(ORDER[2], BACK_CHECK)
            assert checks_of(2)                              # a relaxation from Park follows the check
            for c in checks_of(2):
                self.cue(c["v"].lower(), offset=-0.35)
                self.relax(ORDER[2], c, extra=cleanup)
                cleanup = []

        # ------------------------------------------------------------ rounds 4 and 5: Shop, Work
        with self.beat("shop"):
            self.pop(ORDER[3])
            for c in checks_of(3):
                self.cue(c["v"].lower(), offset=-0.35)
                self.relax(ORDER[3], c)
            self.cue("work", nth=1, offset=-0.1)
            assert not checks_of(4)
            self.pop(ORDER[4], extra=[FadeOut(self.q_label)])

        # ------------------------------------------------------------ the parent route
        with self.beat("route"):
            self.cue("work", offset=-0.1)
            self.play(Indicate(self.num[TARGET], color=GREEN_K, scale_factor=1.3), run_time=0.6)
            for v in reversed(ROUTE[1:]):
                u = PARENT[v]
                self.cue(u.lower(), offset=-0.2)
                seg = self.roads[key(u, v)].copy().set_stroke(GREEN_K, width=11)
                if key(u, v)[0] != v:
                    seg.reverse_points()                 # draw from v back to its parent
                self.play(Create(seg), self.weights[key(u, v)][1].animate.set_color(GREEN_K), run_time=0.4)
            self.cue("six", offset=-0.1)
            total = tex(rf"\cG{{{'+'.join(map(str, ROUTE_W))}={D[TARGET]}}}\ <\ \cR{{{DIRECT}}}", size=54)
            total.move_to(np.array([0, STRIP_Y, 0]))
            self.play(FadeIn(total, shift=UP * 0.15), run_time=0.6)
            self.cue("ten", offset=-0.1)
            direct = self.roads[key(SOURCE, TARGET)]
            self.play(direct.animate.set_stroke(RED_K, width=8),
                      self.weights[key(SOURCE, TARGET)][1].animate.set_color(RED_K), run_time=0.5)

        # ------------------------------------------------------------ the rule
        with self.beat("rule"):
            self.cue("dijkstra", offset=-0.1)
            rule = tex(r"d(v)\leftarrow\min\bigl(d(v),\;\cY{d(u)+w(u,v)}\;\bigr)", size=46)  # room for the outline
            if rule.width > 7.9:
                rule.scale_to_fit_width(7.9)
            rule.move_to(np.array([0, STRIP_Y + 0.62, 0]))
            self.swap(total, rule)
            self.cue("relax", offset=-0.1)
            relax_part = VGroup(*[g for g in rule if np.allclose(color_to_rgb(g.get_fill_color()),
                                                                  color_to_rgb(YELLOW_K), atol=0.03)])
            assert len(relax_part) == len("d(u)+w(u,v)")
            relax_box = highlight(relax_part, buff=0.07)
            self.play(FadeIn(relax_box), run_time=0.5)
            self.cue("no", offset=-0.1)
            nonneg = tex(r"w(u,v)\ \ge\ 0", size=50).next_to(rule, DOWN, buff=0.25)
            self.play(FadeIn(nonneg, shift=UP * 0.15), FadeOut(relax_box), run_time=0.6)

    # ---------------------------------------------------------------- queue + relaxation steps
    def pop(self, u, extra=()):
        """delete_min: the leftmost cell turns green and leaves as its place turns green (final);
        then the rest of the queue slides left."""
        assert self.queue[0] == u
        cell = self.cells.pop(u)
        self.queue.pop(0)
        self.play(cell.box.animate.set_stroke(GREEN_K, width=7), cell.name.animate.set_color(GREEN_K),
                  cell.val.animate.set_color(GREEN_K), run_time=0.35)
        self.play(FadeOut(VGroup(*cell.parts()), shift=UP * 0.35, scale=0.85),
                  self.circles[u].animate.set_stroke(GREEN_K, width=7).set_fill(FINAL_FILL, 1),
                  self.num[u].animate.set_color(GREEN_K), *extra, run_time=0.55)
        if self.queue:
            self.play(*[p.animate.shift(slot_pos(i) - slot_pos(i + 1))
                        for i, v in enumerate(self.queue) for p in self.cells[v].parts()], run_time=0.35)

    def send(self, u, v, color=YELLOW_K):
        """A dot carrying d(u) + w(u, v) runs along the road from u to v."""
        k = key(u, v)
        path = self.roads[k].copy()
        if k[0] != u:
            path.reverse_points()
        dot = Dot(path.get_start(), radius=0.12, color=color).set_z_index(3)
        return dot, MoveAlongPath(dot, path)

    def relax(self, u, c, extra=()):
        """d(v) > d(u) + w(u, v): the old value is struck and leaves, then the new one appears."""
        v, new = c["v"], c["new"]
        assert c["better"]
        k = key(u, v)
        road, wl, old = self.roads[k], self.weights[k][1], self.num[v]
        strike = Line(old.get_corner(DL) + 0.08 * DL, old.get_corner(UR) + 0.08 * UR,
                      color=RED_K, stroke_width=7).set_z_index(9)
        dot, run = self.send(u, v)
        self.play(road.animate.set_stroke(YELLOW_K, width=10), wl.animate.set_color(YELLOW_K),
                  self.num[u].animate.set_color(YELLOW_K), run, *extra, run_time=0.5)
        cell = self.cells[v]
        self.play(old.animate.set_color(RED_K), Create(strike), run_time=0.2)
        self.play(FadeOut(old), FadeOut(strike), FadeOut(dot), FadeOut(cell.val), run_time=0.2)
        new_num = num_tex(new, INK).move_to(p3(v))
        new_val = cell.make_val(new, INK)
        self.est[v] = new
        self.num[v], cell.val = new_num, new_val
        self.reorder(FadeIn(new_num, scale=1.3), FadeIn(new_val, scale=1.3),
                     self.circles[v].animate.set_stroke(INK),
                     road.animate.set_stroke(MUTED, width=ROAD_W), wl.animate.set_color(INK),
                     self.num[u].animate.set_color(GREEN_K))      # u is final

    def reorder(self, *extra):
        """decrease_key: an entry that became smaller hops left over the ones it passes, which dip."""
        order = sorted(self.queue, key=lambda p: (self.est[p], PLACES.index(p)))
        anims, moved = list(extra), False
        for v in order:
            i_old, i_new = self.queue.index(v), order.index(v)
            if i_new != i_old:
                delta = slot_pos(i_new) - slot_pos(i_old)
                sag = min(RISE if i_new < i_old else DIP, 0.49 * abs(delta[0]))
                # positive path_arc bends to the RIGHT of travel: up when moving left, down when moving right
                arc = 4 * np.arctan(2 * sag / abs(delta[0]))
                anims += [p.animate(path_arc=arc).shift(delta) for p in self.cells[v].parts()]
                moved = True
        self.queue = order
        self.play(*anims, run_time=0.6 if moved else 0.35)

    def check_back(self, u, c):
        """A road back into the finished set: the candidate is worse, nothing changes.
        Returns the clean-up animations, to play with the next step."""
        v = c["v"]
        assert c["done"] and not c["better"]
        k = key(u, v)
        road, wl = self.roads[k], self.weights[k][1]
        dot, run = self.send(u, v)
        self.play(road.animate.set_stroke(YELLOW_K, width=10), wl.animate.set_color(YELLOW_K),
                  self.num[u].animate.set_color(YELLOW_K), run, run_time=0.6)
        cand = plate(tex(rf"\cR{{{c['new']}}} > \cG{{{c['old']}}}", size=Size.HEADLINE), opacity=0.95)
        cand.move_to((slot_pos(len(self.queue)) + slot_pos(4)) / 2)   # the empty queue slots, like 8+2 > 3
        self.play(dot.animate.set_color(RED_K), FadeIn(cand, scale=0.8), run_time=0.4)
        self.cue("worse", offset=-0.1)
        self.play(Indicate(self.num[v], color=GREEN_K, scale_factor=1.3), run_time=0.6)
        # u stays yellow: the next relaxation from u uses it and turns it green again
        return [FadeOut(cand, shift=UP * 0.15), FadeOut(dot), wl.animate.set_color(INK),
                road.animate.set_stroke(MUTED, width=ROAD_W)]

    def finished_hull(self, places, pad=0.15):
        pts = []
        for v in places:
            for a in np.linspace(0, TAU, 48, endpoint=False):
                pts.append(p3(v) + (RAD + pad) * np.array([np.cos(a), np.sin(a), 0]))
            if v not in HULL_NAMES:
                continue
            name = self.names[v]
            for corner in (UL, UR, DL, DR):
                base = name.get_corner(corner)
                for a in np.linspace(0, TAU, 12, endpoint=False):
                    pts.append(base + pad * np.array([np.cos(a), np.sin(a), 0]))
        return convex_hull(pts)

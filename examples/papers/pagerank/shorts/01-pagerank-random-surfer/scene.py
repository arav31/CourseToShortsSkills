"""PageRank as a random surfer (Brin & Page 1998). See storyboard.md.

v2 layout: each page is a tall box that fills with its share of the crowd, so the link graph and
the "bar chart" are one picture that spans the whole stage.
"""

from shortkit import *

BEATS = [
    ("hook", "In 1998, Brin and Page ranked the web with one imaginary surfer who clicks links forever. Where does that surfer spend its time?"),
    ("links", "Take four pages and five links. C has three links coming in. A has only one."),
    ("surfer", "On each page, the surfer clicks one of its links at random. But fifteen percent of the time, they get bored and jump to any page at all."),
    ("crowd", "Now swap the one surfer for a crowd, with a quarter of it on each page."),
    ("tick", "Each tick, eighty-five percent of every crowd follows the links, split evenly. The other fifteen percent scatter over all four pages."),
    ("step", "After one tick, C holds fifty-seven percent: half of A's crowd, plus everyone from B and D."),
    ("settle", "Keep ticking. The shares swing, then settle: A thirty-seven, B twenty, C thirty-nine, D four percent. Those shares are PageRank."),
    ("insight", "Look at A. It has one link in, yet almost ties C, because that link comes from C, the busiest page, and C sends A everyone."),
    ("lonely", "D has no links in, so it only ever gets the random jumpers."),
    ("takeaway", "So a link is a vote, worth the voter's own rank, split among all its links."),
]

# ---------------------------------------------------------------- the model (computed, never typed)
PAGES = "ABCD"
LINKS = {"A": "BC", "B": "C", "C": "A", "D": "C"}
D_DAMP = 0.85
N = len(PAGES)
JUMP = (1 - D_DAMP) / N  # 0.0375


def tick(pr):
    new = {p: JUMP for p in PAGES}
    for q, outs in LINKS.items():
        for p in outs:
            new[p] += D_DAMP * pr[q] / len(outs)
    return new


HIST = [{p: 1 / N for p in PAGES}]
for _ in range(80):
    HIST.append(tick(HIST[-1]))
FINAL = HIST[-1]
SETTLE_TICKS = 12
pct = lambda v: round(100 * v)  # noqa: E731
STEP1 = HIST[1]
FIN = {p: pct(FINAL[p]) for p in PAGES}
assert abs(sum(FINAL.values()) - 1) < 1e-12
assert all(pct(HIST[SETTLE_TICKS][p]) == FIN[p] for p in PAGES)
assert spoken(pct(STEP1["C"])) in BEATS[5][1]
assert spoken(round(100 * D_DAMP)) in BEATS[4][1] and spoken(round(100 * (1 - D_DAMP))) in BEATS[4][1]
for p in PAGES:
    assert f"{p} {spoken(FIN[p])}" in BEATS[6][1]
INCOMING = {p: [q for q, outs in LINKS.items() if p in outs] for p in PAGES}
assert len(INCOMING["C"]) == 3 and len(INCOMING["A"]) == 1 and not INCOMING["D"]

NODE_COL = {"A": BLUE_K, "B": PURPLE_K, "C": ORANGE_K, "D": "#C9D1DC"}
FULL = 0.60          # a box is full at 60 % (tick 1 peaks at 57 %)
BW, BH = 1.8, 2.1    # page box size
CX = 4.1 - 0.12 - BW / 2          # box centre x (right column); left column is -CX
TOP_Y = 4.8 - 0.55 - BH / 2       # label above the top boxes
BOT_Y = -2.7 + 0.55 + BH / 2      # label below the bottom boxes
POS = {"A": np.array([-CX, TOP_Y, 0]), "B": np.array([CX, TOP_Y, 0]),
       "C": np.array([CX, BOT_Y, 0]), "D": np.array([-CX, BOT_Y, 0])}
GAP = 0.12


def edge_point(p, direction):
    """Where a ray from page p's centre leaves its box (plus a small gap)."""
    d = np.array(direction, dtype=float)
    d = d / np.linalg.norm(d)
    t = min((BW / 2) / abs(d[0]) if abs(d[0]) > 1e-9 else 1e9, (BH / 2) / abs(d[1]) if abs(d[1]) > 1e-9 else 1e9)
    return POS[p] + d * (t + GAP)


def link_ends(q, p):
    """Start/end points of the link q->p; the two diagonals A<->C run side by side."""
    d = POS[p] - POS[q]
    off = np.zeros(3)
    if {q, p} == {"A", "C"}:
        ac = POS["C"] - POS["A"]
        nrm = np.array([-ac[1], ac[0], 0]) / np.linalg.norm(ac)
        off = nrm * (0.3 if q == "A" else -0.3)
    s = edge_point(q, d) + off
    e = edge_point(p, -d) + off
    return s, e


class Short(ShortScene):
    def construct(self):
        # ---------------- page boxes that fill with their share
        trk = {p: ValueTracker(0.0) for p in PAGES}
        boxes, fills, letters, pcts = {}, {}, {}, {}
        for p in PAGES:
            boxes[p] = Rectangle(width=BW, height=BH, color=NODE_COL[p], stroke_width=6).move_to(POS[p]).set_z_index(2)
            letters[p] = tex(p, size=Size.HEADLINE + 10, color=INK).move_to(POS[p]).set_z_index(3)

            def mk_fill(p=p):
                h = max(min(trk[p].get_value() / FULL, 1.0) * (BH - 0.08), 0.001)
                return Rectangle(width=BW - 0.08, height=h, stroke_width=0, fill_color=NODE_COL[p],
                                 fill_opacity=0.55).move_to(POS[p] + DOWN * (BH / 2 - 0.04), aligned_edge=DOWN).set_z_index(1)

            fills[p] = always_redraw(mk_fill)
        page_group = VGroup(*boxes.values(), *letters.values())
        for p in PAGES:
            self.allow_overlap(letters[p], fills[p])  # the letter sits on its own fill level by design

        def make_pct(p):
            lt = live_text(lambda: f"{100 * trk[p].get_value():.0f}%", size=Size.BODY, color=NODE_COL[p])
            side = UP if p in "AB" else DOWN
            lt.next_to(boxes[p], side, buff=0.1)
            return lt

        links = {(q, p): link_ends(q, p) for q, outs in LINKS.items() for p in outs}
        arrows = {k: Arrow(s, e, buff=0, color=MUTED, stroke_width=6, tip_length=0.3,
                           max_tip_length_to_length_ratio=0.15) for k, (s, e) in links.items()}

        def path(q, p):
            s, e = links[(q, p)]
            return Line(s, e)

        def blob(at, amount, color=YELLOW_K):
            return Dot(at, radius=0.1 + 0.6 * np.sqrt(amount), color=color, fill_opacity=0.9).set_z_index(5)

        mid_y = (TOP_Y + BOT_Y) / 2
        side_slot = np.array([-CX + 0.15, mid_y, 0])  # free spot between A and D (no A-D link)

        # ---------------- hook
        with self.beat("hook"):
            credit = VGroup(
                text("Brin & Page, 1998", size=Size.LABEL, color=INK),
                text("The Anatomy of a Large-Scale Hypertextual Web Search Engine", size=Size.SMALL,
                     color=MUTED, width=4.0),
            ).arrange(DOWN, buff=0.15)
            credit_p = plate(credit).move_to([0, mid_y, 0])
            self.title("PageRank: the random surfer", FadeIn(page_group), run_time=0.8)
            self.play(FadeIn(credit_p, shift=UP * 0.15), run_time=0.8)
            self.cue("surfer")
            dot = Dot(POS["A"] + DOWN * 0.6, radius=0.17, color=YELLOW_K).set_z_index(6)
            self.play(FadeIn(dot, scale=1.8), run_time=0.4)
            self.cue("clicks")
            for p in "BC":
                self.play(dot.animate.move_to(POS[p] + DOWN * 0.6), run_time=0.7)

        # ---------------- links
        with self.beat("links"):
            self.play(FadeOut(credit_p), FadeOut(dot), run_time=0.4)
            self.play(LaggedStart(*[GrowArrow(a) for a in arrows.values()], lag_ratio=0.2), run_time=1.4)
            self.cue("C", nth=0)
            into_c = [arrows[(q, "C")] for q in INCOMING["C"]]
            self.play(*[a.animate.set_color(ORANGE_K) for a in into_c], Indicate(boxes["C"], color=ORANGE_K, scale_factor=1.08),
                      run_time=1.0)
            self.cue("A", nth=0)
            self.play(*[a.animate.set_color(MUTED) for a in into_c],
                      arrows[("C", "A")].animate.set_color(BLUE_K), Indicate(boxes["A"], color=BLUE_K, scale_factor=1.08),
                      run_time=1.0)

        # ---------------- surfer
        with self.beat("surfer"):
            self.play(arrows[("C", "A")].animate.set_color(MUTED), run_time=0.3)
            dot.move_to(POS["A"] + DOWN * 0.6)
            self.play(FadeIn(dot, scale=1.6), run_time=0.4)
            for q, p in [("A", "B"), ("B", "C"), ("C", "A")]:
                self.play(dot.animate.move_to(links[(q, p)][0]), run_time=0.15)
                self.play(MoveAlongPath(dot, path(q, p)), arrows[(q, p)].animate.set_color(YELLOW_K), run_time=0.6)
                self.play(dot.animate.move_to(POS[p] + DOWN * 0.6), arrows[(q, p)].animate.set_color(MUTED), run_time=0.15)
            self.cue("bored")
            self.play(FadeOut(dot, scale=0.3), run_time=0.4)
            dot.move_to(POS["D"] + DOWN * 0.6)
            self.play(FadeIn(dot, scale=2.0), Indicate(boxes["D"], color=YELLOW_K, scale_factor=1.08), run_time=0.6)
            self.play(dot.animate.move_to(links[("D", "C")][0]), run_time=0.15)
            self.play(MoveAlongPath(dot, path("D", "C")), arrows[("D", "C")].animate.set_color(YELLOW_K), run_time=0.6)
            self.play(dot.animate.move_to(POS["C"] + DOWN * 0.6), arrows[("D", "C")].animate.set_color(MUTED), run_time=0.15)

        # ---------------- crowd
        with self.beat("crowd"):
            for p in PAGES:
                pcts[p] = make_pct(p)
            self.add(*fills.values())
            self.play(FadeOut(dot), *[FadeIn(pcts[p]) for p in PAGES], run_time=0.5)
            self.play(*[trk[p].animate.set_value(HIST[0][p]) for p in PAGES], run_time=1.2)
            k_trk = ValueTracker(0)
            k_lab = live_text(lambda: f"tick {int(round(k_trk.get_value()))}", size=Size.LABEL, color=YELLOW_K)
            k_lab.move_to([0, mid_y + 0.35, 0]).align_to(boxes["A"], LEFT)
            self.play(FadeIn(k_lab), run_time=0.4)

        # ---------------- tick: the flow
        with self.beat("tick"):
            blobs, moves = [], []
            for (q, p) in arrows:
                b = blob(links[(q, p)][0], D_DAMP * HIST[0][q] / len(LINKS[q]))
                blobs.append(b)
                moves.append(MoveAlongPath(b, path(q, p)))
            self.play(*[FadeIn(b, scale=0.4) for b in blobs], run_time=0.5)
            self.play(*moves, run_time=1.6)
            self.play(*[FadeOut(b, scale=0.5) for b in blobs], run_time=0.4)
            self.cue("other")
            jump = plate(tex(r"15\%\div 4=3.75\%", size=Size.LABEL, color=YELLOW_K))
            jump.move_to([0, mid_y - 0.4, 0]).align_to(boxes["A"], LEFT)
            drops = [blob(jump.get_center(), JUMP) for _ in PAGES]
            self.play(FadeIn(jump), run_time=0.5)
            self.play(*[dr.animate.move_to(POS[p]).set_opacity(0) for dr, p in zip(drops, PAGES)], run_time=1.0)
            self.remove(*drops)

        # ---------------- step 1 result
        with self.beat("step"):
            self.play(*[trk[p].animate.set_value(STEP1[p]) for p in PAGES], k_trk.animate.set_value(1), run_time=1.2)
            self.cue("half")
            into_c = [arrows[(q, "C")] for q in INCOMING["C"]]
            self.play(*[a.animate.set_color(ORANGE_K).set_stroke(width=9) for a in into_c],
                      boxes["C"].animate.set_stroke(width=11), run_time=0.8)

        # ---------------- settle
        with self.beat("settle"):
            self.play(FadeOut(jump), *[a.animate.set_color(MUTED).set_stroke(width=6) for a in into_c],
                      boxes["C"].animate.set_stroke(width=6), run_time=0.4)
            for k in range(2, SETTLE_TICKS + 1):
                rt = max(0.25, 0.85 - 0.08 * (k - 2))
                self.play(*[trk[p].animate.set_value(HIST[k][p]) for p in PAGES], k_trk.animate.set_value(k),
                          run_time=rt)
            self.play(*[trk[p].animate.set_value(FINAL[p]) for p in PAGES], run_time=0.3)
            self.cue("Those")
            tag = plate(text("PageRank", size=Size.BODY, color=GREEN_K, weight=BOLD)).move_to([0, mid_y - 0.4, 0]).align_to(boxes["A"], LEFT)
            self.play(FadeOut(k_lab), FadeIn(tag), *[pcts[p].animate.set_color(GREEN_K) for p in PAGES], run_time=0.6)

        # ---------------- insight
        with self.beat("insight"):
            ca = arrows[("C", "A")]
            self.play(ca.animate.set_color(GREEN_K).set_stroke(width=11), run_time=0.8)
            self.cue("almost")
            self.play(boxes["A"].animate.set_stroke(GREEN_K, width=11), boxes["C"].animate.set_stroke(GREEN_K, width=11),
                      run_time=0.7)
            self.cue("sends")
            b = blob(links[("C", "A")][0], D_DAMP * FINAL["C"], color=GREEN_K)
            self.play(FadeIn(b), run_time=0.3)
            self.play(MoveAlongPath(b, path("C", "A")), run_time=1.0)
            self.play(FadeOut(b), run_time=0.3)

        # ---------------- lonely
        with self.beat("lonely"):
            self.play(ca.animate.set_color(MUTED).set_stroke(width=6),
                      boxes["A"].animate.set_stroke(NODE_COL["A"], width=6),
                      boxes["C"].animate.set_stroke(NODE_COL["C"], width=6), run_time=0.5)
            self.play(boxes["D"].animate.set_stroke(RED_K, width=11), pcts["D"].animate.set_color(RED_K), run_time=0.8)

        # ---------------- takeaway
        with self.beat("takeaway"):
            formula = tex(rf"PR(p)=\frac{{\cY{{{1 - D_DAMP:.2f}}}}}{{{N}}}+\cY{{{D_DAMP}}}\sum_{{q\to p}}\frac{{PR(q)}}{{\text{{links out of }}q}}",
                          size=Size.HEADLINE)
            body = formula
            if body.width > 7.7:
                body.scale_to_fit_width(7.7)
            fp = plate(body, opacity=0.95)
            fp.move_to([0, mid_y, 0])
            self.play(FadeOut(tag), *[FadeOut(a) for a in arrows.values()],
                      boxes["D"].animate.set_stroke(NODE_COL["D"], width=6), pcts["D"].animate.set_color(GREEN_K),
                      run_time=0.6)
            self.play(FadeIn(fp, shift=DOWN * 0.15), run_time=0.9)

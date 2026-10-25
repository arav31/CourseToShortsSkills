"""s01: How lemons empty a car market (Akerlof 1970, Section II). See storyboard.md."""

from fractions import Fraction as F

from shortkit import *

BEATS = [
    ("hook", "Four owners are selling used cars, and every buyer values each car more than its owner does. So why do the good cars never sell?"),
    ("source", "George Akerlof's 1970 paper, The Market for Lemons, found the catch. Owners know what their car is worth, but buyers can't tell the cars apart."),
    ("average", "So buyers pay for the average car. The average is eight thousand dollars, and a buyer will pay one and a half times that: twelve thousand."),
    ("round1", "But the best car is worth fourteen thousand to its owner. At twelve, she keeps it."),
    ("round2", "Now the average of what's left is six thousand, so the offer drops to nine, and the ten thousand dollar car leaves too."),
    ("round3", "Average four, offer six. The seven thousand dollar car goes."),
    ("lemon", "Only the one thousand dollar lemon is left. Buyers offer fifteen hundred, and it is the only car that sells."),
    ("loss", "If buyers could see quality, all four cars would sell, for sixteen thousand dollars of gains. Hidden quality leaves just five hundred."),
    ("takeaway", "That's adverse selection. The price can only follow the average, so the bad cars drive the good ones out of the market."),
]

# ---- the model (same as runs/paper-lemons/checks/examples.py) ----
CARS = [1, 7, 10, 14]   # owners' values, $ thousands
MARKUP = F(3, 2)


def unravel(cars):
    rounds, on_sale = [], list(cars)
    while True:
        avg = F(sum(on_sale), len(on_sale))
        offer = MARKUP * avg
        stay = [v for v in on_sale if v <= offer]
        rounds.append((list(on_sale), avg, offer, [v for v in on_sale if v > offer]))
        if stay == on_sale:
            return rounds
        on_sale = stay


ROUNDS = unravel(CARS)
assert [r[3] for r in ROUNDS] == [[14], [10], [7], []]
GAIN_SEEN = sum((MARKUP - 1) * v for v in CARS)        # 16
GAIN_HIDDEN = (MARKUP - 1) * ROUNDS[-1][0][0]           # 1/2


def num(x) -> str:
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else f"{float(x):g}"


def dollars_spoken(k) -> str:  # k in $ thousands
    k = F(k)
    if k == F(3, 2):
        return "fifteen hundred"
    if k == F(1, 2):
        return "five hundred"
    return f"{spoken(int(k))} thousand"


assert spoken(int(ROUNDS[0][1])) in BEATS[2][1] and spoken(int(ROUNDS[0][2])) in BEATS[2][1]
assert spoken(CARS[3]) in BEATS[3][1] and spoken(int(ROUNDS[0][2])) in BEATS[3][1]
assert spoken(int(ROUNDS[1][1])) in BEATS[4][1] and spoken(int(ROUNDS[1][2])) in BEATS[4][1]
assert spoken(int(ROUNDS[2][1])) in BEATS[5][1] and spoken(int(ROUNDS[2][2])) in BEATS[5][1]
assert dollars_spoken(ROUNDS[3][2]) in BEATS[6][1]
assert dollars_spoken(GAIN_SEEN) in BEATS[7][1] and dollars_spoken(GAIN_HIDDEN) in BEATS[7][1]

# ---- layout ----
BAND, CHART = STAGE.rows(1.15, 6.0, gap=0.2)
BASE_Y = CHART.bottom + 1.05           # room for car icons and $ labels under the baseline
TOP_V = 22
K = (CHART.top - BASE_Y) / TOP_V        # scene units per $1k
AX_X = -3.55
BAR_X = [-2.55, -1.3, -0.05, 1.2]
BAR_W = 0.95
LINE_END = 1.85
LABEL_X = 2.85
STACK_X = [2.4, 3.45]
STACK_W = 0.8


def y_of(v) -> float:
    return BASE_Y + float(v) * K


def bar(x, lo, hi, color, opacity=1.0, stroke=0.0):
    r = Rectangle(width=BAR_W, height=max((float(hi) - float(lo)) * K, 0.02))
    r.set_fill(color, opacity=opacity).set_stroke(color, width=stroke)
    r.move_to([x, (y_of(lo) + y_of(hi)) / 2, 0])
    return r


def car_icon(color=BLUE_K):
    body = RoundedRectangle(width=0.66, height=0.2, corner_radius=0.07).set_fill(color, 1).set_stroke(width=0)
    cab = RoundedRectangle(width=0.36, height=0.16, corner_radius=0.06).set_fill(color, 1).set_stroke(width=0)
    cab.next_to(body, UP, buff=-0.02)
    w1 = Circle(radius=0.075).set_fill(BG, 1).set_stroke(color, width=3).move_to(body.get_bottom() + LEFT * 0.18)
    w2 = w1.copy().move_to(body.get_bottom() + RIGHT * 0.18)
    return VGroup(cab, body, w1, w2)


def hline(v, color, dashed=False):
    a, b = [AX_X, y_of(v), 0], [LINE_END, y_of(v), 0]
    ln = DashedLine(a, b, dash_length=0.12, color=color, stroke_width=5) if dashed else Line(a, b, color=color, stroke_width=6)
    return ln


def line_label(name, v, color, above):
    lab = plate(tex(rf"\text{{{name}}}\ {num(v)}", size=Size.LABEL, color=color))
    lab.move_to([LABEL_X, y_of(v), 0])
    # offer label sits just above its line, average label just below: they never collide
    return lab.shift(UP * (lab.height / 2 + 0.04)) if above else lab.shift(DOWN * (lab.height / 2 + 0.04))


def readout(on_sale, avg, offer):
    s = "+".join(str(v) for v in on_sale)
    if len(on_sale) > 1:
        l1 = rf"\cB{{\text{{average}}}}=\tfrac{{{s}}}{{{len(on_sale)}}}=\cB{{{num(avg)}}}"
    else:
        l1 = rf"\cB{{\text{{average}}}}=\cB{{{num(avg)}}}"
    l2 = rf"\cY{{\text{{offer}}}}=1.5\times{num(avg)}=\cY{{{num(offer)}}}"
    g = VGroup(tex(l1, size=Size.BODY), tex(l2, size=Size.BODY)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
    BAND.fit(g, buff=0.02, upscale=False)
    return g


class Short(ShortScene):
    def construct(self):
        # axis
        axis = Line([AX_X, BASE_Y, 0], [AX_X, y_of(TOP_V), 0], color=MUTED, stroke_width=3)
        baseline = Line([AX_X, BASE_Y, 0], [LINE_END + 0.1, BASE_Y, 0], color=MUTED, stroke_width=3)
        ticks = VGroup(*[Line([AX_X - 0.08, y_of(t), 0], [AX_X + 0.08, y_of(t), 0], color=MUTED, stroke_width=3)
                         for t in (5, 10, 15, 20)])
        tick_nums = VGroup(*[tex(str(t), size=Size.SMALL, color=MUTED).next_to([AX_X - 0.1, y_of(t), 0], LEFT, buff=0.08)
                             for t in (5, 10, 15, 20)])
        unit = tex(r"\$\text{k}", size=Size.SMALL, color=MUTED).next_to([AX_X, y_of(TOP_V), 0], RIGHT, buff=0.15)
        frame = VGroup(axis, baseline, ticks, tick_nums, unit)

        bars = [bar(x, 0, v, BLUE_K) for x, v in zip(BAR_X, CARS)]
        icons = [car_icon().move_to([x, BASE_Y - 0.3, 0]) for x in BAR_X]
        vlabels = [tex(rf"\${v}\text{{k}}", size=Size.LABEL, color=BLUE_K).move_to([x, BASE_Y - 0.78, 0])
                   for x, v in zip(BAR_X, CARS)]
        caps = [bar(x, v, MARKUP * v, GREEN_K, opacity=0.55, stroke=2) for x, v in zip(BAR_X, CARS)]
        idx = {v: i for i, v in enumerate(CARS)}

        with self.beat("hook"):
            self.title("Why good used cars vanish", FadeIn(frame))
            self.play(LaggedStart(*[AnimationGroup(GrowFromEdge(b, DOWN), FadeIn(c, shift=UP * 0.1), FadeIn(l))
                                    for b, c, l in zip(bars, icons, vlabels)], lag_ratio=0.25), run_time=2.0)
            self.cue("buyer")
            self.play(LaggedStart(*[GrowFromEdge(c, DOWN) for c in caps], lag_ratio=0.15), run_time=1.4)
            buyer_tag = tex(r"\cG{\text{buyer value}}=1.5\times\cB{\text{owner value}}", size=Size.BODY)
            BAND.fit(buyer_tag, buff=0.02, upscale=False)
            self.play(FadeIn(buyer_tag), run_time=0.6)

        with self.beat("source"):
            cite = VGroup(
                tex(r"\text{George Akerlof (1970)}", size=Size.LABEL, color=MUTED),
                tex(r"\text{The Market for ``Lemons''}", size=Size.BODY),
            ).arrange(DOWN, buff=0.12)
            BAND.fit(cite, buff=0.02, upscale=False)
            self.play(FadeOut(buyer_tag), *[c.animate.set_opacity(0.18) for c in caps], run_time=0.5)
            self.play(FadeIn(cite, shift=DOWN * 0.15), run_time=0.6)
            self.cue("Owners")
            self.play(LaggedStart(*[Indicate(l, color=INK) for l in vlabels], lag_ratio=0.2), run_time=1.2)
            self.cue("buyers")
            avg0 = ROUNDS[0][1]
            ghosts = [bar(x, 0, avg0, MUTED, opacity=0.5, stroke=3).set_stroke(INK, width=3) for x in BAR_X]
            qs = [tex("?", size=Size.HEADLINE, color=INK).move_to(g.get_center()) for g in ghosts]
            self.play(*[TransformFromCopy(b, g) for b, g in zip(bars, ghosts)], run_time=1.3)
            self.play(LaggedStart(*[FadeIn(q, scale=0.6) for q in qs], lag_ratio=0.15), run_time=0.8)

        on_sale, avg, offer, leave = ROUNDS[0]
        with self.beat("average"):
            avg_line = hline(avg, BLUE_K, dashed=True)
            avg_lab = line_label("average", avg, BLUE_K, above=False)
            ro = readout(on_sale, avg, offer)
            # the four identical "buyer's view" boxes flatten into one level: the average
            self.play(FadeOut(cite, shift=UP * 0.15), FadeOut(VGroup(*qs)),
                      *[g.animate.stretch_to_fit_height(0.05).move_to([g.get_x(), y_of(avg), 0]).set_opacity(0.6)
                        for g in ghosts], run_time=0.9)
            self.play(FadeOut(VGroup(*ghosts)), Create(avg_line), run_time=0.5)
            self.play(FadeIn(avg_lab), FadeIn(ro[0]), run_time=0.7)
            self.cue("one", offset=-0.1)
            offer_line = hline(avg, YELLOW_K)
            self.add(offer_line)
            target = hline(offer, YELLOW_K)
            off_lab = line_label("offer", offer, YELLOW_K, above=True)
            self.play(Transform(offer_line, target), FadeIn(ro[1]), run_time=1.2)
            self.play(FadeIn(off_lab), run_time=0.5)

        def leave_bar(v):
            i = idx[v]
            self.play(bars[i].animate.set_fill(RED_K), Indicate(vlabels[i], color=RED_K), run_time=0.7)
            self.play(bars[i].animate.set_fill(MUTED, opacity=0.25).set_stroke(MUTED, width=2),
                      icons[i].animate.set_opacity(0.3), vlabels[i].animate.set_opacity(0.35),
                      caps[i].animate.set_opacity(0.06), run_time=0.8)

        with self.beat("round1"):
            self.cue("fourteen")
            self.play(Indicate(bars[idx[leave[0]]], color=RED_K, scale_factor=1.05), run_time=0.8)
            self.cue("keeps")
            leave_bar(leave[0])

        state = {"ro": ro, "avg_lab": avg_lab, "off_lab": off_lab}

        def step(r, cue_avg, cue_offer, t=1.0):
            on_sale, avg, offer, leave = r
            new_ro = readout(on_sale, avg, offer)
            new_avg_lab = line_label("average", avg, BLUE_K, above=False)
            new_off_lab = line_label("offer", offer, YELLOW_K, above=True)
            self.cue(cue_avg)
            self.play(avg_line.animate.move_to([avg_line.get_center()[0], y_of(avg), 0]),
                      FadeOut(state["avg_lab"]), FadeOut(state["ro"][0]), run_time=0.8 * t)
            self.play(FadeIn(new_avg_lab), FadeIn(new_ro[0]), run_time=0.4 * t)
            self.cue(cue_offer)
            self.play(offer_line.animate.move_to([offer_line.get_center()[0], y_of(offer), 0]),
                      FadeOut(state["off_lab"]), FadeOut(state["ro"][1]), run_time=0.8 * t)
            self.play(FadeIn(new_off_lab), FadeIn(new_ro[1]), run_time=0.4 * t)
            state.update(ro=VGroup(new_ro[0], new_ro[1]), avg_lab=new_avg_lab, off_lab=new_off_lab)
            return leave

        with self.beat("round2"):
            gone = step(ROUNDS[1], "average", "drops")
            self.cue("ten")
            leave_bar(gone[0])

        with self.beat("round3"):
            gone = step(ROUNDS[2], "Average", "offer", t=0.6)
            self.cue("seven")
            leave_bar(gone[0])

        with self.beat("lemon"):
            on_sale, avg, offer, _ = ROUNDS[3]
            lemon = idx[on_sale[0]]
            self.play(bars[lemon].animate.set_fill(RED_K), icons[lemon].animate.set_color(RED_K),
                      vlabels[lemon].animate.set_color(RED_K), run_time=0.7)
            step(ROUNDS[3], "left", "fifteen")
            sold = plate(tex(r"\cG{\text{sold}}", size=Size.LABEL)).next_to(bars[lemon], UP, buff=0.35)
            self.cue("sells")
            self.play(FadeIn(sold, shift=DOWN * 0.15), Indicate(icons[lemon], color=GREEN_K), run_time=0.8)

        with self.beat("loss"):
            self.play(FadeOut(VGroup(avg_line, offer_line, state["avg_lab"], state["off_lab"], state["ro"], sold)),
                      *[c.animate.set_opacity(0.55) for c in caps], run_time=0.8)
            seen_hdr = tex(r"\text{seen}", size=Size.SMALL, color=GREEN_K)
            hidden_hdr = tex(r"\text{hidden}", size=Size.SMALL, color=RED_K)
            seen_hdr.move_to([STACK_X[0], BASE_Y - 0.45, 0])
            hidden_hdr.move_to([STACK_X[1], BASE_Y - 0.45, 0])
            # the four gain caps stack into one column, on the same $ axis
            stack, y0 = [], 0
            for c, v in zip(caps, CARS):
                h = (MARKUP - 1) * v
                stack.append(bar(STACK_X[0], y0, y0 + h, GREEN_K, opacity=0.75, stroke=2).set_stroke(BG, width=2).stretch_to_fit_width(STACK_W))
                y0 += h
            assert y0 == GAIN_SEEN
            seen_total = plate(tex(rf"\cG{{\${num(GAIN_SEEN)}\text{{k}}}}", size=Size.LABEL)).next_to(stack[-1], UP, buff=0.15)
            self.play(FadeIn(seen_hdr), LaggedStart(*[TransformFromCopy(c, s) for c, s in zip(caps, stack)], lag_ratio=0.2),
                      run_time=1.6)
            self.play(FadeIn(seen_total, shift=DOWN * 0.1), run_time=0.5)
            self.cue("Hidden")
            hid = bar(STACK_X[1], 0, GAIN_HIDDEN, RED_K, opacity=0.8, stroke=2).stretch_to_fit_width(STACK_W)
            hid_total = plate(tex(rf"\cR{{\${num(GAIN_HIDDEN)}\text{{k}}}}", size=Size.LABEL)).next_to(hid, UP, buff=0.15)
            self.play(FadeIn(hidden_hdr), TransformFromCopy(caps[lemon], hid),
                      *[caps[i].animate.set_opacity(0.12) for i in range(len(CARS)) if i != lemon], run_time=1.0)
            self.play(FadeIn(hid_total, shift=DOWN * 0.1), run_time=0.5)

        with self.beat("takeaway"):
            rule = VGroup(
                tex(r"\cY{\text{offer}}=1.5\times\cB{\text{average of cars still for sale}}", size=Size.LABEL),
                tex(r"\text{Akerlof (1970): the bad drive out the good}", size=Size.SMALL, color=MUTED),
            ).arrange(DOWN, buff=0.16)
            BAND.fit(rule, buff=0.02, upscale=False)
            self.play(FadeIn(rule[0], shift=DOWN * 0.15), run_time=0.9)
            self.cue("bad")
            self.play(Indicate(bars[lemon], color=RED_K, scale_factor=1.15), FadeIn(rule[1]), run_time=0.9)
            self.cue("good")
            self.play(LaggedStart(*[Indicate(bars[i], color=MUTED, scale_factor=1.04) for i in range(len(CARS)) if i != lemon],
                                  lag_ratio=0.2), run_time=1.2)

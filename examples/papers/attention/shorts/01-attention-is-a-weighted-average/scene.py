"""Scaled dot-product attention as a weighted average (Vaswani et al. 2017, section 3.2.1).

Storyboard: see storyboard.md. Numbers are computed here and match checks/examples.py.
"""

import math

from shortkit import *

BEATS = [
    ("hook", "When a Transformer reads the word sat, how does it decide which other words matter?"),
    ("paper", "This is the core idea of the 2017 paper Attention Is All You Need, by Ashish Vaswani and seven colleagues."),
    ("keys", "Sat sends out a query, the vector one, two. Every word, sat included, holds up a key."),
    ("scores", "Multiply query and key entry by entry, and add. That dot product scores each word: one, three, and two."),
    ("scale", "Then divide every score by the square root of two, the key length, so the numbers stay tame."),
    ("softmax", "A softmax turns the scores into weights that are positive and add up to one: point one four, point five eight, and point two eight."),
    ("values", "Each word also carries a value. Here, three points: four, zero. Four, four. And zero, four."),
    ("blend", "The output is the weighted average of the values: a little of the, mostly cat, some sat. It lands near two point nine, three point four."),
    ("takeaway", "That is attention: compare the query with every key, scale, softmax, and average the values."),
]

TOKENS = ["the", "cat", "sat"]
COLORS = [PURPLE_K, ORANGE_K, BLUE_K]
Q = (1, 2)                               # query of "sat"
KEYS = [(1, 0), (1, 1), (0, 1)]
VALUES = [(4, 0), (4, 4), (0, 4)]
D_K = 2

SCORES = [Q[0] * k[0] + Q[1] * k[1] for k in KEYS]
SCALED = [s / math.sqrt(D_K) for s in SCORES]
_E = [math.exp(s) for s in SCALED]
W = [e / sum(_E) for e in _E]
OUTPUT = tuple(sum(W[i] * VALUES[i][j] for i in range(3)) for j in range(2))
W2 = [round(w, 2) for w in W]
OUT1 = tuple(round(x, 1) for x in OUTPUT)

assert SCORES == [1, 3, 2]
assert all(spoken(s) in BEATS[3][1] for s in SCORES)
assert all(spoken(w).replace("zero ", "") in BEATS[5][1] for w in W2)
assert abs(sum(W2) - 1) < 1e-9
assert all(spoken(x) in BEATS[7][1] for x in OUT1)

CARD_X = [-2.75, 0.0, 2.75]
CARD_TOP, CARD_H, CARD_W = 4.75, 1.4, 2.45
BASE_Y = 1.15                            # bar baseline
BAR_W = 1.15
SCORE_UNIT = 0.55                        # scene units per score point
WEIGHT_UNIT = 2.6                        # scene units per unit of weight
BAND = Zone("band", -4.1, 4.1, -2.7, 0.9)          # below the bars
VAL_ZONE = Zone("values", -4.1, 0.1, -2.7, 0.9)
READ_ZONE = Zone("readout", 0.35, 4.1, -2.7, 0.75)


def bar(i, height, opacity=0.85):
    h = max(height, 0.02)
    r = Rectangle(width=BAR_W, height=h, stroke_width=0, fill_color=COLORS[i], fill_opacity=opacity)
    r.move_to([CARD_X[i], BASE_Y + h / 2, 0])
    return r


def bar_label(i, s, height, color=INK):
    return tex(s, size=Size.LABEL, color=color).move_to([CARD_X[i], BASE_Y + height + 0.3, 0])


def coord(p):
    return rf"({p[0]},\,{p[1]})"


class Short(ShortScene):
    def construct(self):
        # ---- persistent objects ------------------------------------------------
        cards, words, keys = VGroup(), VGroup(), VGroup()
        for i, tok in enumerate(TOKENS):
            box = RoundedRectangle(width=CARD_W, height=CARD_H, corner_radius=0.15,
                                   stroke_color=COLORS[i], stroke_width=4, fill_color=BG, fill_opacity=1)
            box.move_to([CARD_X[i], CARD_TOP - CARD_H / 2, 0])
            w = text(tok, size=Size.HEADLINE, color=COLORS[i], weight=BOLD).move_to(box.get_top() + DOWN * 0.42)
            k = tex(r"\cB{k}=" + coord(KEYS[i]), size=Size.LABEL).move_to(box.get_bottom() + UP * 0.4)
            cards.add(box)
            words.add(w)
            keys.add(k)
        baseline = Line([-4.05, BASE_Y, 0], [4.05, BASE_Y, 0], color=MUTED, stroke_width=3)

        # the working, one line per step, laid out once so nothing jumps later
        steps = VGroup(
            tex(r"\text{query of sat: }\cY{q}=" + coord(Q), size=Size.LABEL),
            tex(rf"\cY{{q}}\cdot\cB{{k}}_{{\text{{cat}}}}={Q[0]}\cdot {KEYS[1][0]}+{Q[1]}\cdot {KEYS[1][1]}={SCORES[1]}",
                size=Size.LABEL),
            tex(r"\text{scale: }\div\sqrt{2}\approx\div 1.41", size=Size.LABEL),
            tex(r"\text{softmax: }w_i=\frac{e^{s_i}}{\sum_j e^{s_j}}", size=Size.LABEL),
            tex(rf"\cG{{{W2[0]:.2f}+{W2[1]:.2f}+{W2[2]:.2f}=1}}", size=Size.LABEL),
        ).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        BAND.fit(steps, upscale=False, align="top", buff=0.15)
        step_plates = [plate(m, buff=0.05) for m in steps]

        with self.beat("hook"):
            self.title("Attention averages values",
                       LaggedStart(*[FadeIn(VGroup(cards[i], words[i]), shift=DOWN * 0.2) for i in range(3)],
                                   lag_ratio=0.25, run_time=1.2),
                       Create(baseline, run_time=1.0))
            self.cue("sat")
            self.play(cards[2].animate.set_stroke(YELLOW_K, width=7), run_time=0.6)

        with self.beat("paper"):
            cite_title = text("Attention Is All You Need", size=Size.BODY, weight=BOLD)
            authors = VGroup(
                text("Vaswani, Shazeer, Parmar, Uszkoreit,", size=Size.SMALL, color=MUTED),
                text("Jones, Gomez, Kaiser, Polosukhin", size=Size.SMALL, color=MUTED),
                text("2017  ·  arXiv 1706.03762", size=Size.SMALL, color=MUTED),
            ).arrange(DOWN, buff=0.14)
            cite = VGroup(cite_title, authors).arrange(DOWN, buff=0.3)
            cite_plate = plate(cite, buff=0.2)
            BAND.fit(cite_plate, upscale=False)
            self.play(FadeIn(cite_plate[0]), Write(cite_title), run_time=1.2)
            self.cue("Ashish")
            self.play(LaggedStart(*[FadeIn(a, shift=UP * 0.1) for a in authors], lag_ratio=0.3), run_time=1.2)

        with self.beat("keys"):
            self.play(FadeOut(cite_plate, shift=UP * 0.1), run_time=0.4)
            self.play(FadeIn(step_plates[0], shift=UP * 0.1), run_time=0.6)
            self.cue("key")
            self.play(LaggedStart(*[Write(k) for k in keys], lag_ratio=0.3), run_time=1.4)

        with self.beat("scores"):
            self.play(FadeIn(step_plates[1], shift=DOWN * 0.1), run_time=0.6)
            self.cue("add")
            self.play(Indicate(keys[1], color=ORANGE_K, scale_factor=1.2),
                      Indicate(steps[1], color=YELLOW_K, scale_factor=1.08), run_time=0.9)
            bars, labels = VGroup(), VGroup()
            for i, s in enumerate(SCORES):
                bars.add(bar(i, s * SCORE_UNIT))
                labels.add(bar_label(i, f"{s}", s * SCORE_UNIT))
            for i, word in enumerate(["one", "three", "two"]):
                self.cue(word)
                self.play(GrowFromEdge(bars[i], DOWN), TransformFromCopy(keys[i], labels[i]), run_time=0.6)

        with self.beat("scale"):
            self.play(FadeIn(step_plates[2], shift=DOWN * 0.1), run_time=0.6)
            new_bars = VGroup(*[bar(i, s * SCORE_UNIT) for i, s in enumerate(SCALED)])
            new_labels = VGroup(*[bar_label(i, f"{s:.2f}", s * SCORE_UNIT) for i, s in enumerate(SCALED)])
            self.cue("root")
            self.play(*[Transform(bars[i], new_bars[i]) for i in range(3)],
                      *[FadeOut(labels[i]) for i in range(3)], run_time=1.0)
            self.play(*[FadeIn(new_labels[i]) for i in range(3)], run_time=0.4)
            labels = new_labels

        with self.beat("softmax"):
            self.play(FadeIn(step_plates[3], shift=DOWN * 0.1), run_time=0.7)
            w_bars = VGroup(*[bar(i, w * WEIGHT_UNIT) for i, w in enumerate(W)])
            w_labels = VGroup(*[bar_label(i, f"{w:.2f}", w * WEIGHT_UNIT, color=GREEN_K) for i, w in enumerate(W2)])
            self.cue("weights")
            self.play(*[Transform(bars[i], w_bars[i]) for i in range(3)],
                      *[FadeOut(labels[i]) for i in range(3)], run_time=1.0)
            self.play(*[FadeIn(w_labels[i]) for i in range(3)], run_time=0.4)
            labels = w_labels
            total = steps[4]
            self.cue("point")
            self.play(FadeIn(step_plates[4][0]),
                      *[TransformFromCopy(labels[i], total[5 * i: 5 * i + 4]) for i in range(3)], run_time=1.0)
            self.remove(*[total[5 * i: 5 * i + 4] for i in range(3)])
            self.add(step_plates[4])
            self.play(FadeIn(total[4]), FadeIn(total[9]), FadeIn(total[14:]), run_time=0.3)

        plane = stage_plane((-0.4, 4.8, 1), (-0.9, 4.8, 1), zone=VAL_ZONE, buff=0.05)
        background(plane)

        with self.beat("values"):
            self.play(*[FadeOut(p, shift=UP * 0.1) for p in step_plates], run_time=0.5)
            self.play(Create(plane, lag_ratio=0.02), run_time=0.8)
            dots, vlabels = VGroup(), VGroup()
            offsets = [DOWN * 0.4 + LEFT * 0.2, RIGHT * 0.95, UP * 0.38 + RIGHT * 0.8]
            for i, v in enumerate(VALUES):
                d = Dot(plane.c2p(*v), radius=0.11, color=COLORS[i])
                lab = plate(VGroup(text(TOKENS[i], size=Size.SMALL, color=COLORS[i]),
                                   tex(coord(v), size=Size.SMALL)).arrange(RIGHT, buff=0.1), buff=0.06)
                lab.move_to(plane.c2p(*v) + offsets[i])
                dots.add(d)
                vlabels.add(lab)
            for i, (word, nth) in enumerate([("four", 0), ("four", 1), ("zero", 1)]):
                self.cue(word, nth=nth)
                self.play(FadeIn(dots[i], scale=1.8), FadeIn(vlabels[i]), run_time=0.5)

        with self.beat("blend"):
            starts = [(0.0, 0.0)]
            for i in range(3):
                p = starts[-1]
                starts.append((p[0] + W[i] * VALUES[i][0], p[1] + W[i] * VALUES[i][1]))
            arrows = VGroup(*[vec(plane, starts[i + 1], COLORS[i], start=starts[i], width=10) for i in range(3)]).set_z_index(2)
            rule = plate(tex(r"\cG{\text{output}}=\sum_i w_i\,v_i", size=Size.LABEL))
            READ_ZONE.fit(rule, upscale=False)
            rule.shift(UP * 0.6)
            self.play(FadeIn(rule, shift=UP * 0.1), run_time=0.5)
            for i, word in enumerate(["little", "mostly", "some"]):
                self.cue(word)
                self.play(GrowArrow(arrows[i]), Indicate(labels[i], color=COLORS[i], scale_factor=1.25), run_time=0.7)
            out_dot = Dot(plane.c2p(*OUTPUT), radius=0.13, color=GREEN_K)
            out_lab = plate(tex(rf"\approx({OUT1[0]},\,{OUT1[1]})", size=Size.HEADLINE, color=GREEN_K))
            out_lab.next_to(rule, DOWN, buff=0.35)
            self.cue("lands")
            self.play(FadeIn(out_dot, scale=2.0), TransformFromCopy(out_dot, out_lab), run_time=0.8)

        with self.beat("takeaway"):
            formula = tex(r"\mathrm{softmax}\!\left(\frac{\cY{Q}\,\cB{K}^{\top}}{\sqrt{d_k}}\right)\cG{V}",
                          size=Size.BODY)
            cite2 = text("Vaswani et al., 2017", size=Size.SMALL, color=MUTED)
            final = plate(VGroup(formula, cite2).arrange(DOWN, buff=0.22), opacity=0.95)
            READ_ZONE.fit(final, upscale=False, align="bottom", buff=0.15)
            self.play(FadeOut(rule, shift=UP * 0.1), out_lab.animate.move_to(rule).align_to(rule, UP), run_time=0.6)
            self.play(FadeIn(final, shift=UP * 0.15), run_time=0.9)
            self.play(Circumscribe(final, color=GREEN_K, buff=0.06), run_time=1.2)

"""Bayes' theorem through a medical test: why a positive result means only ~9%.

Storyboard: storyboard.md. Every number on screen comes from N, PREV, SENS, FPR below.
"""

import json
import os

from shortkit import *

BEATS = [
    ("hook", "A test catches ninety percent of cases, and you test positive. So why is your chance of being sick only about nine percent?"),
    ("prevalence", "Picture a thousand people. The disease affects one percent of them, so just ten are sick."),
    ("truepos", "The test catches ninety percent of the sick, so nine of those ten test positive."),
    ("falsepos", "But it also flags nine percent of healthy people. Nine percent of nine hundred ninety is about eighty-nine more."),
    ("condition", "Your test was positive, so you are one of these ninety-eight people. Only nine of them are sick: about nine percent."),
    ("probs", "In probabilities, the nine is ninety percent of one percent. The eighty-nine is nine percent of the other ninety-nine percent."),
    ("bayes", "That is Bayes' theorem: the chance of disease given a positive is the true positives over all the positives."),
    ("takeaway", "When a disease is rare, false alarms from the many healthy people outnumber the real cases almost ten to one."),
]

# ---- the model: every number on screen is computed here ------------------------------
N = 1000
PREV, SENS, FPR = 0.01, 0.90, 0.09
SICK = round(N * PREV)                                   # 10
HEALTHY = N - SICK                                       # 990
TP = round(SENS * SICK)                                  # 9 true positives
FP = round(FPR * HEALTHY)                                # 89 false positives (89.1)
POS = TP + FP                                            # 98
POST = SENS * PREV / (SENS * PREV + FPR * (1 - PREV))    # exact Bayes: 10/109 = 0.0917
PCT = f"{100 * POST:.1f}"                                # "9.2"
assert f"{100 * TP / POS:.1f}" == PCT                    # counting agrees with exact Bayes
# BEATS must be a literal, so pin the numbers the narration speaks to the computed ones.
assert (N, SICK, HEALTHY, TP, FP, POS, round(100 * POST), round(FP / TP)) == (1000, 10, 990, 9, 89, 98, 9, 10)


def p(x: float) -> str:
    return f"{x:g}"


# ---- geometry ---------------------------------------------------------------------------
COLS, ROWS, CELL, RADIUS = 40, 25, 0.2, 0.068
assert COLS * ROWS == N
GRID_TOP = 4.1
BAND_Y = 4.5                                             # counter labels above the grid
SICK_IDX = [r * COLS + c for r in range(2) for c in range(5)]   # a 2 x 5 block, top-left
assert len(SICK_IDX) == SICK
TP_IDX = SICK_IDX[:TP]
HEALTHY_IDX = [i for i in range(N) if i not in set(SICK_IDX)]
FP_IDX = sorted(np.random.default_rng(3).choice(HEALTHY_IDX, FP, replace=False).tolist())
TRAY_LEFT, TRAY_TOP, TRAY_GAP = -3.9, -1.3, 0.3
SICK_C, WELL_C, TEST_C = RED_K, BLUE_K, YELLOW_K


def grid_point(i: int) -> np.ndarray:
    r, c = divmod(i, COLS)
    return np.array([(c - (COLS - 1) / 2) * CELL, GRID_TOP - (r + 0.5) * CELL, 0.0])


def tray_slots():
    """Slots in the 'tested positive' tray: a 3x3 block for the sick, 15x6 for the healthy."""
    red = [np.array([TRAY_LEFT + (c + 0.5) * CELL, TRAY_TOP - (r + 2.0) * CELL, 0.0])
           for r in range(3) for c in range(3)]
    x0 = TRAY_LEFT + 3 * CELL + TRAY_GAP
    blue = [np.array([x0 + (c + 0.5) * CELL, TRAY_TOP - (r + 0.5) * CELL, 0.0])
            for r in range(6) for c in range(15)]
    return red[:TP], blue[:FP]


TRAY_W, TRAY_H = 3 * CELL + TRAY_GAP + 15 * CELL, 6 * CELL

TEX_RULE_PT = 0.398484   # TeX's default \fracrule thickness


def ftex(src: str, size: float = Size.BODY) -> Mobject:
    """tex() with its fraction bars restored.

    shortkit's TexSVG is built with stroke_width=0, but TeX rules (fraction bars) arrive in
    the SVG as stroked, unfilled paths, so they vanish. Re-stroke every zero-height path.
    """
    m = tex(src, size=size)
    width = TEX_RULE_PT * size * TEX_PT_SCALE / 0.01        # Cairo: stroke width 1 = 0.01 units
    for sub in m.submobjects:
        if sub.height < 1e-3 and sub.width > 0.05:
            sub.set_stroke("#FFFFFF", width=width, opacity=1)
    return m


# glyph slices of the two fractions (tex glyphs come out in source order)
NTP, NFP = len(str(TP)), len(str(FP))
NR = len(p(SENS)) + 1 + len(p(PREV))            # "0.9×0.01"
NB = len(p(FPR)) + 1 + len(p(1 - PREV))         # "0.09×0.99"
EQ_SIZE, THM_SIZE = 40, 44


class Short(ShortScene):
    # ---- syncing a motion to a spoken word ------------------------------------------------
    def until_word(self, beat_id: str, t0: float, word: str, fallback: float, nth: int = 0) -> None:
        """Wait until the nth `word` is spoken in this beat (edge-tts word timings), else a fraction."""
        offset = fallback * self._durations[beat_id]
        path = os.environ.get("SHORTKIT_TIMING")
        if path and os.path.exists(path):
            for b in json.load(open(path)).get("beats", []):
                if b["id"] == beat_id and b.get("words"):
                    hits = [w[0] for w in b["words"] if str(w[2]).lower().strip(".,:;?") == word.lower()]
                    if len(hits) > nth:
                        offset = hits[nth]
        remaining = t0 + offset - self.renderer.time
        if remaining > 0.07:
            self.wait(remaining)

    def construct(self):
        people = [Dot(grid_point(i), radius=RADIUS, color=MUTED, fill_opacity=0.7) for i in range(N)]
        sweep = sorted(range(N), key=lambda i: sum(divmod(i, COLS)))   # diagonal sweep order
        crowd = VGroup(*[people[i] for i in sweep])
        sick = VGroup(*[people[i] for i in SICK_IDX])
        well = VGroup(*[people[i] for i in HEALTHY_IDX])
        tp = [people[i] for i in TP_IDX]
        fp = [people[i] for i in FP_IDX]
        red_slots, blue_slots = tray_slots()
        # "you": a positive person near the middle of the crowd (status unknown in the hook)
        you = min(FP_IDX, key=lambda i: np.linalg.norm(grid_point(i) - np.array([0.6, 1.6, 0])))

        # ------------------------------------------------------------------ hook
        with self.beat("hook"):
            t0 = self.renderer.time
            title = text(f"Positive test, only {round(100 * POST)}%?", size=Size.TITLE, weight=BOLD)
            TITLE_ZONE.fit(title, buff=0.05, upscale=False)
            self.play(FadeIn(title, shift=DOWN * 0.15), FadeIn(crowd, lag_ratio=0.004), run_time=3.0)
            self._title_mob = title   # shortkit's title() plays alone; set it by hand so the crowd shows at t=0
            # a ring closes in on one person: you, positive, health unknown
            halo = Circle(radius=0.17, stroke_color=TEST_C, stroke_width=5).move_to(people[you])
            ring = halo.copy().scale(8).set_stroke(opacity=0.0)
            self.until_word("hook", t0, "you", 0.35)
            self.play(ReplacementTransform(ring, halo), people[you].animate.set_fill(INK, 1), run_time=1.0)

        # ------------------------------------------------------------------ prevalence
        with self.beat("prevalence"):
            t0 = self.renderer.time
            people_lbl = text(f"{N} people", size=Size.LABEL).move_to([0, BAND_Y, 0])
            self.play(FadeOut(halo), people[you].animate.set_fill(MUTED, 0.7), FadeIn(people_lbl), run_time=0.8)
            sick_lbl = text(f"{SICK} sick", size=Size.LABEL, color=SICK_C)
            sick_lbl.move_to([0, BAND_Y, 0]).align_to(crowd, LEFT)
            well_lbl = text(f"{HEALTHY} healthy", size=Size.LABEL, color=WELL_C)
            well_lbl.move_to([0, BAND_Y, 0]).align_to(crowd, RIGHT)
            self.until_word("prevalence", t0, "one", 0.45)
            self.play(sick.animate.set_fill(SICK_C, 1), well.animate.set_fill(WELL_C, 0.75),
                      FadeTransform(people_lbl, VGroup(sick_lbl, well_lbl)), run_time=1.2)
            self.until_word("prevalence", t0, "ten", 0.75)
            self.play(Indicate(sick, color=SICK_C, scale_factor=1.25), run_time=0.9)

        # ------------------------------------------------------------------ true positives
        with self.beat("truepos"):
            t0 = self.renderer.time
            box = RoundedRectangle(width=TRAY_W + 0.24, height=TRAY_H + 0.24, corner_radius=0.1,
                                   stroke_color=TEST_C, stroke_width=4)
            box.move_to([TRAY_LEFT + TRAY_W / 2, TRAY_TOP - TRAY_H / 2, 0])
            pos_lbl = text("tested positive", size=Size.LABEL, color=TEST_C)
            pos_lbl.next_to(box, RIGHT, buff=0.35).align_to(box, UP)
            tp_lbl = text(f"{TP} sick", size=Size.LABEL, color=SICK_C)
            tp_lbl.next_to(pos_lbl, DOWN, buff=0.12).align_to(pos_lbl, LEFT)
            self.play(Create(box), FadeIn(pos_lbl), run_time=0.9)
            for d in tp:
                d.set_z_index(3)
            self.until_word("truepos", t0, "nine", 0.5)
            self.play(*[d.animate.set_stroke(TEST_C, width=3, opacity=1) for d in tp], run_time=0.5)
            self.play(LaggedStart(*[d.animate.move_to(s) for d, s in zip(tp, red_slots)], lag_ratio=0.08),
                      FadeIn(tp_lbl), run_time=1.3)

        # ------------------------------------------------------------------ false positives
        with self.beat("falsepos"):
            t0 = self.renderer.time
            for d in fp:
                d.set_z_index(3)
            fp_lbl = text(f"{FP} healthy", size=Size.LABEL, color=WELL_C)
            fp_lbl.next_to(tp_lbl, DOWN, buff=0.12).align_to(tp_lbl, LEFT)
            self.until_word("falsepos", t0, "flags", 0.1)
            self.play(LaggedStart(*[d.animate.set_stroke(TEST_C, width=3, opacity=1) for d in fp],
                                  lag_ratio=0.03), run_time=1.8)
            self.until_word("falsepos", t0, "nine", 0.5, nth=1)
            self.play(LaggedStart(*[d.animate.move_to(s) for d, s in zip(fp, blue_slots)], lag_ratio=0.02),
                      run_time=2.0)
            self.play(FadeIn(fp_lbl), run_time=0.5)

        # ------------------------------------------------------------------ condition on +
        with self.beat("condition"):
            t0 = self.renderer.time
            pos_set = set(TP_IDX) | set(FP_IDX)
            negatives = VGroup(*[people[i] for i in range(N) if i not in pos_set])
            tray = VGroup(box, *tp, *fp)
            header = text(f"{POS} tested positive", size=Size.LABEL, color=TEST_C).move_to([0, BAND_Y, 0])
            tray.generate_target()
            tray.target.scale(1.5).next_to(header, DOWN, buff=0.2).set_x(0)
            red_t, blue_t = VGroup(*tray.target[1:1 + TP]), VGroup(*tray.target[1 + TP:])
            tp_lbl.generate_target()
            tp_lbl.target.next_to(tray.target[0], DOWN, buff=0.15).set_x(red_t.get_center()[0])
            fp_lbl.generate_target()
            fp_lbl.target.next_to(tray.target[0], DOWN, buff=0.15).set_x(blue_t.get_center()[0])
            self.play(FadeOut(negatives), FadeOut(sick_lbl), FadeOut(well_lbl), run_time=1.0)
            self.play(MoveToTarget(tray), MoveToTarget(tp_lbl), MoveToTarget(fp_lbl),
                      ReplacementTransform(pos_lbl, header), run_time=1.4)

            eq_count = ftex(rf"\frac{{\cR{{{TP}}}}}{{\cR{{{TP}}}+\cB{{{FP}}}}}\approx\cG{{{PCT}\%}}", size=EQ_SIZE)
            eq_count.next_to(VGroup(tp_lbl.target, fp_lbl.target), DOWN, buff=0.45).set_x(0)
            c_num = eq_count[0:NTP]
            c_bar = eq_count[NTP]
            c_red = eq_count[NTP + 1:2 * NTP + 1]
            c_plus = eq_count[2 * NTP + 1]
            c_blue = eq_count[2 * NTP + 2:2 * NTP + 2 + NFP]
            c_rest = eq_count[2 * NTP + 2 + NFP:]
            self.until_word("condition", t0, "only", 0.55)
            # the digits of the tray labels become the fraction
            self.play(TransformFromCopy(tp_lbl[0:NTP], c_num), TransformFromCopy(tp_lbl[0:NTP], c_red),
                      TransformFromCopy(fp_lbl[0:NFP], c_blue), FadeIn(c_bar), FadeIn(c_plus), run_time=1.2)
            self.until_word("condition", t0, "about", 0.8)
            self.play(FadeIn(c_rest, shift=LEFT * 0.15), run_time=0.6)
            self.remove(c_num, c_red, c_blue, c_bar, c_plus, c_rest)
            self.add(eq_count)

        # ------------------------------------------------------------------ probabilities
        with self.beat("probs"):
            t0 = self.renderer.time
            eq_prob = ftex(rf"\frac{{\cR{{{p(SENS)}\times{p(PREV)}}}}}"
                           rf"{{\cR{{{p(SENS)}\times{p(PREV)}}}+\cB{{{p(FPR)}\times{p(1 - PREV)}}}}}"
                           rf"\approx\cG{{{PCT}\%}}", size=EQ_SIZE)
            eq_prob.move_to(eq_count)
            p_num, p_bar = eq_prob[0:NR], eq_prob[NR]
            p_red, p_plus = eq_prob[NR + 1:2 * NR + 1], eq_prob[2 * NR + 1]
            p_blue, p_rest = eq_prob[2 * NR + 2:2 * NR + 2 + NB], eq_prob[2 * NR + 2 + NB:]
            # substitute one count at a time; the answer dims while the fraction is half converted
            self.until_word("probs", t0, "nine", 0.15)
            self.play(ReplacementTransform(c_num, p_num), ReplacementTransform(c_red, p_red),
                      ReplacementTransform(c_bar, p_bar), ReplacementTransform(c_plus, p_plus),
                      c_blue.animate.move_to(p_blue), c_rest.animate.move_to(p_rest).set_opacity(0.25),
                      run_time=1.4)
            self.until_word("probs", t0, "eighty-nine", 0.5)
            self.play(ReplacementTransform(c_blue, p_blue), run_time=1.3)
            self.until_word("probs", t0, "other", 0.75)
            self.play(ReplacementTransform(c_rest, p_rest), run_time=0.8)
            self.remove(p_num, p_bar, p_red, p_plus, p_blue, p_rest)
            self.add(eq_prob)

        # ------------------------------------------------------------------ Bayes' theorem
        with self.beat("bayes"):
            t0 = self.renderer.time
            theorem = ftex(r"P(\cR{D}\mid\cY{+})=\frac{\cR{P(+\mid D)\,P(D)}}{\cY{P(+)}}", size=THM_SIZE)
            theorem.next_to(eq_prob, DOWN, buff=0.5).set_x(0)
            self.play(FadeIn(theorem, shift=UP * 0.2), run_time=1.0)
            lhs_box = highlight(theorem[0:6], color=GREEN_K, buff=0.06)       # P(D | +)
            self.until_word("bayes", t0, "chance", 0.25)
            self.play(Create(lhs_box), run_time=0.7)
            num_box = highlight(theorem[7:17], color=SICK_C, buff=0.06)
            red_box = highlight(VGroup(*tp), color=SICK_C, buff=0.06)
            self.until_word("bayes", t0, "true", 0.55)
            self.play(Create(num_box), Create(red_box), run_time=0.7)
            den_box = highlight(theorem[18:22], color=TEST_C, buff=0.06)
            self.until_word("bayes", t0, "all", 0.8)
            self.play(Create(den_box), Indicate(box, color=TEST_C, scale_factor=1.03), run_time=0.8)

        # ------------------------------------------------------------------ takeaway
        with self.beat("takeaway"):
            t0 = self.renderer.time
            self.play(FadeOut(lhs_box), FadeOut(num_box), FadeOut(den_box), FadeOut(red_box), run_time=0.5)
            # regroup the false alarms into blocks shaped like the sick block: 1 red vs ~10 blue
            pitch = 0.26                                            # dot spacing inside a block
            blk = 3 * pitch
            reg = VGroup(*fp)
            rx0, rx1 = reg.get_left()[0] - 0.05, reg.get_right()[0] + 0.05
            ry0, ry1 = reg.get_bottom()[1] - 0.05, reg.get_top()[1] + 0.05
            per_row = 5
            gx = (rx1 - rx0 - per_row * blk) / (per_row - 1)
            gy = (ry1 - ry0 - 2 * blk)
            def block_slot(k):
                b, j = divmod(k, 9)                                 # block number, place in block
                br, bc = divmod(b, per_row)
                r, c = divmod(j, 3)
                return np.array([rx0 + bc * (blk + gx) + (c + 0.5) * pitch,
                                 ry1 - br * (blk + gy) - (r + 0.5) * pitch, 0.0])
            assert FP <= 2 * per_row * 9
            red_c = VGroup(*tp).get_center()
            red_targets = [red_c + np.array([(c - 1) * pitch, (1 - r) * pitch, 0]) for r in range(3) for c in range(3)]
            self.until_word("takeaway", t0, "false", 0.25)
            self.play(LaggedStart(*[d.animate.move_to(block_slot(k)) for k, d in enumerate(fp)], lag_ratio=0.01),
                      *[d.animate.move_to(q) for d, q in zip(tp, red_targets[:TP])], run_time=1.8)
            blue_term = highlight(p_blue, color=WELL_C, buff=0.06)
            self.until_word("takeaway", t0, "outnumber", 0.6)
            self.play(Create(blue_term), Indicate(VGroup(*tp), color=SICK_C, scale_factor=1.15), run_time=1.0)

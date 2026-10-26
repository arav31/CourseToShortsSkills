"""Bigger model, or more data?  How the compute-optimal recipe changed (Kaplan 2020 -> Hoffmann 2022).

Storyboard: storyboard.md.  Every number is computed here from inputs quoted from the original
papers (see checks/examples.py, which recomputes the same values):
  Kaplan et al. 2020:   N = 1.3e9 * Cmin^0.73 (Cmin in PF-days), C = 2 Cmin, C ~ 6 N D
  Hoffmann et al. 2022: 2.86B params at 1e21 FLOPs (D.4), N ~ C^0.5, Gopher budget 5.76e23 FLOPs,
                        Gopher 280B / 300B tokens, Chinchilla 70B / 1.4T tokens
  Pearce & Song 2024:   0.78 (non-embedding params, small scale) vs Kaplan's 0.73
"""

import math

from shortkit import *

BEATS = [
    ("hook", "Fixed compute budget: bigger model, or more data? The field's answer flipped."),
    ("budget", "Training costs about six times parameters times tokens, so a budget is a line: double the model, halve the data."),
    ("kaplan", "Kaplan and colleagues, 2020: per ten times more compute, a model five times bigger, data only twice."),
    ("hoffmann", "Hoffmann and colleagues, 2022: grow both equally, about three times each."),
    ("duel", "On this budget, that's 4.7 versus 2.9 billion parameters. Trained side by side, the smaller won."),
    ("sweep", "Now grow the budget almost six hundred times, to Gopher's compute."),
    ("land", "Kaplan's rule: 480 billion parameters on 200 billion tokens. Hoffmann's: 70 billion on 1.4 trillion."),
    ("real", "Gopher went big, 280 billion on 300 billion tokens. Chinchilla took Hoffmann's shape, twenty tokens per parameter, and beat it."),
    ("pearce", "Why the gap? Pearce and Song, 2024: Kaplan counted only non-embedding parameters, in small models. Do that to Chinchilla's data and you get 0.78. Count everything, and it's 0.51."),
    ("takeaway", "So grow the model and its data together."),
]

# ---------------------------------------------------------------- numbers (from the originals)
PF_DAY = 1e15 * 86400
A_K, A_H = 0.73, 0.50
C0, C_GOPHER = 1e21, 5.76e23
T_END = math.log10(C_GOPHER / C0)          # log10(576)
GOPHER = (280e9, 300e9)
CHIN = (70e9, 1.4e12)
PEARCE_K, PEARCE_T = 0.78, 0.51


def kaplan_n(c):
    return 1.3e9 * (c / 2 / PF_DAY) ** A_K


def hoff_n(c):
    return 2.86e9 * (c / C0) ** A_H


def toks(c, n):
    return c / (6 * n)


K0, H0 = kaplan_n(C0), hoff_n(C0)
KG, HG = kaplan_n(C_GOPHER), hoff_n(C_GOPHER)
KG_D, HG_D = toks(C_GOPHER, KG), toks(C_GOPHER, HG)
K10, K10D, H10 = 10 ** A_K, 10 ** (1 - A_K), 10 ** A_H
TPP = round(CHIN[1] / CHIN[0])

assert f"{K0 / 1e9:.1f}" == "4.7" and "4.7 versus" in BEATS[4][1]
assert f"{H0 / 1e9:.1f}" == "2.9" and "2.9 billion" in BEATS[4][1]
assert round(K10) == 5 and round(K10D) == 2 and round(H10) == 3          # "five", "twice", "three"
assert round(KG / 1e9, -1) == 480 and round(KG_D / 1e9, -1) == 200
assert "480 billion" in BEATS[6][1] and "200 billion" in BEATS[6][1]
assert round(HG / 1e9, -1) == 70 and f"{HG_D / 1e12:.1f}" == "1.4" and "1.4 trillion" in BEATS[6][1]
assert 550 < C_GOPHER / C0 < 600                                           # "almost six hundred times"
assert spoken(TPP) in BEATS[7][1]                                         # "twenty"
assert all(f"{v}" in BEATS[8][1] for v in (PEARCE_K, PEARCE_T))

KAP, HOF, BUD, REAL = ORANGE_K, BLUE_K, YELLOW_K, GREEN_K


def fmt_n(n):
    if n >= 1e12:
        return f"{n / 1e12:.1f}T"
    if n >= 1e10:
        return f"{n / 1e9:.0f}B"
    return f"{n / 1e9:.1f}B"


class Short(ShortScene):
    def construct(self):
        band, pzone = STAGE.rows(1.75, 5.6, gap=0.15)

        # -------- log-log plane: x = log10(N) - 9 (1B..1T), y = log10(D) - 10 (10B..10T)
        left_pad, bottom_pad = 1.0, 0.95
        plane = NumberPlane(
            x_range=(0, 3, 1), y_range=(0, 3, 1),
            x_length=pzone.width - left_pad - 0.45, y_length=pzone.height - bottom_pad - 0.1,
            background_line_style={"stroke_color": GRID, "stroke_width": 2, "stroke_opacity": 1},
            axis_config={"stroke_color": MUTED, "stroke_width": 3}, faded_line_ratio=1,
        )
        plane.move_to([pzone.left + left_pad + plane.width / 2, pzone.bottom + bottom_pad + plane.height / 2, 0])

        def P(n, d):
            return plane.c2p(math.log10(n) - 9, math.log10(d) - 10)

        ticks = VGroup()
        for i, s in enumerate(["1B", "10B", "100B", "1T"]):
            ticks.add(text(s, size=Size.SMALL, color=MUTED).next_to(plane.c2p(i, 0), DOWN, buff=0.12))
        for i, s in enumerate(["10B", "100B", "1T", "10T"]):
            ticks.add(text(s, size=Size.SMALL, color=MUTED).next_to(plane.c2p(0, i), LEFT, buff=0.12))
        xname = text("parameters N", size=Size.SMALL, color=INK).next_to(ticks[1:3], DOWN, buff=0.12)
        xname.set_x(plane.get_center()[0])
        yname = text("tokens D", size=Size.SMALL, color=INK)
        yname.move_to(plane.c2p(0, 3), aligned_edge=UP + LEFT).shift(RIGHT * 0.12 + DOWN * 0.1)

        def budget_line(c, color=BUD, width=6, opacity=1.0):
            s = math.log10(c / 6) - 19                       # x + y = s on this plane
            x0, x1 = max(0.0, s - 3), min(3.0, s)
            return Line(plane.c2p(x0, s - x0), plane.c2p(x1, s - x1), color=color,
                        stroke_width=width, stroke_opacity=opacity)

        t = ValueTracker(0.0)

        def budget_now():
            return C0 * 10 ** t.get_value()

        def kdot_pt():
            c = budget_now()
            n = kaplan_n(c)
            return P(n, toks(c, n))

        def hdot_pt():
            c = budget_now()
            n = hoff_n(c)
            return P(n, toks(c, n))

        with self.beat("hook"):
            self.title("Bigger model, or more data?",
                       Create(plane, lag_ratio=0.05, run_time=1.4), FadeIn(ticks, run_time=1.0),
                       FadeIn(xname, run_time=1.0), FadeIn(yname, run_time=1.0))
            q = text("same compute: where should it go?", size=Size.LABEL, color=INK)
            band.fit(q, upscale=False)
            self.play(FadeIn(q, shift=DOWN * 0.1), run_time=0.8)

        with self.beat("budget"):
            cost = tex(r"\cY{C}\approx 6\,N\,D", size=Size.HEADLINE + 4)
            band.fit(cost, upscale=False)
            self.play(FadeOut(q, shift=UP * 0.1), FadeIn(cost, shift=UP * 0.1), run_time=0.8)
            line = always_redraw(lambda: budget_line(budget_now()))
            self.cue("line")
            self.play(Create(line), run_time=1.0)
            # slide a marker along the line: double N, halve D
            s0 = math.log10(C0 / 6) - 19
            u = ValueTracker(0.25)
            probe = always_redraw(lambda: Dot(plane.c2p(u.get_value(), s0 - u.get_value()), radius=0.09, color=BUD))
            self.play(FadeIn(probe), run_time=0.3)
            self.cue("double")
            self.play(u.animate.set_value(1.0), run_time=1.4)
            self.play(u.animate.set_value(0.45), run_time=1.0)
            self.play(FadeOut(probe), run_time=0.3)
            self.remove(probe)

        # band columns: rule name, exponent, live readout of the dot's (N, D)
        lcol, rcol = band.cols(0.92, 1.08, gap=0.1)

        def column(zone, name, rule, color, nfun):
            nm = text(name, size=Size.SMALL, color=color)
            rl = tex(rule, size=Size.BODY, color=color)
            rd = live_text(lambda: f"N {fmt_n(nfun(budget_now()))} · D {fmt_n(toks(budget_now(), nfun(budget_now())))}",
                           size=Size.SMALL, color=INK)
            g = VGroup(nm, rl, rd).arrange(DOWN, buff=0.14)
            zone.fit(g, upscale=False)
            return nm, rl, rd

        with self.beat("kaplan"):
            k_name, k_rule, k_read = column(lcol, "Kaplan et al., 2020", r"N\propto C^{0.73}", KAP, kaplan_n)
            self.play(cost.animate.scale(0.75).move_to(plane.c2p(2.55, 2.75)), run_time=0.8)
            kdot = always_redraw(lambda: Dot(kdot_pt(), radius=0.12, color=KAP).set_z_index(3))
            self.play(FadeIn(k_name, shift=DOWN * 0.1), FadeIn(k_rule, shift=DOWN * 0.1),
                      FadeIn(kdot, scale=1.5), run_time=0.9)
            k_read.update()
            self.play(FadeIn(k_read), run_time=0.5)
            # one tenfold step of the budget: ghost line and the step each rule takes
            ghost10 = budget_line(C0 * 10, opacity=0.35, width=4)
            k10 = P(kaplan_n(C0 * 10), toks(C0 * 10, kaplan_n(C0 * 10)))
            k_step = Arrow(kdot_pt(), k10, buff=0.12, color=KAP, stroke_width=6, max_tip_length_to_length_ratio=0.2)
            self.cue("ten")
            self.play(FadeIn(ghost10), run_time=0.6)
            self.cue("model")
            self.play(GrowArrow(k_step), run_time=1.0)

        with self.beat("hoffmann"):
            h_name, h_rule, h_read = column(rcol, "Hoffmann et al., 2022", r"N\propto C^{0.5}", HOF, hoff_n)
            hdot = always_redraw(lambda: Dot(hdot_pt(), radius=0.12, color=HOF).set_z_index(3))
            self.play(FadeIn(h_name, shift=DOWN * 0.1), FadeIn(h_rule, shift=DOWN * 0.1),
                      FadeIn(hdot, scale=1.5), run_time=0.9)
            h_read.update()
            self.play(FadeIn(h_read), run_time=0.5)
            h10 = P(hoff_n(C0 * 10), toks(C0 * 10, hoff_n(C0 * 10)))
            h_step = Arrow(hdot_pt(), h10, buff=0.12, color=HOF, stroke_width=6, max_tip_length_to_length_ratio=0.2)
            self.cue("equally")
            self.play(GrowArrow(h_step), run_time=1.0)

        with self.beat("duel"):
            self.play(FadeOut(k_step), FadeOut(h_step), FadeOut(ghost10), run_time=0.6)
            k_lab = label(f"{K0 / 1e9:.1f}B", color=KAP).next_to(kdot_pt(), DL, buff=0.08)
            h_lab = label(f"{H0 / 1e9:.1f}B", color=HOF).next_to(hdot_pt(), UR, buff=0.08)
            self.cue(f"{K0 / 1e9:.1f}", prefix=True)
            self.play(FadeIn(k_lab, shift=UP * 0.1), run_time=0.6)
            self.cue(f"{H0 / 1e9:.1f}", prefix=True)
            self.play(FadeIn(h_lab, shift=DOWN * 0.1), run_time=0.6)
            self.cue("smaller")
            win = label("lower loss", size=Size.SMALL, color=REAL).next_to(h_lab, UP, buff=0.1)
            self.play(FadeIn(win, shift=UP * 0.1), Indicate(hdot, color=REAL, scale_factor=1.8), run_time=1.0)

        with self.beat("sweep"):
            self.play(FadeOut(k_lab), FadeOut(h_lab), FadeOut(win), run_time=0.3)
            k_start, h_start = kdot_pt(), hdot_pt()
            k_trail = always_redraw(lambda: Line(k_start, kdot_pt(), color=KAP, stroke_width=6))
            h_trail = always_redraw(lambda: Line(h_start, hdot_pt(), color=HOF, stroke_width=6))
            start_ghost = budget_line(C0, opacity=0.35, width=4)
            mult = live_text(lambda: f"budget ×{10 ** t.get_value():.0f}", size=Size.SMALL, color=BUD)
            mult.next_to(cost, DOWN, buff=0.15)
            self.add(start_ghost, k_trail, h_trail)
            self.play(FadeIn(mult), run_time=0.3)
            self.cue("grow")
            self.play(t.animate.set_value(T_END), run_time=4.0, rate_func=smooth)

        with self.beat("land"):
            self.cue("480", prefix=True)
            k_hl, h_hl = highlight(k_read, color=KAP), highlight(h_read, color=HOF)
            self.play(FadeIn(k_hl), Indicate(kdot, color=KAP, scale_factor=1.6), run_time=0.9)
            self.cue("70", prefix=True)
            self.play(Indicate(hdot, color=HOF, scale_factor=1.6), FadeIn(h_hl), run_time=0.9)

        with self.beat("real"):
            # real models at (about) the same budget
            g_ring = Circle(radius=0.2, color=INK, stroke_width=5).move_to(P(*GOPHER))
            c_ring = Circle(radius=0.2, color=REAL, stroke_width=5).move_to(P(*CHIN))
            g_lab = plate(VGroup(text("Gopher", size=Size.SMALL, color=INK, weight=BOLD),
                                 text("280B · 300B", size=Size.SMALL, color=INK)).arrange(DOWN, buff=0.08))
            g_lab.move_to(plane.c2p(2.45, 0.5))
            c_lab = plate(VGroup(text("Chinchilla", size=Size.SMALL, color=REAL, weight=BOLD),
                                 text("70B · 1.4T", size=Size.SMALL, color=REAL)).arrange(DOWN, buff=0.08))
            c_lab.move_to(plane.c2p(0.75, 2.3))
            self.play(FadeOut(mult), FadeOut(cost), run_time=0.4)
            self.cue("gopher")
            self.play(Create(g_ring), FadeIn(g_lab, shift=UP * 0.1), run_time=0.9)
            self.cue("chinchilla")
            self.play(Create(c_ring), FadeIn(c_lab, shift=DOWN * 0.1), run_time=0.9)
            diag = DashedLine(P(1e9, TPP * 1e9), P(1e13 / TPP, 1e13), color=REAL, stroke_width=4, dash_length=0.12)
            d_lab = label(rf"D = {TPP}\,N", math=True, size=Size.LABEL, color=REAL).move_to(plane.c2p(2.6, 2.2))
            self.cue(spoken(TPP))
            self.play(Create(diag), FadeIn(d_lab), run_time=1.2)

        with self.beat("pearce"):
            band_old = VGroup(k_name, k_rule, h_name, h_rule)
            self.play(FadeOut(k_hl), FadeOut(h_hl), FadeOut(band_old), FadeOut(k_read), FadeOut(h_read), run_time=0.5)
            self.remove(k_read, h_read)
            p_name = text("Pearce & Song, 2024", size=Size.SMALL, color=PURPLE_K, weight=BOLD)
            p_rows = VGroup(
                tex(rf"\text{{non-embedding, small: }}\cO{{{PEARCE_K}}}\;\approx\;\cO{{{A_K}}}", size=Size.SMALL + 2),
                tex(rf"\text{{all parameters: }}\cB{{{PEARCE_T}}}\;\approx\;\cB{{{A_H:.2f}}}", size=Size.SMALL + 2),
            ).arrange(DOWN, buff=0.14)
            panel = VGroup(p_name, p_rows).arrange(DOWN, buff=0.14)
            band.fit(panel, upscale=False)
            self.play(FadeIn(p_name, shift=DOWN * 0.1), run_time=0.5)
            # Chinchilla's own data, refitted two ways, from the same starting run
            def refit_path(a, color):
                x0, y0 = math.log10(H0) - 9, math.log10(toks(C0, H0)) - 10
                return DashedLine(plane.c2p(x0, y0), plane.c2p(x0 + a * T_END, y0 + (1 - a) * T_END),
                                  color=color, stroke_width=9, dash_length=0.16).set_z_index(4)
            k_like, t_like = refit_path(PEARCE_K, PURPLE_K), refit_path(PEARCE_T, PURPLE_K)
            self.cue("non", prefix=True)
            self.play(FadeIn(p_rows[0], shift=DOWN * 0.1), run_time=0.7)
            self.cue("0.78", prefix=True)
            self.play(Create(k_like), run_time=1.4)
            self.cue("everything")
            self.play(FadeIn(p_rows[1], shift=DOWN * 0.1), FadeOut(k_like), run_time=0.7)
            self.play(Create(t_like), run_time=1.4)

        with self.beat("takeaway"):
            final = tex(r"N\propto C^{0.5},\quad D\propto C^{0.5}", size=Size.HEADLINE, color=REAL)
            band.fit(final, upscale=False)
            self.play(FadeOut(panel, shift=UP * 0.1), FadeOut(t_like), run_time=0.4)
            self.play(FadeIn(final, shift=UP * 0.1), run_time=0.8)
            self.play(FadeIn(highlight(final, color=REAL)), Indicate(hdot, color=REAL, scale_factor=1.6), run_time=1.0)

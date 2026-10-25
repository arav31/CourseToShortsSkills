"""Entropy counts yes/no questions (Shannon 1948, Sections 6 and 10).

A source sends A, B, C, D with chances 1/2, 1/4, 1/8, 1/8. The question tree "A?" -> "B?" -> "C?"
needs 1, 2, 3, 3 questions; the average 7/4 = 1.75 equals the entropy. Recording answers as bits
gives the code 0, 10, 110, 111; the message AAAABBCD takes 14 bits instead of 16.
"""

from fractions import Fraction
from math import log2

from shortkit import *

BEATS = [
    ("hook", "How many yes or no questions does it take, on average, to guess a hidden letter?"),
    ("source", "In his 1948 paper, A Mathematical Theory of Communication, Claude Shannon uses this source: A half the time, B a quarter, C and D an eighth each."),
    ("first", "Ask about the likeliest letter first. Is it A? Half the time, one question is enough."),
    ("deeper", "If not: is it B? Then: is it C? B takes two questions; C and D take three."),
    ("average", "Weight each count by its chance: a half times one, a quarter times two, an eighth times three, twice. One point seven five."),
    ("surprise", "A letter with chance one over two to the k takes k questions: log base two of one over p, its surprise."),
    ("formula", "The average surprise is Shannon's entropy, H. Here, one point seven five bits."),
    ("code", "Write yes as zero and no as one, and the questions become a code: zero, one zero, one one zero, one one one."),
    ("message", "Four A's, two B's, a C and a D take fourteen bits. Two questions per letter would take sixteen."),
    ("takeaway", "Fourteen bits over eight letters is one point seven five per letter: the entropy, the average number of yes or no questions."),
]

# ---- the worked example, computed (checked again in runs/paper-shannon/checks/examples.py)
LET = ["A", "B", "C", "D"]
P = {"A": Fraction(1, 2), "B": Fraction(1, 4), "C": Fraction(1, 8), "D": Fraction(1, 8)}
CODE = {"A": "0", "B": "10", "C": "110", "D": "111"}  # yes = 0, no = 1 along the question path
Q = {s: len(CODE[s]) for s in LET}                    # questions asked = 1, 2, 3, 3
AVG = sum(P[s] * Q[s] for s in LET)                    # 7/4
H = sum(float(P[s]) * log2(1 / float(P[s])) for s in LET)
assert AVG == Fraction(7, 4) and abs(H - float(AVG)) < 1e-12
assert all(log2(1 / P[s]) == Q[s] for s in LET)
MSG = "AAAABBCD"
BITS = "".join(CODE[s] for s in MSG)
FIXED = {"A": "00", "B": "01", "C": "10", "D": "11"}
FIXED_BITS = "".join(FIXED[s] for s in MSG)
assert len(BITS) == 14 and len(FIXED_BITS) == 16 and Fraction(len(BITS), len(MSG)) == AVG
assert spoken(float(AVG)) in BEATS[4][1].lower() and spoken(float(AVG)) in BEATS[6][1]
assert spoken(len(BITS)) in BEATS[8][1].lower() and spoken(len(FIXED_BITS)) in BEATS[8][1]
assert spoken(len(MSG)) in BEATS[9][1].lower()

COL = {"A": BLUE_K, "B": ORANGE_K, "C": PURPLE_K, "D": "#F78FB3"}


def frac_tex(f: Fraction) -> str:
    return rf"{f.numerator}/{f.denominator}"


class Short(ShortScene):
    def construct(self):
        # ---------------- persistent objects ----------------
        # probability bar along the bottom of the stage: widths proportional to the chances
        bar_w, bar_h, bar_y = 8.0, 1.1, -2.05
        x0 = -bar_w / 2
        blocks, bar_letters, bar_fracs = {}, {}, {}
        for s in LET:
            w = float(P[s]) * bar_w
            r = Rectangle(width=w, height=bar_h, stroke_color=COL[s], stroke_width=4,
                          fill_color=COL[s], fill_opacity=0.28)
            r.move_to([x0 + w / 2, bar_y, 0])
            x0 += w
            blocks[s] = r
            bar_letters[s] = text(s, size=Size.LABEL, color=COL[s], weight=BOLD).move_to(r.get_center() + UP * 0.24)
            bar_fracs[s] = tex(frac_tex(P[s]), size=Size.LABEL).move_to(r.get_center() + DOWN * 0.24)
        bar = VGroup(*blocks.values())

        # staircase question tree
        R = 0.44
        pos = {
            "qA": (-2.6, 3.2), "A": (-3.55, 2.0),
            "qB": (-1.5, 2.0), "B": (-2.45, 0.8),
            "qC": (-0.4, 0.8), "C": (-1.35, -0.4), "D": (0.55, -0.4),
        }

        def node(key, label_s, color):
            c = Circle(radius=R, stroke_color=color, stroke_width=5, fill_color=BG, fill_opacity=1)
            c.move_to([*pos[key], 0])
            t = text(label_s, size=Size.LABEL, color=color, weight=BOLD).move_to(c)
            return VGroup(c, t)

        qnodes = {k: node(k, k[1] + "?", YELLOW_K) for k in ("qA", "qB", "qC")}
        leaves = {s: node(s, s, COL[s]) for s in LET}
        for s in LET:
            leaves[s][0].set_fill(COL[s], opacity=0.28)
            leaves[s][0].set_z_index(1)
            leaves[s][1].set_z_index(2)
        for q in qnodes.values():
            q[0].set_z_index(1)
            q[1].set_z_index(2)

        def edge(a, b):
            pa, pb = np.array([*pos[a], 0]), np.array([*pos[b], 0])
            d = (pb - pa) / np.linalg.norm(pb - pa)
            return Line(pa + d * R, pb - d * R, stroke_color=MUTED, stroke_width=5)

        edges = {
            ("qA", "A"): edge("qA", "A"), ("qA", "qB"): edge("qA", "qB"),
            ("qB", "B"): edge("qB", "B"), ("qB", "qC"): edge("qB", "qC"),
            ("qC", "C"): edge("qC", "C"), ("qC", "D"): edge("qC", "D"),
        }

        def edge_label(key, word):
            ln = edges[key]
            side = LEFT if ln.get_end()[0] < ln.get_start()[0] else RIGHT
            return plate(text(word, size=Size.SMALL, color=MUTED)).next_to(ln.get_center(), side, buff=0.14)

        YES = {("qA", "A"), ("qB", "B"), ("qC", "C")}   # "yes" ends the questioning; "no" asks on
        assert all(CODE[k[1]].endswith("0") for k in YES) and CODE["D"] == "111"
        yes_no = {k: edge_label(k, "yes" if k in YES else "no") for k in edges}

        # question-count badges under the leaves
        badges = {s: tex(str(Q[s]), size=Size.LABEL, color=YELLOW_K).next_to(leaves[s], DOWN, buff=0.14) for s in LET}

        # right-hand column for the running sum
        col = Zone("sum", 1.3, 3.75, -0.95, 3.75)

        # ---------------- beats ----------------
        with self.beat("hook"):
            hidden = node("qA", "?", INK)
            hidden.move_to(STAGE.point(0.5, 0.62)).scale(1.5)
            self.title("Entropy counts questions",
                       FadeIn(bar, lag_ratio=0.15), *[FadeIn(bar_letters[s]) for s in LET])
            self.play(FadeIn(hidden, scale=0.6), run_time=0.8)
            self.play(Indicate(hidden, color=YELLOW_K, scale_factor=1.15), run_time=1.0)

        with self.beat("source"):
            credit = VGroup(
                text("Claude Shannon, 1948", size=Size.SMALL, color=MUTED),
                text("A Mathematical Theory of Communication", size=Size.SMALL, color=INK),
            ).arrange(DOWN, buff=0.08)
            credit = plate(credit, opacity=0.95)
            STAGE.fit(credit, upscale=False, align="top", buff=0.02)
            self.play(FadeIn(credit, shift=DOWN * 0.15), FadeOut(hidden), run_time=0.9)
            inner = credit._sk_inner
            self.cue("Mathematical")
            self.play(inner[1].animate.set_color(YELLOW_K), run_time=0.6)
            self.cue("Claude")
            self.play(inner[1].animate.set_color(INK), inner[0].animate.set_color(YELLOW_K), run_time=0.6)
            self.cue("source")
            self.play(inner[0].animate.set_color(MUTED), Indicate(bar, color=YELLOW_K, scale_factor=1.03), run_time=0.6)
            for s, word in zip(LET, ["half", "quarter", "eighth", "eighth"]):
                if s != "D":
                    self.cue(word)
                self.play(FadeIn(bar_fracs[s], shift=UP * 0.1), Indicate(blocks[s], color=COL[s], scale_factor=1.04),
                          run_time=0.5)

        with self.beat("first"):
            self.play(FadeIn(qnodes["qA"], scale=0.7), run_time=0.6)
            self.cue("Half")
            self.play(Create(edges[("qA", "A")]), FadeIn(yes_no[("qA", "A")]),
                      TransformFromCopy(bar_letters["A"], leaves["A"][1]), FadeIn(leaves["A"][0]), run_time=1.0)
            self.play(FadeIn(badges["A"], shift=DOWN * 0.1),
                      blocks["A"].animate.set_fill(opacity=0.5), run_time=0.6)

        with self.beat("deeper"):
            self.play(Create(edges[("qA", "qB")]), FadeIn(yes_no[("qA", "qB")]), FadeIn(qnodes["qB"], scale=0.7),
                      run_time=0.8)
            self.play(Create(edges[("qB", "B")]), FadeIn(yes_no[("qB", "B")]),
                      TransformFromCopy(bar_letters["B"], leaves["B"][1]), FadeIn(leaves["B"][0]), run_time=0.8)
            self.cue("then")
            self.play(Create(edges[("qB", "qC")]), FadeIn(yes_no[("qB", "qC")]), FadeIn(qnodes["qC"], scale=0.7),
                      run_time=0.8)
            self.play(Create(edges[("qC", "C")]), FadeIn(yes_no[("qC", "C")]),
                      Create(edges[("qC", "D")]), FadeIn(yes_no[("qC", "D")]),
                      TransformFromCopy(bar_letters["C"], leaves["C"][1]), FadeIn(leaves["C"][0]),
                      TransformFromCopy(bar_letters["D"], leaves["D"][1]), FadeIn(leaves["D"][0]), run_time=0.9)
            self.cue("two")
            self.play(FadeIn(badges["B"], shift=DOWN * 0.1), run_time=0.5)
            self.cue("three")
            self.play(FadeIn(badges["C"], shift=DOWN * 0.1), FadeIn(badges["D"], shift=DOWN * 0.1), run_time=0.5)

        with self.beat("average"):
            rows = VGroup(*[
                tex(("" if i == 0 else "+") + rf"\tfrac{{{P[s].numerator}}}{{{P[s].denominator}}}\cdot \cY{{{Q[s]}}}",
                    size=Size.HEADLINE + 6)
                for i, s in enumerate(LET)
            ]).arrange(DOWN, buff=0.28, aligned_edge=RIGHT)
            for s, rw in zip(LET, rows):
                rw.set_color(COL[s])
            total_lbl = tex(r"=", size=Size.HEADLINE + 6, color=GREEN_K)
            tracker = ValueTracker(0)
            total_val = live_text(lambda: f"{tracker.get_value():.3f}".rstrip("0").rstrip(".") if tracker.get_value() else "0",
                                  size=Size.HEADLINE + 6, color=GREEN_K, align="left")
            widest = text("1.375", size=Size.HEADLINE + 6)  # widest running value (1/2 + 2/4 + 3/8)  # layout stand-in for the final value
            total = VGroup(total_lbl, widest).arrange(RIGHT, buff=0.2)
            column = VGroup(rows, total).arrange(DOWN, buff=0.4, aligned_edge=RIGHT)
            col.fit(column, upscale=False, align="top")
            total_val.move_to(widest, aligned_edge=LEFT)
            total = VGroup(total_lbl, total_val)
            rule = Line(total.get_corner(UL) + UP * 0.2 + LEFT * 0.1, rows.get_corner(DR) + DOWN * 0.2 + RIGHT * 0.05,
                        stroke_color=MUTED, stroke_width=3)
            rule.put_start_and_end_on(np.array([rows.get_left()[0], rule.get_start()[1], 0]),
                                      np.array([rows.get_right()[0], rule.get_start()[1], 0]))
            running = 0
            for i, (s, word) in enumerate(zip(LET, ["half", "quarter", "eighth", "twice"])):
                self.cue(word)
                running += float(P[s] * Q[s])
                anims = [FadeIn(rows[i], shift=LEFT * 0.3), Indicate(badges[s], color=YELLOW_K, scale_factor=1.4),
                         Indicate(bar_fracs[s], color=COL[s], scale_factor=1.25),
                         tracker.animate.set_value(running)]
                if i == 0:
                    total_val.update()
                    self.play(FadeIn(total), Create(rule), run_time=0.3)
                self.play(*anims, run_time=0.8)
            self.cue("point")
            box = highlight(total, color=GREEN_K)
            self.play(FadeIn(box), run_time=0.5)

        with self.beat("surprise"):
            pows = {s: tex(rf"2^{{-\cY{{{Q[s]}}}}}", size=Size.LABEL + 6).move_to(bar_fracs[s]) for s in LET}
            self.play(FadeOut(box), *[FadeOut(bar_fracs[s], shift=UP * 0.1) for s in LET],
                      *[FadeIn(pows[s], shift=UP * 0.1) for s in LET], run_time=0.9)
            self.cue("takes")
            self.play(*[Indicate(badges[s], color=YELLOW_K, scale_factor=1.4) for s in LET],
                      *[Indicate(pows[s], color=YELLOW_K, scale_factor=1.2) for s in LET], run_time=1.2)
            # the sum column gives way to the surprise of each letter: log2(1/p) = its question count
            head = tex(r"\log_2\frac{1}{p}", size=Size.HEADLINE + 6, color=YELLOW_K)
            srows = VGroup(*[tex(rf"\log_2 {P[s].denominator}=\cY{{{Q[s]}}}", size=Size.HEADLINE + 6, color=COL[s])
                             for s in LET]).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
            stable = VGroup(head, srows).arrange(DOWN, buff=0.4)
            col.fit(stable, upscale=False, align="top")
            self.cue("log")
            self.play(FadeOut(rows), FadeOut(rule), FadeOut(total), run_time=0.5)
            total_val.clear_updaters()
            self.play(FadeIn(head, shift=DOWN * 0.1), run_time=0.6)
            self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in srows], lag_ratio=0.25), run_time=1.2)

        with self.beat("formula"):
            # the probability bar becomes the formula that averages the surprises
            f_lhs = tex(r"H=\sum p\,\log_2(1/p)", size=Size.HEADLINE + 4, color=GREEN_K)
            f_rhs = tex(rf"={float(AVG):g}\ \text{{bits}}", size=Size.HEADLINE + 4, color=GREEN_K)
            formula = plate(VGroup(f_lhs, f_rhs).arrange(RIGHT, buff=0.18), opacity=0.95)
            STAGE.fit(formula, upscale=False)
            formula.move_to(STAGE.point(0.5, 0)).align_to(STAGE.point(0.5, 0) + UP * 0.05, DOWN)
            self.play(FadeOut(bar), *[FadeOut(bar_letters[s]) for s in LET], *[FadeOut(pows[s]) for s in LET],
                      run_time=0.6)
            self.play(FadeIn(formula[0]), Write(f_lhs), run_time=1.4)
            self.cue("Here")
            self.play(FadeIn(f_rhs, shift=LEFT * 0.1), run_time=0.7)

        with self.beat("code"):
            zero_one = {}
            for k, lbl in yes_no.items():
                bit = "0" if k in YES else "1"
                zero_one[k] = plate(tex(bit, size=Size.LABEL, color=YELLOW_K)).move_to(lbl)
            self.play(*[FadeOut(lbl) for lbl in yes_no.values()],
                      *[FadeIn(b) for b in zero_one.values()], run_time=0.9)
            codes = {s: tex(rf"\texttt{{{CODE[s]}}}", size=Size.LABEL + 4, color=COL[s], math=False).move_to(badges[s])
                     for s in LET}
            for s, (word, nth) in zip(LET, [("zero", 1), ("one", 1), ("one", 2), ("one", 4)]):
                self.cue(word, nth=nth)
                self.play(ReplacementTransform(badges[s], codes[s]), run_time=0.6)

        with self.beat("message"):
            # the code key replaces the tree; the bar and the formula make room for the message
            key_y = 3.35
            key_parts = []
            key_targets = []
            for i, s in enumerate(LET):
                leaf_t = leaves[s].copy().scale(0.85)
                code_t = codes[s].copy()
                grp = VGroup(leaf_t, code_t).arrange(RIGHT, buff=0.15)
                grp.move_to([-3.05 + i * 2.05, key_y, 0])
                key_targets.append(grp)
            tree_rest = VGroup(*qnodes.values(), *edges.values(), *zero_one.values())
            self.play(FadeOut(tree_rest), FadeOut(stable), FadeOut(formula), run_time=0.5)
            self.play(*[leaves[s].animate.scale(0.85).move_to(key_targets[i][0]) for i, s in enumerate(LET)],
                      *[codes[s].animate.move_to(key_targets[i][1]) for i, s in enumerate(LET)], run_time=0.8)

            cw = 0.86
            letters = VGroup(*[
                VGroup(Square(cw, stroke_color=COL[s], stroke_width=4, fill_color=COL[s], fill_opacity=0.28),
                       text(s, size=Size.LABEL, color=COL[s], weight=BOLD))
                for s in MSG
            ]).arrange(RIGHT, buff=0.1).move_to([0, 2.35, 0])
            for g in letters:
                g[1].move_to(g[0])

            bw = 0.47

            def strip(bits, owners, y):
                cells = VGroup()
                for b, s in zip(bits, owners):
                    sq = Rectangle(width=bw, height=0.62, stroke_color=COL[s], stroke_width=3,
                                   fill_color=COL[s], fill_opacity=0.22)
                    cells.add(VGroup(sq, text(b, size=Size.SMALL, color=INK)))
                cells.arrange(RIGHT, buff=0.02).move_to([0, y, 0])
                for c in cells:
                    c[1].move_to(c[0])
                return cells

            owners = "".join(s * len(CODE[s]) for s in MSG)
            var = strip(BITS, owners, 1.3)
            owners_f = "".join(s * 2 for s in MSG)
            fix = strip(FIXED_BITS, owners_f, 0.05)
            var_lbl = text(f"{len(BITS)} bits", size=Size.LABEL, color=GREEN_K).next_to(var, DOWN, buff=0.14).align_to(var, RIGHT)
            fix_lbl = text(f"{len(FIXED_BITS)} bits", size=Size.LABEL, color=RED_K).next_to(fix, DOWN, buff=0.14).align_to(fix, RIGHT)
            fix_tag = text("2 questions each", size=Size.SMALL, color=MUTED).next_to(fix, DOWN, buff=0.14).align_to(fix, LEFT)
            var_tag = text("Shannon's tree", size=Size.SMALL, color=MUTED).next_to(var, DOWN, buff=0.14).align_to(var, LEFT)

            self.play(LaggedStart(*[FadeIn(g, shift=DOWN * 0.2) for g in letters], lag_ratio=0.12), run_time=0.9)
            # each letter turns into its codeword cells
            groups, k = [], 0
            for s in MSG:
                n = len(CODE[s])
                groups.append(VGroup(*var[k:k + n]))
                k += n
            self.play(LaggedStart(*[AnimationGroup(Indicate(letters[i], color=COL[MSG[i]], scale_factor=1.15),
                                                   FadeIn(groups[i], shift=DOWN * 0.35))
                                    for i in range(len(MSG))], lag_ratio=0.3), run_time=2.0)
            self.play(FadeIn(var_lbl), FadeIn(var_tag), run_time=0.4)
            self.cue("Two", nth=1)
            fgroups = [VGroup(*fix[2 * i:2 * i + 2]) for i in range(len(MSG))]
            self.play(LaggedStart(*[FadeIn(fgroups[i], shift=DOWN * 0.35) for i in range(len(MSG))],
                                  lag_ratio=0.2), run_time=1.5)
            self.play(FadeIn(fix_lbl), FadeIn(fix_tag), run_time=0.5)

        with self.beat("takeaway"):
            final = plate(tex(rf"\frac{{{len(BITS)}\ \text{{bits}}}}{{{len(MSG)}\ \text{{letters}}}}={float(AVG):g}=H",
                              size=Size.HEADLINE, color=GREEN_K), opacity=0.95)
            final.move_to([0, -1.95, 0])
            self.play(Indicate(var, color=GREEN_K, scale_factor=1.05), Indicate(var_lbl, color=GREEN_K, scale_factor=1.2),
                      run_time=0.9)
            self.play(FadeIn(final, shift=UP * 0.15), run_time=0.9)
            self.cue("entropy")
            self.play(FadeIn(highlight(final, color=GREEN_K, buff=0.05)), run_time=0.6)
            self.cue("questions")
            self.play(*[Indicate(leaves[s], color=COL[s], scale_factor=1.25) for s in LET],
                      *[Indicate(codes[s], color=COL[s], scale_factor=1.25) for s in LET], run_time=1.2)

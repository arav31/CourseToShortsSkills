from __future__ import annotations

import math
import unittest

from tools import stem_course


MIT_14_01_EXPECTATIONS = {
    "Supply and demand equilibrium": ("econ_supply_demand", "market", "market_equilibrium", r"Q_s(P)=Q_d(P)"),
    "Elasticity": ("econ_elasticity", "elasticity", "price_elasticity", r"E_d=\frac{\%\Delta Q}{\%\Delta P}"),
    "Consumer choice": ("econ_budget", "consumer_choice", "consumer_choice", r"p_x x+p_y y=I"),
    "Externalities": ("econ_externality_wedge", "marginal_analysis", "externality", r"MSC=MSB"),
    "Preferences and utility": ("econ_budget", "consumer_choice", "utility", r"U(x,y)"),
    "Budget constraints": ("econ_budget", "consumer_choice", "budget_constraint", r"p_x x+p_y y\leq I"),
    "Marginal rate of substitution": ("econ_budget", "consumer_choice", "mrs", r"MRS=-\frac{MU_x}{MU_y}"),
    "Demand curves": ("econ_supply_demand", "market", "demand_curve", r"Q_d=D(P)"),
    "Income and substitution effects": ("econ_budget", "consumer_choice", "income_substitution", r"\Delta x=SE+IE"),
    "Production functions": ("econ_production_isoquants", "marginal_analysis", "production", r"q=f(L,K)"),
    "Costs and cost curves": ("econ_cost_curves", "marginal_analysis", "costs", r"TC=FC+VC"),
    "Perfect competition": ("econ_perfect_competition", "marginal_analysis", "competition", r"P=MC"),
    "Monopoly": ("econ_monopoly", "marginal_analysis", "monopoly", r"MR=MC"),
    "Oligopoly and strategic behavior": ("game_payoff", "cournot", "oligopoly", r"\pi_i(q_i,q_{-i})"),
    "Welfare and surplus": ("econ_supply_demand", "market", "surplus", r"TS=CS+PS"),
    "Taxes and deadweight loss": ("econ_tax_wedge", "tax", "deadweight_loss", r"DWL=\frac{1}{2}t(Q_0-Q_t)"),
    "Public goods": ("econ_public_goods_vertical_sum", "marginal_analysis", "public_goods", r"MB_{social}=\sum_i MB_i"),
    "Comparative statics": ("econ_supply_demand", "market", "comparative_statics", r"\Delta y/\Delta x"),
    "Price ceilings": ("econ_supply_demand", "market", "price_ceiling", r"P\leq \bar P"),
    "Price floors": ("econ_supply_demand", "market", "price_floor", r"P\geq \underline P"),
}


CURATED_ECONOMICS = {concept.name: concept for concept in stem_course.ECONOMICS}


def short_for(topic: str, index: int = 1) -> dict[str, object]:
    return stem_course.concept_to_short(CURATED_ECONOMICS[topic], index)


class EconomicsPlanningTests(unittest.TestCase):
    def test_all_twenty_mit_topics_have_correct_formula_family_and_state(self) -> None:
        self.assertEqual(len(MIT_14_01_EXPECTATIONS), 20)

        for index, (topic, expectation) in enumerate(MIT_14_01_EXPECTATIONS.items(), 1):
            expected_kind, expected_family, expected_mode, expected_formula = expectation
            with self.subTest(topic=topic):
                short = short_for(topic, index)
                kind = stem_course.infer_visual_kind(short)
                semantic = stem_course.econ_semantic_data(short, kind)

                self.assertEqual(kind, expected_kind)
                self.assertEqual(short["formula"], expected_formula)
                self.assertEqual(semantic["family"], expected_family)
                self.assertEqual(semantic["mode"], expected_mode)
                self.assertTrue(semantic["verified"])
                self.assertGreaterEqual(len(semantic["state_sequence"]), 4)
                self.assertEqual(len(semantic["state_sequence"]), len(set(semantic["state_sequence"])))
                self.assertNotEqual(semantic["state_sequence"][0], semantic["state_sequence"][-1])

                animation_plan = stem_course.build_animation_plan(short)
                self.assertEqual(stem_course.animation_plan_contract_errors(animation_plan, short), [])
                self.assertEqual(animation_plan["semantic_support"]["family"], "economics")
                self.assertEqual(animation_plan["semantic_support"]["status"], "supported")

    def test_tax_and_strategy_source_terms_use_dedicated_routes(self) -> None:
        expectations = {
            "Government Taxation and Deadweight Loss": "econ_tax_wedge",
            "Tax Incidence": "econ_tax_wedge",
            "Nash Equilibrium": "game_payoff",
            "Dominant Strategy": "game_payoff",
        }
        for topic, expected_kind in expectations.items():
            with self.subTest(topic=topic):
                concept = stem_course.source_term_concept(topic, "economics")
                short = stem_course.concept_to_short(concept, 1)
                self.assertEqual(concept.visual_type, expected_kind)
                self.assertEqual(stem_course.infer_visual_kind(short), expected_kind)

        collusion = stem_course.source_term_concept("Oligopoly II", "economics")
        self.assertEqual(collusion.visual_type, "game_payoff")
        collusion_short = stem_course.concept_to_short(collusion, 1)
        semantic = stem_course.econ_semantic_data(collusion_short, "game_payoff")
        self.assertEqual(semantic["model_id"], "oligopoly_collusion")
        self.assertEqual(semantic["scenario_mode"], "cournot_collusive_comparison")
        self.assertEqual(semantic["route_key"], "economics:cournot_collusion")

    def test_fixture_has_no_duplicate_worked_examples_or_generic_fallbacks(self) -> None:
        examples: list[tuple[str, str]] = []
        modes: list[str] = []
        for index, topic in enumerate(MIT_14_01_EXPECTATIONS, 1):
            short = short_for(topic, index)
            kind = stem_course.infer_visual_kind(short)
            worked = short["worked_example"]
            examples.append((str(worked["setup"]).strip().lower(), str(worked["calculation"]).strip().lower()))
            modes.append(str(stem_course.econ_semantic_data(short, kind)["mode"]))
            self.assertIn(kind, stem_course.ECON_VISUAL_KINDS)
            self.assertNotIn(kind, {"numeric_rule", "state_machine"})

        self.assertEqual(len(examples), len(set(examples)))
        self.assertEqual(len(modes), len(set(modes)))


class EconomicsGeometryTests(unittest.TestCase):
    def test_tax_wedge_recomputes_prices_quantity_revenue_and_dwl(self) -> None:
        short = short_for("Taxes and deadweight loss")
        semantic = stem_course.econ_semantic_data(short, "econ_tax_wedge")

        self.assertAlmostEqual(semantic["buyer_price"] - semantic["seller_price"], semantic["tax"])
        self.assertAlmostEqual(semantic["buyer_burden"] + semantic["seller_burden"], semantic["tax"])
        self.assertLess(semantic["quantity_after"], semantic["quantity_before"])
        self.assertAlmostEqual(semantic["taxed_supply"]["intercept"] - semantic["supply"]["intercept"], semantic["tax"])
        self.assertAlmostEqual(semantic["taxed_supply"]["slope"], semantic["supply"]["slope"])
        self.assertAlmostEqual(semantic["tax_revenue"], semantic["tax"] * semantic["quantity_after"])
        self.assertAlmostEqual(
            semantic["deadweight_loss"],
            0.5 * semantic["tax"] * (semantic["quantity_before"] - semantic["quantity_after"]),
        )
        self.assertEqual(
            semantic["state_sequence"],
            [
                "pre_tax_equilibrium",
                "parallel_tax_shift",
                "buyer_seller_wedge",
                "tax_revenue_rectangle",
                "lost_trade_triangle",
                "aligned_dwl_derivation",
            ],
        )
        self.assertTrue(math.isclose(semantic["tax"], 3.0))
        self.assertTrue(math.isclose(semantic["quantity_before"], 12.0))
        self.assertTrue(math.isclose(semantic["quantity_after"], 9.0))
        self.assertTrue(math.isclose(semantic["buyer_price"], 11.5))
        self.assertTrue(math.isclose(semantic["seller_price"], 8.5))
        self.assertTrue(math.isclose(semantic["tax_revenue"], 27.0))
        self.assertTrue(math.isclose(semantic["deadweight_loss"], 4.5))

    def test_payoff_state_computes_best_responses_and_nash_cell(self) -> None:
        semantic = stem_course.econ_semantic_data(short_for("Oligopoly and strategic behavior"), "game_payoff")

        self.assertEqual(semantic["row_names"], ["low", "high"])
        self.assertEqual(semantic["column_names"], ["low", "high"])
        self.assertEqual(semantic["payoffs"], [[(6.0, 6.0), (2.0, 8.0)], [(8.0, 2.0), (4.0, 4.0)]])
        self.assertEqual(semantic["row_best"], [[1, 0], [1, 1]])
        self.assertEqual(semantic["column_best"], [[0, 1], [1, 1]])
        self.assertEqual(semantic["nash"], [[1, 1]])
        self.assertEqual(semantic["dominant_rows"], [1])
        self.assertEqual(semantic["dominant_columns"], [1])
        self.assertEqual(semantic["cournot_motion"]["nash_firm_quantity"], 30.0)
        self.assertEqual(semantic["cournot_motion"]["collusive_firm_quantity"], 22.5)
        self.assertEqual(
            semantic["state_sequence"],
            [
                "reaction_functions",
                "firm_1_best_response",
                "firm_2_best_response",
                "best_response_iteration",
                "mutual_best_response",
                "collusive_comparison",
            ],
        )

        dominant = stem_course.econ_semantic_data(short_for("Dominant strategies"), "game_payoff")
        self.assertEqual(dominant["dominant_rows"], [0])
        self.assertEqual(dominant["dominant_columns"], [0])
        self.assertEqual(dominant["nash"], [[0, 0]])


class EconomicsRendererTests(unittest.TestCase):
    def generated_source(self, topic: str) -> str:
        short = short_for(topic)
        return stem_course.manim_scene(short, "EconomicsVisualRegression", stem_course.build_animation_plan(short))

    def renderer_block(self, source: str, start: str, end: str) -> str:
        return source[source.index(start):source.index(end, source.index(start))]

    def test_all_twenty_scenes_embed_semantic_mathtex_formulas(self) -> None:
        for topic in MIT_14_01_EXPECTATIONS:
            with self.subTest(topic=topic):
                short = short_for(topic)
                source = self.generated_source(topic)
                compile(source, "generated_" + stem_course.slugify(topic) + ".py", "exec")
                self.assertIn(repr(short["formula"]), source)
                self.assertNotIn("\b", source)
                self.assertNotIn("\f", source)

        formula_source = self.renderer_block(
            self.generated_source("Supply and demand equilibrium"),
            "def econ_formula_mob",
            "def build_game_payoff_canvas",
        )
        self.assertIn("self.formula_block(", formula_source)
        self.assertIn("_economics_formula_latex", formula_source)
        self.assertIn("font_size=max(58, int(font_size))", formula_source)
        self.assertNotIn("Text(self.econ_readable_formula", formula_source)
        self.assertNotIn("economics_text", formula_source)

    def test_economics_helper_latex_keeps_non_economics_scenes_compilable(self) -> None:
        short = stem_course.concept_to_short(stem_course.ALGORITHMS[0], 1)
        source = stem_course.manim_scene(
            short,
            "NonEconomicsTemplateRegression",
            stem_course.build_animation_plan(short),
        )

        compile(source, "generated_non_economics_scene.py", "exec")
        self.assertNotIn("\b", source)
        self.assertNotIn("\f", source)
        tax_literal = next(line for line in source.splitlines() if "begin{aligned}DWL" in line)
        self.assertIn(r'\begin{aligned}DWL&=\frac{1}{2}t(Q_0-Q_t)\\', tax_literal)

    def test_tax_renderer_advances_one_causal_construction_per_hold(self) -> None:
        source = self.generated_source("Taxes and deadweight loss")
        renderer = self.renderer_block(source, "def build_tax_wedge_canvas", "def build_elasticity_canvas")

        compile(source, "generated_tax_scene.py", "exec")
        self.assertIn('state = self.build_tax_wedge_canvas(data)', source)
        self.assertIn('lanes = self.econ_visual_lanes()', renderer)
        self.assertIn('def tax_stage_action(cue_index, animations, removals=None):', renderer)
        self.assertEqual(renderer.count('tax_stage_action('), 7)
        self.assertIn('self.register_semantic_actions(actions)', renderer)
        self.assertIn('TransformFromCopy(supply, shifted_supply)', renderer)
        self.assertIn('TransformFromCopy(before, buyer)', renderer)
        self.assertIn('TransformFromCopy(before, seller)', renderer)
        self.assertIn('GrowArrow(wedge)', renderer)
        self.assertIn('Create(revenue)', renderer)
        self.assertIn('Create(lost_trade)', renderer)
        self.assertIn('GrowArrow(loss_arrow)', renderer)
        self.assertIn('FadeOut(old_cue)', renderer)
        self.assertIn('FadeIn(next_cue)', renderer)
        self.assertIn('removals=[shift_arrow, shift_label]', renderer)
        self.assertIn('rate_func=smooth', renderer)
        self.assertIn('price_guides = VGroup(', renderer)
        self.assertIn('def tax_formula_atom(latex, fallback, font_size, color, max_width=None):', renderer)
        self.assertIn('def tax_formula_block(latex, fallback, font_size, color, max_width, max_height=1.0):', renderer)
        self.assertIn('if self.economics_formula_needs_unicode_fallback(atom):', renderer)
        self.assertIn('if self.economics_formula_needs_unicode_fallback(formula):', renderer)
        self.assertIn('equation_panel = Rectangle(', renderer)
        self.assertIn('height=1.06', renderer)
        self.assertIn('equation_center = 0.5 * (lanes["equation"]["top"] + lanes["equation"]["bottom"])', renderer)
        self.assertIn('cue._economics_lane = "equation"', renderer)
        self.assertIn(r'S_t(Q)=S(Q)+t', renderer)
        self.assertIn(r'E_0\to(P_b,P_s,Q_t)', renderer)
        self.assertIn(r'P_b-P_s=t=', renderer)
        self.assertIn(r'R=tQ_t=', renderer)
        self.assertIn(r'b=Q_0-Q_t=', renderer)
        self.assertIn(r'\begin{aligned}DWL&=\frac{1}{2}t(Q_0-Q_t)', renderer)
        self.assertIn("tax_safe_stage_bottom_sequence", renderer)
        self.assertIn('if state_name == "example_calculation"', renderer)
        self.assertIn('"Before tax: Q₀ is "', renderer)
        self.assertIn('"After tax: Qₜ is "', renderer)
        self.assertIn('"Revenue is "', renderer)
        self.assertIn('". Deadweight loss is "', renderer)
        self.assertIn('font_size=max(34, int(font_size))', renderer)
        self.assertIn('self._economics_transformed = True', source)
        self.assertIn("tax_revenue_rectangle", source)
        self.assertIn("aligned_dwl_derivation", source)
        self.assertNotIn('Transform(progress', renderer)
        self.assertNotIn('tax_progress_state', renderer)
        self.assertNotIn('tax_trace_action', renderer)
        self.assertNotIn('MoveAlongPath(tracer', renderer)
        self.assertNotIn('Circle(radius=0.31', renderer)
        self.assertNotIn('construction_glyph', renderer)
        self.assertNotIn('quantity_before_label', renderer)
        self.assertNotIn('price_before_label', renderer)
        self.assertNotIn("DWL = 0.5", renderer)

    def test_tax_mathtex_sources_and_unicode_fallbacks_are_explicit_pairs(self) -> None:
        source = self.generated_source("Taxes and deadweight loss")
        renderer = self.renderer_block(source, "def build_tax_wedge_canvas", "def build_elasticity_canvas")

        semantic_sources = [
            r'\begin{aligned}DWL&=\frac{1}{2}t(Q_0-Q_t)',
            r'S_t(Q)=S(Q)+t',
            r'P_b-P_s=t=',
            r'R=tQ_t=',
            r'b=Q_0-Q_t=',
        ]
        unicode_fallbacks = [
            'DWL = ½t(Q₀ − Qₜ)',
            'Sₜ(Q) = S(Q) + t',
            'Pᵦ − Pₛ = t = ',
            'R = tQₜ = ',
            'b = Q₀ − Qₜ = ',
        ]
        for semantic in semantic_sources:
            self.assertIn(semantic, renderer)
        for fallback in unicode_fallbacks:
            self.assertIn(fallback, renderer)

        formula_helper = self.renderer_block(source, "def econ_formula_mob", "def econ_formula_result")
        self.assertIn('values.get("kind") == "econ_tax_wedge"', formula_helper)
        self.assertIn('"tax_wedge": "DWL = ½t(Q₀ − Qₜ)"', formula_helper)
        self.assertIn('clean_fallback_kind', formula_helper)
        self.assertIn('self.economics_formula_needs_unicode_fallback(formula)', formula_helper)
        economics_helpers = self.renderer_block(source, "def econ_visual_lanes", "def econ_structured_axes")
        self.assertIn('tex_backend == "tectonic-fitz"', economics_helpers)
        self.assertIn('def economics_unicode_formula(', economics_helpers)
        self.assertIn('formula._formula_render_mode = "semantic_unicode_fallback"', economics_helpers)
        self.assertIn('formula._economics_unicode_fallback = str(fallback)', economics_helpers)
        self.assertIn('formula._tax_formula_latex = str(latex)', renderer)
        self.assertIn('formula._tax_formula_fallback = str(fallback)', renderer)
        self.assertNotIn('"DWL = (1/2)', renderer)
        self.assertNotIn('"DWL = (1)/(2)', renderer)

    def test_economics_geometry_equation_and_prose_lanes_do_not_overlap(self) -> None:
        source = self.generated_source("Taxes and deadweight loss")
        helpers = self.renderer_block(source, "def econ_visual_lanes", "def economics_formula_needs_unicode_fallback")
        renderer = self.renderer_block(source, "def build_tax_wedge_canvas", "def build_elasticity_canvas")

        self.assertIn('"geometry": {"top": 2.62, "bottom": -2.55}', helpers)
        self.assertIn('"equation": {"top": -2.72, "bottom": -3.98}', helpers)
        self.assertIn('"prose": {"top": -4.15, "bottom": -6.45}', helpers)
        self.assertLess(-2.72, -2.55)
        self.assertLess(-4.15, -3.98)
        self.assertIn('top=lanes["equation"]["top"] - 0.05', renderer)
        self.assertIn('bottom=lanes["equation"]["bottom"] + 0.05', renderer)
        self.assertIn('complete_calculation = [', renderer)

    def test_tax_plot_labels_are_clamped_inside_runtime_safe_bounds(self) -> None:
        source = self.generated_source("Taxes and deadweight loss")
        renderer = self.renderer_block(source, "def build_tax_wedge_canvas", "def build_elasticity_canvas")

        self.assertIn('def tax_place_plot_label(mob, anchor, offset=ORIGIN):', renderer)
        self.assertIn('left = axes.get_left()[0] + 0.18', renderer)
        self.assertIn('right = axes.get_right()[0] - 0.18', renderer)
        self.assertIn('bottom = max(axes.get_bottom()[1] + 0.14, lanes["geometry"]["bottom"] + 0.08)', renderer)
        self.assertIn('top = min(axes.get_top()[1] - 0.14, lanes["geometry"]["top"] - 0.08)', renderer)
        self.assertIn('self.fit_in(mob, max_width=right - left, max_height=0.62)', renderer)
        self.assertIn('raise ValueError("tax plot label escaped the safe axes bounds")', renderer)
        self.assertIn('mob._tax_safe_bounds = (left, right, bottom, top)', renderer)
        self.assertGreaterEqual(renderer.count('tax_place_plot_label('), 10)
        for label in (
            'demand_tag',
            'supply_tag',
            'before_label',
            'shifted_tag',
            'buyer_label',
            'seller_label',
            'quantity_label',
            'revenue_label',
            'lost_label',
        ):
            self.assertRegex(renderer, rf'tax_place_plot_label\(\s*{label},')
        self.assertNotIn('quantity_before_label', renderer)
        self.assertNotIn('price_before_label', renderer)

    def test_game_renderer_uses_matrix_gutters_and_persists_best_responses(self) -> None:
        source = self.generated_source("Oligopoly and strategic behavior")
        renderer = self.renderer_block(source, "def build_game_payoff_canvas", "def advance_game_payoff_canvas")

        compile(source, "generated_game_scene.py", "exec")
        self.assertIn('state = self.build_game_payoff_canvas(data)', source)
        self.assertIn('width=2.9', renderer)
        self.assertIn('height=1.82', renderer)
        self.assertIn('self.formula_atom(self.fmt(payoff[0]), font_size=58', renderer)
        self.assertIn('self.formula_atom(self.fmt(payoff[1]), font_size=58', renderer)
        self.assertIn('lanes = self.econ_visual_lanes()', renderer)
        self.assertIn('max_height=4.98', renderer)
        self.assertIn('top=lanes["geometry"]["top"]', renderer)
        self.assertIn('bottom=lanes["geometry"]["bottom"]', renderer)
        self.assertIn('row_winners_by_column = [', renderer)
        self.assertIn('column_winners_by_row = [', renderer)
        self.assertIn('def payoff_tick(payoff, color, edge):', renderer)
        self.assertIn('return Line(start, end, color=color, stroke_width=4)', renderer)
        self.assertIn('def equilibrium_corner_mark(cell):', renderer)
        corner_block = self.renderer_block(renderer, 'def equilibrium_corner_mark(cell):', 'nash_marks = {')
        self.assertEqual(corner_block.count('Line('), 8)
        self.assertNotIn('SurroundingRectangle(', corner_block)
        self.assertIn('def vertical_comparison(column, winners):', renderer)
        self.assertIn('def horizontal_comparison(row, winners):', renderer)
        self.assertIn('guide = DoubleArrow(', renderer)
        self.assertIn('stroke_width=4', renderer)
        self.assertIn('MoveAlongPath(cursor, path)', renderer)
        self.assertIn('row_marks = {', renderer)
        self.assertIn('column_marks = {', renderer)
        self.assertIn('nash_marks = {', renderer)
        self.assertIn('edge = "left" if column == 0 else "right"', renderer)
        self.assertIn('edge = "top" if row == 0 else "bottom"', renderer)
        self.assertIn('label.next_to(cells[row_index], LEFT, buff=0.52)', renderer)
        self.assertIn('label.next_to(cells[0][column_index], UP, buff=0.52)', renderer)
        self.assertIn('def comparison_action(spec, marks):', renderer)
        self.assertIn('FadeOut(guide)', renderer)
        self.assertIn('*[TransformFromCopy(cursor, mark) for mark in marks]', renderer)
        self.assertIn('RoundedRectangle(width=0.96, height=0.96', renderer)
        self.assertIn('*[Create(nash_marks[(row, column)])', renderer)
        self.assertIn('def nash_action(run_time):', renderer)
        self.assertIn('def result_action(run_time):', renderer)
        self.assertIn('self.play(FadeIn(final_formula)', renderer)
        self.assertIn('actions.extend([nash_action, result_action])', renderer)
        self.assertIn('self.register_semantic_actions(actions)', renderer)
        self.assertIn('rate_func=linear', renderer)
        self.assertIn('row_player = Text("Firm A", font_size=42', renderer)
        self.assertIn('column_player = Text("Firm B", font_size=42', renderer)
        self.assertIn('"row_marks": row_marks', renderer)
        self.assertIn('"column_marks": column_marks', renderer)
        self.assertIn('"nash_marks": nash_marks', renderer)
        self.assertIn('equation_center = 0.5 * (lanes["equation"]["top"] + lanes["equation"]["bottom"])', renderer)
        self.assertIn('top=lanes["equation"]["top"]', renderer)
        self.assertIn('bottom=lanes["equation"]["bottom"]', renderer)
        self.assertIn(r's^*=(\mathrm{', renderer)
        self.assertIn('if self.economics_formula_needs_unicode_fallback(formula):', renderer)
        self.assertIn('formula._game_formula_fallback = str(fallback)', renderer)
        self.assertNotIn('SurroundingRectangle(', renderer)
        self.assertNotIn('edge_bracket', renderer)
        self.assertNotIn('selection_sweep', renderer)
        self.assertNotIn('nash_pulse', renderer)
        self.assertNotIn('Transform(nash_marks', renderer)
        self.assertNotIn('Write(final_formula)', renderer)
        self.assertNotIn('comparison_focus', renderer)
        self.assertIn("mutual_best_response", source)

    def test_oligopoly_renderer_moves_reaction_states_and_collusive_outcome(self) -> None:
        source = self.generated_source("Oligopoly and strategic behavior")
        renderer = self.renderer_block(
            source,
            "def build_oligopoly_reaction_canvas",
            "def build_game_payoff_canvas",
        )

        self.assertIn('values.get("model_id") == "oligopoly"', source)
        self.assertIn('lambda rival: reaction_intercept - 0.5 * rival', renderer)
        self.assertIn('lambda rival: 2.0 * (reaction_intercept - rival)', renderer)
        self.assertIn('def firm_a_response_action(run_time):', renderer)
        self.assertIn('def firm_b_response_action(run_time):', renderer)
        self.assertIn('def best_response_iteration_action(run_time):', renderer)
        self.assertIn('MoveAlongPath(response_a', renderer)
        self.assertRegex(renderer, r'MoveAlongPath\(\s*response_b,')
        self.assertIn('MoveAlongPath(outcome', renderer)
        self.assertIn('Transform(nash_dot, collusive_dot)', renderer)
        self.assertIn('"Nash: each 30 | Q=60 | P=40"', renderer)
        self.assertIn('"Collusion: each 22.5 | Q=45 | P=55"', renderer)
        self.assertIn('font_size=42', renderer)
        self.assertNotIn('SurroundingRectangle', renderer)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from tools import stem_course
from tools.video_economics_models import validate_economics_video_payload


DEDICATED = {
    "Externalities": ("econ_externality_wedge", "economics:externality_wedge"),
    "Production functions": ("econ_production_isoquants", "economics:production_isoquants"),
    "Costs and cost curves": ("econ_cost_curves", "economics:cost_curves"),
    "Perfect competition": ("econ_perfect_competition", "economics:perfect_competition"),
    "Monopoly": ("econ_monopoly", "economics:monopoly"),
    "Public goods": ("econ_public_goods_vertical_sum", "economics:public_goods_vertical_sum"),
    "International trade": ("econ_international_trade", "economics:international_trade"),
    "Tariff": ("econ_tariff", "economics:tariff"),
    "Labor market": ("econ_labor_market", "economics:labor_market"),
    "Adverse selection": ("econ_adverse_selection", "economics:adverse_selection"),
    "Moral hazard": ("econ_moral_hazard", "economics:moral_hazard"),
    "Healthcare insurance": ("econ_healthcare_insurance", "economics:healthcare_insurance"),
}


def short_for(concept: str) -> dict[str, object]:
    spec = stem_course.economics_topic_spec(concept, fail_closed=True)
    assert spec is not None
    kind, _mode, formula, _prerequisites = spec
    return {
        "index": 1,
        "concept": concept,
        "hook": "Watch the decision rule move the same economic objects.",
        "intuition": "The retained curves determine the corrected outcome.",
        "formula": formula,
        "plain_formula": formula,
        "visual_type": kind,
        "worked_example": {
            "setup": "Use the exact schedules shown in the semantic payload.",
            "calculation": "Apply each named transition in economic order.",
            "takeaway": "The final marker satisfies the displayed invariant.",
        },
    }


class EconomicsVideoIntegrationTests(unittest.TestCase):
    def test_income_substitution_scene_has_a_dedicated_compensated_demand_path(self) -> None:
        short = short_for("Income and substitution effects")
        short["concept"] = "Demand curves and income/substitution effects"
        source = stem_course.manim_scene(
            short,
            "IncomeSubstitutionScene",
            stem_course.build_animation_plan(short),
        )

        self.assertIn('values.get("mode") == "income_substitution"', source)
        self.assertIn('boundary, "ORIGINAL BUDGET"', source)
        self.assertIn('compensated, "COMPENSATED"', source)
        self.assertIn('new_budget, "NEW BUDGET"', source)
        self.assertIn('state["point"].animate.move_to(middle_center)', source)
        self.assertIn('state["point"].animate.move_to(target_center)', source)
        self.assertIn('stroke_width=10', source)
        self.assertIn('"#A371F7"', source)
        self.assertIn('"#7EE787"', source)
        self.assertIn('"#F7C948"', source)
        self.assertIn("['Demand curves and', 'income/substitution effects']", source)
        self.assertIn('play_income_substitution_example', source)
        self.assertIn('state.get("income_substitution_run_time", 4.75)', source)
        compile(source, "generated_income_substitution_scene.py", "exec")

    def test_income_substitution_close_uses_vectors_instead_of_tiny_footer_copy(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index('if isinstance(economics, dict) and economics.get("mode") == "income_substitution":')
        end = helpers.index('self.economics_stage_setup_sequence(setup_stages, font_size=44)', start)
        dedicated_close = helpers[start:end]

        self.assertIn('state["substitution_vector"]', dedicated_close)
        self.assertIn('state["income_vector"]', dedicated_close)
        self.assertIn('calculation_duration * 0.9', dedicated_close)
        self.assertIn('ShowPassingFlash', dedicated_close)
        self.assertNotIn('economics_stage_bottom_sequence', dedicated_close)

    def test_generated_scene_embeds_economics_layout_and_fallback_contracts(self) -> None:
        short = short_for("Monopoly")
        source = stem_course.manim_scene(
            short,
            "EconomicsLayoutContractScene",
            stem_course.build_animation_plan(short),
        )

        renderer_start = source.index("def build_exact_representative_econ_canvas")
        renderer_end = source.index("def play_econ_visual", renderer_start)
        renderer = source[renderer_start:renderer_end]
        monopoly_start = renderer.index('if kind == "econ_monopoly":')
        monopoly_end = renderer.index('elif kind in {"econ_international_trade"', monopoly_start)
        monopoly = renderer[monopoly_start:monopoly_end]

        self.assertIn("axes.scale(0.9).shift(DOWN * 0.48)", monopoly)
        self.assertIn("axes.c2p(0, y_max) + RIGHT * 0.62 + UP * 0.28", monopoly)
        self.assertIn("demand_anchor_q = 0.78 * x_max", monopoly)
        self.assertIn("mr_anchor_q = 0.18 * x_max", monopoly)
        self.assertIn("mc_anchor_q = 0.82 * x_max", monopoly)
        self.assertIn('"choose_monopoly_quantity": choose_quantity', monopoly)
        self.assertIn('"project_monopoly_price": project_price', monopoly)
        self.assertIn('"mark_deadweight_loss": mark_deadweight_loss', monopoly)
        self.assertNotIn("Transform(", monopoly)
        self.assertIn("label._course_persistent_plot_label = True", renderer)
        self.assertIn("self.register_semantic_transition_actions(groups", renderer)
        self.assertIn("place_economics_graph_label(", source)
        self.assertIn("if inside and not any(box.overlaps(obstacle) for obstacle in blocked):", source)
        self.assertIn('raise ValueError("no collision-free graph label position inside plot bounds")', source)
        self.assertIn('min_font_size=44', source)
        self.assertIn('max_chars_per_line=28', source)
        self.assertIn("def normalize_economics_formula_fallback(self, source):", source)
        self.assertIn("fallback = self.normalize_economics_formula_fallback(fallback or latex)", source)
        self.assertNotIn("from tools", source)
        compile(source, "generated_economics_layout_scene.py", "exec")

    def test_generated_scene_imports_without_repository_on_sys_path(self) -> None:
        short = short_for("Monopoly")
        source = stem_course.manim_scene(
            short,
            "PortableEconomicsScene",
            stem_course.build_animation_plan(short),
        )
        harness = '''
import importlib.util
import sys
import types

manim = types.ModuleType("manim")
class Scene:
    pass
class Config:
    pass
manim.Scene = Scene
manim.config = Config()
manim.__all__ = ["Scene", "config"]
sys.modules["manim"] = manim
spec = importlib.util.spec_from_file_location("portable_scene", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.PortableEconomicsScene
'''
        with tempfile.TemporaryDirectory() as directory:
            scene_path = Path(directory) / "portable_scene.py"
            scene_path.write_text(source, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-I", "-c", harness, str(scene_path)],
                cwd=directory,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dedicated_topics_route_payload_and_renderer_together(self) -> None:
        for concept, (kind, route_key) in DEDICATED.items():
            with self.subTest(concept=concept):
                short = short_for(concept)
                self.assertEqual(stem_course.infer_visual_kind(short), kind)
                data = stem_course.visual_data_for(short, kind)["economics"]
                self.assertEqual(data["route_key"], route_key)
                self.assertEqual(validate_economics_video_payload(data["video_payload"]), [])
                descriptor = stem_course.animation_route_descriptor(short, kind)
                self.assertTrue(descriptor["supported"], descriptor["reason"])
                self.assertEqual(descriptor["route_key"], route_key)
                self.assertEqual(descriptor["renderer_implementation"]["visual_kind"], kind)

    def test_transition_callbacks_are_exact_and_present_in_manim_helpers(self) -> None:
        for concept, (kind, _route_key) in DEDICATED.items():
            with self.subTest(concept=concept):
                data = stem_course.visual_data_for(short_for(concept), kind)["economics"]
                expected = [row["kind"] for row in data["video_payload"]["transitions"]]
                self.assertEqual(data["transition_callbacks"], expected)
                for callback in expected:
                    self.assertIn("econ_transition_" + callback, stem_course.MANIM_SCENE_HELPERS)

    def test_representative_runtime_uses_exact_actions_and_column_bound_meters(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index("def build_exact_representative_econ_canvas")
        end = helpers.index("\ndef play_econ_visual", start)
        representative = helpers[start:end]

        self.assertIn("register_semantic_transition_actions(groups", representative)
        self.assertIn("Transform(price_line, world_line)", representative)
        self.assertIn("Transform(gap, gap_after)", representative)
        self.assertIn("Transform(demand_dot, demand_final)", representative)
        self.assertIn("token.animate.move_to(target)", representative)
        self.assertIn("Transform(effort_bar, effort_after)", representative)
        self.assertIn("Transform(patient_dot, insured_dot)", representative)
        self.assertIn(".move_to(background).align_to(background, DOWN)", representative)
        self.assertNotIn("economics_focus", representative)

        source = stem_course.manim_scene(
            short_for("Moral hazard"),
            "MoralHazardRuntimeContractScene",
            stem_course.build_animation_plan(short_for("Moral hazard")),
        )
        compile(source, "generated_moral_hazard_runtime_scene.py", "exec")

    def test_flagged_exact_routes_resolve_with_causal_motion(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index("def build_exact_representative_econ_canvas")
        end = helpers.index("\ndef play_econ_visual", start)
        representative = helpers[start:end]

        for callback in (
            "resolve_trade_gap",
            "resolve_low_risk_exit",
            "resolve_insurer_cost",
            "resolve_healthcare_overuse",
        ):
            with self.subTest(callback=callback):
                self.assertIn("def " + callback + "(run_time):", representative)
                self.assertIn("bind(actions, " + callback + ")", representative)

        self.assertIn("Transform(trade_scan, trade_scan_target)", representative)
        self.assertIn("Transform(trade_scan, trade_scan_mid)", representative)
        self.assertIn("token.animate.shift(RIGHT * 0.9)", representative)
        self.assertIn("pool_box.animate.stretch(0.78, 0", representative)
        self.assertIn("Create(cost_connector)", representative)
        self.assertIn("Transform(cost_band_start, cost_band_mid)", representative)
        self.assertIn("Transform(cost_scan, cost_scan_target)", representative)
        self.assertIn("Transform(overuse_band_start, overuse_band)", representative)
        self.assertIn("Transform(overuse_scan, overuse_scan_mid)", representative)
        self.assertIn("Transform(overuse_scan, overuse_scan_target)", representative)
        self.assertNotIn("def pulse_trade", representative)
        self.assertNotIn("def pulse_pool", representative)
        self.assertNotIn("def pulse_cost", representative)
        self.assertNotIn("def pulse_overuse", representative)

        # These passing canaries are intentionally outside the pacing repair.
        self.assertIn("def pulse_tariff(run_time):", representative)
        self.assertIn("bind(actions, pulse_tariff)", representative)
        self.assertIn("bind(actions, pulse_result(VGroup(demand_dot, supply_dot, guides, equation)))", representative)

    def test_mismatched_kind_and_corrupt_payload_fail_closed(self) -> None:
        short = short_for("Monopoly")
        with self.assertRaisesRegex(ValueError, "requires econ_monopoly"):
            stem_course.econ_semantic_data(short, "econ_curve")
        payload = stem_course.animation_renderer_state(short, "econ_monopoly")
        payload["transitions"][0]["after"] = {}
        with self.assertRaisesRegex(ValueError, "Invalid economics semantic renderer state"):
            stem_course.semantic_plan_contract(payload)

    def test_existing_economics_routes_keep_public_kinds_and_gain_typed_payloads(self) -> None:
        expected = {
            "Supply and demand equilibrium": "econ_supply_demand",
            "Consumer choice": "econ_budget",
            "Elasticity": "econ_elasticity",
            "Taxes and deadweight loss": "econ_tax_wedge",
            "Nash equilibrium": "game_payoff",
        }
        for concept, kind in expected.items():
            with self.subTest(concept=concept):
                self.assertEqual(stem_course.economics_topic_spec(concept, fail_closed=True)[0], kind)
                short = short_for(concept)
                economics = stem_course.visual_data_for(short, kind)["economics"]
                self.assertIn("video_payload", economics)
                self.assertEqual(validate_economics_video_payload(economics["video_payload"]), [])
                self.assertEqual(stem_course.animation_renderer_state(short, kind).get("payload_type"), "economics")


if __name__ == "__main__":
    unittest.main()

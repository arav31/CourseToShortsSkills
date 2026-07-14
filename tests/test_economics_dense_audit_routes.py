from __future__ import annotations

import unittest

from tools import stem_course
from tools.video_economics_models import build_economics_video_payload


class EconomicsDenseAuditRouteTests(unittest.TestCase):
    def short_for(self, title: str) -> dict[str, object]:
        concept = stem_course.source_term_concept(title, "economics")
        return stem_course.concept_to_short(concept, 1)

    def test_phone_cues_are_concise_for_competition_and_tax_routes(self) -> None:
        for title in (
            "Competition I",
            "Competition II",
            "Government Redistribution and Taxation",
        ):
            with self.subTest(title=title):
                short = self.short_for(title)
                for beat in stem_course.canonical_beat_schedule(short):
                    if beat["scene_state"] == "core_formula":
                        continue
                    self.assertLessEqual(len(str(beat["text"]).split()), 10)
                    self.assertLessEqual(len(beat["lines"]), 2)

    def test_oligopoly_routes_split_cournot_from_collusion(self) -> None:
        short = self.short_for("Oligopoly I")
        values = stem_course.visual_data_for(short, "game_payoff")["economics"]
        self.assertEqual(values["model_id"], "oligopoly")
        self.assertEqual(values["cournot_motion"]["nash_firm_quantity"], 30.0)
        self.assertIn("best_response_iteration", values["state_sequence"])

        collusion = build_economics_video_payload("Oligopoly II")
        self.assertEqual(collusion["model_id"], "oligopoly_collusion")
        self.assertEqual(collusion["family"], "cournot_collusion")
        self.assertEqual(collusion["result_fields"]["cournot_total_quantity"], 60.0)
        self.assertEqual(collusion["result_fields"]["collusive_total_quantity"], 45.0)

        collusion_short = self.short_for("Oligopoly II")
        collusion_values = stem_course.visual_data_for(
            collusion_short, "game_payoff"
        )["economics"]
        self.assertEqual(collusion_values["scenario_mode"], "cournot_collusive_comparison")
        self.assertEqual(collusion_values["numeric_setup"], {
            "demand_intercept": 100.0,
            "demand_slope": 1.0,
            "marginal_cost": 10.0,
        })
        self.assertEqual(collusion_values["result_fields"], collusion["result_fields"])
        descriptor = stem_course.animation_route_descriptor(collusion_short, "game_payoff")
        self.assertTrue(descriptor["supported"], descriptor["reason"])
        self.assertEqual(descriptor["route_key"], "economics:cournot_collusion")

        source = stem_course.manim_scene(
            short,
            "EconomicsDenseAuditOligopoly",
            stem_course.build_animation_plan(short),
        )
        self.assertIn('values.get("model_id") == "oligopoly"', source)
        self.assertNotRegex(source, r'short_(?:13|14)|short\["index"\]\s*==')

    def test_generated_economics_scene_uses_phone_typography_helpers(self) -> None:
        short = self.short_for("Competition I")
        source = stem_course.manim_scene(
            short,
            "EconomicsDenseAuditTypography",
            stem_course.build_animation_plan(short),
        )

        self.assertIn("def economics_readable_stages(self, stages, font_size=44):", source)
        self.assertIn("max_chars_per_line=32", source)
        self.assertIn("self.economics_stage_setup_sequence(setup_stages, font_size=44)", source)
        self.assertIn("self.economics_stage_bottom_sequence(calc_stages", source)
        compile(source, "generated_economics_dense_audit.py", "exec")

    def test_competition_removes_redundant_marker_copy_and_enlarges_essential_labels(self) -> None:
        short = self.short_for("Competition I")
        source = stem_course.manim_scene(
            short,
            "EconomicsCompetitionPhoneLabels",
            stem_course.build_animation_plan(short),
        )
        renderer = source[source.index("def play_dedicated_econ_visual"):source.index("def econ_transition_move")]

        self.assertIn('"firm_mc": "MC"', renderer)
        self.assertIn('"firm_output": ""', renderer)
        self.assertIn("label_font_size = 52", renderer)
        self.assertIn("max_width=2.3", renderer)
        self.assertNotIn('Text("FIRM OUTPUT"', renderer)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from tools import stem_course


CANARIES = (
    ("Introduction and Supply & Demand", "supply_demand"),
    ("Preferences and Utility Functions", "budget_choice"),
    ("Budget Constraints and Constrained Choice", "budget_choice"),
    ("Demand Curves and Income/Substitution Effects", "budget_choice"),
)


class EconomicsSemanticTransitionBindingTests(unittest.TestCase):
    def short_for(self, title: str, index: int) -> dict[str, object]:
        concept = stem_course.source_term_concept(title, "economics")
        return stem_course.concept_to_short(concept, index)

    def test_canary_families_generate_exact_callback_registration(self) -> None:
        for index, (title, family) in enumerate(CANARIES, start=1):
            with self.subTest(title=title):
                short = self.short_for(title, index)
                kind = stem_course.infer_visual_kind(short)
                payload = stem_course.animation_renderer_state(short, kind)
                source = stem_course.manim_scene(
                    short,
                    "EconomicsSemanticCanary" + str(index),
                    stem_course.build_animation_plan(short),
                )

                self.assertEqual(payload["family"], family)
                self.assertIn(
                    'payload.get("family") == "' + family + '"',
                    source,
                )
                self.assertIn(
                    "self.register_economics_family_transition_actions(values, {",
                    source,
                )
                for transition in payload["transitions"]:
                    self.assertIn('"' + str(transition["kind"]) + '":', source)
                compile(source, "generated_economics_semantic_canary.py", "exec")

    def test_family_binder_rejects_missing_and_duplicate_actions(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index("def register_economics_family_transition_actions")
        end = helpers.index("\ndef build_budget_canvas", start)
        binder = helpers[start:end]

        self.assertIn("Missing exact economics family action", binder)
        self.assertIn("Economics transition is bound more than once", binder)
        self.assertIn("self.register_semantic_transition_actions(", binder)
        self.assertIn("callback_metadata=callback_metadata or None", binder)
        self.assertIn("enforce_temporal_carriers=bool(callback_metadata)", binder)

    def test_family_callbacks_are_observable_and_use_authored_runtime(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        budget = helpers[
            helpers.index("def build_budget_canvas"):
            helpers.index("def advance_budget_canvas")
        ]
        market = helpers[
            helpers.index("def build_market_canvas"):
            helpers.index("def advance_market_canvas")
        ]

        self.assertIn("GrowFromEdge(feasible_set, DOWN)", budget)
        self.assertIn("Create(contour_low)", budget)
        self.assertIn('Transform(state["point"], middle)', budget)
        self.assertIn('Transform(state["point"], target)', budget)
        self.assertIn("self.semantic_timed_segments(run_time", budget)
        self.assertIn("Create(curve_mobs[index])", market)
        self.assertIn("GrowFromCenter(market_point", market)
        self.assertIn("Create(projections)", market)
        self.assertIn("self.semantic_timed_segments(run_time", market)

    def test_semantic_owned_examples_do_not_dispatch_legacy_advance_motion(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index("def play_example_visual")
        end = helpers.index("\ndef play_recall_visual", start)
        example = helpers[start:end]
        semantic_branch = example[
            example.index('semantic_payload.get("family") in'):
            example.index("representative_kinds =", example.index('semantic_payload.get("family") in'))
        ]

        self.assertIn('"supply_demand", "budget_choice"', semantic_branch)
        self.assertIn("economics_stage_setup_sequence", semantic_branch)
        self.assertIn("economics_stage_bottom_sequence", semantic_branch)
        self.assertNotIn("play_generic_visual", semantic_branch)

    def test_takeaway_handoff_is_a_sequential_lane_transaction(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        budget = helpers[
            helpers.index("def build_budget_canvas"):
            helpers.index("def advance_budget_canvas")
        ]
        market = helpers[
            helpers.index("def build_market_canvas"):
            helpers.index("def advance_market_canvas")
        ]
        example = helpers[
            helpers.index("def play_example_visual"):
            helpers.index("def play_recall_visual")
        ]

        self.assertIn("self.play_economics_cue_handoff([FadeIn(formula)], third)", budget)
        self.assertIn("self.play_economics_cue_handoff([FadeIn(result_formula)], second)", market)
        handoff = helpers[
            helpers.index("def play_economics_cue_handoff"):
            helpers.index("def complete_economics_cue_handoff")
        ]
        self.assertLess(handoff.index("FadeOut(mob"), handoff.index("self.remove(*outgoing)"))
        self.assertLess(handoff.index("self.remove(*outgoing)"), handoff.index("FadeIn(incoming"))
        self.assertIn("next_stages=takeaway_stages", example)
        self.assertIn("first_stage_visible=True", example)
        self.assertLess(
            example.index("next_stages=takeaway_stages"),
            example.index("first_stage_visible=True"),
        )


if __name__ == "__main__":
    unittest.main()

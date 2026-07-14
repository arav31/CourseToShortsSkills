from __future__ import annotations

import unittest

from tools import stem_course


class DynamicProgrammingExplanatoryArcTests(unittest.TestCase):
    def setUp(self) -> None:
        concept = stem_course.source_term_concept(
            "Dynamic Programming State Design",
            "algorithms",
        )
        self.short = stem_course.concept_to_short(concept, 15)
        self.semantic = stem_course.cs_dp_semantics(self.short)

    def test_grid_path_contract_teaches_the_full_causal_argument(self) -> None:
        contract = stem_course.semantic_plan_contract(
            stem_course.animation_renderer_state(self.short, stem_course.infer_visual_kind(self.short))
        )
        self.assertIsNotNone(contract)
        transitions = contract["transitions"]
        transition_ids = [transition["id"] for transition in transitions]

        for transition_id in (
            "grid_paths:problem_setup",
            "grid_paths:state_meaning",
            "grid_paths:recurrence_meaning",
            "grid_paths:base_cases",
            "grid_paths:sufficiency",
            "grid_paths:conclusion",
        ):
            self.assertIn(transition_id, transition_ids)
        self.assertEqual(
            len([transition_id for transition_id in transition_ids if ":update:" in transition_id]),
            6,
        )
        self.assertEqual(
            {transition["beat_state"] for transition in transitions},
            set(stem_course.SEMANTIC_TRANSITION_STATES),
        )
        self.assertTrue(all(float(transition.get("duration_weight", 0)) >= 2.5 for transition in transitions))

    def test_duration_is_earned_by_explanatory_actions(self) -> None:
        beats = stem_course.canonical_beat_schedule(self.short)
        active = [beat for beat in beats if beat["semantic_transition_ids"]]
        expected_weight = sum(float(beat["semantic_transition_weight"]) for beat in active)
        expected_floor = stem_course.MIN_SEMANTIC_ACTION_SECONDS * expected_weight

        self.assertGreaterEqual(expected_weight, 34.0)
        self.assertGreaterEqual(sum(float(beat["transition_motion_floor_seconds"]) for beat in active), expected_floor)
        self.assertGreater(sum(float(beat["duration"]) for beat in beats), 45.0)
        self.assertTrue(all("..." not in str(beat["text"]) for beat in beats))

    def test_generated_scene_keeps_identity_private_and_binds_every_callback(self) -> None:
        plan = stem_course.build_animation_plan(self.short)
        source = stem_course.manim_scene(self.short, "DPExplanatoryArc", plan)
        compile(source, "generated_dp_explanatory_arc.py", "exec")

        self.assertIn("At the same cell, every partial route has the same future", source)
        self.assertIn("routes reach the bottom-right destination", source)
        self.assertNotIn('f"final {final_cell_id}', source)
        self.assertNotIn("future...", source)
        for transition_id in (
            "grid_paths:problem_setup",
            "grid_paths:state_meaning",
            "grid_paths:recurrence_meaning",
            "grid_paths:base_cases",
            "grid_paths:sufficiency",
            "grid_paths:conclusion",
        ):
            self.assertIn(f'"{transition_id}"', source)

    def test_human_labels_never_expose_stable_object_syntax(self) -> None:
        final_update = self.semantic["updates"][-1]
        self.assertEqual(stem_course.dp_cell_display_name(2, 3), "state (2, 3)")
        label = stem_course.grid_path_update_display_label(final_update)
        self.assertEqual(label, "At (2, 3): 4 from above + 6 from left = 10")
        self.assertNotIn("dp:cell", label)


if __name__ == "__main__":
    unittest.main()

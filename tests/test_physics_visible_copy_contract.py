from __future__ import annotations

import ast
import inspect
import re
import unittest

from tools import stem_course
from tools.physics_video_copy import (
    PHYSICS_VISIBLE_COPY_DENYLIST,
    build_physics_visible_copy,
    validate_physics_visible_copy,
)
from tools.video_physics_models import MIT_8_01_VIDEO_ROUTES, ROUTES, build_physics_video_payload


class PhysicsVisibleCopyContractTests(unittest.TestCase):
    def test_every_exact_title_uses_numeric_evidence_and_family_invariant(self) -> None:
        for title, route in MIT_8_01_VIDEO_ROUTES.items():
            with self.subTest(title=title):
                payload = build_physics_video_payload(title)
                copy = payload["visible_copy"]
                self.assertEqual(validate_physics_visible_copy(copy), [])
                self.assertEqual(payload["invariant"], ROUTES[route.family].invariant)
                self.assertNotRegex(payload["invariant"], r"(?i)exact\s+mit|unit\s+\d+")
                for cue in copy.values():
                    self.assertRegex(cue, r"[-+]?\d")
                    for denied in PHYSICS_VISIBLE_COPY_DENYLIST:
                        self.assertIsNone(denied.search(cue))

    def test_visible_copy_filters_implementation_booleans(self) -> None:
        payload = build_physics_video_payload("1D Kinematics - Position and Velocity")
        payload["numeric_evidence"]["result"]["same_particle_and_clock"] = True
        copy = build_physics_visible_copy(payload)
        rendered = " ".join(copy.values()).casefold()
        self.assertNotIn("same particle and clock", rendered)
        self.assertNotIn("true", rendered)
        self.assertIn("final position = 24", rendered)

    def test_silent_physics_cues_are_the_payload_projection(self) -> None:
        short = {
            "concept": "1D Kinematics - Position and Velocity",
            "model_id": "kinematics_position_velocity",
        }
        state = stem_course.animation_renderer_state(short, "physics_kinematics")
        expected = build_physics_visible_copy(state)
        self.assertEqual(
            stem_course.silent_semantic_cue(short, "physics_kinematics", "example_setup", "fallback"),
            expected["setup"],
        )
        self.assertEqual(
            stem_course.silent_semantic_cue(short, "physics_kinematics", "example_calculation", "fallback"),
            expected["calculation"],
        )
        self.assertEqual(
            stem_course.silent_semantic_cue(short, "physics_kinematics", "example_takeaway", "fallback"),
            expected["takeaway"],
        )
        self.assertEqual(
            stem_course.silent_semantic_cue(short, "physics_kinematics", "core_idea", "fallback"),
            stem_course.concise_screen_clause(
                state["invariant"], max_words=stem_course.ANIMATION_PLAN_MAX_CUE_WORDS
            ),
        )

    def test_exact_transitions_follow_setup_calculation_result_order(self) -> None:
        short = {
            "concept": "1D Kinematics - Position and Velocity",
            "model_id": "kinematics_position_velocity",
        }
        assigned = stem_course.assigned_semantic_transition_groups(short, "physics_kinematics")
        self.assertEqual(
            [transition["after_state_id"] for transition in assigned["example_setup"]],
            ["setup"],
        )
        self.assertEqual(
            [transition["after_state_id"] for transition in assigned["example_calculation"]],
            ["calculation"],
        )
        self.assertEqual(
            assigned["example_takeaway"][0]["after_state_id"],
            "result",
        )
        self.assertTrue(
            all(
                transition.get("after_state_id") in {None, "result"}
                for transition in assigned["example_takeaway"]
            )
        )

    def test_vector_terminal_tracker_path_is_componentwise_monotonic(self) -> None:
        source = inspect.getsource(stem_course)
        start = source.index("def play_physics_vector_visual")
        end = source.index("def play_physics_center_of_mass_visual_legacy", start)
        vector_renderer = source[start:end]
        match = re.search(
            r"vector_states\s*=\s*self\.physics_interpolate_state_path\((\[.*?\])\s*,\s*state_count=16\)",
            vector_renderer,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        expression = match.group(1).replace("terminal_normalization", "1.0")
        keyframes = ast.literal_eval(expression)
        for before, after in zip(keyframes, keyframes[1:]):
            self.assertTrue(
                all(right >= left for left, right in zip(before, after)),
                msg=f"vector tracker regressed from {before} to {after}",
            )
        self.assertEqual(keyframes[-1], [1.0, 1.0, 1.0, 2.0])


if __name__ == "__main__":
    unittest.main()

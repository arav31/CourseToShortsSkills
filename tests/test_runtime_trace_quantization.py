import unittest

from tools import stem_course


class RuntimeTraceQuantizationTests(unittest.TestCase):
    def test_dynamic_programming_state_design_keeps_reachable_resolve_window(self) -> None:
        concept = stem_course.source_term_concept(
            "Dynamic Programming State Design",
            "algorithms",
        )
        short = stem_course.concept_to_short(concept, 15)
        plan = stem_course.build_animation_plan(short)
        final_beat = plan["beats"][-1]
        canonical_resolve = sum(
            float(beat["duration"])
            for beat in stem_course.canonical_beat_schedule(short)
            if beat["scene_state"] == "example_takeaway"
        )

        planned_duration = float(final_beat["end_seconds"]) - float(final_beat["start_seconds"])
        self.assertGreaterEqual(
            planned_duration + 1 / stem_course.RENDER_TIMELINE_FPS,
            canonical_resolve,
        )
        self.assertLessEqual(
            float(final_beat["evidence"]["after_seconds"]),
            float(final_beat["end_seconds"]),
        )
        expected_completion = stem_course.renderer_frame_seconds(
            float(final_beat["end_seconds"]) - 0.35,
            rounding="ceil",
        )
        self.assertEqual(
            float(final_beat["evidence"]["after_seconds"]),
            expected_completion,
        )

    def test_generated_runtime_validation_uses_renderer_frames(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS

        self.assertIn("def runtime_renderer_frame(self):", helpers)
        self.assertIn("round(renderer_time * frame_rate) / frame_rate", helpers)
        self.assertIn("float(getattr(renderer, \"time\", 0.0)) * frame_rate", helpers)
        self.assertIn("target_frame = self.runtime_target_frame(target)", helpers)
        self.assertIn("observed_frame != target_frame", helpers)
        self.assertNotIn("frame_tolerance =", helpers)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from tools import stem_course
from tools.physics_model_scenarios import get_physics_model_scenario


class RollingKinematicsRendererTests(unittest.TestCase):
    @staticmethod
    def helper_body(name: str, next_name: str) -> str:
        source = stem_course.MANIM_SCENE_HELPERS
        return source[source.index(f"def {name}("):source.index(f"def {next_name}(")]

    def test_runtime_payload_keeps_no_slip_quantities(self) -> None:
        scenario = get_physics_model_scenario("rolling_kinematics").as_dict()
        values = stem_course.physics_renderer_values_from_scenario("physics_kinematics", scenario)
        self.assertEqual(values["mode"], "rolling_kinematics")
        self.assertEqual(values["model_id"], "rolling_kinematics")
        for key in ("radius", "omega", "alpha", "contact_speed"):
            self.assertIn(key, values)
        self.assertEqual(values["contact_speed"], 0.0)

    def test_generated_source_has_dedicated_causal_rolling_scene(self) -> None:
        body = self.helper_body("play_physics_rolling_kinematics_visual", "play_physics_kinematics_visual")
        for token in (
            "Circle(", "ground = Line(", "spoke = always_redraw", "contact = always_redraw",
            "center_arrow", "rotation_arrow", "center displacement", "rotated arc length",
            r"v_{cm}=\omega R", r"a_{cm}=\alpha R", "zero contact speed",
            "-physical_distance() / radius", "configure_physics_motion",
        ):
            with self.subTest(token=token):
                self.assertIn(token, body)
        self.assertNotIn("Axes(", body)

    def test_phone_labels_have_a_readable_floor(self) -> None:
        body = self.helper_body("play_physics_rolling_kinematics_visual", "play_physics_kinematics_visual")
        self.assertRegex(body, r'physics_phone_text\(\s*"v_cm",\s*font_size=40')
        self.assertRegex(body, r'physics_phone_text\(\s*"omega",\s*font_size=40')
        start = body.index('"contact point: "')
        self.assertRegex(body[start:start + 180], r"font_size=(?:40|42)")
        self.assertIn('"no slip: zero contact speed"', body)
        self.assertNotIn("font_size=27", body)
        self.assertNotIn("font_size=28", body)

    def test_dispatch_uses_identity_without_short_id_hardcoding(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        dispatch = source[source.index("def play_physics_visual("):source.index("def play_wave_visual(")]
        self.assertIn('values.get("mode") == "rolling_kinematics"', dispatch)
        self.assertIn('values.get("model_id") == "rolling_kinematics"', dispatch)
        self.assertIn("play_physics_rolling_kinematics_visual", dispatch)
        self.assertNotIn("short_36", dispatch)

    def test_formula_fallback_is_rolling_specific(self) -> None:
        short = {"model_id": "rolling_kinematics", "scenario_mode": "rolling_kinematics"}
        formula = stem_course.physics_video_formula_text(short, "physics_kinematics")
        self.assertIn("omega R", formula)
        self.assertIn("alpha R", formula)
        self.assertIn("contact</sub> = 0", formula)
        self.assertNotIn("x(t)", formula)

    def test_takeaway_uses_no_slip_invariant_not_generic_graph_copy(self) -> None:
        body = self.helper_body("physics_caption_text", "physics_scene_text")
        self.assertIn('== "rolling_kinematics"', body)
        self.assertIn("the contact point is instantaneously at rest", body)


if __name__ == "__main__":
    unittest.main()

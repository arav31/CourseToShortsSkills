from __future__ import annotations

import argparse
import json
import math
import tempfile
import unittest
from pathlib import Path

from tools import stem_course


def vector_work_short() -> dict[str, object]:
    concept = stem_course.source_term_concept(
        "Kinetic Energy and Work in 2D and 3D",
        "physics",
    )
    return stem_course.concept_to_short(concept, 1)


class VectorWorkRendererTests(unittest.TestCase):
    def test_vector_work_recomputes_dot_product_energy_and_speed(self) -> None:
        short = vector_work_short()
        data = stem_course.physics_semantic_data(short, stem_course.infer_visual_kind(short))

        self.assertEqual(data["mode"], "work_energy_multidimensional")
        setup = data["numeric_setup"]
        calculation = data["model_scenario"]["calculation"]
        result = data["result_fields"]
        self.assertEqual(setup["displacement_vector"], [3.0, 4.0])
        self.assertEqual(setup["force_vector"], [6.0, 8.0])
        self.assertEqual(calculation["dot_product_terms"], [18.0, 32.0])
        self.assertAlmostEqual(calculation["dot_product_work"], 50.0)
        self.assertAlmostEqual(calculation["initial_kinetic_energy"], 25.0)
        self.assertAlmostEqual(result["final_kinetic_energy"], 75.0)
        self.assertAlmostEqual(result["final_speed"], math.sqrt(75.0))

    def test_vector_intent_cannot_downgrade_to_scalar_work(self) -> None:
        short = vector_work_short()
        short["worked_example"] = {
            **short["worked_example"],
            "setup": "A 2 kg puck moves from (0,0) to (3,4) m under a 10 N force, starting at 5 m/s.",
        }

        data = stem_course.physics_semantic_data(short, "physics_work")
        self.assertEqual(data["numeric_setup"]["force_vector"], [6.0, 8.0])
        self.assertAlmostEqual(data["model_scenario"]["calculation"]["dot_product_work"], 50.0)

    def test_generated_source_draws_vector_components_projection_and_path(self) -> None:
        short = vector_work_short()
        plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "VectorWorkCompatibility", plan)

        self.assertIn('values["mode"] == "vector_work_energy"', source)
        self.assertIn('force = values["force_vector"]', source)
        self.assertIn('displacement = values["displacement_vector"]', source)
        self.assertIn("x_component = DashedLine", source)
        self.assertIn("y_component = DashedLine", source)
        self.assertIn("projected_force = always_redraw", source)
        self.assertIn("work_progress = ValueTracker(0.0)", source)
        self.assertIn("def puck_point()", source)
        self.assertIn("measured_path = always_redraw", source)
        self.assertIn("force_arrow = always_redraw", source)
        self.assertIn("projection_drop = always_redraw", source)
        self.assertIn("height=0.82", source)
        self.assertIn("def vector_energy_shape", source)
        self.assertIn("0.52,", source)
        self.assertIn("0.94,", source)
        self.assertIn("show_dot_product,", source)
        self.assertIn("show_dot_product", source)
        self.assertIn("show_vector_result", source)
        self.assertIn("configure_physics_motion", source)
        self.assertNotIn("MoveAlongPath(puck, path_curve)", source)
        self.assertIn('"F dot d = "', source)
        vector_branch = source[
            source.index('if values["mode"] == "vector_work_energy"'):
            source.index('caption, result = self.physics_scene_text(phase, primary_lines, secondary_lines, result_lines, "work becomes the measured change in kinetic energy")')
        ]
        for secondary_label in ("dx_label", "dy_label", "start_label", "end_label", "force_label", "projection_label"):
            self.assertNotIn(secondary_label, vector_branch)
        self.assertIn("parameters = VGroup(", vector_branch)
        self.assertIn("projection_readout = self.physics_phone_text(", vector_branch)
        self.assertIn("dot_product = self.physics_phone_text(", vector_branch)
        self.assertIn("final = self.physics_phone_text(", vector_branch)
        self.assertIn("self.physics_atomic_text_handoff(projection_readout, dot_product)", vector_branch)
        compile(source, "<generated-vector-work-scene>", "exec")

    def test_storyboard_accepts_public_vector_work_short(self) -> None:
        short = vector_work_short()
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            stem_course.write_json(
                run / "short_plan.json",
                {"course_title": "Mechanics", "source_url": "fixture://mechanics", "shorts": [short]},
            )
            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            index_payload = json.loads(
                (run / stem_course.ANIMATION_PLAN_INDEX_NAME).read_text(encoding="utf-8")
            )
            artifact_path = run / index_payload["plans"][0]["path"]
            plan = json.loads(artifact_path.read_text(encoding="utf-8"))

        renderer_state = plan["concrete_example"]["renderer_state"]
        self.assertEqual(plan["semantic_support"]["status"], "supported")
        self.assertEqual(plan["semantic_support"]["route_key"], "physics:mit-8-01:22:work_energy_multidimensional")
        self.assertEqual(plan["semantic_support"]["semantic_mode"], "work_energy_multidimensional")
        self.assertEqual(renderer_state["mode"], "work_energy_multidimensional")
        self.assertEqual(renderer_state["model_scenario"]["calculation"]["dot_product_work"], 50.0)
        self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])


if __name__ == "__main__":
    unittest.main()

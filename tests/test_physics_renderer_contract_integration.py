from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools import stem_course
from tools.physics_model_scenarios import get_physics_model_scenario


class PhysicsRendererContractIntegrationTests(unittest.TestCase):
    def test_public_vector_and_circular_routes_reach_runtime_renderer(self) -> None:
        schedule = "Unit 1: Vectors\nUnit 2: Uniform Circular Motion"
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            stem_course.write_json(run / "source_pack.json", {
                "title": "Classical Mechanics",
                "materials": [{"kind": "page", "title": "Course Schedule", "text": schedule}],
            })
            stem_course.cmd_plan(argparse.Namespace(run=str(run), max_shorts=2))
            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            for index, short in enumerate(plan["shorts"], 1):
                storyboard = stem_course.read_json(run / stem_course.animation_plan_relative_path(index))
                self.assertEqual(storyboard["semantic_support"]["status"], "supported")
                source = stem_course.manim_scene(short, f"PhysicsContract{index}", storyboard)
                compile(source, "<physics-contract-scene>", "exec")

    def test_force_variants_satisfy_mode_specific_required_fields(self) -> None:
        for model_id in ("force_balance", "newton_first_law", "newton_second_law", "action_reaction"):
            with self.subTest(model_id=model_id):
                values = stem_course.physics_renderer_values_from_scenario(
                    "physics_force", get_physics_model_scenario(model_id).as_dict()
                )
                stem_course.validate_physics_renderer_values("physics_force", values)

    def test_circular_and_rolling_variants_satisfy_runtime_contracts(self) -> None:
        cases = (
            ("uniform_circular_motion", "physics_circular"),
            ("radial_acceleration", "physics_circular"),
            ("circular_position", "physics_circular"),
            ("circular_dynamics", "physics_circular"),
            ("rolling_kinematics", "physics_kinematics"),
        )
        for model_id, visual_kind in cases:
            with self.subTest(model_id=model_id):
                values = stem_course.physics_renderer_values_from_scenario(
                    visual_kind, get_physics_model_scenario(model_id).as_dict()
                )
                stem_course.validate_physics_renderer_values(visual_kind, values)

    def test_energy_variants_without_a_matching_scene_contract_fail_closed(self) -> None:
        for model_id in ("energy_conservation", "gravitational_potential_energy", "spring_potential_energy"):
            with self.subTest(model_id=model_id):
                with self.assertRaisesRegex(ValueError, "no compatible 'physics_energy' runtime renderer contract"):
                    stem_course.physics_renderer_values_from_scenario(
                        "physics_energy", get_physics_model_scenario(model_id).as_dict()
                    )

    def test_missing_required_payload_field_is_rejected_before_scene_generation(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required fields: duration"):
            stem_course.validate_physics_renderer_values("physics_kinematics", {
                "mode": "trajectory", "x0": 0.0, "v0": 1.0,
                "acceleration": 2.0, "positions": [0.0, 1.0],
            })


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import re
import unittest

from tools import stem_course


FAMILIES = (
    ("Circular Motion Acceleration", "physics_circular", "radial_acceleration"),
    ("Kinetic Energy and Work in 1D", "physics_work", "work_energy_1d"),
    ("Kinetic Energy and Work in 2D and 3D", "physics_work", "work_energy_multidimensional"),
    ("Potential Energy", "physics_energy", "potential_energy_configuration"),
    ("Rolling Kinematics", "physics_kinematics", "rolling_kinematics"),
)


def short_for(title: str) -> dict[str, object]:
    return stem_course.concept_to_short(stem_course.source_term_concept(title, "physics"), 1)


def helper_body(name: str, next_name: str) -> str:
    source = stem_course.MANIM_SCENE_HELPERS
    return source[source.index(f"def {name}("):source.index(f"def {next_name}(")]


class PhysicsDenseAuditRouteTests(unittest.TestCase):
    def test_flagged_families_route_by_semantics_not_short_ids(self) -> None:
        for title, expected_kind, expected_mode in FAMILIES:
            with self.subTest(title=title):
                short = short_for(title)
                kind = stem_course.infer_visual_kind(short)
                values = stem_course.physics_semantic_data(short, kind)
                source = stem_course.manim_scene(short, "DenseAuditRoute", stem_course.build_animation_plan(short))
                self.assertEqual(kind, expected_kind)
                self.assertEqual(values["mode"], expected_mode)
                self.assertIn(f"visual_kind={expected_kind}", source.splitlines()[0])
                self.assertIn(f"'{expected_kind}'", source)
                self.assertNotRegex(source, r"short_(?:11|21|22|24|36)\b")
                compile(source, f"<{expected_mode}-scene>", "exec")

    def test_phone_typography_and_atomic_work_handoff_contracts(self) -> None:
        scene_text = helper_body("physics_scene_text", "physics_math_mob")
        circular = helper_body("play_physics_circular_visual", "play_physics_rotation_visual")
        radial = circular[circular.index('if values["mode"] == "radial_acceleration"'):circular.index("    center = UP * 0.55")]
        work = helper_body("play_physics_work_visual", "play_physics_energy_visual_legacy")

        self.assertGreaterEqual(scene_text.count("font_size=46"), 2)
        self.assertIn('physics_phone_text("Delta v", font_size=42', radial)
        self.assertIn('"tangent velocities -> inward Delta v"', radial)
        self.assertNotIn("font_size=25", radial)
        self.assertNotIn("FadeOut(calc)", work)
        self.assertIn("self.add(calc)", work)
        self.assertIn("self.add(final, result)", work)

    def test_work_and_potential_motion_is_distributed_across_beats(self) -> None:
        work = helper_body("play_physics_work_visual", "play_physics_energy_visual_legacy")
        potential = helper_body("play_physics_energy_visual", "play_physics_momentum_visual")

        self.assertEqual(work.count("work_targets = ["), 2)
        for match in re.finditer(r"work_targets = \[(.*?)\]", work, re.S):
            self.assertGreaterEqual(len([part for part in match.group(1).split(",") if part.strip()]), 9)
        self.assertIn("work_progress.get_value()", work)
        self.assertGreaterEqual(work.count("configure_physics_motion"), 2)
        self.assertIn("transfer_progress.get_value()", potential)
        targets = re.search(r"transfer_targets = \[(.*?)\]", potential, re.S)
        self.assertIsNotNone(targets)
        self.assertGreaterEqual(len([part for part in targets.group(1).split(",") if part.strip()]), 9)

    def test_physics_state_batches_fill_long_semantic_beats(self) -> None:
        advance = helper_body("advance_concept_motion", "semantic_beat_hold")
        hold = helper_body("semantic_beat_hold", "hold_scene_state")
        configure = helper_body("configure_physics_motion", "physics_interpolate_state_path")
        self.assertIn("state_batches = self.semantic_terminal_batches", configure)
        self.assertIn('"state_batches": state_batches', configure)
        self.assertIn("allocated_frames = self.semantic_frame_partition", advance)
        self.assertIn("last_choreography_intervals", advance)
        self.assertIn("completed_batch_indices", advance)
        self.assertIn('motion.get("kind") == "physics_state"', hold)
        self.assertIn("self.advance_concept_motion(action_window)", hold)
        self.assertIn('beat.get("planned_arc_phase") in {"build", "resolve"}', hold)

    def test_physics_state_paths_are_densified_without_changing_endpoints(self) -> None:
        helper = helper_body("physics_interpolate_state_path", "advance_concept_motion")
        self.assertIn("state_count = max(len(normalized), int(state_count))", helper)
        self.assertIn("if index == state_count:", helper)
        self.assertIn("alpha = 1.0", helper)
        self.assertIn("normalized[segment + 1][axis]", helper)


if __name__ == "__main__":
    unittest.main()

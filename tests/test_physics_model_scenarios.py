from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import unittest

from tools.physics_model_scenarios import (
    FrozenFields,
    PHYSICS_MODEL_SCENARIO_DEFINITIONS,
    PHYSICS_MODEL_SCENARIO_REGISTRY,
    PHYSICS_MODEL_SCENARIOS,
    PHYSICS_SCENARIOS,
    PhysicsModelScenario,
    build_all_physics_model_scenarios,
    build_physics_model_scenario,
    get_physics_model_scenario,
    recompute_physics_model_scenario,
)
from tools.physics_model_specs import PHYSICS_MODEL_REGISTRY


def scenario(model_id: str) -> PhysicsModelScenario:
    return build_physics_model_scenario(model_id)


def contains_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, dict) or isinstance(value, FrozenFields):
        return any(contains_number(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return any(contains_number(item) for item in value)
    return False


def ordered_union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token for group in groups for token in group))


class PhysicsScenarioCoverageTests(unittest.TestCase):
    def test_every_registered_model_builds_a_complete_recomputable_scenario(self) -> None:
        scenarios = build_all_physics_model_scenarios()

        self.assertEqual(set(PHYSICS_MODEL_SCENARIO_DEFINITIONS), set(PHYSICS_MODEL_REGISTRY))
        self.assertEqual(set(PHYSICS_MODEL_SCENARIO_REGISTRY), set(PHYSICS_MODEL_REGISTRY))
        self.assertEqual(set(scenarios), set(PHYSICS_MODEL_REGISTRY))
        self.assertIs(PHYSICS_MODEL_SCENARIOS, PHYSICS_MODEL_SCENARIO_REGISTRY)
        self.assertIs(PHYSICS_SCENARIOS, PHYSICS_MODEL_SCENARIO_REGISTRY)
        self.assertEqual(len({item.mode for item in scenarios.values()}), len(scenarios))
        self.assertEqual(
            len({tuple(state.state_id for state in item.animation_states) for item in scenarios.values()}),
            len(scenarios),
        )

        for model_id, spec in PHYSICS_MODEL_REGISTRY.items():
            with self.subTest(model_id=model_id):
                item = scenarios[model_id]
                self.assertIsInstance(item, PhysicsModelScenario)
                self.assertEqual(item.model_id, model_id)
                self.assertEqual(item.mode, model_id)
                self.assertEqual(item, PHYSICS_MODEL_SCENARIO_REGISTRY[model_id])
                self.assertIs(get_physics_model_scenario(model_id), PHYSICS_MODEL_SCENARIO_REGISTRY[model_id])
                self.assertIs(item["numeric_setup"], item.setup)
                self.assertIs(item["calculation_fields"], item.calculation)
                self.assertIs(item["result_fields"], item.result)
                self.assertIs(item["results"], item.result)
                self.assertIs(item["animation_state_sequence"], item.animation_states)
                self.assertIs(item["evidence_tokens"], item.visible_evidence_tokens)
                self.assertTrue(item.setup)
                self.assertTrue(item.calculation)
                self.assertTrue(item.result)
                self.assertTrue(contains_number(item.setup))
                self.assertTrue(contains_number(item.calculation))
                self.assertTrue(contains_number(item.result))
                self.assertEqual([state.phase for state in item.animation_states], ["setup", "change", "result"])
                self.assertEqual([state.progress for state in item.animation_states], [0.0, 0.5, 1.0])
                self.assertEqual(len({state.state_id for state in item.animation_states}), 3)
                self.assertEqual(item.animation_states[0].values, item.setup)
                self.assertEqual(item.animation_states[1].values, item.calculation)
                self.assertEqual(item.animation_states[2].values, item.result)
                self.assertEqual(item.animation_states[-1].visible_tokens, item.visible_evidence_tokens)
                self.assertEqual(item.animation_states[-1].visible_evidence_tokens, item.visible_evidence_tokens)
                self.assertEqual(item.animation_states[-1].visible_object_ids, spec.required_figure_tokens)
                self.assertEqual(item.animation_states[-1].result_fields, tuple(item.result))
                expected_evidence = ordered_union(spec.required_example_tokens, spec.required_figure_tokens)
                self.assertEqual(item.visible_evidence_tokens, expected_evidence)
                self.assertEqual(item.required_example_tokens, spec.required_example_tokens)
                self.assertEqual(item.required_figure_tokens, spec.required_figure_tokens)
                self.assertEqual(item.exact_visible_evidence_tokens, item.visible_evidence_tokens)
                self.assertEqual(recompute_physics_model_scenario(item), item)

    def test_recomputation_ignores_stale_calculation_and_result_fields(self) -> None:
        original = scenario("rocket_equation")
        stale = original.as_dict()
        stale["calculation"] = {"log_mass_ratio": -999.0}
        stale["result"] = {"delta_velocity": -999.0}

        rebuilt = recompute_physics_model_scenario(stale)

        self.assertEqual(rebuilt, original)
        self.assertNotEqual(rebuilt.calculation["log_mass_ratio"], -999.0)
        self.assertNotEqual(rebuilt.result["delta_velocity"], -999.0)

    def test_setup_overrides_recompute_without_mutating_defaults(self) -> None:
        default_line = scenario("kinematics_1d")
        faster_line = build_physics_model_scenario("kinematics_1d", {"initial_velocity": 5.0})
        lighter_rocket = recompute_physics_model_scenario("rocket_equation", {"final_mass": 250.0})

        self.assertEqual(default_line.setup["initial_velocity"], 3.0)
        self.assertEqual(default_line.result["final_position"], 11.0)
        self.assertEqual(faster_line.result["final_position"], 15.0)
        self.assertEqual(default_line.rebuild({"initial_velocity": 5.0}), faster_line)
        self.assertGreater(lighter_rocket.result["delta_velocity"], scenario("rocket_equation").result["delta_velocity"])

    def test_scenarios_and_registries_are_immutable(self) -> None:
        item = scenario("kinematics_1d")
        exported = item.as_dict()
        exported["setup"]["initial_position"] = 999.0  # type: ignore[index]

        with self.assertRaises(TypeError):
            item.setup["initial_position"] = 2.0  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            item.mode = "changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            PHYSICS_MODEL_SCENARIO_REGISTRY["changed"] = object()  # type: ignore[index]
        all_scenarios = build_all_physics_model_scenarios()
        with self.assertRaises(TypeError):
            all_scenarios["changed"] = item  # type: ignore[index]
        self.assertEqual(item.setup["initial_position"], 1.0)

    def test_invalid_model_and_setup_fields_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported physics model"):
            build_physics_model_scenario("not_a_model")
        with self.assertRaisesRegex(ValueError, "Unsupported physics model"):
            get_physics_model_scenario("not_a_model")
        with self.assertRaisesRegex(ValueError, "unknown setup fields"):
            build_physics_model_scenario("kinematics_1d", {"invented": 1.0})
        with self.assertRaises(TypeError):
            build_physics_model_scenario(None)  # type: ignore[arg-type]


class HighRiskKinematicsTests(unittest.TestCase):
    def test_one_dimensional_planar_and_projectile_results_remain_distinct(self) -> None:
        line = scenario("kinematics_1d")
        plane = scenario("kinematics_2d")
        projectile = scenario("projectile_motion")

        self.assertEqual({line.mode, plane.mode, projectile.mode}, {"kinematics_1d", "kinematics_2d", "projectile_motion"})
        self.assertIn("final_position", line.result)
        self.assertNotIn("final_position_vector", line.result)
        self.assertEqual(plane.result["final_position_vector"], (11.0, 6.0))
        self.assertNotIn("trajectory_is_parabolic", plane.result)
        self.assertTrue(projectile.result["trajectory_is_parabolic"])
        self.assertIn("parabolic_trajectory", projectile.visible_evidence_tokens)
        self.assertIn("number_line", line.visible_evidence_tokens)
        self.assertIn("position_vector", plane.visible_evidence_tokens)

        launch_x, launch_y = projectile.setup["launch_position"]  # type: ignore[misc]
        angle = math.radians(float(projectile.setup["launch_angle"]))
        elapsed = float(projectile.setup["elapsed_time"])
        speed = float(projectile.setup["initial_speed"])
        gravity = float(projectile.setup["gravity"])
        expected = (
            launch_x + speed * math.cos(angle) * elapsed,
            launch_y + speed * math.sin(angle) * elapsed - 0.5 * gravity * elapsed**2,
        )
        self.assertEqual(projectile.result["final_position_vector"], expected)


class HighRiskCollisionTests(unittest.TestCase):
    def test_elastic_inelastic_and_sticking_collisions_preserve_different_invariants(self) -> None:
        elastic = scenario("elastic_collision")
        inelastic = scenario("inelastic_collision")
        stuck = scenario("perfectly_inelastic_collision")

        self.assertEqual(len({elastic.mode, inelastic.mode, stuck.mode}), 3)
        for item in (elastic, inelastic, stuck):
            self.assertAlmostEqual(item.result["final_total_momentum"], item.calculation["initial_total_momentum"])

        self.assertAlmostEqual(elastic.result["kinetic_energy_after"], elastic.result["kinetic_energy_before"])
        self.assertEqual(elastic.result["kinetic_energy_loss"], 0.0)
        self.assertTrue(elastic.result["bodies_separate"])
        self.assertIn("kinetic_energy_after", elastic.visible_evidence_tokens)

        self.assertGreater(inelastic.result["kinetic_energy_loss"], 0.0)
        self.assertNotEqual(inelastic.result["final_velocities"][0], inelastic.result["final_velocities"][1])  # type: ignore[index]
        self.assertTrue(inelastic.result["bodies_separate"])
        self.assertIn("kinetic_energy_loss", inelastic.visible_evidence_tokens)

        self.assertGreater(stuck.result["kinetic_energy_loss"], inelastic.result["kinetic_energy_loss"])
        self.assertEqual(stuck.result["final_velocities"][0], stuck.result["final_velocities"][1])  # type: ignore[index]
        self.assertEqual(stuck.result["shared_final_velocity"], stuck.result["final_velocities"][0])  # type: ignore[index]
        self.assertTrue(stuck.result["bodies_stick"])
        self.assertIn("stuck_after_state", stuck.visible_evidence_tokens)


class HighRiskForceTests(unittest.TestCase):
    def test_interaction_force_types_have_specific_evidence_and_results(self) -> None:
        markers = {
            "action_reaction": "separate_free_body_diagrams",
            "gravity_force": "gravitational_field",
            "contact_force": "normal_force",
            "tension_force": "rope_direction",
            "spring_force": "restoring_force_arrow",
        }
        items = {model_id: scenario(model_id) for model_id in markers}

        self.assertEqual(len({item.mode for item in items.values()}), len(items))
        for model_id, marker in markers.items():
            with self.subTest(model_id=model_id):
                self.assertIn(marker, items[model_id].visible_evidence_tokens)

        self.assertEqual(sum(items["action_reaction"].result["force_pair"]), 0.0)  # type: ignore[arg-type]
        self.assertTrue(items["action_reaction"].result["different_bodies"])
        self.assertEqual(items["gravity_force"].result["weight_vector"], (0.0, -29.400000000000002))
        self.assertEqual(items["contact_force"].result["contact_force_vector"], (-6.0, 20.0))
        self.assertAlmostEqual(items["tension_force"].result["tension_magnitude"], 12.0)
        self.assertEqual(items["spring_force"].result["spring_force"], -10.0)

    def test_linear_quadratic_and_generic_drag_do_not_share_one_law(self) -> None:
        linear = scenario("linear_drag")
        quadratic = scenario("quadratic_drag")
        generic = scenario("drag_force")

        self.assertEqual(linear.result["drag_force_vector"], (-6.0, -0.0))
        self.assertEqual(quadratic.result["drag_force_vector"], (-24.0, -0.0))
        self.assertAlmostEqual(math.hypot(*generic.result["drag_force_vector"]), 12.0)  # type: ignore[arg-type]
        self.assertIn("drag_force", linear.visible_evidence_tokens)
        self.assertIn("reference_area", quadratic.visible_evidence_tokens)
        self.assertIn("drag_law", generic.visible_evidence_tokens)


class HighRiskMassTransferTests(unittest.TestCase):
    def test_control_volume_mass_flow_is_not_the_integrated_rocket_equation(self) -> None:
        flow = scenario("continuous_mass_transfer")
        rocket = scenario("rocket_equation")

        expected_force = float(flow.setup["mass_flow_rate"]) * (
            float(flow.setup["outlet_velocity"]) - float(flow.setup["inlet_velocity"])
        )
        expected_delta = float(rocket.setup["exhaust_speed"]) * math.log(
            float(rocket.setup["initial_mass"]) / float(rocket.setup["final_mass"])
        )
        self.assertEqual(flow.result["external_force"], expected_force)
        self.assertAlmostEqual(rocket.result["delta_velocity"], expected_delta)
        self.assertIn("momentum_rate_in", flow.calculation)
        self.assertNotIn("log_mass_ratio", flow.calculation)
        self.assertIn("log_mass_ratio", rocket.calculation)
        self.assertNotIn("momentum_rate_in", rocket.calculation)
        self.assertIn("control_volume_boundary", flow.visible_evidence_tokens)
        self.assertIn("mass_readout", rocket.visible_evidence_tokens)
        self.assertNotEqual(flow.mode, rocket.mode)


class HighRiskRotationTests(unittest.TestCase):
    def test_particle_rigid_inertia_and_rotational_dynamics_have_separate_results(self) -> None:
        particle = scenario("point_particle_angular_momentum")
        rigid = scenario("rigid_body_angular_momentum")
        inertia = scenario("moment_of_inertia")
        dynamics = scenario("rotational_dynamics")

        self.assertEqual(len({particle.mode, rigid.mode, inertia.mode, dynamics.mode}), 4)
        self.assertEqual(particle.result["angular_momentum_z"], 5.0)
        self.assertTrue(particle.result["point_particle_model"])
        self.assertEqual(rigid.result["angular_momentum_vector"], (2.0, 6.0, 12.0))
        self.assertEqual(inertia.calculation["inertia_contributions"], (2.0, 12.0, 9.0))
        self.assertEqual(inertia.result["moment_of_inertia"], 23.0)
        self.assertEqual(dynamics.calculation["net_torque"], 10.0)
        self.assertEqual(dynamics.calculation["angular_acceleration"], 2.0)
        self.assertEqual(dynamics.result["final_angular_speed"], 7.0)
        self.assertIn("point_particle", particle.visible_evidence_tokens)
        self.assertIn("inertia_tensor", rigid.visible_evidence_tokens)
        self.assertIn("mass_elements", inertia.visible_evidence_tokens)
        self.assertIn("angular_acceleration", dynamics.visible_evidence_tokens)


class HighRiskRollingTests(unittest.TestCase):
    def test_rolling_kinematics_dynamics_energy_and_momentum_do_not_collapse(self) -> None:
        kinematics = scenario("rolling_kinematics")
        dynamics = scenario("rolling_dynamics")
        energy = scenario("rolling_kinetic_energy")
        momentum = scenario("rolling_angular_momentum")

        self.assertEqual(len({kinematics.mode, dynamics.mode, energy.mode, momentum.mode}), 4)
        self.assertEqual(kinematics.calculation["center_speed"], 3.0)
        self.assertEqual(kinematics.result["contact_speed"], 0.0)
        self.assertEqual(
            kinematics.result["final_center_speed"],
            float(kinematics.setup["radius"]) * float(kinematics.result["final_angular_speed"]),
        )
        self.assertEqual(
            kinematics.result["center_displacement"],
            float(kinematics.setup["radius"]) * float(kinematics.calculation["rotation_angle"]),
        )
        self.assertAlmostEqual(
            dynamics.result["center_acceleration"],
            float(dynamics.setup["radius"]) * float(dynamics.result["angular_acceleration"]),
        )
        self.assertAlmostEqual(
            dynamics.result["torque_from_friction"],
            float(dynamics.setup["moment_of_inertia"]) * float(dynamics.result["angular_acceleration"]),
        )
        self.assertEqual(
            energy.result["total_kinetic_energy"],
            float(energy.calculation["translational_energy"]) + float(energy.calculation["rotational_energy"]),
        )
        self.assertEqual(
            momentum.result["angular_momentum_about_contact"],
            float(momentum.calculation["spin_angular_momentum"])
            + float(momentum.calculation["orbital_angular_momentum_about_contact"]),
        )
        self.assertIn("contact_point", kinematics.visible_evidence_tokens)
        self.assertIn("free_body_diagram", dynamics.visible_evidence_tokens)
        self.assertIn("translational_energy", energy.visible_evidence_tokens)
        self.assertIn("reference_point", momentum.visible_evidence_tokens)


class PhysicsScenarioSourceTests(unittest.TestCase):
    def test_new_sources_are_ascii_and_scenario_module_has_no_course_import(self) -> None:
        root = Path(__file__).resolve().parents[1]
        module_path = root / "tools" / "physics_model_scenarios.py"
        for path in (module_path, Path(__file__)):
            with self.subTest(path=path.name):
                path.read_bytes().decode("ascii")

        tree = ast.parse(module_path.read_text(encoding="ascii"))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        self.assertNotIn("tools.stem_course", imported_modules)
        self.assertNotIn("stem_course", imported_modules)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from tools import stem_course
from tools.physics_model_specs import (
    PHYSICS_MODEL_REGISTRY,
    PHYSICS_VISUAL_KINDS,
    resolve_physics_model,
)


class PhysicsModelResolutionTests(unittest.TestCase):
    def assert_model(self, title: str, expected_model_id: str) -> None:
        spec = resolve_physics_model(title, fail_closed=True)
        self.assertEqual(spec.model_id, expected_model_id, msg=title)

    def test_registry_uses_only_existing_visual_kinds(self) -> None:
        self.assertEqual(set(PHYSICS_VISUAL_KINDS), stem_course.PHYSICS_VISUAL_KINDS)
        self.assertTrue(PHYSICS_MODEL_REGISTRY)
        for spec in PHYSICS_MODEL_REGISTRY.values():
            with self.subTest(model_id=spec.model_id):
                self.assertIn(spec.visual_kind, stem_course.PHYSICS_VISUAL_KINDS)
                self.assertTrue(spec.canonical_formula)
                self.assertTrue(spec.prerequisites)
                self.assertTrue(spec.statement_kind)
                self.assertGreaterEqual(len(spec.exact_symbol_rows), 3)
                self.assertTrue(spec.required_example_tokens)
                self.assertTrue(spec.required_figure_tokens)

    def test_kinematics_models_do_not_collapse_into_one_route(self) -> None:
        cases = {
            "Kinematics in One Dimension": "kinematics_1d",
            "Two-Dimensional Kinematics": "kinematics_2d",
            "Projectile Motion": "projectile_motion",
            "Rolling Kinematics": "rolling_kinematics",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

        projectile = resolve_physics_model("Projectile Motion", fail_closed=True)
        self.assertIn("launch_angle", projectile.required_example_tokens)
        self.assertIn("parabolic_trajectory", projectile.required_figure_tokens)
        self.assertNotIn("launch_angle", resolve_physics_model("Kinematics", True).required_example_tokens)

    def test_force_models_preserve_the_interaction_being_taught(self) -> None:
        cases = {
            "Newton's First Law": "newton_first_law",
            "Newton's Second Law": "newton_second_law",
            "Newton's Laws of Motion": "newton_laws_of_motion",
            "Newton's Third Law and Action-Reaction": "action_reaction",
            "Gravity": "gravity_force",
            "Normal and Friction Contact Forces": "contact_force",
            "Tension in a Rope": "tension_force",
            "Hooke's Law for a Spring": "spring_force",
            "Ideal Pulley Constraints": "pulley_constraint",
            "Linear Drag": "linear_drag",
            "Quadratic Drag": "quadratic_drag",
            "Drag Force": "drag_force",
            "Net Force": "force_balance",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

        third_law = resolve_physics_model("Action-Reaction Forces", True)
        self.assertIn("force_on_a_by_b", third_law.required_example_tokens)
        self.assertIn("separate_free_body_diagrams", third_law.required_figure_tokens)

    def test_linear_momentum_and_collision_models_remain_distinct(self) -> None:
        cases = {
            "Linear Momentum": "momentum_definition",
            "Impulse-Momentum Theorem": "impulse_momentum",
            "Conservation of Momentum": "momentum_conservation",
            "Elastic Collisions": "elastic_collision",
            "Inelastic Collisions": "inelastic_collision",
            "Perfectly Inelastic Collision": "perfectly_inelastic_collision",
            "Collision Mechanics": "collision_momentum",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

        elastic = resolve_physics_model("Elastic Collision", True)
        inelastic = resolve_physics_model("Inelastic Collision", True)
        stuck = resolve_physics_model("Perfectly Inelastic Collision", True)
        self.assertIn("kinetic_energy_after", elastic.required_example_tokens)
        self.assertIn("kinetic_energy_loss", inelastic.required_example_tokens)
        self.assertIn("sticking", stuck.required_example_tokens)
        self.assertNotEqual(elastic.canonical_formula, inelastic.canonical_formula)

    def test_work_energy_and_potential_routes_are_specific_first(self) -> None:
        cases = {
            "Mechanical Work": "work_definition",
            "Kinetic Energy and Work": "work_energy_theorem",
            "Gravitational Potential Energy": "gravitational_potential_energy",
            "Spring Potential Energy": "spring_potential_energy",
            "Conservation of Energy": "energy_conservation",
            "Potential Energy": "potential_energy_configuration",
            "Potential Energy Diagrams": "potential_energy_diagram",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

        spring_energy = resolve_physics_model("Spring Potential Energy", True)
        spring_force = resolve_physics_model("Spring Force", True)
        self.assertIn("stored_energy", spring_energy.required_example_tokens)
        self.assertIn("spring_force", spring_force.required_example_tokens)
        self.assertNotEqual(spring_energy.visual_kind, spring_force.visual_kind)

    def test_circular_models_encode_different_visible_evidence(self) -> None:
        cases = {
            "Circular Motion Position": "circular_position",
            "Uniform Circular Motion": "uniform_circular_motion",
            "Circular Motion Acceleration": "radial_acceleration",
            "Circular Motion Dynamics": "circular_dynamics",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

        position = resolve_physics_model("Circular Motion Position", True)
        radial = resolve_physics_model("Radial Acceleration", True)
        dynamics = resolve_physics_model("Centripetal Force", True)
        self.assertIn("radius_vector", position.required_figure_tokens)
        self.assertIn("inward_acceleration_arrow", radial.required_figure_tokens)
        self.assertIn("net_inward_force_arrow", dynamics.required_figure_tokens)

    def test_rotation_models_distinguish_particle_rigid_and_rolling_state(self) -> None:
        cases = {
            "Rigid Body Motion": "rigid_body_motion",
            "Motion of a Rigid Body": "rigid_body_motion",
            "Moment of Inertia": "moment_of_inertia",
            "Torque": "torque",
            "Rotational Dynamics": "rotational_dynamics",
            "Angular Momentum of a Point Particle": "point_particle_angular_momentum",
            "Angular Momentum of a Rigid Body": "rigid_body_angular_momentum",
            "Torque and Angular Impulse": "angular_impulse",
            "Rolling Dynamics": "rolling_dynamics",
            "Rolling Kinetic Energy": "rolling_kinetic_energy",
            "Rolling Angular Momentum": "rolling_angular_momentum",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

        particle = resolve_physics_model("Point-Particle Angular Momentum", True)
        rigid = resolve_physics_model("Rigid-Body Angular Momentum", True)
        rolling_energy = resolve_physics_model("Rolling Kinetic Energy", True)
        rolling_momentum = resolve_physics_model("Rolling Angular Momentum", True)
        self.assertIn("particle_momentum", particle.required_example_tokens)
        self.assertIn("inertia_tensor", rigid.required_example_tokens)
        self.assertIn("translational_energy", rolling_energy.required_example_tokens)
        self.assertIn("reference_point", rolling_momentum.required_example_tokens)

    def test_unicode_dashes_are_title_separators(self) -> None:
        cases = {
            "Rigid Body\N{EN DASH}Motion": "rigid_body_motion",
            "Lesson 28\N{EM DASH}Motion of a Rigid Body": "rigid_body_motion",
        }
        for title, model_id in cases.items():
            with self.subTest(title=title):
                self.assert_model(title, model_id)

    def test_mass_flow_is_not_the_rocket_equation(self) -> None:
        mass_flow = resolve_physics_model("Continuous Mass Transfer", True)
        rocket = resolve_physics_model("Rocket Equation", True)

        self.assertEqual(mass_flow.model_id, "continuous_mass_accumulation")
        self.assertEqual(rocket.model_id, "rocket_equation")
        self.assertIn("initial_mass", mass_flow.required_example_tokens)
        self.assertIn("inlet_mass_flow", mass_flow.required_example_tokens)
        self.assertIn("initial_mass", rocket.required_example_tokens)
        self.assertIn("exhaust_stream", rocket.required_figure_tokens)
        self.assertNotIn("control_volume", rocket.required_example_tokens)

    def test_remaining_mechanics_families_resolve_with_required_tokens(self) -> None:
        cases = {
            "Center of Mass": ("center_of_mass", "center_position"),
            "Relative Velocity": ("relative_velocity", "common_reference_frame"),
            "Relative Velocity and Recoil": ("recoil", "initial_total_momentum"),
            "Ordinary Differential Equation": ("ordinary_differential_equation", "initial_condition"),
            "Unit Vector": ("unit_vector", "normalized_components"),
            "Vector Components": ("vectors", "coordinate_basis"),
            "Traveling Waves": ("waves", "wavelength"),
        }
        for title, (model_id, token) in cases.items():
            with self.subTest(title=title):
                spec = resolve_physics_model(title, fail_closed=True)
                self.assertEqual(spec.model_id, model_id)
                self.assertIn(token, spec.required_example_tokens)

    def test_specs_are_frozen_and_offer_exact_serializable_symbol_rows(self) -> None:
        spec = resolve_physics_model("Center of Mass", True)

        with self.assertRaises(FrozenInstanceError):
            setattr(spec, "model_id", "changed")
        payload = spec.as_dict()
        self.assertEqual(payload["model_id"], "center_of_mass")
        self.assertEqual(
            payload["exact_symbol_rows"][0],
            {"symbol": r"\vec r_{\mathrm{cm}}", "meaning": "center-of-mass position"},
        )
        self.assertEqual(spec.symbol_rows, spec.exact_symbol_rows)

    def test_unknown_topics_are_optional_or_fail_closed(self) -> None:
        self.assertIsNone(resolve_physics_model("Thermodynamic Partition Function"))
        with self.assertRaisesRegex(ValueError, "Unsupported physics topic"):
            resolve_physics_model("Thermodynamic Partition Function", fail_closed=True)
        with self.assertRaisesRegex(TypeError, "title must be a string"):
            resolve_physics_model(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

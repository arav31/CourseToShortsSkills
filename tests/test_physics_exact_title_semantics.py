from __future__ import annotations

import math
import unittest

from tools.physics_model_scenarios import (
    build_physics_semantic_payload,
    build_physics_title_scenario,
)
from tools.physics_model_specs import (
    MIT_8_01_TITLE_CONTRACTS,
    MIT_8_01_TITLE_REGISTRY,
    resolve_physics_model,
    resolve_physics_title_contract,
)
from tools.video_physics_models import (
    MIT_8_01_SCENARIO_RENDER_ROUTES,
    MIT_8_01_VIDEO_ROUTES,
    build_physics_video_payload,
    physics_scenario_render_route,
    resolve_physics_video_model,
    validate_physics_video_payload,
)


OFFICIAL_TITLES = (
    "Vectors",
    "1D Kinematics - Position and Velocity",
    "1D Kinematics - Acceleration",
    "2D Kinematics",
    "Newton's Laws of Motion",
    "Gravity",
    "Contact Forces",
    "Tension and Springs",
    "Circular Motion - Position and Velocity",
    "Uniform Circular Motion",
    "Circular Motion \N{EN DASH} Acceleration",
    "Newton's 2nd Law and Circular Motion",
    "Pulleys and Constraints",
    "Massive Rope",
    "Resistive Forces",
    "Momentum and Impulse",
    "Conservation of Momentum",
    "Center of Mass and Motion",
    "Relative Velocity and Recoil",
    "Continuous Mass Transfer",
    "Kinetic Energy and Work in 1D",
    "Kinetic Energy and Work in 2D and 3D",
    "Conservative and Non-Conservative Forces",
    "Potential Energy",
    "Conservation of Energy",
    "Potential Energy Diagrams",
    "Types of Collision",
    "Elastic Collisions",
    "Motion of a Rigid Body",
    "Moment of Inertia",
    "Torque",
    "Rotational Dynamics",
    "Angular Momentum of a Point Particle",
    "Angular Momentum of a Rigid Body",
    "Torque and Angular Impulse",
    "Rolling Kinematics",
    "Rolling Dynamics",
    "Rolling Kinetic Energy & Angular Momentum",
)


class ExactTitleRegistryTests(unittest.TestCase):
    def test_all_official_titles_have_unique_cross_layer_identity(self) -> None:
        self.assertEqual(len(MIT_8_01_TITLE_CONTRACTS), 38)
        self.assertEqual(len(MIT_8_01_TITLE_REGISTRY), 38)
        self.assertEqual(len(MIT_8_01_VIDEO_ROUTES), 38)
        self.assertEqual(len(MIT_8_01_SCENARIO_RENDER_ROUTES), 38)
        self.assertEqual(tuple(row.exact_title for row in MIT_8_01_TITLE_CONTRACTS), OFFICIAL_TITLES)
        self.assertEqual(
            [contract.unit_number for contract in MIT_8_01_TITLE_CONTRACTS],
            list(range(1, 39)),
        )
        self.assertEqual(len({row.model_id for row in MIT_8_01_TITLE_CONTRACTS}), 38)
        self.assertEqual(len({row.scenario_mode for row in MIT_8_01_TITLE_CONTRACTS}), 38)
        self.assertEqual(len({row.video_route_key for row in MIT_8_01_TITLE_CONTRACTS}), 38)
        resolved_renderer_routes = [
            tuple(physics_scenario_render_route(row.model_id).values())
            for row in MIT_8_01_TITLE_CONTRACTS
        ]
        self.assertEqual(len(set(resolved_renderer_routes)), 38)

        for contract in MIT_8_01_TITLE_CONTRACTS:
            with self.subTest(unit=contract.unit_number, title=contract.exact_title):
                self.assertIs(resolve_physics_title_contract(contract.exact_title, True), contract)
                self.assertEqual(resolve_physics_model(contract.exact_title, True).model_id, contract.model_id)
                scenario = build_physics_title_scenario(contract.exact_title)
                route = resolve_physics_video_model(contract.exact_title, fail_closed=True)
                payload = build_physics_video_payload(contract.exact_title)
                self.assertEqual(scenario.model_id, contract.model_id)
                self.assertEqual(scenario.mode, contract.scenario_mode)
                self.assertEqual(route.model_id, contract.model_id)
                self.assertEqual(route.route_key, contract.video_route_key)
                self.assertEqual(payload["route_key"], contract.video_route_key)
                self.assertEqual(payload["canonical_formula"], contract.canonical_formula)
                self.assertEqual(payload["numeric_evidence_fingerprint"], scenario.numeric_evidence_fingerprint)
                self.assertEqual(validate_physics_video_payload(payload), [])
                renderer_route = physics_scenario_render_route(contract.model_id)
                self.assertTrue(renderer_route["renderer_variant"])
                self.assertTrue(renderer_route["causal_mode"])

    def test_semantic_payload_has_persistent_objects_and_exact_continuous_states(self) -> None:
        payload = build_physics_semantic_payload("Massive Rope")
        object_ids = {row["id"] for row in payload["objects"]}
        self.assertTrue(object_ids)
        previous_after = None
        for transition in payload["transitions"]:
            self.assertEqual(set(transition["persistent_object_ids"]), object_ids)
            self.assertEqual(set(transition["before"]), object_ids)
            self.assertEqual(set(transition["after"]), object_ids)
            self.assertEqual(
                transition["before_evidence"],
                payload["states"][transition["before_state_id"]],
            )
            self.assertEqual(
                transition["after_evidence"],
                payload["states"][transition["after_state_id"]],
            )
            if previous_after is not None:
                self.assertEqual(transition["before"], previous_after)
            previous_after = transition["after"]


class ExactTitleNumericProbeTests(unittest.TestCase):
    def test_audit_numeric_probes_are_recomputed(self) -> None:
        vector = build_physics_title_scenario("Vectors")
        self.assertEqual(vector.calculation["magnitude"], 13.0)
        self.assertEqual(vector.result["normalized_components"], (5.0 / 13.0, 12.0 / 13.0))
        self.assertEqual(vector.result["normalized_magnitude"], 1.0)

        circular = build_physics_title_scenario("Newton's 2nd Law and Circular Motion")
        self.assertAlmostEqual(circular.calculation["required_inward_force"], 12.0)
        self.assertAlmostEqual(
            circular.calculation["required_inward_force"],
            float(circular.setup["mass"])
            * float(circular.setup["speed"]) ** 2
            / float(circular.setup["radius"]),
        )

        rope = build_physics_title_scenario("Massive Rope")
        self.assertEqual(rope.calculation["tension_gradient"], 5.0)
        self.assertEqual(rope.result["tension_at_start"], 2.0)
        self.assertEqual(rope.result["tension_at_end"], 12.0)

        transfer = build_physics_title_scenario("Continuous Mass Transfer")
        self.assertEqual(transfer.result["initial_mass"], 10.0)
        self.assertEqual(transfer.result["final_mass"], 22.0)

        work = build_physics_title_scenario("Kinetic Energy and Work in 2D and 3D")
        self.assertEqual(work.calculation["dot_product_work"], 50.0)

        collision = build_physics_title_scenario("Types of Collision")
        self.assertEqual(collision.calculation["kinetic_energy_before"], 8.0)
        self.assertEqual(collision.calculation["kinetic_energy_after"], 4.0)
        self.assertEqual(collision.result["classification"], "perfectly_inelastic")
        self.assertTrue(collision.result["sticking"])

        rolling = build_physics_title_scenario("Rolling Kinetic Energy & Angular Momentum")
        self.assertEqual(rolling.result["total_kinetic_energy"], 13.5)
        self.assertEqual(rolling.result["angular_momentum_cm"], 1.5)

    def test_high_risk_rotation_and_rolling_routes_are_distinct(self) -> None:
        titles = (
            "Motion of a Rigid Body",
            "Moment of Inertia",
            "Torque",
            "Rotational Dynamics",
            "Angular Momentum of a Point Particle",
            "Angular Momentum of a Rigid Body",
            "Rolling Kinematics",
            "Rolling Dynamics",
            "Rolling Kinetic Energy & Angular Momentum",
        )
        payloads = [build_physics_video_payload(title) for title in titles]
        self.assertEqual(len({row["model_id"] for row in payloads}), len(titles))
        self.assertEqual(len({row["mode"] for row in payloads}), len(titles))
        self.assertEqual(len({row["route_key"] for row in payloads}), len(titles))
        self.assertEqual(len({row["canonical_formula"] for row in payloads}), len(titles))

    def test_combined_units_expose_both_mechanisms(self) -> None:
        tension = build_physics_video_payload("Tension and Springs")
        self.assertEqual(tension["mechanisms"], ["tension", "spring_restoring_force"])
        tension_roles = {row["role"] for row in tension["objects"]}
        self.assertIn("tension arrow", tension_roles)
        self.assertIn("spring", tension_roles)
        self.assertTrue(tension["numeric_evidence"]["result"]["both_mechanisms_visible"])

        rolling = build_physics_video_payload("Rolling Kinetic Energy & Angular Momentum")
        self.assertEqual(
            rolling["mechanisms"],
            ["rolling_kinetic_energy", "center_of_mass_angular_momentum"],
        )
        rolling_roles = {row["role"] for row in rolling["objects"]}
        self.assertIn("energy split meter", rolling_roles)
        self.assertIn("angular momentum arrow", rolling_roles)
        self.assertTrue(rolling["numeric_evidence"]["result"]["both_mechanisms_visible"])


class WorkedExampleOverrideTests(unittest.TestCase):
    def test_structured_override_recomputes_and_shares_fingerprint(self) -> None:
        title = "Kinetic Energy and Work in 2D and 3D"
        override = {
            "model_id": "work_energy_multidimensional",
            "mode": "work_energy_multidimensional",
            "setup": {
                "mass": 4.0,
                "initial_speed": 1.0,
                "force_vector": (10.0, 0.0),
                "displacement_vector": (2.0, 3.0),
            },
            "calculation": {"dot_product_work": -999.0},
            "result": {"final_kinetic_energy": -999.0},
        }
        scenario = build_physics_title_scenario(title, scenario_override=override)
        video = build_physics_video_payload(title, scenario_override=override)
        self.assertEqual(scenario.calculation["dot_product_work"], 20.0)
        self.assertEqual(scenario.result["final_kinetic_energy"], 22.0)
        self.assertAlmostEqual(scenario.result["final_speed"], math.sqrt(11.0))
        self.assertEqual(video["numeric_evidence_fingerprint"], scenario.numeric_evidence_fingerprint)

    def test_recognized_authored_prose_is_parsed_and_arbitrary_prose_fails_closed(self) -> None:
        authored = {
            "setup": "Normalize the vector u=(5,12) m.",
            "calculation": "Its magnitude is 13 m, so u_hat=(0.385,0.923) and its length is 1.",
            "takeaway": "Direction differs from the original vector's size; this is a unit vector.",
        }
        parsed = build_physics_video_payload("Vectors", authored)
        self.assertEqual(parsed["numeric_evidence"]["result"]["normalized_magnitude"], 1.0)

        with self.assertRaisesRegex(ValueError, "worked_example"):
            build_physics_video_payload("Vectors", {"setup": "arbitrary prose 123"})
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_physics_video_payload(
                "Gravity",
                {
                    "setup": "A cart feels a push and friction.",
                    "calculation": "Net force changes speed.",
                    "takeaway": "This does not identify gravity.",
                },
            )

    def test_audit_probe_prose_recomputes_instead_of_using_registry_defaults(self) -> None:
        probes = {
            "Circular Motion \N{EN DASH} Acceleration": {
                "setup": "Compare velocity arrows for a particle at two nearby points on a circle with r=4 m and speed v=8 m/s.",
                "calculation": "Their difference points inward; in the small-angle limit ar=v^2/r=16 m/s^2.",
                "takeaway": "Constructing inward acceleration from two tangent velocity vectors.",
            },
            "Continuous Mass Transfer": {
                "setup": "A fixed control volume starts with M0=10 kg. Mass enters at mdot_in=4 kg/s and leaves at mdot_out=1 kg/s for t=4 s.",
                "calculation": "dMcv/dt=4-1=3 kg/s, so Mcv=10+(3)(4)=22 kg.",
                "takeaway": "Track flux across a fixed control volume and the resulting accumulation.",
            },
            "Kinetic Energy and Work in 2D and 3D": {
                "setup": "A 2 kg puck has displacement (3,4) m under F=(6,8) N, starting at 5 m/s.",
                "calculation": "The dot product work is 6(3)+8(4)=50 J and final kinetic energy is 75 J.",
                "takeaway": "Only the force component along displacement contributes work.",
            },
            "Types of Collision": {
                "setup": "Classify m1=1 kg at v1=4 m/s and m2=1 kg at v2=0 m/s when they leave together at 2 m/s.",
                "calculation": "Momentum is 4 before and after; kinetic energy changes from 8 J to 4 J.",
                "takeaway": "Classify the leave together case as perfectly inelastic.",
            },
            "Rolling Kinetic Energy & Angular Momentum": {
                "setup": "A 2 kg rolling cylinder has r=0.5 m, I=0.25 kg m^2, center speed 3 m/s, and omega=6 rad/s.",
                "calculation": "Rolling gives K=13.5 J and Lcm=1.5 kg m^2/s.",
                "takeaway": "Rolling has translation and rotation plus center angular momentum.",
            },
        }
        expected = {
            "Circular Motion \N{EN DASH} Acceleration": ("radial_acceleration", 16.0),
            "Continuous Mass Transfer": ("final_mass", 22.0),
            "Kinetic Energy and Work in 2D and 3D": ("final_kinetic_energy", 75.0),
            "Types of Collision": ("kinetic_energy_after", 4.0),
            "Rolling Kinetic Energy & Angular Momentum": ("total_kinetic_energy", 13.5),
        }
        for title, worked in probes.items():
            with self.subTest(title=title):
                payload = build_physics_video_payload(title, worked)
                field, value = expected[title]
                evidence = payload["numeric_evidence"]
                observed = evidence["result"].get(field, evidence["calculation"].get(field))
                self.assertEqual(observed, value)

    def test_mismatched_or_unsupported_payloads_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match exact title model"):
            build_physics_title_scenario(
                "Torque",
                scenario_override={"model_id": "moment_of_inertia", "setup": {}},
            )
        with self.assertRaisesRegex(ValueError, "Unsupported exact MIT 8.01 title"):
            build_physics_title_scenario("Thermodynamic Partition Function")
        with self.assertRaisesRegex(ValueError, "broad physics topic"):
            build_physics_video_payload("Net Force", {"setup": {"mass": 1.0}})

        tampered = build_physics_video_payload("Continuous Mass Transfer")
        tampered["numeric_evidence"]["result"]["final_mass"] = 999.0
        self.assertIn(
            "numeric_evidence_fingerprint does not match recomputed evidence",
            validate_physics_video_payload(tampered),
        )


if __name__ == "__main__":
    unittest.main()

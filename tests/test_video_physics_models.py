from __future__ import annotations

import unittest

from tools.video_physics_models import (
    ROUTES,
    build_physics_video_payload,
    physics_label_tex,
    physics_scenario_render_route,
    resolve_physics_video_model,
    validate_physics_video_payload,
)


class PhysicsVideoRouteTests(unittest.TestCase):
    def test_mass_transfer_never_resolves_as_rocket(self) -> None:
        for title in ("Continuous Mass Transfer", "Control Volume Momentum", "Mass Flow Through Inlet and Outlet", "Fluid Continuity Equation"):
            with self.subTest(title=title):
                route = resolve_physics_video_model(title, fail_closed=True)
                self.assertEqual(route.family, "mass_transfer")
                self.assertNotEqual(route, ROUTES["rocket"])
                payload = build_physics_video_payload(title)
                if title == "Continuous Mass Transfer":
                    self.assertEqual(payload["model_id"], "continuous_mass_accumulation")
                    self.assertEqual(payload["numeric_evidence"]["result"]["final_mass"], 22.0)
                    self.assertTrue(payload["route_key"].startswith("physics:mit-8-01:20:"))
                else:
                    self.assertEqual(payload["route_key"], "physics:mass_transfer")
                    self.assertTrue(payload["verification"]["rocket_semantics_absent"])

        self.assertEqual(resolve_physics_video_model("Ideal Rocket Equation", fail_closed=True).family, "rocket")

    def test_requested_routes_are_topic_general(self) -> None:
        cases = {
            "Free-body diagram on an incline": "force", "Two dimensional kinematics": "kinematics",
            "Conservation of mechanical energy": "energy", "Impulse and momentum": "momentum",
            "Resolving vector components": "vectors", "Initial value problem for a second order ODE": "ode",
            "Centre of mass of particles": "center_of_mass", "Motion in a potential well": "potential",
            "Uniform circular motion": "circular_motion", "Gun and bullet recoil": "recoil",
            "Torque and angular acceleration": "rotation", "Tsiolkovsky equation": "rocket",
            "ODE": "ode", "Potential": "potential", "Newton's Laws": "force",
        }
        for title, family in cases.items():
            with self.subTest(title=title):
                self.assertEqual(resolve_physics_video_model(title, fail_closed=True).family, family)
                self.assertEqual(validate_physics_video_payload(build_physics_video_payload(title)), [])

    def test_payloads_are_deterministic_and_never_discard_worked_examples(self) -> None:
        with self.assertRaisesRegex(ValueError, "worked_example"):
            build_physics_video_payload("Continuous Mass Transfer", {"setup": "arbitrary prose 123"})
        with self.assertRaisesRegex(ValueError, "broad physics topic"):
            build_physics_video_payload("Net Force", {"setup": "arbitrary prose 123"})

        override = {
            "model_id": "continuous_mass_accumulation",
            "setup": {
                "initial_mass": 20.0,
                "inlet_mass_flow": 5.0,
                "outlet_mass_flow": 2.0,
                "duration": 3.0,
            },
        }
        first = build_physics_video_payload("Continuous Mass Transfer", scenario_override=override)
        second = build_physics_video_payload("Continuous Mass Transfer", scenario_override=override)
        self.assertEqual(first, second)
        self.assertEqual(first["numeric_evidence"]["result"]["final_mass"], 29.0)
        ids = {row["id"] for row in first["objects"]}
        for index, transition in enumerate(first["transitions"]):
            self.assertEqual(set(transition["persistent_object_ids"]), ids)
            self.assertEqual(set(transition["before"]), ids)
            self.assertEqual(set(transition["after"]), ids)
            if index:
                self.assertEqual(first["transitions"][index - 1]["after"], transition["before"])

    def test_public_adapter_topic_accepts_legacy_prose_without_parsing_it(self) -> None:
        payload = build_physics_video_payload(
            "contact_force",
            {"setup": "Legacy prose is not the renderer-neutral source of truth."},
        )
        self.assertEqual(payload["family"], "force")
        self.assertEqual(payload["route_key"], "physics:force")

    def test_exact_title_identity_and_numeric_fingerprint_survive_alias_lookups(self) -> None:
        title = "Kinetic Energy and Work in 2D and 3D"
        before = build_physics_video_payload(title)

        alias_route = physics_scenario_render_route("vector_work_energy")
        after = build_physics_video_payload(title)

        self.assertEqual(
            alias_route,
            physics_scenario_render_route("work_energy_multidimensional"),
        )
        self.assertEqual(before["model_id"], "work_energy_multidimensional")
        self.assertEqual(before["mode"], "work_energy_multidimensional")
        self.assertEqual(before["route_key"], "physics:mit-8-01:22:work_energy_multidimensional")
        self.assertEqual(after["route_key"], before["route_key"])
        self.assertEqual(after["numeric_evidence_fingerprint"], before["numeric_evidence_fingerprint"])

    def test_mass_transfer_has_fixed_boundary_accumulation_balance_and_steady_resolution(self) -> None:
        payload = build_physics_video_payload("Mass flux through a fixed control volume")
        final = payload["transitions"][-1]["after"]
        self.assertEqual(final["physics:mass_transfer:control_volume"], "fixed boundary at x=0")
        self.assertIn("inward", final["physics:mass_transfer:inlet_flux"])
        self.assertIn("outward", final["physics:mass_transfer:outlet_flux"])
        self.assertEqual(final["physics:mass_transfer:balance"], "dM_cv/dt=m_dot_in-m_dot_out")
        self.assertEqual(final["physics:mass_transfer:steady_state"], "steady: dM_cv/dt=0 => m_dot_in=m_dot_out")
        self.assertIn("M_0+(m_dot_in-m_dot_out)t", final["physics:mass_transfer:stored_mass"])

    def test_newton_force_payload_keeps_force_and_acceleration_signs_aligned(self) -> None:
        for title in ("Newton's Laws of Motion", "Newton's Second Law", "Net Force"):
            with self.subTest(title=title):
                payload = build_physics_video_payload(title)
                if title == "Newton's Laws of Motion":
                    self.assertEqual(payload["mode"], "newton_laws_of_motion")
                    self.assertEqual(payload["numeric_evidence"]["result"]["force_pair"], [-6.0, 6.0])
                    self.assertEqual(payload["numeric_evidence"]["result"]["accelerations"], [-3.0, 2.0])
                    continue
                final = payload["transitions"][-1]["after"]
                self.assertEqual(payload["mode"], "signed_force_balance")
                self.assertIn("+F_{\\mathrm{net}}", final["physics:force:net_force"])
                self.assertIn("+(F_{\\mathrm{net}}/m)", final["physics:force:acceleration"])
                self.assertTrue(payload["verification"]["force_acceleration_signs_match"])

    def test_rolling_kinematics_uses_no_slip_visual_semantics(self) -> None:
        for title in ("Rolling Kinematics", "Pure Rolling", "Rolling Without Slipping"):
            with self.subTest(title=title):
                route = resolve_physics_video_model(title, fail_closed=True)
                payload = build_physics_video_payload(title)
                rendered_states = " ".join(
                    str(value) for transition in payload["transitions"] for value in transition["after"].values()
                )
                self.assertEqual(route.family, "rolling_kinematics")
                if title == "Rolling Kinematics":
                    self.assertEqual(route.visual_kind, "physics_kinematics")
                    self.assertIn(r"v_{\mathrm{cm}}=\omega R", payload["canonical_formula"])
                    self.assertTrue(payload["numeric_evidence"]["result"]["no_slip_satisfied"])
                else:
                    self.assertEqual(route.visual_kind, "physics_kinematics")
                    self.assertIn(r"\omega R=v_{\mathrm{cm}}", rendered_states)
                self.assertNotIn("torque", rendered_states.casefold())
                self.assertNotIn("impulse", rendered_states.casefold())

    def test_compact_physics_labels_are_converted_to_mathtex_latex(self) -> None:
        self.assertEqual(physics_label_tex("x <= (x-2)^2"), r"x \le  (x-2)^{2}")
        self.assertEqual(physics_label_tex("m1 v1 aA"), r"m_{1} v_{1} a_{A}")
        self.assertEqual(physics_label_tex("m_dot >= 0"), r"\dot{m} \ge  0")


if __name__ == "__main__":
    unittest.main()

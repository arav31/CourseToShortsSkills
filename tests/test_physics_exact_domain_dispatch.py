import inspect
import unittest

from tools import stem_course


class ExactPhysicsDomainDispatchTests(unittest.TestCase):
    def test_vectors_scenario_adapts_to_component_resultant_motion(self):
        short = {
            "concept": "Vectors",
            "model_id": "vectors",
            "key_concept": "components reconstruct the same vector",
        }
        payload = stem_course.physics_semantic_data(short, "physics_vector")
        self.assertTrue(payload["domain_renderer_ready"])
        self.assertEqual(payload["mode"], "components_resultant")
        self.assertEqual(payload["components"], [5.0, 12.0])
        self.assertEqual(payload["squared_components"], [25.0, 144.0])
        self.assertAlmostEqual(payload["magnitude"], 13.0)
        self.assertAlmostEqual(payload["direction_degrees"], 67.38013505195957)

    def test_vector_renderer_exposes_exact_physics_state_contract(self):
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index("def play_physics_vector_visual"):
            source.index("def play_physics_center_of_mass_visual_legacy")
        ]
        for token in (
            "component_progress = ValueTracker(0.0)",
            "resultant_progress = ValueTracker(0.0)",
            "x_component = always_redraw",
            "y_component = always_redraw",
            "resultant = always_redraw",
            "self.configure_physics_motion(",
            "[component_progress, resultant_progress, normalization_progress, evidence_stage]",
            "magnitude.add_updater",
            "direction.add_updater",
            '"component_arrows"',
            '"vector_arrow"',
        ):
            self.assertIn(token, renderer)
        self.assertNotIn("register_semantic_track", renderer)

    def test_position_velocity_scenario_adapts_to_synchronized_kinematics(self):
        short = {
            "concept": "1D Kinematics - Position and Velocity",
            "model_id": "kinematics_position_velocity",
            "model_scenario": {
                "model_id": "kinematics_position_velocity",
                "mode": "kinematics_position_velocity",
                "setup": {
                    "initial_position": 0.0,
                    "initial_velocity": 4.0,
                    "acceleration": 1.0,
                    "elapsed_time": 4.0,
                },
            },
            "key_concept": "same particle and clock",
        }
        payload = stem_course.physics_semantic_data(short, "physics_kinematics")
        self.assertTrue(payload["domain_renderer_ready"])
        self.assertEqual(payload["mode"], "trajectory")
        self.assertEqual(payload["positions"][-1], 24.0)
        self.assertEqual(payload["velocities"][-1], 8.0)

    def test_exact_physics_dispatch_prefers_domain_routes_and_rigid_body_canvas(self):
        source = stem_course.MANIM_SCENE_HELPERS
        dispatch = source[source.index("def play_generic_visual("):source.index("def play_example_visual(")]
        self.assertIn('model_id") == "rigid_body_angular_momentum"', dispatch)
        self.assertIn("play_physics_rigid_body_angular_momentum", dispatch)
        self.assertIn('physics_payload.get("domain_renderer_ready")', dispatch)
        self.assertIn("play_exact_physics_domain_contract", dispatch)

    def test_generic_gyroscope_title_uses_dedicated_rigid_body_renderer(self):
        short = {
            "concept": "Gyroscopes",
            "model_id": "rigid_body_angular_momentum",
            "key_concept": "angular momentum resists a change in axis",
        }
        payload = stem_course.physics_semantic_data(short, "physics_rotation")
        self.assertTrue(payload["dedicated_renderer_ready"])
        self.assertEqual(payload["scenario"], payload["model_scenario"])
        self.assertEqual(len(payload["transitions"]), 3)
        self.assertEqual(payload["payload_type"], "physics")
        source = stem_course.MANIM_SCENE_HELPERS
        dispatch = source[source.index("def play_generic_visual("):source.index("def play_example_visual(")]
        self.assertLess(
            dispatch.index('physics_payload.get("model_id") == "rigid_body_angular_momentum"'),
            dispatch.index('if isinstance(physics_payload, dict) and physics_payload.get("exact_title")'),
        )

    def test_domain_motion_is_rebound_to_canonical_transition_ids(self):
        source = stem_course.MANIM_SCENE_HELPERS
        binder = source[
            source.index("def bind_physics_motion_to_semantic_contract"):
            source.index("def play_exact_physics_domain_contract")
        ]
        self.assertIn("transition_id = str(transition.get", binder)
        self.assertIn("self.register_semantic_transition_actions(", binder)
        self.assertIn("callback_metadata={", binder)
        self.assertIn("enforce_temporal_carriers=True", binder)
        self.assertNotIn("Transform(", binder)

    def test_runtime_adds_only_the_planner_invariant_transition(self):
        source = stem_course.MANIM_SCENE_HELPERS
        helper = source[
            source.index("def physics_runtime_semantic_transitions"):
            source.index("def bind_physics_motion_to_semantic_contract")
        ]
        self.assertIn('str(payload.get("family", "physics")) + ":verify_invariant"', helper)
        self.assertIn("Keep the same physical objects visible", helper)

    def test_kinematics_renderer_shares_one_clock_across_particle_x_and_v(self):
        source = stem_course.MANIM_SCENE_HELPERS
        route = source[
            source.index("def play_physics_kinematics_1d_visual"):
            source.index("def play_physics_vector_visual")
        ]
        for token in (
            "number_line = NumberLine(",
            "moving_particle = always_redraw",
            "velocity_axes = Axes(",
            "position_curve.set_points_smoothly",
            "velocity_curve.set_points_as_corners",
            "position_curve.copy().pointwise_become_partial",
            "velocity_curve.copy().pointwise_become_partial",
            "velocity_time_projection = always_redraw",
            '"shared_clock": VGroup(time_projection, velocity_time_projection, t_readout)',
        ):
            self.assertIn(token, route)
        self.assertIn("tracker.get_value()", route)

    def test_accelerated_position_samples_are_nonlinear_while_velocity_is_linear(self):
        short = {
            "concept": "1D Kinematics - Position and Velocity",
            "model_id": "kinematics_position_velocity",
            "model_scenario": {
                "model_id": "kinematics_position_velocity",
                "mode": "kinematics_position_velocity",
                "setup": {
                    "initial_position": 0.0,
                    "initial_velocity": 4.0,
                    "acceleration": 1.0,
                    "elapsed_time": 4.0,
                },
            },
            "key_concept": "same particle and clock",
        }
        payload = stem_course.physics_semantic_data(short, "physics_kinematics")
        positions = payload["positions"]
        velocities = payload["velocities"]
        position_second_differences = [
            positions[index + 1] - 2 * positions[index] + positions[index - 1]
            for index in range(1, len(positions) - 1)
        ]
        velocity_second_differences = [
            velocities[index + 1] - 2 * velocities[index] + velocities[index - 1]
            for index in range(1, len(velocities) - 1)
        ]
        self.assertTrue(all(value > 0.0 for value in position_second_differences))
        self.assertTrue(all(abs(value) < 1e-12 for value in velocity_second_differences))

    def test_structured_math_supports_tensor_vector_angular_momentum(self):
        source = stem_course.MANIM_SCENE_HELPERS
        compositor = source[
            source.index("def physics_structured_math_mob"):
            source.index("def physics_math_mob")
        ]
        self.assertIn("tensor_vector_match", compositor)
        self.assertIn('features.add("tensor_vector_product")', compositor)
        self.assertIn('symbol("ω", vector=True)', compositor)

    def test_structured_math_supports_precession_fraction_symbols(self):
        source = stem_course.MANIM_SCENE_HELPERS
        compositor = source[
            source.index("def physics_structured_math_mob"):
            source.index("def physics_math_mob")
        ]
        self.assertIn('(slash + "Omega", "OMEGAUP")', compositor)
        self.assertIn('(slash + "omega", "OMEGA")', compositor)
        self.assertIn('(slash + "tau", "TAU")', compositor)
        self.assertIn('items.append(token("τ"))', compositor)

    def test_rigid_body_route_uses_body_axis_omega_and_momentum_not_force_cart(self):
        source = stem_course.MANIM_SCENE_HELPERS
        route = source[
            source.index("def play_physics_rigid_body_angular_momentum"):
            source.index("def play_typed_semantic_contract")
        ]
        for token in ("Ellipse(", '"axis z"', "ω = ", "momentum_arrow", "I = diag("):
            self.assertIn(token, route)
        self.assertIn("kg m²/s", route)
        self.assertIn("L = Iω", route)
        self.assertIn("_course_semantic_object_id", route)
        self.assertIn("register_semantic_transition_actions", route)
        self.assertIn("build_actions=[establish]", route)
        self.assertIn("sustain_actions=[sustain_spin]", route)
        self.assertIn("resolve_actions=[verify]", route)
        self.assertIn("RIGHT * 2.55 + UP * 2.55", route)
        self.assertIn("LEFT * 2.55 + UP * 2.55", route)
        self.assertNotIn("force cart", route.casefold())

    def test_rigid_body_plan_copy_explains_inertia_tensor_mapping(self):
        concept = stem_course.source_term_concept(
            "Angular Momentum of a Rigid Body",
            "physics",
        )
        hook = concept.hook.casefold()
        self.assertIn("mass distribution", hook)
        self.assertIn("sets i", hook)
        self.assertIn("i maps ω to l", hook)
        self.assertNotIn("torque", hook)

    def test_dedicated_exact_models_do_not_inherit_broad_family_caption_fields(self):
        source = stem_course.MANIM_SCENE_HELPERS
        captions = source[
            source.index("def physics_caption_text"):
            source.index("def physics_stage_setup_sequence")
        ]
        self.assertIn('if values.get("exact_title"):', captions)
        self.assertIn("return re.sub", captions)
        example = source[
            source.index("def play_example_visual"):
            source.index("def play_recall_visual")
        ]
        self.assertIn("dedicated_exact_physics_canvas", example)
        self.assertIn('not bool(exact_physics_payload.get("domain_renderer_ready"))', example)

    def test_renderer_fingerprint_tracks_new_domain_helpers(self):
        payload = stem_course.renderer_source_fingerprint_payload()
        self.assertIn(
            "play_physics_rigid_body_angular_momentum",
            payload["shared_manim_helpers_and_dispatch"],
        )
        self.assertIn(
            "domain_renderer_ready",
            inspect.getsource(stem_course.physics_semantic_data),
        )

    def test_typed_semantic_renderer_animates_transitionless_beats(self):
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index("def play_typed_semantic_contract"):
            source.index("def play_generic_visual")
        ]
        self.assertIn("def typed_semantic_pulse(run_time):", renderer)
        self.assertIn("sustain_actions=[typed_semantic_pulse]", renderer)


if __name__ == "__main__":
    unittest.main()

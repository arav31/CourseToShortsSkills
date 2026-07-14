from __future__ import annotations

from difflib import SequenceMatcher
import math
import re
import unittest

from tools import stem_course


MIT_MECHANICS_SOURCE_TOPICS = [
    "Rocket Equation",
    "Unit Vector",
    "Differential Equation",
    "Kinetic Energy And Work",
    "Center Of Mass",
    "Continuous Mass Transfer",
    "Position And Velocity",
    "Potential Energy Diagrams",
    "Potential Energy And Energy Conservation",
    "Conservation Of Energy",
    "Laws Of Motion",
    "Uniform Circular Motion",
    "Circular Motion Acceleration",
    "Relative Velocity And Recoil",
    "Torque And Angular Impulse",
    "Circular Motion Position",
]

EXPECTED_VISUALS = {
    "Newton's second law": "physics_force",
    "Kinematics": "physics_kinematics",
    "Work and energy": "physics_work",
    "Momentum": "physics_momentum",
    "Rocket Equation": "physics_rocket",
    "Unit Vector": "physics_vector",
    "Differential Equation": "physics_ode",
    "Kinetic Energy and Work": "physics_work",
    "Center of Mass": "physics_center_of_mass",
    "Continuous Mass Transfer": "physics_mass_transfer",
    "Position and Velocity": "physics_kinematics",
    "Potential Energy Diagrams": "physics_potential",
    "Potential Energy and Energy Conservation": "physics_energy",
    "Conservation of Energy": "physics_energy",
    "Laws of Motion": "physics_force",
    "Uniform Circular Motion": "physics_circular",
    "Circular Motion Acceleration": "physics_circular",
    "Relative Velocity and Recoil": "physics_recoil",
    "Torque and Angular Impulse": "physics_rotation",
    "Circular Motion Position": "physics_circular",
}


def mechanics_shorts() -> list[dict[str, object]]:
    concepts = list(stem_course.PHYSICS_MECHANICS)
    concepts.extend(stem_course.source_term_concept(topic, "physics") for topic in MIT_MECHANICS_SOURCE_TOPICS)
    return [stem_course.concept_to_short(concept, index) for index, concept in enumerate(concepts, 1)]


def helper_body(name: str, next_name: str) -> str:
    source = stem_course.MANIM_SCENE_HELPERS
    start = source.index(f"def {name}(")
    end = source.index(f"def {next_name}(", start)
    return source[start:end]


class PhysicsPlanningTests(unittest.TestCase):
    def test_continuous_mass_transfer_uses_dedicated_fail_closed_route(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Continuous Mass Transfer", "physics"), 1
        )
        self.assertEqual(stem_course.infer_visual_kind(short), "physics_mass_transfer")
        route = stem_course.animation_route_descriptor(short)
        self.assertTrue(route["supported"])
        self.assertEqual(route["route_key"], "physics:mit-8-01:20:continuous_mass_accumulation")
        self.assertEqual(route["renderer_state"]["family"], "mass_transfer")
        semantic_states = " ".join(
            str(value)
            for transition in route["renderer_state"]["transitions"]
            for state in (transition["before"], transition["after"])
            for value in state.values()
        ).lower()
        self.assertNotIn("rocket", semantic_states)

    def test_mass_transfer_renderer_binds_exact_payload_callbacks(self) -> None:
        body = helper_body("play_physics_mass_transfer_visual", "play_physics_rocket_visual_legacy")
        self.assertIn("for transition, action in zip(transitions, actions)", body)
        self.assertIn("self.register_semantic_transition_actions(groups, continuation_actions=[accumulation_cycle])", body)
        self.assertIn("inlet_carrier.animate.move_to", body)
        self.assertIn("outlet_carrier.animate.move_to", body)
        self.assertIn("Create(boundary)", body)
        self.assertNotIn("always_redraw", body)
        self.assertNotIn("FadeOut(boundary", body)

    def test_mass_transfer_uses_canonical_tex_and_phone_readable_lanes(self) -> None:
        body = helper_body("play_physics_mass_transfer_visual", "play_physics_rocket_visual_legacy")

        self.assertIn(r'r"\frac{dM_{cv}}{dt}=\dot{m}_{in}-\dot{m}_{out}"', body)
        self.assertNotIn(r'r"\\frac{dM_{cv}}{dt}', body)
        self.assertIn('"dM(cv)/dt = m_dot(in) - m_dot(out)"', body)
        self.assertIn('"steady: dM(cv)/dt = 0 => m_dot(in) = m_dot(out)"', body)
        self.assertIn('physics_phone_text("IN", font_size=40', body)
        self.assertIn('physics_phone_text("OUT", font_size=40', body)
        self.assertIn("font_size=48", body)
        self.assertNotIn("M_cv", body)

    def test_physics_conservation_fallback_is_ascii_and_semantic(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        start = source.index("def physics_ascii_formula_fallback(")
        end = source.index("def physics_phone_text(", start)
        namespace: dict[str, object] = {"re": re}
        exec(source[start:end], namespace)
        fallback = namespace["physics_ascii_formula_fallback"](
            object(),
            r"\frac{dM_{cv}}{dt}=\dot{m}_{in}-\dot{m}_{out}\Rightarrow 0",
        )

        self.assertTrue(fallback.isascii())
        self.assertEqual(fallback, "(dM(cv))/(dt)=m_dot(in)-m_dot(out)=> 0")
        self.assertNotRegex(fallback, r"\\[A-Za-z]+|[₀-₉]|[\u0300-\u036f]")

    def test_all_twenty_mit_mechanics_topics_route_to_semantic_families(self) -> None:
        shorts = mechanics_shorts()

        self.assertEqual(len(shorts), 20)
        self.assertEqual(
            {str(short["concept"]): stem_course.infer_visual_kind(short) for short in shorts},
            EXPECTED_VISUALS,
        )
        for short in shorts:
            kind = stem_course.infer_visual_kind(short)
            self.assertIn(kind, stem_course.PHYSICS_VISUAL_KINDS)
            if kind != "physics_force":
                self.assertNotIn("cart feels", str(short["worked_example"]["setup"]).lower())

    def test_unsupported_physics_topic_fails_instead_of_inheriting_force_cart(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported physics topic"):
            stem_course.source_term_concept("Thermodynamic Partition Function", "physics")

    def test_mit_fixture_has_no_duplicate_worked_examples(self) -> None:
        signatures: dict[tuple[str, str], str] = {}
        normalized_examples: list[tuple[str, str]] = []
        for short in mechanics_shorts():
            example = short["worked_example"]
            signature = tuple(
                re.sub(r"\s+", " ", str(example[field]).lower()).strip()
                for field in ("setup", "calculation")
            )
            self.assertNotIn(
                signature,
                signatures,
                msg=f"{short['concept']} duplicates {signatures.get(signature)}",
            )
            signatures[signature] = str(short["concept"])
            normalized_examples.append(
                (
                    str(short["concept"]),
                    re.sub(r"[^a-z0-9 ]+", " ", " ".join(signature)),
                )
            )

        for index, (concept, example) in enumerate(normalized_examples):
            for other_concept, other_example in normalized_examples[index + 1 :]:
                similarity = SequenceMatcher(None, example, other_example).ratio()
                self.assertLess(
                    similarity,
                    0.8,
                    msg=f"{concept} and {other_concept} use near-duplicate worked examples ({similarity:.3f})",
                )

    def test_related_mechanics_topics_use_distinct_visible_modes(self) -> None:
        shorts = mechanics_shorts()
        modes = {
            str(short["concept"]): stem_course.physics_semantic_data(short, stem_course.infer_visual_kind(short))["mode"]
            for short in shorts
        }
        hooks = {str(short["concept"]): str(short["hook"]) for short in shorts}

        self.assertEqual(modes["Newton's second law"], "force")
        self.assertEqual(modes["Laws of Motion"], "action_reaction")
        self.assertEqual(modes["Potential Energy Diagrams"], "potential_energy_diagram")
        self.assertEqual(modes["Potential Energy and Energy Conservation"], "spring_exchange")
        self.assertEqual(modes["Conservation of Energy"], "energy_conservation")
        self.assertEqual(modes["Uniform Circular Motion"], "uniform_circular_motion")
        self.assertEqual(modes["Circular Motion Acceleration"], "radial_acceleration")
        self.assertEqual(modes["Circular Motion Position"], "circular_position")
        self.assertEqual(
            len({hooks["Potential Energy and Energy Conservation"], hooks["Conservation of Energy"]}),
            2,
        )
        self.assertEqual(
            len({hooks["Uniform Circular Motion"], hooks["Circular Motion Acceleration"], hooks["Circular Motion Position"]}),
            3,
        )

    def test_generated_scenes_compile_with_structured_physics_payloads(self) -> None:
        for index, short in enumerate(mechanics_shorts(), 1):
            with self.subTest(concept=short["concept"]):
                animation_plan = stem_course.build_animation_plan(short)
                source = stem_course.manim_scene(short, f"PhysicsRegression{index:02d}", animation_plan)
                compile(source, "<generated-physics-scene>", "exec")
                self.assertIn("structured, recomputed physics payload", source)
                self.assertIn("play_physics_visual", source)

    def test_action_reaction_generated_source_binds_signs_to_directions_and_mathtex(self) -> None:
        short = next(short for short in mechanics_shorts() if short["concept"] == "Laws of Motion")
        data = stem_course.physics_semantic_data(short, "physics_force")
        source = stem_course.manim_scene(short, "NewtonSignRegression", stem_course.build_animation_plan(short))
        renderer = source[source.index("    def play_physics_force_visual("):source.index("    def play_physics_kinematics_visual(")]

        self.assertIn("bodies", data)
        self.assertLess(data["bodies"][0]["signed_force"], 0)
        self.assertGreater(data["bodies"][1]["signed_force"], 0)
        self.assertNotIn("accelerations", data)
        self.assertNotIn("forces", data)
        self.assertIn('force_a_value = float(body_a_payload["signed_force"])', renderer)
        self.assertIn("acceleration_a = force_a_value / mass_a", renderer)
        self.assertIn("direction_a = LEFT if force_a_value < 0 else RIGHT", renderer)
        self.assertIn("direction_b = LEFT if force_b_value < 0 else RIGHT", renderer)
        self.assertIn('signed_acceleration_a = ("+" if acceleration_a > 0 else "") + self.fmt(acceleration_a)', renderer)
        self.assertIn("body_a.animate.shift(direction_a * 0.55)", renderer)
        self.assertIn("body_b.animate.shift(direction_b * 0.45)", renderer)
        self.assertGreaterEqual(renderer.count("body_a.animate.shift(direction_a"), 4)
        self.assertGreaterEqual(renderer.count("body_b.animate.shift(direction_b"), 4)
        self.assertIn("force_a_anchor = skater_a.get_left() if force_a_value < 0 else skater_a.get_right()", renderer)
        self.assertIn("force_b_anchor = skater_b.get_left() if force_b_value < 0 else skater_b.get_right()", renderer)
        self.assertIn("acceleration_arrow_a", renderer)
        self.assertIn("acceleration_arrow_b", renderer)
        self.assertIn(r'\vec{a}_{A}=\frac{\vec{F}_{B\to A}}{m_A}', renderer)
        self.assertIn(r'\vec{a}_{B}=\frac{\vec{F}_{A\to B}}{m_B}', renderer)
        self.assertIn('r"\\vec{a}_{A}=\\frac{\\vec{F}_{B\\to A}}{m_A}"', renderer)
        self.assertNotIn('r"\\\\vec{a}_{A}', renderer)
        self.assertIn(r'\frac{\lvert a_A\rvert}{\lvert a_B\rvert}', renderer)
        self.assertNotIn(r'\frac{|a_A|}{|a_B|}', renderer)
        self.assertIn(r'\mathrm{m\,s^{-2}}', renderer)
        self.assertNotIn('"aA="', renderer)
        self.assertNotIn('"aB="', renderer)

    def test_action_reaction_renderer_stages_causality_without_prose_padding(self) -> None:
        short = next(short for short in mechanics_shorts() if short["concept"] == "Laws of Motion")
        source = stem_course.manim_scene(short, "NewtonCausalRegression", stem_course.build_animation_plan(short))
        renderer = source[source.index("    def play_physics_force_visual("):source.index("    def play_physics_kinematics_visual(")]
        captions = source[source.index("    def physics_caption_text("):source.index("    def physics_stage_setup_sequence(")]

        self.assertLess(renderer.index("def show_force_pair"), renderer.index("def show_acceleration_a"))
        self.assertLess(renderer.index("def show_acceleration_a"), renderer.index("def show_acceleration_b"))
        self.assertLess(renderer.index("def show_acceleration_b"), renderer.index("def show_mass_comparison"))
        self.assertLess(renderer.index("def show_mass_comparison"), renderer.index("def resolve_mass_ratio"))
        self.assertIn("self.register_newton_causal_actions([", renderer)
        self.assertIn("resolve_mass_ratio,", renderer)
        self.assertNotIn("self.register_semantic_track(body_a", renderer)
        self.assertEqual(renderer.count("require_mathtex=True"), 7)
        self.assertIn("force_a_equation", renderer)
        self.assertIn("force_b_equation", renderer)
        self.assertIn("ReplacementTransform(force_a_equation, force_b_equation)", renderer)
        self.assertNotIn("force_pair = self.physics_formula_label", renderer)
        self.assertIn('if kind == "physics_force" and values.get("mode") == "action_reaction":', captions)
        self.assertIn('return ""', captions)

    def test_action_reaction_derivations_are_phone_readable_and_every_beat_moves(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = helper_body("play_physics_force_visual", "play_physics_rolling_kinematics_visual")
        scheduler = helper_body("register_newton_causal_actions", "register_semantic_transition_actions")

        self.assertIn("acceleration_a_relation", renderer)
        self.assertIn("acceleration_a_value", renderer)
        self.assertIn("acceleration_b_relation", renderer)
        self.assertIn("acceleration_b_value", renderer)
        self.assertNotIn(r"s^{-2}}\\qquad \\vec{a}", renderer)
        self.assertEqual(renderer.count("font_size=80, max_height=1.5, require_mathtex=True"), 2)
        self.assertEqual(renderer.count("font_size=64, max_height=1.2, require_mathtex=True"), 2)
        self.assertIn("ReplacementTransform(acceleration_a_relation, acceleration_a_value)", renderer)
        self.assertIn("ReplacementTransform(acceleration_b_relation, acceleration_b_value)", renderer)
        self.assertIn("max_width=6.4, max_height=2.2, min_width=3.4, min_height=1.7", renderer)
        self.assertIn("comparison.width + 1e-6 < 3.4", renderer)
        self.assertIn("comparison.height + 1e-6 < 1.7", renderer)
        self.assertIn("minimum_mass_label_clearance = 0.28", renderer)
        self.assertEqual(renderer.count("font_size=46, color="), 2)
        self.assertEqual(renderer.count("max_width=2.8, max_height=0.82, min_height=0.52"), 2)
        self.assertIn("label_b.get_left()[0] - label_a.get_right()[0]", renderer)
        self.assertIn("Newton mass labels do not satisfy horizontal clearance", renderer)
        self.assertIn(".align_to(skater_a, RIGHT)", renderer)
        self.assertIn(".align_to(skater_b, LEFT)", renderer)
        self.assertIn('"max_frozen_tail_seconds": 0.65', scheduler)
        self.assertIn("len(prepared) < len(remaining_beats)", scheduler)
        self.assertIn("if any(not batch for batch in action_batches)", scheduler)
        self.assertNotIn('beat.get("planned_arc_phase") == "transform"', scheduler)
        self.assertGreaterEqual(renderer.count("Indicate("), 7)
        self.assertIn("comparison.animate.shift(UP * 0.06)", renderer)
        self.assertIn("comparison.animate.shift(DOWN * 0.06)", renderer)
        self.assertIn("comparison.animate.shift(UP * 0.1)", renderer)

    def test_structured_newton_math_preserves_semantic_layout_primitives(self) -> None:
        compositor = helper_body("physics_structured_math_mob", "physics_math_mob")
        math_loader = helper_body("physics_math_mob", "physics_ascii_formula_fallback")

        for feature in (
            'features.add("vector_arrow")',
            'features.add("hat")',
            'features.add("subscript")',
            'features.add("superscript")',
            'features.add("fraction")',
            'features.add("absolute_value")',
            'features.add("units")',
        ):
            self.assertIn(feature, compositor)
        self.assertIn('Line(LEFT * width / 2, RIGHT * width / 2', compositor)
        self.assertIn('mob._formula_tex_backend = "manim-structured-math"', compositor)
        self.assertIn('mob._formula_render_mode = "structured_vector_math"', compositor)
        self.assertIn("self.physics_structured_math_mob(source", math_loader)
        self.assertNotIn("physics_ascii_formula_fallback", math_loader)
        self.assertNotIn("Text(fallback_text", math_loader)

    def test_action_reaction_payload_normalization_is_axis_agnostic(self) -> None:
        payload = {
            "mode": "action_reaction",
            "masses": [4.0, 2.0],
            "forces": [8.0, -8.0],
            "accelerations": [-99.0, 99.0],
        }

        normalized = stem_course.normalize_action_reaction_payload(payload)

        self.assertEqual(
            normalized["bodies"],
            [
                {"label": "A", "mass": 4.0, "signed_force": 8.0},
                {"label": "B", "mass": 2.0, "signed_force": -8.0},
            ],
        )
        self.assertNotIn("forces", normalized)
        self.assertNotIn("accelerations", normalized)
        stem_course.validate_physics_renderer_values("physics_force", normalized)

    def test_center_of_mass_scale_does_not_require_number_line_latex(self) -> None:
        short = next(short for short in mechanics_shorts() if short["concept"] == "Center of Mass")
        source = stem_course.manim_scene(short, "CenterOfMassPortabilityRegression", stem_course.build_animation_plan(short))

        self.assertNotIn("include_numbers=True", source)
        self.assertIn("include_numbers=False", source)
        self.assertNotIn("scale_labels = VGroup", helper_body("play_physics_center_of_mass_visual", "play_physics_rocket_visual"))

    def test_rejected_families_have_valid_equations_and_readable_fallbacks(self) -> None:
        shorts = {str(short["concept"]): short for short in mechanics_shorts()}
        kinematics = shorts["Kinematics"]
        rocket = shorts["Rocket Equation"]
        center = shorts["Center of Mass"]

        self.assertIn(r"\frac{1}{2}", str(kinematics["formula"]))
        self.assertNotIn(r"\frac12", str(kinematics["formula"]))
        self.assertEqual(
            center["formula"],
            r"\vec r_{\mathrm{cm}}=\frac{\sum_i m_i\vec r_i}{\sum_i m_i}",
        )
        self.assertEqual(
            rocket["formula"],
            r"\Delta v=v_e\ln\!\left(\frac{m_i}{m_f}\right)",
        )
        self.assertNotIn("e+03", str(rocket["worked_example"]["calculation"]))

        source = stem_course.manim_scene(rocket, "RocketNotationRegression", stem_course.build_animation_plan(rocket))
        self.assertNotIn("frac12", source)
        self.assertNotIn("e+03", source)
        self.assertIn("1022", source)
        self.assertIn("Δv = v<sub>e</sub> ln(m<sub>i</sub>/m<sub>f</sub>)", source)

    def test_physics_captions_are_complete_and_formula_driven(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        captions = helper_body("physics_caption_text", "physics_stage_setup_sequence")
        setup = helper_body("physics_stage_setup_sequence", "physics_stage_bottom_sequence")
        bottom = helper_body("physics_stage_bottom_sequence", "active_hold")

        self.assertIn("def physics_caption_text", helpers)
        self.assertIn("for index in range(len(stages))", setup)
        self.assertNotIn("for index, lines in enumerate(stages", setup)
        self.assertIn('if not text:', bottom)
        self.assertIn('kind == "physics_center_of_mass"', captions)
        self.assertIn('state == "example_calculation"', captions)
        self.assertIn('return ""', captions)
        self.assertNotIn("Spring U:", captions)
        self.assertNotIn("Uₛ:", captions)
        self.assertNotIn("τ = (", captions)
        self.assertIn("Expelled momentum and decreasing mass", captions)
        self.assertIn("group_with_commas=False", helpers)

    def test_physics_renderers_do_not_morph_text_groups(self) -> None:
        physics_block = helper_body("play_physics_force_visual", "cs_array_row")
        unsafe_text_transforms = (
            "Transform(force_pair",
            "Transform(net_calc",
            "Transform(magnitude",
            "Transform(start_label",
            "Transform(moments",
            "Transform(mass_label",
            "Transform(flow_label",
            "Transform(law",
            "Transform(calc",
            "Transform(momentum_calc",
            "Transform(condition",
            "Transform(label",
            "Transform(construction",
            "Transform(torque",
            "Transform(zero",
            "Transform(period_label",
        )
        for transform in unsafe_text_transforms:
            self.assertNotIn(transform, physics_block)
        self.assertIn("def physics_retire_then_show", stem_course.MANIM_SCENE_HELPERS)
        self.assertIn("def physics_atomic_text_handoff", stem_course.MANIM_SCENE_HELPERS)
        self.assertIn("mob_class=Text", stem_course.MANIM_SCENE_HELPERS)
        self.assertIn("def physics_structured_math_mob", stem_course.MANIM_SCENE_HELPERS)
        self.assertIn('acceleration_law_pattern = r"SUMVECF_', stem_course.MANIM_SCENE_HELPERS)
        self.assertIn('token("m"), symbol("a", vector=True)', stem_course.MANIM_SCENE_HELPERS)
        self.assertNotIn("MarkupText(fallback_text", stem_course.MANIM_SCENE_HELPERS)

    def test_rejected_families_use_beat_driven_physics_state(self) -> None:
        renderers = (
            ("play_physics_kinematics_visual", "play_physics_vector_visual"),
            ("play_physics_center_of_mass_visual", "play_physics_rocket_visual"),
            ("play_physics_rocket_visual", "play_physics_ode_visual"),
            ("play_physics_energy_visual", "play_physics_momentum_visual"),
            ("play_physics_rotation_visual", "play_physics_recoil_visual"),
        )
        for name, next_name in renderers:
            with self.subTest(renderer=name):
                body = helper_body(name, next_name)
                self.assertIn("configure_physics_motion", body)
                self.assertNotIn("add_updater(lambda clock, dt", body)

        self.assertIn('motion.get("kind") == "physics_state"', stem_course.MANIM_SCENE_HELPERS)
        self.assertIn('"state_actions": normalized_actions', stem_course.MANIM_SCENE_HELPERS)
        self.assertIn("state_actions[current_index]()", stem_course.MANIM_SCENE_HELPERS)
        kinematics = helper_body("play_physics_kinematics_visual", "play_physics_vector_visual")
        self.assertNotIn("get_area(", kinematics)
        self.assertIn("traced_curve", kinematics)
        self.assertIn("time_projection", kinematics)
        self.assertIn("linear_trace", kinematics)
        self.assertIn("acceleration_contribution", kinematics)
        self.assertNotIn("time_window", kinematics)
        self.assertNotIn("decomposition_pulse", kinematics)
        self.assertIn("term_stage = ValueTracker", kinematics)
        self.assertIn("def term_reveal", kinematics)
        self.assertIn("component_band", kinematics)
        self.assertIn("component_outlines", kinematics)
        self.assertNotIn("rail = RoundedRectangle", kinematics)
        self.assertIn("time_targets = [0.1, 0.22, 0.36, 0.51, 0.67, 0.83, 1.0]", kinematics)
        self.assertIn("term_targets = [0.75, 1.35, 2.05, 2.55, 3.0, 3.0, 3.0]", kinematics)
        self.assertNotIn("equation = self.physics_formula_label", kinematics)

    def test_phone_layout_contracts_keep_semantics_separate(self) -> None:
        rocket = helper_body("play_physics_rocket_visual", "play_physics_ode_visual")
        center = helper_body("play_physics_center_of_mass_visual", "play_physics_rocket_visual_legacy")
        energy = helper_body("play_physics_energy_visual", "play_physics_momentum_visual")
        rotation = helper_body("play_physics_rotation_visual", "play_physics_recoil_visual")

        self.assertIn("mass_fill_shape", rocket)
        self.assertIn("velocity_fill_shape", rocket)
        self.assertIn("def exhaust_packet", rocket)
        self.assertIn("for index in range(9)", rocket)
        self.assertIn('physics_phone_text("mi = "', rocket)
        self.assertIn('physics_phone_text("mf = "', rocket)
        self.assertIn('physics_phone_text("ve = "', rocket)
        self.assertIn("self.add_readability_backplate(mass_readout", rocket)
        self.assertIn("self.add_readability_backplate(velocity_readout", rocket)
        self.assertNotIn("def bar_pulse", rocket)
        self.assertNotIn("mass_pulse", rocket)
        self.assertNotIn("velocity_pulse", rocket)
        self.assertIn("return LEFT * 0.68 + UP * 1.05", rocket)
        self.assertIn("release_at = index / 11.0", rocket)
        self.assertIn("travel = progress() - release_at", rocket)
        self.assertNotIn("packet_phase", rocket)
        self.assertNotIn("% 1.0", rocket)
        self.assertIn("rocket_center() + LEFT * 2.45", rocket)
        self.assertIn("computed_delta_v =", rocket)
        self.assertIn("final_equation = self.physics_formula_label", rocket)
        self.assertIn("show_final_equation", rocket)
        self.assertNotIn("self.add(final_equation)", rocket[: rocket.index("def show_final_equation")])
        self.assertNotIn('semantic_label("moments:', center)
        self.assertNotIn('semantic_label("x_cm', center)
        self.assertNotIn("self.play(balance.animate.set_value", center)
        self.assertIn("def beam_angle", center)
        self.assertIn("0.52 * imbalance", center)
        self.assertNotIn("def moment_token", center)
        self.assertNotIn("moment_scan_window", center)
        self.assertIn("moment_reveal = ValueTracker", center)
        self.assertIn("left_mass_position = ValueTracker", center)
        self.assertIn("right_mass_position = ValueTracker", center)
        self.assertNotIn("def staged_position", center)
        self.assertIn("def left_display_position", center)
        self.assertIn("def right_display_position", center)
        self.assertIn("return left_mass_position.get_value()", center)
        self.assertIn("return right_mass_position.get_value()", center)
        self.assertIn("reveal_targets = [0.0, 0.0, 0.5, 1.0, 1.0, 1.0]", center)
        self.assertNotIn("equality_reveal", center)
        self.assertNotIn("answer_reveal", center)
        self.assertIn("weighted_moment_formula", center)
        self.assertNotIn("perturbation = ValueTracker", center)
        self.assertNotIn("FadeIn(weighted_moment_formula)", center)
        self.assertNotIn("FadeIn(balance_label)", center)
        self.assertNotIn("weighted_moment_formula.add_updater", center)
        self.assertNotIn("balance_label.add_updater", center)
        self.assertIn("show_moment_equality", center)
        self.assertIn("show_balance_answer", center)
        self.assertIn("balance point = ", center)
        self.assertIn("balance_targets = [", center)
        self.assertIn("LEFT * 2.25 + UP * 2.9", center)
        self.assertIn("RIGHT * 2.25 + UP * 2.9", center)
        self.assertNotIn("label1.add_updater", center)

        self.assertNotIn("kinetic_halo", energy)
        self.assertNotIn("transfer_packet", energy)
        self.assertNotIn("flow_phase", energy)
        self.assertIn("transfer_arrow", energy)
        self.assertNotIn("conservation_band", energy)
        self.assertNotIn("equation_band", energy)
        self.assertNotIn("K = E - U", energy)
        self.assertNotIn("state_labels", energy)
        self.assertIn("initial_formula", energy)
        self.assertIn("conservation_identity", energy)
        self.assertIn("equilibrium_formula", energy)
        self.assertIn("speed_formula", energy)
        self.assertIn('physics_metric_readout("U ="', energy)
        self.assertIn('physics_metric_readout("K ="', energy)
        self.assertIn("transfer_progress = ValueTracker", energy)
        self.assertIn("def compression_fraction", energy)
        self.assertNotIn("def release_progress", energy)
        self.assertIn("self.physics_atomic_text_handoff(initial_formula, equilibrium_formula)", energy)
        self.assertIn("transfer_targets = [0.08, 0.18, 0.3, 0.44, 0.56, 0.7, 0.84, 0.94, 1.0]", energy)
        self.assertNotIn("phase_clock", energy)
        self.assertNotIn("equilibrium_label", energy)
        self.assertNotIn("displacement = always_redraw", energy)

        self.assertNotIn("radius_label.add_updater", rotation)
        self.assertNotIn("force_label.add_updater", rotation)
        self.assertIn("momentum_fill_shape", rotation)
        self.assertNotIn("self.play(elapsed.animate.set_value", rotation)
        self.assertIn("accumulation_band", rotation)
        self.assertIn("progress_marker", rotation)
        self.assertNotIn("def impulse_packet", rotation)
        self.assertIn("rod_length = 4.15", rotation)
        self.assertIn("angle_sweep = 1.0", rotation)
        self.assertNotIn("def lever_progress", rotation)
        self.assertNotIn("torque_reveal = ValueTracker", rotation)
        self.assertNotIn("impulse_reveal = ValueTracker", rotation)
        self.assertIn("return start_angle + angle_sweep * progress()", rotation)
        self.assertNotIn("FadeIn(torque_formula)", rotation)
        self.assertNotIn("FadeIn(impulse_formula)", rotation)
        self.assertIn('physics_metric_readout(', rotation)
        self.assertIn("torque_value * elapsed.get_value()", rotation)
        self.assertIn("show_torque_calculation", rotation)
        self.assertIn("show_angular_impulse", rotation)

    def test_physics_handoffs_and_routes_forbid_partial_frame_wipes(self) -> None:
        setup = helper_body("physics_stage_setup_sequence", "physics_stage_bottom_sequence")
        bottom = helper_body("physics_stage_bottom_sequence", "active_hold")
        rocket = helper_body("play_physics_rocket_visual", "play_physics_ode_visual")
        energy = helper_body("play_physics_energy_visual", "play_physics_momentum_visual")
        kinematics = helper_body("play_physics_kinematics_visual", "play_physics_vector_visual")

        self.assertNotIn("FadeOut(", setup)
        self.assertNotIn("FadeOut(", bottom)
        self.assertNotIn("FadeIn(", setup)
        self.assertNotIn("FadeIn(", bottom)
        self.assertNotIn("animate.set_opacity", setup)
        self.assertNotIn("animate.set_opacity", bottom)
        self.assertIn("self.add(staged)", setup)
        self.assertIn("self.remove(staged)", setup)
        self.assertIn("self.add(staged)", bottom)
        self.assertIn("self.remove(*current)", bottom)
        for body, forbidden in (
            (rocket, ("bar_pulse", "mass_pulse", "velocity_pulse")),
            (energy, ("transfer_packet", "flow_phase")),
            (kinematics, ("time_window", "decomposition_pulse")),
        ):
            for marker in forbidden:
                self.assertNotIn(marker, body)

    def test_circular_and_rolling_live_geometry_stays_transition_safe(self) -> None:
        circular = helper_body("play_physics_circular_visual", "play_physics_rotation_visual_legacy")
        rolling = helper_body("play_physics_rolling_kinematics_visual", "play_physics_kinematics_visual")

        self.assertIn("radius_line = always_redraw(lambda: VGroup(", circular)
        self.assertIn("projection_anchor = always_redraw", circular)
        self.assertIn("self.physics_atomic_text_handoff(label, calc)", circular)
        self.assertNotIn("FadeOut(label)", circular)
        self.assertGreaterEqual(rolling.count("self.clamp_to_safe_frame("), 2)
        self.assertIn("def clamp_to_safe_frame", stem_course.MANIM_SCENE_HELPERS)

    def test_energy_scene_uses_explicit_initial_and_final_formula_slots(self) -> None:
        short = next(short for short in mechanics_shorts() if short["concept"] == "Potential Energy and Energy Conservation")
        source = stem_course.manim_scene(short, "EnergyTransitionRegression", stem_course.build_animation_plan(short))

        self.assertIn(r"K_{\\mathrm{initial}}+U_{\\mathrm{initial}}=K_{\\mathrm{final}}+U_{\\mathrm{final}}", source)
        self.assertIn("K<sub>initial</sub> + U<sub>initial</sub> = K<sub>final</sub> + U<sub>final</sub>", source)
        construct = source[source.index("    def construct(self):") :]
        self.assertIn("self.physics_atomic_text_handoff(hook, next_hook)", construct)
        self.assertIn("self.physics_atomic_text_handoff(outgoing_formula_text, formula)", construct)
        self.assertIn("self.physics_atomic_text_handoff(intuition, next_intuition)", construct)

    def test_rejected_renderers_recompute_and_reveal_conclusions_after_motion(self) -> None:
        kinematics = helper_body("play_physics_kinematics_visual", "play_physics_vector_visual")
        center = helper_body("play_physics_center_of_mass_visual", "play_physics_rocket_visual_legacy")
        rocket = helper_body("play_physics_rocket_visual", "play_physics_ode_visual")
        energy = helper_body("play_physics_energy_visual", "play_physics_momentum_visual")
        rotation = helper_body("play_physics_rotation_visual", "play_physics_recoil_visual")

        self.assertIn("final_position = position(duration)", kinematics)
        self.assertIn("final_velocity = v0 + acceleration * duration", kinematics)
        self.assertIn("(m1 * x1 + m2 * x2) / max(total_mass, 1e-6)", center)
        self.assertIn('values["exhaust_speed"] * math.log(values["initial_mass"] / values["final_mass"])', rocket)
        self.assertIn("total_energy = 0.5 * spring_constant * compression * compression", energy)
        self.assertIn("final_speed = math.sqrt(2.0 * total_energy / max(mass_value, 1e-6))", energy)
        self.assertIn('torque_value = values["radius"] * values["force"]', rotation)
        self.assertIn('angular_impulse = torque_value * values["duration"]', rotation)

        for body, callback in (
            (kinematics, "show_final_summary"),
            (center, "show_balance_answer"),
            (rocket, "show_final_equation"),
            (energy, "show_final_speed"),
            (rotation, "show_angular_impulse"),
        ):
            with self.subTest(callback=callback):
                self.assertIn("state_actions=", body)
                self.assertIn(f"def {callback}", body)

        self.assertNotIn("final_summary.add_updater", kinematics)
        self.assertNotIn("weighted_moment_formula.add_updater", center)
        self.assertNotIn("final_equation.add_updater", rocket)
        self.assertNotIn("speed_formula.add_updater", energy)
        self.assertNotIn("impulse_formula.add_updater", rotation)

    def test_publication_physics_uses_phone_scale_text_and_full_beat_motion(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        self.assertIn("def physics_phone_text", helpers)
        self.assertIn("requested_font_size = max(36.0, float(font_size))", helpers)
        self.assertIn("_course_effective_font_size", helpers)
        self.assertIn("font_size=max(40, font_size)", helpers)
        self.assertNotIn("font_size=max(35, font_size)", helpers)
        self.assertIn("width=34", helper_body("physics_stage_setup_sequence", "physics_stage_bottom_sequence"))
        self.assertIn("width=34", helper_body("physics_stage_bottom_sequence", "active_hold"))

        expected_state_counts = {
            ("play_physics_kinematics_visual", "play_physics_vector_visual"): 7,
            ("play_physics_center_of_mass_visual", "play_physics_rocket_visual_legacy"): 6,
            ("play_physics_rocket_visual", "play_physics_ode_visual"): 7,
            ("play_physics_energy_visual", "play_physics_momentum_visual"): 9,
            ("play_physics_rotation_visual", "play_physics_recoil_visual"): 7,
        }
        for (name, next_name), state_count in expected_state_counts.items():
            with self.subTest(renderer=name):
                body = helper_body(name, next_name)
                if name == "play_physics_energy_visual":
                    targets = re.search(r"transfer_targets = \[(.*?)\]", body, re.S).group(1)
                    self.assertEqual(len([part for part in targets.split(",") if part.strip()]), state_count)
                elif name == "play_physics_rotation_visual":
                    start = body.index("elapsed_targets = [")
                    targets = body[start : body.index("self.configure_physics_motion", start)]
                    self.assertEqual(targets.count('values["duration"]'), state_count)
                elif name == "play_physics_center_of_mass_visual":
                    targets = re.search(r"balance_targets = \[(.*?)\]", body, re.S).group(1)
                    self.assertEqual(len([part for part in targets.split(",") if part.strip()]), state_count)
                elif name == "play_physics_kinematics_visual":
                    targets = re.search(r"time_targets = \[(.*?)\]", body, re.S).group(1)
                    self.assertEqual(len([part for part in targets.split(",") if part.strip()]), state_count)
                elif name == "play_physics_rocket_visual":
                    self.assertIn("for index in range(7)", body)


class PhysicsNumericalTests(unittest.TestCase):
    def test_every_displayed_conclusion_recomputes_from_source_values(self) -> None:
        for short in mechanics_shorts():
            kind = stem_course.infer_visual_kind(short)
            data = stem_course.physics_semantic_data(short, kind)
            with self.subTest(concept=short["concept"], kind=kind, mode=data["mode"]):
                self.assertEqual(data["kind"], kind)
                if kind == "physics_force" and data["mode"] == "action_reaction":
                    self.assertAlmostEqual(sum(body["signed_force"] for body in data["bodies"]), 0.0)
                    self.assertTrue(all(body["mass"] > 0 for body in data["bodies"]))
                elif kind == "physics_force":
                    self.assertAlmostEqual(data["net"], data["applied"] - data["opposing"])
                    self.assertAlmostEqual(data["acceleration"], data["net"] / data["mass"])
                elif kind == "physics_kinematics":
                    time = data["duration"]
                    expected_x = data["x0"] + data["v0"] * time + 0.5 * data["acceleration"] * time**2
                    expected_v = data["v0"] + data["acceleration"] * time
                    self.assertAlmostEqual(data["final_position"], expected_x)
                    self.assertAlmostEqual(data["final_velocity"], expected_v)
                    self.assertEqual(len(data["times"]), len(data["positions"]))
                elif kind == "physics_vector":
                    self.assertAlmostEqual(math.hypot(*data["components"]), data["magnitude"])
                    self.assertAlmostEqual(math.hypot(*data["unit"]), 1.0)
                    cross = data["components"][0] * data["unit"][1] - data["components"][1] * data["unit"][0]
                    self.assertAlmostEqual(cross, 0.0)
                elif kind == "physics_center_of_mass":
                    numerator = sum(mass * position for mass, position in zip(data["masses"], data["positions"]))
                    self.assertAlmostEqual(data["center"], numerator / data["total_mass"])
                    self.assertAlmostEqual(
                        sum(mass * (position - data["center"]) for mass, position in zip(data["masses"], data["positions"])),
                        0.0,
                    )
                    self.assertAlmostEqual(data["candidate_positions"][-1], data["center"])
                    self.assertAlmostEqual(data["left_balance_moments"][-1], data["right_balance_moments"][-1])
                elif kind == "physics_rocket" and data["mode"] == "rocket":
                    expected = data["exhaust_speed"] * math.log(data["initial_mass"] / data["final_mass"])
                    self.assertAlmostEqual(data["delta_v"], expected)
                    self.assertEqual(data["mass_samples"][-1], data["final_mass"])
                    self.assertTrue(all(a > b for a, b in zip(data["mass_samples"], data["mass_samples"][1:])))
                    self.assertTrue(all(a < b for a, b in zip(data["velocity_samples"], data["velocity_samples"][1:])))
                elif kind == "physics_mass_transfer":
                    self.assertEqual(data["family"], "mass_transfer")
                    self.assertTrue(all(data["verification"].values()))
                    self.assertGreaterEqual(len(data["transitions"]), 3)
                    setup = data["numeric_setup"]
                    result = data["result_fields"]
                    expected_mass = setup["initial_mass"] + (
                        setup["inlet_mass_flow"] - setup["outlet_mass_flow"]
                    ) * setup["duration"]
                    self.assertAlmostEqual(result["final_mass"], expected_mass)
                elif kind == "physics_rocket":
                    expected = data["mass_rate"] * (data["outgoing_velocity"] - data["incoming_velocity"])
                    self.assertAlmostEqual(data["force"], expected)
                    self.assertAlmostEqual(data["momentum_rate_out"] - data["momentum_rate_in"], expected)
                elif kind == "physics_ode":
                    expected = data["initial"] * math.exp(-data["decay"] * data["duration"])
                    self.assertAlmostEqual(data["final"], expected)
                    self.assertAlmostEqual(data["slopes"][-1], -data["decay"] * data["states"][-1])
                elif kind == "physics_work":
                    self.assertAlmostEqual(data["work"], data["force"] * data["distance"])
                    self.assertAlmostEqual(data["final_energy"] - data["initial_energy"], data["work"])
                    self.assertAlmostEqual(0.5 * data["mass"] * data["final_speed"] ** 2, data["final_energy"])
                elif kind == "physics_energy":
                    if data["mode"] == "energy_conservation":
                        setup = data["numeric_setup"]
                        result = data["result_fields"]
                        self.assertAlmostEqual(
                            result["final_mechanical_energy"],
                            setup["initial_kinetic_energy"]
                            + setup["initial_potential_energy"]
                            + setup["nonconservative_work"],
                        )
                        self.assertAlmostEqual(
                            result["final_potential_energy"],
                            result["final_mechanical_energy"] - result["final_kinetic_energy"],
                        )
                        continue
                    self.assertAlmostEqual(data["final_potential"] + data["kinetic_gain"], data["total_energy"])
                    self.assertAlmostEqual(0.5 * data["mass"] * data["final_speed"] ** 2, data["kinetic_gain"])
                    if data["mode"] == "spring_exchange":
                        for potential, kinetic, speed in zip(data["potential_samples"], data["kinetic_samples"], data["speed_samples"]):
                            self.assertAlmostEqual(potential + kinetic, data["total_energy"])
                            self.assertAlmostEqual(0.5 * data["mass"] * speed**2, kinetic)
                elif kind == "physics_momentum":
                    self.assertAlmostEqual(sum(data["momenta"]), data["total_momentum"])
                    self.assertAlmostEqual(data["final_mass"] * data["final_velocity"], data["total_momentum"])
                elif kind == "physics_potential":
                    setup = data["numeric_setup"]
                    for point in data["result_fields"]["turning_points"]:
                        self.assertAlmostEqual(
                            setup["curvature"] * (point - setup["center"]) ** 2 + setup["floor_energy"],
                            setup["total_energy"],
                        )
                elif kind == "physics_circular" and data["mode"] == "circular_position":
                    self.assertAlmostEqual(math.hypot(*data["position"]), data["radius"])
                    self.assertAlmostEqual(data["speed"], abs(data["radius"] * data["omega"]))
                elif kind == "physics_circular":
                    self.assertAlmostEqual(data["radial_acceleration"], data["speed"] ** 2 / data["radius"])
                    self.assertAlmostEqual(data["omega"], data["speed"] / data["radius"])
                elif kind == "physics_rotation":
                    if data["mode"] == "angular_impulse":
                        setup = data["numeric_setup"]
                        result = data["result_fields"]
                        self.assertAlmostEqual(
                            result["final_angular_momentum"],
                            setup["initial_angular_momentum"]
                            + setup["constant_torque"] * setup["time_interval"],
                        )
                        continue
                    self.assertAlmostEqual(data["torque"], data["radius"] * data["force"])
                    self.assertAlmostEqual(data["angular_impulse"], data["torque"] * data["duration"])
                    self.assertAlmostEqual(data["angular_momentum_samples"][-1], data["angular_impulse"])
                    for time, angular_momentum in zip(data["time_samples"], data["angular_momentum_samples"]):
                        self.assertAlmostEqual(angular_momentum, data["torque"] * time)
                elif kind == "physics_recoil":
                    setup = data["numeric_setup"]
                    result = data["result_fields"]
                    self.assertAlmostEqual(result["final_total_momentum"], setup["initial_total_momentum"])
                    self.assertAlmostEqual(
                        setup["mass_1"] * result["final_velocity_1"]
                        + setup["mass_2"] * result["final_velocity_2"],
                        result["final_total_momentum"],
                    )
                else:
                    self.fail(f"No invariant assertion for {kind}/{data['mode']}")

    def test_wave_family_recomputes_speed_and_period(self) -> None:
        concept = stem_course.source_term_concept("Wave Propagation", "physics")
        short = stem_course.concept_to_short(concept, 1)
        data = stem_course.physics_semantic_data(short, "physics_wave")

        self.assertAlmostEqual(data["speed"], data["wavelength"] * data["frequency"])
        self.assertAlmostEqual(data["period"], 1.0 / data["frequency"])


if __name__ == "__main__":
    unittest.main()

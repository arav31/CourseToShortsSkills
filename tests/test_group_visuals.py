from __future__ import annotations

import ast
import inspect
import math
import re
import unittest

import numpy as np

from tools import stem_course


def semantic_harness():
    namespace = {"math": math, "np": np, "re": re}
    terminal_source = stem_course.MANIM_SCENE_HELPERS[
        stem_course.MANIM_SCENE_HELPERS.index("def semantic_terminal_batches") :
        stem_course.MANIM_SCENE_HELPERS.index("def semantic_callback_choreography")
    ]
    exec(terminal_source, namespace)
    group_source = stem_course.MANIM_SCENE_HELPERS[
        stem_course.MANIM_SCENE_HELPERS.index("def semantic_worked_parts") :
        stem_course.MANIM_SCENE_HELPERS.index("def algebra_factor_semantics")
    ]
    exec(group_source, namespace)

    class Harness:
        pass

    for name in (
        "semantic_worked_parts",
        "semantic_moduli",
        "semantic_integer_sets",
        "semantic_first_int",
        "group_coset_semantics",
        "group_homomorphism_semantics",
        "group_action_semantics",
        "group_structure_semantics",
        "group_plain_math",
        "group_raw_math_source_residue",
        "group_math_residue",
        "group_route_clear_of_bounds",
        "group_collision_safe_transit_points",
        "semantic_terminal_batches",
        "register_group_actions",
    ):
        setattr(Harness, name, namespace[name])
    return Harness()


def formula_fallback_harness():
    namespace = {"json": __import__("json"), "re": re}
    source = stem_course.MANIM_SCENE_HELPERS[
        stem_course.MANIM_SCENE_HELPERS.index("def formula_fallback_text") :
        stem_course.MANIM_SCENE_HELPERS.index("def ensure_semantic_tex_backend")
    ]
    exec(source, namespace)

    class Harness:
        pass

    Harness.formula_fallback_text = namespace["formula_fallback_text"]
    Harness.formula_tex_text = namespace["formula_tex_text"]
    return Harness()


class GroupStructureSemanticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = semantic_harness()

    def test_square_composition_is_derived_and_closes_at_identity(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Groups and operations",
                "formula": r"(G,\cdot)",
                "worked_example": {
                    "setup": "Let G be rotations of a square by 0, 90, 180, and 270 degrees.",
                    "calculation": "90 degrees composed with 270 degrees gives 360 degrees, the identity rotation.",
                    "takeaway": "The result stays among the four rotations.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "rotation_composition")
        self.assertEqual(semantic["element_angles"], [0, 90, 180, 270])
        self.assertEqual((semantic["first_angle"], semantic["second_angle"]), (90, 270))
        self.assertEqual(semantic["total_angle"], 360)
        self.assertEqual(semantic["result_angle"], 0)
        self.assertTrue(semantic["closure"])

    def test_rotation_result_is_recomputed_instead_of_trusting_prose(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Triangle rotations",
                "formula": "R_a R_b",
                "worked_example": {
                    "setup": "Use rotations of a triangle by 0, 120, and 240 degrees.",
                    "calculation": "120 degrees then 120 degrees gives 999 degrees.",
                    "takeaway": "Composition remains a triangle rotation.",
                },
            }
        )

        self.assertEqual(semantic["total_angle"], 240)
        self.assertEqual(semantic["result_angle"], 240)
        self.assertTrue(semantic["closure"])

    def test_even_integer_subgroup_derives_ambient_subset_and_closure(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Subgroups",
                "formula": r"H\leq G",
                "worked_example": {
                    "setup": "In integers under addition, the even integers form a subgroup.",
                    "calculation": "Even + even is even, 0 is even, and the inverse of 2k is -2k.",
                    "takeaway": "The operation never leaves the subset.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "subgroup")
        self.assertEqual(semantic["ambient_label"], "Z")
        self.assertEqual(semantic["subset_label"], "2Z")
        self.assertEqual(semantic["operand_labels"], ["2a", "2b"])
        self.assertEqual(semantic["result_label"], "2(a+b)")

    def test_exact_coefficient_subgroup_uses_difference_geometry(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Subgroups",
                "formula": r"H\le G\iff H\ne\varnothing\text{ and }xy^{-1}\in H",
                "worked_example": {
                    "setup": "Test H=2Z inside the additive group (Z,+).",
                    "calculation": "For x=2a and y=2b, x-y=2(a-b) lies in 2Z.",
                    "takeaway": "Difference closure proves H is a subgroup.",
                },
            }
        )
        self.assertEqual(semantic["subset_label"], "2Z")
        self.assertEqual(semantic["subset_values"], ["-4", "-2", "0", "2", "4"])
        self.assertEqual(semantic["operation_symbol"], "-")
        self.assertEqual(semantic["result_label"], "2(a-b)")
        self.assertEqual(semantic["closure_result"], -6)
        self.assertIn(r"\in 2Z", semantic["closure_tex"])
        self.assertIn("0", semantic["subset_values"])
        self.assertNotIn("1", semantic["subset_values"])

    def test_multiples_subgroup_is_not_hard_coded_to_even_integers(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Subgroups",
                "formula": r"H\leq G",
                "worked_example": {
                    "setup": "The multiples of 5 in the integers form a subgroup under addition.",
                    "calculation": "A sum of two multiples of 5 is another multiple of 5.",
                    "takeaway": "Closure holds inside the subset.",
                },
            }
        )

        self.assertEqual(semantic["subset_label"], "5Z")
        self.assertEqual(semantic["operand_labels"], ["5a", "5b"])
        self.assertEqual(semantic["result_label"], "5(a+b)")

    def test_cyclic_modular_example_walks_generator_powers_to_identity(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Cyclic groups",
                "formula": r"G=\langle g\rangle",
                "worked_example": {
                    "setup": "In integers modulo 6 under addition, 1 generates every residue.",
                    "calculation": "0,1,2,3,4,5 appear as repeated additions of 1.",
                    "takeaway": "The next addition returns to 0.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "cyclic")
        self.assertEqual(semantic["states"], ["0", "1", "2", "3", "4", "5"])
        self.assertEqual(semantic["order"], 6)
        self.assertEqual(semantic["step_label"], "add 1 mod 6")
        self.assertIn(r"\pmod{6}", semantic["return_tex"])

    def test_rotation_order_builds_repeated_angle_states(self) -> None:
        semantic = self.scene.group_structure_semantics(
            {
                "concept": "Orders of elements",
                "formula": "g^n=e",
                "worked_example": {
                    "setup": "A rotation by 90 degrees has order 4.",
                    "calculation": "Four repeats give 360 degrees, the identity.",
                    "takeaway": "The first return occurs after four turns.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "cyclic")
        self.assertEqual(
            semantic["states"],
            ["0" + chr(176), "90" + chr(176), "180" + chr(176), "270" + chr(176)],
        )
        self.assertEqual(semantic["order"], 4)
        self.assertIn(r"90^{\circ}", semantic["return_tex"])

    def test_group_math_fallback_keeps_powers_and_spacing_readable(self) -> None:
        rendered = self.scene.group_plain_math("g^12 * h_2")

        self.assertEqual(rendered, "g" + chr(185) + chr(178) + " " + chr(183) + " h" + chr(8322))

    def test_collision_gate_rejects_a_route_through_occupied_bounds(self) -> None:
        occupied = [(1.0, 2.0, -0.5, 0.5), (3.0, 4.0, 0.75, 1.5)]

        self.assertFalse(self.scene.group_route_clear_of_bounds([(0.0, 0.0), (3.0, 0.0)], occupied))
        self.assertTrue(
            self.scene.group_route_clear_of_bounds(
                [(0.0, 1.8), (0.0, -1.0), (4.5, -1.0), (4.5, 1.8)],
                occupied,
            )
        )

    def test_transit_pathfinder_retains_endpoints_and_avoids_collisions(self) -> None:
        start = np.array([-2.5, 2.17, 0.0])
        end = np.array([-2.5, -2.1, 0.0])
        occupied = [(-3.7, -1.35, 0.39, 2.13), (-1.17, 1.17, -1.64, 0.12)]

        route = self.scene.group_collision_safe_transit_points(start, end, occupied)

        np.testing.assert_allclose(route[0], start)
        np.testing.assert_allclose(route[-1], end)
        self.assertGreaterEqual(len(route), 3)
        expanded = [
            (left - 0.02, right + 0.02, bottom - 0.02, top + 0.02)
            for left, right, bottom, top in occupied
        ]
        self.assertTrue(self.scene.group_route_clear_of_bounds(route, expanded))

    def test_group_actions_bind_only_first_stage_of_each_transform(self) -> None:
        actions = [lambda _run_time, index=index: index for index in range(4)]
        self.scene._semantic_hold_index = 0
        self.scene._beat_schedule = [
            {"duration": 2.0, "planned_arc_phase": "transform", "planned_state_first_stage": True},
            {"duration": 2.0, "planned_arc_phase": "transform", "planned_state_first_stage": False},
            {"duration": 2.0, "planned_arc_phase": "transform", "planned_state_first_stage": True},
            {"duration": 2.0, "planned_arc_phase": "transform", "planned_state_first_stage": True},
            {"duration": 2.0, "planned_arc_phase": "transform", "planned_state_first_stage": True},
        ]
        self.scene.semantic_action_batches = lambda prepared, holds: [[action] for action in prepared]

        self.scene.register_group_actions(actions)

        batches = self.scene._concept_motion["action_batches"]
        self.assertEqual(batches[1], [])
        self.assertTrue(all(batches[index] for index in (0, 2, 3, 4)))

    def test_group_actions_reserve_the_result_for_the_final_hold(self) -> None:
        actions = [lambda _run_time, index=index: index for index in range(4)]
        self.scene._semantic_hold_index = 0
        self.scene._beat_schedule = [{"duration": duration} for duration in (3.0, 1.0, 4.0, 2.0, 5.0)]
        self.scene.semantic_action_batches = lambda prepared, holds: [
            list(prepared[index::len(holds)]) for index in range(len(holds))
        ]

        self.scene.register_group_actions(actions)

        motion = self.scene._concept_motion
        self.assertTrue(motion["result_last"])
        self.assertEqual(motion["action_batches"][-1], [actions[-1]])
        self.assertNotIn(actions[-1], [action for batch in motion["action_batches"][:-1] for action in batch])

    def test_unicode_math_fallback_never_leaks_tex_commands(self) -> None:
        scene = formula_fallback_harness()
        examples = {
            r"S_n": "S" + chr(8333) + "n" + chr(8334),
            r"\tau\;\text{first}": chr(964),
            r"(\sigma\circ\tau)(1)=2": chr(8728),
            r"G/\ker\varphi\cong\operatorname{im}\varphi": chr(8773),
            r"\operatorname{Rot}(\square)\cong\mathbb{Z}/4\mathbb{Z}": chr(8484),
        }

        for source, expected in examples.items():
            rendered = scene.formula_fallback_text(source, source)
            self.assertIn(expected, rendered)
            self.assertIsNone(self.scene.group_math_residue(rendered), rendered)

    def test_unknown_math_command_blocks_instead_of_becoming_visible_text(self) -> None:
        scene = formula_fallback_harness()

        for source in (r"\unknown{q}", r"\integralish{x}", r"\sqcupish"):
            with self.subTest(source=source), self.assertRaisesRegex(RuntimeError, "cannot format command"):
                scene.formula_fallback_text(source, source)

    def test_structured_fallback_preserves_common_semantic_commands(self) -> None:
        scene = formula_fallback_harness()
        examples = {
            r"\mathbb{Z}=(0+H)\,\sqcup\,(1+H)\,\sqcup\,(2+H)": "ℤ = (0 + H) ⊔ (1 + H) ⊔ (2 + H)",
            r"A\cap B\subseteq A\cup B": "A ∩ B ⊆ A ∪ B",
            r"G=N\rtimes H": "G = N ⋊ H",
            r"x\notin A\Longrightarrow x\in A^{c}": "x ∉ A ⟹ x ∈ A⁽c⁾",
            r"\int_0^T F\cdot v\,dt": "∫₀⁽T⁾ F · v dt",
            r"\dot{x}\parallel v \land p\propto q": "ẋ ∥ v ∧ p ∝ q",
            r"n\to\infty": "n→∞",
        }

        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(scene.formula_fallback_text(source, source), expected)

    def test_math_residue_gate_does_not_match_phi_inside_ordinary_words(self) -> None:
        self.assertIsNone(self.scene.group_raw_math_source_residue("group actions and automorphisms"))
        self.assertIsNone(self.scene.group_math_residue("group actions and automorphisms"))
        self.assertIsNone(self.scene.group_raw_math_source_residue(r"\varphi(x)"))
        self.assertIsNotNone(self.scene.group_raw_math_source_residue("phi(x)"))

    def test_mod_six_cosets_are_equal_disjoint_and_form_the_quotient(self) -> None:
        semantic = self.scene.group_coset_semantics(
            {
                "concept": "Cosets and quotient groups",
                "formula": r"gH=\{gh:h\in H\}",
                "worked_example": {
                    "setup": "In integers modulo 6, take H = {0, 3}.",
                    "calculation": "The cosets are {0,3}, {1,4}, and {2,5}.",
                    "takeaway": "They partition the carrier.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "quotient")
        self.assertEqual(semantic["blocks"], [["0", "3"], ["1", "4"], ["2", "5"]])
        self.assertEqual(semantic["block_size"], 2)
        self.assertEqual(semantic["block_count"], 3)
        self.assertEqual(sorted(value for block in semantic["blocks"] for value in block), list("012345"))
        self.assertIn("G/H", semantic["result_tex"])

    def test_lagrange_semantics_construct_four_actual_three_element_cosets(self) -> None:
        semantic = self.scene.group_coset_semantics(
            {
                "concept": "Lagrange's theorem",
                "formula": r"|H|\mid |G|",
                "worked_example": {
                    "setup": "If a group has 12 elements and H has 3 elements.",
                    "calculation": "The left cosets of H form 12/3 = 4 blocks.",
                    "takeaway": "Equal coset blocks force divisibility.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "lagrange")
        self.assertEqual([len(block) for block in semantic["blocks"]], [3, 3, 3, 3])
        self.assertEqual(len({value for block in semantic["blocks"] for value in block}), 12)
        self.assertIn(r"[G:H]=4", semantic["result_tex"])
        self.assertIn(r"4\cdot 3=12", semantic["result_tex"])

    def test_normal_subgroup_semantics_make_left_and_right_cosets_coincide(self) -> None:
        semantic = self.scene.group_coset_semantics(
            {
                "concept": "Normal subgroups",
                "formula": "gH=Hg",
                "worked_example": {
                    "setup": "In any abelian group, every subgroup is normal.",
                    "calculation": "Because gh = hg, left and right cosets match.",
                    "takeaway": "The quotient operation is well defined.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "normal")
        self.assertEqual(semantic["blocks"], [["e", "h"], ["g", "gh"]])
        self.assertEqual(semantic["labels"][1], "gH = Hg")
        self.assertEqual(semantic["result_tex"], r"\forall g\in G,\quad gH=Hg")
        self.assertEqual(semantic["counterexample_context_tex"], r"K=\{e,(12)\}\leq S_3,\quad x=(123)")
        self.assertEqual(semantic["counterexample_left_tex"], r"xK=\{(123),(13)\}")
        self.assertEqual(semantic["counterexample_right_tex"], r"Kx=\{(123),(23)\}")
        self.assertEqual(semantic["counterexample_result_tex"], r"xK\ne Kx")

    def test_parity_homomorphism_derives_fibers_kernel_and_real_phi_tex(self) -> None:
        semantic = self.scene.group_homomorphism_semantics(
            {
                "concept": "Homomorphisms",
                "formula": r"\varphi(a+b)=\varphi(a)+\varphi(b)",
                "worked_example": {
                    "setup": "Map integers under addition to parity by phi(n)=n mod 2.",
                    "calculation": "phi(3+5)=0 and phi(3)+phi(5)=1+1=0 mod 2.",
                    "takeaway": "The map preserves addition.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "homomorphism")
        self.assertEqual(semantic["mapping"], {0: 0, 3: 1, 5: 1, 8: 0})
        self.assertEqual(semantic["fibers"], {0: [0, 8], 1: [3, 5]})
        self.assertIn(r"\varphi", semantic["map_tex"])
        self.assertIn(r"\mathbb{Z}/2\mathbb{Z}", semantic["target_label_tex"])

    def test_kernel_and_first_isomorphism_routes_keep_image_and_quotient_exact(self) -> None:
        kernel = self.scene.group_homomorphism_semantics(
            {
                "concept": "Kernels and images",
                "formula": r"\ker\varphi=\{g:\varphi(g)=e\}",
                "worked_example": {
                    "setup": "Parity maps integers to Z/2Z.",
                    "calculation": "All even integers map to 0, so they form the kernel.",
                    "takeaway": "The image has both parity values.",
                },
            }
        )
        first = self.scene.group_homomorphism_semantics(
            {
                "concept": "First isomorphism theorem",
                "formula": r"G/\ker\varphi\cong \operatorname{im}\varphi",
                "worked_example": {
                    "setup": "For the parity map from integers to Z/2Z, the kernel is even integers.",
                    "calculation": "Z/even integers has two cosets, matching the two parity outputs.",
                    "takeaway": "Collapsing the kernel gives the image structure.",
                },
            }
        )

        self.assertEqual(kernel["mode"], "kernel_image")
        self.assertEqual(kernel["kernel_values"], [-2, 0, 2])
        self.assertEqual(kernel["image_values"], [0, 1])
        self.assertEqual(first["mode"], "first_isomorphism")
        self.assertIn(r"/\ker\varphi\cong", first["result_tex"])
        self.assertIn(r"\operatorname{im}\varphi", first["result_tex"])

    def test_square_rotation_isomorphism_is_bijective_with_trivial_kernel(self) -> None:
        semantic = self.scene.group_homomorphism_semantics(
            {
                "concept": "Isomorphisms",
                "formula": r"G\cong H",
                "worked_example": {
                    "setup": "Map rotations of a square by multiples of 90 degrees to integers modulo 4.",
                    "calculation": "Composition of rotations matches addition modulo 4.",
                    "takeaway": "The operation tables agree.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "isomorphism")
        self.assertEqual(semantic["source_values"], ["0" + chr(176), "90" + chr(176), "180" + chr(176), "270" + chr(176)])
        self.assertEqual(list(semantic["mapping"].values()), [0, 1, 2, 3])
        self.assertEqual(semantic["kernel_values"], ["0" + chr(176)])
        self.assertIn(r"\cong", semantic["result_tex"])

    def test_permutation_composition_orders_move_vertex_one_differently(self) -> None:
        semantic = self.scene.group_action_semantics(
            {
                "concept": "Permutation groups",
                "formula": "S_n",
                "worked_example": {
                    "setup": "Let sigma swap 1 and 2, and tau send 2 to 3.",
                    "calculation": "Composing in opposite orders can move 1 to different places.",
                    "takeaway": "Order matters.",
                },
            }
        )

        self.assertEqual(semantic["mode"], "permutation_composition")
        self.assertEqual(semantic["sigma"], [1, 0, 2])
        self.assertEqual(semantic["tau"], [0, 2, 1])
        self.assertEqual(semantic["tau_then_sigma"], [1, 2, 0])
        self.assertEqual(semantic["sigma_then_tau"], [2, 0, 1])
        self.assertNotEqual(semantic["first_image_tau_then_sigma"], semantic["first_image_sigma_then_tau"])


class GroupSceneSourceTests(unittest.TestCase):
    def test_all_algebra_routes_reflow_phone_cues_including_field_of_fractions(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Field of Fractions", "group_theory"),
            17,
        )
        plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "FieldOfFractionsCueReflow", plan)

        compile(source, "generated_field_of_fractions_reflow.py", "exec")
        self.assertTrue(stem_course.algebra_phone_cue_reflow_enabled("algebra_fraction"))
        self.assertTrue(all(
            stem_course.algebra_phone_cue_reflow_enabled(kind)
            for kind in stem_course.ALGEBRA_VISUAL_KINDS
        ))
        self.assertIn(
            "algebra_phone_cue_reflow_enabled(visual_kind)",
            inspect.getsource(stem_course.manim_scene),
        )
        self.assertTrue(all(len(beat["cue_lines"]) <= 2 for beat in plan["beats"]))

    def test_generated_group_scene_uses_semantic_choreography(self) -> None:
        short = stem_course.concept_to_short(stem_course.GROUP_THEORY[0], 1)
        source = stem_course.manim_scene(short, "GroupVisualRegressionScene", stem_course.build_animation_plan(short))
        compile(source, "generated_group_scene.py", "exec")
        group_source = source[
            source.index("    def semantic_worked_parts") :
            source.index("    def algebra_factor_semantics")
        ]

        compile("class GroupVisualRegressionScene:\n" + group_source, "generated_group_scene.py", "exec")
        self.assertIn("play_group_rotation_structure", source)
        self.assertIn("group_vertex_marker", source)
        self.assertIn("Rotate(shape_ink", source)
        self.assertIn("register_group_actions(actions)", source)
        self.assertIn("MoveAlongPath", source)
        self.assertIn("group_formula_chip", source)
        self.assertIn("group_structured_atom", source)
        self.assertIn("group_atomic_update", source)
        self.assertIn("group_retire_proxy", source)
        self.assertIn("group_transit_path", source)
        self.assertIn("group_polyline_transit_path", source)
        self.assertIn("group_route_clear_of_bounds", source)
        self.assertIn("group_proxy_packet", source)
        self.assertIn("play_group_normality_visual", source)
        self.assertIn("group_display_formula", source)
        self.assertIn("group_lock_text_layer", source)
        self.assertIn('record.get("mob")', source)
        self.assertIn("register_group_actions", source)
        self.assertIn("SQUARE ROTATIONS", source)
        self.assertIn("rotate_square(first", source)
        self.assertIn('semantics["mode"] == "lagrange"', source)
        self.assertIn("outer_x = blocks.get_left()[0] - 0.34", group_source)
        self.assertIn("end = quotient_badges[index].get_center()", group_source)
        self.assertIn("packet_scale = 0.68 if lagrange_grid else 0.92", group_source)
        self.assertIn("self.add(quotient_badges)", group_source)
        self.assertIn("set_equation(identity, identity, identity", group_source)
        self.assertIn("inverse_result = semantics[\"identity_label\"]", group_source)
        self.assertNotIn("marker = source.copy().scale(0.78)", group_source)
        self.assertIn("safe_header_top", source)
        self.assertIn('slash + "forall g"', source)
        self.assertNotIn("\x08", source)
        self.assertNotIn("Transform(cue", group_source)
        self.assertNotIn("TransformFromCopy", group_source)
        self.assertNotIn(".become(", group_source)
        self.assertNotIn("self.remove(marker)", group_source)
        self.assertNotIn("self.remove(packet)", group_source)
        self.assertNotIn("Indicate(quotient_badges", group_source)
        self.assertNotIn("token = source.copy()", group_source)
        self.assertNotIn("range(order * 2)", group_source)
        self.assertNotIn("traveler = blocks[0].copy()", group_source)
        self.assertNotIn("LaggedStart(*[FadeIn(block", group_source)
        self.assertNotIn("FadeIn(caption)", group_source)
        self.assertNotIn("ReplacementTransform(second_label, equation)", source)
        self.assertNotIn("Indicate(result, color", source)
        self.assertNotIn("apply the worked operation", source)

    def test_fibonacci_opening_motion_is_deferred_to_planned_callbacks(self) -> None:
        short = stem_course.source_term_concept(
            "Memoization and Recursive Dynamic Programming",
            "algorithms",
        )
        payload = stem_course.concept_to_short(short, 14)
        source = stem_course.manim_scene(payload, "MemoizedOpeningScene", stem_course.build_animation_plan(payload))

        self.assertNotIn("intro_action(0.85)", source)
        self.assertIn("[intro_actions[ordinal - 1]]", source)

    def test_group_morphs_target_unlabeled_geometry_only(self) -> None:
        group_source = stem_course.MANIM_SCENE_HELPERS[
            stem_course.MANIM_SCENE_HELPERS.index("def semantic_worked_parts") :
            stem_course.MANIM_SCENE_HELPERS.index("def algebra_factor_semantics")
        ]
        tree = ast.parse(group_source)
        allowed_geometry = {
            "active_ring", "angle_cursor", "left_selector", "result_selector",
            "right_selector", "selector", "spoke", "tracker",
        }
        morph_targets = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in {"Transform", "ReplacementTransform", "TransformFromCopy"} or not node.args:
                continue
            target = node.args[0]
            morph_targets.append(target.id if isinstance(target, ast.Name) else ast.unparse(target))

        self.assertEqual(set(morph_targets), allowed_geometry)
        self.assertNotIn("title", morph_targets)
        self.assertNotIn("proof_header", morph_targets)
        self.assertNotIn("cue", morph_targets)


if __name__ == "__main__":
    unittest.main()

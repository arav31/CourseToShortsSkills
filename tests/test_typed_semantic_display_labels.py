import inspect
import unittest

from tools import stem_course
from tools.video_group_models import GROUP_VIDEO_ROUTES, build_group_video_payload


class TypedSemanticDisplayLabelTests(unittest.TestCase):
    def test_problematic_group_roles_are_bounded_without_lowering_font_floor(self):
        cases = {
            "ambient": "ambient integer line",
            "operation": "composition and closure check",
            "subgroup": "persistent subgroup being translated",
            "representative": "coset representative marker",
            "polynomial": "bounded polynomial congruence gate",
        }
        for leaf, role in cases.items():
            with self.subTest(role=role):
                lines = stem_course.bounded_semantic_display_label(role, f"course:route:{leaf}")
                self.assertLessEqual(len(lines), 2)
                self.assertTrue(all(len(line) <= 15 for line in lines))
                self.assertTrue(all(line.strip() for line in lines))

    def test_groups_operation_uses_stable_semantic_leaf_to_fit(self):
        self.assertEqual(
            stem_course.bounded_semantic_display_label(
                "composition and closure check", "modern_algebra:groups:operation"
            ),
            ("operation",),
        )

    def test_policy_compacts_human_role_then_uses_stable_id_leaf(self):
        self.assertEqual(
            stem_course.bounded_semantic_display_label("ambient integer line", "route:ambient"),
            ("ambient",),
        )
        self.assertEqual(
            stem_course.bounded_semantic_display_label(
                "persistent subgroup being translated", "route:subgroup"
            ),
            ("subgroup",),
        )
        self.assertEqual(
            stem_course.bounded_semantic_display_label(
                "bounded polynomial congruence gate", "route:polynomial"
            ),
            ("polynomial",),
        )

    def test_unbounded_machine_copy_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no readable bounded display label"):
            stem_course.bounded_semantic_display_label(
                "supercalifragilisticexpialidocious", "route:also_unreasonably_long"
            )

    def test_formula_bearing_group_setup_remains_within_two_readable_lines(self):
        lines = stem_course.simplified_scene_cue_lines(
            ["Let H = 3 Z in (Z, + ) and translate H by integer representatives."]
        )
        self.assertEqual(len(lines), 2)
        self.assertEqual(" ".join(lines), "Let H = 3 Z in (Z, + ) and translate H by integer representatives.")

    def test_physics_arrow_roles_fit_the_two_line_readable_floor(self):
        self.assertEqual(
            stem_course.bounded_semantic_display_label(
                "angular velocity arrow", "physics:rotation:angular_velocity_arrow"
            ),
            ("angular", "velocity"),
        )
        self.assertEqual(
            stem_course.bounded_semantic_display_label(
                "angular momentum arrow", "physics:rotation:angular_momentum_arrow"
            ),
            ("L vector",),
        )

    def test_homomorphisms_and_kernels_uses_exact_readable_presentation_labels(self):
        payload = build_group_video_payload("Homomorphisms and Kernels")
        expected = {
            "domain": ("domain",),
            "codomain": ("codomain",),
            "map": ("map",),
            "kernel": ("kernel",),
            "image": ("image",),
        }
        for row in payload["objects"]:
            leaf = str(row["id"]).rsplit(":", 1)[-1]
            with self.subTest(role=row["role"]):
                self.assertEqual(
                    stem_course.bounded_semantic_display_label(row["role"], row["id"]),
                    expected[leaf],
                )

    def test_finite_map_kernel_marks_only_authored_member_indices(self):
        payload = build_group_video_payload("Homomorphisms and Kernels")
        geometry = payload["render_geometry"]
        self.assertEqual(geometry["kernel_indices"], [0, 2, 4, 6])
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index("def play_finite_map_semantic_contract"):
            source.index("def play_typed_semantic_contract")
        ]
        self.assertIn("for index in kernel_indices", renderer)
        self.assertIn("domain[index], color=\"#A371F7\"", renderer)
        self.assertNotIn("kernel_members = VGroup", renderer)

    def test_finite_map_image_reveal_conserves_callback_budget(self):
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index("def play_finite_map_semantic_contract"):
            source.index("def play_typed_semantic_contract")
        ]
        self.assertIn(
            "arrow_run_time, image_run_time = self.semantic_timed_segments",
            renderer,
        )
        self.assertIn("run_time=image_run_time", renderer)
        self.assertNotIn("run_time * 0.12", renderer)

    def test_safe_place_supports_horizontal_centers_without_breaking_callers(self):
        source = stem_course.MANIM_SCENE_HELPERS
        signature = source[source.index("def safe_place"):source.index("def clamp_to_safe_frame")]
        self.assertIn("remember=True, *, x=0", signature)
        self.assertIn("mob.move_to(RIGHT * x + UP * y)", signature)

    def test_finite_map_renderer_fails_closed_before_constructing_bad_geometry(self):
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index("def play_finite_map_semantic_contract"):
            source.index("def play_typed_semantic_contract")
        ]
        self.assertIn("Finite-map {field} rows must be mappings", renderer)
        self.assertIn("mapping target is outside", renderer)
        self.assertIn('requirement = "a nonempty index sequence"', renderer)
        self.assertIn("list(range(min(2, len(mapping))))", renderer)
        registration = renderer.index("self.register_semantic_transition_actions(")
        guard = renderer.index("self._typed_semantic_route_key = route_key")
        self.assertGreater(guard, registration)

    def test_every_mit_group_role_has_shell_safe_presentation_copy(self):
        for route in GROUP_VIDEO_ROUTES:
            payload = build_group_video_payload(route.title)
            for row in payload["objects"]:
                with self.subTest(title=route.title, role=row["role"]):
                    lines = stem_course.bounded_semantic_display_label(
                        row["role"], row["id"]
                    )
                    self.assertLessEqual(len(lines), 2)
                    self.assertTrue(all(0 < len(line) <= 10 for line in lines))

    def test_generated_scene_embeds_policy_and_semantic_identity_metadata(self):
        source = stem_course.MANIM_SCENE_HELPERS
        self.assertIn("bounded_semantic_display_label(canonical_role, semantic_object_id)", source)
        self.assertIn("label._course_semantic_object_id = semantic_object_id", source)
        self.assertIn("mob._course_semantic_role = canonical_role", source)
        self.assertIn("font_size=38", source)
        self.assertIn("max_height=1.18", source)
        self.assertIn("height=1.62", source)
        self.assertIn("UP * 2.75", source)
        self.assertIn("DOWN * 2.75", source)
        self.assertIn('fill_color="#0B1020"', source)
        self.assertIn("fill_opacity=1.0", source)
        self.assertIn("links.set_z_index(0)", source)
        self.assertIn('self.register_portrait_role("core_proof", proof_canvas', source)
        self.assertIn("self.register_proof_surface(proof_canvas)", source)
        self.assertIn("MoveAlongPath(tracer", source)
        self.assertIn("ShowPassingFlash", source)
        self.assertNotIn("Indicate(nodes[object_id]", source)
        self.assertNotIn("Transform(self._typed_semantic_state", source)
        self.assertNotIn("FadeOut(old_state),\n                        FadeIn(next_state)", source)
        self.assertEqual(
            stem_course.renderer_source_fingerprint_payload()["semantic_display_label_policy"],
            inspect.getsource(stem_course.bounded_semantic_display_label),
        )
        self.assertIn(
            "{inspect.getsource(bounded_semantic_display_label)}",
            inspect.getsource(stem_course.manim_scene),
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from tools import stem_course


class GroupExactRouteVisualTests(unittest.TestCase):
    def scene_for(self, title: str, index: int) -> tuple[dict, dict, str]:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept(title, "group_theory"), index
        )
        plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "ExactGroupVisualScene", plan)
        compile(source, "generated_exact_group_visual.py", "exec")
        return short, plan, source

    def test_cosets_uses_integer_partition_route_and_all_events(self) -> None:
        _, plan, source = self.scene_for("Cosets", 3)
        route = "modern_algebra:mit_18_703:cosets_of_3z"
        self.assertEqual(plan["semantic_support"]["route_key"], route)
        self.assertEqual(
            stem_course.VIDEO_RENDERER_IMPLEMENTATIONS[route]["dispatcher"],
            "group:cosets_integer_partition",
        )
        self.assertIn("self.play_cosets_integer_partition(group_payload)", source)
        self.assertIn(r"0+H=3\mathbb{Z}=\{3k\}", source)
        self.assertIn(r"1+H=\{3k+1\}", source)
        self.assertIn(r"2+H=\{3k+2\}", source)
        self.assertIn(r"\mathbb{Z}=(0+H)\,\sqcup\,(1+H)\,\sqcup\,(2+H)", source)
        self.assertIn(r"C_r=r+H,\qquad C_i\cap C_j=\emptyset\quad(i\ne j)", source)
        self.assertIn("exact_group_proof_canvas", source)
        self.assertIn('"fix_subgroup": fix_subgroup', source)
        self.assertIn('"identity_coset": identity_coset', source)
        self.assertIn('"other_cosets": other_cosets', source)
        self.assertIn('"partition": resolve_partition', source)
        self.assertIn("def build_coset_hook(run_time)", source)
        self.assertIn("build_actions=[build_coset_hook]", source)
        self.assertIn("resolve_actions=[resolve_coset_takeaway]", source)
        self.assertIn('"carrier_type": "progressive_draw"', source)
        self.assertNotIn("self.play(FadeIn(ambient), FadeIn(ambient_label), FadeIn(subgroup_formula), run_time=0.9)", source)
        self.assertIn("rows.arrange(DOWN, buff=0.22)", source)
        self.assertIn('lane_height = float(contract["lane_height"])', source)
        self.assertIn('float(contract["min_occupied_row_ratio"])', source)
        self.assertIn('float(contract["max_height_occupancy"])', source)
        self.assertIn("complete[0].stretch_to_fit_height(card_height)", source)
        self.assertNotIn("2.35 - float(ambient.get_center()", source)
        self.assertNotIn("-1.62 - float(rows.get_center()", source)
        self.assertIn('self.group_lock_text_layer(rows, "coset row formulas")', source)
        self.assertIn('self.group_lock_text_layer(subgroup_formula, "subgroup formula")', source)
        self.assertIn('self.group_lock_text_layer(formula, "canonical formula")', source)
        self.assertIn('if not getattr(self, "_preserve_composed_final_frame", False):', source)
        self.assertIn("self._preserve_composed_final_frame = True", source)
        self.assertIn("rows[0].set_opacity(1.0)", source)
        self.assertNotIn("rows[0].animate.set_opacity(1.0)", source)
        self.assertNotIn("FadeOut(shift_zero)", source)
        self.assertNotIn("row_outlines =", source)
        self.assertNotIn("Indicate(subgroup_formula", source)
        self.assertNotIn("Circumscribe(rows[", source)
        self.assertIn("Translated copies of H either", source)
        self.assertIn("Translate the same subgroup without", source)
        bindings = stem_course.render_runtime_semantic_transition_bindings(plan)
        self.assertEqual(len(bindings), 4)
        self.assertEqual(len({row["planned_transition_id"] for row in bindings}), 4)

    def test_group_axioms_use_persistent_triangle_motion(self) -> None:
        _, plan, source = self.scene_for("Groups", 1)
        self.assertIn("self.play_group_axioms_contract(group_payload)", source)
        for suffix in ("closure", "identity", "inverse", "associativity"):
            self.assertIn(f'"{suffix}": {suffix}', source)
        self.assertIn("Rotate(VGroup(triangle, orientation)", source)
        self.assertIn("MoveAlongPath(left_token, left_path)", source)
        self.assertIn("LaggedStart(*[Create(arc) for arc in axiom_arcs]", source)
        self.assertIn("All four axioms hold: G is a group", source)
        self.assertEqual(len(stem_course.render_runtime_semantic_transition_bindings(plan)), 4)

    def test_subgroup_and_cyclic_routes_bind_rich_geometry_to_exact_events(self) -> None:
        _, subgroup_plan, subgroup_source = self.scene_for("Subgroups", 2)
        self.assertIn("group_exact_semantic_data(group_payload)", subgroup_source)
        self.assertIn('"difference": difference_action', subgroup_source)
        self.assertIn(r'H=2\mathbb{Z}\subset\mathbb{Z}', subgroup_source)
        self.assertIn(r'2\mathbb{Z}\le\mathbb{Z}', subgroup_source)
        self.assertEqual(len(stem_course.render_runtime_semantic_transition_bindings(subgroup_plan)), 4)

        _, cyclic_plan, cyclic_source = self.scene_for("Cyclic Groups", 4)
        self.assertIn('"advance": advance_orbit', cyclic_source)
        self.assertIn('"return": advance_once', cyclic_source)
        self.assertIn("MoveAlongPath(tracer, sweep)", cyclic_source)
        self.assertIn("group_composite_action", cyclic_source)
        self.assertEqual(len(stem_course.render_runtime_semantic_transition_bindings(cyclic_plan)), 4)

    def test_primality_uses_dynamic_math_route_and_all_events(self) -> None:
        _, plan, source = self.scene_for("A Quick Primality Test", 22)
        route = "modern_algebra:mit_18_703:aks_primality_steps"
        self.assertEqual(plan["semantic_support"]["route_key"], route)
        self.assertEqual(
            stem_course.VIDEO_RENDERER_IMPLEMENTATIONS[route]["dispatcher"],
            "group:aks_primality",
        )
        self.assertIn("self.play_aks_primality_visual(group_payload)", source)
        self.assertIn("def build_aks_hook(run_time)", source)
        self.assertIn("build_actions=[build_aks_hook]", source)
        self.assertIn("resolve_actions=[resolve_aks_takeaway]", source)
        self.assertNotIn("self.play(FadeIn(candidate), Create(gate_frame), FadeIn(gates), FadeIn(work), run_time=0.9)", source)
        self.assertIn(r"b=2:\ \{2^2,3^2,4^2,5^2\}=\{4,9,16,25\}", source)
        self.assertIn(r"b=3:\ \{2^3,3^3\}=\{8,27\}", source)
        self.assertIn(r'(r"b=4:\quad 2^4=16", r"b\ge5:\quad 2^b\ge32>31")', source)
        self.assertIn("minimum_evidence_line_height = float(phone_line_reference.height) * 0.92", source)
        self.assertIn("Primality evidence card scaling violated the minimum line height", source)
        self.assertIn(r"31\notin\{4,8,9,16,25,27\}", source)
        self.assertIn(r"\operatorname{ord}_{29}(31)=28>(\log_2 31)^2", source)
        self.assertIn(r"\gcd(a,31)=1\quad(2\le a\le29)", source)
        self.assertIn(r"(X+a)^{31}=X^{31}+a", source)
        self.assertIn(r"(\mathbb{Z}/31\mathbb{Z})[X]/(X^{29}-1)", source)
        self.assertIn(r"\text{in }(\mathbb{Z}/31\mathbb{Z})[X]/(X^{29}-1)", source)
        self.assertNotIn(r'r"\pmod{31,\ X^{29}-1}"', source)
        self.assertNotIn('math_panel("log_2 31', source)
        self.assertIn('"power_gate": power_gate', source)
        self.assertIn('"choose_r": choose_r', source)
        self.assertIn('"gcd_gate": gcd_gate', source)
        self.assertIn('"polynomial_gate": polynomial_gate', source)
        self.assertIn("status_slot = VGroup(status_frame, status)", source)
        self.assertIn("Can four algebraic gates certify", source)
        self.assertIn("At r = 29, the order 28 exceeds", source)
        self.assertNotIn("Indicate(candidate", source)
        self.assertIn("self.play(DrawBorderThenFill(work), run_time=evidence_time)", source)
        for callback in ("power_gate", "choose_r", "gcd_gate", "polynomial_gate"):
            with self.subTest(callback=callback):
                marker = callback + '._semantic_motion_metadata = {"carrier_type": "progressive_draw"}'
                self.assertIn(marker, source)
        bindings = stem_course.render_runtime_semantic_transition_bindings(plan)
        self.assertEqual(len(bindings), 4)
        self.assertEqual(len({row["planned_transition_id"] for row in bindings}), 4)

    def test_exact_transition_map_fails_closed(self) -> None:
        helper = stem_course.MANIM_SCENE_HELPERS[
            stem_course.MANIM_SCENE_HELPERS.index("def group_exact_transition_map") :
            stem_course.MANIM_SCENE_HELPERS.index("def play_cosets_integer_partition")
        ]
        self.assertIn("must implement every semantic transition", helper)
        self.assertIn("unbound or duplicate transition", helper)
        self.assertIn("unused transition action", helper)
        self.assertIn("lacks a supported visual carrier", helper)
        self.assertIn('transition.get("changed_object_ids", [])', helper)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import textwrap
import unittest

from tools import stem_course


def sphere_harness():
    namespace = {"math": math}
    source = stem_course.MANIM_SCENE_HELPERS[
        stem_course.MANIM_SCENE_HELPERS.index("def sphere_projection_semantics") :
        stem_course.MANIM_SCENE_HELPERS.index("def play_sphere_surface_area_visual")
    ]
    exec(source, namespace)

    class Harness:
        pass

    Harness.sphere_projection_semantics = namespace["sphere_projection_semantics"]
    Harness.sphere_band_geometry = namespace["sphere_band_geometry"]
    return Harness()


def sphere_short() -> dict[str, object]:
    return {
        "index": 1,
        "concept": "Surface area of a sphere",
        "hook": "Why does every sphere have area four times its circular shadow?",
        "intuition": "Radially project tiny latitude patches onto the enclosing cylinder.",
        "formula": r"A=4\pi R^2",
        "plain_formula": "A equals 4 pi R squared",
        "visual_type": "sphere_surface_area",
        "worked_example": {
            "setup": "Put a sphere of radius R inside a cylinder of radius R and height 2R.",
            "calculation": "A patch widens by R/d and shortens by d/R, so its area is unchanged.",
            "takeaway": "Unwrap the cylinder side into a 2 pi R by 2R rectangle.",
        },
    }


class SphereProjectionGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = sphere_harness()

    def test_reciprocal_patch_scales_preserve_area(self) -> None:
        semantics = self.scene.sphere_projection_semantics(
            {"geometry": {"representative_d_over_R": 0.64}}
        )

        self.assertAlmostEqual(semantics["width_stretch"], 1 / 0.64)
        self.assertAlmostEqual(semantics["height_squish"], 0.64)
        self.assertAlmostEqual(semantics["area_scale"], 1.0)
        self.assertAlmostEqual(
            semantics["d_over_R"] ** 2 + semantics["y_over_R"] ** 2,
            1.0,
        )

    def test_every_latitude_band_has_unit_projection_area_scale(self) -> None:
        bands = self.scene.sphere_band_geometry(3.0, 18)

        self.assertEqual(len(bands), 18)
        self.assertTrue(all(band["d"] > 0 for band in bands))
        self.assertTrue(all(abs(band["area_scale"] - 1.0) < 1e-9 for band in bands))
        self.assertTrue(
            all(
                abs(band["surface_height"] * band["height_squish"] - band["projected_height"]) < 1e-9
                for band in bands
            )
        )
        self.assertTrue(
            all(abs(band["sphere_band_area"] - band["cylinder_band_area"]) < 1e-9 for band in bands)
        )
        self.assertTrue(all(bands[index]["y"] < bands[index + 1]["y"] for index in range(17)))

    def test_band_geometry_rejects_a_zero_radius(self) -> None:
        with self.assertRaisesRegex(ValueError, "radius must be positive"):
            self.scene.sphere_band_geometry(0, 12)

    def test_visual_data_requests_coarse_to_fine_projection(self) -> None:
        data = stem_course.visual_data_for(sphere_short(), "sphere_surface_area")

        self.assertEqual(data["visual_kind"], "sphere_surface_area")
        self.assertEqual(data["geometry"]["radius_label"], "R")
        self.assertEqual(data["geometry"]["coarse_band_count"], 6)
        self.assertEqual(data["geometry"]["fine_band_count"], 12)
        self.assertEqual(data["geometry"]["family"], "sphere_surface_area")
        self.assertEqual(len(data["geometry"]["objects"]), 7)
        self.assertEqual(len(data["geometry"]["transitions"]), 10)

    def test_geometry_payload_has_exact_chained_transition_contract(self) -> None:
        geometry = stem_course.visual_data_for(sphere_short(), "sphere_surface_area")["geometry"]
        transitions = geometry["transitions"]

        self.assertEqual(
            [transition["kind"] for transition in transitions],
            [
                "coarse_bands", "refine_bands", "project_bands", "magnify_patch",
                "stretch_width", "squish_height", "cancel_scales", "unwrap",
                "label_dimensions", "area_identity",
            ],
        )
        states = {row["id"]: row["initial_state"] for row in geometry["objects"]}
        for transition in transitions:
            self.assertEqual(set(transition["before"]), set(transition["after"]))
            self.assertEqual(
                transition["before"],
                {object_id: states[object_id] for object_id in transition["before"]},
            )
            states.update(transition["after"])

    def test_semantic_formula_sources_have_real_tex_and_deliberate_unicode_fallbacks(self) -> None:
        data = stem_course.visual_data_for(sphere_short(), "sphere_surface_area")
        semantics = self.scene.sphere_projection_semantics(data)

        self.assertEqual(semantics["formula_sources"]["width_factor"], r"\times\frac{R}{d}")
        self.assertEqual(semantics["formula_sources"]["height_factor"], r"\times\frac{d}{R}")
        self.assertEqual(
            semantics["formula_sources"]["cancellation"],
            r"\frac{R}{d}\cdot\frac{d}{R}=1",
        )
        self.assertEqual(
            semantics["formula_sources"]["full_result"],
            r"A=(2\pi R)(2R)=4\pi R^2",
        )
        self.assertEqual(semantics["formula_fallbacks"]["width_factor"], "× R⁄d")
        self.assertEqual(semantics["formula_fallbacks"]["height_factor"], "× d⁄R")
        self.assertEqual(
            semantics["formula_fallbacks"]["full_result"],
            "A = (2πR)(2R) = 4πR²",
        )
        visible_fallbacks = " ".join(semantics["formula_fallbacks"].values())
        self.assertNotIn("(R)/(d)", visible_fallbacks)
        self.assertNotIn("(d)/(R)", visible_fallbacks)
        self.assertNotIn("R^2", visible_fallbacks)

    def test_visual_state_sequence_is_complete_and_causal(self) -> None:
        semantics = self.scene.sphere_projection_semantics(
            stem_course.visual_data_for(sphere_short(), "sphere_surface_area")
        )

        self.assertEqual(
            semantics["visual_state_sequence"],
            [
                "coarse_latitude_bands",
                "fine_latitude_bands",
                "radial_band_projection",
                "magnified_surface_patch",
                "width_stretch_R_over_d",
                "height_squish_d_over_R",
                "reciprocal_factor_cancellation",
                "single_surface_unwrap",
                "rectangle_dimensions",
                "final_area_identity",
            ],
        )

    def test_proof_geometry_meets_phone_occupancy_contract(self) -> None:
        semantics = self.scene.sphere_projection_semantics(
            stem_course.visual_data_for(sphere_short(), "sphere_surface_area")
        )
        proof_width_ratio = (2 * 2.38) / 9.0
        patch_pair_width_ratio = (
            (1.72 + 1.08 * semantics["width_stretch"]) - (-2.48 - 1.08)
        ) / 9.0

        self.assertGreaterEqual(
            proof_width_ratio,
            semantics["proof_object_min_frame_width_ratio"],
        )
        self.assertGreaterEqual(
            patch_pair_width_ratio,
            semantics["patch_pair_min_frame_width_ratio"],
        )

    def test_semantic_plan_has_exact_assignments_windows_and_runtime_contract(self) -> None:
        short = sphere_short()
        beats = stem_course.canonical_beat_schedule(short)
        pacing = stem_course.short_video_pacing(short)
        plan = stem_course.build_animation_plan(short)
        transform_beats = [beat for beat in plan["beats"] if beat["semantic_transition_ids"]]
        runtime_contracts = [
            contract for contract in stem_course.render_runtime_transition_contracts(plan)
            if str(contract["planned_transition_id"]).startswith("sphere:")
        ]

        duration_profile = stem_course.semantic_duration_profile(short)
        self.assertGreater(duration_profile["object_construction_seconds"], 0)
        self.assertGreater(duration_profile["formula"]["seconds"], 0)
        self.assertGreater(duration_profile["visual_action_seconds"], 0)
        self.assertGreater(pacing["total"], 32.57)
        takeaway_beats = [beat for beat in beats if beat["scene_state"] == "example_takeaway"]
        self.assertEqual(len(takeaway_beats), 1)
        self.assertAlmostEqual(pacing["total"], sum(float(beat["duration"]) for beat in beats), places=2)
        self.assertEqual([len(beat["semantic_transition_ids"]) for beat in transform_beats], [2, 2, 3, 3])
        self.assertEqual(
            [beat["scene_state"] for beat in transform_beats],
            ["core_formula", "core_idea", "example_setup", "example_calculation"],
        )
        windows = [window for beat in transform_beats for window in beat["evidence"]["transition_windows"]]
        self.assertEqual(len(windows), 10)
        self.assertTrue(all(window["before_seconds"] < window["after_seconds"] for window in windows))
        for beat in transform_beats:
            beat_windows = beat["evidence"]["transition_windows"]
            self.assertEqual(
                [window["planned_transition_id"] for window in beat_windows],
                beat["semantic_transition_ids"],
            )
            self.assertTrue(all(
                left["after_seconds"] == right["before_seconds"]
                for left, right in zip(beat_windows, beat_windows[1:])
            ))
        self.assertEqual(
            [contract["planned_transition_id"] for contract in runtime_contracts],
            [window["planned_transition_id"] for window in windows],
        )
        self.assertEqual(
            [(contract["before_seconds"], contract["after_seconds"]) for contract in runtime_contracts],
            [(window["before_seconds"], window["after_seconds"]) for window in windows],
        )
        self.assertTrue(all(float(beat["duration"]) >= float(beat["read_seconds"]) for beat in beats))
        self.assertEqual(
            stem_course.planned_duration_sync(pacing["total"], pacing["total"])["status"],
            "ok",
        )


class SphereSceneSourceTests(unittest.TestCase):
    def sphere_route(self) -> tuple[str, str]:
        short = sphere_short()
        source = stem_course.manim_scene(
            short,
            "SphereSurfaceAreaBenchmark",
            stem_course.build_animation_plan(short),
        )
        route_start = source.index("    def play_sphere_surface_area_visual(")
        route_end = source.index("    def semantic_example_text(", route_start)
        sphere_route = source[route_start:route_end]
        compile(textwrap.dedent(sphere_route), "generated_sphere_route.py", "exec")
        return source, sphere_route

    def test_scene_contains_the_full_geometric_argument(self) -> None:
        source, sphere_route = self.sphere_route()

        action_names = [
            "coarse_bands",
            "refine_bands",
            "project_bands",
            "magnify_patch",
            "stretch_patch_width",
            "squish_patch_height",
            "cancel_patch_scales",
            "unwrap_cylinder_surface",
            "label_dimensions",
            "reveal_area_identity",
        ]
        for action_name in action_names:
            self.assertIn(f"def {action_name}(run_time):", sphere_route)
        action_positions = [sphere_route.index(f"def {name}(run_time):") for name in action_names]
        self.assertEqual(action_positions, sorted(action_positions))

        self.assertIn("self.register_semantic_transition_actions(", sphere_route)
        self.assertIn("tail_actions=resolve_surface_area", sphere_route)
        for transition_id in (
            "sphere:coarse-bands", "sphere:refine-bands", "sphere:project-bands",
            "sphere:magnify-patch", "sphere:stretch-width", "sphere:squish-height",
            "sphere:cancel-scales", "sphere:unwrap", "sphere:label-dimensions",
            "sphere:area-identity",
        ):
            self.assertIn(f'"{transition_id}":', sphere_route)
        self.assertIn("ReplacementTransform(coarse_rings, fine_rings)", sphere_route)
        self.assertIn("TransformFromCopy(selected_surface_patch, source_patch)", sphere_route)
        self.assertIn("TransformFromCopy(source_patch, target_patch)", sphere_route)
        self.assertIn("Transform(target_patch, wide_target_patch)", sphere_route)
        self.assertIn("Transform(target_patch, projected_target_patch)", sphere_route)
        self.assertIn('MathTex(tex_source, font_size=font_size, color=color)', sphere_route)
        self.assertIn('sphere_math("width_factor"', sphere_route)
        self.assertIn('sphere_math("height_factor"', sphere_route)
        self.assertIn("cancel_slashes = VGroup", sphere_route)
        self.assertIn("Transform(cylinder_surface, flat_surface)", sphere_route)
        self.assertIn("cylinder_surface = VGroup(cylinder_body, cylinder_bands)", sphere_route)
        self.assertIn("flat_surface = VGroup(flat_outline, flat_bands)", sphere_route)
        self.assertIn('sphere_math(\n            "circumference"', sphere_route)
        self.assertIn('sphere_math(\n            "area_product"', sphere_route)
        self.assertIn('sphere_math(\n            "final_result"', sphere_route)
        self.assertIn("persistent_visuals.get_family()", sphere_route)
        self.assertIn("derivation_group = VGroup(area_product, final_formula)", sphere_route)
        self.assertIn("quad_patch", sphere_route)
        self.assertIn("selected_surface_patch", sphere_route)
        self.assertIn("fine_rings", sphere_route)
        self.assertIn("cylinder_bands", sphere_route)
        self.assertIn("sphere,", sphere_route)
        self.assertNotIn("projection_probes", source)
        self.assertNotIn("mini_geometry", sphere_route)
        self.assertNotIn("source_area", sphere_route)
        self.assertNotIn("target_area", sphere_route)
        self.assertNotIn("FadeOut(sphere", sphere_route)
        self.assertNotIn("FadeOut(fine_rings", sphere_route)
        self.assertNotIn("MoveAlongPath(selected_cylinder_patch", sphere_route)
        self.assertNotIn("ReplacementTransform(area_product", sphere_route)
        self.assertNotIn("self._beat_schedule =", sphere_route)
        self.assertNotIn("hidden_text_block", sphere_route)
        self.assertNotIn("finished_sphere_story", sphere_route)
        self.assertNotIn("self.play_example_visual =", sphere_route)
        self.assertNotIn("self.is_text_like =", sphere_route)

    def test_result_formula_is_revealed_only_by_the_last_action(self) -> None:
        _source, sphere_route = self.sphere_route()
        resolve_start = sphere_route.index("def reveal_area_identity(run_time):")
        actions_start = sphere_route.index("transition_actions = {", resolve_start)
        resolve_source = sphere_route[resolve_start:actions_start]
        before_resolve = sphere_route[:resolve_start]

        self.assertIn("self.formula_block = sphere_result_last_formula_block", before_resolve)
        self.assertEqual(sphere_route.count("FadeIn(final_formula)"), 1)
        self.assertEqual(sphere_route.count("FadeIn(area_product"), 1)
        self.assertIn("FadeIn(area_product", resolve_source)
        self.assertIn("FadeIn(final_formula)", resolve_source)
        self.assertLess(
            resolve_source.index("FadeIn(area_product"),
            resolve_source.index("FadeIn(final_formula)"),
        )
        self.assertNotIn("FadeIn(final_formula)", before_resolve)
        self.assertNotIn("FadeIn(area_product", before_resolve)

    def test_unwrap_has_no_label_morph_or_per_band_ghost_path(self) -> None:
        _source, sphere_route = self.sphere_route()
        unwrap_start = sphere_route.index("def unwrap_cylinder_surface(run_time):")
        resolve_start = sphere_route.index("def label_dimensions(run_time):", unwrap_start)
        unwrap_source = sphere_route[unwrap_start:resolve_start]

        self.assertIn("Transform(cylinder_surface, flat_surface)", unwrap_source)
        self.assertIn("Transform(seam, seam_target)", unwrap_source)
        self.assertNotIn("Transform(cylinder_bands", unwrap_source)
        self.assertNotIn("LaggedStart", unwrap_source)
        self.assertNotIn("Text(", unwrap_source)
        self.assertNotIn("label.animate", unwrap_source)
        self.assertNotIn("cylinder_label", sphere_route)

    def test_renderer_records_occupancy_and_complete_visual_sequence(self) -> None:
        _source, sphere_route = self.sphere_route()

        self.assertIn("R = 2.38", sphere_route)
        self.assertIn("flat_width = 6.7", sphere_route)
        self.assertIn("self._sphere_proof_object_width_ratio", sphere_route)
        self.assertIn("self._sphere_patch_pair_width_ratio", sphere_route)
        self.assertIn("self._sphere_visual_state_sequence", sphere_route)

    def test_visible_formula_paths_exclude_raw_pseudo_math(self) -> None:
        _source, sphere_route = self.sphere_route()

        self.assertNotIn("(R)/(d)", sphere_route)
        self.assertNotIn("(d)/(R)", sphere_route)
        self.assertNotIn('Text("A=4', sphere_route)
        self.assertNotIn('Text("width x', sphere_route)
        self.assertNotIn('Text("height x', sphere_route)
        self.assertNotIn("self.formula_atom(", sphere_route)


if __name__ == "__main__":
    unittest.main()

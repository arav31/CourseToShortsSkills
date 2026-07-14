from __future__ import annotations

import unittest
import math
import re
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools import audit_video_frames, stem_course


WIDTH = 180
HEIGHT = 320
BACKGROUND = 8


def blank_frame() -> bytearray:
    return bytearray([BACKGROUND]) * (WIDTH * HEIGHT)


def paint_outline(
    pixels: bytearray,
    left: int,
    top: int,
    right: int,
    bottom: int,
    value: int = 220,
    thickness: int = 3,
) -> None:
    for y in range(top, bottom):
        for x in range(left, right):
            if (
                x < left + thickness
                or x >= right - thickness
                or y < top + thickness
                or y >= bottom - thickness
            ):
                pixels[y * WIDTH + x] = value


def paint_cross(pixels: bytearray, value: int = 220) -> None:
    for x in range(12, 168):
        pixels[152 * WIDTH + x] = value
    for y in range(74, 230):
        pixels[y * WIDTH + 90] = value


class PortraitProofSurfaceSolverTests(unittest.TestCase):
    def test_contract_exposes_bounded_cross_domain_role_lanes(self) -> None:
        roles = stem_course.PORTRAIT_PROOF_SURFACE_CONTRACT["roles"]
        self.assertEqual(roles["title"], {"bottom": 6.45, "top": 7.55})
        self.assertEqual(roles["cue_formula"], {"bottom": 4.75, "top": 6.25})
        self.assertEqual(roles["core_proof"], {"bottom": -4.20, "top": 4.50})
        self.assertEqual(roles["evidence"], {"bottom": -6.35, "top": -4.45})
        self.assertAlmostEqual(stem_course.PORTRAIT_PROOF_SURFACE_CONTRACT["lane_width"], 8.1)
        self.assertEqual(
            set(stem_course.PROOF_SURFACE_ROLE_REGISTRY.values()),
            {"core_proof"},
        )

    def test_feasible_core_is_solved_without_attached_label_bounds(self) -> None:
        result = stem_course.proof_surface_layout(6.7, 6.5, "economics")

        self.assertFalse(result["requires_reflow"])
        self.assertTrue(result["minimum_satisfied"])
        self.assertTrue(result["maximum_satisfied"])
        self.assertFalse(result["labels_included_in_bounds"])
        self.assertEqual(result["measured_region"], "core_proof")
        self.assertGreaterEqual(result["area_occupancy"], 0.48)

    def test_wide_core_requires_reflow_instead_of_false_uniform_success(self) -> None:
        result = stem_course.proof_surface_layout(7.2, 2.8, "physics")

        self.assertTrue(result["requires_reflow"])
        self.assertFalse(result["minimum_satisfied"])
        self.assertTrue(result["maximum_satisfied"])


class RuntimeProofSurfaceTransactionTests(unittest.TestCase):
    class Mob:
        def __init__(self, width: float, height: float, *, visible: bool = True) -> None:
            self.width = width
            self.height = height
            self.center = np.zeros(3)
            self.visible = visible
            self.children: list[RuntimeProofSurfaceTransactionTests.Mob] = []

        def family_members_with_points(self):
            return self.children or [self]

        def get_left(self):
            return self.center + np.array([-self.width / 2, 0, 0])

        def get_right(self):
            return self.center + np.array([self.width / 2, 0, 0])

        def get_bottom(self):
            return self.center + np.array([0, -self.height / 2, 0])

        def get_top(self):
            return self.center + np.array([0, self.height / 2, 0])

        def scale(self, factor, about_point=None):
            about = np.array(about_point if about_point is not None else self.center)
            targets = self.children or [self]
            for target in targets:
                target.center = about + (target.center - about) * factor
                target.width *= factor
                target.height *= factor
            return self

        def shift(self, delta):
            for target in self.children or [self]:
                target.center += np.array(delta)
            return self

    @classmethod
    def setUpClass(cls) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        start = source.index("def proof_surface_registry")
        end = source.index("def register_portrait_role", start)
        namespace = {"math": math, "np": np}
        exec(source[start:end], namespace)
        cls.helper_namespace = namespace

    def harness(self):
        harness = type("Harness", (), {})()
        for name, value in self.helper_namespace.items():
            if callable(value):
                setattr(harness, name, value.__get__(harness, type(harness)))
        harness._proof_surface_role_contract = {
            role: {
                **lane,
                "lane_width": stem_course.PORTRAIT_PROOF_SURFACE_CONTRACT["lane_width"],
                "lane_height": lane["top"] - lane["bottom"],
                "center_y": (lane["top"] + lane["bottom"]) / 2,
                **{
                    key: stem_course.PORTRAIT_PROOF_SURFACE_CONTRACT[key]
                    for key in (
                        "min_width_occupancy", "max_width_occupancy",
                        "min_height_occupancy", "max_height_occupancy",
                        "min_area_occupancy", "min_occupied_row_ratio",
                        "min_occupied_column_ratio",
                    )
                },
            }
            for role, lane in stem_course.PORTRAIT_PROOF_SURFACE_CONTRACT["roles"].items()
        }
        harness.mobjects = []
        return harness

    def test_visibility_uses_vector_opacity_when_generic_getter_is_synthetic(self) -> None:
        harness = self.harness()

        class LineLike(self.Mob):
            def get_fill_opacity(self):
                return 0.0

            def get_stroke_opacity(self):
                return 1.0

            def get_opacity(self):
                raise AttributeError("synthetic getter has no opacity attribute")

        line = LineLike(2.0, 0.1)
        harness.mobjects = [line]
        self.assertTrue(harness._proof_surface_leaf_visible(line))

    def test_zero_vector_opacity_is_hidden_without_generic_getter(self) -> None:
        harness = self.harness()

        class HiddenLine(self.Mob):
            def get_fill_opacity(self):
                return 0.0

            def get_stroke_opacity(self):
                return 0.0

            def get_opacity(self):
                raise AssertionError("generic getter must not run after vector samples")

        line = HiddenLine(2.0, 0.1)
        harness.mobjects = [line]
        self.assertFalse(harness._proof_surface_leaf_visible(line))

    def test_generic_opacity_remains_supported_for_non_vector_mobjects(self) -> None:
        harness = self.harness()

        class Generic(self.Mob):
            def get_opacity(self):
                return self.opacity

        visible = Generic(1.0, 1.0)
        visible.opacity = 0.8
        hidden = Generic(1.0, 1.0)
        hidden.opacity = 0.0
        harness.mobjects = [visible]
        self.assertTrue(harness._proof_surface_leaf_visible(visible))
        harness.mobjects = [hidden]
        self.assertFalse(harness._proof_surface_leaf_visible(hidden))

    def visible_root(self, width: float, height: float):
        root = self.Mob(width, height)
        root._proof_surface_id = "surface"
        return root

    def test_hidden_future_descendants_do_not_count(self) -> None:
        harness = self.harness()
        visible = self.Mob(2.0, 2.0)
        hidden = self.Mob(7.0, 7.0, visible=False)
        root = self.Mob(0.0, 0.0)
        root.children = [visible, hidden]
        harness.mobjects = [root]

        bounds, leaves = harness._proof_surface_bounds(root)

        self.assertEqual(leaves, [visible])
        self.assertEqual(bounds, (-1.0, -1.0, 1.0, 1.0))

    def test_uniform_plot_and_stacked_strategies_succeed(self) -> None:
        for strategy in ("uniform", "plot", "stacked"):
            with self.subTest(strategy=strategy):
                harness = self.harness()
                core = self.visible_root(6.7 if strategy == "uniform" else 4.0, 6.5 if strategy == "uniform" else 2.5)
                harness.mobjects = [core]

                def rebuild(_strategy, _contract):
                    replacement = self.visible_root(6.7, 6.5)
                    harness.mobjects = [replacement]
                    return {"core_geometry": replacement, "attachments": [], "evidence": []}

                harness.register_proof_surface(
                    core,
                    strategy=strategy,
                    rebuild=None if strategy == "uniform" else rebuild,
                )
                snapshots = harness.finalize_proof_surface("stable")
                self.assertTrue(snapshots[0]["minimum_satisfied"])
                self.assertTrue(snapshots[0]["maximum_satisfied"])

    def test_rebuild_observes_pristine_core_and_does_not_scale_attachment(self) -> None:
        harness = self.harness()
        core = self.visible_root(4.0, 2.5)
        attachment = self.Mob(0.4, 0.5)
        attachment.center = np.array([-3.75, 0.0, 0.0])
        harness.mobjects = [core, attachment]
        observed_dimensions = []

        def rebuild(_strategy, _contract):
            observed_dimensions.append((core.width, core.height))
            replacement = self.visible_root(6.7, 6.5)
            harness.mobjects = [replacement, attachment]
            return {
                "core_geometry": replacement,
                "attachments": [attachment],
                "evidence": [],
            }

        harness.register_proof_surface(
            core,
            attachments=[attachment],
            strategy="stacked",
            rebuild=rebuild,
        )
        snapshots = harness.finalize_proof_surface("transactional-reflow")

        self.assertEqual(observed_dimensions, [(4.0, 2.5)])
        self.assertAlmostEqual(attachment.width, 0.4)
        self.assertAlmostEqual(attachment.height, 0.5)
        self.assertTrue(snapshots[0]["roles"]["attachments"]["lane_satisfied"])
        self.assertTrue(snapshots[0]["minimum_satisfied"])
        self.assertTrue(snapshots[0]["maximum_satisfied"])

    def test_unresolved_reflow_fails_closed(self) -> None:
        harness = self.harness()
        core = self.visible_root(4.0, 2.5)
        harness.mobjects = [core]

        def unresolved(_strategy, _contract):
            return {"core_geometry": core, "attachments": [], "evidence": []}

        harness.register_proof_surface(core, strategy="plot", rebuild=unresolved)
        with self.assertRaisesRegex(ValueError, "minimum_failures=height_occupancy"):
            harness.finalize_proof_surface("bad-reflow")

    def test_sparse_stacked_reflow_names_occupied_row_deficit(self) -> None:
        harness = self.harness()
        root = self.Mob(0.0, 0.0)
        root._proof_surface_id = "sparse-surface"
        root.children = []
        for center_y in (-3.0, -1.0, 1.0, 3.0):
            band = self.Mob(6.7, 0.08)
            band.center = np.array([0.0, center_y, 0.0])
            root.children.append(band)
        harness.mobjects = [root]

        def unresolved(_strategy, _contract):
            return {"core_geometry": root, "attachments": [], "evidence": []}

        harness.register_proof_surface(root, strategy="stacked", rebuild=unresolved)
        with self.assertRaisesRegex(ValueError, "minimum_failures=.*occupied_row_ratio"):
            harness.finalize_proof_surface("sparse-reflow")

    def test_post_reflow_role_collision_fails_closed(self) -> None:
        harness = self.harness()
        core = self.visible_root(6.7, 6.5)
        evidence = self.Mob(2.0, 1.0)
        harness.mobjects = [core, evidence]
        harness.register_proof_surface(core, evidence=[evidence], strategy="uniform")

        with self.assertRaisesRegex(ValueError, "collisions=core_geometry/evidence"):
            harness.finalize_proof_surface("colliding-reflow")

    def test_sparse_row_or_column_evidence_requires_reflow(self) -> None:
        result = stem_course.proof_surface_layout(
            6.7,
            6.5,
            "group_cosets",
            occupied_row_ratio=0.40,
            occupied_column_ratio=0.80,
        )

        self.assertTrue(result["requires_reflow"])
        self.assertFalse(result["minimum_satisfied"])


class PortraitProofSurfaceAuditTests(unittest.TestCase):
    def test_outer_profile_accepts_a_filled_core_and_separate_evidence(self) -> None:
        pixels = blank_frame()
        paint_outline(pixels, 12, 74, 168, 230)
        paint_outline(pixels, 28, 252, 152, 278)

        profile = audit_video_frames.portrait_proof_surface_profile(
            bytes(pixels), WIDTH, HEIGHT
        )

        self.assertFalse(profile["outer_underfill"])
        self.assertFalse(profile["evidence_intrusion"])
        self.assertGreaterEqual(profile["core_area_occupancy"], 0.48)
        self.assertGreaterEqual(profile["occupied_row_ratio"], 0.55)
        self.assertGreaterEqual(profile["occupied_column_ratio"], 0.60)

    def test_outer_profile_detects_underfill_beyond_old_central_window(self) -> None:
        pixels = blank_frame()
        paint_outline(pixels, 55, 104, 125, 206)

        profile = audit_video_frames.portrait_proof_surface_profile(
            bytes(pixels), WIDTH, HEIGHT
        )

        self.assertTrue(profile["outer_underfill"])
        self.assertLess(profile["core_width_occupancy"], 0.78)

    def test_connected_evidence_crossing_its_top_boundary_is_intrusion(self) -> None:
        pixels = blank_frame()
        paint_outline(pixels, 12, 74, 168, 230)
        paint_outline(pixels, 45, 244, 135, 278)

        profile = audit_video_frames.portrait_proof_surface_profile(
            bytes(pixels), WIDTH, HEIGHT
        )

        self.assertTrue(profile["evidence_intrusion"])

    def test_thin_coordinate_cross_cannot_pass_on_outer_bbox_alone(self) -> None:
        pixels = blank_frame()
        paint_cross(pixels)

        profile = audit_video_frames.portrait_proof_surface_profile(
            bytes(pixels), WIDTH, HEIGHT
        )

        self.assertGreater(profile["core_area_occupancy"], 0.48)
        self.assertLess(
            profile["core_tile_support_ratio"],
            audit_video_frames.PORTRAIT_CORE_MIN_TILE_SUPPORT_RATIO,
        )
        self.assertTrue(profile["outer_underfill"])

    def test_runtime_role_masks_override_outer_bbox_fallback_and_enforce_maximum(self) -> None:
        roles = {
            "core_geometry": {
                "visible": True,
                "visible_descendant_count": 8,
                "width_occupancy": 0.99,
                "height_occupancy": 0.78,
                "area_occupancy": 0.7722,
                "occupied_row_ratio": 0.8,
                "occupied_column_ratio": 0.9,
                "tile_support_ratio": 0.4,
            },
            "evidence": {"visible": True, "lane_satisfied": True},
        }

        profile = audit_video_frames.portrait_proof_surface_profile(
            bytes(blank_frame()), WIDTH, HEIGHT, runtime_roles=roles
        )

        self.assertTrue(profile["runtime_role_masks_used"])
        self.assertFalse(profile["outer_underfill"])
        self.assertTrue(profile["outer_overfill"])

    def test_sustained_outer_and_evidence_failures_reach_dense_audit_flags(self) -> None:
        pixels = blank_frame()
        paint_outline(pixels, 55, 104, 125, 206)
        paint_outline(pixels, 45, 244, 135, 278)
        frames = [bytes(pixels)] * 8

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("portrait-contract.mp4"),
                interval=1.0,
                duration=8.0,
            )

        self.assertIn("outer_portrait_underfill", metrics["serious_review_flags"])
        self.assertIn("evidence_lane_intrusion", metrics["serious_review_flags"])
        self.assertEqual(metrics["outer_portrait_underfill_frame_ratio"], 1.0)
        self.assertEqual(metrics["evidence_lane_intrusion_frame_ratio"], 1.0)

    def test_sustained_runtime_max_occupancy_is_publish_blocking(self) -> None:
        pixels = blank_frame()
        paint_outline(pixels, 12, 74, 168, 230)
        frames = [bytes(pixels)] * 8
        runtime_metadata = {
            "proof_surface_holds": [{
                "renderer_seconds": 0.0,
                "surfaces": [{
                    "roles": {
                        "core_geometry": {
                            "visible": True,
                            "visible_descendant_count": 5,
                            "width_occupancy": 0.99,
                            "height_occupancy": 0.80,
                            "area_occupancy": 0.792,
                            "occupied_row_ratio": 0.8,
                            "occupied_column_ratio": 0.9,
                            "tile_support_ratio": 0.4,
                        },
                        "evidence": {"visible": False, "lane_satisfied": True},
                    }
                }],
            }]
        }
        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("portrait-overfill.mp4"),
                interval=1.0,
                duration=8.0,
                runtime_metadata=runtime_metadata,
            )

        self.assertIn("outer_portrait_overfill", metrics["serious_review_flags"])
        self.assertEqual(metrics["outer_portrait_overfill_frame_ratio"], 1.0)


class GeneratedPortraitRoleTests(unittest.TestCase):
    def test_hold_lifecycle_checkpoints_after_build_and_before_stable_tail(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index("def hold_scene_state")
        end = helpers.index("def frame_partition_seconds", start)
        namespace = {}
        exec(helpers[start:end], namespace)
        hold_scene_state = namespace["hold_scene_state"]
        events = []

        class Harness:
            _beat_schedule = [{
                "scene_state": "hook",
                "stage_index": 0,
                "animation_plan_beat_id": "beat_01_hook",
                "duration": 3.0,
                "label": "hook",
            }]
            _runtime_proof_surface_holds = []

            def proof_surface_registry(self):
                return {"surface": {}}

            def finalize_proof_surface(self, _state_id):
                events.append("finalize")
                return [{"minimum_satisfied": True}]

            def runtime_renderer_seconds(self):
                return 1.0

            def semantic_beat_hold(self, _duration, **kwargs):
                events.append("build")
                kwargs["stable_state_callback"]()
                events.append("stable_tail")

        harness = Harness()
        hold_scene_state(harness, "hook", stage_index=0)

        self.assertEqual(events, ["build", "finalize", "stable_tail"])
        self.assertEqual(len(harness._runtime_proof_surface_holds), 1)

    def test_generated_graph_scene_embeds_registry_and_collision_recheck(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Depth-First Search", "algorithms"),
            1,
        )
        source = stem_course.manim_scene(
            short,
            "PortraitGraphContract",
            stem_course.build_animation_plan(short),
        )

        compile(source, "PortraitGraphContract.py", "exec")
        self.assertIn("def register_portrait_role", source)
        self.assertIn("def reflow_portrait_roles", source)
        self.assertIn('self.register_portrait_role("core_proof", graph_surface, core=graph)', source)
        self.assertIn('self.register_portrait_role("evidence", graph_evidence)', source)
        self.assertIn("self.assert_layout_disjoint(tuple(present), pad=0.08)", source)

    def test_generated_scene_embeds_complete_role_occupancy_contracts(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Depth-First Search", "algorithms"),
            1,
        )
        source = stem_course.manim_scene(
            short,
            "PortraitOccupancyContract",
            stem_course.build_animation_plan(short),
        )

        compile(source, "PortraitOccupancyContract.py", "exec")
        assignment = next(
            line for line in source.splitlines()
            if "self._proof_surface_role_contract =" in line
        )
        for key in (
            "min_area_occupancy",
            "min_width_occupancy",
            "max_width_occupancy",
            "min_height_occupancy",
            "max_height_occupancy",
            "min_occupied_row_ratio",
            "min_occupied_column_ratio",
        ):
            with self.subTest(key=key):
                self.assertIn(repr(key), assignment)

    def test_cross_domain_renderers_use_the_same_semantic_roles(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        markers = (
            'self.register_portrait_role("core_proof", table_group, core=cell_group)',
            'strategy="stacked",\n        rebuild=rebuild_coset_stack',
            'budget_core._proof_surface_id = "economics-budget-plot"',
            'force_geometry._proof_surface_id = "physics-free-body-uniform"',
            'vector_core._proof_surface_id = "physics-vector-uniform"',
        )
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, helpers)

    def test_stable_holds_finalize_and_emit_role_masks(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        self.assertIn("snapshots = self.finalize_proof_surface(state_id)", helpers)
        self.assertIn('"role_masks": {', helpers)
        self.assertIn('"proof_surface_holds": list(', helpers)

    def test_same_lane_pages_are_sequential_transactions(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        transaction = helpers[
            helpers.index("def cue_lane_transaction"):
            helpers.index("def present_cue_pages")
        ]
        removal = transaction.index("self.remove(outgoing)")
        self.assertLess(transaction.index("FadeOut(outgoing)"), removal)
        self.assertLess(removal, transaction.index("FadeIn(incoming", removal))
        self.assertNotIn("FadeOut(outgoing), FadeIn(incoming", transaction)

    def test_cue_transaction_validates_horizontal_and_vertical_swept_bounds(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        start = helpers.index("def assert_cue_lane_transaction")
        end = helpers.index("def cue_lane_transaction", start)
        namespace = {"np": np}
        exec(helpers[start:end], namespace)
        assertion = namespace["assert_cue_lane_transaction"]

        class Mob:
            def __init__(self, left, bottom, right, top) -> None:
                self.bounds = (left, bottom, right, top)

            def get_left(self):
                return (self.bounds[0], 0.0, 0.0)

            def get_right(self):
                return (self.bounds[2], 0.0, 0.0)

            def get_bottom(self):
                return (0.0, self.bounds[1], 0.0)

            def get_top(self):
                return (0.0, self.bounds[3], 0.0)

        harness = SimpleNamespace(_proof_surface_role_contract={
            "cue_formula": {"bottom": 4.75, "top": 6.25, "lane_width": 8.1}
        })
        clear = Mob(-3.5, 5.0, 3.5, 6.0)
        self.assertTrue(assertion(harness, None, clear, "cue_formula", shift=(0.2, 0.08, 0.0)))

        horizontal_escape = Mob(-3.9, 5.0, 4.0, 6.0)
        with self.assertRaisesRegex(ValueError, "leaves its cue_formula lane"):
            assertion(harness, None, horizontal_escape, "cue_formula", shift=(-0.2, 0.0, 0.0))

        vertical_escape = Mob(-3.5, 4.78, 3.5, 6.0)
        with self.assertRaisesRegex(ValueError, "leaves its cue_formula lane"):
            assertion(harness, None, vertical_escape, "cue_formula", shift=(0.0, 0.08, 0.0))


if __name__ == "__main__":
    unittest.main()

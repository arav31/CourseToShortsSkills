from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from tools import audit_video_frames


WIDTH = 180
HEIGHT = 320
BACKGROUND = 8


def frame(width: int = WIDTH, height: int = HEIGHT) -> bytearray:
    return bytearray([BACKGROUND]) * (width * height)


def paint_rectangle(
    pixels: bytearray,
    width: int,
    *,
    left: int,
    top: int,
    right: int,
    bottom: int,
    value: int,
) -> None:
    for y in range(top, bottom):
        row = y * width
        pixels[row + left : row + right] = bytes([value]) * (right - left)


def diagonal_support(end_x: int) -> bytes:
    pixels = frame()
    for x in range(16, end_x):
        center_y = 100 + (x - 16) // 3
        paint_rectangle(
            pixels,
            WIDTH,
            left=x,
            top=center_y - 5,
            right=x + 1,
            bottom=center_y + 5,
            value=220,
        )
    return bytes(pixels)


def sparse_displacement(offset: int) -> bytes:
    pixels = frame()
    left = 31 + offset
    top = 33
    for local_y in range(12):
        for local_x in range(12):
            if (local_x + local_y) % 2 == 0:
                index = (top + local_y) * WIDTH + left + local_x
                pixels[index] = 220
    return bytes(pixels)


def structured_diagram() -> bytes:
    pixels = frame()
    paint_rectangle(pixels, WIDTH, left=45, top=105, right=48, bottom=205, value=180)
    paint_rectangle(pixels, WIDTH, left=45, top=190, right=155, bottom=193, value=180)
    for x in range(58, 146):
        y = 177 - (x - 58) // 2
        paint_rectangle(pixels, WIDTH, left=x, top=y - 1, right=x + 2, bottom=y + 2, value=220)
    for left, top in ((66, 168), (100, 150), (134, 132)):
        paint_rectangle(pixels, WIDTH, left=left, top=top, right=left + 7, bottom=top + 7, value=240)
    return bytes(pixels)


class MotionEvidenceTests(unittest.TestCase):
    def test_visual_lane_profile_rejects_a_shallow_center_strip(self) -> None:
        pixels = frame()
        paint_rectangle(pixels, WIDTH, left=40, top=140, right=140, bottom=154, value=220)

        profile = audit_video_frames.visual_lane_profile(bytes(pixels), WIDTH, HEIGHT)

        self.assertTrue(profile["sparse"])
        self.assertLess(profile["bbox_height_ratio"], 0.05)
        self.assertLess(profile["occupied_row_ratio"], 0.15)

    def test_visual_lane_profile_rejects_a_large_featureless_rectangle(self) -> None:
        pixels = frame()
        paint_rectangle(pixels, WIDTH, left=25, top=100, right=155, bottom=210, value=220)

        profile = audit_video_frames.visual_lane_profile(bytes(pixels), WIDTH, HEIGHT)

        self.assertTrue(profile["geometric_coverage"])
        self.assertEqual(profile["component_count"], 1)
        self.assertEqual(profile["internal_edge_pixel_ratio"], 0.0)
        self.assertFalse(profile["structural_evidence"])
        self.assertFalse(profile["meaningful_diagram"])
        self.assertTrue(profile["sparse"])

    def test_visual_lane_profile_accepts_a_substantive_portrait_diagram(self) -> None:
        profile = audit_video_frames.visual_lane_profile(structured_diagram(), WIDTH, HEIGHT)

        self.assertFalse(profile["sparse"])
        self.assertTrue(profile["structural_evidence"])
        self.assertTrue(profile["meaningful_diagram"])
        self.assertGreaterEqual(profile["component_count"], 2)
        self.assertGreater(profile["internal_edge_pixel_ratio"], 0.10)
        self.assertGreater(profile["bbox_height_ratio"], 0.30)
        self.assertGreater(profile["lower_half_occupied_row_ratio"], 0.70)

    def test_sustained_shallow_diagram_is_a_serious_visual_lane_flag(self) -> None:
        pixels = frame()
        paint_rectangle(pixels, WIDTH, left=40, top=140, right=140, bottom=154, value=220)
        frames = [bytes(pixels) for _ in range(8)]

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("shallow-diagram.mp4"),
                interval=1.0,
                duration=8.0,
            )

        self.assertIn("underfilled_visual_lane", metrics["review_flags"])
        self.assertIn("underfilled_visual_lane", metrics["serious_review_flags"])
        self.assertGreaterEqual(metrics["max_sparse_visual_lane_hold_seconds"], 6.0)

    def test_sustained_featureless_rectangle_is_a_serious_visual_lane_flag(self) -> None:
        pixels = frame()
        paint_rectangle(pixels, WIDTH, left=25, top=100, right=155, bottom=210, value=220)
        frames = [bytes(pixels) for _ in range(8)]

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("featureless-rectangle.mp4"),
                interval=1.0,
                duration=8.0,
            )

        self.assertEqual(metrics["visual_lane_structural_frame_ratio"], 0.0)
        self.assertEqual(metrics["meaningful_visual_lane_frame_ratio"], 0.0)
        self.assertEqual(metrics["sparse_visual_lane_frame_ratio"], 1.0)
        self.assertIn("underfilled_visual_lane", metrics["review_flags"])
        self.assertIn("underfilled_visual_lane", metrics["serious_review_flags"])

    def test_uniform_opacity_change_does_not_count_as_explanatory_motion(self) -> None:
        before = frame(120, 80)
        after = frame(120, 80)
        paint_rectangle(before, 120, left=15, top=15, right=105, bottom=65, value=70)
        paint_rectangle(after, 120, left=15, top=15, right=105, bottom=65, value=190)

        evidence = audit_video_frames.transition_motion_evidence(bytes(before), bytes(after), 120, 80)

        self.assertTrue(evidence["active"])
        self.assertEqual(evidence["directional_coherence"], 1.0)
        self.assertEqual(evidence["local_bidirectional_ratio"], 0.0)
        self.assertEqual(evidence["support_extension_ratio"], 0.0)
        self.assertFalse(evidence["spatial_or_drawn"])
        self.assertTrue(evidence["opacity_dominated"])

    def test_local_displacement_has_two_way_motion_evidence(self) -> None:
        before = frame(120, 80)
        after = frame(120, 80)
        for x in range(12, 108):
            if x % 4 < 2:
                paint_rectangle(before, 120, left=x, top=20, right=x + 1, bottom=60, value=220)
            if (x - 1) % 4 < 2:
                paint_rectangle(after, 120, left=x, top=20, right=x + 1, bottom=60, value=220)

        evidence = audit_video_frames.transition_motion_evidence(bytes(before), bytes(after), 120, 80)

        self.assertTrue(evidence["active"])
        self.assertGreaterEqual(
            evidence["local_bidirectional_ratio"],
            audit_video_frames.MOTION_MIN_LOCAL_BIDIRECTIONAL_RATIO,
        )
        self.assertTrue(evidence["spatial_or_drawn"])
        self.assertFalse(evidence["opacity_dominated"])

    def test_progressive_draw_retains_stable_support_while_extending_it(self) -> None:
        before = diagonal_support(90)
        after = diagonal_support(130)

        evidence = audit_video_frames.transition_motion_evidence(before, after, WIDTH, HEIGHT)

        self.assertTrue(evidence["active"])
        self.assertEqual(evidence["directional_coherence"], 1.0)
        self.assertGreaterEqual(
            evidence["support_extension_ratio"],
            audit_video_frames.MOTION_MIN_SUPPORT_EXTENSION_RATIO,
        )
        self.assertTrue(evidence["spatial_or_drawn"])
        self.assertFalse(evidence["opacity_dominated"])

    def test_single_support_change_is_not_a_progressive_draw_run(self) -> None:
        self.assertEqual(
            audit_video_frames.sustained_true_states(
                [False, True, False, True, True, False],
                minimum_run=2,
            ),
            [False, False, False, True, True, False],
        )

    def test_large_opacity_fades_cannot_satisfy_motion_coverage(self) -> None:
        frames = []
        for value in (40, 100, 160, 220, 160, 100, 40):
            pixels = frame()
            paint_rectangle(pixels, WIDTH, left=20, top=70, right=160, bottom=250, value=value)
            frames.append(bytes(pixels))

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("opacity-only.mp4"),
                interval=1.0,
                duration=7.0,
            )

        self.assertEqual(metrics["broad_visual_change_transition_ratio"], 1.0)
        self.assertEqual(metrics["motion_transition_ratio"], 0.0)
        self.assertEqual(metrics["opacity_dominated_transition_ratio"], 1.0)
        self.assertIn("insufficient_motion_coverage", metrics["review_flags"])

    def test_crossfade_between_static_states_cannot_satisfy_motion_coverage(self) -> None:
        frames = []
        for old_alpha, new_alpha in ((1.0, 0.0), (0.8, 0.2), (0.6, 0.4), (0.4, 0.6), (0.2, 0.8), (0.0, 1.0)):
            pixels = frame()
            paint_rectangle(
                pixels,
                WIDTH,
                left=15,
                top=65,
                right=75,
                bottom=255,
                value=BACKGROUND + round((220 - BACKGROUND) * old_alpha),
            )
            paint_rectangle(
                pixels,
                WIDTH,
                left=105,
                top=65,
                right=165,
                bottom=255,
                value=BACKGROUND + round((220 - BACKGROUND) * new_alpha),
            )
            frames.append(bytes(pixels))

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("crossfade-only.mp4"),
                interval=1.0,
                duration=6.0,
            )

        self.assertEqual(metrics["broad_visual_change_transition_ratio"], 1.0)
        self.assertEqual(metrics["motion_transition_ratio"], 0.0)
        self.assertIn("insufficient_motion_coverage", metrics["review_flags"])

    def test_sustained_sparse_drawing_can_satisfy_motion_coverage(self) -> None:
        frames = [diagonal_support(end_x) for end_x in (50, 70, 90, 110, 130, 150, 170)]

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("progressive-draw.mp4"),
                interval=1.0,
                duration=7.0,
            )

        self.assertEqual(metrics["broad_visual_change_transition_ratio"], 0.0)
        self.assertGreaterEqual(metrics["progressive_draw_transition_ratio"], 0.5)
        self.assertGreaterEqual(metrics["motion_window_coverage_ratio"], 0.5)
        self.assertEqual(metrics["visual_lane_structural_frame_ratio"], 1.0)
        self.assertEqual(metrics["meaningful_visual_lane_frame_ratio"], 1.0)
        self.assertNotIn("insufficient_motion_coverage", metrics["review_flags"])
        self.assertNotIn("low_visual_change", metrics["review_flags"])
        self.assertNotIn("underfilled_visual_lane", metrics["review_flags"])

    def test_sustained_sparse_local_displacement_counts_without_whole_frame_change(self) -> None:
        frames = [sparse_displacement(offset) for offset in range(7)]

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("sparse-local-displacement.mp4"),
                interval=0.25,
                duration=1.75,
            )

        self.assertEqual(metrics["broad_visual_change_transition_ratio"], 0.0)
        self.assertGreaterEqual(metrics["spatial_motion_transition_ratio"], 0.5)
        self.assertLess(metrics["static_transition_ratio"], 0.5)
        self.assertNotIn("insufficient_motion_coverage", metrics["review_flags"])
        self.assertNotIn("low_visual_change", metrics["review_flags"])


if __name__ == "__main__":
    unittest.main()

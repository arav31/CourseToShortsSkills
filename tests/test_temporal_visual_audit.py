from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from tools import audit_video_frames


WIDTH = 180
HEIGHT = 320
BACKGROUND = 8


def sparse_causal_frame(step: int) -> bytes:
    pixels = bytearray([BACKGROUND]) * (WIDTH * HEIGHT)
    left = 48 + step * 2
    for y in range(142, 150):
        pixels[y * WIDTH + left : y * WIDTH + left + 8] = bytes([220]) * 8
    return bytes(pixels)


class TemporalVisualLaneTests(unittest.TestCase):
    def test_sparse_causal_animation_supplies_localized_visual_lane_proof(self) -> None:
        frames = [sparse_causal_frame(step) for step in range(8)]
        static_profiles = [
            audit_video_frames.visual_lane_profile(frame, WIDTH, HEIGHT)
            for frame in frames
        ]
        transition_profiles = [
            audit_video_frames.visual_lane_motion_evidence(previous, current, WIDTH, HEIGHT)
            for previous, current in zip(frames, frames[1:])
        ]

        self.assertTrue(all(profile["sparse"] for profile in static_profiles))
        self.assertTrue(all(not profile["structural_evidence"] for profile in static_profiles))
        self.assertTrue(all(profile["localized_motion_distribution"] for profile in transition_profiles))
        self.assertTrue(all(profile["gain_loss_balance_ratio"] == 1.0 for profile in transition_profiles))

        def sampled_frames(
            _ffmpeg: str,
            _video: Path,
            *,
            interval: float,
            width: int,
            height: int,
        ) -> list[bytes]:
            del interval
            return frames if (width, height) == (WIDTH, HEIGHT) else []

        with mock.patch.object(audit_video_frames, "sample_gray_frames", side_effect=sampled_frames):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("sparse-causal-animation.mp4"),
                interval=0.25,
                duration=2.0,
            )

        self.assertEqual(metrics["visual_lane_structural_frame_ratio"], 0.0)
        self.assertEqual(metrics["visual_lane_temporal_support_frame_ratio"], 1.0)
        self.assertEqual(metrics["meaningful_visual_lane_frame_ratio"], 1.0)
        self.assertEqual(metrics["sparse_visual_lane_frame_ratio"], 0.0)
        self.assertNotIn("underfilled_visual_lane", metrics["review_flags"])


if __name__ == "__main__":
    unittest.main()

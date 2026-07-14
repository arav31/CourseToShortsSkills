from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest import mock

from tools import audit_video_frames


WIDTH = 180
HEIGHT = 320
BACKGROUND = 8
TEXT_WIDTH = 360
TEXT_HEIGHT = 640


def moving_marker(offset: int) -> bytes:
    pixels = bytearray([BACKGROUND]) * (WIDTH * HEIGHT)
    left = 40 + offset
    for y in range(120, 136):
        for x in range(left, left + 16):
            if ((x - left) + (y - 120)) % 2:
                pixels[y * WIDTH + x] = 230
    return bytes(pixels)


def ocr_line(text: str, *, height: int, y: int) -> dict[str, object]:
    return {
        "text": text,
        "confidence": 95.0,
        "x": 100,
        "y": y,
        "width": 700,
        "height": height,
        "words": [],
    }


def structured_text_frame(*, tiny: bool, graph: bool = False, show_formula: bool = True) -> bytes:
    pixels = bytearray([BACKGROUND]) * (TEXT_WIDTH * TEXT_HEIGHT)

    def rectangle(x0: int, y0: int, width: int, height: int, value: int = 235) -> None:
        for y in range(y0, y0 + height):
            pixels[y * TEXT_WIDTH + x0 : y * TEXT_WIDTH + x0 + width] = bytes([value]) * width

    # A large title is deliberately present in every formula fixture.
    for x in range(55, 245, 38):
        rectangle(x, 54, 17, 28)
    if graph:
        rectangle(52, 320, 256, 2)
        rectangle(52, 180, 2, 142)
        for x in range(72, 309, 34):
            rectangle(x, 316, 2, 10)
            rectangle(x - 2, 332, 3, 5)
        for y in range(202, 310, 27):
            rectangle(48, y, 10, 2)
            rectangle(34, y - 2, 4, 5)
        return bytes(pixels)
    if not show_formula:
        return bytes(pixels)

    glyph_height = 7 if tiny else 18
    glyph_width = 3 if tiny else 7
    y = 528 if tiny else 500
    x = 145
    rectangle(x, y, glyph_width, glyph_height)
    rectangle(x + glyph_width + 4, y + 1, glyph_width + 2, max(2, glyph_height // 5))
    rectangle(x + glyph_width + 4, y + glyph_height - max(2, glyph_height // 5), glyph_width + 2, max(2, glyph_height // 5))
    rectangle(x + glyph_width * 2 + 10, y, glyph_width, glyph_height)
    rectangle(x + glyph_width * 3 + 14, y + glyph_height // 2, glyph_width + 3, max(2, glyph_height // 5))
    rectangle(x + glyph_width * 4 + 21, y, glyph_width, glyph_height)
    return bytes(pixels)


def title_only_ocr_frames(count: int, interval: float) -> list[dict[str, object]]:
    return [
        {
            "width": TEXT_WIDTH,
            "height": TEXT_HEIGHT,
            "timestamp_seconds": index * interval,
            "lines": [
                {
                    "text": "Large title",
                    "confidence": 96.0,
                    "x": 50,
                    "y": 50,
                    "width": 205,
                    "height": 36,
                }
            ],
            "words": [],
        }
        for index in range(count)
    ]


class MotionGateRegressionTests(unittest.TestCase):
    def test_sliding_windows_expose_bucket_boundary_bursts(self) -> None:
        states = [False] * 80
        for index in (19, 20, 59, 60):
            states[index] = True
        fixed_windows = [states[start : start + 20] for start in range(0, len(states), 20)]

        coverage = audit_video_frames.motion_window_coverage(
            states,
            interval=0.25,
            window_seconds=5.0,
        )
        maximum_gap, _terminal = audit_video_frames.motion_free_durations(
            states,
            interval=0.25,
            duration=20.0,
        )

        self.assertTrue(all(any(window) for window in fixed_windows))
        self.assertLess(coverage, 1.0)
        self.assertGreaterEqual(maximum_gap, 9.0)

    def test_dense_sampling_detects_a_b_a_replay_hidden_from_coarse_pairs(self) -> None:
        state_a = moving_marker(0)
        state_b = moving_marker(1)
        coarse_frames = [state_a, state_a, state_a]
        dense_frames = [state_a, state_b, state_a, state_a, state_a, state_a, state_a, state_a, state_a]

        def samples(_ffmpeg: str, _video: Path, *, interval: float, width: int, height: int) -> list[bytes]:
            if (width, height) != (WIDTH, HEIGHT):
                return []
            return dense_frames if interval == 0.25 else coarse_frames

        with mock.patch.object(audit_video_frames, "sample_gray_frames", side_effect=samples):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("a-b-a.mp4"),
                interval=1.0,
                duration=2.0,
            )

        self.assertGreater(metrics["motion_transition_ratio"], 0.0)
        self.assertLess(metrics["static_transition_ratio"], 1.0)

    def test_five_second_terminal_still_is_explicit_and_serious(self) -> None:
        frames = [moving_marker(offset) for offset in (0, 2, 4)] + [moving_marker(4)] * 21

        def samples(_ffmpeg: str, _video: Path, *, interval: float, width: int, height: int) -> list[bytes]:
            return frames if (width, height) == (WIDTH, HEIGHT) else []

        with mock.patch.object(audit_video_frames, "sample_gray_frames", side_effect=samples):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("terminal-still.mp4"),
                interval=0.25,
                duration=6.0,
            )

        self.assertGreaterEqual(metrics["terminal_static_duration_seconds"], 5.0)
        self.assertGreaterEqual(metrics["max_motion_free_gap_seconds"], 5.0)
        self.assertIn("terminal_static_hold", metrics["serious_review_flags"])

    def test_long_low_change_run_flags_below_global_ratio_threshold(self) -> None:
        frames = [bytes([BACKGROUND]) * (WIDTH * HEIGHT)] * 6
        frames += [bytes([value]) * (WIDTH * HEIGHT) for value in (50, 100, 150, 200, 250)]

        def samples(_ffmpeg: str, _video: Path, *, interval: float, width: int, height: int) -> list[bytes]:
            del interval
            return frames if (width, height) == (WIDTH, HEIGHT) else []

        with mock.patch.object(audit_video_frames, "sample_gray_frames", side_effect=samples):
            metrics = audit_video_frames.metrics_for(
                "ffmpeg",
                Path("long-low-change.mp4"),
                interval=1.0,
                duration=10.0,
            )

        self.assertLess(metrics["low_change_transition_ratio"], audit_video_frames.LOW_CHANGE_RATIO_LIMIT)
        self.assertEqual(metrics["max_low_change_hold_seconds"], 5.0)
        self.assertIn("prolonged_low_change_run", metrics["serious_review_flags"])
        self.assertNotIn("low_visual_change", metrics["review_flags"])


class LegibilityGateRegressionTests(unittest.TestCase):
    def visual_fallback_metrics(
        self,
        frames: list[bytes],
        interval: float = 0.25,
        runtime_metadata: object = None,
    ) -> dict[str, object]:
        ocr_frames = title_only_ocr_frames(len(frames), interval)
        return audit_video_frames.analyze_ocr_frames(
            ocr_frames,
            interval=interval,
            temporal_frames=frames,
            temporal_interval=interval,
            temporal_width=TEXT_WIDTH,
            temporal_height=TEXT_HEIGHT,
            runtime_metadata=runtime_metadata,
        )

    def test_visual_fallback_blocks_tiny_formula_beside_large_title_when_ocr_misses_it(self) -> None:
        metrics = self.visual_fallback_metrics([structured_text_frame(tiny=True)] * 8)

        self.assertEqual(metrics["frames_with_small_essential_text"], 0)
        self.assertIn("rendered_text_too_small", metrics["serious_review_flags"])
        findings = metrics["visual_small_text_fallback"]["findings"]
        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0]["evidence"]["ocr_missed_region"])

    def test_visual_fallback_correlates_optional_formula_runtime_metadata(self) -> None:
        metadata = {
            "transitions": [
                {
                    "beat_id": "final_formula",
                    "before_seconds": 0.5,
                    "after_seconds": 1.5,
                    "persistent_object_ids": ["result_formula"],
                }
            ]
        }
        metrics = self.visual_fallback_metrics(
            [structured_text_frame(tiny=True)] * 8,
            runtime_metadata=metadata,
        )

        finding = metrics["visual_small_text_fallback"]["findings"][0]
        self.assertTrue(finding["evidence"]["runtime_formula_metadata_confirmed"])

    def test_visual_fallback_ignores_graph_axes_ticks_and_tiny_tick_labels(self) -> None:
        metrics = self.visual_fallback_metrics([structured_text_frame(tiny=True, graph=True)] * 8)

        self.assertNotIn("rendered_text_too_small", metrics["serious_review_flags"])
        self.assertEqual(metrics["visual_small_text_fallback"]["findings"], [])

    def test_visual_fallback_ignores_transient_transition_residue(self) -> None:
        blank = structured_text_frame(tiny=True, show_formula=False)
        residue = structured_text_frame(tiny=True)
        metrics = self.visual_fallback_metrics([blank, residue, residue, blank, blank, blank, blank, blank])

        self.assertNotIn("rendered_text_too_small", metrics["serious_review_flags"])
        self.assertEqual(metrics["visual_small_text_fallback"]["findings"], [])

    def test_visual_fallback_allows_phone_readable_equation(self) -> None:
        metrics = self.visual_fallback_metrics([structured_text_frame(tiny=False)] * 8)

        self.assertNotIn("rendered_text_too_small", metrics["serious_review_flags"])
        self.assertEqual(metrics["visual_small_text_fallback"]["findings"], [])

    def test_tiny_essential_paragraph_is_not_diluted_by_large_labels(self) -> None:
        large_labels = [ocr_line(f"Large label {index}", height=60, y=100 + index * 70) for index in range(8)]
        tiny_paragraph = ocr_line("This tiny paragraph carries the essential explanation", height=12, y=800)
        frames = [
            {
                "width": 1000,
                "height": 1000,
                "timestamp_seconds": index * 0.5,
                "lines": [*large_labels, tiny_paragraph],
                "words": [],
            }
            for index in range(10)
        ]

        metrics = audit_video_frames.analyze_ocr_frames(frames, interval=0.5)

        self.assertLess(metrics["small_line_ratio"], audit_video_frames.OCR_SMALL_LINE_RATIO_LIMIT)
        self.assertEqual(metrics["frames_with_small_essential_text_ratio"], 1.0)
        self.assertEqual(metrics["max_small_essential_text_duration_seconds"], 5.0)
        self.assertEqual(
            metrics["small_essential_timestamps_seconds"],
            [index * 0.5 for index in range(10)],
        )
        self.assertIn("rendered_text_too_small", metrics["serious_review_flags"])

    def test_cli_failure_reasons_cover_serious_flags_and_required_ocr(self) -> None:
        report = {
            "videos": [
                {
                    "video": "videos/example_final.mp4",
                    "metrics": {
                        "serious_review_flags": ["terminal_static_hold"],
                        "ocr_text_layout": {"available": False, "sampled_frames": 0},
                    },
                }
            ]
        }

        reasons = audit_video_frames.audit_failure_reasons(report, require_ocr=True)

        self.assertEqual(len(reasons), 2)
        self.assertTrue(any("serious flags" in reason for reason in reasons))
        self.assertTrue(any("required OCR" in reason for reason in reasons))

    def test_cli_returns_nonzero_after_writing_serious_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            resolved_run = run.resolve()
            video = run / "videos" / "example_preview.mp4"
            video.parent.mkdir()
            video.write_bytes(b"video")
            sheet = resolved_run / "visual_audit" / "example_preview_contact.jpg"
            metrics = {
                "serious_review_flags": ["terminal_static_hold"],
                "ocr_text_layout": {"available": True, "sampled_frames": 2},
            }

            with (
                mock.patch("sys.argv", ["audit_video_frames.py", str(run)]),
                mock.patch.object(audit_video_frames.shutil, "which", return_value="tool"),
                mock.patch.object(audit_video_frames, "probe_video_duration", return_value=6.0),
                mock.patch.object(
                    audit_video_frames,
                    "make_contact_sheet",
                    return_value={"paths": [sheet], "coverage": {"covers_entire_video": True}},
                ),
                mock.patch.object(audit_video_frames, "metrics_for", return_value=metrics),
                mock.patch("builtins.print"),
            ):
                exit_code = audit_video_frames.main()

            self.assertEqual(exit_code, 1)
            self.assertTrue((run / "visual_frame_audit.json").is_file())


if __name__ == "__main__":
    unittest.main()

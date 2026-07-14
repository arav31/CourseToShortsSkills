from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import audit_video_frames
from tools.validate_course_run import CourseRunValidator


def valid_final_metadata(**overrides: object) -> dict[str, object]:
    metadata: dict[str, object] = {
        "duration": 30.0,
        "width": 1080,
        "height": 1920,
        "has_audio": True,
        "frame_rate": 30.0,
        "codec_name": "h264",
        "pix_fmt": "yuv420p",
        "field_order": "progressive",
        "bit_rate": 2_000_000,
        "rotation": 0.0,
    }
    metadata.update(overrides)
    return metadata


class FrameAuditTests(unittest.TestCase):
    def test_frame_change_reports_mean_delta_and_changed_pixel_ratio(self) -> None:
        mean_delta, changed_ratio = audit_video_frames.frame_change(
            bytes([0, 10, 20, 30]),
            bytes([0, 25, 8, 42]),
        )

        self.assertEqual(mean_delta, 9.75)
        self.assertEqual(changed_ratio, 0.75)
        self.assertEqual(audit_video_frames.frame_change(b"abc", b"ab"), (0.0, 0.0))

    def test_longest_run_handles_edges_and_resets(self) -> None:
        self.assertEqual(audit_video_frames.longest_run([]), 0)
        self.assertEqual(
            audit_video_frames.longest_run([True, True, False, True, True, True, False]),
            3,
        )

    def test_static_synthetic_frames_are_measured_and_flagged(self) -> None:
        frame = bytes([20]) * (180 * 320)
        frames = [frame] * 10

        with mock.patch.object(audit_video_frames, "sample_gray_frames", return_value=frames):
            metrics = audit_video_frames.metrics_for("ffmpeg", Path("synthetic.mp4"), interval=4)

        self.assertEqual(metrics["sampled_frames"], 10)
        self.assertEqual(metrics["sample_interval_seconds"], 1.0)
        self.assertEqual(metrics["static_transition_ratio"], 1.0)
        self.assertEqual(metrics["max_static_hold_seconds"], 9.0)
        self.assertIn("prolonged_static_holds", metrics["review_flags"])
        self.assertIn("low_visual_change", metrics["review_flags"])
        self.assertIn("insufficient_motion_coverage", metrics["review_flags"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe are required")
    def test_float_interval_contact_sheets_paginate_and_cover_video(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        assert ffmpeg is not None
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "synthetic.mp4"
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=90x160:r=10:d=2.1",
                    "-c:v",
                    "mpeg4",
                    str(video),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            duration = audit_video_frames.probe_video_duration(video)

            result = audit_video_frames.make_contact_sheet(
                ffmpeg,
                video,
                root / "visual_audit" / "synthetic_contact.jpg",
                interval=0.2,
                cols=2,
                rows=2,
                duration=duration,
            )

            paths = result["paths"]
            coverage = result["coverage"]
            self.assertGreater(len(paths), 1)
            self.assertEqual(len(paths), coverage["sheet_count"])
            self.assertGreater(coverage["sampled_frames"], coverage["tile_capacity"])
            self.assertTrue(coverage["covers_entire_video"])
            self.assertTrue(all(path.is_file() for path in paths))

    def test_main_report_exposes_every_contact_sheet_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            resolved_run = run.resolve()
            video = run / "videos" / "example_final.mp4"
            video.parent.mkdir()
            video.write_bytes(b"video")
            page_one = resolved_run / "visual_audit" / "example_final_contact_01.jpg"
            page_two = resolved_run / "visual_audit" / "example_final_contact_02.jpg"
            coverage = {
                "sample_interval_seconds": 0.5,
                "sampled_frames": 20,
                "sheet_count": 2,
                "covers_entire_video": True,
            }

            with (
                mock.patch(
                    "sys.argv",
                    ["audit_video_frames.py", str(run), "--interval", "0.5", "--allow-missing-ocr"],
                ),
                mock.patch.object(audit_video_frames.shutil, "which", side_effect=lambda name: "ffmpeg" if name == "ffmpeg" else None),
                mock.patch.object(audit_video_frames, "probe_video_duration", return_value=10.0),
                mock.patch.object(
                    audit_video_frames,
                    "make_contact_sheet",
                    return_value={"paths": [page_one, page_two], "coverage": coverage},
                ),
                mock.patch.object(audit_video_frames, "metrics_for", return_value={"sampled_frames": 10}),
                mock.patch("builtins.print"),
            ):
                self.assertEqual(audit_video_frames.main(), 0)

            report = json.loads((run / "visual_frame_audit.json").read_text(encoding="utf-8"))
            item = report["videos"][0]
            self.assertEqual(item["contact_sheet"], "visual_audit/example_final_contact_01.jpg")
            self.assertEqual(
                item["contact_sheets"],
                [
                    "visual_audit/example_final_contact_01.jpg",
                    "visual_audit/example_final_contact_02.jpg",
                ],
            )
            self.assertEqual(item["contact_sheet_coverage"], coverage)
            self.assertEqual(report["settings"]["contact_sheet_interval_seconds"], 0.5)


class ValidatorMetadataPolicyTests(unittest.TestCase):
    def validate_with_probe(self, metadata: dict[str, object]) -> CourseRunValidator:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        run = Path(temporary.name)
        video = run / "videos" / "short_01_example_final.mp4"
        video.parent.mkdir()
        video.write_bytes(b"0" * 10_001)

        validator = CourseRunValidator(run)
        validator.ffprobe = "ffprobe"
        validator.ffmpeg = None
        with mock.patch.object(validator, "probe_video", return_value=metadata) as probe:
            validator.validate_video_file(video, role="final")
        probe.assert_called_once_with(video.resolve())
        return validator

    def test_publishable_metadata_passes_strict_profile(self) -> None:
        validator = self.validate_with_probe(valid_final_metadata())

        failures = [issue for issue in validator.issues if issue.severity == "FAIL"]
        self.assertEqual(failures, [])

    def test_legacy_15_fps_metadata_fails_final_policy(self) -> None:
        validator = self.validate_with_probe(valid_final_metadata(frame_rate=15.0))

        failures = [issue for issue in validator.issues if issue.severity == "FAIL"]
        self.assertTrue(any(issue.area == "video.frame-rate" for issue in failures))
        self.assertTrue(any("15.000 fps" in issue.message for issue in failures))

    def test_each_required_final_encoding_field_is_enforced(self) -> None:
        cases = [
            ({"width": 720, "height": 1280}, "video.resolution"),
            ({"codec_name": "hevc"}, "video.codec"),
            ({"pix_fmt": "yuv444p"}, "video.pixel-format"),
            ({"field_order": "tt"}, "video.scan"),
            ({"bit_rate": 0}, "video.bitrate"),
            ({"rotation": 90}, "video.rotation"),
        ]
        for overrides, expected_area in cases:
            with self.subTest(overrides=overrides):
                temporary = tempfile.TemporaryDirectory()
                self.addCleanup(temporary.cleanup)
                validator = CourseRunValidator(Path(temporary.name))
                validator.validate_final_media_profile(
                    Path(temporary.name) / "short_01_example_final.mp4",
                    valid_final_metadata(**overrides),
                )
                self.assertTrue(
                    any(issue.severity == "FAIL" and issue.area == expected_area for issue in validator.issues),
                    validator.issues,
                )


if __name__ == "__main__":
    unittest.main()

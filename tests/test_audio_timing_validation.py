from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.validate_course_run import CourseRunValidator, file_sha256


class AudioTimingValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.run = Path(self.temporary.name)
        (self.run / "animation_plans").mkdir()
        (self.run / "audio").mkdir()
        (self.run / "videos").mkdir()
        self.plan_path = self.run / "animation_plans/short_01.json"
        self.audio_path = self.run / "audio/short_01_narration.wav"
        self.video_path = self.run / "videos/short_01_example_final.mp4"
        self.timing_path = self.run / "audio/short_01_narration_timing.json"
        self.plan = {
            "beats": [
                {"id": "hook", "start_seconds": 0.0, "end_seconds": 1.0},
                {"id": "proof", "start_seconds": 1.0, "end_seconds": 2.0},
            ]
        }
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        self.audio_path.write_bytes(b"synthetic narration")
        self.video_path.write_bytes(b"synthetic final video")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def manifest(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "engine": "piper",
            "model_id": "en_US-test-medium",
            "piper_tts_version": "1.4.2",
            "model_sha256": "a" * 64,
            "sample_rate": 48_000,
            "channels": 1,
            "total_frames": 96_000,
            "duration": 2.0,
            "plan_sha256": file_sha256(self.plan_path),
            "audio_sha256": file_sha256(self.audio_path),
            "video_sha256": file_sha256(self.video_path),
            "levels": {"integrated_lufs": -16.0, "true_peak_dbfs": -1.5, "sample_peak_dbfs": -2.0},
            "beats": [
                {
                    "beat_id": "hook",
                    "beat_start": 0.0,
                    "beat_end": 1.0,
                    "beat_start_frame": 0,
                    "beat_end_frame": 48_000,
                },
                {
                    "beat_id": "proof",
                    "beat_start": 1.0,
                    "beat_end": 2.0,
                    "beat_start_frame": 48_000,
                    "beat_end_frame": 96_000,
                },
            ],
        }

    def result(self, *, engine: str = "piper", status: str = "ok") -> dict[str, object]:
        return {
            "index": 1,
            "status": "rendered",
            "voiceover": {
                "engine": engine,
                "status": status,
                "audio_file": str(self.audio_path.relative_to(self.run)),
                "timing_manifest": str(self.timing_path.relative_to(self.run)),
            },
            "final_video": str(self.video_path.relative_to(self.run)),
            "sync": {"video_pad_seconds": 0.0, "audio_pad_seconds": 0.0},
        }

    @staticmethod
    def media_metadata(path: Path) -> dict[str, object]:
        if path.suffix == ".wav":
            return {
                "has_audio": True,
                "audio_sample_rate": 48_000,
                "audio_channels": 1,
                "audio_codec_name": "pcm_s16le",
                "audio_duration": 2.0,
            }
        return {
            "has_audio": True,
            "audio_sample_rate": 48_000,
            "audio_channels": 1,
            "audio_codec_name": "aac",
            "audio_duration": 2.0,
            "video_duration": 2.0,
            "duration": 2.0,
            "frame_rate": 30.0,
        }

    def validate(self, result: dict[str, object]) -> CourseRunValidator:
        validator = CourseRunValidator(self.run)
        with mock.patch.object(validator, "probe_media", side_effect=self.media_metadata):
            validator.validate_narration_timing_contracts(
                [{"index": 1, "animation_plan_file": "animation_plans/short_01.json"}],
                {"results": [result]},
            )
        return validator

    def test_hash_bound_exact_piper_timing_contract_passes(self) -> None:
        self.timing_path.write_text(json.dumps(self.manifest()), encoding="utf-8")

        validator = self.validate(self.result())

        self.assertEqual([issue for issue in validator.issues if issue.severity == "FAIL"], [])

    def test_stale_hash_and_cumulative_drift_fail(self) -> None:
        manifest = self.manifest()
        manifest["video_sha256"] = "0" * 64
        beats = manifest["beats"]
        assert isinstance(beats, list)
        beats[0]["beat_end"] = 1.08
        beats[0]["beat_end_frame"] = 51_840
        beats[1]["beat_start"] = 1.08
        beats[1]["beat_start_frame"] = 51_840
        self.timing_path.write_text(json.dumps(manifest), encoding="utf-8")

        validator = self.validate(self.result())
        areas = {issue.area for issue in validator.issues if issue.severity == "FAIL"}

        self.assertIn("audio.hash", areas)
        self.assertIn("audio.drift", areas)
        self.assertNotIn("audio.boundaries", areas)

    def test_voiced_run_missing_manifest_fails_closed(self) -> None:
        validator = self.validate(self.result())

        self.assertTrue(any(issue.area == "audio.evidence" for issue in validator.issues))

    def test_rendered_result_without_voice_record_fails_closed(self) -> None:
        validator = self.validate({"index": 1, "status": "rendered", "final_video": "videos/short_01_example_final.mp4"})

        self.assertTrue(any(issue.area == "audio.evidence" for issue in validator.issues))

    def test_silence_is_valid_only_when_engine_is_explicitly_none(self) -> None:
        silent = self.result(engine="none", status="skipped")
        self.assertEqual(self.validate(silent).issues, [])

        ambiguous = self.result(engine="", status="skipped")
        self.assertTrue(any(issue.area == "audio.evidence" for issue in self.validate(ambiguous).issues))

    def test_top_level_none_indexes_final_as_intentionally_silent(self) -> None:
        result = {"index": 1, "status": "rendered", "voice_engine": "none", "final_video": "videos/short_01_example_final.mp4"}
        validator = CourseRunValidator(self.run)

        validator.index_intentional_silence([{"index": 1, "concept": "Example"}], {"results": [result]})

        self.assertTrue(validator.intentional_silence_for(self.video_path))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
    def test_ffmpeg_probe_retains_audio_stream_contract(self) -> None:
        output = self.run / "synthetic.mp4"
        subprocess.run(
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-v", "error",
                "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=1",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ac", "1", "-ar", "48000", "-shortest", str(output),
            ],
            check=True,
            capture_output=True,
        )
        validator = CourseRunValidator(self.run)

        metadata = validator.probe_media(output)

        self.assertEqual(metadata["audio_sample_rate"], 48_000)
        self.assertEqual(metadata["audio_channels"], 1)
        self.assertEqual(metadata["audio_codec_name"], "aac")
        self.assertGreater(metadata["audio_duration"], 0)
        self.assertGreater(metadata["video_duration"], 0)


if __name__ == "__main__":
    unittest.main()

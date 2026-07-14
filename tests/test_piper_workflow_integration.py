from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from tools import piper_voiceover, stem_course
from tools.validate_course_run import CourseRunValidator, file_sha256


def write_wav(path: Path, frames: int, value: int = 800) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48_000)
        wav.writeframes(value.to_bytes(2, "little", signed=True) * frames)


def algorithm_short() -> dict[str, object]:
    concept = stem_course.ALGORITHMS[2]
    return {
        "index": 1,
        "concept": concept.name,
        "hook": concept.hook,
        "intuition": concept.intuition,
        "formula": concept.formula,
        "plain_formula": stem_course.plain_math(concept.formula),
        "prerequisites": concept.prerequisites,
        "visual_type": concept.visual_type,
        "worked_example": {
            "setup": concept.example_setup,
            "calculation": concept.example_calc,
            "takeaway": concept.example_takeaway,
        },
    }


class PiperWorkflowIntegrationTests(unittest.TestCase):
    def test_mocked_synthesis_expansion_drives_storyboard_scene_and_captions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="piper-workflow-") as tmp:
            run = Path(tmp)
            run.mkdir(exist_ok=True)
            plan = {"course_title": "Piper timing", "shorts": [algorithm_short()]}
            stem_course.write_json(run / "short_plan.json", plan)

            def fake_render(
                beats: list[dict[str, object]],
                output: Path,
                timing_manifest: Path,
                **kwargs: object,
            ) -> dict[str, object]:
                self.assertEqual(kwargs["boundary_fps"], stem_course.RENDER_TIMELINE_FPS)
                normalized = piper_voiceover.normalize_beats(beats)
                speech = [normalized[0].planned_frames + 3_200]
                speech.extend(max(1, beat.planned_frames // 2) for beat in normalized[1:])
                schedule = piper_voiceover.schedule_beats(
                    normalized, speech, boundary_fps=stem_course.RENDER_TIMELINE_FPS
                )
                total_frames = int(schedule[-1]["beat_end_frame"])
                write_wav(Path(output), total_frames)
                report = {
                    "schema_version": 2,
                    "engine": "piper",
                    "status": "rendered",
                    "model_id": "test-voice",
                    "piper_tts_version": "1.4.2",
                    "model_sha256": "a" * 64,
                    "model_assets": [{"role": "model", "sha256": "a" * 64}],
                    "sample_rate": 48_000,
                    "channels": 1,
                    "sample_width_bytes": 2,
                    "total_frames": total_frames,
                    "duration": total_frames / 48_000,
                    "audio_sha256": file_sha256(Path(output)),
                    "levels": {
                        "integrated_lufs": -18.0,
                        "true_peak_dbfs": -2.0,
                        "sample_peak_dbfs": -3.0,
                    },
                    "beats": schedule,
                }
                Path(timing_manifest).write_text(json.dumps(report), encoding="utf-8")
                return report

            args = argparse.Namespace(
                piper_model_dir=str(run / "models"),
                piper_model_manifest=str(run / "models.json"),
                piper_model_id="test-voice",
            )
            with mock.patch.object(piper_voiceover, "render_voiceover", side_effect=fake_render):
                refreshed, animation_plans, voices = stem_course.prepare_piper_workflow(run, plan, args)

            short = refreshed["shorts"][0]
            manifest = stem_course.read_json(run / voices[1]["timing_manifest"])
            canonical = manifest["canonical_beats"]
            storyboard = animation_plans[1]["beats"]
            self.assertTrue(canonical[0]["expanded"])
            self.assertEqual([row["beat_id"] for row in manifest["beats"]], [row["id"] for row in storyboard])
            for timing_row, storyboard_row in zip(manifest["beats"], storyboard):
                self.assertAlmostEqual(timing_row["beat_start"], storyboard_row["start_seconds"], places=5)
                self.assertAlmostEqual(timing_row["beat_end"], storyboard_row["end_seconds"], places=5)
            expected_end = stem_course.srt_timestamp(float(manifest["duration"]))
            captions = (run / short["srt_file"]).read_text(encoding="utf-8")
            self.assertIn(f"--> {expected_end}", captions)
            scene = (run / short["scene_file"]).read_text(encoding="utf-8")
            self.assertIn(stem_course.animation_plan_fingerprint(animation_plans[1]), scene)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
    def test_exact_final_mux_passes_strict_audio_contract_without_padding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="piper-final-") as tmp:
            run = Path(tmp)
            for directory in ("videos", "audio", "animation_plans", "logs"):
                (run / directory).mkdir()
            raw = run / "videos/short_01_fixture_raw.mp4"
            audio = run / "audio/short_01_fixture_narration.wav"
            final = run / "videos/short_01_fixture_final.mp4"
            subprocess.run(
                [
                    shutil.which("ffmpeg") or "ffmpeg",
                    "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", raw,
                ],
                check=True,
                capture_output=True,
            )
            write_wav(audio, 48_000)

            result = stem_course.finalize_piper_video(
                raw,
                audio,
                final,
                run / "logs/finalize.log",
                provenance_id="fixture",
            )

            self.assertEqual(result["status"], "ok")
            command = result["command"]
            self.assertFalse(any(token in command for token in ("-t", "-shortest")))
            self.assertNotIn("tpad", " ".join(command))
            self.assertNotIn("apad", " ".join(command))
            self.assertNotIn("atempo", " ".join(command))
            self.assertEqual(result["video_pad_seconds"], 0.0)
            self.assertEqual(result["audio_pad_seconds"], 0.0)
            video_duration, audio_duration = stem_course.probe_av_durations(final)
            self.assertLessEqual(abs(video_duration - audio_duration), 1 / 30 + 0.001)

            plan_path = run / "animation_plans/short_01.json"
            plan_path.write_text(
                json.dumps({"beats": [{"id": "beat", "start_seconds": 0.0, "end_seconds": 1.0}]}),
                encoding="utf-8",
            )
            timing_path = run / "audio/short_01_fixture_narration_timing.json"
            timing_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "engine": "piper",
                        "model_id": "test-voice",
                        "piper_tts_version": "1.4.2",
                        "model_sha256": "a" * 64,
                        "sample_rate": 48_000,
                        "channels": 1,
                        "total_frames": 48_000,
                        "duration": 1.0,
                        "plan_sha256": file_sha256(plan_path),
                        "audio_sha256": file_sha256(audio),
                        "video_sha256": file_sha256(final),
                        "levels": {
                            "integrated_lufs": -18.0,
                            "true_peak_dbfs": -2.0,
                            "sample_peak_dbfs": -3.0,
                        },
                        "beats": [
                            {
                                "beat_id": "beat",
                                "beat_start": 0.0,
                                "beat_end": 1.0,
                                "beat_start_frame": 0,
                                "beat_end_frame": 48_000,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            validator = CourseRunValidator(run)
            validator.validate_narration_timing_contracts(
                [{"index": 1, "animation_plan_file": str(plan_path.relative_to(run))}],
                {
                    "results": [
                        {
                            "index": 1,
                            "status": "rendered",
                            "final_video": str(final.relative_to(run)),
                            "voiceover": {
                                "status": "ok",
                                "engine": "piper",
                                "audio_file": str(audio.relative_to(run)),
                                "timing_manifest": str(timing_path.relative_to(run)),
                            },
                            "sync": {"video_pad_seconds": 0.0, "audio_pad_seconds": 0.0},
                        }
                    ]
                },
            )
            self.assertEqual([issue for issue in validator.issues if issue.severity == "FAIL"], [])

    def test_none_mode_contract_remains_explicit_and_does_not_create_audio(self) -> None:
        with tempfile.TemporaryDirectory(prefix="none-stability-") as tmp:
            output = Path(tmp) / "audio/narration.mp3"
            self.assertEqual(
                stem_course.make_voiceover("Narration", output, "none"),
                {"status": "skipped", "engine": "none"},
            )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

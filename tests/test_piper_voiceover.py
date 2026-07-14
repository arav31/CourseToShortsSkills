from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from tools import piper_voiceover


SOURCE_LOUDNESS_JSON = json.dumps(
    {
        "input_i": "-6.25",
        "input_tp": "0.00",
        "input_lra": "3.40",
        "input_thresh": "-16.50",
        "target_offset": "0.10",
    }
)
SAFE_LOUDNESS_JSON = json.dumps(
    {
        "input_i": "-16.00",
        "input_tp": "-1.50",
        "input_lra": "3.40",
        "input_thresh": "-26.50",
        "target_offset": "0.00",
    }
)


def write_wav(path: Path, frames: int, *, sample_rate: int = 48_000, value: int = 1000) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(int(value).to_bytes(2, "little", signed=True) * frames)


class FakeVoice:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self.fail_on = fail_on

    def synthesize_wav(self, text: str, wav_file: wave.Wave_write) -> None:
        self.calls.append(text)
        if text == self.fail_on:
            raise RuntimeError("synthetic Piper failure")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22_050)
        wav_file.writeframes((500).to_bytes(2, "little", signed=True) * 100)


class ClippedVoice(FakeVoice):
    def synthesize_wav(self, text: str, wav_file: wave.Wave_write) -> None:
        self.calls.append(text)
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(48_000)
        samples = bytearray()
        for frame in range(3 * 48_000):
            sample = max(-1.0, min(1.0, 1.8 * math.sin(2.0 * math.pi * 440.0 * frame / 48_000)))
            samples.extend(struct.pack("<h", int(sample * 32_767)))
        wav_file.writeframes(samples)


class FakeFFmpeg:
    def __init__(
        self,
        frame_counts: list[int],
        *,
        fail_normalization: int | None = None,
        output_loudness_json: str = SAFE_LOUDNESS_JSON,
        normalized_value: int | None = None,
    ) -> None:
        self.frame_counts = iter(frame_counts)
        self.fail_normalization = fail_normalization
        self.output_loudness_json = output_loudness_json
        self.normalized_value = normalized_value
        self.commands: list[list[str]] = []
        self.normalization_count = 0

    def __call__(self, command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[-3:] == ["-f", "null", "-"]:
            source = Path(command[command.index("-i") + 1])
            payload = (
                SOURCE_LOUDNESS_JSON
                if source.name == "assembled-source.wav"
                else self.output_loudness_json
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr=payload)
        self.normalization_count += 1
        if self.normalization_count == self.fail_normalization:
            return subprocess.CompletedProcess(command, 9, stdout="", stderr="normalization failed")
        destination = Path(command[-1])
        if destination.name == "normalized-program.wav":
            source = Path(command[command.index("-i") + 1])
            if self.normalized_value is None:
                shutil.copyfile(source, destination)
            else:
                with wave.open(str(source), "rb") as wav:
                    frames = wav.getnframes()
                write_wav(destination, frames, value=self.normalized_value)
        else:
            write_wav(destination, next(self.frame_counts), value=1000 + self.normalization_count)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


class PiperVoiceoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.model_dir = self.root / "models"
        self.model_dir.mkdir()
        self.model_path = self.model_dir / "voice.onnx"
        self.config_path = self.model_dir / "voice.onnx.json"
        self.model_path.write_bytes(b"model bytes")
        self.config_path.write_bytes(b'{"audio":{"sample_rate":22050}}')
        self.manifest = self.root / "models.json"
        self._write_manifest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_manifest(self) -> None:
        def entry(role: str, path: Path) -> dict[str, object]:
            contents = path.read_bytes()
            return {
                "role": role,
                "filename": path.name,
                "size_bytes": len(contents),
                "sha256": hashlib.sha256(contents).hexdigest(),
                "url": f"https://example.invalid/{path.name}",
            }

        payload = {
            "schema_version": 1,
            "default_model": "test-voice",
            "models": {
                "test-voice": {
                    "piper_tts_version": "1.4.2",
                    "source": {"repository": "test", "revision": "fixed"},
                    "files": [entry("model", self.model_path), entry("config", self.config_path)],
                }
            },
        }
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")

    def render(
        self,
        beats: list[dict[str, object]],
        frame_counts: list[int],
        *,
        lead_in_seconds: float = 0.0,
        voice: FakeVoice | None = None,
        ffmpeg: FakeFFmpeg | None = None,
    ) -> tuple[dict[str, object], FakeVoice, FakeFFmpeg, Path, Path, mock.Mock]:
        output = self.root / "narration.wav"
        timing = self.root / "narration-timing.json"
        fake_voice = voice or FakeVoice()
        fake_ffmpeg = ffmpeg or FakeFFmpeg(frame_counts)
        loader = mock.Mock(return_value=fake_voice)
        report = piper_voiceover.render_voiceover(
            beats,
            output,
            timing,
            model_dir=self.model_dir,
            manifest_path=self.manifest,
            lead_in_seconds=lead_in_seconds,
            voice_loader=loader,
            command_runner=fake_ffmpeg,
        )
        return report, fake_voice, fake_ffmpeg, output, timing, loader

    def test_schedule_expands_only_overrun_beats_and_preserves_order(self) -> None:
        beats = piper_voiceover.normalize_beats(
            [
                {"id": "hook", "text": "Hook", "duration": 1},
                {"id": "proof", "text": "Proof", "duration": 0.5},
            ]
        )
        schedule = piper_voiceover.schedule_beats(beats, [60_000, 12_000])

        self.assertEqual([row["beat_id"] for row in schedule], ["hook", "proof"])
        self.assertEqual(schedule[0]["beat_start_frame"], 0)
        self.assertEqual(schedule[0]["beat_end_frame"], 60_000)
        self.assertTrue(schedule[0]["expanded"])
        self.assertEqual(schedule[1]["beat_start_frame"], 60_000)
        self.assertEqual(schedule[1]["beat_end_frame"], 84_000)
        self.assertFalse(schedule[1]["expanded"])
        self.assertEqual(schedule[1]["slack_frames"], 12_000)

    def test_model_hash_mismatch_fails_before_voice_loading_or_output(self) -> None:
        original = self.model_path.read_bytes()
        self.model_path.write_bytes(b"x" * len(original))
        loader = mock.Mock()
        output = self.root / "must-not-exist.wav"

        with self.assertRaisesRegex(piper_voiceover.ModelValidationError, "SHA-256 mismatch"):
            piper_voiceover.render_voiceover(
                [{"id": "a", "text": "A", "duration": 1}],
                output,
                self.root / "timing.json",
                model_dir=self.model_dir,
                manifest_path=self.manifest,
                voice_loader=loader,
                command_runner=mock.Mock(),
            )

        loader.assert_not_called()
        self.assertFalse(output.exists())

    def test_one_voice_is_reused_and_synthesis_follows_beat_order(self) -> None:
        beats = [
            {"id": "a", "narration": "First", "duration": 0.5},
            {"id": "b", "narration": "Second", "duration": 0.5},
            {"id": "c", "narration": "Third", "duration": 0.5},
        ]
        report, voice, _, _, timing, loader = self.render(beats, [12_000, 30_000, 6_000])

        loader.assert_called_once_with(self.model_path, self.config_path)
        self.assertEqual(voice.calls, ["First", "Second", "Third"])
        self.assertEqual([row["beat_id"] for row in report["beats"]], ["a", "b", "c"])
        self.assertEqual(json.loads(timing.read_text(encoding="utf-8")), report)
        self.assertEqual(report["levels"]["integrated_lufs"], -16.0)
        self.assertIn("sample_peak_dbfs", report["levels"])
        self.assertTrue(report["level_contract"]["passed"])

    def test_assembled_pcm_obeys_exact_onset_end_and_beat_boundaries(self) -> None:
        beats = [
            {"id": "a", "text": "First", "duration": 0.5},
            {"id": "b", "text": "Second", "duration": 0.25},
        ]
        report, _, _, output, _, _ = self.render(beats, [9_600, 14_400], lead_in_seconds=0.1)
        first, second = report["beats"]

        self.assertEqual(
            (first["beat_start_frame"], first["onset_frame"], first["end_frame"], first["beat_end_frame"]),
            (0, 4_800, 14_400, 24_000),
        )
        self.assertEqual(
            (second["beat_start_frame"], second["onset_frame"], second["end_frame"], second["beat_end_frame"]),
            (24_000, 28_800, 43_200, 43_200),
        )
        with wave.open(str(output), "rb") as wav:
            self.assertEqual((wav.getframerate(), wav.getnchannels(), wav.getsampwidth()), (48_000, 1, 2))
            self.assertEqual(wav.getnframes(), 43_200)
            pcm = wav.readframes(wav.getnframes())
        samples = memoryview(pcm).cast("h")
        self.assertEqual(samples[4_799], 0)
        self.assertNotEqual(samples[4_800], 0)
        self.assertNotEqual(samples[14_399], 0)
        self.assertEqual(samples[14_400], 0)
        self.assertEqual(samples[28_799], 0)
        self.assertNotEqual(samples[28_800], 0)
        self.assertNotEqual(samples[43_199], 0)

    def test_synthesis_failure_propagates_and_never_publishes_partial_files(self) -> None:
        voice = FakeVoice(fail_on="Second")
        ffmpeg = FakeFFmpeg([9_600])
        output = self.root / "narration.wav"
        timing = self.root / "timing.json"

        with self.assertRaisesRegex(piper_voiceover.SynthesisError, "synthetic Piper failure"):
            piper_voiceover.render_voiceover(
                [
                    {"id": "a", "text": "First", "duration": 0.5},
                    {"id": "b", "text": "Second", "duration": 0.5},
                    {"id": "c", "text": "Third", "duration": 0.5},
                ],
                output,
                timing,
                model_dir=self.model_dir,
                manifest_path=self.manifest,
                voice_loader=mock.Mock(return_value=voice),
                command_runner=ffmpeg,
            )

        self.assertEqual(voice.calls, ["First", "Second"])
        self.assertEqual(len(ffmpeg.commands), 1)
        self.assertFalse(output.exists())
        self.assertFalse(timing.exists())

    def test_ffmpeg_failure_propagates_and_command_contract_has_no_time_stretch(self) -> None:
        ffmpeg = FakeFFmpeg([], fail_normalization=1)
        with self.assertRaisesRegex(piper_voiceover.AudioToolError, "normalization failed"):
            self.render(
                [{"id": "a", "text": "First", "duration": 0.5}],
                [],
                ffmpeg=ffmpeg,
            )

        command = ffmpeg.commands[0]
        self.assertEqual(command[0], "ffmpeg")
        self.assertEqual(command[command.index("-ac") + 1], "1")
        self.assertEqual(command[command.index("-ar") + 1], "48000")
        self.assertEqual(command[command.index("-c:a") + 1], "pcm_s16le")
        self.assertNotIn("atempo", " ".join(command))
        self.assertFalse((self.root / "narration.wav").exists())

    def test_ffmpeg_loudness_contract_is_measured_whole_program_and_exact_length(self) -> None:
        _, _, ffmpeg, output, _, _ = self.render(
            [{"id": "a", "text": "First", "duration": 0.5}], [9_600]
        )
        analysis_commands = [command for command in ffmpeg.commands if command[-3:] == ["-f", "null", "-"]]
        self.assertEqual(len(analysis_commands), 2)
        self.assertEqual(
            [Path(command[command.index("-i") + 1]).name for command in analysis_commands],
            ["assembled-source.wav", "assembled.wav"],
        )
        self.assertIn("loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json", analysis_commands[0])

        apply_command = next(
            command
            for command in ffmpeg.commands
            if any("measured_I=" in token for token in command)
        )
        filters = apply_command[apply_command.index("-filter:a") + 1]
        self.assertIn("measured_I=-6.250000", filters)
        self.assertIn("measured_TP=0.000000", filters)
        self.assertIn("linear=true", filters)
        self.assertIn("aresample=48000", filters)
        self.assertIn("atrim=end_sample=24000", filters)
        self.assertIn("apad=whole_len=24000", filters)
        self.assertEqual(apply_command[apply_command.index("-frames:a") + 1], "24000")
        self.assertEqual(apply_command[apply_command.index("-c:a") + 1], "pcm_s16le")
        self.assertNotIn("atempo", filters)
        self.assertNotEqual(apply_command[apply_command.index("-i") + 1], str(output))

    def test_unsafe_verified_levels_fail_closed_without_publishing(self) -> None:
        unsafe = json.dumps(
            {
                "input_i": "-16.0",
                "input_tp": "+0.20",
                "input_lra": "3.0",
                "input_thresh": "-26.0",
            }
        )
        ffmpeg = FakeFFmpeg([9_600], output_loudness_json=unsafe)

        with self.assertRaisesRegex(piper_voiceover.AudioToolError, "true peak 0.20 dBTP"):
            self.render(
                [{"id": "a", "text": "First", "duration": 0.5}],
                [9_600],
                ffmpeg=ffmpeg,
            )

        self.assertFalse((self.root / "narration.wav").exists())
        self.assertFalse((self.root / "narration-timing.json").exists())

    def test_unsafe_sample_peak_fails_closed_even_when_loudnorm_report_is_safe(self) -> None:
        ffmpeg = FakeFFmpeg([9_600], normalized_value=32_767)

        with self.assertRaisesRegex(piper_voiceover.AudioToolError, "sample peak -0.00 dBFS"):
            self.render(
                [{"id": "a", "text": "First", "duration": 0.5}],
                [9_600],
                ffmpeg=ffmpeg,
            )

        self.assertFalse((self.root / "narration.wav").exists())
        self.assertFalse((self.root / "narration-timing.json").exists())

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required")
    def test_real_ffmpeg_corrects_clipped_source_and_keeps_exact_frames(self) -> None:
        report, _, _, output, _, _ = self.render(
            [{"id": "a", "text": "Clipped source", "duration": 3.2}],
            [],
            lead_in_seconds=0.1,
            voice=ClippedVoice(),
            ffmpeg=subprocess.run,
        )

        self.assertEqual(report["total_frames"], 153_600)
        beat = report["beats"][0]
        self.assertEqual(
            (beat["beat_start_frame"], beat["onset_frame"], beat["end_frame"], beat["beat_end_frame"]),
            (0, 4_800, 148_800, 153_600),
        )
        self.assertGreaterEqual(report["levels"]["integrated_lufs"], -17.0)
        self.assertLessEqual(report["levels"]["integrated_lufs"], -15.0)
        self.assertLessEqual(report["levels"]["true_peak_dbfs"], -1.0)
        self.assertLessEqual(report["levels"]["sample_peak_dbfs"], -1.0)
        with wave.open(str(output), "rb") as wav:
            self.assertEqual((wav.getframerate(), wav.getnchannels(), wav.getsampwidth()), (48_000, 1, 2))
            self.assertEqual(wav.getnframes(), 153_600)
            samples = memoryview(wav.readframes(wav.getnframes())).cast("h")
        self.assertTrue(all(sample == 0 for sample in samples[:4_800]))
        self.assertTrue(any(sample != 0 for sample in samples[4_800:4_900]))
        self.assertTrue(all(sample == 0 for sample in samples[148_800:]))

    def test_provisioning_contract_is_declarative_and_pinned(self) -> None:
        contract = piper_voiceover.provisioning_contract(
            self.model_dir, manifest_path=self.manifest
        )
        self.assertFalse(contract["network_allowed_during_render"])
        self.assertEqual(contract["piper_tts_version"], "1.4.2")
        self.assertEqual([item["role"] for item in contract["files"]], ["model", "config"])
        self.assertTrue(all(len(item["sha256"]) == 64 for item in contract["files"]))


if __name__ == "__main__":
    unittest.main()

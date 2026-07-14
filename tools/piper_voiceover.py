#!/usr/bin/env python3
"""Offline, beat-aligned Piper narration rendering.

Rendering never downloads assets. Call :func:`provisioning_contract` from a
separate provisioning step, then validate the resulting local files before use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


SAMPLE_RATE = 48_000
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1
TARGET_INTEGRATED_LUFS = -16.0
TARGET_LOUDNESS_RANGE_LU = 11.0
TARGET_TRUE_PEAK_DBTP = -1.5
TARGET_SAMPLE_PEAK_DBFS = -1.5
MIN_INTEGRATED_LUFS = -17.0
MAX_INTEGRATED_LUFS = -15.0
MAX_TRUE_PEAK_DBTP = -1.0
MAX_SAMPLE_PEAK_DBFS = -1.0
DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "config" / "piper_models.json"


class PiperNarrationError(RuntimeError):
    """Base class for fail-closed narration errors."""


class BeatValidationError(PiperNarrationError):
    """Raised when the requested beat schedule is unsafe or ambiguous."""


class ModelValidationError(PiperNarrationError):
    """Raised when local model assets do not exactly match the pin."""


class SynthesisError(PiperNarrationError):
    """Raised when Piper does not produce a usable beat WAV."""


class AudioToolError(PiperNarrationError):
    """Raised when FFmpeg fails or violates its output contract."""


@dataclass(frozen=True)
class ModelAsset:
    role: str
    filename: str
    size_bytes: int
    sha256: str
    url: str


@dataclass(frozen=True)
class ValidatedModel:
    model_id: str
    model_path: Path
    config_path: Path
    piper_tts_version: str
    assets: tuple[ModelAsset, ...]


@dataclass(frozen=True)
class NarrationBeat:
    beat_id: str
    text: str
    planned_frames: int
    scene_state: str = ""


@dataclass(frozen=True)
class NormalizedBeatAudio:
    beat: NarrationBeat
    path: Path
    frames: int


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
VoiceLoader = Callable[[Path, Path], Any]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelValidationError(f"Cannot read model manifest {path}: {exc}") from exc


def _model_record(manifest_path: Path, model_id: str | None) -> tuple[str, Mapping[str, Any]]:
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ModelValidationError("Unsupported Piper model manifest schema")
    selected_id = model_id or manifest.get("default_model")
    models = manifest.get("models")
    if not isinstance(selected_id, str) or not isinstance(models, dict):
        raise ModelValidationError("Model manifest has no usable default model")
    record = models.get(selected_id)
    if not isinstance(record, dict):
        raise ModelValidationError(f"Unknown Piper model: {selected_id}")
    return selected_id, record


def _assets_from_record(record: Mapping[str, Any]) -> tuple[ModelAsset, ...]:
    raw_assets = record.get("files")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise ModelValidationError("Pinned Piper model has no files")
    assets: list[ModelAsset] = []
    roles: set[str] = set()
    for raw in raw_assets:
        if not isinstance(raw, dict):
            raise ModelValidationError("Invalid Piper model file entry")
        try:
            asset = ModelAsset(
                role=str(raw["role"]),
                filename=str(raw["filename"]),
                size_bytes=int(raw["size_bytes"]),
                sha256=str(raw["sha256"]).lower(),
                url=str(raw["url"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelValidationError("Incomplete Piper model file entry") from exc
        if Path(asset.filename).name != asset.filename:
            raise ModelValidationError(f"Model filename must be a basename: {asset.filename}")
        if asset.role in roles or asset.role not in {"model", "config"}:
            raise ModelValidationError(f"Invalid or duplicate model role: {asset.role}")
        if asset.size_bytes <= 0 or not re.fullmatch(r"[0-9a-f]{64}", asset.sha256):
            raise ModelValidationError(f"Invalid size/hash pin for {asset.filename}")
        if not asset.url.startswith("https://"):
            raise ModelValidationError(f"Provisioning URL must use HTTPS: {asset.filename}")
        roles.add(asset.role)
        assets.append(asset)
    if roles != {"model", "config"}:
        raise ModelValidationError("Pinned Piper model requires model and config files")
    return tuple(assets)


def provisioning_contract(
    model_dir: str | Path,
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Return download instructions without network or target-directory writes."""
    manifest_file = Path(manifest_path)
    selected_id, record = _model_record(manifest_file, model_id)
    assets = _assets_from_record(record)
    target_dir = Path(model_dir)
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return {
        "schema_version": 1,
        "model_id": selected_id,
        "piper_tts_version": str(record.get("piper_tts_version", "")),
        "network_allowed_during_render": False,
        "source": dict(source),
        "files": [
            {
                "role": asset.role,
                "url": asset.url,
                "destination": str(target_dir / asset.filename),
                "size_bytes": asset.size_bytes,
                "sha256": asset.sha256,
            }
            for asset in assets
        ],
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_model_assets(
    model_dir: str | Path,
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    model_id: str | None = None,
) -> ValidatedModel:
    """Validate every local model byte before Piper can be loaded."""
    selected_id, record = _model_record(Path(manifest_path), model_id)
    assets = _assets_from_record(record)
    paths: dict[str, Path] = {}
    for asset in assets:
        path = Path(model_dir) / asset.filename
        try:
            actual_size = path.stat().st_size
        except OSError as exc:
            raise ModelValidationError(f"Missing Piper {asset.role} file: {path}") from exc
        if not path.is_file() or actual_size != asset.size_bytes:
            raise ModelValidationError(
                f"Piper {asset.role} size mismatch for {path}: "
                f"expected {asset.size_bytes}, got {actual_size}"
            )
        actual_hash = _sha256(path)
        if actual_hash != asset.sha256:
            raise ModelValidationError(
                f"Piper {asset.role} SHA-256 mismatch for {path}: "
                f"expected {asset.sha256}, got {actual_hash}"
            )
        paths[asset.role] = path
    version = str(record.get("piper_tts_version", ""))
    if version != "1.4.2":
        raise ModelValidationError(f"Unsupported piper-tts pin in manifest: {version}")
    return ValidatedModel(selected_id, paths["model"], paths["config"], version, assets)


def seconds_to_frames(seconds: Any, *, sample_rate: int = SAMPLE_RATE) -> int:
    try:
        value = Decimal(str(seconds))
    except (InvalidOperation, ValueError) as exc:
        raise BeatValidationError(f"Invalid duration: {seconds!r}") from exc
    if not value.is_finite() or value <= 0:
        raise BeatValidationError(f"Duration must be finite and positive: {seconds!r}")
    return int((value * sample_rate).to_integral_value(rounding=ROUND_HALF_UP))


def normalize_beats(beats: Iterable[Mapping[str, Any]]) -> list[NarrationBeat]:
    """Validate ordered integration input and convert durations to exact frames."""
    normalized: list[NarrationBeat] = []
    seen: set[str] = set()
    for index, raw in enumerate(beats):
        if not isinstance(raw, Mapping):
            raise BeatValidationError(f"Beat {index} is not an object")
        beat_id = str(raw.get("id", raw.get("beat_id", ""))).strip()
        text = str(raw.get("narration", raw.get("text", ""))).strip()
        if not beat_id:
            raise BeatValidationError(f"Beat {index} has no id")
        if beat_id in seen:
            raise BeatValidationError(f"Duplicate beat id: {beat_id}")
        if not text:
            raise BeatValidationError(f"Beat {beat_id} has no narration text")
        if "duration" not in raw:
            raise BeatValidationError(f"Beat {beat_id} has no duration")
        normalized.append(
            NarrationBeat(
                beat_id,
                text,
                seconds_to_frames(raw["duration"]),
                str(raw.get("scene_state", "")).strip(),
            )
        )
        seen.add(beat_id)
    if not normalized:
        raise BeatValidationError("At least one narration beat is required")
    return normalized


def schedule_beats(
    beats: Sequence[NarrationBeat],
    speech_frames: Sequence[int],
    *,
    lead_in_seconds: float = 0.0,
    boundary_fps: int | None = None,
) -> list[dict[str, Any]]:
    """Expand only overrun beats and schedule all boundaries on sample frames."""
    if len(beats) != len(speech_frames):
        raise BeatValidationError("Beat/audio count mismatch")
    if lead_in_seconds < 0:
        raise BeatValidationError("Lead-in cannot be negative")
    if boundary_fps is not None and (
        not isinstance(boundary_fps, int)
        or isinstance(boundary_fps, bool)
        or boundary_fps <= 0
        or SAMPLE_RATE % boundary_fps
    ):
        raise BeatValidationError("Boundary FPS must be a positive divisor of 48000")
    lead_frames = 0 if lead_in_seconds == 0 else seconds_to_frames(lead_in_seconds)
    boundary_frames = SAMPLE_RATE // boundary_fps if boundary_fps else 1
    cursor = 0
    scheduled: list[dict[str, Any]] = []
    for beat, frames in zip(beats, speech_frames):
        if not isinstance(frames, int) or isinstance(frames, bool) or frames <= 0:
            raise BeatValidationError(f"Beat {beat.beat_id} has invalid speech frames: {frames!r}")
        required_frames = lead_frames + frames
        window_frames = max(beat.planned_frames, required_frames)
        window_frames = int(math.ceil(window_frames / boundary_frames) * boundary_frames)
        onset = cursor + lead_frames
        speech_end = onset + frames
        beat_end = cursor + window_frames
        slack = beat_end - speech_end
        scheduled.append(
            {
                "beat_id": beat.beat_id,
                "text": beat.text,
                "scene_state": beat.scene_state,
                "beat_start": cursor / SAMPLE_RATE,
                "beat_end": beat_end / SAMPLE_RATE,
                "onset": onset / SAMPLE_RATE,
                "end": speech_end / SAMPLE_RATE,
                "slack": slack / SAMPLE_RATE,
                "beat_start_frame": cursor,
                "beat_end_frame": beat_end,
                "onset_frame": onset,
                "end_frame": speech_end,
                "slack_frames": slack,
                "planned_frames": beat.planned_frames,
                "speech_frames": frames,
                "expanded": window_frames > beat.planned_frames,
            }
        )
        cursor = beat_end
    return scheduled


def _default_voice_loader(model_path: Path, config_path: Path) -> Any:
    try:
        installed_version = version("piper-tts")
    except PackageNotFoundError as exc:
        raise SynthesisError("piper-tts==1.4.2 is required for Piper narration") from exc
    if installed_version != "1.4.2":
        raise SynthesisError(
            f"piper-tts==1.4.2 is required; installed version is {installed_version}"
        )
    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise SynthesisError("piper-tts==1.4.2 is required for Piper narration") from exc
    return PiperVoice.load(str(model_path), config_path=str(config_path))


def _run_checked(command: list[str], runner: CommandRunner, stage: str) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise AudioToolError(f"{stage} could not start: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic output").strip()
        raise AudioToolError(f"{stage} failed ({result.returncode}): {detail}")
    return result


def ffmpeg_normalize_command(ffmpeg: str, source: Path, destination: Path) -> list[str]:
    """Return the deterministic mono PCM resampling command contract."""
    return [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map_metadata",
        "-1",
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        "-fflags",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        str(destination),
    ]


def ffmpeg_loudness_command(ffmpeg: str, source: Path) -> list[str]:
    """Return the EBU R128/true-peak measurement command contract."""
    return [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "info",
        "-nostats",
        "-i",
        str(source),
        "-filter:a",
        (
            f"loudnorm=I={TARGET_INTEGRATED_LUFS:g}:"
            f"LRA={TARGET_LOUDNESS_RANGE_LU:g}:"
            f"TP={TARGET_TRUE_PEAK_DBTP:g}:print_format=json"
        ),
        "-f",
        "null",
        "-",
    ]


def ffmpeg_apply_loudness_command(
    ffmpeg: str,
    source: Path,
    destination: Path,
    frames: int,
    measurement: Mapping[str, float],
) -> list[str]:
    """Return a measured whole-program loudnorm pass with an exact sample extent."""
    if not isinstance(frames, int) or isinstance(frames, bool) or frames <= 0:
        raise AudioToolError(f"Invalid loudness output frame count: {frames!r}")

    def number(name: str) -> str:
        try:
            value = float(measurement[name])
        except (KeyError, TypeError, ValueError) as exc:
            raise AudioToolError(f"Missing loudness measurement: {name}") from exc
        if not math.isfinite(value):
            raise AudioToolError(f"Non-finite loudness measurement: {name}")
        return format(value, ".6f")

    loudnorm = ":".join(
        (
            f"loudnorm=I={TARGET_INTEGRATED_LUFS:g}",
            f"LRA={TARGET_LOUDNESS_RANGE_LU:g}",
            f"TP={TARGET_TRUE_PEAK_DBTP:g}",
            f"measured_I={number('integrated_lufs')}",
            f"measured_LRA={number('loudness_range_lu')}",
            f"measured_TP={number('true_peak_dbfs')}",
            f"measured_thresh={number('threshold_lufs')}",
            f"offset={number('target_offset_lu')}",
            "linear=true",
            "print_format=summary",
        )
    )
    filters = (
        f"{loudnorm},aresample={SAMPLE_RATE},"
        f"atrim=end_sample={frames},apad=whole_len={frames}"
    )
    return [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map_metadata",
        "-1",
        "-vn",
        "-filter:a",
        filters,
        "-frames:a",
        str(frames),
        "-ac",
        str(CHANNELS),
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        "-fflags",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        str(destination),
    ]


def _wave_frames(path: Path) -> tuple[int, bytes]:
    try:
        with wave.open(str(path), "rb") as wav:
            actual = (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype())
            expected = (SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH_BYTES, "NONE")
            if actual != expected:
                raise AudioToolError(f"Normalized WAV contract mismatch for {path}: {actual}, expected {expected}")
            frames = wav.getnframes()
            pcm = wav.readframes(frames)
    except (OSError, EOFError, wave.Error) as exc:
        raise AudioToolError(f"Cannot read normalized WAV {path}: {exc}") from exc
    if frames <= 0 or len(pcm) != frames * SAMPLE_WIDTH_BYTES:
        raise AudioToolError(f"Normalized WAV has invalid PCM length: {path}")
    return frames, pcm


def _synthesize_beat(voice: Any, text: str, destination: Path) -> None:
    wav_file: wave.Wave_write | None = None
    try:
        wav_file = wave.open(str(destination), "wb")
        voice.synthesize_wav(text, wav_file)
    except Exception as exc:
        if wav_file is not None:
            try:
                wav_file.close()
            except Exception:
                pass
        raise SynthesisError(f"Piper synthesis failed: {exc}") from exc
    try:
        wav_file.close()
    except Exception as exc:
        raise SynthesisError(f"Piper synthesis produced an invalid WAV: {exc}") from exc
    if not destination.is_file() or destination.stat().st_size <= 44:
        raise SynthesisError("Piper synthesis produced no usable WAV data")


def _assemble_audio(
    normalized: Sequence[NormalizedBeatAudio],
    schedule: Sequence[Mapping[str, Any]],
    destination: Path,
) -> None:
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(CHANNELS)
        output.setsampwidth(SAMPLE_WIDTH_BYTES)
        output.setframerate(SAMPLE_RATE)
        cursor = 0
        for audio, timing in zip(normalized, schedule):
            onset = int(timing["onset_frame"])
            if onset < cursor:
                raise AudioToolError(f"Overlapping audio at beat {audio.beat.beat_id}")
            output.writeframesraw(b"\x00" * ((onset - cursor) * SAMPLE_WIDTH_BYTES))
            frames, pcm = _wave_frames(audio.path)
            if frames != audio.frames:
                raise AudioToolError(f"Beat audio changed during assembly: {audio.beat.beat_id}")
            output.writeframesraw(pcm)
            cursor = onset + frames
            beat_end = int(timing["beat_end_frame"])
            output.writeframesraw(b"\x00" * ((beat_end - cursor) * SAMPLE_WIDTH_BYTES))
            cursor = beat_end


def _parse_loudness(
    result: subprocess.CompletedProcess[str], *, require_target_offset: bool = False
) -> dict[str, float]:
    candidates = re.findall(r"\{[^{}]*\}", result.stderr or "", flags=re.DOTALL)
    if not candidates:
        raise AudioToolError("FFmpeg loudness analysis returned no JSON")
    try:
        payload = json.loads(candidates[-1])
        values = {
            "integrated_lufs": float(payload["input_i"]),
            "true_peak_dbfs": float(payload["input_tp"]),
            "loudness_range_lu": float(payload["input_lra"]),
            "threshold_lufs": float(payload["input_thresh"]),
        }
        if require_target_offset:
            values["target_offset_lu"] = float(payload["target_offset"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AudioToolError("FFmpeg loudness JSON is incomplete") from exc
    if not all(math.isfinite(value) for value in values.values()):
        raise AudioToolError("FFmpeg loudness analysis returned non-finite values")
    return values


def _sample_peak_dbfs(path: Path) -> float:
    _, pcm = _wave_frames(path)
    peak = max((abs(sample[0]) for sample in struct.iter_unpack("<h", pcm)), default=0)
    if peak == 0:
        raise AudioToolError("Assembled narration is silent")
    return 20.0 * math.log10(peak / 32768.0)


def _gate_to_schedule_windows(
    source: Path,
    destination: Path,
    schedule: Sequence[Mapping[str, Any]],
) -> None:
    """Remove filter pre/post-ringing outside every scheduled speech window."""
    frames, pcm = _wave_frames(source)
    gated = bytearray(len(pcm))
    for timing in schedule:
        onset = int(timing["onset_frame"])
        end = int(timing["end_frame"])
        if not 0 <= onset < end <= frames:
            raise AudioToolError(f"Invalid speech window during loudness gating: {onset}:{end}")
        byte_start = onset * SAMPLE_WIDTH_BYTES
        byte_end = end * SAMPLE_WIDTH_BYTES
        gated[byte_start:byte_end] = pcm[byte_start:byte_end]
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(CHANNELS)
        output.setsampwidth(SAMPLE_WIDTH_BYTES)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(gated)


def _validate_output_levels(levels: Mapping[str, float]) -> None:
    integrated = float(levels["integrated_lufs"])
    true_peak = float(levels["true_peak_dbfs"])
    sample_peak = float(levels["sample_peak_dbfs"])
    failures: list[str] = []
    if not MIN_INTEGRATED_LUFS <= integrated <= MAX_INTEGRATED_LUFS:
        failures.append(
            f"integrated loudness {integrated:.2f} LUFS is outside "
            f"[{MIN_INTEGRATED_LUFS:.1f}, {MAX_INTEGRATED_LUFS:.1f}]"
        )
    if true_peak > MAX_TRUE_PEAK_DBTP:
        failures.append(
            f"true peak {true_peak:.2f} dBTP exceeds {MAX_TRUE_PEAK_DBTP:.1f} dBTP"
        )
    if sample_peak > MAX_SAMPLE_PEAK_DBFS:
        failures.append(
            f"sample peak {sample_peak:.2f} dBFS exceeds {MAX_SAMPLE_PEAK_DBFS:.1f} dBFS"
        )
    if failures:
        raise AudioToolError("Unsafe normalized narration: " + "; ".join(failures))


def render_voiceover(
    beats: Iterable[Mapping[str, Any]],
    output_wav: str | Path,
    timing_manifest: str | Path,
    *,
    model_dir: str | Path,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    model_id: str | None = None,
    ffmpeg: str = "ffmpeg",
    lead_in_seconds: float = 0.0,
    boundary_fps: int | None = None,
    voice_loader: VoiceLoader | None = None,
    command_runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    """Render ordered narration beats into one exact-window PCM WAV.

    Existing outputs are replaced only after model validation, all synthesis,
    normalization, assembly, and level analysis have succeeded.
    """
    normalized_beats = normalize_beats(beats)
    validated = validate_model_assets(model_dir, manifest_path=manifest_path, model_id=model_id)
    output_path = Path(output_wav)
    timing_path = Path(timing_manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    loader = voice_loader or _default_voice_loader

    with tempfile.TemporaryDirectory(prefix="piper-voiceover-", dir=output_path.parent) as temp_name:
        temp_dir = Path(temp_name)
        try:
            voice = loader(validated.model_path, validated.config_path)
        except PiperNarrationError:
            raise
        except Exception as exc:
            raise SynthesisError(f"Could not load Piper voice: {exc}") from exc

        rendered: list[NormalizedBeatAudio] = []
        for index, beat in enumerate(normalized_beats):
            raw_path = temp_dir / f"beat-{index:04d}-raw.wav"
            normalized_path = temp_dir / f"beat-{index:04d}-48k.wav"
            _synthesize_beat(voice, beat.text, raw_path)
            command = ffmpeg_normalize_command(ffmpeg, raw_path, normalized_path)
            _run_checked(command, command_runner, f"FFmpeg normalization for {beat.beat_id}")
            frames, _ = _wave_frames(normalized_path)
            rendered.append(NormalizedBeatAudio(beat, normalized_path, frames))

        schedule = schedule_beats(
            normalized_beats,
            [audio.frames for audio in rendered],
            lead_in_seconds=lead_in_seconds,
            boundary_fps=boundary_fps,
        )
        assembled_source = temp_dir / "assembled-source.wav"
        _assemble_audio(rendered, schedule, assembled_source)
        total_frames, _ = _wave_frames(assembled_source)
        expected_frames = int(schedule[-1]["beat_end_frame"])
        if total_frames != expected_frames:
            raise AudioToolError(
                f"Assembled boundary mismatch: expected {expected_frames} frames, got {total_frames}"
            )

        source_loudness_result = _run_checked(
            ffmpeg_loudness_command(ffmpeg, assembled_source),
            command_runner,
            "FFmpeg source loudness analysis",
        )
        source_levels = _parse_loudness(source_loudness_result, require_target_offset=True)
        source_levels["sample_peak_dbfs"] = _sample_peak_dbfs(assembled_source)
        normalized_program = temp_dir / "normalized-program.wav"
        _run_checked(
            ffmpeg_apply_loudness_command(
                ffmpeg, assembled_source, normalized_program, expected_frames, source_levels
            ),
            command_runner,
            "FFmpeg measured loudness normalization",
        )
        normalized_frames, _ = _wave_frames(normalized_program)
        if normalized_frames != expected_frames:
            raise AudioToolError(
                f"Normalized boundary mismatch: expected {expected_frames} frames, "
                f"got {normalized_frames}"
            )
        staged_wav = temp_dir / "assembled.wav"
        _gate_to_schedule_windows(normalized_program, staged_wav, schedule)
        total_frames, _ = _wave_frames(staged_wav)
        if total_frames != expected_frames:
            raise AudioToolError(
                f"Normalized boundary mismatch: expected {expected_frames} frames, got {total_frames}"
            )

        loudness_result = _run_checked(
            ffmpeg_loudness_command(ffmpeg, staged_wav),
            command_runner,
            "FFmpeg output loudness verification",
        )
        levels = _parse_loudness(loudness_result)
        levels["sample_peak_dbfs"] = _sample_peak_dbfs(staged_wav)
        _validate_output_levels(levels)
        audio_sha256 = _sha256(staged_wav)
        report = {
            "schema_version": 2,
            "engine": "piper",
            "status": "rendered",
            "model_id": validated.model_id,
            "piper_tts_version": validated.piper_tts_version,
            "model_sha256": next(
                asset.sha256 for asset in validated.assets if asset.role == "model"
            ),
            "model_assets": [
                {
                    "role": asset.role,
                    "filename": asset.filename,
                    "size_bytes": asset.size_bytes,
                    "sha256": asset.sha256,
                }
                for asset in validated.assets
            ],
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "sample_width_bytes": SAMPLE_WIDTH_BYTES,
            "total_frames": total_frames,
            "duration": total_frames / SAMPLE_RATE,
            "audio_sha256": audio_sha256,
            "levels": levels,
            "level_contract": {
                "target_integrated_lufs": TARGET_INTEGRATED_LUFS,
                "target_true_peak_dbtp": TARGET_TRUE_PEAK_DBTP,
                "target_sample_peak_dbfs": TARGET_SAMPLE_PEAK_DBFS,
                "min_integrated_lufs": MIN_INTEGRATED_LUFS,
                "max_integrated_lufs": MAX_INTEGRATED_LUFS,
                "max_true_peak_dbtp": MAX_TRUE_PEAK_DBTP,
                "max_sample_peak_dbfs": MAX_SAMPLE_PEAK_DBFS,
                "passed": True,
            },
            "normalization": {
                "method": "two_pass_loudnorm_with_schedule_gate",
                "source_levels": source_levels,
            },
            "beats": schedule,
        }
        staged_manifest = temp_dir / "timing.json"
        staged_manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(staged_wav, output_path)
        os.replace(staged_manifest, timing_path)
    return report


def _load_beats(path: Path) -> list[Mapping[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BeatValidationError(f"Cannot read beats JSON {path}: {exc}") from exc
    beats = payload.get("beats") if isinstance(payload, dict) else payload
    if not isinstance(beats, list):
        raise BeatValidationError("Beats JSON must be a list or an object with a beats list")
    return beats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    provision = subparsers.add_parser("provision-contract")
    provision.add_argument("--model-dir", required=True)
    provision.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    provision.add_argument("--model-id")
    validate = subparsers.add_parser("validate-model")
    validate.add_argument("--model-dir", required=True)
    validate.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    validate.add_argument("--model-id")
    render = subparsers.add_parser("render")
    render.add_argument("--beats", required=True)
    render.add_argument("--output", required=True)
    render.add_argument("--timing-manifest", required=True)
    render.add_argument("--model-dir", required=True)
    render.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    render.add_argument("--model-id")
    render.add_argument("--ffmpeg", default="ffmpeg")
    render.add_argument("--lead-in", type=float, default=0.0)
    render.add_argument("--boundary-fps", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "provision-contract":
            result = provisioning_contract(args.model_dir, manifest_path=args.manifest, model_id=args.model_id)
        elif args.command == "validate-model":
            validated = validate_model_assets(args.model_dir, manifest_path=args.manifest, model_id=args.model_id)
            result = {"status": "valid", "model_id": validated.model_id}
        else:
            result = render_voiceover(
                _load_beats(Path(args.beats)),
                args.output,
                args.timing_manifest,
                model_dir=args.model_dir,
                manifest_path=args.manifest,
                model_id=args.model_id,
                ffmpeg=args.ffmpeg,
                lead_in_seconds=args.lead_in,
                boundary_fps=args.boundary_fps,
            )
    except PiperNarrationError as exc:
        raise SystemExit(f"Piper narration failed: {exc}") from exc
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

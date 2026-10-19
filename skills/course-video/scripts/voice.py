#!/usr/bin/env python3
"""Synthesize narration for every beat of a short and write timing.json.

    python voice.py <short_dir> [--engine edge-tts|piper|say|openai|none] [--voice NAME]

Each beat in scene.py's BEATS list becomes one audio clip under
<short_dir>/audio/. Clips are cached by (engine, voice, rate, text), so editing
one beat only re-synthesizes that beat. timing.json records each clip's
duration (plus a short breath) and, for edge-tts, per-word timings that the
renderer turns into tightly synced captions.

Engines:
  edge-tts  natural neural voices, free, needs network (default)
  piper     fully offline neural voice (downloads a ~60 MB model once)
  say       macOS built-in voices, offline
  openai    OpenAI TTS (needs OPENAI_API_KEY)
  none      silent: durations are estimated from word count
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import beatlib  # noqa: E402

DEFAULT_VOICES = {
    "edge-tts": "en-US-AndrewMultilingualNeural",
    "piper": "en_US-lessac-medium",
    "say": "Samantha",
    "openai": "alloy",
    "none": "",
}
BREATH_SECONDS = 0.3
PIPER_MODELS = {
    "en_US-lessac-medium": "en/en_US/lessac/medium",
    "en_US-ryan-high": "en/en_US/ryan/high",
    "en_US-lessac-high": "en/en_US/lessac/high",
    "en_US-ljspeech-medium": "en/en_US/ljspeech/medium",
}
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


class VoiceError(RuntimeError):
    pass


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return float(out.stdout.strip())
    except ValueError as exc:
        raise VoiceError(f"could not read duration of {path}: {out.stderr.strip()}") from exc


# ---------------------------------------------------------------- engines


def synth_edge(text: str, voice: str, rate: str, out: Path) -> list[list]:
    try:
        import edge_tts
    except ImportError as exc:
        raise VoiceError("edge-tts is not installed (pip install edge-tts)") from exc

    async def run() -> list[list]:
        words: list[list] = []
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        with out.open("wb") as fh:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    fh.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 1e7
                    words.append([round(start, 3), round(start + chunk["duration"] / 1e7, 3), chunk["text"]])
        return words

    try:
        return asyncio.run(run())
    except Exception as exc:  # network errors, bad voice names
        out.unlink(missing_ok=True)
        raise VoiceError(f"edge-tts failed ({exc}); check network access or pick --engine piper/say/none") from exc


def piper_model(voice: str) -> Path:
    if voice not in PIPER_MODELS:
        raise VoiceError(f"unknown piper voice {voice!r}; choose one of {', '.join(PIPER_MODELS)}")
    cache = Path(os.environ.get("COURSE_SHORTS_CACHE", Path.home() / ".cache" / "course-shorts")) / "piper"
    cache.mkdir(parents=True, exist_ok=True)
    model = cache / f"{voice}.onnx"
    for suffix in (".onnx", ".onnx.json"):
        target = cache / f"{voice}{suffix}"
        if not target.exists():
            url = f"{PIPER_BASE}/{PIPER_MODELS[voice]}/{voice}{suffix}"
            print(f"downloading piper voice {target.name} ...", file=sys.stderr)
            tmp = target.with_suffix(target.suffix + ".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(target)
    return model


def synth_piper(text: str, voice: str, out: Path) -> None:
    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise VoiceError("piper-tts is not installed (pip install piper-tts)") from exc
    model = PiperVoice.load(str(piper_model(voice)))
    with wave.open(str(out), "wb") as wav:
        model.synthesize_wav(text, wav)


def synth_say(text: str, voice: str, out: Path) -> None:
    if not shutil.which("say"):
        raise VoiceError("'say' is only available on macOS")
    aiff = out.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(aiff), str(out)], check=True)
    aiff.unlink(missing_ok=True)


def synth_openai(text: str, voice: str, out: Path) -> None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise VoiceError("OPENAI_API_KEY is not set")
    body = json.dumps({
        "model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        "voice": voice, "input": text, "response_format": "mp3",
    }).encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        out.write_bytes(resp.read())


# ---------------------------------------------------------------- driver


def synthesize(short_dir: Path, engine: str = "edge-tts", voice: str | None = None,
               rate: str = "+0%", quiet: bool = False) -> dict:
    scene = short_dir / "scene.py"
    beats = beatlib.read_beats(scene)
    voice = voice or DEFAULT_VOICES.get(engine, "")
    audio_dir = short_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    timing = {"engine": engine, "voice": voice, "rate": rate, "beats": []}
    keep: set[str] = set()
    for beat in beats:
        entry = {"id": beat["id"], "text": beat["text"], "audio": None, "words": None}
        if engine == "none":
            entry["duration"] = round(beatlib.estimate_seconds(beat["text"]), 3)
            timing["beats"].append(entry)
            continue
        key = hashlib.sha1(f"{engine}|{voice}|{rate}|{beat['text']}".encode()).hexdigest()[:10]
        ext = ".mp3" if engine in {"edge-tts", "openai"} else ".wav"
        clip = audio_dir / f"{beat['id']}-{key}{ext}"
        words_file = clip.with_suffix(".words.json")
        keep.update({clip.name, words_file.name})
        if not clip.exists() or clip.stat().st_size == 0:
            if not quiet:
                print(f"  voice [{engine}] {beat['id']}: {beat['text'][:60]}", file=sys.stderr)
            if engine == "edge-tts":
                words = synth_edge(beat["text"], voice, rate, clip)
                words_file.write_text(json.dumps(words), encoding="utf-8")
            elif engine == "piper":
                synth_piper(beat["text"], voice, clip)
            elif engine == "say":
                synth_say(beat["text"], voice, clip)
            elif engine == "openai":
                synth_openai(beat["text"], voice, clip)
            else:
                raise VoiceError(f"unknown engine {engine!r}")
        duration = ffprobe_duration(clip)
        if duration < 0.3:
            clip.unlink(missing_ok=True)
            raise VoiceError(f"{engine} produced an empty clip for beat {beat['id']!r}")
        entry.update({
            "audio": str(clip.relative_to(short_dir)),
            "audio_seconds": round(duration, 3),
            "duration": round(duration + BREATH_SECONDS, 3),
            "words": json.loads(words_file.read_text()) if words_file.exists() else None,
        })
        timing["beats"].append(entry)
    for stale in audio_dir.iterdir():
        if stale.is_file() and stale.name not in keep:
            stale.unlink()
    timing["total_seconds"] = round(sum(b["duration"] for b in timing["beats"]), 3)
    (short_dir / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")
    return timing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("short_dir", type=Path)
    ap.add_argument("--engine", default="edge-tts", choices=sorted(DEFAULT_VOICES))
    ap.add_argument("--voice", default=None, help="voice name for the engine")
    ap.add_argument("--rate", default="+0%", help="edge-tts speaking rate, e.g. +8%%")
    args = ap.parse_args(argv)
    try:
        timing = synthesize(args.short_dir, args.engine, args.voice, args.rate)
    except (VoiceError, beatlib.BeatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{len(timing['beats'])} beats, {timing['total_seconds']:.1f}s of narration -> "
          f"{args.short_dir / 'timing.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

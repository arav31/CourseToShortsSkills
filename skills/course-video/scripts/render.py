#!/usr/bin/env python3
"""Render one short: narration -> Manim -> captions + audio mix -> MP4 -> audit.

    python render.py <short_dir> [--quality preview|final] [--voice ENGINE] [--voice-name NAME]

<short_dir> must contain scene.py (a ShortScene with a literal BEATS list).
Outputs, all inside <short_dir>:

    preview.mp4 or <short_dir name>.mp4   the video (final quality uses the dir name)
    <name>.srt                             captions with real timings
    render_report.json                     beats, layout issues, motion scan, hash
    review/<quality>-NN.png                contact sheets to look at (preview-01.png, final-01.png, ...)
    build/                                 Manim media + logs (safe to delete)

Narration: by default the timing.json from a previous run is reused when the
beat text still matches; otherwise edge-tts is tried and silence is the fallback.
Pass --voice none for an intentionally silent video.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit  # noqa: E402
import beatlib  # noqa: E402
import voice as voicelib  # noqa: E402

PRESETS = {
    "preview": {"x264": ["-preset", "veryfast", "-crf", "24"], "fps": 15},
    "final": {"x264": ["-preset", "slow", "-crf", "18"], "fps": 30},
}
# Caption band: CAPTION_ZONE bottom is y=-4.9 in a 16-unit frame -> 372 px from the bottom at 1920.
ASS_MARGIN_V, ASS_MARGIN_L, ASS_MARGIN_R = 372, 100, 190
CAPTION_MAX_CHARS = 34


class RenderError(RuntimeError):
    pass


# ---------------------------------------------------------------- narration


def ensure_timing(short_dir: Path, engine: str | None, voice: str | None, rate: str) -> dict:
    beats = beatlib.read_beats(short_dir / "scene.py")
    timing_path = short_dir / "timing.json"
    if engine is None and timing_path.exists():
        timing = json.loads(timing_path.read_text())
        texts = [b.get("text") for b in timing.get("beats", [])]
        if texts == [b["text"] for b in beats] and all(
            not b.get("audio") or (short_dir / b["audio"]).exists() for b in timing["beats"]
        ):
            return timing
        engine = timing.get("engine") or "edge-tts"
        voice = voice or timing.get("voice") or None
    if engine is None:
        engine = "edge-tts"
    try:
        return voicelib.synthesize(short_dir, engine, voice, rate)
    except voicelib.VoiceError as exc:
        if engine == "none":
            raise
        print(f"warning: {exc}\nwarning: falling back to a silent render (--voice none)", file=sys.stderr)
        return voicelib.synthesize(short_dir, "none")


# ---------------------------------------------------------------- manim


def run_manim(short_dir: Path, quality: str, timing_path: Path, trace_path: Path) -> Path:
    scene = short_dir / "scene.py"
    cls = beatlib.find_scene_class(scene)
    build = short_dir / "build"
    build.mkdir(exist_ok=True)
    out_name = f"{cls}_{quality}"
    for stale in build.rglob(f"{out_name}.mp4"):
        stale.unlink()
    trace_path.unlink(missing_ok=True)
    env = dict(os.environ)
    env.update({
        "SHORTKIT_QUALITY": quality, "SHORTKIT_TIMING": str(timing_path), "SHORTKIT_TRACE": str(trace_path),
        "PYTHONPATH": os.pathsep.join([str(HERE), str(short_dir), env.get("PYTHONPATH", "")]),
    })
    cmd = [sys.executable, str(HERE / "run_scene.py"), str(scene), cls, "--media-dir", str(build), "--output", out_name]
    log_path = build / "manim.log"
    print(f"  manim: rendering {cls} ({quality}) ...", file=sys.stderr)
    started = time.time()
    with log_path.open("w") as log:
        proc = subprocess.run(cmd, cwd=short_dir, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    if proc.returncode != 0:
        text = log_path.read_text(errors="replace")
        summary = text.split("=== scene error ===")[-1].strip() if "=== scene error ===" in text else "\n".join(text.splitlines()[-40:])
        raise RenderError(f"the scene failed to render:\n{summary}\n(full traceback: {log_path})")
    found = sorted(build.rglob(f"{out_name}.mp4"), key=lambda p: p.stat().st_mtime)
    if not found:
        raise RenderError(f"Manim finished but {out_name}.mp4 was not found under {build}")
    print(f"  manim: done in {time.time() - started:.0f}s", file=sys.stderr)
    return found[-1]


# ---------------------------------------------------------------- captions


def _tokens(text: str) -> list[str]:
    return text.split()


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def _chunk_tokens(tokens: list[str]) -> list[list[int]]:
    """Group token indices into caption cues: <= CAPTION_MAX_CHARS, break after punctuation."""
    cues, cur, length = [], [], 0
    for i, tok in enumerate(tokens):
        add = len(tok) + (1 if cur else 0)
        if cur and length + add > CAPTION_MAX_CHARS:
            cues.append(cur)
            cur, length = [], 0
            add = len(tok)
        cur.append(i)
        length += add
        if re.search(r"[.!?;:]$", tok) and length >= 14:
            cues.append(cur)
            cur, length = [], 0
    if cur:
        if cues and length < 10 and len(" ".join(tokens[j] for j in cues[-1] + cur)) <= CAPTION_MAX_CHARS + 8:
            cues[-1].extend(cur)
        else:
            cues.append(cur)
    return cues


def _align_words(tokens: list[str], words: list[list]) -> list[tuple[float, float]] | None:
    """Map each text token to a (start, end) from TTS word boundaries."""
    times: list[tuple[float, float] | None] = [None] * len(tokens)
    j = 0
    for start, end, word in words:
        target = _norm(str(word))
        if not target:
            continue
        k = j
        while k < len(tokens) and not (_norm(tokens[k]).startswith(target) or target.startswith(_norm(tokens[k]) or "\0")):
            k += 1
        if k >= len(tokens) or k - j > 3:
            continue
        times[k] = (float(start), float(end)) if times[k] is None else (times[k][0], float(end))
        j = k + 1 if _norm(tokens[k]) == target or target.startswith(_norm(tokens[k])) else k
    known = [t for t in times if t]
    if len(known) < max(2, len(tokens) // 2):
        return None
    # fill gaps by interpolation between known neighbours
    for i, t in enumerate(times):
        if t is None:
            prev = next((times[k][1] for k in range(i - 1, -1, -1) if times[k]), 0.0)
            nxt = next((times[k][0] for k in range(i + 1, len(times)) if times[k]), prev + 0.3)
            times[i] = (prev, max(prev, nxt))
    return times  # type: ignore[return-value]


def caption_cues(trace: dict, timing: dict) -> list[tuple[float, float, str]]:
    by_id = {b["id"]: b for b in timing.get("beats", [])}
    cues: list[tuple[float, float, str]] = []
    beats = trace.get("beats", [])
    for idx, beat in enumerate(beats):
        entry = by_id.get(beat["id"])
        if not entry:
            continue
        tokens = _tokens(entry["text"])
        if not tokens:
            continue
        b_start = float(beat["start"])
        spoken = float(entry.get("audio_seconds") or entry.get("duration") or 1.0)
        limit = float(beats[idx + 1]["start"]) if idx + 1 < len(beats) else float(beat["end"])
        groups = _chunk_tokens(tokens)
        times = _align_words(tokens, entry["words"]) if entry.get("words") else None
        if times is None:
            weights = [sum(len(tokens[i]) + 1 for i in g) for g in groups]
            total, t = float(sum(weights)), b_start
            for g, w in zip(groups, weights):
                d = spoken * w / total
                cues.append((t, t + d, " ".join(tokens[i] for i in g)))
                t += d
        else:
            for g in groups:
                cues.append((b_start + times[g[0]][0], b_start + times[g[-1]][1] + 0.15, " ".join(tokens[i] for i in g)))
        # never bleed into the next beat
        cues[:] = [(a, min(b, limit - 0.02), s) for a, b, s in cues]
    # close tiny gaps so captions do not flicker
    out = []
    for i, (a, b, s) in enumerate(cues):
        if i + 1 < len(cues) and cues[i + 1][0] - b < 0.35:
            b = cues[i + 1][0]  # close tiny gaps and never let two cues overlap
        out.append((a, max(b, a + 0.4), s))
    return out


def _ts_srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _ts_ass(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_srt(cues, path: Path) -> None:
    lines = []
    for i, (a, b, s) in enumerate(cues, 1):
        lines += [str(i), f"{_ts_srt(a)} --> {_ts_srt(b)}", s, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def caption_font() -> str:
    try:
        import manimpango

        available = set(manimpango.list_fonts())
    except Exception:
        available = set()
    for name in (os.environ.get("SHORTKIT_FONT"), "Inter", "Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"):
        if name and name in available:
            return name
    return "Arial"


def write_ass(cues, path: Path) -> None:
    font = caption_font()
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},72,&H00FFFFFF,&H000000FF,&H00141414,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,2,{ASS_MARGIN_L},{ASS_MARGIN_R},{ASS_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for a, b, s in cues:
        safe = s.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
        events.append(f"Dialogue: 0,{_ts_ass(a)},{_ts_ass(b)},Default,,0,0,0,,{safe}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- encode


def encode(raw: Path, out: Path, quality: str, trace: dict, timing: dict, short_dir: Path,
           ass: Path | None) -> None:
    preset = PRESETS[quality]
    duration = audit.probe(raw)["duration"]
    starts = {b["id"]: float(b["start"]) for b in trace.get("beats", [])}
    clips = [(short_dir / b["audio"], starts[b["id"]]) for b in timing.get("beats", [])
             if b.get("audio") and b["id"] in starts]
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(raw)]
    for clip, _ in clips:
        cmd += ["-i", str(clip)]
    graph = ["[0:v]" + (f"ass={ass.name}" if ass else "null") + "[v]"]
    if clips:
        for k, (_, start) in enumerate(clips, 1):
            ms = int(round(start * 1000))
            graph.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}:all=1[a{k}]")
        mix = "".join(f"[a{k}]" for k in range(1, len(clips) + 1))
        graph.append(f"{mix}amix=inputs={len(clips)}:normalize=0:dropout_transition=0,"
                     f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad[aout]")
    cmd += ["-filter_complex", ";".join(graph), "-map", "[v]"]
    if clips:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", *preset["x264"], "-pix_fmt", "yuv420p", "-r", str(preset["fps"]),
            "-movflags", "+faststart", "-t", f"{duration:.3f}", str(out)]
    proc = subprocess.run(cmd, cwd=ass.parent if ass else None, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RenderError(f"ffmpeg failed: {proc.stderr[-1500:]}")


# ---------------------------------------------------------------- main


def render(short_dir: Path, quality: str = "preview", engine: str | None = None, voice: str | None = None,
           rate: str = "+0%", captions: bool = True) -> dict:
    short_dir = short_dir.resolve()
    if not (short_dir / "scene.py").exists():
        raise RenderError(f"{short_dir}/scene.py not found")
    timing = ensure_timing(short_dir, engine, voice, rate)
    build = short_dir / "build"
    build.mkdir(exist_ok=True)
    trace_path = build / f"trace-{quality}.json"
    raw = run_manim(short_dir, quality, short_dir / "timing.json", trace_path)
    if not trace_path.exists():
        raise RenderError("the scene did not write a trace; does it subclass ShortScene and call super().setup()?")
    trace = json.loads(trace_path.read_text())

    name = "preview" if quality == "preview" else short_dir.name
    video = short_dir / f"{name}.mp4"
    cues = caption_cues(trace, timing)
    write_srt(cues, short_dir / f"{name}.srt")
    ass = None
    if captions and trace.get("captions", True) and cues:
        ass = build / "captions.ass"
        write_ass(cues, ass)
    encode(raw, video, quality, trace, timing, short_dir, ass)

    info = audit.probe(video)
    motion = audit.motion_scan(raw)  # the picture alone: changing captions must not hide a frozen frame
    issues = [dict(i, source="layout") for i in trace.get("issues", [])]
    for beat in trace.get("beats", []):
        if beat.get("overrun", 0) > 1.5 and timing.get("engine") != "none":
            issues.append({"severity": "warning", "kind": "narration-gap", "beat": beat["id"], "source": "timing",
                           "detail": f"animations run {beat['overrun']}s past the narration; trim motion or extend the line"})
    issues += [dict(i, source="video") for i in audit.scan_issues(info, motion, quality)]
    if timing.get("engine") != "none" and not info.get("has_audio"):
        issues.append({"severity": "error", "kind": "missing-audio", "source": "video",
                       "detail": "narration was synthesized but the MP4 has no audio stream"})
    sheets = audit.contact_sheets(video, short_dir / "review", prefix=quality)
    errors = [i for i in issues if i["severity"] == "error"]
    report = {
        "quality": quality, "video": video.name, "sha256": audit.sha256(video),
        "duration": round(info["duration"], 2), "probe": info,
        "narration": {"engine": timing.get("engine"), "voice": timing.get("voice"),
                      "seconds": timing.get("total_seconds")},
        "beats": trace.get("beats", []), "motion": motion, "issues": issues,
        "contact_sheets": [str(p.relative_to(short_dir)) for p in sheets],
        "status": "ok" if not errors else "has-errors",
        "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (short_dir / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    review = short_dir / "review.json"
    if quality == "final" and review.exists():
        old = json.loads(review.read_text())
        if old.get("sha256") != report["sha256"]:
            review.unlink()  # an approval only covers the exact video it saw
    return report


def print_summary(short_dir: Path, report: dict) -> None:
    print(f"\n{report['video']}: {report['duration']}s, {report['probe'].get('width')}x{report['probe'].get('height')}, "
          f"narration={report['narration']['engine']}, motion_ratio={report['motion']['motion_ratio']}")
    for beat in report["beats"]:
        flag = f"  (+{beat['overrun']}s past narration)" if beat["overrun"] > 0.2 else ""
        print(f"  beat {beat['id']:<14} {beat['start']:6.2f}s -> {beat['end']:6.2f}s{flag}")
    if report["issues"]:
        print("issues:")
        for i in report["issues"]:
            where = f" [{i.get('beat')}]" if i.get("beat") else ""
            objs = f" {i['objects']}" if i.get("objects") else ""
            print(f"  {i['severity'].upper():7} {i['kind']}{where}: {i['detail']}{objs}")
    else:
        print("issues: none detected automatically")
    print("look at:")
    for sheet in report["contact_sheets"]:
        print(f"  {short_dir / sheet}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("short_dir", type=Path)
    ap.add_argument("--quality", choices=sorted(PRESETS), default="preview")
    ap.add_argument("--voice", dest="engine", default=None, choices=sorted(voicelib.DEFAULT_VOICES),
                    help="narration engine (default: reuse timing.json, else edge-tts, else silent)")
    ap.add_argument("--voice-name", default=None)
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--no-captions", action="store_true", help="do not burn captions into the video")
    args = ap.parse_args(argv)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("error: ffmpeg/ffprobe not found on PATH", file=sys.stderr)
        return 2
    try:
        report = render(args.short_dir, args.quality, args.engine, args.voice_name, args.rate, not args.no_captions)
    except (RenderError, beatlib.BeatError, voicelib.VoiceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print_summary(args.short_dir.resolve(), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

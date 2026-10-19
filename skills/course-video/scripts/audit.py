#!/usr/bin/env python3
"""Look at a rendered short: contact sheets, close-up frames, motion scan, approval.

    python audit.py sheet  <video> [--every 2] [--out DIR]   # timestamped contact sheets
    python audit.py frames <video> --at 3.5 9 12.25 [--out DIR]  # full-size frames
    python audit.py scan   <video>                            # static/blank/motion metrics
    python audit.py approve <short_dir> --notes "what you checked"   # bind review to the MP4 hash
    python audit.py reject  <short_dir> --notes "what must change"

Automated metrics only point at places worth looking. The real check is a
person or agent opening the contact sheets and frames and judging them against
references/quality-bar.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

STATIC_WARN_SECONDS = 6.0
STATIC_ERROR_SECONDS = 10.0


def probe(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate:format=duration",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    info = {"duration": float(data.get("format", {}).get("duration", 0.0)), "has_audio": False}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            num, _, den = str(s.get("avg_frame_rate", "0/1")).partition("/")
            info.update({"width": s.get("width"), "height": s.get("height"), "vcodec": s.get("codec_name"),
                         "pix_fmt": s.get("pix_fmt"), "fps": round(float(num) / float(den or 1), 3) if float(den or 1) else 0})
        elif s.get("codec_type") == "audio":
            info.update({"has_audio": True, "acodec": s.get("codec_name")})
    return info


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def grab_frame(video: Path, t: float, out: Path, width: int | None = None) -> Path:
    vf = ["-vf", f"scale={width}:-2"] if width else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                    *vf, str(out)], check=True)
    return out


def contact_sheets(video: Path, out_dir: Path, every: float | None = None,
                   cols: int = 3, rows: int = 3, tile_w: int = 360, prefix: str = "sheet") -> list[Path]:
    """Write timestamped contact sheets (cols x rows tiles each). Returns paths."""
    from PIL import Image, ImageDraw, ImageFont

    duration = probe(video)["duration"]
    if every is None:
        every = 1.5 if duration <= 45 else 2.0
    times, t = [], min(0.5, duration / 4)
    while t < duration - 0.05:
        times.append(round(t, 2))
        t += every
    if times and duration - times[-1] > 0.4:
        times.append(round(max(0.0, duration - 0.15), 2))
    out_dir.mkdir(parents=True, exist_ok=True)
    for pattern in (f"{prefix}-*.png", "sheet-*.png"):  # sheet-*.png: pre-2.1 naming
        for old in out_dir.glob(pattern):
            old.unlink()
    font = _font(22)
    label_h = 30
    sheets: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        tiles = []
        for i, ts in enumerate(times):
            p = grab_frame(video, ts, Path(tmp) / f"f{i:04d}.png", width=tile_w)
            tiles.append((ts, Image.open(p).convert("RGB")))
        per = cols * rows
        for s in range(0, len(tiles), per):
            chunk = tiles[s:s + per]
            th = chunk[0][1].height
            sheet = Image.new("RGB", (cols * (tile_w + 6) + 6, ((len(chunk) + cols - 1) // cols) * (th + label_h + 6) + 6), (40, 40, 40))
            draw = ImageDraw.Draw(sheet)
            for j, (ts, img) in enumerate(chunk):
                x = 6 + (j % cols) * (tile_w + 6)
                y = 6 + (j // cols) * (th + label_h + 6)
                draw.text((x + 4, y + 3), f"{ts:6.2f}s", fill=(255, 220, 90), font=font)
                sheet.paste(img, (x, y + label_h))
            path = out_dir / f"{prefix}-{s // per + 1:02d}.png"
            sheet.save(path)
            sheets.append(path)
    return sheets


def _font(size: int):
    from PIL import ImageFont

    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def motion_scan(video: Path, sample_fps: float = 4.0) -> dict:
    """Find long static stretches and blank frames from small grayscale samples."""
    import numpy as np

    w, h = 108, 192
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={sample_fps},scale={w}:{h}",
         "-pix_fmt", "gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True,
    )
    frames = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = frames.size // (w * h)
    if n < 2:
        return {"samples": n, "static_runs": [], "longest_static": 0.0, "blank_seconds": 0.0, "motion_ratio": 0.0}
    frames = frames[: n * w * h].reshape(n, h, w).astype(np.int16)
    changed = (np.abs(np.diff(frames, axis=0)) > 8).mean(axis=(1, 2)) > 0.0004  # sensitive to thin strokes
    step = 1.0 / sample_fps
    runs, start = [], None
    for i, moving in enumerate(list(changed) + [True]):
        if not moving and start is None:
            start = i
        elif moving and start is not None:
            runs.append((start * step, i * step))
            start = None
    duration = n * step
    tail_cut = duration - 1.5  # a calm final hold is expected
    static_runs = [
        {"start": round(a, 2), "end": round(b, 2), "seconds": round(b - a, 2)}
        for a, b in runs if (min(b, tail_cut) - a) >= 3.0
    ]
    blank = [(f.std() < 2.0) for f in frames]
    return {
        "samples": int(n),
        "motion_ratio": round(float(changed.mean()), 3),
        "longest_static": max((r["seconds"] for r in static_runs), default=0.0),
        "static_runs": static_runs,
        "blank_seconds": round(sum(blank[1:-1]) * step, 2),
    }


def scan_issues(info: dict, motion: dict, quality: str) -> list[dict]:
    issues = []
    want = (1080, 1920) if quality == "final" else (540, 960)
    if (info.get("width"), info.get("height")) != want:
        issues.append({"severity": "error", "kind": "resolution", "detail": f"{info.get('width')}x{info.get('height')}, expected {want[0]}x{want[1]}"})
    if quality == "final" and (info.get("vcodec") != "h264" or info.get("pix_fmt") != "yuv420p"):
        issues.append({"severity": "error", "kind": "encoding", "detail": f"{info.get('vcodec')}/{info.get('pix_fmt')}, expected h264/yuv420p"})
    for run in motion["static_runs"]:
        sev = "error" if run["seconds"] >= STATIC_ERROR_SECONDS else ("warning" if run["seconds"] >= STATIC_WARN_SECONDS else None)
        if sev:
            issues.append({"severity": sev, "kind": "static-hold",
                           "detail": f"nothing changes from {run['start']}s to {run['end']}s ({run['seconds']}s)"})
    if motion["blank_seconds"] > 0.5:
        issues.append({"severity": "error", "kind": "blank-frames", "detail": f"{motion['blank_seconds']}s of blank frames"})
    return issues


def final_video(short_dir: Path) -> Path:
    report = short_dir / "render_report.json"
    if not report.exists():
        raise SystemExit(f"{short_dir}: no render_report.json; render with --quality final first")
    data = json.loads(report.read_text())
    if data.get("quality") != "final":
        raise SystemExit(f"{short_dir}: last render was {data.get('quality')}; approve only a final render")
    return short_dir / data["video"]


def record_review(short_dir: Path, status: str, notes: str, reviewer: str) -> Path:
    video = final_video(short_dir)
    review = {
        "status": status, "video": video.name, "sha256": sha256(video), "reviewer": reviewer,
        "reviewed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "notes": notes,
    }
    path = short_dir / "review.json"
    path.write_text(json.dumps(review, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("sheet")
    p.add_argument("video", type=Path)
    p.add_argument("--every", type=float, default=None)
    p.add_argument("--out", type=Path, default=None)
    p = sub.add_parser("frames")
    p.add_argument("video", type=Path)
    p.add_argument("--at", type=float, nargs="+", required=True)
    p.add_argument("--out", type=Path, default=None)
    p = sub.add_parser("scan")
    p.add_argument("video", type=Path)
    for name in ("approve", "reject"):
        p = sub.add_parser(name)
        p.add_argument("short_dir", type=Path)
        p.add_argument("--notes", required=True)
        p.add_argument("--reviewer", default="agent")
    args = ap.parse_args(argv)

    if args.cmd == "sheet":
        out = args.out or args.video.parent / "review"
        for path in contact_sheets(args.video, out, args.every):
            print(path)
    elif args.cmd == "frames":
        out = args.out or args.video.parent / "review" / "frames"
        out.mkdir(parents=True, exist_ok=True)
        for t in args.at:
            print(grab_frame(args.video, t, out / f"frame-{t:07.2f}s.png"))
    elif args.cmd == "scan":
        info = probe(args.video)
        motion = motion_scan(args.video)
        quality = "final" if info.get("width") == 1080 else "preview"
        print(json.dumps({"probe": info, "motion": motion, "issues": scan_issues(info, motion, quality)}, indent=2))
    else:
        status = "approved" if args.cmd == "approve" else "changes_requested"
        print(record_review(args.short_dir, status, args.notes, args.reviewer))
    return 0


if __name__ == "__main__":
    sys.exit(main())

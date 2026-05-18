#!/usr/bin/env python3
"""Create contact sheets and lightweight frame metrics for generated shorts.

This is a visual QA helper, not an aesthetic judge. It makes frame review cheap
and repeatable: every run gets contact sheets plus crowding/edge metrics that
highlight videos worth opening before publishing.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def video_files(run: Path) -> list[Path]:
    finals = sorted((run / "videos").glob("*_final.mp4"))
    if finals:
        return finals
    return sorted(path for path in (run / "manim_media" / "videos").glob("**/*.mp4") if "partial_movie_files" not in path.parts)


def make_contact_sheet(ffmpeg: str, video: Path, out: Path, *, interval: int, cols: int, rows: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps=1/{interval},scale=270:-1,tile={cols}x{rows}",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out),
        ],
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def sample_gray_frames(ffmpeg: str, video: Path, *, interval: int, width: int, height: int) -> list[bytes]:
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(video),
            "-vf",
            f"fps=1/{interval},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-pix_fmt",
            "gray",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        timeout=90,
        check=False,
    )
    frame_size = width * height
    raw = result.stdout
    return [raw[i : i + frame_size] for i in range(0, len(raw), frame_size) if len(raw[i : i + frame_size]) == frame_size]


def edge_density(frame: bytes, width: int, height: int) -> float:
    if not frame:
        return 0.0
    edges = 0
    total = 0
    threshold = 34
    for y in range(height - 1):
        row = y * width
        next_row = (y + 1) * width
        for x in range(width - 1):
            value = frame[row + x]
            if abs(value - frame[row + x + 1]) > threshold or abs(value - frame[next_row + x]) > threshold:
                edges += 1
            total += 1
    return edges / total if total else 0.0


def band_density(frame: bytes, width: int, height: int, top: float, bottom: float) -> float:
    y0 = max(0, int(height * top))
    y1 = min(height, int(height * bottom))
    if y1 <= y0:
        return 0.0
    values = frame[y0 * width : y1 * width]
    return sum(1 for value in values if value > 42) / len(values)


def metrics_for(ffmpeg: str, video: Path, *, interval: int) -> dict[str, object]:
    width, height = 180, 320
    frames = sample_gray_frames(ffmpeg, video, interval=interval, width=width, height=height)
    densities = [edge_density(frame, width, height) for frame in frames]
    title_band = [band_density(frame, width, height, 0.00, 0.16) for frame in frames]
    middle_band = [band_density(frame, width, height, 0.26, 0.74) for frame in frames]
    lower_band = [band_density(frame, width, height, 0.74, 1.00) for frame in frames]
    max_edge = max(densities) if densities else 0.0
    max_middle = max(middle_band) if middle_band else 0.0
    review_flags: list[str] = []
    if max_edge > 0.19:
        review_flags.append("high_edge_density")
    if max_middle > 0.38:
        review_flags.append("crowded_middle_band")
    if title_band and max(title_band) > 0.35:
        review_flags.append("crowded_title_band")
    if lower_band and max(lower_band) > 0.35:
        review_flags.append("crowded_lower_band")
    return {
        "sampled_frames": len(frames),
        "max_edge_density": round(max_edge, 4),
        "avg_edge_density": round(sum(densities) / len(densities), 4) if densities else 0.0,
        "max_middle_band_density": round(max_middle, 4),
        "review_flags": review_flags,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit rendered short videos with contact sheets and frame metrics.")
    parser.add_argument("run", type=Path)
    parser.add_argument("--interval", type=int, default=4, help="Seconds between sampled frames/contact-sheet frames.")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--rows", type=int, default=4)
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required for frame audit.")
    run = args.run.resolve()
    out_dir = run / "visual_audit"
    report: dict[str, object] = {"run": str(run), "videos": []}
    for video in video_files(run):
        sheet = out_dir / f"{video.stem}_contact.jpg"
        make_contact_sheet(ffmpeg, video, sheet, interval=args.interval, cols=args.cols, rows=args.rows)
        item = {
            "video": str(video.relative_to(run)),
            "contact_sheet": str(sheet.relative_to(run)),
            "metrics": metrics_for(ffmpeg, video, interval=args.interval),
        }
        report["videos"].append(item)
        print(sheet)
    report_path = run / "visual_frame_audit.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

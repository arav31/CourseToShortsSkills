#!/usr/bin/env python3
"""Create contact sheets and lightweight frame metrics for generated shorts.

This is a visual QA helper, not an aesthetic judge. It makes frame review cheap
and repeatable: every run gets contact sheets plus crowding/edge metrics that
highlight videos worth opening before publishing.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ANALYSIS_INTERVAL_SECONDS = 1.0
MOTION_ANALYSIS_INTERVAL_SECONDS = 0.25
CHANGE_PIXEL_LUMA = 12
STATIC_MAX_MAD = 1.5
STATIC_MAX_CHANGED_RATIO = 0.015
LOW_CHANGE_MAX_MAD = 3.5
LOW_CHANGE_MAX_CHANGED_RATIO = 0.06
PROLONGED_STATIC_SECONDS = 8.0
TERMINAL_STATIC_SECONDS = 2.0
MAX_MOTION_FREE_GAP_SECONDS = 5.0
PROLONGED_LOW_CHANGE_SECONDS = 5.0
LOW_CHANGE_RATIO_LIMIT = 0.75
MIN_MOTION_RATIO = 0.18
MOTION_WINDOW_SECONDS = 5.0
MIN_MOTION_WINDOW_COVERAGE = 0.50
MOTION_MIN_ACTIVE_CHANGED_RATIO = 0.002
MOTION_MIN_LOCAL_BIDIRECTIONAL_RATIO = 0.18
MOTION_MIN_SUPPORT_EXTENSION_RATIO = 0.08
MOTION_STABLE_MAX_LUMA_DELTA = 3
MOTION_MIN_SUPPORT_COMPONENT_PIXELS = 100
MOTION_MIN_SUPPORT_COMPONENT_WIDTH_RATIO = 0.12
MOTION_MIN_SUPPORT_COMPONENT_HEIGHT_RATIO = 0.06
MOTION_MIN_SPATIAL_RUN_TRANSITIONS = 2
MOTION_MIN_DRAW_RUN_TRANSITIONS = 2
BLANK_MAX_LUMA_STDDEV = 4.0
BLANK_MAX_ACTIVE_PIXEL_RATIO = 0.01
BLANK_MAX_EDGE_DENSITY = 0.002
BLANK_FRAME_RATIO_LIMIT = 0.08
BLANK_HOLD_SECONDS = 4.0
UNDERUSED_MAX_ACTIVE_PIXEL_RATIO = 0.08
UNDERUSED_MAX_ACTIVE_TILE_RATIO = 0.12
UNDERUSED_FRAME_RATIO_LIMIT = 0.35
UNDERUSED_HOLD_SECONDS = 10.0
EXTREME_EMPTY_VERTICAL_BAND_RATIO = 0.38
EXTREME_LAYOUT_FRAME_RATIO_LIMIT = 0.20
EXTREME_LAYOUT_HOLD_SECONDS = 6.0
VISUAL_LANE_TOP_RATIO = 0.28
VISUAL_LANE_BOTTOM_RATIO = 0.68
VISUAL_LANE_MIN_BBOX_HEIGHT_RATIO = 0.20
VISUAL_LANE_MIN_OCCUPIED_ROW_RATIO = 0.28
VISUAL_LANE_MIN_COMPONENT_PIXELS = 3
VISUAL_LANE_MIN_COMPONENT_COUNT = 2
VISUAL_LANE_MIN_INTERNAL_EDGE_PIXELS = 8
VISUAL_LANE_MIN_INTERNAL_EDGE_RATIO = 0.015
VISUAL_LANE_MIN_INTERNAL_EDGE_TILES = 2
VISUAL_LANE_MIN_CONTOUR_CHANGE_RATIO = 0.08
VISUAL_LANE_MIN_STRUCTURE_PIXELS = 8
VISUAL_LANE_MIN_STRUCTURE_SPAN_RATIO = 0.05
VISUAL_LANE_MOTION_MIN_CHANGED_PIXELS = 8
VISUAL_LANE_MOTION_MIN_GAIN_LOSS_BALANCE = 0.35
VISUAL_LANE_MOTION_MAX_CENTROID_DISTANCE_RATIO = 0.14
VISUAL_LANE_MOTION_MAX_CHANGED_BBOX_RATIO = 0.18
VISUAL_LANE_MAX_SPARSE_FRAME_RATIO = 0.25
VISUAL_LANE_MAX_SPARSE_HOLD_SECONDS = 6.0
PORTRAIT_CORE_TOP_RATIO = 0.21875
PORTRAIT_CORE_BOTTOM_RATIO = 0.7625
PORTRAIT_EVIDENCE_TOP_RATIO = 0.778125
PORTRAIT_EVIDENCE_BOTTOM_RATIO = 0.896875
PORTRAIT_CONTENT_WIDTH_RATIO = 0.90
PORTRAIT_CORE_MIN_WIDTH_OCCUPANCY = 0.78
PORTRAIT_CORE_MAX_WIDTH_OCCUPANCY = 0.97
PORTRAIT_CORE_MIN_HEIGHT_OCCUPANCY = 0.68
PORTRAIT_CORE_MAX_HEIGHT_OCCUPANCY = 0.95
PORTRAIT_CORE_MIN_AREA_OCCUPANCY = 0.48
PORTRAIT_CORE_MIN_OCCUPIED_ROW_RATIO = 0.55
PORTRAIT_CORE_MIN_OCCUPIED_COLUMN_RATIO = 0.60
PORTRAIT_CORE_MIN_TILE_SUPPORT_RATIO = 0.14
PORTRAIT_LAYOUT_MAX_FLAGGED_FRAME_RATIO = 0.20
PORTRAIT_LAYOUT_MAX_FLAGGED_HOLD_SECONDS = 6.0

OCR_SAMPLE_INTERVAL_SECONDS = 0.5
OCR_MAX_FRAMES = 120
OCR_MIN_LAYOUT_CONFIDENCE = 20.0
OCR_ESSENTIAL_TEXT_CONFIDENCE = 70.0
OCR_LOW_CONFIDENCE = 45.0
OCR_LOW_CONFIDENCE_TOKEN_RATIO_LIMIT = 0.18
OCR_SAFE_HORIZONTAL_INSET_RATIO = 0.035
OCR_SAFE_VERTICAL_INSET_RATIO = 0.025
OCR_SMALL_LINE_HEIGHT_RATIO = 0.0175
OCR_SMALL_LINE_RATIO_LIMIT = 0.18
OCR_SMALL_TEXT_FRAME_RATIO_LIMIT = 0.20
OCR_SMALL_TEXT_MIN_AFFECTED_SECONDS = 1.5
OCR_RUN_TOGETHER_FRAME_RATIO_LIMIT = 0.12
OCR_SIMILAR_LINE_HEIGHT_RATIO = 0.80
OCR_LINE_BOX_VERTICAL_INSET_RATIO = 0.15
OCR_INSET_LINE_OVERLAP_RATIO = 0.25

VISUAL_SMALL_TEXT_FLAG = "rendered_text_too_small"
VISUAL_SMALL_TEXT_FOREGROUND_LUMA = 28
VISUAL_SMALL_TEXT_MIN_HEIGHT_RATIO = 0.006
VISUAL_SMALL_TEXT_BLOCKING_HEIGHT_RATIO = 0.014
VISUAL_SMALL_TEXT_MAX_HEIGHT_RATIO = 0.022
VISUAL_SMALL_TEXT_MIN_WIDTH_RATIO = 0.045
VISUAL_SMALL_TEXT_MAX_WIDTH_RATIO = 0.45
VISUAL_SMALL_TEXT_MIN_COMPONENTS = 4
VISUAL_SMALL_TEXT_MIN_DURATION_SECONDS = 1.5
VISUAL_SMALL_TEXT_MIN_TRACK_IOU = 0.62

TEMPORAL_TEXT_SAMPLE_INTERVAL_SECONDS = 0.25
TEMPORAL_TEXT_MAX_FRAMES = 240
TEMPORAL_TEXT_FRAME_WIDTH = 360
TEMPORAL_TEXT_FRAME_HEIGHT = 640
TEMPORAL_TEXT_MIN_CHARACTERS = 4
TEMPORAL_TEXT_MIN_HEIGHT_RATIO = 0.012
TEMPORAL_TEXT_MIN_WIDTH_RATIO = 0.08
TEMPORAL_TEXT_MIN_NEIGHBOR_SIMILARITY = 0.82
TEMPORAL_TEXT_MIN_FUZZY_SIMILARITY = 0.92
TEMPORAL_TEXT_FUZZY_MAX_CONFIDENCE = 85.0
TEMPORAL_TEXT_MIN_GEOMETRY_IOU = 0.55
TEMPORAL_TEXT_MIN_NEIGHBOR_SHAPE_SUPPORT = 0.72
TEMPORAL_TEXT_MAX_STROKE_COVERAGE = 0.58
TEMPORAL_TEXT_MAX_COMPONENT_AREA_RATIO = 0.68
TEMPORAL_TEXT_FOREGROUND_LUMA = 18
TEMPORAL_TEXT_MIN_EXPECTED_PIXELS = 24
TEMPORAL_TEXT_COHERENT_FADE_RATIO = 0.88
TEMPORAL_TEXT_FLAG = "temporal_text_integrity_loss"

TEMPORAL_VISUAL_SAMPLE_INTERVAL_SECONDS = 0.1
TEMPORAL_VISUAL_MAX_FRAMES = 900
TEMPORAL_VISUAL_FRAME_WIDTH = 144
TEMPORAL_VISUAL_FRAME_HEIGHT = 256
TEMPORAL_VISUAL_FOREGROUND_LUMA = 18
TEMPORAL_VISUAL_STRONG_RETENTION_RATIO = 0.70
TEMPORAL_VISUAL_FADE_PRELOSS_MAX_RETENTION = 0.84
TEMPORAL_VISUAL_FADE_PRELOSS_COHERENT_RATIO = 0.70
TEMPORAL_VISUAL_MIN_GLOBAL_LOSS_PIXELS = 16
TEMPORAL_VISUAL_MIN_GLOBAL_LOSS_RATIO = 0.012
TEMPORAL_VISUAL_MAX_GAIN_TO_LOSS_RATIO = 0.78
TEMPORAL_VISUAL_OUTLIER_MULTIPLIER = 2.4
TEMPORAL_VISUAL_OUTLIER_MARGIN_PIXELS = 8
TEMPORAL_VISUAL_MAX_ADJACENT_LOSS_RATIO = 0.35
TEMPORAL_VISUAL_MIN_REGION_PIXELS = 28
TEMPORAL_VISUAL_MIN_REGION_LOSS_PIXELS = 9
TEMPORAL_VISUAL_MIN_REGION_LOSS_RATIO = 0.08
TEMPORAL_VISUAL_MAX_REGION_LOSS_RATIO = 0.68
TEMPORAL_VISUAL_MIN_REGION_RETENTION_RATIO = 0.28
TEMPORAL_VISUAL_MIN_CUT_PIXELS = 3
TEMPORAL_VISUAL_MIN_CUT_RATIO = 0.04
TEMPORAL_VISUAL_MIN_RECOVERY_RATIO = 0.55
TEMPORAL_VISUAL_MIN_ISOLATED_LOSS_PIXELS = 45
TEMPORAL_VISUAL_MIN_ISOLATED_LOSS_RATIO = 0.22
TEMPORAL_VISUAL_MAX_CAUSAL_CARRIER_LOSS_PIXELS = 96
TEMPORAL_VISUAL_MAX_CAUSAL_CARRIER_REGION_PIXELS = 220
TEMPORAL_VISUAL_MIN_CAUSAL_CARRIER_RECOVERY_RATIO = 0.9
TEMPORAL_VISUAL_COLLISION_CONTEXT_SECONDS = (0.4, 0.8)
TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_PIXELS = 10
TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_AREA_RATIO = 0.0022
TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_BALANCE = 0.55
TEMPORAL_VISUAL_COLLISION_MIN_RESIDUE_RATIO = 0.70
TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_PIXELS = 7
TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_AREA_RATIO = 0.0005
TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_RATIO = 1.8
TEMPORAL_VISUAL_FLAG = "temporal_visual_integrity_loss"

SERIOUS_MOTION_LAYOUT_FLAGS = {
    "blank_frames",
    "underused_frames",
    "prolonged_static_holds",
    "terminal_static_hold",
    "long_motion_free_gap",
    "prolonged_low_change_run",
    "low_visual_change",
    "insufficient_motion_coverage",
    "extreme_layout_imbalance",
    "underfilled_visual_lane",
    "outer_portrait_underfill",
    "outer_portrait_overfill",
    "evidence_lane_intrusion",
}
FUSED_ARTICLE_STEMS = (
    "algorithm",
    "coset",
    "curve",
    "derivative",
    "field",
    "force",
    "function",
    "graph",
    "group",
    "homomorphism",
    "integral",
    "market",
    "matrix",
    "particle",
    "probability",
    "ring",
    "sequence",
    "set",
    "subgroup",
    "system",
    "vector",
)


def video_files(run: Path) -> list[Path]:
    finals = sorted((run / "videos").glob("*_final.mp4"))
    if finals:
        return finals
    previews = sorted((run / "videos").glob("*_preview.mp4"))
    if previews:
        return previews
    return sorted(path for path in (run / "manim_media" / "videos").glob("**/*.mp4") if "partial_movie_files" not in path.parts)


def probe_video_duration(video: Path, ffprobe: str | None = None) -> float:
    ffprobe = ffprobe or shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video),
            ],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return max(0.0, float(result.stdout.strip())) if result.returncode == 0 else 0.0
    except (ValueError, subprocess.TimeoutExpired):
        return 0.0


def _showinfo_timestamps(stderr: str) -> list[float]:
    timestamps: list[float] = []
    for match in re.finditer(r"\bn:\s*\d+\b.*?\bpts_time:([-+\d.eE]+)", stderr):
        try:
            timestamps.append(float(match.group(1)))
        except ValueError:
            continue
    return timestamps


def _contact_sheet_destinations(out: Path, page_count: int) -> list[Path]:
    if page_count <= 1:
        return [out]
    digits = max(2, len(str(page_count)))
    return [out.with_name(f"{out.stem}_{page:0{digits}d}{out.suffix}") for page in range(1, page_count + 1)]


def make_contact_sheet(
    ffmpeg: str,
    video: Path,
    out: Path,
    *,
    interval: float,
    cols: int,
    rows: int,
    duration: float = 0.0,
) -> dict[str, object]:
    if interval <= 0:
        raise ValueError("Contact-sheet interval must be greater than zero.")
    if cols <= 0 or rows <= 0:
        raise ValueError("Contact-sheet columns and rows must be greater than zero.")

    out.parent.mkdir(parents=True, exist_ok=True)
    tile_capacity = cols * rows
    with tempfile.TemporaryDirectory(prefix=f".{out.stem}-", dir=out.parent) as temporary:
        page_pattern = Path(temporary) / "page_%04d.jpg"
        result = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "info",
                "-y",
                "-i",
                str(video),
                "-vf",
                (
                    f"fps=1/{interval}:eof_action=pass,showinfo=checksum=0,scale=270:-1,"
                    f"tile={cols}x{rows}:nb_frames={tile_capacity}:padding=2:margin=2:color=black"
                ),
                "-fps_mode",
                "vfr",
                str(page_pattern),
            ],
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        source_pages = sorted(Path(temporary).glob("page_*.jpg"))
        if result.returncode != 0 or not source_pages:
            detail = result.stderr[-500:].strip()
            raise RuntimeError(f"Contact-sheet generation failed for {video}: {detail}")

        destinations = _contact_sheet_destinations(out, len(source_pages))
        desired = set(destinations)
        numbered_name = re.compile(rf"^{re.escape(out.stem)}_\d+{re.escape(out.suffix)}$")
        stale_candidates = [out, *out.parent.glob(f"{out.stem}_*{out.suffix}")]
        for stale in stale_candidates:
            if stale not in desired and (stale == out or numbered_name.fullmatch(stale.name)):
                stale.unlink(missing_ok=True)
        for source, destination in zip(source_pages, destinations):
            source.replace(destination)

    timestamps = _showinfo_timestamps(result.stderr)
    last_timestamp = timestamps[-1] if timestamps else None
    coverage_end = min(duration, last_timestamp + interval) if duration > 0 and last_timestamp is not None else None
    covers_entire_video = (
        coverage_end >= duration - max(0.05, interval * 0.05)
        if duration > 0 and coverage_end is not None
        else None
    )
    return {
        "paths": destinations,
        "coverage": {
            "sample_interval_seconds": interval,
            "sampled_frames": len(timestamps),
            "first_sample_timestamp_seconds": round(timestamps[0], 3) if timestamps else None,
            "last_sample_timestamp_seconds": round(last_timestamp, 3) if last_timestamp is not None else None,
            "coverage_end_seconds": round(coverage_end, 3) if coverage_end is not None else None,
            "video_duration_seconds": round(duration, 3) if duration > 0 else None,
            "covers_entire_video": covers_entire_video,
            "tile_capacity": tile_capacity,
            "sheet_count": len(destinations),
        },
    }


def sample_gray_frames(ffmpeg: str, video: Path, *, interval: float, width: int, height: int) -> list[bytes]:
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


def sample_gray_frame_window(
    ffmpeg: str,
    video: Path,
    *,
    start: float,
    end: float,
    fps: float,
    width: int,
    height: int,
) -> list[bytes]:
    """Decode a dense interval with output seeking for transition QA."""
    if end <= start or fps <= 0 or width <= 0 or height <= 0:
        return []
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(video),
            "-ss",
            f"{start:.6f}",
            "-t",
            f"{end - start:.6f}",
            "-vf",
            f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
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
    return [
        raw[index : index + frame_size]
        for index in range(0, len(raw), frame_size)
        if len(raw[index : index + frame_size]) == frame_size
    ]


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


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def longest_run(states: list[bool]) -> int:
    longest = 0
    current = 0
    for state in states:
        if state:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def longest_sampled_run_seconds(states: list[bool], *, interval: float) -> float:
    """Duration represented by a consecutive run of affected samples."""
    if interval <= 0:
        raise ValueError("Sample interval must be greater than zero.")
    return longest_run(states) * interval


def frame_change(previous: bytes, current: bytes) -> tuple[float, float]:
    if not previous or len(previous) != len(current):
        return 0.0, 0.0
    absolute_delta = 0
    changed_pixels = 0
    for before, after in zip(previous, current):
        delta = abs(before - after)
        absolute_delta += delta
        if delta >= CHANGE_PIXEL_LUMA:
            changed_pixels += 1
    return absolute_delta / len(current), changed_pixels / len(current)


def _support_extension_ratio(
    active_union: bytearray,
    extension: bytearray,
    stable: bytearray,
    width: int,
    height: int,
) -> float:
    """Measure a progressively extended foreground component.

    A draw animation retains an already-visible part of a connected shape while
    adding a new part. A uniform fade changes the old pixels too, so it has no
    stable support and cannot satisfy this signal.
    """
    if not active_union or len(active_union) != width * height:
        return 0.0
    visited = bytearray(len(active_union))
    best = 0.0
    for start, active in enumerate(active_union):
        if not active or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        component_size = 0
        extension_pixels = 0
        stable_pixels = 0
        min_x = width
        max_x = -1
        min_y = height
        max_y = -1
        while stack:
            index = stack.pop()
            component_size += 1
            extension_pixels += int(extension[index])
            stable_pixels += int(stable[index])
            x = index % width
            y = index // width
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            neighbors = []
            if x:
                neighbors.append(index - 1)
            if x + 1 < width:
                neighbors.append(index + 1)
            if index >= width:
                neighbors.append(index - width)
            if index + width < len(active_union):
                neighbors.append(index + width)
            for neighbor in neighbors:
                if active_union[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
        component_width = max_x - min_x + 1
        component_height = max_y - min_y + 1
        if (
            component_size < MOTION_MIN_SUPPORT_COMPONENT_PIXELS
            or component_width < width * MOTION_MIN_SUPPORT_COMPONENT_WIDTH_RATIO
            or component_height < height * MOTION_MIN_SUPPORT_COMPONENT_HEIGHT_RATIO
            or extension_pixels < 3
            or stable_pixels < 3
        ):
            continue
        extension_share = extension_pixels / (extension_pixels + stable_pixels)
        if extension_share <= 0.75:
            best = max(best, extension_share)
    return best


def sustained_true_states(states: list[bool], minimum_run: int) -> list[bool]:
    """Keep only true runs long enough to demonstrate temporal progression."""
    if minimum_run <= 1:
        return list(states)
    sustained = [False] * len(states)
    start = 0
    while start < len(states):
        if not states[start]:
            start += 1
            continue
        end = start + 1
        while end < len(states) and states[end]:
            end += 1
        if end - start >= minimum_run:
            sustained[start:end] = [True] * (end - start)
        start = end
    return sustained


def transition_motion_evidence(previous: bytes, current: bytes, width: int, height: int) -> dict[str, float | bool]:
    """Separate rendered movement/drawing from opacity-only state changes.

    Full-canvas MAD is useful for finding visually busy transitions, but it
    gives a large fade more credit than a small moving object. This profile adds
    two size-independent signals: locally interleaved brightening/darkening for
    displacement, and stable connected support that grows for progressive
    drawing. It deliberately treats a plain fade or crossfade as non-motion.
    """
    pixel_count = width * height
    if not previous or len(previous) != len(current) or len(current) != pixel_count:
        return {
            "active": False,
            "changed_pixel_ratio": 0.0,
            "directional_coherence": 0.0,
            "local_bidirectional_ratio": 0.0,
            "support_extension_ratio": 0.0,
            "spatial_or_drawn": False,
            "opacity_dominated": False,
        }

    previous_background = dominant_luma(previous)
    current_background = dominant_luma(current)
    tile_width = max(4, round(width / 12))
    tile_height = max(4, round(height / 20))
    tile_cols = math.ceil(width / tile_width)
    tile_rows = math.ceil(height / tile_height)
    tile_positive = [0] * (tile_cols * tile_rows)
    tile_negative = [0] * (tile_cols * tile_rows)
    active_union = bytearray(pixel_count)
    extension_positive = bytearray(pixel_count)
    extension_negative = bytearray(pixel_count)
    stable = bytearray(pixel_count)
    positive = 0
    negative = 0

    for index, (before, after) in enumerate(zip(previous, current)):
        delta = after - before
        changed = abs(delta) >= CHANGE_PIXEL_LUMA
        x = index % width
        y = index // width
        tile_index = (y // tile_height) * tile_cols + (x // tile_width)
        if delta >= CHANGE_PIXEL_LUMA:
            positive += 1
            tile_positive[tile_index] += 1
        elif delta <= -CHANGE_PIXEL_LUMA:
            negative += 1
            tile_negative[tile_index] += 1

        before_active = abs(before - previous_background) >= CHANGE_PIXEL_LUMA
        after_active = abs(after - current_background) >= CHANGE_PIXEL_LUMA
        if before_active or after_active:
            active_union[index] = 1
        if changed and after_active and not before_active:
            extension_positive[index] = 1
        if changed and before_active and not after_active:
            extension_negative[index] = 1
        if before_active and after_active and abs(delta) <= MOTION_STABLE_MAX_LUMA_DELTA:
            stable[index] = 1

    changed_pixels = positive + negative
    changed_ratio = changed_pixels / pixel_count
    active = changed_ratio >= MOTION_MIN_ACTIVE_CHANGED_RATIO
    directional_coherence = max(positive, negative) / changed_pixels if changed_pixels else 0.0
    local_bidirectional_pixels = sum(
        2 * min(brightened, darkened)
        for brightened, darkened in zip(tile_positive, tile_negative)
    )
    local_bidirectional_ratio = local_bidirectional_pixels / changed_pixels if changed_pixels else 0.0

    dominant_extension = extension_positive if positive >= negative else extension_negative
    support_extension = _support_extension_ratio(active_union, dominant_extension, stable, width, height)
    spatial_or_drawn = active and (
        local_bidirectional_ratio >= MOTION_MIN_LOCAL_BIDIRECTIONAL_RATIO
        or support_extension >= MOTION_MIN_SUPPORT_EXTENSION_RATIO
    )
    return {
        "active": active,
        "changed_pixel_ratio": changed_ratio,
        "directional_coherence": directional_coherence,
        "local_bidirectional_ratio": local_bidirectional_ratio,
        "support_extension_ratio": support_extension,
        "spatial_or_drawn": spatial_or_drawn,
        "opacity_dominated": active and not spatial_or_drawn,
    }


def dominant_luma(frame: bytes) -> int:
    histogram = [0] * 256
    for value in frame:
        histogram[value] += 1
    # Smooth nearby compression values so a nominally flat background remains
    # the dominant cluster rather than several adjacent one-value peaks.
    return max(range(256), key=lambda value: sum(histogram[max(0, value - 2) : min(256, value + 3)]))


def frame_usage(frame: bytes, width: int, height: int, edge: float) -> dict[str, float | bool]:
    if not frame:
        return {"luma_stddev": 0.0, "active_pixel_ratio": 0.0, "active_tile_ratio": 0.0, "blank": True, "underused": True}

    background = dominant_luma(frame)
    mean = sum(frame) / len(frame)
    variance = sum((value - mean) ** 2 for value in frame) / len(frame)
    luma_stddev = math.sqrt(variance)
    active_pixels = sum(1 for value in frame if abs(value - background) >= CHANGE_PIXEL_LUMA)
    active_pixel_ratio = active_pixels / len(frame)

    tile_cols, tile_rows = 10, 16
    active_tiles = 0
    for tile_y in range(tile_rows):
        y0 = tile_y * height // tile_rows
        y1 = (tile_y + 1) * height // tile_rows
        for tile_x in range(tile_cols):
            x0 = tile_x * width // tile_cols
            x1 = (tile_x + 1) * width // tile_cols
            tile_size = (x1 - x0) * (y1 - y0)
            tile_active = 0
            for y in range(y0, y1):
                row = y * width
                tile_active += sum(1 for value in frame[row + x0 : row + x1] if abs(value - background) >= CHANGE_PIXEL_LUMA)
            if tile_size and tile_active / tile_size >= 0.04:
                active_tiles += 1
    active_tile_ratio = active_tiles / (tile_cols * tile_rows)

    blank = (
        luma_stddev <= BLANK_MAX_LUMA_STDDEV
        and active_pixel_ratio <= BLANK_MAX_ACTIVE_PIXEL_RATIO
        and edge <= BLANK_MAX_EDGE_DENSITY
    )
    underused = blank or (
        active_pixel_ratio <= UNDERUSED_MAX_ACTIVE_PIXEL_RATIO
        and active_tile_ratio <= UNDERUSED_MAX_ACTIVE_TILE_RATIO
    )
    return {
        "luma_stddev": luma_stddev,
        "active_pixel_ratio": active_pixel_ratio,
        "active_tile_ratio": active_tile_ratio,
        "blank": blank,
        "underused": underused,
    }


def _empty_visual_lane_profile() -> dict[str, float | int | bool]:
    return {
        "active_pixel_ratio": 0.0,
        "bbox_width_ratio": 0.0,
        "bbox_height_ratio": 0.0,
        "bbox_fill_ratio": 0.0,
        "centroid_y_ratio": 0.0,
        "occupied_row_ratio": 0.0,
        "lower_half_occupied_row_ratio": 0.0,
        "component_count": 0,
        "internal_edge_pixel_ratio": 0.0,
        "internal_edge_tile_count": 0,
        "contour_change_ratio": 0.0,
        "geometric_coverage": False,
        "structural_evidence": False,
        "meaningful_diagram": False,
        "sparse": True,
    }


def _binary_component_areas(mask: bytes | bytearray, width: int, height: int) -> list[int]:
    if not mask or width <= 0 or height <= 0 or len(mask) != width * height:
        return []
    visited = bytearray(len(mask))
    areas: list[int] = []
    for start, active in enumerate(mask):
        if not active or visited[start]:
            continue
        visited[start] = 1
        stack = [start]
        area = 0
        while stack:
            index = stack.pop()
            area += 1
            y, x = divmod(index, width)
            for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
                row = neighbor_y * width
                for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = row + neighbor_x
                    if mask[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        stack.append(neighbor)
        areas.append(area)
    return sorted(areas, reverse=True)


def _visual_lane_bounds(height: int) -> tuple[int, int]:
    top = max(0, min(height - 1, round(height * VISUAL_LANE_TOP_RATIO)))
    bottom = max(top + 1, min(height, round(height * VISUAL_LANE_BOTTOM_RATIO)))
    return top, bottom


def visual_lane_profile(frame: bytes, width: int, height: int) -> dict[str, float | int | bool]:
    """Measure explanatory structure in the central lane.

    Area and bounding-box coverage are retained as layout diagnostics, but they
    are not proof of a diagram. A meaningful lane also needs visible structure:
    separate components, edges inside its outer silhouette, or a changing
    contour such as a curve or arrowhead.
    """
    if not frame or width <= 0 or height <= 0 or len(frame) != width * height:
        return _empty_visual_lane_profile()
    background = dominant_luma(frame)
    top, bottom = _visual_lane_bounds(height)
    lane_height = bottom - top
    lane_pixels = width * lane_height
    active_mask = bytearray(lane_pixels)
    active_coordinates: list[tuple[int, int]] = []
    row_signatures: list[tuple[int, int, int, int]] = []
    occupied_rows = 0
    lower_occupied_rows = 0
    minimum_row_pixels = max(2, round(width * 0.006))
    lower_start = top + lane_height // 2
    for y in range(top, bottom):
        row = frame[y * width : (y + 1) * width]
        active_x = [x for x, value in enumerate(row) if abs(value - background) >= CHANGE_PIXEL_LUMA]
        active_coordinates.extend((x, y) for x in active_x)
        lane_row = (y - top) * width
        for x in active_x:
            active_mask[lane_row + x] = 1
        if len(active_x) >= minimum_row_pixels:
            occupied_rows += 1
            run_count = 1 + sum(after > before + 1 for before, after in zip(active_x, active_x[1:]))
            row_signatures.append((y, active_x[0], active_x[-1], run_count))
            if y >= lower_start:
                lower_occupied_rows += 1
    if not active_coordinates:
        return _empty_visual_lane_profile()
    xs = [coordinate[0] for coordinate in active_coordinates]
    ys = [coordinate[1] for coordinate in active_coordinates]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bbox_width = max_x - min_x + 1
    bbox_height = max_y - min_y + 1
    bbox_width_ratio = bbox_width / width
    bbox_height_ratio = bbox_height / height
    bbox_fill_ratio = len(active_coordinates) / (bbox_width * bbox_height)
    occupied_row_ratio = occupied_rows / max(1, lane_height)
    lower_half_occupied_row_ratio = lower_occupied_rows / max(1, bottom - lower_start)
    geometric_coverage = (
        bbox_height_ratio >= VISUAL_LANE_MIN_BBOX_HEIGHT_RATIO
        or occupied_row_ratio >= VISUAL_LANE_MIN_OCCUPIED_ROW_RATIO
    )

    component_count = sum(
        area >= VISUAL_LANE_MIN_COMPONENT_PIXELS
        for area in _binary_component_areas(active_mask, width, lane_height)
    )
    internal_edge_pixels: set[int] = set()
    for y in range(min_y, max_y + 1):
        lane_y = y - top
        row = y * width
        lane_row = lane_y * width
        for x in range(min_x, max_x + 1):
            lane_index = lane_row + x
            if not active_mask[lane_index]:
                continue
            inside_bbox = min_x + 1 < x < max_x - 1 and min_y + 1 < y < max_y - 1
            if not inside_bbox:
                continue
            neighbors = (
                active_mask[lane_index - 1],
                active_mask[lane_index + 1],
                active_mask[lane_index - width],
                active_mask[lane_index + width],
            )
            if not all(neighbors):
                internal_edge_pixels.add(lane_index)
                continue
            value = frame[row + x]
            if (
                abs(value - frame[row + x + 1]) >= CHANGE_PIXEL_LUMA
                or abs(value - frame[(y + 1) * width + x]) >= CHANGE_PIXEL_LUMA
            ):
                internal_edge_pixels.add(lane_index)

    edge_tile_columns, edge_tile_rows = 6, 8
    internal_edge_tiles = {
        min(edge_tile_rows - 1, (index // width) * edge_tile_rows // lane_height) * edge_tile_columns
        + min(edge_tile_columns - 1, (index % width) * edge_tile_columns // width)
        for index in internal_edge_pixels
    }
    internal_edge_pixel_ratio = len(internal_edge_pixels) / len(active_coordinates)
    contour_comparisons = 0
    contour_changes = 0
    for before, after in zip(row_signatures, row_signatures[1:]):
        if after[0] != before[0] + 1:
            continue
        contour_comparisons += 1
        if before[1:] != after[1:]:
            contour_changes += 1
    contour_change_ratio = contour_changes / contour_comparisons if contour_comparisons else 0.0
    enough_structure_extent = (
        len(active_coordinates) >= VISUAL_LANE_MIN_STRUCTURE_PIXELS
        and max(bbox_width_ratio, bbox_height_ratio) >= VISUAL_LANE_MIN_STRUCTURE_SPAN_RATIO
    )
    multiple_components = component_count >= VISUAL_LANE_MIN_COMPONENT_COUNT
    distributed_internal_edges = (
        len(internal_edge_pixels) >= VISUAL_LANE_MIN_INTERNAL_EDGE_PIXELS
        and internal_edge_pixel_ratio >= VISUAL_LANE_MIN_INTERNAL_EDGE_RATIO
        and len(internal_edge_tiles) >= VISUAL_LANE_MIN_INTERNAL_EDGE_TILES
    )
    changing_contour = contour_change_ratio >= VISUAL_LANE_MIN_CONTOUR_CHANGE_RATIO
    structural_evidence = enough_structure_extent and (
        multiple_components
        or distributed_internal_edges
        or changing_contour
    )
    return {
        "active_pixel_ratio": len(active_coordinates) / lane_pixels,
        "bbox_width_ratio": bbox_width_ratio,
        "bbox_height_ratio": bbox_height_ratio,
        "bbox_fill_ratio": bbox_fill_ratio,
        "centroid_y_ratio": (sum(ys) / len(ys)) / height,
        "occupied_row_ratio": occupied_row_ratio,
        "lower_half_occupied_row_ratio": lower_half_occupied_row_ratio,
        "component_count": component_count,
        "internal_edge_pixel_ratio": internal_edge_pixel_ratio,
        "internal_edge_tile_count": len(internal_edge_tiles),
        "contour_change_ratio": contour_change_ratio,
        "geometric_coverage": geometric_coverage,
        "structural_evidence": structural_evidence,
        "meaningful_diagram": structural_evidence,
        "sparse": not structural_evidence,
    }


def portrait_proof_surface_profile(
    frame: bytes,
    width: int,
    height: int,
    runtime_roles: dict[str, object] | None = None,
) -> dict[str, float | bool]:
    """Measure role masks when available, otherwise use component/tile support."""
    empty = {
        "core_width_occupancy": 0.0,
        "core_height_occupancy": 0.0,
        "core_area_occupancy": 0.0,
        "occupied_row_ratio": 0.0,
        "occupied_column_ratio": 0.0,
        "outer_underfill": True,
        "outer_overfill": False,
        "evidence_intrusion": False,
        "core_tile_support_ratio": 0.0,
        "core_component_count": 0,
        "runtime_role_masks_used": False,
    }
    if isinstance(runtime_roles, dict):
        core = runtime_roles.get("core_geometry")
        evidence = runtime_roles.get("evidence")
        if isinstance(core, dict) and bool(core.get("visible")):
            width_occupancy = float(core.get("width_occupancy") or 0.0)
            height_occupancy = float(core.get("height_occupancy") or 0.0)
            area_occupancy = float(core.get("area_occupancy") or 0.0)
            row_ratio = float(core.get("occupied_row_ratio") or 0.0)
            column_ratio = float(core.get("occupied_column_ratio") or 0.0)
            tile_support = float(core.get("tile_support_ratio") or 0.0)
            outer_underfill = (
                width_occupancy < PORTRAIT_CORE_MIN_WIDTH_OCCUPANCY - 1e-6
                or height_occupancy < PORTRAIT_CORE_MIN_HEIGHT_OCCUPANCY - 1e-6
                or area_occupancy < PORTRAIT_CORE_MIN_AREA_OCCUPANCY - 1e-6
                or row_ratio < PORTRAIT_CORE_MIN_OCCUPIED_ROW_RATIO - 1e-6
                or column_ratio < PORTRAIT_CORE_MIN_OCCUPIED_COLUMN_RATIO - 1e-6
            )
            outer_overfill = (
                width_occupancy > PORTRAIT_CORE_MAX_WIDTH_OCCUPANCY + 1e-6
                or height_occupancy > PORTRAIT_CORE_MAX_HEIGHT_OCCUPANCY + 1e-6
            )
            evidence_intrusion = bool(
                isinstance(evidence, dict)
                and bool(evidence.get("visible"))
                and not bool(evidence.get("lane_satisfied", True))
            )
            return {
                "core_width_occupancy": width_occupancy,
                "core_height_occupancy": height_occupancy,
                "core_area_occupancy": area_occupancy,
                "occupied_row_ratio": row_ratio,
                "occupied_column_ratio": column_ratio,
                "core_tile_support_ratio": tile_support,
                "core_component_count": int(core.get("visible_descendant_count") or 0),
                "outer_underfill": outer_underfill,
                "outer_overfill": outer_overfill,
                "evidence_intrusion": evidence_intrusion,
                "runtime_role_masks_used": True,
            }
    if not frame or width <= 0 or height <= 0 or len(frame) != width * height:
        return empty
    background = dominant_luma(frame)
    core_top = max(0, min(height - 1, round(height * PORTRAIT_CORE_TOP_RATIO)))
    core_bottom = max(core_top + 1, min(height, round(height * PORTRAIT_CORE_BOTTOM_RATIO)))
    evidence_top = max(core_bottom, min(height - 1, round(height * PORTRAIT_EVIDENCE_TOP_RATIO)))
    evidence_bottom = max(evidence_top + 1, min(height, round(height * PORTRAIT_EVIDENCE_BOTTOM_RATIO)))
    active = {
        (x, y)
        for y in range(core_top, evidence_bottom)
        for x, value in enumerate(frame[y * width : (y + 1) * width])
        if abs(value - background) >= CHANGE_PIXEL_LUMA
    }
    core_active = [(x, y) for x, y in active if y < core_bottom]
    if not core_active:
        return empty
    xs = [x for x, _ in core_active]
    ys = [y for _, y in core_active]
    lane_width = max(1.0, width * PORTRAIT_CONTENT_WIDTH_RATIO)
    lane_height = max(1, core_bottom - core_top)
    core_width_occupancy = (max(xs) - min(xs) + 1) / lane_width
    core_height_occupancy = (max(ys) - min(ys) + 1) / lane_height
    core_area_occupancy = core_width_occupancy * core_height_occupancy
    minimum_row_pixels = max(2, round(width * 0.006))
    minimum_column_pixels = max(2, round(lane_height * 0.006))
    row_counts: dict[int, int] = {}
    column_counts: dict[int, int] = {}
    for x, y in core_active:
        row_counts[y] = row_counts.get(y, 0) + 1
        column_counts[x] = column_counts.get(x, 0) + 1
    occupied_row_ratio = sum(value >= minimum_row_pixels for value in row_counts.values()) / lane_height
    occupied_column_ratio = (
        sum(value >= minimum_column_pixels for value in column_counts.values()) / lane_width
    )
    tile_columns, tile_rows = 20, 24
    occupied_tiles = {
        (
            min(tile_rows - 1, max(0, (y - core_top) * tile_rows // lane_height)),
            min(tile_columns - 1, max(0, x * tile_columns // width)),
        )
        for x, y in core_active
    }
    core_tile_support_ratio = len(occupied_tiles) / float(tile_columns * tile_rows)
    core_remaining = set(core_active)
    core_component_count = 0
    while core_remaining:
        start = core_remaining.pop()
        stack = [start]
        component_size = 1
        while stack:
            x, y = stack.pop()
            for neighbor in (
                (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
                (x - 1, y), (x + 1, y),
                (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
            ):
                if neighbor in core_remaining:
                    core_remaining.remove(neighbor)
                    stack.append(neighbor)
                    component_size += 1
        if component_size >= 3:
            core_component_count += 1
    outer_underfill = (
        core_width_occupancy < PORTRAIT_CORE_MIN_WIDTH_OCCUPANCY
        or core_height_occupancy < PORTRAIT_CORE_MIN_HEIGHT_OCCUPANCY
        or core_area_occupancy < PORTRAIT_CORE_MIN_AREA_OCCUPANCY
        or occupied_row_ratio < PORTRAIT_CORE_MIN_OCCUPIED_ROW_RATIO
        or occupied_column_ratio < PORTRAIT_CORE_MIN_OCCUPIED_COLUMN_RATIO
        or core_tile_support_ratio < PORTRAIT_CORE_MIN_TILE_SUPPORT_RATIO
    )
    outer_overfill = (
        core_width_occupancy > PORTRAIT_CORE_MAX_WIDTH_OCCUPANCY
        or core_height_occupancy > PORTRAIT_CORE_MAX_HEIGHT_OCCUPANCY
    )

    # Evidence is allowed below its top boundary. A connected foreground
    # component that starts there and crosses upward is an intrusion, while an
    # unrelated core component near the lower edge is not.
    remaining = set(active)
    evidence_intrusion = False
    while remaining and not evidence_intrusion:
        start = remaining.pop()
        stack = [start]
        component = [start]
        while stack:
            x, y = stack.pop()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        has_evidence = any(y >= evidence_top for _, y in component)
        crosses_evidence_top = any(y < evidence_top for _, y in component)
        evidence_intrusion = has_evidence and crosses_evidence_top
    return {
        "core_width_occupancy": core_width_occupancy,
        "core_height_occupancy": core_height_occupancy,
        "core_area_occupancy": core_area_occupancy,
        "occupied_row_ratio": occupied_row_ratio,
        "occupied_column_ratio": occupied_column_ratio,
        "core_tile_support_ratio": core_tile_support_ratio,
        "core_component_count": core_component_count,
        "outer_underfill": outer_underfill,
        "outer_overfill": outer_overfill,
        "evidence_intrusion": evidence_intrusion,
        "runtime_role_masks_used": False,
    }


def visual_lane_motion_evidence(
    previous: bytes,
    current: bytes,
    width: int,
    height: int,
) -> dict[str, float | bool]:
    """Measure localized movement or progressive drawing inside the visual lane."""
    if not previous or len(previous) != len(current) or len(current) != width * height:
        evidence = transition_motion_evidence(b"", b"", 0, 0)
        evidence.update(
            {
                "localized_motion_distribution": False,
                "gain_loss_balance_ratio": 0.0,
                "gain_loss_centroid_distance_ratio": 0.0,
                "changed_bbox_area_ratio": 0.0,
            }
        )
        return evidence
    top, bottom = _visual_lane_bounds(height)
    previous_lane = b"".join(previous[y * width : (y + 1) * width] for y in range(top, bottom))
    current_lane = b"".join(current[y * width : (y + 1) * width] for y in range(top, bottom))
    lane_height = bottom - top
    evidence = transition_motion_evidence(previous_lane, current_lane, width, lane_height)
    previous_background = dominant_luma(previous_lane)
    current_background = dominant_luma(current_lane)
    gained: list[tuple[int, int]] = []
    lost: list[tuple[int, int]] = []
    for index, (before, after) in enumerate(zip(previous_lane, current_lane)):
        before_active = abs(before - previous_background) >= CHANGE_PIXEL_LUMA
        after_active = abs(after - current_background) >= CHANGE_PIXEL_LUMA
        if before_active == after_active:
            continue
        coordinate = (index % width, index // width)
        if after_active:
            gained.append(coordinate)
        else:
            lost.append(coordinate)

    changed_coordinates = gained + lost
    changed_pixels = len(changed_coordinates)
    gain_loss_balance = min(len(gained), len(lost)) / max(len(gained), len(lost)) if gained and lost else 0.0
    if gained and lost:
        gained_centroid = (
            sum(x for x, _y in gained) / len(gained),
            sum(y for _x, y in gained) / len(gained),
        )
        lost_centroid = (
            sum(x for x, _y in lost) / len(lost),
            sum(y for _x, y in lost) / len(lost),
        )
        centroid_distance = math.hypot(
            gained_centroid[0] - lost_centroid[0],
            gained_centroid[1] - lost_centroid[1],
        ) / math.hypot(width, lane_height)
    else:
        centroid_distance = 0.0
    if changed_coordinates:
        changed_width = max(x for x, _y in changed_coordinates) - min(x for x, _y in changed_coordinates) + 1
        changed_height = max(y for _x, y in changed_coordinates) - min(y for _x, y in changed_coordinates) + 1
        changed_bbox_area_ratio = changed_width * changed_height / (width * lane_height)
    else:
        changed_bbox_area_ratio = 0.0
    localized_motion_distribution = (
        changed_pixels >= VISUAL_LANE_MOTION_MIN_CHANGED_PIXELS
        and gain_loss_balance >= VISUAL_LANE_MOTION_MIN_GAIN_LOSS_BALANCE
        and centroid_distance <= VISUAL_LANE_MOTION_MAX_CENTROID_DISTANCE_RATIO
        and changed_bbox_area_ratio <= VISUAL_LANE_MOTION_MAX_CHANGED_BBOX_RATIO
    )
    spatial_or_drawn = bool(evidence["spatial_or_drawn"]) or localized_motion_distribution
    evidence.update(
        {
            "active": bool(evidence["active"]) or localized_motion_distribution,
            "spatial_or_drawn": spatial_or_drawn,
            "opacity_dominated": (bool(evidence["active"]) or localized_motion_distribution) and not spatial_or_drawn,
            "localized_motion_distribution": localized_motion_distribution,
            "gain_loss_balance_ratio": gain_loss_balance,
            "gain_loss_centroid_distance_ratio": centroid_distance,
            "changed_bbox_area_ratio": changed_bbox_area_ratio,
        }
    )
    return evidence


def interior_empty_vertical_band_ratio(frame: bytes, width: int, height: int) -> float:
    """Return the largest empty interior row band between visible content.

    Outer letterbox/margin space is deliberately ignored. A title near the top
    and a tiny formula near the bottom therefore exposes the unused gulf between
    them, while a normally centered composition is not penalized for margins.
    """
    if not frame or width <= 0 or height <= 0:
        return 0.0
    background = dominant_luma(frame)
    minimum_active = max(2, round(width * 0.006))
    active_rows: list[int] = []
    for y in range(height):
        row = frame[y * width : (y + 1) * width]
        active = sum(1 for value in row if abs(value - background) >= CHANGE_PIXEL_LUMA)
        if active >= minimum_active:
            active_rows.append(y)
    if len(active_rows) < 2:
        return 0.0
    largest_gap = max(max(0, after - before - 1) for before, after in zip(active_rows, active_rows[1:]))
    return largest_gap / height


def _dilate_binary_mask(mask: bytes | bytearray, width: int, height: int, radius: int = 1) -> bytes:
    if not mask or len(mask) != width * height or radius < 0:
        return b""
    if radius == 0:
        return bytes(mask)
    dilated = bytearray(len(mask))
    for index, active in enumerate(mask):
        if not active:
            continue
        y, x = divmod(index, width)
        x0 = max(0, x - radius)
        x1 = min(width, x + radius + 1)
        fill = b"\x01" * (x1 - x0)
        for neighbor_y in range(max(0, y - radius), min(height, y + radius + 1)):
            start = neighbor_y * width + x0
            dilated[start : start + len(fill)] = fill
    return bytes(dilated)


def _temporal_visual_profiles(
    frames: list[bytes],
    width: int,
    height: int,
) -> tuple[list[int], list[bytes], list[bytes], list[int]]:
    pixel_count = width * height
    if pixel_count <= 0 or any(len(frame) != pixel_count for frame in frames):
        return [], [], [], []
    backgrounds: list[int] = []
    masks: list[bytes] = []
    dilated_masks: list[bytes] = []
    active_counts: list[int] = []
    for frame in frames:
        background = dominant_luma(frame)
        mask = bytearray(pixel_count)
        active_count = 0
        for index, value in enumerate(frame):
            if abs(value - background) >= TEMPORAL_VISUAL_FOREGROUND_LUMA:
                mask[index] = 1
                active_count += 1
        backgrounds.append(background)
        masks.append(bytes(mask))
        dilated_masks.append(_dilate_binary_mask(mask, width, height))
        active_counts.append(active_count)
    return backgrounds, masks, dilated_masks, active_counts


def _temporal_tile_geometry(width: int, height: int) -> tuple[int, int, list[int]]:
    columns = min(12, max(4, width // 8))
    rows = min(20, max(6, round(columns * height / max(1, width) * 0.94)))
    tile_for_pixel = [0] * (width * height)
    for y in range(height):
        tile_y = min(rows - 1, y * rows // height)
        row = y * width
        for x in range(width):
            tile_x = min(columns - 1, x * columns // width)
            tile_for_pixel[row + x] = tile_y * columns + tile_x
    return columns, rows, tile_for_pixel


def _tile_counts(mask: bytes | bytearray, tile_for_pixel: list[int], tile_count: int) -> list[int]:
    counts = [0] * tile_count
    for index, active in enumerate(mask):
        if active:
            counts[tile_for_pixel[index]] += 1
    return counts


def _tile_region_sum(
    counts: list[int],
    columns: int,
    tile_x: int,
    tile_y: int,
    tile_width: int,
    tile_height: int,
) -> int:
    return sum(
        sum(counts[row * columns + tile_x : row * columns + tile_x + tile_width])
        for row in range(tile_y, tile_y + tile_height)
    )


def _temporal_region_boxes(columns: int, rows: int, width: int, height: int) -> list[tuple[int, int, int, int]]:
    tile_widths = sorted({min(columns, value) for value in (3, 4, 6, 8, columns) if value <= columns})
    tile_heights = sorted({min(rows, value) for value in (2, 3, 4, 6, 8) if value <= rows})
    boxes: list[tuple[int, int, int, int]] = []
    for tile_height in tile_heights:
        for tile_width in tile_widths:
            if tile_width == columns and tile_height == rows:
                continue
            for tile_y in range(rows - tile_height + 1):
                for tile_x in range(columns - tile_width + 1):
                    x0 = tile_x * width // columns
                    y0 = tile_y * height // rows
                    x1 = (tile_x + tile_width) * width // columns
                    y1 = (tile_y + tile_height) * height // rows
                    boxes.append((x0, y0, x1, y1))
    return boxes


def _box_mask_component_areas(
    mask: bytes | bytearray,
    width: int,
    height: int,
    box: tuple[int, int, int, int],
) -> list[int]:
    x0, y0, x1, y1 = box
    visited: set[int] = set()
    areas: list[int] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            start = y * width + x
            if not mask[start] or start in visited:
                continue
            visited.add(start)
            stack = [start]
            area = 0
            while stack:
                index = stack.pop()
                area += 1
                current_y, current_x = divmod(index, width)
                for neighbor_y in range(max(y0, current_y - 1), min(y1, current_y + 2)):
                    row = neighbor_y * width
                    for neighbor_x in range(max(x0, current_x - 1), min(x1, current_x + 2)):
                        neighbor = row + neighbor_x
                        if mask[neighbor] and neighbor not in visited:
                            visited.add(neighbor)
                            stack.append(neighbor)
            if area >= 2:
                areas.append(area)
    return sorted(areas, reverse=True)


def _foreground_components(
    frame: bytes,
    width: int,
    height: int,
) -> list[dict[str, int]]:
    """Return small high-contrast connected regions with their geometry."""
    if not frame or len(frame) != width * height:
        return []
    background = dominant_luma(frame)
    mask = bytearray(
        1 if abs(value - background) >= VISUAL_SMALL_TEXT_FOREGROUND_LUMA else 0
        for value in frame
    )
    visited = bytearray(len(mask))
    components: list[dict[str, int]] = []
    for start, active in enumerate(mask):
        if not active or visited[start]:
            continue
        visited[start] = 1
        stack = [start]
        area = 0
        min_x = width
        max_x = 0
        min_y = height
        max_y = 0
        while stack:
            index = stack.pop()
            y, x = divmod(index, width)
            area += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
                row = neighbor_y * width
                for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = row + neighbor_x
                    if mask[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        stack.append(neighbor)
        if area >= 2:
            components.append(
                {
                    "x0": min_x,
                    "y0": min_y,
                    "x1": max_x + 1,
                    "y1": max_y + 1,
                    "area": area,
                }
            )
    return components


def _small_text_candidates(frame: bytes, width: int, height: int) -> list[dict[str, object]]:
    """Find compact glyph clusters while rejecting axes, ticks, and tiny labels."""
    maximum_height = max(3, round(height * VISUAL_SMALL_TEXT_MAX_HEIGHT_RATIO))
    components = sorted(
        [
            component
            for component in _foreground_components(frame, width, height)
            if component["y1"] - component["y0"] <= maximum_height
            and component["x1"] - component["x0"] <= width * 0.16
        ],
        key=lambda component: component["x0"],
    )
    if not components:
        return []

    # Characters in a line, and the stacked pieces of a fraction, remain close
    # after downsampling. Widely repeated graph ticks do not join this graph.
    horizontal_gap = max(3, round(maximum_height * 0.75))
    vertical_gap = max(2, round(maximum_height * 0.45))
    parents = list(range(len(components)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = root(first)
        second_root = root(second)
        if first_root != second_root:
            parents[second_root] = first_root

    for first_index, first in enumerate(components):
        for second_index in range(first_index + 1, len(components)):
            second = components[second_index]
            if second["x0"] - first["x1"] > horizontal_gap:
                break
            x_gap = max(0, max(first["x0"], second["x0"]) - min(first["x1"], second["x1"]))
            y_gap = max(0, max(first["y0"], second["y0"]) - min(first["y1"], second["y1"]))
            if x_gap <= horizontal_gap and y_gap <= vertical_gap:
                union(first_index, second_index)

    groups: dict[int, list[dict[str, int]]] = {}
    for index, component in enumerate(components):
        groups.setdefault(root(index), []).append(component)

    candidates: list[dict[str, object]] = []
    for group in groups.values():
        if len(group) < VISUAL_SMALL_TEXT_MIN_COMPONENTS:
            continue
        x0 = min(component["x0"] for component in group)
        y0 = min(component["y0"] for component in group)
        x1 = max(component["x1"] for component in group)
        y1 = max(component["y1"] for component in group)
        box_width = x1 - x0
        box_height = y1 - y0
        width_ratio = box_width / width
        height_ratio = box_height / height
        if not (
            VISUAL_SMALL_TEXT_MIN_WIDTH_RATIO <= width_ratio <= VISUAL_SMALL_TEXT_MAX_WIDTH_RATIO
            and VISUAL_SMALL_TEXT_MIN_HEIGHT_RATIO <= height_ratio < VISUAL_SMALL_TEXT_MAX_HEIGHT_RATIO
        ):
            continue
        active_pixels = sum(component["area"] for component in group)
        fill_ratio = active_pixels / max(1, box_width * box_height)
        substantial = [
            component
            for component in group
            if component["area"] >= 3
            and component["x1"] - component["x0"] >= 2
            and component["y1"] - component["y0"] >= 2
        ]
        horizontal_strokes = sum(
            component["x1"] - component["x0"] >= 2.5 * max(1, component["y1"] - component["y0"])
            for component in group
        )
        center_rows = {round((component["y0"] + component["y1"]) / 2) for component in group}
        text_like_variety = horizontal_strokes > 0 or len(group) >= 5 or len(center_rows) >= 3
        if len(substantial) < 2 or not 0.06 <= fill_ratio <= 0.68 or not text_like_variety:
            continue
        candidates.append(
            {
                "box": [x0, y0, x1, y1],
                "component_count": len(group),
                "active_pixels": active_pixels,
                "fill_ratio": fill_ratio,
                "height_ratio": height_ratio,
                "width_ratio": width_ratio,
                "horizontal_stroke_count": horizontal_strokes,
            }
        )
    return candidates


def _candidate_overlaps_ocr(
    candidate: dict[str, object],
    ocr_frame: dict[str, object] | None,
    width: int,
    height: int,
) -> bool:
    if not isinstance(ocr_frame, dict):
        return False
    source_width = int(ocr_frame.get("width") or 0)
    source_height = int(ocr_frame.get("height") or 0)
    if source_width <= 0 or source_height <= 0:
        return False
    box = list(candidate["box"])
    candidate_area = max(1, (box[2] - box[0]) * (box[3] - box[1]))
    for line in list(ocr_frame.get("lines") or []):
        if float(line.get("confidence", -1)) < OCR_MIN_LAYOUT_CONFIDENCE:
            continue
        line_box = [
            round(int(line.get("x") or 0) * width / source_width),
            round(int(line.get("y") or 0) * height / source_height),
            round((int(line.get("x") or 0) + int(line.get("width") or 0)) * width / source_width),
            round((int(line.get("y") or 0) + int(line.get("height") or 0)) * height / source_height),
        ]
        intersection = max(0, min(box[2], line_box[2]) - max(box[0], line_box[0])) * max(
            0, min(box[3], line_box[3]) - max(box[1], line_box[1])
        )
        if intersection / candidate_area >= 0.45:
            return True
    return False


def _formula_metadata_intervals(metadata: object) -> list[tuple[float, float]]:
    """Extract formula-like runtime windows from generic generated metadata."""
    intervals: list[tuple[float, float]] = []

    def visit(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        searchable = " ".join(
            str(item).lower()
            for key, item in value.items()
            if key in {"beat_id", "planned_transition_id", "persistent_object_ids", "kind", "role", "type"}
        )
        if any(token in searchable for token in ("formula", "equation", "math")):
            start = value.get("before_seconds", value.get("start_seconds", value.get("timestamp_seconds")))
            end = value.get("after_seconds", value.get("end_seconds", start))
            try:
                start_value = float(start)
                end_value = float(end)
                intervals.append((min(start_value, end_value), max(start_value, end_value)))
            except (TypeError, ValueError):
                pass
        for item in value.values():
            visit(item)

    visit(metadata)
    return intervals


def analyze_visual_small_text_fallback(
    frames: list[bytes],
    *,
    interval: float,
    width: int,
    height: int,
    ocr_frames: list[dict[str, object]] | None = None,
    ocr_interval: float = 0.0,
    runtime_metadata: object = None,
) -> dict[str, object]:
    """Detect sustained unreadably small formula/text geometry without OCR."""
    available = bool(frames and interval > 0 and width > 0 and height > 0)
    if not available:
        return {"available": False, "findings": [], "blocking_findings": []}
    ocr_frames = ocr_frames or []
    metadata_intervals = _formula_metadata_intervals(runtime_metadata)
    tracks: list[dict[str, object]] = []
    completed: list[dict[str, object]] = []

    for frame_index, frame in enumerate(frames):
        timestamp = frame_index * interval
        nearest_ocr: dict[str, object] | None = None
        if ocr_frames:
            nearest_ocr = min(
                ocr_frames,
                key=lambda item: abs(float(item.get("timestamp_seconds") or 0.0) - timestamp),
            )
            if abs(float(nearest_ocr.get("timestamp_seconds") or 0.0) - timestamp) > max(ocr_interval, interval) * 0.75:
                nearest_ocr = None
        candidates = [
            candidate
            for candidate in _small_text_candidates(frame, width, height)
            if not _candidate_overlaps_ocr(candidate, nearest_ocr, width, height)
        ]
        unmatched_tracks = set(range(len(tracks)))
        for candidate in candidates:
            best_index: int | None = None
            best_iou = 0.0
            for track_index in unmatched_tracks:
                track = tracks[track_index]
                previous = dict(track["last"])
                iou = _box_iou_pixels(list(previous["box"]), list(candidate["box"]))
                component_stable = abs(int(previous["component_count"]) - int(candidate["component_count"])) <= 2
                active_ratio = int(candidate["active_pixels"]) / max(1, int(previous["active_pixels"]))
                if iou >= VISUAL_SMALL_TEXT_MIN_TRACK_IOU and component_stable and 0.72 <= active_ratio <= 1.38 and iou > best_iou:
                    best_index = track_index
                    best_iou = iou
            if best_index is None:
                tracks.append({"start": frame_index, "end": frame_index, "last": candidate, "samples": 1})
            else:
                track = tracks[best_index]
                track.update({"end": frame_index, "last": candidate, "samples": int(track["samples"]) + 1})
                unmatched_tracks.remove(best_index)
        for track_index in sorted(unmatched_tracks, reverse=True):
            completed.append(tracks.pop(track_index))
    completed.extend(tracks)

    findings: list[dict[str, object]] = []
    for track in completed:
        duration = int(track["samples"]) * interval
        if duration + 1e-9 < VISUAL_SMALL_TEXT_MIN_DURATION_SECONDS:
            continue
        candidate = dict(track["last"])
        start_seconds = int(track["start"]) * interval
        end_seconds = (int(track["end"]) + 1) * interval
        metadata_confirmed = any(
            start_seconds <= metadata_end + interval and end_seconds >= metadata_start - interval
            for metadata_start, metadata_end in metadata_intervals
        )
        publish_blocking = (
            float(candidate["height_ratio"]) < VISUAL_SMALL_TEXT_BLOCKING_HEIGHT_RATIO
        )
        findings.append(
            {
                "frame_index": int(track["start"]),
                "timestamp_seconds": round(start_seconds, 3),
                "flags": [VISUAL_SMALL_TEXT_FLAG],
                "publish_blocking": publish_blocking,
                "blocking_flags": [VISUAL_SMALL_TEXT_FLAG] if publish_blocking else [],
                "evidence": {
                    "kind": "stable_small_text_like_connected_region",
                    "region_pixels": candidate["box"],
                    "duration_seconds": round(duration, 3),
                    "component_count": candidate["component_count"],
                    "height_ratio": round(float(candidate["height_ratio"]), 4),
                    "width_ratio": round(float(candidate["width_ratio"]), 4),
                    "fill_ratio": round(float(candidate["fill_ratio"]), 4),
                    "ocr_missed_region": True,
                    "runtime_formula_metadata_confirmed": metadata_confirmed,
                },
            }
        )
    return {
        "available": True,
        "sampling_strategy": "dense_stable_connected_region_geometry",
        "sampled_frames": len(frames),
        "sample_interval_seconds": interval,
        "candidate_track_count": len(completed),
        "formula_metadata_interval_count": len(metadata_intervals),
        "findings": findings,
        "blocking_findings": [finding for finding in findings if finding["publish_blocking"]],
        "thresholds": {
            "minimum_height_ratio": VISUAL_SMALL_TEXT_MIN_HEIGHT_RATIO,
            "blocking_height_ratio": VISUAL_SMALL_TEXT_BLOCKING_HEIGHT_RATIO,
            "phone_readable_height_ratio": VISUAL_SMALL_TEXT_MAX_HEIGHT_RATIO,
            "minimum_width_ratio": VISUAL_SMALL_TEXT_MIN_WIDTH_RATIO,
            "phone_readable_width_ratio": VISUAL_SMALL_TEXT_MAX_WIDTH_RATIO,
            "minimum_component_count": VISUAL_SMALL_TEXT_MIN_COMPONENTS,
            "minimum_sustained_seconds": VISUAL_SMALL_TEXT_MIN_DURATION_SECONDS,
            "minimum_track_iou": VISUAL_SMALL_TEXT_MIN_TRACK_IOU,
        },
    }


def _box_iou_pixels(first: list[int], second: list[int]) -> float:
    first_x0, first_y0, first_x1, first_y1 = first
    second_x0, second_y0, second_x1, second_y1 = second
    intersection = max(0, min(first_x1, second_x1) - max(first_x0, second_x0)) * max(
        0,
        min(first_y1, second_y1) - max(first_y0, second_y0),
    )
    first_area = max(0, first_x1 - first_x0) * max(0, first_y1 - first_y0)
    second_area = max(0, second_x1 - second_x0) * max(0, second_y1 - second_y0)
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


def _dedupe_temporal_visual_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for finding in sorted(findings, key=lambda item: float(item.get("_score") or 0.0), reverse=True):
        evidence = dict(finding.get("evidence") or {})
        box = list(evidence.get("region_pixels") or [0, 0, 0, 0])
        timestamp = float(finding.get("timestamp_seconds") or 0.0)
        kind = str(evidence.get("kind") or "")
        duplicate = False
        for existing in selected:
            existing_evidence = dict(existing.get("evidence") or {})
            existing_kind = str(existing_evidence.get("kind") or "")
            existing_timestamp = float(existing.get("timestamp_seconds") or 0.0)
            time_limit = 0.8 if "collision" in kind or "collision" in existing_kind else 0.35
            if (
                abs(timestamp - existing_timestamp) <= time_limit
                and _box_iou_pixels(box, list(existing_evidence.get("region_pixels") or [0, 0, 0, 0])) >= 0.15
            ):
                duplicate = True
                break
        if not duplicate:
            finding.pop("_score", None)
            selected.append(finding)
        if len(selected) >= 24:
            break
    return sorted(selected, key=lambda item: float(item.get("timestamp_seconds") or 0.0))


def analyze_temporal_visual_integrity(
    frames: list[bytes],
    *,
    interval: float,
    width: int,
    height: int,
) -> dict[str, object]:
    """Find local structural destruction while tolerating fades and causal motion.

    Abrupt loss must be a temporal outlier that cuts through a still-retained
    region. Collision evidence is stricter: the same local window must contain
    full-strength source residue, destination residue, and center-only pixels.
    """
    available = bool(len(frames) >= 3 and interval > 0 and width > 0 and height > 0)
    backgrounds, masks, dilated_masks, active_counts = _temporal_visual_profiles(frames, width, height)
    if not available or not masks:
        return {
            "available": False,
            "sampled_frames": len(frames),
            "sample_interval_seconds": interval,
            "integrity_loss_count": 0,
            "abrupt_loss_candidate_count": 0,
            "collision_candidate_count": 0,
            "coherent_transition_suppression_count": 0,
            "causal_motion_suppression_count": 0,
            "findings": [],
        }

    columns, rows, tile_for_pixel = _temporal_tile_geometry(width, height)
    tile_count = columns * rows
    region_boxes = _temporal_region_boxes(columns, rows, width, height)
    transition_profiles: list[dict[str, float | int]] = []
    for frame_index in range(1, len(frames)):
        previous_mask = masks[frame_index - 1]
        current_mask = masks[frame_index]
        previous_dilated = dilated_masks[frame_index - 1]
        current_dilated = dilated_masks[frame_index]
        loss_count = 0
        gain_count = 0
        for previous, current, previous_near, current_near in zip(
            previous_mask,
            current_mask,
            previous_dilated,
            current_dilated,
        ):
            loss_count += int(bool(previous and not current_near))
            gain_count += int(bool(current and not previous_near))
        transition_profiles.append(
            {
                "frame_index": frame_index,
                "loss_count": loss_count,
                "gain_count": gain_count,
                "loss_ratio": loss_count / max(1, active_counts[frame_index - 1]),
            }
        )

    findings: list[dict[str, object]] = []
    abrupt_candidates = 0
    collision_candidates = 0
    coherent_suppressions = 0
    causal_suppressions = 0
    for transition_index, profile in enumerate(transition_profiles):
        frame_index = int(profile["frame_index"])
        loss_count = int(profile["loss_count"])
        gain_count = int(profile["gain_count"])
        nearby_losses = [
            int(other["loss_count"])
            for index, other in enumerate(transition_profiles)
            if index != transition_index and abs(index - transition_index) <= 5
        ]
        baseline_loss = percentile([float(value) for value in nearby_losses], 0.5)
        outlier_floor = baseline_loss * TEMPORAL_VISUAL_OUTLIER_MULTIPLIER + TEMPORAL_VISUAL_OUTLIER_MARGIN_PIXELS
        if (
            loss_count < TEMPORAL_VISUAL_MIN_GLOBAL_LOSS_PIXELS
            or float(profile["loss_ratio"]) < TEMPORAL_VISUAL_MIN_GLOBAL_LOSS_RATIO
            or loss_count < outlier_floor
        ):
            continue
        abrupt_candidates += 1
        adjacent_losses = [
            int(transition_profiles[index]["loss_count"])
            for index in (transition_index - 1, transition_index + 1)
            if 0 <= index < len(transition_profiles)
        ]
        if adjacent_losses and max(adjacent_losses) > (
            loss_count * TEMPORAL_VISUAL_MAX_ADJACENT_LOSS_RATIO + TEMPORAL_VISUAL_OUTLIER_MARGIN_PIXELS
        ):
            coherent_suppressions += 1
            continue
        if gain_count > loss_count * TEMPORAL_VISUAL_MAX_GAIN_TO_LOSS_RATIO:
            causal_suppressions += 1
            continue

        previous_mask = masks[frame_index - 1]
        current_mask = masks[frame_index]
        current_dilated = dilated_masks[frame_index]
        previous_dilated = dilated_masks[frame_index - 1]
        loss_mask = bytearray(width * height)
        gain_mask = bytearray(width * height)
        strong_retained_mask = bytearray(width * height)
        previous_background = backgrounds[frame_index - 1]
        current_background = backgrounds[frame_index]
        for index, (previous, current, previous_near, current_near) in enumerate(
            zip(previous_mask, current_mask, previous_dilated, current_dilated)
        ):
            if previous and not current_near:
                loss_mask[index] = 1
            if current and not previous_near:
                gain_mask[index] = 1
            if previous and current:
                previous_contrast = abs(frames[frame_index - 1][index] - previous_background)
                current_contrast = abs(frames[frame_index][index] - current_background)
                if current_contrast >= previous_contrast * TEMPORAL_VISUAL_STRONG_RETENTION_RATIO:
                    strong_retained_mask[index] = 1
        if frame_index >= 2:
            preloss_ratios: list[float] = []
            earlier_background = backgrounds[frame_index - 2]
            for index, lost in enumerate(loss_mask):
                if not lost:
                    continue
                earlier_contrast = abs(frames[frame_index - 2][index] - earlier_background)
                if earlier_contrast < TEMPORAL_VISUAL_FOREGROUND_LUMA * 0.65:
                    continue
                previous_contrast = abs(frames[frame_index - 1][index] - previous_background)
                preloss_ratios.append(previous_contrast / earlier_contrast)
            coherent_preloss_ratio = (
                sum(ratio <= TEMPORAL_VISUAL_FADE_PRELOSS_MAX_RETENTION for ratio in preloss_ratios)
                / len(preloss_ratios)
                if preloss_ratios
                else 0.0
            )
            if (
                len(preloss_ratios) >= max(8, round(loss_count * 0.35))
                and coherent_preloss_ratio >= TEMPORAL_VISUAL_FADE_PRELOSS_COHERENT_RATIO
            ):
                coherent_suppressions += 1
                continue
        retained_neighborhood = _dilate_binary_mask(strong_retained_mask, width, height, radius=2)
        cut_mask = bytes(
            int(bool(lost and retained_near))
            for lost, retained_near in zip(loss_mask, retained_neighborhood)
        )
        recovery_masks = dilated_masks[frame_index + 1 : min(len(dilated_masks), frame_index + 3)]
        recovered_mask = bytes(
            int(bool(lost and any(future[index] for future in recovery_masks)))
            for index, lost in enumerate(loss_mask)
        )
        count_sets = {
            "expected": _tile_counts(previous_mask, tile_for_pixel, tile_count),
            "lost": _tile_counts(loss_mask, tile_for_pixel, tile_count),
            "gained": _tile_counts(gain_mask, tile_for_pixel, tile_count),
            "retained": _tile_counts(strong_retained_mask, tile_for_pixel, tile_count),
            "cut": _tile_counts(cut_mask, tile_for_pixel, tile_count),
            "recovered": _tile_counts(recovered_mask, tile_for_pixel, tile_count),
        }
        best_region: tuple[float, tuple[int, int, int, int], dict[str, float | int]] | None = None
        for box in region_boxes:
            x0, y0, x1, y1 = box
            tile_x0 = x0 * columns // width
            tile_y0 = y0 * rows // height
            tile_x1 = math.ceil(x1 * columns / width)
            tile_y1 = math.ceil(y1 * rows / height)
            tile_width = max(1, tile_x1 - tile_x0)
            tile_height = max(1, tile_y1 - tile_y0)
            expected = _tile_region_sum(count_sets["expected"], columns, tile_x0, tile_y0, tile_width, tile_height)
            lost = _tile_region_sum(count_sets["lost"], columns, tile_x0, tile_y0, tile_width, tile_height)
            gained = _tile_region_sum(count_sets["gained"], columns, tile_x0, tile_y0, tile_width, tile_height)
            retained = _tile_region_sum(count_sets["retained"], columns, tile_x0, tile_y0, tile_width, tile_height)
            cut = _tile_region_sum(count_sets["cut"], columns, tile_x0, tile_y0, tile_width, tile_height)
            recovered = _tile_region_sum(count_sets["recovered"], columns, tile_x0, tile_y0, tile_width, tile_height)
            loss_ratio = lost / max(1, expected)
            retention_ratio = retained / max(1, expected)
            cut_ratio = cut / max(1, lost)
            recovery_ratio = recovered / max(1, lost)
            if (
                expected < TEMPORAL_VISUAL_MIN_REGION_PIXELS
                or lost < TEMPORAL_VISUAL_MIN_REGION_LOSS_PIXELS
                or loss_ratio < TEMPORAL_VISUAL_MIN_REGION_LOSS_RATIO
                or loss_ratio > TEMPORAL_VISUAL_MAX_REGION_LOSS_RATIO
                or retention_ratio < TEMPORAL_VISUAL_MIN_REGION_RETENTION_RATIO
                or gained > lost * TEMPORAL_VISUAL_MAX_GAIN_TO_LOSS_RATIO
                or cut < TEMPORAL_VISUAL_MIN_CUT_PIXELS
                or cut_ratio < TEMPORAL_VISUAL_MIN_CUT_RATIO
                or recovery_ratio < TEMPORAL_VISUAL_MIN_RECOVERY_RATIO
            ):
                continue
            score = loss_ratio * min(1.0, lost / 40) * (1 + min(0.5, cut_ratio))
            evidence = {
                "expected_foreground_pixels": expected,
                "lost_foreground_pixels": lost,
                "gained_foreground_pixels": gained,
                "strongly_retained_foreground_pixels": retained,
                "recovered_foreground_pixels": recovered,
                "regional_loss_ratio": loss_ratio,
                "regional_retention_ratio": retention_ratio,
                "loss_retention_cut_ratio": cut_ratio,
                "regional_recovery_ratio": recovery_ratio,
            }
            if best_region is None or score > best_region[0]:
                best_region = (score, box, evidence)

        if best_region is None:
            coherent_suppressions += 1
            continue
        score, box, evidence = best_region
        loss_components = _box_mask_component_areas(loss_mask, width, height, box)
        if not loss_components:
            coherent_suppressions += 1
            continue
        isolated_loss = len(loss_components) < 3
        compact_causal_carrier = (
            len(loss_components) == 1
            and int(evidence["lost_foreground_pixels"]) <= TEMPORAL_VISUAL_MAX_CAUSAL_CARRIER_LOSS_PIXELS
            and int(evidence["expected_foreground_pixels"]) <= TEMPORAL_VISUAL_MAX_CAUSAL_CARRIER_REGION_PIXELS
            and float(evidence["regional_recovery_ratio"]) >= TEMPORAL_VISUAL_MIN_CAUSAL_CARRIER_RECOVERY_RATIO
        )
        if compact_causal_carrier:
            causal_suppressions += 1
            continue
        if isolated_loss and (
            int(evidence["lost_foreground_pixels"]) < TEMPORAL_VISUAL_MIN_ISOLATED_LOSS_PIXELS
            or float(evidence["regional_loss_ratio"]) < TEMPORAL_VISUAL_MIN_ISOLATED_LOSS_RATIO
        ):
            causal_suppressions += 1
            continue
        kind = (
            "regional_shredding"
            if len(loss_components) >= 3 and (not loss_components or loss_components[0] < int(evidence["lost_foreground_pixels"]) * 0.75)
            else "isolated_regional_loss_or_partial_wipe"
        )
        timestamp = frame_index * interval
        findings.append(
            {
                "_score": score,
                "frame_index": frame_index,
                "timestamp_seconds": round(timestamp, 3),
                "flags": [TEMPORAL_VISUAL_FLAG, kind],
                "publish_blocking": True,
                "blocking_flags": [TEMPORAL_VISUAL_FLAG],
                "examples": [],
                "evidence": {
                    "kind": kind,
                    "region_pixels": list(box),
                    "transition_neighbor_timestamps_seconds": [
                        round((frame_index - 1) * interval, 3),
                        round(frame_index * interval, 3),
                    ],
                    "global_loss_pixels": loss_count,
                    "global_gain_pixels": gain_count,
                    "nearby_median_loss_pixels": round(baseline_loss, 2),
                    "loss_component_count": len(loss_components),
                    **{key: round(value, 4) if isinstance(value, float) else value for key, value in evidence.items()},
                },
            }
        )

    collision_radii = sorted(
        {
            max(2, round(seconds / interval))
            for seconds in TEMPORAL_VISUAL_COLLISION_CONTEXT_SECONDS
            if round(seconds / interval) * 2 < len(frames)
        }
    )
    collision_min_endpoint_pixels = max(
        TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_PIXELS,
        round(width * height * TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_AREA_RATIO),
    )
    collision_min_extra_pixels = max(
        TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_PIXELS,
        round(width * height * TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_AREA_RATIO),
    )
    for radius in collision_radii:
        for frame_index in range(radius, len(frames) - radius, 2):
            before_index = frame_index - radius
            after_index = frame_index + radius
            before_mask = masks[before_index]
            center_mask = masks[frame_index]
            after_mask = masks[after_index]
            before_dilated = dilated_masks[before_index]
            after_dilated = dilated_masks[after_index]
            before_only = bytearray(width * height)
            after_only = bytearray(width * height)
            before_residue = bytearray(width * height)
            after_residue = bytearray(width * height)
            center_extra = bytearray(width * height)
            before_only_count = 0
            after_only_count = 0
            before_residue_count = 0
            after_residue_count = 0
            extra_count = 0
            for index, (before, center, after, before_near, after_near) in enumerate(
                zip(before_mask, center_mask, after_mask, before_dilated, after_dilated)
            ):
                unique_before = bool(before and not after_near)
                unique_after = bool(after and not before_near)
                extra = bool(center and not before_near and not after_near)
                if unique_before:
                    before_only[index] = 1
                    before_only_count += 1
                    if center:
                        before_residue[index] = 1
                        before_residue_count += 1
                if unique_after:
                    after_only[index] = 1
                    after_only_count += 1
                    if center:
                        after_residue[index] = 1
                        after_residue_count += 1
                if extra:
                    center_extra[index] = 1
                    extra_count += 1
            if (
                before_only_count < collision_min_endpoint_pixels
                or after_only_count < collision_min_endpoint_pixels
                or extra_count < collision_min_extra_pixels
                or min(before_only_count, after_only_count) / max(before_only_count, after_only_count)
                < TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_BALANCE * 0.5
                or before_residue_count / before_only_count < TEMPORAL_VISUAL_COLLISION_MIN_RESIDUE_RATIO
                or after_residue_count / after_only_count < TEMPORAL_VISUAL_COLLISION_MIN_RESIDUE_RATIO
            ):
                continue

            collision_candidates += 1
            count_sets = {
                "before": _tile_counts(before_only, tile_for_pixel, tile_count),
                "after": _tile_counts(after_only, tile_for_pixel, tile_count),
                "before_residue": _tile_counts(before_residue, tile_for_pixel, tile_count),
                "after_residue": _tile_counts(after_residue, tile_for_pixel, tile_count),
                "extra": _tile_counts(center_extra, tile_for_pixel, tile_count),
            }
            best_region: tuple[float, tuple[int, int, int, int], dict[str, float | int]] | None = None
            for box in region_boxes:
                x0, y0, x1, y1 = box
                tile_x0 = x0 * columns // width
                tile_y0 = y0 * rows // height
                tile_x1 = math.ceil(x1 * columns / width)
                tile_y1 = math.ceil(y1 * rows / height)
                tile_width = max(1, tile_x1 - tile_x0)
                tile_height = max(1, tile_y1 - tile_y0)
                values = {
                    name: _tile_region_sum(counts, columns, tile_x0, tile_y0, tile_width, tile_height)
                    for name, counts in count_sets.items()
                }
                before_pixels = values["before"]
                after_pixels = values["after"]
                extra_pixels = values["extra"]
                endpoint_balance = min(before_pixels, after_pixels) / max(1, max(before_pixels, after_pixels))
                before_ratio = values["before_residue"] / max(1, before_pixels)
                after_ratio = values["after_residue"] / max(1, after_pixels)
                extra_ratio = extra_pixels / max(1, min(before_pixels, after_pixels))
                if (
                    before_pixels < collision_min_endpoint_pixels
                    or after_pixels < collision_min_endpoint_pixels
                    or endpoint_balance < TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_BALANCE
                    or before_ratio < TEMPORAL_VISUAL_COLLISION_MIN_RESIDUE_RATIO
                    or after_ratio < TEMPORAL_VISUAL_COLLISION_MIN_RESIDUE_RATIO
                    or extra_pixels < collision_min_extra_pixels
                    or extra_ratio < TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_RATIO
                ):
                    continue
                score = min(before_ratio, after_ratio) * min(1.0, extra_ratio)
                evidence = {
                    "source_only_pixels": before_pixels,
                    "destination_only_pixels": after_pixels,
                    "endpoint_pixel_balance_ratio": endpoint_balance,
                    "source_residue_ratio": before_ratio,
                    "destination_residue_ratio": after_ratio,
                    "center_only_pixels": extra_pixels,
                    "center_only_to_endpoint_ratio": extra_ratio,
                }
                if best_region is None or score > best_region[0]:
                    best_region = (score, box, evidence)
            if best_region is None:
                causal_suppressions += 1
                continue
            score, box, evidence = best_region
            kind = "destructive_transition_collision"
            findings.append(
                {
                    "_score": score,
                    "frame_index": frame_index,
                    "timestamp_seconds": round(frame_index * interval, 3),
                    "flags": [TEMPORAL_VISUAL_FLAG, kind],
                    "publish_blocking": True,
                    "blocking_flags": [TEMPORAL_VISUAL_FLAG],
                    "examples": [],
                    "evidence": {
                        "kind": kind,
                        "region_pixels": list(box),
                        "context_timestamps_seconds": [
                            round(before_index * interval, 3),
                            round(frame_index * interval, 3),
                            round(after_index * interval, 3),
                        ],
                        **{key: round(value, 4) if isinstance(value, float) else value for key, value in evidence.items()},
                    },
                }
            )

    unique_findings = _dedupe_temporal_visual_findings(findings)
    return {
        "available": True,
        "sampled_frames": len(frames),
        "sample_interval_seconds": interval,
        "sampling_strategy": "dense_multiscale_temporal_structural_sampling",
        "frame_budget": TEMPORAL_VISUAL_MAX_FRAMES,
        "integrity_loss_count": len(unique_findings),
        "publish_blocking_finding_count": len(unique_findings),
        "abrupt_loss_candidate_count": abrupt_candidates,
        "collision_candidate_count": collision_candidates,
        "coherent_transition_suppression_count": coherent_suppressions,
        "causal_motion_suppression_count": causal_suppressions,
        "thresholds": {
            "foreground_luma_delta": TEMPORAL_VISUAL_FOREGROUND_LUMA,
            "fade_preloss_max_contrast_retention": TEMPORAL_VISUAL_FADE_PRELOSS_MAX_RETENTION,
            "fade_preloss_minimum_coherent_ratio": TEMPORAL_VISUAL_FADE_PRELOSS_COHERENT_RATIO,
            "minimum_global_loss_pixels": TEMPORAL_VISUAL_MIN_GLOBAL_LOSS_PIXELS,
            "minimum_global_loss_ratio": TEMPORAL_VISUAL_MIN_GLOBAL_LOSS_RATIO,
            "maximum_gain_to_loss_ratio": TEMPORAL_VISUAL_MAX_GAIN_TO_LOSS_RATIO,
            "outlier_multiplier": TEMPORAL_VISUAL_OUTLIER_MULTIPLIER,
            "maximum_adjacent_loss_ratio": TEMPORAL_VISUAL_MAX_ADJACENT_LOSS_RATIO,
            "minimum_region_loss_ratio": TEMPORAL_VISUAL_MIN_REGION_LOSS_RATIO,
            "maximum_region_loss_ratio": TEMPORAL_VISUAL_MAX_REGION_LOSS_RATIO,
            "minimum_region_retention_ratio": TEMPORAL_VISUAL_MIN_REGION_RETENTION_RATIO,
            "minimum_region_recovery_ratio": TEMPORAL_VISUAL_MIN_RECOVERY_RATIO,
            "minimum_isolated_region_loss_pixels": TEMPORAL_VISUAL_MIN_ISOLATED_LOSS_PIXELS,
            "minimum_isolated_region_loss_ratio": TEMPORAL_VISUAL_MIN_ISOLATED_LOSS_RATIO,
            "maximum_causal_carrier_loss_pixels": TEMPORAL_VISUAL_MAX_CAUSAL_CARRIER_LOSS_PIXELS,
            "maximum_causal_carrier_region_pixels": TEMPORAL_VISUAL_MAX_CAUSAL_CARRIER_REGION_PIXELS,
            "minimum_causal_carrier_recovery_ratio": TEMPORAL_VISUAL_MIN_CAUSAL_CARRIER_RECOVERY_RATIO,
            "collision_context_seconds": list(TEMPORAL_VISUAL_COLLISION_CONTEXT_SECONDS),
            "collision_minimum_endpoint_area_ratio": TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_AREA_RATIO,
            "collision_minimum_endpoint_balance_ratio": TEMPORAL_VISUAL_COLLISION_MIN_ENDPOINT_BALANCE,
            "collision_minimum_endpoint_residue_ratio": TEMPORAL_VISUAL_COLLISION_MIN_RESIDUE_RATIO,
            "collision_minimum_center_only_ratio": TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_RATIO,
            "collision_minimum_center_only_area_ratio": TEMPORAL_VISUAL_COLLISION_MIN_EXTRA_AREA_RATIO,
        },
        "findings": unique_findings,
    }


def parse_tesseract_tsv(tsv: str) -> dict[str, object] | None:
    """Parse Tesseract TSV into word and line regions without third-party packages."""
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t"))
    if not rows:
        return None

    width = height = 0
    words: list[dict[str, object]] = []
    line_words: dict[tuple[int, int, int, int], list[dict[str, object]]] = {}
    for row in rows:
        try:
            level = int(row.get("level") or 0)
            left = int(row.get("left") or 0)
            top = int(row.get("top") or 0)
            box_width = int(row.get("width") or 0)
            box_height = int(row.get("height") or 0)
        except ValueError:
            continue
        if level == 1:
            width = max(width, box_width)
            height = max(height, box_height)
        if level != 5:
            continue
        text = (row.get("text") or "").strip()
        if not text or box_width <= 0 or box_height <= 0:
            continue
        try:
            confidence = float(row.get("conf") or -1)
        except ValueError:
            confidence = -1.0
        key = tuple(int(row.get(name) or 0) for name in ("page_num", "block_num", "par_num", "line_num"))
        word: dict[str, object] = {
            "text": text,
            "confidence": confidence,
            "x": left,
            "y": top,
            "width": box_width,
            "height": box_height,
            "line_key": key,
        }
        words.append(word)
        if confidence >= OCR_MIN_LAYOUT_CONFIDENCE or any(character.isalnum() for character in text):
            line_words.setdefault(key, []).append(word)

    lines: list[dict[str, object]] = []
    for key, grouped_words in line_words.items():
        left = min(int(word["x"]) for word in grouped_words)
        top = min(int(word["y"]) for word in grouped_words)
        right = max(int(word["x"]) + int(word["width"]) for word in grouped_words)
        bottom = max(int(word["y"]) + int(word["height"]) for word in grouped_words)
        ordered = sorted(grouped_words, key=lambda word: int(word["x"]))
        confidences = [float(word["confidence"]) for word in ordered if float(word["confidence"]) >= 0]
        lines.append(
            {
                "key": key,
                "text": " ".join(str(word["text"]) for word in ordered),
                "confidence": sum(confidences) / len(confidences) if confidences else -1.0,
                "x": left,
                "y": top,
                "width": right - left,
                "height": bottom - top,
                "words": ordered,
            }
        )
    return {"width": width, "height": height, "words": words, "lines": lines}


def _axis_overlap(start_a: int, size_a: int, start_b: int, size_b: int) -> int:
    return max(0, min(start_a + size_a, start_b + size_b) - max(start_a, start_b))


def _inset_axis_overlap_ratio(start_a: float, size_a: float, start_b: float, size_b: float, inset_ratio: float) -> float:
    inset_a = size_a * inset_ratio
    inset_b = size_b * inset_ratio
    inner_start_a = start_a + inset_a
    inner_start_b = start_b + inset_b
    inner_size_a = max(1.0, size_a - 2 * inset_a)
    inner_size_b = max(1.0, size_b - 2 * inset_b)
    overlap = max(
        0.0,
        min(inner_start_a + inner_size_a, inner_start_b + inner_size_b)
        - max(inner_start_a, inner_start_b),
    )
    return overlap / max(1.0, min(inner_size_a, inner_size_b))


def _robust_line_vertical_box(line: dict[str, object]) -> tuple[float, float]:
    words = [
        word
        for word in line.get("words", [])
        if int(word.get("height", 0) or 0) > 0
    ]
    if len(words) < 2:
        return float(line["y"]), float(max(1, int(line["height"])))
    heights = [float(word["height"]) for word in words]
    lower_quartile = max(1.0, percentile(heights, 0.25))
    # PSM 11 sometimes joins a faint neighboring stroke to one word and makes
    # that box several times taller than the visible glyphs. Use the compact
    # word cluster so that artifact cannot manufacture a line collision.
    compact_words = [
        word
        for word in words
        if float(word["height"]) <= lower_quartile * 1.55
    ]
    if len(compact_words) < max(1, math.ceil(len(words) * 0.4)):
        compact_words = words
    compact_heights = [float(word["height"]) for word in compact_words]
    centers = [float(word["y"]) + float(word["height"]) / 2 for word in compact_words]
    robust_height = max(1.0, percentile(compact_heights, 0.5))
    robust_center = percentile(centers, 0.5)
    return robust_center - robust_height / 2, robust_height


def is_essential_text_line(line: dict[str, object]) -> bool:
    """Return whether an OCR line is reliable enough to block publication."""
    if float(line.get("confidence", -1)) < OCR_ESSENTIAL_TEXT_CONFIDENCE:
        return False
    alphanumeric = sum(character.isalnum() for character in str(line.get("text") or ""))
    return alphanumeric >= 2


def text_line_outside_safe_area(line: dict[str, object], width: int, height: int) -> bool:
    return (
        int(line["x"]) < width * OCR_SAFE_HORIZONTAL_INSET_RATIO
        or int(line["x"]) + int(line["width"]) > width * (1 - OCR_SAFE_HORIZONTAL_INSET_RATIO)
        or int(line["y"]) < height * OCR_SAFE_VERTICAL_INSET_RATIO
        or int(line["y"]) + int(line["height"]) > height * (1 - OCR_SAFE_VERTICAL_INSET_RATIO)
    )


def _script_pair(first: dict[str, object], second: dict[str, object]) -> bool:
    """Recognize small superscript/subscript regions before overlap scoring."""
    height_a = max(1, int(first["height"]))
    height_b = max(1, int(second["height"]))
    smaller, larger = (first, second) if height_a <= height_b else (second, first)
    ratio = int(smaller["height"]) / max(1, int(larger["height"]))
    if ratio > 0.68:
        return False
    small_center_y = int(smaller["y"]) + int(smaller["height"]) / 2
    large_center_y = int(larger["y"]) + int(larger["height"]) / 2
    horizontal_gap = max(
        0,
        max(int(smaller["x"]), int(larger["x"]))
        - min(int(smaller["x"]) + int(smaller["width"]), int(larger["x"]) + int(larger["width"])),
    )
    larger_right = int(larger["x"]) + int(larger["width"])
    script_anchor = int(smaller["x"])
    anchored_at_line_end = (
        larger_right - int(larger["height"]) * 0.35
        <= script_anchor
        <= larger_right + int(larger["height"]) * 0.75
    )
    return (
        abs(small_center_y - large_center_y) >= int(larger["height"]) * 0.16
        and horizontal_gap <= int(larger["height"]) * 0.75
        and anchored_at_line_end
        and int(smaller["width"]) <= max(int(larger["width"]) * 0.75, int(larger["height"]) * 2)
    )


def text_line_overlap_pairs(lines: list[dict[str, object]]) -> list[tuple[int, int, str]]:
    """Find intersecting text lines.

    Similar-height regions must overlap substantially. Small regions aligned as
    super/subscripts are ignored so ordinary mathematical notation is not
    mistaken for a collision.
    """
    collisions: list[tuple[int, int, str]] = []
    for first_index, first in enumerate(lines):
        if float(first.get("confidence", -1)) < OCR_MIN_LAYOUT_CONFIDENCE:
            continue
        for second_index in range(first_index + 1, len(lines)):
            second = lines[second_index]
            if float(second.get("confidence", -1)) < OCR_MIN_LAYOUT_CONFIDENCE or _script_pair(first, second):
                continue
            x_overlap = _axis_overlap(int(first["x"]), int(first["width"]), int(second["x"]), int(second["width"]))
            x_ratio = x_overlap / max(1, min(int(first["width"]), int(second["width"])))
            robust_y_a, robust_height_a = _robust_line_vertical_box(first)
            robust_y_b, robust_height_b = _robust_line_vertical_box(second)
            similar_height = (
                min(robust_height_a, robust_height_b) / max(robust_height_a, robust_height_b)
                >= OCR_SIMILAR_LINE_HEIGHT_RATIO
            )
            if similar_height:
                vertical_collision = _inset_axis_overlap_ratio(
                    robust_y_a,
                    robust_height_a,
                    robust_y_b,
                    robust_height_b,
                    OCR_LINE_BOX_VERTICAL_INSET_RATIO,
                ) >= OCR_INSET_LINE_OVERLAP_RATIO
            else:
                robust_overlap = max(
                    0.0,
                    min(robust_y_a + robust_height_a, robust_y_b + robust_height_b)
                    - max(robust_y_a, robust_y_b),
                )
                vertical_collision = (
                    robust_overlap / max(1.0, min(robust_height_a, robust_height_b))
                    >= 0.30
                )
            if x_ratio >= 0.16 and vertical_collision:
                collisions.append((first_index, second_index, "overlap"))
    return collisions


def suspicious_run_together_word(word: dict[str, object]) -> bool:
    text = str(word.get("text") or "").strip()
    alphanumeric = "".join(character for character in text if character.isalnum())
    if len(alphanumeric) < 5 or re.search(r"[=+*/^_\\]", text) or "-" in text:
        return False
    lowered = alphanumeric.lower()
    if any(lowered == f"a{stem}" or lowered == f"an{stem}" or lowered == f"the{stem}" for stem in FUSED_ARTICLE_STEMS):
        return True
    if not re.fullmatch(r"[A-Za-z0-9]+", text):
        return False
    if re.search(r"[a-z]{2,}[A-Z][a-z]{2,}", alphanumeric) or re.search(r"[A-Za-z]{2,}\d[A-Za-z]{2,}", alphanumeric):
        return True
    aspect_ratio = int(word.get("width") or 0) / max(1, int(word.get("height") or 0))
    return len(alphanumeric) >= 18 and aspect_ratio >= 6.5


def _normalized_ocr_text(line: dict[str, object]) -> str:
    return "".join(character.lower() for character in str(line.get("text") or "") if character.isalnum())


def _normalized_line_box(line: dict[str, object], frame: dict[str, object]) -> tuple[float, float, float, float]:
    width = max(1, int(frame.get("width") or 0))
    height = max(1, int(frame.get("height") or 0))
    return (
        int(line.get("x") or 0) / width,
        int(line.get("y") or 0) / height,
        int(line.get("width") or 0) / width,
        int(line.get("height") or 0) / height,
    )


def _box_iou(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    overlap_width = max(0.0, min(first_x + first_width, second_x + second_width) - max(first_x, second_x))
    overlap_height = max(0.0, min(first_y + first_height, second_y + second_height) - max(first_y, second_y))
    intersection = overlap_width * overlap_height
    union = first_width * first_height + second_width * second_height - intersection
    return intersection / union if union > 0 else 0.0


def _temporal_anchor_lines(frame: dict[str, object]) -> list[dict[str, object]]:
    width = max(1, int(frame.get("width") or 0))
    height = max(1, int(frame.get("height") or 0))
    return [
        line
        for line in list(frame.get("lines") or [])
        if float(line.get("confidence", -1)) >= OCR_ESSENTIAL_TEXT_CONFIDENCE
        and len(_normalized_ocr_text(line)) >= TEMPORAL_TEXT_MIN_CHARACTERS
        and int(line.get("height") or 0) / height >= TEMPORAL_TEXT_MIN_HEIGHT_RATIO
        and int(line.get("width") or 0) / width >= TEMPORAL_TEXT_MIN_WIDTH_RATIO
    ]


def _matching_persistent_lines(
    first_frame: dict[str, object],
    second_frame: dict[str, object],
) -> list[tuple[dict[str, object], dict[str, object], float, float]]:
    candidates: list[tuple[float, dict[str, object], dict[str, object], float, float]] = []
    for first in _temporal_anchor_lines(first_frame):
        first_text = _normalized_ocr_text(first)
        first_box = _normalized_line_box(first, first_frame)
        for second in _temporal_anchor_lines(second_frame):
            second_text = _normalized_ocr_text(second)
            similarity = difflib.SequenceMatcher(None, first_text, second_text).ratio()
            if similarity < TEMPORAL_TEXT_MIN_NEIGHBOR_SIMILARITY:
                continue
            if first_text != second_text and (
                similarity < TEMPORAL_TEXT_MIN_FUZZY_SIMILARITY
                or min(float(first.get("confidence", -1)), float(second.get("confidence", -1)))
                >= TEMPORAL_TEXT_FUZZY_MAX_CONFIDENCE
            ):
                continue
            geometry_iou = _box_iou(first_box, _normalized_line_box(second, second_frame))
            if geometry_iou < TEMPORAL_TEXT_MIN_GEOMETRY_IOU:
                continue
            candidates.append((similarity + geometry_iou, first, second, similarity, geometry_iou))

    matches: list[tuple[dict[str, object], dict[str, object], float, float]] = []
    used_first: set[int] = set()
    used_second: set[int] = set()
    for _score, first, second, similarity, geometry_iou in sorted(candidates, key=lambda item: item[0], reverse=True):
        first_id = id(first)
        second_id = id(second)
        if first_id in used_first or second_id in used_second:
            continue
        used_first.add(first_id)
        used_second.add(second_id)
        matches.append((first, second, similarity, geometry_iou))
    return matches


def _map_line_box_to_frame(
    line: dict[str, object],
    source_frame: dict[str, object],
    target_width: int,
    target_height: int,
) -> tuple[float, float, float, float]:
    source_width = max(1, int(source_frame.get("width") or 0))
    source_height = max(1, int(source_frame.get("height") or 0))
    scale = min(target_width / source_width, target_height / source_height)
    offset_x = (target_width - source_width * scale) / 2
    offset_y = (target_height - source_height * scale) / 2
    return (
        offset_x + int(line.get("x") or 0) * scale,
        offset_y + int(line.get("y") or 0) * scale,
        int(line.get("width") or 0) * scale,
        int(line.get("height") or 0) * scale,
    )


def _temporal_text_roi(
    first_line: dict[str, object],
    first_frame: dict[str, object],
    second_line: dict[str, object],
    second_frame: dict[str, object],
    target_width: int,
    target_height: int,
) -> tuple[int, int, int, int]:
    boxes = [
        _map_line_box_to_frame(first_line, first_frame, target_width, target_height),
        _map_line_box_to_frame(second_line, second_frame, target_width, target_height),
    ]
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[0] + box[2] for box in boxes)
    bottom = max(box[1] + box[3] for box in boxes)
    line_height = max(box[3] for box in boxes)
    horizontal_padding = max(2.0, line_height * 0.35)
    vertical_padding = max(2.0, line_height * 0.45)
    x0 = max(0, math.floor(left - horizontal_padding))
    y0 = max(0, math.floor(top - vertical_padding))
    x1 = min(target_width, math.ceil(right + horizontal_padding))
    y1 = min(target_height, math.ceil(bottom + vertical_padding))
    return x0, y0, x1, y1


def _connected_foreground_mask(mask: list[bool], width: int, height: int) -> tuple[list[bool], list[int]]:
    if not mask or width <= 0 or height <= 0:
        return [False] * len(mask), []
    visited = bytearray(len(mask))
    filtered = [False] * len(mask)
    component_areas: list[int] = []
    minimum_area = max(2, round(len(mask) * 0.0008))
    for start, active in enumerate(mask):
        if not active or visited[start]:
            continue
        visited[start] = 1
        stack = [start]
        component: list[int] = []
        while stack:
            index = stack.pop()
            component.append(index)
            y, x = divmod(index, width)
            for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
                row = neighbor_y * width
                for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = row + neighbor_x
                    if mask[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        stack.append(neighbor)
        if len(component) < minimum_area:
            continue
        component_areas.append(len(component))
        for index in component:
            filtered[index] = True
    return filtered, component_areas


def _text_region_evidence(
    frame: bytes,
    frame_width: int,
    frame_height: int,
    roi: tuple[int, int, int, int],
) -> dict[str, object]:
    x0, y0, x1, y1 = roi
    region_width = max(0, x1 - x0)
    region_height = max(0, y1 - y0)
    if len(frame) != frame_width * frame_height or region_width <= 0 or region_height <= 0:
        return {"mask": [], "contrasts": [], "component_areas": [], "active_pixels": 0}
    values = [
        frame[y * frame_width + x]
        for y in range(y0, y1)
        for x in range(x0, x1)
    ]
    background = dominant_luma(bytes(values))
    contrasts = [abs(value - background) for value in values]
    raw_mask = [contrast >= TEMPORAL_TEXT_FOREGROUND_LUMA for contrast in contrasts]
    mask, component_areas = _connected_foreground_mask(raw_mask, region_width, region_height)
    return {
        "mask": mask,
        "contrasts": contrasts,
        "component_areas": component_areas,
        "active_pixels": sum(component_areas),
    }


def _dilated_mask(mask: list[bool], width: int, height: int) -> list[bool]:
    dilated = [False] * len(mask)
    for index, active in enumerate(mask):
        if not active:
            continue
        y, x = divmod(index, width)
        for neighbor_y in range(max(0, y - 1), min(height, y + 2)):
            row = neighbor_y * width
            for neighbor_x in range(max(0, x - 1), min(width, x + 2)):
                dilated[row + neighbor_x] = True
    return dilated


def _mask_support(source: list[bool], target: list[bool]) -> float:
    source_count = sum(source)
    return sum(1 for source_pixel, target_pixel in zip(source, target) if source_pixel and target_pixel) / source_count if source_count else 0.0


def _global_foreground_pixels(frame: bytes) -> int:
    if not frame:
        return 0
    background = dominant_luma(frame)
    return sum(1 for value in frame if abs(value - background) >= TEMPORAL_TEXT_FOREGROUND_LUMA)


def _ocr_confirms_line_at(
    frames: list[dict[str, object]],
    timestamp: float,
    expected_line: dict[str, object],
    expected_frame: dict[str, object],
    interval: float,
) -> bool:
    if not frames:
        return False
    closest = min(
        frames,
        key=lambda frame: abs(float(frame.get("timestamp_seconds") or 0.0) - timestamp),
    )
    if abs(float(closest.get("timestamp_seconds") or 0.0) - timestamp) > max(0.02, interval * 0.2):
        return False
    expected_text = _normalized_ocr_text(expected_line)
    expected_box = _normalized_line_box(expected_line, expected_frame)
    for line in _temporal_anchor_lines(closest):
        similarity = difflib.SequenceMatcher(None, expected_text, _normalized_ocr_text(line)).ratio()
        if similarity >= TEMPORAL_TEXT_MIN_NEIGHBOR_SIMILARITY and _box_iou(
            expected_box,
            _normalized_line_box(line, closest),
        ) >= TEMPORAL_TEXT_MIN_GEOMETRY_IOU:
            return True
    return False


def analyze_temporal_text_integrity(
    ocr_frames: list[dict[str, object]],
    visual_frames: list[bytes],
    *,
    ocr_interval: float,
    visual_interval: float,
    visual_width: int,
    visual_height: int,
) -> dict[str, object]:
    """Find isolated structural loss inside OCR-confirmed persistent text."""
    available = bool(ocr_frames and visual_frames and visual_interval > 0 and visual_width > 0 and visual_height > 0)
    if not available:
        return {
            "available": False,
            "sampled_frames": len(visual_frames),
            "sample_interval_seconds": visual_interval,
            "matched_persistent_regions": 0,
            "candidate_samples_checked": 0,
            "integrity_loss_count": 0,
            "coherent_transition_suppression_count": 0,
            "findings": [],
        }

    findings: list[dict[str, object]] = []
    inspected: set[tuple[int, int, int, str]] = set()
    matched_regions = 0
    candidate_samples_checked = 0
    coherent_suppressions = 0
    global_foreground_cache: dict[int, int] = {}

    def global_foreground(index: int) -> int:
        if index not in global_foreground_cache:
            global_foreground_cache[index] = _global_foreground_pixels(visual_frames[index])
        return global_foreground_cache[index]

    for gap in (1, 2):
        for first_index in range(0, len(ocr_frames) - gap):
            second_index = first_index + gap
            first_frame = ocr_frames[first_index]
            second_frame = ocr_frames[second_index]
            first_timestamp = float(first_frame.get("timestamp_seconds", first_index * ocr_interval))
            second_timestamp = float(second_frame.get("timestamp_seconds", second_index * ocr_interval))
            if second_timestamp <= first_timestamp or second_timestamp - first_timestamp > ocr_interval * 2.25:
                continue
            visual_first = round(first_timestamp / visual_interval)
            visual_second = round(second_timestamp / visual_interval)
            if visual_first < 0 or visual_second >= len(visual_frames) or visual_second - visual_first < 2:
                continue

            for first_line, second_line, text_similarity, geometry_iou in _matching_persistent_lines(first_frame, second_frame):
                matched_regions += 1
                roi = _temporal_text_roi(
                    first_line,
                    first_frame,
                    second_line,
                    second_frame,
                    visual_width,
                    visual_height,
                )
                region_width = roi[2] - roi[0]
                region_height = roi[3] - roi[1]
                if region_width <= 0 or region_height <= 0:
                    continue
                first_evidence = _text_region_evidence(
                    visual_frames[visual_first], visual_width, visual_height, roi
                )
                second_evidence = _text_region_evidence(
                    visual_frames[visual_second], visual_width, visual_height, roi
                )
                first_mask = list(first_evidence["mask"])
                second_mask = list(second_evidence["mask"])
                first_active = int(first_evidence["active_pixels"])
                second_active = int(second_evidence["active_pixels"])
                expected_pixels = (first_active + second_active) / 2
                if expected_pixels < TEMPORAL_TEXT_MIN_EXPECTED_PIXELS:
                    continue
                area_stability = min(first_active, second_active) / max(first_active, second_active)
                first_dilated = _dilated_mask(first_mask, region_width, region_height)
                second_dilated = _dilated_mask(second_mask, region_width, region_height)
                neighbor_shape_support = min(
                    _mask_support(first_mask, second_dilated),
                    _mask_support(second_mask, first_dilated),
                )
                if area_stability < 0.78 or neighbor_shape_support < TEMPORAL_TEXT_MIN_NEIGHBOR_SHAPE_SUPPORT:
                    continue
                expected_mask = [
                    (first_pixel and second_dilated[index]) or (second_pixel and first_dilated[index])
                    for index, (first_pixel, second_pixel) in enumerate(zip(first_mask, second_mask))
                ]
                expected_count = sum(expected_mask)
                if expected_count < TEMPORAL_TEXT_MIN_EXPECTED_PIXELS:
                    continue

                for visual_index in range(visual_first + 1, visual_second):
                    key = (visual_index, roi[0] // 4, roi[1] // 4, _normalized_ocr_text(first_line))
                    if key in inspected:
                        continue
                    inspected.add(key)
                    candidate_samples_checked += 1
                    current_evidence = _text_region_evidence(
                        visual_frames[visual_index], visual_width, visual_height, roi
                    )
                    current_mask = list(current_evidence["mask"])
                    current_dilated = _dilated_mask(current_mask, region_width, region_height)
                    stroke_coverage = _mask_support(expected_mask, current_dilated)
                    current_active = int(current_evidence["active_pixels"])
                    component_area_ratio = current_active / expected_pixels if expected_pixels else 0.0
                    if (
                        stroke_coverage > TEMPORAL_TEXT_MAX_STROKE_COVERAGE
                        or component_area_ratio > TEMPORAL_TEXT_MAX_COMPONENT_AREA_RATIO
                    ):
                        continue

                    current_contrasts = list(current_evidence["contrasts"])
                    first_contrasts = list(first_evidence["contrasts"])
                    second_contrasts = list(second_evidence["contrasts"])
                    contrast_ratios = []
                    for index, expected in enumerate(expected_mask):
                        if not expected:
                            continue
                        baseline = max(1.0, (first_contrasts[index] + second_contrasts[index]) / 2)
                        contrast_ratios.append(min(1.5, current_contrasts[index] / baseline))
                    median_ratio = percentile(contrast_ratios, 0.5)
                    tolerance = max(0.08, median_ratio * 0.25)
                    coherent_ratio = (
                        sum(1 for ratio in contrast_ratios if abs(ratio - median_ratio) <= tolerance)
                        / len(contrast_ratios)
                        if contrast_ratios
                        else 0.0
                    )
                    neighbor_global = (
                        global_foreground(visual_first) + global_foreground(visual_second)
                    ) / 2
                    global_retention = global_foreground(visual_index) / neighbor_global if neighbor_global else 0.0
                    timestamp = visual_index * visual_interval
                    ocr_confirms = _ocr_confirms_line_at(
                        ocr_frames,
                        timestamp,
                        first_line,
                        first_frame,
                        ocr_interval,
                    )
                    coherent_full_fade = (
                        not ocr_confirms
                        and coherent_ratio >= TEMPORAL_TEXT_COHERENT_FADE_RATIO
                        and global_retention <= component_area_ratio + 0.15
                    )
                    if coherent_full_fade:
                        coherent_suppressions += 1
                        continue

                    findings.append(
                        {
                            "frame_index": visual_index,
                            "timestamp_seconds": round(timestamp, 3),
                            "flags": [TEMPORAL_TEXT_FLAG],
                            "publish_blocking": True,
                            "blocking_flags": [TEMPORAL_TEXT_FLAG],
                            "examples": [str(first_line.get("text") or "")[:100]],
                            "evidence": {
                                "neighbor_timestamps_seconds": [
                                    round(first_timestamp, 3),
                                    round(second_timestamp, 3),
                                ],
                                "neighbor_text_similarity": round(text_similarity, 4),
                                "neighbor_geometry_iou": round(geometry_iou, 4),
                                "neighbor_shape_support": round(neighbor_shape_support, 4),
                                "expected_connected_region_count": round(
                                    (
                                        len(list(first_evidence["component_areas"]))
                                        + len(list(second_evidence["component_areas"]))
                                    )
                                    / 2,
                                    2,
                                ),
                                "observed_connected_region_count": len(list(current_evidence["component_areas"])),
                                "expected_stroke_coverage_ratio": round(stroke_coverage, 4),
                                "connected_region_area_ratio": round(component_area_ratio, 4),
                                "global_foreground_retention_ratio": round(global_retention, 4),
                                "ocr_confirmed_at_bad_sample": ocr_confirms,
                            },
                        }
                    )

    unique_findings: list[dict[str, object]] = []
    finding_keys: set[tuple[float, str]] = set()
    for finding in sorted(findings, key=lambda item: float(item["timestamp_seconds"])):
        finding_key = (float(finding["timestamp_seconds"]), str(finding["examples"][0]))
        if finding_key in finding_keys:
            continue
        finding_keys.add(finding_key)
        unique_findings.append(finding)
    return {
        "available": True,
        "sampled_frames": len(visual_frames),
        "sample_interval_seconds": visual_interval,
        "sampling_strategy": "ocr_anchored_dense_connected_region_sampling",
        "frame_budget": TEMPORAL_TEXT_MAX_FRAMES,
        "matched_persistent_regions": matched_regions,
        "candidate_samples_checked": candidate_samples_checked,
        "integrity_loss_count": len(unique_findings),
        "coherent_transition_suppression_count": coherent_suppressions,
        "thresholds": {
            "minimum_neighbor_text_similarity": TEMPORAL_TEXT_MIN_NEIGHBOR_SIMILARITY,
            "minimum_fuzzy_neighbor_text_similarity": TEMPORAL_TEXT_MIN_FUZZY_SIMILARITY,
            "fuzzy_neighbor_max_confidence": TEMPORAL_TEXT_FUZZY_MAX_CONFIDENCE,
            "minimum_neighbor_geometry_iou": TEMPORAL_TEXT_MIN_GEOMETRY_IOU,
            "minimum_neighbor_shape_support": TEMPORAL_TEXT_MIN_NEIGHBOR_SHAPE_SUPPORT,
            "maximum_bad_sample_stroke_coverage": TEMPORAL_TEXT_MAX_STROKE_COVERAGE,
            "maximum_bad_sample_connected_region_area_ratio": TEMPORAL_TEXT_MAX_COMPONENT_AREA_RATIO,
            "coherent_fade_ratio": TEMPORAL_TEXT_COHERENT_FADE_RATIO,
        },
        "findings": unique_findings,
    }


def analyze_ocr_frames(
    frames: list[dict[str, object]],
    *,
    interval: float,
    temporal_frames: list[bytes] | None = None,
    temporal_interval: float = 0.0,
    temporal_width: int = 0,
    temporal_height: int = 0,
    runtime_metadata: object = None,
) -> dict[str, object]:
    line_count = 0
    essential_line_count = 0
    word_count = 0
    small_line_count = 0
    clipped_line_count = 0
    overlap_pair_count = 0
    low_confidence_count = 0
    confidence_token_count = 0
    run_together_count = 0
    frames_with_text = 0
    frames_with_essential_text = 0
    frames_with_small_text = 0
    frames_with_small_essential_text = 0
    frames_with_clipped_text = 0
    frames_with_overlap = 0
    frames_with_run_together = 0
    publish_blocking_frames = 0
    line_height_ratios: list[float] = []
    small_essential_states: list[bool] = []
    small_essential_timestamps_seconds: list[float] = []
    findings: list[dict[str, object]] = []
    blocking_findings: list[dict[str, object]] = []

    for frame_index, frame in enumerate(frames):
        width = int(frame.get("width") or 0)
        height = int(frame.get("height") or 0)
        lines = list(frame.get("lines") or [])
        words = list(frame.get("words") or [])
        if width <= 0 or height <= 0:
            continue
        eligible_lines = [
            line
            for line in lines
            if float(line.get("confidence", -1)) >= OCR_MIN_LAYOUT_CONFIDENCE
            and (sum(character.isalnum() for character in str(line.get("text") or "")) >= 2 or int(line.get("width") or 0) >= 20)
        ]
        if eligible_lines:
            frames_with_text += 1
        line_count += len(eligible_lines)
        word_count += len(words)
        essential_indexes = {
            line_index for line_index, line in enumerate(eligible_lines) if is_essential_text_line(line)
        }
        frames_with_essential_text += bool(essential_indexes)
        essential_line_count += len(essential_indexes)

        small_lines = []
        small_essential_lines = []
        clipped_lines = []
        for line_index, line in enumerate(eligible_lines):
            height_ratio = int(line["height"]) / height
            line_height_ratios.append(height_ratio)
            if height_ratio < OCR_SMALL_LINE_HEIGHT_RATIO:
                small_lines.append(line)
                if line_index in essential_indexes:
                    small_essential_lines.append(line)
            if line_index in essential_indexes and text_line_outside_safe_area(line, width, height):
                clipped_lines.append(line)
        small_line_count += len(small_lines)
        clipped_line_count += len(clipped_lines)
        frames_with_small_text += bool(small_lines)
        frames_with_small_essential_text += bool(small_essential_lines)
        small_essential_states.append(bool(small_essential_lines))
        if small_essential_lines:
            small_essential_timestamps_seconds.append(
                float(frame.get("timestamp_seconds", frame_index * interval))
            )
        frames_with_clipped_text += bool(clipped_lines)

        collisions = [
            collision
            for collision in text_line_overlap_pairs(eligible_lines)
            if collision[0] in essential_indexes and collision[1] in essential_indexes
        ]
        overlap_pair_count += len(collisions)
        frames_with_overlap += bool(collisions)

        low_confidence = []
        run_together = []
        for word in words:
            text = str(word.get("text") or "")
            alphabetic = "".join(character for character in text if character.isalpha())
            confidence = float(word.get("confidence", -1))
            if len(alphabetic) >= 3 and confidence >= 0:
                confidence_token_count += 1
                if confidence < OCR_LOW_CONFIDENCE:
                    low_confidence.append(word)
            if suspicious_run_together_word(word):
                run_together.append(word)
        low_confidence_count += len(low_confidence)
        run_together_count += len(run_together)
        frames_with_run_together += bool(run_together)

        frame_flags: list[str] = []
        if small_lines:
            frame_flags.append("small_text")
        if clipped_lines:
            frame_flags.append("unsafe_edge_text")
        if collisions:
            frame_flags.append("text_overlap")
        if low_confidence:
            frame_flags.append("low_confidence_text")
        if run_together:
            frame_flags.append("run_together_text")
        blocking_flags: list[str] = []
        if clipped_lines:
            blocking_flags.append("rendered_text_outside_safe_area")
        if collisions:
            blocking_flags.append("rendered_text_overlap")
        publish_blocking_frames += bool(blocking_flags)
        if frame_flags:
            examples = [
                str(line.get("text") or "")[:100]
                for line in (clipped_lines or small_essential_lines or small_lines)[:3]
            ]
            for first_index, second_index, _kind in collisions[:3]:
                examples.extend(
                    [
                        str(eligible_lines[first_index].get("text") or "")[:100],
                        str(eligible_lines[second_index].get("text") or "")[:100],
                    ]
                )
            examples.extend(str(word.get("text") or "")[:100] for word in (run_together or low_confidence)[:3])
            timestamp = float(frame.get("timestamp_seconds", frame_index * interval))
            finding = {
                "frame_index": frame_index,
                "timestamp_seconds": round(timestamp, 3),
                "flags": frame_flags,
                "publish_blocking": bool(blocking_flags),
                "blocking_flags": blocking_flags,
                "examples": list(dict.fromkeys(example for example in examples if example)),
            }
            if len(findings) < 24 or blocking_flags:
                findings.append(finding)
            if blocking_flags:
                blocking_findings.append(finding)

    temporal_metrics = analyze_temporal_text_integrity(
        frames,
        temporal_frames or [],
        ocr_interval=interval,
        visual_interval=temporal_interval,
        visual_width=temporal_width,
        visual_height=temporal_height,
    )
    temporal_findings = list(temporal_metrics.get("findings") or [])
    publish_blocking_frames += len(temporal_findings)
    findings.extend(temporal_findings)
    blocking_findings.extend(temporal_findings)
    visual_small_text_metrics = analyze_visual_small_text_fallback(
        temporal_frames or [],
        interval=temporal_interval,
        width=temporal_width,
        height=temporal_height,
        ocr_frames=frames,
        ocr_interval=interval,
        runtime_metadata=runtime_metadata,
    )
    visual_small_text_findings = list(visual_small_text_metrics.get("findings") or [])
    visual_small_text_blocking_findings = list(
        visual_small_text_metrics.get("blocking_findings") or []
    )
    publish_blocking_frames += len(visual_small_text_blocking_findings)
    findings.extend(visual_small_text_findings)
    blocking_findings.extend(visual_small_text_blocking_findings)

    text_frame_denominator = max(1, frames_with_text)
    essential_text_frame_denominator = max(1, frames_with_essential_text)
    small_line_ratio = small_line_count / line_count if line_count else 0.0
    clipped_line_ratio = clipped_line_count / line_count if line_count else 0.0
    low_confidence_ratio = low_confidence_count / confidence_token_count if confidence_token_count else 0.0
    small_frame_ratio = frames_with_small_text / text_frame_denominator
    small_essential_frame_ratio = frames_with_small_essential_text / essential_text_frame_denominator
    max_small_essential_duration = longest_sampled_run_seconds(small_essential_states, interval=interval)
    clipped_frame_ratio = frames_with_clipped_text / text_frame_denominator
    overlap_frame_ratio = frames_with_overlap / text_frame_denominator
    run_together_frame_ratio = frames_with_run_together / text_frame_denominator

    review_flags: list[str] = []
    serious_review_flags: list[str] = []
    if (
        small_essential_frame_ratio >= OCR_SMALL_TEXT_FRAME_RATIO_LIMIT
        and max_small_essential_duration >= OCR_SMALL_TEXT_MIN_AFFECTED_SECONDS
    ):
        review_flags.append(VISUAL_SMALL_TEXT_FLAG)
        serious_review_flags.append(VISUAL_SMALL_TEXT_FLAG)
    if visual_small_text_findings:
        review_flags.append(VISUAL_SMALL_TEXT_FLAG)
    if visual_small_text_blocking_findings:
        serious_review_flags.append(VISUAL_SMALL_TEXT_FLAG)
    if clipped_line_count:
        review_flags.append("rendered_text_outside_safe_area")
        serious_review_flags.append("rendered_text_outside_safe_area")
    if overlap_pair_count:
        review_flags.append("rendered_text_overlap")
        serious_review_flags.append("rendered_text_overlap")
    if low_confidence_count >= 2 and low_confidence_ratio >= OCR_LOW_CONFIDENCE_TOKEN_RATIO_LIMIT:
        review_flags.append("low_confidence_rendered_text")
    if run_together_count and run_together_frame_ratio >= OCR_RUN_TOGETHER_FRAME_RATIO_LIMIT:
        review_flags.append("suspected_run_together_text")
        serious_review_flags.append("suspected_run_together_text")
    if temporal_findings:
        review_flags.append(TEMPORAL_TEXT_FLAG)
        serious_review_flags.append(TEMPORAL_TEXT_FLAG)

    sample_timestamps = [
        float(frame.get("timestamp_seconds", frame_index * interval))
        for frame_index, frame in enumerate(frames)
    ]
    sample_gaps = [after - before for before, after in zip(sample_timestamps, sample_timestamps[1:])]
    return {
        "available": True,
        "sampled_frames": len(frames),
        "sample_interval_seconds": interval,
        "first_sample_timestamp_seconds": round(sample_timestamps[0], 3) if sample_timestamps else None,
        "last_sample_timestamp_seconds": round(sample_timestamps[-1], 3) if sample_timestamps else None,
        "max_sample_gap_seconds": round(max(sample_gaps), 3) if sample_gaps else 0.0,
        "sampling_strategy": "dense_uniform_transition_sampling",
        "frame_budget": OCR_MAX_FRAMES,
        "frames_with_text": frames_with_text,
        "frames_with_essential_text": frames_with_essential_text,
        "detected_lines": line_count,
        "high_confidence_essential_lines": essential_line_count,
        "detected_words": word_count,
        "median_line_height_ratio": round(percentile(line_height_ratios, 0.5), 4),
        "p10_line_height_ratio": round(percentile(line_height_ratios, 0.1), 4),
        "small_line_ratio": round(small_line_ratio, 4),
        "frames_with_small_text_ratio": round(small_frame_ratio, 4),
        "frames_with_small_essential_text": frames_with_small_essential_text,
        "frames_with_small_essential_text_ratio": round(small_essential_frame_ratio, 4),
        "max_small_essential_text_duration_seconds": round(max_small_essential_duration, 3),
        "small_essential_timestamps_seconds": [
            round(timestamp, 3) for timestamp in small_essential_timestamps_seconds
        ],
        "safe_area_line_violation_ratio": round(clipped_line_ratio, 4),
        "essential_safe_area_violation_count": clipped_line_count,
        "frames_with_safe_area_violations": frames_with_clipped_text,
        "frames_with_safe_area_violations_ratio": round(clipped_frame_ratio, 4),
        "overlap_pair_count": overlap_pair_count,
        "frames_with_text_overlap": frames_with_overlap,
        "frames_with_text_overlap_ratio": round(overlap_frame_ratio, 4),
        "low_confidence_token_ratio": round(low_confidence_ratio, 4),
        "suspected_run_together_token_count": run_together_count,
        "frames_with_run_together_text_ratio": round(run_together_frame_ratio, 4),
        "publish_blocking_frame_count": publish_blocking_frames,
        "temporal_text_integrity": temporal_metrics,
        "visual_small_text_fallback": visual_small_text_metrics,
        "thresholds": {
            "minimum_layout_confidence": OCR_MIN_LAYOUT_CONFIDENCE,
            "essential_text_confidence": OCR_ESSENTIAL_TEXT_CONFIDENCE,
            "low_confidence": OCR_LOW_CONFIDENCE,
            "horizontal_safe_inset_ratio": OCR_SAFE_HORIZONTAL_INSET_RATIO,
            "vertical_safe_inset_ratio": OCR_SAFE_VERTICAL_INSET_RATIO,
            "small_line_height_ratio": OCR_SMALL_LINE_HEIGHT_RATIO,
            "small_line_ratio_limit": OCR_SMALL_LINE_RATIO_LIMIT,
            "small_text_frame_ratio_limit": OCR_SMALL_TEXT_FRAME_RATIO_LIMIT,
            "small_text_min_affected_seconds": OCR_SMALL_TEXT_MIN_AFFECTED_SECONDS,
            "similar_line_height_ratio": OCR_SIMILAR_LINE_HEIGHT_RATIO,
            "line_box_vertical_inset_ratio": OCR_LINE_BOX_VERTICAL_INSET_RATIO,
            "inset_line_overlap_ratio": OCR_INSET_LINE_OVERLAP_RATIO,
            "publish_blocking_layout_finding_count": 1,
            "run_together_frame_ratio_limit": OCR_RUN_TOGETHER_FRAME_RATIO_LIMIT,
        },
        "findings": findings,
        "blocking_findings": blocking_findings,
        "review_flags": list(dict.fromkeys(review_flags)),
        "serious_review_flags": list(dict.fromkeys(serious_review_flags)),
    }


def bounded_ocr_interval(duration: float, requested_interval: float) -> float:
    if requested_interval <= 0:
        raise ValueError("OCR sample interval must be greater than zero.")
    requested_interval = min(requested_interval, OCR_SAMPLE_INTERVAL_SECONDS)
    if duration <= 0:
        return requested_interval
    return max(requested_interval, duration / OCR_MAX_FRAMES)


def bounded_temporal_text_interval(duration: float, ocr_interval: float) -> float:
    if ocr_interval <= 0:
        raise ValueError("Temporal text sample interval must be greater than zero.")
    requested_interval = min(TEMPORAL_TEXT_SAMPLE_INTERVAL_SECONDS, ocr_interval / 2)
    if duration <= 0:
        return requested_interval
    return max(requested_interval, duration / TEMPORAL_TEXT_MAX_FRAMES)


def bounded_temporal_visual_interval(duration: float) -> float:
    if duration <= 0:
        return TEMPORAL_VISUAL_SAMPLE_INTERVAL_SECONDS
    return max(TEMPORAL_VISUAL_SAMPLE_INTERVAL_SECONDS, duration / TEMPORAL_VISUAL_MAX_FRAMES)


def sample_ocr_frames(
    ffmpeg: str,
    tesseract: str,
    video: Path,
    *,
    interval: float,
    duration: float | None = None,
) -> tuple[list[dict[str, object]], list[str], float]:
    frames: list[dict[str, object]] = []
    errors: list[str] = []
    if duration is None:
        duration = probe_video_duration(video)
    effective_interval = bounded_ocr_interval(duration, interval)
    with tempfile.TemporaryDirectory(prefix="course-frame-ocr-") as temporary:
        pattern = Path(temporary) / "frame_%05d.png"
        extraction = subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-i",
                str(video),
                "-vf",
                f"fps=1/{effective_interval}:eof_action=pass",
                "-frames:v",
                str(OCR_MAX_FRAMES),
                str(pattern),
            ],
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        if extraction.returncode != 0:
            return [], [f"ffmpeg extraction failed: {extraction.stderr[:240]}"], effective_interval
        for sample_index, image_path in enumerate(sorted(Path(temporary).glob("frame_*.png"))):
            try:
                result = subprocess.run(
                    [tesseract, str(image_path), "stdout", "--psm", "11", "tsv"],
                    text=True,
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                errors.append(f"OCR timed out for {image_path.name}")
                continue
            if result.returncode != 0:
                errors.append(f"OCR failed for {image_path.name}: {result.stderr[:160]}")
                continue
            parsed = parse_tesseract_tsv(result.stdout)
            if parsed:
                parsed["sample_index"] = sample_index
                parsed["timestamp_seconds"] = round(sample_index * effective_interval, 6)
                frames.append(parsed)
    return frames, errors, effective_interval


def motion_window_coverage(motion_states: list[bool], *, interval: float, window_seconds: float) -> float:
    """Return motion coverage across overlapping windows.

    Advancing by one transition prevents a burst on a fixed bucket boundary
    from receiving credit for two otherwise motion-free time spans.
    """
    if not motion_states:
        return 0.0
    if interval <= 0 or window_seconds <= 0:
        raise ValueError("Motion window and interval must be greater than zero.")
    transitions_per_window = max(1, math.ceil(window_seconds / interval))
    if len(motion_states) <= transitions_per_window:
        windows = [motion_states]
    else:
        windows = [
            motion_states[start : start + transitions_per_window]
            for start in range(len(motion_states) - transitions_per_window + 1)
        ]
    return sum(1 for window in windows if any(window)) / len(windows)


def motion_free_durations(
    motion_states: list[bool],
    *,
    interval: float,
    duration: float,
) -> tuple[float, float]:
    """Return the maximum and terminal spans without explanatory motion."""
    if interval <= 0:
        raise ValueError("Motion interval must be greater than zero.")
    observed_duration = max(0.0, len(motion_states) * interval)
    timeline_duration = max(observed_duration, duration)
    motion_indexes = [index for index, state in enumerate(motion_states) if state]
    if not motion_indexes:
        return timeline_duration, timeline_duration

    maximum_gap = motion_indexes[0] * interval
    previous_motion = motion_indexes[0]
    for motion_index in motion_indexes[1:]:
        maximum_gap = max(maximum_gap, (motion_index - previous_motion - 1) * interval)
        previous_motion = motion_index
    terminal = max(0.0, timeline_duration - (motion_indexes[-1] + 1) * interval)
    return max(maximum_gap, terminal), terminal


def aggregate_transition_states(
    states: list[bool],
    *,
    source_interval: float,
    target_interval: float,
    target_count: int,
) -> list[bool]:
    """Collapse fine transition evidence into coarser analysis intervals."""
    if target_count <= 0:
        return []
    aggregated = []
    for target_index in range(target_count):
        start_seconds = target_index * target_interval
        end_seconds = (target_index + 1) * target_interval
        start_index = max(0, int(math.floor(start_seconds / source_interval + 1e-9)))
        end_index = min(len(states), int(math.ceil(end_seconds / source_interval - 1e-9)))
        aggregated.append(any(states[start_index:end_index]))
    return aggregated


def runtime_proof_roles_at(
    runtime_metadata: object,
    timestamp: float,
) -> dict[str, object] | None:
    """Return the latest stable-hold role mask at or before a sampled frame."""
    if not isinstance(runtime_metadata, dict):
        return None
    holds = runtime_metadata.get("proof_surface_holds")
    if not isinstance(holds, list):
        return None
    eligible = [
        hold for hold in holds
        if isinstance(hold, dict)
        and float(hold.get("renderer_seconds") or 0.0) <= float(timestamp) + 1e-6
    ]
    if not eligible:
        return None
    surfaces = eligible[-1].get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return None
    surface = surfaces[0]
    roles = surface.get("roles") if isinstance(surface, dict) else None
    role_masks = surface.get("role_masks") if isinstance(surface, dict) else None
    if isinstance(role_masks, dict):
        role_rows = roles if isinstance(roles, dict) else {}
        return {
            str(name): {
                **(role_rows.get(name, {}) if isinstance(role_rows.get(name), dict) else {}),
                **(mask if isinstance(mask, dict) else {}),
            }
            for name, mask in role_masks.items()
        }
    return roles if isinstance(roles, dict) else None


def metrics_for(
    ffmpeg: str,
    video: Path,
    *,
    interval: float,
    tesseract: str | None = None,
    duration: float | None = None,
    runtime_metadata: object = None,
) -> dict[str, object]:
    if interval <= 0:
        raise ValueError("Frame-audit interval must be greater than zero.")
    if duration is None:
        duration = probe_video_duration(video)
    width, height = 180, 320
    analysis_interval = min(float(interval), ANALYSIS_INTERVAL_SECONDS)
    frames = sample_gray_frames(ffmpeg, video, interval=analysis_interval, width=width, height=height)
    motion_analysis_interval = min(analysis_interval, MOTION_ANALYSIS_INTERVAL_SECONDS)
    motion_frames = (
        frames
        if motion_analysis_interval == analysis_interval
        else sample_gray_frames(
            ffmpeg,
            video,
            interval=motion_analysis_interval,
            width=width,
            height=height,
        )
    )
    densities = [edge_density(frame, width, height) for frame in frames]
    title_band = [band_density(frame, width, height, 0.00, 0.16) for frame in frames]
    middle_band = [band_density(frame, width, height, 0.26, 0.74) for frame in frames]
    lower_band = [band_density(frame, width, height, 0.74, 1.00) for frame in frames]
    usage = [frame_usage(frame, width, height, density) for frame, density in zip(frames, densities)]
    visual_lane_profiles = [visual_lane_profile(frame, width, height) for frame in frames]
    portrait_profiles = [
        portrait_proof_surface_profile(
            frame,
            width,
            height,
            runtime_roles=runtime_proof_roles_at(runtime_metadata, index * analysis_interval),
        )
        for index, frame in enumerate(frames)
    ]
    changes = [frame_change(previous, current) for previous, current in zip(frames, frames[1:])]
    mean_deltas = [change[0] for change in changes]
    changed_ratios = [change[1] for change in changes]
    static_candidate_states = [
        mean_delta <= STATIC_MAX_MAD and changed_ratio <= STATIC_MAX_CHANGED_RATIO
        for mean_delta, changed_ratio in changes
    ]
    low_change_candidate_states = [
        mean_delta <= LOW_CHANGE_MAX_MAD and changed_ratio <= LOW_CHANGE_MAX_CHANGED_RATIO
        for mean_delta, changed_ratio in changes
    ]
    motion_changes = [
        frame_change(previous, current)
        for previous, current in zip(motion_frames, motion_frames[1:])
    ]
    broad_visual_change_states = [
        not (
            mean_delta <= LOW_CHANGE_MAX_MAD
            and changed_ratio <= LOW_CHANGE_MAX_CHANGED_RATIO
        )
        for mean_delta, changed_ratio in motion_changes
    ]
    motion_profiles = [
        transition_motion_evidence(previous, current, width, height)
        for previous, current in zip(motion_frames, motion_frames[1:])
    ]
    visual_lane_motion_profiles = [
        visual_lane_motion_evidence(previous, current, width, height)
        for previous, current in zip(motion_frames, motion_frames[1:])
    ]
    spatial_candidate_states = [
        bool(profile["active"])
        and float(profile["local_bidirectional_ratio"]) >= MOTION_MIN_LOCAL_BIDIRECTIONAL_RATIO
        for profile in motion_profiles
    ]
    spatial_motion_states = sustained_true_states(
        spatial_candidate_states,
        MOTION_MIN_SPATIAL_RUN_TRANSITIONS,
    )
    draw_candidate_states = [
        float(profile["support_extension_ratio"]) >= MOTION_MIN_SUPPORT_EXTENSION_RATIO
        for profile in motion_profiles
    ]
    draw_motion_states = sustained_true_states(draw_candidate_states, MOTION_MIN_DRAW_RUN_TRANSITIONS)
    motion_states = [
        spatial or drawn
        for spatial, drawn in zip(spatial_motion_states, draw_motion_states)
    ]
    visual_lane_spatial_states = sustained_true_states(
        [
            bool(profile["active"])
            and (
                float(profile["local_bidirectional_ratio"]) >= MOTION_MIN_LOCAL_BIDIRECTIONAL_RATIO
                or bool(profile["localized_motion_distribution"])
            )
            for profile in visual_lane_motion_profiles
        ],
        MOTION_MIN_SPATIAL_RUN_TRANSITIONS,
    )
    visual_lane_draw_states = sustained_true_states(
        [
            float(profile["support_extension_ratio"]) >= MOTION_MIN_SUPPORT_EXTENSION_RATIO
            for profile in visual_lane_motion_profiles
        ],
        MOTION_MIN_DRAW_RUN_TRANSITIONS,
    )
    visual_lane_motion_states = [
        spatial or drawn
        for spatial, drawn in zip(visual_lane_spatial_states, visual_lane_draw_states)
    ]
    motion_at_analysis_interval = aggregate_transition_states(
        motion_states,
        source_interval=motion_analysis_interval,
        target_interval=analysis_interval,
        target_count=len(static_candidate_states),
    )
    visual_lane_motion_at_analysis_interval = aggregate_transition_states(
        visual_lane_motion_states,
        source_interval=motion_analysis_interval,
        target_interval=analysis_interval,
        target_count=max(0, len(frames) - 1),
    )
    visual_lane_temporal_support_states = [False] * len(frames)
    for transition_index, state in enumerate(visual_lane_motion_at_analysis_interval):
        if state:
            visual_lane_temporal_support_states[transition_index] = True
            visual_lane_temporal_support_states[transition_index + 1] = True
    static_states = [
        candidate and not motion
        for candidate, motion in zip(static_candidate_states, motion_at_analysis_interval)
    ]
    low_change_states = [
        candidate and not motion
        for candidate, motion in zip(low_change_candidate_states, motion_at_analysis_interval)
    ]
    opacity_states = [
        bool(profile["active"]) and not motion
        for profile, motion in zip(motion_profiles, motion_states)
    ]
    blank_states = [bool(item["blank"]) for item in usage]
    underused_states = [bool(item["underused"]) for item in usage]
    sparse_visual_lane_states = [
        not bool(item["blank"])
        and bool(profile["sparse"])
        and not temporal_support
        for item, profile, temporal_support in zip(
            usage,
            visual_lane_profiles,
            visual_lane_temporal_support_states,
        )
    ]
    outer_portrait_underfill_states = [
        not bool(item["blank"]) and bool(profile["outer_underfill"])
        for item, profile in zip(usage, portrait_profiles)
    ]
    outer_portrait_overfill_states = [
        not bool(item["blank"]) and bool(profile["outer_overfill"])
        for item, profile in zip(usage, portrait_profiles)
    ]
    evidence_intrusion_states = [
        not bool(item["blank"]) and bool(profile["evidence_intrusion"])
        for item, profile in zip(usage, portrait_profiles)
    ]
    empty_vertical_bands = [interior_empty_vertical_band_ratio(frame, width, height) for frame in frames]
    extreme_layout_states = [
        not bool(item["blank"])
        and empty_band >= EXTREME_EMPTY_VERTICAL_BAND_RATIO
        and float(item["active_tile_ratio"]) <= 0.22
        for item, empty_band in zip(usage, empty_vertical_bands)
    ]

    max_edge = max(densities) if densities else 0.0
    max_middle = max(middle_band) if middle_band else 0.0
    static_ratio = sum(static_states) / len(static_states) if static_states else 0.0
    low_change_ratio = sum(low_change_states) / len(low_change_states) if low_change_states else 0.0
    broad_visual_change_ratio = (
        sum(broad_visual_change_states) / len(broad_visual_change_states)
        if broad_visual_change_states
        else 0.0
    )
    motion_ratio = sum(motion_states) / len(motion_states) if motion_states else 0.0
    spatial_motion_ratio = (
        sum(spatial_motion_states) / len(spatial_motion_states)
        if spatial_motion_states
        else 0.0
    )
    progressive_draw_ratio = (
        sum(draw_motion_states) / len(draw_motion_states)
        if draw_motion_states
        else 0.0
    )
    opacity_ratio = sum(opacity_states) / len(opacity_states) if opacity_states else 0.0
    motion_windows = motion_window_coverage(
        motion_states,
        interval=motion_analysis_interval,
        window_seconds=MOTION_WINDOW_SECONDS,
    )
    max_motion_free_gap, terminal_static_duration = motion_free_durations(
        motion_states,
        interval=motion_analysis_interval,
        duration=float(duration or 0.0),
    )
    blank_ratio = sum(blank_states) / len(blank_states) if blank_states else 0.0
    underused_ratio = sum(underused_states) / len(underused_states) if underused_states else 0.0
    max_static_hold = longest_run(static_states) * analysis_interval
    max_low_change_hold = longest_run(low_change_states) * analysis_interval
    max_blank_hold = longest_run(blank_states) * analysis_interval
    max_underused_hold = longest_run(underused_states) * analysis_interval
    sparse_visual_lane_ratio = (
        sum(sparse_visual_lane_states) / len(sparse_visual_lane_states)
        if sparse_visual_lane_states else 0.0
    )
    visual_lane_structural_ratio = (
        sum(bool(profile["structural_evidence"]) for profile in visual_lane_profiles)
        / len(visual_lane_profiles)
        if visual_lane_profiles else 0.0
    )
    visual_lane_temporal_support_ratio = (
        sum(visual_lane_temporal_support_states) / len(visual_lane_temporal_support_states)
        if visual_lane_temporal_support_states else 0.0
    )
    meaningful_visual_lane_ratio = (
        sum(
            bool(profile["meaningful_diagram"]) or temporal_support
            for profile, temporal_support in zip(
                visual_lane_profiles,
                visual_lane_temporal_support_states,
            )
        )
        / len(visual_lane_profiles)
        if visual_lane_profiles else 0.0
    )
    max_sparse_visual_lane_hold = longest_run(sparse_visual_lane_states) * analysis_interval
    outer_portrait_underfill_ratio = (
        sum(outer_portrait_underfill_states) / len(outer_portrait_underfill_states)
        if outer_portrait_underfill_states else 0.0
    )
    evidence_intrusion_ratio = (
        sum(evidence_intrusion_states) / len(evidence_intrusion_states)
        if evidence_intrusion_states else 0.0
    )
    max_outer_portrait_underfill_hold = longest_run(outer_portrait_underfill_states) * analysis_interval
    outer_portrait_overfill_ratio = (
        sum(outer_portrait_overfill_states) / len(outer_portrait_overfill_states)
        if outer_portrait_overfill_states else 0.0
    )
    max_outer_portrait_overfill_hold = longest_run(outer_portrait_overfill_states) * analysis_interval
    max_evidence_intrusion_hold = longest_run(evidence_intrusion_states) * analysis_interval
    extreme_layout_ratio = sum(extreme_layout_states) / len(extreme_layout_states) if extreme_layout_states else 0.0
    max_extreme_layout_hold = longest_run(extreme_layout_states) * analysis_interval

    review_flags: list[str] = []
    if max_edge > 0.19:
        review_flags.append("high_edge_density")
    if max_middle > 0.38:
        review_flags.append("crowded_middle_band")
    if title_band and max(title_band) > 0.35:
        review_flags.append("crowded_title_band")
    if lower_band and max(lower_band) > 0.35:
        review_flags.append("crowded_lower_band")
    if max_static_hold >= PROLONGED_STATIC_SECONDS:
        review_flags.append("prolonged_static_holds")
    if terminal_static_duration > TERMINAL_STATIC_SECONDS:
        review_flags.append("terminal_static_hold")
    if max_motion_free_gap >= MAX_MOTION_FREE_GAP_SECONDS:
        review_flags.append("long_motion_free_gap")
    if max_low_change_hold >= PROLONGED_LOW_CHANGE_SECONDS:
        review_flags.append("prolonged_low_change_run")
    low_change_is_unmitigated = (
        not motion_changes
        or motion_ratio < MIN_MOTION_RATIO
        or motion_windows < MIN_MOTION_WINDOW_COVERAGE
        or max_low_change_hold >= PROLONGED_STATIC_SECONDS
    )
    if low_change_ratio >= LOW_CHANGE_RATIO_LIMIT and low_change_is_unmitigated:
        review_flags.append("low_visual_change")
    if blank_ratio >= BLANK_FRAME_RATIO_LIMIT or max_blank_hold >= BLANK_HOLD_SECONDS:
        review_flags.append("blank_frames")
    if underused_ratio >= UNDERUSED_FRAME_RATIO_LIMIT or max_underused_hold >= UNDERUSED_HOLD_SECONDS:
        review_flags.append("underused_frames")
    if motion_changes and (motion_ratio < MIN_MOTION_RATIO or motion_windows < MIN_MOTION_WINDOW_COVERAGE):
        review_flags.append("insufficient_motion_coverage")
    if extreme_layout_ratio >= EXTREME_LAYOUT_FRAME_RATIO_LIMIT or max_extreme_layout_hold >= EXTREME_LAYOUT_HOLD_SECONDS:
        review_flags.append("extreme_layout_imbalance")
    if (
        sparse_visual_lane_ratio >= VISUAL_LANE_MAX_SPARSE_FRAME_RATIO
        or max_sparse_visual_lane_hold >= VISUAL_LANE_MAX_SPARSE_HOLD_SECONDS
    ):
        review_flags.append("underfilled_visual_lane")
    if (
        outer_portrait_underfill_ratio >= PORTRAIT_LAYOUT_MAX_FLAGGED_FRAME_RATIO
        or max_outer_portrait_underfill_hold >= PORTRAIT_LAYOUT_MAX_FLAGGED_HOLD_SECONDS
    ):
        review_flags.append("outer_portrait_underfill")
    if (
        outer_portrait_overfill_ratio >= PORTRAIT_LAYOUT_MAX_FLAGGED_FRAME_RATIO
        or max_outer_portrait_overfill_hold >= PORTRAIT_LAYOUT_MAX_FLAGGED_HOLD_SECONDS
    ):
        review_flags.append("outer_portrait_overfill")
    if (
        evidence_intrusion_ratio >= PORTRAIT_LAYOUT_MAX_FLAGGED_FRAME_RATIO
        or max_evidence_intrusion_hold >= PORTRAIT_LAYOUT_MAX_FLAGGED_HOLD_SECONDS
    ):
        review_flags.append("evidence_lane_intrusion")

    serious_review_flags = [flag for flag in review_flags if flag in SERIOUS_MOTION_LAYOUT_FLAGS]
    runtime_overfill_confirmed = any(
        overfill and bool(profile.get("runtime_role_masks_used"))
        for overfill, profile in zip(outer_portrait_overfill_states, portrait_profiles)
    )
    if "outer_portrait_overfill" in serious_review_flags and not runtime_overfill_confirmed:
        serious_review_flags.remove("outer_portrait_overfill")
    temporal_visual_interval = bounded_temporal_visual_interval(duration)
    temporal_visual_frames = sample_gray_frames(
        ffmpeg,
        video,
        interval=temporal_visual_interval,
        width=TEMPORAL_VISUAL_FRAME_WIDTH,
        height=TEMPORAL_VISUAL_FRAME_HEIGHT,
    )[:TEMPORAL_VISUAL_MAX_FRAMES]
    temporal_visual_metrics = analyze_temporal_visual_integrity(
        temporal_visual_frames,
        interval=temporal_visual_interval,
        width=TEMPORAL_VISUAL_FRAME_WIDTH,
        height=TEMPORAL_VISUAL_FRAME_HEIGHT,
    )
    if temporal_visual_metrics.get("findings"):
        review_flags.append(TEMPORAL_VISUAL_FLAG)
        serious_review_flags.append(TEMPORAL_VISUAL_FLAG)

    ocr_interval = min(float(interval), OCR_SAMPLE_INTERVAL_SECONDS)
    if tesseract:
        ocr_frames, ocr_errors, effective_ocr_interval = sample_ocr_frames(
            ffmpeg,
            tesseract,
            video,
            interval=ocr_interval,
            duration=duration,
        )
        if ocr_frames:
            temporal_interval = bounded_temporal_text_interval(duration, effective_ocr_interval)
            temporal_frames = sample_gray_frames(
                ffmpeg,
                video,
                interval=temporal_interval,
                width=TEMPORAL_TEXT_FRAME_WIDTH,
                height=TEMPORAL_TEXT_FRAME_HEIGHT,
            )[:TEMPORAL_TEXT_MAX_FRAMES]
            ocr_metrics = analyze_ocr_frames(
                ocr_frames,
                interval=effective_ocr_interval,
                temporal_frames=temporal_frames,
                temporal_interval=temporal_interval,
                temporal_width=TEMPORAL_TEXT_FRAME_WIDTH,
                temporal_height=TEMPORAL_TEXT_FRAME_HEIGHT,
                runtime_metadata=runtime_metadata,
            )
            last_ocr_timestamp = float(ocr_metrics.get("last_sample_timestamp_seconds") or 0.0)
            ocr_coverage_end = min(duration, last_ocr_timestamp + effective_ocr_interval) if duration > 0 else None
            ocr_metrics["video_duration_seconds"] = round(duration, 3) if duration > 0 else None
            ocr_metrics["coverage_end_seconds"] = round(ocr_coverage_end, 3) if ocr_coverage_end is not None else None
            ocr_metrics["covers_entire_video"] = (
                ocr_coverage_end >= duration - max(0.05, effective_ocr_interval * 0.05)
                if ocr_coverage_end is not None and duration > 0
                else None
            )
            if ocr_errors:
                ocr_metrics["errors"] = ocr_errors[:8]
            review_flags.extend(str(flag) for flag in ocr_metrics.get("review_flags", []))
            serious_review_flags.extend(str(flag) for flag in ocr_metrics.get("serious_review_flags", []))
        else:
            ocr_metrics = {
                "available": False,
                "sampled_frames": 0,
                "sample_interval_seconds": effective_ocr_interval,
                "frame_budget": OCR_MAX_FRAMES,
                "video_duration_seconds": round(duration, 3) if duration > 0 else None,
                "errors": ocr_errors or ["OCR produced no parseable frame data."],
                "review_flags": ["ocr_text_layout_not_checked"],
                "serious_review_flags": [],
            }
            review_flags.append("ocr_text_layout_not_checked")
    else:
        ocr_metrics = {
            "available": False,
            "sampled_frames": 0,
            "sample_interval_seconds": ocr_interval,
            "frame_budget": OCR_MAX_FRAMES,
            "video_duration_seconds": round(duration, 3) if duration > 0 else None,
            "errors": ["Tesseract executable was not found."],
            "review_flags": ["ocr_text_layout_not_checked"],
            "serious_review_flags": [],
        }
        review_flags.append("ocr_text_layout_not_checked")

    review_flags = list(dict.fromkeys(review_flags))
    serious_review_flags = list(dict.fromkeys(serious_review_flags))

    active_pixel_ratios = [float(item["active_pixel_ratio"]) for item in usage]
    active_tile_ratios = [float(item["active_tile_ratio"]) for item in usage]
    visual_lane_active_ratios = [float(item["active_pixel_ratio"]) for item in visual_lane_profiles]
    visual_lane_bbox_widths = [float(item["bbox_width_ratio"]) for item in visual_lane_profiles]
    visual_lane_bbox_heights = [float(item["bbox_height_ratio"]) for item in visual_lane_profiles]
    visual_lane_bbox_fills = [float(item["bbox_fill_ratio"]) for item in visual_lane_profiles]
    visual_lane_centroids = [float(item["centroid_y_ratio"]) for item in visual_lane_profiles]
    visual_lane_occupied_rows = [float(item["occupied_row_ratio"]) for item in visual_lane_profiles]
    visual_lane_lower_coverage = [float(item["lower_half_occupied_row_ratio"]) for item in visual_lane_profiles]
    visual_lane_component_counts = [float(item["component_count"]) for item in visual_lane_profiles]
    visual_lane_internal_edges = [float(item["internal_edge_pixel_ratio"]) for item in visual_lane_profiles]
    visual_lane_contour_changes = [float(item["contour_change_ratio"]) for item in visual_lane_profiles]
    portrait_core_widths = [float(item["core_width_occupancy"]) for item in portrait_profiles]
    portrait_core_heights = [float(item["core_height_occupancy"]) for item in portrait_profiles]
    portrait_core_areas = [float(item["core_area_occupancy"]) for item in portrait_profiles]
    portrait_occupied_rows = [float(item["occupied_row_ratio"]) for item in portrait_profiles]
    portrait_occupied_columns = [float(item["occupied_column_ratio"]) for item in portrait_profiles]
    return {
        "sampled_frames": len(frames),
        "sample_interval_seconds": analysis_interval,
        "motion_sampled_frames": len(motion_frames),
        "motion_sample_interval_seconds": motion_analysis_interval,
        "analyzed_span_seconds": round(max(0, len(frames) - 1) * analysis_interval, 2),
        "max_edge_density": round(max_edge, 4),
        "avg_edge_density": round(sum(densities) / len(densities), 4) if densities else 0.0,
        "max_middle_band_density": round(max_middle, 4),
        "avg_frame_change_luma": round(sum(mean_deltas) / len(mean_deltas), 3) if mean_deltas else 0.0,
        "median_frame_change_luma": round(percentile(mean_deltas, 0.5), 3),
        "p90_frame_change_luma": round(percentile(mean_deltas, 0.9), 3),
        "avg_changed_pixel_ratio": round(sum(changed_ratios) / len(changed_ratios), 4) if changed_ratios else 0.0,
        "static_transition_ratio": round(static_ratio, 4),
        "low_change_transition_ratio": round(low_change_ratio, 4),
        "broad_visual_change_transition_ratio": round(broad_visual_change_ratio, 4),
        "motion_transition_ratio": round(motion_ratio, 4),
        "spatial_motion_transition_ratio": round(spatial_motion_ratio, 4),
        "progressive_draw_transition_ratio": round(progressive_draw_ratio, 4),
        "opacity_dominated_transition_ratio": round(opacity_ratio, 4),
        "motion_window_coverage_ratio": round(motion_windows, 4),
        "max_motion_free_gap_seconds": round(max_motion_free_gap, 2),
        "terminal_static_duration_seconds": round(terminal_static_duration, 2),
        "max_static_hold_seconds": round(max_static_hold, 2),
        "max_low_change_hold_seconds": round(max_low_change_hold, 2),
        "blank_frame_ratio": round(blank_ratio, 4),
        "max_blank_hold_seconds": round(max_blank_hold, 2),
        "underused_frame_ratio": round(underused_ratio, 4),
        "max_underused_hold_seconds": round(max_underused_hold, 2),
        "sparse_visual_lane_frame_ratio": round(sparse_visual_lane_ratio, 4),
        "max_sparse_visual_lane_hold_seconds": round(max_sparse_visual_lane_hold, 2),
        "outer_portrait_underfill_frame_ratio": round(outer_portrait_underfill_ratio, 4),
        "max_outer_portrait_underfill_hold_seconds": round(max_outer_portrait_underfill_hold, 2),
        "outer_portrait_overfill_frame_ratio": round(outer_portrait_overfill_ratio, 4),
        "max_outer_portrait_overfill_hold_seconds": round(max_outer_portrait_overfill_hold, 2),
        "evidence_lane_intrusion_frame_ratio": round(evidence_intrusion_ratio, 4),
        "max_evidence_lane_intrusion_hold_seconds": round(max_evidence_intrusion_hold, 2),
        "median_portrait_core_width_occupancy": round(percentile(portrait_core_widths, 0.5), 4),
        "median_portrait_core_height_occupancy": round(percentile(portrait_core_heights, 0.5), 4),
        "median_portrait_core_area_occupancy": round(percentile(portrait_core_areas, 0.5), 4),
        "median_portrait_core_occupied_row_ratio": round(percentile(portrait_occupied_rows, 0.5), 4),
        "median_portrait_core_occupied_column_ratio": round(percentile(portrait_occupied_columns, 0.5), 4),
        "visual_lane_structural_frame_ratio": round(visual_lane_structural_ratio, 4),
        "visual_lane_temporal_support_frame_ratio": round(visual_lane_temporal_support_ratio, 4),
        "meaningful_visual_lane_frame_ratio": round(meaningful_visual_lane_ratio, 4),
        "median_visual_lane_active_pixel_ratio": round(percentile(visual_lane_active_ratios, 0.5), 4),
        "median_visual_lane_bbox_width_ratio": round(percentile(visual_lane_bbox_widths, 0.5), 4),
        "median_visual_lane_bbox_height_ratio": round(percentile(visual_lane_bbox_heights, 0.5), 4),
        "median_visual_lane_bbox_fill_ratio": round(percentile(visual_lane_bbox_fills, 0.5), 4),
        "median_visual_lane_centroid_y_ratio": round(percentile(visual_lane_centroids, 0.5), 4),
        "median_visual_lane_occupied_row_ratio": round(percentile(visual_lane_occupied_rows, 0.5), 4),
        "median_visual_lane_lower_half_coverage_ratio": round(percentile(visual_lane_lower_coverage, 0.5), 4),
        "median_visual_lane_component_count": round(percentile(visual_lane_component_counts, 0.5), 2),
        "median_visual_lane_internal_edge_pixel_ratio": round(percentile(visual_lane_internal_edges, 0.5), 4),
        "median_visual_lane_contour_change_ratio": round(percentile(visual_lane_contour_changes, 0.5), 4),
        "sparse_visual_lane_timestamps_seconds": [
            round(frame_index * analysis_interval, 2)
            for frame_index, state in enumerate(sparse_visual_lane_states)
            if state
        ][:24],
        "max_interior_empty_vertical_band_ratio": round(max(empty_vertical_bands), 4) if empty_vertical_bands else 0.0,
        "extreme_layout_imbalance_frame_ratio": round(extreme_layout_ratio, 4),
        "max_extreme_layout_imbalance_hold_seconds": round(max_extreme_layout_hold, 2),
        "extreme_layout_imbalance_timestamps_seconds": [
            round(frame_index * analysis_interval, 2)
            for frame_index, state in enumerate(extreme_layout_states)
            if state
        ][:24],
        "avg_active_pixel_ratio": round(sum(active_pixel_ratios) / len(active_pixel_ratios), 4) if active_pixel_ratios else 0.0,
        "median_active_tile_ratio": round(percentile(active_tile_ratios, 0.5), 4),
        "temporal_visual_integrity": temporal_visual_metrics,
        "ocr_text_layout": ocr_metrics,
        "thresholds": {
            "changed_pixel_min_luma_delta": CHANGE_PIXEL_LUMA,
            "motion_analysis_interval_seconds": MOTION_ANALYSIS_INTERVAL_SECONDS,
            "static_pair_max_mean_luma_delta": STATIC_MAX_MAD,
            "static_pair_max_changed_pixel_ratio": STATIC_MAX_CHANGED_RATIO,
            "low_change_pair_max_mean_luma_delta": LOW_CHANGE_MAX_MAD,
            "low_change_pair_max_changed_pixel_ratio": LOW_CHANGE_MAX_CHANGED_RATIO,
            "prolonged_static_hold_seconds": PROLONGED_STATIC_SECONDS,
            "terminal_static_hold_seconds": TERMINAL_STATIC_SECONDS,
            "maximum_motion_free_gap_seconds": MAX_MOTION_FREE_GAP_SECONDS,
            "prolonged_low_change_seconds": PROLONGED_LOW_CHANGE_SECONDS,
            "low_change_transition_ratio": LOW_CHANGE_RATIO_LIMIT,
            "min_motion_transition_ratio": MIN_MOTION_RATIO,
            "motion_window_seconds": MOTION_WINDOW_SECONDS,
            "min_motion_window_coverage_ratio": MIN_MOTION_WINDOW_COVERAGE,
            "motion_min_active_changed_pixel_ratio": MOTION_MIN_ACTIVE_CHANGED_RATIO,
            "motion_min_local_bidirectional_ratio": MOTION_MIN_LOCAL_BIDIRECTIONAL_RATIO,
            "motion_min_support_extension_ratio": MOTION_MIN_SUPPORT_EXTENSION_RATIO,
            "motion_stable_max_luma_delta": MOTION_STABLE_MAX_LUMA_DELTA,
            "motion_min_support_component_pixels": MOTION_MIN_SUPPORT_COMPONENT_PIXELS,
            "motion_min_support_component_width_ratio": MOTION_MIN_SUPPORT_COMPONENT_WIDTH_RATIO,
            "motion_min_support_component_height_ratio": MOTION_MIN_SUPPORT_COMPONENT_HEIGHT_RATIO,
            "motion_min_spatial_run_transitions": MOTION_MIN_SPATIAL_RUN_TRANSITIONS,
            "motion_min_draw_run_transitions": MOTION_MIN_DRAW_RUN_TRANSITIONS,
            "blank_max_luma_stddev": BLANK_MAX_LUMA_STDDEV,
            "blank_max_active_pixel_ratio": BLANK_MAX_ACTIVE_PIXEL_RATIO,
            "blank_max_edge_density": BLANK_MAX_EDGE_DENSITY,
            "blank_frame_ratio": BLANK_FRAME_RATIO_LIMIT,
            "blank_hold_seconds": BLANK_HOLD_SECONDS,
            "underused_max_active_pixel_ratio": UNDERUSED_MAX_ACTIVE_PIXEL_RATIO,
            "underused_max_active_tile_ratio": UNDERUSED_MAX_ACTIVE_TILE_RATIO,
            "underused_frame_ratio": UNDERUSED_FRAME_RATIO_LIMIT,
            "underused_hold_seconds": UNDERUSED_HOLD_SECONDS,
            "extreme_empty_vertical_band_ratio": EXTREME_EMPTY_VERTICAL_BAND_RATIO,
            "extreme_layout_frame_ratio": EXTREME_LAYOUT_FRAME_RATIO_LIMIT,
            "extreme_layout_hold_seconds": EXTREME_LAYOUT_HOLD_SECONDS,
            "visual_lane_top_ratio": VISUAL_LANE_TOP_RATIO,
            "visual_lane_bottom_ratio": VISUAL_LANE_BOTTOM_RATIO,
            "visual_lane_min_bbox_height_ratio": VISUAL_LANE_MIN_BBOX_HEIGHT_RATIO,
            "visual_lane_min_occupied_row_ratio": VISUAL_LANE_MIN_OCCUPIED_ROW_RATIO,
            "visual_lane_min_component_pixels": VISUAL_LANE_MIN_COMPONENT_PIXELS,
            "visual_lane_min_component_count": VISUAL_LANE_MIN_COMPONENT_COUNT,
            "visual_lane_min_internal_edge_pixels": VISUAL_LANE_MIN_INTERNAL_EDGE_PIXELS,
            "visual_lane_min_internal_edge_ratio": VISUAL_LANE_MIN_INTERNAL_EDGE_RATIO,
            "visual_lane_min_internal_edge_tiles": VISUAL_LANE_MIN_INTERNAL_EDGE_TILES,
            "visual_lane_min_contour_change_ratio": VISUAL_LANE_MIN_CONTOUR_CHANGE_RATIO,
            "visual_lane_min_structure_pixels": VISUAL_LANE_MIN_STRUCTURE_PIXELS,
            "visual_lane_min_structure_span_ratio": VISUAL_LANE_MIN_STRUCTURE_SPAN_RATIO,
            "visual_lane_motion_min_changed_pixels": VISUAL_LANE_MOTION_MIN_CHANGED_PIXELS,
            "visual_lane_motion_min_gain_loss_balance": VISUAL_LANE_MOTION_MIN_GAIN_LOSS_BALANCE,
            "visual_lane_motion_max_centroid_distance_ratio": VISUAL_LANE_MOTION_MAX_CENTROID_DISTANCE_RATIO,
            "visual_lane_motion_max_changed_bbox_ratio": VISUAL_LANE_MOTION_MAX_CHANGED_BBOX_RATIO,
            "visual_lane_max_sparse_frame_ratio": VISUAL_LANE_MAX_SPARSE_FRAME_RATIO,
            "visual_lane_max_sparse_hold_seconds": VISUAL_LANE_MAX_SPARSE_HOLD_SECONDS,
            "portrait_core_top_ratio": PORTRAIT_CORE_TOP_RATIO,
            "portrait_core_bottom_ratio": PORTRAIT_CORE_BOTTOM_RATIO,
            "portrait_evidence_top_ratio": PORTRAIT_EVIDENCE_TOP_RATIO,
            "portrait_evidence_bottom_ratio": PORTRAIT_EVIDENCE_BOTTOM_RATIO,
            "portrait_core_min_width_occupancy": PORTRAIT_CORE_MIN_WIDTH_OCCUPANCY,
            "portrait_core_max_width_occupancy": PORTRAIT_CORE_MAX_WIDTH_OCCUPANCY,
            "portrait_core_min_height_occupancy": PORTRAIT_CORE_MIN_HEIGHT_OCCUPANCY,
            "portrait_core_max_height_occupancy": PORTRAIT_CORE_MAX_HEIGHT_OCCUPANCY,
            "portrait_core_min_area_occupancy": PORTRAIT_CORE_MIN_AREA_OCCUPANCY,
            "portrait_core_min_occupied_row_ratio": PORTRAIT_CORE_MIN_OCCUPIED_ROW_RATIO,
            "portrait_core_min_occupied_column_ratio": PORTRAIT_CORE_MIN_OCCUPIED_COLUMN_RATIO,
            "portrait_core_min_tile_support_ratio": PORTRAIT_CORE_MIN_TILE_SUPPORT_RATIO,
            "portrait_layout_max_flagged_frame_ratio": PORTRAIT_LAYOUT_MAX_FLAGGED_FRAME_RATIO,
            "portrait_layout_max_flagged_hold_seconds": PORTRAIT_LAYOUT_MAX_FLAGGED_HOLD_SECONDS,
        },
        "review_flags": review_flags,
        "serious_review_flags": serious_review_flags,
    }


def audit_failure_reasons(report: dict[str, object], *, require_ocr: bool) -> list[str]:
    reasons: list[str] = []
    videos = report.get("videos")
    if not isinstance(videos, list):
        return ["audit report has no videos array"]
    for item in videos:
        if not isinstance(item, dict):
            continue
        video = str(item.get("video") or "video")
        metrics = item.get("metrics")
        if not isinstance(metrics, dict):
            reasons.append(f"{video}: frame metrics are unavailable")
            continue
        serious = metrics.get("serious_review_flags")
        if isinstance(serious, list) and serious:
            reasons.append(f"{video}: serious flags: {', '.join(str(flag) for flag in serious)}")
        ocr = metrics.get("ocr_text_layout")
        if require_ocr and (
            not isinstance(ocr, dict)
            or not bool(ocr.get("available"))
            or int(ocr.get("sampled_frames") or 0) < 1
        ):
            reasons.append(f"{video}: required OCR/layout audit is unavailable")
    return reasons


def runtime_metadata_by_video(run: Path) -> dict[str, dict[str, object]]:
    """Index optional generated runtime rows by normalized video path."""
    trace_path = run / "render_runtime_trace.json"
    if not trace_path.is_file():
        return {}
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    renders = payload.get("renders") if isinstance(payload, dict) else None
    if not isinstance(renders, list):
        return {}
    return {
        Path(str(row.get("video_file"))).as_posix(): row
        for row in renders
        if isinstance(row, dict) and str(row.get("video_file") or "").strip()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit rendered short videos with contact sheets and frame metrics.")
    parser.add_argument("run", type=Path)
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between sampled contact-sheet frames.")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument(
        "--allow-missing-ocr",
        action="store_true",
        help="Allow draft/preview audits to complete when OCR is unavailable.",
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.cols <= 0 or args.rows <= 0:
        parser.error("--cols and --rows must be greater than zero")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required for frame audit.")
    tesseract = shutil.which("tesseract")
    run = args.run.resolve()
    videos = video_files(run)
    require_ocr = not args.allow_missing_ocr and any(video.name.endswith("_final.mp4") for video in videos)
    out_dir = run / "visual_audit"
    runtime_rows = runtime_metadata_by_video(run)
    report: dict[str, object] = {
        "run": str(run),
        "settings": {
            "contact_sheet_interval_seconds": args.interval,
            "contact_sheet_columns": args.cols,
            "contact_sheet_rows": args.rows,
            "ocr_max_sample_interval_seconds": OCR_SAMPLE_INTERVAL_SECONDS,
            "ocr_frame_budget_per_video": OCR_MAX_FRAMES,
            "temporal_visual_max_sample_interval_seconds": TEMPORAL_VISUAL_SAMPLE_INTERVAL_SECONDS,
            "temporal_visual_frame_budget_per_video": TEMPORAL_VISUAL_MAX_FRAMES,
            "temporal_text_max_sample_interval_seconds": TEMPORAL_TEXT_SAMPLE_INTERVAL_SECONDS,
            "temporal_text_frame_budget_per_video": TEMPORAL_TEXT_MAX_FRAMES,
            "ocr_required": require_ocr,
        },
        "videos": [],
    }
    for video in videos:
        sheet = out_dir / f"{video.stem}_contact.jpg"
        duration = probe_video_duration(video)
        sheet_result = make_contact_sheet(
            ffmpeg,
            video,
            sheet,
            interval=args.interval,
            cols=args.cols,
            rows=args.rows,
            duration=duration,
        )
        sheet_paths = [Path(path) for path in sheet_result["paths"]]
        relative_sheet_paths = [str(path.relative_to(run)) for path in sheet_paths]
        item = {
            "video": str(video.relative_to(run)),
            "contact_sheet": relative_sheet_paths[0],
            "contact_sheets": relative_sheet_paths,
            "contact_sheet_coverage": sheet_result["coverage"],
            "metrics": metrics_for(
                ffmpeg,
                video,
                interval=args.interval,
                tesseract=tesseract,
                duration=duration,
                runtime_metadata=runtime_rows.get(video.relative_to(run).as_posix()),
            ),
        }
        report["videos"].append(item)
        for sheet_path in sheet_paths:
            print(sheet_path)
    report_path = run / "visual_frame_audit.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_path)
    failure_reasons = audit_failure_reasons(report, require_ocr=require_ocr)
    for reason in failure_reasons:
        print(f"ERROR: {reason}", file=sys.stderr)
    return 1 if failure_reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())

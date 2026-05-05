#!/usr/bin/env python3
"""Validate generated course notes, Manim assets, captions, and videos.

The validator is intentionally topic-agnostic: it checks the quality signals
that matter before upload without depending on a particular STEM subject.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}
MIN_FINAL_DURATION_SECONDS = 10.0
MIN_ANY_VIDEO_DURATION_SECONDS = 3.0
TARGET_ASPECT_RATIO = 9 / 16


@dataclass
class Issue:
    severity: str
    area: str
    message: str
    path: str | None = None
    line: int | None = None
    fix: str | None = None


class CourseRunValidator:
    def __init__(self, run: Path, *, draft: bool = False, allow_fallback_pdf: bool = False) -> None:
        self.run = run.resolve()
        self.draft = draft
        self.allow_fallback_pdf = allow_fallback_pdf
        self.issues: list[Issue] = []
        self.ffprobe = shutil.which("ffprobe")
        self.ffmpeg = shutil.which("ffmpeg")
        self.video_cache: dict[Path, dict[str, Any]] = {}

    def validate(self) -> list[Issue]:
        if not self.run.exists():
            self.fail("run", "Run directory does not exist.", self.run, fix="Pass an existing runs/<course> directory.")
            return self.issues
        if not self.run.is_dir():
            self.fail("run", "Run path is not a directory.", self.run)
            return self.issues

        plan = self.load_json(self.run / "short_plan.json", required=False)
        self.validate_source_pack()
        self.validate_notes()
        self.validate_short_plan(plan)
        self.validate_scene_script_caption_assets(plan)
        self.validate_videos(plan)
        self.validate_publish_queue()
        return self.issues

    def fail(self, area: str, message: str, path: Path | None = None, *, line: int | None = None, fix: str | None = None) -> None:
        self.issues.append(Issue("FAIL", area, message, self.display_path(path), line, fix))

    def warn(self, area: str, message: str, path: Path | None = None, *, line: int | None = None, fix: str | None = None) -> None:
        self.issues.append(Issue("WARN", area, message, self.display_path(path), line, fix))

    def info(self, area: str, message: str, path: Path | None = None, *, fix: str | None = None) -> None:
        self.issues.append(Issue("INFO", area, message, self.display_path(path), None, fix))

    def display_path(self, path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return str(path.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            return str(path)

    def load_json(self, path: Path, *, required: bool) -> Any:
        if not path.exists():
            if required:
                self.fail("json", "Required JSON artifact is missing.", path)
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.fail("json", f"JSON is not parseable: {exc.msg}.", path, line=exc.lineno, fix="Regenerate or repair this JSON file.")
            return None

    def validate_source_pack(self) -> None:
        source_pack = self.run / "source_pack.json"
        if not source_pack.exists():
            self.warn("source-pack", "source_pack.json is missing; coverage cannot be audited.", source_pack)
            return
        pack = self.load_json(source_pack, required=True)
        if isinstance(pack, dict):
            text = json.dumps(pack, ensure_ascii=False)
            if len(text) < 1000:
                self.warn("source-pack", "source_pack.json is very small; notes may be based on thin source material.", source_pack)

    def validate_notes(self) -> None:
        tex = self.run / "notes.tex"
        md = self.run / "notes.md"
        pdf = self.run / "notes.pdf"
        report_path = self.run / "notes_compile_report.json"

        if not tex.exists() and not md.exists():
            self.warn("notes", "No notes.tex or notes.md artifact found.", self.run, fix="Run `python tools/stem_course.py notes --run <run> --compile`.")
            return

        if tex.exists():
            self.check_nonempty(tex, "notes")
            self.scan_latex_quality(tex)
        else:
            self.warn("notes", "notes.tex is missing; LaTeX formatting cannot be checked.", tex)

        if md.exists():
            self.check_nonempty(md, "notes")
            self.scan_markdown_quality(md)
        else:
            self.warn("notes", "notes.md is missing.", md)

        if not pdf.exists():
            self.fail("notes.pdf", "Compiled notes.pdf is missing.", pdf, fix="Run notes generation with `--compile`; use `--pdf-engine latex` for a real LaTeX build.")
        else:
            self.check_pdf_file(pdf)

        report = self.load_json(report_path, required=False)
        if report is None:
            self.warn("notes.compile", "notes_compile_report.json is missing; PDF provenance is unknown.", report_path)
            return
        if not isinstance(report, dict):
            self.fail("notes.compile", "notes_compile_report.json must be an object.", report_path)
            return
        status = report.get("status")
        engine = str(report.get("engine", "unknown"))
        if status != "ok":
            self.fail("notes.compile", f"Notes compile status is {status!r}, not 'ok'.", report_path, fix="Read the compile report/log and rerun notes compilation.")
        if engine == "pymupdf-fallback":
            message = "notes.pdf was generated by the PyMuPDF fallback, so LaTeX layout/formatting was not actually compiled."
            fix = "Install tectonic, BasicTeX, or MacTeX, then run `python tools/stem_course.py notes --run <run> --compile --pdf-engine latex`."
            if self.allow_fallback_pdf:
                self.warn("notes.compile", message, report_path, fix=fix)
            else:
                self.fail("notes.compile", message, report_path, fix=fix)

    def scan_latex_quality(self, path: Path) -> None:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        in_display_math = False
        for lineno, line in enumerate(lines, start=1):
            line_no_comment = strip_latex_comment(line)
            outside_segments, in_display_math = latex_outside_display_segments(line_no_comment, in_display_math)
            outside_text = " ".join(outside_segments)
            if re.search(r"\[\s*\[[^\n]{1,160}\]\s*,\s*\[[^\n]{1,160}\]\s*\]", outside_text):
                self.fail(
                    "notes.latex",
                    "Matrix is written as prose/Python list notation instead of a LaTeX matrix.",
                    path,
                    line=lineno,
                    fix="Use a displayed math environment such as `\\begin{bmatrix}2 & 1 \\\\ 1 & 3\\end{bmatrix}`.",
                )
            if re.search(r"\\\^(?:\\\{\\\})?", line_no_comment):
                self.fail(
                    "notes.latex",
                    "Escaped power notation will render as literal caret text instead of mathematical exponentiation.",
                    path,
                    line=lineno,
                    fix="Use math mode, for example `$3^2 + 4^2$`, rather than `\\^\\{\\}`.",
                )
            for segment in outside_segments:
                for inline_segment in outside_math_segments(segment):
                    if re.search(r"(?<!\\)\^", inline_segment):
                        self.fail(
                            "notes.latex",
                            "Bare `^` appears outside math mode.",
                            path,
                            line=lineno,
                            fix="Wrap exponent expressions in `$...$` or rewrite them using a LaTeX math environment.",
                        )
                        break
                    if re.search(r"\bsqrt\s*\(", inline_segment):
                        self.warn(
                            "notes.latex",
                            "`sqrt(...)` appears as prose rather than LaTeX math.",
                            path,
                            line=lineno,
                            fix="Use `\\sqrt{...}` inside math mode.",
                        )
                        break

    def scan_markdown_quality(self, path: Path) -> None:
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if re.search(r"\[\s*\[[^\n]{1,160}\]\s*,\s*\[[^\n]{1,160}\]\s*\]", line):
                self.warn(
                    "notes.markdown",
                    "Matrix is written as Python list notation; generated notes should present matrices as math.",
                    path,
                    line=lineno,
                    fix="Prefer a LaTeX `bmatrix` or a clearly formatted Markdown table.",
                )

    def check_pdf_file(self, path: Path) -> None:
        if path.stat().st_size < 1024:
            self.fail("notes.pdf", "notes.pdf is too small to be a useful compiled artifact.", path)
            return
        with path.open("rb") as handle:
            header = handle.read(5)
        if header != b"%PDF-":
            self.fail("notes.pdf", "notes.pdf does not start with a PDF header.", path, fix="Regenerate the PDF.")
        elif path.stat().st_size < 10_000:
            self.warn("notes.pdf", "notes.pdf is unusually small; verify it contains the full notes.", path)

    def validate_short_plan(self, plan: Any) -> None:
        if plan is None:
            self.warn("short-plan", "short_plan.json is missing; expected scene/script/caption coverage cannot be audited.", self.run / "short_plan.json")
            return
        if not isinstance(plan, dict):
            self.fail("short-plan", "short_plan.json must be an object.", self.run / "short_plan.json")
            return
        shorts = plan.get("shorts")
        if not isinstance(shorts, list) or not shorts:
            self.fail("short-plan", "short_plan.json has no shorts array.", self.run / "short_plan.json")
            return
        required_fields = ["index", "concept", "hook", "intuition", "worked_example", "question_prompt", "visual_type"]
        for pos, short in enumerate(shorts, start=1):
            if not isinstance(short, dict):
                self.fail("short-plan", f"Short item {pos} is not an object.", self.run / "short_plan.json")
                continue
            for field in required_fields:
                if field not in short:
                    self.fail("short-plan", f"Short {short.get('index', pos)} is missing `{field}`.", self.run / "short_plan.json")

    def validate_scene_script_caption_assets(self, plan: Any) -> None:
        shorts = plan_shorts(plan)
        if not shorts:
            return
        if not self.scene_asset_stage_present(shorts):
            return

        normalized_sources: list[tuple[Path, str]] = []
        for short in shorts:
            index = int(short.get("index", 0) or 0)
            concept = str(short.get("concept", f"short-{index}"))
            slug = slugify(concept)
            scene = self.run / str(short.get("scene_file") or f"scenes/short_{index:02d}_{slug}.py")
            caption = self.run / str(short.get("srt_file") or f"captions/short_{index:02d}_{slug}.srt")
            script = self.run / "scripts" / f"short_{index:02d}_{slug}.md"

            self.validate_scene(scene, index, normalized_sources)
            self.validate_caption(caption, index)
            self.validate_script(script, index)

        self.detect_repeated_scene_sources(normalized_sources)

    def scene_asset_stage_present(self, shorts: list[dict[str, Any]]) -> bool:
        if any((self.run / dirname).exists() for dirname in ("scenes", "scripts", "captions")):
            return True
        return any("scene_file" in short or "srt_file" in short or "class_name" in short for short in shorts)

    def validate_scene(self, path: Path, index: int, normalized_sources: list[tuple[Path, str]]) -> None:
        if not path.exists():
            self.fail("scene", f"Scene file for short {index:02d} is missing.", path, fix="Run `python tools/stem_course.py manim --run <run>` or restore the scene file.")
            return
        self.check_nonempty(path, "scene")
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            compile(text, str(path), "exec")
        except SyntaxError as exc:
            self.fail("scene", f"Scene Python has a syntax error: {exc.msg}.", path, line=exc.lineno, fix="Repair the Manim scene before rendering.")
            return

        if re.search(r"\b(?:setup|calc|question|answer)_lines\s*=\s*\[[^\n]*\[\s*\[", text):
            self.fail(
                "scene.layout",
                "Scene-facing text contains matrix/Python list notation, which usually renders as an unreadable single-line label.",
                path,
                fix="Sanitize narration/screen text and show matrices through a visual matrix object or MathTex bmatrix.",
            )

        play_count = len(re.findall(r"\bself\.play\s*\(", text))
        if play_count == 0:
            self.fail("scene.motion", f"Scene for short {index:02d} has no self.play calls and will look static.", path, fix="Add animated transformations, writes, fades, or camera movement.")
        elif play_count < 3:
            self.warn("scene.motion", f"Scene for short {index:02d} has only {play_count} self.play calls.", path, fix="Add enough visual changes to avoid a static explainer.")

        wait_total = sum(parse_float(value) for value in re.findall(r"\bself\.wait\s*\(\s*([0-9.]+)", text))
        if wait_total > 45 and play_count < 8:
            self.warn("scene.motion", f"Scene waits for {wait_total:.1f}s with relatively few animations.", path, fix="Break long waits with meaningful highlights or transformations.")

        width = first_int_match(r"config\.pixel_width\s*=\s*(\d+)", text)
        height = first_int_match(r"config\.pixel_height\s*=\s*(\d+)", text)
        if width and height:
            if height <= width:
                self.fail("scene.orientation", f"Scene config is not vertical ({width}x{height}).", path, fix="Use vertical 9:16 dimensions such as 1080x1920.")
            elif abs((width / height) - TARGET_ASPECT_RATIO) > 0.08:
                self.warn("scene.orientation", f"Scene aspect ratio {width}:{height} is not close to 9:16.", path)
        else:
            self.warn("scene.orientation", "Scene does not set config.pixel_width and config.pixel_height.", path, fix="Set 1080x1920 or another vertical 9:16 size.")

        normalized_sources.append((path, normalize_scene_source(text)))

    def detect_repeated_scene_sources(self, sources: list[tuple[Path, str]]) -> None:
        for i, (left_path, left_text) in enumerate(sources):
            for right_path, right_text in sources[i + 1 :]:
                if not left_text or not right_text:
                    continue
                ratio = SequenceMatcher(None, left_text, right_text).ratio()
                if ratio > 0.94:
                    self.warn(
                        "scene.repetition",
                        f"Scene source is {ratio:.0%} similar to {self.display_path(right_path)}; batch may look repetitive.",
                        left_path,
                        fix="Vary the visual model, transformations, layout, or worked-example animation.",
                    )

    def validate_caption(self, path: Path, index: int) -> None:
        if not path.exists():
            self.fail("caption", f"SRT caption for short {index:02d} is missing.", path)
            return
        self.check_nonempty(path, "caption")
        text = path.read_text(encoding="utf-8", errors="replace")
        cues = parse_srt_cues(text)
        if not cues:
            self.fail("caption", f"SRT caption for short {index:02d} has no parseable cues.", path, fix="Regenerate captions or repair the SRT timestamps.")
            return
        previous_end = -1.0
        for start, end in cues:
            if end <= start:
                self.fail("caption", f"SRT cue has non-positive duration ({start:.2f}s to {end:.2f}s).", path)
            if start < previous_end - 0.05:
                self.fail("caption", "SRT cues overlap or move backward in time.", path)
                break
            previous_end = end
        total = max(end for _, end in cues)
        if total < 20:
            self.warn("caption", f"SRT caption for short {index:02d} is only {total:.1f}s long.", path)

    def validate_script(self, path: Path, index: int) -> None:
        if not path.exists():
            self.fail("script", f"Script markdown for short {index:02d} is missing.", path)
            return
        self.check_nonempty(path, "script")
        text = path.read_text(encoding="utf-8", errors="replace")
        word_count = len(re.findall(r"\b[\w'-]+\b", text))
        if word_count < 45:
            self.warn("script", f"Script for short {index:02d} is very short ({word_count} words).", path)
        if "## Beats" not in text and "|" not in text:
            self.warn("script", f"Script for short {index:02d} does not expose a beat/timing structure.", path)
        if re.search(r"\bmatrix\b[^\n]{0,80}\[\s*\[[^\n]{1,160}\]\s*,\s*\[[^\n]{1,160}\]\s*\]", text, flags=re.I):
            self.warn(
                "script.format",
                "Script text describes a matrix using Python list notation; that tends to leak into captions or on-screen labels.",
                path,
                fix="Use spoken prose for narration and a rendered matrix visual in the scene.",
            )

    def validate_videos(self, plan: Any) -> None:
        shorts = plan_shorts(plan)
        if shorts and self.render_outputs_expected(shorts):
            self.validate_expected_render_outputs(shorts)

        for video in sorted((self.run / "videos").glob("**/*")):
            if video.is_file() and video.suffix.lower() in VIDEO_SUFFIXES:
                role = "final" if "_final" in video.name or video.name.endswith("final.mp4") else "raw"
                self.validate_video_file(video, role=role)

        for video in sorted((self.run / "manim_media" / "videos").glob("**/*.mp4")):
            if "partial_movie_files" in video.parts:
                continue
            self.validate_video_file(video, role="manim")

        render_report = self.load_json(self.run / "render_report.json", required=False)
        if render_report is not None:
            self.validate_render_report(render_report)

    def render_outputs_expected(self, shorts: list[dict[str, Any]]) -> bool:
        if (self.run / "videos").exists() or (self.run / "render_report.json").exists() or (self.run / "instagram_publish_queue.json").exists():
            return True
        if any("video_file" in short for short in shorts):
            return True
        return self.scene_asset_stage_present(shorts)

    def validate_expected_render_outputs(self, shorts: list[dict[str, Any]]) -> None:
        for short in shorts:
            index = int(short.get("index", 0) or 0)
            concept = str(short.get("concept", f"short-{index}"))
            slug = slugify(concept)
            class_name = str(short.get("class_name") or "".join(part.title() for part in slug.split("-")) + "Short")
            expected_final = self.run / str(short.get("video_file") or f"videos/short_{index:02d}_{slug}_final.mp4")
            final_exists = expected_final.exists()
            if not final_exists:
                severity = self.warn if self.draft else self.fail
                severity(
                    "video.final",
                    f"Final MP4 for short {index:02d} is missing.",
                    expected_final,
                    fix="Run `python tools/stem_course.py render --run <run> --voice-engine <engine>` before queueing or publishing.",
                )
            else:
                self.validate_video_file(expected_final, role="final")

            manim_outputs = [
                path
                for path in (self.run / "manim_media" / "videos").glob(f"**/{class_name}.mp4")
                if "partial_movie_files" not in path.parts
            ]
            raw = self.run / "videos" / f"short_{index:02d}_{slug}_raw.mp4"
            if not manim_outputs and not raw.exists() and not final_exists:
                severity = self.warn if self.draft else self.fail
                severity(
                    "video.manim",
                    f"No rendered Manim MP4 was found for short {index:02d}.",
                    self.run / "manim_media" / "videos",
                    fix="Render the scene and inspect the Manim log if the class output is missing.",
                )

    def validate_render_report(self, report: Any) -> None:
        if not isinstance(report, dict):
            self.fail("render-report", "render_report.json must be an object.", self.run / "render_report.json")
            return
        results = report.get("results")
        if not isinstance(results, list):
            self.fail("render-report", "render_report.json has no results array.", self.run / "render_report.json")
            return
        for result in results:
            if not isinstance(result, dict):
                continue
            status = result.get("status")
            if status != "rendered":
                self.fail("render-report", f"Render result for short {result.get('index')} is {status!r}.", self.run / "render_report.json", fix="Fix the failed render stage and rerun rendering.")
            voice = result.get("voiceover")
            if isinstance(voice, dict) and voice.get("status") not in {"ok", None}:
                severity = self.warn if self.draft else self.fail
                severity(
                    "render-report.audio",
                    f"Voiceover for short {result.get('index')} is {voice.get('status')!r}: {voice.get('message', voice.get('engine', 'unknown engine'))}.",
                    self.run / "render_report.json",
                    fix="Use a working voice engine before treating the video as upload-ready.",
                )

    def validate_video_file(self, path: Path, *, role: str) -> None:
        path = path.resolve()
        if path in self.video_cache:
            return
        if not path.exists():
            self.fail("video", "Video file is missing.", path)
            return
        if path.stat().st_size < 10_000:
            self.fail("video", "Video file is too small to be valid.", path)
            return
        if not self.ffprobe:
            self.fail("video.probe", "ffprobe is unavailable, so video metadata cannot be validated.", path, fix="Install FFmpeg.")
            return

        metadata = self.probe_video(path)
        self.video_cache[path] = metadata
        if not metadata:
            return

        duration = metadata.get("duration", 0.0)
        width = metadata.get("width")
        height = metadata.get("height")
        has_audio = bool(metadata.get("has_audio"))

        min_duration = MIN_FINAL_DURATION_SECONDS if role == "final" else MIN_ANY_VIDEO_DURATION_SECONDS
        if duration < min_duration:
            self.fail("video.duration", f"{role} video duration is only {duration:.2f}s.", path, fix="Render a complete scene, not a stub or failed output.")
        elif role == "final" and duration < 20:
            self.warn("video.duration", f"Final video is short ({duration:.1f}s); confirm the concept, example, and recall prompt all fit.", path)

        if width and height:
            if height <= width:
                self.fail("video.orientation", f"{role} video is not vertical ({width}x{height}).", path, fix="Render at a vertical 9:16 resolution.")
            elif abs((width / height) - TARGET_ASPECT_RATIO) > 0.08:
                self.warn("video.orientation", f"{role} video aspect ratio {width}:{height} is not close to 9:16.", path)
        else:
            self.fail("video.probe", "Video stream width/height could not be read.", path)

        if not has_audio:
            message = f"{role} video has no audio stream."
            fix = "Render with a working voice engine; silent files are drafts, not upload-ready videos."
            if role == "final" and not self.draft:
                self.fail("video.audio", message, path, fix=fix)
            else:
                self.warn("video.audio", message, path, fix=fix)

        self.analyze_video_frames(path, role=role)

    def probe_video(self, path: Path) -> dict[str, Any]:
        result = subprocess.run(
            [
                self.ffprobe or "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            self.fail("video.probe", f"ffprobe failed: {result.stderr.strip()[:240]}", path)
            return {}
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail("video.probe", "ffprobe returned invalid JSON.", path)
            return {}

        streams = payload.get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
        duration = parse_float(payload.get("format", {}).get("duration"))
        if duration <= 0:
            duration = parse_float(video_stream.get("duration"))
        return {
            "duration": duration,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "has_audio": bool(audio_streams),
        }

    def analyze_video_frames(self, path: Path, *, role: str) -> None:
        if not self.ffmpeg:
            self.warn("video.frames", "ffmpeg is unavailable, so blank/static frame checks were skipped.", path, fix="Install FFmpeg.")
            return
        metadata = self.video_cache.get(path.resolve(), {})
        duration = float(metadata.get("duration") or 0.0)
        if duration <= 0:
            return
        frame_count = min(8, max(4, int(math.ceil(duration / 20))))
        fps = frame_count / max(duration, 1.0)
        frame_size = 64 * 64
        result = subprocess.run(
            [
                self.ffmpeg,
                "-v",
                "error",
                "-i",
                str(path),
                "-vf",
                f"fps={fps:.6f},scale=64:64,format=gray",
                "-frames:v",
                str(frame_count),
                "-f",
                "rawvideo",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        if result.returncode != 0:
            self.warn("video.frames", f"Could not sample frames: {result.stderr.decode('utf-8', errors='replace')[:240]}", path)
            return

        raw = result.stdout
        frames = [raw[i : i + frame_size] for i in range(0, len(raw), frame_size) if len(raw[i : i + frame_size]) == frame_size]
        if len(frames) < 2:
            self.warn("video.frames", "Too few frames were sampled for blank/static checks.", path)
            return

        stats = [frame_stats(frame) for frame in frames]
        blank_flags = [(stdev < 2.0 and (mean < 30.0 or mean > 245.0)) for mean, stdev in stats]
        blank_ratio = sum(blank_flags) / len(blank_flags)
        if blank_ratio >= 0.75:
            self.fail("video.blank", f"{role} video appears blank in {blank_ratio:.0%} of sampled frames.", path, fix="Open the render and fix missing/hidden Manim objects or failed compositing.")
        elif blank_ratio >= 0.35:
            self.warn("video.blank", f"{role} video has many blank-looking sampled frames ({blank_ratio:.0%}).", path)

        diffs = [mean_abs_diff(frames[i - 1], frames[i]) for i in range(1, len(frames))]
        if diffs:
            low_motion_ratio = sum(diff < 1.2 for diff in diffs) / len(diffs)
            median_diff = statistics.median(diffs)
            if low_motion_ratio >= 0.8 or (median_diff < 1.0 and max(diffs) < 4.0):
                self.warn("video.static", f"{role} video looks static across sampled frames (median frame diff {median_diff:.2f}).", path, fix="Add meaningful animation or inspect for repeated still scenes.")

    def validate_publish_queue(self) -> None:
        queue_path = self.run / "instagram_publish_queue.json"
        if not queue_path.exists():
            return
        queue = self.load_json(queue_path, required=True)
        if not isinstance(queue, dict):
            self.fail("publish-queue", "instagram_publish_queue.json must be an object.", queue_path)
            return
        items = queue.get("items")
        if not isinstance(items, list) or not items:
            self.fail("publish-queue", "Publish queue has no items.", queue_path)
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            video_file = item.get("video_file")
            if not video_file:
                self.fail("publish-queue", f"Queue item {item.get('short_index')} has no video_file.", queue_path)
                continue
            video_path = self.run / str(video_file)
            if not video_path.exists():
                self.fail("publish-queue", f"Queue item {item.get('short_index')} points to a missing local video.", video_path)
            else:
                self.validate_video_file(video_path, role="final")
            if not item.get("video_url"):
                self.warn("publish-queue", f"Queue item {item.get('short_index')} has no public video_url for API publishing.", queue_path, fix="Host the MP4s and rerun queue with `--public-base-url`.")

    def check_nonempty(self, path: Path, area: str) -> None:
        if path.stat().st_size == 0:
            self.fail(area, "Artifact is empty.", path)


def strip_latex_comment(line: str) -> str:
    return re.split(r"(?<!\\)%", line, maxsplit=1)[0]


def latex_outside_display_segments(line: str, in_display_math: bool) -> tuple[list[str], bool]:
    segments: list[str] = []
    cursor = 0
    token_re = re.compile(r"(\\\[|\\\]|\\begin\{(?:equation|align|gather|multline)\*?\}|\\end\{(?:equation|align|gather|multline)\*?\})")
    for match in token_re.finditer(line):
        if not in_display_math and match.start() > cursor:
            segments.append(line[cursor:match.start()])
        token = match.group(0)
        if token.startswith(r"\[") or token.startswith(r"\begin"):
            in_display_math = True
        elif token.startswith(r"\]") or token.startswith(r"\end"):
            in_display_math = False
        cursor = match.end()
    if not in_display_math and cursor < len(line):
        segments.append(line[cursor:])
    return segments, in_display_math


def outside_math_segments(line: str) -> list[str]:
    parts = re.split(r"(?<!\\)\$", line)
    return parts[0::2]


def slugify(text: str, fallback: str = "course") -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or fallback


def first_int_match(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return int(match.group(1))


def parse_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_srt_cues(text: str) -> list[tuple[float, float]]:
    cues: list[tuple[float, float]] = []
    for match in re.finditer(r"(\d\d:\d\d:\d\d,\d{3})\s*-->\s*(\d\d:\d\d:\d\d,\d{3})", text):
        cues.append((srt_time_to_seconds(match.group(1)), srt_time_to_seconds(match.group(2))))
    return cues


def srt_time_to_seconds(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def normalize_scene_source(text: str) -> str:
    construct = re.search(r"\n    def construct\(self\):\n(?P<body>.*)", text, flags=re.S)
    if construct:
        text = construct.group("body")
    text = re.sub(r"#.*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def frame_stats(frame: bytes) -> tuple[float, float]:
    values = frame
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def mean_abs_diff(left: bytes, right: bytes) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / min(len(left), len(right))


def plan_shorts(plan: Any) -> list[dict[str, Any]]:
    if not isinstance(plan, dict):
        return []
    shorts = plan.get("shorts")
    if not isinstance(shorts, list):
        return []
    return [short for short in shorts if isinstance(short, dict)]


def print_human_report(run: Path, issues: list[Issue]) -> None:
    failures = [issue for issue in issues if issue.severity == "FAIL"]
    warnings = [issue for issue in issues if issue.severity == "WARN"]
    infos = [issue for issue in issues if issue.severity == "INFO"]
    status = "FAILED" if failures else "PASSED"
    print(f"Course run validation {status}: {run}")
    print(f"Summary: {len(failures)} failure(s), {len(warnings)} warning(s), {len(infos)} info item(s)")
    if not issues:
        print("No quality issues found.")
        return
    for issue in issues:
        location = f" {issue.path}" if issue.path else ""
        if issue.line:
            location += f":{issue.line}"
        print(f"\n{issue.severity} [{issue.area}]{location}")
        print(f"  {issue.message}")
        if issue.fix:
            print(f"  Fix: {issue.fix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate generated course notes, Manim scenes, captions, and videos.")
    parser.add_argument("run", help="Run directory, for example runs/<course>")
    parser.add_argument("--draft", action="store_true", help="Treat incomplete final render/audio checks as warnings instead of publish-readiness failures.")
    parser.add_argument("--allow-fallback-pdf", action="store_true", help="Warn instead of fail when notes.pdf was created by the PyMuPDF fallback.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of the human report.")
    args = parser.parse_args(argv)

    validator = CourseRunValidator(Path(args.run), draft=args.draft, allow_fallback_pdf=args.allow_fallback_pdf)
    issues = validator.validate()
    failures = [issue for issue in issues if issue.severity == "FAIL"]

    if args.json:
        print(json.dumps({"run": str(Path(args.run)), "status": "failed" if failures else "passed", "issues": [asdict(issue) for issue in issues]}, indent=2))
    else:
        print_human_report(Path(args.run), issues)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

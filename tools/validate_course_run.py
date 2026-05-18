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
GROUP_VISUAL_KINDS = {"group_structure", "group_cosets", "group_homomorphism", "group_action"}
ECON_VISUAL_KINDS = {"econ_supply_demand", "econ_elasticity", "econ_budget", "econ_curve", "econ_tax_wedge"}
GEOMETRY_VISUAL_KINDS = {"sphere_surface_area"}
REQUIRED_SYNC_FIELDS = ("raw_duration", "voice_duration", "target_duration", "final_duration", "video_time_scale")
NUMERIC_RULE_DOMAINS = ("algebra", "group", "econ", "economics", "micro")
GENERIC_VISUAL_TYPES = {"", "generic", "numeric_rule", "state_machine"}
VISUAL_TYPE_ALIASES: dict[str, set[str]] = {
    "markov": {"markov", "probability"},
    "projection": {"projection", "calculus_tangent"},
    "area": {"area", "calculus_area"},
    "quadratic": {"quadratic", "calculus_tangent"},
}
CONCEPT_VISUAL_FAMILIES: list[tuple[tuple[str, ...], set[str]]] = [
    (("coset",), {"group_cosets"}),
    (("homomorphism",), {"group_homomorphism"}),
    (("action", "orbit", "stabilizer"), {"group_action"}),
    (("group",), GROUP_VISUAL_KINDS),
    (("supply", "demand"), {"econ_supply_demand", "econ_tax_wedge"}),
    (("tax", "incidence", "deadweight", "wedge"), {"econ_tax_wedge"}),
    (("elasticity",), {"econ_elasticity", "econ_tax_wedge"}),
    (("budget",), {"econ_budget", "econ_curve"}),
    (("indifference", "curve"), {"econ_budget", "econ_curve", "econ_supply_demand"}),
]



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
        self.silent_final_allowed = False

    def validate(self) -> list[Issue]:
        if not self.run.exists():
            self.fail("run", "Run directory does not exist.", self.run, fix="Pass an existing runs/<course> directory.")
            return self.issues
        if not self.run.is_dir():
            self.fail("run", "Run path is not a directory.", self.run)
            return self.issues

        plan = self.load_json(self.run / "short_plan.json", required=False)
        self.validate_no_nested_run_artifacts()
        self.validate_source_pack()
        self.validate_notes()
        self.validate_short_plan(plan)
        self.validate_scene_script_caption_assets(plan)
        self.validate_videos(plan)
        self.validate_visual_frame_audit(plan)
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

    def validate_no_nested_run_artifacts(self) -> None:
        nested_markers = []
        for marker_name in ("short_plan.json", "render_report.json"):
            for marker in self.run.glob(f"**/{marker_name}"):
                if marker.parent == self.run:
                    continue
                nested_markers.append(marker)
        for marker in sorted(nested_markers):
            self.fail(
                "run.contamination",
                f"Nested run artifact `{marker.name}` found below this run directory.",
                marker,
                fix="Move nested runs outside this run directory before validating or publishing.",
            )

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
            self.scan_notes_comprehensiveness(tex)
            self.scan_notes_staleness(tex, require_figures=True)
        else:
            self.warn("notes", "notes.tex is missing; LaTeX formatting cannot be checked.", tex)

        if md.exists():
            self.check_nonempty(md, "notes")
            self.scan_markdown_quality(md)
            self.scan_notes_staleness(md, require_figures=False)
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
        self.scan_notes_compile_warnings(report, report_path)

    def scan_notes_staleness(self, path: Path, *, require_figures: bool) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        has_source_inventory = "source inventory" in lowered or "source-derived coverage checklist" in lowered
        checklist_count = len(re.findall(r"(?m)^\s*(?:[-*]|\\item)\s*\[[ xX]?\]", text))
        figure_count = len(re.findall(r"\\begin\{tikzpicture\}|\\includegraphics(?:\[[^\]]*\])?\{|!\[[^\]]*\]\(", text))
        if has_source_inventory or checklist_count >= 6:
            self.fail(
                "notes.stale-template",
                "Notes still look like a source inventory/checklist template rather than integrated course notes.",
                path,
                fix="Regenerate notes with the current comprehensive notes template.",
            )
        if figure_count == 0 and len(text) > 5000:
            if require_figures:
                self.fail(
                    "notes.stale-template",
                    "Notes contain no figures or embedded visuals; this matches stale low-quality note output.",
                    path,
                    fix="Regenerate notes with topic-specific figures enabled.",
                )
            else:
                self.warn(
                    "notes.markdown",
                    "Markdown notes have no embedded figures; TeX/PDF remains the canonical visual notes artifact.",
                    path,
                )

    def scan_notes_compile_warnings(self, report: dict[str, Any], report_path: Path) -> None:
        text = json.dumps(report, ensure_ascii=False)
        candidates = [self.run / "notes.log", self.run / "notes_compile.log"]
        for raw_path in (report.get("log_file"), report.get("log_path"), report.get("tex_log")):
            if isinstance(raw_path, str) and raw_path:
                candidates.append(self.run / raw_path)
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                text += "\n" + candidate.read_text(encoding="utf-8", errors="replace")
        warning_counts = report.get("warning_counts") if isinstance(report.get("warning_counts"), dict) else {}
        overfull = max(
            int(warning_counts.get("overfull_hboxes", 0) or 0),
            len(re.findall(r"Overfull \\hbox|Overfull \\vbox", text)),
        )
        underfull = max(
            int(warning_counts.get("underfull_hboxes", 0) or 0),
            len(re.findall(r"Underfull \\hbox|Underfull \\vbox", text)),
        )
        if overfull >= 8 or underfull >= 20 or (overfull + underfull) >= 24:
            self.warn(
                "notes.compile.layout",
                f"LaTeX reported {overfull} overfull and {underfull} underfull boxes.",
                report_path,
                fix="Inspect the notes compile log and simplify or reflow crowded equations, tables, and figures.",
            )

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


    def scan_notes_comprehensiveness(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        forbidden = ["Source Inventory", "Source-Derived Coverage Checklist", "source-derived coverage checklist"]
        for phrase in forbidden:
            if phrase in text:
                self.fail("notes.format", f"notes.tex still contains `{phrase}` instead of integrated course notes.", path, fix="Expand source-derived material into real topic notes; do not list sources or checklists.")
                break
        topic_count = len(re.findall(r"\\subsection\{", text))
        figure_count = len(re.findall(r"\\begin\{tikzpicture\}|\\includegraphics(?:\[[^\]]*\])?\{", text))
        if figure_count < max(4, min(12, topic_count // 4)):
            self.fail("notes.figures", f"notes.tex contains only {figure_count} embedded figure(s) for {topic_count} topic subsections.", path, fix="Generate topic-specific TikZ figures or include generated graphics directly in notes.tex/PDF.")
        if len(text) < 30_000:
            self.warn("notes.depth", f"notes.tex is compact ({len(text):,} characters); full-course notes may be too short.", path, fix="Add definitions, formulas, properties, examples, questions, and supplemental topics until the course is covered.")
        if topic_count < 12:
            self.warn("notes.depth", f"notes.tex has only {topic_count} topic subsections; broad courses should cover more of the course map.", path, fix="Generate notes from the full course topic library, not only the shorts queue.")

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
        try:
            import fitz  # type: ignore
            doc = fitz.open(path)
            page_count = doc.page_count
            doc.close()
            if page_count < 8:
                self.fail("notes.pdf", f"notes.pdf has only {page_count} pages; full-course notes are too short.", path, fix="Regenerate comprehensive notes from the full course topic set.")
            elif page_count < 20:
                self.warn("notes.pdf", f"notes.pdf has only {page_count} pages; verify it covers the whole course.", path)
        except Exception:
            pass

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
        scene_visuals: list[dict[str, Any]] = []
        domain_text = json.dumps(shorts, ensure_ascii=False).lower()
        for short in shorts:
            index = int(short.get("index", 0) or 0)
            concept = str(short.get("concept", f"short-{index}"))
            slug = slugify(concept)
            scene = self.run / str(short.get("scene_file") or f"scenes/short_{index:02d}_{slug}.py")
            caption = self.run / str(short.get("srt_file") or f"captions/short_{index:02d}_{slug}.srt")
            script = self.run / "scripts" / f"short_{index:02d}_{slug}.md"

            visual_kind = self.validate_scene(scene, index, normalized_sources)
            self.validate_planned_visual_type(short, visual_kind, scene)
            scene_visuals.append({"path": scene, "visual_kind": visual_kind, "concept": concept})
            self.validate_caption(caption, index, expected_duration=parse_float(short.get("target_duration_seconds")))
            self.validate_script(script, index)

        self.detect_repeated_scene_sources(normalized_sources)
        self.validate_scene_visual_quality(scene_visuals, domain_text)

    def validate_planned_visual_type(self, short: dict[str, Any], visual_kind: str, scene: Path) -> None:
        planned = str(short.get("visual_type") or "").strip().lower()
        actual = str(visual_kind or "").strip().lower()
        if planned in GENERIC_VISUAL_TYPES or not actual:
            return
        acceptable = VISUAL_TYPE_ALIASES.get(planned, {planned})
        if actual not in acceptable:
            index = short.get("index", "?")
            self.fail(
                "scene.visual-routing",
                f"Short {index} planned visual_type={planned!r}, but generated scene declares visual_kind={actual!r}.",
                scene,
                fix="Regenerate the scene or update visual-kind inference so the planned course-specific visual is honored.",
            )

    def scene_asset_stage_present(self, shorts: list[dict[str, Any]]) -> bool:
        if any((self.run / dirname).exists() for dirname in ("scenes", "scripts", "captions")):
            return True
        return any("scene_file" in short or "srt_file" in short or "class_name" in short for short in shorts)

    def validate_scene(self, path: Path, index: int, normalized_sources: list[tuple[Path, str]]) -> str:
        if not path.exists():
            self.fail("scene", f"Scene file for short {index:02d} is missing.", path, fix="Run `python tools/stem_course.py manim --run <run>` or restore the scene file.")
            return ""
        self.check_nonempty(path, "scene")
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            compile(text, str(path), "exec")
        except SyntaxError as exc:
            self.fail("scene", f"Scene Python has a syntax error: {exc.msg}.", path, line=exc.lineno, fix="Repair the Manim scene before rendering.")
            return ""

        if re.search(r"\b(?:setup|calc|question|answer)_lines\s*=\s*\[[^\n]*\[\s*\[", text):
            self.fail(
                "scene.layout",
                "Scene-facing text contains matrix/Python list notation, which usually renders as an unreadable single-line label.",
                path,
                fix="Sanitize narration/screen text and show matrices through a visual matrix object or MathTex bmatrix.",
            )
        if "avoid_layout_collisions" not in text or "safe_place" not in text:
            self.fail("scene.layout-helper", "Scene is missing the collision-aware safe placement helper.", path, fix="Regenerate Manim scenes after updating the course-manim skill.")
        if "avoid_layout_collisions" not in text:
            self.fail("scene.stale-template", "Scene source is missing the current avoid_layout_collisions marker.", path, fix="Regenerate Manim scenes with the current template.")
        if "Active recall" in text:
            self.fail("scene.structure", "Scene still contains an active recall section.", path, fix="Regenerate Manim scenes with the current concept-plus-example video template.")

        visual_match = re.search(r"visual_kind\s*=\s*['\"]([^'\"]+)['\"]", text)
        visual_kind = visual_match.group(1) if visual_match else ""
        if visual_kind in GROUP_VISUAL_KINDS and "def play_group_visual" not in text:
            self.fail("scene.visual", f"Group-theory visual `{visual_kind}` falls through without a domain-specific group renderer.", path, fix="Regenerate scenes after updating the Manim skill helpers.")
        if visual_kind in ECON_VISUAL_KINDS and "def play_econ_visual" not in text:
            self.fail("scene.visual", f"Economics visual `{visual_kind}` falls through without a domain-specific economics renderer.", path, fix="Regenerate scenes after updating the Manim skill helpers.")
        if visual_kind in GEOMETRY_VISUAL_KINDS and "def play_sphere_surface_area_visual" not in text:
            self.fail("scene.visual", f"Geometry visual `{visual_kind}` falls through without its proof-style renderer.", path, fix="Regenerate scenes after updating the Manim skill helpers.")

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
        return visual_kind

    def validate_scene_visual_quality(self, scene_visuals: list[dict[str, Any]], domain_text: str) -> None:
        if not scene_visuals:
            return
        kinds = [str(item.get("visual_kind") or "") for item in scene_visuals]
        known = [kind for kind in kinds if kind]
        if not known:
            self.warn("scene.visual-quality", "No scene source declares visual_kind; visual variety cannot be audited.", self.run / "scenes")
            return
        total = len(scene_visuals)
        numeric_count = sum(1 for kind in kinds if kind == "numeric_rule")
        domain_needs_specifics = any(token in domain_text for token in NUMERIC_RULE_DOMAINS)
        if domain_needs_specifics:
            numeric_ratio = numeric_count / total
            if numeric_count >= 3 and numeric_ratio > 0.35:
                self.fail(
                    "scene.visual-quality",
                    f"{numeric_count}/{total} scenes use generic visual_kind='numeric_rule' in a domain that needs concept-specific visuals.",
                    self.run / "scenes",
                    fix="Use group/economics/algebra visual families instead of generic numeric-rule scenes.",
                )
            elif numeric_count >= 2:
                self.warn(
                    "scene.visual-quality",
                    f"{numeric_count}/{total} scenes use generic visual_kind='numeric_rule'.",
                    self.run / "scenes",
                    fix="Prefer concept-specific visual families for repeated domain concepts.",
                )
        counts = {kind: kinds.count(kind) for kind in set(known)}
        dominant_kind, dominant_count = max(counts.items(), key=lambda item: (item[1], item[0]))
        dominant_ratio = dominant_count / total
        if total >= 4 and dominant_count >= 4 and dominant_ratio >= 0.65:
            severity = self.fail if dominant_kind == "numeric_rule" or dominant_ratio >= 0.8 else self.warn
            severity(
                "scene.visual-quality",
                f"{dominant_count}/{total} scenes repeat visual_kind={dominant_kind!r}.",
                self.run / "scenes",
                fix="Vary visual_kind across the run so the videos do not feel templated.",
            )
        for item in scene_visuals:
            concept_text = str(item.get("concept") or "").lower()
            visual_kind = str(item.get("visual_kind") or "")
            for tokens, expected in CONCEPT_VISUAL_FAMILIES:
                if any(token in concept_text for token in tokens) and visual_kind not in expected:
                    self.warn(
                        "scene.visual-family",
                        f"Concept {item.get('concept')!r} uses visual_kind={visual_kind!r}, not one of {sorted(expected)}.",
                        item.get("path") if isinstance(item.get("path"), Path) else self.run / "scenes",
                        fix="Regenerate or edit the scene to use the concept-specific visual family.",
                    )
                    break

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

    def validate_caption(self, path: Path, index: int, *, expected_duration: float = 0.0) -> None:
        if not path.exists():
            self.fail("caption", f"SRT caption for short {index:02d} is missing.", path)
            return
        self.check_nonempty(path, "caption")
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\b(Active recall|Recognition cue|Common trap|Try this|Answer:)\b", text):
            self.fail("caption.structure", "Caption file still contains active-recall wording.", path, fix="Regenerate captions with the current concept-plus-example timing model.")
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
        if total < 24:
            self.warn("caption", f"SRT caption for short {index:02d} is only {total:.1f}s long.", path)
        if expected_duration > 0 and abs(total - expected_duration) > max(3.0, expected_duration * 0.12):
            self.fail("caption.sync", f"SRT length {total:.1f}s does not match planned/render target {expected_duration:.1f}s.", path, fix="Regenerate captions from script-paced timing or rerun render so captions are stretched to the final duration.")

    def validate_script(self, path: Path, index: int) -> None:
        if not path.exists():
            self.fail("script", f"Script markdown for short {index:02d} is missing.", path)
            return
        self.check_nonempty(path, "script")
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\b(Active recall|Recognition cue|Common trap|Try this|recall question)\b", text):
            self.fail("script.structure", "Script still contains active-recall wording.", path, fix="Regenerate scripts with the current concept-plus-example timing model.")
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
        render_report = self.load_json(self.run / "render_report.json", required=False)
        self.silent_final_allowed = self.render_report_allows_silent(render_report)

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

        if render_report is not None:
            self.validate_render_report(render_report)

    def render_report_allows_silent(self, report: Any) -> bool:
        if not isinstance(report, dict):
            return False
        results = report.get("results")
        if not isinstance(results, list):
            return False
        for result in results:
            if not isinstance(result, dict):
                continue
            voice = result.get("voiceover")
            if isinstance(voice, dict) and (voice.get("status") == "skipped" or voice.get("engine") == "none"):
                return True
        return False

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
                target = parse_float(short.get("target_duration_seconds"))
                metadata = self.video_cache.get(expected_final.resolve(), {})
                duration = float(metadata.get("duration") or 0.0)
                if target > 0 and duration > 0 and duration + 1.0 < target:
                    self.fail("video.sync", f"Final MP4 is {duration:.1f}s, shorter than the planned/audio target {target:.1f}s.", expected_final, fix="Do not use ffmpeg -shortest; pad video/audio and mux to the longest stream.")

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
            if isinstance(voice, dict) and voice.get("status") not in {"ok", "skipped", None}:
                severity = self.warn if self.draft else self.fail
                severity(
                    "render-report.audio",
                    f"Voiceover for short {result.get('index')} is {voice.get('status')!r}: {voice.get('message', voice.get('engine', 'unknown engine'))}.",
                    self.run / "render_report.json",
                    fix="Use a working voice engine or render intentionally with --voice-engine none.",
                )
            sync = result.get("sync")
            if isinstance(voice, dict) and voice.get("status") == "ok":
                if not isinstance(sync, dict):
                    self.fail(
                        "render-report.sync",
                        f"Voiceover for short {result.get('index')} is ok, but no sync object was recorded.",
                        self.run / "render_report.json",
                        fix="Record raw_duration, voice_duration, target_duration, final_duration, and video_time_scale in render_report.json.",
                    )
                    continue
                missing_sync = [field for field in REQUIRED_SYNC_FIELDS if field not in sync]
                if missing_sync:
                    self.fail(
                        "render-report.sync",
                        f"Voiceover for short {result.get('index')} is ok, but sync is missing {', '.join(missing_sync)}.",
                        self.run / "render_report.json",
                        fix="Regenerate render_report.json with complete sync provenance.",
                    )
            if isinstance(sync, dict):
                raw = parse_float(sync.get("raw_duration"))
                voice_dur = parse_float(sync.get("voice_duration"))
                final = parse_float(sync.get("final_duration", result.get("duration_seconds")))
                target = parse_float(sync.get("target_duration")) or (voice_dur + 0.35 if voice_dur > 0 else max(raw, voice_dur))
                if voice_dur > 0 and final + 0.75 < target:
                    self.fail("render-report.sync", f"Final video {final:.1f}s is shorter than the voice-aligned target {target:.1f}s.", self.run / "render_report.json", fix="Generate voice first, pace Manim to that duration, then mux without `-shortest`.")
                if voice_dur > 0 and abs(final - (voice_dur + 0.35)) > max(1.2, voice_dur * 0.06):
                    self.fail("render-report.sync", f"Final video {final:.1f}s is not aligned to voiceover length {voice_dur:.1f}s.", self.run / "render_report.json", fix="Time-scale the rendered video to the narration duration before padding the short tail.")
                if raw > 0 and voice_dur > 0 and abs(raw - voice_dur) > 1.0 and parse_float(sync.get("video_time_scale")) == 1.0 and parse_float(sync.get("video_pad_seconds")) <= 0:
                    self.fail("render-report.sync", "Raw Manim duration and voiceover duration differ, but no time scaling or padding was recorded.", self.run / "render_report.json", fix="Use the voice-first render flow and record video_time_scale in render_report.json.")

    def validate_visual_frame_audit(self, plan: Any) -> None:
        final_videos = sorted((self.run / "videos").glob("*_final.mp4"))
        if not final_videos and not self.render_outputs_expected(plan_shorts(plan)):
            return

        report_path = self.run / "visual_frame_audit.json"
        if not report_path.exists():
            self.warn(
                "visual-audit",
                "visual_frame_audit.json is missing, so overlap/crowding contact-sheet review is not recorded.",
                report_path,
                fix="Run `python tools/audit_video_frames.py <run>` after rendering and inspect the contact sheets.",
            )
            return

        report = self.load_json(report_path, required=True)
        if not isinstance(report, dict):
            self.fail("visual-audit", "visual_frame_audit.json must be an object.", report_path)
            return
        videos = report.get("videos")
        if not isinstance(videos, list) or not videos:
            self.fail("visual-audit", "visual_frame_audit.json has no videos array.", report_path)
            return

        audited: set[str] = set()
        for item in videos:
            if not isinstance(item, dict):
                self.fail("visual-audit", "Visual audit video entry must be an object.", report_path)
                continue
            video_rel = str(item.get("video") or "")
            if video_rel:
                audited.add(video_rel)
            contact_rel = str(item.get("contact_sheet") or "")
            if contact_rel and not (self.run / contact_rel).exists():
                self.fail("visual-audit", f"Contact sheet is missing for {video_rel or 'a video'}.", self.run / contact_rel)
            elif not contact_rel:
                self.fail("visual-audit", f"No contact sheet recorded for {video_rel or 'a video'}.", report_path)

            metrics = item.get("metrics")
            if not isinstance(metrics, dict):
                self.fail("visual-audit", f"No frame metrics recorded for {video_rel or 'a video'}.", report_path)
                continue
            sampled = int(parse_float(metrics.get("sampled_frames")))
            if sampled < 3:
                self.warn("visual-audit", f"Only {sampled} frame(s) sampled for {video_rel or 'a video'}.", report_path)
            flags = metrics.get("review_flags")
            if isinstance(flags, list) and flags:
                self.fail(
                    "visual-audit",
                    f"Frame audit flagged {video_rel or 'a video'} for {', '.join(str(flag) for flag in flags)}.",
                    report_path,
                    fix="Open the contact sheet, patch the relevant visual family, rerender, and rerun `tools/audit_video_frames.py`.",
                )

        for final in final_videos:
            try:
                rel = str(final.relative_to(self.run))
            except ValueError:
                rel = str(final)
            if rel not in audited:
                self.warn("visual-audit", f"Final video {final.name} is not represented in visual_frame_audit.json.", report_path)

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
        elif role == "final" and duration < 24:
            self.warn("video.duration", f"Final video is short ({duration:.1f}s); confirm the concept, example, and recall prompt all fit.", path)

        if width and height:
            if height <= width:
                self.fail("video.orientation", f"{role} video is not vertical ({width}x{height}).", path, fix="Render at a vertical 9:16 resolution.")
            elif abs((width / height) - TARGET_ASPECT_RATIO) > 0.08:
                self.warn("video.orientation", f"{role} video aspect ratio {width}:{height} is not close to 9:16.", path)
        else:
            self.fail("video.probe", "Video stream width/height could not be read.", path)

        if not has_audio and role == "final" and not self.silent_final_allowed:
            message = f"{role} video has no audio stream."
            fix = "Render with a working voice engine, or render intentionally with --voice-engine none so the report marks silence as expected."
            if not self.draft:
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
            status = str(item.get("status") or "").lower()
            if not video_path.exists():
                if status == "ready":
                    self.fail("publish-queue", f"Queue item {item.get('short_index')} is marked ready but its local final video is missing.", video_path)
                else:
                    self.warn("publish-queue", f"Queue item {item.get('short_index')} points to a missing local video.", video_path)
            else:
                self.validate_video_file(video_path, role="final")
            if status == "ready" and not item.get("video_url"):
                self.warn("publish-queue", f"Queue item {item.get('short_index')} is locally ready but has no public video_url for API publishing.", queue_path, fix="Host the MP4s and rerun queue with `--public-base-url`.")
            elif not item.get("video_url"):
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
    # Strip LaTeX inline math before scanning prose. The validator checks for
    # bare caret/sqrt leaks outside math mode, so valid \(x^{2}\) spans
    # should not be reported.
    line = re.sub(r"\\\([^\n]*?\\\)", "", line)
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

#!/usr/bin/env python3
"""Validate generated course notes, Manim assets, captions, and videos.

The validator is intentionally topic-agnostic: it checks the quality signals
that matter before upload without depending on a particular STEM subject.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
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

try:
    from tools import stem_course as stem_course_contract
except ModuleNotFoundError:  # Direct `python tools/validate_course_run.py` execution.
    import stem_course as stem_course_contract


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}
MIN_FINAL_DURATION_SECONDS = 10.0
MIN_ANY_VIDEO_DURATION_SECONDS = 3.0
MIN_FINAL_FRAME_RATE = 29.0
FINAL_VIDEO_WIDTH = 1080
FINAL_VIDEO_HEIGHT = 1920
TARGET_ASPECT_RATIO = 9 / 16
GROUP_VISUAL_KINDS = {"group_structure", "group_cosets", "group_homomorphism", "group_action"}
ECON_VISUAL_KINDS = {"econ_supply_demand", "econ_elasticity", "econ_budget", "econ_curve", "econ_tax_wedge"}
GEOMETRY_VISUAL_KINDS = {"sphere_surface_area"}
REQUIRED_SYNC_FIELDS = ("raw_duration", "voice_duration", "target_duration", "final_duration", "video_time_scale")
PIPER_SAMPLE_RATE = 48_000
PIPER_CHANNELS = 1
MAX_BEAT_BOUNDARY_ERROR_SECONDS = 0.100
MAX_CUMULATIVE_DRIFT_SECONDS = 0.150
MAX_MEANINGFUL_EXTENSION_SECONDS = 0.050
MAX_SAMPLE_PEAK_DBFS = -0.1
MAX_TRUE_PEAK_DBFS = -1.0
MIN_INTEGRATED_LUFS = -24.0
MAX_INTEGRATED_LUFS = -12.0
NUMERIC_RULE_DOMAINS = ("algebra", "group", "econ", "economics", "micro")
GENERIC_VISUAL_TYPES = {"", "generic", "numeric_rule"}
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
SERIOUS_VISUAL_AUDIT_FLAGS = {
    "blank_frames",
    "underused_frames",
    "prolonged_static_holds",
    "low_visual_change",
    "insufficient_motion_coverage",
    "extreme_layout_imbalance",
    "rendered_text_outside_safe_area",
    "rendered_text_overlap",
    "rendered_text_too_small",
    "suspected_run_together_text",
}
ANIMATION_PLAN_SCHEMA_VERSION = stem_course_contract.ANIMATION_PLAN_SCHEMA_VERSION
ANIMATION_PLAN_INDEX_NAME = stem_course_contract.ANIMATION_PLAN_INDEX_NAME
ANIMATION_PLAN_DIRECTORY = stem_course_contract.ANIMATION_PLAN_DIRECTORY
ANIMATION_PLAN_MIN_BEATS = stem_course_contract.ANIMATION_PLAN_MIN_BEATS
ANIMATION_PLAN_MAX_BEATS = stem_course_contract.ANIMATION_PLAN_MAX_BEATS
ANIMATION_PLAN_MIN_TRANSFORMATIONS = stem_course_contract.ANIMATION_PLAN_MIN_TRANSFORMATIONS
ANIMATION_PLAN_MIN_OBJECT_ACTIVE_RATIO = stem_course_contract.ANIMATION_PLAN_MIN_OBJECT_ACTIVE_RATIO
SCENE_METADATA_VERSION = stem_course_contract.SCENE_METADATA_VERSION
VISUAL_REVIEW_SCHEMA_VERSION = stem_course_contract.VISUAL_REVIEW_SCHEMA_VERSION
VISUAL_REVIEW_NAME = stem_course_contract.VISUAL_REVIEW_NAME
RENDER_RUNTIME_TRACE_SCHEMA_VERSION = "course-render-runtime-trace-v1"
RENDER_RUNTIME_TRACE_NAME = "render_runtime_trace.json"
MAX_CONTACT_SHEET_INTERVAL_SECONDS = 0.5
VISUAL_REVIEW_CHECKPOINT_ROLES = {"opening", "pre_action", "post_action", "intermediate", "final"}
STATE_CHANGE_ATTRIBUTE = "state"
ANIMATION_SOURCE_FIELDS = stem_course_contract.ANIMATION_SOURCE_FIELDS
ANIMATION_SUPPORTED_VISUAL_KINDS = set(stem_course_contract.ANIMATION_SUPPORTED_VISUAL_KINDS)
PDF_TITLE_PAGE_NUMBER = 1
PDF_USABLE_BODY_MARGIN_RATIO = 0.07
PDF_MAX_FIGURE_BLANK_RUN_RATIO = 0.60
PDF_MIN_TRAILING_BLANK_BEFORE_FIGURE_RATIO = 0.35
PDF_FIGURE_BLOCK_START_RATIO = 0.25
PDF_SECTION_HEADING_MIN_FONT_SIZE = 13.0
PDF_MIN_TEXT_INTERSECTION_WIDTH = 1.0
PDF_MIN_TEXT_INTERSECTION_HEIGHT = 1.0
PDF_MIN_TEXT_INTERSECTION_AREA = 8.0
PDF_FIGURE_REGION_PADDING_POINTS = 12.0
PDF_FIGURE_CLUSTER_GAP_POINTS = 24.0
PDF_FIGURE_CAPTION_MAX_GAP_POINTS = 96.0
PDF_FIGURE_CAPTION_PATTERN = re.compile(r"^Figure\s+(\d+)\s*:")
PDF_FIGURE_REFERENCE_PATTERN = re.compile(r"\bFigure\s+\d+\b", flags=re.IGNORECASE)
PDF_UNNUMBERED_FIGURE_DISCUSSION_PATTERN = re.compile(
    r"\b(?:the|this|that|preceding|following|above|below)\s+figure\b",
    flags=re.IGNORECASE,
)
PDF_MIN_BODY_OCCUPANCY_RATIO = 0.18
PDF_MAX_TRAILING_BLANK_RATIO = 0.55
PDF_TEX_DELIMITER_PATTERN = re.compile(r"^[!()\[\]{}|\u2016\u2308\u2309\u230a\u230b]+$")

COURSE_COVERAGE_STOP_WORDS = {
    "a", "an", "and", "application", "applications", "chapter", "choice", "course",
    "for", "from", "i", "ii", "iii", "in", "introduction", "law", "laws", "lesson",
    "distinct", "module", "of", "over", "part", "principle", "principles", "process", "the", "theory",
    "to", "topic", "unit", "using",
}


def concept_signature(value: object) -> set[str]:
    """Normalize a course heading while retaining its domain-bearing vocabulary."""
    words = re.findall(r"[a-z0-9]+", str(value).lower().replace("1d", "one dimensional").replace("2d", "two dimensional").replace("3d", "three dimensional"))
    signature: set[str] = set()
    for word in words:
        if word in COURSE_COVERAGE_STOP_WORDS or word.isdigit() or len(word) < 3:
            continue
        if word.endswith("ies") and len(word) > 5:
            word = word[:-3] + "y"
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 4:
            word = word[:-1]
        signature.add(word)
    return signature


def concepts_semantically_overlap(course_unit: object, video_concept: object) -> bool:
    """Allow a broader video concept to represent one or several related course units."""
    unit = concept_signature(course_unit)
    video = concept_signature(video_concept)
    if not unit or not video:
        return False
    shared = unit & video
    if not shared:
        return False
    smaller_coverage = len(shared) / min(len(unit), len(video))
    unit_coverage = len(shared) / len(unit)
    return smaller_coverage >= 0.67 or (len(shared) >= 2 and unit_coverage >= 0.5)


def semantic_course_coverage(course_units: list[object], video_concepts: list[object]) -> dict[str, Any]:
    """Measure concept coverage without imposing one video per notes chapter."""
    units = [str(value).strip() for value in course_units if str(value).strip()]
    concepts = [str(value).strip() for value in video_concepts if str(value).strip()]
    rows: list[dict[str, Any]] = []
    for unit in units:
        matches = [concept for concept in concepts if concepts_semantically_overlap(unit, concept)]
        rows.append({"course_unit": unit, "matched_video_concepts": matches, "status": "covered" if matches else "uncovered"})

    missing_indexes = [index for index, row in enumerate(rows) if row["status"] == "uncovered"]
    longest_run = 0
    current_run = 0
    previous = -2
    for index in missing_indexes:
        current_run = current_run + 1 if index == previous + 1 else 1
        longest_run = max(longest_run, current_run)
        previous = index
    missing_count = len(missing_indexes)
    material_limit = max(2, math.ceil(len(rows) * 0.15)) if rows else 0
    materially_uncovered = bool(rows) and (missing_count >= material_limit or longest_run >= 3)
    return {
        "status": "failed" if materially_uncovered else "ok",
        "course_unit_count": len(rows),
        "covered_course_unit_count": len(rows) - missing_count,
        "uncovered_course_unit_count": missing_count,
        "material_uncovered_limit": material_limit,
        "longest_uncovered_run": longest_run,
        "units": rows,
    }



@dataclass
class Issue:
    severity: str
    area: str
    message: str
    path: str | None = None
    line: int | None = None
    fix: str | None = None


def canonical_json_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


SEMANTIC_IDENTITY_MIN_TRANSITIONS = 4
SEMANTIC_EXEMPTION_INTENTS = {
    "alternate",
    "derived",
    "intentional_alternate",
    "intentional_derived",
}
SEMANTIC_TRUNCATION_END_WORDS = {
    "an", "and", "as", "before", "between", "by", "for", "from",
    "in", "into", "is", "of", "on", "or", "than", "that", "the", "then", "to",
    "when", "where", "while", "with",
}


def _semantic_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _semantic_strings(value: object) -> str:
    """Flatten evidence without allowing metadata keys to prove their own presence."""
    if isinstance(value, dict):
        return " ".join(_semantic_strings(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_semantic_strings(item) for item in value)
    return str(value) if value is not None else ""


def _semantic_token_text(value: object) -> str:
    text = str(value).replace("_", " ").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _semantic_token_present(token: object, evidence: object) -> bool:
    needle = _semantic_token_text(token)
    haystack = _semantic_token_text(_semantic_strings(evidence))
    if not needle:
        return False
    alternatives = [part.strip() for part in re.split(r"\s+(?:or|and/or)\s+|/", needle) if part.strip()]
    if len(alternatives) > 1:
        return any(f" {part} " in f" {haystack} " for part in alternatives)
    return f" {needle} " in f" {haystack} "


def _semantic_numeric_tokens(value: object) -> set[str]:
    text = _semantic_strings(value)
    tokens: set[str] = set()
    for match in re.finditer(r"(?<![A-Za-z0-9_.^])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?![A-Za-z0-9_.])", text):
        try:
            number = float(match.group(0))
        except ValueError:
            continue
        if not math.isfinite(number):
            continue
        tokens.add("0" if number == 0 else format(number, ".12g"))
    return tokens


def _semantic_numeric_leaf_tokens(value: object) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            tokens.update(_semantic_numeric_leaf_tokens(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            tokens.update(_semantic_numeric_leaf_tokens(item))
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        number = float(value)
        tokens.add("0" if number == 0 else format(number, ".12g"))
    elif isinstance(value, str):
        tokens.update(_semantic_numeric_tokens(value))
    return tokens


def _canonical_semantic_numeric_evidence(value: object) -> object | None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("numeric evidence contains a non-finite value")
        return 0.0 if number == 0 else number
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key in sorted(value, key=str):
            canonical = _canonical_semantic_numeric_evidence(value[key])
            if canonical is not None:
                result[str(key)] = canonical
        return result
    if isinstance(value, (list, tuple)):
        return [_canonical_semantic_numeric_evidence(item) for item in value]
    raise TypeError(f"numeric evidence contains unsupported value {value!r}")


def semantic_numeric_evidence_fingerprint(scenario: dict[str, Any]) -> str:
    """Hash a scenario's typed setup/calculation/result numeric evidence."""
    if not isinstance(scenario, dict):
        raise TypeError("scenario must be an object")
    result = scenario.get("result", scenario.get("results"))
    if not isinstance(scenario.get("setup"), dict) or not isinstance(scenario.get("calculation"), dict) or not isinstance(result, dict):
        raise ValueError("scenario must contain object-valued setup, calculation, and result")
    evidence = {
        "setup": _canonical_semantic_numeric_evidence(scenario["setup"]),
        "calculation": _canonical_semantic_numeric_evidence(scenario["calculation"]),
        "result": _canonical_semantic_numeric_evidence(result),
    }
    serialized = json.dumps(evidence, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode("ascii")).hexdigest()


def _semantic_named_variables(value: object) -> set[str]:
    text = str(value)
    variables: set[str] = set()
    assignment_pattern = r"(?<![A-Za-z0-9])([A-Za-z](?:[A-Za-z0-9]*|_\{?[A-Za-z0-9]+\}?))\s*="
    for match in re.finditer(assignment_pattern, text):
        variable = re.sub(r"[^A-Za-z0-9]+", "", match.group(1)).casefold()
        if variable:
            variables.add(variable)
    return variables


def _semantic_variable_corpus(value: object) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            segments = [segment.casefold() for segment in re.findall(r"[A-Za-z0-9]+", str(key)) if segment]
            normalized = "".join(segments)
            if normalized:
                tokens.add(normalized)
            tokens.update(_semantic_variable_corpus(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            tokens.update(_semantic_variable_corpus(item))
    elif isinstance(value, str):
        tokens.update(
            re.sub(r"[^A-Za-z0-9]+", "", token).casefold()
            for token in re.findall(r"[A-Za-z](?:[A-Za-z0-9]*|_\{?[A-Za-z0-9]+\}?)", value)
        )
    return {token for token in tokens if token}


def _semantic_exemption_rows(short: dict[str, Any], artifact: dict[str, Any]) -> list[object]:
    rows: list[object] = []
    renderer = _semantic_mapping(_semantic_mapping(artifact.get("concrete_example")).get("renderer_state"))
    for container in (short, artifact, _semantic_mapping(artifact.get("semantic_support")), renderer):
        for key in ("semantic_identity_exemptions", "numeric_evidence_exemptions"):
            value = container.get(key)
            if isinstance(value, list):
                rows.extend(value)
        identity = _semantic_mapping(container.get("semantic_identity"))
        if isinstance(identity.get("exemptions"), list):
            rows.extend(identity["exemptions"])
    return rows


def _validated_semantic_exemptions(
    short: dict[str, Any], artifact: dict[str, Any]
) -> tuple[set[tuple[str, str, str]], list[str]]:
    accepted: set[tuple[str, str, str]] = set()
    errors: list[str] = []
    for position, row in enumerate(_semantic_exemption_rows(short, artifact), start=1):
        if not isinstance(row, dict):
            errors.append(f"semantic identity exemption {position} is not an object")
            continue
        kind = str(row.get("kind") or row.get("evidence_kind") or "").strip().casefold()
        raw_value = row.get("value", row.get("token", row.get("variable", row.get("numeric_value"))))
        value = str(raw_value).strip().casefold() if raw_value is not None else ""
        intent = str(row.get("intent") or row.get("value_kind") or row.get("reason_type") or "").strip().casefold()
        reason = str(row.get("reason") or row.get("justification") or "").strip()
        artifacts = row.get("artifacts", row.get("applies_to"))
        if (
            kind not in {"numeric", "numeric_value", "named_variable", "variable"}
            or not value
            or intent not in SEMANTIC_EXEMPTION_INTENTS
            or len(reason) < 8
            or not isinstance(artifacts, list)
            or not artifacts
            or any(not str(item).strip() for item in artifacts)
        ):
            errors.append(
                f"semantic identity exemption {position} must declare kind/value, derived-or-alternate intent, "
                "a specific reason, and target artifacts"
            )
            continue
        canonical_kind = "numeric" if kind in {"numeric", "numeric_value"} else "variable"
        if canonical_kind == "numeric":
            try:
                number = float(value)
                value = "0" if number == 0 else format(number, ".12g")
            except ValueError:
                errors.append(f"semantic identity exemption {position} has a non-numeric numeric value {value!r}")
                continue
        for target in artifacts:
            accepted.add((canonical_kind, value, str(target).strip().casefold()))
    return accepted, errors


def _semantic_is_exempt(
    exemptions: set[tuple[str, str, str]], kind: str, value: str, artifact: str
) -> bool:
    target = artifact.casefold()
    return any(
        (kind, value.casefold(), candidate) in exemptions
        for candidate in (target, "*", "all")
    )


def _semantic_visible_storyboard(artifact: dict[str, Any]) -> dict[str, Any]:
    concrete = _semantic_mapping(artifact.get("concrete_example"))
    renderer = _semantic_mapping(concrete.get("renderer_state"))
    equation_evidence = {
        key: value
        for key, value in renderer.items()
        if any(marker in str(key).casefold() for marker in ("formula", "equation", "symbol_evidence"))
    }
    visible_states = []
    states = renderer.get("animation_states")
    if isinstance(states, list):
        visible_states = [
            state
            for state in states
            if isinstance(state, dict)
            and any(state.get(key) for key in ("visible_tokens", "visible_evidence_tokens", "visible_object_ids"))
        ]
    beats: list[dict[str, Any]] = []
    for beat in artifact.get("beats", []) if isinstance(artifact.get("beats"), list) else []:
        if not isinstance(beat, dict):
            continue
        beats.append(
            {
                key: beat.get(key)
                for key in ("text", "cue_lines", "action", "claim", "start_state", "end_state", "state_delta", "evidence")
            }
        )
    return {
        "concrete_example": {key: concrete.get(key) for key in ("setup", "calculation", "takeaway", "screen_values")},
        "beats": beats,
        "semantic_transition_contract": artifact.get("semantic_transition_contract"),
        "invariant": artifact.get("invariant"),
        "reveal": artifact.get("reveal"),
        "renderer_equation_evidence": equation_evidence,
        "visible_renderer_states": visible_states,
    }


def _semantic_declared_tokens(containers: list[dict[str, Any]], *, forbidden: bool) -> list[str]:
    names = (
        ("forbidden_tokens", "forbidden_cross_family_tokens", "forbidden_mechanism_tokens")
        if forbidden
        else ("required_tokens", "required_mechanism_tokens")
    )
    tokens: list[str] = []
    for container in containers:
        vocabulary = _semantic_mapping(container.get("mechanism_vocabulary"))
        route_metadata = _semantic_mapping(container.get("route_metadata"))
        for source in (container, vocabulary, route_metadata):
            for name in names:
                value = source.get(name)
                if isinstance(value, list):
                    tokens.extend(str(item).strip() for item in value if str(item).strip())
    return list(dict.fromkeys(tokens))


def _semantic_required_tokens(containers: list[dict[str, Any]], name: str) -> list[str]:
    tokens: list[str] = []
    for container in containers:
        value = container.get(name)
        if isinstance(value, list):
            tokens.extend(str(item).strip() for item in value if str(item).strip())
    return list(dict.fromkeys(tokens))


def _unbalanced_delimiter(text: str) -> str | None:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    escaped = False
    for character in text:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in "([{":
            stack.append(character)
        elif character in pairs:
            if not stack or stack.pop() != pairs[character]:
                return character
    if stack:
        return stack[-1]
    bars = re.sub(r"\\mid\b", "", text)
    bars = bars.replace(r"\lvert", "|").replace(r"\rvert", "|").replace(r"\vert", "|")
    bars = re.sub(r"(?<!\\)\|\|", "", bars)
    absolute_bar_open = False
    for match in re.finditer(r"(?<!\\)\|", bars):
        position = match.start()
        left = bars[position - 1] if position else ""
        right = bars[position + 1] if position + 1 < len(bars) else ""
        if absolute_bar_open:
            absolute_bar_open = False
        elif right and not right.isspace() and (not left or left.isspace() or left in "=+*/<>^_([{,:;"):
            absolute_bar_open = True
        # All other bars are binary relations or set/presentation separators.
    return "|" if absolute_bar_open else None


def _strip_tex_prose_macros(formula: str) -> str:
    """Remove prose-only TeX arguments before formula structure comparison."""
    text = formula
    pattern = re.compile(r"\\(?:text|textrm|textsf|texttt)\s*\{")
    while True:
        match = pattern.search(text)
        if match is None:
            return text
        depth = 1
        position = match.end()
        while position < len(text) and depth:
            if text[position] == "{" and (position == 0 or text[position - 1] != "\\"):
                depth += 1
            elif text[position] == "}" and (position == 0 or text[position - 1] != "\\"):
                depth -= 1
            position += 1
        prefix = text[:match.start()].rstrip()
        if prefix.endswith((",", ";")):
            prefix = prefix[:-1]
        text = prefix + (" " if depth == 0 else text[match.start():]) + text[position:]
        if depth:
            return text


def _canonical_formula_structure(formula: object) -> tuple[str, ...]:
    text = _strip_tex_prose_macros(str(formula or ""))
    superscripts = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁽⁾ⁱⁿᵏʲ", "0123456789+-()inkj")
    subscripts = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ", "0123456789+-()aehijklmnoprstuvx")
    text = re.sub(r"⁽([^⁾]+)⁾", lambda match: "^" + match.group(1).translate(superscripts) + " ", text)
    text = re.sub(r"₍([^₎]+)₎", lambda match: "_" + match.group(1).translate(subscripts) + " ", text)
    text = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁱⁿᵏʲ]+", lambda match: "^" + match.group().translate(superscripts) + " ", text)
    text = re.sub(r"[₀₁₂₃₄₅₆₇₈₉₊₋ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ]+", lambda match: "_" + match.group().translate(subscripts) + " ", text)
    fraction = re.compile(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
    while fraction.search(text):
        text = fraction.sub(r"\1/\2", text)
    text = re.sub(r"\\(?:mathrm|mathbf|mathit|mathsf|operatorname)\s*\{([^{}]+)\}", r"\1", text)
    replacements = {
        "\\left": "", "\\right": "", "\\,": "", "\\;": "", "\\!": "",
        "\\cdots": "...", "\\ldots": "...", "\\cdot": "*", "\\times": "*", "\\div": "/",
        "\\leq": "<=", "\\le": "<=", "\\geq": ">=", "\\ge": ">=",
        "\\neq": "!=", "\\ne": "!=", "\\Rightarrow": "=>", "\\implies": "=>",
        "\\in": "in", "\\subseteq": "subseteq", "\\subset": "subset",
        "\\vert": "|", "\\lvert": "|", "\\rvert": "|", "\\mid": "|",
        "\\bmod": " mod ", "\\pmod": " mod ", "\\Theta": "theta",
        "\\min": " min ", "\\max": " max ", "\\lfloor": "[", "\\rfloor": "]",
        "\\leftarrow": " arrow ", "\\to": " arrow ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\\(?:qquad|quad|bigl|bigr|Bigl|Bigr|displaystyle)\b", " ", text)
    unicode_replacements = {
        "≤": "<=", "≥": ">=", "≠": "!=", "→": "arrow", "←": "arrow",
        "…": "...", "Θ": "theta", "⌊": "[", "⌋": "]", "×": "*", "÷": "/",
    }
    for source, target in unicode_replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\.\.\.", "ellipsis", text)
    raw_tokens = re.findall(r"<=|>=|!=|=>|[=+*/<>^_|(),\[\]{}-]|\\[A-Za-z]+|\d+(?:\.\d+)?|[A-Za-z]+", text)
    tokens: list[str] = []
    for token in raw_tokens:
        if token.isalpha() and len(token) == 2 and token.islower():
            tokens.extend(token)
        elif token not in {"{", "}"}:
            tokens.append(token.casefold())
    return tuple(tokens)


def _formula_structure_is_present(expected: tuple[str, ...], candidate: object) -> bool:
    actual = _canonical_formula_structure(candidate)
    if not expected or not actual:
        return False
    if actual == expected:
        return True
    width = len(expected)
    return any(actual[index:index + width] == expected for index in range(len(actual) - width + 1))


def _semantic_numeric_capable(renderer: dict[str, Any], *scenarios: dict[str, Any]) -> bool:
    for container in (renderer, *scenarios):
        capability = container.get("numeric_evidence_capability", container.get("numeric_capability"))
        if isinstance(capability, bool):
            return capability
        if isinstance(capability, str) and capability.casefold() in {"typed", "numeric", "supported"}:
            return True
    if str(renderer.get("payload_type") or "").casefold() in {"physics", "economics"}:
        return True
    return any(key in renderer for key in ("numeric_setup", "calculation_fields", "result_fields"))


def _semantic_cue_integrity_errors(short: dict[str, Any], artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cue_rows: list[tuple[str, list[str]]] = []
    for position, beat in enumerate(artifact.get("beats", []) if isinstance(artifact.get("beats"), list) else [], start=1):
        if not isinstance(beat, dict):
            continue
        lines = beat.get("cue_lines")
        values = lines if isinstance(lines, list) else [beat.get("text")]
        cue_rows.append((f"beat {position}", [str(value or "").strip() for value in values if str(value or "").strip()]))
    for label, lines in cue_rows:
        cue = " ".join(lines)
        for line_position, line in enumerate(lines, start=1):
            if re.search(r"\\[A-Za-z]+|(?<!\w)[_^]\{?", line):
                errors.append(f"animation plan {label} cue {line_position} exposes raw TeX fragments: {line!r}")
        delimiter = _unbalanced_delimiter(cue)
        if delimiter is not None:
            errors.append(f"animation plan {label} has unbalanced delimiter {delimiter!r}: {cue!r}")
        stripped = cue.rstrip()
        if (
            re.search(r"(?:[=+*/<>^_-]|\\[A-Za-z]*)[.,;:]?$", stripped)
            or (stripped.endswith("|") and stripped.count("|") % 2)
            or re.search(r"\\[A-Za-z]+\{[^}]*$", stripped)
        ):
            errors.append(f"animation plan {label} is truncated mid-operator or mid-token: {cue!r}")
        terminal_word = re.search(r"([A-Za-z]+)[.!?]?\s*$", stripped)
        if (
            terminal_word
            and terminal_word.group(1).islower()
            and terminal_word.group(1) in SEMANTIC_TRUNCATION_END_WORDS
            and not re.search(r"[.!?]\s*$", stripped)
        ):
            errors.append(f"animation plan {label} is truncated after {terminal_word.group(1)!r}: {cue!r}")

    formula = str(short.get("formula") or short.get("plain_formula") or "").strip()
    if formula:
        delimiter = _unbalanced_delimiter(formula)
        if delimiter is not None:
            errors.append(f"short_plan.json core formula has unbalanced delimiter {delimiter!r}: {formula!r}")
        expected_structure = _canonical_formula_structure(formula)
        renderer = _semantic_mapping(_semantic_mapping(artifact.get("concrete_example")).get("renderer_state"))
        canonical_renderer_formula = renderer.get("canonical_formula")
        if canonical_renderer_formula is not None and (
            _canonical_formula_structure(canonical_renderer_formula) != expected_structure
        ):
            errors.append(
                "canonical formula mismatch short_plan.json ↔ animation plan renderer_state: "
                f"short_plan={formula!r}, renderer_state={canonical_renderer_formula!r}"
            )
        formula_evidence = [
            value for key, value in renderer.items()
            if any(marker in str(key).casefold() for marker in ("canonical_formula", "equation_evidence", "formula_evidence"))
        ]
        formula_evidence.extend(" ".join(lines) for _label, lines in cue_rows)
        if expected_structure and not any(
            _formula_structure_is_present(expected_structure, candidate) for candidate in formula_evidence
        ):
            errors.append(
                "short_plan.json core formula token structure is absent from visible cue/renderer equation evidence: "
                + " ".join(expected_structure)
            )
    return errors


def _semantic_transition_rows(artifact: dict[str, Any]) -> tuple[list[object], str, list[str]]:
    support = _semantic_mapping(artifact.get("semantic_support"))
    renderer = _semantic_mapping(_semantic_mapping(artifact.get("concrete_example")).get("renderer_state"))
    contract = artifact.get("semantic_transition_contract")
    if (
        isinstance(contract, dict)
        and isinstance(contract.get("transitions"), list)
        and contract["transitions"]
    ):
        return contract["transitions"], "semantic_transition_contract", []

    validation_errors: list[str] = []
    for container_name, container in (
        ("animation plan", artifact),
        ("semantic_support", support),
        ("renderer_state", renderer),
    ):
        for field in ("validated_route_contract", "route_contract", "semantic_route_contract"):
            route_contract = container.get(field)
            if not isinstance(route_contract, dict):
                continue
            validated = route_contract.get("validated") is True or route_contract.get("status") == "validated"
            route_matches = route_contract.get("route_key") == support.get("route_key")
            rows = route_contract.get("equivalent_typed_transitions", route_contract.get("transitions"))
            if validated and route_matches and isinstance(rows, list):
                return rows, f"{container_name}.{field}", []
            validation_errors.append(
                f"{container_name}.{field} does not prove validated, route-matched equivalent typed transitions"
            )
    return [], "semantic_transition_contract", validation_errors


def _semantic_transition_errors(artifact: dict[str, Any]) -> list[str]:
    support = _semantic_mapping(artifact.get("semantic_support"))
    if support.get("status") != "supported":
        return []
    rows, source, errors = _semantic_transition_rows(artifact)
    if len(rows) < SEMANTIC_IDENTITY_MIN_TRANSITIONS:
        errors.append(
            f"{source} has {len(rows)} causal transitions; supported semantic plans require at least "
            f"{SEMANTIC_IDENTITY_MIN_TRANSITIONS}"
        )
    seen: set[str] = set()
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"{source} transition {position} is not an object")
            continue
        transition_id = str(row.get("id", "")).strip()
        before = row.get("before")
        after = row.get("after")
        persistent = row.get("persistent_object_ids")
        if not transition_id or transition_id in seen:
            errors.append(f"{source} transition {position} needs a unique nonempty id")
        seen.add(transition_id)
        if (
            not isinstance(before, dict)
            or not before
            or not isinstance(after, dict)
            or set(before) != set(after)
            or before == after
        ):
            errors.append(f"{source} transition {transition_id or position} lacks complete changed before/after snapshots")
        if (
            not isinstance(persistent, list)
            or not persistent
            or not isinstance(before, dict)
            or not set(before).issubset({str(item) for item in persistent})
        ):
            errors.append(f"{source} transition {transition_id or position} does not type every snapshot object as persistent")
        if not str(row.get("action") or row.get("claim") or "").strip():
            errors.append(f"{source} transition {transition_id or position} has no causal action/claim")
    return errors


def _semantic_identity_sources(short: dict[str, Any], artifact: dict[str, Any]) -> dict[str, list[tuple[str, object]]]:
    support = _semantic_mapping(artifact.get("semantic_support"))
    renderer = _semantic_mapping(_semantic_mapping(artifact.get("concrete_example")).get("renderer_state"))
    short_scenario = _semantic_mapping(short.get("model_scenario"))
    renderer_scenario = _semantic_mapping(renderer.get("model_scenario"))

    def declared(rows: list[tuple[str, object]]) -> list[tuple[str, object]]:
        return [(label, value) for label, value in rows if value is not None and str(value).strip()]

    return {
        "model_id": declared([
            ("short_plan.model_id", short.get("model_id")),
            ("short_plan.model_scenario.model_id", short_scenario.get("model_id")),
            ("animation_plan.semantic_support.model_id", support.get("model_id")),
            ("animation_plan.renderer_state.model_id", renderer.get("model_id")),
            ("animation_plan.renderer_state.model_scenario.model_id", renderer_scenario.get("model_id")),
        ]),
        "route_key": declared([
            ("short_plan.route_key", short.get("route_key")),
            ("animation_plan.semantic_support.route_key", support.get("route_key")),
            ("animation_plan.renderer_state.route_key", renderer.get("route_key")),
            ("animation_plan.renderer_state.exact_route_key", renderer.get("exact_route_key")),
            ("animation_plan.renderer_state.model_scenario.route_key", renderer_scenario.get("route_key")),
        ]),
        "semantic_mode": declared([
            ("short_plan.semantic_mode", short.get("semantic_mode")),
            ("animation_plan.semantic_support.semantic_mode", support.get("semantic_mode")),
            ("animation_plan.renderer_state.semantic_mode", renderer.get("semantic_mode")),
            ("animation_plan.renderer_state.model_scenario.semantic_mode", renderer_scenario.get("semantic_mode")),
        ]),
        "scenario_mode": declared([
            ("short_plan.scenario_mode", short.get("scenario_mode")),
            ("short_plan.model_scenario.mode", short_scenario.get("mode")),
            ("animation_plan.renderer_state.scenario_mode", renderer.get("scenario_mode")),
            ("animation_plan.renderer_state.model_scenario.mode", renderer_scenario.get("mode")),
        ]),
    }


def _semantic_route_aliases(renderer: dict[str, Any]) -> dict[str, str]:
    """Canonicalize only public/internal routes explicitly paired by route-key fields."""
    public = str(renderer.get("route_key") or "").strip()
    exact = str(renderer.get("exact_route_key") or "").strip()
    exact_payload = _semantic_mapping(renderer.get("exact_semantic_payload"))
    payload_route = str(exact_payload.get("route_key") or "").strip()
    canonical = exact or payload_route
    return {public: canonical} if public and canonical else {}


def semantic_identity_contract_errors(short: dict[str, Any], artifact: dict[str, Any]) -> list[str]:
    """Return fail-closed cross-artifact semantic identity violations for one short."""
    errors: list[str] = []
    support = _semantic_mapping(artifact.get("semantic_support"))
    renderer = _semantic_mapping(_semantic_mapping(artifact.get("concrete_example")).get("renderer_state"))
    short_scenario = _semantic_mapping(short.get("model_scenario"))
    renderer_scenario = _semantic_mapping(renderer.get("model_scenario"))
    route_aliases = _semantic_route_aliases(renderer)
    for facet, rows in _semantic_identity_sources(short, artifact).items():
        values = {
            route_aliases.get(str(value), str(value)) if facet == "route_key" else str(value)
            for _label, value in rows
        }
        if len(values) > 1:
            detail = ", ".join(f"{label}={value!r}" for label, value in rows)
            errors.append(f"exact {facet} mismatch across short_plan.json ↔ animation plan ↔ renderer/model scenario: {detail}")
    if support.get("status") == "supported":
        if not str(support.get("route_key") or "").strip():
            errors.append("animation plan supported semantic route has no route_key")
        if renderer.get("route_key") is not None and renderer.get("route_key") != support.get("route_key"):
            errors.append(
                "exact route_key mismatch across animation plan ↔ renderer_state: "
                f"semantic_support.route_key={support.get('route_key')!r}, renderer_state.route_key={renderer.get('route_key')!r}"
            )
    if short_scenario and renderer_scenario and canonical_json_hash(short_scenario) != canonical_json_hash(renderer_scenario):
        errors.append("exact model_scenario mismatch short_plan.json ↔ animation plan renderer_state")
    numeric_capable = _semantic_numeric_capable(renderer, short_scenario, renderer_scenario)
    if numeric_capable:
        computed_fingerprints: list[tuple[str, str]] = []
        for label, scenario in (
            ("short_plan.model_scenario", short_scenario),
            ("animation_plan.renderer_state.model_scenario", renderer_scenario),
        ):
            if not scenario:
                continue
            try:
                computed = semantic_numeric_evidence_fingerprint(scenario)
            except (TypeError, ValueError) as exc:
                errors.append(f"{label} cannot produce a numeric evidence fingerprint: {exc}")
                continue
            computed_fingerprints.append((label, computed))
            declared = scenario.get("numeric_evidence_fingerprint")
            if declared is not None and declared != computed:
                errors.append(
                    f"numeric evidence fingerprint mismatch in {label}: declared={declared!r}, computed={computed!r}"
                )
        if len({fingerprint for _label, fingerprint in computed_fingerprints}) > 1:
            detail = ", ".join(f"{label}={fingerprint!r}" for label, fingerprint in computed_fingerprints)
            errors.append(f"numeric evidence fingerprint mismatch short_plan.json ↔ animation plan model scenario: {detail}")
        renderer_fingerprint = renderer.get("numeric_evidence_fingerprint")
        if renderer_fingerprint is not None and renderer_scenario:
            expected_renderer_fingerprint = semantic_numeric_evidence_fingerprint(renderer_scenario)
            if renderer_fingerprint != expected_renderer_fingerprint:
                errors.append(
                    "numeric evidence fingerprint mismatch animation plan renderer_state ↔ model_scenario: "
                    f"renderer_state={renderer_fingerprint!r}, model_scenario={expected_renderer_fingerprint!r}"
                )
    if renderer_scenario:
        scenario_sections = {
            "numeric_setup": renderer_scenario.get("setup"),
            "calculation_fields": renderer_scenario.get("calculation"),
            "result_fields": renderer_scenario.get("result", renderer_scenario.get("results")),
        }
        for renderer_field, expected in scenario_sections.items():
            actual = renderer.get(renderer_field)
            if actual is not None and expected is not None and canonical_json_hash(actual) != canonical_json_hash(expected):
                errors.append(
                    f"exact scenario data mismatch animation plan renderer_state.{renderer_field} ↔ "
                    f"renderer_state.model_scenario"
                )

    exemptions, exemption_errors = _validated_semantic_exemptions(short, artifact)
    errors.extend(exemption_errors)
    worked = _semantic_mapping(short.get("worked_example"))
    authored_evidence = {key: worked.get(key) for key in ("setup", "calculation")}
    scenario_evidence: object = renderer_scenario or short_scenario or renderer
    visible_evidence = _semantic_visible_storyboard(artifact)
    if numeric_capable:
        authored_numbers = _semantic_numeric_tokens(authored_evidence)
        scenario_numbers = _semantic_numeric_leaf_tokens(scenario_evidence)
        visible_numbers = _semantic_numeric_leaf_tokens(visible_evidence)
        for target, available in (("model_scenario", scenario_numbers), ("visible_storyboard", visible_numbers)):
            missing = sorted(
                number
                for number in authored_numbers - available
                if not _semantic_is_exempt(exemptions, "numeric", number, target)
            )
            if missing:
                errors.append(
                    f"numeric evidence mismatch short_plan.worked_example ↔ {target}: authored values "
                    f"{missing!r} are absent from {target}"
                )

    authored_variables = _semantic_named_variables(_semantic_strings(authored_evidence))
    scenario_variables = _semantic_variable_corpus(scenario_evidence)
    visible_variables = _semantic_variable_corpus(visible_evidence)
    for target, available in (("model_scenario", scenario_variables), ("visible_storyboard", visible_variables)):
        missing = sorted(
            variable
            for variable in authored_variables - available
            if not _semantic_is_exempt(exemptions, "variable", variable, target)
        )
        if missing:
            errors.append(
                f"named-variable mismatch short_plan.worked_example ↔ {target}: authored variables "
                f"{missing!r} are absent from {target}"
            )

    token_containers = [support, renderer, short_scenario, renderer_scenario]
    authored_and_visible = {"authored": authored_evidence, "visible": visible_evidence}
    for token in _semantic_declared_tokens(token_containers, forbidden=False):
        if not _semantic_token_present(token, authored_and_visible):
            errors.append(
                f"mechanism vocabulary mismatch route/model contract ↔ worked example/storyboard: required token {token!r} is absent"
            )
    for token in _semantic_required_tokens(token_containers, "required_example_tokens"):
        if not _semantic_token_present(token, worked):
            errors.append(f"worked-example evidence is missing required example token {token!r}")
    figure_renderer = {
        key: value
        for key, value in renderer.items()
        if key not in {"required_example_tokens", "required_figure_tokens"}
    }
    figure_evidence = {
        "renderer": figure_renderer,
        "visible_renderer_states": visible_evidence.get("visible_renderer_states"),
        "semantic_transition_contract": visible_evidence.get("semantic_transition_contract"),
    }
    for token in _semantic_required_tokens(token_containers, "required_figure_tokens"):
        if not _semantic_token_present(token, figure_evidence):
            errors.append(f"visible figure/storyboard evidence is missing required figure token {token!r}")
    for token in _semantic_declared_tokens(token_containers, forbidden=True):
        if _semantic_token_present(token, authored_and_visible):
            errors.append(
                f"forbidden cross-family mechanism token {token!r} appears in short_plan/worked-example or visible storyboard evidence"
            )

    errors.extend(_semantic_cue_integrity_errors(short, artifact))
    errors.extend(_semantic_transition_errors(artifact))
    return list(dict.fromkeys(errors))


def _scene_literal_assignment(source: str, names: set[str]) -> dict[str, object]:
    """Read generated literal runtime contracts without executing scene code."""
    found: dict[str, object] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        if value_node is None:
            continue
        for target in targets:
            name = target.id if isinstance(target, ast.Name) else (target.attr if isinstance(target, ast.Attribute) else "")
            if name not in names:
                continue
            try:
                found[name] = ast.literal_eval(value_node)
            except (ValueError, TypeError, SyntaxError):
                continue
    return found


def semantic_scene_contract_errors(
    short: dict[str, Any], artifact: dict[str, Any], scene_source: str
) -> list[str]:
    """Compare the generated scene/runtime literals to the accepted animation plan."""
    errors: list[str] = []
    support = _semantic_mapping(artifact.get("semantic_support"))
    renderer = _semantic_mapping(_semantic_mapping(artifact.get("concrete_example")).get("renderer_state"))
    literals = _scene_literal_assignment(scene_source, {"visual_data", "_animation_plan"})
    embedded_plan = literals.get("_animation_plan")
    visual_data = literals.get("visual_data")
    if not isinstance(embedded_plan, dict):
        errors.append("generated scene/runtime contract has no literal _animation_plan object")
    elif canonical_json_hash(embedded_plan) != canonical_json_hash(artifact):
        errors.append("exact animation-plan mismatch: generated scene/runtime _animation_plan differs from animation plan JSON")
    if not isinstance(visual_data, dict):
        errors.append("generated scene/runtime contract has no literal visual_data object")
    else:
        candidates = [
            value
            for value in visual_data.values()
            if isinstance(value, dict)
            and any(key in value for key in ("route_key", "model_id", "scenario_mode", "model_scenario"))
        ]
        scene_renderer = next(
            (candidate for candidate in candidates if candidate.get("route_key") == support.get("route_key")),
            candidates[0] if len(candidates) == 1 else None,
        )
        if renderer and not isinstance(scene_renderer, dict):
            errors.append(
                f"generated scene visual_data has no renderer payload for animation-plan route {support.get('route_key')!r}"
            )
        elif isinstance(scene_renderer, dict):
            identity_fields = ("route_key", "model_id", "scenario_mode", "semantic_mode")
            for field in identity_fields:
                expected = renderer.get(field)
                actual = scene_renderer.get(field)
                if expected is not None and actual != expected:
                    errors.append(
                        f"exact {field} mismatch animation plan renderer_state ↔ generated scene visual_data: "
                        f"renderer_state={expected!r}, scene={actual!r}"
                    )
            expected_scenario = renderer.get("model_scenario")
            if isinstance(expected_scenario, dict) and scene_renderer.get("model_scenario") != expected_scenario:
                errors.append("exact model_scenario mismatch animation plan renderer_state ↔ generated scene visual_data")
    metadata = stem_course_contract.generated_scene_metadata(scene_source)
    if metadata.get("route_key") != support.get("route_key"):
        errors.append(
            "exact route_key mismatch animation plan ↔ generated scene metadata: "
            f"animation plan={support.get('route_key')!r}, scene metadata={metadata.get('route_key')!r}"
        )
    return list(dict.fromkeys(errors))


def animation_short_source_payload(short: dict[str, Any]) -> dict[str, Any]:
    return stem_course_contract.animation_short_source_payload(short)


def animation_short_source_fingerprint(short: dict[str, Any]) -> str:
    return stem_course_contract.animation_short_source_fingerprint(short)


def animation_short_plan_fingerprint(plan: dict[str, Any]) -> str:
    return stem_course_contract.animation_short_plan_fingerprint(plan)


def animation_plan_artifact_fingerprint(plan: dict[str, Any]) -> str:
    return canonical_json_hash(plan)


def _structural_label(value: object) -> str:
    """Normalize an explicit structural label without retaining example values."""
    if value is None or value == "":
        return ""
    label = str(value).split(";", 1)[0].lower()
    label = re.sub(r"\d+(?:\.\d+)?", "", label)
    return re.sub(r"[^a-z_]+", "_", label).strip("_")


def scene_causal_signature(animation_plan: dict[str, Any]) -> tuple[object, ...]:
    """Describe scene causality using plan structure, not generated Python prose."""
    support = animation_plan.get("semantic_support") if isinstance(animation_plan.get("semantic_support"), dict) else {}
    concrete = animation_plan.get("concrete_example") if isinstance(animation_plan.get("concrete_example"), dict) else {}
    renderer_state = concrete.get("renderer_state") if isinstance(concrete.get("renderer_state"), dict) else {}
    scenario = renderer_state.get("model_scenario") if isinstance(renderer_state.get("model_scenario"), dict) else {}

    variant_fields = (
        "payload_type", "kind", "family", "mode", "route_key", "visual_kind",
        "renderer_variant", "variant", "dispatcher",
    )
    renderer_variant = tuple(
        (field, _structural_label(renderer_state[field]))
        for field in variant_fields
        if _structural_label(renderer_state.get(field))
    )
    scenario_mode = tuple(
        _structural_label(value)
        for value in (
            renderer_state.get("model_id"),
            renderer_state.get("scenario_mode"),
            scenario.get("model_id"),
            scenario.get("mode"),
        )
        if _structural_label(value)
    )

    roster = animation_plan.get("object_roster") if isinstance(animation_plan.get("object_roster"), list) else []
    object_roles = tuple(
        _structural_label(item.get("role"))
        for item in roster
        if isinstance(item, dict) and item.get("persistent", True) and _structural_label(item.get("role"))
    )

    transition_contract = (
        animation_plan.get("semantic_transition_contract")
        if isinstance(animation_plan.get("semantic_transition_contract"), dict)
        else {}
    )
    transitions = transition_contract.get("transitions") if isinstance(transition_contract.get("transitions"), list) else []
    ordered_transitions = tuple(
        (_structural_label(row.get("kind")), _structural_label(row.get("id")))
        for row in transitions
        if isinstance(row, dict)
    )
    states = scenario.get("animation_states")
    if not isinstance(states, list):
        states = renderer_state.get("animation_states") if isinstance(renderer_state.get("animation_states"), list) else []
    ordered_states = tuple(
        (_structural_label(row.get("phase")), _structural_label(row.get("state_id")))
        for row in states
        if isinstance(row, dict)
    )

    required_tokens: list[object] = []
    for container in (renderer_state, scenario):
        values = container.get("required_figure_tokens")
        if isinstance(values, list):
            required_tokens.extend(values)
    figure_tokens = tuple(sorted({_structural_label(token) for token in required_tokens if _structural_label(token)}))

    return (
        _structural_label(support.get("visual_kind")),
        _structural_label(support.get("route_key")),
        _structural_label(support.get("semantic_mode")),
        renderer_variant,
        scenario_mode,
        object_roles,
        ordered_transitions,
        ordered_states,
        figure_tokens,
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nested_value(payload: object, *names: str) -> object | None:
    """Find a contract field at top level or in a provenance/artifact section."""
    if not isinstance(payload, dict):
        return None
    for name in names:
        if payload.get(name) is not None:
            return payload[name]
    for section_name in ("hashes", "artifacts", "provenance", "media", "timing"):
        section = payload.get(section_name)
        if isinstance(section, dict):
            for name in names:
                if section.get(name) is not None:
                    return section[name]
    return None


def planned_state_change_contracts(animation_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return exact state deltas that a temporal review or runtime trace may claim."""
    semantic_contract = (
        animation_plan.get("semantic_transition_contract")
        if isinstance(animation_plan.get("semantic_transition_contract"), dict)
        else {}
    )
    semantic_rows = semantic_contract.get("transitions") if isinstance(semantic_contract.get("transitions"), list) else []
    semantic_by_id = {
        str(row.get("id")).strip(): row
        for row in semantic_rows
        if isinstance(row, dict) and str(row.get("id", "")).strip()
    }
    beats = animation_plan.get("beats") if isinstance(animation_plan.get("beats"), list) else []
    declared_semantic_transitions: list[tuple[dict[str, Any], str]] = []
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        evidence = beat.get("evidence") if isinstance(beat.get("evidence"), dict) else {}
        transition_ids = beat.get("semantic_transition_ids")
        if not isinstance(transition_ids, list):
            transition_ids = evidence.get("semantic_transition_ids")
        for value in transition_ids if isinstance(transition_ids, list) else []:
            transition_id = str(value).strip()
            if transition_id:
                declared_semantic_transitions.append((beat, transition_id))

    contracts: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    if declared_semantic_transitions:
        for beat, transition_id in declared_semantic_transitions:
            beat_id = str(beat.get("id", "")).strip()
            transition = semantic_by_id.get(transition_id)
            if not isinstance(transition, dict):
                continue
            evidence = beat.get("evidence") if isinstance(beat.get("evidence"), dict) else {}
            observed_before = transition.get("before") if isinstance(transition.get("before"), dict) else {}
            observed_after = transition.get("after") if isinstance(transition.get("after"), dict) else {}
            persistent_ids = (
                [str(value) for value in transition.get("persistent_object_ids", [])]
                if isinstance(transition.get("persistent_object_ids"), list)
                else []
            )
            key = (beat_id, transition_id)
            if (
                key in seen
                or not observed_before
                or set(observed_before) != set(observed_after)
                or observed_before == observed_after
                or not set(observed_before).issubset(set(persistent_ids))
            ):
                continue
            seen.add(key)
            contracts.append(
                {
                    "beat_id": beat_id,
                    "planned_transition_id": transition_id,
                    "before_seconds": evidence.get("before_seconds"),
                    "after_seconds": evidence.get("after_seconds"),
                    "persistent_object_ids": persistent_ids,
                    "changed_attribute": STATE_CHANGE_ATTRIBUTE,
                    "observed_before": observed_before,
                    "observed_after": observed_after,
                    "motion_evidence_required": (
                        float(beat.get("duration", 0.0) or 0.0) >= 5.0
                        or str(beat.get("arc_phase", "")) == "resolve"
                    ),
                }
            )
        return contracts

    for beat in beats:
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("id", "")).strip()
        evidence = beat.get("evidence") if isinstance(beat.get("evidence"), dict) else {}
        before_seconds = evidence.get("before_seconds")
        after_seconds = evidence.get("after_seconds")
        state_delta = beat.get("state_delta") if isinstance(beat.get("state_delta"), dict) else {}
        delta_before = state_delta.get("before") if isinstance(state_delta.get("before"), dict) else {}
        delta_after = state_delta.get("after") if isinstance(state_delta.get("after"), dict) else {}
        changed_ids = (
            [str(value) for value in state_delta.get("changed_object_ids", [])]
            if isinstance(state_delta.get("changed_object_ids"), list)
            else []
        )
        if beat.get("arc_phase") == "transform" and beat_id and changed_ids:
            key = (beat_id, beat_id)
            if (
                key not in seen
                and len(changed_ids) == len(set(changed_ids))
                and set(changed_ids).issubset(delta_before)
                and set(changed_ids).issubset(delta_after)
                and all(delta_before[object_id] != delta_after[object_id] for object_id in changed_ids)
            ):
                seen.add(key)
                contracts.append(
                    {
                        "beat_id": beat_id,
                        "planned_transition_id": beat_id,
                        "before_seconds": before_seconds,
                        "after_seconds": after_seconds,
                        "persistent_object_ids": changed_ids,
                        "changed_attribute": STATE_CHANGE_ATTRIBUTE,
                        "observed_before": {object_id: delta_before[object_id] for object_id in changed_ids},
                        "observed_after": {object_id: delta_after[object_id] for object_id in changed_ids},
                        "motion_evidence_required": (
                            float(beat.get("duration", 0.0) or 0.0) >= 5.0
                            or str(beat.get("arc_phase", "")) == "resolve"
                        ),
                    }
                )
                continue

        persistent_ids = (
            [str(value) for value in evidence.get("persistent_object_ids", [])]
            if isinstance(evidence.get("persistent_object_ids"), list)
            else []
        )
        start_state = beat.get("start_state") if isinstance(beat.get("start_state"), dict) else {}
        end_state = beat.get("end_state") if isinstance(beat.get("end_state"), dict) else {}
        changed_ids = [
            object_id
            for object_id in persistent_ids
            if object_id in start_state and object_id in end_state and start_state[object_id] != end_state[object_id]
        ]
        if not beat_id or not changed_ids:
            continue
        key = (beat_id, beat_id)
        if key in seen:
            continue
        seen.add(key)
        contracts.append(
            {
                "beat_id": beat_id,
                "planned_transition_id": beat_id,
                "before_seconds": before_seconds,
                "after_seconds": after_seconds,
                "persistent_object_ids": persistent_ids,
                "changed_attribute": STATE_CHANGE_ATTRIBUTE,
                "observed_before": {object_id: start_state[object_id] for object_id in changed_ids},
                "observed_after": {object_id: end_state[object_id] for object_id in changed_ids},
                "motion_evidence_required": (
                    float(beat.get("duration", 0.0) or 0.0) >= 5.0
                    or str(beat.get("arc_phase", "")) == "resolve"
                ),
            }
        )
    return contracts


def structured_state_change_error(
    record: Any,
    expected: dict[str, Any] | None,
    *,
    video_file: str | None = None,
    runtime_event: bool = False,
) -> str | None:
    if not isinstance(record, dict):
        return "entry is not an object"
    if expected is None:
        return "beat_id/planned_transition_id does not identify a planned transition"
    if record.get("beat_id") != expected["beat_id"] or record.get("planned_transition_id") != expected["planned_transition_id"]:
        return "transition identity does not match the animation plan"
    if record.get("changed_attribute") != expected["changed_attribute"]:
        return f"changed_attribute must be {STATE_CHANGE_ATTRIBUTE!r}"
    persistent_ids = record.get("persistent_object_ids")
    if (
        not isinstance(persistent_ids, list)
        or not persistent_ids
        or any(not isinstance(value, str) or not value for value in persistent_ids)
        or len(persistent_ids) != len(set(persistent_ids))
        or set(persistent_ids) != set(expected["persistent_object_ids"])
    ):
        return "persistent_object_ids do not exactly match the planned transition"
    observed_before = record.get("observed_before")
    observed_after = record.get("observed_after")
    if not isinstance(observed_before, dict) or not observed_before or not isinstance(observed_after, dict) or not observed_after:
        return "observed_before and observed_after must be non-empty object-ID maps"
    if canonical_json_hash(observed_before) != canonical_json_hash(expected["observed_before"]):
        return "observed_before does not match the planned before-state"
    if canonical_json_hash(observed_after) != canonical_json_hash(expected["observed_after"]):
        return "observed_after does not match the planned after-state"
    if canonical_json_hash(observed_before) == canonical_json_hash(observed_after):
        return "observed state does not change"

    before_seconds = parse_float(expected.get("before_seconds"))
    after_seconds = parse_float(expected.get("after_seconds"))
    if runtime_event:
        if "before_seconds" not in record or "after_seconds" not in record:
            return "runtime event lacks before_seconds or after_seconds"
        if round(parse_float(record.get("before_seconds")) * stem_course_contract.RENDER_TIMELINE_FPS) != round(before_seconds * stem_course_contract.RENDER_TIMELINE_FPS):
            return "runtime before_seconds does not match planned evidence"
        if round(parse_float(record.get("after_seconds")) * stem_course_contract.RENDER_TIMELINE_FPS) != round(after_seconds * stem_course_contract.RENDER_TIMELINE_FPS):
            return "runtime after_seconds does not match planned evidence"
    else:
        expected_before_frame = f"{video_file}#t={before_seconds:.2f}s"
        expected_after_frame = f"{video_file}#t={after_seconds:.2f}s"
        if record.get("before_frame") != expected_before_frame or record.get("after_frame") != expected_after_frame:
            return "before_frame/after_frame do not match the planned evidence window"
    return None


def semantic_runtime_event_error(
    record: dict[str, Any],
    expected: dict[str, Any],
    expected_callback_count: int | None,
) -> str | None:
    """Validate renderer evidence that exists only on canonical per-ID events."""
    before_seconds = parse_float(expected.get("before_seconds"))
    after_seconds = parse_float(expected.get("after_seconds"))
    if record.get("timing_source") != "manim.renderer.time":
        return "timing_source must be 'manim.renderer.time'"

    renderer_markers = record.get("renderer_markers")
    if not isinstance(renderer_markers, list) or len(renderer_markers) != 2:
        return "renderer_markers must contain exactly one before and one after marker"
    for marker, phase, expected_seconds in zip(
        renderer_markers,
        ("before", "after"),
        (before_seconds, after_seconds),
    ):
        if not isinstance(marker, dict) or marker.get("phase") != phase:
            return f"renderer_markers are not in exact before/after order"
        try:
            marker_seconds = float(marker.get("renderer_seconds"))
        except (TypeError, ValueError):
            return f"{phase} renderer marker has invalid timing"
        if (
            not math.isfinite(marker_seconds)
            or round(marker_seconds * stem_course_contract.RENDER_TIMELINE_FPS)
            != round(expected_seconds * stem_course_contract.RENDER_TIMELINE_FPS)
        ):
            return f"{phase} renderer marker does not match planned evidence"

    if expected_callback_count is None:
        return "event has no valid semantic callback binding"
    execution_records = record.get("execution_records")
    if not isinstance(execution_records, list):
        return "execution_records must be an array"
    if len(execution_records) != expected_callback_count:
        return (
            f"execution_records count {len(execution_records)} does not match the exact registered callback "
            f"count {expected_callback_count}"
        )
    transition_id = expected["planned_transition_id"]
    for position, callback in enumerate(execution_records, start=1):
        if not isinstance(callback, dict):
            return f"callback {position} is not an object"
        if (
            callback.get("kind") != "callback"
            or callback.get("status") != "ok"
            or callback.get("declared_transition_id") != transition_id
            or not str(callback.get("callback_name", "")).strip()
        ):
            return f"callback {position} is not a successful execution of {transition_id!r}"
        try:
            started_seconds = float(callback.get("started_seconds"))
            finished_seconds = float(callback.get("finished_seconds"))
        except (TypeError, ValueError):
            return f"callback {position} has invalid renderer timing"
        if (
            not math.isfinite(started_seconds)
            or not math.isfinite(finished_seconds)
            or not round(before_seconds * stem_course_contract.RENDER_TIMELINE_FPS)
            <= round(started_seconds * stem_course_contract.RENDER_TIMELINE_FPS)
            <= round(finished_seconds * stem_course_contract.RENDER_TIMELINE_FPS)
            <= round(after_seconds * stem_course_contract.RENDER_TIMELINE_FPS)
        ):
            return f"callback {position} falls outside the planned renderer window"
        intervals = callback.get("choreography_intervals")
        if expected.get("motion_evidence_required") and not (
            isinstance(intervals, list)
            and any(isinstance(interval, dict) and interval.get("qualifying_motion") for interval in intervals)
        ):
            return f"callback {position} lacks qualifying choreography motion evidence"
    return None


def pdf_visible_run_text(value: Any) -> str:
    """Normalize visible PDF text while removing non-rendering controls."""
    printable = "".join(character if character.isprintable() else " " for character in str(value))
    return re.sub(r"\s+", " ", printable).strip()


def pdf_tex_delimiter_run(text: str, font: str) -> bool:
    """Return whether a run is a TeX delimiter with a deliberately loose glyph box."""
    if not PDF_TEX_DELIMITER_PATTERN.fullmatch(text.strip()):
        return False
    normalized_font = font.casefold()
    return any(marker in normalized_font for marker in ("cmex", "math", "symbol"))


def pdf_page_layout_geometry(page: Any) -> tuple[list[dict[str, Any]], list[tuple[float, float]], list[dict[str, Any]]]:
    """Extract text runs, occupied vertical intervals, and anchored figure captions."""
    runs: list[dict[str, Any]] = []
    occupied_intervals: list[tuple[float, float]] = []
    captions: list[dict[str, Any]] = []
    page_dict = page.get_text("dict", sort=True)
    for block_index, block in enumerate(page_dict.get("blocks", [])):
        block_type = block.get("type")
        if block_type == 1:
            bbox = block.get("bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                occupied_intervals.append((float(bbox[1]), float(bbox[3])))
            continue
        if block_type != 0:
            continue
        for line_index, line in enumerate(block.get("lines", [])):
            line_spans = line.get("spans", [])
            line_text = pdf_visible_run_text("".join(str(span.get("text", "")) for span in line_spans))
            if not line_text:
                continue
            line_bbox = line.get("bbox")
            if isinstance(line_bbox, (list, tuple)) and len(line_bbox) == 4:
                occupied_intervals.append((float(line_bbox[1]), float(line_bbox[3])))
            caption_match = PDF_FIGURE_CAPTION_PATTERN.match(line_text)
            if caption_match and isinstance(line_bbox, (list, tuple)) and len(line_bbox) == 4:
                caption_number = int(caption_match.group(1))
                captions.append(
                    {
                        "label": f"Figure {caption_number}",
                        "number": caption_number,
                        "bbox": tuple(float(value) for value in line_bbox),
                    }
                )
            for span_index, span in enumerate(line_spans):
                text = pdf_visible_run_text(span.get("text", ""))
                bbox = span.get("bbox")
                if not text or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                    continue
                runs.append(
                    {
                        "text": text,
                        "font": str(span.get("font", "")),
                        "size": float(span.get("size", 0.0) or 0.0),
                        "bbox": tuple(float(value) for value in bbox),
                        "line_id": (block_index, line_index),
                        "span_id": (block_index, line_index, span_index),
                    }
                )
    return runs, occupied_intervals, captions


def pdf_figure_layout_regions(
    page: Any,
    captions: list[dict[str, Any]],
) -> list[tuple[float, float, float, float]]:
    """Associate each caption with its nearest vector or raster drawing cluster."""
    rectangles: list[tuple[float, float, float, float]] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is not None:
            rectangles.append((float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)))
    try:
        image_info = page.get_image_info()
    except (AttributeError, RuntimeError):
        image_info = []
    for image in image_info:
        bbox = image.get("bbox") if isinstance(image, dict) else None
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            rectangles.append(tuple(float(value) for value in bbox))
    if not rectangles:
        return []

    clusters: list[tuple[float, float, float, float]] = []
    for left, top, right, bottom in sorted(rectangles, key=lambda rect: (rect[1], rect[0])):
        if clusters and top <= clusters[-1][3] + PDF_FIGURE_CLUSTER_GAP_POINTS:
            cluster_left, cluster_top, cluster_right, cluster_bottom = clusters[-1]
            clusters[-1] = (
                min(cluster_left, left),
                min(cluster_top, top),
                max(cluster_right, right),
                max(cluster_bottom, bottom),
            )
        else:
            clusters.append((left, top, right, bottom))

    page_rect = page.rect
    regions: list[tuple[float, float, float, float]] = []
    for caption in captions:
        caption_bbox = caption.get("bbox")
        if not isinstance(caption_bbox, tuple) or len(caption_bbox) != 4:
            continue
        caption_top = float(caption_bbox[1])
        caption_bottom = float(caption_bbox[3])
        eligible_clusters = [
            cluster
            for cluster in clusters
            if cluster[1] < caption_top
            and cluster[3] <= caption_bottom + PDF_FIGURE_REGION_PADDING_POINTS
            and max(0.0, caption_top - cluster[3]) <= PDF_FIGURE_CAPTION_MAX_GAP_POINTS
        ]
        if not eligible_clusters:
            continue
        left, top, right, bottom = min(
            eligible_clusters,
            key=lambda cluster: max(0.0, caption_top - cluster[3]),
        )
        region = (
            max(float(page_rect.x0), left - PDF_FIGURE_REGION_PADDING_POINTS),
            max(float(page_rect.y0), top - PDF_FIGURE_REGION_PADDING_POINTS),
            min(float(page_rect.x1), right + PDF_FIGURE_REGION_PADDING_POINTS),
            min(float(page_rect.y1), bottom + PDF_FIGURE_REGION_PADDING_POINTS),
        )
        if region not in regions:
            regions.append(region)
    return regions


def pdf_run_center_in_regions(
    run: dict[str, Any],
    regions: list[tuple[float, float, float, float]],
) -> bool:
    x0, y0, x1, y1 = run["bbox"]
    center_x = (x0 + x1) / 2.0
    center_y = (y0 + y1) / 2.0
    return any(left <= center_x <= right and top <= center_y <= bottom for left, top, right, bottom in regions)


def pdf_text_intersections(
    runs: list[dict[str, Any]],
    *,
    regions: list[tuple[float, float, float, float]] | None = None,
) -> list[dict[str, Any]]:
    """Find visible overlap between independently positioned rendered text runs."""
    intersections: list[dict[str, Any]] = []
    visible_runs: list[dict[str, Any]] = []
    for run in runs:
        text = pdf_visible_run_text(run.get("text", ""))
        if not text:
            continue
        normalized_run = {**run, "text": text}
        if regions is not None and not pdf_run_center_in_regions(normalized_run, regions):
            continue
        visible_runs.append(normalized_run)
    ordered_runs = sorted(visible_runs, key=lambda run: (run["bbox"][0], run["bbox"][1]))
    for index, first in enumerate(ordered_runs):
        first_x0, first_y0, first_x1, first_y1 = first["bbox"]
        for second in ordered_runs[index + 1:]:
            second_x0, second_y0, second_x1, second_y1 = second["bbox"]
            if second_x0 > first_x1 - PDF_MIN_TEXT_INTERSECTION_WIDTH:
                break
            # PyMuPDF keeps TeX super/subscripts and adjacent symbols on one
            # extracted line even when their generous font boxes overlap.
            if first.get("line_id") == second.get("line_id"):
                continue
            if pdf_tex_delimiter_run(first["text"], str(first.get("font", ""))) or pdf_tex_delimiter_run(
                second["text"], str(second.get("font", ""))
            ):
                continue
            width = min(first_x1, second_x1) - max(first_x0, second_x0)
            height = min(first_y1, second_y1) - max(first_y0, second_y0)
            area = width * height
            if (
                width < PDF_MIN_TEXT_INTERSECTION_WIDTH
                or height < PDF_MIN_TEXT_INTERSECTION_HEIGHT
                or area < PDF_MIN_TEXT_INTERSECTION_AREA
            ):
                continue
            intersections.append(
                {
                    "first": first["text"],
                    "second": second["text"],
                    "width": width,
                    "height": height,
                    "area": area,
                }
            )
    return intersections


def pdf_largest_vertical_blank_run(
    occupied_intervals: list[tuple[float, float]],
    *,
    body_top: float,
    body_bottom: float,
) -> tuple[float, float]:
    """Return the largest blank run and usable-body height in PDF points."""
    usable_height = max(0.0, body_bottom - body_top)
    clipped = sorted(
        (max(body_top, start), min(body_bottom, end))
        for start, end in occupied_intervals
        if end >= body_top and start <= body_bottom
    )
    merged: list[tuple[float, float]] = []
    for start, end in clipped:
        if end < start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    cursor = body_top
    largest_blank = 0.0
    for start, end in merged:
        largest_blank = max(largest_blank, start - cursor)
        cursor = max(cursor, end)
    largest_blank = max(largest_blank, body_bottom - cursor)
    return max(0.0, largest_blank), usable_height


def pdf_trailing_vertical_blank_run(
    occupied_intervals: list[tuple[float, float]],
    *,
    body_top: float,
    body_bottom: float,
) -> tuple[float, float]:
    """Return the blank run after the final occupied body element."""
    usable_height = max(0.0, body_bottom - body_top)
    occupied_bottoms = [
        min(body_bottom, end)
        for start, end in occupied_intervals
        if end >= body_top and start <= body_bottom
    ]
    final_bottom = max(occupied_bottoms, default=body_top)
    return max(0.0, body_bottom - final_bottom), usable_height


def pdf_vertical_occupancy_ratio(
    occupied_intervals: list[tuple[float, float]],
    *,
    body_top: float,
    body_bottom: float,
) -> float:
    """Return the proportion of the usable body covered by rendered content."""
    usable_height = max(0.0, body_bottom - body_top)
    if usable_height <= 0:
        return 0.0
    clipped = sorted(
        (max(body_top, start), min(body_bottom, end))
        for start, end in occupied_intervals
        if end >= body_top and start <= body_bottom
    )
    merged: list[tuple[float, float]] = []
    for start, end in clipped:
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return sum(end - start for start, end in merged) / usable_height


def pdf_page_starts_section(runs: list[dict[str, Any]], *, body_top: float, body_bottom: float) -> bool:
    """Recognize an explicit rendered heading at the start of a new section."""
    usable_height = max(0.0, body_bottom - body_top)
    body_runs = [
        run
        for run in runs
        if float(run["bbox"][3]) >= body_top and float(run["bbox"][1]) <= body_bottom
    ]
    if not body_runs:
        return False
    first_top = min(float(run["bbox"][1]) for run in body_runs)
    return any(
        float(run.get("size", 0.0)) >= PDF_SECTION_HEADING_MIN_FONT_SIZE
        and float(run["bbox"][1]) <= body_top + usable_height * PDF_FIGURE_BLOCK_START_RATIO
        and float(run["bbox"][1]) <= first_top + 6.0
        for run in body_runs
    )


def pdf_page_leading_figure(
    page: Any,
    runs: list[dict[str, Any]],
    captions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the leading caption when a figure is the next page's first body block.

    A display-sized heading before the figure is an observable rendered section
    boundary, so that intentional pagination is not reported as figure spill.
    """
    regions = pdf_figure_layout_regions(page, captions)
    if not regions:
        return None
    leading_region = min(regions, key=lambda region: (region[1], region[0]))
    page_rect = page.rect
    body_margin = float(page_rect.height) * PDF_USABLE_BODY_MARGIN_RATIO
    body_top = float(page_rect.y0) + body_margin
    body_bottom = float(page_rect.y1) - body_margin
    usable_height = max(0.0, body_bottom - body_top)
    if leading_region[1] > body_top + usable_height * PDF_FIGURE_BLOCK_START_RATIO:
        return None

    preceding_runs = [
        run
        for run in runs
        if float(run["bbox"][3]) >= body_top and float(run["bbox"][1]) < leading_region[1]
        and not pdf_run_center_in_regions(run, regions)
    ]
    if any(float(run.get("size", 0.0)) >= PDF_SECTION_HEADING_MIN_FONT_SIZE for run in preceding_runs):
        return None
    if preceding_runs:
        # Ordinary body copy means the page does not begin with the figure block.
        return None

    region_bottom = leading_region[3] + PDF_FIGURE_CAPTION_MAX_GAP_POINTS
    return next(
        (
            caption
            for caption in captions
            if leading_region[1] <= float(caption["bbox"][1]) <= region_bottom
        ),
        None,
    )


def latex_bmatrix_findings(text: str) -> list[dict[str, Any]]:
    """Return structural defects in bmatrix environments with source line numbers."""
    findings: list[dict[str, Any]] = []
    inline_spans = [
        match.span()
        for pattern in (r"(?<!\\)\$(?:\\.|[^$])*?(?<!\\)\$", r"\\\((?:.|\n)*?\\\)")
        for match in re.finditer(pattern, text)
    ]
    environment_pattern = re.compile(
        r"\\begin\{bmatrix\}(.*?)\\end\{bmatrix\}",
        flags=re.DOTALL,
    )
    row_separator = re.compile(r"(?<!\\)\\\\(?:\[[^\]]*\])?")

    for match in environment_pattern.finditer(text):
        body = match.group(1)
        line = text.count("\n", 0, match.start()) + 1
        rows = row_separator.split(body)
        column_counts = [row.count("&") + 1 for row in rows if row.strip()]

        malformed = bool(
            re.search(r"(?<!\\)\\[ \t]+(?=\S)", body)
            or re.search(r"(?<!/)//(?!/)", body)
            or any(re.search(r"(?:^|&)\s*(?:&|$)", row.strip()) for row in rows)
            or len(column_counts) == 1 and len([row for row in body.splitlines() if "&" in row]) > 1
        )
        if malformed:
            findings.append(
                {
                    "line": line,
                    "message": "bmatrix contains a malformed row or column separator.",
                }
            )
        if len(column_counts) > 1 and len(set(column_counts)) > 1:
            findings.append(
                {
                    "line": line,
                    "message": f"bmatrix has ragged rows with column counts {column_counts}.",
                }
            )

        is_inline = any(start <= match.start() and match.end() <= end for start, end in inline_spans)
        if is_inline and len(column_counts) > 1 and sum(column_counts) > 4:
            findings.append(
                {
                    "line": line,
                    "message": (
                        f"Inline bmatrix is oversized ({len(column_counts)} rows and up to "
                        f"{max(column_counts)} columns); use display math."
                    ),
                }
            )
    return findings


def notes_pdf_layout_findings(document: Any) -> list[dict[str, Any]]:
    """Audit rendered notes pages for sparse prose, detached discussion, and figure spill."""
    findings: list[dict[str, Any]] = []
    page_profiles: list[dict[str, Any]] = []
    for page_index, page in enumerate(document):
        runs, occupied_intervals, captions = pdf_page_layout_geometry(page)
        drawings = page.get_drawings()
        for drawing in drawings:
            rect = drawing.get("rect")
            if rect is not None:
                occupied_intervals.append((float(rect.y0), float(rect.y1)))
        try:
            has_images = bool(page.get_image_info())
        except (AttributeError, RuntimeError):
            has_images = False
        page_rect = page.rect
        body_margin = float(page_rect.height) * PDF_USABLE_BODY_MARGIN_RATIO
        body_top = float(page_rect.y0) + body_margin
        body_bottom = float(page_rect.y1) - body_margin
        trailing_blank, usable_height = pdf_trailing_vertical_blank_run(
            occupied_intervals,
            body_top=body_top,
            body_bottom=body_bottom,
        )
        page_profiles.append(
            {
                "page": page,
                "page_number": page_index + 1,
                "runs": runs,
                "occupied_intervals": occupied_intervals,
                "captions": captions,
                "body_top": body_top,
                "body_bottom": body_bottom,
                "usable_height": usable_height,
                "trailing_blank": trailing_blank,
                "trailing_blank_ratio": trailing_blank / usable_height if usable_height > 0 else 0.0,
                "occupancy_ratio": pdf_vertical_occupancy_ratio(
                    occupied_intervals,
                    body_top=body_top,
                    body_bottom=body_bottom,
                ),
                "starts_section": pdf_page_starts_section(runs, body_top=body_top, body_bottom=body_bottom),
                "has_visual": bool(drawings) or has_images,
                "text": " ".join(str(run["text"]) for run in runs),
            }
        )

    caption_pages = [
        profile
        for profile in page_profiles
        if profile["captions"]
    ]
    final_page_number = len(page_profiles)
    for page_index, profile in enumerate(page_profiles):
        page_number = int(profile["page_number"])
        if page_number == PDF_TITLE_PAGE_NUMBER:
            continue

        page_text = str(profile["text"])
        has_unnumbered_discussion = bool(PDF_UNNUMBERED_FIGURE_DISCUSSION_PATTERN.search(page_text))
        has_explicit_reference = bool(PDF_FIGURE_REFERENCE_PATTERN.search(page_text))
        if (
            has_unnumbered_discussion
            and not has_explicit_reference
            and not profile["captions"]
            and not profile["has_visual"]
            and caption_pages
        ):
            nearest_caption_page = min(
                caption_pages,
                key=lambda candidate: abs(int(candidate["page_number"]) - page_number),
            )
            nearest_caption = nearest_caption_page["captions"][0]
            caption_page_number = int(nearest_caption_page["page_number"])
            findings.append(
                {
                    "kind": "detached-figure-discussion",
                    "page_number": page_number,
                    "caption_page_number": caption_page_number,
                    "caption": str(nearest_caption["label"]),
                    "caption_number": int(nearest_caption["number"]),
                    "message": (
                        f"Page {page_number} discusses 'the figure' without a numbered Figure reference, "
                        f"but the nearest anchored caption ({nearest_caption['label']}) is on page "
                        f"{caption_page_number}. Keep unnumbered figure discussion with its figure or cite it explicitly."
                    ),
                }
            )

        if profile["starts_section"] and page_number != final_page_number:
            continue
        occupancy_ratio = float(profile["occupancy_ratio"])
        trailing_blank_ratio = float(profile["trailing_blank_ratio"])
        sparse_body = occupancy_ratio < PDF_MIN_BODY_OCCUPANCY_RATIO
        excessive_tail = trailing_blank_ratio >= PDF_MAX_TRAILING_BLANK_RATIO
        next_starts_section = (
            page_index + 1 < len(page_profiles)
            and bool(page_profiles[page_index + 1]["starts_section"])
        )
        if next_starts_section:
            continue

        is_final_prose_page = (
            page_number == final_page_number
            and bool(profile["runs"])
            and not profile["captions"]
            and not profile["has_visual"]
        )
        if is_final_prose_page and (sparse_body or excessive_tail):
            findings.append(
                {
                    "kind": "sparse-final-prose-page",
                    "page_number": page_number,
                    "body_occupancy_ratio": occupancy_ratio,
                    "trailing_blank_ratio": trailing_blank_ratio,
                    "message": (
                        f"Page {page_number}, the final prose page, uses only {occupancy_ratio:.1%} of its "
                        f"usable body and leaves {trailing_blank_ratio:.1%} blank at the end, indicating "
                        "a stranded final fragment."
                    ),
                }
            )
        elif (
            page_number != final_page_number
            and not profile["has_visual"]
            and (sparse_body or excessive_tail)
        ):
            findings.append(
                {
                    "kind": "low-body-occupancy" if sparse_body else "excessive-trailing-blank",
                    "page_number": page_number,
                    "body_occupancy_ratio": occupancy_ratio,
                    "trailing_blank_ratio": trailing_blank_ratio,
                    "message": (
                        f"Page {page_number} uses {occupancy_ratio:.1%} of its usable body and leaves "
                        f"{trailing_blank_ratio:.1%} blank at the end, without a rendered section "
                        "boundary to explain the sparse layout."
                    ),
                }
            )

    for page_index, page in enumerate(document):
        page_number = page_index + 1
        if page_number == PDF_TITLE_PAGE_NUMBER:
            continue

        runs, occupied_intervals, captions = pdf_page_layout_geometry(page)
        if not captions:
            continue
        figure_regions = pdf_figure_layout_regions(page, captions)
        for intersection in pdf_text_intersections(runs, regions=figure_regions):
            first = intersection["first"][:48]
            second = intersection["second"][:48]
            findings.append(
                {
                    "kind": "text-intersection",
                    "page_number": page_number,
                    **intersection,
                    "message": (
                        f"Page {page_number} has intersecting rendered text runs {first!r} and {second!r} "
                        f"({intersection['width']:.2f}pt by {intersection['height']:.2f}pt)."
                    ),
                }
            )
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect is not None:
                occupied_intervals.append((float(rect.y0), float(rect.y1)))
        page_rect = page.rect
        body_margin = float(page_rect.height) * PDF_USABLE_BODY_MARGIN_RATIO
        body_top = float(page_rect.y0) + body_margin
        body_bottom = float(page_rect.y1) - body_margin
        largest_blank, usable_height = pdf_largest_vertical_blank_run(
            occupied_intervals,
            body_top=body_top,
            body_bottom=body_bottom,
        )
        blank_ratio = largest_blank / usable_height if usable_height > 0 else 0.0
        if blank_ratio < PDF_MAX_FIGURE_BLANK_RUN_RATIO:
            continue
        caption_label = str(captions[0]["label"])
        caption_number = int(captions[0]["number"])
        findings.append(
            {
                "kind": "sparse-figure-page",
                "page_number": page_number,
                "caption": caption_label,
                "caption_number": caption_number,
                "largest_blank_points": largest_blank,
                "usable_body_points": usable_height,
                "blank_ratio": blank_ratio,
                "message": (
                    f"Page {page_number} has an anchored {caption_label} caption but its largest usable-body "
                    f"blank run is {blank_ratio:.1%} ({largest_blank:.1f}pt of {usable_height:.1f}pt), "
                    "indicating a sparse figure spill page."
                ),
            }
        )

    # Figure placement can strand a large blank tail on the preceding prose
    # page even when the figure page itself is not sparse enough to trip the
    # page-local check above.
    final_page_index = len(document) - 1
    for page_index in range(1, final_page_index):
        page = document[page_index]
        next_page = document[page_index + 1]
        next_runs, _, next_captions = pdf_page_layout_geometry(next_page)
        leading_caption = pdf_page_leading_figure(next_page, next_runs, next_captions)
        if leading_caption is None:
            continue

        _, occupied_intervals, _ = pdf_page_layout_geometry(page)
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect is not None:
                occupied_intervals.append((float(rect.y0), float(rect.y1)))
        page_rect = page.rect
        body_margin = float(page_rect.height) * PDF_USABLE_BODY_MARGIN_RATIO
        body_top = float(page_rect.y0) + body_margin
        body_bottom = float(page_rect.y1) - body_margin
        trailing_blank, usable_height = pdf_trailing_vertical_blank_run(
            occupied_intervals,
            body_top=body_top,
            body_bottom=body_bottom,
        )
        blank_ratio = trailing_blank / usable_height if usable_height > 0 else 0.0
        if blank_ratio < PDF_MIN_TRAILING_BLANK_BEFORE_FIGURE_RATIO:
            continue

        page_number = page_index + 1
        next_page_number = page_number + 1
        caption_label = str(leading_caption["label"])
        findings.append(
            {
                "kind": "trailing-blank-before-figure",
                "page_number": page_number,
                "next_page_number": next_page_number,
                "caption": caption_label,
                "caption_number": int(leading_caption["number"]),
                "largest_blank_points": trailing_blank,
                "usable_body_points": usable_height,
                "blank_ratio": blank_ratio,
                "message": (
                    f"Page {page_number} leaves {blank_ratio:.1%} of its usable body blank at the end "
                    f"({trailing_blank:.1f}pt of {usable_height:.1f}pt) before anchored {caption_label} "
                    f"begins page {next_page_number}, indicating a displaced figure block."
                ),
            }
        )
    return findings


class CourseRunValidator:
    def __init__(self, run: Path, *, draft: bool = False, allow_fallback_pdf: bool = False) -> None:
        self.run = run.resolve()
        self.draft = draft
        self.allow_fallback_pdf = allow_fallback_pdf
        self.issues: list[Issue] = []
        self.ffprobe = shutil.which("ffprobe")
        self.ffmpeg = shutil.which("ffmpeg")
        self.video_cache: dict[Path, dict[str, Any]] = {}
        self.validated_video_roles: set[tuple[Path, str]] = set()
        self.analyzed_video_paths: set[Path] = set()
        self.silent_final_paths: set[Path] = set()
        self.course_title = self.run.name

    def validate(self) -> list[Issue]:
        if not self.run.exists():
            self.fail("run", "Run directory does not exist.", self.run, fix="Pass an existing runs/<course> directory.")
            return self.issues
        if not self.run.is_dir():
            self.fail("run", "Run path is not a directory.", self.run)
            return self.issues

        plan = self.load_json(self.run / "short_plan.json", required=False)
        if isinstance(plan, dict) and str(plan.get("course_title", "")).strip():
            self.course_title = str(plan["course_title"]).strip()
        self.validate_no_nested_run_artifacts()
        self.validate_source_pack()
        self.validate_notes()
        self.validate_short_plan(plan)
        self.validate_animation_plans(plan)
        self.validate_scene_script_caption_assets(plan)
        self.validate_videos(plan)
        self.validate_visual_frame_audit(plan)
        self.validate_visual_review(plan)
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

        self.validate_notes_coverage_report()

        if not tex.exists() and not md.exists():
            self.fail("notes", "No notes.tex or notes.md artifact found.", self.run, fix="Run `python tools/stem_course.py notes --run <run> --compile`.")

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

    def validate_notes_coverage_report(self) -> None:
        """Require the notes coverage ledger to prove every strict notes gate."""
        path = self.run / "notes_coverage_report.json"
        severity = self.warn if self.draft else self.fail
        if not path.exists():
            severity(
                "notes.coverage",
                "notes_coverage_report.json is missing; notes coverage cannot be verified.",
                path,
                fix="Regenerate the notes so the coverage ledger is written and all checks pass.",
            )
            return
        coverage = self.load_json(path, required=False)
        if coverage is None:
            return
        if not isinstance(coverage, dict):
            severity("notes.coverage", "notes_coverage_report.json must be a JSON object.", path)
            return

        status = coverage.get("status")
        if status != "ok":
            detail = "missing" if status is None else repr(status)
            severity(
                "notes.coverage",
                f"Notes coverage status is {detail}, not 'ok'.",
                path,
                fix="Resolve every coverage failure and regenerate the notes coverage report.",
            )

        topics = coverage.get("topics")
        if not isinstance(topics, list):
            severity("notes.coverage.topics", "Notes coverage topics are missing or malformed.", path)
        else:
            failed_topics: list[str] = []
            failed_figure_bindings: list[str] = []
            for position, topic in enumerate(topics, start=1):
                if not isinstance(topic, dict):
                    failed_topics.append(f"topic {position}")
                    continue
                label = str(topic.get("concept") or f"topic {position}")
                checks = topic.get("checks") if isinstance(topic.get("checks"), dict) else {}
                failed_checks = [str(name) for name, passed in checks.items() if passed is not True]
                missing = topic.get("missing") if isinstance(topic.get("missing"), list) else []
                if topic.get("status") != "ok" or failed_checks or missing:
                    failed_topics.append(label)

                figure_declared = checks.get("figure_generated") is True or bool(
                    topic.get("figure") or topic.get("figure_declared")
                )
                binding = topic.get("figure_binding_contract")
                binding_failed = (
                    checks.get("figure_example_binding") is False
                    or isinstance(binding, dict) and binding.get("status") != "ok"
                )
                if figure_declared and binding_failed:
                    failed_figure_bindings.append(label)
            if failed_topics:
                preview = ", ".join(failed_topics[:8]) + (" ..." if len(failed_topics) > 8 else "")
                severity(
                    "notes.coverage.topics",
                    f"{len(failed_topics)} notes topic(s) have failed or incomplete checks: {preview}.",
                    path,
                    fix="Regenerate or repair each failed topic before publishing the notes.",
                )
            if failed_figure_bindings:
                preview = ", ".join(failed_figure_bindings[:8])
                severity(
                    "notes.coverage.figures",
                    f"Declared figures have failed example bindings for: {preview}.",
                    path,
                    fix="Bind every generated figure to the topic's worked example and regenerate the ledger.",
                )

        gap_contracts = (
            ("outline", "outline_coverage_status", "missing_outline_topic_count"),
            ("source subtopic", "source_subtopic_status", "missing_source_subtopic_count"),
        )
        for label, status_field, count_field in gap_contracts:
            gap_status = coverage.get(status_field)
            try:
                gap_count = int(coverage.get(count_field, 0) or 0)
            except (TypeError, ValueError):
                gap_count = 1
            if gap_status == "failed" or gap_count > 0:
                severity(
                    "notes.coverage.gaps",
                    f"Notes have {gap_count} missing {label} item(s) ({status_field}={gap_status!r}).",
                    path,
                    fix="Cover every authoritative outline and required source item, then regenerate the ledger.",
                )

        page_status = coverage.get("page_integrity_status")
        page_findings = coverage.get("page_integrity_findings")
        if page_status == "failed" or isinstance(page_findings, list) and bool(page_findings):
            finding_count = len(page_findings) if isinstance(page_findings, list) else 0
            severity(
                "notes.coverage.page-integrity",
                f"Notes page integrity failed with {finding_count} finding(s).",
                path,
                fix="Correct the rendered PDF layout findings, recompile, and regenerate the coverage report.",
            )

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
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for finding in latex_bmatrix_findings(text):
            self.fail(
                "notes.latex.matrix",
                finding["message"],
                path,
                line=finding["line"],
                fix="Use consistent `&` columns and `\\\\` row separators; move large matrices into display math.",
            )
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
        topic_count = len(re.findall(r"\\section\s*(?:\[[^\]]*\])?\{", text))
        figure_count = len(re.findall(r"\\begin\{tikzpicture\}|\\includegraphics(?:\[[^\]]*\])?\{", text))
        if figure_count < max(4, min(12, topic_count // 4)):
            self.fail("notes.figures", f"notes.tex contains only {figure_count} embedded figure(s) for {topic_count} topic sections.", path, fix="Generate topic-specific TikZ figures or include generated graphics directly in notes.tex/PDF.")
        if len(text) < 30_000:
            self.warn("notes.depth", f"notes.tex is compact ({len(text):,} characters); full-course notes may be too short.", path, fix="Add definitions, formulas, properties, examples, questions, and supplemental topics until the course is covered.")
        if topic_count < 12:
            self.warn("notes.depth", f"notes.tex has only {topic_count} topic sections; broad courses should cover more of the course map.", path, fix="Generate notes from the full course topic library, not only the shorts queue.")

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
            with fitz.open(path) as doc:
                page_count = doc.page_count
                layout_findings = notes_pdf_layout_findings(doc)
        except Exception as exc:
            self.warn(
                "notes.pdf.layout",
                f"Rendered notes PDF layout could not be inspected: {exc}.",
                path,
                fix="Install PyMuPDF and regenerate notes.pdf if the file cannot be opened.",
            )
            return

        for finding in layout_findings:
            if finding["kind"] == "text-intersection":
                fix = "Move colliding figure labels or text runs apart and recompile notes.pdf."
            elif finding["kind"] == "detached-figure-discussion":
                fix = "Keep unnumbered figure discussion beside its caption, or cite the numbered Figure explicitly."
            elif finding["kind"] in {
                "sparse-final-prose-page",
                "low-body-occupancy",
                "excessive-trailing-blank",
            }:
                fix = "Reflow the prose so substantive body content is not stranded on a sparse rendered page."
            else:
                fix = "Keep each figure with substantive surrounding exposition instead of isolating it on a spill page."
            self.fail("notes.pdf.layout", finding["message"], path, fix=fix)

        coverage_path = self.run / "notes_coverage_report.json"
        topic_count = 0
        if coverage_path.exists():
            try:
                coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
                topic_count = int(coverage.get("topic_count", 0) or 0) if isinstance(coverage, dict) else 0
            except (OSError, ValueError, json.JSONDecodeError):
                topic_count = 0
        comprehensive_minimum = max(50, topic_count * 2) if topic_count >= 8 else 20
        if page_count < 8:
            self.fail("notes.pdf", f"notes.pdf has only {page_count} pages; full-course notes are too short.", path, fix="Regenerate comprehensive notes from the full course topic set.")
        elif topic_count >= 8 and page_count < comprehensive_minimum and not self.draft:
            self.fail(
                "notes.pdf",
                f"notes.pdf has {page_count} pages for {topic_count} course topics; the comprehensive target is at least {comprehensive_minimum} pages.",
                path,
                fix="Expand definitions, derivations, proofs, examples, procedures, and figures for every calendar unit, then recompile.",
            )
        elif page_count < comprehensive_minimum:
            self.warn("notes.pdf", f"notes.pdf has only {page_count} pages; verify it covers the whole course.", path)

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
        example_signatures: dict[str, int] = {}
        for pos, short in enumerate(shorts, start=1):
            if not isinstance(short, dict):
                self.fail("short-plan", f"Short item {pos} is not an object.", self.run / "short_plan.json")
                continue
            for field in required_fields:
                if field not in short:
                    self.fail("short-plan", f"Short {short.get('index', pos)} is missing `{field}`.", self.run / "short_plan.json")
            self.validate_worked_example(short, pos, example_signatures)
        self.validate_course_concept_coverage(shorts)

    def validate_course_concept_coverage(self, shorts: list[Any]) -> None:
        """Join the comprehensive notes inventory to the videos they are meant to feed."""
        coverage_path = self.run / "notes_coverage_report.json"
        source_path = self.run / "source_pack.json"
        coverage = self.load_json(coverage_path, required=False) if coverage_path.exists() else None
        course_units: list[object] = []
        if isinstance(coverage, dict) and isinstance(coverage.get("topics"), list):
            course_units = [
                topic.get("concept", "") for topic in coverage["topics"] if isinstance(topic, dict)
            ]
        if not course_units and source_path.exists():
            source_pack = self.load_json(source_path, required=False)
            if isinstance(source_pack, dict):
                course_units = stem_course_contract.source_outline_topics(source_pack)
        if len(course_units) < 5:
            self.warn(
                "course.coverage",
                "Fewer than five authoritative notes units were available; semantic video coverage could not be audited reliably.",
                coverage_path if coverage_path.exists() else source_path,
            )
            return

        video_concepts = [short.get("concept", "") for short in shorts if isinstance(short, dict)]
        report = semantic_course_coverage(course_units, video_concepts)
        if report["status"] == "failed":
            missing = [row["course_unit"] for row in report["units"] if row["status"] == "uncovered"]
            preview = ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else "")
            self.fail(
                "course.coverage",
                f"Videos materially under-cover the notes course map: {report['uncovered_course_unit_count']}/{report['course_unit_count']} units are unmapped (longest consecutive run: {report['longest_uncovered_run']}). Uncovered: {preview}.",
                self.run / "short_plan.json",
                fix="Group related units into broader storyboard concepts or add videos for the uncovered major units, then regenerate storyboards.",
            )

    def animation_plan_issue(self, area: str, message: str, path: Path, *, fix: str | None = None) -> None:
        severity = self.warn if self.draft else self.fail
        severity(area, message, path, fix=fix)

    def validate_animation_plans(self, plan: Any) -> None:
        if not isinstance(plan, dict) or not plan_shorts(plan):
            return
        remediation = "Run `python tools/stem_course.py storyboard --run <run>` after every short-plan change."
        index_path = self.run / ANIMATION_PLAN_INDEX_NAME
        if not index_path.exists():
            self.animation_plan_issue(
                "animation-plan.missing",
                f"{ANIMATION_PLAN_INDEX_NAME} is missing; Manim has no required storyboard contract.",
                index_path,
                fix=remediation,
            )
            return
        try:
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.animation_plan_issue("animation-plan.index", f"Animation plan index is unreadable: {exc}.", index_path, fix=remediation)
            return
        if not isinstance(index_payload, dict):
            self.animation_plan_issue("animation-plan.index", "Animation plan index must be a JSON object.", index_path, fix=remediation)
            return
        if index_payload.get("schema_version") != ANIMATION_PLAN_SCHEMA_VERSION:
            self.animation_plan_issue(
                "animation-plan.index",
                f"Animation plan index schema must be {ANIMATION_PLAN_SCHEMA_VERSION!r}.",
                index_path,
                fix=remediation,
            )
        expected_plan_fingerprint = animation_short_plan_fingerprint(plan)
        if index_payload.get("short_plan_fingerprint") != expected_plan_fingerprint:
            self.animation_plan_issue(
                "animation-plan.stale",
                "Animation plan index is stale for the current short_plan.json.",
                index_path,
                fix=remediation,
            )
        raw_rows = index_payload.get("plans") if isinstance(index_payload.get("plans"), list) else []
        rows: dict[int, dict[str, Any]] = {}
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            try:
                row_index = int(row.get("short_index", 0) or 0)
            except (TypeError, ValueError):
                continue
            if row_index > 0:
                rows[row_index] = row

        for short in plan_shorts(plan):
            try:
                short_index = int(short.get("index", 0) or 0)
            except (TypeError, ValueError):
                continue
            expected_relative = f"{ANIMATION_PLAN_DIRECTORY}/short_{short_index:02d}.json"
            row = rows.get(short_index)
            if row is None:
                self.animation_plan_issue(
                    "animation-plan.missing",
                    f"Short {short_index:02d} is missing from the animation plan index.",
                    index_path,
                    fix=remediation,
                )
                continue
            relative = str(row.get("path") or short.get("animation_plan_file") or expected_relative)
            relative_path = Path(relative)
            artifact_path = self.run / relative_path
            if relative_path.is_absolute() or ".." in relative_path.parts or relative != expected_relative:
                self.animation_plan_issue(
                    "animation-plan.path",
                    f"Short {short_index:02d} uses a noncanonical or unsafe animation plan path.",
                    artifact_path,
                    fix=remediation,
                )
                continue
            if not artifact_path.exists():
                self.animation_plan_issue(
                    "animation-plan.missing",
                    f"Short {short_index:02d} animation plan is missing.",
                    artifact_path,
                    fix=remediation,
                )
                continue
            try:
                artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.animation_plan_issue(
                    "animation-plan.invalid",
                    f"Short {short_index:02d} animation plan is unreadable: {exc}.",
                    artifact_path,
                    fix=remediation,
                )
                continue
            if not isinstance(artifact, dict):
                self.animation_plan_issue(
                    "animation-plan.invalid",
                    f"Short {short_index:02d} animation plan must be a JSON object.",
                    artifact_path,
                    fix=remediation,
                )
                continue
            for message in self.animation_plan_contract_messages(artifact, short):
                area = "animation-plan.stale" if "stale" in message else "animation-plan.invalid"
                self.animation_plan_issue(
                    area,
                    f"Course {self.course_title!r} / short {short_index:02d} ({short.get('concept', '')!r}) / "
                    f"artifacts short_plan.json ↔ {relative}: {message}.",
                    artifact_path,
                    fix=remediation,
                )
            artifact_fingerprint = animation_plan_artifact_fingerprint(artifact)
            if row.get("artifact_fingerprint") != artifact_fingerprint:
                self.animation_plan_issue(
                    "animation-plan.stale",
                    f"Short {short_index:02d} animation plan no longer matches its index hash.",
                    artifact_path,
                    fix=remediation,
                )
            semantic_support = artifact.get("semantic_support") if isinstance(artifact.get("semantic_support"), dict) else {}
            index_contract = {
                "visual_kind": semantic_support.get("visual_kind"),
                "visual_family": semantic_support.get("family"),
                "visual_route": semantic_support.get("route_key"),
                "support_status": semantic_support.get("status"),
                "unsupported_reason": semantic_support.get("unsupported_reason"),
                "renderer_state_fingerprint": semantic_support.get("renderer_state_fingerprint"),
            }
            if any(row.get(field) != value for field, value in index_contract.items()):
                self.animation_plan_issue(
                    "animation-plan.stale",
                    f"Short {short_index:02d} animation plan index does not match its semantic route metadata.",
                    index_path,
                    fix=remediation,
                )
            if short.get("animation_plan_artifact_fingerprint") != artifact_fingerprint:
                self.animation_plan_issue(
                    "animation-plan.stale",
                    f"Short {short_index:02d} animation plan metadata is stale.",
                    self.run / "short_plan.json",
                    fix=remediation,
                )

    def animation_plan_contract_messages(self, artifact: dict[str, Any], short: dict[str, Any]) -> list[str]:
        errors = list(stem_course_contract.animation_plan_contract_errors(artifact, short))
        errors.extend(semantic_identity_contract_errors(short, artifact))
        if artifact.get("schema_version") != ANIMATION_PLAN_SCHEMA_VERSION:
            errors.append(f"schema_version must be {ANIMATION_PLAN_SCHEMA_VERSION}")
        if artifact.get("source_fingerprint") != animation_short_source_fingerprint(short):
            errors.append("source_fingerprint is stale for short_plan.json")
        for field in ("visual_claim", "concrete_example", "object_roster", "continuity_spine", "beats", "invariant", "reveal", "qa_evidence_timestamps"):
            if not artifact.get(field):
                errors.append(f"{field} is required")
        support = artifact.get("semantic_support") if isinstance(artifact.get("semantic_support"), dict) else {}
        expected_kind = stem_course_contract.infer_visual_kind(short)
        expected_route = stem_course_contract.animation_route_descriptor(short, expected_kind)
        if support.get("visual_kind") != expected_kind:
            errors.append(f"semantic visual_kind must be {expected_kind}")
        if support.get("route_key") != expected_route["route_key"]:
            errors.append("semantic route_key does not match the visual kind and worked example")
        expected_status = "supported" if expected_route["supported"] else "unsupported"
        if support.get("status") != expected_status:
            errors.append(f"semantic support status must be {expected_status}")
        if support.get("status") != "supported" or support.get("visual_kind") not in ANIMATION_SUPPORTED_VISUAL_KINDS:
            errors.append("semantic visual-family support is missing")
        route_key = str(support.get("route_key", "")).strip()
        if (
            not str(support.get("family", "")).strip()
            or not route_key
            or support.get("renderer_route") != f"{route_key} semantic renderer"
        ):
            errors.append("semantic family and concrete renderer route are required")
        expected_components = stem_course_contract.animation_route_plan_components(short, expected_kind)
        concrete = artifact.get("concrete_example") if isinstance(artifact.get("concrete_example"), dict) else {}
        renderer_state = concrete.get("renderer_state") if isinstance(concrete.get("renderer_state"), dict) else None
        if renderer_state is None:
            errors.append("concrete_example.renderer_state is required")
        else:
            expected_state = expected_components["renderer_state"]
            if canonical_json_hash(renderer_state) != canonical_json_hash(expected_state):
                errors.append("renderer_state is stale for the worked example")
            if support.get("renderer_state_fingerprint") != canonical_json_hash(renderer_state):
                errors.append("renderer_state_fingerprint does not match the renderer state")
        if artifact.get("object_roster") != expected_components["object_roster"]:
            errors.append("object_roster does not match the concrete semantic route")
        actual_beats = artifact.get("beats") if isinstance(artifact.get("beats"), list) else []
        actual_actions = [beat.get("action") for beat in actual_beats if isinstance(beat, dict)]
        if actual_actions != expected_components["actions"]:
            errors.append("beat actions do not match the concrete visual route and worked example")
        if artifact.get("semantic_transition_contract") != expected_components.get("semantic_contract"):
            errors.append("semantic_transition_contract is stale or incomplete")
        invariant = artifact.get("invariant") if isinstance(artifact.get("invariant"), dict) else {}
        if invariant.get("statement") != expected_components["blueprint"]["invariant"]:
            errors.append("invariant does not match the concrete visual route")
        reveal = artifact.get("reveal") if isinstance(artifact.get("reveal"), dict) else {}
        expected_reveal = stem_course_contract.animation_cue(
            expected_components["takeaway"] or stem_course_contract.video_formula_text(short, expected_kind),
            width=180,
        )
        if reveal.get("statement") != expected_reveal:
            errors.append("reveal does not match the worked-example conclusion")

        roster = artifact.get("object_roster") if isinstance(artifact.get("object_roster"), list) else []
        roster_ids: list[str] = []
        for position, item in enumerate(roster, start=1):
            if not isinstance(item, dict):
                errors.append(f"object_roster item {position} must be an object")
                continue
            object_id = str(item.get("id", "")).strip()
            if object_id:
                roster_ids.append(object_id)
            else:
                errors.append(f"object_roster item {position} needs a stable id")
            if not str(item.get("role", "")).strip() or not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(item.get("color", ""))):
                errors.append(f"object {object_id or position} needs a semantic role and hex color")
        if len(roster_ids) < 3:
            errors.append("object_roster needs at least three semantic objects")
        if len(roster_ids) != len(set(roster_ids)):
            errors.append("object_roster ids must be unique")
        roster_id_set = set(roster_ids)

        continuity = artifact.get("continuity_spine") if isinstance(artifact.get("continuity_spine"), dict) else {}
        spine_ids = {str(value) for value in continuity.get("object_ids", []) if str(value)} if isinstance(continuity.get("object_ids"), list) else set()
        if not spine_ids or not spine_ids.issubset(roster_id_set):
            errors.append("continuity_spine must name valid persistent object ids")
        if not str(continuity.get("concept_to_example", "")).strip():
            errors.append("continuity_spine must define the concept-to-example handoff")

        beats = artifact.get("beats") if isinstance(artifact.get("beats"), list) else []
        if not ANIMATION_PLAN_MIN_BEATS <= len(beats) <= ANIMATION_PLAN_MAX_BEATS:
            errors.append(f"beats must contain {ANIMATION_PLAN_MIN_BEATS}-{ANIMATION_PLAN_MAX_BEATS} semantic beats")
        beat_ids: set[str] = set()
        transformations = 0
        active_count = 0
        previous_end = -1.0
        previous_carry: set[str] | None = None
        for position, beat in enumerate(beats, start=1):
            if not isinstance(beat, dict):
                errors.append(f"beat {position} must be an object")
                continue
            for field in ("id", "start_state", "action", "end_state", "carry", "text", "evidence"):
                if field not in beat:
                    errors.append(f"beat {position} is missing {field}")
            beat_id = str(beat.get("id", "")).strip()
            if not beat_id or beat_id in beat_ids:
                errors.append(f"beat {position} needs a unique id")
            beat_ids.add(beat_id)
            active = {str(value) for value in beat.get("active_objects", []) if str(value)} if isinstance(beat.get("active_objects"), list) else set()
            carry = {str(value) for value in beat.get("carry", []) if str(value)} if isinstance(beat.get("carry"), list) else set()
            if active:
                active_count += 1
            if not active.issubset(roster_id_set) or not carry.issubset(roster_id_set):
                errors.append(f"beat {position} references unknown object ids")
            if previous_carry is not None and not previous_carry.intersection(active):
                errors.append(f"beat {position} breaks object continuity with the previous beat")
            if spine_ids and not spine_ids.intersection(active):
                errors.append(f"beat {position} does not act on the continuity spine")
            previous_carry = carry
            action = str(beat.get("action", "")).lower()
            if bool(beat.get("full_reset")) or any(term in action for term in ("clear canvas", "full reset", "blank reset", "replace the entire scene")):
                errors.append(f"beat {position} performs a forbidden full reset")
            if bool(beat.get("domain_state_change")) and action and not any(term in action for term in ("fade in text", "fade out text", "write the title", "replace the caption")):
                transformations += 1
            start = parse_float(beat.get("start_seconds")) or 0.0
            end = parse_float(beat.get("end_seconds")) or 0.0
            if start < previous_end - 0.01 or end <= start:
                errors.append(f"beat {position} has invalid or overlapping timing")
            previous_end = end
            evidence = beat.get("evidence") if isinstance(beat.get("evidence"), dict) else {}
            before = parse_float(evidence.get("before_seconds")) or 0.0
            after = parse_float(evidence.get("after_seconds")) or 0.0
            persistent = {str(value) for value in evidence.get("persistent_object_ids", []) if str(value)} if isinstance(evidence.get("persistent_object_ids"), list) else set()
            if not (start <= before < after <= end) or not persistent.intersection(spine_ids):
                errors.append(f"beat {position} evidence must bracket the change on a continuity object")
        if transformations < ANIMATION_PLAN_MIN_TRANSFORMATIONS:
            errors.append(f"plan needs at least {ANIMATION_PLAN_MIN_TRANSFORMATIONS} domain-state transformations")
        active_ratio = active_count / len(beats) if beats else 0.0
        if active_ratio < ANIMATION_PLAN_MIN_OBJECT_ACTIVE_RATIO:
            errors.append(f"object-active beat ratio {active_ratio:.2f} is below {ANIMATION_PLAN_MIN_OBJECT_ACTIVE_RATIO:.2f}")
        evidence_rows = artifact.get("qa_evidence_timestamps") if isinstance(artifact.get("qa_evidence_timestamps"), list) else []
        evidenced_ids = {str(row.get("beat_id")) for row in evidence_rows if isinstance(row, dict)}
        if len(evidence_rows) < ANIMATION_PLAN_MIN_TRANSFORMATIONS or len(evidenced_ids.intersection(beat_ids)) < ANIMATION_PLAN_MIN_TRANSFORMATIONS:
            errors.append("qa_evidence_timestamps must cover at least four planned transformations")
        return list(dict.fromkeys(errors))

    def validate_worked_example(self, short: dict[str, Any], pos: int, signatures: dict[str, int]) -> None:
        index = short.get("index", pos)
        example = short.get("worked_example")
        if not isinstance(example, dict):
            self.fail("short-plan.example", f"Short {index} has no worked_example object.", self.run / "short_plan.json")
            return
        fields = [str(example.get(key, "")).strip() for key in ("setup", "calculation", "takeaway")]
        if any(not field for field in fields):
            self.fail("short-plan.example", f"Short {index} has an incomplete worked_example.", self.run / "short_plan.json")
            return

        combined = " ".join(fields)
        word_count = len(re.findall(r"\b[\w'-]+\b", combined))
        if word_count < 16:
            self.fail(
                "short-plan.example",
                f"Short {index} worked_example is too thin ({word_count} words).",
                self.run / "short_plan.json",
                fix="Give setup, calculation, and interpretation with concrete values or a concrete symbolic object.",
            )
        if not re.search(r"\d|=|->|\{|\}|\(|\)|\[|\]|\bmod\b|\b[A-Z]\s*-\s*[A-Z]\b", combined):
            self.fail(
                "short-plan.example",
                f"Short {index} worked_example has no concrete numbers, equations, sets, vectors, or symbolic objects.",
                self.run / "short_plan.json",
                fix="Add at least one teachable concrete example, even for theoretical concepts.",
            )

        placeholder_pattern = (
            r"\b("
            r"pick a small|choose a small|build a small|set up a small|"
            r"work through one|work through the definition|representative example|"
            r"the example should|the calculation should|mini-example template"
            r")\b"
        )
        if re.search(placeholder_pattern, combined, flags=re.I):
            self.fail(
                "short-plan.example",
                f"Short {index} worked_example still reads like an example placeholder.",
                self.run / "short_plan.json",
                fix="Replace it with a specific example that teaches the concept through values, objects, and a conclusion.",
            )

        signature = re.sub(r"[^a-z0-9=]+", " ", " ".join(fields[:2]).lower()).strip()
        signature = re.sub(r"\b(short|concept|example|takeaway)\b", " ", signature)
        signature = re.sub(r"\s+", " ", signature)
        if signature:
            previous = signatures.get(signature)
            if previous is not None:
                self.fail(
                    "short-plan.example",
                    f"Short {index} repeats the worked example from short {previous}.",
                    self.run / "short_plan.json",
                    fix="Use a new example for each video so the series teaches rather than recycles.",
                )
            else:
                try:
                    signatures[signature] = int(index)
                except Exception:
                    signatures[signature] = pos

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
            self.validate_scene_animation_plan_link(short, scene)
            self.validate_planned_visual_type(short, visual_kind, scene)
            animation_plan = self.current_animation_plan(short)
            current_metadata = self.current_scene_metadata(scene)
            structured = animation_plan is not None
            if animation_plan is not None:
                self.validate_exact_scene_route(short, scene, visual_kind, animation_plan, current_metadata or {})
            scene_visuals.append(
                {
                    "path": scene,
                    "visual_kind": visual_kind,
                    "concept": concept,
                    "animation_plan": animation_plan if structured else None,
                }
            )
            self.validate_caption(caption, index, expected_duration=parse_float(short.get("target_duration_seconds")))
            self.validate_script(script, index)

        self.detect_repeated_scene_sources(normalized_sources, scene_visuals)
        self.validate_scene_visual_quality(scene_visuals, domain_text)

    def current_animation_plan(self, short: dict[str, Any]) -> dict[str, Any] | None:
        try:
            short_index = int(short.get("index", 0) or 0)
        except (TypeError, ValueError):
            short_index = 0
        relative = str(
            short.get("animation_plan_file")
            or (f"{ANIMATION_PLAN_DIRECTORY}/short_{short_index:02d}.json" if short_index > 0 else "")
        ).strip()
        if not relative:
            return None
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            return None
        path = self.run / relative_path
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(artifact, dict) or artifact.get("schema_version") != ANIMATION_PLAN_SCHEMA_VERSION:
            return None
        if artifact.get("source_fingerprint") != animation_short_source_fingerprint(short):
            return None
        expected_fingerprint = str(short.get("animation_plan_artifact_fingerprint") or "").strip()
        if expected_fingerprint and expected_fingerprint != animation_plan_artifact_fingerprint(artifact):
            return None
        return artifact

    def current_scene_metadata(self, scene: Path) -> dict[str, str] | None:
        try:
            source = scene.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        metadata = stem_course_contract.generated_scene_metadata(source)
        if metadata.get("scene_metadata_version") != SCENE_METADATA_VERSION:
            return None
        return metadata

    def validate_exact_scene_route(
        self,
        short: dict[str, Any],
        scene: Path,
        declared_visual_kind: str,
        animation_plan: dict[str, Any],
        metadata: dict[str, str],
    ) -> None:
        support = animation_plan.get("semantic_support") if isinstance(animation_plan.get("semantic_support"), dict) else {}
        expected_kind = stem_course_contract.infer_visual_kind(short)
        expected_route = stem_course_contract.animation_route_descriptor(short, expected_kind)
        expected = {
            "visual_kind": expected_kind,
            "route_key": expected_route.get("route_key"),
            "semantic_mode": expected_route.get("semantic_mode", ""),
            "status": "supported" if expected_route.get("supported") else "unsupported",
        }
        mismatches = [
            field
            for field, value in expected.items()
            if support.get(field) != value
        ]
        if mismatches:
            self.fail(
                "scene.visual-routing",
                f"Short {short.get('index', '?')} animation-plan semantic_support has stale {', '.join(mismatches)}.",
                scene,
                fix="Regenerate the animation plan and scene from the current semantic route.",
            )

        plan_kind = str(support.get("visual_kind") or "")
        plan_route = str(support.get("route_key") or "")
        try:
            scene_source = scene.read_text(encoding="utf-8", errors="replace")
        except OSError:
            scene_source = ""
        scene_route_match = re.search(r"renderer_route_key\s*=\s*['\"]([^'\"]+)['\"]", scene_source)
        declared_route = scene_route_match.group(1) if scene_route_match else ""
        scene_values = {
            "visual_kind assignment": declared_visual_kind,
            "visual_kind metadata": metadata.get("visual_kind", ""),
            "route assignment": declared_route,
            "route metadata": metadata.get("route_key", ""),
        }
        stale_fields = [
            label
            for label, value in scene_values.items()
            if value != (plan_kind if "visual_kind" in label else plan_route)
        ]
        if stale_fields:
            self.fail(
                "scene.visual-routing",
                f"Short {short.get('index', '?')} scene does not exactly match animation-plan semantic_support: {', '.join(stale_fields)}.",
                scene,
                fix="Regenerate the scene from its current animation plan.",
            )
        scene_relative = self.display_path(scene) or str(scene)
        for message in semantic_scene_contract_errors(short, animation_plan, scene_source):
            self.fail(
                "scene.semantic-identity",
                f"Course {self.course_title!r} / short {short.get('index', '?')} "
                f"({short.get('concept', '')!r}) / artifacts short_plan.json ↔ animation plan ↔ "
                f"{scene_relative}: {message}.",
                scene,
                fix="Regenerate the scene/runtime contract from the validated animation plan.",
            )

    def validate_scene_animation_plan_link(self, short: dict[str, Any], scene: Path) -> None:
        if not scene.exists():
            return
        expected = str(short.get("animation_plan_artifact_fingerprint", "")).strip()
        text = scene.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"animation_plan_fingerprint=([0-9a-f]{64})", text)
        actual = match.group(1) if match else ""
        if not expected or not actual:
            self.animation_plan_issue(
                "scene.animation-plan",
                f"Scene for short {short.get('index', '?')} does not embed its animation-plan fingerprint.",
                scene,
                fix="Regenerate scenes with `python tools/stem_course.py manim --run <run>` after storyboarding.",
            )
        elif actual != expected:
            self.animation_plan_issue(
                "scene.animation-plan",
                f"Scene for short {short.get('index', '?')} was generated from a stale animation plan.",
                scene,
                fix="Regenerate scenes after rerunning the storyboard stage.",
            )

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
            if isinstance(item.get("animation_plan"), dict):
                continue
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

    def detect_repeated_scene_sources(
        self,
        sources: list[tuple[Path, str]],
        scene_visuals: list[dict[str, Any]] | None = None,
    ) -> None:
        structured_paths: set[Path] = set()
        signature_groups: dict[tuple[object, ...], list[dict[str, Any]]] = {}
        for item in scene_visuals or []:
            animation_plan = item.get("animation_plan")
            path = item.get("path")
            if not isinstance(animation_plan, dict) or not isinstance(path, Path):
                continue
            structured_paths.add(path)
            signature_groups.setdefault(scene_causal_signature(animation_plan), []).append(item)

        severity = self.warn if self.draft else self.fail
        for group in signature_groups.values():
            concepts = {str(item.get("concept") or "").strip().casefold() for item in group}
            if len(concepts) < 2:
                continue
            labels = ", ".join(repr(item.get("concept")) for item in group)
            severity(
                "scene.repetition",
                f"Distinct concepts collapse to the same structural causal signature: {labels}.",
                group[0]["path"],
                fix="Give each concept a distinct renderer variant, model scenario, persistent roles, transitions, or required figure evidence.",
            )

        legacy_sources = [(path, source) for path, source in sources if path not in structured_paths]
        for i, (left_path, left_text) in enumerate(legacy_sources):
            for right_path, right_text in legacy_sources[i + 1 :]:
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
        self.index_intentional_silence(shorts, render_report)

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
            self.validate_narration_timing_contracts(shorts, render_report)
        elif any(path.is_file() for path in (self.run / "videos").glob("*_final.mp4")):
            self.fail(
                "audio.evidence",
                "Final render exists without render_report.json, so voice_engine and timing evidence cannot be verified.",
                self.run / "render_report.json",
            )

    def index_intentional_silence(self, shorts: list[dict[str, Any]], report: Any) -> None:
        self.silent_final_paths.clear()
        if not isinstance(report, dict):
            return
        results = report.get("results")
        if not isinstance(results, list):
            return

        silent_by_index: dict[int, dict[str, Any]] = {}
        for result in results:
            if not isinstance(result, dict):
                continue
            voice = result.get("voiceover") if isinstance(result.get("voiceover"), dict) else {}
            index = parse_positive_int(result.get("index"))
            engine = str(voice.get("engine") or result.get("voice_engine") or report.get("voice_engine") or "").lower()
            if (
                index is not None
                and engine == "none"
            ):
                silent_by_index[index] = result

        mapped_indexes: set[int] = set()
        for short in shorts:
            index = parse_positive_int(short.get("index"))
            if index is None or index not in silent_by_index:
                continue
            concept = str(short.get("concept", f"short-{index}"))
            slug = slugify(concept)
            final = self.run / str(short.get("video_file") or f"videos/short_{index:02d}_{slug}_final.mp4")
            self.silent_final_paths.add(final.resolve())
            mapped_indexes.add(index)

        for index, result in silent_by_index.items():
            explicit_path_found = False
            for field in ("video_file", "final_video", "final_file", "output_file"):
                value = result.get(field)
                if isinstance(value, str) and value:
                    self.silent_final_paths.add((self.run / value).resolve())
                    explicit_path_found = True
            if index not in mapped_indexes and not explicit_path_found:
                matches = list((self.run / "videos").glob(f"short_{index:02d}_*_final.mp4"))
                if len(matches) == 1:
                    self.silent_final_paths.add(matches[0].resolve())

    def intentional_silence_for(self, path: Path) -> bool:
        return path.resolve() in self.silent_final_paths

    def validate_narration_timing_contracts(self, shorts: list[dict[str, Any]], report: Any) -> None:
        """Fail closed unless every voiced render has hash-bound, per-beat timing evidence."""
        if not isinstance(report, dict) or not isinstance(report.get("results"), list):
            return
        shorts_by_index = {
            index: short
            for short in shorts
            if (index := parse_positive_int(short.get("index"))) is not None
        }
        for result in report["results"]:
            if not isinstance(result, dict):
                continue
            index = parse_positive_int(result.get("index"))
            voice = result.get("voiceover") if isinstance(result.get("voiceover"), dict) else {}
            engine = str(
                voice.get("engine")
                or result.get("voice_engine")
                or report.get("voice_engine")
                or ""
            ).strip().lower()
            if engine == "none":
                continue
            status = str(voice.get("status") or "").strip().lower()
            voiced = (
                engine not in {"", "none"}
                or status in {"ok", "rendered"}
                or str(result.get("status") or "").lower() == "rendered"
            )
            if not voiced:
                if status == "skipped":
                    self.fail(
                        "audio.evidence",
                        f"Short {index or '?'} skipped voiceover without explicitly recording voice_engine=none.",
                        self.run / "render_report.json",
                    )
                continue
            short = shorts_by_index.get(index or -1)
            if short is None:
                self.fail("audio.evidence", f"Voiced render short {index or '?'} has no matching short plan.", self.run / "render_report.json")
                continue
            manifest, manifest_path = self.locate_narration_manifest(index or 0, result, voice)
            if manifest is None:
                self.fail(
                    "audio.evidence",
                    f"Voiced short {index:02d} has no narration_timing/report manifest.",
                    manifest_path,
                    fix="Regenerate Piper narration and retain its hash-bound timing manifest.",
                )
                continue
            self.validate_narration_manifest(index or 0, short, result, voice, manifest, manifest_path)

        result_indexes = {
            value
            for result in report["results"]
            if isinstance(result, dict) and (value := parse_positive_int(result.get("index"))) is not None
        }
        for index, short in shorts_by_index.items():
            if index in result_indexes:
                continue
            final_path = self._result_media_path(index, short, {}, {}, audio=False)
            if final_path is not None:
                self.fail(
                    "audio.evidence",
                    f"Final short {index:02d} has no render-report result or voice_engine evidence.",
                    self.run / "render_report.json",
                )

    def locate_narration_manifest(
        self,
        index: int,
        result: dict[str, Any],
        voice: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, Path]:
        if isinstance(voice.get("beats"), list):
            return voice, self.run / "render_report.json"
        for payload in (voice, result):
            for field in ("narration_timing", "timing_manifest", "voiceover_report", "report"):
                embedded = payload.get(field)
                if isinstance(embedded, dict) and isinstance(embedded.get("beats"), list):
                    return embedded, self.run / "render_report.json"
        field_names = (
            "narration_timing", "narration_timing_file", "timing_manifest",
            "timing_manifest_file", "voiceover_report", "report_manifest", "report_file", "report",
        )
        candidates: list[Path] = []
        for payload in (voice, result):
            for field in field_names:
                value = payload.get(field)
                if isinstance(value, str) and value.strip():
                    candidates.append(self.run / value)
        if not candidates:
            patterns = (
                f"**/*{index:02d}*narration*timing*.json",
                f"**/*{index:02d}*voiceover*report*.json",
                f"**/*{index:02d}*timing*.json",
            )
            for pattern in patterns:
                candidates.extend(sorted(self.run.glob(pattern)))
        candidates = list(dict.fromkeys(path.resolve() for path in candidates))
        fallback = candidates[0] if candidates else self.run / f"audio/short_{index:02d}_narration_timing.json"
        for path in candidates:
            try:
                path.relative_to(self.run)
            except ValueError:
                continue
            payload = self.load_json(path, required=False)
            if isinstance(payload, dict) and isinstance(payload.get("beats"), list):
                return payload, path
        return None, fallback

    def _result_media_path(
        self,
        index: int,
        short: dict[str, Any],
        result: dict[str, Any],
        voice: dict[str, Any],
        *,
        audio: bool,
    ) -> Path | None:
        fields = (
            ("audio_file", "voice_file", "voiceover_file", "narration_audio", "output_wav", "path")
            if audio
            else ("video_file", "final_video", "final_file", "output_file")
        )
        payloads = (voice, result) if audio else (result, short)
        for payload in payloads:
            for field in fields:
                value = payload.get(field)
                if isinstance(value, str) and value.strip():
                    path = (self.run / value).resolve()
                    if path.exists():
                        return path
        if audio:
            matches = [
                path for path in self.run.glob(f"**/short_{index:02d}_*")
                if path.is_file() and path.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac"}
            ]
        else:
            matches = list((self.run / "videos").glob(f"short_{index:02d}_*_final.mp4"))
        return matches[0].resolve() if len(matches) == 1 else None

    def validate_narration_manifest(
        self,
        index: int,
        short: dict[str, Any],
        result: dict[str, Any],
        voice: dict[str, Any],
        manifest: dict[str, Any],
        manifest_path: Path,
    ) -> None:
        plan_path = (self.run / str(short.get("animation_plan_file") or f"{ANIMATION_PLAN_DIRECTORY}/short_{index:02d}.json")).resolve()
        audio_path = self._result_media_path(index, short, result, voice, audio=True)
        video_path = self._result_media_path(index, short, result, voice, audio=False)
        if not plan_path.exists() or audio_path is None or video_path is None:
            missing = [name for name, path in (("plan", plan_path if plan_path.exists() else None), ("audio", audio_path), ("video", video_path)) if path is None]
            self.fail("audio.evidence", f"Short {index:02d} timing evidence cannot locate current {', '.join(missing)} artifact(s).", manifest_path)
            return
        plan = self.load_json(plan_path, required=False)
        if not isinstance(plan, dict):
            self.fail("audio.timing", f"Short {index:02d} animation plan is unreadable for timing validation.", plan_path)
            return

        expected_hashes = {
            "plan": {file_sha256(plan_path), canonical_json_hash(plan)},
            "audio": {file_sha256(audio_path)},
            "video": {file_sha256(video_path)},
        }
        hash_names = {
            "plan": ("plan_sha256", "animation_plan_sha256", "plan_hash", "animation_plan_hash"),
            "audio": ("audio_sha256", "narration_audio_sha256", "audio_hash", "voiceover_sha256"),
            "video": ("video_sha256", "final_video_sha256", "video_hash", "final_mp4_sha256"),
        }
        for role, aliases in hash_names.items():
            recorded = ""
            for payload in (manifest, voice, result):
                value = nested_value(payload, *aliases)
                if value is not None:
                    recorded = str(value).lower()
                    break
            if recorded not in expected_hashes[role]:
                self.fail("audio.hash", f"Short {index:02d} has a missing or stale current {role} SHA-256.", manifest_path)

        engine = str(manifest.get("engine") or voice.get("engine") or result.get("voice_engine") or "").lower()
        evidence_payloads = (manifest, voice, result)
        model_id = next((value for payload in evidence_payloads if (value := nested_value(payload, "model_id", "voice_model")) is not None), None)
        version = next((value for payload in evidence_payloads if (value := nested_value(payload, "piper_tts_version", "piper_version", "engine_version")) is not None), None)
        provenance = next(
            (
                value
                for payload in evidence_payloads
                if (value := nested_value(payload, "model_sha256", "model_hash", "model_files", "model_hashes", "model_assets", "files")) is not None
            ),
            None,
        )
        provenance_text = json.dumps(provenance, sort_keys=True) if provenance is not None else ""
        if engine != "piper" or not str(model_id or "").strip() or not str(version or "").strip() or not re.search(r"[0-9a-fA-F]{64}", provenance_text):
            self.fail("audio.provenance", f"Short {index:02d} lacks Piper model/version/hash provenance.", manifest_path)

        planned_beats = plan.get("beats") if isinstance(plan.get("beats"), list) else []
        timed_beats = manifest.get("beats") if isinstance(manifest.get("beats"), list) else []
        planned_ids = [str(beat.get("id", "")) for beat in planned_beats if isinstance(beat, dict)]
        timed_ids = [str(beat.get("beat_id", beat.get("id", ""))) for beat in timed_beats if isinstance(beat, dict)]
        if not planned_ids or timed_ids != planned_ids:
            self.fail("audio.beats", f"Short {index:02d} timing beat IDs do not exactly match plan order.", manifest_path)
        elif len(timed_beats) == len(planned_beats):
            self.validate_beat_boundaries(index, planned_beats, timed_beats, manifest, manifest_path)

        manifest_rate = int(parse_float(manifest.get("sample_rate")))
        manifest_channels = int(parse_float(manifest.get("channels")))
        total_frames = parse_positive_int(manifest.get("total_frames"))
        if manifest_rate != PIPER_SAMPLE_RATE or manifest_channels != PIPER_CHANNELS or total_frames is None:
            self.fail("audio.profile", f"Short {index:02d} timing manifest must record 48kHz mono and total_frames.", manifest_path)
        elif timed_beats and isinstance(timed_beats[-1], dict) and total_frames != parse_positive_int(timed_beats[-1].get("beat_end_frame")):
            self.fail("audio.boundaries", f"Short {index:02d} total_frames does not equal the final beat boundary.", manifest_path)

        audio_metadata = self.probe_media(audio_path)
        final_metadata = self.video_cache.get(video_path) or self.probe_media(video_path)
        self.video_cache[video_path] = final_metadata
        for label, metadata in (("narration", audio_metadata), ("final", final_metadata)):
            if int(parse_float(metadata.get("audio_sample_rate"))) != PIPER_SAMPLE_RATE or int(parse_float(metadata.get("audio_channels"))) != PIPER_CHANNELS:
                self.fail("audio.profile", f"Short {index:02d} {label} audio must be 48kHz mono.", audio_path if label == "narration" else video_path)
        if total_frames is not None and abs(parse_float(audio_metadata.get("audio_duration")) - total_frames / PIPER_SAMPLE_RATE) > 1.0 / PIPER_SAMPLE_RATE:
            self.fail("audio.boundaries", f"Short {index:02d} narration duration does not match total_frames.", audio_path)
        if str(final_metadata.get("audio_codec_name") or "").lower() != "aac":
            self.fail("audio.codec", f"Short {index:02d} final audio stream is not AAC.", video_path)
        frame_rate = parse_float(final_metadata.get("frame_rate"))
        frame_duration = 1.0 / frame_rate if frame_rate > 0 else 0.0
        av_delta = abs(parse_float(final_metadata.get("video_duration") or final_metadata.get("duration")) - parse_float(final_metadata.get("audio_duration")))
        if frame_duration <= 0 or av_delta > frame_duration + 0.001:
            self.fail("audio.av-sync", f"Short {index:02d} final A/V delta {av_delta:.3f}s exceeds one video frame.", video_path)

        sync = result.get("sync") if isinstance(result.get("sync"), dict) else {}
        extension_fields = (
            "video_pad_seconds", "audio_pad_seconds", "final_video_pad_seconds",
            "frozen_extension_seconds", "frozen_video_extension_seconds",
            "freeze_extension_seconds", "clone_pad_seconds",
        )
        meaningful: dict[str, float] = {}
        for payload in (sync, result, manifest):
            for field in extension_fields:
                value = parse_float(payload.get(field))
                if value > MAX_MEANINGFUL_EXTENSION_SECONDS:
                    meaningful[field] = value
        if meaningful:
            self.fail("audio.extension", f"Short {index:02d} uses meaningful pad/frozen extension: {', '.join(meaningful)}.", self.run / "render_report.json")
        self.validate_audio_levels(index, manifest, manifest_path)

    def validate_beat_boundaries(
        self,
        index: int,
        planned: list[Any],
        timed: list[Any],
        manifest: dict[str, Any],
        manifest_path: Path,
    ) -> None:
        sample_rate = int(parse_float(manifest.get("sample_rate"))) or PIPER_SAMPLE_RATE
        previous_end: float | None = None
        duration_drift = 0.0
        max_error = 0.0
        for plan_beat, timed_beat in zip(planned, timed):
            if not isinstance(plan_beat, dict) or not isinstance(timed_beat, dict):
                self.fail("audio.beats", f"Short {index:02d} contains a non-object timing beat.", manifest_path)
                return
            planned_start = parse_float(plan_beat.get("start_seconds"))
            planned_end = parse_float(plan_beat.get("end_seconds"))
            missing_fields = [field for field in ("beat_start", "beat_end", "beat_start_frame", "beat_end_frame") if field not in timed_beat]
            if missing_fields:
                self.fail("audio.boundaries", f"Short {index:02d} beat lacks exact boundary fields: {', '.join(missing_fields)}.", manifest_path)
                return
            actual_start = parse_float(timed_beat.get("beat_start", timed_beat.get("start_seconds")))
            actual_end = parse_float(timed_beat.get("beat_end", timed_beat.get("end_seconds")))
            if "beat_start_frame" in timed_beat and abs(actual_start - parse_float(timed_beat["beat_start_frame"]) / sample_rate) > 0.5 / sample_rate:
                self.fail("audio.boundaries", f"Short {index:02d} beat frame/start boundary is not exact.", manifest_path)
            if "beat_end_frame" in timed_beat and abs(actual_end - parse_float(timed_beat["beat_end_frame"]) / sample_rate) > 0.5 / sample_rate:
                self.fail("audio.boundaries", f"Short {index:02d} beat frame/end boundary is not exact.", manifest_path)
            if actual_end <= actual_start or (previous_end is not None and actual_start < previous_end - 0.5 / sample_rate):
                self.fail("audio.boundaries", f"Short {index:02d} timing boundaries overlap or are unordered.", manifest_path)
            if previous_end is not None and abs(actual_start - previous_end) > 0.5 / sample_rate:
                self.fail("audio.boundaries", f"Short {index:02d} timing boundaries are not contiguous.", manifest_path)
            max_error = max(max_error, abs(actual_start - planned_start), abs(actual_end - planned_end))
            duration_drift += abs((actual_end - actual_start) - (planned_end - planned_start))
            previous_end = actual_end
        if max_error > MAX_BEAT_BOUNDARY_ERROR_SECONDS + 1e-9:
            self.fail("audio.boundaries", f"Short {index:02d} maximum beat boundary error is {max_error:.3f}s (>100ms).", manifest_path)
        if duration_drift > MAX_CUMULATIVE_DRIFT_SECONDS + 1e-9:
            self.fail("audio.drift", f"Short {index:02d} cumulative beat drift is {duration_drift:.3f}s (>150ms).", manifest_path)

    def validate_audio_levels(self, index: int, manifest: dict[str, Any], path: Path) -> None:
        levels = manifest.get("levels") if isinstance(manifest.get("levels"), dict) else {}
        checks = (
            (("sample_peak_dbfs",), MAX_SAMPLE_PEAK_DBFS, "sample peak", "max"),
            (("true_peak_dbfs", "input_tp"), MAX_TRUE_PEAK_DBFS, "true peak", "max"),
        )
        for aliases, threshold, label, _ in checks:
            value = nested_value(levels, *aliases)
            if value is not None and parse_float(value) > threshold:
                self.fail("audio.levels", f"Short {index:02d} {label} {parse_float(value):.2f} dBFS exceeds {threshold:.1f} dBFS.", path)
        loudness = nested_value(levels, "integrated_lufs", "input_i")
        if loudness is not None and not MIN_INTEGRATED_LUFS <= parse_float(loudness) <= MAX_INTEGRATED_LUFS:
            self.fail("audio.levels", f"Short {index:02d} integrated loudness {parse_float(loudness):.2f} LUFS is outside -24 to -12 LUFS.", path)

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
            plan_sync = result.get("plan_sync")
            if not isinstance(plan_sync, dict):
                self.fail(
                    "render-report.plan-sync",
                    f"Render result for short {result.get('index')} does not record semantic-plan duration sync.",
                    self.run / "render_report.json",
                    fix="Rerun rendering with the current skill so planned and raw Manim durations are compared before finalization.",
                )
            elif plan_sync.get("status") != "ok":
                self.fail(
                    "render-report.plan-sync",
                    f"Raw Manim duration {parse_float(plan_sync.get('rendered_duration')):.1f}s does not match the semantic plan {parse_float(plan_sync.get('planned_duration')):.1f}s.",
                    self.run / "render_report.json",
                    fix="Add meaningful scene choreography/read time; never redefine the planned duration to whatever Manim emitted.",
                )
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
                target = parse_float(sync.get("target_duration")) or max(raw, voice_dur)
                tolerance = max(0.75, target * 0.03)
                if target > 0 and abs(final - target) > tolerance:
                    self.fail("render-report.sync", f"Final video {final:.1f}s does not match the aligned media target {target:.1f}s.", self.run / "render_report.json", fix="Pad the shorter stream to max(raw video, voiceover) and mux without `-shortest`.")
                if raw > 0 and voice_dur > 0:
                    expected_video_pad = max(0.0, voice_dur - raw)
                    expected_audio_pad = max(0.0, raw - voice_dur)
                    recorded_video_pad = parse_float(sync.get("video_pad_seconds"))
                    recorded_audio_pad = parse_float(sync.get("audio_pad_seconds"))
                    if abs(recorded_video_pad - expected_video_pad) > 0.2 or abs(recorded_audio_pad - expected_audio_pad) > 0.2:
                        self.fail("render-report.sync", "Recorded media padding does not explain the raw video/voiceover duration difference.", self.run / "render_report.json", fix="Clone-pad video when narration is longer and audio-pad when narration is shorter; record both durations.")
                if parse_float(sync.get("audio_truncated_seconds")) > 0.05:
                    self.fail("render-report.sync", "Finalization truncated narration.", self.run / "render_report.json", fix="Use the longest input duration as the mux target and never use a shorter `-t` or `-shortest`.")

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
        settings = report.get("settings") if isinstance(report.get("settings"), dict) else {}
        contact_interval = parse_float(settings.get("contact_sheet_interval_seconds"))
        if contact_interval <= 0 or contact_interval > MAX_CONTACT_SHEET_INTERVAL_SECONDS:
            self.fail(
                "visual-audit.sampling",
                "Contact-sheet evidence must sample the complete video at least every 0.5 seconds.",
                report_path,
                fix="Rerun `python tools/audit_video_frames.py <run> --interval 0.5` after the final encode.",
            )
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
            coverage = item.get("contact_sheet_coverage") if isinstance(item.get("contact_sheet_coverage"), dict) else {}
            if coverage.get("covers_entire_video") is not True:
                self.fail(
                    "visual-audit.coverage",
                    f"Contact sheets do not cover the entire duration of {video_rel or 'a video'}.",
                    report_path,
                    fix="Rerun the frame audit on the exact complete final MP4.",
                )

            metrics = item.get("metrics")
            if not isinstance(metrics, dict):
                self.fail("visual-audit", f"No frame metrics recorded for {video_rel or 'a video'}.", report_path)
                continue
            sampled = int(parse_float(metrics.get("sampled_frames")))
            if sampled < 3:
                self.warn("visual-audit", f"Only {sampled} frame(s) sampled for {video_rel or 'a video'}.", report_path)
            flags_value = metrics.get("review_flags")
            flags = [str(flag) for flag in flags_value] if isinstance(flags_value, list) else []
            serious_value = metrics.get("serious_review_flags")
            if isinstance(serious_value, list):
                serious_flags = [str(flag) for flag in serious_value]
            else:
                # Backward compatibility for reports emitted before explicit
                # severity was persisted alongside review flags.
                serious_flags = [flag for flag in flags if flag in SERIOUS_VISUAL_AUDIT_FLAGS]
            serious_flags = list(dict.fromkeys(serious_flags))
            review_only_flags = [flag for flag in flags if flag not in serious_flags]
            if serious_flags:
                severity = self.warn if self.draft else self.fail
                severity(
                    "visual-audit",
                    f"Frame audit found publish-blocking issues in {video_rel or 'a video'}: {', '.join(serious_flags)}.",
                    report_path,
                    fix="Inspect the recorded OCR/layout findings and contact sheet, patch the visual family, rerender, and rerun `tools/audit_video_frames.py`.",
                )
            if review_only_flags:
                self.warn(
                    "visual-audit",
                    f"Frame audit recommends review of {video_rel or 'a video'} for {', '.join(review_only_flags)}.",
                    report_path,
                    fix="Inspect the contact sheet and OCR findings before publishing.",
                )

            ocr_metrics = metrics.get("ocr_text_layout")
            if not isinstance(ocr_metrics, dict):
                self.warn(
                    "visual-audit.ocr",
                    f"Rendered-text OCR/layout metrics are missing for {video_rel or 'a video'}.",
                    report_path,
                    fix="Rerun `tools/audit_video_frames.py`; install Tesseract for rendered-text checks.",
                )
            elif not bool(ocr_metrics.get("available")):
                errors = ocr_metrics.get("errors")
                detail = f" ({str(errors[0])[:160]})" if isinstance(errors, list) and errors else ""
                self.warn(
                    "visual-audit.ocr",
                    f"Rendered-text OCR/layout checks were unavailable for {video_rel or 'a video'}{detail}.",
                    report_path,
                    fix="Install Tesseract and rerun `tools/audit_video_frames.py`.",
                )
            elif int(parse_float(ocr_metrics.get("sampled_frames"))) < 2:
                self.warn(
                    "visual-audit.ocr",
                    f"Too few OCR frames were sampled for {video_rel or 'a video'}.",
                    report_path,
                    fix="Rerun the frame audit on the complete render.",
                )

        for final in final_videos:
            try:
                rel = str(final.relative_to(self.run))
            except ValueError:
                rel = str(final)
            if rel not in audited:
                self.warn("visual-audit", f"Final video {final.name} is not represented in visual_frame_audit.json.", report_path)

    def visual_review_issue(self, area: str, message: str, path: Path, *, fix: str | None = None) -> None:
        severity = self.warn if self.draft else self.fail
        severity(area, message, path, fix=fix)

    def load_render_runtime_trace(
        self,
        expected_index_fingerprint: str,
    ) -> dict[int, dict[str, Any]] | None:
        trace_path = self.run / RENDER_RUNTIME_TRACE_NAME
        producer_fix = (
            "Producer-side integration is required: instrument the render path in tools/stem_course.py to emit "
            f"{RENDER_RUNTIME_TRACE_NAME} from renderer-executed state transitions; do not synthesize it during review."
        )
        if not trace_path.exists():
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"{RENDER_RUNTIME_TRACE_NAME} is missing; strict review requires hash-bound renderer runtime evidence. "
                "The render producer does not emit this artifact yet.",
                trace_path,
                fix=producer_fix,
            )
            return None
        try:
            payload = json.loads(trace_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"{RENDER_RUNTIME_TRACE_NAME} is unreadable: {exc}.",
                trace_path,
                fix=producer_fix,
            )
            return None
        if not isinstance(payload, dict):
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"{RENDER_RUNTIME_TRACE_NAME} must be a JSON object.",
                trace_path,
                fix=producer_fix,
            )
            return None
        invalid_reasons: list[str] = []
        if payload.get("schema_version") != RENDER_RUNTIME_TRACE_SCHEMA_VERSION:
            invalid_reasons.append(f"schema_version must be {RENDER_RUNTIME_TRACE_SCHEMA_VERSION!r}")
        if payload.get("animation_plan_index_fingerprint") != expected_index_fingerprint:
            invalid_reasons.append("animation_plan_index_fingerprint is missing or stale")
        raw_renders = payload.get("renders")
        if not isinstance(raw_renders, list):
            invalid_reasons.append("renders must be an array")
            raw_renders = []
        rows: dict[int, dict[str, Any]] = {}
        for row in raw_renders:
            if not isinstance(row, dict):
                invalid_reasons.append("every render trace row must be an object")
                continue
            short_index = parse_positive_int(row.get("short_index"))
            if short_index is None:
                invalid_reasons.append("every render trace row needs a positive short_index")
            elif short_index in rows:
                invalid_reasons.append(f"short {short_index:02d} has duplicate render trace rows")
            else:
                rows[short_index] = row
        if invalid_reasons:
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"{RENDER_RUNTIME_TRACE_NAME} violates its contract: {'; '.join(invalid_reasons[:4])}.",
                trace_path,
                fix=producer_fix,
            )
            return None
        return rows

    def validate_render_runtime_trace_row(
        self,
        row: dict[str, Any] | None,
        *,
        index: int,
        video_file: str,
        video_hash: str,
        plan_fingerprint: str,
        expected_contracts: list[dict[str, Any]],
        remediation: str,
    ) -> set[tuple[str, str]]:
        trace_path = self.run / RENDER_RUNTIME_TRACE_NAME
        if row is None:
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"Short {index:02d} has no renderer runtime trace row.",
                trace_path,
                fix=remediation,
            )
            return set()
        stale_fields = [
            field
            for field, expected in (
                ("video_file", video_file),
                ("video_sha256", video_hash),
                ("animation_plan_fingerprint", plan_fingerprint),
            )
            if row.get(field) != expected
        ]
        if stale_fields:
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"Short {index:02d} runtime trace has stale hash/path fields: {', '.join(stale_fields)}.",
                trace_path,
                fix=remediation,
            )
            return set()

        expected_keys = [
            (str(contract["beat_id"]), str(contract["planned_transition_id"]))
            for contract in expected_contracts
        ]
        expected_by_key = dict(zip(expected_keys, expected_contracts))
        semantic_contract = any(beat_id != transition_id for beat_id, transition_id in expected_keys)
        event_field = "semantic_transition_events" if semantic_contract else "transitions"
        raw_events = row.get(event_field)
        errors: list[str] = []
        if not isinstance(raw_events, list):
            errors.append(f"{event_field} must be an array")
            events: list[Any] = []
        else:
            events = raw_events

        callback_counts: dict[tuple[str, str], int] = {}
        if semantic_contract:
            raw_bindings = row.get("semantic_transition_bindings")
            if not isinstance(raw_bindings, list):
                errors.append("semantic_transition_bindings must be an array")
                bindings: list[Any] = []
            else:
                bindings = raw_bindings
            binding_keys: list[tuple[str, str]] = []
            seen_binding_keys: set[tuple[str, str]] = set()
            for position, binding in enumerate(bindings, start=1):
                key = (
                    str(binding.get("beat_id", "")) if isinstance(binding, dict) else "",
                    str(binding.get("planned_transition_id", "")) if isinstance(binding, dict) else "",
                )
                binding_keys.append(key)
                if not isinstance(binding, dict):
                    errors.append(f"semantic binding {position}: entry is not an object")
                    continue
                if key not in expected_by_key:
                    errors.append(f"semantic binding {position}: transition {key[1]!r} is not planned")
                    continue
                if key in seen_binding_keys:
                    errors.append(f"semantic binding {position}: duplicates planned transition {key[1]!r}")
                    continue
                seen_binding_keys.add(key)
                registered_count = binding.get("registered_callback_count")
                executed_count = binding.get("executed_callback_count")
                successful_count = binding.get("successful_callback_count")
                if (
                    type(registered_count) is not int
                    or registered_count <= 0
                    or type(executed_count) is not int
                    or type(successful_count) is not int
                    or executed_count != registered_count
                    or successful_count != registered_count
                    or binding.get("status") != "ok"
                ):
                    errors.append(
                        f"semantic binding {position}: callbacks were not registered, executed, and successful exactly once each"
                    )
                    continue
                callback_counts[key] = registered_count
            missing_bindings = set(expected_keys) - seen_binding_keys
            if missing_bindings:
                labels = ", ".join(
                    transition_id
                    for beat_id, transition_id in expected_keys
                    if (beat_id, transition_id) in missing_bindings
                )
                errors.append(f"semantic callback bindings omit planned transitions ({labels})")
            if binding_keys != expected_keys:
                errors.append("semantic callback bindings are not in planned transition order")

        valid_keys: set[tuple[str, str]] = set()
        event_keys: list[tuple[str, str]] = []
        for position, event in enumerate(events, start=1):
            key = (
                str(event.get("beat_id", "")) if isinstance(event, dict) else "",
                str(event.get("planned_transition_id", "")) if isinstance(event, dict) else "",
            )
            event_keys.append(key)
            error = structured_state_change_error(event, expected_by_key.get(key), runtime_event=True)
            if error is not None:
                errors.append(f"event {position}: {error}")
            elif key in valid_keys:
                errors.append(f"event {position}: duplicates planned transition {key[1]!r}")
            elif semantic_contract:
                callback_error = semantic_runtime_event_error(event, expected_by_key[key], callback_counts.get(key))
                if callback_error is not None:
                    errors.append(f"event {position}: {callback_error}")
                else:
                    valid_keys.add(key)
            else:
                valid_keys.add(key)
        if event_keys != expected_keys:
            errors.append(f"{event_field} are not in exact planned transition order")
        missing_keys = set(expected_by_key) - valid_keys
        if errors:
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"Short {index:02d} runtime trace contains invalid transition evidence: {'; '.join(errors[:3])}.",
                trace_path,
                fix=remediation,
            )
        if missing_keys:
            missing_labels = ", ".join(sorted(transition_id for _, transition_id in missing_keys)[:4])
            self.visual_review_issue(
                "visual-review.runtime-trace",
                f"Short {index:02d} runtime trace omits {len(missing_keys)} planned transitions ({missing_labels}).",
                trace_path,
                fix=remediation,
            )
        return valid_keys

    def validate_visual_review(self, plan: Any) -> None:
        shorts = plan_shorts(plan)
        final_videos = sorted((self.run / "videos").glob("*_final.mp4"))
        if not shorts or (not final_videos and not self.render_outputs_expected(shorts)):
            return
        review_path = self.run / VISUAL_REVIEW_NAME
        remediation = (
            "Run `python tools/stem_course.py visual-review --run <run>`, actually inspect every evidence window, "
            "then record each planned_transition_id with changed_attribute='state', exact persistent_object_ids, "
            "object-keyed observed_before/observed_after maps, matching frame references, and the reviewer verdict."
        )
        if not review_path.exists():
            self.visual_review_issue(
                "visual-review.missing",
                "visual_review.json is missing; automated frame metrics are triage and do not prove temporal review.",
                review_path,
                fix=remediation,
            )
            return
        try:
            payload = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.visual_review_issue("visual-review.invalid", f"visual_review.json is unreadable: {exc}.", review_path, fix=remediation)
            return
        if not isinstance(payload, dict):
            self.visual_review_issue("visual-review.invalid", "visual_review.json must be a JSON object.", review_path, fix=remediation)
            return
        if payload.get("schema_version") != VISUAL_REVIEW_SCHEMA_VERSION:
            self.visual_review_issue(
                "visual-review.invalid",
                f"Visual review schema must be {VISUAL_REVIEW_SCHEMA_VERSION!r}.",
                review_path,
                fix=remediation,
            )
        index_path = self.run / ANIMATION_PLAN_INDEX_NAME
        if not index_path.exists():
            self.visual_review_issue("visual-review.stale", "Visual review cannot be tied to a missing animation plan index.", review_path, fix=remediation)
            return
        try:
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.visual_review_issue("visual-review.stale", "Visual review cannot be tied to an invalid animation plan index.", review_path, fix=remediation)
            return
        expected_index_fingerprint = canonical_json_hash(index_payload)
        if payload.get("animation_plan_index_fingerprint") != expected_index_fingerprint:
            self.visual_review_issue(
                "visual-review.stale",
                "Visual review was completed against a different animation plan index.",
                review_path,
                fix=remediation,
            )
        runtime_trace_rows = self.load_render_runtime_trace(expected_index_fingerprint)
        raw_reviews = payload.get("reviews") if isinstance(payload.get("reviews"), list) else []
        reviews: dict[int, dict[str, Any]] = {}
        for review in raw_reviews:
            if not isinstance(review, dict):
                continue
            index = parse_positive_int(review.get("short_index"))
            if index is not None:
                reviews[index] = review

        for short in shorts:
            index = parse_positive_int(short.get("index"))
            if index is None:
                continue
            concept = str(short.get("concept", f"short-{index}"))
            slug = slugify(concept)
            video_file = str(short.get("video_file") or f"videos/short_{index:02d}_{slug}_final.mp4")
            relative_video = Path(video_file)
            if relative_video.is_absolute() or ".." in relative_video.parts:
                self.visual_review_issue("visual-review.path", f"Short {index:02d} review uses an unsafe video path.", review_path, fix=remediation)
                continue
            video_path = self.run / relative_video
            if not video_path.exists():
                continue
            review = reviews.get(index)
            if review is None:
                self.visual_review_issue(
                    "visual-review.missing",
                    f"Short {index:02d} has no temporal review entry.",
                    review_path,
                    fix=remediation,
                )
                continue
            if review.get("video_file") != video_file:
                self.visual_review_issue(
                    "visual-review.stale",
                    f"Short {index:02d} review points to a different final video.",
                    review_path,
                    fix=remediation,
                )
            current_video_hash = file_sha256(video_path)
            recorded_video_hash = str(review.get("video_sha256", ""))
            if not re.fullmatch(r"[0-9a-f]{64}", recorded_video_hash) or recorded_video_hash != current_video_hash:
                self.visual_review_issue(
                    "visual-review.video-hash",
                    f"Short {index:02d} review has a missing or stale final-video hash.",
                    review_path,
                    fix=remediation,
                )

            plan_file = str(short.get("animation_plan_file") or f"{ANIMATION_PLAN_DIRECTORY}/short_{index:02d}.json")
            animation_plan_path = self.run / plan_file
            if not animation_plan_path.exists():
                continue
            try:
                animation_plan = json.loads(animation_plan_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(animation_plan, dict):
                continue
            plan_fingerprint = animation_plan_artifact_fingerprint(animation_plan)
            if review.get("animation_plan_fingerprint") != plan_fingerprint:
                self.visual_review_issue(
                    "visual-review.stale",
                    f"Short {index:02d} review was completed against a different animation plan.",
                    review_path,
                    fix=remediation,
                )
            expected_change_contracts = planned_state_change_contracts(animation_plan)
            expected_change_by_key = {
                (str(contract["beat_id"]), str(contract["planned_transition_id"])): contract
                for contract in expected_change_contracts
            }
            if len(expected_change_contracts) < ANIMATION_PLAN_MIN_TRANSFORMATIONS:
                self.visual_review_issue(
                    "visual-review.changes",
                    f"Short {index:02d} animation plan exposes only {len(expected_change_contracts)} structured state deltas.",
                    review_path,
                    fix="Regenerate the storyboard with at least four object-keyed before/after transitions.",
                )
            runtime_transition_keys: set[tuple[str, str]] | None = None
            if runtime_trace_rows is not None:
                runtime_transition_keys = self.validate_render_runtime_trace_row(
                    runtime_trace_rows.get(index),
                    index=index,
                    video_file=video_file,
                    video_hash=current_video_hash,
                    plan_fingerprint=plan_fingerprint,
                    expected_contracts=expected_change_contracts,
                    remediation=(
                        "Instrument tools/stem_course.py render to record renderer-executed object state deltas and "
                        f"regenerate {RENDER_RUNTIME_TRACE_NAME} for the final video."
                    ),
                )
            continuity = animation_plan.get("continuity_spine") if isinstance(animation_plan.get("continuity_spine"), dict) else {}
            spine_ids = {str(value) for value in continuity.get("object_ids", []) if str(value)} if isinstance(continuity.get("object_ids"), list) else set()
            reviewed_spine = {str(value) for value in review.get("persistent_object_ids", []) if str(value)} if isinstance(review.get("persistent_object_ids"), list) else set()
            if not spine_ids or not spine_ids.issubset(reviewed_spine):
                self.visual_review_issue(
                    "visual-review.continuity",
                    f"Short {index:02d} review does not record every continuity-spine object.",
                    review_path,
                    fix=remediation,
                )

            expected_evidence = [
                {
                    "beat_id": row.get("beat_id"),
                    "before_seconds": row.get("before_seconds"),
                    "after_seconds": row.get("after_seconds"),
                    "persistent_object_ids": row.get("persistent_object_ids", []),
                    "expected_change": row.get("expected_change"),
                }
                for row in animation_plan.get("qa_evidence_timestamps", [])
                if isinstance(row, dict)
            ]
            actual_evidence = review.get("evidence_windows") if isinstance(review.get("evidence_windows"), list) else []
            if canonical_json_hash(actual_evidence) != canonical_json_hash(expected_evidence):
                self.visual_review_issue(
                    "visual-review.stale",
                    f"Short {index:02d} review evidence windows no longer match the animation plan.",
                    review_path,
                    fix=remediation,
                )
            evidence_by_beat = {
                str(row.get("beat_id")): row for row in expected_evidence if isinstance(row, dict) and row.get("beat_id")
            }

            checkpoints = review.get("checkpoints") if isinstance(review.get("checkpoints"), list) else []
            checkpoint_roles = {str(item.get("role")) for item in checkpoints if isinstance(item, dict)}
            if checkpoint_roles != VISUAL_REVIEW_CHECKPOINT_ROLES:
                self.visual_review_issue(
                    "visual-review.frames",
                    f"Short {index:02d} must record opening, pre-action, post-action, intermediate, and final frames.",
                    review_path,
                    fix=remediation,
                )
            checkpoint_observations: list[str] = []
            for checkpoint in checkpoints:
                if not isinstance(checkpoint, dict):
                    continue
                role = str(checkpoint.get("role", ""))
                beat_id = str(checkpoint.get("beat_id", ""))
                timestamp = parse_float(checkpoint.get("timestamp_seconds"))
                frame_reference = str(checkpoint.get("frame_reference", "")).strip()
                observation = str(checkpoint.get("observation", "")).strip()
                persistent_ids = {str(value) for value in checkpoint.get("persistent_object_ids", []) if str(value)} if isinstance(checkpoint.get("persistent_object_ids"), list) else set()
                evidence = evidence_by_beat.get(beat_id)
                before = parse_float(evidence.get("before_seconds")) if isinstance(evidence, dict) else 0.0
                after = parse_float(evidence.get("after_seconds")) if isinstance(evidence, dict) else 0.0
                if role not in VISUAL_REVIEW_CHECKPOINT_ROLES or evidence is None or not (before - 0.05 <= timestamp <= after + 0.05):
                    self.visual_review_issue(
                        "visual-review.frames",
                        f"Short {index:02d} checkpoint {role or '?'} is not tied to a planned evidence timestamp.",
                        review_path,
                        fix=remediation,
                    )
                if not frame_reference or not persistent_ids.intersection(spine_ids):
                    self.visual_review_issue(
                        "visual-review.frames",
                        f"Short {index:02d} checkpoint {role or '?'} lacks a frame reference or persistent object ID.",
                        review_path,
                        fix=remediation,
                    )
                expected_frame_reference = f"{video_file}#t={timestamp:.2f}s"
                if frame_reference != expected_frame_reference:
                    self.visual_review_issue(
                        "visual-review.frames",
                        f"Short {index:02d} checkpoint {role or '?'} frame reference does not match its recorded timestamp.",
                        review_path,
                        fix=remediation,
                    )
                if len(re.findall(r"\b[\w'-]+\b", observation)) < 4:
                    self.visual_review_issue(
                        "visual-review.incomplete",
                        f"Short {index:02d} checkpoint {role or '?'} has no specific visual observation.",
                        review_path,
                        fix=remediation,
                    )
                else:
                    checkpoint_observations.append(re.sub(r"\W+", " ", observation.lower()).strip())
            if len(checkpoint_observations) == len(VISUAL_REVIEW_CHECKPOINT_ROLES) and len(set(checkpoint_observations)) < len(checkpoint_observations):
                self.visual_review_issue(
                    "visual-review.incomplete",
                    f"Short {index:02d} repeats checkpoint observations instead of recording each viewed frame.",
                    review_path,
                    fix=remediation,
                )

            changes = review.get("observed_state_changes") if isinstance(review.get("observed_state_changes"), list) else []
            valid_change_keys: set[tuple[str, str]] = set()
            invalid_change_reasons: list[str] = []
            for position, change in enumerate(changes, start=1):
                key = (
                    str(change.get("beat_id", "")) if isinstance(change, dict) else "",
                    str(change.get("planned_transition_id", "")) if isinstance(change, dict) else "",
                )
                error = structured_state_change_error(
                    change,
                    expected_change_by_key.get(key),
                    video_file=video_file,
                )
                if error is not None:
                    invalid_change_reasons.append(f"entry {position}: {error}")
                elif key in valid_change_keys:
                    invalid_change_reasons.append(f"entry {position}: duplicates planned transition {key[1]!r}")
                elif runtime_transition_keys is not None and key not in runtime_transition_keys:
                    invalid_change_reasons.append(
                        f"entry {position}: planned transition {key[1]!r} has no valid renderer runtime event"
                    )
                else:
                    valid_change_keys.add(key)
            if len(valid_change_keys) < ANIMATION_PLAN_MIN_TRANSFORMATIONS:
                invalid_detail = f" Invalid entries: {'; '.join(invalid_change_reasons[:3])}." if invalid_change_reasons else ""
                self.visual_review_issue(
                    "visual-review.changes",
                    f"Short {index:02d} records only {len(valid_change_keys)} structured, plan-matched state changes; "
                    f"at least four distinct transitions are required.{invalid_detail}",
                    review_path,
                    fix=remediation,
                )
            elif invalid_change_reasons:
                self.visual_review_issue(
                    "visual-review.changes",
                    f"Short {index:02d} contains invalid state-change claims: {'; '.join(invalid_change_reasons[:3])}.",
                    review_path,
                    fix=remediation,
                )

            overlap_legibility = review.get("overlap_legibility") if isinstance(review.get("overlap_legibility"), dict) else {}
            review_notes = str(overlap_legibility.get("notes", "")).strip()
            if (
                overlap_legibility.get("overlap") != "pass"
                or overlap_legibility.get("legibility") != "pass"
                or len(re.findall(r"\b[\w'-]+\b", review_notes)) < 4
            ):
                self.visual_review_issue(
                    "visual-review.legibility",
                    f"Short {index:02d} has not passed explicit overlap and phone-legibility review.",
                    review_path,
                    fix=remediation,
                )
            dense_review = review.get("dense_transition_review") if isinstance(review.get("dense_transition_review"), dict) else {}
            dense_interval = parse_float(dense_review.get("sample_interval_seconds"))
            dense_notes = str(dense_review.get("notes", "")).strip()
            if (
                dense_interval <= 0
                or dense_interval > 0.25
                or dense_review.get("covers_entire_video") is not True
                or dense_review.get("labeled_object_collisions") != "pass"
                or dense_review.get("persistent_text_integrity") != "pass"
                or len(re.findall(r"\b[\w'-]+\b", dense_notes)) < 8
            ):
                self.visual_review_issue(
                    "visual-review.transitions",
                    f"Short {index:02d} has not passed a complete quarter-second transition sweep.",
                    review_path,
                    fix=remediation,
                )
            reviewer = review.get("reviewer") if isinstance(review.get("reviewer"), dict) else {}
            reviewer_kind = str(reviewer.get("kind", "")).strip().lower()
            reviewer_name = str(reviewer.get("name", "")).strip()
            if reviewer_kind not in {"human", "agent"} or not reviewer_name or not review.get("reviewed_at"):
                self.visual_review_issue(
                    "visual-review.reviewer",
                    f"Short {index:02d} review lacks a named human/agent reviewer and completion time.",
                    review_path,
                    fix=remediation,
                )
            if review.get("verdict") != "pass":
                self.visual_review_issue(
                    "visual-review.verdict",
                    f"Short {index:02d} temporal reviewer verdict is not 'pass'.",
                    review_path,
                    fix=remediation,
                )

    def validate_video_file(self, path: Path, *, role: str) -> None:
        path = path.resolve()
        validation_key = (path, role)
        if validation_key in self.validated_video_roles:
            return
        self.validated_video_roles.add(validation_key)
        if not path.exists():
            self.fail("video", "Video file is missing.", path)
            return
        if path.stat().st_size < 10_000:
            self.fail("video", "Video file is too small to be valid.", path)
            return
        if not self.ffprobe:
            self.fail("video.probe", "ffprobe is unavailable, so video metadata cannot be validated.", path, fix="Install FFmpeg.")
            return

        metadata = self.video_cache.get(path)
        if metadata is None:
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

        if role == "final":
            self.validate_final_media_profile(path, metadata)
        elif width and height:
            if height <= width:
                self.fail("video.orientation", f"{role} video is not vertical ({width}x{height}).", path, fix="Render at a vertical 9:16 resolution.")
            elif abs((width / height) - TARGET_ASPECT_RATIO) > 0.08:
                self.warn("video.orientation", f"{role} video aspect ratio {width}:{height} is not close to 9:16.", path)
        else:
            self.fail("video.probe", "Video stream width/height could not be read.", path)

        if not has_audio and role == "final" and not self.intentional_silence_for(path):
            message = f"{role} video has no audio stream."
            fix = "Render with a working voice engine, or render intentionally with --voice-engine none so the report marks silence as expected."
            if not self.draft:
                self.fail("video.audio", message, path, fix=fix)
            else:
                self.warn("video.audio", message, path, fix=fix)

        if path not in self.analyzed_video_paths:
            self.analyzed_video_paths.add(path)
            self.analyze_video_frames(path, role=role)

    def publish_media_issue(self, area: str, message: str, path: Path, *, fix: str) -> None:
        severity = self.warn if self.draft else self.fail
        severity(area, message, path, fix=fix)

    def validate_final_media_profile(self, path: Path, metadata: dict[str, Any]) -> None:
        width = metadata.get("width")
        height = metadata.get("height")
        frame_rate = parse_float(metadata.get("frame_rate"))
        codec_name = str(metadata.get("codec_name") or "unknown").lower()
        pixel_format = str(metadata.get("pix_fmt") or "unknown").lower()
        field_order = str(metadata.get("field_order") or "unknown").lower()
        bit_rate = parse_float(metadata.get("bit_rate"))
        rotation = parse_float(metadata.get("rotation"))
        audio_codec = str(metadata.get("audio_codec_name") or "").lower()
        audio_sample_rate = int(parse_float(metadata.get("audio_sample_rate")))
        audio_channels = int(parse_float(metadata.get("audio_channels")))

        if path.stem.lower().endswith("_raw"):
            self.publish_media_issue(
                "video.final-path",
                "A *_raw.mp4 render is referenced as final output.",
                path,
                fix="Point short_plan.json and the publish queue at the encoded *_final.mp4 artifact.",
            )
        if path.suffix.lower() != ".mp4":
            self.publish_media_issue(
                "video.container",
                f"Final video uses {path.suffix or 'no extension'} instead of MP4.",
                path,
                fix="Encode the final upload artifact as an .mp4 file.",
            )
        if width != FINAL_VIDEO_WIDTH or height != FINAL_VIDEO_HEIGHT:
            self.publish_media_issue(
                "video.resolution",
                f"Final video is {width or '?'}x{height or '?'}, not exact {FINAL_VIDEO_WIDTH}x{FINAL_VIDEO_HEIGHT} vertical output.",
                path,
                fix=f"Scale and encode the final video at exactly {FINAL_VIDEO_WIDTH}x{FINAL_VIDEO_HEIGHT}.",
            )
        if frame_rate <= 0:
            self.publish_media_issue(
                "video.frame-rate",
                "Final video frame rate could not be read from the encoded video stream.",
                path,
                fix="Re-encode at 30 fps or higher and verify it with ffprobe.",
            )
        elif frame_rate < MIN_FINAL_FRAME_RATE:
            self.publish_media_issue(
                "video.frame-rate",
                f"Final video frame rate is {frame_rate:.3f} fps, below {MIN_FINAL_FRAME_RATE:.0f} fps.",
                path,
                fix="Re-render or re-encode the final MP4 at 30 fps or higher.",
            )
        if codec_name != "h264":
            self.publish_media_issue(
                "video.codec",
                f"Final video codec is {codec_name!r}, not H.264.",
                path,
                fix="Encode the final MP4 with libx264/H.264.",
            )
        if pixel_format != "yuv420p":
            self.publish_media_issue(
                "video.pixel-format",
                f"Final video pixel format is {pixel_format!r}, not yuv420p.",
                path,
                fix="Encode with -pix_fmt yuv420p for broad publishing compatibility.",
            )
        if field_order != "progressive":
            self.publish_media_issue(
                "video.scan",
                f"Final video field order is {field_order!r}, not progressive.",
                path,
                fix="Deinterlace if needed and encode progressive output.",
            )
        if bit_rate <= 0:
            self.publish_media_issue(
                "video.bitrate",
                "Final video encoded bitrate could not be read.",
                path,
                fix="Re-encode the final MP4 with a defined video bitrate or quality setting and verify it with ffprobe.",
            )
        if not math.isclose(rotation % 360.0, 0.0, abs_tol=0.01):
            self.publish_media_issue(
                "video.rotation",
                f"Final video carries {rotation:g}-degree rotation metadata.",
                path,
                fix="Bake orientation into the pixels and clear rotation metadata before publishing.",
            )
        if metadata.get("has_audio") and "audio_codec_name" in metadata and audio_codec != "aac":
            self.publish_media_issue("video.audio-codec", f"Final audio codec is {audio_codec or 'unknown'!r}, not AAC.", path, fix="Encode the final audio stream as AAC.")
        if metadata.get("has_audio") and {"audio_sample_rate", "audio_channels"}.issubset(metadata) and (audio_sample_rate != PIPER_SAMPLE_RATE or audio_channels != PIPER_CHANNELS):
            self.publish_media_issue("video.audio-profile", f"Final audio is {audio_sample_rate or '?'}Hz with {audio_channels or '?'} channel(s), not 48kHz mono.", path, fix="Encode final narration at 48kHz mono.")

    def probe_video(self, path: Path) -> dict[str, Any]:
        return self.probe_media(path)

    def probe_media(self, path: Path) -> dict[str, Any]:
        """Retain video and first-audio-stream metadata for timing validation."""
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
        audio_stream = audio_streams[0] if audio_streams else {}
        format_metadata = payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
        duration = parse_float(format_metadata.get("duration"))
        if duration <= 0:
            duration = parse_float(video_stream.get("duration")) or parse_float(audio_stream.get("duration"))
        video_duration = parse_float(video_stream.get("duration")) or duration
        audio_duration = parse_float(audio_stream.get("duration"))
        if audio_stream and audio_duration <= 0:
            audio_duration = duration
        avg_frame_rate = parse_rate(video_stream.get("avg_frame_rate"))
        nominal_frame_rate = parse_rate(video_stream.get("r_frame_rate"))
        if avg_frame_rate <= 0 and duration > 0:
            avg_frame_rate = parse_float(video_stream.get("nb_frames")) / duration
        video_bit_rate = parse_float(video_stream.get("bit_rate"))
        container_bit_rate = parse_float(format_metadata.get("bit_rate"))
        tags = video_stream.get("tags", {}) if isinstance(video_stream.get("tags"), dict) else {}
        rotation = parse_float(tags.get("rotate"))
        side_data_list = video_stream.get("side_data_list", [])
        if isinstance(side_data_list, list):
            for side_data in side_data_list:
                if isinstance(side_data, dict) and side_data.get("rotation") is not None:
                    rotation = parse_float(side_data.get("rotation"))
                    break
        return {
            "duration": duration,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "has_audio": bool(audio_streams),
            "video_duration": video_duration,
            "audio_duration": audio_duration,
            "audio_sample_rate": parse_positive_int(audio_stream.get("sample_rate")),
            "audio_channels": parse_positive_int(audio_stream.get("channels")),
            "audio_codec_name": audio_stream.get("codec_name"),
            "sample_rate": parse_positive_int(audio_stream.get("sample_rate")),
            "channels": parse_positive_int(audio_stream.get("channels")),
            "audio_codec": audio_stream.get("codec_name"),
            "frame_rate": avg_frame_rate or nominal_frame_rate,
            "avg_frame_rate": avg_frame_rate,
            "nominal_frame_rate": nominal_frame_rate,
            "codec_name": video_stream.get("codec_name"),
            "pix_fmt": video_stream.get("pix_fmt"),
            "field_order": video_stream.get("field_order"),
            "bit_rate": video_bit_rate or container_bit_rate,
            "video_bit_rate": video_bit_rate,
            "container_bit_rate": container_bit_rate,
            "rotation": rotation,
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


def parse_rate(value: Any) -> float:
    if isinstance(value, str) and "/" in value:
        numerator, denominator = value.split("/", 1)
        denominator_value = parse_float(denominator)
        if denominator_value == 0:
            return 0.0
        return parse_float(numerator) / denominator_value
    return parse_float(value)


def parse_positive_int(value: Any) -> int | None:
    number = parse_float(value)
    if number <= 0 or not number.is_integer():
        return None
    return int(number)


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

"""Learner-facing copy derived from recomputed physics scenario evidence."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Final


PHYSICS_VISIBLE_COPY_DENYLIST: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bexact\s+mit\b", re.IGNORECASE),
    re.compile(r"\bunit\s+\d+\b", re.IGNORECASE),
    re.compile(r"\binitialize\s+the\b", re.IGNORECASE),
    re.compile(r"\badvance\s+the\s+same\s+state\b", re.IGNORECASE),
    re.compile(r"\b[a-z][a-z0-9_]*\s*=\s*(?:true|false)\b", re.IGNORECASE),
)

_IMPLEMENTATION_KEY_PARTS: Final[frozenset[str]] = frozenset({
    "clock", "identity", "mechanism", "persist", "same", "shared", "visible",
})
_SECTION_LEADS: Final[Mapping[str, str]] = {
    "setup": "Setup",
    "calculation": "Calculation",
    "result": "Result",
}


def _is_learner_field(key: object, value: object) -> bool:
    """Exclude renderer assertions and booleans from visible numeric evidence."""
    if isinstance(value, bool) or value is None:
        return False
    words = set(re.findall(r"[a-z0-9]+", str(key).casefold()))
    return not bool(words & _IMPLEMENTATION_KEY_PARTS)


def _format_number(value: int | float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("physics visible copy cannot contain non-finite numbers")
    if number == 0:
        number = 0.0
    return f"{number:.4g}"


def _format_value(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip().replace("_", " ")
        return text or None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = [_format_value(item) for item in value]
        visible = [item for item in items if item is not None]
        return "(" + ", ".join(visible) + ")" if visible else None
    return None


def _evidence_sections(payload: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    evidence = payload.get("numeric_evidence")
    if isinstance(evidence, Mapping):
        return {
            section: values
            for section in _SECTION_LEADS
            if isinstance((values := evidence.get(section)), Mapping)
        }
    scenario = payload.get("model_scenario") or payload.get("scenario")
    if isinstance(scenario, Mapping):
        return {
            section: values
            for section in _SECTION_LEADS
            if isinstance((values := scenario.get(section)), Mapping)
        }
    aliases = {
        "setup": payload.get("numeric_setup"),
        "calculation": payload.get("calculation_fields"),
        "result": payload.get("result_fields"),
    }
    return {key: value for key, value in aliases.items() if isinstance(value, Mapping)}


def _section_copy(section: str, fields: Mapping[str, object], *, max_characters: int) -> str:
    lead = _SECTION_LEADS[section] + ": "
    clauses: list[str] = []
    for key, value in fields.items():
        if not _is_learner_field(key, value):
            continue
        rendered = _format_value(value)
        if rendered is None:
            continue
        clause = f"{str(key).replace('_', ' ')} = {rendered}"
        candidate = lead + "; ".join([*clauses, clause]) + "."
        if len(candidate) > max_characters:
            continue
        clauses.append(clause)
    if not clauses:
        raise ValueError(f"physics {section} evidence has no learner-visible values")
    return lead + "; ".join(clauses) + "."


def build_physics_visible_copy(
    payload: Mapping[str, object],
    *,
    max_characters: int = 90,
) -> dict[str, str]:
    """Build setup, calculation, and takeaway cues from authoritative evidence."""
    sections = _evidence_sections(payload)
    missing = [section for section in _SECTION_LEADS if section not in sections]
    if missing:
        raise ValueError("physics visible copy is missing evidence sections: " + ", ".join(missing))
    copy = {
        "setup": _section_copy("setup", sections["setup"], max_characters=max_characters),
        "calculation": _section_copy(
            "calculation", sections["calculation"], max_characters=max_characters
        ),
        "takeaway": _section_copy("result", sections["result"], max_characters=max_characters),
    }
    errors = validate_physics_visible_copy(copy, max_characters=max_characters)
    if errors:
        raise ValueError("Invalid physics visible copy: " + "; ".join(errors))
    return copy


def validate_physics_visible_copy(
    copy: Mapping[str, object],
    *,
    max_characters: int = 90,
) -> list[str]:
    """Return violations of the reusable learner-copy contract."""
    errors: list[str] = []
    for key in ("setup", "calculation", "takeaway"):
        text = str(copy.get(key, "")).strip()
        if not text:
            errors.append(f"{key} copy is required")
            continue
        if len(text) > max_characters:
            errors.append(f"{key} copy exceeds {max_characters} characters")
        if not re.search(r"[-+]?\d", text):
            errors.append(f"{key} copy must contain numeric scenario evidence")
        for pattern in PHYSICS_VISIBLE_COPY_DENYLIST:
            if pattern.search(text):
                errors.append(f"{key} copy contains denied implementation or metadata text")
                break
    return errors


def physics_visible_cue(payload: Mapping[str, object], state_name: str) -> str | None:
    """Map animation-plan state names to the shared evidence-bound copy."""
    key = {
        "example_setup": "setup",
        "example_calculation": "calculation",
        "example_takeaway": "takeaway",
    }.get(state_name)
    if key is None:
        return None
    return build_physics_visible_copy(payload)[key]


__all__ = [
    "PHYSICS_VISIBLE_COPY_DENYLIST",
    "build_physics_visible_copy",
    "physics_visible_cue",
    "validate_physics_visible_copy",
]

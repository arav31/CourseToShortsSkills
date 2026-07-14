"""Exact, renderer-neutral state models for weighted graph animations.

The helpers in this module deliberately keep algorithmic values separate from
their visible labels.  A renderer can consume a trace step without recomputing
math or guessing which persistent text object must be replaced.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping as MappingABC
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union


class MathematicalInfinity(Enum):
    """A non-``None`` internal value for an unreachable graph distance."""

    POSITIVE = "positive_infinity"


INFINITY = MathematicalInfinity.POSITIVE
ExactValue = Union[Fraction, MathematicalInfinity]
NumberInput = Union[int, float, str, Decimal, Fraction]
DistanceInput = Union[NumberInput, MathematicalInfinity, None]
EdgeInput = Union[
    "DirectedEdge",
    Mapping[str, object],
    Sequence[object],
]

_UNSAFE_DISPLAY_PLACEHOLDER = re.compile(
    r"(?<![A-Za-z0-9_])(?:none|nan|[+-]?inf(?:inity)?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def exact_number(value: NumberInput) -> Fraction:
    """Convert a finite numeric input to a decimal-exact ``Fraction``.

    Floats are converted through their shortest decimal spelling.  This treats
    a supplied ``0.1`` as the intended decimal one tenth instead of exposing
    the binary floating-point approximation in captions and evidence.
    """

    if isinstance(value, bool):
        raise TypeError("Boolean values are not graph weights")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Graph weights must be finite")
        return Fraction(value)
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Graph weights must be finite")
        return Fraction(str(value))
    if isinstance(value, str):
        text = value.strip().replace("−", "-")
        if not text or text == "∞" or _UNSAFE_DISPLAY_PLACEHOLDER.search(text):
            raise ValueError(f"Graph weights must be finite, got {value!r}")
        try:
            return Fraction(text)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f"Invalid exact graph weight: {value!r}") from exc
    raise TypeError(f"Unsupported graph weight type: {type(value).__name__}")


def distance_value(value: DistanceInput) -> ExactValue:
    """Normalize legacy distance inputs without exposing their placeholders."""

    if value is None or value is INFINITY:
        return INFINITY
    if isinstance(value, MathematicalInfinity):
        return INFINITY
    if isinstance(value, float) and math.isinf(value):
        if value < 0:
            raise ValueError("A shortest-path distance cannot use negative infinity")
        return INFINITY
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"∞", "inf", "+inf", "infinity", "+infinity", "none"}:
            return INFINITY
    return exact_number(value)


def format_exact(value: DistanceInput) -> str:
    """Format exact values for visible text, using mathematical infinity."""

    normalized = distance_value(value)
    if normalized is INFINITY:
        return "∞"
    if normalized.denominator == 1:
        return str(normalized.numerator)
    return f"{normalized.numerator}/{normalized.denominator}"


def is_display_safe_text(text: object) -> bool:
    """Return whether text is finite, single-line, and placeholder-free."""

    if not isinstance(text, str) or not text:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        return False
    return _UNSAFE_DISPLAY_PLACEHOLDER.search(text) is None


def ensure_display_safe_text(text: object, *, context: str = "display text") -> str:
    """Return valid display text or raise a focused formatting error."""

    if not is_display_safe_text(text):
        raise ValueError(f"Unsafe {context}: {text!r}")
    return str(text)


def _node_name(value: object) -> str:
    text = str(value).strip()
    return ensure_display_safe_text(text, context="vertex name")


@dataclass(frozen=True)
class DirectedEdge:
    """One stable, directed edge with an exact weight."""

    edge_id: str
    source: str
    target: str
    weight: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", ensure_display_safe_text(str(self.edge_id), context="edge id"))
        object.__setattr__(self, "source", _node_name(self.source))
        object.__setattr__(self, "target", _node_name(self.target))
        object.__setattr__(self, "weight", exact_number(self.weight))


def _mapping_value(mapping: Mapping[str, object], names: Sequence[str]) -> object:
    for name in names:
        if name in mapping:
            return mapping[name]
    raise KeyError(names[0])


def normalize_directed_edges(edges: Iterable[EdgeInput]) -> Tuple[DirectedEdge, ...]:
    """Normalize tuple/dict/dataclass edges and assign stable IDs.

    Three-item sequences are ``(source, target, weight)``.  Four-item
    sequences append an explicit edge ID.  Mapping inputs accept the existing
    ``from``/``to``/``weight`` shape as well as ``source``/``target``/``weight``.
    Parallel edges remain distinct through their IDs.
    """

    parsed = []
    for raw_edge in edges:
        explicit_id: Optional[str]
        if isinstance(raw_edge, DirectedEdge):
            parsed.append((raw_edge.source, raw_edge.target, raw_edge.weight, raw_edge.edge_id))
            continue
        if isinstance(raw_edge, Mapping):
            if "directed" in raw_edge and not bool(raw_edge["directed"]):
                raise ValueError("video graph models require directed edges")
            try:
                source = _mapping_value(raw_edge, ("source", "from", "u"))
                target = _mapping_value(raw_edge, ("target", "to", "v"))
            except KeyError as exc:
                raise ValueError("Each edge needs source/from and target/to") from exc
            weight = raw_edge.get("weight", raw_edge.get("w", 1))
            raw_id = raw_edge.get("edge_id", raw_edge.get("id"))
            explicit_id = str(raw_id) if raw_id is not None else None
        elif isinstance(raw_edge, Sequence) and not isinstance(raw_edge, (str, bytes)):
            if len(raw_edge) not in {3, 4}:
                raise ValueError("Edge sequences must have 3 or 4 items")
            source, target, weight = raw_edge[:3]
            explicit_id = str(raw_edge[3]) if len(raw_edge) == 4 else None
        else:
            raise TypeError(f"Unsupported edge input: {raw_edge!r}")
        parsed.append((_node_name(source), _node_name(target), exact_number(weight), explicit_id))

    normalized = []
    used_ids = set()
    for source, target, weight, explicit_id in parsed:
        source_name = _node_name(source)
        target_name = _node_name(target)
        if explicit_id is not None:
            edge_id = ensure_display_safe_text(explicit_id.strip(), context="edge id")
            if edge_id in used_ids:
                raise ValueError(f"Duplicate edge id: {edge_id}")
        else:
            base = f"{source_name}->{target_name}"
            edge_id = base
            suffix = 2
            while edge_id in used_ids:
                edge_id = f"{base}#{suffix}"
                suffix += 1
        used_ids.add(edge_id)
        normalized.append(DirectedEdge(edge_id, source_name, target_name, exact_number(weight)))
    return tuple(normalized)


@dataclass(frozen=True)
class VisibleLabel:
    """The exact value and text owned by one persistent visual object."""

    object_id: str
    owner_id: str
    scope: str
    value: ExactValue
    text: str

    def to_payload(self) -> dict[str, object]:
        return {
            "object_id": self.object_id,
            "owner_id": self.owner_id,
            "scope": self.scope,
            "exact_value": format_exact(self.value),
            "text": self.text,
        }


@dataclass(frozen=True)
class LabelReplacement:
    """Evidence that one visible object persists while its label is replaced."""

    persistent_object_id: str
    old_label: VisibleLabel
    new_label: VisibleLabel
    operation: str = "replace"

    def to_payload(self) -> dict[str, object]:
        return {
            "persistent_object_id": self.persistent_object_id,
            "operation": self.operation,
            "old_text": self.old_label.text,
            "new_text": self.new_label.text,
            "old_exact_value": format_exact(self.old_label.value),
            "new_exact_value": format_exact(self.new_label.value),
        }


@dataclass(frozen=True)
class ArithmeticEvidence:
    """Machine-checkable exact inputs paired with display-ready arithmetic."""

    rule: str
    exact_inputs: Tuple[Tuple[str, ExactValue], ...]
    exact_result: Fraction
    display_text: str

    def input_map(self) -> dict[str, ExactValue]:
        return dict(self.exact_inputs)

    def to_payload(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "exact_inputs": {name: format_exact(value) for name, value in self.exact_inputs},
            "exact_result": format_exact(self.exact_result),
            "display_text": self.display_text,
        }


@dataclass(frozen=True)
class TransitionEvidence:
    """Compact review evidence for one claimed on-screen update."""

    claim: str
    arithmetic_text: str
    persistent_object_id: str
    old_visible_text: str
    new_visible_text: str

    def to_payload(self) -> dict[str, str]:
        return {
            "claim": self.claim,
            "arithmetic_text": self.arithmetic_text,
            "persistent_object_id": self.persistent_object_id,
            "old_visible_text": self.old_visible_text,
            "new_visible_text": self.new_visible_text,
        }


def _serialize_exact_payload(value: object) -> object:
    """Convert exact trace values to stable JSON/render payload values."""

    if value is INFINITY or isinstance(value, MathematicalInfinity):
        return "∞"
    if isinstance(value, Fraction):
        return format_exact(value)
    if isinstance(value, MappingABC):
        return {str(key): _serialize_exact_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_serialize_exact_payload(item) for item in value]
    if isinstance(value, list):
        return [_serialize_exact_payload(item) for item in value]
    return value


@dataclass(frozen=True)
class GraphState:
    """Exact renderer-neutral state on either side of one route event."""

    distances: Tuple[Tuple[str, ExactValue], ...]
    edge_weights: Tuple[Tuple[str, Fraction], ...]
    settled: Tuple[str, ...] = ()
    frontier: Tuple[str, ...] = ()
    active_vertex: Optional[str] = None

    @property
    def distance_values(self) -> dict[str, ExactValue]:
        return dict(self.distances)

    @property
    def edge_weight_values(self) -> dict[str, Fraction]:
        return dict(self.edge_weights)

    def to_payload(self) -> dict[str, object]:
        return {
            "distances": {
                vertex: format_exact(value) for vertex, value in self.distances
            },
            "edge_weights": {
                edge_id: format_exact(value) for edge_id, value in self.edge_weights
            },
            "settled": list(self.settled),
            "frontier": list(self.frontier),
            "active_vertex": self.active_vertex or "",
        }


@dataclass(frozen=True)
class GraphTraceEvent(MappingABC[str, object]):
    """Typed event that remains compatible with legacy mapping consumers."""

    event_id: str
    algorithm: str
    kind: str
    sequence: int
    phase_index: int
    object_id: str
    caption: str
    before_state: GraphState
    after_state: GraphState
    details: Tuple[Tuple[str, object], ...] = ()

    @property
    def detail_map(self) -> dict[str, object]:
        return dict(self.details)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "event_id": self.event_id,
            "event": self.kind,
            "algorithm": self.algorithm,
            "sequence": self.sequence,
            "object_id": self.object_id,
            "caption": self.caption,
            "before_state": self.before_state.to_payload(),
            "after_state": self.after_state.to_payload(),
        }
        if self.phase_index:
            payload["pass"] = self.phase_index
        for key, value in self.details:
            payload[key] = _serialize_exact_payload(value)
        return payload

    def __getitem__(self, key: str) -> object:
        return self.to_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_payload())

    def __len__(self) -> int:
        return len(self.to_payload())


@dataclass(frozen=True)
class GraphAnimationStep:
    """A complete before/after contract for one successful graph update."""

    step_id: str
    algorithm: str
    kind: str
    sequence: int
    phase_index: int
    edge: DirectedEdge
    successful: bool
    old_edge_label: VisibleLabel
    new_edge_label: VisibleLabel
    old_distance_label: VisibleLabel
    new_distance_label: VisibleLabel
    edge_labels_before: Tuple[VisibleLabel, ...]
    edge_labels_after: Tuple[VisibleLabel, ...]
    distance_labels_before: Tuple[VisibleLabel, ...]
    distance_labels_after: Tuple[VisibleLabel, ...]
    label_replacements: Tuple[LabelReplacement, ...]
    arithmetic: ArithmeticEvidence
    caption: str
    evidence: TransitionEvidence

    def to_payload(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "algorithm": self.algorithm,
            "kind": self.kind,
            "sequence": self.sequence,
            "phase_index": self.phase_index,
            "from": self.edge.source,
            "to": self.edge.target,
            "edge_id": self.edge.edge_id,
            "successful": self.successful,
            "old_edge_label": self.old_edge_label.to_payload(),
            "new_edge_label": self.new_edge_label.to_payload(),
            "old_distance_label": self.old_distance_label.to_payload(),
            "new_distance_label": self.new_distance_label.to_payload(),
            "edge_labels_before": {
                label.owner_id: label.to_payload() for label in self.edge_labels_before
            },
            "edge_labels_after": {
                label.owner_id: label.to_payload() for label in self.edge_labels_after
            },
            "distance_labels_before": {
                label.owner_id: label.to_payload() for label in self.distance_labels_before
            },
            "distance_labels_after": {
                label.owner_id: label.to_payload() for label in self.distance_labels_after
            },
            "label_replacements": [replacement.to_payload() for replacement in self.label_replacements],
            "arithmetic": self.arithmetic.to_payload(),
            "caption": self.caption,
            "evidence": self.evidence.to_payload(),
        }


@dataclass(frozen=True)
class GraphAnimationTrace:
    """An immutable animation trace with exact final and visible states."""

    algorithm: str
    vertices: Tuple[str, ...]
    edges: Tuple[DirectedEdge, ...]
    initial_edge_labels: Tuple[VisibleLabel, ...]
    initial_distance_labels: Tuple[VisibleLabel, ...]
    steps: Tuple[GraphAnimationStep, ...]
    final_edge_labels: Tuple[VisibleLabel, ...]
    final_distance_labels: Tuple[VisibleLabel, ...]
    final_distance_values: Tuple[Tuple[str, ExactValue], ...]
    potentials: Tuple[Tuple[str, Fraction], ...] = ()
    settled_order: Tuple[str, ...] = ()
    passes: int = 0
    negative_cycle: bool = False
    route_events: Tuple[Mapping[str, object], ...] = ()
    extracts_unreachable: bool = False

    @property
    def typed_events(self) -> Tuple[GraphTraceEvent, ...]:
        """Return route events with exact before/after state contracts."""

        return tuple(
            event for event in self.route_events if isinstance(event, GraphTraceEvent)
        )

    @property
    def final_distances(self) -> dict[str, ExactValue]:
        return dict(self.final_distance_values)

    @property
    def final_edge_weights(self) -> dict[str, Fraction]:
        return {
            label.owner_id: exact_number(label.value)
            for label in self.final_edge_labels
        }

    @property
    def final_displayed_edge_weights(self) -> dict[str, str]:
        return {label.owner_id: label.text for label in self.final_edge_labels}

    @property
    def final_displayed_distances(self) -> dict[str, str]:
        return {label.owner_id: label.text for label in self.final_distance_labels}

    def to_payload(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "vertices": list(self.vertices),
            "edges": [
                {
                    "edge_id": edge.edge_id,
                    "from": edge.source,
                    "to": edge.target,
                    "exact_weight": format_exact(edge.weight),
                }
                for edge in self.edges
            ],
            "initial_edge_labels": {
                label.owner_id: label.to_payload() for label in self.initial_edge_labels
            },
            "initial_distance_labels": {
                label.owner_id: label.to_payload() for label in self.initial_distance_labels
            },
            "steps": [step.to_payload() for step in self.steps],
            "final_edge_labels": {
                label.owner_id: label.to_payload() for label in self.final_edge_labels
            },
            "final_distance_labels": {
                label.owner_id: label.to_payload() for label in self.final_distance_labels
            },
            "final_distances": {
                vertex: format_exact(value) for vertex, value in self.final_distance_values
            },
            "potentials": {vertex: format_exact(value) for vertex, value in self.potentials},
            "settled_order": list(self.settled_order),
            "passes": self.passes,
            "negative_cycle": self.negative_cycle,
            "extracts_unreachable": self.extracts_unreachable,
            "route_events": [dict(event) for event in self.route_events],
        }


@dataclass(frozen=True)
class ValidationResult:
    errors: Tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def valid(self) -> bool:
        return self.ok

    def require_valid(self) -> None:
        if self.errors:
            raise ValueError("Invalid graph animation trace:\n- " + "\n- ".join(self.errors))


def _vertex_order(
    edges: Sequence[DirectedEdge],
    vertices: Optional[Iterable[object]],
    source: Optional[object] = None,
) -> Tuple[str, ...]:
    ordered = []
    if vertices is not None:
        for vertex in vertices:
            name = _node_name(vertex)
            if name not in ordered:
                ordered.append(name)
    for edge in edges:
        for name in (edge.source, edge.target):
            if name not in ordered:
                ordered.append(name)
    if source is not None:
        source_name = _node_name(source)
        if source_name not in ordered:
            ordered.insert(0, source_name)
    return tuple(ordered)


def _graph_state(
    vertices: Sequence[str],
    edges: Sequence[DirectedEdge],
    distances: Mapping[str, ExactValue],
    *,
    edge_weights: Optional[Mapping[str, Fraction]] = None,
    settled: Sequence[str] = (),
    frontier: Sequence[str] = (),
    active_vertex: Optional[str] = None,
) -> GraphState:
    weights = (
        {edge.edge_id: edge.weight for edge in edges}
        if edge_weights is None
        else edge_weights
    )
    return GraphState(
        distances=tuple((vertex, distances[vertex]) for vertex in vertices),
        edge_weights=tuple((edge.edge_id, exact_number(weights[edge.edge_id])) for edge in edges),
        settled=tuple(settled),
        frontier=tuple(frontier),
        active_vertex=active_vertex,
    )


def _route_event(
    *,
    algorithm: str,
    sequence: int,
    kind: str,
    phase_index: int,
    object_id: str,
    caption: str,
    before_state: GraphState,
    after_state: GraphState,
    details: Sequence[Tuple[str, object]] = (),
) -> GraphTraceEvent:
    stable_algorithm = algorithm.replace("_", "-")
    return GraphTraceEvent(
        event_id=f"{stable_algorithm}:event:{sequence:04d}",
        algorithm=algorithm,
        kind=kind,
        sequence=sequence,
        phase_index=phase_index,
        object_id=object_id,
        caption=ensure_display_safe_text(caption, context=f"{algorithm} event caption"),
        before_state=before_state,
        after_state=after_state,
        details=tuple(details),
    )


def _edge_labels(
    edges: Sequence[DirectedEdge],
    weights: Mapping[str, Fraction],
    *,
    reweighted: Iterable[str] = (),
) -> Tuple[VisibleLabel, ...]:
    reweighted_ids = set(reweighted)
    return tuple(
        VisibleLabel(
            object_id=f"edge-label:{edge.edge_id}",
            owner_id=edge.edge_id,
            scope="reweighted_edge_weight" if edge.edge_id in reweighted_ids else "edge_weight",
            value=weights[edge.edge_id],
            text=format_exact(weights[edge.edge_id]),
        )
        for edge in edges
    )


def _distance_labels(
    vertices: Sequence[str],
    distances: Mapping[str, ExactValue],
    *,
    scope: str,
) -> Tuple[VisibleLabel, ...]:
    prefix = "potential-label" if scope == "potential" else "distance-label"
    return tuple(
        VisibleLabel(
            object_id=f"{prefix}:{vertex}",
            owner_id=vertex,
            scope=scope,
            value=distances[vertex],
            text=format_exact(distances[vertex]),
        )
        for vertex in vertices
    )


def _labels_by_owner(labels: Sequence[VisibleLabel]) -> dict[str, VisibleLabel]:
    return {label.owner_id: label for label in labels}


def _parenthesized_if_negative(value: Fraction) -> str:
    text = format_exact(value)
    return f"({text})" if value < 0 else text


def _add_expression(left: Fraction, right: Fraction) -> str:
    return f"{format_exact(left)} + {_parenthesized_if_negative(right)}"


def _make_relaxation_step(
    *,
    algorithm: str,
    sequence: int,
    phase_index: int,
    edge: DirectedEdge,
    edges: Sequence[DirectedEdge],
    vertices: Sequence[str],
    distances: Mapping[str, ExactValue],
) -> Optional[GraphAnimationStep]:
    source_distance = distances[edge.source]
    if source_distance is INFINITY:
        return None
    candidate = exact_number(source_distance) + edge.weight
    old_distance = distances[edge.target]
    if old_distance is not INFINITY and candidate >= exact_number(old_distance):
        return None

    edge_weights = {item.edge_id: item.weight for item in edges}
    edge_labels_before = _edge_labels(edges, edge_weights)
    edge_labels_after = edge_labels_before
    distance_labels_before = _distance_labels(vertices, distances, scope="distance")
    updated_distances = dict(distances)
    updated_distances[edge.target] = candidate
    distance_labels_after = _distance_labels(vertices, updated_distances, scope="distance")
    old_edge_label = _labels_by_owner(edge_labels_before)[edge.edge_id]
    new_edge_label = _labels_by_owner(edge_labels_after)[edge.edge_id]
    old_distance_label = _labels_by_owner(distance_labels_before)[edge.target]
    new_distance_label = _labels_by_owner(distance_labels_after)[edge.target]
    replacement = LabelReplacement(
        persistent_object_id=old_distance_label.object_id,
        old_label=old_distance_label,
        new_label=new_distance_label,
    )
    arithmetic_text = (
        f"min({format_exact(old_distance)}, "
        f"{_add_expression(exact_number(source_distance), edge.weight)}) = {format_exact(candidate)}"
    )
    caption = ensure_display_safe_text(
        f"Relax {edge.source}->{edge.target}: {arithmetic_text}",
        context="relaxation caption",
    )
    arithmetic = ArithmeticEvidence(
        rule="strict_relaxation",
        exact_inputs=(
            ("source_distance", exact_number(source_distance)),
            ("edge_weight", edge.weight),
            ("old_distance", old_distance),
        ),
        exact_result=candidate,
        display_text=arithmetic_text,
    )
    evidence = TransitionEvidence(
        claim=f"d({edge.target}) decreases",
        arithmetic_text=arithmetic_text,
        persistent_object_id=replacement.persistent_object_id,
        old_visible_text=old_distance_label.text,
        new_visible_text=new_distance_label.text,
    )
    return GraphAnimationStep(
        step_id=f"{algorithm}:{sequence}",
        algorithm=algorithm,
        kind="relax_distance",
        sequence=sequence,
        phase_index=phase_index,
        edge=edge,
        successful=True,
        old_edge_label=old_edge_label,
        new_edge_label=new_edge_label,
        old_distance_label=old_distance_label,
        new_distance_label=new_distance_label,
        edge_labels_before=edge_labels_before,
        edge_labels_after=edge_labels_after,
        distance_labels_before=distance_labels_before,
        distance_labels_after=distance_labels_after,
        label_replacements=(replacement,),
        arithmetic=arithmetic,
        caption=caption,
        evidence=evidence,
    )


def _make_reweight_step(
    *,
    sequence: int,
    edge: DirectedEdge,
    edges: Sequence[DirectedEdge],
    vertices: Sequence[str],
    potentials: Mapping[str, Fraction],
    visible_weights: Mapping[str, Fraction],
    reweighted_ids: Iterable[str],
) -> GraphAnimationStep:
    reweighted_before = tuple(reweighted_ids)
    edge_labels_before = _edge_labels(edges, visible_weights, reweighted=reweighted_before)
    new_weight = edge.weight + potentials[edge.source] - potentials[edge.target]
    updated_weights = dict(visible_weights)
    updated_weights[edge.edge_id] = new_weight
    reweighted_after = reweighted_before + (edge.edge_id,)
    edge_labels_after = _edge_labels(edges, updated_weights, reweighted=reweighted_after)
    potential_values: dict[str, ExactValue] = dict(potentials)
    distance_labels_before = _distance_labels(vertices, potential_values, scope="potential")
    distance_labels_after = distance_labels_before
    old_edge_label = _labels_by_owner(edge_labels_before)[edge.edge_id]
    new_edge_label = _labels_by_owner(edge_labels_after)[edge.edge_id]
    old_distance_label = _labels_by_owner(distance_labels_before)[edge.target]
    new_distance_label = _labels_by_owner(distance_labels_after)[edge.target]
    replacement = LabelReplacement(
        persistent_object_id=old_edge_label.object_id,
        old_label=old_edge_label,
        new_label=new_edge_label,
    )
    arithmetic_text = (
        f"{format_exact(edge.weight)} + {_parenthesized_if_negative(potentials[edge.source])} "
        f"- {_parenthesized_if_negative(potentials[edge.target])} = {format_exact(new_weight)}"
    )
    caption = ensure_display_safe_text(
        f"Reweight {edge.source}->{edge.target}: {arithmetic_text}",
        context="reweight caption",
    )
    arithmetic = ArithmeticEvidence(
        rule="johnson_reweight",
        exact_inputs=(
            ("old_edge_weight", edge.weight),
            ("source_potential", potentials[edge.source]),
            ("target_potential", potentials[edge.target]),
        ),
        exact_result=new_weight,
        display_text=arithmetic_text,
    )
    evidence = TransitionEvidence(
        claim=f"w'({edge.source},{edge.target}) replaces w({edge.source},{edge.target})",
        arithmetic_text=arithmetic_text,
        persistent_object_id=replacement.persistent_object_id,
        old_visible_text=old_edge_label.text,
        new_visible_text=new_edge_label.text,
    )
    return GraphAnimationStep(
        step_id=f"johnson:{sequence}",
        algorithm="johnson",
        kind="reweight_edge",
        sequence=sequence,
        phase_index=sequence,
        edge=edge,
        successful=True,
        old_edge_label=old_edge_label,
        new_edge_label=new_edge_label,
        old_distance_label=old_distance_label,
        new_distance_label=new_distance_label,
        edge_labels_before=edge_labels_before,
        edge_labels_after=edge_labels_after,
        distance_labels_before=distance_labels_before,
        distance_labels_after=distance_labels_after,
        label_replacements=(replacement,),
        arithmetic=arithmetic,
        caption=caption,
        evidence=evidence,
    )


def build_bellman_ford_trace(
    edges: Iterable[EdgeInput],
    source: object,
    *,
    vertices: Optional[Iterable[object]] = None,
) -> GraphAnimationTrace:
    """Build every ordered Bellman-Ford scan and exact state transition."""

    normalized_edges = normalize_directed_edges(edges)
    source_name = _node_name(source)
    ordered_vertices = _vertex_order(normalized_edges, vertices, source_name)
    distances: dict[str, ExactValue] = {vertex: INFINITY for vertex in ordered_vertices}
    distances[source_name] = Fraction(0)
    initial_distances = dict(distances)
    steps = []
    passes = 0
    sequence = 1
    route_events: list[GraphTraceEvent] = []
    event_sequence = 1
    edge_weights = {edge.edge_id: edge.weight for edge in normalized_edges}

    def state() -> GraphState:
        return _graph_state(
            ordered_vertices,
            normalized_edges,
            distances,
            edge_weights=edge_weights,
        )

    def emit(
        kind: str,
        phase_index: int,
        object_id: str,
        caption: str,
        before_state: GraphState,
        after_state: GraphState,
        *details: Tuple[str, object],
    ) -> None:
        nonlocal event_sequence
        route_events.append(
            _route_event(
                algorithm="bellman_ford",
                sequence=event_sequence,
                kind=kind,
                phase_index=phase_index,
                object_id=object_id,
                caption=caption,
                before_state=before_state,
                after_state=after_state,
                details=details,
            )
        )
        event_sequence += 1

    converged = False
    for pass_index in range(1, max(1, len(ordered_vertices))):
        changed = False
        pass_state = state()
        emit(
            "pass_start",
            pass_index,
            "graph:bellman-ford:pass",
            f"Pass {pass_index}: scan all {len(normalized_edges)} edges",
            pass_state,
            pass_state,
            ("edge_count", len(normalized_edges)),
        )
        for edge in normalized_edges:
            before_scan = state()
            step = _make_relaxation_step(
                algorithm="bellman_ford",
                sequence=sequence,
                phase_index=pass_index,
                edge=edge,
                edges=normalized_edges,
                vertices=ordered_vertices,
                distances=distances,
            )
            improved = step is not None
            source_distance = distances[edge.source]
            old_target = distances[edge.target]
            candidate: ExactValue = (
                INFINITY
                if source_distance is INFINITY
                else exact_number(source_distance) + edge.weight
            )
            emit(
                "edge_scan",
                pass_index,
                f"edge:{edge.edge_id}",
                f"Pass {pass_index}: scan {edge.source}->{edge.target}"
                + ("; improvement found" if improved else "; no change"),
                before_scan,
                before_scan,
                ("edge_id", edge.edge_id),
                ("from", edge.source),
                ("to", edge.target),
                ("successful", improved),
                ("source_distance", source_distance),
                ("edge_weight", edge.weight),
                ("candidate", candidate),
                ("old_target_distance", old_target),
            )
            if step is not None:
                steps.append(step)
                distances = {label.owner_id: label.value for label in step.distance_labels_after}
                after_relaxation = state()
                emit(
                    "relaxation",
                    pass_index,
                    f"distance-label:{edge.target}",
                    step.caption,
                    before_scan,
                    after_relaxation,
                    ("edge_id", edge.edge_id),
                    ("from", edge.source),
                    ("to", edge.target),
                    ("successful", True),
                    ("step_id", step.step_id),
                    ("old_distance", step.old_distance_label.value),
                    ("new_distance", step.new_distance_label.value),
                )
                sequence += 1
                changed = True
        passes = pass_index
        completed_state = state()
        emit(
            "pass_complete",
            pass_index,
            "graph:bellman-ford:pass",
            f"Pass {pass_index} complete: "
            + ("at least one label changed" if changed else "no labels changed"),
            completed_state,
            completed_state,
            ("changed", changed),
            ("completed_passes", passes),
        )
        if not changed:
            emit(
                "convergence",
                pass_index,
                "graph:bellman-ford:convergence",
                f"Converged after {passes} complete passes",
                completed_state,
                completed_state,
                ("completed_passes", passes),
                ("reason", "complete pass made no changes"),
            )
            converged = True
            break

    cycle_pass = len(ordered_vertices)
    final_scan_state = state()
    emit(
        "negative_cycle_scan_start",
        cycle_pass,
        "graph:bellman-ford:cycle-check",
        f"Final negative-cycle scan checks all {len(normalized_edges)} edges",
        final_scan_state,
        final_scan_state,
        ("edge_count", len(normalized_edges)),
    )
    cycle_witnesses: list[str] = []
    for edge in normalized_edges:
        source_distance = distances[edge.source]
        old_target = distances[edge.target]
        candidate = (
            INFINITY
            if source_distance is INFINITY
            else exact_number(source_distance) + edge.weight
        )
        improves = (
            source_distance is not INFINITY
            and (
                old_target is INFINITY
                or exact_number(candidate) < exact_number(old_target)
            )
        )
        if improves:
            cycle_witnesses.append(edge.edge_id)
        emit(
            "negative_cycle_edge_scan",
            cycle_pass,
            f"edge:{edge.edge_id}",
            f"Final scan {edge.source}->{edge.target}: "
            + ("would improve" if improves else "no change"),
            final_scan_state,
            final_scan_state,
            ("edge_id", edge.edge_id),
            ("from", edge.source),
            ("to", edge.target),
            ("successful", improves),
            ("source_distance", source_distance),
            ("edge_weight", edge.weight),
            ("candidate", candidate),
            ("old_target_distance", old_target),
        )
    negative_cycle = bool(cycle_witnesses)
    if not negative_cycle and not converged:
        emit(
            "convergence",
            cycle_pass,
            "graph:bellman-ford:convergence",
            f"Final scan confirms convergence after {passes} complete passes",
            final_scan_state,
            final_scan_state,
            ("completed_passes", passes),
            ("reason", "final scan found no improvement"),
        )
    emit(
        "negative_cycle_check",
        cycle_pass,
        "graph:bellman-ford:cycle-check",
        "Final scan found a reachable negative cycle"
        if negative_cycle
        else "Final scan found no reachable negative cycle",
        final_scan_state,
        final_scan_state,
        ("negative_cycle", negative_cycle),
        ("witness_edge_ids", tuple(cycle_witnesses)),
        ("completed_passes", passes),
    )
    trace = GraphAnimationTrace(
        algorithm="bellman_ford",
        vertices=ordered_vertices,
        edges=normalized_edges,
        initial_edge_labels=_edge_labels(normalized_edges, edge_weights),
        initial_distance_labels=_distance_labels(ordered_vertices, initial_distances, scope="distance"),
        steps=tuple(steps),
        final_edge_labels=_edge_labels(normalized_edges, edge_weights),
        final_distance_labels=_distance_labels(ordered_vertices, distances, scope="distance"),
        final_distance_values=tuple((vertex, distances[vertex]) for vertex in ordered_vertices),
        passes=passes,
        negative_cycle=negative_cycle,
        route_events=tuple(route_events),
    )
    validate_animation_trace(trace).require_valid()
    return trace


def build_dijkstra_trace(
    edges: Iterable[EdgeInput],
    source: object,
    *,
    vertices: Optional[Iterable[object]] = None,
    include_unreachable: bool = False,
) -> GraphAnimationTrace:
    """Build independent extract/settle events and every outgoing attempt."""

    normalized_edges = normalize_directed_edges(edges)
    if any(edge.weight < 0 for edge in normalized_edges):
        raise ValueError("Dijkstra requires nonnegative edge weights")
    if not isinstance(include_unreachable, bool):
        raise TypeError("include_unreachable must be a boolean")
    source_name = _node_name(source)
    ordered_vertices = _vertex_order(normalized_edges, vertices, source_name)
    distances: dict[str, ExactValue] = {vertex: INFINITY for vertex in ordered_vertices}
    distances[source_name] = Fraction(0)
    initial_distances = dict(distances)
    outgoing = {vertex: [] for vertex in ordered_vertices}
    for edge in normalized_edges:
        outgoing[edge.source].append(edge)

    settled = []
    settled_set = set()
    steps = []
    sequence = 1
    route_events: list[GraphTraceEvent] = []
    event_sequence = 1
    edge_weights = {edge.edge_id: edge.weight for edge in normalized_edges}
    current_state = _graph_state(
        ordered_vertices,
        normalized_edges,
        distances,
        edge_weights=edge_weights,
    )

    def emit(
        kind: str,
        phase_index: int,
        object_id: str,
        caption: str,
        before_state: GraphState,
        after_state: GraphState,
        *details: Tuple[str, object],
    ) -> None:
        nonlocal event_sequence, current_state
        route_events.append(
            _route_event(
                algorithm="dijkstra",
                sequence=event_sequence,
                kind=kind,
                phase_index=phase_index,
                object_id=object_id,
                caption=caption,
                before_state=before_state,
                after_state=after_state,
                details=details,
            )
        )
        event_sequence += 1
        current_state = after_state

    while True:
        candidates = [
            vertex
            for vertex in ordered_vertices
            if vertex not in settled_set
            and (include_unreachable or distances[vertex] is not INFINITY)
        ]
        if not candidates:
            break
        phase_index = len(settled) + 1
        frontier_state = _graph_state(
            ordered_vertices,
            normalized_edges,
            distances,
            edge_weights=edge_weights,
            settled=settled,
            frontier=candidates,
        )
        emit(
            "frontier",
            phase_index,
            "graph:dijkstra:frontier",
            "Unsettled frontier: "
            + ", ".join(
                f"{vertex}:{format_exact(distances[vertex])}"
                for vertex in candidates
            ),
            current_state,
            frontier_state,
            ("vertices", tuple(candidates)),
            ("labels", {vertex: distances[vertex] for vertex in candidates}),
        )
        current = min(
            candidates,
            key=lambda vertex: (
                distances[vertex] is INFINITY,
                Fraction(0)
                if distances[vertex] is INFINITY
                else exact_number(distances[vertex]),
                vertex,
            ),
        )
        extracted_state = _graph_state(
            ordered_vertices,
            normalized_edges,
            distances,
            edge_weights=edge_weights,
            settled=settled,
            frontier=candidates,
            active_vertex=current,
        )
        emit(
            "extract_min",
            phase_index,
            f"vertex:{current}",
            f"Extract min {current} with d={format_exact(distances[current])}",
            current_state,
            extracted_state,
            ("vertex", current),
            ("distance", distances[current]),
        )
        settled_set.add(current)
        settled.append(current)
        settled_state = _graph_state(
            ordered_vertices,
            normalized_edges,
            distances,
            edge_weights=edge_weights,
            settled=settled,
            frontier=candidates,
            active_vertex=current,
        )
        emit(
            "settle",
            phase_index,
            f"vertex:{current}",
            "Settled: " + ", ".join(settled),
            current_state,
            settled_state,
            ("vertex", current),
            ("settled", tuple(settled)),
        )
        for edge in outgoing[current]:
            before_attempt = current_state
            step = _make_relaxation_step(
                algorithm="dijkstra",
                sequence=sequence,
                phase_index=len(settled),
                edge=edge,
                edges=normalized_edges,
                vertices=ordered_vertices,
                distances=distances,
            )
            if step is not None:
                steps.append(step)
                distances = {label.owner_id: label.value for label in step.distance_labels_after}
                sequence += 1
            after_attempt = _graph_state(
                ordered_vertices,
                normalized_edges,
                distances,
                edge_weights=edge_weights,
                settled=settled,
                frontier=candidates,
                active_vertex=current,
            )
            emit(
                "outgoing_relaxation",
                phase_index,
                f"edge:{edge.edge_id}",
                f"Relax outgoing {edge.source}->{edge.target}"
                + ("; improve" if step is not None else "; keep label"),
                before_attempt,
                after_attempt,
                ("from", edge.source),
                ("to", edge.target),
                ("edge_id", edge.edge_id),
                ("successful", step is not None),
                ("current_vertex", current),
                ("old_distance", before_attempt.distance_values[edge.target]),
                ("new_distance", after_attempt.distance_values[edge.target]),
                ("step_id", step.step_id if step is not None else ""),
            )

    trace = GraphAnimationTrace(
        algorithm="dijkstra",
        vertices=ordered_vertices,
        edges=normalized_edges,
        initial_edge_labels=_edge_labels(normalized_edges, edge_weights),
        initial_distance_labels=_distance_labels(ordered_vertices, initial_distances, scope="distance"),
        steps=tuple(steps),
        final_edge_labels=_edge_labels(normalized_edges, edge_weights),
        final_distance_labels=_distance_labels(ordered_vertices, distances, scope="distance"),
        final_distance_values=tuple((vertex, distances[vertex]) for vertex in ordered_vertices),
        settled_order=tuple(settled),
        route_events=tuple(route_events),
        extracts_unreachable=include_unreachable,
    )
    validate_animation_trace(trace).require_valid()
    return trace


def _compute_johnson_potentials(
    vertices: Sequence[str],
    edges: Sequence[DirectedEdge],
) -> dict[str, Fraction]:
    potentials = {vertex: Fraction(0) for vertex in vertices}
    for _pass in range(max(0, len(vertices) - 1)):
        changed = False
        for edge in edges:
            candidate = potentials[edge.source] + edge.weight
            if candidate < potentials[edge.target]:
                potentials[edge.target] = candidate
                changed = True
        if not changed:
            break
    if any(
        potentials[edge.source] + edge.weight < potentials[edge.target]
        for edge in edges
    ):
        raise ValueError("Johnson reweighting is undefined for a graph with a negative cycle")
    return potentials


def build_johnson_reweight_trace(
    edges: Iterable[EdgeInput],
    *,
    vertices: Optional[Iterable[object]] = None,
    potentials: Optional[Mapping[object, NumberInput]] = None,
) -> GraphAnimationTrace:
    """Build exact edge-label replacements for Johnson reweighting.

    Without supplied potentials, Bellman-Ford's super-source initialization is
    represented by setting every potential to zero before relaxing the original
    edges.  This is exactly equivalent to adding zero-weight ``q->v`` edges.
    """

    normalized_edges = normalize_directed_edges(edges)
    ordered_vertices = _vertex_order(normalized_edges, vertices)
    if potentials is None:
        exact_potentials = _compute_johnson_potentials(ordered_vertices, normalized_edges)
    else:
        supplied = {_node_name(vertex): exact_number(value) for vertex, value in potentials.items()}
        missing = [vertex for vertex in ordered_vertices if vertex not in supplied]
        extra = [vertex for vertex in supplied if vertex not in ordered_vertices]
        if missing or extra:
            raise ValueError(f"Potentials must match graph vertices; missing={missing}, extra={extra}")
        exact_potentials = {vertex: supplied[vertex] for vertex in ordered_vertices}

    visible_weights = {edge.edge_id: edge.weight for edge in normalized_edges}
    initial_weights = dict(visible_weights)
    potential_values: dict[str, ExactValue] = dict(exact_potentials)
    steps = []
    reweighted_ids = []
    route_events: list[GraphTraceEvent] = []
    event_sequence = 1

    def state() -> GraphState:
        return _graph_state(
            ordered_vertices,
            normalized_edges,
            potential_values,
            edge_weights=visible_weights,
        )

    def emit(
        kind: str,
        object_id: str,
        caption: str,
        before_state: GraphState,
        after_state: GraphState,
        *details: Tuple[str, object],
    ) -> None:
        nonlocal event_sequence
        route_events.append(
            _route_event(
                algorithm="johnson",
                sequence=event_sequence,
                kind=kind,
                phase_index=0,
                object_id=object_id,
                caption=caption,
                before_state=before_state,
                after_state=after_state,
                details=details,
            )
        )
        event_sequence += 1

    initial_state = state()
    emit(
        "potential_phase_start",
        "graph:johnson:potentials",
        "Bellman-Ford from persistent super-source q computes h(v)",
        initial_state,
        initial_state,
        ("super_source", "q"),
    )
    for vertex in ordered_vertices:
        potential_state = state()
        emit(
            "potential_reveal",
            f"potential-label:{vertex}",
            f"h({vertex})={format_exact(exact_potentials[vertex])}",
            potential_state,
            potential_state,
            ("vertex", vertex),
            ("potential", exact_potentials[vertex]),
        )
    phase_state = state()
    emit(
        "reweight_phase_start",
        "graph:johnson:phase",
        "Reweight every edge with w'=w+h(u)-h(v)",
        phase_state,
        phase_state,
    )
    for sequence, edge in enumerate(normalized_edges, start=1):
        before_reweight = state()
        step = _make_reweight_step(
            sequence=sequence,
            edge=edge,
            edges=normalized_edges,
            vertices=ordered_vertices,
            potentials=exact_potentials,
            visible_weights=visible_weights,
            reweighted_ids=reweighted_ids,
        )
        steps.append(step)
        visible_weights = {
            label.owner_id: exact_number(label.value) for label in step.edge_labels_after
        }
        reweighted_ids.append(edge.edge_id)
        after_reweight = state()
        emit(
            "reweight_edge",
            f"edge-label:{edge.edge_id}",
            step.caption,
            before_reweight,
            after_reweight,
            ("edge_id", edge.edge_id),
            ("from", edge.source),
            ("to", edge.target),
            ("old_weight", step.old_edge_label.value),
            ("new_weight", step.new_edge_label.value),
            ("step_id", step.step_id),
        )
    ready_state = state()
    emit(
        "shortest_paths_ready",
        "graph:johnson:phase",
        "All reweighted edges are nonnegative; run Dijkstra from each source",
        ready_state,
        ready_state,
        ("all_nonnegative", all(weight >= 0 for weight in visible_weights.values())),
    )

    trace = GraphAnimationTrace(
        algorithm="johnson",
        vertices=ordered_vertices,
        edges=normalized_edges,
        initial_edge_labels=_edge_labels(normalized_edges, initial_weights),
        initial_distance_labels=_distance_labels(ordered_vertices, potential_values, scope="potential"),
        steps=tuple(steps),
        final_edge_labels=_edge_labels(normalized_edges, visible_weights, reweighted=reweighted_ids),
        final_distance_labels=_distance_labels(ordered_vertices, potential_values, scope="potential"),
        final_distance_values=tuple((vertex, exact_potentials[vertex]) for vertex in ordered_vertices),
        potentials=tuple((vertex, exact_potentials[vertex]) for vertex in ordered_vertices),
        route_events=tuple(route_events),
    )
    validate_animation_trace(trace).require_valid()
    return trace


@dataclass(frozen=True)
class JohnsonUnweightStep:
    """One exact conversion from a reweighted distance to an original one."""

    step_id: str
    sequence: int
    source: str
    target: str
    reweighted_distance: ExactValue
    source_potential: Fraction
    target_potential: Fraction
    original_distance: ExactValue
    before_state: Tuple[Tuple[Tuple[str, str], ExactValue], ...]
    after_state: Tuple[Tuple[Tuple[str, str], ExactValue], ...]
    arithmetic_text: str

    def to_payload(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "sequence": self.sequence,
            "event": "unweight",
            "source": self.source,
            "target": self.target,
            "reweighted_distance": format_exact(self.reweighted_distance),
            "source_potential": format_exact(self.source_potential),
            "target_potential": format_exact(self.target_potential),
            "original_distance": format_exact(self.original_distance),
            "before_state": {
                f"{source}->{target}": format_exact(value)
                for (source, target), value in self.before_state
            },
            "after_state": {
                f"{source}->{target}": format_exact(value)
                for (source, target), value in self.after_state
            },
            "arithmetic_text": self.arithmetic_text,
        }


@dataclass(frozen=True)
class JohnsonPathVerification:
    """Endpoint-offset evidence for one selected shortest path."""

    verification_id: str
    source: str
    target: str
    vertex_path: Tuple[str, ...]
    edge_path: Tuple[str, ...]
    original_path_weight: Fraction
    reweighted_path_weight: Fraction
    endpoint_offset: Fraction
    unweighted_distance: Fraction
    telescopes: bool
    path_order_preserved: bool
    arithmetic_text: str

    def to_payload(self) -> dict[str, object]:
        return {
            "verification_id": self.verification_id,
            "source": self.source,
            "target": self.target,
            "vertex_path": list(self.vertex_path),
            "edge_path": list(self.edge_path),
            "original_path_weight": format_exact(self.original_path_weight),
            "reweighted_path_weight": format_exact(self.reweighted_path_weight),
            "endpoint_offset": format_exact(self.endpoint_offset),
            "unweighted_distance": format_exact(self.unweighted_distance),
            "telescopes": self.telescopes,
            "path_order_preserved": self.path_order_preserved,
            "arithmetic_text": self.arithmetic_text,
        }


@dataclass(frozen=True)
class JohnsonAlgorithmTrace:
    """The complete Johnson pipeline, retaining every sub-algorithm trace."""

    algorithm: str
    vertices: Tuple[str, ...]
    super_source: str
    super_source_object_id: str
    original_edges: Tuple[DirectedEdge, ...]
    augmented_edges: Tuple[DirectedEdge, ...]
    potential_trace: GraphAnimationTrace
    potentials: Tuple[Tuple[str, Fraction], ...]
    reweight_trace: GraphAnimationTrace
    reweighted_edges: Tuple[DirectedEdge, ...]
    dijkstra_traces: Tuple[Tuple[str, GraphAnimationTrace], ...]
    unweight_steps: Tuple[JohnsonUnweightStep, ...]
    all_pairs_distance_values: Tuple[Tuple[Tuple[str, str], ExactValue], ...]
    path_verifications: Tuple[JohnsonPathVerification, ...]
    route_events: Tuple[Mapping[str, object], ...]

    @property
    def all_pairs_distances(self) -> dict[Tuple[str, str], ExactValue]:
        return dict(self.all_pairs_distance_values)

    @property
    def dijkstra_by_source(self) -> dict[str, GraphAnimationTrace]:
        return dict(self.dijkstra_traces)

    @property
    def verified(self) -> bool:
        return validate_johnson_trace(self).ok

    def to_payload(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "vertices": list(self.vertices),
            "super_source": self.super_source,
            "super_source_object_id": self.super_source_object_id,
            "original_edges": [
                {
                    "edge_id": edge.edge_id,
                    "from": edge.source,
                    "to": edge.target,
                    "weight": format_exact(edge.weight),
                }
                for edge in self.original_edges
            ],
            "augmented_edges": [
                {
                    "edge_id": edge.edge_id,
                    "from": edge.source,
                    "to": edge.target,
                    "weight": format_exact(edge.weight),
                }
                for edge in self.augmented_edges
            ],
            "potential_trace": self.potential_trace.to_payload(),
            "potentials": {
                vertex: format_exact(value) for vertex, value in self.potentials
            },
            "reweight_trace": self.reweight_trace.to_payload(),
            "reweighted_edges": [
                {
                    "edge_id": edge.edge_id,
                    "from": edge.source,
                    "to": edge.target,
                    "weight": format_exact(edge.weight),
                }
                for edge in self.reweighted_edges
            ],
            "dijkstra_traces": {
                source: trace.to_payload() for source, trace in self.dijkstra_traces
            },
            "unweight_steps": [step.to_payload() for step in self.unweight_steps],
            "all_pairs_distances": {
                f"{source}->{target}": format_exact(value)
                for (source, target), value in self.all_pairs_distance_values
            },
            "path_verifications": [
                verification.to_payload()
                for verification in self.path_verifications
            ],
            "route_events": [dict(event) for event in self.route_events],
            "verified": self.verified,
        }


def _dijkstra_predecessors(
    trace: GraphAnimationTrace,
) -> dict[str, Tuple[str, str]]:
    predecessors: dict[str, Tuple[str, str]] = {}
    for step in trace.steps:
        predecessors[step.edge.target] = (step.edge.source, step.edge.edge_id)
    return predecessors


def _reconstruct_edge_path(
    source: str,
    target: str,
    predecessors: Mapping[str, Tuple[str, str]],
    vertex_count: int,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    if source == target:
        return (source,), ()
    vertices = [target]
    edges: list[str] = []
    current = target
    for _index in range(vertex_count):
        predecessor = predecessors.get(current)
        if predecessor is None:
            return (), ()
        parent, edge_id = predecessor
        vertices.append(parent)
        edges.append(edge_id)
        current = parent
        if current == source:
            return tuple(reversed(vertices)), tuple(reversed(edges))
    raise AssertionError("Dijkstra predecessor chain contains a cycle")


def build_johnson_trace(
    edges: Iterable[EdgeInput],
    *,
    vertices: Optional[Iterable[object]] = None,
    super_source: object = "q",
) -> JohnsonAlgorithmTrace:
    """Build Johnson's full super-source/BF/reweight/Dijkstra/unweight trace."""

    original_edges = normalize_directed_edges(edges)
    ordered_vertices = _vertex_order(original_edges, vertices)
    q = _node_name(super_source)
    if q in ordered_vertices:
        raise ValueError(f"Johnson super-source {q!r} collides with an input vertex")

    super_edges = tuple(
        DirectedEdge(
            edge_id=f"johnson:{q}->{vertex}",
            source=q,
            target=vertex,
            weight=Fraction(0),
        )
        for vertex in ordered_vertices
    )
    augmented_edges = original_edges + super_edges
    potential_trace = build_bellman_ford_trace(
        augmented_edges,
        q,
        vertices=(q, *ordered_vertices),
    )
    if potential_trace.negative_cycle:
        raise ValueError("Johnson's algorithm requires a graph without a negative cycle")
    potential_distances = potential_trace.final_distances
    exact_potentials = tuple(
        (vertex, exact_number(potential_distances[vertex]))
        for vertex in ordered_vertices
    )
    potential_map = dict(exact_potentials)
    reweight_trace = build_johnson_reweight_trace(
        original_edges,
        vertices=ordered_vertices,
        potentials=potential_map,
    )
    reweighted_edges = tuple(
        DirectedEdge(
            edge.edge_id,
            edge.source,
            edge.target,
            reweight_trace.final_edge_weights[edge.edge_id],
        )
        for edge in original_edges
    )

    dijkstra_traces = tuple(
        (
            source,
            build_dijkstra_trace(
                reweighted_edges,
                source,
                vertices=ordered_vertices,
                include_unreachable=True,
            ),
        )
        for source in ordered_vertices
    )
    original_by_id = {edge.edge_id: edge for edge in original_edges}
    reweighted_by_id = {edge.edge_id: edge for edge in reweighted_edges}
    pair_order = tuple(
        (source, target)
        for source in ordered_vertices
        for target in ordered_vertices
    )
    dijkstra_by_source = dict(dijkstra_traces)
    visible_pair_values: dict[Tuple[str, str], ExactValue] = {
        (source, target): dijkstra_by_source[source].final_distances[target]
        for source, target in pair_order
    }
    all_pairs: list[Tuple[Tuple[str, str], ExactValue]] = []
    unweight_steps: list[JohnsonUnweightStep] = []
    path_verifications: list[JohnsonPathVerification] = []

    def pair_snapshot() -> Tuple[Tuple[Tuple[str, str], ExactValue], ...]:
        return tuple((pair, visible_pair_values[pair]) for pair in pair_order)

    for source, dijkstra_trace in dijkstra_traces:
        predecessors = _dijkstra_predecessors(dijkstra_trace)
        for target in ordered_vertices:
            reweighted_distance = dijkstra_trace.final_distances[target]
            before_snapshot = pair_snapshot()
            if reweighted_distance is INFINITY:
                original_distance: ExactValue = INFINITY
                arithmetic_text = f"d({source},{target}) remains ∞"
            else:
                original_distance = (
                    exact_number(reweighted_distance)
                    - potential_map[source]
                    + potential_map[target]
                )
                arithmetic_text = (
                    f"{format_exact(reweighted_distance)} - "
                    f"{_parenthesized_if_negative(potential_map[source])} + "
                    f"{_parenthesized_if_negative(potential_map[target])} = "
                    f"{format_exact(original_distance)}"
                )
            all_pairs.append(((source, target), original_distance))
            visible_pair_values[(source, target)] = original_distance
            unweight_steps.append(
                JohnsonUnweightStep(
                    step_id=f"johnson:unweight:{source}->{target}",
                    sequence=len(unweight_steps) + 1,
                    source=source,
                    target=target,
                    reweighted_distance=reweighted_distance,
                    source_potential=potential_map[source],
                    target_potential=potential_map[target],
                    original_distance=original_distance,
                    before_state=before_snapshot,
                    after_state=pair_snapshot(),
                    arithmetic_text=arithmetic_text,
                )
            )

            if reweighted_distance is INFINITY:
                continue
            vertex_path, edge_path = _reconstruct_edge_path(
                source,
                target,
                predecessors,
                len(ordered_vertices),
            )
            if not vertex_path:
                raise AssertionError("reachable Dijkstra target lacks a predecessor path")
            original_weight = sum(
                (original_by_id[edge_id].weight for edge_id in edge_path),
                Fraction(0),
            )
            reweighted_weight = sum(
                (reweighted_by_id[edge_id].weight for edge_id in edge_path),
                Fraction(0),
            )
            endpoint_offset = potential_map[source] - potential_map[target]
            unweighted = (
                reweighted_weight
                - potential_map[source]
                + potential_map[target]
            )
            path_verifications.append(
                JohnsonPathVerification(
                    verification_id=f"johnson:telescope:{source}->{target}",
                    source=source,
                    target=target,
                    vertex_path=vertex_path,
                    edge_path=edge_path,
                    original_path_weight=original_weight,
                    reweighted_path_weight=reweighted_weight,
                    endpoint_offset=endpoint_offset,
                    unweighted_distance=unweighted,
                    telescopes=(reweighted_weight == original_weight + endpoint_offset),
                    path_order_preserved=(
                        reweighted_weight == original_weight + endpoint_offset
                        and unweighted == exact_number(original_distance)
                    ),
                    arithmetic_text=(
                        f"w'(path)={format_exact(reweighted_weight)} = "
                        f"w(path) {format_exact(original_weight)} + endpoint offset "
                        f"{format_exact(endpoint_offset)}"
                    ),
                )
            )

    route_events: list[dict[str, object]] = []

    def route(kind: str, **payload: object) -> None:
        sequence = len(route_events) + 1
        route_events.append(
            {
                "event_id": f"johnson-full:event:{sequence:04d}",
                "event": kind,
                "algorithm": "johnson",
                "sequence": sequence,
                **payload,
            }
        )

    route(
        "super_source_add",
        vertex=q,
        object_id=f"vertex:{q}",
        edge_ids=tuple(edge.edge_id for edge in super_edges),
    )
    route(
        "potentials_derived",
        object_id="graph:johnson:potentials",
        potentials={vertex: format_exact(value) for vertex, value in exact_potentials},
        bellman_ford_event_ids=tuple(
            event.event_id for event in potential_trace.typed_events
        ),
    )
    route(
        "reweight_complete",
        object_id="graph:johnson:reweighted-edges",
        edge_ids=tuple(edge.edge_id for edge in reweighted_edges),
    )
    for source, dijkstra_trace in dijkstra_traces:
        route(
            "dijkstra_trace",
            source=source,
            object_id=f"graph:johnson:dijkstra:{source}",
            event_ids=tuple(event.event_id for event in dijkstra_trace.typed_events),
            settled=tuple(dijkstra_trace.settled_order),
        )
    for step in unweight_steps:
        route(
            "unweight",
            source=step.source,
            target=step.target,
            object_id=step.step_id,
            before=format_exact(step.reweighted_distance),
            after=format_exact(step.original_distance),
            arithmetic_text=step.arithmetic_text,
        )
    route(
        "complete",
        object_id="graph:johnson:complete",
        pair_count=len(all_pairs),
        telescoping_checks=len(path_verifications),
    )

    trace = JohnsonAlgorithmTrace(
        algorithm="johnson",
        vertices=ordered_vertices,
        super_source=q,
        super_source_object_id=f"vertex:{q}",
        original_edges=original_edges,
        augmented_edges=augmented_edges,
        potential_trace=potential_trace,
        potentials=exact_potentials,
        reweight_trace=reweight_trace,
        reweighted_edges=reweighted_edges,
        dijkstra_traces=dijkstra_traces,
        unweight_steps=tuple(unweight_steps),
        all_pairs_distance_values=tuple(all_pairs),
        path_verifications=tuple(path_verifications),
        route_events=tuple(route_events),
    )
    validate_johnson_trace(trace).require_valid()
    return trace


def validate_johnson_trace(trace: JohnsonAlgorithmTrace) -> ValidationResult:
    """Validate the complete Johnson stage handoffs and telescoping evidence."""

    errors: list[str] = []
    vertices = trace.vertices
    errors.extend(
        f"potential trace: {error}"
        for error in validate_animation_trace(trace.potential_trace).errors
    )
    errors.extend(
        f"reweight trace: {error}"
        for error in validate_animation_trace(trace.reweight_trace).errors
    )
    if trace.super_source in vertices:
        errors.append("Johnson super-source collides with an input vertex")
    if trace.super_source not in trace.potential_trace.vertices:
        errors.append("potential trace does not retain the super-source")
    q_edges = [
        edge for edge in trace.augmented_edges if edge.source == trace.super_source
    ]
    if [edge.target for edge in q_edges] != list(vertices):
        errors.append("super-source does not have one ordered zero edge to every vertex")
    if any(edge.weight != 0 for edge in q_edges):
        errors.append("super-source edges are not zero weight")
    if trace.potential_trace.negative_cycle:
        errors.append("potential Bellman-Ford trace found a negative cycle")

    potentials = dict(trace.potentials)
    if set(potentials) != set(vertices):
        errors.append("potentials do not cover every input vertex")
    else:
        for vertex in vertices:
            value = trace.potential_trace.final_distances.get(vertex)
            if value is INFINITY or exact_number(value) != potentials[vertex]:
                errors.append(f"potential for {vertex} does not come from Bellman-Ford")

    original_by_id = {edge.edge_id: edge for edge in trace.original_edges}
    reweighted_by_id = {edge.edge_id: edge for edge in trace.reweighted_edges}
    if set(original_by_id) != set(reweighted_by_id):
        errors.append("reweighted edges do not preserve original edge IDs")
    elif set(potentials) == set(vertices):
        for edge_id, original in original_by_id.items():
            expected = (
                original.weight
                + potentials[original.source]
                - potentials[original.target]
            )
            actual = reweighted_by_id[edge_id].weight
            if actual != expected:
                errors.append(f"reweighted edge {edge_id} has incorrect exact weight")
            if actual < 0:
                errors.append(f"reweighted edge {edge_id} is negative")

    sources = [source for source, _trace in trace.dijkstra_traces]
    if sources != list(vertices) or len(set(sources)) != len(vertices):
        errors.append("Johnson does not contain exactly one Dijkstra trace per source")
    for source, dijkstra_trace in trace.dijkstra_traces:
        if dijkstra_trace.algorithm != "dijkstra":
            errors.append(f"source {source} does not own a Dijkstra trace")
        if set(dijkstra_trace.vertices) != set(vertices):
            errors.append(f"Dijkstra trace for {source} does not cover every vertex")
        route_validation = validate_graph_route_events(dijkstra_trace)
        errors.extend(f"Dijkstra {source}: {error}" for error in route_validation.errors)

    expected_pairs = [(source, target) for source in vertices for target in vertices]
    actual_pairs = [pair for pair, _value in trace.all_pairs_distance_values]
    if actual_pairs != expected_pairs:
        errors.append("all-pairs distances are not in stable source/target order")
    if len(trace.unweight_steps) != len(expected_pairs):
        errors.append("unweight trace does not contain one step per ordered pair")
    else:
        dijkstra_by_source = trace.dijkstra_by_source
        previous_after: Optional[
            Tuple[Tuple[Tuple[str, str], ExactValue], ...]
        ] = None
        for pair, step in zip(expected_pairs, trace.unweight_steps):
            if (step.source, step.target) != pair:
                errors.append(f"unweight step {step.step_id} is out of order")
                continue
            expected_reweighted = dijkstra_by_source[step.source].final_distances[
                step.target
            ]
            if step.reweighted_distance != expected_reweighted:
                errors.append(f"unweight step {step.step_id} has wrong before value")
            if expected_reweighted is INFINITY:
                expected_original: ExactValue = INFINITY
            else:
                expected_original = (
                    exact_number(expected_reweighted)
                    - potentials[step.source]
                    + potentials[step.target]
                )
            if step.original_distance != expected_original:
                errors.append(f"unweight step {step.step_id} has wrong after value")
            before_values = dict(step.before_state)
            after_values = dict(step.after_state)
            if list(before_values) != expected_pairs or list(after_values) != expected_pairs:
                errors.append(f"unweight step {step.step_id} does not carry a full ordered state")
            if previous_after is not None and step.before_state != previous_after:
                errors.append(f"unweight step {step.step_id} breaks state continuity")
            changed_pairs = [
                candidate
                for candidate in expected_pairs
                if before_values.get(candidate) != after_values.get(candidate)
            ]
            expected_changed = [] if expected_reweighted == expected_original else [pair]
            if changed_pairs != expected_changed:
                errors.append(f"unweight step {step.step_id} changes the wrong pair")
            if before_values.get(pair) != expected_reweighted:
                errors.append(f"unweight step {step.step_id} before-state is inaccurate")
            if after_values.get(pair) != expected_original:
                errors.append(f"unweight step {step.step_id} after-state is inaccurate")
            previous_after = step.after_state

        pair_values = dict(trace.all_pairs_distance_values)
        step_values = {
            (step.source, step.target): step.original_distance
            for step in trace.unweight_steps
        }
        if pair_values != step_values:
            errors.append("all-pairs result does not match the unweight trace")

    verification_ids: set[str] = set()
    verified_pairs: list[Tuple[str, str]] = []
    for verification in trace.path_verifications:
        if verification.verification_id in verification_ids:
            errors.append(f"path verification ID {verification.verification_id} is duplicated")
        verification_ids.add(verification.verification_id)
        verified_pairs.append((verification.source, verification.target))
        if not verification.telescopes:
            errors.append(f"{verification.verification_id} does not telescope")
        if not verification.path_order_preserved:
            errors.append(f"{verification.verification_id} does not preserve path order")
        if verification.unweighted_distance != verification.original_path_weight:
            errors.append(f"{verification.verification_id} unweights to the wrong path")

    reachable_pairs = [
        pair
        for pair, value in trace.all_pairs_distance_values
        if value is not INFINITY
    ]
    if verified_pairs != reachable_pairs:
        errors.append("path-order/telescoping evidence does not cover every reachable pair")

    route_ids: set[str] = set()
    for expected_sequence, event in enumerate(trace.route_events, start=1):
        event_id = str(event.get("event_id", ""))
        if event.get("sequence") != expected_sequence:
            errors.append(f"Johnson route event {event_id} is out of sequence")
        if not event_id or event_id in route_ids:
            errors.append(f"Johnson route event ID {event_id!r} is missing or duplicated")
        route_ids.add(event_id)
    if not trace.route_events or trace.route_events[-1].get("event") != "complete":
        errors.append("Johnson route does not end with completion")

    return ValidationResult(tuple(errors))


def _check_label_set(
    labels: Sequence[VisibleLabel],
    location: str,
    errors: list[str],
) -> dict[str, VisibleLabel]:
    by_owner = {}
    object_ids = set()
    for label in labels:
        if label.owner_id in by_owner:
            errors.append(f"{location} duplicates label owner {label.owner_id}")
        if label.object_id in object_ids:
            errors.append(f"{location} duplicates persistent object {label.object_id}")
        by_owner[label.owner_id] = label
        object_ids.add(label.object_id)
        if not is_display_safe_text(label.text):
            errors.append(f"{location} has unsafe text {label.text!r}")
        if label.text != format_exact(label.value):
            errors.append(
                f"{location} label {label.owner_id} displays {label.text!r}, "
                f"expected {format_exact(label.value)!r}"
            )
    return by_owner


def _same_label_state(left: Mapping[str, VisibleLabel], right: Mapping[str, VisibleLabel]) -> bool:
    return left == right


def validate_graph_route_events(trace: GraphAnimationTrace) -> ValidationResult:
    """Validate typed route ordering independently of successful update steps."""

    errors: list[str] = []
    if not trace.route_events:
        return ValidationResult(())
    typed_events = trace.typed_events
    if len(typed_events) != len(trace.route_events):
        return ValidationResult(("route contains events without typed state contracts",))

    seen_ids: set[str] = set()
    previous_after: Optional[GraphState] = None
    for expected_sequence, event in enumerate(typed_events, start=1):
        if event.sequence != expected_sequence:
            errors.append(f"route event {event.event_id} has non-contiguous sequence")
        if event.event_id in seen_ids:
            errors.append(f"route event ID {event.event_id} is duplicated")
        seen_ids.add(event.event_id)
        if event.algorithm != trace.algorithm:
            errors.append(f"route event {event.event_id} has the wrong algorithm")
        if previous_after is not None and event.before_state != previous_after:
            errors.append(f"route event {event.event_id} breaks exact state continuity")
        if not is_display_safe_text(event.caption):
            errors.append(f"route event {event.event_id} has unsafe caption text")
        previous_after = event.after_state

    if trace.algorithm == "bellman_ford":
        edge_ids = [edge.edge_id for edge in trace.edges]
        for pass_index in range(1, trace.passes + 1):
            pass_events = [
                event for event in typed_events if event.phase_index == pass_index
            ]
            starts = [event for event in pass_events if event.kind == "pass_start"]
            completes = [event for event in pass_events if event.kind == "pass_complete"]
            scans = [event for event in pass_events if event.kind == "edge_scan"]
            if len(starts) != 1 or len(completes) != 1:
                errors.append(f"Bellman-Ford pass {pass_index} lacks one start/complete pair")
            if [event.detail_map.get("edge_id") for event in scans] != edge_ids:
                errors.append(f"Bellman-Ford pass {pass_index} does not scan every edge in order")
            for scan in scans:
                if not scan.detail_map.get("successful"):
                    continue
                later = typed_events[scan.sequence :]
                if not later or later[0].kind != "relaxation":
                    errors.append(f"successful scan {scan.event_id} lacks its relaxation event")
                elif later[0].detail_map.get("edge_id") != scan.detail_map.get("edge_id"):
                    errors.append(f"successful scan {scan.event_id} relaxes a different edge")
        negative_scans = [
            event for event in typed_events if event.kind == "negative_cycle_edge_scan"
        ]
        if [event.detail_map.get("edge_id") for event in negative_scans] != edge_ids:
            errors.append("Bellman-Ford final negative-cycle scan is incomplete or unordered")
        if typed_events[-1].kind != "negative_cycle_check":
            errors.append("Bellman-Ford route does not end with its cycle-check summary")
        if not trace.negative_cycle and not any(
            event.kind == "convergence" for event in typed_events
        ):
            errors.append("Bellman-Ford route omits convergence evidence")

    if trace.algorithm == "dijkstra":
        extracted = [
            str(event.detail_map.get("vertex"))
            for event in typed_events
            if event.kind == "extract_min"
        ]
        settled = [
            str(event.detail_map.get("vertex"))
            for event in typed_events
            if event.kind == "settle"
        ]
        if extracted != list(trace.settled_order):
            errors.append("Dijkstra extract-min events do not match settled order")
        if settled != list(trace.settled_order):
            errors.append("Dijkstra settle events do not match settled order")
        if len(extracted) != len(set(extracted)):
            errors.append("Dijkstra extracts a vertex more than once")
        expected_extracted = (
            list(trace.vertices)
            if trace.extracts_unreachable
            else [
                vertex
                for vertex, value in trace.final_distance_values
                if value is not INFINITY
            ]
        )
        if set(extracted) != set(expected_extracted):
            qualifier = "vertex" if trace.extracts_unreachable else "reachable vertex"
            errors.append(f"Dijkstra does not extract every {qualifier} exactly once")

        active_vertex: Optional[str] = None
        outgoing_by_source = {
            vertex: [edge.edge_id for edge in trace.edges if edge.source == vertex]
            for vertex in trace.settled_order
        }
        attempted_by_source = {vertex: [] for vertex in trace.settled_order}
        awaiting_settle: Optional[str] = None
        for event in typed_events:
            if event.kind == "extract_min":
                active_vertex = str(event.detail_map.get("vertex"))
                awaiting_settle = active_vertex
            elif event.kind == "settle":
                vertex = str(event.detail_map.get("vertex"))
                if vertex != awaiting_settle:
                    errors.append(f"Dijkstra settles {vertex} without its extraction")
                awaiting_settle = None
            elif event.kind == "outgoing_relaxation":
                source = str(event.detail_map.get("from"))
                if awaiting_settle is not None or source != active_vertex:
                    errors.append(
                        f"Dijkstra relaxation {event.event_id} is not from the current extracted vertex"
                    )
                if source in attempted_by_source:
                    attempted_by_source[source].append(str(event.detail_map.get("edge_id")))
        for vertex, expected_edge_ids in outgoing_by_source.items():
            if attempted_by_source[vertex] != expected_edge_ids:
                errors.append(f"Dijkstra outgoing attempts for {vertex} are incomplete or unordered")

    return ValidationResult(tuple(errors))


def validate_animation_trace(trace: GraphAnimationTrace) -> ValidationResult:
    """Validate arithmetic, text, snapshots, and persistent replacement evidence."""

    errors: list[str] = list(validate_graph_route_events(trace).errors)
    edge_by_id = {edge.edge_id: edge for edge in trace.edges}
    if len(edge_by_id) != len(trace.edges):
        errors.append("trace has duplicate edge IDs")
    if len(set(trace.vertices)) != len(trace.vertices):
        errors.append("trace has duplicate vertices")
    for edge in trace.edges:
        if edge.source not in trace.vertices or edge.target not in trace.vertices:
            errors.append(f"edge {edge.edge_id} references a missing vertex")

    current_edges = _check_label_set(trace.initial_edge_labels, "initial edge labels", errors)
    current_distances = _check_label_set(trace.initial_distance_labels, "initial distance labels", errors)
    if set(current_edges) != set(edge_by_id):
        errors.append("initial edge labels do not cover every edge exactly once")
    if set(current_distances) != set(trace.vertices):
        errors.append("initial distance labels do not cover every vertex exactly once")

    for expected_sequence, step in enumerate(trace.steps, start=1):
        location = f"step {step.step_id}"
        if step.algorithm != trace.algorithm:
            errors.append(f"{location} algorithm does not match trace")
        if step.sequence != expected_sequence:
            errors.append(f"{location} has non-contiguous sequence {step.sequence}")
        if not step.successful:
            errors.append(f"{location} is present but not a successful update")
        if step.edge.edge_id not in edge_by_id or step.edge != edge_by_id.get(step.edge.edge_id):
            errors.append(f"{location} references inconsistent edge data")
        if not is_display_safe_text(step.caption):
            errors.append(f"{location} has unsafe caption {step.caption!r}")
        if not is_display_safe_text(step.arithmetic.display_text):
            errors.append(f"{location} has unsafe arithmetic text")

        before_edges = _check_label_set(step.edge_labels_before, f"{location} edge labels before", errors)
        after_edges = _check_label_set(step.edge_labels_after, f"{location} edge labels after", errors)
        before_distances = _check_label_set(
            step.distance_labels_before, f"{location} distance labels before", errors
        )
        after_distances = _check_label_set(
            step.distance_labels_after, f"{location} distance labels after", errors
        )
        if not _same_label_state(before_edges, current_edges):
            errors.append(f"{location} edge before-state does not continue the visible trace")
        if not _same_label_state(before_distances, current_distances):
            errors.append(f"{location} distance before-state does not continue the visible trace")
        if step.old_edge_label != before_edges.get(step.edge.edge_id):
            errors.append(f"{location} old edge label is not the visible before-label")
        if step.new_edge_label != after_edges.get(step.edge.edge_id):
            errors.append(f"{location} new edge label is not the visible after-label")
        if step.old_distance_label != before_distances.get(step.edge.target):
            errors.append(f"{location} old distance label is not the target before-label")
        if step.new_distance_label != after_distances.get(step.edge.target):
            errors.append(f"{location} new distance label is not the target after-label")

        if len(step.label_replacements) != 1:
            errors.append(f"{location} must have exactly one persistent label replacement")
            replacement = None
        else:
            replacement = step.label_replacements[0]
            if replacement.operation != "replace":
                errors.append(f"{location} label update is not a replacement")
            if replacement.old_label.object_id != replacement.new_label.object_id:
                errors.append(f"{location} replacement changes persistent object identity")
            if replacement.persistent_object_id != replacement.old_label.object_id:
                errors.append(f"{location} replacement does not name its persistent object")

        inputs = step.arithmetic.input_map()
        if len(inputs) != len(step.arithmetic.exact_inputs):
            errors.append(f"{location} arithmetic evidence duplicates an input name")
        if step.kind == "relax_distance":
            required = {"source_distance", "edge_weight", "old_distance"}
            if set(inputs) != required:
                errors.append(f"{location} relaxation evidence inputs are incomplete")
            else:
                source_distance = inputs["source_distance"]
                edge_weight = inputs["edge_weight"]
                old_distance = inputs["old_distance"]
                if source_distance is INFINITY or edge_weight is INFINITY:
                    errors.append(f"{location} relaxation uses non-finite arithmetic input")
                else:
                    candidate = exact_number(source_distance) + exact_number(edge_weight)
                    if candidate != step.arithmetic.exact_result:
                        errors.append(f"{location} relaxation result does not match exact arithmetic")
                    if old_distance is not INFINITY and candidate >= exact_number(old_distance):
                        errors.append(f"{location} is not a strict successful relaxation")
                    changed = [owner for owner in before_distances if before_distances[owner] != after_distances.get(owner)]
                    if changed != [step.edge.target]:
                        errors.append(f"{location} must change only the target distance label")
                    if before_edges != after_edges:
                        errors.append(f"{location} unexpectedly changes visible edge weights")
                    if after_distances.get(step.edge.target) is not None:
                        if after_distances[step.edge.target].value != candidate:
                            errors.append(f"{location} target label does not display the relaxed value")
                if replacement is not None:
                    if replacement.old_label != step.old_distance_label or replacement.new_label != step.new_distance_label:
                        errors.append(f"{location} does not persistently replace the distance label")
        elif step.kind == "reweight_edge":
            required = {"old_edge_weight", "source_potential", "target_potential"}
            if set(inputs) != required:
                errors.append(f"{location} reweight evidence inputs are incomplete")
            else:
                old_weight = inputs["old_edge_weight"]
                source_potential = inputs["source_potential"]
                target_potential = inputs["target_potential"]
                if INFINITY in {old_weight, source_potential, target_potential}:
                    errors.append(f"{location} reweighting uses infinity")
                else:
                    expected_weight = (
                        exact_number(old_weight)
                        + exact_number(source_potential)
                        - exact_number(target_potential)
                    )
                    if expected_weight != step.arithmetic.exact_result:
                        errors.append(f"{location} reweight result does not match exact arithmetic")
                    changed = [owner for owner in before_edges if before_edges[owner] != after_edges.get(owner)]
                    if changed != [step.edge.edge_id]:
                        errors.append(f"{location} must replace only its visible edge label")
                    if before_distances != after_distances:
                        errors.append(f"{location} unexpectedly changes potential labels")
                    if after_edges.get(step.edge.edge_id) is not None:
                        if after_edges[step.edge.edge_id].value != expected_weight:
                            errors.append(f"{location} edge label does not display the reweighted value")
                if replacement is not None:
                    if replacement.old_label != step.old_edge_label or replacement.new_label != step.new_edge_label:
                        errors.append(f"{location} does not persistently replace the edge label")
        else:
            errors.append(f"{location} has unknown update kind {step.kind!r}")

        if step.evidence.arithmetic_text != step.arithmetic.display_text:
            errors.append(f"{location} review evidence does not cite the arithmetic")
        if replacement is not None:
            if step.evidence.persistent_object_id != replacement.persistent_object_id:
                errors.append(f"{location} review evidence cites the wrong persistent object")
            if step.evidence.old_visible_text != replacement.old_label.text:
                errors.append(f"{location} review evidence has the wrong old visible text")
            if step.evidence.new_visible_text != replacement.new_label.text:
                errors.append(f"{location} review evidence has the wrong new visible text")
        for evidence_text in (
            step.evidence.claim,
            step.evidence.arithmetic_text,
            step.evidence.old_visible_text,
            step.evidence.new_visible_text,
        ):
            if not is_display_safe_text(evidence_text):
                errors.append(f"{location} has unsafe review evidence text {evidence_text!r}")

        current_edges = after_edges
        current_distances = after_distances

    final_edges = _check_label_set(trace.final_edge_labels, "final edge labels", errors)
    final_distances = _check_label_set(trace.final_distance_labels, "final distance labels", errors)
    if final_edges != current_edges:
        errors.append("final edge labels do not match the last visible edge state")
    if final_distances != current_distances:
        errors.append("final distance labels do not match the last visible distance state")
    exact_final_distances = dict(trace.final_distance_values)
    if set(exact_final_distances) != set(trace.vertices):
        errors.append("final exact distances do not cover every vertex")
    else:
        for vertex, value in exact_final_distances.items():
            if vertex not in final_distances or final_distances[vertex].value != value:
                errors.append(f"final visible distance for {vertex} lacks exact-state evidence")
    if trace.algorithm == "johnson":
        for edge_id, label in final_edges.items():
            if label.value is INFINITY or exact_number(label.value) < 0:
                errors.append(f"Johnson final displayed weight for {edge_id} is negative")

    return ValidationResult(tuple(errors))


def collect_transition_evidence(trace: GraphAnimationTrace) -> Tuple[TransitionEvidence, ...]:
    """Return the complete, ordered evidence trail after validating the trace."""

    validate_animation_trace(trace).require_valid()
    return tuple(step.evidence for step in trace.steps)


def build_complete_dijkstra_trace(
    edges: Iterable[EdgeInput],
    source: object,
    *,
    vertices: Optional[Iterable[object]] = None,
) -> GraphAnimationTrace:
    """Build the all-vertex queue variant, including extraction at infinity."""

    return build_dijkstra_trace(
        edges,
        source,
        vertices=vertices,
        include_unreachable=True,
    )


# Readable aliases for callers that think in terms of an animation rather than a build step.
bellman_ford_animation_trace = build_bellman_ford_trace
dijkstra_animation_trace = build_dijkstra_trace
complete_dijkstra_animation_trace = build_complete_dijkstra_trace
johnson_reweight_animation_trace = build_johnson_reweight_trace
johnson_animation_trace = build_johnson_trace
johnson_full_animation_trace = build_johnson_trace


__all__ = [
    "ArithmeticEvidence",
    "DirectedEdge",
    "GraphAnimationStep",
    "GraphAnimationTrace",
    "GraphState",
    "GraphTraceEvent",
    "INFINITY",
    "JohnsonAlgorithmTrace",
    "JohnsonPathVerification",
    "JohnsonUnweightStep",
    "LabelReplacement",
    "MathematicalInfinity",
    "TransitionEvidence",
    "ValidationResult",
    "VisibleLabel",
    "bellman_ford_animation_trace",
    "build_bellman_ford_trace",
    "build_complete_dijkstra_trace",
    "build_dijkstra_trace",
    "build_johnson_reweight_trace",
    "build_johnson_trace",
    "collect_transition_evidence",
    "complete_dijkstra_animation_trace",
    "dijkstra_animation_trace",
    "distance_value",
    "ensure_display_safe_text",
    "exact_number",
    "format_exact",
    "is_display_safe_text",
    "johnson_animation_trace",
    "johnson_full_animation_trace",
    "johnson_reweight_animation_trace",
    "normalize_directed_edges",
    "validate_animation_trace",
    "validate_graph_route_events",
    "validate_johnson_trace",
]

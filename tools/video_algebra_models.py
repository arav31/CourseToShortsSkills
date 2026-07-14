"""Renderer-neutral semantic models for introductory ring, ideal, and field videos."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping


RING_VISUAL_KIND = "algebra_ring_structure"
IDEAL_VISUAL_KIND = "algebra_ideal_quotient"
FIELD_VISUAL_KIND = "algebra_field_structure"

RING_ROUTE_KEY = "algebra:ring_structure"
IDEAL_ROUTE_KEY = "algebra:ideal_quotient"
FIELD_ROUTE_KEY = "algebra:field_structure"

ALGEBRA_VISUAL_KINDS = frozenset({
    RING_VISUAL_KIND,
    IDEAL_VISUAL_KIND,
    FIELD_VISUAL_KIND,
})


@dataclass(frozen=True)
class AlgebraVideoSpec:
    visual_kind: str
    route_key: str
    model_mode: str
    canonical_formula: str
    compatible_routes: tuple[tuple[str, str], ...] = ()

    def accepts_route(self, route_key: str, model_mode: str) -> bool:
        """Return whether runtime metadata can render this algebra model.

        Exact course payloads may own their route key and semantic mode while
        still targeting the same algebra visual.  Compatibility is recorded as
        key/mode pairs so unrelated routes cannot match on only one field.
        """

        return (route_key, model_mode) in (
            (self.route_key, self.model_mode),
            *self.compatible_routes,
        )


RING_SPEC = AlgebraVideoSpec(
    visual_kind=RING_VISUAL_KIND,
    route_key=RING_ROUTE_KEY,
    model_mode="ring_distributivity",
    canonical_formula=r"a(b+c)=ab+ac",
    compatible_routes=((
        "modern_algebra:mit_18_703:ring_distributivity",
        "ring_laws_ideals",
    ),),
)
IDEAL_SPEC = AlgebraVideoSpec(
    visual_kind=IDEAL_VISUAL_KIND,
    route_key=IDEAL_ROUTE_KEY,
    model_mode="ideal_absorption_quotient",
    canonical_formula=r"rI\subseteq I,\qquad R/I",
)
FIELD_SPEC = AlgebraVideoSpec(
    visual_kind=FIELD_VISUAL_KIND,
    route_key=FIELD_ROUTE_KEY,
    model_mode="field_inverse_division",
    canonical_formula=r"a\ne0\Rightarrow aa^{-1}=1",
)


def normalize_algebra_topic(title: str) -> str:
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    text = unicodedata.normalize("NFKC", title).casefold()
    text = text.replace("\u2010", "-").replace("\u2011", "-")
    text = text.replace("\u2012", "-").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def resolve_algebra_video_model(
    title: str,
    *,
    fail_closed: bool = False,
) -> AlgebraVideoSpec | None:
    """Resolve a topic to one of the three introductory algebra proof models.

    More specialized algebra topics deliberately remain with their existing
    factorization, extension, and Galois renderers.
    """

    topic = normalize_algebra_topic(title)
    words = set(topic.split())
    specialized = (
        "field extension",
        "extension degree",
        "algebraic element",
        "minimal polynomial",
        "galois",
        "automorphism",
        "polynomial ring",
        "euclidean domain",
        "principal ideal domain",
        "unique factorization",
        "irreducible",
    )
    if any(marker in topic for marker in specialized):
        spec = None
    elif "ideal" in words or "ideals" in words or "quotient ring" in topic or "quotient rings" in topic:
        spec = IDEAL_SPEC
    elif "field" in words or "fields" in words:
        spec = FIELD_SPEC
    elif "ring" in words or "rings" in words:
        spec = RING_SPEC
    else:
        spec = None
    if spec is None and fail_closed:
        raise ValueError(f"Unsupported introductory algebra video topic: {title!r}")
    return spec


def algebra_video_route_is_compatible(
    title: str,
    route_key: str,
    model_mode: str,
) -> bool:
    """Check standalone or integrated runtime metadata for an algebra topic."""

    spec = resolve_algebra_video_model(title)
    return spec is not None and spec.accepts_route(route_key, model_mode)


def _worked_text(worked_example: Mapping[str, object] | None) -> str:
    worked = worked_example or {}
    return " ".join(
        str(worked.get(key, ""))
        for key in ("setup", "calculation", "takeaway")
    )


def _positive_ints(text: str) -> list[int]:
    values: list[int] = []
    for token in re.findall(r"(?<![A-Za-z])\d+(?![A-Za-z])", text):
        value = int(token)
        if value > 0 and value not in values:
            values.append(value)
    return values


def _modulus(text: str) -> int | None:
    patterns = (
        r"(?:mod(?:ulo)?|mod\.)\s*(\d+)",
        r"\bZ\s*/\s*(\d+)\s*Z\b",
        r"\bZ(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    return all(value % divisor for divisor in range(2, int(value ** 0.5) + 1))


def _objects(rows: list[tuple[str, str, str, str]]) -> list[dict[str, object]]:
    return [
        {
            "id": object_id,
            "role": role,
            "color": color,
            "initial_state": initial_state,
            "persistent": True,
        }
        for object_id, role, color, initial_state in rows
    ]


def _transition(
    transition_id: str,
    kind: str,
    claim: str,
    action: str,
    object_ids: list[str],
    before: Mapping[str, str],
    after: Mapping[str, str],
    evidence_tokens: list[str],
) -> dict[str, object]:
    return {
        "id": transition_id,
        "kind": kind,
        "claim": claim,
        "action": action,
        "persistent_object_ids": list(object_ids),
        "before": dict(before),
        "after": dict(after),
        "evidence_tokens": list(evidence_tokens),
    }


def _ring_payload(spec: AlgebraVideoSpec, text: str) -> dict[str, object]:
    values = _positive_ints(text)
    a, b, c = (values + [2, 3, 4])[:3]
    modulus = _modulus(text)
    reduce = (lambda value: value % modulus) if modulus else (lambda value: value)
    sum_value = reduce(b + c)
    left_value = reduce(a * sum_value)
    first_product = reduce(a * b)
    second_product = reduce(a * c)
    right_value = reduce(first_product + second_product)
    if left_value != right_value:
        raise ValueError("Ring model failed its distributive-law check")
    carrier_label = f"Z/{modulus}Z" if modulus else "Z"
    ids = [
        "algebra:ring:carrier",
        "algebra:ring:operands",
        "algebra:ring:left_path",
        "algebra:ring:right_path",
        "algebra:ring:verdict",
    ]
    state0 = {
        ids[0]: f"{carrier_label} with addition and multiplication",
        ids[1]: f"a={a}, b={b}, c={c} selected",
        ids[2]: "b+c is not evaluated",
        ids[3]: "ab+ac is not evaluated",
        ids[4]: "distributivity is unchecked",
    }
    state1 = {**state0, ids[2]: f"b+c={sum_value}"}
    state2 = {**state1, ids[2]: f"a(b+c)={left_value}"}
    state3 = {**state2, ids[3]: f"ab+ac={first_product}+{second_product}={right_value}"}
    state4 = {**state3, ids[4]: f"{left_value}={right_value}; distributivity verified"}
    transitions = [
        _transition(
            "ring:add_closure",
            "addition_closure",
            "Evaluate the inner sum without leaving the ring carrier.",
            f"Move b={b} and c={c} through addition; retain b+c={sum_value} on the left path.",
            ids,
            state0,
            state1,
            [str(b), str(c), str(sum_value)],
        ),
        _transition(
            "ring:left_product",
            "left_multiplication",
            "Multiply the retained sum by the same persistent a.",
            f"Carry a={a} into the left path and replace it with a(b+c)={left_value}.",
            ids,
            state1,
            state2,
            [str(a), str(sum_value), str(left_value)],
        ),
        _transition(
            "ring:distribute",
            "distributive_split",
            "Copy the role of a across both terms and evaluate the right path.",
            f"Split a across b and c; retain ab+ac={first_product}+{second_product}={right_value}.",
            ids,
            state2,
            state3,
            [str(first_product), str(second_product), str(right_value)],
        ),
        _transition(
            "ring:match_paths",
            "path_equality",
            "Resolve both operation paths at the same carrier element.",
            f"Join the two persistent paths at {left_value}={right_value} and mark distributivity verified.",
            ids,
            state3,
            state4,
            [str(left_value), str(right_value)],
        ),
    ]
    return {
        "payload_type": "algebra",
        "family": "ring_structure",
        "mode": spec.model_mode,
        "visual_kind": spec.visual_kind,
        "route_key": spec.route_key,
        "carrier_label": carrier_label,
        "subject_id": ids[1],
        "invariant": "The same carrier and the same operands survive both operation paths, which meet at one result.",
        "objects": _objects([
            (ids[0], "persistent ring carrier with two named operations", "#58A6FF", state0[ids[0]]),
            (ids[1], "persistent operands shared by both distributive paths", "#EAF2FF", state0[ids[1]]),
            (ids[2], "left evaluation path a(b+c)", "#F7C948", state0[ids[2]]),
            (ids[3], "right evaluation path ab+ac", "#A371F7", state0[ids[3]]),
            (ids[4], "equality verdict joining both paths", "#7EE787", state0[ids[4]]),
        ]),
        "transitions": transitions,
        "display": {
            "a": a,
            "b": b,
            "c": c,
            "sum": sum_value,
            "left": left_value,
            "ab": first_product,
            "ac": second_product,
            "right": right_value,
            "modulus": modulus,
        },
    }


def _ideal_payload(spec: AlgebraVideoSpec, text: str) -> dict[str, object]:
    generator_match = re.search(r"(?:multiples of|generated by)\s+(\d+)", text, re.IGNORECASE)
    generator = int(generator_match.group(1)) if generator_match else (_modulus(text) or 5)
    if generator <= 1:
        raise ValueError("Ideal model needs a nontrivial positive generator")
    ambient = 3
    ideal_element = 2 * generator
    product = ambient * ideal_element
    representative = generator + 3
    residue = representative % generator
    ids = [
        "algebra:ideal:carrier",
        "algebra:ideal:subset",
        "algebra:ideal:multiplier",
        "algebra:ideal:quotient",
        "algebra:ideal:verdict",
    ]
    state0 = {
        ids[0]: "Z is the ambient ring",
        ids[1]: f"I={generator}Z is named",
        ids[2]: f"r={ambient}; i={ideal_element}",
        ids[3]: "quotient classes are not formed",
        ids[4]: "absorption and quotient compatibility are unchecked",
    }
    state1 = {**state0, ids[1]: f"i={ideal_element} belongs to I={generator}Z"}
    state2 = {
        **state1,
        ids[1]: f"{product} remains in I={generator}Z",
        ids[2]: f"r i={ambient}({ideal_element})={product}",
    }
    state3 = {**state2, ids[3]: f"I collapses to [0] in Z/{generator}Z"}
    state4 = {
        **state3,
        ids[3]: f"[{representative}]=[{residue}] because {representative}-{residue} is in I",
        ids[4]: "absorption makes quotient multiplication independent of representatives",
    }
    transitions = [
        _transition(
            "ideal:select_element",
            "ideal_membership",
            "Locate one concrete ideal element inside the fixed ambient ring.",
            f"Highlight i={ideal_element} inside I={generator}Z while retaining the ambient multiplier r={ambient}.",
            ids,
            state0,
            state1,
            [str(ideal_element), f"{generator}Z"],
        ),
        _transition(
            "ideal:absorb_product",
            "ambient_absorption",
            "Multiply by an arbitrary ambient element and keep the product inside the ideal.",
            f"Move r={ambient} onto i={ideal_element}; retain ri={product} inside I={generator}Z.",
            ids,
            state1,
            state2,
            [str(ambient), str(ideal_element), str(product)],
        ),
        _transition(
            "ideal:collapse_zero",
            "quotient_collapse",
            "Turn the entire ideal into the zero class of the quotient.",
            f"Collapse the highlighted I={generator}Z region into [0] in Z/{generator}Z.",
            ids,
            state2,
            state3,
            ["[0]", f"Z/{generator}Z"],
        ),
        _transition(
            "ideal:identify_representatives",
            "representative_equivalence",
            "Identify two representatives whose difference lies in the ideal.",
            f"Merge [{representative}] with [{residue}] because {representative}-{residue}={generator} lies in I.",
            ids,
            state3,
            state4,
            [str(representative), str(residue), str(generator)],
        ),
    ]
    return {
        "payload_type": "algebra",
        "family": "ideal_quotient",
        "mode": spec.model_mode,
        "visual_kind": spec.visual_kind,
        "route_key": spec.route_key,
        "carrier_label": "Z",
        "subject_id": ids[1],
        "invariant": "The same ideal absorbs every ambient product, then becomes exactly the zero class of the quotient.",
        "objects": _objects([
            (ids[0], "persistent ambient ring", "#58A6FF", state0[ids[0]]),
            (ids[1], "persistent ideal subset that later becomes the zero class", "#F7C948", state0[ids[1]]),
            (ids[2], "ambient multiplier and ideal element", "#EAF2FF", state0[ids[2]]),
            (ids[3], "persistent quotient-class rail", "#A371F7", state0[ids[3]]),
            (ids[4], "well-defined quotient verdict", "#7EE787", state0[ids[4]]),
        ]),
        "transitions": transitions,
        "display": {
            "generator": generator,
            "ambient": ambient,
            "ideal_element": ideal_element,
            "product": product,
            "representative": representative,
            "residue": residue,
        },
    }


def _field_payload(spec: AlgebraVideoSpec, text: str) -> dict[str, object]:
    modulus = _modulus(text) or 5
    if not _is_prime(modulus):
        raise ValueError(
            f"Field inverse model requires a prime modulus, got {modulus}; use a ring route for composite moduli"
        )
    values = _positive_ints(text)
    element = next((value % modulus for value in values if value % modulus not in {0, 1}), 2 % modulus)
    if element == 0:
        element = 1
    inverse = next(candidate for candidate in range(1, modulus) if element * candidate % modulus == 1)
    candidates = [candidate for candidate in range(1, modulus) if candidate != inverse][:2] + [inverse]
    while len(candidates) < 3:
        candidates.insert(0, 1)
    dividend = 4 % modulus or 1
    quotient = dividend * inverse % modulus
    ids = [
        "algebra:field:carrier",
        "algebra:field:element",
        "algebra:field:candidate",
        "algebra:field:product",
        "algebra:field:division",
    ]
    state0 = {
        ids[0]: f"Z/{modulus}Z with nonzero residues visible",
        ids[1]: f"a={element} selected",
        ids[2]: "inverse candidate is hidden",
        ids[3]: "multiplicative identity has not been reached",
        ids[4]: "division is unresolved",
    }
    candidate_states = []
    previous = state0
    transitions = []
    for index, candidate in enumerate(candidates, start=1):
        product = element * candidate % modulus
        current = {
            **previous,
            ids[2]: f"x={candidate} tested",
            ids[3]: f"{element}*{candidate}={product} mod {modulus}",
        }
        transition_id = f"field:test_candidate_{index}"
        claim = (
            f"Test candidate {candidate} on the same selected nonzero element."
            if candidate != inverse
            else f"Reach the identity and retain {candidate} as the inverse of {element}."
        )
        action = (
            f"Move the persistent candidate marker to {candidate}; update the product to {product}."
            if candidate != inverse
            else f"Move the same marker to {candidate}; update {element}*{candidate} to the identity 1."
        )
        transitions.append(_transition(
            transition_id,
            "inverse_search",
            claim,
            action,
            ids,
            previous,
            current,
            [str(element), str(candidate), str(product)],
        ))
        candidate_states.append(current)
        previous = current
    final_state = {
        **previous,
        ids[4]: f"{dividend}/{element}={dividend}*{inverse}={quotient} mod {modulus}",
    }
    transitions.append(_transition(
        "field:resolve_division",
        "division_by_inverse",
        "Use the retained inverse to turn division into multiplication.",
        f"Carry inverse {inverse} into {dividend}/{element}; resolve the quotient as {quotient} modulo {modulus}.",
        ids,
        previous,
        final_state,
        [str(dividend), str(element), str(inverse), str(quotient)],
    ))
    return {
        "payload_type": "algebra",
        "family": "field_structure",
        "mode": spec.model_mode,
        "visual_kind": spec.visual_kind,
        "route_key": spec.route_key,
        "carrier_label": f"Z/{modulus}Z",
        "subject_id": ids[1],
        "invariant": "One nonzero element and one persistent candidate marker expose the inverse that makes division possible.",
        "objects": _objects([
            (ids[0], "persistent finite-field carrier", "#58A6FF", state0[ids[0]]),
            (ids[1], "selected nonzero field element", "#EAF2FF", state0[ids[1]]),
            (ids[2], "persistent inverse-candidate marker", "#F7C948", state0[ids[2]]),
            (ids[3], "persistent product readout", "#A371F7", state0[ids[3]]),
            (ids[4], "division result built from the retained inverse", "#7EE787", state0[ids[4]]),
        ]),
        "transitions": transitions,
        "display": {
            "modulus": modulus,
            "element": element,
            "inverse": inverse,
            "candidates": candidates,
            "products": [element * candidate % modulus for candidate in candidates],
            "dividend": dividend,
            "quotient": quotient,
        },
    }


def validate_algebra_video_payload(payload: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    objects = payload.get("objects") if isinstance(payload.get("objects"), list) else []
    object_ids = [str(row.get("id", "")) for row in objects if isinstance(row, Mapping)]
    transitions = payload.get("transitions") if isinstance(payload.get("transitions"), list) else []
    if payload.get("payload_type") != "algebra":
        errors.append("payload_type must be algebra")
    if payload.get("visual_kind") not in ALGEBRA_VISUAL_KINDS:
        errors.append("visual_kind is not a dedicated algebra route")
    if len(object_ids) < 4 or len(object_ids) != len(set(object_ids)) or any(not value for value in object_ids):
        errors.append("algebra model needs at least four unique persistent object ids")
    if len(transitions) < 4:
        errors.append("algebra model needs at least four semantic transitions")
    previous_after: dict[str, str] | None = None
    seen_ids: set[str] = set()
    expected_keys = set(object_ids)
    for position, transition in enumerate(transitions, start=1):
        if not isinstance(transition, Mapping):
            errors.append(f"transition {position} must be an object")
            continue
        transition_id = str(transition.get("id", ""))
        before = transition.get("before") if isinstance(transition.get("before"), Mapping) else {}
        after = transition.get("after") if isinstance(transition.get("after"), Mapping) else {}
        persistent = {str(value) for value in transition.get("persistent_object_ids", [])}
        if not transition_id or transition_id in seen_ids:
            errors.append(f"transition {position} needs a unique id")
        seen_ids.add(transition_id)
        if set(before) != expected_keys or set(after) != expected_keys or persistent != expected_keys:
            errors.append(f"transition {position} must carry complete before/after object identities")
        if before == after:
            errors.append(f"transition {position} does not change semantic state")
        if previous_after is not None and dict(before) != previous_after:
            errors.append(f"transition {position} breaks build-transform-resolve continuity")
        previous_after = dict(after)
    return errors


def build_algebra_video_payload(
    title: str,
    worked_example: Mapping[str, object] | None = None,
) -> dict[str, object]:
    spec = resolve_algebra_video_model(title, fail_closed=True)
    assert spec is not None
    text = _worked_text(worked_example)
    if spec is RING_SPEC:
        payload = _ring_payload(spec, text)
    elif spec is IDEAL_SPEC:
        payload = _ideal_payload(spec, text)
    else:
        payload = _field_payload(spec, text)
    errors = validate_algebra_video_payload(payload)
    if errors:
        raise ValueError("Invalid algebra video payload: " + "; ".join(errors))
    return payload

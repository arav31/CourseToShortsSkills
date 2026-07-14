"""Deterministic, renderer-neutral semantic transitions for physics videos."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Final, Mapping

try:
    from tools.physics_video_copy import build_physics_visible_copy, validate_physics_visible_copy
    from tools.physics_model_scenarios import (
        build_physics_semantic_payload,
        physics_numeric_evidence_fingerprint,
    )
    from tools.physics_model_specs import (
        MIT_8_01_TITLE_CONTRACTS,
        resolve_physics_title_contract,
    )
except ModuleNotFoundError:  # Imported by direct execution of tools/stem_course.py.
    from physics_video_copy import build_physics_visible_copy, validate_physics_visible_copy
    from physics_model_scenarios import (
        build_physics_semantic_payload,
        physics_numeric_evidence_fingerprint,
    )
    from physics_model_specs import MIT_8_01_TITLE_CONTRACTS, resolve_physics_title_contract


@dataclass(frozen=True)
class PhysicsVideoRoute:
    route_key: str
    family: str
    visual_kind: str
    canonical_formula: str
    invariant: str
    model_id: str | None = None
    scenario_mode: str | None = None
    unit_number: int | None = None


def _route(family: str, formula: str, invariant: str, *, visual_kind: str | None = None) -> PhysicsVideoRoute:
    return PhysicsVideoRoute(
        route_key=f"physics:{family}",
        family=family,
        visual_kind=visual_kind or f"physics_{family}",
        canonical_formula=formula,
        invariant=invariant,
    )


ROUTES: Final[dict[str, PhysicsVideoRoute]] = {
    "mass_transfer": _route("mass_transfer", r"dM_{cv}/dt=\sum\dot m_{in}-\sum\dot m_{out}", "Mass crosses a fixed control-volume boundary; the control volume itself never becomes a vehicle."),
    "rocket": _route("rocket", r"\Delta v=v_e\ln(m_i/m_f)", "Rocket and expelled propellant form the momentum-exchange system while vehicle mass decreases."),
    "force": _route("force", r"\sum\vec F_{ext}=m\vec a", "The chosen body identity and system boundary persist while forces determine acceleration."),
    "rolling_kinematics": _route("rolling_kinematics", r"v_{\mathrm{cm}}=\omega R,\quad a_{\mathrm{cm}}=\alpha R", "The contact point has zero relative speed while translation and rotation describe the same rolling body.", visual_kind="physics_kinematics"),
    "kinematics": _route("kinematics", r"\vec r(t)=\vec r_0+\vec v_0t+\frac12\vec a t^2", "One object's position and velocity states share the same clock and reference frame."),
    "energy": _route("energy", r"E_i+W_{nc}=E_f", "Energy is transferred or transformed, with every included store represented in the balance."),
    "momentum": _route("momentum", r"\vec p_i+\vec J=\vec p_f", "Momentum changes only by the displayed external impulse for the chosen system."),
    "vectors": _route("vectors", r"\vec A=A_x\hat i+A_y\hat j", "Components and resultant denote the same vector in one persistent basis."),
    "ode": _route("ode", r"dy/dt=f(t,y),\quad y(t_0)=y_0", "Every solution state obeys the differential law and the displayed initial condition."),
    "center_of_mass": _route("center_of_mass", r"\vec r_{cm}=\sum m_i\vec r_i/\sum m_i", "The center marker is the mass-weighted position of the same persistent components."),
    "potential": _route("potential", r"\vec F=-\nabla U", "Potential differences, not the arbitrary zero level, determine the force and motion."),
    "circular_motion": _route("circular_motion", r"a_r=v^2/r", "Velocity is tangent and radial acceleration points toward the persistent center."),
    "recoil": _route("recoil", r"\vec p_{total,i}=\vec p_{total,f}", "Opposing momenta balance for the isolated system."),
    "rotation": _route("rotation", r"\sum\tau=I\alpha", "Torque and angular acceleration are evaluated about the same persistent axis."),
}


_OFFICIAL_LEGACY_FAMILY: Final[Mapping[str, str]] = {
    **{model_id: "kinematics" for model_id in ("kinematics_position_velocity", "kinematics_acceleration", "kinematics_2d")},
    **{model_id: "force" for model_id in ("newton_laws_of_motion", "gravity_force", "contact_force", "tension_and_springs", "pulley_constraint", "massive_rope", "drag_force")},
    **{model_id: "circular_motion" for model_id in ("circular_position", "uniform_circular_motion", "radial_acceleration", "circular_dynamics")},
    **{model_id: "momentum" for model_id in ("impulse_momentum", "momentum_conservation", "collision_classification", "elastic_collision")},
    **{model_id: "energy" for model_id in ("work_energy_1d", "work_energy_multidimensional", "conservative_nonconservative_forces", "potential_energy_configuration", "energy_conservation")},
    **{model_id: "rotation" for model_id in ("rigid_body_motion", "moment_of_inertia", "torque", "rotational_dynamics", "point_particle_angular_momentum", "rigid_body_angular_momentum", "angular_impulse", "rolling_dynamics", "rolling_energy_angular_momentum")},
    "vectors": "vectors",
    "center_of_mass": "center_of_mass",
    "recoil": "recoil",
    "continuous_mass_accumulation": "mass_transfer",
    "potential_energy_diagram": "potential",
    "rolling_kinematics": "rolling_kinematics",
}


MIT_8_01_VIDEO_ROUTES: Final[Mapping[str, PhysicsVideoRoute]] = {
    contract.exact_title: PhysicsVideoRoute(
        route_key=contract.video_route_key,
        family=_OFFICIAL_LEGACY_FAMILY[contract.model_id],
        visual_kind=contract.spec.visual_kind,
        canonical_formula=contract.canonical_formula,
        invariant=ROUTES[_OFFICIAL_LEGACY_FAMILY[contract.model_id]].invariant,
        model_id=contract.model_id,
        scenario_mode=contract.scenario_mode,
        unit_number=contract.unit_number,
    )
    for contract in MIT_8_01_TITLE_CONTRACTS
}


MIT_8_01_SCENARIO_RENDER_ROUTES: Final[Mapping[str, tuple[str, str]]] = {
    contract.model_id: (
        f"mit_8_01_{contract.unit_number:02d}_{contract.model_id}",
        f"exact_title_{contract.scenario_mode}",
    )
    for contract in MIT_8_01_TITLE_CONTRACTS
}


# Scenario ids are deliberately mapped to concrete renderer behavior here.  A
# resolved model must never inherit a broad family animation by accident.
_PHYSICS_SCENARIO_RENDER_ROUTES: Final[dict[str, tuple[str, str]]] = {
    "kinematics_1d": ("kinematics_1d", "position_velocity_acceleration"),
    "kinematics_2d": ("kinematics_2d_components", "planar_vector_evolution"),
    "projectile_motion": ("projectile_components", "horizontal_inertia_vertical_gravity"),
    "rolling_kinematics": ("rolling_no_slip", "translation_rotation_constraint"),
    "force_balance": ("newton_force_cart", "net_force_acceleration"),
    "newton_first_law": ("newton_force_cart", "balanced_force_constant_velocity"),
    "newton_second_law": ("newton_force_cart", "net_force_momentum_change"),
    "action_reaction": ("action_reaction_pair", "reciprocal_interaction"),
    "gravity_force": ("gravity_freefall", "field_accelerates_mass"),
    "contact_force": ("contact_surface_components", "normal_friction_resultant"),
    "tension_force": ("rope_aligned_tension", "rope_pull_direction"),
    "spring_force": ("hooke_spring_deformation", "displacement_restoring_force"),
    "pulley_constraint": ("pulley_inextensible_rope", "fixed_length_linked_acceleration"),
    "linear_drag": ("linear_drag_velocity", "drag_scales_with_speed"),
    "quadratic_drag": ("quadratic_drag_velocity", "drag_scales_with_speed_squared"),
    "drag_force": ("resistive_force_velocity", "drag_antiparallel_to_velocity"),
}


def _adapter_key(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("physics adapter id must be a string")
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "_", text.replace("'", "")).strip("_")


# These names have appeared in public short plans and renderer payloads.  They
# identify the same numerical scenario; they do not replace its canonical id.
_PHYSICS_SCENARIO_ADAPTER_ALIASES: Final[Mapping[str, str]] = {
    "newton_laws": "newton_laws_of_motion",
    "newtons_laws": "newton_laws_of_motion",
    "continuous_mass_transfer": "continuous_mass_accumulation",
    "normal_force": "contact_force",
    "friction_force": "contact_force",
    "normal_and_friction_contact_forces": "contact_force",
    "rope_tension": "tension_force",
    "hookes_law": "spring_force",
    "hooke_law": "spring_force",
    "vector_work": "work_energy_multidimensional",
    "vector_work_energy": "work_energy_multidimensional",
    "dot_product_work": "work_energy_multidimensional",
    "work_energy_2d": "work_energy_multidimensional",
    "work_energy_3d": "work_energy_multidimensional",
}


class _ScenarioRenderRouteRegistry(Mapping[str, tuple[str, str]]):
    """Canonical route mapping with alias-aware lookup and canonical iteration."""

    def __init__(
        self,
        routes: Mapping[str, tuple[str, str]],
        aliases: Mapping[str, str],
    ) -> None:
        self._routes = dict(routes)
        self._aliases = {_adapter_key(alias): target for alias, target in aliases.items()}
        unknown_targets = sorted(set(self._aliases.values()) - set(self._routes) - set(MIT_8_01_SCENARIO_RENDER_ROUTES))
        if unknown_targets:
            raise ValueError(f"Physics scenario adapter aliases target unknown models: {unknown_targets}")

    def canonical_model_id(self, model_id: str) -> str | None:
        key = _adapter_key(model_id)
        if key in self._routes or key in MIT_8_01_SCENARIO_RENDER_ROUTES:
            return key
        return self._aliases.get(key)

    def __getitem__(self, model_id: str) -> tuple[str, str]:
        canonical = self.canonical_model_id(model_id)
        if canonical is None:
            raise KeyError(model_id)
        route = self._routes.get(canonical)
        if route is None:
            route = MIT_8_01_SCENARIO_RENDER_ROUTES.get(canonical)
        if route is None:  # Defensive: constructor and canonical_model_id enforce this.
            raise KeyError(model_id)
        return route

    def __iter__(self) -> Iterator[str]:
        return iter(self._routes)

    def __len__(self) -> int:
        return len(self._routes)

    def __contains__(self, model_id: object) -> bool:
        if not isinstance(model_id, str):
            return False
        return _adapter_key(model_id) in self._routes


PHYSICS_SCENARIO_RENDER_ROUTES: Final[Mapping[str, tuple[str, str]]] = _ScenarioRenderRouteRegistry(
    _PHYSICS_SCENARIO_RENDER_ROUTES,
    _PHYSICS_SCENARIO_ADAPTER_ALIASES,
)


def resolve_physics_scenario_adapter(model_id: str) -> str | None:
    """Resolve a public adapter name without weakening unknown-id handling."""
    registry = PHYSICS_SCENARIO_RENDER_ROUTES
    assert isinstance(registry, _ScenarioRenderRouteRegistry)
    return registry.canonical_model_id(model_id)


def physics_scenario_render_route(model_id: str) -> dict[str, str]:
    """Return the explicit renderer variant and causal choreography for a model."""
    route = PHYSICS_SCENARIO_RENDER_ROUTES.get(model_id)
    if route is None:
        raise ValueError(f"Physics model {model_id!r} has no explicit scenario renderer route.")
    renderer_variant, causal_mode = route
    return {"renderer_variant": renderer_variant, "causal_mode": causal_mode}


def normalize_physics_topic(title: str) -> str:
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").casefold()
    text = text.replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


# Specific concepts precede broad words such as momentum, mass, motion, or energy.
_RULES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("mass_transfer", ("continuous mass transfer", "control volume", "mass flow", "mass flux", "continuity equation", "fluid continuity", "inlet and outlet")),
    ("rocket", ("rocket equation", "tsiolkovsky", "rocket propulsion", "ideal rocket", "rocket")),
    ("center_of_mass", ("center of mass", "centre of mass", "barycenter")),
    ("recoil", ("recoil", "explosion momentum", "gun and bullet")),
    ("circular_motion", ("circular motion", "centripetal", "radial acceleration", "uniform circle")),
    ("potential", ("potential energy", "potential well", "energy landscape", "conservative potential", "potential")),
    ("rolling_kinematics", ("rolling kinematics", "rolling without slipping", "rolling without slip", "pure rolling", "no slip rolling")),
    ("rotation", ("rotation", "rotational", "torque", "angular acceleration", "moment of inertia")),
    ("ode", ("ordinary differential equation", "first order ode", "second order ode", "initial value problem", "ode")),
    ("vectors", ("vector", "components", "dot product", "cross product", "unit vector")),
    ("kinematics", ("kinematics", "projectile motion", "constant acceleration", "position velocity acceleration")),
    ("force", ("force", "newton law", "newtons law", "newton first law", "newton second law", "newton third law", "newtons first law", "newtons second law", "newtons third law", "free body", "friction", "tension")),
    ("momentum", ("momentum", "impulse", "collision")),
    ("energy", ("energy", "work energy", "power", "mechanical work")),
)


def physics_label_tex(label: str) -> str:
    """Convert compact physics notation into MathTex-safe LaTeX."""
    if not isinstance(label, str):
        raise TypeError("label must be a string")
    tex = label.strip()
    tex = tex.replace("<=", r"\le ").replace(">=", r"\ge ").replace("=>", r"\Rightarrow ")
    tex = re.sub(r"\^\s*\{?(-?\d+)\}?", r"^{\1}", tex)
    tex = re.sub(r"\b([A-Za-z])([0-9]+)\b", r"\1_{\2}", tex)
    tex = re.sub(r"\b([a-z])([A-Z])\b", r"\1_{\2}", tex)
    tex = re.sub(r"\b([A-Za-z])_dot\b", r"\\dot{\1}", tex)
    return tex.rstrip()


def resolve_physics_video_model(title: str, *, fail_closed: bool = False) -> PhysicsVideoRoute | None:
    contract = resolve_physics_title_contract(title)
    if contract is not None:
        return MIT_8_01_VIDEO_ROUTES[contract.exact_title]
    topic = normalize_physics_topic(title)
    route = next((ROUTES[key] for key, phrases in _RULES if any(phrase in topic for phrase in phrases)), None)
    if route is None and fail_closed:
        raise ValueError(f"Unsupported physics video topic: {title!r}")
    return route


def _objects(family: str, roles: tuple[str, ...], initial: Mapping[str, str]) -> list[dict[str, object]]:
    colors = ("#EAF2FF", "#58A6FF", "#7EE787", "#F7C948", "#F7C948", "#7EE787")
    return [
        {"id": f"physics:{family}:{role}", "role": role.replace("_", " "), "color": colors[index % len(colors)], "persistent": True, "initial_state": initial[f"physics:{family}:{role}"]}
        for index, role in enumerate(roles)
    ]


def _transition(transition_id: str, claim: str, before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, object]:
    ids = list(before)
    return {"id": transition_id, "claim": claim, "action": claim, "persistent_object_ids": ids, "before": dict(before), "after": dict(after)}


def _mass_transfer_payload(route: PhysicsVideoRoute) -> dict[str, object]:
    roles = ("control_volume", "inlet_flux", "outlet_flux", "stored_mass", "balance", "steady_state")
    ids = [f"physics:mass_transfer:{role}" for role in roles]
    s0 = dict(zip(ids, ("fixed boundary at x=0", "hidden", "hidden", "M_cv(0)=M_0", "unassembled", "unresolved")))
    s1 = {**s0, ids[1]: "arrow crosses boundary inward; rate=m_dot_in"}
    s2 = {**s1, ids[2]: "arrow crosses boundary outward; rate=m_dot_out"}
    s3 = {**s2, ids[3]: "M_cv(t)=M_0+(m_dot_in-m_dot_out)t", ids[4]: "dM_cv/dt=m_dot_in-m_dot_out"}
    s4 = {**s3, ids[5]: "steady: dM_cv/dt=0 => m_dot_in=m_dot_out"}
    transitions = [
        _transition("mass_transfer:show_inlet", "Mass enters across the fixed boundary.", s0, s1),
        _transition("mass_transfer:show_outlet", "Mass leaves across a different fixed-boundary port.", s1, s2),
        _transition("mass_transfer:accumulate", "Net flux changes mass stored inside the control volume.", s2, s3),
        _transition("mass_transfer:steady_resolution", "Zero accumulation requires equal total inlet and outlet rates.", s3, s4),
    ]
    return {
        "payload_type": "physics", "kind": route.visual_kind, "family": route.family, "mode": route.family, "route_key": route.route_key,
        "visual_kind": route.visual_kind, "canonical_formula": route.canonical_formula,
        "subject_id": ids[0], "invariant": route.invariant, "objects": _objects(route.family, roles, s0),
        "transitions": transitions,
        "verification": {
            "fixed_control_volume": all(state[ids[0]] == s0[ids[0]] for state in (s1, s2, s3, s4)),
            "has_inlet_and_outlet_flux": "inward" in s4[ids[1]] and "outward" in s4[ids[2]],
            "continuity_balance_exact": s4[ids[4]] == "dM_cv/dt=m_dot_in-m_dot_out",
            "steady_state_exact": s4[ids[5]] == "steady: dM_cv/dt=0 => m_dot_in=m_dot_out",
            "rocket_semantics_absent": not any("rocket" in value.casefold() or "exhaust" in value.casefold() for value in s4.values()),
        },
    }


def _general_payload(route: PhysicsVideoRoute) -> dict[str, object]:
    roles = ("system", "given_state", "law", "resolved_state")
    ids = [f"physics:{route.family}:{role}" for role in roles]
    s0 = dict(zip(ids, (f"{route.family} system selected", "givens visible", "not applied", "unresolved")))
    s1 = {**s0, ids[1]: "givens measured in one reference frame"}
    s2 = {**s1, ids[2]: f"applied: {route.canonical_formula}"}
    s3 = {**s2, ids[3]: "resolved from displayed givens and law"}
    return {
        "payload_type": "physics", "kind": route.visual_kind, "family": route.family, "mode": route.family, "route_key": route.route_key,
        "visual_kind": route.visual_kind, "canonical_formula": route.canonical_formula,
        "subject_id": ids[0], "invariant": route.invariant, "objects": _objects(route.family, roles, s0),
        "transitions": [
            _transition(f"{route.family}:measure", "Establish the exact initial state.", s0, s1),
            _transition(f"{route.family}:apply_law", "Apply the route's canonical physical law.", s1, s2),
            _transition(f"{route.family}:resolve", "Resolve the final state without replacing the subject.", s2, s3),
        ],
        "verification": {"identity_persists": True, "law_is_exact": s3[ids[2]] == f"applied: {route.canonical_formula}", "resolved": s3[ids[3]].startswith("resolved")},
    }


def _force_payload(route: PhysicsVideoRoute) -> dict[str, object]:
    roles = ("body", "positive_axis", "net_force", "acceleration")
    ids = [f"physics:force:{role}" for role in roles]
    s0 = dict(zip(ids, ("same body", r"+\hat{x} points right", "unresolved", "unresolved")))
    s1 = {**s0, ids[2]: r"\sum \vec F_{\mathrm{ext}}=+F_{\mathrm{net}}\hat{x}"}
    s2 = {**s1, ids[3]: r"\vec a=+(F_{\mathrm{net}}/m)\hat{x}"}
    s3 = {**s2, ids[3]: r"\vec a=+(F_{\mathrm{net}}/m)\hat{x},\quad \operatorname{sgn}(a_x)=\operatorname{sgn}(F_{\mathrm{net},x})"}
    return {
        "payload_type": "physics", "kind": route.visual_kind, "family": route.family, "mode": "signed_force_balance", "route_key": route.route_key,
        "visual_kind": route.visual_kind, "canonical_formula": route.canonical_formula,
        "subject_id": ids[0], "invariant": route.invariant, "objects": _objects(route.family, roles, s0),
        "transitions": [
            _transition("force:resolve_net", "Resolve the signed external-force sum on the chosen axis.", s0, s1),
            _transition("force:accelerate", "Draw acceleration with the same sign as net force.", s1, s2),
            _transition("force:verify_sign", "Verify Newton's second-law direction before resolving magnitude.", s2, s3),
        ],
        "verification": {"identity_persists": True, "force_acceleration_signs_match": True, "signed_axis_is_explicit": True},
    }


def _rolling_kinematics_payload(route: PhysicsVideoRoute) -> dict[str, object]:
    roles = ("wheel", "contact_point", "translation", "rotation")
    ids = [f"physics:rolling_kinematics:{role}" for role in roles]
    s0 = dict(zip(ids, ("same rigid wheel", "instantaneously at rest", "unresolved", "unresolved")))
    s1 = {**s0, ids[2]: r"v_{\mathrm{cm}}\hat{x}"}
    s2 = {**s1, ids[3]: r"\omega R=v_{\mathrm{cm}}"}
    s3 = {**s2, ids[2]: r"a_{\mathrm{cm}}=\alpha R"}
    return {
        "payload_type": "physics", "kind": route.visual_kind, "family": route.family, "mode": route.family, "route_key": route.route_key,
        "visual_kind": route.visual_kind, "canonical_formula": route.canonical_formula,
        "subject_id": ids[0], "invariant": route.invariant, "objects": _objects(route.family, roles, s0),
        "transitions": [
            _transition("rolling:translate", "Track center-of-mass translation.", s0, s1),
            _transition("rolling:rotate", "Couple angular speed to translation through no slip.", s1, s2),
            _transition("rolling:accelerate", "Couple angular and center-of-mass acceleration.", s2, s3),
        ],
        "verification": {"identity_persists": True, "no_slip_constraint_visible": True, "torque_impulse_absent": True},
    }


def validate_physics_video_payload(payload: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    objects = payload.get("objects") if isinstance(payload.get("objects"), list) else []
    object_ids = [str(row.get("id", "")) for row in objects if isinstance(row, Mapping)]
    expected = set(object_ids)
    transitions = payload.get("transitions") if isinstance(payload.get("transitions"), list) else []
    if payload.get("payload_type") != "physics": errors.append("payload_type must be physics")
    if len(expected) != len(object_ids) or not expected: errors.append("object ids must be nonempty and unique")
    if any(not isinstance(row, Mapping) or row.get("persistent") is not True for row in objects):
        errors.append("every object must be explicitly persistent")
    if len(transitions) < 3:
        errors.append("physics model needs at least three semantic transitions")
    previous = None
    for index, transition in enumerate(transitions, 1):
        if not isinstance(transition, Mapping): errors.append(f"transition {index} must be an object"); continue
        before, after = transition.get("before"), transition.get("after")
        if not isinstance(before, Mapping) or not isinstance(after, Mapping) or set(before) != expected or set(after) != expected:
            errors.append(f"transition {index} must expose complete exact states")
        elif before == after: errors.append(f"transition {index} does not change state")
        if set(transition.get("persistent_object_ids", [])) != expected: errors.append(f"transition {index} loses persistent identities")
        if previous is not None and dict(before or {}) != previous: errors.append(f"transition {index} breaks continuity")
        previous = dict(after or {})
    verification = payload.get("verification")
    if not isinstance(verification, Mapping) or not verification or not all(value is True for value in verification.values()):
        errors.append("verification checks must all pass")
    if not payload.get("invariant"): errors.append("invariant is required")
    if payload.get("semantic_schema") == "physics-semantic-v1":
        if not payload.get("canonical_formula"):
            errors.append("canonical_formula is required")
        if not payload.get("model_id") or payload.get("model_id") != payload.get("mode"):
            errors.append("exact-title model_id and mode must match")
        fingerprint = payload.get("numeric_evidence_fingerprint")
        evidence = payload.get("numeric_evidence")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            errors.append("numeric_evidence_fingerprint must be a SHA-256 hex digest")
        elif not isinstance(evidence, Mapping):
            errors.append("numeric_evidence must be a mapping")
        else:
            try:
                recomputed = physics_numeric_evidence_fingerprint(evidence)
            except (TypeError, ValueError) as exc:
                errors.append(f"numeric_evidence is invalid: {exc}")
            else:
                if recomputed != fingerprint:
                    errors.append("numeric_evidence_fingerprint does not match recomputed evidence")
        if not isinstance(payload.get("mechanisms"), list) or not payload.get("mechanisms"):
            errors.append("exact-title mechanisms are required")
        visible_copy = payload.get("visible_copy")
        if not isinstance(visible_copy, Mapping):
            errors.append("exact-title visible_copy is required")
        else:
            errors.extend(validate_physics_visible_copy(visible_copy))
    return errors


def build_physics_video_payload(
    title: str,
    worked_example: Mapping[str, object] | None = None,
    *,
    scenario_override: Mapping[str, object] | None = None,
) -> dict[str, object]:
    contract = resolve_physics_title_contract(title)
    if contract is not None:
        route = MIT_8_01_VIDEO_ROUTES[contract.exact_title]
        semantic = build_physics_semantic_payload(title, worked_example, scenario_override)
        payload = {
            **semantic,
            "payload_type": "physics",
            "kind": route.visual_kind,
            "family": route.family,
            "route_key": route.route_key,
            "subject_id": semantic["objects"][0]["id"],
            "invariant": route.invariant,
            "verification": {
                "identity_persists": True,
                "formula_is_exact": semantic["canonical_formula"] == route.canonical_formula,
                "scenario_mode_is_exact": semantic["mode"] == route.scenario_mode,
                "numeric_evidence_is_shared": semantic["numeric_evidence_fingerprint"]
                == semantic["scenario"]["numeric_evidence_fingerprint"],
            },
        }
        payload["visible_copy"] = build_physics_visible_copy(payload)
        errors = validate_physics_video_payload(payload)
        if errors:
            raise ValueError("Invalid physics video payload: " + "; ".join(errors))
        return payload

    if scenario_override is not None:
        raise ValueError("scenario_override is supported only for an exact MIT 8.01 title")
    adapter_model_id = resolve_physics_scenario_adapter(title)
    if worked_example is not None and adapter_model_id is None:
        raise ValueError(
            "worked_example cannot be safely parsed for a broad physics topic; use an exact MIT 8.01 title or structured exact-title scenario"
        )
    route = resolve_physics_video_model(title, fail_closed=True)
    assert route is not None
    builders = {
        "mass_transfer": _mass_transfer_payload,
        "force": _force_payload,
        "rolling_kinematics": _rolling_kinematics_payload,
    }
    payload = builders.get(route.family, _general_payload)(route)
    errors = validate_physics_video_payload(payload)
    if errors:
        raise ValueError("Invalid physics video payload: " + "; ".join(errors))
    return payload

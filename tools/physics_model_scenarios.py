"""Immutable numerical scenarios for every registered mechanics model.

The module is deliberately independent of stem_course.  A scenario is built
only from a frozen default setup and a pure calculator selected by model_id.
Displayed calculation and result fields are therefore always recomputed from
the setup instead of copied from prose or stored conclusions.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Callable, Final, Optional, Sequence, Tuple, Union

try:
    from tools.physics_model_specs import (
        MIT_8_01_TITLE_CONTRACTS,
        PHYSICS_MODEL_REGISTRY,
        PhysicsTitleContract,
        resolve_physics_title_contract,
    )
except ModuleNotFoundError:  # Imported by direct execution of tools/stem_course.py.
    from physics_model_specs import (
        MIT_8_01_TITLE_CONTRACTS,
        PHYSICS_MODEL_REGISTRY,
        PhysicsTitleContract,
        resolve_physics_title_contract,
    )


CalculatorResult = Tuple[Mapping[str, object], Mapping[str, object]]
Calculator = Callable[[Mapping[str, object]], CalculatorResult]


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return FrozenFields.from_mapping(value)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: object) -> object:
    if isinstance(value, FrozenFields):
        return value.as_dict()
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


@dataclass(frozen=True, eq=False)
class FrozenFields(Mapping[str, object]):
    """Small recursively immutable mapping used by public scenario payloads."""

    _items: Tuple[Tuple[str, object], ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "FrozenFields":
        items = tuple((key, _freeze_value(value)) for key, value in values.items())
        if any(not isinstance(key, str) for key, _ in items):
            raise TypeError("scenario field names must be strings")
        if len({key for key, _ in items}) != len(items):
            raise ValueError("scenario field names must be unique")
        return cls(items)

    def __getitem__(self, key: str) -> object:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def as_dict(self) -> dict[str, object]:
        return {key: _thaw_value(value) for key, value in self._items}


@dataclass(frozen=True)
class AnimationState(Mapping[str, object]):
    """One immutable state in the semantic animation sequence."""

    state_id: str
    phase: str
    progress: float
    values: FrozenFields = field()
    visible_tokens: Tuple[str, ...]
    visible_object_ids: Tuple[str, ...]
    result_fields: Tuple[str, ...]

    @property
    def visible_evidence_tokens(self) -> Tuple[str, ...]:
        return self.visible_tokens

    def __getitem__(self, key: str) -> object:
        if key == "visible_evidence_tokens":
            return self.visible_tokens
        if key in _ANIMATION_FIELD_NAMES:
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(_ANIMATION_FIELD_NAMES)

    def __len__(self) -> int:
        return len(_ANIMATION_FIELD_NAMES)

    def as_dict(self) -> dict[str, object]:
        return {
            "state_id": self.state_id,
            "phase": self.phase,
            "progress": self.progress,
            "values": self.values.as_dict(),
            "visible_tokens": list(self.visible_tokens),
            "visible_evidence_tokens": list(self.visible_tokens),
            "visible_object_ids": list(self.visible_object_ids),
            "result_fields": list(self.result_fields),
        }


_ANIMATION_FIELD_NAMES: Final[Tuple[str, ...]] = (
    "state_id",
    "phase",
    "progress",
    "values",
    "visible_tokens",
    "visible_object_ids",
    "result_fields",
)


@dataclass(frozen=True)
class PhysicsModelScenario(Mapping[str, object]):
    """A complete, immutable and renderer-neutral mechanics scenario."""

    model_id: str
    mode: str
    setup: FrozenFields
    calculation: FrozenFields
    result: FrozenFields
    animation_states: Tuple[AnimationState, ...]
    required_example_tokens: Tuple[str, ...]
    required_figure_tokens: Tuple[str, ...]
    visible_evidence_tokens: Tuple[str, ...]

    @property
    def numeric_setup(self) -> FrozenFields:
        return self.setup

    @property
    def calculation_fields(self) -> FrozenFields:
        return self.calculation

    @property
    def result_fields(self) -> FrozenFields:
        return self.result

    @property
    def results(self) -> FrozenFields:
        return self.result

    @property
    def animation_state_sequence(self) -> Tuple[AnimationState, ...]:
        return self.animation_states

    @property
    def evidence_tokens(self) -> Tuple[str, ...]:
        return self.visible_evidence_tokens

    @property
    def exact_visible_evidence_tokens(self) -> Tuple[str, ...]:
        return self.visible_evidence_tokens

    @property
    def numeric_evidence_fingerprint(self) -> str:
        return physics_numeric_evidence_fingerprint(self)

    def rebuild(self, setup_overrides: Mapping[str, object]) -> "PhysicsModelScenario":
        return build_physics_model_scenario(self.model_id, setup_overrides)

    def __getitem__(self, key: str) -> object:
        if key == "numeric_evidence_fingerprint":
            return self.numeric_evidence_fingerprint
        aliases = {
            "numeric_setup": self.setup,
            "calculation_fields": self.calculation,
            "result_fields": self.result,
            "results": self.result,
            "animation_state_sequence": self.animation_states,
            "evidence_tokens": self.visible_evidence_tokens,
            "exact_visible_evidence_tokens": self.visible_evidence_tokens,
        }
        if key in aliases:
            return aliases[key]
        if key in _SCENARIO_FIELD_NAMES:
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(_SCENARIO_FIELD_NAMES)

    def __len__(self) -> int:
        return len(_SCENARIO_FIELD_NAMES)

    def as_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "mode": self.mode,
            "setup": self.setup.as_dict(),
            "calculation": self.calculation.as_dict(),
            "result": self.result.as_dict(),
            "results": self.result.as_dict(),
            "animation_states": [state.as_dict() for state in self.animation_states],
            "required_example_tokens": list(self.required_example_tokens),
            "required_figure_tokens": list(self.required_figure_tokens),
            "visible_evidence_tokens": list(self.visible_evidence_tokens),
            "numeric_evidence_fingerprint": self.numeric_evidence_fingerprint,
        }


_SCENARIO_FIELD_NAMES: Final[Tuple[str, ...]] = (
    "model_id",
    "mode",
    "setup",
    "calculation",
    "result",
    "animation_states",
    "required_example_tokens",
    "required_figure_tokens",
    "visible_evidence_tokens",
)


def _canonical_numeric_evidence(value: object) -> object:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("numeric evidence contains a non-finite value")
        return 0.0 if number == 0.0 else number
    if isinstance(value, Mapping):
        return {
            str(key): canonical
            for key in sorted(value)
            if (canonical := _canonical_numeric_evidence(value[key])) is not None
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_canonical_numeric_evidence(item) for item in value]
    raise TypeError(f"numeric evidence contains unsupported value {value!r}")


def physics_numeric_evidence_fingerprint(
    scenario: Union[PhysicsModelScenario, Mapping[str, object]],
) -> str:
    """Hash only recomputed setup/calculation/result numeric evidence."""

    if not isinstance(scenario, Mapping):
        raise TypeError("scenario must be a physics scenario mapping")
    try:
        evidence = {
            "setup": _canonical_numeric_evidence(scenario["setup"]),
            "calculation": _canonical_numeric_evidence(scenario["calculation"]),
            "result": _canonical_numeric_evidence(scenario["result"]),
        }
    except KeyError as error:
        raise ValueError("scenario must contain setup, calculation, and result") from error
    serialized = json.dumps(evidence, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class PhysicsScenarioDefinition:
    """Frozen data selecting one setup, calculator and animation vocabulary."""

    mode: str
    setup: FrozenFields
    calculator: Calculator
    state_ids: Tuple[str, str, str]
    distinguishing_tokens: Tuple[str, ...] = ()


def _number(setup: Mapping[str, object], key: str) -> float:
    value = setup[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{key} must be a finite number")
    return number


def _numbers(setup: Mapping[str, object], key: str) -> Tuple[float, ...]:
    value = setup[key]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{key} must be a numeric sequence")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise TypeError(f"{key} must be a numeric sequence")
    numbers = tuple(float(item) for item in value)
    if not numbers or any(not math.isfinite(item) for item in numbers):
        raise ValueError(f"{key} must contain finite numbers")
    return numbers


def _vector2(setup: Mapping[str, object], key: str) -> Tuple[float, float]:
    values = _numbers(setup, key)
    if len(values) != 2:
        raise ValueError(f"{key} must contain exactly two components")
    return values[0], values[1]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _magnitude(vector: Sequence[float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _kinematics_1d(setup: Mapping[str, object]) -> CalculatorResult:
    x0 = _number(setup, "initial_position")
    v0 = _number(setup, "initial_velocity")
    acceleration = _number(setup, "acceleration")
    elapsed = _number(setup, "elapsed_time")
    velocity_term = v0 * elapsed
    acceleration_term = 0.5 * acceleration * elapsed**2
    return (
        {"velocity_displacement": velocity_term, "acceleration_displacement": acceleration_term},
        {"final_position": x0 + velocity_term + acceleration_term, "final_velocity": v0 + acceleration * elapsed},
    )


def _kinematics_position_velocity(setup: Mapping[str, object]) -> CalculatorResult:
    calculation, result = _kinematics_1d(setup)
    calculation = dict(calculation)
    result = dict(result)
    calculation["position_graph_endpoint"] = (setup["elapsed_time"], result["final_position"])
    calculation["velocity_graph_endpoint"] = (setup["elapsed_time"], result["final_velocity"])
    result["same_particle_and_clock"] = True
    return calculation, result


def _kinematics_acceleration(setup: Mapping[str, object]) -> CalculatorResult:
    calculation, result = _kinematics_1d(setup)
    acceleration = _number(setup, "acceleration")
    elapsed = _number(setup, "elapsed_time")
    calculation = dict(calculation)
    result = dict(result)
    calculation["velocity_change"] = acceleration * elapsed
    result["acceleration_is_velocity_slope"] = True
    return calculation, result


def _kinematics_2d(setup: Mapping[str, object]) -> CalculatorResult:
    position = _vector2(setup, "initial_position_vector")
    velocity = _vector2(setup, "initial_velocity_vector")
    acceleration = _vector2(setup, "acceleration_vector")
    elapsed = _number(setup, "elapsed_time")
    velocity_displacement = tuple(component * elapsed for component in velocity)
    acceleration_displacement = tuple(0.5 * component * elapsed**2 for component in acceleration)
    final_position = tuple(position[i] + velocity_displacement[i] + acceleration_displacement[i] for i in range(2))
    final_velocity = tuple(velocity[i] + acceleration[i] * elapsed for i in range(2))
    return (
        {"velocity_displacement_vector": velocity_displacement, "acceleration_displacement_vector": acceleration_displacement},
        {"final_position_vector": final_position, "final_velocity_vector": final_velocity},
    )


def _projectile_motion(setup: Mapping[str, object]) -> CalculatorResult:
    launch = _vector2(setup, "launch_position")
    speed = _number(setup, "initial_speed")
    angle = math.radians(_number(setup, "launch_angle"))
    gravity = _number(setup, "gravity")
    elapsed = _number(setup, "elapsed_time")
    horizontal_velocity = speed * math.cos(angle)
    initial_vertical_velocity = speed * math.sin(angle)
    final_position = (
        launch[0] + horizontal_velocity * elapsed,
        launch[1] + initial_vertical_velocity * elapsed - 0.5 * gravity * elapsed**2,
    )
    final_velocity = (horizontal_velocity, initial_vertical_velocity - gravity * elapsed)
    return (
        {"horizontal_velocity": horizontal_velocity, "initial_vertical_velocity": initial_vertical_velocity, "gravity_drop": 0.5 * gravity * elapsed**2},
        {"final_position_vector": final_position, "final_velocity_vector": final_velocity, "trajectory_is_parabolic": True},
    )


def _rolling_kinematics(setup: Mapping[str, object]) -> CalculatorResult:
    radius = _number(setup, "radius")
    angular_speed = _number(setup, "angular_speed")
    angular_acceleration = _number(setup, "angular_acceleration")
    elapsed = _number(setup, "elapsed_time")
    center_speed = angular_speed * radius
    center_acceleration = angular_acceleration * radius
    angular_displacement = angular_speed * elapsed + 0.5 * angular_acceleration * elapsed**2
    final_angular_speed = angular_speed + angular_acceleration * elapsed
    return (
        {"center_speed": center_speed, "center_acceleration": center_acceleration, "rotation_angle": angular_displacement},
        {"center_displacement": radius * angular_displacement, "final_angular_speed": final_angular_speed, "final_center_speed": radius * final_angular_speed, "contact_speed": 0.0, "no_slip_satisfied": True},
    )


def _force_balance(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    forces = _numbers(setup, "external_forces")
    net_force = sum(forces)
    return ({"force_sum": net_force}, {"net_force": net_force, "acceleration": net_force / mass})


def _newton_first_law(setup: Mapping[str, object]) -> CalculatorResult:
    forces = _numbers(setup, "external_forces")
    velocity = _number(setup, "initial_velocity")
    elapsed = _number(setup, "time_interval")
    net_force = sum(forces)
    acceleration = net_force / _number(setup, "mass")
    return (
        {"force_sum": net_force, "acceleration": acceleration, "velocity_change": acceleration * elapsed},
        {"final_velocity": velocity + acceleration * elapsed, "constant_velocity": math.isclose(net_force, 0.0)},
    )


def _newton_second_law(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    forces = _numbers(setup, "external_forces")
    elapsed = _number(setup, "time_interval")
    net_force = sum(forces)
    acceleration = net_force / mass
    return (
        {"force_sum": net_force, "momentum_change": net_force * elapsed},
        {"acceleration": acceleration, "final_velocity": _number(setup, "initial_velocity") + acceleration * elapsed},
    )


def _newton_laws(setup: Mapping[str, object]) -> CalculatorResult:
    initial = _number(setup, "initial_momentum")
    final = _number(setup, "final_momentum")
    elapsed = _number(setup, "time_interval")
    change = final - initial
    return ({"momentum_change": change}, {"average_external_force": change / elapsed, "final_momentum": final})


def _action_reaction(setup: Mapping[str, object]) -> CalculatorResult:
    force = _number(setup, "interaction_force")
    masses = _numbers(setup, "masses")
    if len(masses) != 2:
        raise ValueError("masses must contain two values")
    pair = (force, -force)
    return (
        {"force_on_b_by_a": pair[0], "force_on_a_by_b": pair[1], "internal_force_sum": sum(pair)},
        {"force_pair": pair, "accelerations": (pair[1] / masses[0], pair[0] / masses[1]), "different_bodies": True},
    )


def _newton_laws_of_motion(setup: Mapping[str, object]) -> CalculatorResult:
    force = _number(setup, "interaction_force")
    masses = _numbers(setup, "masses")
    if len(masses) != 2 or any(mass <= 0.0 for mass in masses):
        raise ValueError("masses must contain two positive values")
    force_pair = (-force, force)
    return (
        {
            "force_on_a_by_b": force_pair[0],
            "force_on_b_by_a": force_pair[1],
            "internal_force_sum": sum(force_pair),
        },
        {
            "force_pair": force_pair,
            "accelerations": (force_pair[0] / masses[0], force_pair[1] / masses[1]),
            "different_bodies": True,
        },
    )


def _gravity_force(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    field = _vector2(setup, "gravitational_field")
    weight = tuple(mass * component for component in field)
    return ({"mass_times_field": weight}, {"weight_vector": weight, "weight_magnitude": _magnitude(weight)})


def _contact_force(setup: Mapping[str, object]) -> CalculatorResult:
    normal = _number(setup, "normal_force")
    friction = _number(setup, "friction_force")
    contact = (friction, normal)
    return ({"normal_component": (0.0, normal), "tangent_component": (friction, 0.0)}, {"contact_force_vector": contact, "contact_force_magnitude": _magnitude(contact)})


def _tension_force(setup: Mapping[str, object]) -> CalculatorResult:
    magnitude = _number(setup, "tension_magnitude")
    direction = _vector2(setup, "rope_direction")
    norm = _magnitude(direction)
    if math.isclose(norm, 0.0):
        raise ValueError("rope_direction must be nonzero")
    unit = tuple(component / norm for component in direction)
    tension = tuple(magnitude * component for component in unit)
    return ({"rope_unit_vector": unit}, {"tension_vector": tension, "tension_magnitude": _magnitude(tension)})


def _spring_force(setup: Mapping[str, object]) -> CalculatorResult:
    spring_constant = _number(setup, "spring_constant")
    displacement = _number(setup, "displacement")
    force = -spring_constant * displacement
    return ({"restoring_product": spring_constant * displacement}, {"spring_force": force, "stored_energy": 0.5 * spring_constant * displacement**2})


def _tension_and_springs(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    tension = _number(setup, "tension_force")
    spring_constant = _number(setup, "spring_constant")
    displacement = _number(setup, "displacement")
    if mass <= 0.0 or spring_constant <= 0.0:
        raise ValueError("mass and spring_constant must be positive")
    spring_force = -spring_constant * displacement
    net_force = tension + spring_force
    return (
        {
            "tension_force": tension,
            "spring_force": spring_force,
            "stored_spring_energy": 0.5 * spring_constant * displacement**2,
            "net_force": net_force,
        },
        {"acceleration": net_force / mass, "both_mechanisms_visible": True},
    )


def _massive_rope(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "rope_mass")
    length = _number(setup, "rope_length")
    trailing = _number(setup, "trailing_tension")
    leading = _number(setup, "leading_tension")
    if mass <= 0.0 or length <= 0.0:
        raise ValueError("rope_mass and rope_length must be positive")
    tension_change = leading - trailing
    acceleration = tension_change / mass
    return (
        {
            "linear_mass_density": mass / length,
            "tension_change": tension_change,
            "tension_gradient": tension_change / length,
        },
        {
            "acceleration": acceleration,
            "tension_at_start": trailing,
            "tension_at_end": leading,
            "tension_is_nonuniform": not math.isclose(trailing, leading),
        },
    )


def _pulley_constraint(setup: Mapping[str, object]) -> CalculatorResult:
    mass_1 = _number(setup, "mass_1")
    mass_2 = _number(setup, "mass_2")
    gravity = _number(setup, "gravity")
    acceleration = (mass_2 - mass_1) * gravity / (mass_1 + mass_2)
    tension = mass_1 * (gravity + acceleration)
    return (
        {"driving_force": (mass_2 - mass_1) * gravity, "shared_acceleration_magnitude": acceleration},
        {"accelerations": (-acceleration, acceleration), "tension": tension, "string_length_change": 0.0},
    )


def _linear_drag(setup: Mapping[str, object]) -> CalculatorResult:
    coefficient = _number(setup, "drag_coefficient")
    velocity = _vector2(setup, "relative_velocity")
    force = tuple(-coefficient * component for component in velocity)
    return ({"speed": _magnitude(velocity), "linear_drag_magnitude": _magnitude(force)}, {"drag_force_vector": force})


def _quadratic_drag(setup: Mapping[str, object]) -> CalculatorResult:
    density = _number(setup, "fluid_density")
    coefficient = _number(setup, "drag_coefficient")
    area = _number(setup, "reference_area")
    velocity = _vector2(setup, "relative_velocity")
    speed = _magnitude(velocity)
    scale = -0.5 * density * coefficient * area * speed
    force = tuple(scale * component for component in velocity)
    return ({"speed": speed, "dynamic_pressure_factor": 0.5 * density * speed**2, "quadratic_drag_magnitude": _magnitude(force)}, {"drag_force_vector": force})


def _drag_force(setup: Mapping[str, object]) -> CalculatorResult:
    base = _number(setup, "base_drag")
    quadratic = _number(setup, "quadratic_coefficient")
    velocity = _vector2(setup, "relative_velocity")
    speed = _magnitude(velocity)
    if math.isclose(speed, 0.0):
        raise ValueError("relative_velocity must be nonzero for a directed drag force")
    magnitude = base + quadratic * speed**2
    unit = tuple(component / speed for component in velocity)
    force = tuple(-magnitude * component for component in unit)
    return ({"speed": speed, "drag_law_value": magnitude, "velocity_unit_vector": unit}, {"drag_force_vector": force, "opposes_velocity": _dot(force, velocity) < 0.0})


def _momentum_definition(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    velocity = _vector2(setup, "velocity")
    momentum = tuple(mass * component for component in velocity)
    return ({"component_products": momentum}, {"momentum_vector": momentum, "momentum_magnitude": _magnitude(momentum)})


def _impulse_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    initial = _number(setup, "initial_momentum")
    samples = _numbers(setup, "force_samples")
    interval = _number(setup, "sample_interval")
    if len(samples) < 2:
        raise ValueError("force_samples must contain at least two samples")
    segment_impulses = tuple(0.5 * (left + right) * interval for left, right in zip(samples, samples[1:]))
    impulse = sum(segment_impulses)
    return ({"segment_impulses": segment_impulses, "impulse": impulse}, {"momentum_change": impulse, "final_momentum": initial + impulse})


def _momentum_conservation(setup: Mapping[str, object]) -> CalculatorResult:
    masses = _numbers(setup, "masses")
    initial_velocities = _numbers(setup, "initial_velocities")
    if len(masses) != 2 or len(initial_velocities) != 2:
        raise ValueError("masses and initial_velocities must contain two values")
    external_impulse = _number(setup, "external_impulse")
    final_velocity_1 = _number(setup, "final_velocity_1")
    initial_total = _dot(masses, initial_velocities)
    target_total = initial_total + external_impulse
    final_velocity_2 = (target_total - masses[0] * final_velocity_1) / masses[1]
    return (
        {"initial_total_momentum": initial_total, "target_final_momentum": target_total},
        {"final_velocities": (final_velocity_1, final_velocity_2), "final_total_momentum": target_total, "momentum_residual": 0.0},
    )


def _collision_solution(setup: Mapping[str, object], restitution: float) -> CalculatorResult:
    masses = _numbers(setup, "masses")
    velocities = _numbers(setup, "initial_velocities")
    if len(masses) != 2 or len(velocities) != 2:
        raise ValueError("masses and initial_velocities must contain two values")
    mass_1, mass_2 = masses
    velocity_1, velocity_2 = velocities
    total_mass = mass_1 + mass_2
    total_momentum = mass_1 * velocity_1 + mass_2 * velocity_2
    final_1 = (total_momentum - mass_2 * restitution * (velocity_1 - velocity_2)) / total_mass
    final_2 = (total_momentum + mass_1 * restitution * (velocity_1 - velocity_2)) / total_mass
    energy_before = 0.5 * mass_1 * velocity_1**2 + 0.5 * mass_2 * velocity_2**2
    energy_after = 0.5 * mass_1 * final_1**2 + 0.5 * mass_2 * final_2**2
    calculation = {
        "initial_total_momentum": total_momentum,
        "relative_approach_speed": velocity_1 - velocity_2,
        "coefficient_of_restitution": restitution,
    }
    result = {
        "final_velocities": (final_1, final_2),
        "final_total_momentum": mass_1 * final_1 + mass_2 * final_2,
        "kinetic_energy_before": energy_before,
        "kinetic_energy_after": energy_after,
        "kinetic_energy_loss": energy_before - energy_after,
    }
    return calculation, result


def _elastic_collision(setup: Mapping[str, object]) -> CalculatorResult:
    calculation, result = _collision_solution(setup, 1.0)
    result = dict(result)
    result.update({"bodies_separate": True, "kinetic_energy_conserved": True})
    return calculation, result


def _inelastic_collision(setup: Mapping[str, object]) -> CalculatorResult:
    restitution = _number(setup, "coefficient_of_restitution")
    if not 0.0 < restitution < 1.0:
        raise ValueError("coefficient_of_restitution must lie strictly between zero and one")
    calculation, result = _collision_solution(setup, restitution)
    result = dict(result)
    result.update({"bodies_separate": True, "kinetic_energy_conserved": False})
    return calculation, result


def _perfectly_inelastic_collision(setup: Mapping[str, object]) -> CalculatorResult:
    calculation, generic_result = _collision_solution(setup, 0.0)
    shared_velocity = generic_result["final_velocities"][0]  # type: ignore[index]
    result = dict(generic_result)
    result.update({"shared_final_velocity": shared_velocity, "bodies_stick": True, "kinetic_energy_conserved": False})
    return calculation, result


def _collision_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    masses = _numbers(setup, "masses")
    initial_velocities = _numbers(setup, "initial_velocities")
    if len(masses) != 2 or len(initial_velocities) != 2:
        raise ValueError("masses and initial_velocities must contain two values")
    impulse = _number(setup, "external_impulse")
    final_velocity_1 = _number(setup, "final_velocity_1")
    initial_total = _dot(masses, initial_velocities)
    final_total = initial_total + impulse
    final_velocity_2 = (final_total - masses[0] * final_velocity_1) / masses[1]
    return (
        {"initial_total_momentum": initial_total, "external_impulse": impulse, "target_final_momentum": final_total},
        {"final_velocities": (final_velocity_1, final_velocity_2), "final_total_momentum": final_total},
    )


def _collision_classification(setup: Mapping[str, object]) -> CalculatorResult:
    masses = _numbers(setup, "masses")
    initial = _numbers(setup, "initial_velocities")
    final = _numbers(setup, "final_velocities")
    if len(masses) != 2 or len(initial) != 2 or len(final) != 2:
        raise ValueError("masses and velocity states must each contain two values")
    momentum_before = _dot(masses, initial)
    momentum_after = _dot(masses, final)
    kinetic_before = 0.5 * sum(mass * velocity**2 for mass, velocity in zip(masses, initial))
    kinetic_after = 0.5 * sum(mass * velocity**2 for mass, velocity in zip(masses, final))
    momentum_conserved = math.isclose(momentum_before, momentum_after, rel_tol=1e-9, abs_tol=1e-9)
    sticking = math.isclose(final[0], final[1], rel_tol=1e-9, abs_tol=1e-9)
    if not momentum_conserved:
        classification = "not_isolated_or_invalid"
    elif math.isclose(kinetic_before, kinetic_after, rel_tol=1e-9, abs_tol=1e-9):
        classification = "elastic"
    elif sticking:
        classification = "perfectly_inelastic"
    elif kinetic_after < kinetic_before:
        classification = "inelastic"
    else:
        classification = "superelastic"
    return (
        {
            "momentum_before": momentum_before,
            "momentum_after": momentum_after,
            "kinetic_energy_before": kinetic_before,
            "kinetic_energy_after": kinetic_after,
        },
        {
            "classification": classification,
            "momentum_conserved": momentum_conserved,
            "sticking": sticking,
            "kinetic_energy_change": kinetic_after - kinetic_before,
        },
    )


def _work_definition(setup: Mapping[str, object]) -> CalculatorResult:
    force = _vector2(setup, "force_vector")
    displacement = _vector2(setup, "displacement_vector")
    force_magnitude = _magnitude(force)
    displacement_magnitude = _magnitude(displacement)
    if math.isclose(force_magnitude * displacement_magnitude, 0.0):
        raise ValueError("force and displacement vectors must be nonzero")
    cosine = _dot(force, displacement) / (force_magnitude * displacement_magnitude)
    work = _dot(force, displacement)
    return ({"force_magnitude": force_magnitude, "displacement_magnitude": displacement_magnitude, "direction_cosine": cosine}, {"work": work})


def _work_energy_theorem(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    initial_speed = _number(setup, "initial_speed")
    net_force = _number(setup, "net_force")
    distance = _number(setup, "distance")
    work = net_force * distance
    initial_energy = 0.5 * mass * initial_speed**2
    final_energy = initial_energy + work
    return (
        {"net_work": work, "initial_kinetic_energy": initial_energy, "final_kinetic_energy": final_energy},
        {"kinetic_energy_change": work, "final_speed": math.sqrt(2.0 * final_energy / mass)},
    )


def _work_energy_1d(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    initial_speed = _number(setup, "initial_speed")
    force = _number(setup, "force")
    distance = _number(setup, "distance")
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    work = force * distance
    initial_energy = 0.5 * mass * initial_speed**2
    final_energy = initial_energy + work
    if final_energy < 0.0:
        raise ValueError("work would produce negative final kinetic energy")
    return (
        {"work": work, "initial_kinetic_energy": initial_energy, "final_kinetic_energy": final_energy},
        {"kinetic_energy_change": work, "final_speed": math.sqrt(2.0 * final_energy / mass)},
    )


def _work_energy_multidimensional(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    initial_speed = _number(setup, "initial_speed")
    force = _vector2(setup, "force_vector")
    displacement = _vector2(setup, "displacement_vector")
    if mass <= 0.0:
        raise ValueError("mass must be positive")
    work = _dot(force, displacement)
    initial_energy = 0.5 * mass * initial_speed**2
    final_energy = initial_energy + work
    if final_energy < 0.0:
        raise ValueError("work would produce negative final kinetic energy")
    return (
        {
            "dot_product_terms": tuple(force[i] * displacement[i] for i in range(2)),
            "dot_product_work": work,
            "initial_kinetic_energy": initial_energy,
        },
        {"final_kinetic_energy": final_energy, "final_speed": math.sqrt(2.0 * final_energy / mass)},
    )


def _conservative_nonconservative_forces(setup: Mapping[str, object]) -> CalculatorResult:
    conservative_force = _number(setup, "conservative_force")
    nonconservative_force = _number(setup, "nonconservative_force")
    displacement = _number(setup, "displacement")
    conservative_work = conservative_force * displacement
    nonconservative_work = nonconservative_force * displacement
    return (
        {
            "conservative_work": conservative_work,
            "nonconservative_work": nonconservative_work,
            "potential_energy_change": -conservative_work,
        },
        {
            "net_work": conservative_work + nonconservative_work,
            "mechanical_energy_change": nonconservative_work,
            "mechanisms_are_distinct": True,
        },
    )


def _potential_energy_configuration(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    spring_constant = _number(setup, "spring_constant")
    displacement = _number(setup, "displacement")
    if mass <= 0.0 or spring_constant <= 0.0:
        raise ValueError("mass and spring_constant must be positive")
    stored = 0.5 * spring_constant * displacement**2
    return (
        {"squared_displacement": displacement**2, "stored_energy": stored},
        {
            "release_speed": math.sqrt(2.0 * stored / mass),
            "reference_position": _number(setup, "reference_position"),
        },
    )


def _gravitational_potential_energy(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    gravity = _number(setup, "gravity")
    initial = _number(setup, "initial_height")
    final = _number(setup, "final_height")
    height_change = final - initial
    return ({"height_change": height_change, "weight": mass * gravity}, {"potential_energy_change": mass * gravity * height_change})


def _spring_potential_energy(setup: Mapping[str, object]) -> CalculatorResult:
    spring_constant = _number(setup, "spring_constant")
    displacement = _number(setup, "displacement")
    squared_displacement = displacement**2
    return ({"squared_displacement": squared_displacement, "half_spring_constant": 0.5 * spring_constant}, {"stored_energy": 0.5 * spring_constant * squared_displacement})


def _energy_conservation(setup: Mapping[str, object]) -> CalculatorResult:
    initial_kinetic = _number(setup, "initial_kinetic_energy")
    initial_potential = _number(setup, "initial_potential_energy")
    nonconservative_work = _number(setup, "nonconservative_work")
    final_kinetic = _number(setup, "final_kinetic_energy")
    available_final = initial_kinetic + initial_potential + nonconservative_work
    final_potential = available_final - final_kinetic
    return (
        {"initial_mechanical_energy": initial_kinetic + initial_potential, "energy_after_transfer": available_final},
        {"final_kinetic_energy": final_kinetic, "final_potential_energy": final_potential, "final_mechanical_energy": final_kinetic + final_potential},
    )


def _potential_energy(setup: Mapping[str, object]) -> CalculatorResult:
    spring_constant = _number(setup, "curvature")
    position = _number(setup, "position")
    potential = 0.5 * spring_constant * position**2
    gradient = spring_constant * position
    return ({"potential_value": potential, "potential_gradient": gradient}, {"conservative_force": -gradient})


def _potential_energy_diagram(setup: Mapping[str, object]) -> CalculatorResult:
    curvature = _number(setup, "curvature")
    center = _number(setup, "center")
    floor = _number(setup, "floor_energy")
    total = _number(setup, "total_energy")
    samples = _numbers(setup, "position_samples")
    if curvature <= 0.0 or total < floor:
        raise ValueError("potential well requires positive curvature and total energy above its floor")
    potentials = tuple(curvature * (position - center) ** 2 + floor for position in samples)
    kinetic = tuple(total - potential for potential in potentials)
    offset = math.sqrt((total - floor) / curvature)
    return (
        {"potential_samples": potentials, "kinetic_energy_samples": kinetic},
        {"turning_points": (center - offset, center + offset), "allowed_samples": tuple(value >= 0.0 for value in kinetic)},
    )


def _circular_position(setup: Mapping[str, object]) -> CalculatorResult:
    radius = _number(setup, "radius")
    angular_speed = _number(setup, "angular_speed")
    initial_phase = _number(setup, "initial_phase")
    elapsed = _number(setup, "elapsed_time")
    phase = angular_speed * elapsed + initial_phase
    position = (radius * math.cos(phase), radius * math.sin(phase))
    velocity = (-radius * angular_speed * math.sin(phase), radius * angular_speed * math.cos(phase))
    return ({"phase": phase, "angular_displacement": angular_speed * elapsed}, {"position_vector": position, "velocity_vector": velocity, "radius_check": _magnitude(position)})


def _uniform_circular_motion(setup: Mapping[str, object]) -> CalculatorResult:
    radius = _number(setup, "radius")
    speed = _number(setup, "speed")
    angular_speed = speed / radius
    return ({"circumference": 2.0 * math.pi * radius, "angular_speed": angular_speed}, {"period": 2.0 * math.pi / angular_speed, "tangential_speed": speed})


def _radial_acceleration(setup: Mapping[str, object]) -> CalculatorResult:
    radius = _number(setup, "radius")
    speed = _number(setup, "speed")
    angular_speed = speed / radius
    return ({"angular_speed": angular_speed, "speed_squared": speed**2}, {"radial_acceleration": speed**2 / radius, "direction_is_inward": True})


def _circular_dynamics(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    radius = _number(setup, "radius")
    speed = _number(setup, "speed")
    forces = _numbers(setup, "inward_forces")
    required = mass * speed**2 / radius
    return ({"required_inward_force": required, "provided_inward_force": sum(forces)}, {"radial_acceleration": speed**2 / radius, "force_balance_residual": sum(forces) - required})


def _rigid_body_motion(setup: Mapping[str, object]) -> CalculatorResult:
    reference_velocity = _vector2(setup, "reference_velocity")
    relative_position = _vector2(setup, "relative_position")
    angular_velocity = _number(setup, "angular_velocity")
    rotational_velocity = (-angular_velocity * relative_position[1], angular_velocity * relative_position[0])
    point_velocity = tuple(reference_velocity[i] + rotational_velocity[i] for i in range(2))
    return ({"rotational_velocity": rotational_velocity}, {"material_point_velocity": point_velocity, "body_relative_distance": _magnitude(relative_position)})


def _moment_of_inertia(setup: Mapping[str, object]) -> CalculatorResult:
    masses = _numbers(setup, "mass_elements")
    distances = _numbers(setup, "perpendicular_distances")
    if len(masses) != len(distances):
        raise ValueError("mass_elements and perpendicular_distances must have equal length")
    contributions = tuple(mass * distance**2 for mass, distance in zip(masses, distances))
    return ({"inertia_contributions": contributions}, {"moment_of_inertia": sum(contributions)})


def _torque(setup: Mapping[str, object]) -> CalculatorResult:
    lever = _vector2(setup, "lever_arm_vector")
    force = _vector2(setup, "force_vector")
    torque = lever[0] * force[1] - lever[1] * force[0]
    return ({"cross_product_terms": (lever[0] * force[1], lever[1] * force[0])}, {"torque_z": torque, "rotation_sense": 1.0 if torque >= 0.0 else -1.0})


def _rotational_dynamics(setup: Mapping[str, object]) -> CalculatorResult:
    torques = _numbers(setup, "external_torques")
    inertia = _number(setup, "moment_of_inertia")
    initial_speed = _number(setup, "initial_angular_speed")
    elapsed = _number(setup, "elapsed_time")
    net_torque = sum(torques)
    acceleration = net_torque / inertia
    return ({"net_torque": net_torque, "angular_acceleration": acceleration}, {"final_angular_speed": initial_speed + acceleration * elapsed, "angular_impulse": net_torque * elapsed})


def _point_particle_angular_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    position = _vector2(setup, "particle_position")
    momentum = _vector2(setup, "particle_momentum")
    terms = (position[0] * momentum[1], position[1] * momentum[0])
    return ({"cross_product_terms": terms}, {"angular_momentum_z": terms[0] - terms[1], "point_particle_model": True})


def _rigid_body_angular_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    inertia = _numbers(setup, "inertia_tensor_diagonal")
    angular_velocity = _numbers(setup, "angular_velocity_vector")
    if len(inertia) != 3 or len(angular_velocity) != 3:
        raise ValueError("inertia tensor diagonal and angular velocity must have three components")
    angular_momentum = tuple(inertia[i] * angular_velocity[i] for i in range(3))
    return ({"tensor_vector_products": angular_momentum}, {"angular_momentum_vector": angular_momentum, "rotational_kinetic_energy": 0.5 * _dot(angular_velocity, angular_momentum)})


def _angular_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    positions = setup["component_positions"]
    momenta = setup["component_momenta"]
    if not isinstance(positions, Sequence) or not isinstance(momenta, Sequence) or len(positions) != len(momenta):
        raise ValueError("component positions and momenta must be paired sequences")
    contributions = []
    for position_value, momentum_value in zip(positions, momenta):
        position = _vector2({"value": position_value}, "value")
        momentum = _vector2({"value": momentum_value}, "value")
        contributions.append(position[0] * momentum[1] - position[1] * momentum[0])
    return ({"component_angular_momenta": tuple(contributions)}, {"total_angular_momentum_z": sum(contributions)})


def _angular_impulse(setup: Mapping[str, object]) -> CalculatorResult:
    initial = _number(setup, "initial_angular_momentum")
    torque = _number(setup, "constant_torque")
    elapsed = _number(setup, "time_interval")
    impulse = torque * elapsed
    return ({"angular_impulse": impulse, "angular_momentum_change": impulse}, {"final_angular_momentum": initial + impulse})


def _rolling_dynamics(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    radius = _number(setup, "radius")
    inertia = _number(setup, "moment_of_inertia")
    gravity = _number(setup, "gravity")
    angle = math.radians(_number(setup, "incline_angle_degrees"))
    downhill_gravity = mass * gravity * math.sin(angle)
    center_acceleration = gravity * math.sin(angle) / (1.0 + inertia / (mass * radius**2))
    angular_acceleration = center_acceleration / radius
    friction = mass * center_acceleration - downhill_gravity
    return (
        {"downhill_gravity_component": downhill_gravity, "static_friction": friction, "net_translation_force": mass * center_acceleration},
        {"center_acceleration": center_acceleration, "angular_acceleration": angular_acceleration, "torque_from_friction": -friction * radius, "no_slip_satisfied": True},
    )


def _rolling_kinetic_energy(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    radius = _number(setup, "radius")
    inertia = _number(setup, "moment_of_inertia")
    angular_speed = _number(setup, "angular_speed")
    center_speed = angular_speed * radius
    translational = 0.5 * mass * center_speed**2
    rotational = 0.5 * inertia * angular_speed**2
    return ({"center_speed": center_speed, "translational_energy": translational, "rotational_energy": rotational}, {"total_kinetic_energy": translational + rotational, "no_slip_satisfied": True})


def _rolling_angular_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    radius = _number(setup, "radius")
    inertia = _number(setup, "moment_of_inertia")
    angular_speed = _number(setup, "angular_speed")
    center_speed = angular_speed * radius
    spin = inertia * angular_speed
    orbital_about_contact = mass * radius * center_speed
    return (
        {"center_speed": center_speed, "spin_angular_momentum": spin, "orbital_angular_momentum_about_contact": orbital_about_contact},
        {"angular_momentum_about_contact": spin + orbital_about_contact, "parallel_axis_inertia": inertia + mass * radius**2},
    )


def _rolling_energy_angular_momentum(setup: Mapping[str, object]) -> CalculatorResult:
    mass = _number(setup, "mass")
    radius = _number(setup, "radius")
    inertia = _number(setup, "moment_of_inertia")
    center_speed = _number(setup, "center_speed")
    angular_speed = _number(setup, "angular_speed")
    if mass <= 0.0 or radius <= 0.0 or inertia <= 0.0:
        raise ValueError("mass, radius, and moment_of_inertia must be positive")
    no_slip_residual = center_speed - angular_speed * radius
    if not math.isclose(no_slip_residual, 0.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("center_speed and angular_speed violate the no-slip constraint")
    translational = 0.5 * mass * center_speed**2
    rotational = 0.5 * inertia * angular_speed**2
    return (
        {
            "translational_energy": translational,
            "rotational_energy": rotational,
            "no_slip_residual": no_slip_residual,
        },
        {
            "total_kinetic_energy": translational + rotational,
            "angular_momentum_cm": inertia * angular_speed,
            "no_slip_satisfied": True,
            "both_mechanisms_visible": True,
        },
    )


def _continuous_mass_accumulation(setup: Mapping[str, object]) -> CalculatorResult:
    initial_mass = _number(setup, "initial_mass")
    inlet = _number(setup, "inlet_mass_flow")
    outlet = _number(setup, "outlet_mass_flow")
    duration = _number(setup, "duration")
    if initial_mass < 0.0 or inlet < 0.0 or outlet < 0.0 or duration < 0.0:
        raise ValueError("mass, flow rates, and duration must be nonnegative")
    net_rate = inlet - outlet
    mass_change = net_rate * duration
    final_mass = initial_mass + mass_change
    if final_mass < 0.0:
        raise ValueError("outflow would make stored mass negative")
    return (
        {"net_mass_flow": net_rate, "mass_change": mass_change},
        {"initial_mass": initial_mass, "final_mass": final_mass, "fixed_control_volume": True},
    )


def _continuous_mass_transfer(setup: Mapping[str, object]) -> CalculatorResult:
    rate = _number(setup, "mass_flow_rate")
    incoming = _number(setup, "inlet_velocity")
    outgoing = _number(setup, "outlet_velocity")
    duration = _number(setup, "duration")
    flux_in = rate * incoming
    flux_out = rate * outgoing
    return (
        {"momentum_rate_in": flux_in, "momentum_rate_out": flux_out, "mass_processed": rate * duration},
        {"external_force": flux_out - flux_in, "mass_flow_is_continuous": True},
    )


def _rocket_equation(setup: Mapping[str, object]) -> CalculatorResult:
    initial_mass = _number(setup, "initial_mass")
    final_mass = _number(setup, "final_mass")
    exhaust_speed = _number(setup, "exhaust_speed")
    if initial_mass <= final_mass or final_mass <= 0.0:
        raise ValueError("rocket masses must satisfy initial_mass > final_mass > 0")
    ratio = initial_mass / final_mass
    logarithm = math.log(ratio)
    return ({"mass_ratio": ratio, "log_mass_ratio": logarithm, "propellant_mass": initial_mass - final_mass}, {"delta_velocity": exhaust_speed * logarithm, "vehicle_mass_decreases": True})


def _center_of_mass(setup: Mapping[str, object]) -> CalculatorResult:
    masses = _numbers(setup, "component_masses")
    positions = _numbers(setup, "component_positions")
    if len(masses) != len(positions):
        raise ValueError("component masses and positions must have equal length")
    weighted_positions = tuple(mass * position for mass, position in zip(masses, positions))
    total_mass = sum(masses)
    center = sum(weighted_positions) / total_mass
    balance_residual = sum(mass * (position - center) for mass, position in zip(masses, positions))
    return ({"weighted_positions": weighted_positions, "total_mass": total_mass}, {"center_position": center, "balance_residual": balance_residual})


def _recoil(setup: Mapping[str, object]) -> CalculatorResult:
    mass_1 = _number(setup, "mass_1")
    mass_2 = _number(setup, "mass_2")
    initial_total = _number(setup, "initial_total_momentum")
    velocity_2 = _number(setup, "final_velocity_2")
    velocity_1 = (initial_total - mass_2 * velocity_2) / mass_1
    return ({"body_2_momentum": mass_2 * velocity_2, "body_1_momentum": mass_1 * velocity_1}, {"final_velocity_1": velocity_1, "final_velocity_2": velocity_2, "final_total_momentum": mass_1 * velocity_1 + mass_2 * velocity_2})


def _relative_velocity(setup: Mapping[str, object]) -> CalculatorResult:
    velocity_a = _vector2(setup, "object_a_velocity")
    velocity_b = _vector2(setup, "object_b_velocity")
    relative = tuple(velocity_a[i] - velocity_b[i] for i in range(2))
    return ({"component_differences": relative}, {"relative_velocity_vector": relative, "relative_speed": _magnitude(relative)})


def _ordinary_differential_equation(setup: Mapping[str, object]) -> CalculatorResult:
    initial = _number(setup, "initial_condition")
    decay = _number(setup, "decay_rate")
    elapsed = _number(setup, "evaluation_time")
    exponential_factor = math.exp(-decay * elapsed)
    final = initial * exponential_factor
    return ({"exponential_factor": exponential_factor, "elapsed_decay": decay * elapsed}, {"state_at_evaluation_time": final, "rate_at_evaluation_time": -decay * final})


def _unit_vector(setup: Mapping[str, object]) -> CalculatorResult:
    components = _vector2(setup, "vector_components")
    magnitude = _magnitude(components)
    if math.isclose(magnitude, 0.0):
        raise ValueError("vector_components must be nonzero")
    normalized = tuple(component / magnitude for component in components)
    return ({"vector_magnitude": magnitude}, {"normalized_components": normalized, "normalized_magnitude": _magnitude(normalized)})


def _vectors(setup: Mapping[str, object]) -> CalculatorResult:
    components = _vector2(setup, "vector_components")
    magnitude = _magnitude(components)
    if math.isclose(magnitude, 0.0):
        raise ValueError("vector_components must be nonzero")
    direction = math.degrees(math.atan2(components[1], components[0]))
    normalized = tuple(component / magnitude for component in components)
    return (
        {"squared_components": tuple(component**2 for component in components), "magnitude": magnitude},
        {
            "magnitude": magnitude,
            "direction_degrees": direction,
            "normalized_components": normalized,
            "normalized_magnitude": _magnitude(normalized),
        },
    )


def _waves(setup: Mapping[str, object]) -> CalculatorResult:
    amplitude = _number(setup, "amplitude")
    wavelength = _number(setup, "wavelength")
    frequency = _number(setup, "frequency")
    phase = _number(setup, "phase")
    position = _number(setup, "position")
    elapsed = _number(setup, "time")
    wave_number = 2.0 * math.pi / wavelength
    angular_frequency = 2.0 * math.pi * frequency
    displacement = amplitude * math.sin(wave_number * position - angular_frequency * elapsed + phase)
    return (
        {"wave_number": wave_number, "angular_frequency": angular_frequency, "phase_argument": wave_number * position - angular_frequency * elapsed + phase},
        {"wave_speed": wavelength * frequency, "period": 1.0 / frequency, "displacement": displacement},
    )


def _definition(
    model_id: str,
    calculator: Calculator,
    setup: Mapping[str, object],
    state_ids: Tuple[str, str, str],
    distinguishing_tokens: Tuple[str, ...] = (),
) -> Tuple[str, PhysicsScenarioDefinition]:
    return (
        model_id,
        PhysicsScenarioDefinition(
            mode=model_id,
            setup=FrozenFields.from_mapping(setup),
            calculator=calculator,
            state_ids=state_ids,
            distinguishing_tokens=distinguishing_tokens,
        ),
    )


_SCENARIO_DEFINITION_ROWS: Final[Tuple[Tuple[str, PhysicsScenarioDefinition], ...]] = (
    _definition(
        "kinematics_1d",
        _kinematics_1d,
        {"initial_position": 1.0, "initial_velocity": 3.0, "acceleration": 2.0, "elapsed_time": 2.0},
        ("place_on_number_line", "advance_axis_clock", "read_scalar_position_velocity"),
        ("one-dimensional signed axis", "scalar x position"),
    ),
    _definition(
        "kinematics_2d",
        _kinematics_2d,
        {"initial_position_vector": (1.0, 2.0), "initial_velocity_vector": (3.0, 4.0), "acceleration_vector": (2.0, -2.0), "elapsed_time": 2.0},
        ("place_planar_vectors", "trace_two_component_path", "read_vector_position_velocity"),
        ("two-dimensional vector components", "planar trajectory"),
    ),
    _definition(
        "projectile_motion",
        _projectile_motion,
        {"launch_position": (0.0, 1.0), "initial_speed": 10.0, "launch_angle": 30.0, "gravity": 9.8, "elapsed_time": 1.0},
        ("launch_at_angle", "trace_gravity_parabola", "read_projectile_coordinates"),
        ("horizontal velocity constant", "vertical gravity acceleration", "projectile arc"),
    ),
    _definition(
        "rolling_kinematics",
        _rolling_kinematics,
        {"radius": 0.5, "angular_speed": 6.0, "angular_acceleration": 2.0, "elapsed_time": 1.5},
        ("mark_zero_speed_contact", "roll_without_slip", "compare_translation_rotation"),
        ("v_cm equals omega R", "a_cm equals alpha R", "contact point instantaneously at rest"),
    ),
    _definition(
        "force_balance",
        _force_balance,
        {"mass": 4.0, "external_forces": (12.0, -4.0)},
        ("draw_system_boundary", "sum_external_force_arrows", "show_net_force_acceleration"),
        ("chosen system", "vector sum of external forces"),
    ),
    _definition(
        "newton_first_law",
        _newton_first_law,
        {"mass": 2.0, "external_forces": (5.0, -5.0), "initial_velocity": 3.0, "time_interval": 4.0},
        ("show_balanced_forces", "advance_in_inertial_frame", "confirm_constant_velocity"),
        ("zero net external force", "unchanged velocity"),
    ),
    _definition(
        "newton_second_law",
        _newton_second_law,
        {"mass": 3.0, "external_forces": (15.0, -3.0), "initial_velocity": 1.0, "time_interval": 2.0},
        ("draw_free_body_diagram", "sum_force_and_change_momentum", "show_mass_acceleration"),
        ("net external force", "dp per dt", "constant mass acceleration"),
    ),
    _definition(
        "newton_laws",
        _newton_laws,
        {"initial_momentum": 4.0, "final_momentum": 10.0, "time_interval": 2.0},
        ("choose_inertial_system", "track_momentum_change", "read_average_external_force"),
        ("inertial frame momentum law", "system momentum change"),
    ),
    _definition(
        "action_reaction",
        _action_reaction,
        {"masses": (2.0, 4.0), "interaction_force": 8.0},
        ("separate_two_bodies", "draw_reciprocal_force_pair", "compare_equal_opposite_forces"),
        ("same interaction", "equal and opposite", "forces act on different bodies"),
    ),
    _definition(
        "gravity_force",
        _gravity_force,
        {"mass": 3.0, "gravitational_field": (0.0, -9.8)},
        ("place_body_in_field", "multiply_mass_by_field", "show_weight_vector"),
        ("gravitational field interaction", "weight points with field"),
    ),
    _definition(
        "contact_force",
        _contact_force,
        {"normal_force": 20.0, "friction_force": -6.0},
        ("mark_surface_contact", "resolve_normal_and_friction", "show_total_contact_force"),
        ("surface interaction", "normal plus tangential friction"),
    ),
    _definition(
        "tension_force",
        _tension_force,
        {"tension_magnitude": 12.0, "rope_direction": (3.0, 4.0)},
        ("mark_rope_attachment", "normalize_rope_direction", "draw_tension_along_rope"),
        ("rope interaction", "tension pulls away along rope"),
    ),
    _definition(
        "spring_force",
        _spring_force,
        {"spring_constant": 50.0, "equilibrium_position": 0.0, "displacement": 0.2},
        ("mark_spring_equilibrium", "displace_spring_end", "draw_opposing_restoring_force"),
        ("elastic interaction", "restoring force opposite displacement"),
    ),
    _definition(
        "pulley_constraint",
        _pulley_constraint,
        {"mass_1": 2.0, "mass_2": 3.0, "gravity": 9.8, "string_length": 4.0},
        ("show_continuous_rope", "move_linked_masses", "compare_opposite_accelerations"),
        ("fixed string length", "equal acceleration magnitudes"),
    ),
    _definition(
        "linear_drag",
        _linear_drag,
        {"drag_coefficient": 1.5, "relative_velocity": (4.0, 0.0)},
        ("show_relative_velocity", "scale_force_linearly", "draw_opposing_linear_drag"),
        ("drag proportional to speed", "linear constitutive law"),
    ),
    _definition(
        "quadratic_drag",
        _quadratic_drag,
        {"fluid_density": 1.2, "drag_coefficient": 0.5, "reference_area": 0.8, "relative_velocity": (10.0, 0.0)},
        ("show_area_and_flow", "square_relative_speed", "draw_opposing_quadratic_drag"),
        ("drag proportional to speed squared", "density coefficient area"),
    ),
    _definition(
        "drag_force",
        _drag_force,
        {"base_drag": 2.0, "quadratic_coefficient": 0.1, "relative_velocity": (6.0, 8.0)},
        ("show_fluid_relative_motion", "evaluate_speed_dependent_law", "draw_antiparallel_drag"),
        ("generic nonnegative drag magnitude", "force antiparallel to velocity"),
    ),
    _definition(
        "momentum_definition",
        _momentum_definition,
        {"mass": 2.5, "velocity": (3.0, 4.0)},
        ("show_mass_and_velocity", "multiply_vector_by_mass", "show_momentum_vector"),
        ("linear momentum equals mass times velocity",),
    ),
    _definition(
        "impulse_momentum",
        _impulse_momentum,
        {"initial_momentum": 4.0, "force_samples": (2.0, 6.0, 4.0), "sample_interval": 1.0},
        ("plot_force_history", "accumulate_force_time_area", "shift_momentum_by_impulse"),
        ("force time area", "impulse equals momentum change"),
    ),
    _definition(
        "momentum_conservation",
        _momentum_conservation,
        {"masses": (2.0, 3.0), "initial_velocities": (4.0, -1.0), "external_impulse": 0.0, "final_velocity_1": -1.0},
        ("show_isolated_before_state", "redistribute_body_momenta", "match_total_after_momentum"),
        ("zero external impulse", "same total momentum before and after"),
    ),
    _definition(
        "elastic_collision",
        _elastic_collision,
        {"masses": (2.0, 3.0), "initial_velocities": (4.0, -1.0)},
        ("approach_before_collision", "exchange_impulse", "separate_with_equal_total_kinetic_energy"),
        ("coefficient of restitution 1", "bodies separated after", "kinetic energy unchanged"),
    ),
    _definition(
        "inelastic_collision",
        _inelastic_collision,
        {"masses": (2.0, 3.0), "initial_velocities": (4.0, -1.0), "coefficient_of_restitution": 0.4},
        ("approach_before_collision", "deform_and_transfer_energy", "separate_with_kinetic_energy_loss"),
        ("restitution between 0 and 1", "bodies separated after", "positive kinetic energy loss"),
    ),
    _definition(
        "perfectly_inelastic_collision",
        _perfectly_inelastic_collision,
        {"masses": (2.0, 3.0), "initial_velocities": (4.0, -1.0)},
        ("approach_before_collision", "stick_at_impact", "move_as_one_shared_mass"),
        ("coefficient of restitution 0", "bodies stuck after", "one shared final velocity"),
    ),
    _definition(
        "collision_momentum",
        _collision_momentum,
        {"masses": (2.0, 3.0), "initial_velocities": (3.0, 1.0), "external_impulse": -2.0, "final_velocity_1": 0.5},
        ("show_preimpact_momentum", "apply_collision_and_external_impulse", "show_postimpact_momentum"),
        ("external impulse changes system momentum",),
    ),
    _definition(
        "work_definition",
        _work_definition,
        {"force_vector": (6.0, 8.0), "displacement_vector": (3.0, 0.0)},
        ("draw_force_on_path", "project_force_along_displacement", "accumulate_dot_product_work"),
        ("force displacement dot product", "path work"),
    ),
    _definition(
        "work_energy_theorem",
        _work_energy_theorem,
        {"mass": 2.0, "initial_speed": 2.0, "net_force": 5.0, "distance": 3.0},
        ("show_initial_motion", "transfer_net_work", "show_final_kinetic_energy"),
        ("net work equals kinetic energy change",),
    ),
    _definition(
        "gravitational_potential_energy",
        _gravitational_potential_energy,
        {"mass": 2.0, "gravity": 9.8, "initial_height": 1.0, "final_height": 4.0, "reference_level": 0.0},
        ("mark_reference_height", "raise_mass_against_gravity", "show_gravitational_energy_change"),
        ("near Earth height change", "reference level"),
    ),
    _definition(
        "spring_potential_energy",
        _spring_potential_energy,
        {"spring_constant": 80.0, "equilibrium_position": 0.0, "displacement": 0.3},
        ("mark_unstretched_spring", "compress_from_equilibrium", "show_stored_elastic_energy"),
        ("elastic energy proportional to displacement squared",),
    ),
    _definition(
        "energy_conservation",
        _energy_conservation,
        {"initial_kinetic_energy": 4.0, "initial_potential_energy": 16.0, "nonconservative_work": -2.0, "final_kinetic_energy": 10.0},
        ("show_initial_energy_bars", "apply_nonconservative_transfer", "balance_final_energy_bars"),
        ("system energy accounting", "nonconservative transfer included"),
    ),
    _definition(
        "potential_energy",
        _potential_energy,
        {"curvature": 6.0, "position": 2.0},
        ("plot_potential_function", "measure_local_gradient", "draw_force_down_gradient"),
        ("conservative force is negative gradient",),
    ),
    _definition(
        "potential_energy_diagram",
        _potential_energy_diagram,
        {"curvature": 1.0, "center": 0.0, "floor_energy": 1.0, "total_energy": 10.0, "position_samples": (-4.0, -2.0, 0.0, 2.0, 4.0)},
        ("draw_potential_and_total_energy", "shade_classically_allowed_region", "mark_zero_kinetic_turning_points"),
        ("K equals E minus U", "turning points where U equals E"),
    ),
    _definition(
        "circular_position",
        _circular_position,
        {"radius": 3.0, "angular_speed": 2.0, "initial_phase": 0.0, "elapsed_time": 0.5},
        ("place_radius_vector", "advance_angular_phase", "read_planar_position"),
        ("position remains on circle", "phase sets coordinates"),
    ),
    _definition(
        "uniform_circular_motion",
        _uniform_circular_motion,
        {"radius": 2.0, "speed": 6.0},
        ("place_body_on_circle", "move_at_constant_tangential_speed", "complete_one_period"),
        ("constant speed changing direction", "period from angular speed"),
    ),
    _definition(
        "radial_acceleration",
        _radial_acceleration,
        {"radius": 2.0, "speed": 6.0},
        ("show_tangent_velocity", "compare_velocity_directions", "draw_inward_acceleration"),
        ("v squared over R", "acceleration points inward"),
    ),
    _definition(
        "circular_dynamics",
        _circular_dynamics,
        {"mass": 4.0, "radius": 2.0, "speed": 6.0, "inward_forces": (80.0, -8.0)},
        ("draw_radial_free_body_diagram", "sum_inward_forces", "match_required_centripetal_force"),
        ("net inward force", "m v squared over R"),
    ),
    _definition(
        "rigid_body_motion",
        _rigid_body_motion,
        {"reference_velocity": (1.0, 2.0), "angular_velocity": 3.0, "relative_position": (2.0, 1.0)},
        ("mark_two_material_points", "translate_and_rotate_rigid_body", "add_reference_and_rotational_velocity"),
        ("fixed body-relative separation", "translation plus omega cross r"),
    ),
    _definition(
        "moment_of_inertia",
        _moment_of_inertia,
        {"mass_elements": (2.0, 3.0, 1.0), "perpendicular_distances": (1.0, 2.0, 3.0)},
        ("mark_rotation_axis", "weight_mass_elements_by_radius_squared", "sum_rotational_inertia"),
        ("mass distribution about chosen axis", "sum m r squared"),
    ),
    _definition(
        "torque",
        _torque,
        {"lever_arm_vector": (2.0, 0.0), "force_vector": (3.0, 4.0)},
        ("mark_pivot_and_application_point", "draw_lever_and_force", "show_cross_product_turning_effect"),
        ("r cross F", "signed turning tendency"),
    ),
    _definition(
        "rotational_dynamics",
        _rotational_dynamics,
        {"external_torques": (12.0, -2.0), "moment_of_inertia": 5.0, "initial_angular_speed": 1.0, "elapsed_time": 3.0},
        ("draw_external_torques", "sum_torque_and_accelerate", "read_final_angular_speed"),
        ("net torque divided by moment of inertia", "angular acceleration response"),
    ),
    _definition(
        "point_particle_angular_momentum",
        _point_particle_angular_momentum,
        {"particle_position": (2.0, 1.0), "particle_momentum": (3.0, 4.0)},
        ("mark_origin_and_point_particle", "draw_r_and_particle_momentum", "show_r_cross_p_direction"),
        ("single point particle", "r cross p", "no inertia tensor"),
    ),
    _definition(
        "rigid_body_angular_momentum",
        _rigid_body_angular_momentum,
        {"inertia_tensor_diagonal": (2.0, 3.0, 4.0), "angular_velocity_vector": (1.0, 2.0, 3.0)},
        ("show_extended_rigid_body", "apply_inertia_tensor_to_angular_velocity", "show_rigid_angular_momentum"),
        ("extended rigid body", "L equals inertia tensor times omega", "not r cross p for one particle"),
    ),
    _definition(
        "angular_momentum",
        _angular_momentum,
        {"component_positions": ((1.0, 0.0), (0.0, 2.0)), "component_momenta": ((0.0, 3.0), (-4.0, 0.0))},
        ("mark_system_origin", "sum_component_r_cross_p", "show_total_system_angular_momentum"),
        ("multi-particle system sum",),
    ),
    _definition(
        "angular_impulse",
        _angular_impulse,
        {"initial_angular_momentum": 2.0, "constant_torque": 6.0, "time_interval": 3.0},
        ("plot_torque_history", "accumulate_torque_time_area", "shift_angular_momentum"),
        ("torque time area", "angular momentum change"),
    ),
    _definition(
        "rolling_dynamics",
        _rolling_dynamics,
        {"mass": 3.0, "radius": 0.5, "moment_of_inertia": 0.375, "gravity": 9.8, "incline_angle_degrees": 30.0},
        ("draw_incline_free_body_diagram", "apply_static_friction_torque", "accelerate_translation_and_rotation"),
        ("rolling force balance", "static friction torque", "a_cm equals alpha R"),
    ),
    _definition(
        "rolling_kinetic_energy",
        _rolling_kinetic_energy,
        {"mass": 2.0, "radius": 0.5, "moment_of_inertia": 0.25, "angular_speed": 8.0},
        ("show_rolling_speed_constraint", "fill_translation_and_rotation_energy_meters", "sum_rolling_kinetic_energy"),
        ("one half m v_cm squared", "one half I omega squared", "energy has two parts"),
    ),
    _definition(
        "rolling_angular_momentum",
        _rolling_angular_momentum,
        {"mass": 2.0, "radius": 0.5, "moment_of_inertia": 0.25, "angular_speed": 8.0},
        ("mark_contact_reference_point", "add_spin_and_orbital_parts", "show_angular_momentum_about_contact"),
        ("reference point at contact", "spin plus center orbital angular momentum", "parallel axis inertia"),
    ),
    _definition(
        "continuous_mass_transfer",
        _continuous_mass_transfer,
        {"mass_flow_rate": 2.5, "inlet_velocity": 3.0, "outlet_velocity": 9.0, "duration": 2.0},
        ("draw_fixed_control_volume", "stream_mass_through_inlet_and_outlet", "compare_momentum_flux_rates"),
        ("steady control volume", "continuous inlet and outlet", "force from momentum flux difference", "no logarithm"),
    ),
    _definition(
        "rocket_equation",
        _rocket_equation,
        {"initial_mass": 500.0, "final_mass": 300.0, "exhaust_speed": 2000.0},
        ("show_initial_vehicle_mass", "expel_exhaust_as_vehicle_mass_falls", "read_logarithmic_delta_velocity"),
        ("variable vehicle mass", "exhaust relative to rocket", "delta velocity uses log mass ratio", "no fixed control volume"),
    ),
    _definition(
        "center_of_mass",
        _center_of_mass,
        {"component_masses": (2.0, 3.0), "component_positions": (1.0, 6.0)},
        ("place_component_masses", "accumulate_weighted_positions", "mark_balance_center"),
        ("mass-weighted average position", "zero first moment about center"),
    ),
    _definition(
        "recoil",
        _recoil,
        {"mass_1": 4.0, "mass_2": 1.0, "initial_total_momentum": 0.0, "final_velocity_2": 8.0},
        ("show_joint_rest_state", "separate_bodies_oppositely", "match_opposite_final_momenta"),
        ("isolated separation", "opposite recoil momentum"),
    ),
    _definition(
        "relative_velocity",
        _relative_velocity,
        {"object_a_velocity": (5.0, 2.0), "object_b_velocity": (1.0, -1.0)},
        ("show_common_reference_frame", "draw_two_velocity_vectors", "subtract_to_relative_velocity"),
        ("velocity of A minus velocity of B", "same reference frame"),
    ),
    _definition(
        "ordinary_differential_equation",
        _ordinary_differential_equation,
        {"initial_time": 0.0, "initial_condition": 8.0, "decay_rate": 0.5, "evaluation_time": 4.0},
        ("mark_initial_condition", "evolve_under_rate_law", "read_state_and_slope"),
        ("state trajectory from initial value", "rate equals negative decay times state"),
    ),
    _definition(
        "unit_vector",
        _unit_vector,
        {"vector_components": (3.0, 4.0)},
        ("draw_source_vector", "divide_components_by_magnitude", "show_unit_length_vector"),
        ("same direction", "magnitude exactly one"),
    ),
    _definition(
        "vectors",
        _vectors,
        {"vector_components": (5.0, 12.0)},
        ("draw_coordinate_basis", "resolve_component_arrows", "show_magnitude_and_direction"),
        ("component reconstruction", "direction angle"),
    ),
    _definition(
        "waves",
        _waves,
        {"amplitude": 2.0, "wavelength": 4.0, "frequency": 1.5, "phase": 0.25, "position": 1.0, "time": 0.5},
        ("draw_initial_wave_profile", "propagate_phase", "read_displacement_speed_period"),
        ("traveling sinusoidal profile", "speed equals wavelength times frequency"),
    ),
    _definition(
        "kinematics_position_velocity",
        _kinematics_position_velocity,
        {"initial_position": 0.0, "initial_velocity": 4.0, "acceleration": 1.0, "elapsed_time": 4.0},
        ("pv_place_particle_and_graphs", "pv_advance_shared_clock", "pv_read_position_velocity"),
        ("same particle", "position and velocity graphs", "shared clock"),
    ),
    _definition(
        "kinematics_acceleration",
        _kinematics_acceleration,
        {"initial_position": 0.0, "initial_velocity": 2.0, "acceleration": 2.0, "elapsed_time": 5.0},
        ("acc_place_initial_velocity", "acc_accumulate_velocity_change", "acc_read_slope_and_state"),
        ("acceleration is velocity slope", "velocity change", "position consequence"),
    ),
    _definition(
        "newton_laws_of_motion",
        _newton_laws_of_motion,
        {"masses": (2.0, 3.0), "interaction_force": 6.0},
        ("laws_separate_interacting_bodies", "laws_draw_reciprocal_pair", "laws_compare_accelerations"),
        ("equal and opposite forces", "different bodies", "mass dependent acceleration"),
    ),
    _definition(
        "tension_and_springs",
        _tension_and_springs,
        {"mass": 1.0, "tension_force": 7.0, "spring_constant": 20.0, "displacement": 0.2},
        ("ts_show_rope_and_spring", "ts_resolve_both_forces", "ts_accelerate_same_body"),
        ("tension along rope", "spring restoring force", "both mechanisms"),
    ),
    _definition(
        "massive_rope",
        _massive_rope,
        {"rope_mass": 5.0, "rope_length": 2.0, "trailing_tension": 2.0, "leading_tension": 12.0},
        ("mr_segment_massive_rope", "mr_show_tension_gradient", "mr_match_distributed_acceleration"),
        ("nonuniform tension", "linear mass density", "tension gradient"),
    ),
    _definition(
        "continuous_mass_accumulation",
        _continuous_mass_accumulation,
        {"initial_mass": 10.0, "inlet_mass_flow": 4.0, "outlet_mass_flow": 1.0, "duration": 4.0},
        ("cma_fix_control_volume", "cma_cross_inlet_and_outlet", "cma_update_stored_mass"),
        ("fixed control volume", "inlet minus outlet", "stored mass accumulation"),
    ),
    _definition(
        "work_energy_1d",
        _work_energy_1d,
        {"mass": 3.0, "initial_speed": 2.0, "force": 7.0, "distance": 6.0},
        ("we1_show_signed_path", "we1_accumulate_force_distance_work", "we1_update_kinetic_energy"),
        ("one dimensional signed work", "kinetic energy change"),
    ),
    _definition(
        "work_energy_multidimensional",
        _work_energy_multidimensional,
        {"mass": 2.0, "initial_speed": 5.0, "force_vector": (6.0, 8.0), "displacement_vector": (3.0, 4.0)},
        ("wend_draw_force_and_displacement", "wend_project_dot_product", "wend_update_kinetic_energy"),
        ("force displacement dot product", "only parallel component works"),
    ),
    _definition(
        "conservative_nonconservative_forces",
        _conservative_nonconservative_forces,
        {"conservative_force": 14.0, "nonconservative_force": -1.0, "displacement": 1.0},
        ("cnc_identify_force_classes", "cnc_route_work_to_energy", "cnc_compare_mechanical_change"),
        ("conservative work changes potential", "nonconservative work changes mechanical energy"),
    ),
    _definition(
        "potential_energy_configuration",
        _potential_energy_configuration,
        {"mass": 2.0, "spring_constant": 80.0, "displacement": 0.3, "reference_position": 0.0},
        ("pec_mark_reference_configuration", "pec_store_spring_energy", "pec_release_to_kinetic_energy"),
        ("configuration energy", "stated zero reference", "release conversion"),
    ),
    _definition(
        "collision_classification",
        _collision_classification,
        {"masses": (1.0, 1.0), "initial_velocities": (4.0, 0.0), "final_velocities": (2.0, 2.0)},
        ("cc_show_exact_before_state", "cc_check_momentum_and_energy", "cc_label_sticking_collision"),
        ("momentum before and after", "kinetic energy comparison", "sticking classification"),
    ),
    _definition(
        "rolling_energy_angular_momentum",
        _rolling_energy_angular_momentum,
        {"mass": 2.0, "radius": 0.5, "moment_of_inertia": 0.25, "center_speed": 3.0, "angular_speed": 6.0},
        ("ream_show_no_slip_rolling_state", "ream_split_translation_and_rotation_energy", "ream_show_energy_and_angular_momentum"),
        ("translation plus rotation energy", "center angular momentum", "both mechanisms"),
    ),
)


if len({model_id for model_id, _ in _SCENARIO_DEFINITION_ROWS}) != len(_SCENARIO_DEFINITION_ROWS):
    raise RuntimeError("physics scenario definitions contain duplicate model ids")


PHYSICS_MODEL_SCENARIO_DEFINITIONS: Final[Mapping[str, PhysicsScenarioDefinition]] = MappingProxyType(
    dict(_SCENARIO_DEFINITION_ROWS)
)


_model_ids = frozenset(PHYSICS_MODEL_REGISTRY)
_scenario_ids = frozenset(PHYSICS_MODEL_SCENARIO_DEFINITIONS)
if _model_ids != _scenario_ids:
    missing = sorted(_model_ids - _scenario_ids)
    extra = sorted(_scenario_ids - _model_ids)
    raise RuntimeError(f"physics scenario coverage mismatch: missing={missing}, extra={extra}")


_modes = tuple(definition.mode for definition in PHYSICS_MODEL_SCENARIO_DEFINITIONS.values())
if len(set(_modes)) != len(_modes):
    raise RuntimeError("every physics scenario must have a distinct mode")


def _unique_tokens(tokens: Sequence[str]) -> Tuple[str, ...]:
    ordered = []
    seen = set()
    for token in tokens:
        if not isinstance(token, str) or not token:
            raise ValueError("visible evidence tokens must be nonempty strings")
        if token not in seen:
            ordered.append(token)
            seen.add(token)
    return tuple(ordered)


def _contains_finite_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return any(_contains_finite_number(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_finite_number(item) for item in value)
    return False


def _assert_finite_values(fields: Mapping[str, object], label: str) -> None:
    def visit(value: object) -> None:
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise ValueError(f"{label} contains a non-finite number")
            return
        if isinstance(value, Mapping):
            for item in value.values():
                visit(item)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                visit(item)
            return
        raise TypeError(f"{label} contains unsupported value {value!r}")

    for field_value in fields.values():
        visit(field_value)


def build_physics_model_scenario(
    model_id: str,
    setup_overrides: Optional[Mapping[str, object]] = None,
) -> PhysicsModelScenario:
    """Build one scenario and recompute all displayed fields from its setup."""

    if not isinstance(model_id, str):
        raise TypeError("model_id must be a string")
    try:
        definition = PHYSICS_MODEL_SCENARIO_DEFINITIONS[model_id]
    except KeyError as error:
        raise ValueError(f"Unsupported physics model {model_id!r}") from error
    if setup_overrides is not None and not isinstance(setup_overrides, Mapping):
        raise TypeError("setup_overrides must be a mapping")

    setup_values = dict(definition.setup.items())
    if setup_overrides:
        unknown = sorted(set(setup_overrides) - set(setup_values))
        if unknown:
            raise ValueError(f"unknown setup fields for {model_id}: {unknown}")
        setup_values.update(setup_overrides)
    setup = FrozenFields.from_mapping(setup_values)
    _assert_finite_values(setup, "setup")
    if not _contains_finite_number(setup):
        raise ValueError(f"physics scenario {model_id!r} requires a concrete numeric setup")

    calculation_values, result_values = definition.calculator(setup)
    calculation = FrozenFields.from_mapping(calculation_values)
    result = FrozenFields.from_mapping(result_values)
    if not calculation or not result:
        raise ValueError(f"physics scenario {model_id!r} requires calculation and result fields")
    _assert_finite_values(calculation, "calculation")
    _assert_finite_values(result, "result")
    if not _contains_finite_number(calculation) or not _contains_finite_number(result):
        raise ValueError(f"physics scenario {model_id!r} must compute numeric evidence")

    spec = PHYSICS_MODEL_REGISTRY[model_id]
    example_tokens = tuple(spec.required_example_tokens)
    figure_tokens = tuple(spec.required_figure_tokens)
    evidence_tokens = _unique_tokens(example_tokens + figure_tokens)
    state_tokens = (
        _unique_tokens(example_tokens[:1]),
        _unique_tokens(example_tokens),
        evidence_tokens,
    )
    state_values = (setup, calculation, result)
    figure_midpoint = max(1, (len(figure_tokens) + 1) // 2)
    state_object_ids = (figure_tokens[:1], figure_tokens[:figure_midpoint], figure_tokens)
    state_result_fields = ((), tuple(calculation), tuple(result))
    phases = ("setup", "change", "result")
    animation_states = tuple(
        AnimationState(
            state_id=state_id,
            phase=phases[index],
            progress=index / 2.0,
            values=state_values[index],
            visible_tokens=state_tokens[index],
            visible_object_ids=state_object_ids[index],
            result_fields=state_result_fields[index],
        )
        for index, state_id in enumerate(definition.state_ids)
    )
    return PhysicsModelScenario(
        model_id=model_id,
        mode=definition.mode,
        setup=setup,
        calculation=calculation,
        result=result,
        animation_states=animation_states,
        required_example_tokens=example_tokens,
        required_figure_tokens=figure_tokens,
        visible_evidence_tokens=evidence_tokens,
    )


def recompute_physics_model_scenario(
    scenario_or_model_id: Union[str, PhysicsModelScenario, Mapping[str, object]],
    setup: Optional[Mapping[str, object]] = None,
) -> PhysicsModelScenario:
    """Rebuild from setup, intentionally ignoring supplied calculation/results."""

    if isinstance(scenario_or_model_id, str):
        return build_physics_model_scenario(scenario_or_model_id, setup)
    if setup is not None:
        raise ValueError("setup is only accepted when recomputing by model_id")
    if not isinstance(scenario_or_model_id, Mapping):
        raise TypeError("scenario_or_model_id must be a model id or scenario mapping")
    try:
        model_id = scenario_or_model_id["model_id"]
        source_setup = scenario_or_model_id["setup"]
    except KeyError as error:
        raise ValueError("scenario mapping must contain model_id and setup") from error
    if not isinstance(model_id, str):
        raise TypeError("scenario model_id must be a string")
    if not isinstance(source_setup, Mapping):
        raise TypeError("scenario setup must be a mapping")
    return build_physics_model_scenario(model_id, source_setup)


_MIT_8_01_SETUP_OVERRIDES_BY_MODEL_ID: Final[Mapping[str, FrozenFields]] = MappingProxyType(
    {
        "kinematics_2d": FrozenFields.from_mapping(
            {
                "initial_position_vector": (1.0, 0.0),
                "initial_velocity_vector": (3.0, 0.0),
                "acceleration_vector": (1.0, 0.0),
                "elapsed_time": 4.0,
            }
        ),
        "circular_position": FrozenFields.from_mapping(
            {"radius": 3.0, "angular_speed": 1.5, "initial_phase": 0.0, "elapsed_time": 2.0}
        ),
        "radial_acceleration": FrozenFields.from_mapping({"radius": 4.0, "speed": 8.0}),
        "circular_dynamics": FrozenFields.from_mapping(
            {"mass": 2.0, "radius": 2.0, "speed": math.sqrt(12.0), "inward_forces": (15.0, -3.0)}
        ),
        "impulse_momentum": FrozenFields.from_mapping(
            {"initial_momentum": 1.2, "force_samples": (-3.2, -3.2), "sample_interval": 0.3}
        ),
        "momentum_conservation": FrozenFields.from_mapping(
            {
                "masses": (2.0, 6.0),
                "initial_velocities": (4.0, 0.0),
                "external_impulse": 0.0,
                "final_velocity_1": 1.0,
            }
        ),
        "recoil": FrozenFields.from_mapping(
            {"mass_1": 4.0, "mass_2": 0.2, "initial_total_momentum": 0.0, "final_velocity_2": 20.0}
        ),
        "energy_conservation": FrozenFields.from_mapping(
            {
                "initial_kinetic_energy": 0.0,
                "initial_potential_energy": 176.4,
                "nonconservative_work": 0.0,
                "final_kinetic_energy": 117.6,
            }
        ),
        "potential_energy_diagram": FrozenFields.from_mapping(
            {
                "curvature": 1.0,
                "center": 2.0,
                "floor_energy": 1.0,
                "total_energy": 5.0,
                "position_samples": (0.0, 1.0, 2.0, 3.0, 4.0),
            }
        ),
        "elastic_collision": FrozenFields.from_mapping(
            {"masses": (1.0, 1.0), "initial_velocities": (5.0, 0.0)}
        ),
        "rigid_body_motion": FrozenFields.from_mapping(
            {"reference_velocity": (3.0, 1.0), "angular_velocity": 2.0, "relative_position": (0.6, 0.0)}
        ),
        "moment_of_inertia": FrozenFields.from_mapping(
            {"mass_elements": (3.0, 3.0), "perpendicular_distances": (2.0, 1.0)}
        ),
        "torque": FrozenFields.from_mapping(
            {"lever_arm_vector": (0.4, 0.0), "force_vector": (5.0 * math.sqrt(3.0), 5.0)}
        ),
        "rotational_dynamics": FrozenFields.from_mapping(
            {"external_torques": (-9.0, 3.0), "moment_of_inertia": 2.0, "initial_angular_speed": 0.0, "elapsed_time": 1.0}
        ),
        "point_particle_angular_momentum": FrozenFields.from_mapping(
            {"particle_position": (2.0, 0.0), "particle_momentum": (0.0, 3.0)}
        ),
        "rigid_body_angular_momentum": FrozenFields.from_mapping(
            {"inertia_tensor_diagonal": (0.8, 0.8, 0.8), "angular_velocity_vector": (0.0, 0.0, 5.0)}
        ),
        "angular_impulse": FrozenFields.from_mapping(
            {"initial_angular_momentum": 4.0, "constant_torque": 3.0, "time_interval": 2.0}
        ),
        "rolling_dynamics": FrozenFields.from_mapping(
            {"mass": 2.0, "radius": 0.5, "moment_of_inertia": 0.25, "gravity": 9.8, "incline_angle_degrees": 30.0}
        ),
    }
)


_PROSE_REQUIRED_MARKERS: Final[Mapping[str, Tuple[str, ...]]] = MappingProxyType(
    {
        "vectors": ("normalize",),
        "kinematics_position_velocity": ("x0", "v0", "t="),
        "kinematics_acceleration": ("x0", "v0", "a="),
        "newton_laws_of_motion": ("skater", "interaction force"),
        "circular_position": ("circle", "omega"),
        "uniform_circular_motion": ("constant speed", "radius"),
        "radial_acceleration": ("circle", "inward"),
        "impulse_momentum": ("impulse", "momentum"),
        "momentum_conservation": ("total momentum", "isolated"),
        "center_of_mass": ("weighted center",),
        "recoil": ("launcher", "projectile"),
        "continuous_mass_accumulation": ("fixed control volume", "enters", "leaves"),
        "work_energy_1d": ("work", "straight track"),
        "work_energy_multidimensional": ("dot", "displacement"),
        "potential_energy_configuration": ("spring displacement", "stored potential"),
        "energy_conservation": ("potential energy", "total bar"),
        "potential_energy_diagram": ("turning points", "u(x)"),
        "collision_classification": ("classify", "leave together"),
        "elastic_collision": ("elastically", "kinetic energy"),
        "rigid_body_motion": ("rigid bar", "omega cross r"),
        "moment_of_inertia": ("point mass", "i=mr"),
        "torque": ("lever arm", "sin"),
        "rotational_dynamics": ("net torque", "alpha"),
        "point_particle_angular_momentum": ("point particle", "lz"),
        "rigid_body_angular_momentum": ("rigid disk", "l=i"),
        "angular_impulse": ("angular impulse", "angular momentum"),
        "rolling_kinematics": ("without slipping", "contact point"),
        "rolling_dynamics": ("rolls down", "static friction"),
        "rolling_energy_angular_momentum": ("rolling", "lcm"),
    }
)


_PROSE_REQUIRED_NUMBERS: Final[Mapping[str, Tuple[float, ...]]] = MappingProxyType(
    {
        "vectors": (5.0, 12.0, 13.0, 1.0),
        "energy_conservation": (3.0, 6.0, 2.0, 9.8, 118.0, 8.85),
        "potential_energy_diagram": (2.0, 1.0, 5.0, 0.0, 4.0),
        "torque": (0.4, 10.0, 30.0, 2.0),
        "rolling_dynamics": (2.0, 0.5, 30.0, 3.27, 0.25, 9.8),
    }
)


_NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?")


def _flatten_numeric_values(value: object) -> Tuple[float, ...]:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return ()
    if isinstance(value, (int, float)):
        return (abs(float(value)),)
    if isinstance(value, Mapping):
        return tuple(number for item in value.values() for number in _flatten_numeric_values(item))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(number for item in value for number in _flatten_numeric_values(item))
    return ()


def _parse_recognized_worked_example(
    contract: PhysicsTitleContract,
    worked_example: Mapping[str, object],
    default_setup: Mapping[str, object],
) -> Mapping[str, object]:
    text_fields = [worked_example.get(key) for key in ("setup", "calculation", "takeaway")]
    if not all(isinstance(value, str) and value.strip() for value in text_fields):
        raise ValueError(
            "worked_example must provide nonempty setup, calculation, and takeaway text or a structured setup mapping"
        )
    text = " ".join(str(value) for value in text_fields).casefold()
    markers = _PROSE_REQUIRED_MARKERS.get(contract.model_id)
    if markers is None or any(marker not in text for marker in markers):
        raise ValueError(
            f"worked_example does not match the {contract.exact_title!r} semantic contract; provide a structured scenario setup"
        )
    observed = tuple(abs(float(value)) for value in _NUMBER_PATTERN.findall(text))
    required = _PROSE_REQUIRED_NUMBERS.get(
        contract.model_id,
        tuple(number for number in _flatten_numeric_values(default_setup) if not math.isclose(number, 0.0)),
    )
    for number in required:
        if not any(math.isclose(number, candidate, rel_tol=1e-6, abs_tol=1e-6) for candidate in observed):
            raise ValueError(
                f"worked_example numeric evidence does not match {contract.exact_title!r}; provide a structured scenario setup"
            )
    return default_setup


def _structured_setup_from_override(
    contract: PhysicsTitleContract,
    override: Mapping[str, object],
) -> Optional[Mapping[str, object]]:
    source: Mapping[str, object] = override
    for key in ("model_scenario", "scenario"):
        nested = source.get(key)
        if nested is not None:
            if not isinstance(nested, Mapping):
                raise TypeError(f"{key} must be a mapping")
            source = nested
            break
    model_id = source.get("model_id")
    if model_id is not None and model_id != contract.model_id:
        raise ValueError(
            f"scenario model_id {model_id!r} does not match exact title model {contract.model_id!r}"
        )
    mode = source.get("mode")
    if mode is not None and mode != contract.scenario_mode:
        raise ValueError(
            f"scenario mode {mode!r} does not match exact title mode {contract.scenario_mode!r}"
        )
    for key in ("setup", "numeric_setup"):
        setup = source.get(key)
        if isinstance(setup, Mapping):
            return setup
        if setup is not None and key == "numeric_setup":
            raise TypeError("numeric_setup must be a mapping")
    if source is not override or model_id is not None or mode is not None:
        if "setup" in source and not isinstance(source.get("setup"), Mapping):
            return None
        raise ValueError("structured scenario override must contain a setup mapping")
    return None


def build_physics_title_scenario(
    title: str,
    worked_example: Optional[Mapping[str, object]] = None,
    scenario_override: Optional[Mapping[str, object]] = None,
) -> PhysicsModelScenario:
    """Build an exact-title scenario, recomputing every derived numeric field."""

    contract = resolve_physics_title_contract(title, fail_closed=True)
    if worked_example is not None and not isinstance(worked_example, Mapping):
        raise TypeError("worked_example must be a mapping")
    if scenario_override is not None and not isinstance(scenario_override, Mapping):
        raise TypeError("scenario_override must be a mapping")
    if worked_example is not None and scenario_override is not None:
        raise ValueError("provide worked_example or scenario_override, not both")

    setup_values = dict(
        _MIT_8_01_SETUP_OVERRIDES_BY_MODEL_ID.get(
            contract.model_id, PHYSICS_MODEL_SCENARIO_DEFINITIONS[contract.model_id].setup
        ).items()
    )
    supplied = scenario_override if scenario_override is not None else worked_example
    if supplied is not None:
        structured = _structured_setup_from_override(contract, supplied)
        if structured is not None:
            setup_values.update(structured)
        else:
            parsed = _parse_recognized_worked_example(contract, supplied, setup_values)
            setup_values.update(parsed)
    scenario = build_physics_model_scenario(contract.model_id, setup_values)
    if scenario.mode != contract.scenario_mode:
        raise ValueError("resolved scenario mode does not match exact-title contract")
    return scenario


def build_physics_semantic_payload(
    title: str,
    worked_example: Optional[Mapping[str, object]] = None,
    scenario_override: Optional[Mapping[str, object]] = None,
) -> dict[str, object]:
    """Return renderer-neutral objects, exact states, and semantic transitions."""

    contract = resolve_physics_title_contract(title, fail_closed=True)
    scenario = build_physics_title_scenario(title, worked_example, scenario_override)
    spec = contract.spec
    object_ids = [f"physics:{contract.model_id}:{token}" for token in spec.required_figure_tokens]
    if not object_ids:
        raise ValueError("physics semantic payload requires at least one object")

    exact_states = {
        "uninitialized": {"phase": "uninitialized", "values": {}},
        "setup": {"phase": "setup", "values": scenario.setup.as_dict()},
        "calculation": {"phase": "calculation", "values": scenario.calculation.as_dict()},
        "result": {"phase": "result", "values": scenario.result.as_dict()},
    }

    def object_state(state_id: str) -> dict[str, object]:
        state = exact_states[state_id]
        return {
            object_id: {
                "phase": state["phase"],
                "visible": state_id != "uninitialized",
                "state_id": state_id,
                "evidence": state["values"],
            }
            for object_id in object_ids
        }

    transition_rows = (
        ("establish", "Establish the exact objects and authored setup.", "uninitialized", "setup"),
        ("compute", "Apply the canonical formula to the displayed numeric setup.", "setup", "calculation"),
        ("resolve", "Resolve the exact after-state from recomputed evidence.", "calculation", "result"),
    )
    transitions = [
        {
            "id": f"{contract.model_id}:{transition_id}",
            "claim": claim,
            "action": claim,
            "persistent_object_ids": list(object_ids),
            "before_state_id": before_id,
            "after_state_id": after_id,
            "before": object_state(before_id),
            "after": object_state(after_id),
            "before_evidence": exact_states[before_id],
            "after_evidence": exact_states[after_id],
        }
        for transition_id, claim, before_id, after_id in transition_rows
    ]
    objects = [
        {
            "id": object_id,
            "role": token.replace("_", " "),
            "persistent": True,
            "initial_state": object_state("uninitialized")[object_id],
        }
        for object_id, token in zip(object_ids, spec.required_figure_tokens)
    ]
    return {
        "semantic_schema": "physics-semantic-v1",
        "unit_number": contract.unit_number,
        "exact_title": contract.exact_title,
        "model_id": contract.model_id,
        "mode": scenario.mode,
        "video_route_key": contract.video_route_key,
        "visual_kind": spec.visual_kind,
        "canonical_formula": spec.canonical_formula,
        "mechanisms": list(contract.mechanism_ids),
        "objects": objects,
        "states": exact_states,
        "transitions": transitions,
        "scenario_mode": scenario.mode,
        "model_scenario": scenario.as_dict(),
        "numeric_setup": scenario.setup.as_dict(),
        "result_fields": scenario.result.as_dict(),
        "animation_states": [state.as_dict() for state in scenario.animation_states],
        "visible_evidence_tokens": list(scenario.visible_evidence_tokens),
        "scenario": scenario.as_dict(),
        "numeric_evidence": {
            "setup": scenario.setup.as_dict(),
            "calculation": scenario.calculation.as_dict(),
            "result": scenario.result.as_dict(),
        },
        "numeric_evidence_fingerprint": scenario.numeric_evidence_fingerprint,
    }


def build_all_physics_model_scenarios() -> Mapping[str, PhysicsModelScenario]:
    """Return a fresh immutable mapping containing every default scenario."""

    return MappingProxyType(
        {model_id: build_physics_model_scenario(model_id) for model_id in PHYSICS_MODEL_SCENARIO_DEFINITIONS}
    )


def get_physics_model_scenario(model_id: str) -> PhysicsModelScenario:
    """Return the immutable default scenario for an exact model id."""

    if not isinstance(model_id, str):
        raise TypeError("model_id must be a string")
    try:
        return PHYSICS_MODEL_SCENARIO_REGISTRY[model_id]
    except KeyError as error:
        raise ValueError(f"Unsupported physics model {model_id!r}") from error


PHYSICS_MODEL_SCENARIO_REGISTRY: Final[Mapping[str, PhysicsModelScenario]] = (
    build_all_physics_model_scenarios()
)
PHYSICS_MODEL_SCENARIOS = PHYSICS_MODEL_SCENARIO_REGISTRY
PHYSICS_SCENARIOS = PHYSICS_MODEL_SCENARIO_REGISTRY


__all__ = [
    "AnimationState",
    "FrozenFields",
    "PHYSICS_MODEL_SCENARIO_DEFINITIONS",
    "PHYSICS_MODEL_SCENARIO_REGISTRY",
    "PHYSICS_MODEL_SCENARIOS",
    "PHYSICS_SCENARIOS",
    "PhysicsModelScenario",
    "PhysicsScenarioDefinition",
    "build_all_physics_model_scenarios",
    "build_physics_model_scenario",
    "build_physics_semantic_payload",
    "build_physics_title_scenario",
    "get_physics_model_scenario",
    "physics_numeric_evidence_fingerprint",
    "recompute_physics_model_scenario",
]

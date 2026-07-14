"""Immutable, numeric scenarios for every registered economics model.

The scenario registry is deliberately independent of ``stem_course``.  Each
entry supplies a concrete setup, results derived from that setup, a small scene
contract, and the exact evidence strings required by the matching model spec.
Call :func:`build_economics_model_scenario` with setup overrides to obtain a
new scenario whose result fields and animation states have been recomputed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
import hashlib
import json
from math import isfinite, sqrt
from numbers import Real
from types import MappingProxyType
from typing import Final

try:
    from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY
except ModuleNotFoundError:  # Imported by direct execution of tools/stem_course.py.
    from economics_model_specs import ECONOMICS_MODEL_REGISTRY


NumericMap = Mapping[str, float]
Calculator = Callable[[NumericMap], Mapping[str, Real]]


def _ordered_union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token for group in groups for token in group))


def _freeze_numeric(values: Mapping[str, Real], field_name: str) -> NumericMap:
    frozen: dict[str, float] = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            raise TypeError(f"{field_name} keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name}[{key!r}] must be a real number")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"{field_name}[{key!r}] must be finite")
        frozen[key] = number
    if not frozen:
        raise ValueError(f"{field_name} must not be empty")
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class AxisSpec:
    """One immutable Cartesian axis used by a scenario."""

    axis_id: str
    horizontal_label: str
    vertical_label: str
    horizontal_min: float
    horizontal_max: float
    vertical_min: float
    vertical_max: float

    def as_dict(self) -> dict[str, object]:
        return {
            "axis_id": self.axis_id,
            "horizontal_label": self.horizontal_label,
            "vertical_label": self.vertical_label,
            "horizontal_min": self.horizontal_min,
            "horizontal_max": self.horizontal_max,
            "vertical_min": self.vertical_min,
            "vertical_max": self.vertical_max,
        }


@dataclass(frozen=True)
class SceneObject:
    """A visible curve, marker, region, table, or annotation."""

    object_id: str
    kind: str
    label: str
    axis_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "object_id": self.object_id,
            "kind": self.kind,
            "label": self.label,
            "axis_id": self.axis_id,
        }


@dataclass(frozen=True)
class AnimationState(Mapping[str, object]):
    """One deterministic reveal state in the scenario animation."""

    state_id: str
    phase: str
    progress: float
    values: NumericMap = field()
    visible_object_ids: tuple[str, ...]
    visible_evidence_tokens: tuple[str, ...]
    result_fields: tuple[str, ...]

    @property
    def visible_tokens(self) -> tuple[str, ...]:
        return self.visible_evidence_tokens

    def __getitem__(self, key: str) -> object:
        if key == "visible_tokens":
            return self.visible_evidence_tokens
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
            "values": dict(self.values),
            "visible_object_ids": list(self.visible_object_ids),
            "visible_evidence_tokens": list(self.visible_evidence_tokens),
            "result_fields": list(self.result_fields),
        }


_ANIMATION_FIELD_NAMES = (
    "state_id",
    "phase",
    "progress",
    "values",
    "visible_object_ids",
    "visible_evidence_tokens",
    "result_fields",
)


@dataclass(frozen=True)
class NumericScenarioSchema(Mapping[str, NumericMap]):
    """Typed numeric phases shared by planning, rendering, and validation."""

    setup: NumericMap
    calculation: NumericMap
    result: NumericMap

    def __getitem__(self, key: str) -> NumericMap:
        if key in ("setup", "calculation", "result"):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(("setup", "calculation", "result"))

    def __len__(self) -> int:
        return 3

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {
            "setup": dict(self.setup),
            "calculation": dict(self.calculation),
            "result": dict(self.result),
        }


@dataclass(frozen=True)
class EconomicsModelScenario(Mapping[str, object]):
    """A complete immutable worked scenario for one economics model."""

    model_id: str
    mode: str
    setup: NumericMap
    calculation: NumericMap
    results: NumericMap
    animation_states: tuple[AnimationState, ...]
    axes: tuple[AxisSpec, ...]
    objects: tuple[SceneObject, ...]
    required_example_tokens: tuple[str, ...]
    required_figure_tokens: tuple[str, ...]
    visible_evidence_tokens: tuple[str, ...]

    @property
    def numeric_setup(self) -> NumericMap:
        return self.setup

    @property
    def result_fields(self) -> NumericMap:
        return self.results

    @property
    def calculation_fields(self) -> NumericMap:
        return self.calculation

    @property
    def result(self) -> NumericMap:
        return self.results

    @property
    def animation_state_sequence(self) -> tuple[AnimationState, ...]:
        return self.animation_states

    @property
    def axis_specs(self) -> tuple[AxisSpec, ...]:
        return self.axes

    @property
    def object_specs(self) -> tuple[SceneObject, ...]:
        return self.objects

    @property
    def exact_visible_evidence_tokens(self) -> tuple[str, ...]:
        return self.visible_evidence_tokens

    @property
    def evidence_tokens(self) -> tuple[str, ...]:
        return self.visible_evidence_tokens

    @property
    def numeric_evidence_fingerprint(self) -> str:
        return economics_numeric_evidence_fingerprint(self)

    @property
    def numeric_fingerprint(self) -> str:
        return self.numeric_evidence_fingerprint

    @property
    def numeric_schema(self) -> NumericScenarioSchema:
        return NumericScenarioSchema(self.setup, self.calculation, self.results)

    def rebuild(self, setup_overrides: Mapping[str, Real]) -> "EconomicsModelScenario":
        return build_economics_model_scenario(self.model_id, setup_overrides)

    def __getitem__(self, key: str) -> object:
        if key in ("numeric_evidence_fingerprint", "numeric_fingerprint", "numeric_schema"):
            return getattr(self, key)
        aliases = {
            "numeric_setup": self.setup,
            "calculation_fields": self.calculation,
            "result": self.results,
            "result_fields": self.results,
            "animation_state_sequence": self.animation_states,
            "axis_specs": self.axes,
            "object_specs": self.objects,
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
            "numeric_schema": self.numeric_schema.as_dict(),
            "setup": dict(self.setup),
            "calculation": dict(self.calculation),
            "results": dict(self.results),
            "result": dict(self.results),
            "animation_states": [state.as_dict() for state in self.animation_states],
            "axes": [axis.as_dict() for axis in self.axes],
            "objects": [obj.as_dict() for obj in self.objects],
            "required_example_tokens": list(self.required_example_tokens),
            "required_figure_tokens": list(self.required_figure_tokens),
            "visible_evidence_tokens": list(self.visible_evidence_tokens),
            "required_evidence_metadata": {
                "example_tokens": list(self.required_example_tokens),
                "figure_tokens": list(self.required_figure_tokens),
                "required_tokens": list(self.visible_evidence_tokens),
            },
            "numeric_evidence_fingerprint": self.numeric_evidence_fingerprint,
            "numeric_fingerprint": self.numeric_fingerprint,
        }


_SCENARIO_FIELD_NAMES = (
    "model_id",
    "mode",
    "setup",
    "calculation",
    "results",
    "animation_states",
    "axes",
    "objects",
    "required_example_tokens",
    "required_figure_tokens",
    "visible_evidence_tokens",
)


def _canonical_numeric_evidence(values: Mapping[str, object]) -> dict[str, float]:
    canonical: dict[str, float] = {}
    for key in sorted(values):
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"numeric evidence field {key!r} must be a real number")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"numeric evidence field {key!r} must be finite")
        canonical[str(key)] = 0.0 if number == 0.0 else number
    if not canonical:
        raise ValueError("numeric evidence phase must not be empty")
    return canonical


def economics_numeric_evidence_fingerprint(
    scenario: EconomicsModelScenario | Mapping[str, object],
) -> str:
    """Hash canonical recomputed setup, calculation, and result evidence."""

    if not isinstance(scenario, Mapping):
        raise TypeError("scenario must be an economics scenario mapping")
    try:
        setup = scenario["setup"]
        calculation = scenario["calculation"]
        result = scenario["result"]
    except KeyError as exc:
        raise ValueError(
            "scenario must contain setup, calculation, and result"
        ) from exc
    if not all(isinstance(phase, Mapping) for phase in (setup, calculation, result)):
        raise TypeError("scenario numeric evidence phases must be mappings")
    evidence = {
        "setup": _canonical_numeric_evidence(setup),  # type: ignore[arg-type]
        "calculation": _canonical_numeric_evidence(calculation),  # type: ignore[arg-type]
        "result": _canonical_numeric_evidence(result),  # type: ignore[arg-type]
    }
    serialized = json.dumps(
        evidence, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(serialized.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class _ScenarioDefinition:
    mode: str
    setup: tuple[tuple[str, float], ...]
    calculator: Calculator
    axes: tuple[AxisSpec, ...]
    objects: tuple[SceneObject, ...]


EconomicsScenarioDefinition = _ScenarioDefinition


def _setup(**values: float) -> tuple[tuple[str, float], ...]:
    return tuple(values.items())


def _axis(
    horizontal_label: str,
    vertical_label: str,
    horizontal_max: float = 120.0,
    vertical_max: float = 120.0,
) -> tuple[AxisSpec, ...]:
    return (
        AxisSpec(
            axis_id="main",
            horizontal_label=horizontal_label,
            vertical_label=vertical_label,
            horizontal_min=0.0,
            horizontal_max=horizontal_max,
            vertical_min=0.0,
            vertical_max=vertical_max,
        ),
    )


def _infer_object_kind(object_id: str) -> str:
    if "matrix" in object_id or "payoff" in object_id:
        return "table"
    if any(
        word in object_id
        for word in ("area", "gap", "wedge", "range", "surplus", "shortage")
    ):
        return "region"
    if any(
        word in object_id
        for word in ("point", "bundle", "marker", "equilibrium", "choice")
    ):
        return "marker"
    if any(
        word in object_id
        for word in ("curve", "line", "frontier", "function", "constraint")
    ):
        return "curve"
    return "annotation"


def _objects(*object_ids: str) -> tuple[SceneObject, ...]:
    return tuple(
        SceneObject(
            object_id=object_id,
            kind=_infer_object_kind(object_id),
            label=object_id.replace("_", " "),
            axis_id="main",
        )
        for object_id in object_ids
    )


def _definition(
    mode: str,
    setup: tuple[tuple[str, float], ...],
    calculator: Calculator,
    horizontal_label: str,
    vertical_label: str,
    object_ids: tuple[str, ...],
    horizontal_max: float = 120.0,
    vertical_max: float = 120.0,
) -> _ScenarioDefinition:
    return _ScenarioDefinition(
        mode=mode,
        setup=setup,
        calculator=calculator,
        axes=_axis(horizontal_label, vertical_label, horizontal_max, vertical_max),
        objects=_objects(*object_ids),
    )


def _linear_equilibrium(
    demand_intercept: float,
    demand_slope: float,
    supply_intercept: float,
    supply_slope: float,
) -> tuple[float, float]:
    price = (demand_intercept - supply_intercept) / (demand_slope + supply_slope)
    quantity = demand_intercept - demand_slope * price
    return price, quantity


def _supply_demand_intro(s: NumericMap) -> Mapping[str, Real]:
    q_d = s["demand_intercept"] - s["demand_slope"] * s["price"]
    q_s = s["supply_intercept"] + s["supply_slope"] * s["price"]
    return {"quantity_demanded": q_d, "quantity_supplied": q_s, "market_gap": q_d - q_s}


def _market_equilibrium(s: NumericMap) -> Mapping[str, Real]:
    price, quantity = _linear_equilibrium(
        s["demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    return {
        "equilibrium_price": price,
        "equilibrium_quantity": quantity,
        "quantity_demanded": quantity,
        "quantity_supplied": quantity,
    }


def _demand_curve(s: NumericMap) -> Mapping[str, Real]:
    quantity = (
        s["demand_intercept"]
        - s["own_price_slope"] * s["own_price"]
        + s["income_coefficient"] * s["income"]
        + s["cross_price_coefficient"] * s["related_good_price"]
        + s["taste_shift"]
    )
    return {"own_price": s["own_price"], "quantity_demanded": quantity}


def _supply_curve(s: NumericMap) -> Mapping[str, Real]:
    quantity = (
        s["supply_intercept"]
        + s["output_price_slope"] * s["output_price"]
        - s["wage_coefficient"] * s["wage"]
        - s["rental_coefficient"] * s["rental_price"]
        + s["technology_coefficient"] * s["technology"]
    )
    return {"output_price": s["output_price"], "quantity_supplied": quantity}


def _comparative_statics(s: NumericMap) -> Mapping[str, Real]:
    initial_price, initial_quantity = _linear_equilibrium(
        s["initial_demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    new_price, new_quantity = _linear_equilibrium(
        s["new_demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    return {
        "initial_equilibrium_price": initial_price,
        "new_equilibrium_price": new_price,
        "price_change": new_price - initial_price,
        "initial_equilibrium_quantity": initial_quantity,
        "new_equilibrium_quantity": new_quantity,
        "quantity_change": new_quantity - initial_quantity,
    }


def _price_ceiling(s: NumericMap) -> Mapping[str, Real]:
    equilibrium_price, _ = _linear_equilibrium(
        s["demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    q_d = s["demand_intercept"] - s["demand_slope"] * s["ceiling_price"]
    q_s = s["supply_intercept"] + s["supply_slope"] * s["ceiling_price"]
    binding = s["ceiling_price"] < equilibrium_price
    return {
        "equilibrium_price": equilibrium_price,
        "quantity_demanded": q_d,
        "quantity_supplied": q_s,
        "shortage": max(q_d - q_s, 0.0) if binding else 0.0,
        "binding_indicator": float(binding),
    }


def _price_floor(s: NumericMap) -> Mapping[str, Real]:
    equilibrium_price, _ = _linear_equilibrium(
        s["demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    q_d = s["demand_intercept"] - s["demand_slope"] * s["floor_price"]
    q_s = s["supply_intercept"] + s["supply_slope"] * s["floor_price"]
    binding = s["floor_price"] > equilibrium_price
    return {
        "equilibrium_price": equilibrium_price,
        "quantity_demanded": q_d,
        "quantity_supplied": q_s,
        "surplus": max(q_s - q_d, 0.0) if binding else 0.0,
        "binding_indicator": float(binding),
    }


def _price_controls(s: NumericMap) -> Mapping[str, Real]:
    equilibrium_price, _ = _linear_equilibrium(
        s["demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    qd_ceiling = s["demand_intercept"] - s["demand_slope"] * s["ceiling_price"]
    qs_ceiling = s["supply_intercept"] + s["supply_slope"] * s["ceiling_price"]
    qd_floor = s["demand_intercept"] - s["demand_slope"] * s["floor_price"]
    qs_floor = s["supply_intercept"] + s["supply_slope"] * s["floor_price"]
    ceiling_binding = s["ceiling_price"] < equilibrium_price
    floor_binding = s["floor_price"] > equilibrium_price
    return {
        "equilibrium_price": equilibrium_price,
        "ceiling_shortage": (
            max(qd_ceiling - qs_ceiling, 0.0) if ceiling_binding else 0.0
        ),
        "floor_surplus": max(qs_floor - qd_floor, 0.0) if floor_binding else 0.0,
        "ceiling_binding_indicator": float(ceiling_binding),
        "floor_binding_indicator": float(floor_binding),
    }


def _consumer_preferences(s: NumericMap) -> Mapping[str, Real]:
    utility_a = s["bundle_a_x"] * s["bundle_a_y"]
    utility_b = s["bundle_b_x"] * s["bundle_b_y"]
    return {
        "bundle_a_score": utility_a,
        "bundle_b_score": utility_b,
        "preferred_bundle_index": 1.0 if utility_a >= utility_b else 2.0,
        "ranking_gap": abs(utility_a - utility_b),
    }


def _utility_representation(s: NumericMap) -> Mapping[str, Real]:
    utility_a = sqrt(s["bundle_a_x"] * s["bundle_a_y"])
    utility_b = sqrt(s["bundle_b_x"] * s["bundle_b_y"])
    return {
        "utility_a": utility_a,
        "utility_b": utility_b,
        "preferred_bundle_index": 1.0 if utility_a >= utility_b else 2.0,
    }


def _budget_constraint(s: NumericMap) -> Mapping[str, Real]:
    expenditure = s["price_x"] * s["bundle_x"] + s["price_y"] * s["bundle_y"]
    return {
        "expenditure": expenditure,
        "budget_slack": s["income"] - expenditure,
        "affordable_indicator": float(expenditure <= s["income"]),
        "x_intercept": s["income"] / s["price_x"],
        "y_intercept": s["income"] / s["price_y"],
        "budget_slope": -s["price_x"] / s["price_y"],
    }


def _mrs(s: NumericMap) -> Mapping[str, Real]:
    mu_x = 0.5 * sqrt(s["quantity_y"] / s["quantity_x"])
    mu_y = 0.5 * sqrt(s["quantity_x"] / s["quantity_y"])
    mrs = mu_x / mu_y
    return {
        "marginal_utility_x": mu_x,
        "marginal_utility_y": mu_y,
        "MRS": mrs,
        "curve_slope": -mrs,
    }


def _consumer_choice(s: NumericMap) -> Mapping[str, Real]:
    x = s["utility_share_x"] * s["income"] / s["price_x"]
    y = (1.0 - s["utility_share_x"]) * s["income"] / s["price_y"]
    utility = x ** s["utility_share_x"] * y ** (1.0 - s["utility_share_x"])
    return {
        "chosen_x": x,
        "chosen_y": y,
        "expenditure": s["price_x"] * x + s["price_y"] * y,
        "utility": utility,
    }


def _income_substitution(s: NumericMap) -> Mapping[str, Real]:
    substitution = s["compensated_quantity"] - s["initial_quantity"]
    income = s["final_quantity"] - s["compensated_quantity"]
    return {
        "substitution_effect": substitution,
        "income_effect": income,
        "total_change": substitution + income,
    }


def _own_price_elasticity(s: NumericMap) -> Mapping[str, Real]:
    quantity_change = (s["new_quantity"] - s["initial_quantity"]) / s[
        "initial_quantity"
    ]
    price_change = (s["new_price"] - s["initial_price"]) / s["initial_price"]
    elasticity = quantity_change / price_change
    return {
        "percent_quantity_change": quantity_change,
        "percent_own_price_change": price_change,
        "own_price_elasticity": elasticity,
        "elasticity_magnitude": abs(elasticity),
    }


def _income_elasticity(s: NumericMap) -> Mapping[str, Real]:
    quantity_change = (s["new_quantity"] - s["initial_quantity"]) / s[
        "initial_quantity"
    ]
    income_change = (s["new_income"] - s["initial_income"]) / s["initial_income"]
    elasticity = quantity_change / income_change
    return {
        "percent_quantity_change": quantity_change,
        "percent_income_change": income_change,
        "income_elasticity": elasticity,
        "normal_good_indicator": float(elasticity > 0.0),
        "inferior_good_indicator": float(elasticity < 0.0),
    }


def _cross_price_elasticity(s: NumericMap) -> Mapping[str, Real]:
    quantity_change = (s["new_quantity_x"] - s["initial_quantity_x"]) / s[
        "initial_quantity_x"
    ]
    other_price_change = (s["new_price_y"] - s["initial_price_y"]) / s[
        "initial_price_y"
    ]
    elasticity = quantity_change / other_price_change
    return {
        "percent_quantity_x_change": quantity_change,
        "percent_price_y_change": other_price_change,
        "cross_price_elasticity": elasticity,
        "substitutes_indicator": float(elasticity > 0.0),
        "complements_indicator": float(elasticity < 0.0),
    }


def _production_function(s: NumericMap) -> Mapping[str, Real]:
    output = (
        s["technology"]
        * s["labor"] ** s["labor_share"]
        * s["capital"] ** (1.0 - s["labor_share"])
    )
    return {
        "output": output,
        "marginal_product_labor": s["labor_share"] * output / s["labor"],
        "marginal_product_capital": (1.0 - s["labor_share"]) * output / s["capital"],
    }


def _labor_market(s: NumericMap) -> Mapping[str, Real]:
    wage, employment = _linear_equilibrium(
        s["labor_demand_intercept"],
        s["labor_demand_slope"],
        s["labor_supply_intercept"],
        s["labor_supply_slope"],
    )
    return {
        "equilibrium_wage": wage,
        "employment": employment,
        "labor_demanded": employment,
        "labor_supplied": employment,
    }


def _labor_input(s: NumericMap) -> Mapping[str, Real]:
    labor = (s["marginal_product_intercept"] - s["wage"] / s["marginal_revenue"]) / s[
        "marginal_product_slope"
    ]
    marginal_product = (
        s["marginal_product_intercept"] - s["marginal_product_slope"] * labor
    )
    return {
        "labor_input": labor,
        "marginal_product_labor": marginal_product,
        "marginal_revenue_product_labor": s["marginal_revenue"] * marginal_product,
    }


def _capital_input(s: NumericMap) -> Mapping[str, Real]:
    capital = (
        s["marginal_product_intercept"] - s["rental_price"] / s["marginal_revenue"]
    ) / s["marginal_product_slope"]
    marginal_product = (
        s["marginal_product_intercept"] - s["marginal_product_slope"] * capital
    )
    return {
        "capital_input": capital,
        "marginal_product_capital": marginal_product,
        "marginal_revenue_product_capital": s["marginal_revenue"] * marginal_product,
    }


def _factor_inputs(s: NumericMap) -> Mapping[str, Real]:
    alpha = s["labor_share"]
    if not 0.0 < alpha < 1.0:
        raise ValueError("labor_share must lie strictly between zero and one")
    if min(s["technology"], s["target_output"], s["wage"], s["rental_price"]) <= 0.0:
        raise ValueError("technology, target output, and factor prices must be positive")
    capital_labor_ratio = (
        s["wage"] * (1.0 - alpha) / (s["rental_price"] * alpha)
    )
    labor = s["target_output"] / (
        s["technology"] * capital_labor_ratio ** (1.0 - alpha)
    )
    capital = capital_labor_ratio * labor
    marginal_product_labor = (
        alpha * s["target_output"] / labor
    )
    marginal_product_capital = (
        (1.0 - alpha) * s["target_output"] / capital
    )
    return {
        "labor_input": labor,
        "capital_input": capital,
        "capital_labor_ratio": capital_labor_ratio,
        "marginal_product_labor": marginal_product_labor,
        "marginal_product_capital": marginal_product_capital,
        "MRTS_labor_for_capital": marginal_product_labor / marginal_product_capital,
        "factor_price_ratio": s["wage"] / s["rental_price"],
        "minimum_cost": s["wage"] * labor + s["rental_price"] * capital,
        "produced_output": s["technology"] * labor**alpha * capital ** (1.0 - alpha),
    }


def _intertemporal_choice(s: NumericMap) -> Mapping[str, Real]:
    present_value = s["income_now"] + s["income_later"] / (1.0 + s["interest_rate"])
    consumption_later = (present_value - s["chosen_consumption_now"]) * (
        1.0 + s["interest_rate"]
    )
    return {
        "present_value_wealth": present_value,
        "chosen_consumption_now": s["chosen_consumption_now"],
        "chosen_consumption_later": consumption_later,
        "saving_now": s["income_now"] - s["chosen_consumption_now"],
        "max_consumption_now": present_value,
        "max_consumption_later": present_value * (1.0 + s["interest_rate"]),
    }


def _cost_curves(s: NumericMap) -> Mapping[str, Real]:
    variable_cost = (
        s["variable_linear_cost"] * s["output"]
        + s["variable_quadratic_cost"] * s["output"] ** 2
    )
    total_cost = s["fixed_cost"] + variable_cost
    return {
        "FC": s["fixed_cost"],
        "VC": variable_cost,
        "TC": total_cost,
        "AC": total_cost / s["output"],
        "AVC": variable_cost / s["output"],
        "MC": s["variable_linear_cost"]
        + 2.0 * s["variable_quadratic_cost"] * s["output"],
    }


def _perfect_competition(s: NumericMap) -> Mapping[str, Real]:
    output = (s["market_price"] - s["marginal_cost_intercept"]) / s[
        "marginal_cost_slope"
    ]
    variable_cost = (
        s["marginal_cost_intercept"] * output
        + 0.5 * s["marginal_cost_slope"] * output**2
    )
    revenue = s["market_price"] * output
    return {
        "price": s["market_price"],
        "marginal_revenue": s["market_price"],
        "chosen_output": output,
        "total_revenue": revenue,
        "total_cost": s["fixed_cost"] + variable_cost,
        "profit": revenue - s["fixed_cost"] - variable_cost,
    }


def _competitive_shutdown(s: NumericMap) -> Mapping[str, Real]:
    shutdown = s["market_price"] < s["minimum_average_variable_cost"]
    output = 0.0 if shutdown else s["operating_output"]
    return {
        "chosen_output": output,
        "shutdown_indicator": float(shutdown),
        "price_minus_minimum_AVC": s["market_price"]
        - s["minimum_average_variable_cost"],
        "short_run_profit": -s["fixed_cost"] if shutdown else s["operating_profit"],
    }


def _monopoly(s: NumericMap) -> Mapping[str, Real]:
    quantity = (s["demand_intercept"] - s["marginal_cost"]) / (2.0 * s["demand_slope"])
    price = s["demand_intercept"] - s["demand_slope"] * quantity
    return {
        "monopoly_quantity": quantity,
        "monopoly_price": price,
        "marginal_revenue": s["demand_intercept"] - 2.0 * s["demand_slope"] * quantity,
        "profit": (price - s["marginal_cost"]) * quantity - s["fixed_cost"],
    }


def _marginal_revenue(s: NumericMap) -> Mapping[str, Real]:
    price = s["demand_intercept"] - s["demand_slope"] * s["quantity"]
    return {
        "price": price,
        "total_revenue": price * s["quantity"],
        "marginal_revenue": s["demand_intercept"]
        - 2.0 * s["demand_slope"] * s["quantity"],
        "quantity_price_effect": -s["demand_slope"] * s["quantity"],
    }


def _price_discrimination(s: NumericMap) -> Mapping[str, Real]:
    quantity_1 = (s["demand_1_intercept"] - s["marginal_cost"]) / (
        2.0 * s["demand_1_slope"]
    )
    quantity_2 = (s["demand_2_intercept"] - s["marginal_cost"]) / (
        2.0 * s["demand_2_slope"]
    )
    price_1 = s["demand_1_intercept"] - s["demand_1_slope"] * quantity_1
    price_2 = s["demand_2_intercept"] - s["demand_2_slope"] * quantity_2
    return {
        "market_1_quantity": quantity_1,
        "market_2_quantity": quantity_2,
        "market_1_price": price_1,
        "market_2_price": price_2,
        "total_quantity": quantity_1 + quantity_2,
        "common_marginal_revenue": s["marginal_cost"],
        "profit": (price_1 - s["marginal_cost"]) * quantity_1
        + (price_2 - s["marginal_cost"]) * quantity_2
        - s["fixed_cost"],
    }


def _oligopoly(s: NumericMap) -> Mapping[str, Real]:
    firm_quantity = (s["demand_intercept"] - s["marginal_cost"]) / (
        3.0 * s["demand_slope"]
    )
    total_quantity = 2.0 * firm_quantity
    price = s["demand_intercept"] - s["demand_slope"] * total_quantity
    profit = (price - s["marginal_cost"]) * firm_quantity
    return {
        "firm_1_quantity": firm_quantity,
        "firm_2_quantity": firm_quantity,
        "total_quantity": total_quantity,
        "market_price": price,
        "firm_1_profit": profit,
        "firm_2_profit": profit,
    }


def _oligopoly_collusion(s: NumericMap) -> Mapping[str, Real]:
    cournot_firm_quantity = (s["demand_intercept"] - s["marginal_cost"]) / (
        3.0 * s["demand_slope"]
    )
    cournot_total_quantity = 2.0 * cournot_firm_quantity
    collusive_total_quantity = (s["demand_intercept"] - s["marginal_cost"]) / (
        2.0 * s["demand_slope"]
    )
    collusive_firm_quantity = collusive_total_quantity / 2.0
    cournot_price = s["demand_intercept"] - s["demand_slope"] * cournot_total_quantity
    collusive_price = s["demand_intercept"] - s["demand_slope"] * collusive_total_quantity
    return {
        "cournot_firm_quantity": cournot_firm_quantity,
        "cournot_total_quantity": cournot_total_quantity,
        "cournot_price": cournot_price,
        "cournot_firm_profit": (cournot_price - s["marginal_cost"]) * cournot_firm_quantity,
        "collusive_firm_quantity": collusive_firm_quantity,
        "collusive_total_quantity": collusive_total_quantity,
        "collusive_price": collusive_price,
        "collusive_firm_profit": (collusive_price - s["marginal_cost"]) * collusive_firm_quantity,
        "output_restriction": cournot_total_quantity - collusive_total_quantity,
        "price_increase": collusive_price - cournot_price,
    }


def _strategic_game(s: NumericMap) -> Mapping[str, Real]:
    row_payoffs = (s["row_aa"], s["row_ab"], s["row_ba"], s["row_bb"])
    column_payoffs = (s["column_aa"], s["column_ab"], s["column_ba"], s["column_bb"])
    return {
        "player_count": 2.0,
        "strategy_profiles": 4.0,
        "largest_row_payoff": max(row_payoffs),
        "largest_column_payoff": max(column_payoffs),
        "payoff_sum_at_aa": s["row_aa"] + s["column_aa"],
        "payoff_sum_at_bb": s["row_bb"] + s["column_bb"],
    }


def _nash_equilibrium(s: NumericMap) -> Mapping[str, Real]:
    cells = (
        ("aa", s["row_aa"], s["column_aa"], s["row_ba"], s["column_ab"]),
        ("ab", s["row_ab"], s["column_ab"], s["row_bb"], s["column_aa"]),
        ("ba", s["row_ba"], s["column_ba"], s["row_aa"], s["column_bb"]),
        ("bb", s["row_bb"], s["column_bb"], s["row_ab"], s["column_ba"]),
    )
    nash_totals = [
        row + column
        for _, row, column, row_alternative, column_alternative in cells
        if row >= row_alternative and column >= column_alternative
    ]
    return {
        "nash_equilibrium_count": float(len(nash_totals)),
        "largest_nash_total_payoff": max(nash_totals, default=0.0),
        "unilateral_deviation_gain_at_aa": max(
            s["row_ba"] - s["row_aa"], s["column_ab"] - s["column_aa"], 0.0
        ),
    }


def _dominant_strategy(s: NumericMap) -> Mapping[str, Real]:
    row_a = s["row_aa"] > s["row_ba"] and s["row_ab"] > s["row_bb"]
    row_b = s["row_ba"] > s["row_aa"] and s["row_bb"] > s["row_ab"]
    column_a = s["column_aa"] > s["column_ab"] and s["column_ba"] > s["column_bb"]
    column_b = s["column_ab"] > s["column_aa"] and s["column_bb"] > s["column_ba"]
    row_index = 0.0 if row_a else 1.0 if row_b else -1.0
    column_index = 0.0 if column_a else 1.0 if column_b else -1.0
    payoff_by_cell = {
        (0.0, 0.0): s["row_aa"] + s["column_aa"],
        (0.0, 1.0): s["row_ab"] + s["column_ab"],
        (1.0, 0.0): s["row_ba"] + s["column_ba"],
        (1.0, 1.0): s["row_bb"] + s["column_bb"],
    }
    return {
        "row_dominant_strategy_index": row_index,
        "column_dominant_strategy_index": column_index,
        "dominant_strategy_count": float(row_a or row_b) + float(column_a or column_b),
        "dominant_equilibrium_total_payoff": payoff_by_cell.get(
            (row_index, column_index), 0.0
        ),
    }


def _consumer_surplus(s: NumericMap) -> Mapping[str, Real]:
    surplus = 0.5 * (s["choke_price"] - s["market_price"]) * s["quantity"]
    return {
        "CS": surplus,
        "willingness_to_pay_at_zero": s["choke_price"],
        "market_expenditure": s["market_price"] * s["quantity"],
    }


def _producer_surplus(s: NumericMap) -> Mapping[str, Real]:
    surplus = 0.5 * (s["market_price"] - s["supply_intercept_price"]) * s["quantity"]
    return {
        "PS": surplus,
        "minimum_supply_price": s["supply_intercept_price"],
        "producer_revenue": s["market_price"] * s["quantity"],
    }


def _total_surplus(s: NumericMap) -> Mapping[str, Real]:
    return {
        "CS": s["consumer_surplus"],
        "PS": s["producer_surplus"],
        "TS": s["consumer_surplus"] + s["producer_surplus"],
    }


def _welfare_surplus(s: NumericMap) -> Mapping[str, Real]:
    quantity = (s["marginal_benefit_intercept"] - s["marginal_cost_intercept"]) / (
        s["marginal_benefit_slope"] + s["marginal_cost_slope"]
    )
    price = s["marginal_benefit_intercept"] - s["marginal_benefit_slope"] * quantity
    cs = 0.5 * (s["marginal_benefit_intercept"] - price) * quantity
    ps = 0.5 * (price - s["marginal_cost_intercept"]) * quantity
    return {
        "efficient_quantity": quantity,
        "equilibrium_price": price,
        "CS": cs,
        "PS": ps,
        "TS": cs + ps,
    }


def _tax_incidence(s: NumericMap) -> Mapping[str, Real]:
    denominator = s["absolute_demand_elasticity"] + s["supply_elasticity"]
    buyer_burden = s["tax"] * s["supply_elasticity"] / denominator
    seller_burden = s["tax"] * s["absolute_demand_elasticity"] / denominator
    return {
        "buyer_burden": buyer_burden,
        "seller_burden": seller_burden,
        "buyer_price": s["pre_tax_price"] + buyer_burden,
        "seller_price": s["pre_tax_price"] - seller_burden,
        "tax_wedge": buyer_burden + seller_burden,
    }


def _tax_deadweight_loss(s: NumericMap) -> Mapping[str, Real]:
    quantity_reduction = s["quantity_before_tax"] - s["quantity_after_tax"]
    return {
        "quantity_reduction": quantity_reduction,
        "tax_revenue": s["tax"] * s["quantity_after_tax"],
        "DWL": 0.5 * s["tax"] * quantity_reduction,
    }


def _externality(s: NumericMap) -> Mapping[str, Real]:
    market_quantity = (s["benefit_intercept"] - s["private_cost_intercept"]) / (
        s["benefit_slope"] + s["private_cost_slope"]
    )
    social_cost_intercept = s["private_cost_intercept"] + s["external_cost_per_unit"]
    efficient_quantity = (s["benefit_intercept"] - social_cost_intercept) / (
        s["benefit_slope"] + s["private_cost_slope"]
    )
    return {
        "market_quantity": market_quantity,
        "efficient_quantity": efficient_quantity,
        "overproduction": market_quantity - efficient_quantity,
        "marginal_external_cost": s["external_cost_per_unit"],
    }


def _coase_bargaining(s: NumericMap) -> Mapping[str, Real]:
    abatement = (s["abatement_benefit_intercept"] - s["abatement_cost_intercept"]) / (
        s["abatement_benefit_slope"] + s["abatement_cost_slope"]
    )
    gross_gains = (
        0.5
        * (s["abatement_benefit_intercept"] - s["abatement_cost_intercept"])
        * abatement
    )
    return {
        "efficient_abatement": abatement,
        "marginal_benefit": s["abatement_benefit_intercept"]
        - s["abatement_benefit_slope"] * abatement,
        "marginal_cost": s["abatement_cost_intercept"]
        + s["abatement_cost_slope"] * abatement,
        "gross_bargaining_gains": gross_gains,
        "net_bargaining_gains": gross_gains - s["transaction_costs"],
        "bargaining_feasible_indicator": float(gross_gains >= s["transaction_costs"]),
    }


def _common_resource(s: NumericMap) -> Mapping[str, Real]:
    open_access = (s["benefit_intercept"] - s["private_cost_intercept"]) / (
        s["benefit_slope"] + s["private_cost_slope"]
    )
    efficient = (s["benefit_intercept"] - s["private_cost_intercept"]) / (
        s["benefit_slope"] + s["private_cost_slope"] + s["external_cost_slope"]
    )
    return {
        "open_access_quantity": open_access,
        "efficient_quantity": efficient,
        "overuse": open_access - efficient,
        "marginal_external_cost_at_efficiency": s["external_cost_slope"] * efficient,
    }


def _public_good(s: NumericMap) -> Mapping[str, Real]:
    social_intercept = s["person_1_benefit_intercept"] + s["person_2_benefit_intercept"]
    social_slope = s["person_1_benefit_slope"] + s["person_2_benefit_slope"]
    quantity = (social_intercept - s["marginal_cost_intercept"]) / (
        social_slope + s["marginal_cost_slope"]
    )
    common_value = social_intercept - social_slope * quantity
    net_benefit = 0.5 * (social_intercept - s["marginal_cost_intercept"]) * quantity
    return {
        "efficient_public_good_quantity": quantity,
        "social_marginal_benefit": common_value,
        "marginal_cost": common_value,
        "total_net_benefit": net_benefit,
    }


def _international_trade(s: NumericMap) -> Mapping[str, Real]:
    autarky_price, autarky_quantity = _linear_equilibrium(
        s["demand_intercept"],
        s["demand_slope"],
        s["supply_intercept"],
        s["supply_slope"],
    )
    domestic_demand = s["demand_intercept"] - s["demand_slope"] * s["world_price"]
    domestic_supply = s["supply_intercept"] + s["supply_slope"] * s["world_price"]
    return {
        "autarky_price": autarky_price,
        "autarky_quantity": autarky_quantity,
        "domestic_demand": domestic_demand,
        "domestic_supply": domestic_supply,
        "imports": max(domestic_demand - domestic_supply, 0.0),
        "exports": max(domestic_supply - domestic_demand, 0.0),
    }


def _tariff(s: NumericMap) -> Mapping[str, Real]:
    free_trade_demand = s["demand_intercept"] - s["demand_slope"] * s["world_price"]
    free_trade_supply = s["supply_intercept"] + s["supply_slope"] * s["world_price"]
    domestic_price = s["world_price"] + s["tariff"]
    tariff_demand = s["demand_intercept"] - s["demand_slope"] * domestic_price
    tariff_supply = s["supply_intercept"] + s["supply_slope"] * domestic_price
    imports_before = max(free_trade_demand - free_trade_supply, 0.0)
    imports_after = max(tariff_demand - tariff_supply, 0.0)
    production_distortion = tariff_supply - free_trade_supply
    consumption_distortion = free_trade_demand - tariff_demand
    return {
        "domestic_price": domestic_price,
        "domestic_demand_after": tariff_demand,
        "domestic_supply_after": tariff_supply,
        "imports_before": imports_before,
        "imports_after": imports_after,
        "import_reduction": imports_before - imports_after,
        "tariff_revenue": s["tariff"] * imports_after,
        "production_distortion": production_distortion,
        "consumption_distortion": consumption_distortion,
        "tariff_deadweight_loss": 0.5 * s["tariff"] * (
            production_distortion + consumption_distortion
        ),
    }


def _choice_under_uncertainty(s: NumericMap) -> Mapping[str, Real]:
    expected_payoff = (
        s["loss_probability"] * s["loss_payoff"]
        + (1.0 - s["loss_probability"]) * s["no_loss_payoff"]
    )
    expected_utility = s["loss_probability"] * sqrt(s["loss_payoff"]) + (
        1.0 - s["loss_probability"]
    ) * sqrt(s["no_loss_payoff"])
    certainty_equivalent = expected_utility**2
    return {
        "expected_payoff": expected_payoff,
        "expected_utility": expected_utility,
        "certainty_equivalent": certainty_equivalent,
        "risk_premium": expected_payoff - certainty_equivalent,
    }


def _social_insurance(s: NumericMap) -> Mapping[str, Real]:
    loss_consumption = (
        s["initial_wealth"] - s["loss"] - s["contribution"] + s["benefit"]
    )
    no_loss_consumption = s["initial_wealth"] - s["contribution"]
    expected_utility = s["loss_probability"] * sqrt(loss_consumption) + (
        1.0 - s["loss_probability"]
    ) * sqrt(no_loss_consumption)
    return {
        "loss_state_consumption": loss_consumption,
        "no_loss_state_consumption": no_loss_consumption,
        "consumption_gap": no_loss_consumption - loss_consumption,
        "expected_utility": expected_utility,
    }


def _adverse_selection(s: NumericMap) -> Mapping[str, Real]:
    high_fair = s["high_risk_probability"] * s["loss_cost"]
    low_fair = s["low_risk_probability"] * s["loss_cost"]
    pooled = s["high_risk_share"] * high_fair + (1.0 - s["high_risk_share"]) * low_fair
    remaining_low_share = (1.0 - s["high_risk_share"]) * (1.0 - s["low_risk_exit_rate"])
    remaining_total = s["high_risk_share"] + remaining_low_share
    post_exit_high_share = s["high_risk_share"] / remaining_total
    return {
        "high_risk_fair_premium": high_fair,
        "low_risk_fair_premium": low_fair,
        "pooling_premium": pooled,
        "low_risk_cross_subsidy": pooled - low_fair,
        "high_risk_discount": high_fair - pooled,
        "post_exit_high_risk_share": post_exit_high_share,
        "post_exit_pooling_premium": (
            post_exit_high_share * high_fair
            + (1.0 - post_exit_high_share) * low_fair
        ),
    }


def _moral_hazard(s: NumericMap) -> Mapping[str, Real]:
    insurer_cost = s["covered_loss_probability"] * s["coverage_rate"] * s["loss_cost"]
    patient_cost = (
        s["covered_loss_probability"] * (1.0 - s["coverage_rate"]) * s["loss_cost"]
    )
    return {
        "expected_insurer_cost": insurer_cost,
        "expected_patient_loss_cost": patient_cost,
        "loss_probability_increase": s["covered_loss_probability"]
        - s["uncovered_loss_probability"],
        "effort_change": s["covered_effort"] - s["uncovered_effort"],
    }


def _equity_efficiency(s: NumericMap) -> Mapping[str, Real]:
    before_gap = abs(s["person_1_before"] - s["person_2_before"])
    after_gap = abs(s["person_1_after"] - s["person_2_after"])
    changes = (
        s["person_1_after"] - s["person_1_before"],
        s["person_2_after"] - s["person_2_before"],
    )
    return {
        "social_welfare_before": s["person_1_before"] + s["person_2_before"],
        "social_welfare_after": s["person_1_after"] + s["person_2_after"],
        "efficiency_gain": sum(changes),
        "equity_gap_reduction": before_gap - after_gap,
        "winners": float(sum(change > 0.0 for change in changes)),
        "losers": float(sum(change < 0.0 for change in changes)),
    }


def _behavioral_economics(s: NumericMap) -> Mapping[str, Real]:
    benchmark_later = s["discount_factor"] ** s["delay_periods"] * s["later_utility"]
    observed_later = s["present_bias"] * benchmark_later
    return {
        "benchmark_later_value": benchmark_later,
        "behavioral_later_value": observed_later,
        "benchmark_later_choice_indicator": float(benchmark_later > s["now_utility"]),
        "observed_now_choice_indicator": float(s["now_utility"] >= observed_later),
        "present_bias_value_gap": benchmark_later - observed_later,
    }


def _health_economics(s: NumericMap) -> Mapping[str, Real]:
    efficient = (s["marginal_benefit_intercept"] - s["marginal_cost_intercept"]) / (
        s["marginal_benefit_slope"] + s["marginal_cost_slope"]
    )
    patient_price = (1.0 - s["insurance_coverage_rate"]) * s["resource_price"]
    patient_quantity = (s["marginal_benefit_intercept"] - patient_price) / s[
        "marginal_benefit_slope"
    ]
    common_value = (
        s["marginal_benefit_intercept"] - s["marginal_benefit_slope"] * efficient
    )
    return {
        "efficient_health_care_quantity": efficient,
        "patient_price": patient_price,
        "patient_demanded_quantity": patient_quantity,
        "insurance_induced_overuse": patient_quantity - efficient,
        "marginal_benefit_at_efficiency": common_value,
        "marginal_cost_at_efficiency": common_value,
    }


_COMMON_MARKET_SETUP = _setup(
    demand_intercept=100.0,
    demand_slope=8.0,
    supply_intercept=10.0,
    supply_slope=7.0,
)


_DEFINITIONS: Final[Mapping[str, _ScenarioDefinition]] = MappingProxyType(
    {
        "supply_demand_intro": _definition(
            "market_price_quantity_readout",
            _setup(
                price=6.0,
                demand_intercept=100.0,
                demand_slope=8.0,
                supply_intercept=10.0,
                supply_slope=7.0,
            ),
            _supply_demand_intro,
            "quantity",
            "price",
            ("demand_curve", "supply_curve", "price_quantity_marker"),
        ),
        "market_equilibrium": _definition(
            "market_clearing_intersection",
            _setup(
                demand_intercept=120.0,
                demand_slope=10.0,
                supply_intercept=0.0,
                supply_slope=5.0,
            ),
            _market_equilibrium,
            "quantity",
            "price",
            ("demand_curve", "supply_curve", "equilibrium_marker"),
        ),
        "demand_curve": _definition(
            "own_price_demand_trace",
            _setup(
                demand_intercept=90.0,
                own_price_slope=6.0,
                own_price=5.0,
                income=40.0,
                income_coefficient=0.5,
                related_good_price=4.0,
                cross_price_coefficient=2.0,
                taste_shift=3.0,
            ),
            _demand_curve,
            "quantity demanded",
            "own price",
            ("demand_curve", "own_price_quantity_point", "held_fixed_shifters"),
        ),
        "supply_curve": _definition(
            "output_price_supply_trace",
            _setup(
                supply_intercept=10.0,
                output_price_slope=6.0,
                output_price=8.0,
                wage=4.0,
                wage_coefficient=2.0,
                rental_price=3.0,
                rental_coefficient=1.0,
                technology=5.0,
                technology_coefficient=4.0,
            ),
            _supply_curve,
            "quantity supplied",
            "output price",
            ("supply_curve", "output_price_quantity_point", "held_fixed_inputs"),
        ),
        "supply_demand_curves": _definition(
            "paired_market_curves",
            _setup(
                price=6.0,
                demand_intercept=96.0,
                demand_slope=8.0,
                supply_intercept=12.0,
                supply_slope=6.0,
            ),
            _supply_demand_intro,
            "quantity",
            "price",
            ("demand_curve", "supply_curve", "common_price_marker"),
        ),
        "comparative_statics": _definition(
            "before_after_demand_shift",
            _setup(
                initial_demand_intercept=100.0,
                new_demand_intercept=120.0,
                demand_slope=10.0,
                supply_intercept=20.0,
                supply_slope=5.0,
            ),
            _comparative_statics,
            "quantity",
            "price",
            (
                "initial_demand_curve",
                "shifted_demand_curve",
                "supply_curve",
                "initial_equilibrium",
                "new_equilibrium",
            ),
        ),
        "price_ceiling_shortage": _definition(
            "binding_ceiling_excess_demand",
            _COMMON_MARKET_SETUP + (("ceiling_price", 4.0),),
            _price_ceiling,
            "quantity",
            "price",
            (
                "demand_curve",
                "supply_curve",
                "equilibrium_marker",
                "price_ceiling_line",
                "shortage_gap",
            ),
        ),
        "price_floor_surplus": _definition(
            "binding_floor_excess_supply",
            _COMMON_MARKET_SETUP + (("floor_price", 8.0),),
            _price_floor,
            "quantity",
            "price",
            (
                "demand_curve",
                "supply_curve",
                "equilibrium_marker",
                "price_floor_line",
                "surplus_gap",
            ),
        ),
        "price_controls": _definition(
            "ceiling_floor_comparison",
            _COMMON_MARKET_SETUP + (("ceiling_price", 4.0), ("floor_price", 8.0)),
            _price_controls,
            "quantity",
            "price",
            (
                "demand_curve",
                "supply_curve",
                "price_ceiling_line",
                "shortage_gap",
                "price_floor_line",
                "surplus_gap",
            ),
        ),
        "consumer_preferences": _definition(
            "ordinal_bundle_ranking",
            _setup(bundle_a_x=6.0, bundle_a_y=4.0, bundle_b_x=4.0, bundle_b_y=5.0),
            _consumer_preferences,
            "good x",
            "good y",
            ("bundle_a", "bundle_b", "indifference_curve", "preferred_bundle_marker"),
        ),
        "utility_representation": _definition(
            "utility_level_representation",
            _setup(bundle_a_x=9.0, bundle_a_y=4.0, bundle_b_x=4.0, bundle_b_y=4.0),
            _utility_representation,
            "good x",
            "good y",
            (
                "bundle_a",
                "bundle_b",
                "utility_indifference_curve",
                "ranking_annotation",
            ),
        ),
        "budget_constraint": _definition(
            "affordable_set_and_intercepts",
            _setup(income=120.0, price_x=10.0, price_y=5.0, bundle_x=8.0, bundle_y=6.0),
            _budget_constraint,
            "x",
            "y",
            (
                "budget_line",
                "affordable_region",
                "candidate_bundle",
                "x_intercept_marker",
                "y_intercept_marker",
            ),
        ),
        "marginal_rate_of_substitution": _definition(
            "indifference_tangent_mrs",
            _setup(quantity_x=4.0, quantity_y=9.0),
            _mrs,
            "good x",
            "good y",
            ("indifference_curve", "tangent_line", "bundle_point", "MRS_readout"),
        ),
        "consumer_choice": _definition(
            "utility_maximizing_tangency",
            _setup(income=100.0, price_x=10.0, price_y=5.0, utility_share_x=0.4),
            _consumer_choice,
            "good x",
            "good y",
            (
                "budget_line",
                "indifference_curve",
                "chosen_bundle",
                "unaffordable_bundle",
            ),
        ),
        "income_substitution_effects": _definition(
            "slutsky_three_bundle_decomposition",
            _setup(
                initial_quantity=10.0, compensated_quantity=14.0, final_quantity=17.0
            ),
            _income_substitution,
            "quantity x",
            "purchasing power",
            (
                "initial_budget_line",
                "compensated_budget_line",
                "final_budget_line",
                "initial_bundle",
                "compensated_bundle",
                "final_bundle",
            ),
        ),
        "own_price_elasticity": _definition(
            "own_price_quantity_response",
            _setup(
                initial_price=10.0,
                new_price=12.0,
                initial_quantity=100.0,
                new_quantity=80.0,
            ),
            _own_price_elasticity,
            "quantity demanded",
            "own price",
            (
                "demand_curve",
                "initial_price_quantity_point",
                "new_price_quantity_point",
                "own_price_elasticity_readout",
            ),
        ),
        "income_elasticity": _definition(
            "income_quantity_classification",
            _setup(
                initial_income=50.0,
                new_income=60.0,
                initial_quantity=40.0,
                new_quantity=48.0,
            ),
            _income_elasticity,
            "income",
            "quantity demanded",
            (
                "income_quantity_curve",
                "initial_income_quantity_point",
                "new_income_quantity_point",
                "normal_inferior_classification",
            ),
        ),
        "cross_price_elasticity": _definition(
            "other_good_price_response",
            _setup(
                initial_price_y=10.0,
                new_price_y=12.0,
                initial_quantity_x=50.0,
                new_quantity_x=55.0,
            ),
            _cross_price_elasticity,
            "price of good y",
            "quantity demanded of good x",
            (
                "good_x_demand_curve",
                "good_y_price_change",
                "quantity_x_change",
                "substitutes_complements_classification",
            ),
        ),
        "production_function": _definition(
            "labor_capital_output_surface_slice",
            _setup(technology=2.0, labor=9.0, capital=16.0, labor_share=0.5),
            _production_function,
            "input",
            "output",
            (
                "production_function_curve",
                "labor_input_marker",
                "capital_input_marker",
                "output_point",
                "marginal_product_tangent",
            ),
        ),
        "labor_market": _definition(
            "labor_supply_demand_equilibrium",
            _setup(
                labor_demand_intercept=100.0,
                labor_demand_slope=4.0,
                labor_supply_intercept=20.0,
                labor_supply_slope=4.0,
            ),
            _labor_market,
            "labor",
            "wage",
            ("labor_demand_curve", "labor_supply_curve", "wage_employment_equilibrium"),
        ),
        "labor_input_market": _definition(
            "derived_labor_demand_mrp",
            _setup(
                wage=30.0,
                marginal_revenue=10.0,
                marginal_product_intercept=8.0,
                marginal_product_slope=0.5,
            ),
            _labor_input,
            "labor input",
            "wage and MRP_L",
            (
                "labor_MRP_curve",
                "wage_line",
                "labor_input_choice",
                "marginal_product_labor_readout",
            ),
        ),
        "capital_input_market": _definition(
            "derived_capital_demand_mrp",
            _setup(
                rental_price=36.0,
                marginal_revenue=12.0,
                marginal_product_intercept=6.0,
                marginal_product_slope=0.25,
            ),
            _capital_input,
            "capital input",
            "rental price and MRP_K",
            (
                "capital_MRP_curve",
                "rental_price_line",
                "capital_input_choice",
                "marginal_product_capital_readout",
            ),
        ),
        "factor_input_markets": _definition(
            "joint_factor_cost_minimization",
            _setup(
                technology=2.0,
                target_output=120.0,
                labor_share=0.5,
                wage=30.0,
                rental_price=20.0,
            ),
            _factor_inputs,
            "labor input",
            "capital input",
            (
                "target_output_isoquant",
                "isocost_line",
                "labor_input_choice",
                "capital_input_choice",
                "cost_minimizing_tangency",
            ),
        ),
        "intertemporal_choice": _definition(
            "present_value_budget_choice",
            _setup(
                income_now=80.0,
                income_later=110.0,
                interest_rate=0.1,
                chosen_consumption_now=100.0,
            ),
            _intertemporal_choice,
            "current consumption c_1",
            "future consumption c_2",
            (
                "intertemporal_budget_line",
                "endowment_point",
                "chosen_consumption_bundle",
                "saving_borrowing_arrow",
            ),
            200.0,
            220.0,
        ),
        "cost_curves": _definition(
            "five_cost_measure_reconciliation",
            _setup(
                fixed_cost=100.0,
                variable_linear_cost=5.0,
                variable_quadratic_cost=1.0,
                output=10.0,
            ),
            _cost_curves,
            "output",
            "cost",
            (
                "fixed_cost_line",
                "variable_cost_curve",
                "total_cost_curve",
                "average_cost_curve",
                "average_variable_cost_curve",
                "marginal_cost_curve",
            ),
            40.0,
            400.0,
        ),
        "perfect_competition": _definition(
            "price_taker_output_profit",
            _setup(
                market_price=50.0,
                marginal_cost_intercept=10.0,
                marginal_cost_slope=2.0,
                fixed_cost=100.0,
            ),
            _perfect_competition,
            "firm output",
            "price and cost",
            (
                "price_equals_MR_line",
                "marginal_cost_curve",
                "competitive_output_choice",
                "profit_area",
            ),
        ),
        "competitive_shutdown": _definition(
            "short_run_avc_shutdown_test",
            _setup(
                market_price=8.0,
                minimum_average_variable_cost=10.0,
                fixed_cost=100.0,
                operating_output=12.0,
                operating_profit=-40.0,
            ),
            _competitive_shutdown,
            "firm output",
            "price and cost",
            (
                "price_line",
                "marginal_cost_curve",
                "average_variable_cost_curve",
                "shutdown_point",
                "zero_output_marker",
            ),
        ),
        "monopoly": _definition(
            "single_price_monopoly_choice",
            _setup(
                demand_intercept=100.0,
                demand_slope=2.0,
                marginal_cost=20.0,
                fixed_cost=100.0,
            ),
            _monopoly,
            "quantity",
            "price revenue and cost",
            (
                "demand_curve",
                "marginal_revenue_curve",
                "marginal_cost_line",
                "monopoly_quantity_marker",
                "monopoly_price_marker",
                "profit_area",
            ),
        ),
        "marginal_revenue": _definition(
            "total_to_marginal_revenue",
            _setup(demand_intercept=80.0, demand_slope=2.0, quantity=15.0),
            _marginal_revenue,
            "quantity",
            "revenue",
            (
                "demand_curve",
                "total_revenue_curve",
                "marginal_revenue_curve",
                "quantity_point",
                "MR_readout",
            ),
        ),
        "price_discrimination": _definition(
            "two_market_equal_mr_allocation",
            _setup(
                demand_1_intercept=100.0,
                demand_1_slope=2.0,
                demand_2_intercept=80.0,
                demand_2_slope=1.0,
                marginal_cost=20.0,
                fixed_cost=100.0,
            ),
            _price_discrimination,
            "segmented quantity",
            "price revenue and cost",
            (
                "market_1_demand_curve",
                "market_2_demand_curve",
                "market_1_MR_curve",
                "market_2_MR_curve",
                "marginal_cost_line",
                "market_1_price_marker",
                "market_2_price_marker",
            ),
        ),
        "oligopoly": _definition(
            "cournot_mutual_best_response",
            _setup(demand_intercept=100.0, demand_slope=1.0, marginal_cost=10.0),
            _oligopoly,
            "firm 1 quantity",
            "firm 2 quantity",
            (
                "firm_1_best_response_curve",
                "firm_2_best_response_curve",
                "mutual_best_response",
                "profit_readout",
            ),
        ),
        "oligopoly_collusion": _definition(
            "cournot_collusive_comparison",
            _setup(demand_intercept=100.0, demand_slope=1.0, marginal_cost=10.0),
            _oligopoly_collusion,
            "firm 1 quantity",
            "firm 2 quantity",
            (
                "firm_1_best_response_curve",
                "firm_2_best_response_curve",
                "cournot_equilibrium",
                "collusive_quantity_marker",
                "collusive_price_marker",
                "joint_profit_comparison",
            ),
        ),
        "strategic_game": _definition(
            "normal_form_payoff_inventory",
            _setup(
                row_aa=3.0,
                column_aa=3.0,
                row_ab=0.0,
                column_ab=5.0,
                row_ba=5.0,
                column_ba=0.0,
                row_bb=1.0,
                column_bb=1.0,
            ),
            _strategic_game,
            "column strategy",
            "row strategy",
            (
                "payoff_matrix",
                "row_player",
                "column_player",
                "strategy_labels",
                "payoff_cells",
            ),
            2.0,
            2.0,
        ),
        "nash_equilibrium": _definition(
            "mutual_best_response_cells",
            _setup(
                row_aa=4.0,
                column_aa=4.0,
                row_ab=0.0,
                column_ab=1.0,
                row_ba=1.0,
                column_ba=0.0,
                row_bb=3.0,
                column_bb=3.0,
            ),
            _nash_equilibrium,
            "column strategy",
            "row strategy",
            (
                "payoff_matrix",
                "row_best_response_marks",
                "column_best_response_marks",
                "nash_equilibrium_cells",
                "unilateral_deviation_check",
            ),
            2.0,
            2.0,
        ),
        "dominant_strategy": _definition(
            "all_rival_actions_dominance_check",
            _setup(
                row_aa=3.0,
                column_aa=3.0,
                row_ab=0.0,
                column_ab=5.0,
                row_ba=5.0,
                column_ba=0.0,
                row_bb=1.0,
                column_bb=1.0,
            ),
            _dominant_strategy,
            "column strategy",
            "row strategy",
            (
                "payoff_matrix",
                "row_payoff_comparisons",
                "column_payoff_comparisons",
                "dominant_strategy_marker",
            ),
            2.0,
            2.0,
        ),
        "consumer_surplus": _definition(
            "buyer_willingness_to_pay_area",
            _setup(choke_price=100.0, market_price=40.0, quantity=30.0),
            _consumer_surplus,
            "quantity",
            "price",
            (
                "demand_curve",
                "market_price_line",
                "traded_quantity_marker",
                "consumer_surplus_area",
            ),
        ),
        "producer_surplus": _definition(
            "seller_price_above_cost_area",
            _setup(supply_intercept_price=10.0, market_price=40.0, quantity=30.0),
            _producer_surplus,
            "quantity",
            "price",
            (
                "supply_curve",
                "market_price_line",
                "traded_quantity_marker",
                "producer_surplus_area",
            ),
        ),
        "total_surplus": _definition(
            "consumer_plus_producer_surplus",
            _setup(consumer_surplus=900.0, producer_surplus=450.0),
            _total_surplus,
            "quantity",
            "price",
            (
                "demand_curve",
                "supply_curve",
                "consumer_surplus_area",
                "producer_surplus_area",
                "total_surplus_readout",
            ),
        ),
        "welfare_surplus": _definition(
            "marginal_benefit_cost_welfare",
            _setup(
                marginal_benefit_intercept=100.0,
                marginal_benefit_slope=2.0,
                marginal_cost_intercept=10.0,
                marginal_cost_slope=1.0,
            ),
            _welfare_surplus,
            "quantity",
            "marginal benefit and cost",
            (
                "marginal_benefit_curve",
                "marginal_cost_curve",
                "efficient_quantity_marker",
                "consumer_surplus_area",
                "producer_surplus_area",
            ),
        ),
        "tax_incidence": _definition(
            "elasticity_tax_burden_split",
            _setup(
                tax=12.0,
                pre_tax_price=50.0,
                absolute_demand_elasticity=2.0,
                supply_elasticity=1.0,
            ),
            _tax_incidence,
            "quantity",
            "price",
            (
                "demand_curve",
                "supply_curve",
                "buyer_price_line",
                "seller_price_line",
                "tax_wedge",
                "buyer_burden_area",
                "seller_burden_area",
            ),
        ),
        "tax_deadweight_loss": _definition(
            "tax_revenue_and_lost_trades",
            _setup(tax=10.0, quantity_before_tax=100.0, quantity_after_tax=80.0),
            _tax_deadweight_loss,
            "quantity",
            "price",
            (
                "demand_curve",
                "supply_curve",
                "tax_wedge",
                "tax_revenue_area",
                "deadweight_loss_area",
            ),
        ),
        "externality": _definition(
            "private_social_quantity_gap",
            _setup(
                benefit_intercept=100.0,
                benefit_slope=2.0,
                private_cost_intercept=10.0,
                private_cost_slope=1.0,
                external_cost_per_unit=15.0,
            ),
            _externality,
            "quantity",
            "marginal benefit and cost",
            (
                "private_cost_curve",
                "social_cost_curve",
                "private_benefit_curve",
                "market_quantity_marker",
                "efficient_quantity_marker",
                "external_cost_wedge",
            ),
        ),
        "coase_bargaining": _definition(
            "property_rights_bargaining_range",
            _setup(
                abatement_benefit_intercept=60.0,
                abatement_benefit_slope=3.0,
                abatement_cost_intercept=10.0,
                abatement_cost_slope=2.0,
                transaction_costs=8.0,
            ),
            _coase_bargaining,
            "abatement",
            "marginal benefit and cost",
            (
                "abatement_benefit_curve",
                "abatement_cost_curve",
                "efficient_abatement_marker",
                "bargaining_range",
                "transaction_cost_annotation",
            ),
        ),
        "common_resource": _definition(
            "open_access_overuse_gap",
            _setup(
                benefit_intercept=100.0,
                benefit_slope=2.0,
                private_cost_intercept=10.0,
                private_cost_slope=1.0,
                external_cost_slope=1.0,
            ),
            _common_resource,
            "resource use",
            "marginal benefit and cost",
            (
                "private_cost_curve",
                "social_cost_curve",
                "benefit_curve",
                "open_access_quantity_marker",
                "efficient_quantity_marker",
                "overuse_gap",
            ),
        ),
        "public_good": _definition(
            "vertical_marginal_benefit_sum",
            _setup(
                person_1_benefit_intercept=40.0,
                person_1_benefit_slope=1.0,
                person_2_benefit_intercept=30.0,
                person_2_benefit_slope=0.5,
                marginal_cost_intercept=10.0,
                marginal_cost_slope=0.5,
            ),
            _public_good,
            "public good quantity",
            "marginal benefit and cost",
            (
                "person_1_benefit_curve",
                "person_2_benefit_curve",
                "social_marginal_benefit_curve",
                "marginal_cost_curve",
                "efficient_public_good_marker",
            ),
        ),
        "international_trade": _definition(
            "small_open_economy_imports_exports",
            _setup(
                demand_intercept=100.0,
                demand_slope=4.0,
                supply_intercept=10.0,
                supply_slope=2.0,
                world_price=10.0,
            ),
            _international_trade,
            "domestic quantity",
            "price",
            (
                "domestic_demand_curve",
                "domestic_supply_curve",
                "world_price_line",
                "autarky_equilibrium",
                "imports_exports_gap",
            ),
        ),
        "tariff": _definition(
            "small_country_tariff_import_reduction",
            _setup(
                demand_intercept=100.0,
                demand_slope=4.0,
                supply_intercept=10.0,
                supply_slope=2.0,
                world_price=10.0,
                tariff=3.0,
            ),
            _tariff,
            "domestic quantity",
            "price",
            (
                "domestic_demand_curve",
                "domestic_supply_curve",
                "world_price_line",
                "tariff_price_line",
                "free_trade_import_gap",
                "tariff_import_gap",
                "tariff_revenue_area",
                "tariff_deadweight_loss_areas",
            ),
        ),
        "choice_under_uncertainty": _definition(
            "state_probability_expected_utility",
            _setup(loss_probability=0.25, loss_payoff=25.0, no_loss_payoff=100.0),
            _choice_under_uncertainty,
            "state payoff",
            "utility",
            (
                "loss_state_point",
                "no_loss_state_point",
                "probability_weights",
                "expected_utility_point",
                "certainty_equivalent_marker",
            ),
        ),
        "social_insurance": _definition(
            "insurance_consumption_smoothing",
            _setup(
                loss_probability=0.2,
                initial_wealth=100.0,
                loss=60.0,
                contribution=10.0,
                benefit=40.0,
            ),
            _social_insurance,
            "state",
            "consumption",
            (
                "loss_state_point",
                "no_loss_state_point",
                "contribution_arrow",
                "benefit_arrow",
                "consumption_smoothing_gap",
            ),
        ),
        "adverse_selection": _definition(
            "hidden_risk_pooling_premium",
            _setup(
                high_risk_share=0.4,
                high_risk_probability=0.3,
                low_risk_probability=0.1,
                loss_cost=1000.0,
                low_risk_exit_rate=0.5,
            ),
            _adverse_selection,
            "risk type",
            "premium and expected cost",
            (
                "high_risk_group",
                "low_risk_group",
                "private_information_marker",
                "pooling_premium_line",
                "enrollment_choice",
            ),
            2.0,
            400.0,
        ),
        "moral_hazard": _definition(
            "hidden_action_coverage_incentive",
            _setup(
                uncovered_loss_probability=0.1,
                covered_loss_probability=0.2,
                uncovered_effort=0.8,
                covered_effort=0.4,
                coverage_rate=0.8,
                loss_cost=1000.0,
            ),
            _moral_hazard,
            "coverage",
            "effort and loss probability",
            (
                "uncovered_effort_point",
                "covered_effort_point",
                "private_action_marker",
                "loss_probability_curve",
                "coverage_incentive_arrow",
            ),
            1.0,
            1.0,
        ),
        "equity_efficiency": _definition(
            "distributional_winners_losers",
            _setup(
                person_1_before=80.0,
                person_2_before=20.0,
                person_1_after=65.0,
                person_2_after=35.0,
            ),
            _equity_efficiency,
            "individual 1 utility",
            "individual 2 utility",
            (
                "utility_possibility_frontier",
                "before_distribution_point",
                "after_distribution_point",
                "social_welfare_curve",
                "winners_losers_annotation",
            ),
        ),
        "behavioral_economics": _definition(
            "present_bias_benchmark_choice",
            _setup(
                present_bias=0.6,
                discount_factor=0.9,
                delay_periods=1.0,
                now_utility=50.0,
                later_utility=80.0,
            ),
            _behavioral_economics,
            "time",
            "discounted utility",
            (
                "now_choice_point",
                "later_choice_point",
                "benchmark_discount_curve",
                "behavioral_discount_curve",
                "observed_choice_marker",
                "bias_gap",
            ),
        ),
        "health_economics": _definition(
            "insured_patient_social_quantity_gap",
            _setup(
                marginal_benefit_intercept=120.0,
                marginal_benefit_slope=4.0,
                marginal_cost_intercept=20.0,
                marginal_cost_slope=2.0,
                resource_price=50.0,
                insurance_coverage_rate=0.8,
            ),
            _health_economics,
            "health care quantity",
            "patient price and marginal value",
            (
                "marginal_health_benefit_curve",
                "marginal_social_cost_curve",
                "patient_price_line",
                "efficient_quantity_marker",
                "patient_demanded_quantity_marker",
                "insurance_overuse_gap",
            ),
        ),
    }
)

ECONOMICS_MODEL_SCENARIO_DEFINITIONS = _DEFINITIONS


def _animation_states(
    model_id: str,
    objects: tuple[SceneObject, ...],
    setup: NumericMap,
    calculation: NumericMap,
    results: NumericMap,
    example_tokens: tuple[str, ...],
    visible_tokens: tuple[str, ...],
    result_fields: tuple[str, ...],
) -> tuple[AnimationState, ...]:
    object_ids = tuple(obj.object_id for obj in objects)
    midpoint = max(1, (len(object_ids) + 1) // 2)
    return (
        AnimationState(
            state_id=f"{model_id}:setup",
            phase="setup",
            progress=0.0,
            values=setup,
            visible_object_ids=object_ids[:1],
            visible_evidence_tokens=example_tokens[:1],
            result_fields=(),
        ),
        AnimationState(
            state_id=f"{model_id}:change",
            phase="change",
            progress=0.5,
            values=calculation,
            visible_object_ids=object_ids[:midpoint],
            visible_evidence_tokens=example_tokens,
            result_fields=tuple(calculation),
        ),
        AnimationState(
            state_id=f"{model_id}:result",
            phase="result",
            progress=1.0,
            values=results,
            visible_object_ids=object_ids,
            visible_evidence_tokens=visible_tokens,
            result_fields=result_fields,
        ),
    )


def _build_from_definition(
    model_id: str,
    definition: _ScenarioDefinition,
    setup_overrides: Mapping[str, Real] | None,
) -> EconomicsModelScenario:
    setup_values: dict[str, Real] = dict(definition.setup)
    if setup_overrides is not None:
        if not isinstance(setup_overrides, Mapping):
            raise TypeError("setup_overrides must be a mapping")
        unknown = set(setup_overrides) - set(setup_values)
        if unknown:
            unknown_text = ", ".join(sorted(str(key) for key in unknown))
            raise ValueError(f"unknown setup fields for {model_id}: {unknown_text}")
        setup_values.update(setup_overrides)
    setup = _freeze_numeric(setup_values, "setup")
    try:
        computed_values = definition.calculator(setup)
        calculation = _freeze_numeric(computed_values, "calculation")
        results = _freeze_numeric(computed_values, "results")
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"invalid numeric setup for {model_id}: {exc}") from exc

    spec = ECONOMICS_MODEL_REGISTRY[model_id]
    visible_tokens = _ordered_union(
        spec.required_example_tokens, spec.required_figure_tokens
    )
    result_fields = tuple(results)
    animation_states = _animation_states(
        model_id,
        definition.objects,
        setup,
        calculation,
        results,
        spec.required_example_tokens,
        visible_tokens,
        result_fields,
    )
    return EconomicsModelScenario(
        model_id=model_id,
        mode=definition.mode,
        setup=setup,
        calculation=calculation,
        results=results,
        animation_states=animation_states,
        axes=definition.axes,
        objects=definition.objects,
        required_example_tokens=spec.required_example_tokens,
        required_figure_tokens=spec.required_figure_tokens,
        visible_evidence_tokens=visible_tokens,
    )


def build_economics_model_scenario(
    model_id: str,
    setup_overrides: Mapping[str, Real] | None = None,
) -> EconomicsModelScenario:
    """Build one scenario, recalculating results from optional overrides."""

    if not isinstance(model_id, str):
        raise TypeError("economics model_id must be a string")
    definition = _DEFINITIONS.get(model_id)
    if definition is None:
        raise ValueError(f"Unsupported economics model_id {model_id!r}")
    return _build_from_definition(model_id, definition, setup_overrides)


def recompute_economics_model_scenario(
    scenario_or_model_id: str | EconomicsModelScenario | Mapping[str, object],
    setup: Mapping[str, Real] | None = None,
) -> EconomicsModelScenario:
    """Rebuild from setup while ignoring any supplied stale result fields."""

    if isinstance(scenario_or_model_id, str):
        return build_economics_model_scenario(scenario_or_model_id, setup)
    if setup is not None:
        raise ValueError("setup is only accepted when recomputing by model_id")
    if not isinstance(scenario_or_model_id, Mapping):
        raise TypeError("scenario_or_model_id must be a model id or scenario mapping")
    try:
        model_id = scenario_or_model_id["model_id"]
        source_setup = scenario_or_model_id["setup"]
    except KeyError as exc:
        raise ValueError("scenario mapping must contain model_id and setup") from exc
    if not isinstance(model_id, str):
        raise TypeError("scenario model_id must be a string")
    if not isinstance(source_setup, Mapping):
        raise TypeError("scenario setup must be a mapping")
    return build_economics_model_scenario(model_id, source_setup)  # type: ignore[arg-type]


def build_all_economics_model_scenarios() -> Mapping[str, EconomicsModelScenario]:
    """Return a fresh immutable mapping of all default scenarios."""

    return _build_registry()


def get_economics_model_scenario(model_id: str) -> EconomicsModelScenario:
    """Return the immutable default scenario for an exact model ID."""

    if not isinstance(model_id, str):
        raise TypeError("economics model_id must be a string")
    try:
        return ECONOMICS_MODEL_SCENARIO_REGISTRY[model_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported economics model_id {model_id!r}") from exc


def _build_registry() -> Mapping[str, EconomicsModelScenario]:
    expected = set(ECONOMICS_MODEL_REGISTRY)
    actual = set(_DEFINITIONS)
    if expected != actual:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise RuntimeError(
            f"economics scenario coverage mismatch: missing={missing}, extra={extra}"
        )

    scenarios = {
        model_id: _build_from_definition(model_id, _DEFINITIONS[model_id], None)
        for model_id in ECONOMICS_MODEL_REGISTRY
    }
    modes = [scenario.mode for scenario in scenarios.values()]
    if len(modes) != len(set(modes)):
        raise RuntimeError("economics scenario modes must be unique")
    return MappingProxyType(scenarios)


ECONOMICS_MODEL_SCENARIO_REGISTRY: Final[Mapping[str, EconomicsModelScenario]] = (
    _build_registry()
)
ECONOMICS_MODEL_SCENARIOS = ECONOMICS_MODEL_SCENARIO_REGISTRY
ECONOMICS_SCENARIOS = ECONOMICS_MODEL_SCENARIO_REGISTRY


__all__ = [
    "AnimationState",
    "AxisSpec",
    "ECONOMICS_MODEL_SCENARIO_DEFINITIONS",
    "ECONOMICS_MODEL_SCENARIO_REGISTRY",
    "ECONOMICS_MODEL_SCENARIOS",
    "ECONOMICS_SCENARIOS",
    "EconomicsModelScenario",
    "EconomicsScenarioDefinition",
    "NumericScenarioSchema",
    "SceneObject",
    "build_all_economics_model_scenarios",
    "build_economics_model_scenario",
    "economics_numeric_evidence_fingerprint",
    "get_economics_model_scenario",
    "recompute_economics_model_scenario",
]

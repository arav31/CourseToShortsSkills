"""Data-driven TikZ bodies for exact physics and economics scenarios.

The renderer is intentionally independent of ``stem_course`` and of the model
registries.  It consumes only a scenario mapping and its selected visual kind,
which keeps it reusable in notes generation, previews, and focused tests.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real
import re
from typing import Callable, Final


PHYSICS_VISUAL_KINDS: Final[frozenset[str]] = frozenset(
    {
        "physics_force",
        "physics_kinematics",
        "physics_vector",
        "physics_center_of_mass",
        "physics_rocket",
        "physics_mass_transfer",
        "physics_ode",
        "physics_work",
        "physics_energy",
        "physics_momentum",
        "physics_potential",
        "physics_circular",
        "physics_rotation",
        "physics_recoil",
        "physics_wave",
    }
)

ECONOMICS_VISUAL_KINDS: Final[frozenset[str]] = frozenset(
    {
        "econ_budget",
        "econ_curve",
        "econ_elasticity",
        "econ_supply_demand",
        "econ_tax_wedge",
        "econ_production_isoquants",
        "game_payoff",
    }
)

MODEL_SCENARIO_VISUAL_KINDS: Final[frozenset[str]] = (
    PHYSICS_VISUAL_KINDS | ECONOMICS_VISUAL_KINDS
)


@dataclass(frozen=True)
class _FigureContext:
    model_id: str
    visual_kind: str
    setup: Mapping[str, object]
    results: Mapping[str, object]
    figure_tokens: tuple[str, ...]
    evidence_tokens: tuple[str, ...]
    horizontal_label: str
    vertical_label: str


_MAX_LEGEND_ROWS: Final[int] = 4
_DRAWING_RIGHT_EDGE: Final[float] = 5.9
_RIGHT_ANNOTATION_X: Final[float] = 5.85

_MODEL_AXIS_LABELS: Final[Mapping[str, tuple[str, str]]] = {
    "kinematics_position_velocity": ("time", "position and velocity"),
    "kinematics_acceleration": ("time", "velocity and acceleration"),
    "kinematics_2d": ("x", "y"),
    "projectile_motion": ("x", "y"),
    "impulse_momentum": ("time", "force"),
    "potential_energy": ("position x", "potential energy U(x)"),
    "potential_energy_diagram": ("position x", "potential energy U(x)"),
    "point_particle_angular_momentum": ("x", "y"),
    "angular_impulse": ("time", "torque"),
    "relative_velocity": ("velocity component v_x", "velocity component v_y"),
    "ordinary_differential_equation": ("time", "state"),
    "unit_vector": ("x component", "y component"),
    "vectors": ("x component", "y component"),
    "production_function": ("labor L (capital K fixed)", "output q"),
}

_MODEL_QUANTITY_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "kinematics_position_velocity": (
        "initial_velocity",
        "acceleration",
        "final_velocity",
        "final_position",
    ),
    "kinematics_acceleration": (
        "initial_velocity",
        "acceleration",
        "final_velocity",
        "final_position",
    ),
    "kinematics_1d": (
        "initial_position",
        "initial_velocity",
        "final_position",
        "final_velocity",
    ),
    "projectile_motion": (
        "initial_speed",
        "launch_angle",
        "final_position_vector",
        "final_velocity_vector",
    ),
    "continuous_mass_transfer": (
        "mass_flow_rate",
        "inlet_velocity",
        "outlet_velocity",
        "external_force",
    ),
    "continuous_mass_accumulation": (
        "initial_mass",
        "inlet_mass_flow",
        "outlet_mass_flow",
        "final_mass",
    ),
    "potential_energy": ("curvature", "position", "conservative_force"),
    "potential_energy_diagram": (
        "floor_energy",
        "total_energy",
        "turning_points",
    ),
    "rigid_body_motion": (
        "reference_velocity",
        "angular_velocity",
        "material_point_velocity",
    ),
    "rigid_body_angular_momentum": (
        "inertia_tensor_diagonal",
        "angular_velocity_vector",
        "angular_momentum_vector",
        "rotational_kinetic_energy",
    ),
    "market_equilibrium": (
        "demand_intercept",
        "supply_intercept",
        "equilibrium_price",
        "equilibrium_quantity",
    ),
    "production_function": (
        "labor",
        "capital",
        "output",
        "marginal_product_labor",
    ),
    "monopoly": (
        "marginal_cost",
        "monopoly_quantity",
        "monopoly_price",
        "profit",
    ),
    "public_good": (
        "efficient_public_good_quantity",
        "social_marginal_benefit",
        "marginal_cost",
        "total_net_benefit",
    ),
    "strategic_game": ("largest_row_payoff", "largest_column_payoff"),
    "nash_equilibrium": (
        "nash_equilibrium_count",
        "largest_nash_total_payoff",
        "unilateral_deviation_gain_at_aa",
    ),
    "dominant_strategy": (
        "row_dominant_strategy_index",
        "column_dominant_strategy_index",
        "dominant_equilibrium_total_payoff",
    ),
    "tax_incidence": ("tax", "buyer_price", "seller_price", "tax_wedge"),
    "tax_deadweight_loss": (
        "tax",
        "quantity_before_tax",
        "quantity_after_tax",
        "DWL",
    ),
    "international_trade": (
        "world_price",
        "domestic_demand",
        "domestic_supply",
        "imports",
    ),
}

_QUANTITY_LABELS: Final[Mapping[str, str]] = {
    "initial_position": r"$x_0$",
    "initial_velocity": r"$v_0$",
    "acceleration": r"$a$",
    "elapsed_time": r"$t$",
    "final_position": "Final position",
    "final_velocity": "Final velocity",
    "initial_position_vector": r"$\mathbf{x}_0$",
    "initial_velocity_vector": r"$\mathbf{v}_0$",
    "acceleration_vector": r"$\mathbf{a}$",
    "final_position_vector": r"$\mathbf{x}_f$",
    "final_velocity_vector": r"$\mathbf{v}_f$",
    "initial_speed": r"$v_0$",
    "final_speed": r"$v_f$",
    "launch_angle": r"$\theta$",
    "mass_flow_rate": r"$\dot m$",
    "inlet_mass_flow": r"$\dot m_{\mathrm{in}}$",
    "outlet_mass_flow": r"$\dot m_{\mathrm{out}}$",
    "net_mass_flow": r"$\dot M_{\mathrm{cv}}$",
    "inlet_velocity": r"$\mathbf{v}_{\mathrm{in}}$",
    "outlet_velocity": r"$\mathbf{v}_{\mathrm{out}}$",
    "external_force": r"$\mathbf{F}_{\mathrm{ext}}$",
    "curvature": r"$k$",
    "position": r"$x$",
    "conservative_force": r"$F(x)$",
    "floor_energy": r"$U_{\min}$",
    "total_energy": r"$E$",
    "turning_points": "Turning points",
    "reference_velocity": r"$\mathbf{v}_O$",
    "angular_velocity": r"$\boldsymbol{\omega}$",
    "material_point_velocity": r"$\mathbf{v}_P$",
    "inertia_tensor_diagonal": "Principal inertias",
    "angular_velocity_vector": r"$\boldsymbol{\omega}$",
    "angular_momentum_vector": r"$\mathbf{L}$",
    "rotational_kinetic_energy": r"$K_{\mathrm{rot}}$",
    "demand_intercept": "Demand intercept",
    "supply_intercept": "Supply intercept",
    "equilibrium_price": r"$P^*$",
    "equilibrium_quantity": r"$Q^*$",
    "labor": r"$L$",
    "capital": r"$K$",
    "output": r"$Q$",
    "marginal_product_labor": r"$MP_L$",
    "marginal_cost": r"$MC$",
    "monopoly_quantity": r"$q_m$",
    "monopoly_price": r"$P_m$",
    "profit": r"$\pi$",
    "efficient_public_good_quantity": r"$G^*$",
    "social_marginal_benefit": r"$SMB$",
    "total_net_benefit": "Total net benefit",
    "largest_row_payoff": "Largest row payoff",
    "largest_column_payoff": "Largest column payoff",
    "nash_equilibrium_count": "Nash equilibria",
    "largest_nash_total_payoff": "Largest equilibrium payoff",
    "unilateral_deviation_gain_at_aa": "Deviation gain at (A, A)",
    "row_dominant_strategy_index": "Row dominant strategy",
    "column_dominant_strategy_index": "Column dominant strategy",
    "dominant_equilibrium_total_payoff": "Dominant-equilibrium payoff",
    "tax": r"$t$",
    "buyer_price": r"$P_b$",
    "seller_price": r"$P_s$",
    "tax_wedge": "Tax wedge",
    "quantity_before_tax": r"$Q_0$",
    "quantity_after_tax": r"$Q_t$",
    "DWL": r"$DWL$",
    "world_price": r"$P_w$",
    "domestic_demand": r"$Q_d$",
    "domestic_supply": r"$Q_s$",
    "imports": "Imports",
    "mass": r"$m$",
    "radius": r"$R$",
    "gravity": r"$g$",
    "work": r"$W$",
    "velocity": r"$\mathbf{v}$",
    "momentum_vector": r"$\mathbf{p}$",
    "momentum_magnitude": r"$|\mathbf{p}|$",
    "moment_of_inertia": r"$I$",
    "angular_speed": r"$\omega$",
    "final_angular_speed": r"$\omega_f$",
    "frequency": r"$f$",
    "wavelength": r"$\lambda$",
    "wave_speed": r"$v_{\mathrm{wave}}$",
    "period": r"$T$",
    "income": r"$I$",
    "price_x": r"$p_x$",
    "price_y": r"$p_y$",
    "x_intercept": r"$I/p_x$",
    "y_intercept": r"$I/p_y$",
    "MRS": r"$MRS$",
    "CS": r"$CS$",
    "PS": r"$PS$",
    "TS": r"$TS$",
}

_INLINE_MATH_LABELS: Final[Mapping[str, str]] = {
    "U(x)": r"$U(x)$",
    "c_1": r"$c_1$",
    "c_2": r"$c_2$",
    "labor L (capital K fixed)": r"labor $L$ (capital $K$ fixed)",
    "MRP_L": r"$MRP_L$",
    "MRP_K": r"$MRP_K$",
    "output q": r"output $q$",
    "v_x": r"$v_x$",
    "v_y": r"$v_y$",
}

_LEGEND_EXCLUDED_TERMS: Final[frozenset[str]] = frozenset(
    {
        "binding",
        "boolean",
        "check",
        "conserved",
        "continuous",
        "different",
        "indicator",
        "model",
        "opposes",
        "provenance",
        "renderer",
        "residual",
        "satisfied",
    }
)

_PREFERRED_QUANTITY_TERMS: Final[Mapping[str, int]] = {
    "final": 18,
    "equilibrium": 18,
    "efficient": 16,
    "chosen": 15,
    "change": 14,
    "quantity": 13,
    "price": 13,
    "velocity": 13,
    "speed": 13,
    "force": 12,
    "energy": 12,
    "momentum": 12,
    "output": 12,
    "profit": 12,
    "surplus": 12,
    "work": 11,
    "acceleration": 11,
    "mass": 10,
    "time": 9,
    "income": 9,
    "labor": 9,
    "capital": 9,
    "tax": 9,
}


def latex_escape_label(value: object) -> str:
    """Escape an arbitrary value for a visible LaTeX text label."""

    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "%": r"\%",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
    }
    return "".join(replacements.get(character, character) for character in str(value))


def normalize_figure_token(value: object) -> str:
    """Normalize source tokens and escaped TikZ text to comparable words."""

    text = str(value)
    for escaped, literal in (
        (r"\textbackslash{}", " "),
        (r"\textasciicircum{}", "^"),
        (r"\textasciitilde{}", "~"),
        (r"\_", "_"),
        (r"\%", "%"),
        (r"\&", "&"),
        (r"\#", "#"),
        (r"\$", "$"),
        (r"\{", "{"),
        (r"\}", "}"),
    ):
        text = text.replace(escaped, literal)
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def figure_token_is_represented(tikz_body: str, token: str) -> bool:
    """Return whether a token appears as a normalized contiguous phrase."""

    needle = normalize_figure_token(token)
    haystack = normalize_figure_token(tikz_body)
    return bool(needle) and f" {needle} " in f" {haystack} "


def _as_token_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise TypeError(f"scenario {field_name} must be a sequence of strings")
    tokens = tuple(value)
    if any(not isinstance(token, str) or not token for token in tokens):
        raise ValueError(f"scenario {field_name} must contain nonempty strings")
    return tokens


def _ordered_union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token for group in groups for token in group))


def _axis_labels(
    scenario: Mapping[str, object], model_id: str
) -> tuple[str, str]:
    fallback = _MODEL_AXIS_LABELS.get(model_id, ("horizontal", "vertical"))
    axes = scenario.get("axes", scenario.get("axis_specs", ()))
    if isinstance(axes, Sequence) and not isinstance(axes, (str, bytes)) and axes:
        axis = axes[0]
        if isinstance(axis, Mapping):
            horizontal = axis.get("horizontal_label", fallback[0])
            vertical = axis.get("vertical_label", fallback[1])
        else:
            horizontal = getattr(axis, "horizontal_label", fallback[0])
            vertical = getattr(axis, "vertical_label", fallback[1])
        authored = str(horizontal), str(vertical)
        if model_id == "production_function" and authored == ("input", "output"):
            return fallback
        return authored
    return fallback


def _context(scenario: Mapping[str, object], visual_kind: str) -> _FigureContext:
    if not isinstance(scenario, Mapping):
        raise TypeError("scenario must be a mapping")
    if visual_kind not in MODEL_SCENARIO_VISUAL_KINDS:
        raise ValueError(f"unsupported model-scenario visual kind: {visual_kind!r}")

    model_id = scenario.get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("scenario model_id must be a nonempty string")
    setup = scenario.get("setup", scenario.get("numeric_setup"))
    results = scenario.get(
        "results", scenario.get("result", scenario.get("result_fields"))
    )
    if not isinstance(setup, Mapping) or not setup:
        raise ValueError("scenario setup must be a nonempty mapping")
    if not isinstance(results, Mapping) or not results:
        raise ValueError("scenario results must be a nonempty mapping")

    figure_tokens = _as_token_tuple(
        scenario.get("required_figure_tokens", ()), "required_figure_tokens"
    )
    if not figure_tokens:
        raise ValueError("scenario required_figure_tokens must not be empty")
    raw_evidence = scenario.get(
        "visible_evidence_tokens", scenario.get("exact_visible_evidence_tokens")
    )
    if raw_evidence is None:
        example_tokens = _as_token_tuple(
            scenario.get("required_example_tokens", ()), "required_example_tokens"
        )
        evidence_tokens = _ordered_union(example_tokens, figure_tokens)
    else:
        evidence_tokens = _as_token_tuple(raw_evidence, "visible_evidence_tokens")
    missing_evidence = [token for token in figure_tokens if token not in evidence_tokens]
    if missing_evidence:
        raise ValueError(
            "scenario visible_evidence_tokens omit required figure tokens: "
            + ", ".join(missing_evidence)
        )

    horizontal, vertical = _axis_labels(scenario, model_id)
    return _FigureContext(
        model_id=model_id,
        visual_kind=visual_kind,
        setup=setup,
        results=results,
        figure_tokens=figure_tokens,
        evidence_tokens=evidence_tokens,
        horizontal_label=horizontal,
        vertical_label=vertical,
    )


def _format_number(value: Real) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("scenario labels require finite numeric values")
    if number == 0.0:
        number = 0.0
    return format(number, ".7g")


def _format_display_number(value: Real, *, unit: str | None = None) -> str:
    """Compact a number for a worked-values panel without changing its source."""

    if isinstance(value, int):
        rendered = str(value)
    elif isinstance(value, Fraction) and value.denominator == 1:
        rendered = str(value.numerator)
    elif (
        isinstance(value, Fraction)
        and abs(value.numerator) <= 9999
        and value.denominator <= 1000
    ):
        rendered = f"{value.numerator}/{value.denominator}"
    else:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("scenario labels require finite numeric values")
        if number.is_integer():
            rendered = str(int(value))
        else:
            if number == 0.0:
                number = 0.0
            rendered = format(number, ".4g")

    suffix = unit.strip() if unit is not None else ""
    return f"{rendered} {suffix}" if suffix else rendered


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Real):
        return _format_number(value)
    if isinstance(value, Mapping):
        return "{" + ", ".join(
            f"{key}: {_format_value(item)}" for key, item in value.items()
        ) + "}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "(" + ", ".join(_format_value(item) for item in value) + ")"
    return str(value)


def _label(value: object) -> str:
    return latex_escape_label(value)


def _natural_text_label(value: object) -> str:
    """Escape prose while typesetting the few inline notation tokens as math."""

    text = str(value)
    pattern = re.compile(
        "|".join(
            re.escape(token)
            for token in sorted(_INLINE_MATH_LABELS, key=len, reverse=True)
        )
    )
    rendered: list[str] = []
    cursor = 0
    for match in pattern.finditer(text):
        rendered.append(latex_escape_label(text[cursor : match.start()].replace("_", " ")))
        rendered.append(_INLINE_MATH_LABELS[match.group(0)])
        cursor = match.end()
    rendered.append(latex_escape_label(text[cursor:].replace("_", " ")))
    return "".join(rendered)


def _quantity_label(key: object, *, model_id: str) -> str:
    text = str(key)
    if model_id == "production_function" and text == "output":
        return r"$q$"
    if text in _QUANTITY_LABELS:
        return _QUANTITY_LABELS[text]

    acronyms = {
        "ac": "AC",
        "avc": "AVC",
        "cs": "CS",
        "dwl": "DWL",
        "fc": "FC",
        "ie": "IE",
        "mc": "MC",
        "mrs": "MRS",
        "mrp": "MRP",
        "ps": "PS",
        "se": "SE",
        "tc": "TC",
        "tr": "TR",
        "ts": "TS",
        "vc": "VC",
    }
    words = [acronyms.get(word.casefold(), word.casefold()) for word in text.split("_")]
    label = " ".join(words)
    if label:
        label = label[0].upper() + label[1:]
    return latex_escape_label(label)


def _math_value(value: object, *, depth: int = 0) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Real):
        return _format_display_number(value)
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and depth < 2
        and 0 < len(value) <= 4
    ):
        items = [_math_value(item, depth=depth + 1) for item in value]
        if any(item is None for item in items):
            return None
        rendered = "(" + ", ".join(item for item in items if item is not None) + ")"
        return rendered if len(rendered) <= 48 else None
    return None


def _legend_value(value: object) -> str | None:
    math_value = _math_value(value)
    if math_value is not None:
        return f"${math_value}$"
    if isinstance(value, str) and value and len(value) <= 32:
        return latex_escape_label(value.replace("_", " "))
    return None


def _quantity_score(ctx: _FigureContext, key: str, *, is_result: bool) -> int:
    words = set(normalize_figure_token(key).split())
    context_words = set(
        normalize_figure_token(
            " ".join(
                (*ctx.figure_tokens, ctx.horizontal_label, ctx.vertical_label)
            )
        ).split()
    )
    score = 8 * len(words & context_words) + (5 if is_result else 0)
    score += sum(_PREFERRED_QUANTITY_TERMS.get(word, 0) for word in words)
    if words & {"coefficient", "intercept", "slope"}:
        score -= 8
    return score


def _quantity_candidates(
    ctx: _FigureContext, values: Mapping[str, object], *, is_result: bool
) -> list[tuple[int, str, str]]:
    candidates: list[tuple[int, str, str]] = []
    for raw_key, value in values.items():
        key = str(raw_key)
        words = set(normalize_figure_token(key).split())
        if words & _LEGEND_EXCLUDED_TERMS:
            continue
        rendered_value = _legend_value(value)
        if rendered_value is None:
            continue
        candidates.append(
            (_quantity_score(ctx, key, is_result=is_result), key, rendered_value)
        )
    return sorted(candidates, key=lambda item: (-item[0], item[1]))


def _selected_quantities(ctx: _FigureContext) -> list[tuple[str, str]]:
    explicit_fields = _MODEL_QUANTITY_FIELDS.get(ctx.model_id)
    if explicit_fields is not None:
        selected: list[tuple[str, str]] = []
        for key in explicit_fields:
            for values in (ctx.setup, ctx.results):
                if key not in values:
                    continue
                rendered_value = _legend_value(values[key])
                if rendered_value is not None:
                    selected.append((key, rendered_value))
                break
        return selected[:_MAX_LEGEND_ROWS]

    setup = _quantity_candidates(ctx, ctx.setup, is_result=False)
    results = _quantity_candidates(ctx, ctx.results, is_result=True)
    chosen = setup[:2] + results[:2]
    if len(chosen) < _MAX_LEGEND_ROWS:
        chosen_keys = {key for _, key, _ in chosen}
        remaining = sorted(
            (item for item in (*setup[2:], *results[2:]) if item[1] not in chosen_keys),
            key=lambda item: (-item[0], item[1]),
        )
        chosen.extend(remaining[: _MAX_LEGEND_ROWS - len(chosen)])
    return [(key, rendered_value) for _, key, rendered_value in chosen]


def _pick(ctx: _FigureContext, *needles: str, fallback: str) -> str:
    normalized_needles = tuple(normalize_figure_token(needle) for needle in needles)
    for token in ctx.figure_tokens:
        normalized = normalize_figure_token(token)
        if any(needle and needle in normalized for needle in normalized_needles):
            return _natural_text_label(token)
    return _natural_text_label(fallback)


def _axes(ctx: _FigureContext) -> str:
    return (
        rf"\draw[->,thick] (0,0) -- (5.9,0) node[right] "
        rf"{{{_natural_text_label(ctx.horizontal_label)}}};"
        "\n"
        rf"\draw[->,thick] (0,0) -- (0,3.7) node[above] "
        rf"{{{_natural_text_label(ctx.vertical_label)}}};"
    )


def _bounded_right_annotation(
    text: str,
    *,
    y: float,
    color: str | None = None,
    anchor: str = "south east",
) -> str:
    """Place a right-edge label inside the drawing lane, away from the legend."""

    if _RIGHT_ANNOTATION_X > _DRAWING_RIGHT_EDGE:
        raise RuntimeError("right annotation lane extends beyond the drawing canvas")
    options = [f"anchor={anchor}"]
    if color:
        options.append(color)
    return (
        rf"\node[{','.join(options)}] at "
        rf"({_format_number(_RIGHT_ANNOTATION_X)},{_format_number(y)}) {{{text}}};"
    )


def _shared_clock_marker() -> str:
    """Draw the common clock guide with its label in a separate top-left lane."""

    return (
        r"\draw[dashed,red!70!black] (3.7,0.25) -- (3.7,3.25);"
        "\n"
        r"\node[anchor=south east,red!70!black] at (3.55,3.35) {shared clock};"
    )


def _quantity_legend(ctx: _FigureContext) -> str:
    heading = (
        "Worked values" if ctx.visual_kind in PHYSICS_VISUAL_KINDS else "Model quantities"
    )
    rows = [rf"\textbf{{{heading}}}"]
    rows.extend(
        f"{_quantity_label(key, model_id=ctx.model_id)} = {rendered_value}"
        for key, rendered_value in _selected_quantities(ctx)
    )
    return (
        r"\node[draw,fill=white,anchor=north west,align=left,font=\scriptsize,"
        r"text width=3.75cm,inner sep=4pt] at (6.35,3.55) {"
        + r" \\ ".join(rows)
        + "};"
    )


def _physics_force(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    if model == "action_reaction":
        return [
            r"\node[draw,circle,minimum size=0.9cm,fill=blue!8] (fa) at (1.65,1.8) {A};",
            r"\node[draw,circle,minimum size=0.9cm,fill=orange!12] (fb) at (4.35,1.8) {B};",
            r"\draw[->,very thick,red!70!black] (fa) -- node[above] {interaction pair} (fb);",
            r"\draw[->,very thick,blue!70!black] (fb) -- node[below] {equal and opposite} (fa);",
            r"\draw[dashed] (0.8,0.75) rectangle (2.5,3.0); \draw[dashed] (3.5,0.75) rectangle (5.2,3.0);",
        ]
    if model == "pulley_constraint":
        return [
            r"\draw[thick] (2.2,3.2) -- (3.8,3.2);",
            r"\draw[thick] (3,2.55) circle (0.65);",
            r"\draw[very thick] (2.35,2.55) -- (2.35,0.8) (3.65,2.55) -- (3.65,0.8);",
            r"\node[draw,fill=blue!8] (pm1) at (2.35,0.55) {mass}; \node[draw,fill=orange!10] (pm2) at (3.65,0.55) {mass};",
            r"\draw[->,very thick,green!50!black] (1.8,0.55) -- (1.8,1.45) node[left] {acceleration};",
            r"\draw[->,very thick,green!50!black] (4.2,1.45) -- (4.2,0.55) node[right] {acceleration};",
        ]
    if model == "spring_force":
        return [
            r"\draw[very thick] (0.45,0.65) -- (0.45,3.05);",
            r"\draw[very thick] (0.45,1.85) -- (0.9,1.85) -- (1.15,2.2) -- (1.55,1.5) -- (1.95,2.2) -- (2.35,1.5) -- (2.75,1.85);",
            r"\node[draw,fill=blue!8,minimum size=0.9cm] (spb) at (3.25,1.85) {body};",
            r"\draw[dashed] (2.7,0.65) -- (2.7,3.05) node[above] {equilibrium marker};",
            r"\draw[->,very thick,red!70!black] (3.25,1.15) -- (2.25,1.15) node[midway,below] {restoring force arrow};",
            r"\draw[->,thick,blue!70!black] (2.7,2.65) -- (3.25,2.65) node[midway,above] {displacement arrow};",
        ]
    if model == "tension_force":
        return [
            r"\draw[very thick] (0.65,3.0) -- (4.1,1.2);",
            r"\node[draw,fill=blue!8,minimum size=0.9cm] (tb) at (4.55,0.95) {body};",
            r"\fill (4.1,1.2) circle (2pt) node[above right] {attachment point};",
            r"\draw[->,very thick,red!70!black] (4.1,1.2) -- (2.7,1.92) node[above] {tension arrow};",
            r"\node at (1.45,2.75) {rope segment};",
        ]
    if model == "contact_force":
        return [
            r"\draw[very thick] (0.4,0.75) -- (5.5,0.75) node[right] {surface};",
            r"\node[draw,fill=blue!8,minimum width=1.2cm,minimum height=0.8cm] (cb) at (2.8,1.2) {body};",
            r"\fill (2.8,0.75) circle (2pt) node[below] {contact point};",
            r"\draw[->,very thick,blue!70!black] (2.8,1.2) -- (2.8,2.75) node[above] {normal arrow};",
            r"\draw[->,very thick,red!70!black] (2.8,1.05) -- (1.25,1.05) node[left] {friction arrow};",
        ]
    if model == "gravity_force":
        return [
            r"\draw[very thick] (0.4,0.6) -- (5.5,0.6) node[right] {reference surface};",
            r"\node[draw,circle,fill=blue!8,minimum size=0.9cm] (gb) at (2.8,2.65) {body};",
            r"\draw[->,very thick,red!70!black] (gb) -- (2.8,1.0);",
            r"\node[anchor=east,red!70!black] at (2.65,0.95) {gravity arrow};",
            r"\draw[->,thick,blue!70!black] (4.25,3.1) -- (4.25,1.2);",
            r"\node[anchor=west,blue!70!black] at (4.4,1.45) {field direction};",
        ]
    if model in {"linear_drag", "quadratic_drag", "drag_force"}:
        parts = [
            r"\fill[blue!7] (0.35,0.45) rectangle (5.55,3.2);",
            r"\node[draw,circle,fill=white,minimum size=0.9cm] (db) at (2.9,1.8) {body};",
            r"\draw[->,very thick,green!50!black] (db) -- (4.8,1.8) node[anchor=west,text width=1.45cm,align=left] {relative velocity arrow};",
            r"\draw[->,very thick,red!70!black] (db) -- (1.1,1.8) node[anchor=east,text width=1.65cm,align=right] {opposing drag arrow};",
            r"\node[anchor=north east] at (5.4,3.05) {fluid};",
        ]
        if model == "quadratic_drag":
            parts.append(r"\draw[dashed,thick] (2.45,1.35) rectangle (3.35,2.25) node[above right] {area marker};")
        elif model == "linear_drag":
            parts.append(r"\draw[thick] (0.75,0.9) -- (1.15,1.1) (0.75,1.3) -- (1.15,1.5);")
        else:
            parts.append(r"\node[draw,fill=white] at (2.9,0.75) {drag law};")
        return parts
    return [
        r"\draw[dashed,thick] (1.2,0.75) rectangle (4.75,3.05);",
        r"\node[anchor=south west] at (0.25,3.25) {free body diagram};",
        r"\node[anchor=south east] at (5.65,3.25) {system boundary};",
        r"\node[draw,fill=blue!8,minimum width=1.25cm,minimum height=0.85cm] (fb) at (2.8,1.8) {body};",
        r"\draw[->,very thick,red!70!black] (fb) -- (0.55,1.8) node[left] {force arrows};",
        r"\draw[->,very thick,red!70!black] (fb) -- (4.95,1.8);",
        r"\draw[->,very thick,blue!70!black] (2.8,2.25) -- (4.25,2.75);",
        r"\node[anchor=west,text width=1.35cm,align=left] at (4.35,2.75) {net force arrow};",
        r"\draw[->,thick,green!50!black] (2.8,1.35) -- (4.35,0.85) node[right] {acceleration arrow};",
    ]


def _physics_kinematics(ctx: _FigureContext) -> list[str]:
    if ctx.model_id == "rolling_kinematics":
        return [
            r"\draw[very thick] (0.35,0.75) -- (5.65,0.75) node[right] {ground};",
            r"\draw[fill=blue!8,thick] (2.6,1.75) circle (1.0) node {rolling body};",
            r"\filldraw (2.6,0.75) circle (2.5pt) node[below] {contact point};",
            r"\draw[->,very thick,green!50!black] (2.6,2.95) -- (4.35,2.95);",
            _bounded_right_annotation(
                "translation arrow", y=3.05, color="green!50!black"
            ),
            r"\draw[->,very thick,red!70!black] (1.85,1.75) arc[start angle=180,end angle=500,radius=0.75] node[left] {rotation arrow};",
        ]
    if ctx.model_id == "kinematics_position_velocity":
        return [
            r"\draw[->,thick] (0.45,1.95) -- (5.65,1.95) node[right] {time};",
            r"\draw[->,thick] (0.45,1.95) -- (0.45,3.5) node[above] {position $x$};",
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.55,2.1) (1.5,2.25) (2.55,2.55) (3.7,2.95) (5.2,3.4)};",
            _bounded_right_annotation(
                "position graph", y=3.48, color="blue!70!black"
            ),
            r"\draw[->,thick] (0.45,0.25) -- (5.65,0.25) node[right] {time};",
            r"\draw[->,thick] (0.45,0.25) -- (0.45,1.65) node[above] {velocity $v$};",
            r"\draw[very thick,green!50!black] (0.55,0.5) -- (5.2,1.45);",
            _bounded_right_annotation(
                "velocity graph", y=1.55, color="green!50!black"
            ),
            _shared_clock_marker(),
        ]
    if ctx.model_id == "kinematics_acceleration":
        return [
            r"\draw[->,thick] (0.45,1.95) -- (5.65,1.95) node[right] {time};",
            r"\draw[->,thick] (0.45,1.95) -- (0.45,3.5) node[above] {velocity $v$};",
            r"\draw[very thick,blue!70!black] (0.55,2.15) -- (5.2,3.35);",
            _bounded_right_annotation(
                "velocity graph", y=3.45, color="blue!70!black"
            ),
            r"\draw[->,thick] (0.45,0.25) -- (5.65,0.25) node[right] {time};",
            r"\draw[->,thick] (0.45,0.25) -- (0.45,1.65) node[above] {acceleration $a$};",
            r"\draw[very thick,orange!80!black] (0.55,1.05) -- (5.2,1.05);",
            _bounded_right_annotation(
                "acceleration graph", y=1.15, color="orange!80!black"
            ),
            _shared_clock_marker(),
        ]
    if ctx.model_id == "kinematics_1d":
        return [
            r"\draw[<->,thick] (0.35,1.55) -- (5.65,1.55) node[right] {number line};",
            r"\foreach \x in {1,2,3,4,5} \draw (\x,1.43) -- (\x,1.67);",
            r"\filldraw[blue!70!black] (3.15,1.55) circle (2.5pt) node[above] {position marker};",
            r"\draw[->,very thick,green!50!black] (3.15,1.05) -- (4.65,1.05) node[right] {velocity arrow};",
            r"\node[draw,fill=gray!5] at (1.15,2.65) {time readout};",
        ]
    if ctx.model_id == "projectile_motion":
        return [
            _axes(ctx),
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.45,0.45) (1.35,1.75) (2.4,2.65) (3.55,2.55) (4.75,1.45) (5.35,0.45)} node[right] {parabolic trajectory};",
            r"\draw[->,very thick,green!50!black] (2.4,2.65) -- (3.5,2.75) node[above] {velocity vector};",
            r"\draw[->,very thick,red!70!black] (4.15,3.25) -- (4.15,2.0) node[right] {gravity arrow};",
        ]
    return [
        _axes(ctx),
        r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.55,0.45) (1.5,1.0) (2.55,1.7) (3.7,2.1) (5.1,2.25)};",
        r"\node[anchor=east,blue!70!black] at (5.65,1.95) {trajectory};",
        r"\coordinate (kinematic-state) at (3.7,2.1);",
        r"\draw[->,very thick,green!50!black] (kinematic-state) -- (4.85,2.38) node[above] {velocity arrow};",
        r"\draw[->,very thick,red!70!black] (0,0) -- (3.7,2.1) node[pos=0.66,above left] {position vector};",
        r"\draw[->,very thick,green!50!black] (3.7,2.1) -- (5.0,2.55) node[midway,above left] {velocity vector};",
    ]


def _physics_vector(ctx: _FigureContext) -> list[str]:
    source = "source vector" if ctx.model_id == "unit_vector" else "vector arrow"
    parts = [
        _axes(ctx),
        rf"\draw[->,very thick,blue!70!black] (0,0) -- (4.35,2.75) node[above] {{{source}}};",
        r"\draw[dashed,thick] (4.35,0) -- (4.35,2.75) -- (0,2.75);",
        r"\draw[->,thick,gray!75] (0,0.25) -- (4.35,0.25) node[midway,below] {component arrows};",
        r"\draw[->,thick,gray!75] (0.25,0) -- (0.25,2.75);",
        r"\node[draw,fill=white] at (3.1,0.9) {magnitude label};",
    ]
    if ctx.model_id == "unit_vector":
        parts.append(r"\draw[->,very thick,green!50!black] (0,0) -- (2.1,1.33) node[above] {unit vector};")
    else:
        parts.append(r"\draw[->,thick,red!70!black] (1.05,0) arc[start angle=0,end angle=32,radius=1.05] node[right] {direction angle};")
    return parts


def _physics_center_of_mass(ctx: _FigureContext) -> list[str]:
    return [
        r"\draw[<->,thick] (0.35,1.5) -- (5.65,1.5) node[right] {position axis};",
        r"\node[draw,circle,fill=blue!8,minimum size=0.75cm] at (1.25,1.5) {mass};",
        r"\node[draw,circle,fill=orange!10,minimum size=1.0cm] at (4.75,1.5) {mass};",
        r"\draw[very thick,green!50!black] (3.3,0.9) -- (3.3,2.1) node[above] {center of mass marker};",
        r"\draw[<->,thick] (1.25,0.55) -- (4.75,0.55) node[midway,below] {balance indicator};",
        r"\node at (2.95,2.8) {mass markers};",
    ]


def _physics_rocket(ctx: _FigureContext) -> list[str]:
    if ctx.model_id == "continuous_mass_accumulation":
        return [
            r"\draw[dashed,very thick] (1.45,0.8) rectangle (4.55,3.0) node[above left] {fixed control volume};",
            r"\draw[->,very thick,blue!70!black] (0.25,2.25) -- (1.45,2.25) node[above] {$\dot m_{\mathrm{in}}$};",
            r"\draw[->,very thick,red!70!black] (4.55,1.45) -- (5.75,1.45) node[above] {$\dot m_{\mathrm{out}}$};",
            r"\node[draw,fill=blue!6] at (3,1.9) {stored mass $M_{\mathrm{cv}}$};",
            r"\draw[->,thick] (1.75,0.45) -- (4.35,0.45) node[right] {time};",
            r"\draw[very thick,green!50!black] (2.0,0.55) -- (4.0,0.95) node[right] {accumulation graph};",
        ]
    if ctx.model_id == "continuous_mass_transfer":
        return [
            r"\draw[dashed,very thick] (1.45,0.75) rectangle (4.55,3.0) node[above left] {control volume boundary};",
            r"\draw[->,very thick,blue!70!black] (0.25,1.9) -- (1.45,1.9) node[above] {$\dot m,\ \mathbf{v}_{\mathrm{in}}$};",
            r"\draw[->,very thick,red!70!black] (4.55,1.9) -- (5.75,1.9) node[above] {$\dot m,\ \mathbf{v}_{\mathrm{out}}$};",
            r"\node at (3,1.9) {continuous flow};",
            r"\node[draw,fill=white] at (3,0.35) {$\dot m\mathbf{v}_{\mathrm{out}}-\dot m\mathbf{v}_{\mathrm{in}}$};",
        ]
    return [
        r"\draw[very thick,fill=gray!10] (3.05,3.25) -- (2.35,1.25) -- (3.05,1.55) -- (3.75,1.25) -- cycle;",
        r"\draw[very thick,orange!80!black] (2.65,1.2) -- (2.35,0.45) (3.05,1.35) -- (3.05,0.35) (3.45,1.2) -- (3.75,0.45) node[right] {exhaust stream};",
        r"\draw[->,very thick,blue!70!black] (3.85,2.25) -- (5.3,2.25) node[right] {velocity arrow};",
        r"\node[draw,fill=white] at (0.95,2.7) {mass readout};",
        r"\node[draw,fill=white] at (5.0,0.65) {delta velocity readout};",
        r"\node at (3.05,3.48) {rocket};",
    ]


def _physics_ode(ctx: _FigureContext) -> list[str]:
    return [
        _axes(ctx),
        r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.25,3.1) (1.1,2.35) (2.0,1.75) (3.0,1.25) (4.2,0.85) (5.35,0.55)} node[right] {state trajectory};",
        r"\filldraw[green!50!black] (0.25,3.1) circle (2.5pt) node[above right] {initial condition marker};",
        r"\draw[->,very thick,red!70!black] (3.0,1.25) -- (3.9,0.9) node[below] {slope indicator};",
        r"\node[below] at (3,0) {time axis};",
    ]


def _physics_work(ctx: _FigureContext) -> list[str]:
    if ctx.model_id == "work_energy_theorem":
        return [
            r"\node[draw,fill=blue!8] (wi) at (1.0,1.45) {initial body};",
            r"\node[draw,fill=green!10] (wf) at (4.95,1.45) {final body};",
            r"\draw[->,very thick,blue!70!black] (wi) -- node[above] {force path} (wf);",
            r"\draw[->,thick] (0.55,0.75) -- (1.45,0.75) node[right] {initial speed arrow};",
            r"\draw[->,very thick] (4.25,0.75) -- (5.75,0.75) node[right] {final speed arrow};",
            r"\draw[fill=orange!18,thick] (2.25,2.35) rectangle (3.75,3.05) node[midway] {kinetic energy meter};",
        ]
    return [
        r"\draw[very thick,blue!70!black] (0.55,1.15) .. controls (2.1,2.65) and (3.8,0.65) .. (5.4,2.25) node[right] {path};",
        r"\draw[->,very thick,red!70!black] (2.45,1.65) -- (3.25,2.85) node[above] {force vector};",
        r"\draw[->,very thick,green!50!black] (2.45,1.65) -- (3.75,1.25) node[below] {displacement vector};",
        r"\draw[fill=orange!18,thick] (0.65,2.65) rectangle (1.85,3.2) node[midway] {work accumulator};",
    ]


def _physics_energy(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    if model == "gravitational_potential_energy":
        return [
            r"\draw[->,thick] (1.05,0.45) -- (1.05,3.35) node[above] {height axis};",
            r"\draw[dashed] (0.45,0.75) -- (5.5,0.75) node[right] {reference level};",
            r"\node[draw,circle,fill=blue!8] at (2.6,1.25) {body}; \node[draw,circle,fill=green!10] at (2.6,2.75) {body};",
            r"\draw[->,very thick,red!70!black] (3.35,2.75) -- (3.35,1.45) node[right] {gravity arrow};",
            r"\draw[fill=orange!18,thick] (4.35,1.0) rectangle (5.25,2.9) node[midway,rotate=90] {potential energy meter};",
        ]
    if model == "spring_potential_energy":
        return [
            r"\draw[very thick] (0.45,0.65) -- (0.45,3.05);",
            r"\draw[very thick] (0.45,1.85) -- (0.9,1.85) -- (1.2,2.2) -- (1.6,1.5) -- (2.0,2.2) -- (2.4,1.5) -- (2.8,1.85);",
            r"\node[draw,fill=blue!8] at (3.25,1.85) {spring};",
            r"\draw[dashed] (2.8,0.65) -- (2.8,3.05) node[above] {equilibrium marker};",
            r"\draw[<->,thick] (2.8,1.0) -- (3.25,1.0) node[midway,below] {displacement marker};",
            r"\draw[fill=orange!18,thick] (4.35,0.8) rectangle (5.25,2.85) node[midway,rotate=90] {potential energy meter};",
        ]
    if model == "potential_energy":
        return [
            _axes(ctx),
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.4,3.05) (1.5,1.65) (2.8,0.65) (4.1,1.65) (5.25,3.05)} node[right] {$U(x)$};",
            r"\draw[->,very thick,red!70!black] (4.1,1.65) -- (3.05,0.85) node[anchor=north east] {$\nabla U$};",
            r"\draw[->,very thick,green!50!black] (4.1,1.65) -- (4.95,2.4) node[anchor=south west] {$F=-\nabla U$};",
        ]
    return [
        r"\node at (1.55,3.25) {initial state}; \node at (4.45,3.25) {final state};",
        r"\draw[fill=blue!18,thick] (0.7,0.65) rectangle (1.45,2.25);",
        r"\node[rotate=90,font=\scriptsize] at (1.075,1.45) {kinetic energy meter};",
        r"\draw[fill=orange!18,thick] (1.65,0.65) rectangle (2.4,2.8);",
        r"\node[rotate=90,font=\scriptsize] at (2.025,1.725) {potential energy meter};",
        r"\draw[fill=blue!18,thick] (3.55,0.65) rectangle (4.3,2.45);",
        r"\draw[fill=orange!18,thick] (4.5,0.65) rectangle (5.25,2.35);",
        r"\draw[<->,very thick,green!50!black] (2.55,1.65) -- (3.35,1.65);",
        r"\node[anchor=north] at (2.95,0.45) {total energy marker};",
    ]


def _physics_momentum(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    if model == "impulse_momentum":
        return [
            _axes(ctx),
            r"\fill[blue!14] (0.65,0) -- (0.65,1.25) -- (1.75,2.4) -- (3.0,1.65) -- (4.4,2.75) -- (5.15,0) -- cycle;",
            r"\draw[very thick,blue!70!black] plot coordinates {(0.65,1.25) (1.75,2.4) (3.0,1.65) (4.4,2.75) (5.15,1.2)};",
            r"\node at (2.8,0.55) {impulse area};",
            r"\draw[->,thick] (0.65,3.2) -- (1.45,3.2);",
            r"\node[anchor=south west,font=\scriptsize,text width=1.9cm,align=left] at (0.65,3.3) {momentum before};",
            r"\draw[->,very thick] (3.55,3.2) -- (4.35,3.2);",
            r"\node[anchor=south west,font=\scriptsize,text width=1.9cm,align=left] at (3.55,3.3) {momentum after};",
        ]
    if model == "momentum_definition":
        return [
            r"\draw[dashed] (0.65,0.65) rectangle (5.35,3.05) node[above left] {reference frame};",
            r"\node[draw,fill=blue!8] (mb) at (1.75,1.7) {body};",
            r"\draw[->,thick,green!50!black] (mb) -- (3.15,1.7) node[above] {velocity arrow};",
            r"\draw[->,very thick,blue!70!black] (mb) -- (4.75,1.1) node[right] {momentum arrow};",
        ]
    if model in {"elastic_collision", "inelastic_collision", "perfectly_inelastic_collision"}:
        parts = [
            r"\draw[dashed] (0.35,0.45) rectangle (5.65,3.25) node[above left] {system boundary};",
            r"\node at (1.45,2.9) {before state}; \node at (4.5,2.9) {after state};",
            r"\node[draw,circle,fill=blue!8] at (0.9,1.65) {A}; \node[draw,circle,fill=orange!10] at (1.9,1.65) {B};",
            r"\draw[->,very thick] (0.45,1.05) -- (1.35,1.05); \draw[->,thick] (2.35,1.05) -- (1.65,1.05);",
        ]
        if model == "perfectly_inelastic_collision":
            parts.extend(
                [
                    r"\node[draw,fill=green!10,minimum width=1.5cm] at (4.45,1.65) {A+B};",
                    r"\draw[->,very thick] (4.1,1.05) -- (5.35,1.05) node[right] {shared velocity arrow};",
                    r"\node at (4.45,2.35) {stuck after state};",
                ]
            )
        elif model == "elastic_collision":
            parts.extend(
                [
                    r"\node[draw,circle,fill=blue!8] at (3.85,1.65) {A}; \node[draw,circle,fill=orange!10] at (5.0,1.65) {B};",
                    r"\draw[->,thick] (3.85,1.05) -- (3.1,1.05); \draw[->,very thick] (5.0,1.05) -- (5.6,1.05);",
                    r"\node[draw,fill=green!10] at (4.45,0.55) {kinetic energy meter};",
                ]
            )
        else:
            parts.extend(
                [
                    r"\node[draw,circle,fill=blue!8] at (4.05,1.65) {A}; \node[draw,circle,fill=orange!10] at (4.9,1.65) {B};",
                    r"\draw[->,thick] (4.05,1.05) -- (4.6,1.05); \draw[->,thick] (4.9,0.75) -- (5.35,0.75);",
                    r"\node[draw,fill=red!8] at (4.45,0.45) {energy transfer meter};",
                ]
            )
        return parts
    return [
        r"\draw[dashed] (0.35,0.5) rectangle (5.65,3.2) node[above left] {system boundary};",
        r"\node at (1.35,2.85) {before state}; \node at (4.55,2.85) {after state};",
        r"\node[draw,circle,fill=blue!8] at (1.0,1.65) {A}; \node[draw,circle,fill=orange!10] at (1.9,1.65) {B};",
        r"\node[draw,circle,fill=blue!8] at (4.05,1.65) {A}; \node[draw,circle,fill=orange!10] at (4.95,1.65) {B};",
        r"\draw[->,very thick,blue!70!black] (0.55,1.0) -- (2.35,1.0) node[midway,below] {momentum vectors};",
        r"\draw[->,very thick,green!50!black] (3.65,1.0) -- (5.45,1.0) node[midway,below] {total momentum marker};",
    ]


def _physics_potential(ctx: _FigureContext) -> list[str]:
    return [
        _axes(ctx),
        r"\fill[green!10] (1.35,0) -- (1.35,2.65) -- (4.55,2.65) -- (4.55,0) -- cycle;",
        r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.45,3.25) (1.35,2.65) (2.1,1.15) (3.0,0.6) (3.9,1.15) (4.55,2.65) (5.45,3.25)} node[right] {$U(x)$};",
        r"\draw[very thick,red!70!black] (0.35,2.65) -- (5.45,2.65) node[right] {$E$};",
        r"\filldraw (1.35,2.65) circle (2.3pt) node[above left] {$x_-$}; \filldraw (4.55,2.65) circle (2.3pt) node[above right] {$x_+$};",
        r"\node at (2.95,1.75) {classically allowed};",
    ]


def _physics_circular(ctx: _FigureContext) -> list[str]:
    parts = [
        r"\draw[very thick] (3,1.8) circle (1.45);",
        r"\filldraw (3,1.8) circle (2pt) node[below left] {center};",
        r"\node[draw,circle,fill=blue!8,minimum size=0.55cm] (cm) at (4.15,2.68) {body};",
    ]
    if ctx.model_id == "circular_position":
        parts.extend(
            [
                r"\draw[->,very thick,blue!70!black] (3,1.8) -- (cm) node[midway,above left] {radius vector};",
                r"\draw[->,thick,red!70!black] (3.7,1.8) arc[start angle=0,end angle=37,radius=0.7];",
                r"\node[anchor=west,red!70!black] at (4.0,1.95) {angle marker};",
                r"\draw[thin] (cm.north) -- (4.55,3.2);",
                r"\node[anchor=south east] at (5.55,3.25) {position marker};",
            ]
        )
    elif ctx.model_id == "uniform_circular_motion":
        parts.extend(
            [
                r"\draw[->,very thick,green!50!black] (cm) -- (3.15,3.45) node[above] {tangent velocity arrow};",
                r"\draw[->,thick,red!70!black] (1.25,1.8) arc[start angle=180,end angle=480,radius=1.75] node[left] {lap phase};",
            ]
        )
    elif ctx.model_id == "radial_acceleration":
        parts.extend(
            [
                r"\draw[->,very thick,green!50!black] (cm) -- (3.15,3.45) node[above] {tangent velocity arrow};",
                r"\draw[->,very thick,red!70!black] (cm) -- (3,1.8) node[midway,below right] {inward acceleration arrow};",
                r"\draw[->,thick,blue!70!black] (1.8,0.35) -- (2.8,0.35) node[right] {velocity difference};",
            ]
        )
    else:
        parts.extend(
            [
                r"\draw[->,very thick,red!70!black] (cm) -- (3,1.8);",
                r"\node[anchor=south west,red!70!black] (inward-force-label) at (0.3,3.35) {net inward force arrow};",
                r"\draw[thin,red!70!black] (inward-force-label.south east) -- (3.55,2.22);",
                r"\draw[->,thick,red!70!black] (cm) -- (4.9,2.95);",
                _bounded_right_annotation(
                    "force arrows", y=3.05, color="red!70!black"
                ),
            ]
        )
    return parts


def _rolling_rotation(ctx: _FigureContext) -> list[str]:
    parts = [
        r"\draw[very thick] (0.45,0.65) -- (5.55,0.65) node[right] {surface};",
        r"\draw[very thick,fill=blue!8] (2.75,1.6) circle (0.95);",
        r"\filldraw (2.75,0.65) circle (2pt) node[below] {contact point};",
        r"\draw[->,very thick,green!50!black] (2.75,1.6) -- (4.65,1.6);",
        r"\node[anchor=south west,green!50!black] at (3.35,1.7) {translation arrow};",
        r"\draw[->,very thick,red!70!black] (1.55,1.6) arc[start angle=180,end angle=500,radius=1.2] node[left] {rotation arrow};",
    ]
    if ctx.model_id == "rolling_kinetic_energy":
        parts.extend(
            [
                r"\draw[fill=green!12,thick] (4.15,2.25) rectangle (5.65,2.75);",
                r"\node[font=\scriptsize] at (4.9,2.5) {translation $K$};",
                r"\draw[fill=orange!16,thick] (4.15,2.95) rectangle (5.65,3.45);",
                r"\node[font=\scriptsize] at (4.9,3.2) {rotation $K$};",
            ]
        )
    elif ctx.model_id == "rolling_angular_momentum":
        parts.extend(
            [
                r"\filldraw (2.75,1.6) circle (2pt) node[above] {center of mass};",
                r"\draw[->,very thick,blue!70!black] (2.75,0.65) -- (4.4,2.75) node[right] {angular momentum arrow};",
            ]
        )
    elif ctx.model_id == "rolling_dynamics":
        parts.extend(
            [
                r"\draw[dashed] (1.35,0.35) rectangle (4.15,3.05) node[above left] {free body diagram};",
                r"\draw[->,very thick,blue!70!black] (2.75,1.6) -- (2.75,3.25);",
            ]
        )
    else:
        parts.append(r"\node at (2.75,3.05) {rolling body};")
    return parts


def _physics_rotation(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    if model.startswith("rolling_"):
        return _rolling_rotation(ctx)
    if model == "rigid_body_motion":
        return [
            r"\draw[fill=blue!8,thick] (0.85,0.85) -- (4.75,1.1) -- (5.15,2.75) -- (1.35,3.1) -- cycle;",
            r"\filldraw (2.1,1.7) circle (2pt);",
            r"\node[anchor=north] at (2.1,1.55) {reference point $O$};",
            r"\filldraw (4.0,2.25) circle (2pt);",
            r"\draw[thin] (4.0,2.25) -- (3.85,3.05);",
            r"\node[anchor=south east] at (3.85,3.05) {material point $P$};",
            r"\draw[->,very thick,green!50!black] (2.1,1.7) -- (3.45,1.7) node[below] {$\mathbf{v}_O$};",
            r"\draw[->,very thick,red!70!black] (2.0,1.7) arc[start angle=180,end angle=500,radius=1.0] node[left] {$\boldsymbol{\omega}$};",
            r"\draw[->,very thick,blue!70!black] (4.0,2.25) -- (5.25,3.1) node[right] {$\mathbf{v}_P$};",
        ]
    if model == "torque":
        return [
            r"\filldraw (1.1,0.85) circle (2.5pt) node[below] {pivot};",
            r"\draw[very thick] (1.1,0.85) -- (4.25,2.15) node[midway,below] {lever arm};",
            r"\draw[->,very thick,red!70!black] (4.25,2.15) -- (4.25,3.45) node[above] {force arrow};",
            r"\draw[->,very thick,blue!70!black] (2.15,0.85) arc[start angle=0,end angle=115,radius=1.05] node[above] {torque arc};",
            r"\draw[fill=gray!7] (1.1,0.85) -- (4.25,2.15) -- (3.95,2.45) -- cycle;",
        ]
    if model == "angular_impulse":
        return [
            _axes(ctx),
            r"\fill[blue!14] (0.75,0) rectangle (4.75,2.25);",
            r"\draw[very thick,blue!70!black] (0.75,2.25) -- (4.75,2.25);",
            r"\node at (2.75,1.1) {angular impulse area};",
            r"\draw[->,thick] (0.65,3.2) -- (1.35,3.2);",
            r"\node[anchor=south west,font=\scriptsize,text width=2.1cm,align=left] at (0.65,3.3) {angular momentum before};",
            r"\draw[->,very thick] (3.75,3.2) -- (4.45,3.2);",
            r"\node[anchor=south west,font=\scriptsize,text width=2.1cm,align=left] at (3.55,3.3) {angular momentum after};",
        ]
    if model == "moment_of_inertia":
        return [
            r"\draw[very thick] (3,0.35) -- (3,3.35) node[above] {rotation axis};",
            r"\draw[fill=blue!6,thick] (0.7,0.8) ellipse (2.05 and 1.15);",
            r"\node[draw,circle,fill=orange!12] at (1.25,1.1) {mass}; \node[draw,circle,fill=orange!12] at (2.05,2.25) {mass}; \node[draw,circle,fill=orange!12] at (4.6,1.55) {mass};",
            r"\draw[<->,thick] (3,2.65) -- (1.95,2.65) node[midway,above] {radius markers};",
            r"\node at (4.8,3.0) {mass elements};",
        ]
    if model == "point_particle_angular_momentum":
        return [
            _axes(ctx),
            r"\filldraw (0,0) circle (2pt) node[below left] {origin};",
            r"\node[draw,circle,fill=blue!8,minimum size=1.05cm] (pp) at (3.75,2.35) {};",
            r"\node[anchor=north] at (3.75,2.25) {point particle};",
            r"\draw[->,very thick,blue!70!black] (0,0) -- (pp) node[midway,above] {position vector};",
            r"\draw[->,very thick,green!50!black] (pp) -- (5.15,2.8);",
            r"\node[anchor=east,green!50!black] at (5.65,3.05) {momentum vector};",
            r"\node[draw,fill=white,text width=3.0cm,align=center] at (4.25,0.75) {angular momentum direction};",
        ]
    if model in {"rigid_body_angular_momentum", "angular_momentum"}:
        if model == "rigid_body_angular_momentum":
            return [
                r"\draw[fill=blue!8,thick] (1.0,0.75) -- (4.75,1.15) -- (5.0,2.85) -- (1.55,3.1) -- cycle;",
                r"\draw[very thick] (3,0.35) -- (3,3.45) node[above] {rotation axis};",
                r"\draw[->,very thick,red!70!black] (2.1,1.85) arc[start angle=180,end angle=500,radius=0.9] node[left] {$\boldsymbol{\omega}$};",
                r"\draw[->,very thick,blue!70!black] (3,1.85) -- (4.7,3.15) node[right] {$\mathbf{L}$};",
                r"\node at (4.55,0.6) {rigid body};",
            ]
        return [
            r"\draw[dashed] (0.5,0.5) rectangle (5.5,3.15) node[above left] {system boundary};",
            r"\filldraw (2.85,1.65) circle (2pt) node[below] {origin};",
            r"\node[draw,circle,fill=blue!8] (ap1) at (1.25,2.45) {mass}; \node[draw,circle,fill=orange!10] (ap2) at (4.55,2.15) {mass};",
            r"\draw[->,thick] (2.85,1.65) -- (ap1); \draw[->,thick] (2.85,1.65) -- (ap2);",
            r"\draw[->,very thick,blue!70!black] (2.85,1.65) -- (3.65,3.35) node[right] {angular momentum arrow};",
        ]
    return [
        r"\draw[fill=blue!8,thick] (0.85,0.85) -- (4.75,1.1) -- (5.15,2.75) -- (1.35,3.1) -- cycle;",
        r"\filldraw (2.1,1.7) circle (2pt);",
        r"\node[anchor=east] at (1.85,1.25) {reference point};",
        r"\filldraw (4.0,2.25) circle (2pt);",
        r"\draw[thin] (4.0,2.25) -- (3.0,3.25);",
        r"\node[anchor=south east] at (3.0,3.25) {material point};",
        r"\draw[->,very thick,green!50!black] (2.1,1.7) -- (3.45,1.7);",
        r"\node[anchor=north] at (2.8,0.7) {translation arrow};",
        r"\draw[->,very thick,red!70!black] (2.0,1.7) arc[start angle=180,end angle=500,radius=1.0] node[left] {rotation arrow};",
        r"\draw[->,very thick,blue!70!black] (4.0,2.25) -- (5.15,3.0);",
        r"\node[anchor=south east,text width=2.1cm,align=right,blue!70!black] at (5.0,3.05) {angular acceleration arrow};",
    ]


def _physics_recoil(ctx: _FigureContext) -> list[str]:
    if ctx.model_id == "relative_velocity":
        return [
            _axes(ctx),
            r"\node[draw,circle,fill=blue!8] at (1.0,0.7) {object A}; \node[draw,circle,fill=orange!10] at (1.0,0.25) {object B};",
            r"\draw[->,very thick,blue!70!black] (1.0,0.7) -- (4.9,2.75) node[right] {velocity A};",
            r"\draw[->,very thick,orange!80!black] (1.0,0.25) -- (3.1,1.05) node[right] {velocity B};",
            r"\draw[->,very thick,green!50!black] (3.1,1.05) -- (4.9,2.75) node[midway,right] {relative velocity arrow};",
            r"\node at (4.65,0.45) {reference frame};",
        ]
    return [
        r"\draw[dashed] (0.45,0.55) rectangle (5.55,3.2) node[above left] {system boundary};",
        r"\node[draw,fill=gray!8] at (1.35,1.75) {before state};",
        r"\draw[->,very thick] (2.1,1.75) -- (2.75,1.75);",
        r"\node[draw,circle,fill=blue!8] at (4.0,1.75) {A}; \node[draw,circle,fill=orange!10] at (5.0,1.75) {B};",
        r"\draw[->,very thick,blue!70!black] (4.0,1.1) -- (3.0,1.1); \draw[->,very thick,red!70!black] (5.0,1.1) -- (5.75,1.1);",
        r"\node at (4.5,2.65) {separation state}; \node at (4.5,0.55) {opposite momentum arrows};",
    ]


def _physics_wave(ctx: _FigureContext) -> list[str]:
    return [
        r"\draw[->,thick] (0.25,1.75) -- (5.75,1.75) node[right] {equilibrium axis};",
        r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.35,1.75) (0.85,2.7) (1.35,2.95) (1.85,2.7) (2.35,1.75) (2.85,0.8) (3.35,0.55) (3.85,0.8) (4.35,1.75) (4.85,2.7) (5.35,2.95)} node[right] {wave profile};",
        r"\draw[<->,thick,red!70!black] (1.35,1.75) -- (1.35,2.95) node[midway,left] {amplitude marker};",
        r"\draw[<->,thick,green!50!black] (1.35,3.35) -- (5.35,3.35) node[midway,above] {wavelength marker};",
        r"\draw[->,very thick,orange!80!black] (3.25,0.2) -- (4.95,0.2) node[right] {propagation arrow};",
    ]


_SURPLUS_LABEL_EXCLUSION_RADIUS: Final[float] = 0.55


def _scenario_number(values: Mapping[str, object], key: str) -> float:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"surplus geometry requires numeric {key}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("scenario labels require finite numeric values")
    return number


def _surplus_label_point(
    x: float, y: float, dx: float, dy: float
) -> tuple[float, float]:
    if math.hypot(dx, dy) < _SURPLUS_LABEL_EXCLUSION_RADIUS:
        raise ValueError("surplus label offset enters the equilibrium exclusion radius")
    return x + dx, y + dy


def _surplus_market_geometry(ctx: _FigureContext) -> list[str]:
    """Build scaled surplus geometry from the scenario's economic quantities."""

    model = ctx.model_id
    if model == "consumer_surplus":
        q_star = _scenario_number(ctx.setup, "quantity")
        p_star = _scenario_number(ctx.setup, "market_price")
        demand_zero = _scenario_number(ctx.setup, "choke_price")
        supply_zero = p_star
    elif model == "producer_surplus":
        q_star = _scenario_number(ctx.setup, "quantity")
        p_star = _scenario_number(ctx.setup, "market_price")
        demand_zero = p_star
        supply_zero = _scenario_number(ctx.setup, "supply_intercept_price")
    elif model == "welfare_surplus":
        q_star = _scenario_number(ctx.results, "efficient_quantity")
        p_star = _scenario_number(ctx.results, "equilibrium_price")
        demand_zero = _scenario_number(ctx.setup, "marginal_benefit_intercept")
        supply_zero = _scenario_number(ctx.setup, "marginal_cost_intercept")
    else:
        cs = _scenario_number(ctx.results, "CS")
        ps = _scenario_number(ctx.results, "PS")
        q_star = max(math.sqrt(max(cs + ps, 1.0)), 1.0)
        p_star = max(2.0 * ps / q_star, 1.0)
        demand_zero = p_star + 2.0 * cs / q_star
        supply_zero = 0.0

    if q_star <= 0.0 or p_star < 0.0 or demand_zero < p_star or supply_zero > p_star:
        raise ValueError("surplus geometry requires a positive traded quantity and ordered prices")

    q_max = 1.32 * q_star
    price_span = max(demand_zero, p_star, supply_zero, 1.0)
    p_max = 1.12 * price_span
    left, bottom, width, height = 0.45, 0.25, 4.85, 3.15

    def x(quantity: float) -> float:
        return left + width * quantity / q_max

    def y(price: float) -> float:
        return bottom + height * price / p_max

    qx, py = x(q_star), y(p_star)
    demand_y0, supply_y0 = y(demand_zero), y(supply_zero)
    equilibrium_label = _surplus_label_point(qx, py, 0.68, 0.56)
    parts: list[str] = []

    if model in {"consumer_surplus", "total_surplus", "welfare_surplus"}:
        parts.append(
            rf"\fill[green!18] ({left:.3f},{py:.3f}) -- ({left:.3f},{demand_y0:.3f}) -- ({qx:.3f},{py:.3f}) -- cycle;"
        )
    if model in {"producer_surplus", "total_surplus", "welfare_surplus"}:
        parts.append(
            rf"\fill[orange!18] ({left:.3f},{supply_y0:.3f}) -- ({qx:.3f},{py:.3f}) -- ({left:.3f},{py:.3f}) -- cycle;"
        )

    parts.extend(
        [
            _axes(ctx),
            rf"\draw[dashed,thin] ({qx:.3f},{bottom:.3f}) -- ({qx:.3f},{py:.3f});",
            rf"\draw[dashed,thin] ({left:.3f},{py:.3f}) -- ({qx:.3f},{py:.3f});",
        ]
    )
    if model in {"consumer_surplus", "total_surplus", "welfare_surplus"}:
        parts.append(
            rf"\draw[very thick,red!70!black] ({left:.3f},{demand_y0:.3f}) -- ({qx:.3f},{py:.3f}) node[pos=0.16,above right,font=\scriptsize] {{{'marginal benefit' if model == 'welfare_surplus' else 'demand'}}};"
        )
    if model in {"producer_surplus", "total_surplus", "welfare_surplus"}:
        parts.append(
            rf"\draw[very thick,blue!70!black] ({left:.3f},{supply_y0:.3f}) -- ({qx:.3f},{py:.3f}) node[pos=0.18,below right,font=\scriptsize] {{{'marginal cost' if model == 'welfare_surplus' else 'supply'}}};"
        )
    parts.extend(
        [
            rf"\filldraw[green!50!black] ({qx:.3f},{py:.3f}) circle (2.4pt);",
            rf"\draw[thin] ({qx:.3f},{py:.3f}) -- ({equilibrium_label[0]:.3f},{equilibrium_label[1]:.3f});",
            rf"\node[anchor=south west,font=\scriptsize] at ({equilibrium_label[0]:.3f},{equilibrium_label[1]:.3f}) {{$ (Q^*,P^*) $}};",
            rf"\node[anchor=north,font=\scriptsize] at ({qx:.3f},{bottom - 0.05:.3f}) {{$Q^*$}};",
            rf"\node[anchor=east,font=\scriptsize] at ({left - 0.05:.3f},{py:.3f}) {{$P^*$}};",
        ]
    )
    if model in {"consumer_surplus", "total_surplus", "welfare_surplus"}:
        parts.append(rf"\node[anchor=east,font=\scriptsize] at ({x(0.18*q_star):.3f},{y((demand_zero+p_star)/2):.3f}) {{consumer surplus}};")
    if model in {"producer_surplus", "total_surplus", "welfare_surplus"}:
        parts.append(rf"\node[anchor=east,font=\scriptsize] at ({x(0.18*q_star):.3f},{y((supply_zero+p_star)/2):.3f}) {{producer surplus}};")
    if model in {"total_surplus", "welfare_surplus"}:
        parts.append(r"\node[anchor=north east,font=\scriptsize] at (5.2,3.55) {total surplus};")
    return parts


def _economics_market(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    parts = [_axes(ctx)]
    if model == "comparative_statics":
        parts.extend(
            [
                r"\draw[very thick,red!70!black] (0.6,3.15) -- (5.2,0.65) node[right] {initial demand};",
                r"\draw[very thick,red!45!black,dashed] (1.35,3.4) -- (5.65,1.0) node[right] {shift};",
                r"\draw[very thick,blue!70!black] (0.65,0.65) -- (5.25,3.15) node[right] {supply};",
                r"\filldraw (2.95,1.9) circle (2.3pt) node[left] {initial equilibrium};",
                r"\filldraw[green!50!black] (3.65,2.28) circle (2.3pt) node[right] {new equilibrium};",
            ]
        )
        return parts
    if model in {"price_ceiling_shortage", "price_floor_surplus", "price_controls"}:
        parts.extend(
            [
                r"\draw[very thick,red!70!black] (0.6,3.2) -- (5.3,0.65) node[right] {demand};",
                r"\draw[very thick,blue!70!black] (0.6,0.65) -- (5.3,3.2) node[right] {supply};",
                r"\filldraw (2.95,1.93) circle (2.3pt) node[above] {P*};",
            ]
        )
        if model in {"price_ceiling_shortage", "price_controls"}:
            parts.extend(
                [
                    r"\draw[very thick,green!50!black] (0.4,1.25) -- (5.5,1.25) node[right] {price ceiling};",
                    r"\draw[<->,thick] (1.7,0.85) -- (4.25,0.85) node[midway,below] {shortage};",
                ]
            )
        if model in {"price_floor_surplus", "price_controls"}:
            parts.extend(
                [
                    r"\draw[very thick,orange!80!black] (0.4,2.65) -- (5.5,2.65) node[right] {price floor};",
                    r"\draw[<->,thick] (1.7,3.25) -- (4.25,3.25) node[midway,above] {surplus};",
                ]
            )
        return parts
    if model in {"consumer_surplus", "producer_surplus", "total_surplus", "welfare_surplus"}:
        return _surplus_market_geometry(ctx)
    if model == "international_trade":
        return parts + [
            r"\draw[very thick,red!70!black] (0.6,3.2) -- (5.3,0.65) node[pos=0.82,below right,font=\scriptsize] {domestic demand};",
            r"\draw[very thick,blue!70!black] (0.6,0.65) -- (5.3,3.2) node[pos=0.76,above left,font=\scriptsize] {domestic supply};",
            r"\draw[very thick,green!50!black] (0.4,1.45) -- (5.5,1.45) node[right] {$P_w$};",
            r"\draw[<->,thick] (1.65,0.85) -- (4.05,0.85) node[midway,below] {trade volume};",
        ]
    if model == "tariff":
        return parts + [
            r"\draw[very thick,red!70!black] (0.6,3.2) -- (5.3,0.65) node[pos=0.82,below right,font=\scriptsize] {domestic demand};",
            r"\draw[very thick,blue!70!black] (0.6,0.65) -- (5.3,3.2) node[pos=0.76,above left,font=\scriptsize] {domestic supply};",
            r"\draw[very thick,green!50!black] (0.4,1.25) -- (5.5,1.25) node[right] {world price};",
            r"\draw[very thick,orange!80!black] (0.4,1.75) -- (5.5,1.75) node[right] {tariff price};",
            r"\draw[<->,thick] (2.05,0.75) -- (3.75,0.75) node[midway,below] {import reduction};",
            r"\fill[green!15] (2.25,1.25) rectangle (3.55,1.75); \node[font=\scriptsize] at (2.9,1.5) {tariff revenue};",
            r"\fill[orange!28] (1.8,1.25) -- (2.25,1.75) -- (2.25,1.25) -- cycle; \node[font=\scriptsize] at (4.25,2.25) {deadweight loss};",
        ]
    demand_label = _pick(ctx, "demand", fallback="demand")
    supply_label = _pick(ctx, "supply", fallback="supply")
    parts.extend(
        [
            rf"\draw[very thick,red!70!black] (0.6,3.2) -- (5.3,0.65) node[right] {{{demand_label}}};",
            rf"\draw[very thick,blue!70!black] (0.6,0.65) -- (5.3,3.2) node[right] {{{supply_label}}};",
            (
                r"\filldraw[green!50!black] (2.95,1.93) circle (2.3pt) "
                r"node[above right] {equilibrium price and quantity $(Q^*,P^*)$};"
                if model == "market_equilibrium"
                else r"\filldraw[green!50!black] (2.95,1.93) circle (2.3pt) node[above right] {equilibrium};"
            ),
        ]
    )
    return parts


def _economics_budget(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    parts = [_axes(ctx)]
    if model in {"consumer_preferences", "utility_representation"}:
        return parts + [
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.65,3.15) (1.15,2.05) (2.2,1.25) (4.8,0.65)} node[right] {indifference curve};",
            r"\draw[very thick,blue!40!black,dashed] plot[smooth] coordinates {(1.25,3.35) (1.9,2.25) (3.1,1.45) (5.45,1.05)};",
            r"\filldraw[green!50!black] (2.25,1.25) circle (2.4pt) node[above] {bundle A};",
            r"\filldraw[orange!80!black] (3.65,1.25) circle (2.4pt) node[above] {bundle B};",
            r"\node[draw,fill=white] at (4.75,2.75) {utility ranking};",
        ]
    if model == "marginal_rate_of_substitution":
        return parts + [
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.65,3.2) (1.2,2.2) (2.25,1.35) (4.95,0.65)} node[right] {indifference curve};",
            r"\filldraw (2.25,1.35) circle (2.4pt) node[above right] {bundle point};",
            r"\draw[very thick,red!70!black] (0.95,2.25) -- (4.25,0.35) node[right] {tangent};",
            r"\node[draw,fill=white] at (4.65,2.75) {MRS};",
        ]
    if model == "income_substitution_effects":
        return parts + [
            r"\draw[very thick,blue!70!black] (0.45,2.65) -- (4.1,0.45) node[right] {initial budget};",
            r"\draw[very thick,green!50!black,dashed] (0.75,3.15) -- (4.4,0.95) node[right] {compensated budget};",
            r"\draw[very thick,orange!80!black] (1.15,3.45) -- (4.8,1.25) node[right] {final budget};",
            r"\filldraw (1.75,1.85) circle (2.3pt); \filldraw (2.8,1.8) circle (2.3pt); \filldraw (3.85,1.75) circle (2.3pt);",
            r"\draw[->,thick] (1.75,0.65) -- (2.8,0.65) node[midway,below] {SE}; \draw[->,thick] (2.8,0.65) -- (3.85,0.65) node[midway,below] {IE};",
        ]
    parts.extend(
        [
            r"\fill[blue!8] (0,0) -- (0,3.2) -- (5.25,0) -- cycle;",
            r"\draw[very thick,blue!70!black] (0,3.2) -- (5.25,0) node[pos=0.88,above left,font=\scriptsize] {budget line};",
            r"\draw[very thick,red!70!black] plot[smooth] coordinates {(0.75,3.35) (1.45,2.25) (2.75,1.35) (5.15,0.75)} node[pos=0.82,below right,font=\scriptsize] {indifference curve};",
            r"\filldraw[green!50!black] (2.55,1.55) circle (2.5pt) node[above right] {chosen bundle};",
        ]
    )
    if model == "intertemporal_choice":
        parts.extend(
            [
                r"\filldraw[orange!80!black] (1.5,2.3) circle (2.4pt) node[above] {endowment};",
                r"\draw[->,very thick] (1.5,2.3) -- (2.55,1.55) node[midway,above] {saving borrowing arrow};",
            ]
        )
    elif model == "budget_constraint":
        parts.append(r"\node at (1.25,0.65) {affordable region};")
    return parts


def _economics_elasticity(ctx: _FigureContext) -> list[str]:
    parts = [_axes(ctx)]
    if ctx.model_id == "own_price_elasticity":
        return parts + [
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.55,3.25) (1.55,2.65) (2.8,1.9) (4.1,1.15) (5.35,0.55)} node[right] {demand};",
            r"\filldraw (1.55,2.65) circle (2.4pt) node[above] {initial point}; \filldraw[green!50!black] (4.1,1.15) circle (2.4pt) node[below] {new point};",
            r"\draw[->,thick] (1.65,2.35) -- (3.95,1.35) node[midway,above] {own price response};",
            r"\node[draw,fill=white] at (4.65,3.05) {E d};",
        ]
    if ctx.model_id == "income_elasticity":
        return parts + [
            r"\draw[very thick,green!50!black] plot[smooth] coordinates {(0.55,0.65) (1.65,1.1) (2.8,1.75) (4.0,2.45) (5.35,3.15)};",
            r"\filldraw (1.65,1.1) circle (2.4pt) node[below] {initial income}; \filldraw (4.0,2.45) circle (2.4pt) node[above] {new income};",
            r"\node[draw,fill=blue!7] at (4.75,0.75) {normal / inferior};",
            r"\node[draw,fill=white] at (1.25,3.05) {E I};",
        ]
    return parts + [
        r"\draw[very thick,orange!80!black] (0.55,0.75) -- (5.25,2.95) node[right] {good x demand};",
        r"\draw[->,very thick,blue!70!black] (1.3,2.8) -- (3.15,2.8) node[midway,above] {good y price change};",
        r"\draw[->,very thick,green!50!black] (3.15,1.3) -- (4.65,2.0) node[right] {quantity x change};",
        r"\node[draw,fill=white] at (1.35,0.55) {substitutes / complements};",
    ]


def _economics_tax(ctx: _FigureContext) -> list[str]:
    parts = [
        _axes(ctx),
        r"\draw[very thick,red!70!black] (0.6,3.25) -- (5.35,0.65) node[right] {demand};",
        r"\draw[very thick,blue!70!black] (0.6,0.65) -- (5.35,3.25) node[right] {supply};",
    ]
    if ctx.model_id == "tax_incidence":
        return parts + [
            r"\coordinate (tax-quantity) at (2.75,0); \coordinate (buyer-price-at-tax-quantity) at (2.75,2.55); \coordinate (seller-price-at-tax-quantity) at (2.75,1.45);",
            r"\draw[very thick] (seller-price-at-tax-quantity) -- (buyer-price-at-tax-quantity) node[midway,right] {tax wedge};",
            r"\draw[dashed] (0.45,2.55) -- (buyer-price-at-tax-quantity) node[left] {$P_b$}; \draw[dashed] (0.45,1.45) -- (seller-price-at-tax-quantity) node[left] {$P_s$};",
            r"\draw[dashed] (tax-quantity) -- (seller-price-at-tax-quantity); \node[anchor=north] at (tax-quantity) {$Q_t$};",
            r"\fill[green!15] (0.55,1.95) rectangle (2.75,2.55); \fill[orange!18] (0.55,1.45) rectangle (2.75,1.95);",
            r"\node[font=\scriptsize] at (1.65,2.18) {buyer incidence}; \node[font=\scriptsize] at (1.65,1.72) {seller incidence};",
        ]
    return parts + [
        r"\draw[very thick] (2.7,1.45) -- (2.7,2.55) node[midway,right] {tax wedge};",
        r"\fill[blue!12] (0.65,1.45) rectangle (2.7,2.55); \node at (1.55,2.0) {revenue};",
        r"\fill[orange!28] (2.7,1.45) -- (2.7,2.55) -- (3.8,2.0) -- cycle;",
        r"\node at (3.15,1.2) {DWL};",
    ]


def _game_matrix(ctx: _FigureContext) -> list[str]:
    keys = (
        ("row_aa", "column_aa"),
        ("row_ab", "column_ab"),
        ("row_ba", "column_ba"),
        ("row_bb", "column_bb"),
    )
    values = [
        (_format_value(ctx.setup[row]), _format_value(ctx.setup[column]))
        for row, column in keys
    ]
    parts = [
        r"\node at (3.2,3.45) {column player}; \node[rotate=90] at (0.45,1.75) {row player};",
        r"\draw[thick] (1.15,0.55) rectangle (5.25,3.05); \draw[thick] (3.2,0.55) -- (3.2,3.05); \draw[thick] (1.15,1.8) -- (5.25,1.8);",
        r"\node at (2.15,3.25) {strategy A}; \node at (4.2,3.25) {strategy B}; \node at (0.85,2.4) {A}; \node at (0.85,1.15) {B};",
        rf"\node at (2.15,2.4) {{({_label(values[0][0])}, {_label(values[0][1])})}};",
        rf"\node at (4.2,2.4) {{({_label(values[1][0])}, {_label(values[1][1])})}};",
        rf"\node at (2.15,1.15) {{({_label(values[2][0])}, {_label(values[2][1])})}};",
        rf"\node at (4.2,1.15) {{({_label(values[3][0])}, {_label(values[3][1])})}};",
    ]
    if ctx.model_id == "nash_equilibrium":
        parts.append(r"\draw[very thick,green!50!black] (1.35,1.95) rectangle (2.95,2.85) node[above right] {Nash equilibrium};")
        parts.append(r"\draw[->,thick,red!70!black] (5.65,1.75) -- (4.75,2.25) node[pos=0,left] {best responses};")
    elif ctx.model_id == "dominant_strategy":
        parts.append(r"\fill[green!9] (1.16,0.56) rectangle (5.24,1.79); \node at (3.2,0.3) {dominant strategy};")
        parts.append(r"\draw[->,thick,blue!70!black] (0.55,1.15) -- (1.1,1.15) node[pos=0,left] {payoff comparison};")
    return parts


def _economics_game(ctx: _FigureContext) -> list[str]:
    if ctx.model_id == "oligopoly_collusion":
        return [
            _axes(ctx),
            r"\draw[very thick,blue!70!black] (0.65,3.15) -- (5.25,0.65) node[pos=0.79,below left,font=\scriptsize] {firm 1 reaction curve};",
            r"\draw[very thick,red!70!black] (0.65,0.65) -- (5.25,3.15) node[pos=0.78,above left,font=\scriptsize] {firm 2 reaction curve};",
            r"\filldraw[blue!70!black] (2.95,1.9) circle (2.7pt) node[above right] {Cournot equilibrium};",
            r"\filldraw[green!50!black] (2.35,1.45) circle (2.7pt) node[below left] {collusive quantity};",
            r"\draw[->,very thick,orange!80!black] (2.9,1.82) -- (2.42,1.5) node[midway,below right,font=\scriptsize] {output restriction};",
            r"\node[draw,fill=white] at (4.65,0.35) {collusive price rises};",
        ]
    if ctx.model_id != "oligopoly":
        return _game_matrix(ctx)
    return [
        _axes(ctx),
        r"\draw[very thick,blue!70!black] (0.65,3.15) -- (5.25,0.65) node[pos=0.79,below left,font=\scriptsize] {firm 1 best response};",
        r"\draw[very thick,red!70!black] (0.65,0.65) -- (5.25,3.15) node[pos=0.78,above left,font=\scriptsize] {firm 2 best response};",
        r"\filldraw[green!50!black] (2.95,1.9) circle (2.5pt);",
        r"\draw[thin,green!50!black] (3.02,1.98) -- (3.35,2.28) node[anchor=south west,font=\scriptsize] {mutual best response};",
        r"\node[draw,fill=white] at (4.7,0.35) {payoffs};",
    ]


def _economics_isoquants(ctx: _FigureContext) -> list[str]:
    if ctx.model_id != "factor_input_markets":
        raise ValueError(
            f"economics isoquant renderer does not support model {ctx.model_id!r}"
        )
    return [
        _axes(ctx),
        r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.75,3.15) (1.25,2.35) (2.15,1.65) (3.45,1.05) (5.2,0.65)};",
        _bounded_right_annotation(
            "target isoquant", y=0.95, color="blue!70!black"
        ),
        r"\draw[very thick,orange!80!black] (0.55,3.2) -- (5.25,0.55);",
        _bounded_right_annotation(
            "isocost", y=0.45, color="orange!80!black", anchor="north east"
        ),
        r"\filldraw[green!50!black] (2.55,1.45) circle (2.7pt) node[above right] {tangency};",
        r"\draw[dashed] (2.55,0) -- (2.55,1.45); \draw[dashed] (0,1.45) -- (2.55,1.45);",
        r"\node[draw,fill=white] at (4.65,3.1) {MRTS = factor price ratio};",
        r"\node[anchor=north] at (2.55,-0.08) {labor}; \node[anchor=east] at (-0.08,1.45) {capital};",
    ]


def _firm_marginal_curve(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    parts = [_axes(ctx)]
    if model == "price_discrimination":
        return parts + [
            r"\draw[very thick,red!70!black] (0.45,3.15) -- (2.55,1.25) node[right] {$D_1$}; \draw[very thick,red!45!black,dashed] (0.45,2.55) -- (2.25,0.65) node[right] {$MR_1$};",
            r"\draw[very thick,blue!70!black] (3.2,3.15) -- (5.35,1.25); \draw[very thick,blue!45!black,dashed] (3.2,2.55) -- (5.0,0.65) node[pos=0.5,above right,font=\scriptsize] {$MR_2$}; % semantic alias {MR 2}",
            r"\node[anchor=south east,blue!70!black] at (5.85,1.4) {$D_2$}; % semantic alias {D 2}",
            r"\draw[very thick,green!50!black] (0.35,1.0) -- (5.45,1.0);",
            r"\node[anchor=north east,green!50!black] at (5.85,0.9) {$MC$}; % semantic alias {MC}",
            r"\node at (1.45,3.45) {$P_1$}; \node at (4.25,3.45) {$P_2$};",
        ]
    if model == "marginal_revenue":
        return parts + [
            r"\draw[very thick,red!70!black] (0.55,3.2) -- (5.3,1.05) node[right] {demand};",
            r"\draw[very thick,blue!70!black] (0.55,2.8) -- (3.75,0.35) node[right] {marginal revenue};",
            r"\draw[very thick,green!50!black] plot[smooth] coordinates {(0.5,0.45) (1.5,1.5) (2.7,2.15) (3.9,2.05) (5.15,0.75)} node[right] {TR};",
            r"\filldraw (2.75,1.85) circle (2.4pt) node[above] {MR};",
        ]
    if model == "competitive_shutdown":
        return parts + [
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.55,2.9) (1.5,1.55) (2.8,0.85) (4.1,1.5) (5.25,2.8)} node[right] {AVC};",
            r"\draw[very thick,red!70!black] (0.55,0.75) -- (5.25,3.2) node[right] {MC};",
            r"\draw[very thick,green!50!black] (0.4,0.65) -- (5.35,0.65) node[right] {P};",
            r"\filldraw (2.55,0.75) circle (2.4pt) node[above] {shutdown point}; \node at (0.8,0.3) {q=0};",
        ]
    if model == "perfect_competition":
        return parts + [
            r"\draw[very thick,green!50!black] (0.45,2.0) -- (5.35,2.0) node[right] {P=MR};",
            r"\draw[very thick,red!70!black] plot[smooth] coordinates {(0.65,0.55) (1.8,0.85) (3.0,1.55) (4.25,2.55) (5.15,3.35)} node[right] {MC};",
            r"\draw[dashed] (3.55,0) -- (3.55,2.0); \node[anchor=north,font=\scriptsize] at (3.55,-0.08) {q*};",
            r"\fill[blue!10] (2.25,1.15) rectangle (3.55,2.0); \node[anchor=east,font=\scriptsize] at (3.38,1.55) {profit or loss};",
        ]
    return parts + [
        r"\draw[very thick,red!70!black] (0.55,3.2) -- (5.35,0.8) node[right] {$D$};",
        r"\draw[very thick,red!45!black,dashed] (0.55,2.75) -- (3.95,0.35) node[right] {$MR$};",
        r"\draw[very thick,green!50!black] (0.4,1.25) -- (5.35,1.25) node[right] {$MC$};",
        r"\draw[dashed] (2.7,0) -- (2.7,1.25) node[below] {$q_m$};",
        r"\draw[dashed] (0,2.15) -- (2.7,2.15) node[left] {$P_m$};",
    ]


def _social_marginal_curve(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    parts = [_axes(ctx)]
    if model == "health_economics":
        return parts + [
            r"\draw[very thick,red!70!black] (0.55,3.2) -- (5.25,0.65) node[right] {marginal benefit};",
            r"\draw[thick,blue!45!black,dashed] (0.55,0.55) -- (5.05,2.55) node[pos=0.78,below right,font=\scriptsize] {private cost};",
            r"\draw[very thick,blue!70!black] (0.55,0.65) -- (5.25,3.0) node[pos=0.82,above left,font=\scriptsize] {social cost};",
            r"\coordinate (patient-quantity) at (4.35,0); \coordinate (patient-price-at-demand) at (4.35,0.92);",
            r"\draw[very thick,orange!80!black] (0.45,0.92) -- (patient-price-at-demand) node[pos=0.04,above right,font=\scriptsize] {patient price};",
            r"\draw[dashed] (patient-quantity) -- (patient-price-at-demand); \node[anchor=north,font=\scriptsize] at (patient-quantity) {patient demand};",
            r"\filldraw[green!50!black] (3.0,2.0) circle (2.4pt) node[above] {efficient quantity};",
            r"\draw[<->,thick,orange!80!black] (3.0,0.35) -- (4.35,0.35) node[midway,below,font=\scriptsize] {insurance overuse};",
        ]
    if model == "public_good":
        return parts + [
            r"\draw[thick,red!45!black] (0.55,2.6) -- (5.25,0.55) node[right] {$MB_1+MB_2$};",
            r"\draw[very thick,red!70!black] (0.55,3.35) -- (5.25,1.25) node[right] {$SMB$};",
            r"\draw[very thick,blue!70!black] (0.55,0.65) -- (5.25,3.05) node[right] {$MC$};",
            r"\filldraw (3.05,2.2) circle (2.4pt) node[above] {$G^*$};",
        ]
    if model == "coase_bargaining":
        return parts + [
            r"\draw[very thick,red!70!black] (0.55,3.2) -- (5.25,0.65) node[right] {marginal benefit};",
            r"\draw[very thick,blue!70!black] (0.55,0.65) -- (5.25,3.2) node[right] {marginal cost};",
            r"\filldraw (2.9,1.9) circle (2.4pt) node[above] {efficient abatement};",
            r"\draw[<->,thick,green!50!black] (1.4,0.4) -- (4.35,0.4) node[midway,below] {bargaining range};",
        ]
    parts.extend(
        [
            r"\draw[very thick,red!70!black] (0.55,3.2) -- (5.25,0.65) node[right] {marginal benefit};",
            r"\draw[very thick,blue!70!black] (0.55,0.65) -- (5.25,3.0) node[pos=0.82,below right,font=\scriptsize] {private cost};",
            r"\draw[very thick,blue!45!black,dashed] (0.55,1.15) -- (5.0,3.45) node[pos=0.78,above left,font=\scriptsize] {social cost};",
            r"\filldraw (2.55,1.65) circle (2.4pt) node[below] {market quantity};",
            r"\filldraw[green!50!black] (3.0,2.0) circle (2.4pt) node[above] {efficient quantity};",
        ]
    )
    if model in {"externality", "common_resource", "health_economics"}:
        parts.append(r"\draw[<->,thick,orange!80!black] (2.55,0.35) -- (3.0,0.35) node[midway,below] {wedge / gap};")
    return parts


def _information_curve(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    if model == "choice_under_uncertainty":
        return [
            r"\draw[thick] (0.65,1.8) -- (5.35,1.8);",
            r"\filldraw[red!70!black] (1.15,1.8) circle (3pt) node[above] {loss state}; \filldraw[green!50!black] (4.85,1.8) circle (3pt) node[above] {no loss state};",
            r"\draw[->,very thick,blue!70!black] (2.0,2.75) -- (3.0,2.0) -- (4.0,2.75) node[right] {probabilities};",
            r"\filldraw (3.0,1.8) circle (2.5pt) node[below] {expected utility};",
            r"\node[draw,fill=white] at (3.0,0.65) {certainty equivalent};",
        ]
    if model == "social_insurance":
        return [
            r"\node[draw,fill=red!8] at (1.15,2.65) {loss state}; \node[draw,fill=green!10] at (1.15,1.0) {no loss state};",
            r"\node[draw,fill=red!4,font=\scriptsize] at (4.35,2.25) {loss consumption}; \node[draw,fill=green!5,font=\scriptsize] at (4.35,1.4) {no loss consumption};",
            r"\draw[->,very thick,blue!70!black] (1.8,1.0) -- (3.65,1.4) node[midway,below,font=\scriptsize] {contribution};",
            r"\draw[->,very thick,green!50!black] (1.8,2.65) -- (3.65,2.25) node[midway,above,font=\scriptsize] {benefit};",
            r"\draw[<->,thick] (5.25,1.4) -- (5.25,2.25); \draw[thin] (5.25,1.4) -- (4.85,0.72); \node[anchor=north,font=\scriptsize] at (4.85,0.68) {consumption gap};",
        ]
    if model == "adverse_selection":
        return [
            r"\node[draw,fill=red!8,minimum width=1.5cm] at (1.15,2.5) {high risk}; \node[draw,fill=green!8,minimum width=1.5cm] at (1.15,1.05) {low risk};",
            r"\draw[very thick,blue!70!black] (2.3,1.8) -- (5.25,1.8) node[right] {pooling premium};",
            r"\draw[->,thick] (1.95,2.5) -- (3.2,1.8); \draw[->,thick] (1.95,1.05) -- (3.2,1.8);",
            r"\node[draw,fill=white] at (4.55,2.75) {private information};",
            r"\node at (4.45,0.75) {enrollment};",
        ]
    if model == "moral_hazard":
        return [
            _axes(ctx),
            r"\draw[very thick,red!70!black] (0.55,0.65) -- (5.25,3.1) node[right] {loss probability};",
            r"\filldraw (1.55,1.15) circle (2.4pt) node[below] {uncovered effort}; \filldraw[orange!80!black] (4.25,2.55) circle (2.4pt) node[above] {covered effort};",
            r"\draw[->,very thick,blue!70!black] (1.65,1.3) -- (4.1,2.45) node[midway,above] {coverage};",
            r"\node[draw,fill=white] at (4.75,0.55) {private action};",
        ]
    if model == "equity_efficiency":
        return [
            _axes(ctx),
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.55,3.25) (1.55,2.85) (2.8,2.15) (4.0,1.25) (5.25,0.55)} node[right] {efficient frontier};",
            r"\filldraw[red!70!black] (1.55,1.1) circle (2.5pt) node[below] {before}; \filldraw[green!50!black] (2.75,2.1) circle (2.5pt) node[above] {after};",
            r"\draw[->,very thick] (1.55,1.1) -- (2.75,2.1) node[midway,below right] {social welfare};",
        ]
    return [
        r"\node[draw,fill=blue!8,minimum width=1.2cm] at (1.2,1.5) {now}; \node[draw,fill=green!8,minimum width=1.2cm] at (4.8,1.5) {later};",
        r"\draw[->,very thick,green!50!black] (1.8,2.15) -- (4.2,2.15) node[midway,above] {benchmark};",
        r"\draw[->,very thick,red!70!black] (4.2,0.85) -- (1.8,0.85) node[midway,below] {observed choice};",
        r"\draw[<->,thick,orange!80!black] (2.3,1.5) -- (3.7,1.5) node[midway,above] {bias gap};",
    ]


def _economics_curve(ctx: _FigureContext) -> list[str]:
    model = ctx.model_id
    if model in {
        "perfect_competition",
        "competitive_shutdown",
        "monopoly",
        "marginal_revenue",
        "price_discrimination",
    }:
        return _firm_marginal_curve(ctx)
    if model in {
        "externality",
        "coase_bargaining",
        "common_resource",
        "public_good",
        "health_economics",
    }:
        return _social_marginal_curve(ctx)
    if model in {
        "choice_under_uncertainty",
        "social_insurance",
        "adverse_selection",
        "moral_hazard",
        "equity_efficiency",
        "behavioral_economics",
    }:
        return _information_curve(ctx)
    if model == "cost_curves":
        return [
            _axes(ctx),
            r"\draw[very thick,gray!70] (0.4,0.85) -- (5.35,0.85) node[right] {FC};",
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.5,0.45) (1.5,0.75) (2.7,1.25) (4.0,2.1) (5.2,3.25)}; \node[blue!70!black,font=\scriptsize] at (4.78,2.82) {VC};",
            r"\draw[very thick,red!70!black] plot[smooth] coordinates {(0.5,1.3) (1.5,1.55) (2.7,2.0) (4.0,2.75) (5.1,3.45)}; \node[red!70!black,font=\scriptsize] at (4.28,3.25) {TC};",
            r"\draw[very thick,green!50!black] plot[smooth] coordinates {(0.55,3.2) (1.5,2.0) (2.8,1.45) (4.1,1.7) (5.25,2.6)}; \node[green!50!black,font=\scriptsize] at (4.72,2.18) {AC};",
            r"\draw[very thick,orange!80!black,dashed] (0.65,0.55) -- (5.05,3.15); \node[orange!80!black,font=\scriptsize] at (3.9,2.85) {MC};",
        ]
    if model == "production_function":
        return [
            _axes(ctx),
            r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.4,0.45) (1.2,1.35) (2.2,2.05) (3.4,2.55) (4.7,2.9) (5.45,3.05)} node[pos=0.86,above left,font=\scriptsize] {$q=f(L,K;A)$};",
            r"\filldraw[green!50!black] (3.4,2.55) circle (2.4pt); \node[anchor=south east,font=\scriptsize] at (3.28,2.62) {$q$};",
            r"\draw[very thick,red!70!black] (2.05,2.05) -- (4.7,3.05) node[pos=0.82,above left,font=\scriptsize] {$MP_L$};",
            r"\node at (1.2,0.35) {factor input};",
        ]
    parts = [_axes(ctx)]
    if model == "factor_input_markets":
        return parts + [
            r"\draw[very thick,blue!70!black] (0.55,3.15) -- (3.0,0.65) node[right] {MRP L};",
            r"\draw[very thick,red!70!black] (3.1,3.15) -- (5.55,0.65) node[right] {MRP K};",
            r"\draw[thick,green!50!black] (0.45,1.35) -- (2.95,1.35) node[right] {wage};",
            r"\draw[thick,orange!80!black] (3.05,1.8) -- (5.5,1.8) node[right] {rental price};",
        ]
    return parts + [
        r"\draw[very thick,blue!70!black] plot[smooth] coordinates {(0.55,3.15) (1.45,2.45) (2.7,1.65) (4.0,1.05) (5.35,0.65)} node[right] {marginal curve};",
        r"\draw[very thick,green!50!black] (0.45,1.45) -- (5.4,1.45) node[right] {input price};",
        r"\filldraw (3.05,1.45) circle (2.4pt) node[above] {choice};",
    ]


_RENDERERS: Final[Mapping[str, Callable[[_FigureContext], list[str]]]] = {
    "physics_force": _physics_force,
    "physics_kinematics": _physics_kinematics,
    "physics_vector": _physics_vector,
    "physics_center_of_mass": _physics_center_of_mass,
    "physics_rocket": _physics_rocket,
    "physics_mass_transfer": _physics_rocket,
    "physics_ode": _physics_ode,
    "physics_work": _physics_work,
    "physics_energy": _physics_energy,
    "physics_momentum": _physics_momentum,
    "physics_potential": _physics_potential,
    "physics_circular": _physics_circular,
    "physics_rotation": _physics_rotation,
    "physics_recoil": _physics_recoil,
    "physics_wave": _physics_wave,
    "econ_supply_demand": _economics_market,
    "econ_budget": _economics_budget,
    "econ_elasticity": _economics_elasticity,
    "econ_tax_wedge": _economics_tax,
    "econ_production_isoquants": _economics_isoquants,
    "game_payoff": _economics_game,
    "econ_curve": _economics_curve,
}


def render_fibonacci_memo_figure(
    target: int = 7,
) -> tuple[str, list[str]]:
    """Render a top-down Fibonacci dependency DAG above its memo table."""

    if isinstance(target, bool) or not isinstance(target, int) or target < 2:
        raise ValueError("target must be an integer of at least 2")
    if target > 12:
        raise ValueError("target must be at most 12 for a readable notes figure")

    x_step = 5.2 / target
    nodes = []
    for n in range(target, -1, -1):
        x = 0.4 + (target - n) * x_step
        nodes.append(
            rf"\node[draw,circle,minimum size=0.62cm,inner sep=1pt] "
            rf"(fib-{n}) at ({_format_number(x)},2.75) {{$F_{n}$}};"
        )
    edges = [
        rf"\draw[->,thick] (fib-{n}) to[bend left=24] "
        rf"node[above,font=\scriptsize] {{$n-{delta}$}} (fib-{n-delta});"
        for n in range(target, 1, -1)
        for delta in (1, 2)
    ]
    cache_cells = []
    for n in range(target + 1):
        x = 0.4 + n * x_step
        cache_cells.append(
            rf"\node[draw,minimum width={_format_number(x_step)}cm,minimum height=0.58cm] "
            rf"(memo-{n}) at ({_format_number(x)},0.75) {{$F_{n}$}};"
        )
    body = "\n".join(
        [
            r"\node[anchor=west,font=\bfseries] at (0.25,3.5) {top-down calls: parent requests dependencies};",
            *nodes,
            *edges,
            r"\draw[->,very thick,blue!70!black] (fib-0.south) -- (memo-0.north) node[midway,left,font=\scriptsize] {store base};",
            r"\node[anchor=west,font=\bfseries] at (0.25,1.45) {memo fills on return: $F_0,F_1,\ldots,F_n$};",
            *cache_cells,
            rf"\draw[->,very thick,green!50!black] (memo-0.south west) -- (memo-{target}.south east) node[midway,below,font=\scriptsize] {{cached states are reused}};",
        ]
    )
    evidence = [
        "top-down root requests smaller dependencies",
        *(
            f"F({n})->F({n-delta})"
            for n in range(target, 1, -1)
            for delta in (1, 2)
        ),
        "memo stores values after dependencies return",
    ]
    return body, evidence


def render_complexity_growth_figure(
    sample_sizes: Sequence[int] = (1, 2, 4, 8, 16, 32),
) -> tuple[str, list[str]]:
    """Render readable growth curves with explicit input ticks and samples."""

    sizes = tuple(sample_sizes)
    if (
        len(sizes) < 3
        or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in sizes)
        or tuple(sorted(set(sizes))) != sizes
    ):
        raise ValueError("sample_sizes must be at least three increasing positive integers")

    def x_coordinate(index: int) -> float:
        return 0.55 + 4.75 * index / (len(sizes) - 1)

    raw_series = {
        "constant": [1.0 for _ in sizes],
        "logarithmic": [math.log2(n) + 1.0 for n in sizes],
        "linear": [float(n) for n in sizes],
        "quadratic": [float(n * n) for n in sizes],
    }
    colors = {
        "constant": "gray!75!black",
        "logarithmic": "green!50!black",
        "linear": "blue!70!black",
        "quadratic": "red!70!black",
    }
    parts = [
        r"\draw[->,thick] (0.35,0.35) -- (5.75,0.35) node[right] {input size $n$};",
        r"\draw[->,thick] (0.35,0.35) -- (0.35,3.55) node[above] {relative work};",
    ]
    for index, n in enumerate(sizes):
        x = x_coordinate(index)
        parts.append(
            rf"\draw ({_format_number(x)},0.27) -- ({_format_number(x)},0.43); "
            rf"\node[anchor=north,font=\scriptsize] at ({_format_number(x)},0.22) {{{n}}};"
        )
    max_value = max(raw_series["quadratic"])
    for name, values in raw_series.items():
        coordinates = []
        for index, value in enumerate(values):
            x = x_coordinate(index)
            y = 0.55 + 2.55 * math.log1p(value) / math.log1p(max_value)
            coordinates.append((x, y))
        coordinate_text = " ".join(
            f"({_format_number(x)},{_format_number(y)})" for x, y in coordinates
        )
        color = colors[name]
        parts.append(
            rf"\draw[very thick,{color}] plot[smooth] coordinates {{{coordinate_text}}};"
        )
        for index, (x, y) in enumerate(coordinates):
            parts.append(
                rf"\filldraw[{color}] ({_format_number(x)},{_format_number(y)}) circle (1.8pt) "
                rf"node[inner sep=0pt] (sample-{name}-{sizes[index]}) {{}};"
            )
        label = {
            "constant": r"$O(1)$",
            "logarithmic": r"$O(\log n)$",
            "linear": r"$O(n)$",
            "quadratic": r"$O(n^2)$",
        }[name]
        last_x, last_y = coordinates[-1]
        parts.append(
            rf"\node[anchor=west,font=\scriptsize,{color}] at "
            rf"({_format_number(last_x + 0.08)},{_format_number(last_y)}) {{{label}}};"
        )
    evidence = [
        f"sample n={n}: constant=1, logarithmic={_format_number(math.log2(n) + 1)}, "
        f"linear={n}, quadratic={n*n}"
        for n in sizes
    ]
    return "\n".join(parts), evidence


def render_model_scenario_figure(
    scenario: Mapping[str, object], visual_kind: str
) -> tuple[str, list[str]]:
    """Return a learner-facing TikZ body and machine-only evidence metadata."""

    ctx = _context(scenario, visual_kind)
    parts = _RENDERERS[visual_kind](ctx)
    parts.append(_quantity_legend(ctx))
    body = "\n".join(part for part in parts if part.strip()).strip()
    if not body:
        raise RuntimeError(f"empty TikZ body for model scenario {ctx.model_id!r}")
    return body, list(ctx.evidence_tokens)


def model_scenario_figure_body(
    scenario: Mapping[str, object], visual_kind: str
) -> tuple[str, list[str]]:
    """Compatibility spelling for :func:`render_model_scenario_figure`."""

    return render_model_scenario_figure(scenario, visual_kind)


def physics_model_scenario_figure_body(
    scenario: Mapping[str, object], visual_kind: str
) -> tuple[str, list[str]]:
    """Render a physics scenario and reject an economics visual kind."""

    if visual_kind not in PHYSICS_VISUAL_KINDS:
        raise ValueError(f"not a physics visual kind: {visual_kind!r}")
    return render_model_scenario_figure(scenario, visual_kind)


def economics_model_scenario_figure_body(
    scenario: Mapping[str, object], visual_kind: str
) -> tuple[str, list[str]]:
    """Render an economics scenario and reject a physics visual kind."""

    if visual_kind not in ECONOMICS_VISUAL_KINDS:
        raise ValueError(f"not an economics visual kind: {visual_kind!r}")
    return render_model_scenario_figure(scenario, visual_kind)


__all__ = [
    "ECONOMICS_VISUAL_KINDS",
    "MODEL_SCENARIO_VISUAL_KINDS",
    "PHYSICS_VISUAL_KINDS",
    "economics_model_scenario_figure_body",
    "figure_token_is_represented",
    "latex_escape_label",
    "model_scenario_figure_body",
    "normalize_figure_token",
    "physics_model_scenario_figure_body",
    "render_complexity_growth_figure",
    "render_fibonacci_memo_figure",
    "render_model_scenario_figure",
]

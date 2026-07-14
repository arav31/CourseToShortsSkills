"""Deterministic, renderer-neutral semantic models for economics videos.

The routes here describe what changes on screen.  They intentionally do not
depend on ``stem_course`` and do not ask a renderer to infer economic meaning
from a generic collection of curves.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
import re
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence
import unicodedata

try:
    from tools.economics_model_specs import (
        ECONOMICS_MODEL_REGISTRY,
        resolve_economics_model,
    )
    from tools.economics_model_scenarios import (
        economics_numeric_evidence_fingerprint,
        get_economics_model_scenario,
    )
except ModuleNotFoundError:  # Direct execution from tools/video_economics_models.py.
    from economics_model_specs import ECONOMICS_MODEL_REGISTRY, resolve_economics_model
    from economics_model_scenarios import (
        economics_numeric_evidence_fingerprint,
        get_economics_model_scenario,
    )


@dataclass(frozen=True)
class EconomicsVideoRoute:
    route_key: str
    family: str
    model_ids: frozenset[str]
    invariant: str
    verification: tuple[str, ...]
    object_roles: tuple[tuple[str, str], ...]
    steps: tuple[tuple[str, str, str], ...]
    changed_objects: tuple[str, ...]


@dataclass(frozen=True)
class GraphBox:
    """Axis-aligned graph-space bounds used by the renderer layout contract."""

    left: float
    right: float
    bottom: float
    top: float

    def expanded(self, padding: float) -> "GraphBox":
        return GraphBox(
            self.left - padding,
            self.right + padding,
            self.bottom - padding,
            self.top + padding,
        )

    def overlaps(self, other: "GraphBox") -> bool:
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.top <= other.bottom
            or self.bottom >= other.top
        )


@dataclass(frozen=True)
class GraphLabelPlacement:
    center: tuple[float, float]
    bounds: GraphBox
    leader: tuple[tuple[float, float], tuple[float, float]] | None


@dataclass(frozen=True)
class GraphGuideSweep:
    """Conservative bounds covering every position of a moving graph guide."""

    bounds: GraphBox
    keyframes: tuple[GraphBox, ...]


@dataclass(frozen=True)
class PhoneCopyStage:
    """One readable explanatory beat rendered without reducing font size."""

    lines: tuple[str, ...]
    font_size: int


@dataclass(frozen=True)
class EconomicsFormulaSources:
    """Semantic TeX plus a font-independent fallback for visible formulas."""

    latex: str
    fallback: str


@dataclass(frozen=True)
class CournotMotionState:
    """Exact quantities used by the reaction-function animation."""

    demand_intercept: float
    demand_slope: float
    marginal_cost: float
    reaction_intercept: float
    reaction_slope: float
    nash_firm_quantity: float
    nash_total_quantity: float
    nash_price: float
    collusive_firm_quantity: float
    collusive_total_quantity: float
    collusive_price: float


def build_cournot_motion_state(
    demand_intercept: float,
    demand_slope: float,
    marginal_cost: float,
) -> CournotMotionState:
    """Build symmetric linear-Cournot states for causal on-screen motion."""
    intercept = float(demand_intercept)
    slope = float(demand_slope)
    cost = float(marginal_cost)
    if slope <= 0:
        raise ValueError("Cournot demand slope must be positive")
    if intercept <= cost:
        raise ValueError("Cournot demand intercept must exceed marginal cost")
    reaction_intercept = (intercept - cost) / (2.0 * slope)
    nash_firm_quantity = (intercept - cost) / (3.0 * slope)
    collusive_firm_quantity = (intercept - cost) / (4.0 * slope)
    nash_total = 2.0 * nash_firm_quantity
    collusive_total = 2.0 * collusive_firm_quantity
    return CournotMotionState(
        demand_intercept=intercept,
        demand_slope=slope,
        marginal_cost=cost,
        reaction_intercept=reaction_intercept,
        reaction_slope=-0.5,
        nash_firm_quantity=nash_firm_quantity,
        nash_total_quantity=nash_total,
        nash_price=intercept - slope * nash_total,
        collusive_firm_quantity=collusive_firm_quantity,
        collusive_total_quantity=collusive_total,
        collusive_price=intercept - slope * collusive_total,
    )


_UNICODE_MATH_ASCII = str.maketrans({
    "½": "1/2",
    "α": "alpha",
    "β": "beta",
    "δ": "delta",
    "Δ": "Delta",
    "ε": "epsilon",
    "η": "eta",
    "λ": "lambda",
    "μ": "mu",
    "π": "pi",
    "ρ": "rho",
    "σ": "sigma",
    "τ": "tau",
    "φ": "phi",
    "−": "-",
    "⁄": "/",
    "×": "x",
    "÷": "/",
    "≤": "<=",
    "≥": ">=",
    "≠": "!=",
    "∈": " in ",
    "∑": "sum",
    "→": "->",
})
_SUBSCRIPT_UNICODE_ASCII = str.maketrans({
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "ₐ": "a", "ᵦ": "b", "ₑ": "e", "ᵢ": "i", "ⱼ": "j", "ₖ": "k",
    "ₗ": "l", "ₘ": "m", "ₙ": "n", "ₒ": "o", "ₚ": "p", "ᵣ": "r",
    "ₛ": "s", "ₜ": "t", "ᵤ": "u", "ᵥ": "v", "ₓ": "x",
    "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
})
_SUBSCRIPT_CHARS = "₀₁₂₃₄₅₆₇₈₉ₐᵦₑᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ₊₋₌"


def economics_formula_sources(latex: str, plain: str | None = None) -> EconomicsFormulaSources:
    """Return semantic TeX and an ASCII-only fallback safe for Pango fonts.

    Economics notation frequently uses Unicode modifier letters for subscripts
    (notably ``ᵦ`` for buyer price). Their font coverage is unreliable. The
    fallback therefore spells indices as parentheses while retaining the TeX
    source for renderers with a working math backend.
    """
    if not isinstance(latex, str) or not latex.strip():
        raise ValueError("economics formula latex must be a non-empty string")
    source = plain if isinstance(plain, str) and plain.strip() else latex
    fallback = re.sub(
        "[" + _SUBSCRIPT_CHARS + "]+",
        lambda match: "(" + match.group(0).translate(_SUBSCRIPT_UNICODE_ASCII) + ")",
        source,
    )
    fallback = fallback.replace("₍", "(").replace("₎", ")")
    fallback = fallback.translate(_UNICODE_MATH_ASCII)
    fallback = unicodedata.normalize("NFKD", fallback)
    fallback = re.sub(r"([A-Za-z0-9)])\u0304", r"bar(\1)", fallback)
    fallback = fallback.translate(_UNICODE_MATH_ASCII)
    fallback = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"(\1)/(\2)", fallback)
    fallback = re.sub(r"\\(?:bar|overline)\s*\{([^{}]+)\}", r"bar(\1)", fallback)
    fallback = re.sub(r"_\s*\{([^{}]+)\}", r"(\1)", fallback)
    fallback = re.sub(r"_\s*([A-Za-z0-9+-]+)", r"(\1)", fallback)
    fallback = re.sub(r"\^\s*\{([^{}]+)\}", r"^(\1)", fallback)
    commands = {
        "leq": "<=", "geq": ">=", "neq": "!=", "in": " in ",
        "sum": "sum", "Delta": "Delta", "delta": "delta", "pi": "pi",
        "beta": "beta", "mu": "mu", "lambda": "lambda", "times": "x",
        "cdot": "*", "rightarrow": "->", "Rightarrow": "=>",
    }
    fallback = re.sub(
        r"\\([A-Za-z]+)",
        lambda match: commands.get(match.group(1), match.group(1)),
        fallback,
    )
    fallback = fallback.replace("{", "(").replace("}", ")")
    fallback = fallback.replace("\\", " ")
    fallback = " ".join(fallback.split())
    fallback = fallback.encode("ascii", "ignore").decode("ascii")
    if not fallback:
        raise ValueError("economics formula fallback is empty")
    return EconomicsFormulaSources(latex=latex.strip(), fallback=fallback)


def _centered_box(center: tuple[float, float], size: tuple[float, float]) -> GraphBox:
    x, y = center
    width, height = size
    return GraphBox(x - width / 2, x + width / 2, y - height / 2, y + height / 2)


def economics_guide_sweep(keyframes: Sequence[GraphBox]) -> GraphGuideSweep:
    """Return the full swept corridor for a translating or staged guide.

    The union is deliberately conservative: labels avoid the entire animation
    trajectory, including positions between keyframes, rather than only the
    guide's initial and final bounds.
    """
    frames = tuple(keyframes)
    if len(frames) < 2:
        raise ValueError("a moving guide sweep requires at least two keyframes")
    return GraphGuideSweep(
        bounds=GraphBox(
            min(frame.left for frame in frames),
            max(frame.right for frame in frames),
            min(frame.bottom for frame in frames),
            max(frame.top for frame in frames),
        ),
        keyframes=frames,
    )


def stage_phone_readable_copy(
    text: str,
    *,
    min_font_size: int = 30,
    max_chars_per_line: int = 34,
    max_lines: int = 2,
) -> tuple[PhoneCopyStage, ...]:
    """Wrap complete sentences into phone-sized stages without orphan fragments."""
    words = text.split()
    if not words:
        raise ValueError("phone copy must not be empty")
    if min_font_size <= 0 or max_chars_per_line <= 0 or max_lines <= 0:
        raise ValueError("phone copy layout limits must be positive")
    if any(len(word) > max_chars_per_line for word in words):
        raise ValueError("phone copy contains a word wider than the readable line")
    sentences = [part.strip() for part in re.findall(r"[^.!?]+[.!?]?", text) if part.strip()]
    stages: list[PhoneCopyStage] = []
    for sentence in sentences:
        sentence_words = sentence.split()
        lines: list[str] = []
        current = ""
        for word in sentence_words:
            candidate = word if not current else current + " " + word
            if len(candidate) <= max_chars_per_line:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        if len(lines) > max_lines:
            raise ValueError(
                "visible sentence exceeds one phone stage; concise it before rendering"
            )
        stages.append(PhoneCopyStage(tuple(lines), min_font_size))
    return tuple(stages)


def place_economics_graph_label(
    anchor: tuple[float, float],
    size: tuple[float, float],
    plot_bounds: GraphBox,
    obstacles: Iterable[GraphBox | GraphGuideSweep],
    *,
    preferred_offsets: Sequence[tuple[float, float]] = (
        (0.0, 0.55),
        (0.7, 0.45),
        (-0.7, 0.45),
        (0.7, -0.45),
        (-0.7, -0.45),
        (1.0, 0.0),
        (-1.0, 0.0),
    ),
    clearance: float = 0.12,
    leader_threshold: float = 0.72,
) -> GraphLabelPlacement:
    """Place a graph label without intersecting curves, markers, or prior labels.

    Coordinates are renderer-neutral graph coordinates. Candidates are evaluated
    in preference order and then by distance, so callers can tune visual intent
    without coupling placement to a model or short identifier.
    """
    if size[0] <= 0 or size[1] <= 0:
        raise ValueError("label size must be positive")
    blocked = tuple(
        (obstacle.bounds if isinstance(obstacle, GraphGuideSweep) else obstacle).expanded(clearance)
        for obstacle in obstacles
    )
    candidates: list[tuple[float, int, tuple[float, float], GraphBox]] = []
    for priority, (dx, dy) in enumerate(preferred_offsets):
        for scale in (1.0, 1.5, 2.0, 3.0):
            scaled_dx, scaled_dy = dx * scale, dy * scale
            center = (anchor[0] + scaled_dx, anchor[1] + scaled_dy)
            box = _centered_box(center, size)
            inside = (
                box.left >= plot_bounds.left
                and box.right <= plot_bounds.right
                and box.bottom >= plot_bounds.bottom
                and box.top <= plot_bounds.top
            )
            if inside and not any(box.overlaps(obstacle) for obstacle in blocked):
                candidates.append((hypot(scaled_dx, scaled_dy), priority, center, box))
    if not candidates:
        raise ValueError("no collision-free graph label position inside plot bounds")
    _distance, _priority, center, box = min(candidates, key=lambda row: (row[1], row[0]))
    displacement = hypot(center[0] - anchor[0], center[1] - anchor[1])
    leader = (anchor, center) if displacement >= leader_threshold else None
    return GraphLabelPlacement(center=center, bounds=box, leader=leader)


def _route(
    family: str,
    model_ids: tuple[str, ...],
    invariant: str,
    verification: tuple[str, ...],
    object_roles: tuple[tuple[str, str], ...],
    steps: tuple[tuple[str, str, str], ...],
    changed_objects: tuple[str, ...] = (),
) -> EconomicsVideoRoute:
    if len(steps) < 3:
        raise ValueError(f"economics route {family!r} requires at least three causal steps")
    return EconomicsVideoRoute(
        route_key=f"economics:{family}",
        family=family,
        model_ids=frozenset(model_ids),
        invariant=invariant,
        verification=verification,
        object_roles=object_roles,
        steps=steps,
        changed_objects=changed_objects,
    )


ECONOMICS_VIDEO_ROUTES: tuple[EconomicsVideoRoute, ...] = (
    _route(
        "supply_demand",
        ("supply_demand_intro", "market_equilibrium", "demand_curve", "supply_curve",
         "supply_demand_curves", "comparative_statics"),
        "At equilibrium, the quantity read from demand equals the quantity read from supply at one price.",
        ("demand quantity at P*", "supply quantity at P*", "Qd(P*) = Qs(P*)"),
        (("demand", "inverse demand schedule"), ("supply", "inverse supply schedule"),
         ("market", "market price and quantity marker")),
        (("draw_schedules", "Demand and supply are retained as distinct schedules.", "demand and supply visible"),
         ("clear_market", "Move the market marker to their intersection.", "P*=intersection; Qd=Qs=Q*"),
         ("project_market_values", "Project the clearing price and quantity from the retained intersection.", "same P* and Q* projected to both axes")),
    ),
    _route(
        "price_ceiling",
        ("price_ceiling_shortage",),
        "A binding ceiling lies below equilibrium and creates shortage equal to quantity demanded minus quantity supplied.",
        ("Pceiling < P*", "shortage = Qd(Pceiling) - Qs(Pceiling)"),
        (("demand", "demand schedule"), ("supply", "supply schedule"),
         ("ceiling", "binding maximum price"), ("shortage", "excess-demand span")),
        (("mark_equilibrium", "Resolve the unregulated market equilibrium first.", "P* and Q* retained"),
         ("lower_ceiling", "Move price below equilibrium while retaining both schedules.", "Pceiling=4"),
         ("measure_shortage", "Read demand and supply at the ceiling.", "shortage=Qd-Qs")),
    ),
    _route(
        "price_floor",
        ("price_floor_surplus",),
        "A binding floor lies above equilibrium and creates surplus equal to quantity supplied minus quantity demanded.",
        ("Pfloor > P*", "surplus = Qs(Pfloor) - Qd(Pfloor)"),
        (("demand", "demand schedule"), ("supply", "supply schedule"),
         ("floor", "binding minimum price"), ("surplus", "excess-supply span")),
        (("mark_equilibrium", "Resolve the unregulated market equilibrium first.", "P* and Q* retained"),
         ("raise_floor", "Move price above equilibrium while retaining both schedules.", "Pfloor=8"),
         ("measure_surplus", "Read supply and demand at the floor.", "surplus=Qs-Qd")),
    ),
    _route(
        "price_controls_comparison",
        ("price_controls",),
        "Ceilings and floors change opposite excess-quantity objects and must be measured separately.",
        ("ceiling shortage=Qd-Qs", "floor surplus=Qs-Qd"),
        (("market", "unchanged demand and supply"), ("ceiling", "maximum-price case"),
         ("floor", "minimum-price case"), ("gaps", "shortage and surplus spans")),
        (("mark_unregulated_equilibrium", "Retain the common unregulated market benchmark.", "P* and Q* retained"),
         ("measure_ceiling_case", "Measure excess demand below equilibrium.", "ceiling shortage"),
         ("measure_floor_case", "Replace it with excess supply above equilibrium.", "floor surplus")),
    ),
    _route(
        "surplus",
        ("consumer_surplus", "producer_surplus", "total_surplus", "welfare_surplus"),
        "Surplus is an area between willingness to pay or marginal cost and the traded-price benchmark.",
        ("CS is above price and below demand", "PS is below price and above supply", "TS=CS+PS"),
        (("demand", "willingness-to-pay boundary"), ("supply", "marginal-cost boundary"),
         ("price", "market price"), ("surplus", "named welfare area")),
        (("construct_consumer_surplus", "Measure willingness to pay above the retained market price.", "CS area below demand and above price"),
         ("construct_producer_surplus", "Measure gains above marginal cost at that same traded quantity.", "PS area above supply and below price"),
         ("sum_total_surplus", "Combine consumer and producer areas without changing price or quantity.", "TS=CS+PS")),
    ),
    _route(
        "equity_efficiency",
        ("equity_efficiency",),
        "A distributional move changes who gains and loses separately from the total-welfare change.",
        ("efficiency change=sum of utility changes", "equity change=before gap-after gap"),
        (("before", "initial utility distribution"), ("after", "changed utility distribution"),
         ("efficiency", "total welfare comparison"), ("equity", "utility-gap comparison")),
        (("measure_initial_distribution", "Retain the initial total utility and utility gap as separate baselines.", "before total and before gap"),
         ("move_distribution", "Move both individual utility coordinates to the new allocation.", "one winner and one loser"),
         ("compare_equity_efficiency", "Measure total and gap changes as separate objects.", "efficiency change and equity-gap reduction")),
    ),
    _route(
        "international_trade",
        ("international_trade",),
        "At one world price, imports equal domestic demand minus domestic supply.",
        ("Pw < Pautarky", "imports = Qd(Pw) - Qs(Pw)", "domestic demand and supply use the same Pw"),
        (("demand", "domestic demand schedule"), ("supply", "domestic supply schedule"),
         ("autarky", "closed-economy equilibrium benchmark"),
         ("world_price", "horizontal world-price line"), ("imports", "horizontal import gap")),
        (("mark_autarky", "Resolve the domestic closed-economy benchmark first.", "autarky price=15 and quantity=40"),
         ("open_market", "Replace autarky price with the retained world price.", "Pw=10 below autarky price 15"),
         ("measure_imports", "Read domestic demand and supply at that same price.", "imports=60-30=30")),
        ("autarky", "world_price", "imports"),
    ),
    _route(
        "tariff",
        ("tariff",),
        "A small-country tariff raises the domestic price by exactly t and reduces imports.",
        ("Pdomestic = Pw + t", "imports after = Qd(Pw+t) - Qs(Pw+t)", "tariff revenue = t*imports after"),
        (("demand", "unchanged domestic demand"), ("supply", "unchanged domestic supply"),
         ("world_price", "free-trade price line"), ("tariff_price", "world price plus tariff"),
         ("imports", "before-and-after import gaps"), ("revenue", "tariff revenue")),
        (("raise_domestic_price", "Move the price line from Pw to Pw+t while retaining both schedules.", "13=10+3"),
         ("contract_imports", "Move both quantity endpoints inward at the tariff price.", "imports fall from 30 to 12"),
         ("account_tariff_revenue", "Construct revenue from tariff times remaining imports.", "revenue=3*12=36")),
        ("tariff_price", "imports", "revenue"),
    ),
    _route(
        "labor_market",
        ("labor_market", "labor_input_market"),
        "Labor demand is derived from worker revenue product, and employment clears where labor demand equals labor supply.",
        ("Ld(w*) = Ls(w*)", "MRP(L) is labor demand", "employment=60 and wage=10"),
        (("labor_demand", "derived labor demand or MRP"), ("labor_supply", "labor supply"),
         ("wage", "equilibrium wage"), ("employment", "equilibrium employment")),
        (("derive_labor_demand", "Construct labor demand from marginal revenue product.", "labor demand is MRP"),
         ("clear_labor_market", "Intersect labor demand and labor supply.", "equilibrium wage=10"),
         ("mark_employment", "Project the same crossing to the employment axis.", "labor demanded=labor supplied=employment=60")),
        ("labor_demand", "wage", "employment"),
    ),
    _route(
        "budget_choice",
        ("consumer_preferences", "utility_representation", "budget_constraint",
         "marginal_rate_of_substitution", "consumer_choice", "income_substitution_effects"),
        "The chosen bundle remains feasible and lies on the highest attainable indifference curve.",
        ("px*x + py*y <= income", "MRS = px/py", "chosen bundle feasible"),
        (("budget", "budget line and feasible set"), ("preference", "ordered indifference curves"),
         ("choice", "chosen consumption bundle")),
        (("reveal_feasible_set", "Retain only bundles satisfying the budget.", "feasible set bounded by budget"),
         ("rank_attainable_curves", "Compare attainable indifference curves without changing prices or income.", "highest attainable preference contour"),
         ("select_tangency", "Move the same bundle marker to the highest attainable curve.", "MRS=px/py at choice")),
    ),
    _route(
        "intertemporal_choice",
        ("intertemporal_choice",),
        "Consumption now and later must satisfy one present-value budget, with slope -(1+r).",
        ("c1+c2/(1+r)=y1+y2/(1+r)", "saving=y1-c1", "borrowing implies saving<0"),
        (("budget", "intertemporal budget line"), ("endowment", "income endowment"),
         ("choice", "chosen dated-consumption bundle"), ("transfer", "saving or borrowing transfer")),
        (("mark_endowment", "Place the income endowment on the retained intertemporal budget.", "endowment=(y1,y2)"),
         ("choose_dated_bundle", "Move along the same present-value budget to the chosen bundle.", "chosen c1 and c2 exhaust present-value wealth"),
         ("measure_transfer", "Measure saving or borrowing from current income to current consumption.", "saving=y1-c1")),
    ),
    _route(
        "expected_utility",
        ("choice_under_uncertainty",),
        "Expected utility probability-weights state utilities; its certainty equivalent need not equal expected payoff.",
        ("EU=sum p_s u(c_s)", "CE=u^-1(EU)", "risk premium=E[c]-CE"),
        (("states", "state-contingent payoffs"), ("probabilities", "state probabilities"),
         ("expected_utility", "probability-weighted utility"), ("certainty_equivalent", "certain payoff with equal utility")),
        (("weight_states", "Apply each probability to its retained state utility.", "probabilities sum to one"),
         ("locate_expected_utility", "Sum the weighted state utilities.", "EU=sum p_s u(c_s)"),
         ("measure_risk_premium", "Compare expected payoff with the certainty equivalent.", "risk premium=E[c]-CE")),
    ),
    _route(
        "social_insurance",
        ("social_insurance",),
        "A contribution lowers no-loss consumption while a benefit raises loss-state consumption, narrowing the state gap.",
        ("c_loss=W-loss-contribution+benefit", "c_no_loss=W-contribution", "gap=c_no_loss-c_loss"),
        (("loss_state", "consumption in the covered loss state"), ("no_loss_state", "consumption without a loss"),
         ("contribution", "social-insurance contribution"), ("benefit", "loss-state transfer"),
         ("gap", "remaining consumption gap")),
        (("collect_contribution", "Deduct the contribution in both retained states.", "contribution=10"),
         ("pay_benefit", "Add the benefit only in the loss state.", "benefit=40"),
         ("measure_smoothing", "Measure the remaining state-consumption gap.", "gap=c_no_loss-c_loss")),
    ),
    _route(
        "present_bias",
        ("behavioral_economics",),
        "Present bias multiplies delayed value by beta today and can reverse the benchmark later choice.",
        ("benchmark=delta^t u_later", "behavioral=beta*benchmark", "0<beta<1"),
        (("now", "immediate utility"), ("later", "long-run discounted utility"),
         ("present_bias", "beta wedge on delayed utility"), ("choice", "benchmark and observed choice indicators")),
        (("discount_later", "Apply long-run discounting to the delayed payoff.", "benchmark later value"),
         ("apply_present_bias", "Apply beta only when the delayed payoff is evaluated from now.", "behavioral value=beta*benchmark"),
         ("compare_choices", "Compare benchmark and present-biased choice indicators.", "preference reversal exposed")),
    ),
    _route(
        "elasticity",
        ("own_price_elasticity", "income_elasticity", "cross_price_elasticity"),
        "Elasticity compares a named quantity response with the proportional change in its named driver.",
        ("percent quantity response", "percent named-driver change", "elasticity = response/driver"),
        (("baseline", "baseline quantity and driver values"), ("changed", "changed quantity and driver values"),
         ("ratio", "signed elasticity and classification")),
        (("establish_baseline", "Retain the initial quantity and named driver values.", "baseline quantity and driver"),
         ("measure_changes", "Replace baseline values with exact proportional changes.", "%delta Q and %delta driver"),
         ("classify_response", "Divide the retained quantity response by its named driver change.", "signed elasticity classified")),
    ),
    _route(
        "tax",
        ("tax_incidence", "tax_deadweight_loss"),
        "The buyer price minus the seller price equals the per-unit tax at every taxed trade.",
        ("Pb - Ps = t", "Qt <= Q0", "tax revenue = t*Qt"),
        (("market", "pre-tax demand and supply market"), ("wedge", "buyer-seller price wedge"),
         ("quantity", "pre-tax and taxed quantity markers"), ("welfare", "revenue and deadweight regions")),
        (("insert_wedge", "Separate buyer and seller prices by exactly t.", "Pb-Ps=t"),
         ("contract_trade", "Move quantity from Q0 to Qt while retaining the wedge.", "Qt<=Q0"),
         ("account_welfare", "Partition the retained wedge into revenue and lost trades.", "revenue=t*Qt; DWL on Q0-Qt")),
    ),
    _route(
        "game",
        ("strategic_game", "nash_equilibrium", "dominant_strategy"),
        "Each highlighted strategy is evaluated against the other player's retained strategy.",
        ("same payoff matrix", "best response for player 1", "best response for player 2"),
        (("matrix", "persistent strategy and payoff matrix"), ("row_response", "player one best response"),
         ("column_response", "player two best response"), ("outcome", "mutual-best-response outcome")),
        (("mark_row_response", "Hold the column fixed and mark player one's best response.", "row payoff maximized within column"),
         ("mark_column_response", "Hold the row fixed and mark player two's best response.", "column payoff maximized within row"),
         ("resolve_outcome", "Retain cells marked for both players.", "mutual best response identified")),
    ),
    _route(
        "externality_wedge",
        ("externality",),
        "MSC equals MPC plus marginal external cost, so the corrective quantity is where demand meets MSC, not MPC.",
        ("MSC = MPC + MEC", "Qsocial from demand=MSC", "Qsocial <= Qprivate"),
        (("demand", "marginal benefit or demand curve"), ("mpc", "marginal private cost curve"),
         ("msc", "marginal social cost curve"), ("wedge", "MEC wedge between MSC and MPC"),
         ("quantity", "private and corrective quantity markers")),
        (("expose_external_cost", "Lift MSC above retained MPC by the exact MEC wedge.", "vertical wedge=MSC-MPC=MEC"),
         ("mark_private_quantity", "Intersect demand with MPC and retain Qprivate.", "demand=MPC at Qprivate"),
         ("correct_quantity", "Move the policy marker to demand=MSC while retaining Qprivate.", "demand=MSC at Qsocial; Qsocial<=Qprivate")),
    ),
    _route(
        "coase_bargaining",
        ("coase_bargaining",),
        "Bargaining selects efficient abatement only when gains from agreement cover transaction costs.",
        ("MBabatement=MCabatement", "net gains=gross gains-transaction costs"),
        (("benefit", "marginal abatement benefit"), ("cost", "marginal abatement cost"),
         ("abatement", "efficient negotiated amount"), ("transaction_cost", "bargaining friction")),
        (("measure_gross_gains", "Accumulate gains where marginal benefit exceeds marginal cost.", "gross bargaining gains"),
         ("find_bargained_abatement", "Intersect marginal benefit and marginal cost.", "efficient abatement"),
         ("deduct_transaction_cost", "Deduct transaction cost from gross gains.", "net bargaining gains")),
    ),
    _route(
        "common_resource",
        ("common_resource",),
        "Open access ignores marginal external depletion cost, so use exceeds the social optimum.",
        ("MSC=MPC+MEC", "open-access quantity > efficient quantity"),
        (("benefit", "marginal private benefit"), ("private_cost", "marginal private cost"),
         ("social_cost", "marginal social cost"), ("overuse", "open-access quantity gap")),
        (("mark_open_access", "Intersect benefit with private cost.", "open-access quantity"),
         ("internalize_depletion", "Replace private cost with social cost.", "efficient quantity"),
         ("measure_overuse", "Compare open-access use with the retained efficient quantity.", "overuse=open-access quantity-efficient quantity")),
    ),
    _route(
        "adverse_selection",
        ("adverse_selection",),
        "Hidden risk makes the pooling premium a weighted expected loss, not either type's fair premium.",
        ("pooling premium = 0.4*300 + 0.6*100", "pooling premium=180", "low-risk cross-subsidy=80"),
        (("types", "hidden high- and low-risk groups"), ("fair_premiums", "type-specific expected losses"),
         ("pool", "pooling premium"), ("enrollment", "low-risk enrollment response")),
        (("hide_risk_type", "Combine observable enrollment while retaining hidden type labels.", "risk type is private"),
         ("price_pool", "Replace type-specific prices with the weighted pooling premium.", "180 lies between 100 and 300"),
         ("show_selection_pressure", "Compare the pool price with the low-risk fair premium.", "low-risk cross-subsidy=80")),
        ("types", "pool", "enrollment"),
    ),
    _route(
        "moral_hazard",
        ("moral_hazard",),
        "Coverage changes the insured person's hidden effort and therefore changes loss probability.",
        ("coverage=80%", "effort falls 0.8 to 0.4", "loss probability rises 0.1 to 0.2"),
        (("coverage", "insurance coverage"), ("effort", "hidden prevention effort"),
         ("risk", "loss probability"), ("insurer_cost", "expected insurer cost")),
        (("add_coverage", "Increase coverage while retaining the same insured person.", "coverage=80%"),
         ("reduce_hidden_effort", "Move hidden effort from 0.8 to 0.4.", "effort change=-0.4"),
         ("increase_loss_risk", "Raise loss probability from 0.1 to 0.2.", "loss probability increase=0.1"),
         ("price_insurer_cost", "Apply coverage and loss severity to the changed probability.", "expected insurer cost=160")),
        ("coverage", "effort", "risk", "insurer_cost"),
    ),
    _route(
        "healthcare_insurance",
        ("health_economics",),
        "Insurance lowers the patient price below resource cost, so patient demand exceeds the efficient healthcare quantity.",
        ("patient price=(1-coverage)*resource price", "MB=MC at efficient quantity", "overuse=patient demand-efficient quantity"),
        (("benefit", "marginal health benefit"), ("social_cost", "marginal social cost"),
         ("patient_price", "insured out-of-pocket price"), ("efficient_quantity", "MB=MC quantity"),
         ("patient_quantity", "quantity demanded at patient price"), ("overuse", "insurance-induced quantity gap")),
        (("find_efficient_quantity", "Intersect marginal benefit with marginal social cost.", "efficient quantity=16.67"),
         ("lower_patient_price", "Lower the retained patient price to 20% of resource price.", "patient price=10"),
         ("expand_patient_quantity", "Move quantity demanded along marginal benefit to the insured price.", "patient quantity=27.5"),
         ("measure_healthcare_overuse", "Measure the gap from efficient to patient-demanded quantity.", "overuse=27.5-16.67=10.83")),
        ("efficient_quantity", "patient_price", "patient_quantity", "overuse"),
    ),
    _route(
        "production_isoquants",
        ("production_function",),
        "Every point on one isoquant produces the same output; outward input expansion reaches a strictly higher output isoquant.",
        ("q=f(K,L)", "same isoquant => same q", "input expansion => q1 > q0"),
        (("inputs", "capital-labor input bundle"), ("isoquant0", "initial equal-output isoquant"),
         ("isoquant1", "higher-output isoquant"), ("output", "persistent output label")),
        (("trace_isoquant", "Move the input bundle along isoquant q0 without changing output.", "f(K0,L0)=f(K1,L1)=q0"),
         ("expand_inputs", "Move the same input bundle northeast onto isoquant q1.", "K and/or L expands"),
         ("replace_output", "Replace the retained output label q0 with q1.", "q1>q0")),
    ),
    _route(
        "factor_cost_minimization",
        ("factor_input_markets", "capital_input_market"),
        "The cost-minimizing labor-capital bundle reaches target output where the isoquant is tangent to an isocost.",
        ("q=A L^alpha K^(1-alpha)", "MRTS=MP_L/MP_K=w/r", "cost=wL+rK"),
        (("isoquant", "target-output isoquant"), ("isocost", "factor-cost line"),
         ("labor", "cost-minimizing labor input"), ("capital", "cost-minimizing capital input"),
         ("tangency", "MRTS-factor-price equality")),
        (("fix_output", "Retain the isoquant for the required target output.", "produced output=target output"),
         ("slide_isocost", "Move the isocost inward until it first reaches the isoquant.", "minimum cost=wL+rK"),
         ("verify_tangency", "Compare the retained MRTS with the factor-price ratio.", "MRTS=w/r")),
    ),
    _route(
        "cost_curves",
        ("cost_curves",),
        "MC crosses AC at AC's minimum; the chosen output is read on the quantity axis, never from a market intersection.",
        ("MC = delta TC/delta q", "AC = TC/q", "MC=AC at min AC"),
        (("mc", "marginal cost curve"), ("ac", "average cost curve"),
         ("output", "output quantity marker"), ("cost", "cost-at-output labels")),
        (("draw_cost_measures", "Retain distinct MC and AC curves over output.", "MC and AC indexed by q"),
         ("locate_ac_minimum", "Move the output marker to the MC-AC crossing.", "MC(qmin)=AC(qmin)"),
         ("read_output_cost", "Project q and cost from the same crossing.", "output=qmin; AC is minimized")),
    ),
    _route(
        "perfect_competition",
        ("perfect_competition",),
        "A price-taking firm chooses firm output where P=MC, while market supply and demand determine the price.",
        ("market Qd = Qs", "firm P = MR", "firm P = MC(qfirm)"),
        (("market", "market demand-supply equilibrium"), ("price", "price transferred from market to firm"),
         ("firm_mc", "individual firm's marginal cost"), ("firm_output", "individual firm's output choice")),
        (("clear_market", "Resolve market demand and supply to one price.", "Qd=Qs determines P*"),
         ("transfer_price", "Carry P* horizontally into the separate firm panel.", "firm takes P* as given"),
         ("choose_firm_output", "Intersect the retained price line with firm MC.", "P*=MC(qfirm)")),
    ),
    _route(
        "competitive_shutdown",
        ("competitive_shutdown",),
        "A competitive firm produces in the short run only when price covers minimum average variable cost.",
        ("shutdown iff P<min AVC", "q=0 when shutdown", "fixed cost remains sunk in the short run"),
        (("price", "market price line"), ("mc", "marginal cost curve"),
         ("avc", "average variable cost curve"), ("shutdown", "minimum-AVC threshold"),
         ("output", "operating or zero output marker")),
        (("compare_price_avc", "Compare retained market price with minimum AVC.", "P-min AVC=-2"),
         ("apply_shutdown_rule", "Move the firm's output marker to zero when price is below AVC.", "chosen output=0"),
         ("retain_fixed_cost", "Keep fixed cost in the short-run profit accounting.", "short-run profit=-fixed cost")),
    ),
    _route(
        "monopoly",
        ("monopoly", "marginal_revenue"),
        "Set MR=MC to choose quantity; demand then gives price.",
        ("MR(qm) = MC(qm)", "Pm = demand(qm)", "deadweight trades from qm to qefficient"),
        (("demand", "market inverse demand curve"), ("mr", "marginal revenue curve"),
         ("mc", "marginal cost curve"), ("quantity", "monopoly and efficient quantity markers"),
         ("price", "price projected from demand"), ("deadweight", "unrealized-gains region")),
        (("choose_monopoly_quantity", "Intersect MR and MC to retain qm.", "MR(qm)=MC(qm)"),
         ("project_monopoly_price", "Project vertically from qm to demand, then horizontally to Pm.", "Pm=D(qm), not MR(qm)"),
         ("mark_deadweight_loss", "Retain qm and shade gains from trades through qefficient.", "DWL spans qm to demand=MC")),
    ),
    _route(
        "price_discrimination",
        ("price_discrimination",),
        "A discriminating monopolist allocates output until marginal revenue is equal across separated markets and marginal cost.",
        ("MR1=MR2=MC", "P1=D1(q1)", "P2=D2(q2)"),
        (("market_1", "first separated demand and MR schedules"), ("market_2", "second separated demand and MR schedules"),
         ("mc", "common marginal cost"), ("allocation", "market-specific quantities"),
         ("prices", "market-specific prices")),
        (("equalize_marginal_revenue", "Allocate quantities until both retained MR schedules equal MC.", "MR1=MR2=MC"),
         ("project_segment_prices", "Read each segment's price from its own demand curve.", "P1=D1(q1); P2=D2(q2)"),
         ("account_segment_profit", "Combine segment margins and subtract fixed cost.", "profit=sum((Pi-MC)qi)-FC")),
    ),
    _route(
        "cournot",
        ("oligopoly",),
        "At Cournot-Nash output, each firm's quantity is a best response to the rival's retained quantity.",
        ("q1=BR1(q2)", "q2=BR2(q1)", "Q=q1+q2"),
        (("reaction_1", "firm one's best-response curve"), ("reaction_2", "firm two's best-response curve"),
         ("nash", "mutual-best-response quantity pair"), ("profit", "per-firm Cournot profit")),
        (("trace_reactions", "Retain both firms' quantity best responses.", "two reaction curves"),
         ("locate_cournot_nash", "Move to their mutual-best-response intersection.", "q1=q2=30"),
         ("price_cournot_output", "Price total Cournot output on inverse demand.", "Q=60; P=40")),
    ),
    _route(
        "cournot_collusion",
        ("oligopoly_collusion",),
        "Symmetric collusion restricts total output below Cournot-Nash output and raises price and joint profit.",
        ("Qc<Qn", "Pc>Pn", "collusive per-firm profit>Cournot per-firm profit"),
        (("reaction_curves", "Cournot best responses"), ("cournot", "Cournot-Nash benchmark"),
         ("collusion", "joint-profit-maximizing quantity"), ("price", "Cournot and collusive prices"),
         ("profit", "per-firm profit comparison")),
        (("mark_cournot_benchmark", "Retain the mutual-best-response Cournot benchmark.", "Qn=60; Pn=40"),
         ("restrict_joint_output", "Move total output to the joint-profit maximum.", "Qc=45<Qn"),
         ("compare_price_profit", "Reprice the retained market and compare per-firm profit.", "Pc=55>Pn; collusive profit rises")),
    ),
    _route(
        "public_goods_vertical_sum",
        ("public_good",),
        "For a nonrival public good, individual willingness to pay is summed vertically at the same quantity.",
        ("SMB(G) = sum_i MB_i(G)", "same G for every person", "SMB(G*) = MC(G*)"),
        (("mb1", "person one's marginal willingness to pay"), ("mb2", "person two's marginal willingness to pay"),
         ("smb", "vertical sum of individual marginal benefits"), ("mc", "marginal provision cost"),
         ("quantity", "common public-good quantity marker")),
        (("align_common_quantity", "Hold one quantity G fixed across both individual schedules.", "same G consumed by both people"),
         ("sum_willingness_to_pay", "Stack MB1(G) and MB2(G) vertically into SMB(G).", "SMB(G)=MB1(G)+MB2(G)"),
         ("choose_provision", "Move the common quantity marker to SMB=MC.", "SMB(G*)=MC(G*)")),
    ),
)

def _build_route_registries(
    routes: Sequence[EconomicsVideoRoute],
) -> tuple[Mapping[str, EconomicsVideoRoute], Mapping[str, EconomicsVideoRoute]]:
    families: dict[str, EconomicsVideoRoute] = {}
    models: dict[str, EconomicsVideoRoute] = {}
    for route in routes:
        if route.family in families:
            raise RuntimeError(f"duplicate economics video route family: {route.family}")
        families[route.family] = route
        for model_id in route.model_ids:
            previous = models.get(model_id)
            if previous is not None:
                raise RuntimeError(
                    f"economics model {model_id!r} appears in both "
                    f"{previous.family!r} and {route.family!r} routes"
                )
            models[model_id] = route
    return MappingProxyType(families), MappingProxyType(models)


ECONOMICS_VIDEO_ROUTE_REGISTRY, _MODEL_ROUTE_REGISTRY = _build_route_registries(
    ECONOMICS_VIDEO_ROUTES
)
ECONOMICS_MODEL_VIDEO_ROUTE_REGISTRY: Mapping[str, EconomicsVideoRoute] = (
    _MODEL_ROUTE_REGISTRY
)

if set(ECONOMICS_MODEL_VIDEO_ROUTE_REGISTRY) != set(ECONOMICS_MODEL_REGISTRY):
    raise RuntimeError("economics video routes must cover all registered models exactly")


def resolve_economics_video_route(topic_or_model_id: str, *, fail_closed: bool = False) -> EconomicsVideoRoute | None:
    """Resolve either an economics model ID or a human topic title."""
    if not isinstance(topic_or_model_id, str):
        raise TypeError("topic_or_model_id must be a string")
    key = topic_or_model_id.strip()
    route = _MODEL_ROUTE_REGISTRY.get(key)
    if route is None and key:
        spec = resolve_economics_model(key)
        route = _MODEL_ROUTE_REGISTRY.get(spec.model_id) if spec else None
    if route is None and fail_closed:
        raise ValueError(f"Unsupported economics video route: {topic_or_model_id!r}")
    return route


def build_economics_video_payload(topic_or_model_id: str) -> dict[str, object]:
    """Build complete semantic snapshots for one deterministic economics route."""
    route = resolve_economics_video_route(topic_or_model_id, fail_closed=True)
    assert route is not None
    spec = resolve_economics_model(topic_or_model_id, fail_closed=True)
    assert spec is not None
    scenario = get_economics_model_scenario(spec.model_id)
    model_scenario = scenario.as_dict()
    evidence = spec.required_evidence_metadata
    required_tokens = evidence.required_tokens
    ids = tuple(f"{route.route_key}:{name}" for name, _role in route.object_roles)
    setup_state = {
        object_id: f"{role}: retained at setup"
        for object_id, (_name, role) in zip(ids, route.object_roles)
    }
    states: list[dict[str, str]] = [{object_id: "absent" for object_id in ids}, setup_state]
    transitions: list[dict[str, object]] = [{
        "id": f"{route.family}:establish_economic_objects",
        "kind": "establish_economic_objects",
        "claim": "Construct and retain every named economic object for this route.",
        "action": "Draw the named axes, schedules, and markers once and retain their identities.",
        "persistent_object_ids": list(ids),
        "before": dict(states[0]),
        "after": dict(setup_state),
        "verification": "all named schedules, markers, and axes are visible",
    }]
    for index, (step_id, claim, step_evidence) in enumerate(route.steps, start=1):
        before = states[-1]
        after = dict(before)
        role = (
            route.changed_objects[min(index - 1, len(route.changed_objects) - 1)]
            if route.changed_objects else route.object_roles[(index - 1) % len(route.object_roles)][0]
        )
        changed_id = f"{route.route_key}:{role}"
        if changed_id not in after:
            raise ValueError(f"route {route.route_key} changes undeclared object {role!r}")
        after[changed_id] = step_evidence
        transitions.append({
            "id": f"{route.family}:{step_id}",
            "kind": step_id,
            "claim": claim,
            "action": claim,
            "persistent_object_ids": list(ids),
            "before": dict(before),
            "after": dict(after),
            "verification": step_evidence,
            "changed_object_id": changed_id,
        })
        states.append(after)
    return {
        "payload_type": "economics",
        "model_id": spec.model_id,
        "scenario_mode": scenario.mode,
        "numeric_setup": dict(scenario.setup),
        "calculation_fields": dict(scenario.calculation),
        "calculation": dict(scenario.calculation),
        "result_fields": dict(scenario.results),
        "model_scenario": model_scenario,
        "scenario": model_scenario,
        "numeric_evidence": {
            "setup": dict(scenario.setup),
            "calculation": dict(scenario.calculation),
            "result": dict(scenario.results),
        },
        "numeric_evidence_fingerprint": scenario.numeric_evidence_fingerprint,
        "numeric_fingerprint": scenario.numeric_fingerprint,
        "required_example_tokens": list(evidence.example_tokens),
        "required_figure_tokens": list(evidence.figure_tokens),
        "required_tokens": list(required_tokens),
        "required_evidence_metadata": evidence.as_dict(),
        "visible_evidence_tokens": list(scenario.visible_evidence_tokens),
        "animation_states": [state.as_dict() for state in scenario.animation_states],
        "family": route.family,
        "route_key": route.route_key,
        "invariant": route.invariant,
        "verification": list(route.verification),
        "persistent_object_ids": list(ids),
        "objects": [
            {
                "id": object_id,
                "role": role,
                "color": ("#58A6FF", "#F7C948", "#FF7B72", "#A371F7", "#7EE787", "#EAF2FF")[index % 6],
                "persistent": True,
                "initial_state": states[0][object_id],
            }
            for index, (object_id, (_name, role)) in enumerate(zip(ids, route.object_roles))
        ],
        "states": states,
        "transitions": transitions,
        "changed_objects": list(route.changed_objects),
    }


def _close(left: float, right: float, tolerance: float = 1e-7) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def _identity_errors(payload: Mapping[str, object]) -> list[str]:
    model_id = str(payload.get("model_id", ""))
    setup = payload.get("numeric_setup")
    result = payload.get("result_fields")
    if not isinstance(setup, Mapping) or not isinstance(result, Mapping):
        return ["numeric setup and result fields are required"]
    errors: list[str] = []
    if model_id == "price_ceiling_shortage":
        expected = max(float(result["quantity_demanded"]) - float(result["quantity_supplied"]), 0.0)
        if not _close(result["shortage"], expected):
            errors.append("price-ceiling identity requires shortage=quantity demanded-quantity supplied")
    elif model_id == "price_floor_surplus":
        expected = max(float(result["quantity_supplied"]) - float(result["quantity_demanded"]), 0.0)
        if not _close(result["surplus"], expected):
            errors.append("price-floor identity requires surplus=quantity supplied-quantity demanded")
    elif model_id == "price_controls":
        qd_ceiling = float(setup["demand_intercept"]) - float(setup["demand_slope"]) * float(setup["ceiling_price"])
        qs_ceiling = float(setup["supply_intercept"]) + float(setup["supply_slope"]) * float(setup["ceiling_price"])
        qd_floor = float(setup["demand_intercept"]) - float(setup["demand_slope"]) * float(setup["floor_price"])
        qs_floor = float(setup["supply_intercept"]) + float(setup["supply_slope"]) * float(setup["floor_price"])
        if not _close(result["ceiling_shortage"], max(qd_ceiling - qs_ceiling, 0.0)):
            errors.append("price-controls ceiling shortage identity failed")
        if not _close(result["floor_surplus"], max(qs_floor - qd_floor, 0.0)):
            errors.append("price-controls floor surplus identity failed")
    elif model_id == "consumer_surplus":
        expected = 0.5 * (float(setup["choke_price"]) - float(setup["market_price"])) * float(setup["quantity"])
        if not _close(result["CS"], expected):
            errors.append("consumer-surplus area identity failed")
    elif model_id == "producer_surplus":
        expected = 0.5 * (float(setup["market_price"]) - float(setup["supply_intercept_price"])) * float(setup["quantity"])
        if not _close(result["PS"], expected):
            errors.append("producer-surplus area identity failed")
    elif model_id in {"total_surplus", "welfare_surplus"}:
        if not _close(result["TS"], float(result["CS"]) + float(result["PS"])):
            errors.append("total-surplus identity requires TS=CS+PS")
    elif model_id == "equity_efficiency":
        before = float(setup["person_1_before"]) + float(setup["person_2_before"])
        after = float(setup["person_1_after"]) + float(setup["person_2_after"])
        if not _close(result["efficiency_gain"], after - before):
            errors.append("equity-efficiency total-welfare identity failed")
    elif model_id == "externality":
        if not _close(result["overproduction"], float(result["market_quantity"]) - float(result["efficient_quantity"])):
            errors.append("externality identity requires overproduction=market quantity-efficient quantity")
    elif model_id == "coase_bargaining":
        if not _close(result["marginal_benefit"], result["marginal_cost"]):
            errors.append("Coase bargaining identity requires marginal benefit=marginal cost")
        if not _close(result["net_bargaining_gains"], float(result["gross_bargaining_gains"]) - float(setup["transaction_costs"])):
            errors.append("Coase bargaining net-gains identity failed")
    elif model_id == "common_resource":
        if not _close(result["overuse"], float(result["open_access_quantity"]) - float(result["efficient_quantity"])):
            errors.append("common-resource identity requires overuse=open-access quantity-efficient quantity")
    elif model_id == "international_trade":
        expected = float(result["domestic_demand"]) - float(result["domestic_supply"])
        if not _close(result["imports"], max(expected, 0.0)):
            errors.append("trade identity requires imports=domestic demand-domestic supply")
    elif model_id == "tariff":
        if not _close(result["domestic_price"], float(setup["world_price"]) + float(setup["tariff"])):
            errors.append("tariff identity requires domestic price=world price+tariff")
        if not _close(result["imports_after"], float(result["domestic_demand_after"]) - float(result["domestic_supply_after"])):
            errors.append("tariff identity requires imports after=demand after-supply after")
        if not _close(result["tariff_revenue"], float(setup["tariff"]) * float(result["imports_after"])):
            errors.append("tariff revenue identity failed")
        distortion = float(result["production_distortion"]) + float(result["consumption_distortion"])
        if not _close(result["tariff_deadweight_loss"], 0.5 * float(setup["tariff"]) * distortion):
            errors.append("tariff deadweight-loss identity failed")
    elif model_id == "labor_market":
        if not (_close(result["employment"], result["labor_demanded"]) and _close(result["employment"], result["labor_supplied"])):
            errors.append("labor-market identity requires employment=labor demanded=labor supplied")
    elif model_id == "factor_input_markets":
        if not _close(result["produced_output"], setup["target_output"]):
            errors.append("factor-cost identity requires produced output=target output")
        if not _close(result["MRTS_labor_for_capital"], result["factor_price_ratio"]):
            errors.append("factor-cost tangency requires MRTS=wage/rental price")
        cost = float(setup["wage"]) * float(result["labor_input"]) + float(setup["rental_price"]) * float(result["capital_input"])
        if not _close(result["minimum_cost"], cost):
            errors.append("factor-cost accounting requires cost=wL+rK")
    elif model_id == "intertemporal_choice":
        present_value = float(setup["income_now"]) + float(setup["income_later"]) / (1.0 + float(setup["interest_rate"]))
        chosen_value = float(result["chosen_consumption_now"]) + float(result["chosen_consumption_later"]) / (1.0 + float(setup["interest_rate"]))
        if not (_close(result["present_value_wealth"], present_value) and _close(chosen_value, present_value)):
            errors.append("intertemporal choice must exhaust the present-value budget")
    elif model_id == "competitive_shutdown":
        expected_shutdown = float(setup["market_price"]) < float(setup["minimum_average_variable_cost"])
        if not _close(result["shutdown_indicator"], float(expected_shutdown)):
            errors.append("competitive shutdown indicator disagrees with P<minimum AVC")
        if expected_shutdown and not _close(result["chosen_output"], 0.0):
            errors.append("competitive shutdown requires zero output below minimum AVC")
    elif model_id == "price_discrimination":
        if not _close(result["common_marginal_revenue"], setup["marginal_cost"]):
            errors.append("price discrimination requires MR1=MR2=MC")
        price_1 = float(setup["demand_1_intercept"]) - float(setup["demand_1_slope"]) * float(result["market_1_quantity"])
        price_2 = float(setup["demand_2_intercept"]) - float(setup["demand_2_slope"]) * float(result["market_2_quantity"])
        if not (_close(result["market_1_price"], price_1) and _close(result["market_2_price"], price_2)):
            errors.append("price discrimination prices must be read from segment demands")
    elif model_id == "oligopoly_collusion":
        if not float(result["collusive_total_quantity"]) < float(result["cournot_total_quantity"]):
            errors.append("collusion must restrict output below Cournot output")
        if not float(result["collusive_price"]) > float(result["cournot_price"]):
            errors.append("collusion must raise price above the Cournot price")
        if not _close(result["output_restriction"], float(result["cournot_total_quantity"]) - float(result["collusive_total_quantity"])):
            errors.append("collusive output restriction identity failed")
    elif model_id == "choice_under_uncertainty":
        if not _close(result["certainty_equivalent"], float(result["expected_utility"]) ** 2):
            errors.append("certainty equivalent must invert the stated square-root utility")
        if not _close(result["risk_premium"], float(result["expected_payoff"]) - float(result["certainty_equivalent"])):
            errors.append("risk premium requires expected payoff minus certainty equivalent")
    elif model_id == "social_insurance":
        expected_gap = float(result["no_loss_state_consumption"]) - float(result["loss_state_consumption"])
        if not _close(result["consumption_gap"], expected_gap):
            errors.append("social-insurance smoothing gap identity failed")
    elif model_id == "behavioral_economics":
        benchmark = float(setup["discount_factor"]) ** float(setup["delay_periods"]) * float(setup["later_utility"])
        behavioral = float(setup["present_bias"]) * benchmark
        if not (_close(result["benchmark_later_value"], benchmark) and _close(result["behavioral_later_value"], behavioral)):
            errors.append("present-bias valuation requires behavioral value=beta*benchmark")
    elif model_id == "adverse_selection":
        pooled = float(setup["high_risk_share"]) * float(result["high_risk_fair_premium"]) + (1.0 - float(setup["high_risk_share"])) * float(result["low_risk_fair_premium"])
        if not _close(result["pooling_premium"], pooled):
            errors.append("adverse-selection pooling premium is not the weighted expected loss")
        remaining_low = (1.0 - float(setup["high_risk_share"])) * (1.0 - float(setup["low_risk_exit_rate"]))
        post_high = float(setup["high_risk_share"]) / (float(setup["high_risk_share"]) + remaining_low)
        post_pool = post_high * float(result["high_risk_fair_premium"]) + (1.0 - post_high) * float(result["low_risk_fair_premium"])
        if not _close(result["post_exit_pooling_premium"], post_pool):
            errors.append("adverse-selection post-exit pool identity failed")
    elif model_id == "moral_hazard":
        if not _close(result["effort_change"], float(setup["covered_effort"]) - float(setup["uncovered_effort"])):
            errors.append("moral-hazard effort change identity failed")
        if not _close(result["loss_probability_increase"], float(setup["covered_loss_probability"]) - float(setup["uncovered_loss_probability"])):
            errors.append("moral-hazard probability change identity failed")
    elif model_id == "health_economics":
        patient_price = (1.0 - float(setup["insurance_coverage_rate"])) * float(setup["resource_price"])
        if not _close(result["patient_price"], patient_price):
            errors.append("healthcare patient-price identity failed")
        if not _close(result["insurance_induced_overuse"], float(result["patient_demanded_quantity"]) - float(result["efficient_health_care_quantity"])):
            errors.append("healthcare quantity-gap identity failed")
    return errors


def validate_economics_video_payload(payload: Mapping[str, object]) -> list[str]:
    """Return structural and continuity errors in an economics payload."""
    errors: list[str] = []
    errors.extend(_identity_errors(payload))
    model_scenario = payload.get("model_scenario")
    fingerprint = payload.get("numeric_evidence_fingerprint")
    numeric_evidence = payload.get("numeric_evidence")
    if not isinstance(model_scenario, Mapping):
        errors.append("canonical model_scenario is required")
    if not isinstance(numeric_evidence, Mapping):
        errors.append("setup/calculation/result numeric evidence is required")
    else:
        try:
            recomputed_fingerprint = economics_numeric_evidence_fingerprint(
                numeric_evidence
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid numeric evidence: {exc}")
        else:
            if fingerprint != recomputed_fingerprint:
                errors.append("numeric_evidence_fingerprint does not match numeric evidence")
    if isinstance(model_scenario, Mapping):
        if model_scenario.get("numeric_evidence_fingerprint") != fingerprint:
            errors.append("model_scenario fingerprint must match payload fingerprint")
        if payload.get("scenario") != model_scenario:
            errors.append("scenario alias must equal canonical model_scenario")
        if model_scenario.get("numeric_fingerprint") != payload.get("numeric_fingerprint"):
            errors.append("model_scenario numeric fingerprint must match payload fingerprint")
    required_example = payload.get("required_example_tokens")
    required_figure = payload.get("required_figure_tokens")
    required_tokens = payload.get("required_tokens")
    if not isinstance(required_example, (list, tuple)) or not required_example:
        errors.append("required example tokens are required")
    if not isinstance(required_figure, (list, tuple)) or not required_figure:
        errors.append("required figure tokens are required")
    if isinstance(required_example, (list, tuple)) and isinstance(required_figure, (list, tuple)):
        expected_tokens = list(dict.fromkeys((*required_example, *required_figure)))
        if required_tokens != expected_tokens:
            errors.append("required tokens must be the ordered union of evidence tokens")
        if payload.get("visible_evidence_tokens") != expected_tokens:
            errors.append("visible evidence tokens must expose every required token")
        expected_metadata = {
            "example_tokens": list(required_example),
            "figure_tokens": list(required_figure),
            "required_tokens": expected_tokens,
        }
        if payload.get("required_evidence_metadata") != expected_metadata:
            errors.append("required evidence metadata must expose exact canonical tokens")
    animation_states = payload.get("animation_states")
    if not isinstance(animation_states, (list, tuple)) or [
        state.get("phase") for state in animation_states if isinstance(state, Mapping)
    ] != ["setup", "change", "result"]:
        errors.append("animation states must expose setup, change, and result phases")
    route_key = payload.get("route_key")
    if not isinstance(route_key, str) or not route_key.startswith("economics:"):
        errors.append("canonical economics route_key is required")
    ids = tuple(payload.get("persistent_object_ids", ()))
    if not ids or len(ids) != len(set(ids)):
        errors.append("persistent object IDs must be present and unique")
    if not payload.get("invariant") or not payload.get("verification"):
        errors.append("invariant and verification are required")
    objects = payload.get("objects", ())
    if not isinstance(objects, (list, tuple)) or {
        row.get("id") for row in objects if isinstance(row, Mapping)
    } != set(ids):
        errors.append("objects must define every persistent object ID exactly once")
    previous_after: Mapping[str, object] | None = None
    observed_changed_roles: list[str] = []
    transitions = payload.get("transitions", ())
    if not isinstance(transitions, (list, tuple)) or len(transitions) < 4:
        errors.append("at least three causal transitions are required")
        return errors
    for index, transition in enumerate(transitions):
        if not isinstance(transition, Mapping):
            errors.append(f"transition {index} must be a mapping")
            continue
        before = transition.get("before")
        after = transition.get("after")
        if not isinstance(before, Mapping) or set(before) != set(ids):
            errors.append(f"transition {index} before snapshot is incomplete")
        if not isinstance(after, Mapping) or set(after) != set(ids):
            errors.append(f"transition {index} after snapshot is incomplete")
        if before == after:
            errors.append(f"transition {index} does not change semantic state")
        if previous_after is not None and before != previous_after:
            errors.append(f"transition {index} breaks state continuity")
        if index > 0 and isinstance(before, Mapping) and isinstance(after, Mapping):
            changed = {object_id for object_id in ids if before.get(object_id) != after.get(object_id)}
            if len(changed) != 1:
                errors.append(f"transition {index} must change exactly one declared economic object")
            else:
                changed_id = next(iter(changed))
                if transition.get("changed_object_id") != changed_id:
                    errors.append(f"transition {index} changed-object declaration does not match its snapshots")
                observed_changed_roles.append(changed_id.rsplit(":", 1)[-1])
        if isinstance(after, Mapping):
            previous_after = after
    declared_changed = list(payload.get("changed_objects", ()))
    if declared_changed and observed_changed_roles != declared_changed:
        errors.append("route changed objects must match transition order exactly")
    return errors


# Friendly aliases for callers that use model rather than route terminology.
resolve_economics_video_model = resolve_economics_video_route
build_video_economics_payload = build_economics_video_payload

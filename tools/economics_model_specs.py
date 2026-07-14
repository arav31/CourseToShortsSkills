"""Typed, data-only microeconomics model resolution.

The registry deliberately has no dependency on ``stem_course``.  It can be
imported there without creating a circular dependency, while the duplicated
visual-kind literal is checked by focused tests against ``ECON_VISUAL_KINDS``.

Required tokens are case-insensitive literal substrings.  They describe the
minimum vocabulary that a worked example or figure must preserve; they are not
alternative spellings or a bag of optional keywords.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Literal
import unicodedata


EconVisualKind = Literal[
    "econ_budget",
    "econ_curve",
    "econ_elasticity",
    "econ_supply_demand",
    "econ_tax_wedge",
    "game_payoff",
    "econ_externality_wedge",
    "econ_production_isoquants",
    "econ_cost_curves",
    "econ_perfect_competition",
    "econ_monopoly",
    "econ_public_goods_vertical_sum",
    "econ_international_trade",
    "econ_tariff",
    "econ_labor_market",
    "econ_adverse_selection",
    "econ_moral_hazard",
    "econ_healthcare_insurance",
]

StatementKind = Literal[
    "accounting_identity",
    "behavioral_relation",
    "best_response_condition",
    "budget_constraint",
    "classification_rule",
    "comparative_static",
    "definition",
    "equilibrium_condition",
    "expected_utility",
    "incentive_condition",
    "optimality_condition",
    "policy_wedge",
    "resource_constraint",
    "welfare_measure",
]

# Kept local so this module stays pure and safe to import from stem_course.py.
ECON_VISUAL_KINDS: frozenset[str] = frozenset(
    {
        "econ_budget",
        "econ_curve",
        "econ_elasticity",
        "econ_supply_demand",
        "econ_tax_wedge",
        "game_payoff",
        "econ_externality_wedge",
        "econ_production_isoquants",
        "econ_cost_curves",
        "econ_perfect_competition",
        "econ_monopoly",
        "econ_public_goods_vertical_sum",
        "econ_international_trade",
        "econ_tariff",
        "econ_labor_market",
        "econ_adverse_selection",
        "econ_moral_hazard",
        "econ_healthcare_insurance",
    }
)


@dataclass(frozen=True)
class SymbolRow(Mapping[str, str]):
    """One exact notation row, also usable through a dict-like interface."""

    symbol: str
    meaning: str

    def __getitem__(self, key: str) -> str:
        if key == "symbol":
            return self.symbol
        if key == "meaning":
            return self.meaning
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(("symbol", "meaning"))

    def __len__(self) -> int:
        return 2

    def as_dict(self) -> dict[str, str]:
        return {"symbol": self.symbol, "meaning": self.meaning}


@dataclass(frozen=True)
class EvidenceMetadata(Mapping[str, object]):
    """Exact evidence strings a rendered example must make visible."""

    example_tokens: tuple[str, ...]
    figure_tokens: tuple[str, ...]

    @property
    def required_tokens(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.example_tokens, *self.figure_tokens)))

    def __getitem__(self, key: str) -> object:
        if key in ("example_tokens", "figure_tokens", "required_tokens"):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(("example_tokens", "figure_tokens", "required_tokens"))

    def __len__(self) -> int:
        return 3

    def as_dict(self) -> dict[str, object]:
        return {
            "example_tokens": list(self.example_tokens),
            "figure_tokens": list(self.figure_tokens),
            "required_tokens": list(self.required_tokens),
        }


@dataclass(frozen=True)
class EconomicsModelSpec(Mapping[str, object]):
    """Immutable semantic contract for one microeconomics model."""

    model_id: str
    visual_kind: EconVisualKind
    canonical_formula: str
    prerequisites: tuple[str, ...]
    learner_assumptions: tuple[str, ...]
    statement_kind: StatementKind
    exact_symbol_rows: tuple[SymbolRow, ...]
    required_example_tokens: tuple[str, ...]
    required_figure_tokens: tuple[str, ...]

    @property
    def symbol_rows(self) -> tuple[SymbolRow, ...]:
        """Compatibility alias for consumers that use the shorter field name."""

        return self.exact_symbol_rows

    @property
    def required_evidence_metadata(self) -> EvidenceMetadata:
        return EvidenceMetadata(
            self.required_example_tokens,
            self.required_figure_tokens,
        )

    def __getitem__(self, key: str) -> object:
        if key == "symbol_rows":
            return self.exact_symbol_rows
        if key == "required_evidence_metadata":
            return self.required_evidence_metadata
        if key in _SPEC_FIELD_NAMES:
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(_SPEC_FIELD_NAMES)

    def __len__(self) -> int:
        return len(_SPEC_FIELD_NAMES)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly copy without exposing mutable registry state."""

        return {
            "model_id": self.model_id,
            "visual_kind": self.visual_kind,
            "canonical_formula": self.canonical_formula,
            "prerequisites": list(self.prerequisites),
            "learner_assumptions": list(self.learner_assumptions),
            "statement_kind": self.statement_kind,
            "exact_symbol_rows": [row.as_dict() for row in self.exact_symbol_rows],
            "required_example_tokens": list(self.required_example_tokens),
            "required_figure_tokens": list(self.required_figure_tokens),
            "required_evidence_metadata": self.required_evidence_metadata.as_dict(),
        }


_SPEC_FIELD_NAMES = (
    "model_id",
    "visual_kind",
    "canonical_formula",
    "prerequisites",
    "learner_assumptions",
    "statement_kind",
    "exact_symbol_rows",
    "required_example_tokens",
    "required_figure_tokens",
)


@dataclass(frozen=True)
class _Definition:
    spec: EconomicsModelSpec
    exact_titles: tuple[str, ...]


def _rows(*rows: tuple[str, str]) -> tuple[SymbolRow, ...]:
    return tuple(SymbolRow(symbol, meaning) for symbol, meaning in rows)


def _spec(
    model_id: str,
    visual_kind: EconVisualKind,
    canonical_formula: str,
    prerequisites: tuple[str, ...],
    statement_kind: StatementKind,
    symbol_rows: tuple[SymbolRow, ...],
    example_tokens: tuple[str, ...],
    figure_tokens: tuple[str, ...],
    *exact_titles: str,
) -> _Definition:
    assumption_by_kind = {
        "accounting_identity": (
            "All terms use the same market, period, and accounting boundary.",
        ),
        "behavioral_relation": (
            "Non-price shifters are held fixed while the displayed relation is evaluated.",
        ),
        "best_response_condition": (
            "Each deviation is compared while the other players' strategies stay fixed.",
        ),
        "budget_constraint": (
            "Prices and income are fixed, and only affordable bundles are feasible.",
        ),
        "classification_rule": (
            "The comparison uses one stated baseline and a common unit convention.",
        ),
        "comparative_static": (
            "Only the named primitive changes between the two static equilibria.",
        ),
        "equilibrium_condition": (
            "The compared schedules describe the same market and time period, with omitted shifters fixed.",
        ),
        "expected_utility": (
            "Probabilities are nonnegative and sum to one, and outcomes use the stated utility representation.",
        ),
        "incentive_condition": (
            "Compliance and deviation are evaluated under the same information and prices.",
        ),
        "optimality_condition": (
            "The candidate is feasible and is checked against relevant boundary alternatives.",
        ),
        "policy_wedge": (
            "The underlying behavioral schedules remain fixed while the policy rule is imposed.",
        ),
        "resource_constraint": (
            "Every use draws from the same fixed aggregate resource.",
        ),
        "welfare_measure": (
            "Marginal schedules are integrable over the traded range and the stated surplus criterion is the welfare benchmark.",
        ),
    }
    return _Definition(
        EconomicsModelSpec(
            model_id=model_id,
            visual_kind=visual_kind,
            canonical_formula=canonical_formula,
            prerequisites=prerequisites,
            learner_assumptions=assumption_by_kind.get(
                statement_kind,
                (
                    "The market definition, time period, units, and omitted shifters remain fixed during the evaluation.",
                ),
            ),
            statement_kind=statement_kind,
            exact_symbol_rows=symbol_rows,
            required_example_tokens=example_tokens,
            required_figure_tokens=figure_tokens,
        ),
        exact_titles=(model_id.replace("_", " "), *exact_titles),
    )


_DEFINITIONS: tuple[_Definition, ...] = (
    _spec(
        "supply_demand_intro",
        "econ_supply_demand",
        r"Q_d=D(P;z_d),\quad Q_s=S(P;z_s)",
        ("graphs", "prices", "quantities"),
        "behavioral_relation",
        _rows(
            ("P", "market price"),
            ("Q_d", "quantity demanded at price P"),
            ("Q_s", "quantity supplied at price P"),
            ("z_d", "non-price demand shifters held fixed"),
            ("z_s", "non-price supply shifters held fixed"),
        ),
        ("price", "quantity demanded", "quantity supplied"),
        ("price", "quantity", "demand", "supply"),
        "supply and demand",
        "introduction to supply and demand",
        "intro to supply and demand",
        "supply demand introduction",
        "introduction and supply and demand",
    ),
    _spec(
        "market_equilibrium",
        "econ_supply_demand",
        r"Q_s(P^*)=Q_d(P^*)=Q^*",
        ("supply", "demand", "graphs"),
        "equilibrium_condition",
        _rows(
            ("P^*", "market-clearing price"),
            ("Q^*", "market-clearing quantity"),
            ("Q_d(P)", "quantity demanded at price P"),
            ("Q_s(P)", "quantity supplied at price P"),
        ),
        ("quantity demanded", "quantity supplied", "equilibrium price", "equilibrium quantity"),
        ("demand", "supply", "P^*", "Q^*"),
        "equilibrium",
        "market equilibrium",
        "supply and demand equilibrium",
        "competitive equilibrium",
    ),
    _spec(
        "demand_curve",
        "econ_supply_demand",
        r"Q_d=D(P;I,P_y,T)",
        ("consumer choice", "prices", "ceteris paribus"),
        "behavioral_relation",
        _rows(
            ("Q_d", "quantity demanded of the good"),
            ("P", "own price of the good"),
            ("I", "consumer income held fixed along a demand curve"),
            ("P_y", "prices of related goods held fixed"),
            ("T", "tastes held fixed"),
        ),
        ("own price", "quantity demanded", "holding fixed"),
        ("price", "quantity demanded", "demand"),
        "demand",
        "demand curve",
        "demand curves",
        "individual demand",
        "market demand",
    ),
    _spec(
        "supply_curve",
        "econ_supply_demand",
        r"Q_s=S(P;w,r,A)",
        ("production", "costs", "ceteris paribus"),
        "behavioral_relation",
        _rows(
            ("Q_s", "quantity supplied of the good"),
            ("P", "output price"),
            ("w", "wage or labor-input price held fixed"),
            ("r", "rental price of capital held fixed"),
            ("A", "technology held fixed"),
        ),
        ("output price", "quantity supplied", "holding fixed"),
        ("price", "quantity supplied", "supply"),
        "supply",
        "supply curve",
        "supply curves",
        "individual supply",
        "market supply",
    ),
    _spec(
        "supply_demand_curves",
        "econ_supply_demand",
        r"Q_d=D(P;z_d),\quad Q_s=S(P;z_s)",
        ("graphs", "ceteris paribus", "market behavior"),
        "behavioral_relation",
        _rows(
            ("P", "market price on the vertical axis"),
            ("Q", "market quantity on the horizontal axis"),
            ("Q_d(P)", "quantity demanded along the demand curve"),
            ("Q_s(P)", "quantity supplied along the supply curve"),
            ("z_d,z_s", "demand and supply shifters held fixed along each curve"),
        ),
        ("price", "quantity demanded", "quantity supplied", "holding fixed"),
        ("price", "quantity", "demand curve", "supply curve"),
        "demand and supply curves",
        "supply and demand curves",
        "market demand and supply curves",
    ),
    _spec(
        "comparative_statics",
        "econ_supply_demand",
        r"F(y^*,x)=0,\quad \frac{dy^*}{dx}=-\frac{F_x}{F_y}",
        ("equilibrium", "functions", "holding other variables fixed"),
        "comparative_static",
        _rows(
            ("y^*", "endogenous equilibrium outcome"),
            ("x", "exogenous parameter that changes"),
            ("F", "equilibrium condition"),
            ("dy^*/dx", "equilibrium response to the parameter"),
        ),
        ("before", "after", "parameter", "holding fixed"),
        ("initial equilibrium", "shift", "new equilibrium"),
        "comparative statics",
        "comparative static analysis",
        "market comparative statics",
    ),
    _spec(
        "price_ceiling_shortage",
        "econ_supply_demand",
        r"\bar P<P^*\Rightarrow Q_d(\bar P)-Q_s(\bar P)>0",
        ("supply", "demand", "market equilibrium"),
        "policy_wedge",
        _rows(
            (r"\bar P", "legal maximum price"),
            ("P^*", "unregulated equilibrium price"),
            (r"Q_d(\bar P)", "quantity demanded at the ceiling"),
            (r"Q_s(\bar P)", "quantity supplied at the ceiling"),
            ("shortage", "quantity demanded minus quantity supplied"),
        ),
        ("binding", "price ceiling", "quantity demanded", "quantity supplied", "shortage"),
        ("demand", "supply", "P^*", "price ceiling", "shortage"),
        "price ceiling",
        "price ceilings",
        "binding price ceiling",
        "shortage",
        "excess demand",
    ),
    _spec(
        "price_floor_surplus",
        "econ_supply_demand",
        r"\underline P>P^*\Rightarrow Q_s(\underline P)-Q_d(\underline P)>0",
        ("supply", "demand", "market equilibrium"),
        "policy_wedge",
        _rows(
            (r"\underline P", "legal minimum price"),
            ("P^*", "unregulated equilibrium price"),
            (r"Q_d(\underline P)", "quantity demanded at the floor"),
            (r"Q_s(\underline P)", "quantity supplied at the floor"),
            ("surplus", "quantity supplied minus quantity demanded"),
        ),
        ("binding", "price floor", "quantity supplied", "quantity demanded", "surplus"),
        ("demand", "supply", "P^*", "price floor", "surplus"),
        "price floor",
        "price floors",
        "binding price floor",
        "surplus",
        "excess supply",
    ),
    _spec(
        "price_controls",
        "econ_supply_demand",
        r"\bar P<P^*<\underline P",
        ("supply", "demand", "market equilibrium"),
        "policy_wedge",
        _rows(
            (r"\bar P", "binding maximum price that creates a shortage"),
            (r"\underline P", "binding minimum price that creates a surplus"),
            ("P^*", "unregulated equilibrium price"),
            ("Q_d", "quantity demanded at a controlled price"),
            ("Q_s", "quantity supplied at a controlled price"),
        ),
        ("price ceiling", "shortage", "price floor", "surplus"),
        ("demand", "supply", "price ceiling", "price floor", "P^*"),
        "price controls",
        "shortages and surpluses",
        "price ceilings and floors",
        "price controls shortages and surpluses",
    ),
    _spec(
        "consumer_preferences",
        "econ_budget",
        r"(x_1,y_1)\succeq(x_2,y_2)",
        ("bundles", "binary relations"),
        "definition",
        _rows(
            ("(x_i,y_i)", "consumption bundle i"),
            (r"\succeq", "weak preference relation"),
            (r"\sim", "indifference relation"),
            (r"\succ", "strict preference relation"),
        ),
        ("bundle", "ranking", "preferred"),
        ("good x", "good y", "bundle", "indifference"),
        "consumer preferences",
        "preferences",
        "preference relations",
    ),
    _spec(
        "utility_representation",
        "econ_budget",
        r"U(x_1,y_1)\geq U(x_2,y_2)\Longleftrightarrow(x_1,y_1)\succeq(x_2,y_2)",
        ("consumer preferences", "functions"),
        "definition",
        _rows(
            ("U(x,y)", "utility representation of a preference ranking"),
            ("x,y", "quantities in a consumption bundle"),
            (r"\succeq", "weak preference relation"),
            (r"\bar U", "fixed utility level on an indifference curve"),
        ),
        ("utility", "bundle", "ranking"),
        ("good x", "good y", "indifference curve", "utility"),
        "utility",
        "utility functions",
        "preferences and utility",
        "preferences and utility functions",
        "utility representation",
        "indifference curves",
    ),
    _spec(
        "budget_constraint",
        "econ_budget",
        r"p_xx+p_yy\leq I",
        ("prices", "income", "linear inequalities"),
        "budget_constraint",
        _rows(
            ("x,y", "quantities of the two goods"),
            ("p_x,p_y", "prices per unit of x and y"),
            ("I", "income or expenditure budget"),
            (r"-p_x/p_y", "slope of the budget line with y vertical"),
        ),
        ("income", "price of x", "price of y", "affordable"),
        ("x", "y", "budget line", "I/p_x", "I/p_y"),
        "budget constraint",
        "budget constraints",
        "consumer budget",
        "budget line",
    ),
    _spec(
        "marginal_rate_of_substitution",
        "econ_budget",
        r"MRS_{xy}=\frac{MU_x}{MU_y}=-\left.\frac{dy}{dx}\right|_{U=\bar U}",
        ("utility", "marginal utility", "slopes"),
        "definition",
        _rows(
            ("MU_x", "marginal utility of good x"),
            ("MU_y", "marginal utility of good y"),
            (r"MRS_{xy}", "units of y willingly given up for one more unit of x"),
            (r"dy/dx|_{U=\bar U}", "slope along a fixed indifference curve"),
        ),
        ("marginal utility of x", "marginal utility of y", "indifference curve"),
        ("tangent", "indifference curve", "MRS"),
        "marginal rate of substitution",
        "mrs",
        "diminishing marginal rate of substitution",
    ),
    _spec(
        "consumer_choice",
        "econ_budget",
        r"\max_{x,y}U(x,y)\quad\mathrm{s.t.}\quad p_xx+p_yy\leq I",
        ("preferences", "utility", "budget constraint"),
        "optimality_condition",
        _rows(
            ("x^*,y^*", "chosen affordable bundle"),
            ("U(x,y)", "utility representation"),
            ("p_x,p_y", "goods prices"),
            ("I", "income"),
            ("MRS", "indifference-curve slope magnitude at an interior choice"),
        ),
        ("utility", "budget", "affordable bundle", "choice"),
        ("budget line", "indifference curve", "chosen bundle"),
        "consumer choice",
        "utility maximization",
        "optimal consumer choice",
        "budget constraints and constrained choice",
    ),
    _spec(
        "income_substitution_effects",
        "econ_budget",
        r"\Delta x=SE+IE",
        ("demand", "budget constraints", "consumer choice"),
        "accounting_identity",
        _rows(
            (r"\Delta x", "total change in demand after a price change"),
            ("SE", "substitution effect holding purchasing power compensated"),
            ("IE", "income effect from changed real purchasing power"),
            ("x^0,x^c,x^1", "initial, compensated, and final quantities"),
        ),
        ("initial bundle", "compensated bundle", "final bundle", "substitution effect", "income effect"),
        ("initial budget", "compensated budget", "final budget", "SE", "IE"),
        "income and substitution effects",
        "income substitution effects",
        "income substitution",
        "substitution and income effects",
        "slutsky decomposition",
        "demand curves and income substitution effects",
    ),
    _spec(
        "own_price_elasticity",
        "econ_elasticity",
        r"E_d=\frac{\%\Delta Q_d}{\%\Delta P}",
        ("percent changes", "demand curves"),
        "definition",
        _rows(
            ("E_d", "own-price elasticity of demand"),
            (r"\%\Delta Q_d", "percentage change in quantity demanded"),
            (r"\%\Delta P", "percentage change in the good's own price"),
            (r"|E_d|", "response magnitude used to classify demand"),
        ),
        ("percent change in quantity demanded", "percent change in price", "elasticity"),
        ("demand", "initial point", "new point", "%Delta Q_d", "%Delta P", "E_d"),
        "elasticity",
        "price elasticity",
        "price elasticity of demand",
        "own price elasticity",
        "own price elasticity of demand",
    ),
    _spec(
        "income_elasticity",
        "econ_elasticity",
        r"E_I=\frac{\%\Delta Q_d}{\%\Delta I}",
        ("percent changes", "demand"),
        "classification_rule",
        _rows(
            ("E_I", "income elasticity of demand"),
            (r"\%\Delta Q_d", "percentage change in quantity demanded"),
            (r"\%\Delta I", "percentage change in income"),
            ("E_I>0", "normal-good classification in the measured range"),
            ("E_I<0", "inferior-good classification in the measured range"),
        ),
        ("percent change in quantity demanded", "percent change in income", "normal", "inferior"),
        ("income", "quantity demanded", "E_I", "normal", "inferior"),
        "income elasticity",
        "income elasticity of demand",
        "normal and inferior goods",
    ),
    _spec(
        "cross_price_elasticity",
        "econ_elasticity",
        r"E_{xy}=\frac{\%\Delta Q_x}{\%\Delta P_y}",
        ("percent changes", "demand", "related goods"),
        "classification_rule",
        _rows(
            (r"E_{xy}", "cross-price elasticity of demand for x with respect to the price of y"),
            (r"\%\Delta Q_x", "percentage change in quantity demanded of x"),
            (r"\%\Delta P_y", "percentage change in the price of y"),
            (r"E_{xy}>0", "substitute-goods classification"),
            (r"E_{xy}<0", "complement-goods classification"),
        ),
        ("quantity demanded of x", "price of y", "substitutes", "complements"),
        ("good x", "good y", "E_{xy}", "substitutes", "complements"),
        "cross price elasticity",
        "cross price elasticity of demand",
        "cross elasticity",
        "substitutes and complements",
    ),
    _spec(
        "production_function",
        "econ_curve",
        r"q=f(L,K;A)",
        ("functions", "labor", "capital"),
        "behavioral_relation",
        _rows(
            ("q", "output"),
            ("L", "labor input"),
            ("K", "capital input"),
            ("A", "technology or total factor productivity"),
            ("MP_L", "marginal product of labor holding capital fixed"),
            ("MP_K", "marginal product of capital holding labor fixed"),
        ),
        ("labor input", "capital input", "output", "technology"),
        ("input", "output", "production function", "marginal product"),
        "production",
        "production function",
        "production functions",
        "production theory",
        "technology and production",
    ),
    _spec(
        "labor_market",
        "econ_supply_demand",
        r"L_d(w^*)=L_s(w^*)=L^*",
        ("supply and demand", "labor", "wages"),
        "equilibrium_condition",
        _rows(
            ("w^*", "equilibrium real wage"),
            ("L^*", "equilibrium employment"),
            ("L_d(w)", "quantity of labor demanded at wage w"),
            ("L_s(w)", "quantity of labor supplied at wage w"),
        ),
        ("wage", "labor demanded", "labor supplied", "employment"),
        ("wage", "labor", "labor demand", "labor supply", "w^*", "L^*"),
        "labor market",
        "labor markets",
        "labour market",
        "labor market equilibrium",
    ),
    _spec(
        "labor_input_market",
        "econ_curve",
        r"w=MRP_L=MR\cdot MP_L",
        ("production", "marginal product", "profit maximization"),
        "optimality_condition",
        _rows(
            ("w", "wage paid for one more unit of labor"),
            ("MP_L", "marginal product of labor"),
            ("MR", "marginal revenue from one more unit of output"),
            ("MRP_L", "marginal revenue product of labor"),
            ("L^*", "profit-maximizing labor input"),
        ),
        ("wage", "marginal product of labor", "marginal revenue product", "labor input"),
        ("labor input", "wage", "MRP_L", "L^*"),
        "labor input market",
        "demand for labor",
        "labor demand",
        "marginal revenue product of labor",
        "derived demand for labor",
        "input markets i",
        "input markets i labor",
        "input markets i labor market",
    ),
    _spec(
        "capital_input_market",
        "econ_curve",
        r"r_K=MRP_K=MR\cdot MP_K",
        ("production", "marginal product", "profit maximization"),
        "optimality_condition",
        _rows(
            ("r_K", "rental price of one more unit of capital"),
            ("MP_K", "marginal product of capital"),
            ("MR", "marginal revenue from one more unit of output"),
            ("MRP_K", "marginal revenue product of capital"),
            ("K^*", "profit-maximizing capital input"),
        ),
        ("rental price", "marginal product of capital", "marginal revenue product", "capital input"),
        ("capital input", "rental price", "MRP_K", "K^*"),
        "capital input market",
        "demand for capital",
        "capital demand",
        "marginal revenue product of capital",
        "derived demand for capital",
    ),
    _spec(
        "factor_input_markets",
        "econ_production_isoquants",
        r"MRTS_{LK}=\frac{MP_L}{MP_K}=\frac{w}{r_K},\quad q=A L^\alpha K^{1-\alpha}",
        ("production", "isoquants", "cost minimization"),
        "optimality_condition",
        _rows(
            ("w", "price of labor input"),
            ("r_K", "rental price of capital input"),
            ("MRTS_{LK}", "marginal rate of technical substitution at the chosen bundle"),
            (r"\bar q", "target output on the retained isoquant"),
            ("L^*,K^*", "cost-minimizing input bundle"),
        ),
        ("labor input", "capital input", "wage", "rental price", "target output", "cost minimization"),
        ("labor", "capital", "isoquant", "isocost", "tangency", "MRTS"),
        "labor and capital input markets",
        "input markets",
        "input markets ii",
        "input markets ii labor and capital",
        "factor markets",
        "markets for labor and capital",
    ),
    _spec(
        "intertemporal_choice",
        "econ_budget",
        r"c_1+\frac{c_2}{1+r}=y_1+\frac{y_2}{1+r}",
        ("consumer choice", "present value", "interest rates"),
        "budget_constraint",
        _rows(
            ("c_1,c_2", "consumption now and later"),
            ("y_1,y_2", "income now and later"),
            ("r", "real interest rate"),
            ("1/(1+r)", "present-value price of future consumption"),
        ),
        ("current consumption", "future consumption", "interest rate", "present value"),
        ("c_1", "c_2", "endowment", "intertemporal budget", "slope -(1+r)"),
        "intertemporal choice",
        "consumption over time",
        "making choices over time",
        "saving and borrowing",
        "intertemporal budget constraint",
    ),
    _spec(
        "cost_curves",
        "econ_curve",
        r"TC(q)=FC+VC(q),\quad AC(q)=\frac{TC(q)}{q},\quad MC(q)=\frac{dTC(q)}{dq}",
        ("production", "functions", "derivatives"),
        "accounting_identity",
        _rows(
            ("FC", "fixed cost that does not vary with current output"),
            ("VC(q)", "variable cost of producing q"),
            ("TC(q)", "total cost, equal to fixed plus variable cost"),
            ("AC(q)", "average total cost per unit"),
            ("AVC(q)", "average variable cost per unit"),
            ("MC(q)", "marginal cost of one more unit"),
        ),
        ("fixed cost", "variable cost", "total cost", "average cost", "marginal cost"),
        ("FC", "VC", "TC", "AC", "MC", "output"),
        "costs",
        "cost curves",
        "costs and cost curves",
        "fixed variable total average and marginal costs",
        "fc vc tc ac mc",
        "costs incl fc vc tc ac mc",
        "costs including fc vc tc ac mc",
    ),
    _spec(
        "perfect_competition",
        "econ_curve",
        r"P=MR=MC(q^*)",
        ("costs", "marginal analysis", "price-taking firms"),
        "optimality_condition",
        _rows(
            ("P", "market price taken as given by the firm"),
            ("MR", "marginal revenue, equal to price for a price taker"),
            ("MC(q)", "marginal cost at output q"),
            ("q^*", "profit-maximizing output when operating"),
            (r"\pi", "revenue minus economic cost"),
        ),
        ("price taker", "price", "marginal revenue", "marginal cost", "profit"),
        ("P=MR", "MC", "q^*", "profit or loss"),
        "perfect competition",
        "competition",
        "competition i",
        "competitive firm",
        "competitive markets",
        "price taking firm",
    ),
    _spec(
        "competitive_shutdown",
        "econ_curve",
        r"q^*=0\quad\mathrm{if}\quad P<\min_q AVC(q)",
        ("perfect competition", "variable costs", "profit maximization"),
        "classification_rule",
        _rows(
            ("P", "market price"),
            ("AVC(q)", "average variable cost at output q"),
            (r"\min AVC", "short-run shutdown price"),
            ("q^*", "chosen output, zero below the shutdown price"),
            ("FC", "fixed cost paid in the short run even after shutdown"),
        ),
        ("price", "average variable cost", "fixed cost", "shut down"),
        ("P", "MC", "AVC", "shutdown point", "q=0"),
        "shutdown",
        "shutdown condition",
        "competitive shutdown",
        "firm shutdown decision",
        "short run shutdown",
        "competition ii",
    ),
    _spec(
        "monopoly",
        "econ_curve",
        r"MR(q_m)=MC(q_m),\quad P_m=P(q_m)",
        ("demand", "costs", "marginal revenue"),
        "optimality_condition",
        _rows(
            ("q_m", "monopoly profit-maximizing quantity"),
            ("P_m", "price read from demand at q_m"),
            ("MR(q)", "marginal revenue from selling one more unit"),
            ("MC(q)", "marginal cost of one more unit"),
            ("P(q)", "inverse market demand"),
        ),
        ("demand", "marginal revenue", "marginal cost", "quantity", "price"),
        ("demand", "MR", "MC", "q_m", "P_m"),
        "monopoly",
        "monopolist",
        "monopoly pricing",
        "monopoly i",
    ),
    _spec(
        "marginal_revenue",
        "econ_curve",
        r"MR(q)=\frac{d[P(q)q]}{dq}=P(q)+qP'(q)",
        ("inverse demand", "revenue", "derivatives"),
        "definition",
        _rows(
            ("TR(q)", "total revenue P(q)q"),
            ("MR(q)", "derivative of total revenue with respect to output"),
            ("P(q)", "inverse demand"),
            (r"P'(q)", "change in price needed to sell additional output"),
        ),
        ("total revenue", "price", "quantity", "marginal revenue"),
        ("demand", "marginal revenue", "TR", "MR"),
        "marginal revenue",
        "total and marginal revenue",
        "marginal revenue curve",
    ),
    _spec(
        "price_discrimination",
        "econ_curve",
        r"MR_1(q_1)=MR_2(q_2)=MC(q_1+q_2)",
        ("monopoly", "marginal revenue", "market segmentation"),
        "optimality_condition",
        _rows(
            ("q_1,q_2", "quantities sold to separated customer groups"),
            ("MR_1,MR_2", "marginal revenue in each group"),
            ("MC", "marginal cost of total output"),
            ("P_1,P_2", "group-specific prices read from demand"),
        ),
        ("market 1", "market 2", "marginal revenue", "marginal cost", "price"),
        ("D_1", "D_2", "MR_1", "MR_2", "MC", "P_1", "P_2"),
        "price discrimination",
        "third degree price discrimination",
        "first degree price discrimination",
        "second degree price discrimination",
        "monopoly ii",
    ),
    _spec(
        "oligopoly",
        "game_payoff",
        r"\pi_i(q_i,q_{-i})=P(Q)q_i-C_i(q_i)",
        ("profits", "best responses", "strategic interaction"),
        "behavioral_relation",
        _rows(
            ("q_i", "output chosen by firm i"),
            (r"q_{-i}", "rivals' output choices"),
            (r"Q=\sum_jq_j", "total market output"),
            (r"\pi_i", "profit of firm i"),
            (r"BR_i", "firm i's best response"),
        ),
        ("firm 1", "firm 2", "strategy", "profit", "best response"),
        ("firm 1 best response", "firm 2 best response", "equilibrium", "reaction curves"),
        "oligopoly",
        "oligopoly and strategic behavior",
        "cournot oligopoly",
        "bertrand oligopoly",
        "oligopoly i",
    ),
    _spec(
        "oligopoly_collusion",
        "game_payoff",
        r"Q_C=\frac{a-c}{2b}<Q_N=\frac{2(a-c)}{3b}",
        ("oligopoly", "Cournot best responses", "joint-profit maximization"),
        "comparative_static",
        _rows(
            ("Q_N", "total output at the symmetric Cournot-Nash equilibrium"),
            ("Q_C", "joint-profit-maximizing cartel output"),
            ("P_N", "market price at Cournot-Nash output"),
            ("P_C", "market price at collusive output"),
            (r"\pi_i", "per-firm profit under the stated symmetric allocation"),
        ),
        ("Cournot", "collusion", "joint profit", "quantity", "price"),
        ("reaction curves", "Cournot equilibrium", "collusive quantity", "collusive price"),
        "oligopoly ii",
        "collusion in oligopoly",
        "cournot and collusion",
    ),
    _spec(
        "strategic_game",
        "game_payoff",
        r"G=\langle N,(S_i)_{i\in N},(u_i)_{i\in N}\rangle",
        ("sets", "payoffs", "optimization"),
        "definition",
        _rows(
            ("N", "set of players"),
            ("S_i", "strategy set of player i"),
            ("s_i", "strategy selected by player i"),
            (r"s_{-i}", "strategies selected by all other players"),
            ("u_i", "payoff function of player i"),
        ),
        ("players", "strategies", "payoffs"),
        ("row player", "column player", "strategies", "payoffs"),
        "game theory",
        "game",
        "games",
        "strategic game",
        "normal form game",
        "payoff matrix",
        "strategic interaction",
    ),
    _spec(
        "nash_equilibrium",
        "game_payoff",
        r"s_i^*\in BR_i(s_{-i}^*)\quad\forall i",
        ("strategic games", "payoffs", "best responses"),
        "best_response_condition",
        _rows(
            (r"s^*", "candidate strategy profile"),
            (r"s_i^*", "player i's strategy in the candidate profile"),
            (r"s_{-i}^*", "other players' strategies in the candidate profile"),
            (r"BR_i", "best-response correspondence of player i"),
            ("u_i", "payoff used to compare unilateral deviations"),
        ),
        ("best response", "unilateral deviation", "strategy profile", "payoff"),
        ("payoffs", "row best responses", "column best responses", "Nash equilibrium"),
        "nash equilibrium",
        "nash equilibria",
        "mutual best response",
    ),
    _spec(
        "dominant_strategy",
        "game_payoff",
        r"u_i(s_i^D,s_{-i})\geq u_i(s_i',s_{-i})\quad\forall s_i',s_{-i}",
        ("strategic games", "payoffs"),
        "best_response_condition",
        _rows(
            (r"s_i^D", "dominant strategy of player i"),
            (r"s_i'", "alternative strategy for player i"),
            (r"s_{-i}", "arbitrary strategies of the other players"),
            ("u_i", "payoff of player i"),
        ),
        ("every rival strategy", "payoff", "dominant strategy"),
        ("payoffs", "row comparison", "column comparison", "dominant strategy"),
        "dominant strategy",
        "dominant strategies",
        "strictly dominant strategy",
        "weakly dominant strategy",
    ),
    _spec(
        "consumer_surplus",
        "econ_supply_demand",
        r"CS=\int_0^{Q^*}[P_D(q)-P^*]\,dq",
        ("demand", "willingness to pay", "integration or areas"),
        "welfare_measure",
        _rows(
            ("CS", "consumer surplus"),
            (r"P_D(q)", "inverse demand or marginal willingness to pay"),
            ("P^*", "market price"),
            ("Q^*", "quantity purchased"),
        ),
        ("willingness to pay", "market price", "consumer surplus"),
        ("demand", "price", "quantity", "consumer surplus"),
        "consumer surplus",
        "buyers surplus",
    ),
    _spec(
        "producer_surplus",
        "econ_supply_demand",
        r"PS=\int_0^{Q^*}[P^*-P_S(q)]\,dq",
        ("supply", "marginal cost", "integration or areas"),
        "welfare_measure",
        _rows(
            ("PS", "producer surplus"),
            (r"P_S(q)", "inverse supply or marginal opportunity cost"),
            ("P^*", "market price"),
            ("Q^*", "quantity sold"),
        ),
        ("market price", "marginal cost", "producer surplus"),
        ("supply", "price", "quantity", "producer surplus"),
        "producer surplus",
        "sellers surplus",
    ),
    _spec(
        "total_surplus",
        "econ_supply_demand",
        r"TS=CS+PS",
        ("consumer surplus", "producer surplus"),
        "accounting_identity",
        _rows(
            ("TS", "total surplus from completed trades"),
            ("CS", "consumer surplus"),
            ("PS", "producer surplus"),
            ("Q^*", "efficient traded quantity in the benchmark model"),
        ),
        ("consumer surplus", "producer surplus", "total surplus"),
        ("demand", "supply", "CS", "PS", "TS"),
        "total surplus",
        "social surplus",
        "supply and demand and consumer producer surplus",
    ),
    _spec(
        "welfare_surplus",
        "econ_supply_demand",
        r"TS(Q)=\int_0^Q[MB(q)-MC(q)]\,dq",
        ("supply", "demand", "marginal benefit", "marginal cost"),
        "welfare_measure",
        _rows(
            ("MB(q)", "marginal benefit of unit q"),
            ("MC(q)", "marginal opportunity cost of unit q"),
            ("CS", "consumer surplus"),
            ("PS", "producer surplus"),
            ("TS", "total surplus, equal to CS plus PS"),
        ),
        ("marginal benefit", "marginal cost", "consumer surplus", "producer surplus", "total surplus"),
        ("demand", "supply", "CS", "PS", "efficient quantity"),
        "welfare",
        "welfare and surplus",
        "economic welfare",
        "welfare economics",
        "gains from trade",
    ),
    _spec(
        "tax_incidence",
        "econ_tax_wedge",
        r"P_b-P_s=t",
        ("supply", "demand", "elasticity", "taxes"),
        "policy_wedge",
        _rows(
            ("t", "per-unit tax wedge"),
            ("P_b", "price paid by buyers after tax"),
            ("P_s", "price received by sellers after tax"),
            ("P^*", "pre-tax equilibrium price"),
            (r"\varepsilon_d,\varepsilon_s", "demand and supply elasticities governing burden shares"),
        ),
        ("tax", "buyer price", "seller price", "buyer burden", "seller burden", "elasticity"),
        ("demand", "supply", "P_b", "P_s", "tax wedge", "incidence"),
        "tax incidence",
        "incidence of taxation",
        "government redistribution and taxation",
        "who bears a tax",
    ),
    _spec(
        "tax_deadweight_loss",
        "econ_tax_wedge",
        r"DWL=\frac{1}{2}t(Q_0-Q_t)",
        ("surplus", "tax incidence", "supply and demand"),
        "welfare_measure",
        _rows(
            ("DWL", "total surplus lost because the tax prevents trades"),
            ("t", "per-unit tax wedge"),
            ("Q_0", "quantity traded before tax"),
            ("Q_t", "quantity traded after tax"),
            (r"tQ_t", "tax revenue transferred to the government"),
        ),
        ("tax", "quantity before tax", "quantity after tax", "tax revenue", "deadweight loss"),
        ("demand", "supply", "tax wedge", "revenue", "DWL"),
        "deadweight loss",
        "dwl",
        "taxes and deadweight loss",
        "tax and deadweight loss",
        "government taxation and deadweight loss",
        "excess burden of taxation",
    ),
    _spec(
        "externality",
        "econ_curve",
        r"MSC(Q^*)=MSB(Q^*)",
        ("marginal analysis", "welfare", "markets"),
        "optimality_condition",
        _rows(
            ("MPC", "marginal private cost"),
            ("MSC", "marginal social cost including external cost"),
            ("MPB", "marginal private benefit"),
            ("MSB", "marginal social benefit including external benefit"),
            ("Q^*", "socially efficient quantity"),
        ),
        ("private", "social", "external cost or benefit", "efficient quantity"),
        ("MPC", "MSC", "MPB or MSB", "market quantity", "efficient quantity"),
        "externality",
        "externalities",
        "negative externality",
        "positive externality",
    ),
    _spec(
        "coase_bargaining",
        "econ_curve",
        r"MB_{abatement}(a^*)=MC_{abatement}(a^*)",
        ("externalities", "property rights", "bargaining"),
        "optimality_condition",
        _rows(
            ("a", "amount of abatement or negotiated activity change"),
            (r"MB_{abatement}", "marginal benefit from reducing the externality"),
            (r"MC_{abatement}", "marginal cost of reducing the externality"),
            ("a^*", "efficient bargained abatement"),
            ("TC", "transaction costs of reaching and enforcing agreement"),
        ),
        ("property rights", "transaction costs", "bargaining", "efficient"),
        ("marginal benefit", "marginal cost", "efficient abatement", "bargaining range"),
        "coase theorem",
        "coase bargaining",
        "property rights and externalities",
    ),
    _spec(
        "common_resource",
        "econ_curve",
        r"MSC(q)=MPC(q)+MEC(q)>MPC(q)",
        ("externalities", "rivalry", "excludability"),
        "behavioral_relation",
        _rows(
            ("q", "use or extraction from the common resource"),
            ("MPC", "marginal private cost faced by one user"),
            ("MEC", "marginal external depletion or congestion cost"),
            ("MSC", "marginal social cost"),
            ("q^*", "efficient use below the open-access quantity"),
        ),
        ("rival", "nonexcludable", "external cost", "overuse"),
        ("private cost", "social cost", "open access quantity", "efficient quantity"),
        "common resource",
        "common resources",
        "tragedy of the commons",
        "open access resource",
    ),
    _spec(
        "public_good",
        "econ_curve",
        r"\sum_i MB_i(G^*)=MC(G^*)",
        ("externalities", "welfare", "marginal analysis"),
        "optimality_condition",
        _rows(
            ("G", "quantity of the public good"),
            ("MB_i(G)", "person i's marginal benefit"),
            (r"\sum_i MB_i", "vertical sum of individual marginal benefits"),
            ("MC(G)", "marginal provision cost"),
            ("G^*", "efficient public-good quantity"),
        ),
        ("nonrival", "nonexcludable", "free rider", "marginal benefits", "provision cost"),
        ("individual marginal benefits", "social marginal benefit", "marginal cost", "G^*"),
        "public good",
        "public goods",
        "free rider problem",
        "public good provision",
    ),
    _spec(
        "international_trade",
        "econ_supply_demand",
        r"M=Q_d(P_w)-Q_s(P_w)",
        ("supply and demand", "welfare", "opportunity cost"),
        "accounting_identity",
        _rows(
            ("P_w", "world price faced by a small open economy"),
            (r"Q_d(P_w)", "domestic quantity demanded at the world price"),
            (r"Q_s(P_w)", "domestic quantity supplied at the world price"),
            ("M", "imports, equal to domestic demand minus domestic supply"),
            ("X", "exports when domestic supply exceeds domestic demand"),
        ),
        ("world price", "domestic demand", "domestic supply", "imports or exports", "gains from trade"),
        ("domestic demand", "domestic supply", "world price", "imports or exports"),
        "trade",
        "international trade",
        "introduction to trade",
        "gains from international trade",
        "free trade",
        "imports and exports",
    ),
    _spec(
        "tariff",
        "econ_supply_demand",
        r"M_t=Q_d(P_w+t)-Q_s(P_w+t)",
        ("international trade", "supply and demand", "tax revenue"),
        "policy_wedge",
        _rows(
            ("P_w", "world price before the tariff"),
            ("t", "per-unit tariff"),
            ("P_w+t", "domestic price with the tariff"),
            ("M_0", "imports under free trade"),
            ("M_t", "imports after the tariff"),
        ),
        ("world price", "tariff", "domestic price", "imports before", "imports after", "tariff revenue", "deadweight loss"),
        ("domestic demand", "domestic supply", "world price", "tariff price", "import reduction", "deadweight loss"),
        "tariff",
        "import tariff",
        "tariffs and trade",
        "international trade welfare and policy",
    ),
    _spec(
        "choice_under_uncertainty",
        "econ_curve",
        r"EU=\sum_s p_su(c_s)",
        ("probability", "utility", "weighted averages"),
        "expected_utility",
        _rows(
            ("s", "possible state of the world"),
            ("p_s", "probability of state s"),
            ("c_s", "consumption or payoff in state s"),
            ("u(c_s)", "state-dependent utility"),
            ("EU", "probability-weighted expected utility"),
        ),
        ("state", "probability", "payoff", "utility", "expected utility"),
        ("states", "probabilities", "utilities", "expected utility"),
        "uncertainty",
        "choice under uncertainty",
        "expected utility",
        "risk and uncertainty",
    ),
    _spec(
        "social_insurance",
        "econ_curve",
        r"EU=p\,u(c_{loss})+(1-p)u(c_{no\ loss})",
        ("uncertainty", "insurance", "consumption smoothing"),
        "expected_utility",
        _rows(
            ("p", "probability of the insured loss"),
            (r"c_{loss}", "consumption in the loss state after transfers"),
            (r"c_{no\ loss}", "consumption in the no-loss state after contributions"),
            (r"\tau", "social-insurance contribution or tax"),
            ("b", "benefit paid in the covered state"),
        ),
        ("loss probability", "contribution", "benefit", "consumption smoothing", "insurance"),
        ("loss state", "no loss state", "contribution", "benefit", "consumption"),
        "social insurance",
        "government social insurance",
        "unemployment insurance",
        "disability insurance",
    ),
    _spec(
        "adverse_selection",
        "econ_curve",
        r"\pi_{pool}=E[C\mid\text{insured pool}]",
        ("uncertainty", "insurance", "conditional expectations", "private information"),
        "classification_rule",
        _rows(
            (r"\pi_{pool}", "premium based on expected cost in the insured pool"),
            ("C", "insurer cost when a covered loss occurs"),
            (r"\theta", "privately known risk type"),
            (r"p_\theta", "loss probability for type theta"),
            (r"E[C\mid pool]", "average expected cost of people who enroll"),
        ),
        ("risk type", "private information", "premium", "high risk", "low risk"),
        ("high risk", "low risk", "pooling premium", "enrollment"),
        "adverse selection",
        "hidden information",
        "insurance market selection",
    ),
    _spec(
        "moral_hazard",
        "econ_curve",
        r"e^*\in\arg\max_e\{E[u(c;e)]-v(e)\}",
        ("uncertainty", "insurance", "incentives", "optimization"),
        "incentive_condition",
        _rows(
            ("e", "unobserved prevention or care effort"),
            ("e^*", "effort chosen under the insurance contract"),
            ("c", "state-contingent consumption after coverage"),
            ("v(e)", "cost or disutility of effort"),
            (r"p(e)", "loss probability affected by effort"),
        ),
        ("coverage", "unobserved action", "effort", "incentive", "loss probability"),
        ("coverage", "effort", "loss probability", "private action"),
        "moral hazard",
        "hidden action",
        "insurance incentives",
    ),
    _spec(
        "equity_efficiency",
        "econ_curve",
        r"W=W(u_1,\ldots,u_n)",
        ("welfare", "utility", "distribution"),
        "welfare_measure",
        _rows(
            ("W", "social welfare index under an explicit ethical criterion"),
            ("u_i", "utility or well-being of person i"),
            (r"\Delta W", "welfare change from a policy or allocation"),
            ("efficiency", "absence of an available Pareto improvement"),
            ("equity", "distributional judgment stated separately from efficiency"),
        ),
        ("winners", "losers", "efficiency", "equity", "distribution"),
        ("individual 1", "individual 2", "utility possibility", "efficient frontier", "social welfare"),
        "equity",
        "equity and efficiency",
        "distribution and equity",
        "inequality and welfare",
    ),
    _spec(
        "behavioral_economics",
        "econ_curve",
        r"V=\sum_t\beta\delta^t u(c_t)",
        ("consumer choice", "utility", "probability or time"),
        "behavioral_relation",
        _rows(
            (r"\beta", "present-bias parameter"),
            (r"\delta", "long-run discount factor"),
            ("c_t", "consumption or payoff at time t"),
            ("u(c_t)", "instantaneous utility"),
            ("V", "behaviorally discounted value"),
        ),
        ("benchmark choice", "observed choice", "bias", "incentive"),
        ("now", "later", "benchmark", "observed choice"),
        "behavioral economics",
        "behavioral",
        "behavioural economics",
        "present bias",
        "bounded rationality",
        "loss aversion",
    ),
    _spec(
        "health_economics",
        "econ_curve",
        r"MB_H(q_H^*)=MC_H(q_H^*)",
        ("marginal analysis", "insurance", "externalities"),
        "optimality_condition",
        _rows(
            ("q_H", "quantity of health care or health-producing input"),
            (r"MB_H", "marginal health benefit valued in the stated units"),
            (r"MC_H", "marginal social resource cost of care"),
            (r"P_{patient}", "out-of-pocket price faced by the patient"),
            ("q_H^*", "efficient health-care quantity in the stated model"),
        ),
        ("health care", "patient price", "marginal benefit", "marginal cost", "insurance"),
        ("health care quantity", "patient price", "marginal benefit", "marginal cost", "efficient quantity"),
        "health economics",
        "health",
        "economics of health",
        "health care markets",
        "healthcare economics",
    ),
)


def _normalize_title(title: str) -> str:
    if not isinstance(title, str):
        raise TypeError("economics model title must be a string")
    separated_title = "".join(" " if unicodedata.category(char) == "Pd" else char for char in title)
    ascii_title = unicodedata.normalize("NFKD", separated_title).encode("ascii", "ignore").decode("ascii")
    ascii_title = ascii_title.casefold().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", ascii_title).strip()


_SOURCE_LABEL_RE = re.compile(
    r"^(?:lecture summary|lecture|lec|lesson) (?:[0-9]+(?: [0-9]+)*|[ivxlcdm]+) "
)


def _strip_source_label(normalized_title: str) -> str:
    return _SOURCE_LABEL_RE.sub("", normalized_title, count=1)


def _build_registry() -> tuple[Mapping[str, EconomicsModelSpec], Mapping[str, str]]:
    models: dict[str, EconomicsModelSpec] = {}
    exact_titles: dict[str, str] = {}
    for definition in _DEFINITIONS:
        spec = definition.spec
        if spec.model_id in models:
            raise RuntimeError(f"duplicate economics model id: {spec.model_id}")
        if spec.visual_kind not in ECON_VISUAL_KINDS:
            raise RuntimeError(f"unsupported economics visual kind: {spec.visual_kind}")
        if not spec.canonical_formula or not spec.prerequisites or not spec.exact_symbol_rows:
            raise RuntimeError(f"incomplete economics model spec: {spec.model_id}")
        for tokens in (spec.required_example_tokens, spec.required_figure_tokens):
            if not tokens or any(not token.strip() for token in tokens) or len(tokens) != len(set(tokens)):
                raise RuntimeError(f"invalid required tokens for economics model: {spec.model_id}")
        symbols = tuple(row.symbol for row in spec.exact_symbol_rows)
        if len(symbols) != len(set(symbols)):
            raise RuntimeError(f"duplicate symbol row for economics model: {spec.model_id}")
        models[spec.model_id] = spec
        for title in definition.exact_titles:
            normalized = _normalize_title(title)
            previous = exact_titles.get(normalized)
            if previous is not None and previous != spec.model_id:
                raise RuntimeError(
                    f"economics title alias {title!r} maps to both {previous!r} and {spec.model_id!r}"
                )
            exact_titles[normalized] = spec.model_id
    return MappingProxyType(models), MappingProxyType(exact_titles)


ECONOMICS_MODEL_REGISTRY, _EXACT_TITLE_MODEL_IDS = _build_registry()
# A descriptive alias for callers migrating from stem_course.ECONOMICS_TOPIC_SPECS.
ECONOMICS_MODEL_SPECS = ECONOMICS_MODEL_REGISTRY

# The authoritative MIT 14.01 lecture-title surface. Keeping this public and
# data-only lets route and scenario tests audit all titles without duplicating
# resolver expectations in each consumer.
MIT_14_01_TITLE_MODEL_IDS: Mapping[str, str] = MappingProxyType({
    "Introduction and Supply & Demand": "supply_demand_intro",
    "Preferences and Utility Functions": "utility_representation",
    "Budget Constraints and Constrained Choice": "consumer_choice",
    "Demand Curves and Income/Substitution Effects": "income_substitution_effects",
    "Production Theory": "production_function",
    "Costs": "cost_curves",
    "Competition I": "perfect_competition",
    "Competition II": "competitive_shutdown",
    "Supply and Demand & Consumer/Producer Surplus": "total_surplus",
    "Welfare Economics": "welfare_surplus",
    "Monopoly I": "monopoly",
    "Monopoly II": "price_discrimination",
    "Oligopoly I": "oligopoly",
    "Oligopoly II": "oligopoly_collusion",
    "Input Markets I\N{EM DASH}Labor Market": "labor_input_market",
    "Input Markets II\N{EM DASH}Labor and Capital": "factor_input_markets",
    "Making Choices over Time": "intertemporal_choice",
    "Introduction to Trade": "international_trade",
    "International Trade: Welfare and Policy": "tariff",
    "Uncertainty": "choice_under_uncertainty",
    "Social Insurance": "social_insurance",
    "Efficiency and Equity": "equity_efficiency",
    "Government Redistribution and Taxation": "tax_incidence",
    "Externalities": "externality",
    "Behavioral Economics": "behavioral_economics",
    "Healthcare Economics": "health_economics",
})

if len(MIT_14_01_TITLE_MODEL_IDS) != 26:
    raise RuntimeError("MIT 14.01 title contract must contain exactly 26 titles")
_MIT_14_01_NORMALIZED_TITLE_MODEL_IDS = MappingProxyType({
    _normalize_title(title): model_id
    for title, model_id in MIT_14_01_TITLE_MODEL_IDS.items()
})
if len(_MIT_14_01_NORMALIZED_TITLE_MODEL_IDS) != 26:
    raise RuntimeError("MIT 14.01 title contract contains normalized duplicates")
if not set(MIT_14_01_TITLE_MODEL_IDS.values()) <= set(ECONOMICS_MODEL_REGISTRY):
    raise RuntimeError("MIT 14.01 title contract references an unknown economics model")


@dataclass(frozen=True)
class _TitleRule:
    model_id: str
    any_phrases: tuple[str, ...] = ()
    all_phrases: tuple[str, ...] = ()
    excluded_phrases: tuple[str, ...] = ()

    def matches(self, normalized_title: str) -> bool:
        padded = f" {normalized_title} "

        def contains(phrase: str) -> bool:
            return f" {_normalize_title(phrase)} " in padded

        if self.excluded_phrases and any(contains(phrase) for phrase in self.excluded_phrases):
            return False
        if self.all_phrases and not all(contains(phrase) for phrase in self.all_phrases):
            return False
        return not self.any_phrases or any(contains(phrase) for phrase in self.any_phrases)


# Specific concepts precede umbrella concepts.  Exact aliases are consulted
# before this table, so adding a broad marker cannot shadow a canonical title.
_BROAD_TITLE_RULES: tuple[_TitleRule, ...] = (
    _TitleRule("cross_price_elasticity", any_phrases=("cross price elasticity", "cross elasticity")),
    _TitleRule("cross_price_elasticity", all_phrases=("elasticity", "substitutes")),
    _TitleRule("cross_price_elasticity", all_phrases=("elasticity", "complements")),
    _TitleRule("income_elasticity", all_phrases=("income", "elasticity")),
    _TitleRule(
        "own_price_elasticity",
        any_phrases=("own price elasticity", "price elasticity", "elasticity of demand", "elasticities"),
        excluded_phrases=("income elasticity", "cross price elasticity", "cross elasticity"),
    ),
    _TitleRule("consumer_surplus", any_phrases=("consumer surplus", "buyer surplus")),
    _TitleRule("producer_surplus", any_phrases=("producer surplus", "seller surplus")),
    _TitleRule("total_surplus", any_phrases=("total surplus", "social surplus")),
    _TitleRule("price_controls", all_phrases=("ceiling", "floor")),
    _TitleRule("price_controls", all_phrases=("shortage", "surplus")),
    _TitleRule("price_controls", any_phrases=("shortages and surpluses",)),
    _TitleRule("price_ceiling_shortage", any_phrases=("price ceiling", "rent control", "excess demand", "shortage")),
    _TitleRule("price_floor_surplus", any_phrases=("price floor", "minimum wage", "excess supply")),
    _TitleRule("income_substitution_effects", any_phrases=("income and substitution", "substitution effect", "slutsky")),
    _TitleRule("income_substitution_effects", all_phrases=("income", "substitution")),
    _TitleRule("marginal_rate_of_substitution", any_phrases=("marginal rate of substitution", "mrs")),
    _TitleRule("intertemporal_choice", any_phrases=("intertemporal", "saving and borrowing", "consumption over time")),
    _TitleRule("consumer_choice", any_phrases=("consumer choice", "utility maximization")),
    _TitleRule("budget_constraint", any_phrases=("budget constraint", "budget line", "affordable set")),
    _TitleRule("utility_representation", any_phrases=("utility", "indifference curve", "indifference curves")),
    _TitleRule("consumer_preferences", any_phrases=("consumer preference", "preference relation")),
    _TitleRule("factor_input_markets", all_phrases=("labor", "capital", "input")),
    _TitleRule("factor_input_markets", any_phrases=("factor market", "input market")),
    _TitleRule(
        "labor_input_market",
        any_phrases=("labor input", "labour input", "demand for labor", "demand for labour", "labor demand", "labour demand", "mrp of labor"),
    ),
    _TitleRule(
        "capital_input_market",
        any_phrases=("capital input", "demand for capital", "capital demand", "mrp of capital"),
    ),
    _TitleRule("labor_market", any_phrases=("labor market", "labour market", "employment market")),
    _TitleRule("production_function", any_phrases=("production function", "production technology", "marginal product", "returns to scale")),
    _TitleRule("competitive_shutdown", any_phrases=("shutdown", "average variable cost")),
    _TitleRule("price_discrimination", any_phrases=("price discrimination", "discriminating monopolist")),
    _TitleRule("marginal_revenue", any_phrases=("marginal revenue", "revenue curve")),
    _TitleRule("monopoly", any_phrases=("monopoly", "monopolist", "market power")),
    _TitleRule("perfect_competition", any_phrases=("perfect competition", "competitive firm", "price taker", "price taking")),
    _TitleRule("cost_curves", all_phrases=("fc", "vc", "tc", "ac", "mc")),
    _TitleRule("cost_curves", any_phrases=("cost curve", "fixed cost", "variable cost", "total cost", "average cost", "marginal cost")),
    _TitleRule("nash_equilibrium", any_phrases=("nash", "mutual best response")),
    _TitleRule("dominant_strategy", any_phrases=("dominant strategy", "dominant strategies", "dominance")),
    _TitleRule("oligopoly", any_phrases=("oligopoly", "cournot", "bertrand", "strategic firms")),
    _TitleRule("strategic_game", any_phrases=("game theory", "strategic game", "games", "payoff matrix", "strategic interaction")),
    _TitleRule("tax_incidence", any_phrases=("tax incidence", "incidence of tax", "tax burden")),
    _TitleRule("tax_deadweight_loss", any_phrases=("deadweight loss", "dwl", "excess burden", "tax wedge")),
    _TitleRule("welfare_surplus", any_phrases=("economic welfare", "welfare analysis", "gains from trade")),
    _TitleRule("coase_bargaining", any_phrases=("coase", "property rights bargaining")),
    _TitleRule("common_resource", any_phrases=("common resource", "commons", "open access resource")),
    _TitleRule("public_good", any_phrases=("public good", "public goods", "free rider", "free riders", "nonrival")),
    _TitleRule("externality", any_phrases=("externality", "externalities", "external cost", "external benefit")),
    _TitleRule("adverse_selection", any_phrases=("adverse selection", "hidden information")),
    _TitleRule("moral_hazard", any_phrases=("moral hazard", "hidden action")),
    _TitleRule("social_insurance", any_phrases=("social insurance", "unemployment insurance", "disability insurance")),
    _TitleRule("health_economics", any_phrases=("health economics", "health care", "healthcare", "medical care")),
    _TitleRule("choice_under_uncertainty", any_phrases=("uncertainty", "expected utility", "risk aversion", "insurance choice")),
    _TitleRule("tariff", any_phrases=("tariff", "import duty", "customs duty")),
    _TitleRule("international_trade", any_phrases=("international trade", "free trade", "world price", "import", "export")),
    _TitleRule("behavioral_economics", any_phrases=("behavioral", "behavioural", "present bias", "loss aversion", "bounded rationality")),
    _TitleRule("equity_efficiency", any_phrases=("equity", "inequality", "distributional", "social welfare function")),
    _TitleRule("comparative_statics", any_phrases=("comparative static", "comparative statics", "equilibrium shift")),
    _TitleRule("market_equilibrium", any_phrases=("market equilibrium", "equilibrium price", "market clearing")),
    _TitleRule("demand_curve", any_phrases=("demand curve", "market demand", "individual demand")),
    _TitleRule("supply_curve", any_phrases=("supply curve", "market supply", "individual supply")),
    _TitleRule("supply_demand_curves", all_phrases=("supply", "demand", "curve")),
    _TitleRule("supply_demand_curves", all_phrases=("supply", "demand", "curves")),
    _TitleRule("supply_demand_intro", all_phrases=("supply", "demand")),
)


def resolve_economics_model(
    title: str,
    fail_closed: bool = False,
) -> EconomicsModelSpec | None:
    """Resolve a title, consulting exact aliases before ordered broad rules.

    Unknown titles return ``None`` by default.  ``fail_closed=True`` raises a
    ``ValueError`` so a planner cannot silently fall back to a generic curve.
    """

    normalized = _strip_source_label(_normalize_title(title))
    model_id = _MIT_14_01_NORMALIZED_TITLE_MODEL_IDS.get(normalized)
    if model_id is None:
        model_id = _EXACT_TITLE_MODEL_IDS.get(normalized)
    if model_id is not None:
        return ECONOMICS_MODEL_REGISTRY[model_id]

    if normalized:
        for rule in _BROAD_TITLE_RULES:
            if rule.matches(normalized):
                return ECONOMICS_MODEL_REGISTRY[rule.model_id]

    if fail_closed:
        raise ValueError(
            f"Unsupported economics topic {title!r}: add an exact model contract before planning it."
        )
    return None


__all__ = [
    "ECONOMICS_MODEL_REGISTRY",
    "ECONOMICS_MODEL_SPECS",
    "ECON_VISUAL_KINDS",
    "MIT_14_01_TITLE_MODEL_IDS",
    "EconVisualKind",
    "EconomicsModelSpec",
    "StatementKind",
    "SymbolRow",
    "resolve_economics_model",
]

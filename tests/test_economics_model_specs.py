from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from tools import stem_course
from tools.economics_model_specs import (
    ECONOMICS_MODEL_REGISTRY,
    ECON_VISUAL_KINDS,
    MIT_14_01_TITLE_MODEL_IDS,
    EconomicsModelSpec,
    resolve_economics_model,
)


def resolved(title: str) -> EconomicsModelSpec:
    spec = resolve_economics_model(title, fail_closed=True)
    assert spec is not None
    return spec


class EconomicsModelCoverageTests(unittest.TestCase):
    def test_representative_titles_cover_requested_microeconomics_models(self) -> None:
        expectations = {
            "Introduction to Supply & Demand": "supply_demand_intro",
            "Supply and demand equilibrium": "market_equilibrium",
            "Demand curves": "demand_curve",
            "Supply curves": "supply_curve",
            "Demand and supply curves": "supply_demand_curves",
            "Comparative statics after a demand shock": "comparative_statics",
            "Binding price ceiling and shortage": "price_ceiling_shortage",
            "Binding price floor and surplus": "price_floor_surplus",
            "Shortages and surpluses": "price_controls",
            "Consumer preferences": "consumer_preferences",
            "Preferences and utility": "utility_representation",
            "Budget constraints": "budget_constraint",
            "Marginal rate of substitution": "marginal_rate_of_substitution",
            "Consumer choice": "consumer_choice",
            "Income and substitution effects": "income_substitution_effects",
            "Own-price elasticity of demand": "own_price_elasticity",
            "Income elasticity of demand": "income_elasticity",
            "Cross-price elasticity of demand": "cross_price_elasticity",
            "Production functions": "production_function",
            "Labor market equilibrium": "labor_market",
            "Derived demand for labor": "labor_input_market",
            "Demand for capital": "capital_input_market",
            "Labor and capital input markets": "factor_input_markets",
            "Intertemporal choice": "intertemporal_choice",
            "Costs incl. FC, VC, TC, AC, MC": "cost_curves",
            "Perfect competition": "perfect_competition",
            "Competition": "perfect_competition",
            "Short-run shutdown condition": "competitive_shutdown",
            "Monopoly": "monopoly",
            "Marginal revenue": "marginal_revenue",
            "Third-degree price discrimination": "price_discrimination",
            "Oligopoly and strategic behavior": "oligopoly",
            "Normal-form game": "strategic_game",
            "Nash equilibrium": "nash_equilibrium",
            "Dominant strategies": "dominant_strategy",
            "Consumer surplus": "consumer_surplus",
            "Producer surplus": "producer_surplus",
            "Total surplus": "total_surplus",
            "Welfare and surplus": "welfare_surplus",
            "Tax incidence": "tax_incidence",
            "Taxes and deadweight loss": "tax_deadweight_loss",
            "DWL": "tax_deadweight_loss",
            "Externalities": "externality",
            "Coase theorem": "coase_bargaining",
            "Common resources": "common_resource",
            "Public goods": "public_good",
            "International trade": "international_trade",
            "Choice under uncertainty": "choice_under_uncertainty",
            "Social insurance": "social_insurance",
            "Adverse selection": "adverse_selection",
            "Moral hazard": "moral_hazard",
            "Equity and efficiency": "equity_efficiency",
            "Behavioral economics": "behavioral_economics",
            "Health economics": "health_economics",
        }

        for title, model_id in expectations.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_every_registry_entry_has_complete_typed_contract(self) -> None:
        self.assertGreaterEqual(len(ECONOMICS_MODEL_REGISTRY), 50)
        self.assertEqual(ECON_VISUAL_KINDS, frozenset(stem_course.ECON_VISUAL_KINDS))

        for model_id, spec in ECONOMICS_MODEL_REGISTRY.items():
            with self.subTest(model_id=model_id):
                self.assertIsInstance(spec, EconomicsModelSpec)
                self.assertEqual(spec.model_id, model_id)
                self.assertIn(spec.visual_kind, stem_course.ECON_VISUAL_KINDS)
                self.assertTrue(spec.canonical_formula)
                self.assertTrue(spec.prerequisites)
                self.assertTrue(spec.statement_kind)
                self.assertTrue(spec.exact_symbol_rows)
                self.assertTrue(spec.required_example_tokens)
                self.assertTrue(spec.required_figure_tokens)
                self.assertEqual(spec.symbol_rows, spec.exact_symbol_rows)
                self.assertEqual(spec["model_id"], model_id)
                for row in spec.exact_symbol_rows:
                    self.assertTrue(row.symbol)
                    self.assertTrue(row.meaning)
                    self.assertEqual(row["symbol"], row.symbol)
                    self.assertEqual(row["meaning"], row.meaning)


class EconomicsModelResolutionTests(unittest.TestCase):
    def test_authoritative_mit_title_contract_is_complete_and_exact(self) -> None:
        self.assertEqual(len(MIT_14_01_TITLE_MODEL_IDS), 26)
        for title, model_id in MIT_14_01_TITLE_MODEL_IDS.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_official_mit_outline_titles_resolve_exactly(self) -> None:
        expectations = {
            "Budget Constraints and Constrained Choice": "consumer_choice",
            "Production Theory": "production_function",
            "Competition I": "perfect_competition",
            "Competition II": "competitive_shutdown",
            "Welfare Economics": "welfare_surplus",
            "Input Markets I": "labor_input_market",
            "Input Markets I\N{EM DASH}Labor Market": "labor_input_market",
            "Input Markets II": "factor_input_markets",
            "Input Markets II\N{EN DASH}Labor and Capital": "factor_input_markets",
            "Making Choices over Time": "intertemporal_choice",
            "Introduction to Trade": "international_trade",
            "Government Redistribution and Taxation": "tax_incidence",
        }

        for title, model_id in expectations.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_lecture_labels_accept_arabic_and_roman_numbers(self) -> None:
        expectations = {
            "Lec 7: Competition I": "perfect_competition",
            "Lecture VII: Competition II": "competitive_shutdown",
            "Lecture Summary 15: Input Markets I\N{EM DASH}Labor Market": "labor_input_market",
            "Lesson XVI: Input Markets II\N{EN DASH}Labor and Capital": "factor_input_markets",
        }

        for title, model_id in expectations.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_official_aliases_preserve_high_risk_distinctions(self) -> None:
        distinctions = {
            "Budget Constraints": "budget_constraint",
            "Budget Constraints and Constrained Choice": "consumer_choice",
            "Input Markets I": "labor_input_market",
            "Input Markets II": "factor_input_markets",
            "Government Redistribution and Taxation": "tax_incidence",
            "Taxes and deadweight loss": "tax_deadweight_loss",
            "Welfare Economics": "welfare_surplus",
            "Efficiency and Equity": "equity_efficiency",
        }

        for title, model_id in distinctions.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_all_26_authoritative_titles_resolve_to_intentional_models(self) -> None:
        expectations = {
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
        }

        self.assertEqual(len(expectations), 26)
        for title, model_id in expectations.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_exact_and_specific_rules_precede_broad_markers(self) -> None:
        distinctions = {
            "Income elasticity for a normal good": "income_elasticity",
            "Cross-price elasticity for substitutes": "cross_price_elasticity",
            "Price discrimination by a monopolist": "price_discrimination",
            "Marginal revenue under monopoly": "marginal_revenue",
            "Labor input demand in the labor market": "labor_input_market",
            "Labor and capital input demand": "factor_input_markets",
            "Consumer surplus under a price floor": "consumer_surplus",
            "Tax incidence and the tax wedge": "tax_incidence",
            "Moral hazard in health insurance": "moral_hazard",
            "Adverse selection under uncertainty": "adverse_selection",
            "Public goods with positive externalities": "public_good",
            "Coase bargaining for an externality": "coase_bargaining",
            "Nash equilibrium in an oligopoly game": "nash_equilibrium",
            "Dominant strategy in a payoff matrix": "dominant_strategy",
        }

        for title, model_id in distinctions.items():
            with self.subTest(title=title):
                self.assertEqual(resolved(title).model_id, model_id)

    def test_price_control_imbalance_directions_are_not_interchanged(self) -> None:
        ceiling = resolved("Rent control creates excess demand")
        floor = resolved("A minimum wage creates excess supply")

        self.assertEqual(ceiling.model_id, "price_ceiling_shortage")
        self.assertIn("Q_d", ceiling.canonical_formula)
        self.assertIn("Q_s", ceiling.canonical_formula)
        self.assertLess(ceiling.canonical_formula.index("Q_d"), ceiling.canonical_formula.index("Q_s"))
        self.assertEqual(floor.model_id, "price_floor_surplus")
        self.assertLess(floor.canonical_formula.index("Q_s"), floor.canonical_formula.index("Q_d"))

    def test_unknown_and_blank_titles_obey_fail_closed(self) -> None:
        self.assertIsNone(resolve_economics_model(""))
        self.assertIsNone(resolve_economics_model("A topic outside the registry"))
        with self.assertRaisesRegex(ValueError, "Unsupported economics topic"):
            resolve_economics_model("A topic outside the registry", fail_closed=True)
        with self.assertRaises(TypeError):
            resolve_economics_model(None)  # type: ignore[arg-type]


class EconomicsModelTokenTests(unittest.TestCase):
    def test_price_control_tokens_are_exact_and_directional(self) -> None:
        self.assertEqual(
            resolved("Price ceilings").required_example_tokens,
            ("binding", "price ceiling", "quantity demanded", "quantity supplied", "shortage"),
        )
        self.assertEqual(
            resolved("Price ceilings").required_figure_tokens,
            ("demand", "supply", "P^*", "price ceiling", "shortage"),
        )
        self.assertEqual(
            resolved("Price floors").required_example_tokens,
            ("binding", "price floor", "quantity supplied", "quantity demanded", "surplus"),
        )
        self.assertEqual(
            resolved("Price floors").required_figure_tokens,
            ("demand", "supply", "P^*", "price floor", "surplus"),
        )

    def test_elasticity_tokens_name_the_changed_variables_and_classification(self) -> None:
        self.assertEqual(
            resolved("Own-price elasticity").required_example_tokens,
            ("percent change in quantity demanded", "percent change in price", "elasticity"),
        )
        self.assertEqual(
            resolved("Income elasticity").required_example_tokens,
            ("percent change in quantity demanded", "percent change in income", "normal", "inferior"),
        )
        self.assertEqual(
            resolved("Cross-price elasticity").required_example_tokens,
            ("quantity demanded of x", "price of y", "substitutes", "complements"),
        )

    def test_cost_tokens_require_all_five_cost_concepts(self) -> None:
        costs = resolved("Costs and cost curves")
        self.assertEqual(
            costs.required_example_tokens,
            ("fixed cost", "variable cost", "total cost", "average cost", "marginal cost"),
        )
        self.assertEqual(costs.required_figure_tokens, ("FC", "VC", "TC", "AC", "MC", "output"))
        self.assertEqual(
            tuple(row.symbol for row in costs.exact_symbol_rows),
            ("FC", "VC(q)", "TC(q)", "AC(q)", "AVC(q)", "MC(q)"),
        )

    def test_information_problem_tokens_keep_hidden_information_and_action_apart(self) -> None:
        selection = resolved("Adverse selection")
        hazard = resolved("Moral hazard")

        self.assertEqual(
            selection.required_example_tokens,
            ("risk type", "private information", "premium", "high risk", "low risk"),
        )
        self.assertEqual(
            hazard.required_example_tokens,
            ("coverage", "unobserved action", "effort", "incentive", "loss probability"),
        )
        self.assertNotIn("effort", selection.required_example_tokens)
        self.assertNotIn("risk type", hazard.required_example_tokens)

    def test_as_dict_returns_defensive_json_friendly_copies(self) -> None:
        spec = resolved("Tax incidence")
        exported = spec.as_dict()
        self.assertEqual(exported["model_id"], "tax_incidence")
        self.assertIsInstance(exported["prerequisites"], list)
        self.assertIsInstance(exported["exact_symbol_rows"], list)
        exported["prerequisites"].append("changed")  # type: ignore[union-attr]
        self.assertNotIn("changed", spec.prerequisites)
        with self.assertRaises(FrozenInstanceError):
            spec.model_id = "changed"  # type: ignore[misc]

    def test_new_sources_are_ascii(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for path in (root / "tools/economics_model_specs.py", Path(__file__)):
            with self.subTest(path=path.name):
                path.read_bytes().decode("ascii")


if __name__ == "__main__":
    unittest.main()

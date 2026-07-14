from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import isfinite
from pathlib import Path
import re
import unittest

from tools.economics_model_scenarios import (
    ECONOMICS_MODEL_SCENARIO_DEFINITIONS,
    ECONOMICS_MODEL_SCENARIO_REGISTRY,
    ECONOMICS_MODEL_SCENARIOS,
    ECONOMICS_SCENARIOS,
    EconomicsModelScenario,
    build_all_economics_model_scenarios,
    build_economics_model_scenario,
    economics_numeric_evidence_fingerprint,
    get_economics_model_scenario,
    recompute_economics_model_scenario,
)
from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY


EXPECTED_SALIENT_RESULTS: dict[str, tuple[str, float]] = {
    "supply_demand_intro": ("market_gap", 0.0),
    "market_equilibrium": ("equilibrium_price", 8.0),
    "demand_curve": ("quantity_demanded", 91.0),
    "supply_curve": ("quantity_supplied", 67.0),
    "supply_demand_curves": ("quantity_demanded", 48.0),
    "comparative_statics": ("quantity_change", 20.0 / 3.0),
    "price_ceiling_shortage": ("shortage", 30.0),
    "price_floor_surplus": ("surplus", 30.0),
    "price_controls": ("floor_surplus", 30.0),
    "consumer_preferences": ("ranking_gap", 4.0),
    "utility_representation": ("utility_a", 6.0),
    "budget_constraint": ("budget_slack", 10.0),
    "marginal_rate_of_substitution": ("MRS", 2.25),
    "consumer_choice": ("chosen_y", 12.0),
    "income_substitution_effects": ("total_change", 7.0),
    "own_price_elasticity": ("own_price_elasticity", -1.0),
    "income_elasticity": ("income_elasticity", 1.0),
    "cross_price_elasticity": ("cross_price_elasticity", 0.5),
    "production_function": ("output", 24.0),
    "labor_market": ("employment", 60.0),
    "labor_input_market": ("labor_input", 10.0),
    "capital_input_market": ("capital_input", 12.0),
    "factor_input_markets": ("capital_input", 73.48469228349535),
    "intertemporal_choice": ("chosen_consumption_later", 88.0),
    "cost_curves": ("TC", 250.0),
    "perfect_competition": ("profit", 300.0),
    "competitive_shutdown": ("chosen_output", 0.0),
    "monopoly": ("monopoly_price", 60.0),
    "marginal_revenue": ("marginal_revenue", 20.0),
    "price_discrimination": ("profit", 1600.0),
    "oligopoly": ("firm_1_profit", 900.0),
    "oligopoly_collusion": ("collusive_firm_profit", 1012.5),
    "strategic_game": ("strategy_profiles", 4.0),
    "nash_equilibrium": ("nash_equilibrium_count", 2.0),
    "dominant_strategy": ("dominant_strategy_count", 2.0),
    "consumer_surplus": ("CS", 900.0),
    "producer_surplus": ("PS", 450.0),
    "total_surplus": ("TS", 1350.0),
    "welfare_surplus": ("efficient_quantity", 30.0),
    "tax_incidence": ("tax_wedge", 12.0),
    "tax_deadweight_loss": ("DWL", 100.0),
    "externality": ("overproduction", 5.0),
    "coase_bargaining": ("net_bargaining_gains", 242.0),
    "common_resource": ("overuse", 7.5),
    "public_good": ("efficient_public_good_quantity", 30.0),
    "international_trade": ("imports", 30.0),
    "tariff": ("tariff_revenue", 36.0),
    "choice_under_uncertainty": ("risk_premium", 4.6875),
    "social_insurance": ("consumption_gap", 20.0),
    "adverse_selection": ("pooling_premium", 180.0),
    "moral_hazard": ("loss_probability_increase", 0.1),
    "equity_efficiency": ("equity_gap_reduction", 30.0),
    "behavioral_economics": ("present_bias_value_gap", 28.8),
    "health_economics": ("insurance_induced_overuse", 65.0 / 6.0),
}


def ordered_union(*groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token for group in groups for token in group))


class EconomicsScenarioCoverageTests(unittest.TestCase):
    def test_registry_covers_every_and_only_model_spec(self) -> None:
        self.assertEqual(
            set(ECONOMICS_MODEL_SCENARIO_REGISTRY), set(ECONOMICS_MODEL_REGISTRY)
        )
        self.assertEqual(
            set(ECONOMICS_MODEL_SCENARIO_DEFINITIONS), set(ECONOMICS_MODEL_REGISTRY)
        )
        self.assertEqual(
            set(build_all_economics_model_scenarios()), set(ECONOMICS_MODEL_REGISTRY)
        )
        self.assertEqual(set(EXPECTED_SALIENT_RESULTS), set(ECONOMICS_MODEL_REGISTRY))
        self.assertIs(ECONOMICS_MODEL_SCENARIOS, ECONOMICS_MODEL_SCENARIO_REGISTRY)
        self.assertIs(ECONOMICS_SCENARIOS, ECONOMICS_MODEL_SCENARIO_REGISTRY)

        modes = [scenario.mode for scenario in ECONOMICS_MODEL_SCENARIOS.values()]
        self.assertEqual(len(modes), len(set(modes)))

    def test_every_scenario_has_complete_scene_and_animation_contract(self) -> None:
        for model_id, scenario in ECONOMICS_MODEL_SCENARIOS.items():
            with self.subTest(model_id=model_id):
                self.assertIsInstance(scenario, EconomicsModelScenario)
                self.assertEqual(scenario.model_id, model_id)
                self.assertEqual(scenario["model_id"], model_id)
                self.assertIs(scenario["numeric_setup"], scenario.setup)
                self.assertIs(scenario["calculation_fields"], scenario.calculation)
                self.assertIs(scenario["result_fields"], scenario.results)
                self.assertIs(
                    scenario["evidence_tokens"], scenario.visible_evidence_tokens
                )
                self.assertTrue(scenario.mode)
                self.assertTrue(scenario.setup)
                self.assertTrue(scenario.calculation)
                self.assertTrue(scenario.results)
                self.assertTrue(
                    all(isfinite(value) for value in scenario.setup.values())
                )
                self.assertTrue(
                    all(isfinite(value) for value in scenario.calculation.values())
                )
                self.assertTrue(
                    all(isfinite(value) for value in scenario.results.values())
                )

                self.assertTrue(scenario.axes)
                axis_ids = {axis.axis_id for axis in scenario.axes}
                self.assertEqual(len(axis_ids), len(scenario.axes))
                for axis in scenario.axes:
                    self.assertTrue(axis.horizontal_label)
                    self.assertTrue(axis.vertical_label)
                    self.assertLess(axis.horizontal_min, axis.horizontal_max)
                    self.assertLess(axis.vertical_min, axis.vertical_max)

                self.assertTrue(scenario.objects)
                object_ids = tuple(obj.object_id for obj in scenario.objects)
                self.assertEqual(len(object_ids), len(set(object_ids)))
                self.assertTrue(
                    all(obj.axis_id in axis_ids for obj in scenario.objects)
                )

                states = scenario.animation_states
                self.assertEqual(
                    tuple(state.phase for state in states),
                    ("setup", "change", "result"),
                )
                self.assertEqual(
                    tuple(state.progress for state in states), (0.0, 0.5, 1.0)
                )
                self.assertEqual(len({state.state_id for state in states}), 3)
                self.assertEqual(states[-1].visible_object_ids, object_ids)
                self.assertEqual(states[-1].result_fields, tuple(scenario.results))
                self.assertEqual(
                    states[-1].visible_evidence_tokens, scenario.visible_evidence_tokens
                )
                self.assertIs(states[0].values, scenario.setup)
                self.assertIs(states[1].values, scenario.calculation)
                self.assertIs(states[-1].values, scenario.results)
                self.assertEqual(
                    states[-1]["visible_tokens"], scenario.visible_evidence_tokens
                )
                self.assertIs(
                    scenario.animation_state_sequence, scenario.animation_states
                )
                self.assertIs(scenario.axis_specs, scenario.axes)
                self.assertIs(scenario.object_specs, scenario.objects)

                exported = scenario.as_dict()
                self.assertEqual(
                    set(exported["calculation"]), set(scenario.calculation)
                )
                self.assertRegex(
                    scenario.numeric_evidence_fingerprint, r"^[0-9a-f]{64}$"
                )
                self.assertEqual(
                    exported["numeric_evidence_fingerprint"],
                    economics_numeric_evidence_fingerprint(exported),
                )

    def test_required_tokens_are_preserved_exactly_and_become_visible(self) -> None:
        for model_id, spec in ECONOMICS_MODEL_REGISTRY.items():
            scenario = ECONOMICS_MODEL_SCENARIOS[model_id]
            with self.subTest(model_id=model_id):
                expected_visible = ordered_union(
                    spec.required_example_tokens,
                    spec.required_figure_tokens,
                )
                self.assertEqual(
                    scenario.required_example_tokens, spec.required_example_tokens
                )
                self.assertEqual(
                    scenario.required_figure_tokens, spec.required_figure_tokens
                )
                self.assertEqual(scenario.visible_evidence_tokens, expected_visible)
                self.assertEqual(
                    scenario.exact_visible_evidence_tokens, expected_visible
                )
                self.assertEqual(
                    scenario.animation_states[-1].visible_evidence_tokens,
                    expected_visible,
                )


class EconomicsScenarioArithmeticTests(unittest.TestCase):
    def test_every_model_has_an_independently_expected_numeric_result(self) -> None:
        for model_id, (result_field, expected) in EXPECTED_SALIENT_RESULTS.items():
            with self.subTest(model_id=model_id, result_field=result_field):
                actual = ECONOMICS_MODEL_SCENARIOS[model_id].results[result_field]
                self.assertAlmostEqual(actual, expected, places=9)

    def test_default_registry_is_a_fresh_recomputation_for_every_model(self) -> None:
        for model_id, default in ECONOMICS_MODEL_SCENARIOS.items():
            rebuilt = build_economics_model_scenario(model_id)
            with self.subTest(model_id=model_id):
                self.assertEqual(set(rebuilt.results), set(default.results))
                for result_field, expected in default.results.items():
                    self.assertAlmostEqual(
                        rebuilt.results[result_field], expected, places=12
                    )

    def test_setup_overrides_recompute_results_instead_of_reusing_defaults(
        self,
    ) -> None:
        equilibrium = build_economics_model_scenario(
            "market_equilibrium",
            {"demand_intercept": 150.0},
        )
        self.assertAlmostEqual(equilibrium.results["equilibrium_price"], 10.0)
        self.assertAlmostEqual(equilibrium.results["equilibrium_quantity"], 50.0)

        elasticity = build_economics_model_scenario(
            "own_price_elasticity",
            {"new_quantity": 70.0},
        )
        self.assertAlmostEqual(elasticity.results["own_price_elasticity"], -1.5)
        self.assertAlmostEqual(elasticity.results["elasticity_magnitude"], 1.5)

        costs = build_economics_model_scenario("cost_curves", {"output": 20.0})
        self.assertEqual(
            dict(costs.results),
            {
                "FC": 100.0,
                "VC": 500.0,
                "TC": 600.0,
                "AC": 30.0,
                "AVC": 25.0,
                "MC": 45.0,
            },
        )

        selection = build_economics_model_scenario(
            "adverse_selection", {"high_risk_share": 0.5}
        )
        self.assertAlmostEqual(selection.results["pooling_premium"], 200.0)

        hazard = build_economics_model_scenario("moral_hazard", {"coverage_rate": 0.5})
        self.assertAlmostEqual(hazard.results["expected_insurer_cost"], 100.0)
        self.assertAlmostEqual(hazard.results["expected_patient_loss_cost"], 100.0)

        health = build_economics_model_scenario(
            "health_economics", {"insurance_coverage_rate": 0.5}
        )
        self.assertAlmostEqual(health.results["patient_price"], 25.0)
        self.assertAlmostEqual(health.results["patient_demanded_quantity"], 23.75)

    def test_binding_controls_turn_off_when_moved_across_equilibrium(self) -> None:
        ceiling = build_economics_model_scenario(
            "price_ceiling_shortage",
            {"ceiling_price": 7.0},
        )
        floor = build_economics_model_scenario(
            "price_floor_surplus",
            {"floor_price": 5.0},
        )
        self.assertEqual(ceiling.results["binding_indicator"], 0.0)
        self.assertEqual(ceiling.results["shortage"], 0.0)
        self.assertEqual(floor.results["binding_indicator"], 0.0)
        self.assertEqual(floor.results["surplus"], 0.0)


class EconomicsScenarioDistinctionTests(unittest.TestCase):
    def test_elasticities_change_different_denominators_and_classifications(
        self,
    ) -> None:
        own = ECONOMICS_MODEL_SCENARIOS["own_price_elasticity"]
        income = ECONOMICS_MODEL_SCENARIOS["income_elasticity"]
        cross = ECONOMICS_MODEL_SCENARIOS["cross_price_elasticity"]

        self.assertIn("initial_price", own.setup)
        self.assertNotIn("initial_income", own.setup)
        self.assertNotIn("initial_price_y", own.setup)
        self.assertIn("initial_income", income.setup)
        self.assertIn("normal_good_indicator", income.results)
        self.assertIn("inferior_good_indicator", income.results)
        self.assertIn("initial_price_y", cross.setup)
        self.assertIn("initial_quantity_x", cross.setup)
        self.assertIn("substitutes_indicator", cross.results)
        self.assertIn("complements_indicator", cross.results)
        self.assertEqual(own.results["own_price_elasticity"], -1.0)
        self.assertEqual(income.results["income_elasticity"], 1.0)
        self.assertEqual(cross.results["cross_price_elasticity"], 0.5)

    def test_preferences_budget_mrs_choice_and_time_are_not_one_generic_budget_scene(
        self,
    ) -> None:
        model_ids = (
            "consumer_preferences",
            "utility_representation",
            "budget_constraint",
            "marginal_rate_of_substitution",
            "consumer_choice",
            "intertemporal_choice",
        )
        modes = {ECONOMICS_MODEL_SCENARIOS[model_id].mode for model_id in model_ids}
        self.assertEqual(len(modes), len(model_ids))
        self.assertIn(
            "preferred_bundle_index",
            ECONOMICS_MODEL_SCENARIOS["consumer_preferences"].results,
        )
        self.assertIn(
            "utility_a", ECONOMICS_MODEL_SCENARIOS["utility_representation"].results
        )
        self.assertIn(
            "affordable_indicator",
            ECONOMICS_MODEL_SCENARIOS["budget_constraint"].results,
        )
        self.assertIn(
            "MRS", ECONOMICS_MODEL_SCENARIOS["marginal_rate_of_substitution"].results
        )
        self.assertIn("chosen_x", ECONOMICS_MODEL_SCENARIOS["consumer_choice"].results)
        self.assertIn(
            "present_value_wealth",
            ECONOMICS_MODEL_SCENARIOS["intertemporal_choice"].results,
        )
        self.assertIn(
            "interest_rate", ECONOMICS_MODEL_SCENARIOS["intertemporal_choice"].setup
        )

    def test_cost_scenario_reconciles_all_cost_measures(self) -> None:
        costs = ECONOMICS_MODEL_SCENARIOS["cost_curves"]
        self.assertEqual(tuple(costs.results), ("FC", "VC", "TC", "AC", "AVC", "MC"))
        self.assertEqual(costs.results["TC"], costs.results["FC"] + costs.results["VC"])
        self.assertEqual(
            costs.results["AC"], costs.results["TC"] / costs.setup["output"]
        )
        self.assertEqual(
            costs.results["AVC"], costs.results["VC"] / costs.setup["output"]
        )
        for token in ("FC", "VC", "TC", "AC", "MC"):
            self.assertIn(token, costs.visible_evidence_tokens)

    def test_labor_and_capital_markets_keep_inputs_and_prices_separate(self) -> None:
        labor = ECONOMICS_MODEL_SCENARIOS["labor_input_market"]
        capital = ECONOMICS_MODEL_SCENARIOS["capital_input_market"]
        factors = ECONOMICS_MODEL_SCENARIOS["factor_input_markets"]
        market = ECONOMICS_MODEL_SCENARIOS["labor_market"]

        self.assertIn("wage", labor.setup)
        self.assertIn("labor_input", labor.results)
        self.assertNotIn("capital_input", labor.results)
        self.assertIn("rental_price", capital.setup)
        self.assertIn("capital_input", capital.results)
        self.assertNotIn("labor_input", capital.results)
        self.assertIn("labor_input", factors.results)
        self.assertIn("capital_input", factors.results)
        self.assertAlmostEqual(
            factors.results["produced_output"], factors.setup["target_output"]
        )
        self.assertAlmostEqual(
            factors.results["MRTS_labor_for_capital"],
            factors.results["factor_price_ratio"],
        )
        self.assertEqual(factors.mode, "joint_factor_cost_minimization")
        self.assertIn("employment", market.results)
        self.assertNotIn("marginal_revenue", market.setup)

    def test_competition_shutdown_monopoly_revenue_and_segmentation_remain_distinct(
        self,
    ) -> None:
        competition = ECONOMICS_MODEL_SCENARIOS["perfect_competition"]
        shutdown = ECONOMICS_MODEL_SCENARIOS["competitive_shutdown"]
        monopoly = ECONOMICS_MODEL_SCENARIOS["monopoly"]
        revenue = ECONOMICS_MODEL_SCENARIOS["marginal_revenue"]
        discrimination = ECONOMICS_MODEL_SCENARIOS["price_discrimination"]

        self.assertEqual(
            competition.results["price"], competition.results["marginal_revenue"]
        )
        self.assertEqual(shutdown.results["shutdown_indicator"], 1.0)
        self.assertEqual(
            shutdown.results["short_run_profit"], -shutdown.setup["fixed_cost"]
        )
        self.assertEqual(
            monopoly.results["marginal_revenue"], monopoly.setup["marginal_cost"]
        )
        self.assertGreater(
            monopoly.results["monopoly_price"], monopoly.results["marginal_revenue"]
        )
        self.assertEqual(
            revenue.results["total_revenue"],
            revenue.results["price"] * revenue.setup["quantity"],
        )
        self.assertNotEqual(
            discrimination.results["market_1_price"],
            discrimination.results["market_2_price"],
        )
        self.assertEqual(
            discrimination.results["common_marginal_revenue"],
            discrimination.setup["marginal_cost"],
        )

        collusion = ECONOMICS_MODEL_SCENARIOS["oligopoly_collusion"]
        self.assertLess(
            collusion.results["collusive_total_quantity"],
            collusion.results["cournot_total_quantity"],
        )
        self.assertGreater(
            collusion.results["collusive_price"], collusion.results["cournot_price"]
        )
        self.assertGreater(
            collusion.results["collusive_firm_profit"],
            collusion.results["cournot_firm_profit"],
        )

    def test_surplus_measures_have_separate_areas_and_accounting(self) -> None:
        consumer = ECONOMICS_MODEL_SCENARIOS["consumer_surplus"]
        producer = ECONOMICS_MODEL_SCENARIOS["producer_surplus"]
        total = ECONOMICS_MODEL_SCENARIOS["total_surplus"]
        welfare = ECONOMICS_MODEL_SCENARIOS["welfare_surplus"]

        self.assertEqual(consumer.results["CS"], 900.0)
        self.assertNotIn("PS", consumer.results)
        self.assertEqual(producer.results["PS"], 450.0)
        self.assertNotIn("CS", producer.results)
        self.assertEqual(total.results["TS"], total.results["CS"] + total.results["PS"])
        self.assertEqual(
            welfare.results["TS"], welfare.results["CS"] + welfare.results["PS"]
        )
        self.assertEqual(welfare.results["efficient_quantity"], 30.0)

    def test_trade_uncertainty_insurance_and_information_failures_stay_specific(
        self,
    ) -> None:
        trade = ECONOMICS_MODEL_SCENARIOS["international_trade"]
        uncertainty = ECONOMICS_MODEL_SCENARIOS["choice_under_uncertainty"]
        insurance = ECONOMICS_MODEL_SCENARIOS["social_insurance"]
        selection = ECONOMICS_MODEL_SCENARIOS["adverse_selection"]
        hazard = ECONOMICS_MODEL_SCENARIOS["moral_hazard"]

        self.assertEqual(
            trade.results["imports"],
            trade.results["domestic_demand"] - trade.results["domestic_supply"],
        )
        self.assertEqual(
            uncertainty.results["certainty_equivalent"],
            uncertainty.results["expected_utility"] ** 2,
        )
        self.assertIn("contribution", insurance.setup)
        self.assertIn("benefit", insurance.setup)
        self.assertIn("high_risk_probability", selection.setup)
        self.assertIn("pooling_premium", selection.results)
        self.assertNotIn("effort_change", selection.results)
        self.assertIn("covered_effort", hazard.setup)
        self.assertIn("effort_change", hazard.results)
        self.assertNotIn("pooling_premium", hazard.results)
        self.assertIn("private information", selection.visible_evidence_tokens)
        self.assertIn("unobserved action", hazard.visible_evidence_tokens)

    def test_equity_behavioral_and_health_results_encode_different_questions(
        self,
    ) -> None:
        equity = ECONOMICS_MODEL_SCENARIOS["equity_efficiency"]
        behavioral = ECONOMICS_MODEL_SCENARIOS["behavioral_economics"]
        health = ECONOMICS_MODEL_SCENARIOS["health_economics"]

        self.assertEqual(equity.results["efficiency_gain"], 0.0)
        self.assertEqual(equity.results["equity_gap_reduction"], 30.0)
        self.assertEqual(behavioral.results["benchmark_later_choice_indicator"], 1.0)
        self.assertEqual(behavioral.results["observed_now_choice_indicator"], 1.0)
        self.assertGreater(
            health.results["patient_demanded_quantity"],
            health.results["efficient_health_care_quantity"],
        )
        self.assertEqual(
            health.results["marginal_benefit_at_efficiency"],
            health.results["marginal_cost_at_efficiency"],
        )


class EconomicsScenarioImmutabilityTests(unittest.TestCase):
    def test_scenarios_and_nested_state_are_immutable(self) -> None:
        scenario = ECONOMICS_MODEL_SCENARIOS["market_equilibrium"]
        with self.assertRaises(FrozenInstanceError):
            scenario.mode = "changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            scenario.setup["demand_intercept"] = 1.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            scenario.results["equilibrium_price"] = 1.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            ECONOMICS_MODEL_SCENARIOS["changed"] = scenario  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            scenario.axes[0].horizontal_label = "changed"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            scenario.animation_states[0].phase = "changed"  # type: ignore[misc]

    def test_as_dict_is_a_defensive_serializable_copy(self) -> None:
        scenario = ECONOMICS_MODEL_SCENARIOS["tax_incidence"]
        exported = scenario.as_dict()
        self.assertEqual(exported["model_id"], "tax_incidence")
        exported_setup = exported["setup"]
        assert isinstance(exported_setup, dict)
        exported_setup["tax"] = 999.0
        self.assertEqual(scenario.setup["tax"], 12.0)

    def test_builder_rejects_unknown_or_non_numeric_setup(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported economics model_id"):
            build_economics_model_scenario("not_a_model")
        with self.assertRaises(TypeError):
            build_economics_model_scenario(None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "unknown setup fields"):
            build_economics_model_scenario("market_equilibrium", {"mystery": 1.0})
        with self.assertRaisesRegex(TypeError, "must be a real number"):
            build_economics_model_scenario(
                "market_equilibrium",
                {"demand_intercept": "high"},  # type: ignore[dict-item]
            )
        with self.assertRaisesRegex(ValueError, "Unsupported economics model_id"):
            get_economics_model_scenario("not_a_model")

    def test_get_and_rebuild_are_pure_and_leave_defaults_unchanged(self) -> None:
        default = get_economics_model_scenario("market_equilibrium")
        rebuilt = default.rebuild({"demand_intercept": 150.0})
        self.assertIs(default, ECONOMICS_MODEL_SCENARIOS["market_equilibrium"])
        self.assertIsNot(default, rebuilt)
        self.assertEqual(default.setup["demand_intercept"], 120.0)
        self.assertEqual(rebuilt.setup["demand_intercept"], 150.0)

    def test_recompute_ignores_stale_exported_results(self) -> None:
        original = get_economics_model_scenario("market_equilibrium")
        stale = original.as_dict()
        stale["result"] = {"equilibrium_price": -999.0}
        stale["results"] = {"equilibrium_price": -999.0}
        stale["calculation"] = {"equilibrium_price": -999.0}

        rebuilt = recompute_economics_model_scenario(stale)

        self.assertEqual(rebuilt, original)
        self.assertEqual(rebuilt.results["equilibrium_price"], 8.0)
        self.assertEqual(rebuilt.calculation["equilibrium_price"], 8.0)

    def test_numeric_fingerprint_is_deterministic_and_setup_sensitive(self) -> None:
        baseline = build_economics_model_scenario("market_equilibrium")
        rebuilt = build_economics_model_scenario("market_equilibrium")
        shifted = build_economics_model_scenario(
            "market_equilibrium", {"demand_intercept": 150.0}
        )

        self.assertEqual(
            baseline.numeric_evidence_fingerprint,
            rebuilt.numeric_evidence_fingerprint,
        )
        self.assertNotEqual(
            baseline.numeric_evidence_fingerprint,
            shifted.numeric_evidence_fingerprint,
        )
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", baseline.numeric_evidence_fingerprint))

    def test_new_sources_are_ascii_and_do_not_import_stem_course(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = (root / "tools/economics_model_scenarios.py", Path(__file__))
        for path in paths:
            with self.subTest(path=path.name):
                path.read_bytes().decode("ascii")

        module_source = paths[0].read_text(encoding="ascii")
        self.assertNotIn("import " + "stem_course", module_source)
        self.assertNotIn("from tools import " + "stem_course", module_source)


if __name__ == "__main__":
    unittest.main()

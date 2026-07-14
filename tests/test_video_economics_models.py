from __future__ import annotations

import unittest

from tools.economics_model_specs import (
    ECONOMICS_MODEL_REGISTRY,
    MIT_14_01_TITLE_MODEL_IDS,
)
from tools.video_economics_models import (
    ECONOMICS_MODEL_VIDEO_ROUTE_REGISTRY,
    ECONOMICS_VIDEO_ROUTES,
    ECONOMICS_VIDEO_ROUTE_REGISTRY,
    EconomicsVideoRoute,
    _build_route_registries,
    economics_formula_sources,
    economics_guide_sweep,
    GraphBox,
    build_cournot_motion_state,
    build_economics_video_payload,
    place_economics_graph_label,
    resolve_economics_video_route,
    stage_phone_readable_copy,
    validate_economics_video_payload,
)


class EconomicsVideoRouteTests(unittest.TestCase):
    def test_all_54_model_routes_serialize_canonical_numeric_contracts(self) -> None:
        self.assertEqual(len(ECONOMICS_MODEL_REGISTRY), 54)
        self.assertEqual(
            set(ECONOMICS_MODEL_VIDEO_ROUTE_REGISTRY),
            set(ECONOMICS_MODEL_REGISTRY),
        )
        for model_id in ECONOMICS_MODEL_REGISTRY:
            with self.subTest(model_id=model_id):
                payload = build_economics_video_payload(model_id)
                scenario = payload["model_scenario"]
                self.assertEqual(payload["route_key"], ECONOMICS_MODEL_VIDEO_ROUTE_REGISTRY[model_id].route_key)
                self.assertEqual(payload["numeric_evidence_fingerprint"], scenario["numeric_evidence_fingerprint"])
                self.assertEqual(payload["numeric_evidence"]["setup"], scenario["setup"])
                self.assertEqual(payload["numeric_evidence"]["calculation"], scenario["calculation"])
                self.assertEqual(payload["numeric_evidence"]["result"], scenario["result"])
                self.assertEqual(payload["required_tokens"], payload["visible_evidence_tokens"])
                self.assertEqual(
                    [state["phase"] for state in payload["animation_states"]],
                    ["setup", "change", "result"],
                )
                self.assertGreaterEqual(len(payload["transitions"]), 3)
                self.assertEqual(validate_economics_video_payload(payload), [])

    def test_all_26_mit_titles_expose_three_causal_transformations(self) -> None:
        self.assertEqual(len(MIT_14_01_TITLE_MODEL_IDS), 26)
        for title in MIT_14_01_TITLE_MODEL_IDS:
            with self.subTest(title=title):
                payload = build_economics_video_payload(title)
                self.assertGreaterEqual(len(payload["transitions"]), 4)
                self.assertEqual(validate_economics_video_payload(payload), [])

    def test_named_route_repairs_keep_cournot_and_tax_sequences_stable(self) -> None:
        for family in ("supply_demand", "budget_choice", "surplus", "equity_efficiency"):
            with self.subTest(family=family):
                self.assertGreaterEqual(
                    len(ECONOMICS_VIDEO_ROUTE_REGISTRY[family].steps), 3
                )
        self.assertEqual(
            [step[0] for step in ECONOMICS_VIDEO_ROUTE_REGISTRY["tax"].steps],
            ["insert_wedge", "contract_trade", "account_welfare"],
        )
        self.assertEqual(
            [step[0] for step in ECONOMICS_VIDEO_ROUTE_REGISTRY["cournot"].steps],
            ["trace_reactions", "locate_cournot_nash", "price_cournot_output"],
        )
        self.assertEqual(
            [step[0] for step in ECONOMICS_VIDEO_ROUTE_REGISTRY["cournot_collusion"].steps],
            ["mark_cournot_benchmark", "restrict_joint_output", "compare_price_profit"],
        )

    def test_payload_validator_rejects_numeric_metadata_corruption(self) -> None:
        payload = build_economics_video_payload("market_equilibrium")
        payload["numeric_evidence"]["result"]["equilibrium_price"] += 1.0
        self.assertIn(
            "numeric_evidence_fingerprint does not match numeric evidence",
            validate_economics_video_payload(payload),
        )

    def test_route_registry_rejects_duplicate_families_and_model_ids(self) -> None:
        route = ECONOMICS_VIDEO_ROUTES[0]
        with self.assertRaisesRegex(RuntimeError, "duplicate economics video route family"):
            _build_route_registries((*ECONOMICS_VIDEO_ROUTES, route))

        duplicate_model_route = EconomicsVideoRoute(
            route_key="economics:duplicate_model_probe",
            family="duplicate_model_probe",
            model_ids=route.model_ids,
            invariant="probe",
            verification=("probe",),
            object_roles=(("probe", "probe"),),
            steps=(("probe", "probe", "probe"),),
            changed_objects=(),
        )
        with self.assertRaisesRegex(RuntimeError, "appears in both"):
            _build_route_registries((*ECONOMICS_VIDEO_ROUTES, duplicate_model_route))

    def test_all_26_authoritative_titles_have_intentional_routes(self) -> None:
        expectations = {
            "Introduction and Supply & Demand": "supply_demand",
            "Preferences and Utility Functions": "budget_choice",
            "Budget Constraints and Constrained Choice": "budget_choice",
            "Demand Curves and Income/Substitution Effects": "budget_choice",
            "Production Theory": "production_isoquants",
            "Costs": "cost_curves",
            "Competition I": "perfect_competition",
            "Competition II": "competitive_shutdown",
            "Supply and Demand & Consumer/Producer Surplus": "surplus",
            "Welfare Economics": "surplus",
            "Monopoly I": "monopoly",
            "Monopoly II": "price_discrimination",
            "Oligopoly I": "cournot",
            "Oligopoly II": "cournot_collusion",
            "Input Markets I\N{EM DASH}Labor Market": "labor_market",
            "Input Markets II\N{EM DASH}Labor and Capital": "factor_cost_minimization",
            "Making Choices over Time": "intertemporal_choice",
            "Introduction to Trade": "international_trade",
            "International Trade: Welfare and Policy": "tariff",
            "Uncertainty": "expected_utility",
            "Social Insurance": "social_insurance",
            "Efficiency and Equity": "equity_efficiency",
            "Government Redistribution and Taxation": "tax",
            "Externalities": "externality_wedge",
            "Behavioral Economics": "present_bias",
            "Healthcare Economics": "healthcare_insurance",
        }

        self.assertEqual(len(expectations), 26)
        for title, family in expectations.items():
            with self.subTest(title=title):
                route = resolve_economics_video_route(title, fail_closed=True)
                self.assertEqual(route.family, family)
                self.assertEqual(validate_economics_video_payload(build_economics_video_payload(title)), [])

    def test_cournot_motion_state_links_reactions_nash_and_collusion(self) -> None:
        state = build_cournot_motion_state(100, 1, 10)

        self.assertEqual(state.reaction_intercept, 45)
        self.assertEqual(state.reaction_slope, -0.5)
        self.assertEqual(state.nash_firm_quantity, 30)
        self.assertEqual(state.nash_total_quantity, 60)
        self.assertEqual(state.nash_price, 40)
        self.assertEqual(state.collusive_firm_quantity, 22.5)
        self.assertEqual(state.collusive_total_quantity, 45)
        self.assertEqual(state.collusive_price, 55)
        self.assertLess(state.collusive_total_quantity, state.nash_total_quantity)
        self.assertGreater(state.collusive_price, state.nash_price)

    def test_tax_incidence_keeps_tex_and_uses_font_safe_fallback(self) -> None:
        sources = economics_formula_sources(r"P_b-P_s=t", "Pᵦ − Pₛ = t")

        self.assertEqual(sources.latex, r"P_b-P_s=t")
        self.assertEqual(sources.fallback, "P(b) - P(s) = t")

    def test_economics_fallback_removes_missing_glyph_risk_generically(self) -> None:
        cases = (
            (r"DWL=\frac{1}{2}t(Q_0-Q_t)", "DWL = ½t(Q₀ − Qₜ)"),
            (r"P\leq \bar{P}", "P ≤ P̄"),
            (r"\pi_i(q_i,q_{-i})", "πᵢ(qᵢ, q₋ᵢ)"),
        )
        for latex, plain in cases:
            with self.subTest(latex=latex):
                sources = economics_formula_sources(latex, plain)
                self.assertTrue(sources.fallback.isascii())
                self.assertNotIn("_", sources.fallback)
                self.assertNotIn("\\", sources.fallback)
                self.assertNotIn("□", sources.fallback)
                self.assertTrue(sources.fallback.strip())
        self.assertIn("1/2", economics_formula_sources(*cases[0]).fallback)

    def test_old_budget_label_clears_bundle_marker_and_budget_line(self) -> None:
        plot = GraphBox(0.0, 7.0, 0.0, 9.0)
        initial_bundle_marker = GraphBox(3.68, 4.32, 4.18, 4.82)
        old_budget_segment = GraphBox(2.7, 5.3, 3.88, 4.12)

        placement = place_economics_graph_label(
            (4.0, 4.0),
            (1.6, 0.5),
            plot,
            (initial_bundle_marker, old_budget_segment),
        )

        self.assertFalse(placement.bounds.overlaps(initial_bundle_marker.expanded(0.12)))
        self.assertFalse(placement.bounds.overlaps(old_budget_segment.expanded(0.12)))
        self.assertIsNotNone(placement.leader)

    def test_price_control_label_clears_control_line_and_market_curves(self) -> None:
        plot = GraphBox(0.0, 24.0, 0.0, 18.0)
        control_line = GraphBox(0.0, 24.0, 6.94, 7.06)
        demand_near_anchor = GraphBox(10.1, 12.0, 7.35, 8.05)
        supply_near_anchor = GraphBox(11.65, 13.1, 7.12, 7.82)

        placement = place_economics_graph_label(
            (11.2, 7.0),
            (2.5, 0.55),
            plot,
            (control_line, demand_near_anchor, supply_near_anchor),
        )

        for obstacle in (control_line, demand_near_anchor, supply_near_anchor):
            self.assertFalse(placement.bounds.overlaps(obstacle.expanded(0.12)))
        self.assertGreaterEqual(placement.center[1] + 0.275, control_line.top + 0.12)

    def test_graph_label_placement_is_geometry_driven(self) -> None:
        source_anchor = (3.0, 2.0)
        placement = place_economics_graph_label(
            source_anchor,
            (1.0, 0.4),
            GraphBox(0.0, 6.0, 0.0, 4.0),
            (),
        )
        self.assertEqual(placement.center, (3.0, 2.55))

    def test_old_budget_label_clears_complete_moving_guide_sweep(self) -> None:
        cyan_guide_sweep = economics_guide_sweep((
            GraphBox(1.95, 2.05, 0.0, 9.0),
            GraphBox(3.15, 3.25, 0.0, 9.0),
            GraphBox(4.35, 4.45, 0.0, 9.0),
        ))

        placement = place_economics_graph_label(
            (3.2, 5.1),
            (1.0, 0.5),
            GraphBox(0.0, 7.0, 0.0, 9.0),
            (cyan_guide_sweep,),
        )

        self.assertEqual(cyan_guide_sweep.bounds, GraphBox(1.95, 4.45, 0.0, 9.0))
        self.assertFalse(placement.bounds.overlaps(cyan_guide_sweep.bounds.expanded(0.12)))
        self.assertGreater(placement.center[0], cyan_guide_sweep.bounds.right)

    def test_long_sentence_must_be_concised_before_phone_staging(self) -> None:
        with self.assertRaisesRegex(ValueError, "concise it before rendering"):
            stage_phone_readable_copy(
                "The price change first causes substitution toward x, then the income effect moves the final bundle.",
                min_font_size=32,
                max_chars_per_line=28,
                max_lines=2,
            )

    def test_high_risk_topics_have_dedicated_routes(self) -> None:
        expected = {
            "Externalities": "externality_wedge",
            "Production Theory": "production_isoquants",
            "Costs and cost curves": "cost_curves",
            "Perfect competition": "perfect_competition",
            "Monopoly": "monopoly",
            "Public goods": "public_goods_vertical_sum",
            "International trade": "international_trade",
            "Tariff": "tariff",
            "Labor market": "labor_market",
            "Adverse selection": "adverse_selection",
            "Moral hazard": "moral_hazard",
            "Healthcare insurance": "healthcare_insurance",
        }
        for title, family in expected.items():
            with self.subTest(title=title):
                route = resolve_economics_video_route(title, fail_closed=True)
                self.assertEqual(route.family, family)
                self.assertNotEqual(route.route_key, "economics:econ_curve")

    def test_existing_route_families_remain_resolvable(self) -> None:
        expected = {
            "Supply and demand equilibrium": "supply_demand",
            "Consumer choice": "budget_choice",
            "Own-price elasticity": "elasticity",
            "Tax incidence": "tax",
            "Nash equilibrium": "game",
        }
        for title, family in expected.items():
            with self.subTest(title=title):
                self.assertEqual(resolve_economics_video_route(title).family, family)

    def test_payloads_have_exact_complete_continuous_snapshots(self) -> None:
        for family, route in ECONOMICS_VIDEO_ROUTE_REGISTRY.items():
            with self.subTest(family=family):
                payload = build_economics_video_payload(next(iter(route.model_ids)))
                self.assertEqual(validate_economics_video_payload(payload), [])
                ids = set(payload["persistent_object_ids"])
                self.assertTrue(ids)
                self.assertTrue(all(row["persistent"] for row in payload["objects"]))
                for index, transition in enumerate(payload["transitions"]):
                    self.assertEqual(set(transition["before"]), ids)
                    self.assertEqual(set(transition["after"]), ids)
                    self.assertEqual(set(transition["persistent_object_ids"]), ids)
                    if index:
                        self.assertEqual(payload["transitions"][index - 1]["after"], transition["before"])

    def test_adjacent_topics_are_not_interchangeable(self) -> None:
        pairs = (
            ("Externalities", "Costs and cost curves"),
            ("Production Theory", "Costs and cost curves"),
            ("Perfect competition", "Monopoly"),
            ("Monopoly", "Public goods"),
            ("Supply and demand equilibrium", "Perfect competition"),
        )
        for left_title, right_title in pairs:
            with self.subTest(left=left_title, right=right_title):
                left = build_economics_video_payload(left_title)
                right = build_economics_video_payload(right_title)
                self.assertNotEqual(left["route_key"], right["route_key"])
                self.assertNotEqual(left["persistent_object_ids"], right["persistent_object_ids"])
                self.assertNotEqual(left["invariant"], right["invariant"])
                self.assertNotEqual(left["verification"], right["verification"])
                self.assertNotEqual(
                    [step["kind"] for step in left["transitions"]],
                    [step["kind"] for step in right["transitions"]],
                )

    def test_signature_preserves_economic_order_of_operations(self) -> None:
        monopoly = build_economics_video_payload("Monopoly")
        self.assertEqual(
            [step["kind"] for step in monopoly["transitions"]],
            ["establish_economic_objects", "choose_monopoly_quantity", "project_monopoly_price", "mark_deadweight_loss"],
        )
        public_good = build_economics_video_payload("Public goods")
        self.assertEqual(public_good["transitions"][2]["kind"], "sum_willingness_to_pay")
        self.assertIn("vertical", public_good["transitions"][2]["claim"].casefold())

    def test_representative_routes_validate_identities_and_changed_objects(self) -> None:
        model_ids = (
            "international_trade", "tariff", "labor_market", "adverse_selection",
            "moral_hazard", "health_economics",
        )
        route_keys = set()
        for model_id in model_ids:
            with self.subTest(model_id=model_id):
                payload = build_economics_video_payload(model_id)
                self.assertEqual(validate_economics_video_payload(payload), [])
                route_keys.add(payload["route_key"])
                changed = [
                    row["changed_object_id"].rsplit(":", 1)[-1]
                    for row in payload["transitions"][1:]
                ]
                self.assertEqual(changed, payload["changed_objects"])
        self.assertEqual(len(route_keys), len(model_ids))

    def test_policy_welfare_and_information_fail_closed_to_distinct_routes(self) -> None:
        groups = {
            "price_ceiling": ("price_ceiling_shortage",),
            "price_floor": ("price_floor_surplus",),
            "price_controls_comparison": ("price_controls",),
            "surplus": ("consumer_surplus", "producer_surplus", "total_surplus", "welfare_surplus"),
            "equity_efficiency": ("equity_efficiency",),
            "externality_wedge": ("externality",),
            "coase_bargaining": ("coase_bargaining",),
            "common_resource": ("common_resource",),
        }
        route_keys = set()
        for family, model_ids in groups.items():
            for model_id in model_ids:
                with self.subTest(model_id=model_id):
                    payload = build_economics_video_payload(model_id)
                    self.assertEqual(payload["family"], family)
                    self.assertEqual(validate_economics_video_payload(payload), [])
                    route_keys.add(payload["route_key"])
        self.assertEqual(len(route_keys), len(groups))

    def test_policy_welfare_and_externality_identities_reject_corruption(self) -> None:
        cases = (
            ("price_ceiling_shortage", "shortage"),
            ("price_floor_surplus", "surplus"),
            ("price_controls", "ceiling_shortage"),
            ("consumer_surplus", "CS"),
            ("producer_surplus", "PS"),
            ("total_surplus", "TS"),
            ("welfare_surplus", "TS"),
            ("equity_efficiency", "efficiency_gain"),
            ("externality", "overproduction"),
            ("coase_bargaining", "net_bargaining_gains"),
            ("common_resource", "overuse"),
        )
        for model_id, field in cases:
            with self.subTest(model_id=model_id):
                payload = build_economics_video_payload(model_id)
                payload["result_fields"][field] += 1.0
                self.assertTrue(validate_economics_video_payload(payload))

    def test_corrupt_representative_identities_fail_closed(self) -> None:
        cases = (
            ("international_trade", "imports"),
            ("tariff", "tariff_revenue"),
            ("labor_market", "employment"),
            ("adverse_selection", "pooling_premium"),
            ("moral_hazard", "effort_change"),
            ("health_economics", "patient_price"),
            ("factor_input_markets", "MRTS_labor_for_capital"),
            ("intertemporal_choice", "present_value_wealth"),
            ("competitive_shutdown", "shutdown_indicator"),
            ("price_discrimination", "common_marginal_revenue"),
            ("oligopoly_collusion", "output_restriction"),
            ("choice_under_uncertainty", "risk_premium"),
            ("social_insurance", "consumption_gap"),
            ("behavioral_economics", "behavioral_later_value"),
        )
        for model_id, field in cases:
            with self.subTest(model_id=model_id):
                payload = build_economics_video_payload(model_id)
                payload["result_fields"][field] += 1.0
                self.assertTrue(validate_economics_video_payload(payload))

    def test_unknown_route_fails_closed_on_request(self) -> None:
        self.assertIsNone(resolve_economics_video_route("macroeconomic growth accounting"))
        with self.assertRaisesRegex(ValueError, "Unsupported economics video route"):
            resolve_economics_video_route("macroeconomic growth accounting", fail_closed=True)


if __name__ == "__main__":
    unittest.main()

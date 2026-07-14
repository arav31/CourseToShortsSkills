from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from fractions import Fraction
import math
from numbers import Real
from pathlib import Path
import re
import unittest

from tools.economics_model_scenarios import ECONOMICS_MODEL_SCENARIOS
from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY
from tools.model_scenario_figures import (
    ECONOMICS_VISUAL_KINDS,
    MODEL_SCENARIO_VISUAL_KINDS,
    PHYSICS_VISUAL_KINDS,
    _format_display_number,
    economics_model_scenario_figure_body,
    figure_token_is_represented,
    latex_escape_label,
    model_scenario_figure_body,
    physics_model_scenario_figure_body,
    render_model_scenario_figure,
)
from tools.physics_model_scenarios import PHYSICS_MODEL_SCENARIOS
from tools.physics_model_specs import PHYSICS_MODEL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
LEARNER_LEGEND_MARKER = r"\node[draw,fill=white,anchor=north west"
AXES_MARKER = r"\draw[->,thick] (0,0) -- (5.9,0) node[right]"
LEARNER_VISIBLE_BANS = (
    "Figure semantics",
    "Scenario evidence",
    "model_id",
    "renderer",
    "provenance",
)


def cases() -> list[tuple[str, str, Mapping[str, object]]]:
    rows: list[tuple[str, str, Mapping[str, object]]] = []
    for model_id, spec in PHYSICS_MODEL_REGISTRY.items():
        rows.append((model_id, spec.visual_kind, PHYSICS_MODEL_SCENARIOS[model_id]))
    for model_id, spec in ECONOMICS_MODEL_REGISTRY.items():
        rows.append((model_id, spec.visual_kind, ECONOMICS_MODEL_SCENARIOS[model_id]))
    return rows


def core_body(body: str) -> str:
    return body.split(LEARNER_LEGEND_MARKER, 1)[0].strip()


def assert_balanced(test: unittest.TestCase, body: str, model_id: str) -> None:
    pairs = {"}": "{", "]": "[", ")": "("}
    stack: list[tuple[str, int]] = []
    for index, character in enumerate(body):
        if character in "{[(":
            stack.append((character, index))
        elif character in "}])":
            test.assertTrue(stack, f"{model_id}: unexpected {character} at {index}")
            opener, opener_index = stack.pop()
            test.assertEqual(
                opener,
                pairs[character],
                f"{model_id}: {opener} at {opener_index} closes with {character}",
            )
    test.assertEqual(stack, [], f"{model_id}: unclosed delimiters {stack[-5:]}")


def format_source_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Real):
        number = float(value)
        if number == 0.0:
            number = 0.0
        return format(number, ".7g")
    if isinstance(value, Mapping):
        return "{" + ", ".join(
            f"{key}: {format_source_value(item)}" for key, item in value.items()
        ) + "}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "(" + ", ".join(format_source_value(item) for item in value) + ")"
    return str(value)


class ModelScenarioFigureCoverageTests(unittest.TestCase):
    def test_every_registered_scenario_renders_from_a_plain_dict(self) -> None:
        rows = cases()
        self.assertEqual(
            len(rows), len(PHYSICS_MODEL_REGISTRY) + len(ECONOMICS_MODEL_REGISTRY)
        )
        self.assertEqual(
            MODEL_SCENARIO_VISUAL_KINDS,
            PHYSICS_VISUAL_KINDS | ECONOMICS_VISUAL_KINDS,
        )

        for model_id, visual_kind, scenario in rows:
            exported = scenario.as_dict()  # type: ignore[attr-defined]
            with self.subTest(model_id=model_id, visual_kind=visual_kind):
                first = render_model_scenario_figure(exported, visual_kind)
                second = render_model_scenario_figure(exported, visual_kind)
                self.assertEqual(first, second)
                body, evidence = first
                self.assertTrue(body.strip())
                self.assertIn(r"\draw", body)
                self.assertEqual(body.count(LEARNER_LEGEND_MARKER), 1)
                expected_heading = (
                    r"\textbf{Worked values}"
                    if visual_kind in PHYSICS_VISUAL_KINDS
                    else r"\textbf{Model quantities}"
                )
                self.assertIn(expected_heading, body)
                self.assertNotIn(r"\begin{tikzpicture}", body)
                self.assertIsNone(re.search(r"\\n(?=\\)", body))
                self.assertEqual(evidence, list(scenario.visible_evidence_tokens))  # type: ignore[attr-defined]
                self.assertIsInstance(evidence, list)
                assert_balanced(self, body, model_id)

    def test_required_figure_tokens_are_drawing_or_metadata_evidence(self) -> None:
        for model_id, visual_kind, scenario in cases():
            body, evidence = model_scenario_figure_body(scenario, visual_kind)
            with self.subTest(model_id=model_id):
                for token in scenario.required_figure_tokens:  # type: ignore[attr-defined]
                    self.assertTrue(
                        figure_token_is_represented(body, token) or token in evidence,
                        f"{model_id}: {token!r} absent from drawing and metadata",
                    )
                self.assertEqual(evidence, list(scenario.visible_evidence_tokens))  # type: ignore[attr-defined]

    def test_shared_axes_never_render_generic_fallback_labels(self) -> None:
        axes_models: list[str] = []
        for model_id, visual_kind, scenario in cases():
            body, _evidence = render_model_scenario_figure(scenario, visual_kind)
            if AXES_MARKER not in body:
                continue
            axes_models.append(model_id)
            with self.subTest(model_id=model_id):
                self.assertNotIn("{horizontal}", body)
                self.assertNotIn("{vertical}", body)
        self.assertGreaterEqual(len(axes_models), 11)

    def test_rendering_is_deterministic_and_does_not_mutate_exported_input(self) -> None:
        scenario = ECONOMICS_MODEL_SCENARIOS["market_equilibrium"].as_dict()
        before = repr(scenario)
        first = render_model_scenario_figure(scenario, "econ_supply_demand")
        second = render_model_scenario_figure(scenario, "econ_supply_demand")
        self.assertEqual(first, second)
        self.assertEqual(repr(scenario), before)


class ModelScenarioFigureDataTests(unittest.TestCase):
    def test_worked_value_display_formatter_has_a_compact_precision_budget(self) -> None:
        self.assertEqual(_format_display_number(42), "42")
        self.assertEqual(_format_display_number(42.0), "42")
        self.assertEqual(_format_display_number(10**400), "1" + "0" * 400)
        self.assertEqual(_format_display_number(Fraction(1, 3)), "1/3")
        self.assertEqual(_format_display_number(0.123456789), "0.1235")
        self.assertEqual(_format_display_number(12.3456789, unit="m/s"), "12.35 m/s")

    def test_worked_value_rounding_does_not_change_exact_scenario_state(self) -> None:
        scenario = PHYSICS_MODEL_SCENARIOS["kinematics_1d"].as_dict()
        scenario["setup"]["initial_position"] = 123456789
        scenario["setup"]["initial_velocity"] = Fraction(1, 3)
        scenario["results"]["final_position"] = 0.123456789
        scenario["results"]["final_velocity"] = 9876.54321
        before = repr(scenario)

        body, _ = render_model_scenario_figure(scenario, "physics_kinematics")

        self.assertIn(r"$x_0$ = $123456789$", body)
        self.assertIn(r"$v_0$ = $1/3$", body)
        self.assertIn(r"Final position = $0.1235$", body)
        self.assertIn(r"Final velocity = $9877$", body)
        self.assertNotIn("0.123456789", body)
        self.assertNotIn("9876.54321", body)
        self.assertEqual(repr(scenario), before)

    def test_learner_legends_are_compact_and_omit_boolean_dumps(self) -> None:
        for model_id, visual_kind, scenario in cases():
            body, _evidence = render_model_scenario_figure(scenario, visual_kind)
            legend = body[body.index(LEARNER_LEGEND_MARKER) :]
            with self.subTest(model_id=model_id):
                self.assertGreaterEqual(legend.count(" = "), 1)
                self.assertLessEqual(legend.count(" = "), 4)
                self.assertNotIn(r"\textbf{Setup}", legend)
                self.assertNotIn(r"\textbf{Results}", legend)
                self.assertNotRegex(legend.casefold(), r"\b(?:true|false)\b")

    def test_rendered_tikz_omits_internal_terms_and_raw_field_names(self) -> None:
        for model_id, visual_kind, scenario in cases():
            body, _evidence = render_model_scenario_figure(scenario, visual_kind)
            setup = scenario.setup  # type: ignore[attr-defined]
            results = getattr(scenario, "results", getattr(scenario, "result", None))
            assert isinstance(results, Mapping)
            with self.subTest(model_id=model_id):
                for banned in LEARNER_VISIBLE_BANS:
                    self.assertNotIn(banned.casefold(), body.casefold())
                self.assertNotIn(r"\texttt", body)
                self.assertNotIn(r"\_", body)
                for key in (*setup, *results):
                    if "_" not in key:
                        continue
                    self.assertNotIn(key, body)
                    self.assertNotIn(latex_escape_label(key), body)

    def test_override_values_replace_default_numeric_labels(self) -> None:
        from tools.economics_model_scenarios import build_economics_model_scenario
        from tools.physics_model_scenarios import build_physics_model_scenario

        physics = build_physics_model_scenario(
            "kinematics_1d",
            {
                "initial_position": 11.0,
                "initial_velocity": 7.0,
                "acceleration": 3.0,
                "elapsed_time": 2.0,
            },
        )
        physics_body, _ = render_model_scenario_figure(
            physics.as_dict(), "physics_kinematics"
        )
        self.assertIn(r"$x_0$ = $11$", physics_body)
        self.assertIn(r"$v_0$ = $7$", physics_body)
        self.assertIn(r"Final position = $31$", physics_body)

        economics = build_economics_model_scenario(
            "market_equilibrium", {"demand_intercept": 150.0}
        )
        economics_body, _ = render_model_scenario_figure(
            economics.as_dict(), "econ_supply_demand"
        )
        self.assertIn(r"Demand intercept = $150$", economics_body)
        self.assertIn(r"$P^*$ = $10$", economics_body)
        self.assertIn(r"$Q^*$ = $50$", economics_body)

    def test_game_matrix_payoffs_are_read_from_scenario_setup(self) -> None:
        scenario = ECONOMICS_MODEL_SCENARIOS["strategic_game"]
        body, _ = render_model_scenario_figure(scenario, "game_payoff")
        for row_key, column_key in (
            ("row_aa", "column_aa"),
            ("row_ab", "column_ab"),
            ("row_ba", "column_ba"),
            ("row_bb", "column_bb"),
        ):
            payoff = (
                f"({format_source_value(scenario.setup[row_key])}, "
                f"{format_source_value(scenario.setup[column_key])})"
            )
            self.assertIn(payoff, body)


class ModelScenarioFigureCompositionTests(unittest.TestCase):
    def render_core(self, model_id: str) -> str:
        if model_id in PHYSICS_MODEL_REGISTRY:
            scenario = PHYSICS_MODEL_SCENARIOS[model_id]
            visual_kind = PHYSICS_MODEL_REGISTRY[model_id].visual_kind
        else:
            scenario = ECONOMICS_MODEL_SCENARIOS[model_id]
            visual_kind = ECONOMICS_MODEL_REGISTRY[model_id].visual_kind
        return core_body(render_model_scenario_figure(scenario, visual_kind)[0])

    def test_representative_families_use_domain_specific_compositions(self) -> None:
        expectations = {
            "force_balance": "system boundary",
            "projectile_motion": "parabolic trajectory",
            "unit_vector": "component arrows",
            "energy_conservation": "kinetic energy meter",
            "elastic_collision": "before state",
            "potential_energy_diagram": "classically allowed",
            "radial_acceleration": "inward acceleration arrow",
            "torque": "torque arc",
            "waves": "wave profile",
            "market_equilibrium": "demand",
            "budget_constraint": "affordable region",
            "own_price_elasticity": "own price response",
            "tax_deadweight_loss": "DWL",
            "strategic_game": "column player",
            "marginal_revenue": "marginal revenue",
        }
        for model_id, marker in expectations.items():
            with self.subTest(model_id=model_id):
                self.assertIn(marker, self.render_core(model_id))

    def test_requested_topics_have_specific_readable_core_labels(self) -> None:
        expectations = {
            "continuous_mass_transfer": (
                "control volume boundary",
                r"$\dot m",
                r"\mathbf{v}_{\mathrm{out}}$",
            ),
            "potential_energy": (r"$U(x)$", r"$F=-\nabla U$"),
            "rigid_body_motion": (
                "reference point $O$",
                r"$\boldsymbol{\omega}$",
                r"$\mathbf{v}_P$",
            ),
            "market_equilibrium": ("demand", "supply", r"$(Q^*,P^*)$"),
            "production_function": (r"$q=f(L,K;A)$", r"$MP_L$"),
            "monopoly": (r"$MR$", r"$MC$", r"$q_m$", r"$P_m$"),
            "public_good": (r"$SMB$", r"$MC$", r"$G^*$"),
            "nash_equilibrium": ("Nash equilibrium", "best responses"),
            "tax_incidence": ("tax wedge", r"$P_b$", r"$P_s$"),
            "international_trade": ("domestic demand", r"$P_w$", "trade volume"),
        }
        for model_id, labels in expectations.items():
            core = self.render_core(model_id)
            with self.subTest(model_id=model_id):
                for label in labels:
                    self.assertIn(label, core)
                self.assertNotIn(r"\_", core)
                for banned in LEARNER_VISIBLE_BANS:
                    self.assertNotIn(banned.casefold(), core.casefold())

    def test_production_uses_canonical_lowercase_notation(self) -> None:
        scenario = ECONOMICS_MODEL_SCENARIOS["production_function"]
        body, _evidence = render_model_scenario_figure(scenario, "econ_curve")
        core = core_body(body)

        self.assertIn(r"$q=f(L,K;A)$", core)
        self.assertIn(
            r"node[anchor=south east,font=\scriptsize] at (3.28,2.62) {$q$}",
            core,
        )
        self.assertIn(r"$MP_L$", core)
        self.assertIn(r"$q$ = $24$", body)
        self.assertNotIn(r"$Q=F(L,K)$", body)
        self.assertNotIn(r"node[anchor=south east,font=\scriptsize] at (3.28,2.62) {$Q$}", body)
        self.assertNotIn(r"$Q$ =", body)

    def test_model_specific_axis_labels(self) -> None:
        expectations = {
            "kinematics_2d": ("{x}", "{y}"),
            "projectile_motion": ("{x}", "{y}"),
            "impulse_momentum": ("{time}", "{force}"),
            "potential_energy": ("{position x}", r"{potential energy $U(x)$}"),
            "potential_energy_diagram": (
                "{position x}",
                r"{potential energy $U(x)$}",
            ),
            "point_particle_angular_momentum": ("{x}", "{y}"),
            "angular_impulse": ("{time}", "{torque}"),
            "relative_velocity": (
                r"{velocity component $v_x$}",
                r"{velocity component $v_y$}",
            ),
            "ordinary_differential_equation": ("{time}", "{state}"),
            "unit_vector": ("{x component}", "{y component}"),
            "vectors": ("{x component}", "{y component}"),
            "production_function": (
                r"{labor $L$ (capital $K$ fixed)}",
                r"{output $q$}",
            ),
        }
        for model_id, (horizontal, vertical) in expectations.items():
            core = self.render_core(model_id)
            with self.subTest(model_id=model_id):
                self.assertIn(f"node[right] {horizontal};", core)
                self.assertIn(f"node[above] {vertical};", core)

    def test_high_risk_sibling_models_have_different_core_bodies(self) -> None:
        sibling_groups = (
            ("kinematics_1d", "kinematics_2d", "projectile_motion"),
            ("linear_drag", "quadratic_drag", "drag_force"),
            ("elastic_collision", "inelastic_collision", "perfectly_inelastic_collision"),
            ("circular_position", "uniform_circular_motion", "radial_acceleration", "circular_dynamics"),
            ("point_particle_angular_momentum", "rigid_body_angular_momentum", "angular_momentum"),
            ("rolling_dynamics", "rolling_kinetic_energy", "rolling_angular_momentum"),
            ("continuous_mass_transfer", "rocket_equation"),
            ("price_ceiling_shortage", "price_floor_surplus", "price_controls"),
            ("own_price_elasticity", "income_elasticity", "cross_price_elasticity"),
            ("consumer_preferences", "budget_constraint", "marginal_rate_of_substitution", "consumer_choice"),
            ("perfect_competition", "competitive_shutdown", "monopoly", "marginal_revenue", "price_discrimination"),
            ("strategic_game", "nash_equilibrium", "dominant_strategy", "oligopoly"),
            ("consumer_surplus", "producer_surplus", "total_surplus", "welfare_surplus"),
            ("adverse_selection", "moral_hazard"),
        )
        for group in sibling_groups:
            cores = [self.render_core(model_id) for model_id in group]
            with self.subTest(group=group):
                self.assertEqual(len(set(cores)), len(group))

    def test_worked_values_panel_has_a_dedicated_right_hand_lane(self) -> None:
        for model_id, visual_kind, scenario in cases():
            body, _ = render_model_scenario_figure(scenario, visual_kind)
            with self.subTest(model_id=model_id):
                self.assertIn("text width=3.75cm", body)
                self.assertIn("at (6.35,3.55)", body)

    def test_crowded_point_labels_use_explicit_anchors_or_leaders(self) -> None:
        circular = self.render_core("circular_position")
        self.assertIn(r"\draw[thin] (cm.north) --", circular)
        self.assertNotIn(r"\node[above right] at (cm)", circular)

        rigid = self.render_core("rigid_body_motion")
        self.assertIn(r"\draw[thin] (4.0,2.25) --", rigid)
        self.assertNotIn("circle (2pt) node[above] {material point", rigid)

    def test_economics_labels_stay_out_of_the_values_panel_lane(self) -> None:
        risky_labels = {
            "budget_constraint": ("budget line", "indifference curve"),
            "production_function": (r"$q=f(L,K;A)$", r"$MP_L$"),
            "cost_curves": ("{VC}", "{TC}", "{AC}", "{MC}"),
            "oligopoly": ("firm 1 best response", "firm 2 best response"),
            "international_trade": ("domestic demand", "domestic supply"),
            "externality": ("private cost", "social cost"),
            "health_economics": ("private cost", "social cost"),
        }
        for model_id, labels in risky_labels.items():
            core = self.render_core(model_id)
            with self.subTest(model_id=model_id):
                for label in labels:
                    line = next(line for line in core.splitlines() if label in line)
                    self.assertTrue("node[pos=" in line or r"\node[" in line)
                    self.assertNotIn("node[right]", line)

    def test_compact_economics_annotations_have_separate_anchors(self) -> None:
        competition = self.render_core("perfect_competition")
        self.assertIn(r"node[anchor=north,font=\scriptsize] at (3.55,-0.08) {q*}", competition)
        self.assertIn(r"node[anchor=east,font=\scriptsize] at (3.38,1.55) {profit or loss}", competition)

        oligopoly = self.render_core("oligopoly")
        self.assertIn(r"\draw[thin,green!50!black] (3.02,1.98) --", oligopoly)
        self.assertNotIn("circle (2.5pt) node[above right] {mutual best response}", oligopoly)

        insurance = self.render_core("social_insurance")
        self.assertIn(r"at (4.85,0.68) {consumption gap}", insurance)
        self.assertIn(r"(5.25,1.4) -- (4.85,0.72)", insurance)
        self.assertNotIn("node[midway,right] {consumption}", insurance)

    def test_producer_surplus_geometry_is_scaled_and_painted_before_strokes(self) -> None:
        from tools.economics_model_scenarios import build_economics_model_scenario

        baseline = self.render_core("producer_surplus")
        shifted_scenario = build_economics_model_scenario(
            "producer_surplus",
            {
                "supply_intercept_price": 25.0,
                "market_price": 70.0,
                "quantity": 20.0,
            },
        )
        shifted = core_body(
            render_model_scenario_figure(
                shifted_scenario, "econ_supply_demand"
            )[0]
        )

        self.assertNotEqual(baseline, shifted)
        self.assertIn(r"\fill[orange!18]", shifted)
        self.assertLess(
            shifted.index(r"\fill[orange!18]"),
            shifted.index(r"\draw[very thick,blue!70!black]"),
        )
        self.assertIn(r"\draw[dashed,thin]", shifted)
        self.assertIn(r"{$Q^*$}", shifted)
        self.assertIn(r"{$P^*$}", shifted)
        self.assertIn(r"{$ (Q^*,P^*) $}", shifted)
        self.assertIn("{producer surplus}", shifted)

        baseline_start = re.search(
            r"\\draw\[very thick,blue!70!black\] \(([^)]+)\)", baseline
        )
        shifted_start = re.search(
            r"\\draw\[very thick,blue!70!black\] \(([^)]+)\)", shifted
        )
        self.assertIsNotNone(baseline_start)
        self.assertIsNotNone(shifted_start)
        self.assertNotEqual(baseline_start.group(1), shifted_start.group(1))

    def test_surplus_tokens_are_drawn_in_core_not_supplied_only_by_legend(self) -> None:
        for model_id in (
            "consumer_surplus",
            "producer_surplus",
            "total_surplus",
            "welfare_surplus",
        ):
            core = self.render_core(model_id)
            with self.subTest(model_id=model_id):
                self.assertIn("quantity", core.lower())
                self.assertTrue("price" in core.lower() or "marginal" in core.lower())
                self.assertRegex(core, r"\\fill\[(?:green|orange)!18\]")
                self.assertIn(r"(Q^*,P^*)", core)

    def test_long_top_and_arrow_labels_are_bounded(self) -> None:
        force = self.render_core("force_balance")
        self.assertIn(r"anchor=south west", force)
        self.assertIn(r"anchor=south east", force)
        self.assertNotIn("rectangle (4.75,3.05) node", force)

        drag = self.render_core("quadratic_drag")
        self.assertIn("text width=1.45cm", drag)
        self.assertIn("text width=1.65cm", drag)

        point_particle = self.render_core("point_particle_angular_momentum")
        self.assertIn("text width=3.0cm", point_particle)
        self.assertIn("minimum size=1.05cm", point_particle)

    def test_momentum_annotations_reserve_space_between_arrow_and_text(self) -> None:
        for model_id in ("impulse_momentum", "angular_impulse"):
            core = self.render_core(model_id)
            with self.subTest(model_id=model_id):
                self.assertIn(r"anchor=south west,font=\scriptsize,text width=", core)
                self.assertNotRegex(core, r"-- \([^)]+\) node\[right\] \{(?:angular )?momentum")

    def test_rolling_energy_labels_are_outside_meter_rectangles(self) -> None:
        core = self.render_core("rolling_kinetic_energy")
        self.assertIn(r"at (4.9,2.5) {translation $K$}", core)
        self.assertIn(r"at (4.9,3.2) {rotation $K$}", core)
        self.assertNotIn(r"translational\\energy meter", core)
        self.assertNotIn("rectangle (5.65,2.95) node[midway]", core)


class ModelScenarioFigureApiTests(unittest.TestCase):
    def test_domain_entry_points_validate_visual_kinds(self) -> None:
        physics = PHYSICS_MODEL_SCENARIOS["vectors"]
        economics = ECONOMICS_MODEL_SCENARIOS["market_equilibrium"]
        self.assertTrue(
            physics_model_scenario_figure_body(physics, "physics_vector")[0]
        )
        self.assertTrue(
            economics_model_scenario_figure_body(
                economics, "econ_supply_demand"
            )[0]
        )
        with self.assertRaisesRegex(ValueError, "not a physics visual kind"):
            physics_model_scenario_figure_body(physics, "econ_curve")
        with self.assertRaisesRegex(ValueError, "not an economics visual kind"):
            economics_model_scenario_figure_body(economics, "physics_force")

    def test_invalid_scenario_contracts_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported"):
            render_model_scenario_figure({}, "unknown")
        with self.assertRaisesRegex(ValueError, "model_id"):
            render_model_scenario_figure(
                {
                    "setup": {"x": 1.0},
                    "result": {"y": 2.0},
                    "required_figure_tokens": ["body"],
                },
                "physics_force",
            )
        with self.assertRaisesRegex(ValueError, "omit required figure tokens"):
            render_model_scenario_figure(
                {
                    "model_id": "example",
                    "setup": {"x": 1.0},
                    "result": {"y": 2.0},
                    "required_figure_tokens": ["body"],
                    "visible_evidence_tokens": ["different"],
                },
                "physics_force",
            )

    def test_latex_escaping_and_normalization_cover_special_tokens(self) -> None:
        token = "rate_% & value_{x} #1 $ ^ ~ \\"
        escaped = latex_escape_label(token)
        for marker in (
            r"\_",
            r"\%",
            r"\&",
            r"\{",
            r"\}",
            r"\#",
            r"\$",
            r"\textasciicircum{}",
            r"\textasciitilde{}",
            r"\textbackslash{}",
        ):
            self.assertIn(marker, escaped)
        body, evidence = render_model_scenario_figure(
            {
                "model_id": "escaped_example",
                "setup": {"source_value": 2.0},
                "result": {"result_value": 4.0},
                "required_example_tokens": ["source_value"],
                "required_figure_tokens": [token],
                "visible_evidence_tokens": ["source_value", token],
            },
            "physics_vector",
        )
        self.assertFalse(figure_token_is_represented(body, token))
        self.assertNotIn(escaped, body)
        self.assertIn(r"Source value = $2$", body)
        self.assertEqual(evidence, ["source_value", token])

    def test_new_sources_are_ascii_and_do_not_import_stem_course(self) -> None:
        paths = (
            ROOT / "tools/model_scenario_figures.py",
            ROOT / "tests/test_model_scenario_figures.py",
        )
        for path in paths:
            with self.subTest(path=path.name):
                source = path.read_bytes().decode("ascii")
                tree = ast.parse(source)
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.append(node.module)
                self.assertFalse(
                    any(name == "stem_course" or name.endswith(".stem_course") for name in imports)
                )

    def test_no_nonfinite_values_are_silently_rendered(self) -> None:
        scenario = PHYSICS_MODEL_SCENARIOS["kinematics_1d"].as_dict()
        setup = scenario["setup"]
        assert isinstance(setup, dict)
        setup["initial_position"] = math.inf
        with self.assertRaisesRegex(ValueError, "finite numeric values"):
            render_model_scenario_figure(scenario, "physics_kinematics")


if __name__ == "__main__":
    unittest.main()

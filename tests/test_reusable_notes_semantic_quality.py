from __future__ import annotations

import re
import unittest

from tools.course_notes_models import build_model_note_payload
from tools.economics_model_scenarios import ECONOMICS_MODEL_SCENARIOS
from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY
from tools.model_scenario_figures import (
    render_complexity_growth_figure,
    render_fibonacci_memo_figure,
    render_model_scenario_figure,
)
from tools.physics_model_scenarios import PHYSICS_MODEL_SCENARIOS
from tools.physics_model_specs import PHYSICS_MODEL_REGISTRY


def worked_calculation(model_id: str, domain: str) -> str:
    payload = build_model_note_payload(model_id, domain)
    worked = next(example for example in payload["examples"] if example["kind"] == "worked")
    return str(worked["calculation"])


def render_physics(model_id: str) -> str:
    return render_model_scenario_figure(
        PHYSICS_MODEL_SCENARIOS[model_id],
        PHYSICS_MODEL_REGISTRY[model_id].visual_kind,
    )[0]


def render_economics(model_id: str) -> str:
    return render_model_scenario_figure(
        ECONOMICS_MODEL_SCENARIOS[model_id],
        ECONOMICS_MODEL_REGISTRY[model_id].visual_kind,
    )[0]


class WorkedDerivationQualityTests(unittest.TestCase):
    def test_atwood_derivation_eliminates_tension_then_substitutes_back(self) -> None:
        calculation = worked_calculation("pulley_constraint", "physics")
        first_balance = calculation.index(r"T-m_1g=m_1a")
        second_balance = calculation.index(r"m_2g-T=m_2a")
        eliminated = calculation.index(r"(m_2-m_1)g=(m_1+m_2)a")
        acceleration = calculation.index(r"a=(3-2)9.8/(2+3)=1.96")
        tension = calculation.index(r"T=m_1(g+a)=2(9.8+1.96)=23.52")
        self.assertLess(max(first_balance, second_balance), eliminated)
        self.assertLess(eliminated, acceleration)
        self.assertLess(acceleration, tension)

    def test_competitive_firm_derives_output_cost_revenue_and_profit(self) -> None:
        calculation = worked_calculation("perfect_competition", "economics")
        stages = (
            r"MR=P=50",
            r"50=10+2q",
            r"q^*=20",
            r"VC(q)=10q+(2/2)q^2",
            r"TC=VC+FC=700",
            r"TR=Pq^*=50(20)=1000",
            r"\pi=TR-TC=1000-700=300",
        )
        positions = [calculation.index(stage) for stage in stages]
        self.assertEqual(positions, sorted(positions))

    def test_monopoly_examples_derive_marginal_revenue_before_prices(self) -> None:
        monopoly = worked_calculation("monopoly", "economics")
        monopoly_stages = (
            r"TR(q)=100q-2q^2",
            r"MR(q)=100-4q",
            r"100-4q=20",
            r"q_m=20",
            r"P_m=100-2(20)=60",
            r"\pi=P_mq_m-MC\,q_m-FC=60(20)-20(20)-100=700",
        )
        self.assertEqual(
            [monopoly.index(stage) for stage in monopoly_stages],
            sorted(monopoly.index(stage) for stage in monopoly_stages),
        )

        discrimination = worked_calculation("price_discrimination", "economics")
        self.assertLess(discrimination.index(r"MR_1=100-4q_1"), discrimination.index(r"q_1=(100-20)/4=20"))
        self.assertLess(discrimination.index(r"MR_2=80-2q_2"), discrimination.index(r"q_2=(80-20)/2=30"))
        self.assertLess(discrimination.index(r"q_2=(80-20)/2=30"), discrimination.index(r"P_1=60"))
        self.assertIn(r"60(20)+50(30)-20(50)-100=1600", discrimination)

    def test_inertia_comparison_moves_mass_without_changing_its_amount(self) -> None:
        payload = build_model_note_payload("moment_of_inertia", "physics")
        boundary = next(example for example in payload["examples"] if example["kind"] == "boundary")
        setup = str(boundary["setup"])
        calculation = str(boundary["calculation"])
        self.assertIn("Change only perpendicular distances", setup)
        self.assertIn(r"\left(1, 2, 3\right)", setup)
        self.assertIn(r"\left(1.25, 2, 3\right)", setup)
        self.assertNotIn("replace \\(\\text{mass elements}", setup)
        self.assertIn(r"\left(3.125, 12, 9\right)", calculation)
        self.assertIn(r"I_{\mathrm{rot}}=24.125", calculation)


class FigureSemanticQualityTests(unittest.TestCase):
    def test_kinematics_velocity_arrow_starts_on_the_trajectory(self) -> None:
        body = render_physics("kinematics_2d")
        self.assertIn(r"\coordinate (kinematic-state) at (3.7,2.1);", body)
        self.assertRegex(
            body,
            r"\\draw\[->,very thick,green!50!black\] \(kinematic-state\) -- \([^)]*\).*\{velocity arrow\}",
        )
        trajectory = next(line for line in body.splitlines() if "plot[smooth] coordinates" in line)
        self.assertIn("(3.7,2.1)", trajectory)

    def test_tax_prices_and_wedge_share_one_traded_quantity(self) -> None:
        body = render_economics("tax_incidence")
        self.assertIn(r"(seller-price-at-tax-quantity) -- (buyer-price-at-tax-quantity)", body)
        self.assertIn(r"-- (buyer-price-at-tax-quantity) node[left] {$P_b$}", body)
        self.assertIn(r"-- (seller-price-at-tax-quantity) node[left] {$P_s$}", body)
        self.assertIn(r"(tax-quantity) -- (seller-price-at-tax-quantity)", body)
        coordinate_line = next(line for line in body.splitlines() if "coordinate (tax-quantity)" in line)
        self.assertEqual(coordinate_line.count("(2.75,"), 3)

    def test_health_figure_links_patient_price_to_patient_demand(self) -> None:
        body = render_economics("health_economics")
        self.assertIn(r"-- (patient-price-at-demand)", body)
        self.assertIn(r"(patient-quantity) -- (patient-price-at-demand)", body)
        self.assertIn(r"{patient price}", body)
        self.assertIn(r"{insurance overuse}", body)

    def test_price_discrimination_uses_typeset_subscripts(self) -> None:
        body = render_economics("price_discrimination")
        for label in (r"$D_1$", r"$D_2$", r"$MR_1$", r"$MR_2$", r"$P_1$", r"$P_2$"):
            self.assertIn(label, body)
        self.assertNotRegex(body, r"node[^\n]*\{(?:D|MR|P) [12]\};")

    def test_fibonacci_edges_point_from_each_request_to_its_dependencies(self) -> None:
        body, evidence = render_fibonacci_memo_figure(6)
        edge_pairs = {
            (int(parent), int(child))
            for parent, child in re.findall(
                r"\\draw\[->,thick\] \(fib-(\d+)\).*?\(fib-(\d+)\);",
                body,
            )
        }
        expected = {(n, n - delta) for n in range(2, 7) for delta in (1, 2)}
        self.assertEqual(edge_pairs, expected)
        self.assertTrue(all(parent > child for parent, child in edge_pairs))
        memo_cells = re.findall(r"\\node\[draw,[^\n]+\] \(memo-(\d+)\)", body)
        self.assertEqual([int(index) for index in memo_cells], list(range(7)))
        self.assertIn("F(6)->F(5)", evidence)

    def test_complexity_ticks_have_a_sample_from_every_series(self) -> None:
        sizes = (1, 2, 4, 8, 16)
        body, evidence = render_complexity_growth_figure(sizes)
        sample_nodes = re.findall(r"\(sample-(constant|logarithmic|linear|quadratic)-(\d+)\)", body)
        self.assertEqual(len(sample_nodes), 4 * len(sizes))
        for size in sizes:
            self.assertEqual({series for series, n in sample_nodes if int(n) == size}, {"constant", "logarithmic", "linear", "quadratic"})
        self.assertEqual(len(evidence), len(sizes))
        self.assertIn("linear=16, quadratic=256", evidence[-1])


if __name__ == "__main__":
    unittest.main()

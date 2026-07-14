from __future__ import annotations

import unittest

from tools.economics_model_scenarios import ECONOMICS_MODEL_SCENARIOS
from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY
from tools.model_scenario_figures import render_model_scenario_figure
from tools.physics_model_scenarios import PHYSICS_MODEL_SCENARIOS
from tools.physics_model_specs import PHYSICS_MODEL_REGISTRY


RIGHT_LANE_COORDINATE = "at (5.85,"


def render_physics(model_id: str) -> str:
    scenario = PHYSICS_MODEL_SCENARIOS[model_id]
    visual_kind = PHYSICS_MODEL_REGISTRY[model_id].visual_kind
    return render_model_scenario_figure(scenario, visual_kind)[0]


def render_economics(model_id: str) -> str:
    scenario = ECONOMICS_MODEL_SCENARIOS[model_id]
    visual_kind = ECONOMICS_MODEL_REGISTRY[model_id].visual_kind
    return render_model_scenario_figure(scenario, visual_kind)[0]


class ModelScenarioFigureLayoutTests(unittest.TestCase):
    def assert_bounded_right_label(
        self, body: str, label: str, *, anchor: str = "south east"
    ) -> None:
        matching_lines = [line for line in body.splitlines() if "{" + label + "}" in line]
        self.assertEqual(len(matching_lines), 1)
        line = matching_lines[0]
        self.assertIn(rf"\node[anchor={anchor}", line)
        self.assertIn(RIGHT_LANE_COORDINATE, line)
        self.assertNotIn("node[right]", line)

    def assert_separated_right_labels(
        self, body: str, upper_label: str, lower_label: str
    ) -> None:
        self.assert_bounded_right_label(body, upper_label)
        self.assert_bounded_right_label(body, lower_label, anchor="north east")
        lower_line = next(
            line for line in body.splitlines() if "{" + lower_label + "}" in line
        )
        self.assertIn("anchor=north east", lower_line)

    def test_stacked_kinematics_graph_labels_stay_left_of_worked_values(self) -> None:
        expected_labels = {
            "kinematics_position_velocity": ("position graph", "velocity graph"),
            "kinematics_acceleration": ("velocity graph", "acceleration graph"),
        }
        for model_id, labels in expected_labels.items():
            body = render_physics(model_id)
            with self.subTest(model_id=model_id):
                for label in labels:
                    self.assert_bounded_right_label(body, label)

    def test_shared_clock_uses_a_separate_left_top_annotation_lane(self) -> None:
        for model_id in (
            "kinematics_position_velocity",
            "kinematics_acceleration",
        ):
            body = render_physics(model_id)
            with self.subTest(model_id=model_id):
                clock_lines = [
                    line for line in body.splitlines() if "{shared clock}" in line
                ]
                self.assertEqual(len(clock_lines), 1)
                self.assertIn(
                    r"\node[anchor=south east,red!70!black] at (3.55,3.35)",
                    clock_lines[0],
                )
                guide_line = next(
                    line
                    for line in body.splitlines()
                    if r"\draw[dashed,red!70!black]" in line
                )
                self.assertNotIn("node[above]", guide_line)
                self.assertNotIn("shared clock", guide_line)

    def test_circular_force_labels_do_not_grow_into_speed_and_mass_legend(self) -> None:
        body = render_physics("circular_dynamics")
        self.assert_bounded_right_label(body, "force arrows")
        inward_label_line = next(
            line for line in body.splitlines() if "{net inward force arrow}" in line
        )
        self.assertIn("(inward-force-label) at (0.3,3.35)", inward_label_line)
        inward_arrow_line = next(
            line
            for line in body.splitlines()
            if r"\draw[->,very thick,red!70!black] (cm) -- (3,1.8)" in line
        )
        self.assertNotIn("node[", inward_arrow_line)
        self.assertIn(
            r"\draw[thin,red!70!black] (inward-force-label.south east) -- (3.55,2.22);",
            body,
        )

    def test_rolling_translation_label_does_not_grow_into_angular_legend(self) -> None:
        body = render_physics("rolling_kinematics")
        self.assert_bounded_right_label(body, "translation arrow")
        self.assertNotIn("node[right] {translation arrow}", body)

    def test_price_discrimination_d2_and_mc_use_separated_label_lanes(self) -> None:
        body = render_economics("price_discrimination")
        self.assert_separated_right_labels(body, "D 2", "MC")
        mr2_line = next(line for line in body.splitlines() if "{MR 2}" in line)
        self.assertIn("node[pos=0.5,above right,font=\\scriptsize]", mr2_line)
        self.assertNotIn("node[right] {D 2}", body)
        self.assertNotIn("node[right] {MC}", body)
        self.assertNotIn("node[right] {MR 2}", body)

    def test_isoquant_and_isocost_use_separated_label_lanes(self) -> None:
        body = render_economics("factor_input_markets")
        self.assert_separated_right_labels(body, "target isoquant", "isocost")
        self.assertNotIn("node[right] {target isoquant}", body)
        self.assertNotIn("node[right] {isocost}", body)


if __name__ == "__main__":
    unittest.main()

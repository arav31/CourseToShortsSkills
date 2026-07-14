from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course
from tools.physics_model_scenarios import get_physics_model_scenario


class StoryboardScenarioRoutingTests(unittest.TestCase):
    def test_plan_to_storyboard_keeps_oligopoly_collusion_numerically_coherent(self) -> None:
        concept = stem_course.source_term_concept("Oligopoly II", "economics")
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / "source_pack.json").write_text(
                json.dumps({"title": "MIT 14.01", "materials": []}),
                encoding="utf-8",
            )
            with mock.patch.object(stem_course, "choose_concepts", return_value=[concept]):
                stem_course.cmd_plan(argparse.Namespace(run=str(run), max_shorts=40))
            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            short = json.loads(
                (run / "short_plan.json").read_text(encoding="utf-8")
            )["shorts"][0]
            storyboard = json.loads(
                (run / short["animation_plan_file"]).read_text(encoding="utf-8")
            )

        authored = json.dumps(
            {
                "worked_example": short["worked_example"],
                "question_prompt": short["question_prompt"],
                "beats": storyboard["beats"],
                "reveal": storyboard["reveal"],
                "semantic_transition_contract": storyboard["semantic_transition_contract"],
            },
            sort_keys=True,
        ).casefold()
        self.assertEqual(short["model_id"], "oligopoly_collusion")
        self.assertEqual(
            storyboard["semantic_support"]["route_key"],
            "economics:cournot_collusion",
        )
        self.assertNotRegex(
            authored,
            r"high,high|low,low|high or low price|payoff matrix|payoff cell",
        )

        example = " ".join(short["worked_example"].values())
        for token in (
            "P=100-1Q",
            "MC=10",
            "QN=60",
            "PN=40",
            "profit 900",
            "QC=45",
            "PC=55",
            "profit to 1012.5",
        ):
            self.assertIn(token, example)

        renderer = storyboard["concrete_example"]["renderer_state"]
        self.assertEqual(renderer["numeric_setup"], {
            "demand_intercept": 100.0,
            "demand_slope": 1.0,
            "marginal_cost": 10.0,
        })
        self.assertEqual(renderer["result_fields"]["cournot_total_quantity"], 60.0)
        self.assertEqual(renderer["result_fields"]["cournot_price"], 40.0)
        self.assertEqual(renderer["result_fields"]["cournot_firm_profit"], 900.0)
        self.assertEqual(renderer["result_fields"]["collusive_total_quantity"], 45.0)
        self.assertEqual(renderer["result_fields"]["collusive_price"], 55.0)
        self.assertEqual(renderer["result_fields"]["collusive_firm_profit"], 1012.5)
        cue_text = " ".join(str(beat["text"]) for beat in storyboard["beats"])
        for cue in (
            "QN 60 falls to QC 45",
            "Demand intercept 100 slope 1 and MC 10",
            "Price rises 40 to 55",
            "Per-firm profit rises 900 to 1012.5",
        ):
            self.assertIn(cue, cue_text)
        transition_actions = " ".join(
            str(row["action"])
            for row in storyboard["semantic_transition_contract"]["transitions"]
        )
        self.assertIn("Q=60, P=40, and per-firm profit=900", transition_actions)
        self.assertIn("P=40 to P=55", transition_actions)
        self.assertEqual(stem_course.animation_plan_contract_errors(storyboard, short), [])

    def test_cmd_plan_authors_rolling_content_from_model_identity(self) -> None:
        concept = stem_course.source_term_concept("Rolling Kinematics", "physics")
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / "source_pack.json").write_text(
                json.dumps({"title": "Physics", "materials": []}),
                encoding="utf-8",
            )
            with mock.patch.object(stem_course, "choose_concepts", return_value=[concept]):
                stem_course.cmd_plan(argparse.Namespace(run=str(run), max_shorts=40))
            short = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))["shorts"][0]

        authored = " ".join((
            short["hook"],
            short["intuition"],
            *short["worked_example"].values(),
            *short["question_prompt"].values(),
        )).casefold()
        self.assertEqual(short["concept"], "Rolling Kinematics")
        self.assertEqual(short["model_id"], "rolling_kinematics")
        self.assertEqual(short["scenario_mode"], "rolling_kinematics")
        self.assertEqual(short["visual_type"], "physics_kinematics")
        self.assertIn("rolling body", authored)
        self.assertIn("without slipping", authored)
        self.assertIn("contact point", authored)
        self.assertNotIn("torque", authored)
        self.assertNotIn("angular impulse", authored)

    def test_semantic_scenario_overrides_misleading_physics_concept_subtype(self) -> None:
        scenario = get_physics_model_scenario("rolling_kinematics").as_dict()
        short = {
            "index": 40,
            "concept": "Torque",
            "hook": "Torque measures rotational leverage.",
            "intuition": "Apply a tangential force at a lever arm.",
            "formula": r"\tau=rF_\perp",
            "plain_formula": "tau = r F_perp",
            "visual_type": "physics_rotation",
            "worked_example": {
                "setup": "F = 10 N, r = 2 m, dt = 3 s",
                "calculation": "tau = 20 N m",
                "takeaway": "angular impulse is 60 kg m^2/s",
            },
            "model_id": "rolling_kinematics",
            "scenario_mode": "rolling_kinematics",
            "model_scenario": scenario,
        }

        plan = stem_course.build_animation_plan(short)
        searchable = str(plan).casefold()
        actions = " ".join(str(beat["action"]) for beat in plan["beats"]).casefold()
        renderer_transitions = str(
            plan["concrete_example"]["renderer_state"]["transitions"]
        ).casefold()

        self.assertEqual(plan["semantic_support"]["visual_kind"], "physics_kinematics")
        self.assertEqual(plan["semantic_support"]["route_key"], "physics:rolling_kinematics")
        self.assertEqual(plan["semantic_support"]["semantic_mode"], "rolling_kinematics")
        self.assertIn("rolling body", searchable)
        self.assertIn("no slip", searchable)
        self.assertIn("contact point has zero relative speed", plan["invariant"]["statement"].casefold())
        self.assertIn("contact_speed", str(plan["concrete_example"]))
        self.assertNotIn("torque", plan["visual_claim"].casefold())
        self.assertNotIn("applied force", actions)
        self.assertNotIn("angular impulse", actions)
        self.assertNotIn("torque", renderer_transitions)
        self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])


if __name__ == "__main__":
    unittest.main()

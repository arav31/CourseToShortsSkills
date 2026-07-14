from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from tools import stem_course
from tools.economics_model_scenarios import get_economics_model_scenario
from tools.economics_model_specs import MIT_14_01_TITLE_MODEL_IDS
from tools.physics_model_specs import MIT_8_01_TITLE_CONTRACTS
from tools.validate_course_run import CourseRunValidator
from tools.video_economics_models import resolve_economics_video_route


def fresh_source_run(course_title: str, titles: list[str]) -> tempfile.TemporaryDirectory[str]:
    temporary = tempfile.TemporaryDirectory(prefix="mit-exact-title-plan-")
    run = Path(temporary.name)
    stem_course.write_json(run / "source_pack.json", {
        "title": course_title,
        "materials": [{
            "kind": "page",
            "title": "Course outline",
            "text": "\n".join(
                f"Unit {index}: {title}" for index, title in enumerate(titles, start=1)
            ),
        }],
    })
    stem_course.cmd_plan(argparse.Namespace(
        run=str(run), max_shorts=0, allow_partial_plan=False
    ))
    stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
    return temporary


def assert_scenario_prose(
    case: unittest.TestCase,
    worked: dict[str, object],
    scenario: dict[str, object],
) -> None:
    prose = " ".join(str(worked[field]) for field in ("setup", "calculation", "takeaway"))
    result_key = "result" if "result" in scenario else "results"
    for section in ("setup", "calculation", result_key):
        values = scenario[section]
        case.assertIsInstance(values, dict)
        for variable, value in values.items():
            case.assertIn(str(variable), prose)
            case.assertIn(str(value), prose)
    for token in scenario["required_example_tokens"]:
        case.assertIn(str(token), prose)


def assert_animation_state_figure_evidence(
    case: unittest.TestCase,
    renderer: dict[str, object],
) -> None:
    scenario = renderer["model_scenario"]
    case.assertIsInstance(scenario, dict)
    states = renderer.get("animation_states", scenario["animation_states"])
    case.assertIsInstance(states, list)
    visible = " ".join(
        str(state.get(field, ""))
        for state in states
        for field in ("visible_tokens", "visible_evidence_tokens", "visible_object_ids")
    )
    required = renderer.get("required_figure_tokens", scenario["required_figure_tokens"])
    for token in required:
        case.assertIn(str(token), visible)


class MitExactTitlePlanIntegrationTests(unittest.TestCase):
    def assert_strict_animation_plans_pass(self, run: Path) -> None:
        plan = stem_course.read_json(run / "short_plan.json")
        validator = CourseRunValidator(run)
        validator.validate_animation_plans(plan)
        failures = [issue for issue in validator.issues if issue.severity == "FAIL"]
        self.assertEqual(failures, [])

    def test_fresh_mit_8_01_plan_passes_all_38_exact_titles(self) -> None:
        titles = [contract.exact_title for contract in MIT_8_01_TITLE_CONTRACTS]
        temporary = fresh_source_run("MIT 8.01 Classical Mechanics", titles)
        self.addCleanup(temporary.cleanup)
        run = Path(temporary.name)
        plan = stem_course.read_json(run / "short_plan.json")
        self.assertEqual(len(plan["shorts"]), 38)

        for short, contract in zip(plan["shorts"], MIT_8_01_TITLE_CONTRACTS):
            with self.subTest(title=contract.exact_title):
                scenario = short["model_scenario"]
                storyboard = stem_course.read_json(
                    run / stem_course.animation_plan_relative_path(int(short["index"]))
                )
                renderer = storyboard["concrete_example"]["renderer_state"]
                self.assertEqual(short["concept"], contract.exact_title)
                self.assertEqual(scenario["model_id"], contract.model_id)
                self.assertEqual(scenario["mode"], contract.scenario_mode)
                self.assertEqual(renderer["model_scenario"], scenario)
                self.assertEqual(storyboard["semantic_support"]["route_key"], contract.video_route_key)
                self.assertEqual(renderer["route_key"], contract.video_route_key)
                assert_scenario_prose(self, short["worked_example"], scenario)
                assert_animation_state_figure_evidence(self, renderer)

        self.assert_strict_animation_plans_pass(run)

    def test_fresh_mit_14_01_plan_passes_all_26_exact_titles(self) -> None:
        titles = list(MIT_14_01_TITLE_MODEL_IDS)
        temporary = fresh_source_run("MIT 14.01 Principles of Microeconomics", titles)
        self.addCleanup(temporary.cleanup)
        run = Path(temporary.name)
        plan = stem_course.read_json(run / "short_plan.json")
        self.assertEqual(len(plan["shorts"]), 26)

        for short, (title, model_id) in zip(plan["shorts"], MIT_14_01_TITLE_MODEL_IDS.items()):
            with self.subTest(title=title):
                scenario = get_economics_model_scenario(model_id).as_dict()
                route = resolve_economics_video_route(model_id, fail_closed=True)
                storyboard = stem_course.read_json(
                    run / stem_course.animation_plan_relative_path(int(short["index"]))
                )
                renderer = storyboard["concrete_example"]["renderer_state"]
                self.assertEqual(short["concept"], title)
                self.assertEqual(short["model_scenario"], scenario)
                self.assertEqual(renderer["model_scenario"], scenario)
                self.assertEqual(storyboard["semantic_support"]["route_key"], route.route_key)
                self.assertEqual(renderer["route_key"], route.route_key)
                self.assertEqual(renderer["canonical_formula"], short["formula"])
                assert_scenario_prose(self, short["worked_example"], scenario)
                assert_animation_state_figure_evidence(self, renderer)

        self.assert_strict_animation_plans_pass(run)

    def test_attach_replaces_independent_stories_for_every_exact_title(self) -> None:
        cases = [
            (contract.exact_title, contract.model_id, "generic")
            for contract in MIT_8_01_TITLE_CONTRACTS
        ] + [
            (title, model_id, "generic")
            for title, model_id in MIT_14_01_TITLE_MODEL_IDS.items()
        ]
        for index, (title, model_id, visual_type) in enumerate(cases, start=1):
            with self.subTest(title=title):
                short: dict[str, object] = {
                    "index": index,
                    "concept": title,
                    "visual_type": visual_type,
                    "formula": "independent authored formula",
                    "worked_example": {
                        "setup": "independent authored setup",
                        "calculation": "independent authored calculation",
                        "takeaway": "independent authored result",
                    },
                }
                stem_course.attach_plan_model_identity(short)
                self.assertEqual(short["model_id"], model_id)
                self.assertNotEqual(short["formula"], "independent authored formula")
                self.assertNotIn("independent authored", str(short["worked_example"]))


if __name__ == "__main__":
    unittest.main()

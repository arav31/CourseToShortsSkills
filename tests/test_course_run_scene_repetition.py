from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.validate_course_run import CourseRunValidator, scene_causal_signature


def structured_plan() -> dict[str, object]:
    return {
        "semantic_support": {
            "visual_kind": "econ_budget",
            "route_key": "economics:consumer_choice:income_substitution",
            "semantic_mode": "consumer_choice",
            "status": "supported",
        },
        "concrete_example": {
            "renderer_state": {
                "payload_type": "economics",
                "family": "consumer_choice",
                "mode": "income_substitution",
                "renderer_variant": "compensated_demand",
                "model_id": "income_substitution_effects",
                "scenario_mode": "income_substitution",
                "required_figure_tokens": ["compensated_bundle", "income_vector"],
                "model_scenario": {
                    "model_id": "income_substitution_effects",
                    "mode": "income_substitution",
                    "animation_states": [
                        {"phase": "setup", "state_id": "income_substitution_effects:setup", "values": {"income": 100}},
                        {"phase": "change", "state_id": "income_substitution_effects:change", "values": {"income": 80}},
                        {"phase": "result", "state_id": "income_substitution_effects:result", "values": {"quantity": 7}},
                    ],
                },
            }
        },
        "object_roster": [
            {"id": "budget", "role": "budget line; instantiated from consumer prose with 100 dollars", "persistent": True},
            {"id": "bundle", "role": "chosen bundle; instantiated from different worked-example prose", "persistent": True},
            {"id": "compensated", "role": "compensated bundle; values are 3 and 7", "persistent": True},
        ],
        "semantic_transition_contract": {
            "transitions": [
                {"id": "consumer_choice:rotate_budget", "kind": "rotate_budget", "claim": "Price falls from 10 to 8."},
                {"id": "consumer_choice:compensate", "kind": "compensate_income", "claim": "Hold utility fixed at 42."},
                {"id": "consumer_choice:resolve", "kind": "resolve_bundle", "claim": "Quantity rises to 7."},
            ]
        },
    }


class SceneRepetitionValidationTests(unittest.TestCase):
    def test_current_plan_skips_first_match_income_substitution_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="scene-routing-") as tmp:
            validator = CourseRunValidator(Path(tmp))
            validator.validate_scene_visual_quality(
                [
                    {
                        "path": Path(tmp) / "scene.py",
                        "concept": "Demand curves and income/substitution effects",
                        "visual_kind": "econ_budget",
                        "animation_plan": structured_plan(),
                    }
                ],
                "economics demand income substitution",
            )

            self.assertFalse(any(issue.area == "scene.visual-family" for issue in validator.issues))

    def test_distinct_concepts_with_same_causal_signature_fail_in_strict_mode(self) -> None:
        first = structured_plan()
        second = copy.deepcopy(first)
        second["concrete_example"]["renderer_state"]["model_scenario"]["animation_states"][0]["values"] = {"income": 999}
        second["semantic_transition_contract"]["transitions"][0]["claim"] = "Entirely different prose and 999 values."
        second["object_roster"][0]["role"] += "; another prose wrapper"

        with tempfile.TemporaryDirectory(prefix="scene-repetition-") as tmp:
            root = Path(tmp)
            left = root / "left.py"
            right = root / "right.py"
            validator = CourseRunValidator(root)
            visuals = [
                {"path": left, "concept": "Income and substitution effects", "animation_plan": first},
                {"path": right, "concept": "Compensated demand decomposition", "animation_plan": second},
            ]
            with mock.patch("tools.validate_course_run.SequenceMatcher", side_effect=AssertionError("modern plans must not compare source")):
                validator.detect_repeated_scene_sources([(left, "same wrapper"), (right, "same wrapper")], visuals)

            collisions = [issue for issue in validator.issues if issue.area == "scene.repetition"]
            self.assertEqual(len(collisions), 1)
            self.assertEqual(collisions[0].severity, "FAIL")
            self.assertIn("structural causal signature", collisions[0].message)

    def test_causal_signature_distinguishes_each_structural_dimension(self) -> None:
        baseline = structured_plan()
        mutations = (
            ("route", lambda plan: plan["semantic_support"].update(route_key="economics:consumer_choice:mrs")),
            ("renderer variant", lambda plan: plan["concrete_example"]["renderer_state"].update(renderer_variant="slutsky")),
            ("scenario mode", lambda plan: plan["concrete_example"]["renderer_state"].update(scenario_mode="hicksian")),
            ("persistent role", lambda plan: plan["object_roster"][0].update(role="indifference curve")),
            ("transition", lambda plan: plan["semantic_transition_contract"]["transitions"][0].update(kind="shift_budget")),
            ("state id", lambda plan: plan["concrete_example"]["renderer_state"]["model_scenario"]["animation_states"][0].update(state_id="consumer_choice:initial")),
            ("figure token", lambda plan: plan["concrete_example"]["renderer_state"].update(required_figure_tokens=["utility_tangent"])),
        )
        baseline_signature = scene_causal_signature(baseline)
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(baseline)
                mutate(changed)
                self.assertNotEqual(scene_causal_signature(changed), baseline_signature)


if __name__ == "__main__":
    unittest.main()

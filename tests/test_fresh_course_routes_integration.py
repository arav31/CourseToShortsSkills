from __future__ import annotations

import ast
import re
import types
import unittest

from tools import stem_course
from tools.economics_model_specs import MIT_14_01_TITLE_MODEL_IDS
from tools.physics_model_specs import MIT_8_01_TITLE_CONTRACTS
from tools.video_economics_models import validate_economics_video_payload
from tools.video_group_models import GROUP_VIDEO_ROUTES, build_group_video_payload


CS_COURSE_TITLES = (
    "Data Structures", "Sorting", "Hashing", "Linear Sorting",
    "Binary Search Trees", "AVL Trees and Rotations", "Binary Heaps",
    "Breadth-First Search", "Depth-First Search", "Weighted Shortest Paths",
    "Bellman-Ford", "Dijkstra's Algorithm", "Johnson's Algorithm",
    "Memoization and Recursive Dynamic Programming",
    "Dynamic Programming State Design", "Dynamic Programming Applications",
    "Pseudopolynomial Dynamic Programming", "Complexity",
)


def planned_short(title: str, domain: str, index: int) -> dict[str, object]:
    short = stem_course.concept_to_short(
        stem_course.source_term_concept(title, domain),
        index,
    )
    stem_course.attach_plan_model_identity(short)
    return short


def assert_storyboard_contract(
    case: unittest.TestCase,
    short: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    kind = stem_course.infer_visual_kind(short)
    descriptor = stem_course.animation_route_descriptor(short, kind)
    case.assertTrue(descriptor["supported"], descriptor["reason"])
    plan = stem_course.build_animation_plan(short)
    case.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])
    return descriptor, plan


class FreshCourseRouteIntegrationTests(unittest.TestCase):
    def test_all_38_physics_titles_keep_canonical_identity_and_evidence(self) -> None:
        self.assertEqual(len(MIT_8_01_TITLE_CONTRACTS), 38)
        descriptor_keys: set[str] = set()
        for contract in MIT_8_01_TITLE_CONTRACTS:
            with self.subTest(title=contract.exact_title):
                short = planned_short(contract.exact_title, "physics", contract.unit_number)
                descriptor, plan = assert_storyboard_contract(self, short)
                renderer = descriptor["renderer_state"]
                scenario = renderer["scenario"]
                expected_worked = stem_course.canonical_physics_worked_example(scenario)
                self.assertEqual(short["worked_example"], expected_worked)
                self.assertEqual(descriptor["route_key"], contract.video_route_key)
                self.assertEqual(renderer["route_key"], contract.video_route_key)
                self.assertEqual(renderer["model_id"], contract.model_id)
                self.assertEqual(renderer["worked_example"], expected_worked)
                self.assertEqual(plan["semantic_support"]["route_key"], contract.video_route_key)
                descriptor_keys.add(str(descriptor["route_key"]))
        self.assertEqual(len(descriptor_keys), 38)

    def test_all_26_economics_titles_use_structured_video_payloads(self) -> None:
        self.assertEqual(len(MIT_14_01_TITLE_MODEL_IDS), 26)
        for index, (title, model_id) in enumerate(MIT_14_01_TITLE_MODEL_IDS.items(), start=1):
            with self.subTest(title=title):
                short = planned_short(title, "economics", index)
                kind = stem_course.infer_visual_kind(short)
                economics = stem_course.visual_data_for(short, kind)["economics"]
                payload = economics["video_payload"]
                self.assertEqual(payload["model_id"], model_id)
                self.assertEqual(payload["worked_example"], short["worked_example"])
                self.assertEqual(validate_economics_video_payload(payload), [])
                descriptor, plan = assert_storyboard_contract(self, short)
                self.assertEqual(descriptor["renderer_state"]["model_id"], model_id)
                self.assertEqual(plan["concrete_example"]["renderer_state"]["model_id"], model_id)

    def test_all_24_group_titles_have_complete_math_aware_cues(self) -> None:
        self.assertEqual(len(GROUP_VIDEO_ROUTES), 24)
        helper_tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
        fallback_node = next(
            node for node in helper_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "formula_fallback_text"
        )
        namespace = {"re": re}
        exec(compile(ast.Module(body=[fallback_node], type_ignores=[]), "<group-fallback>", "exec"), namespace)
        harness = types.SimpleNamespace(formula_tex_text=lambda value: value)
        harness.formula_fallback_text = types.MethodType(namespace["formula_fallback_text"], harness)
        residue = re.compile(
            r"\\[A-Za-z]+|\b(?:Longrightarrow|xrightarrow|operatorname|langle|rangle|frac|mathbb|pmod)\b"
        )

        for index, route in enumerate(GROUP_VIDEO_ROUTES, start=1):
            with self.subTest(title=route.title):
                payload = build_group_video_payload(route.title)
                formula = str(payload["canonical_formula"])
                unicode_formula = stem_course.formula_unicode_text(formula)
                generated_fallback = harness.formula_fallback_text(formula, formula)
                self.assertNotRegex(unicode_formula, residue)
                self.assertNotRegex(generated_fallback, residue)
                cue, lines = stem_course.animation_plan_visible_cue(formula)
                self.assertLessEqual(len(lines), stem_course.ANIMATION_PLAN_MAX_CUE_LINES)
                self.assertNotIn("...", cue)
                short = planned_short(route.title, "group_theory", index)
                descriptor, _plan = assert_storyboard_contract(self, short)
                self.assertEqual(descriptor["route_key"], route.route_key)

    def test_all_18_cs_titles_finish_storyboards_with_canonical_special_routes(self) -> None:
        self.assertEqual(len(CS_COURSE_TITLES), 18)
        for index, title in enumerate(CS_COURSE_TITLES, start=1):
            with self.subTest(title=title):
                short = planned_short(title, "algorithms", index)
                descriptor, _plan = assert_storyboard_contract(self, short)
                renderer = descriptor["renderer_state"]
                if title == "Johnson's Algorithm":
                    self.assertEqual(renderer["route_key"], "cs:graph:johnson")
                    self.assertEqual(descriptor["route_key"], "cs:graph:johnson")
                if title == "Memoization and Recursive Dynamic Programming":
                    self.assertEqual(renderer["route_key"], "cs:dp:fibonacci_table")
                    self.assertEqual(descriptor["route_key"], "cs:dp:fibonacci_table")

        avl = planned_short("AVL Trees and Rotations", "algorithms", 1)
        state = stem_course.animation_renderer_state(avl, stem_course.infer_visual_kind(avl))
        transitions = stem_course.semantic_plan_contract(state)["transitions"]
        expose = next(row for row in transitions if row["id"] == "avl:expose-imbalance")
        rotate = next(row for row in transitions if row["id"] == "avl:rotate-once")
        self.assertEqual(rotate["before"]["cs:avl:pivot"], expose["after"]["cs:avl:pivot"])


if __name__ == "__main__":
    unittest.main()

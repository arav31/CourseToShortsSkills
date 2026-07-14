from __future__ import annotations

import ast
import unittest

from tools import stem_course


CURATED = {concept.name: concept for concept in stem_course.ALGORITHMS}
LEGACY_TOPICS = (
    "Asymptotic complexity",
    "Divide and conquer",
    "Data Structures",
    "Sorting",
    "Hashing",
    "Binary Search Trees",
    "AVL Trees and Rotations",
    "Binary Heaps",
)


def short_for(topic: str, index: int = 1) -> dict[str, object]:
    concept = CURATED.get(topic) or stem_course.source_term_concept(topic, "algorithms")
    return stem_course.concept_to_short(concept, index)


def helper_function(name: str):
    tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<cs-helper>", "exec"), namespace)
    return namespace[name]


class CsLegacyRouteContractTests(unittest.TestCase):
    def test_all_eight_routes_have_exact_persistent_transition_bindings(self) -> None:
        for index, topic in enumerate(LEGACY_TOPICS, start=1):
            with self.subTest(topic=topic):
                short = short_for(topic, index)
                kind = stem_course.infer_visual_kind(short)
                self.assertNotEqual(kind, "numeric_rule")
                state = stem_course.animation_renderer_state(short, kind)
                contract = stem_course.semantic_plan_contract(state)
                self.assertIsNotNone(contract)
                transitions = contract["transitions"]
                self.assertGreaterEqual(len(transitions), 4)
                transition_ids = [str(row["id"]) for row in transitions]
                self.assertEqual(len(transition_ids), len(set(transition_ids)))

                roster_ids = {str(row["id"]) for row in contract["objects"]}
                for transition in transitions:
                    self.assertTrue(set(transition["persistent_object_ids"]).issubset(roster_ids))
                    self.assertNotEqual(transition["before"], transition["after"])

                plan = stem_course.build_animation_plan(short)
                self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])
                scheduled_ids = [
                    transition_id
                    for beat in plan["beats"]
                    for transition_id in beat["semantic_transition_ids"]
                ]
                self.assertEqual(scheduled_ids, transition_ids)
                bindings = stem_course.render_runtime_semantic_transition_bindings(plan)
                self.assertEqual(
                    [str(row["planned_transition_id"]) for row in bindings],
                    transition_ids,
                )

                source = stem_course.manim_scene(short, f"LegacyRoute{index}", plan)
                compile(source, f"legacy_route_{index}.py", "exec")
                self.assertIn("self.register_semantic_transition_actions(transition_groups", source)

    def test_divide_sorting_and_counting_cues_are_not_interchangeable(self) -> None:
        counting = short_for("Linear Sorting")
        divide = short_for("Divide and conquer")
        divide_kind = stem_course.infer_visual_kind(divide)
        divide_cues = " ".join((
            stem_course.silent_semantic_cue(divide, divide_kind, "core_idea", "fallback"),
            stem_course.silent_semantic_cue(divide, divide_kind, "example_calculation", "fallback"),
        )).lower()
        self.assertIn("recursion level", divide_cues)
        self.assertIn("accumulate", divide_cues)
        self.assertNotIn("merge", divide_cues)

        sorting = short_for("Sorting")
        sorting_kind = stem_course.infer_visual_kind(sorting)
        sorting_cues = " ".join((
            stem_course.silent_semantic_cue(sorting, sorting_kind, "core_idea", "fallback"),
            stem_course.silent_semantic_cue(sorting, sorting_kind, "example_calculation", "fallback"),
        )).lower()
        self.assertIn("merge", sorting_cues)
        self.assertIn("identity", sorting_cues)
        self.assertNotIn("recursion level", sorting_cues)

        counting_kind = stem_course.infer_visual_kind(counting)
        counting_idea = stem_course.silent_semantic_cue(
            counting,
            counting_kind,
            "core_idea",
            "fallback",
        )
        self.assertIn("bucket", counting_idea.lower())

    def test_transition_beats_cap_static_inspection_tails(self) -> None:
        segmenter = helper_function("semantic_action_hold_segments")
        scheduler = object()
        for topic in LEGACY_TOPICS:
            short = short_for(topic)
            for beat in stem_course.canonical_beat_schedule(short):
                count = int(beat["semantic_transition_count"])
                if not count:
                    continue
                leading, motion, trailing = segmenter(
                    scheduler,
                    float(beat["duration"]),
                    count,
                )
                self.assertAlmostEqual(leading + motion + trailing, float(beat["duration"]))
                self.assertLessEqual(trailing, stem_course.MAX_SEMANTIC_FROZEN_TAIL_SECONDS)
                self.assertGreaterEqual(motion / float(beat["duration"]), 0.60)

    def test_legacy_replay_cycles_are_removed_from_repaired_blocks(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        merge = helpers.split('if mode == "merge":', 1)[1].split('if mode == "stack_push_pop":', 1)[0]
        stack = helpers.split('if mode == "stack_push_pop":', 1)[1].split("row = self.cs_sort_bars", 1)[0]
        hashing = helpers.split('if semantic_family == "hash":', 1)[1].split('if semantic_family == "graph":', 1)[0]
        trees = helpers.split('if semantic_family in {"tree", "avl"}:', 1)[1].split('if semantic_family == "heap":', 1)[0]
        heap = helpers.split('if semantic_family == "heap":', 1)[1].split('if semantic_family == "complexity":', 1)[0]
        complexity = helpers.split('if semantic_family == "complexity":', 1)[1].split('if semantic_family == "_legacy_complexity":', 1)[0]

        for block in (merge, stack, hashing, trees, heap, complexity):
            self.assertIn("register_semantic_transition_actions", block)
            self.assertNotIn("configure_cs_state_cycle", block)
        self.assertEqual(trees.count("def rotate_avl_once"), 1)
        self.assertNotIn("ReplacementTransform(tree", trees)
        self.assertNotIn("register_semantic_actions(actions)", heap)
        self.assertNotIn("register_semantic_actions(actions)", complexity)


if __name__ == "__main__":
    unittest.main()

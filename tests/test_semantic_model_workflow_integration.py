from __future__ import annotations

import unittest

from tools import stem_course
from tools.physics_model_specs import MIT_8_01_TITLE_CONTRACTS
from tools.video_group_models import GROUP_VIDEO_ROUTES, MIT_18_703_CALENDAR_TITLES


def exact_short(title: str, domain: str, index: int = 1) -> dict[str, object]:
    concept = stem_course.authoritative_plan_concept(title, domain)
    short = {
        "index": index,
        "concept": concept.name,
        "hook": concept.hook,
        "intuition": concept.intuition,
        "formula": concept.formula,
        "plain_formula": stem_course.plain_math(concept.formula),
        "prerequisites": concept.prerequisites,
        "misconception": concept.misconception,
        "worked_example": {
            "setup": concept.example_setup,
            "calculation": concept.example_calc,
            "takeaway": stem_course.concise_result_claim(concept.example_takeaway),
        },
        "question_prompt": {
            "question": concept.application_question,
            "answer": concept.application_answer,
        },
        "visual_type": stem_course.routed_concept_visual_type(concept.name, concept.visual_type),
    }
    stem_course.attach_plan_model_identity(short)
    return short


class SemanticModelWorkflowIntegrationTests(unittest.TestCase):
    def test_all_group_titles_have_exact_plan_and_scene_contracts(self) -> None:
        dispatchers = set()
        for index, title in enumerate(MIT_18_703_CALENDAR_TITLES, start=1):
            with self.subTest(title=title):
                short = exact_short(title, "group theory", index)
                plan = stem_course.build_animation_plan(short)
                route = next(route for route in GROUP_VIDEO_ROUTES if route.title == title)
                contract = plan["semantic_transition_contract"]
                self.assertEqual(plan["semantic_support"]["route_key"], route.route_key)
                self.assertEqual(contract["route_key"], route.route_key)
                self.assertTrue(contract["mechanism"])
                self.assertTrue(contract["numeric_evidence_fingerprint"])
                self.assertEqual(len(contract["transitions"]), 4)
                self.assertNotIn("...", " ".join(beat["text"] for beat in plan["beats"]))
                dispatcher = stem_course.VIDEO_RENDERER_IMPLEMENTATIONS[route.route_key]["dispatcher"]
                dispatchers.add(dispatcher)
                scene = stem_course.manim_scene(short, f"GroupScene{index}", plan)
                self.assertIn(route.route_key, scene)
                self.assertIn(dispatcher, scene)
                self.assertIn("play_typed_semantic_contract", scene)
        self.assertEqual(len(dispatchers), len(MIT_18_703_CALENDAR_TITLES))

    def test_all_physics_titles_share_route_mechanism_and_numeric_identity(self) -> None:
        dispatchers = set()
        for contract in MIT_8_01_TITLE_CONTRACTS:
            with self.subTest(title=contract.exact_title):
                short = exact_short(contract.exact_title, "physics", contract.unit_number)
                plan = stem_course.build_animation_plan(short)
                renderer = plan["concrete_example"]["renderer_state"]
                semantic = plan["semantic_transition_contract"]
                self.assertEqual(plan["semantic_support"]["route_key"], contract.video_route_key)
                self.assertEqual(semantic["route_key"], contract.video_route_key)
                self.assertEqual(semantic["mechanism"], ", ".join(renderer["mechanisms"]))
                self.assertEqual(
                    semantic["numeric_evidence_fingerprint"],
                    renderer["numeric_evidence_fingerprint"],
                )
                self.assertEqual(renderer["scenario"], short["model_scenario"])
                dispatcher = stem_course.VIDEO_RENDERER_IMPLEMENTATIONS[contract.video_route_key]["dispatcher"]
                dispatchers.add(dispatcher)
                scene = stem_course.manim_scene(short, f"PhysicsScene{contract.unit_number}", plan)
                self.assertIn(dispatcher, scene)
                self.assertIn(renderer["renderer_variant"], scene)
        self.assertEqual(len(dispatchers), len(MIT_8_01_TITLE_CONTRACTS))

    def test_complete_algorithm_traces_and_formula_cues_survive(self) -> None:
        topics = (
            "Breadth-First Search",
            "Bellman-Ford",
            "Dijkstra's Algorithm",
            "Johnson's Algorithm",
            "Dynamic Programming",
            "Pseudopolynomial Dynamic Programming",
        )
        plans = {}
        for index, topic in enumerate(topics, start=1):
            short = stem_course.concept_to_short(
                stem_course.source_term_concept(topic, "algorithms"), index
            )
            plans[topic] = stem_course.build_animation_plan(short)

        bfs_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Breadth-First Search", "algorithms"), 1
        )
        self.assertEqual(
            plans["Breadth-First Search"]["beats"][1]["text"],
            stem_course.formula_unicode_text(str(bfs_short["formula"])) + ".",
        )
        self.assertEqual(
            plans["Johnson's Algorithm"]["beats"][1]["text"],
            "w'(u, v) = w(u, v) + h(u) - h(v).",
        )
        self.assertEqual(
            stem_course.animation_plan_visible_cue("f(x) = g(x) + h(x)")[0],
            "f(x) = g(x) + h(x).",
        )
        for topic in ("Bellman-Ford", "Dijkstra's Algorithm", "Johnson's Algorithm"):
            plan = plans[topic]
            self.assertGreaterEqual(len(plan["object_roster"]), 3)
            self.assertTrue(plan["concrete_example"]["renderer_state"]["route_events"])
            self.assertEqual(stem_course.animation_plan_contract_errors(plan), [])

        memo = plans["Dynamic Programming"]["concrete_example"]["renderer_state"]
        self.assertEqual(memo["mode"], "fibonacci_memo")
        self.assertTrue({"call", "cache_miss", "store", "return", "cache_hit"}.issubset(
            {event["event"] for event in memo["route_events"]}
        ))
        knapsack = plans["Pseudopolynomial Dynamic Programming"]["concrete_example"]["renderer_state"]
        evidence = knapsack["pseudopolynomial_evidence"]
        self.assertEqual(evidence["baseline"]["table_columns"], evidence["baseline"]["capacity"] + 1)
        self.assertLess(evidence["baseline"]["encoded_bits"], evidence["baseline"]["table_columns"])


if __name__ == "__main__":
    unittest.main()

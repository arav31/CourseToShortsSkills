from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools import stem_course
from tools.video_algebra_models import (
    FIELD_ROUTE_KEY,
    FIELD_VISUAL_KIND,
    IDEAL_ROUTE_KEY,
    IDEAL_VISUAL_KIND,
    RING_ROUTE_KEY,
    RING_VISUAL_KIND,
    algebra_video_route_is_compatible,
    build_algebra_video_payload,
    resolve_algebra_video_model,
    validate_algebra_video_payload,
)


EXPECTED_ROUTES = {
    "Rings": (RING_VISUAL_KIND, RING_ROUTE_KEY, "ring_distributivity"),
    "Ideals": (IDEAL_VISUAL_KIND, IDEAL_ROUTE_KEY, "ideal_absorption_quotient"),
    "Fields": (FIELD_VISUAL_KIND, FIELD_ROUTE_KEY, "field_inverse_division"),
}

EXPECTED_RUNTIME_ROUTES = {
    **EXPECTED_ROUTES,
    "Rings": (
        RING_VISUAL_KIND,
        "modern_algebra:mit_18_703:ring_distributivity",
        "ring_laws_ideals",
    ),
}


def library_short(title: str, index: int = 1) -> dict[str, object]:
    concept = next(concept for concept in stem_course.GROUP_THEORY if concept.name == title)
    return stem_course.concept_to_short(concept, index)


def unsupported_short() -> dict[str, object]:
    return {
        "index": 1,
        "concept": "Unclassified Symbol Shuffle",
        "hook": "A rule moves symbols.",
        "intuition": "Apply the rule repeatedly.",
        "formula": "f(x)",
        "plain_formula": "f(x)",
        "prerequisites": [],
        "visual_type": "numeric_rule",
        "worked_example": {
            "setup": "Start with one symbol.",
            "calculation": "Apply an unnamed rule.",
            "takeaway": "The symbol changes.",
        },
    }


class AlgebraVideoModelTests(unittest.TestCase):
    def test_topic_variants_route_by_structure_without_capturing_specialized_algebra(self) -> None:
        variants = {
            "Ring axioms": RING_VISUAL_KIND,
            "Ideals and quotient rings": IDEAL_VISUAL_KIND,
            "Finite fields": FIELD_VISUAL_KIND,
        }
        for title, visual_kind in variants.items():
            with self.subTest(title=title):
                spec = resolve_algebra_video_model(title, fail_closed=True)
                self.assertEqual(spec.visual_kind, visual_kind)
                concept = stem_course.source_term_concept(title, "group_theory")
                self.assertEqual(concept.visual_type, visual_kind)
                self.assertEqual(
                    stem_course.routed_concept_visual_type(title, "numeric_rule"),
                    visual_kind,
                )

        for title in ("Field extensions", "Polynomial rings", "Unique factorization domains"):
            with self.subTest(specialized=title):
                self.assertIsNone(resolve_algebra_video_model(title))

    def test_exact_mit_titles_resolve_to_dedicated_visuals_and_modes(self) -> None:
        for title, (visual_kind, route_key, mode) in EXPECTED_ROUTES.items():
            with self.subTest(title=title):
                spec = resolve_algebra_video_model(title, fail_closed=True)
                self.assertIsNotNone(spec)
                self.assertEqual(spec.visual_kind, visual_kind)
                self.assertEqual(spec.route_key, route_key)
                self.assertEqual(spec.model_mode, mode)

                short = library_short(title)
                self.assertEqual(short["visual_type"], visual_kind)
                plan = stem_course.build_animation_plan(short)
                runtime_visual, runtime_route, runtime_mode = EXPECTED_RUNTIME_ROUTES[title]
                self.assertEqual(plan["semantic_support"]["visual_kind"], visual_kind)
                self.assertEqual(runtime_visual, visual_kind)
                self.assertEqual(plan["semantic_support"]["route_key"], runtime_route)
                self.assertEqual(plan["semantic_support"]["semantic_mode"], runtime_mode)
                self.assertEqual(plan["semantic_support"]["status"], "supported")
                self.assertTrue(
                    algebra_video_route_is_compatible(title, runtime_route, runtime_mode)
                )

    def test_algebra_route_compatibility_requires_an_exact_key_mode_pair(self) -> None:
        self.assertTrue(
            algebra_video_route_is_compatible(
                "Rings",
                "modern_algebra:mit_18_703:ring_distributivity",
                "ring_laws_ideals",
            )
        )
        self.assertFalse(
            algebra_video_route_is_compatible(
                "Rings",
                "modern_algebra:mit_18_703:ring_distributivity",
                "ring_distributivity",
            )
        )
        self.assertTrue(
            algebra_video_route_is_compatible(
                "Ring axioms", RING_ROUTE_KEY, "ring_distributivity"
            )
        )

    def test_algebra_payloads_carry_complete_identity_snapshots_and_continuity(self) -> None:
        for title in EXPECTED_ROUTES:
            with self.subTest(title=title):
                short = library_short(title)
                payload = build_algebra_video_payload(title, short["worked_example"])
                self.assertEqual(validate_algebra_video_payload(payload), [])
                object_ids = {row["id"] for row in payload["objects"]}
                transitions = payload["transitions"]
                self.assertGreaterEqual(len(transitions), 4)
                for position, transition in enumerate(transitions):
                    self.assertEqual(set(transition["persistent_object_ids"]), object_ids)
                    self.assertEqual(set(transition["before"]), object_ids)
                    self.assertEqual(set(transition["after"]), object_ids)
                    self.assertNotEqual(transition["before"], transition["after"])
                    if position:
                        self.assertEqual(transitions[position - 1]["after"], transition["before"])

                plan = stem_course.build_animation_plan(short)
                self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])
                self.assertEqual(
                    [beat["arc_phase"] for beat in plan["beats"]],
                    ["build", "transform", "transform", "transform", "transform", "resolve"],
                )
                self.assertEqual(plan["contract_metrics"]["domain_state_transformations"], 4)
                for previous, current in zip(plan["beats"], plan["beats"][1:]):
                    handoff_ids = set(current.get("animated_handoff", {}).get("object_ids", []))
                    for object_id in previous["carry"]:
                        self.assertTrue(
                            previous["end_state"][object_id] == current["start_state"][object_id]
                            or object_id in handoff_ids
                        )

    def test_generated_manim_source_compiles_and_consumes_every_algebra_route(self) -> None:
        action_names = {
            "Rings": ("add_closure", "left_product", "distribute", "match_paths"),
            "Ideals": ("select_element", "absorb_product", "collapse_zero", "identify_representatives"),
            "Fields": ("test_candidate", "resolve_division"),
        }
        for index, (title, (_visual, _route_key, _mode)) in enumerate(EXPECTED_ROUTES.items(), start=1):
            with self.subTest(title=title):
                short = library_short(title, index)
                plan = stem_course.build_animation_plan(short)
                source = stem_course.manim_scene(short, f"{title}RouteScene", plan)
                compile(source, f"generated_{title.lower()}_scene.py", "exec")
                _runtime_visual, route_key, mode = EXPECTED_RUNTIME_ROUTES[title]
                self.assertIn(f"route_key={route_key}", source.splitlines()[0])
                self.assertIn(repr(mode), source)
                self.assertIn("play_algebra_semantic_visual", source)
                self.assertIn("algebra_register_transition_actions", source)
                self.assertIn("register_semantic_transition_actions(groups)", source)
                for transition in plan["semantic_transition_contract"]["transitions"]:
                    self.assertIn(str(transition["id"]), source)
                for action_name in action_names[title]:
                    self.assertIn("def " + action_name, source)
                if title == "Rings":
                    self.assertIn("'payload_type': 'group_theory'", source)
                    self.assertIn("play_typed_semantic_contract(group_payload)", source)

    def test_existing_group_route_remains_registered_and_compilable(self) -> None:
        short = stem_course.concept_to_short(stem_course.GROUP_THEORY[0], 1)
        plan = stem_course.build_animation_plan(short)
        self.assertEqual(short["visual_type"], "group_structure")
        self.assertEqual(plan["semantic_support"]["route_key"], "group_structure")
        source = stem_course.manim_scene(short, "PreservedGroupRouteScene", plan)
        compile(source, "generated_group_route_scene.py", "exec")
        self.assertIn("play_group_visual", source)


class NumericRuleFailClosedTests(unittest.TestCase):
    def test_build_rejects_unsupported_numeric_rule_before_scene_generation(self) -> None:
        short = unsupported_short()
        with self.assertRaisesRegex(ValueError, "Unsupported numeric_rule route"):
            stem_course.build_animation_plan(short)

    def test_storyboard_stops_without_writing_a_scene_or_plan_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run = Path(temporary_directory)
            (run / "short_plan.json").write_text(
                json.dumps({"course_title": "Synthetic", "shorts": [unsupported_short()]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Unsupported numeric_rule route"):
                stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            self.assertFalse((run / stem_course.ANIMATION_PLAN_INDEX_NAME).exists())
            self.assertFalse((run / "scenes").exists())

    def test_manim_rejects_a_forged_numeric_rule_plan(self) -> None:
        valid_short = library_short("Rings")
        forged_plan = stem_course.build_animation_plan(valid_short)
        with self.assertRaisesRegex(ValueError, "valid animation plan"):
            stem_course.manim_scene(
                unsupported_short(),
                "UnsupportedNumericRuleScene",
                forged_plan,
            )


if __name__ == "__main__":
    unittest.main()

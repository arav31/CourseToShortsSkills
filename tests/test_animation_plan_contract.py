from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course
from tools.validate_course_run import (
    ANIMATION_PLAN_SCHEMA_VERSION,
    CourseRunValidator,
    GENERIC_VISUAL_TYPES,
    RENDER_RUNTIME_TRACE_NAME,
    RENDER_RUNTIME_TRACE_SCHEMA_VERSION,
    canonical_json_hash,
    planned_state_change_contracts,
)


def short_from_concept(concept: stem_course.Concept, index: int = 1) -> dict[str, object]:
    return {
        "index": index,
        "concept": concept.name,
        "hook": concept.hook,
        "intuition": concept.intuition,
        "formula": concept.formula,
        "plain_formula": stem_course.plain_math(concept.formula),
        "prerequisites": concept.prerequisites,
        "visual_type": concept.visual_type,
        "worked_example": {
            "setup": concept.example_setup,
            "calculation": concept.example_calc,
            "takeaway": concept.example_takeaway,
        },
        "question_prompt": {
            "question": concept.application_question,
            "answer": concept.application_answer,
        },
    }


def course_plan(shorts: list[dict[str, object]]) -> dict[str, object]:
    return {"course_title": "Cross-domain fixture", "source_url": "fixture://course", "shorts": shorts}


class AnimationPlanContractTests(unittest.TestCase):
    def domain_cases(self) -> list[tuple[str, stem_course.Concept, str]]:
        return [
            ("group theory", stem_course.GROUP_THEORY[0], "algebra-and-groups"),
            ("linear algebra", stem_course.LINEAR_ALGEBRA[2], "linear-algebra"),
            ("algorithms", stem_course.ALGORITHMS[2], "algorithms-and-cs"),
            ("physics", stem_course.PHYSICS_MECHANICS[0], "physics"),
            ("economics", stem_course.ECONOMICS[0], "economics"),
        ]

    def test_cross_domain_plans_satisfy_visual_story_contract(self) -> None:
        self.assertTrue(set(stem_course.CS_VISUAL_KINDS).issubset(stem_course.ANIMATION_CS_KINDS))
        self.assertTrue(set(stem_course.PHYSICS_VISUAL_KINDS).issubset(stem_course.ANIMATION_PHYSICS_KINDS))
        self.assertEqual(stem_course.MISSING_STATIC_ANIMATION_ROUTES, set())
        self.assertEqual(stem_course.MISSING_CS_ANIMATION_ROUTES, set())
        actions_by_domain: dict[str, tuple[str, ...]] = {}
        for index, (domain, concept, expected_family) in enumerate(self.domain_cases(), start=1):
            with self.subTest(domain=domain):
                short = short_from_concept(concept, index)
                plan = stem_course.build_animation_plan(short)
                self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])
                self.assertEqual(plan["semantic_support"]["family"], expected_family)
                self.assertEqual(plan["semantic_support"]["status"], "supported")
                beats = plan["beats"]
                self.assertGreaterEqual(len(beats), 5)
                self.assertLessEqual(len(beats), 8)
                self.assertEqual(
                    [beat["arc_phase"] for beat in beats],
                    ["build", "transform", "transform", "transform", "transform", "resolve"],
                )
                self.assertEqual(sum(bool(beat["domain_state_change"]) for beat in beats), 4)
                self.assertFalse(beats[0]["domain_state_change"])
                self.assertFalse(beats[-1]["domain_state_change"])
                self.assertTrue(all(beat["state_delta"]["before"] for beat in beats))
                self.assertTrue(all(beat["state_delta"]["after"] for beat in beats))
                self.assertGreaterEqual(sum(bool(beat["active_objects"]) for beat in beats) / len(beats), 0.70)
                self.assertFalse(any(beat["full_reset"] for beat in beats))
                for left, right in zip(beats, beats[1:]):
                    self.assertTrue(set(left["carry"]).intersection(right["active_objects"]))
                    handoff_ids = set(right.get("animated_handoff", {}).get("object_ids", []))
                    for object_id in left["carry"]:
                        self.assertTrue(
                            left["end_state"][object_id] == right["start_state"][object_id]
                            or object_id in handoff_ids
                        )
                self.assertTrue(all(1 <= len(beat["cue_lines"]) <= 2 for beat in beats))
                actions_by_domain[domain] = tuple(str(beat["action"]) for beat in beats)

        self.assertEqual(len(set(actions_by_domain.values())), len(actions_by_domain))

    def test_structured_animated_handoff_is_the_only_state_chain_escape(self) -> None:
        short = short_from_concept(stem_course.GROUP_THEORY[0])
        plan = stem_course.build_animation_plan(short)
        previous = plan["beats"][0]
        current = plan["beats"][1]
        object_id = previous["carry"][0]
        target_state = "explicitly animated transform input"
        current["start_state"][object_id] = target_state
        current["state_delta"]["before"][object_id] = target_state
        current["state_delta"]["changed_object_ids"] = [
            key
            for key in current["start_state"]
            if current["start_state"].get(key) != current["end_state"].get(key)
        ]
        current["animated_handoff"] = {
            "object_ids": [object_id],
            "from_state": {object_id: previous["end_state"][object_id]},
            "to_state": {object_id: target_state},
            "action": "Morph the carried object into the next input state.",
        }

        self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])

        broken = json.loads(json.dumps(plan))
        del broken["beats"][1]["animated_handoff"]
        self.assertTrue(
            any(
                "breaks carried state" in error
                for error in stem_course.animation_plan_contract_errors(broken, short)
            )
        )

    def test_transform_delta_and_final_resolve_fail_closed(self) -> None:
        short = short_from_concept(stem_course.GROUP_THEORY[0])
        plan = stem_course.build_animation_plan(short)

        missing_delta = json.loads(json.dumps(plan))
        missing_delta["beats"][2]["state_delta"] = {}
        self.assertTrue(
            any(
                "nonempty structured state_delta" in error
                for error in stem_course.animation_plan_contract_errors(missing_delta, short)
            )
        )

        only_three = json.loads(json.dumps(plan))
        demoted = only_three["beats"][2]
        demoted["arc_phase"] = "hold"
        demoted["end_state"] = dict(demoted["start_state"])
        demoted["state_delta"] = {
            "before": dict(demoted["start_state"]),
            "after": dict(demoted["start_state"]),
            "changed_object_ids": [],
        }
        demoted["domain_state_change"] = False
        only_three["contract_metrics"]["domain_state_transformations"] = 3
        self.assertTrue(
            any(
                "at least 4 transform deltas" in error
                for error in stem_course.animation_plan_contract_errors(only_three, short)
            )
        )

        bypassed_resolve = json.loads(json.dumps(plan))
        last_transform = bypassed_resolve["beats"][-2]
        resolve = bypassed_resolve["beats"][-1]
        object_id = last_transform["state_delta"]["changed_object_ids"][0]
        replacement = "different resolve input"
        resolve["start_state"][object_id] = replacement
        resolve["state_delta"]["before"][object_id] = replacement
        resolve["state_delta"]["changed_object_ids"] = [
            key
            for key in resolve["start_state"]
            if resolve["start_state"].get(key) != resolve["end_state"].get(key)
        ]
        resolve["animated_handoff"] = {
            "object_ids": [object_id],
            "from_state": {object_id: last_transform["end_state"][object_id]},
            "to_state": {object_id: replacement},
            "action": "Animate away from the transformed state before resolving.",
        }
        self.assertTrue(
            any(
                "final resolve must consume" in error
                for error in stem_course.animation_plan_contract_errors(bypassed_resolve, short)
            )
        )

    def test_animation_plan_rejects_dense_or_three_line_visible_cues(self) -> None:
        short = short_from_concept(stem_course.GROUP_THEORY[0])
        plan = stem_course.build_animation_plan(short)

        three_lines = json.loads(json.dumps(plan))
        three_lines["beats"][0]["text"] = "first line second line third line"
        three_lines["beats"][0]["cue_lines"] = ["first line", "second line", "third line"]
        self.assertTrue(
            any(
                "one or two nonempty lines" in error
                for error in stem_course.animation_plan_contract_errors(three_lines, short)
            )
        )

        dense = json.loads(json.dumps(plan))
        dense_words = ["a"] * (stem_course.ANIMATION_PLAN_MAX_CUE_WORDS + 1)
        dense["beats"][0]["text"] = " ".join(dense_words)
        dense["beats"][0]["cue_lines"] = [
            " ".join(dense_words[:13]),
            " ".join(dense_words[13:]),
        ]
        self.assertTrue(
            any(
                "exceeds the text budget" in error
                for error in stem_course.animation_plan_contract_errors(dense, short)
            )
        )

    def test_route_plans_are_specific_within_cs_physics_and_economics(self) -> None:
        bfs = short_from_concept(stem_course.ALGORITHMS[2])
        heap = stem_course.concept_to_short(stem_course.source_term_concept("Priority Queue", "algorithms"), 2)
        force = short_from_concept(stem_course.PHYSICS_MECHANICS[0])
        potential = stem_course.concept_to_short(stem_course.source_term_concept("Potential Energy Diagrams", "physics"), 2)
        market = short_from_concept(stem_course.ECONOMICS[0])
        elasticity = short_from_concept(stem_course.ECONOMICS[1], 2)

        pairs = ((bfs, heap), (force, potential), (market, elasticity))
        for left_short, right_short in pairs:
            left = stem_course.build_animation_plan(left_short)
            right = stem_course.build_animation_plan(right_short)
            with self.subTest(left=left_short["concept"], right=right_short["concept"]):
                self.assertNotEqual(left["semantic_support"]["route_key"], right["semantic_support"]["route_key"])
                self.assertNotEqual(
                    [item["role"] for item in left["object_roster"]],
                    [item["role"] for item in right["object_roster"]],
                )
                self.assertNotEqual(
                    [beat["action"] for beat in left["beats"]],
                    [beat["action"] for beat in right["beats"]],
                )
                self.assertNotEqual(left["invariant"]["statement"], right["invariant"]["statement"])
                self.assertNotEqual(
                    left["concrete_example"]["renderer_state"],
                    right["concrete_example"]["renderer_state"],
                )

        self.assertEqual(stem_course.build_animation_plan(bfs)["semantic_support"]["route_key"], "cs:graph:bfs")
        self.assertEqual(stem_course.build_animation_plan(heap)["semantic_support"]["route_key"], "cs:heap")

    def test_supported_video_routes_equal_registered_implementations(self) -> None:
        expected_visual_kinds = (
            {"matrix_vector", "vector_components", "linear_combination"}
            | stem_course.ANIMATION_GROUP_KINDS
            | stem_course.ANIMATION_CS_KINDS
            | stem_course.ANIMATION_STATE_MACHINE_KINDS
            | stem_course.ANIMATION_PHYSICS_KINDS
            | stem_course.ANIMATION_ECON_KINDS
            | stem_course.ANIMATION_CALCULUS_KINDS
            | stem_course.ANIMATION_PROBABILITY_KINDS
            | stem_course.ANIMATION_CHEMISTRY_KINDS
            | stem_course.ANIMATION_GEOMETRY_KINDS
        )
        self.assertEqual(
            stem_course.VIDEO_SUPPORTED_ROUTE_KEYS,
            frozenset(stem_course.VIDEO_RENDERER_IMPLEMENTATIONS),
        )
        self.assertEqual(
            stem_course.ANIMATION_SUPPORTED_VISUAL_KINDS,
            frozenset(
                implementation["visual_kind"]
                for implementation in stem_course.VIDEO_RENDERER_IMPLEMENTATIONS.values()
            ),
        )
        self.assertEqual(stem_course.ANIMATION_SUPPORTED_VISUAL_KINDS, expected_visual_kinds)
        self.assertTrue(stem_course.VIDEO_SUPPORTED_ROUTE_KEYS.issubset(stem_course.ANIMATION_ROUTE_BLUEPRINTS))

        for concept_name in ("Projection", "Positive definite matrices", "Determinants"):
            with self.subTest(concept=concept_name):
                concept = next(concept for concept in stem_course.LINEAR_ALGEBRA if concept.name == concept_name)
                short = short_from_concept(concept)
                plan = stem_course.build_animation_plan(short)
                route_key = plan["semantic_support"]["route_key"]
                self.assertNotIn(route_key, stem_course.VIDEO_RENDERER_IMPLEMENTATIONS)
                self.assertEqual(plan["semantic_support"]["status"], "unsupported")
                self.assertIn("no video renderer implementation", plan["semantic_support"]["unsupported_reason"])
                with self.assertRaisesRegex(ValueError, "valid animation plan"):
                    stem_course.manim_scene(short, "UnsupportedAlias", plan)

    def test_graph_and_dp_plans_are_grounded_in_exact_renderer_modes(self) -> None:
        expectations = {
            "Depth-First Search": ("cs:graph:dfs", "active root-to-current path", "active stack"),
            "Topological Sort": ("cs:graph:topological", "indegree zero", "release"),
            "Bellman-Ford": ("cs:graph:bellman_ford", "after pass k", "Relax"),
            "Dijkstra's Algorithm": ("cs:graph:dijkstra", "settled distances", "Relax"),
            "Johnson's Algorithm": ("cs:graph:johnson", "potential terms telescope", "algorithm state"),
            "Dynamic Programming State Design": ("cs:dp:grid_paths", "entering from above", "from above"),
            "Dynamic Programming Applications": ("cs:dp:matrix_chain", "cheapest value", "split costs"),
            "Pseudopolynomial Dynamic Programming": ("cs:dp:knapsack", "at most once", "exclude"),
        }
        route_keys = set()
        for index, (topic, (route_key, invariant_fragment, action_fragment)) in enumerate(expectations.items(), start=1):
            with self.subTest(topic=topic):
                short = stem_course.concept_to_short(stem_course.source_term_concept(topic, "algorithms"), index)
                plan = stem_course.build_animation_plan(short)
                renderer_state = plan["concrete_example"]["renderer_state"]
                route_keys.add(plan["semantic_support"]["route_key"])

                self.assertEqual(plan["semantic_support"]["route_key"], route_key)
                self.assertEqual(plan["invariant"]["statement"], renderer_state["invariant"])
                self.assertIn(invariant_fragment, plan["invariant"]["statement"].lower())
                self.assertTrue(any(action_fragment.lower() in beat["action"].lower() for beat in plan["beats"][1:5]))
                self.assertTrue(plan["semantic_transition_contract"]["transitions"])
                self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])
                if topic == "Johnson's Algorithm":
                    trace = renderer_state["animation_trace"]
                    self.assertEqual(trace["super_source"], "q")
                    self.assertTrue(trace["potential_trace"]["route_events"])
                    self.assertEqual(set(trace["dijkstra_traces"]), set(renderer_state["nodes"]))
                    self.assertTrue(trace["unweight_steps"])

        self.assertEqual(len(route_keys), len(expectations))

    def test_scene_schedule_preserves_semantic_transition_ids(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Dynamic Programming Applications", "algorithms"),
            1,
        )
        plan = stem_course.build_animation_plan(short)
        schedule = stem_course.animation_plan_scene_schedule(short, plan)

        scheduled_ids = [
            transition_id
            for beat in schedule
            for transition_id in beat["semantic_transition_ids"]
        ]
        planned_ids = [
            transition_id
            for beat in plan["beats"]
            for transition_id in beat["semantic_transition_ids"]
        ]
        self.assertEqual(scheduled_ids, planned_ids)
        self.assertEqual(len(scheduled_ids), len(set(scheduled_ids)))

    def test_split_scene_stages_tile_the_exact_storyboard_window(self) -> None:
        short = short_from_concept(stem_course.GROUP_THEORY[0])
        short["hook"] = (
            "The operation combines two elements inside the same carrier. "
            "The identity keeps neutral motion visible. "
            "Inverses keep every move reversible. "
            "Associativity keeps regrouping consistent."
        )
        plan = stem_course.build_animation_plan(short)

        schedule = stem_course.animation_plan_scene_schedule(short, plan)
        idea = [beat for beat in schedule if beat["scene_state"] == "hook"]
        planned = next(beat for beat in plan["beats"] if beat["scene_state"] == "hook")

        self.assertGreater(len(idea), 1)
        self.assertTrue(all(stem_course.complete_visible_prose_stage(beat["text"]) for beat in idea))
        self.assertTrue(all(beat["animation_plan_beat_id"] == planned["id"] for beat in idea))
        self.assertTrue(idea[0]["planned_state_first_stage"])
        self.assertTrue(idea[-1]["planned_state_last_stage"])
        self.assertEqual(idea[0]["planned_stage_window_seconds"][0], planned["start_seconds"])
        self.assertEqual(idea[-1]["planned_stage_window_seconds"][1], planned["end_seconds"])
        for left, right in zip(idea, idea[1:]):
            self.assertAlmostEqual(
                left["planned_stage_window_seconds"][1],
                right["planned_stage_window_seconds"][0],
            )

    def test_semantic_plan_mutations_fail_closed(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Johnson's Algorithm", "algorithms"),
            1,
        )
        plan = stem_course.build_animation_plan(short)

        mutations = []
        changed_claim = json.loads(json.dumps(plan))
        changed_claim["beats"][1]["claim"] = "Sort an unrelated array."
        mutations.append(changed_claim)

        changed_evidence = json.loads(json.dumps(plan))
        changed_evidence["beats"][1]["evidence"]["expected_change"] = "Fill a knapsack cell."
        mutations.append(changed_evidence)

        changed_transition = json.loads(json.dumps(plan))
        changed_transition["beats"][1]["semantic_transition_ids"][0] = "unrelated:1"
        mutations.append(changed_transition)

        changed_object = json.loads(json.dumps(plan))
        changed_object["beats"][1]["evidence"]["persistent_object_ids"] = ["graph:topology"]
        mutations.append(changed_object)

        changed_state = json.loads(json.dumps(plan))
        first_transition = plan["semantic_transition_contract"]["transitions"][0]
        object_id = next(iter(first_transition["before"]))
        changed_state["beats"][1]["start_state"][object_id] = "999"
        mutations.append(changed_state)

        changed_contract = json.loads(json.dumps(plan))
        changed_contract["semantic_transition_contract"]["transitions"][0]["after"] = {object_id: "999"}
        mutations.append(changed_contract)

        changed_qa = json.loads(json.dumps(plan))
        changed_qa["qa_evidence_timestamps"][1]["expected_change"] = "Unrelated QA claim."
        mutations.append(changed_qa)

        for position, mutated in enumerate(mutations, start=1):
            with self.subTest(mutation=position):
                self.assertTrue(stem_course.animation_plan_contract_errors(mutated, short))

    def test_state_machine_requires_a_concrete_automaton(self) -> None:
        concrete = {
            "index": 1,
            "concept": "Finite state automaton",
            "hook": "A finite automaton carries one state token through labeled transitions.",
            "intuition": "The same token follows the edge selected by each input symbol.",
            "formula": r"\delta(q_0,1)=q_1",
            "plain_formula": "delta(q0, 1) = q1",
            "visual_type": "state_machine",
            "worked_example": {
                "setup": "Use states q0 and q1; start at q0 with input 1.",
                "calculation": "On input 1, transition q0 -> q1; q1 is accepting.",
                "takeaway": "The input moves the persistent token to q1.",
            },
            "question_prompt": {"question": "Where does input 1 go?", "answer": "It reaches q1."},
        }
        generic = {
            **concrete,
            "concept": "Workflow state",
            "hook": "A process changes state over time.",
            "intuition": "Status can change.",
            "worked_example": {
                "setup": "A process begins with one status and later changes.",
                "calculation": "The status changes after an event.",
                "takeaway": "The process has a new status.",
            },
        }

        concrete_plan = stem_course.build_animation_plan(concrete)
        generic_plan = stem_course.build_animation_plan(generic)
        self.assertEqual(concrete_plan["semantic_support"]["route_key"], "state_machine:automaton")
        self.assertEqual(concrete_plan["semantic_support"]["status"], "supported")
        self.assertEqual(stem_course.animation_plan_contract_errors(concrete_plan, concrete), [])
        self.assertEqual(generic_plan["semantic_support"]["route_key"], "state_machine:generic")
        self.assertEqual(generic_plan["semantic_support"]["status"], "unsupported")
        self.assertTrue(stem_course.animation_plan_contract_errors(generic_plan, generic))
        self.assertNotIn("state_machine", GENERIC_VISUAL_TYPES)

    def test_storyboard_writes_index_and_manim_consumes_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="animation-contract-") as tmp:
            run = Path(tmp)
            short = short_from_concept(stem_course.GROUP_THEORY[0])
            stem_course.write_json(run / "short_plan.json", course_plan([short]))

            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            index_path = run / stem_course.ANIMATION_PLAN_INDEX_NAME
            artifact_path = run / stem_course.animation_plan_relative_path(1)
            self.assertTrue(index_path.exists())
            self.assertTrue(artifact_path.exists())

            stem_course.cmd_manim(argparse.Namespace(run=str(run)))
            updated = stem_course.read_json(run / "short_plan.json")
            scene = run / str(updated["shorts"][0]["scene_file"])
            source = scene.read_text(encoding="utf-8")
            artifact = stem_course.read_json(artifact_path)
            self.assertIn(f"animation_plan_fingerprint={stem_course.animation_plan_fingerprint(artifact)}", source)
            self.assertIn("self._planned_objects", source)
            self.assertIn("self._continuity_spine_ids", source)
            self.assertIn("planned_action", source)

    def test_stale_manim_helper_fingerprint_is_rejected_before_render(self) -> None:
        short = short_from_concept(stem_course.GROUP_THEORY[0])
        plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "RendererFingerprintScene", plan)
        metadata = stem_course.generated_scene_metadata(source)

        self.assertEqual(metadata["renderer_source_fingerprint"], stem_course.renderer_source_fingerprint())
        self.assertEqual(stem_course.generated_scene_contract_errors(source, plan), [])
        with tempfile.TemporaryDirectory(prefix="renderer-fingerprint-") as tmp:
            scene = Path(tmp) / "scene.py"
            scene.write_text(source, encoding="utf-8")
            self.assertEqual(stem_course.require_current_generated_scene(scene, plan), source)
            with mock.patch.object(
                stem_course,
                "MANIM_SCENE_HELPERS",
                stem_course.MANIM_SCENE_HELPERS + "\n# changed shared renderer helper\n",
            ):
                self.assertTrue(
                    any(
                        "renderer-source fingerprint is stale" in error
                        for error in stem_course.generated_scene_contract_errors(source, plan)
                    )
                )
                with self.assertRaisesRegex(RuntimeError, "renderer-source fingerprint is stale"):
                    stem_course.require_current_generated_scene(scene, plan)

            run = Path(tmp) / "run"
            run.mkdir()
            stem_course.write_json(run / "short_plan.json", course_plan([short]))
            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            stem_course.cmd_manim(argparse.Namespace(run=str(run)))
            with mock.patch.object(
                stem_course,
                "MANIM_SCENE_HELPERS",
                stem_course.MANIM_SCENE_HELPERS + "\n# changed before cmd_render\n",
            ):
                with self.assertRaisesRegex(SystemExit, "renderer-source fingerprint is stale"):
                    stem_course.cmd_render(
                        argparse.Namespace(run=str(run), quality="preview", voice_engine="none")
                    )

    def test_manim_rejects_missing_and_invalid_animation_plans(self) -> None:
        with tempfile.TemporaryDirectory(prefix="animation-contract-") as tmp:
            run = Path(tmp)
            short = short_from_concept(stem_course.LINEAR_ALGEBRA[2])
            stem_course.write_json(run / "short_plan.json", course_plan([short]))
            with self.assertRaises(SystemExit):
                stem_course.cmd_manim(argparse.Namespace(run=str(run)))

            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            artifact_path = run / stem_course.animation_plan_relative_path(1)
            artifact = stem_course.read_json(artifact_path)
            artifact["beats"][1]["active_objects"] = []
            stem_course.write_json(artifact_path, artifact)
            with self.assertRaises(SystemExit):
                stem_course.cmd_manim(argparse.Namespace(run=str(run)))

    def test_numeric_rule_fails_before_an_animation_plan_is_built(self) -> None:
        short = {
            "index": 1,
            "concept": "Unclassified relation",
            "hook": "A relation changes one exact input into one exact output.",
            "intuition": "The operation needs a real semantic renderer before publication.",
            "formula": "y=2x+1",
            "plain_formula": "y = 2x + 1",
            "visual_type": "numeric_rule",
            "worked_example": {
                "setup": "Use x=3 in y=2x+1.",
                "calculation": "y=2(3)+1=7.",
                "takeaway": "The exact input maps to 7.",
            },
            "question_prompt": {"question": "What happens at x=4?", "answer": "The result is 9."},
        }
        with self.assertRaisesRegex(ValueError, "Unsupported numeric_rule route"):
            stem_course.build_animation_plan(short)
        self.assertNotIn("numeric_rule", stem_course.ANIMATION_SUPPORTED_VISUAL_KINDS)

    def test_validator_strict_fails_missing_or_stale_plan_while_draft_warns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="animation-contract-") as tmp:
            run = Path(tmp)
            short = short_from_concept(stem_course.ALGORITHMS[2])
            plan = course_plan([short])
            stem_course.write_json(run / "short_plan.json", plan)

            strict = CourseRunValidator(run)
            strict.validate_animation_plans(plan)
            self.assertTrue(any(issue.severity == "FAIL" and issue.area == "animation-plan.missing" for issue in strict.issues))

            draft = CourseRunValidator(run, draft=True)
            draft.validate_animation_plans(plan)
            self.assertFalse(any(issue.severity == "FAIL" for issue in draft.issues))
            self.assertTrue(any(issue.severity == "WARN" and issue.area == "animation-plan.missing" for issue in draft.issues))

            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            current = stem_course.read_json(run / "short_plan.json")
            current["shorts"][0]["hook"] = "A changed hook invalidates the storyboard source hash."
            stem_course.write_json(run / "short_plan.json", current)
            stale = CourseRunValidator(run)
            stale.validate_animation_plans(current)
            self.assertTrue(any(issue.severity == "FAIL" and issue.area == "animation-plan.stale" for issue in stale.issues))

    def test_validator_accepts_current_producer_schema_and_rejects_stale_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="animation-schema-") as tmp:
            run = Path(tmp)
            short = short_from_concept(stem_course.ALGORITHMS[2])
            stem_course.write_json(run / "short_plan.json", course_plan([short]))
            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            current = stem_course.read_json(run / "short_plan.json")

            self.assertEqual(ANIMATION_PLAN_SCHEMA_VERSION, stem_course.ANIMATION_PLAN_SCHEMA_VERSION)
            accepted = CourseRunValidator(run)
            accepted.validate_animation_plans(current)
            self.assertEqual(
                [issue for issue in accepted.issues if issue.severity == "FAIL" and issue.area.startswith("animation-plan")],
                [],
            )

            stale_version = "course-animation-plan-stale-fixture"
            artifact_path = run / str(current["shorts"][0]["animation_plan_file"])
            artifact = stem_course.read_json(artifact_path)
            artifact["schema_version"] = stale_version
            stem_course.write_json(artifact_path, artifact)
            index_path = run / stem_course.ANIMATION_PLAN_INDEX_NAME
            index_payload = stem_course.read_json(index_path)
            index_payload["schema_version"] = stale_version
            stem_course.write_json(index_path, index_payload)

            rejected = CourseRunValidator(run)
            rejected.validate_animation_plans(current)
            self.assertTrue(
                any(
                    issue.severity == "FAIL"
                    and issue.area == "animation-plan.index"
                    and ANIMATION_PLAN_SCHEMA_VERSION in issue.message
                    for issue in rejected.issues
                )
            )
            self.assertTrue(
                any(
                    issue.severity == "FAIL"
                    and issue.area == "animation-plan.invalid"
                    and ANIMATION_PLAN_SCHEMA_VERSION in issue.message
                    for issue in rejected.issues
                )
            )

    def test_validator_fails_when_notes_sources_and_pdf_are_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="missing-notes-") as tmp:
            validator = CourseRunValidator(Path(tmp))

            validator.validate_notes()

            failures = {(issue.area, issue.severity) for issue in validator.issues}
            self.assertIn(("notes", "FAIL"), failures)
            self.assertIn(("notes.pdf", "FAIL"), failures)

    def test_all_runs_storyboard_between_plan_and_manim(self) -> None:
        calls: list[str] = []

        def record(name: str):
            return lambda _args: calls.append(name)

        args = argparse.Namespace(
            url="fixture://course",
            out="/private/tmp/animation-plan-all-fixture",
            sample=None,
            max_pages=1,
            max_pdfs=1,
            max_shorts=1,
            no_pdf=True,
            pdf_engine="none",
            no_render=True,
            quality="preview",
            voice_engine="none",
            playlist=None,
            public_base_url=None,
        )
        with (
            mock.patch.object(stem_course, "cmd_extract", record("extract")),
            mock.patch.object(stem_course, "cmd_plan", record("plan")),
            mock.patch.object(stem_course, "cmd_storyboard", record("storyboard")),
            mock.patch.object(stem_course, "cmd_notes", record("notes")),
            mock.patch.object(stem_course, "cmd_manim", record("manim")),
        ):
            stem_course.cmd_all(args)

        self.assertEqual(calls, ["extract", "plan", "storyboard", "notes", "manim"])


class VisualReviewContractTests(unittest.TestCase):
    def create_rendered_fixture(self, root: Path) -> dict[str, object]:
        short = short_from_concept(stem_course.ALGORITHMS[2])
        stem_course.write_json(root / "short_plan.json", course_plan([short]))
        stem_course.cmd_storyboard(argparse.Namespace(run=str(root)))
        plan = stem_course.read_json(root / "short_plan.json")
        video_file = f"videos/short_01_{stem_course.slugify(str(short['concept']))}_final.mp4"
        video = root / video_file
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"review-fixture-video" * 1024)
        plan["shorts"][0]["video_file"] = video_file
        plan["shorts"][0]["target_duration_seconds"] = 30.0
        stem_course.write_json(root / "short_plan.json", plan)
        stem_course.cmd_visual_review(argparse.Namespace(run=str(root)))
        return stem_course.read_json(root / "short_plan.json")

    def animation_plan_and_contracts(self, root: Path, review: dict[str, object]) -> tuple[dict[str, object], list[dict[str, object]]]:
        plan_file = str(review.get("animation_plan_file") or "animation_plans/short_01.json")
        animation_plan = stem_course.read_json(root / plan_file)
        contracts = planned_state_change_contracts(animation_plan)
        self.assertGreaterEqual(len(contracts), 4)
        return animation_plan, contracts

    def write_runtime_trace(
        self,
        root: Path,
        review: dict[str, object],
        contracts: list[dict[str, object]],
    ) -> None:
        index_payload = stem_course.read_json(root / stem_course.ANIMATION_PLAN_INDEX_NAME)
        semantic_events = []
        semantic_bindings = []
        for contract in contracts:
            before_seconds = float(contract["before_seconds"])
            after_seconds = float(contract["after_seconds"])
            transition_id = str(contract["planned_transition_id"])
            semantic_events.append(
                {
                    **contract,
                    "renderer_markers": [
                        {"phase": "before", "renderer_seconds": before_seconds},
                        {"phase": "after", "renderer_seconds": after_seconds},
                    ],
                    "execution_records": [
                        {
                            "kind": "callback",
                            "callback_name": "fixture_transform",
                            "declared_transition_id": transition_id,
                            "started_seconds": before_seconds,
                            "finished_seconds": after_seconds,
                            "choreography_intervals": [
                                {
                                    "started_frame": round(before_seconds * stem_course.RENDER_TIMELINE_FPS),
                                    "finished_frame": round(after_seconds * stem_course.RENDER_TIMELINE_FPS),
                                    "frame_count": max(
                                        1,
                                        round((after_seconds - before_seconds) * stem_course.RENDER_TIMELINE_FPS),
                                    ),
                                    "animation_types": ["Transform"],
                                    "persistent_carrier_ids": contract["persistent_object_ids"],
                                    "carrier_type": "displacement",
                                    "semantic_before": contract["observed_before"],
                                    "semantic_after": contract["observed_after"],
                                    "qualifying_motion": True,
                                }
                            ],
                            "status": "ok",
                        }
                    ],
                    "timing_source": "manim.renderer.time",
                }
            )
            semantic_bindings.append(
                {
                    "beat_id": contract["beat_id"],
                    "planned_transition_id": transition_id,
                    "registered_callback_count": 1,
                    "executed_callback_count": 1,
                    "successful_callback_count": 1,
                    "status": "ok",
                }
            )
        stem_course.write_json(
            root / RENDER_RUNTIME_TRACE_NAME,
            {
                "schema_version": RENDER_RUNTIME_TRACE_SCHEMA_VERSION,
                "animation_plan_index_fingerprint": canonical_json_hash(index_payload),
                "renders": [
                    {
                        "short_index": review["short_index"],
                        "video_file": review["video_file"],
                        "video_sha256": review["video_sha256"],
                        "animation_plan_fingerprint": review["animation_plan_fingerprint"],
                        "transitions": [],
                        "semantic_transition_events": semantic_events,
                        "semantic_transition_bindings": semantic_bindings,
                    }
                ],
            },
        )

    def complete_review(self, root: Path, *, include_runtime_trace: bool = True) -> None:
        path = root / stem_course.VISUAL_REVIEW_NAME
        payload = json.loads(path.read_text(encoding="utf-8"))
        review = payload["reviews"][0]
        _, contracts = self.animation_plan_and_contracts(root, review)
        checkpoint_notes = {
            "opening": "The blue graph topology and start node appear together.",
            "pre_action": "The same frontier remains visible before the dequeue step.",
            "post_action": "The processed node changes while the graph identity persists.",
            "intermediate": "The queue marker advances across the unchanged graph topology.",
            "final": "The completed traversal remains attached to the original graph.",
        }
        for checkpoint in review["checkpoints"]:
            checkpoint["observation"] = checkpoint_notes[checkpoint["role"]]
        review["observed_state_changes"] = [
            {
                "beat_id": contract["beat_id"],
                "planned_transition_id": contract["planned_transition_id"],
                "before_frame": f"{review['video_file']}#t={contract['before_seconds']:.2f}s",
                "after_frame": f"{review['video_file']}#t={contract['after_seconds']:.2f}s",
                "persistent_object_ids": contract["persistent_object_ids"],
                "changed_attribute": contract["changed_attribute"],
                "observed_before": contract["observed_before"],
                "observed_after": contract["observed_after"],
            }
            for contract in contracts[:4]
        ]
        review["overlap_legibility"] = {
            "overlap": "pass",
            "legibility": "pass",
            "notes": "No collisions; labels remain readable at phone size.",
        }
        review["dense_transition_review"] = {
            "sample_interval_seconds": 0.25,
            "covers_entire_video": True,
            "labeled_object_collisions": "pass",
            "persistent_text_integrity": "pass",
            "notes": "Every quarter-second transition keeps labels separate and persistent text visually complete.",
        }
        review["reviewer"] = {"kind": "agent", "name": "Temporal QA fixture"}
        review["reviewed_at"] = "2026-07-10T12:00:00Z"
        review["verdict"] = "pass"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if include_runtime_trace:
            self.write_runtime_trace(root, review, contracts)

    def test_pending_template_does_not_count_as_actual_watching(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)

            strict = CourseRunValidator(run)
            strict.validate_visual_review(plan)
            self.assertTrue(any(issue.severity == "FAIL" and issue.area.startswith("visual-review") for issue in strict.issues))

            draft = CourseRunValidator(run, draft=True)
            draft.validate_visual_review(plan)
            self.assertFalse(any(issue.severity == "FAIL" for issue in draft.issues))
            self.assertTrue(any(issue.severity == "WARN" and issue.area.startswith("visual-review") for issue in draft.issues))

    def test_completed_review_passes_then_video_hash_change_invalidates_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)
            self.complete_review(run)

            complete = CourseRunValidator(run)
            complete.validate_visual_review(plan)
            self.assertEqual([issue for issue in complete.issues if issue.severity == "FAIL"], [])

            video = run / str(plan["shorts"][0]["video_file"])
            video.write_bytes(video.read_bytes() + b"changed-after-review")
            stale = CourseRunValidator(run)
            stale.validate_visual_review(plan)
            self.assertTrue(any(issue.severity == "FAIL" and issue.area == "visual-review.video-hash" for issue in stale.issues))

    def test_generic_prose_observations_do_not_satisfy_structured_state_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)
            self.complete_review(run)
            review_path = run / stem_course.VISUAL_REVIEW_NAME
            payload = json.loads(review_path.read_text(encoding="utf-8"))
            review = payload["reviews"][0]
            review["observed_state_changes"] = [
                {
                    "beat_id": evidence["beat_id"],
                    "before_frame": f"{review['video_file']}#t={evidence['before_seconds']:.2f}s",
                    "after_frame": f"{review['video_file']}#t={evidence['after_seconds']:.2f}s",
                    "persistent_object_ids": evidence["persistent_object_ids"],
                    "observation": "Persistent objects visibly complete a distinct transformation in this beat.",
                }
                for evidence in review["evidence_windows"][:4]
            ]
            review_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            validator = CourseRunValidator(run)
            validator.validate_visual_review(plan)

            failures = [issue for issue in validator.issues if issue.area == "visual-review.changes"]
            self.assertTrue(failures)
            self.assertIn("plan-matched", failures[0].message)
            self.assertIn("planned_transition_id", failures[0].message)

    def test_fabricated_structured_after_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)
            self.complete_review(run)
            review_path = run / stem_course.VISUAL_REVIEW_NAME
            payload = json.loads(review_path.read_text(encoding="utf-8"))
            first_change = payload["reviews"][0]["observed_state_changes"][0]
            object_id = next(iter(first_change["observed_after"]))
            first_change["observed_after"][object_id] = "fabricated state that is absent from the plan"
            review_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            validator = CourseRunValidator(run)
            validator.validate_visual_review(plan)

            self.assertTrue(
                any(
                    issue.severity == "FAIL"
                    and issue.area == "visual-review.changes"
                    and "planned after-state" in issue.message
                    for issue in validator.issues
                )
            )

    def test_runtime_trace_is_required_in_strict_mode_and_optional_in_draft(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)
            self.complete_review(run, include_runtime_trace=False)

            strict = CourseRunValidator(run)
            strict.validate_visual_review(plan)
            runtime_failures = [
                issue
                for issue in strict.issues
                if issue.severity == "FAIL" and issue.area == "visual-review.runtime-trace"
            ]
            self.assertTrue(runtime_failures)
            self.assertIn("producer", runtime_failures[0].message.lower())

            draft = CourseRunValidator(run, draft=True)
            draft.validate_visual_review(plan)
            self.assertFalse(any(issue.severity == "FAIL" for issue in draft.issues))
            self.assertTrue(
                any(issue.severity == "WARN" and issue.area == "visual-review.runtime-trace" for issue in draft.issues)
            )

    def test_runtime_trace_event_must_match_the_planned_delta(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)
            self.complete_review(run)
            trace_path = run / RENDER_RUNTIME_TRACE_NAME
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            event = trace["renders"][0]["semantic_transition_events"][0]
            object_id = next(iter(event["observed_before"]))
            event["observed_before"][object_id] = "fabricated runtime state"
            trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

            validator = CourseRunValidator(run)
            validator.validate_visual_review(plan)

            self.assertTrue(
                any(
                    issue.severity == "FAIL"
                    and issue.area == "visual-review.runtime-trace"
                    and "planned before-state" in issue.message
                    for issue in validator.issues
                )
            )

    def test_sparse_transition_review_cannot_pass_production_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="visual-review-") as tmp:
            run = Path(tmp)
            plan = self.create_rendered_fixture(run)
            self.complete_review(run)
            review_path = run / stem_course.VISUAL_REVIEW_NAME
            payload = json.loads(review_path.read_text(encoding="utf-8"))
            payload["reviews"][0]["dense_transition_review"]["sample_interval_seconds"] = 0.5
            review_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            validator = CourseRunValidator(run)
            validator.validate_visual_review(plan)

            self.assertTrue(
                any(issue.severity == "FAIL" and issue.area == "visual-review.transitions" for issue in validator.issues)
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import ast
import math
import unittest
from types import SimpleNamespace
from typing import Optional

from tools import stem_course


def helper(name: str):
    tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
    node = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    namespace = {
        "math": math,
        "config": SimpleNamespace(frame_rate=30.0),
        "smooth": lambda value: value,
    }
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<helper>", "exec"), namespace)
    return namespace[name]


def priority_queue_short(setup: Optional[str] = None) -> dict[str, object]:
    concept = stem_course.source_term_concept("Priority Queue", "algorithms")
    short = stem_course.concept_to_short(concept, 8)
    if setup is not None:
        worked = dict(short["worked_example"])
        worked["setup"] = setup
        short["worked_example"] = worked
    return short


class TemporalSchedulerTests(unittest.TestCase):
    def scheduler(self):
        class Scheduler:
            pass

        scheduler = Scheduler()
        scheduler._semantic_hold_index = 0
        scheduler._beat_schedule = [{
            "duration": 6.0,
            "animation_plan_beat_id": "beat:long",
            "semantic_transition_ids": ["step:1", "step:2"],
            "planned_transition_windows": [],
        }]
        scheduler.registered = []
        scheduler.runtime_register_semantic_callbacks = (
            lambda transition_id, actions: scheduler.registered.append(
                (transition_id, len(actions))
            )
        )
        scheduler.normalize_semantic_motion_metadata = helper(
            "normalize_semantic_motion_metadata"
        ).__get__(scheduler)
        return scheduler

    def test_phase_actions_are_woven_without_changing_semantic_callback_count(self) -> None:
        register = helper("register_semantic_transition_actions")
        scheduler = self.scheduler()

        def build(_run_time):
            pass

        def first(_run_time):
            pass

        def second(_run_time):
            pass

        def sustain(_run_time):
            pass

        def resolve(_run_time):
            pass

        register(
            scheduler,
            {"step:1": [first], "step:2": [second]},
            build_actions=[build],
            sustain_actions=[sustain],
            resolve_actions=[resolve],
            callback_metadata={
                sustain: {
                    "motion_kind": "displacement",
                    "visible_object_ids": ["selector"],
                    "displacement": 0.5,
                    "semantic_before": {"selector": "left"},
                    "semantic_after": {"selector": "right"},
                }
            },
            enforce_temporal_carriers=True,
        )

        batch = scheduler._concept_motion["action_batches"][0]
        self.assertEqual(batch[0], build)
        self.assertEqual(batch[-1], resolve)
        self.assertEqual([action for action in batch if action in {first, second}], [first, second])
        self.assertGreaterEqual(batch.count(sustain), 1)
        self.assertEqual(scheduler.registered, [("step:1", 1), ("step:2", 1)])
        self.assertEqual(
            len(scheduler._concept_motion["callback_metadata_batches"][0]),
            len(batch),
        )

    def test_long_hook_and_takeaway_receive_qualifying_lifecycle_batches(self) -> None:
        register = helper("register_semantic_transition_actions")
        scheduler = self.scheduler()
        scheduler._beat_schedule = [
            {"duration": 6.0, "animation_plan_beat_id": "beat_01_hook", "semantic_transition_ids": [], "planned_transition_windows": []},
            {"duration": 6.0, "animation_plan_beat_id": "beat_06_takeaway", "semantic_transition_ids": [], "planned_transition_windows": []},
        ]

        def build(_run_time):
            pass

        def sustain(_run_time):
            pass

        def resolve(_run_time):
            pass

        metadata = {
            build: {"carrier_type": "progressive_draw", "persistent_carrier_ids": ["canvas"], "semantic_before": {"canvas": "hidden"}, "semantic_after": {"canvas": "visible"}},
            sustain: {"carrier_type": "displacement", "persistent_carrier_ids": ["tracer"], "semantic_before": {"tracer": "left"}, "semantic_after": {"tracer": "right"}, "displacement": 0.5},
            resolve: {"carrier_type": "causal_verification", "persistent_carrier_ids": ["tracer"], "semantic_before": {"result": "unchecked"}, "semantic_after": {"result": "verified"}},
        }
        register(
            scheduler,
            {},
            build_actions=[build],
            sustain_actions=[sustain],
            resolve_actions=[resolve],
            callback_metadata=metadata,
            enforce_temporal_carriers=True,
        )

        for batch, metadata_batch in zip(
            scheduler._concept_motion["action_batches"],
            scheduler._concept_motion["callback_metadata_batches"],
        ):
            self.assertTrue(batch)
            self.assertTrue(any(
                row["persistent_carrier_ids"]
                and row["semantic_before"] != row["semantic_after"]
                and row["carrier_type"] in {"displacement", "progressive_draw", "causal_verification"}
                for row in metadata_batch
            ))

    def test_exact_domain_routes_register_real_hook_lifecycle_callbacks(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        physics = source[source.index("def bind_physics_motion_to_semantic_contract"):source.index("def play_exact_physics_domain_contract")]
        budget = source[source.index("def build_budget_canvas"):source.index("def advance_budget_canvas")]
        cs = source[source.index("def play_cs_visual"):source.index("def play_probability_visual")]
        self.assertIn("build_actions=build_callbacks", physics)
        self.assertIn("resolve_actions=resolve_callbacks", physics)
        self.assertIn("build_actions=[build_budget_hook]", budget)
        self.assertIn("sustain_actions=[sustain_budget_hook]", budget)
        self.assertIn("build_actions=[build_array_access_hook]", cs)
        self.assertIn("build_actions=[build_complexity_hook]", cs)

    def test_long_beat_rejects_nonvisible_or_nonspatial_sole_carriers(self) -> None:
        register = helper("register_semantic_transition_actions")

        for metadata in (
            {"motion_kind": "opacity_only", "visible_object_ids": ["cell"], "semantic_before": {"cell": "a"}, "semantic_after": {"cell": "b"}},
            {"motion_kind": "displacement", "visible_object_ids": ["cell"], "displacement": 0.0, "semantic_before": {"cell": "a"}, "semantic_after": {"cell": "b"}},
            {"motion_kind": "progressive_draw", "visible_object_ids": [], "semantic_before": {"cell": "a"}, "semantic_after": {"cell": "b"}},
        ):
            with self.subTest(metadata=metadata):
                scheduler = self.scheduler()

                def first(_run_time):
                    pass

                def second(_run_time):
                    pass

                with self.assertRaisesRegex(ValueError, "visible nonzero spatial"):
                    register(
                        scheduler,
                        {"step:1": [first], "step:2": [second]},
                        callback_metadata={first: metadata},
                        enforce_temporal_carriers=True,
                    )

    def test_carrier_type_alias_is_canonical_for_every_strict_motion_kind(self) -> None:
        register = helper("register_semantic_transition_actions")
        for carrier_type in (
            "displacement",
            "progressive_draw",
            "accumulation",
            "causal_verification",
        ):
            with self.subTest(carrier_type=carrier_type):
                scheduler = self.scheduler()

                def first(_run_time):
                    pass

                def second(_run_time):
                    pass

                metadata = {
                    "carrier_type": carrier_type,
                    "visible_object_ids": [" carrier:one ", "carrier:one"],
                    "semantic_before": {" state ": "before"},
                    "semantic_after": {" state ": "after"},
                }
                if carrier_type == "displacement":
                    metadata["displacement"] = "0.5"
                register(
                    scheduler,
                    {"step:1": [first], "step:2": [second]},
                    callback_metadata={first: metadata},
                    enforce_temporal_carriers=True,
                )
                normalized = scheduler._concept_motion["callback_metadata_batches"][0][0]
                self.assertEqual(normalized["carrier_type"], carrier_type)
                self.assertEqual(normalized["motion_kind"], carrier_type)
                self.assertEqual(normalized["persistent_carrier_ids"], ["carrier:one"])
                self.assertEqual(normalized["visible_object_ids"], ["carrier:one"])
                self.assertEqual(normalized["semantic_before"], {"state": "before"})

    def test_conflicting_motion_aliases_fail_closed(self) -> None:
        normalize = helper("normalize_semantic_motion_metadata")
        with self.assertRaisesRegex(ValueError, "conflicting carrier_type and motion_kind"):
            normalize(
                object(),
                {"carrier_type": "accumulation", "motion_kind": "progressive_draw"},
            )

    def test_phase_callbacks_preserve_exact_frame_duration(self) -> None:
        register = helper("register_semantic_transition_actions")
        advance = helper("advance_concept_motion")
        scheduler = self.scheduler()
        scheduler.renderer = SimpleNamespace(time=0.0)
        for name in (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
        ):
            setattr(scheduler, name, helper(name).__get__(scheduler))
        executed = []

        def callback(label):
            def run(run_time):
                executed.append(label)
                scheduler.renderer.time += float(run_time)
            return run

        first = callback("first")
        second = callback("second")
        sustain = callback("sustain")
        resolve = callback("resolve")
        register(
            scheduler,
            {"step:1": [first], "step:2": [second]},
            sustain_actions=[sustain],
            resolve_actions=[resolve],
            callback_metadata={
                sustain: {
                    "motion_kind": "displacement",
                    "visible_object_ids": ["selector"],
                    "displacement": 0.5,
                    "semantic_before": {"selector": "left"},
                    "semantic_after": {"selector": "right"},
                },
            },
            enforce_temporal_carriers=True,
        )

        self.assertTrue(advance(scheduler, 6.0))
        self.assertAlmostEqual(scheduler.renderer.time, 6.0, places=8)
        self.assertEqual(executed.count("first"), 1)
        self.assertEqual(executed.count("second"), 1)

    def test_physics_states_are_allocated_globally_with_terminal_reservation(self) -> None:
        scheduler = self.scheduler()
        scheduler._beat_schedule = [
            {"duration": duration, "animation_plan_beat_id": beat_id}
            for duration, beat_id in ((4.0, "build"), (8.0, "transform-a"), (5.0, "transform-b"), (6.0, "resolve"))
        ]
        scheduler.semantic_action_batch_counts = helper("semantic_action_batch_counts").__get__(scheduler)
        scheduler.semantic_action_batches = helper("semantic_action_batches").__get__(scheduler)
        scheduler.semantic_terminal_batches = helper("semantic_terminal_batches").__get__(scheduler)
        terminal_calls = []

        class Tracker:
            def __init__(self):
                self.value = 0.0

            def get_value(self):
                return self.value

            @property
            def animate(self):
                return self

            def set_value(self, value):
                self.value = float(value)
                return self

        configure = helper("configure_physics_motion")
        states = [[float(index)] for index in range(1, 19)]
        tracker = Tracker()
        configure(
            scheduler,
            [tracker],
            states,
            terminal_action=lambda: terminal_calls.append("endpoint"),
            carrier_metadata={"persistent_carrier_ids": ["physics:test"]},
        )

        batches = scheduler._concept_motion["state_batches"]
        self.assertEqual([item for batch in batches for item in batch], list(enumerate(states)))
        self.assertEqual(batches[-1], [(17, [18.0])])
        self.assertIs(scheduler._concept_motion["state_actions"][-1], scheduler._concept_motion["state_actions"][17])
        self.assertTrue(callable(scheduler._concept_motion["state_actions"][-1]))
        self.assertEqual(terminal_calls, [])

        scheduler.renderer = SimpleNamespace(time=0.0)
        for name in (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
        ):
            setattr(scheduler, name, helper(name).__get__(scheduler))

        def play(*_animations, run_time, **_kwargs):
            scheduler.renderer.time += math.ceil(float(run_time) * 30) / 30.0

        scheduler.play = play
        advance = helper("advance_concept_motion")
        for beat_id in ("build", "transform-a", "transform-b", "resolve"):
            scheduler._runtime_active_beat_id = beat_id
            self.assertTrue(advance(scheduler, scheduler.semantic_play_seconds(120)))

        self.assertEqual(scheduler.runtime_renderer_frame(), 480)
        self.assertEqual(tracker.get_value(), 18.0)
        self.assertEqual(terminal_calls, ["endpoint"])
        self.assertTrue(scheduler._concept_motion["exhausted"])

    def test_actual_subplay_frames_and_semantic_carriers_are_recorded(self) -> None:
        scheduler = self.scheduler()
        scheduler.renderer = SimpleNamespace(time=0.0)
        scheduler.runtime_renderer_frame = helper("runtime_renderer_frame").__get__(scheduler)

        def play(*_animations, run_time, **_kwargs):
            scheduler.renderer.time += math.ceil(float(run_time) * 30) / 30.0

        scheduler.play = play
        scheduler.normalize_semantic_motion_metadata = helper(
            "normalize_semantic_motion_metadata"
        ).__get__(scheduler)
        trace = helper("semantic_callback_choreography")
        Transform = type("Transform", (), {})
        FadeIn = type("FadeIn", (), {})

        def moving(run_time):
            scheduler.play(Transform(), run_time=run_time)

        metadata = {
            "carrier_type": "displacement",
            "persistent_carrier_ids": ["persistent:selector"],
            "semantic_before": {"selector": "source"},
            "semantic_after": {"selector": "target"},
            "displacement": 1.0,
        }
        intervals = trace(scheduler, moving, 2.0, metadata)
        self.assertEqual(intervals[0]["frame_count"], 60)
        self.assertTrue(intervals[0]["qualifying_motion"])
        self.assertEqual(intervals[0]["persistent_carrier_ids"], ["persistent:selector"])

        alias_metadata = {
            "carrier_type": "causal_verification",
            "visible_object_ids": [" persistent:proof "],
            "semantic_before": {"proof": "claim"},
            "semantic_after": {"proof": "verified"},
        }
        alias_intervals = trace(scheduler, moving, 1.0, alias_metadata)
        self.assertTrue(alias_intervals[0]["qualifying_motion"])
        self.assertEqual(alias_intervals[0]["carrier_type"], "causal_verification")

        def opacity_only(run_time):
            scheduler.play(FadeIn(), run_time=run_time)

        rejected = trace(scheduler, opacity_only, 1.0, metadata)
        self.assertFalse(rejected[0]["qualifying_motion"])

    def test_domain_routes_publish_ordered_causal_carriers(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        for token in (
            '"economics:feasible-set"',
            '"economics:utility-boundaries"',
            '"economics:selected-bundle"',
            '"group:coset-partition"',
            '"group:homomorphism:kernel-image"',
            '"physics:vector:endpoint"',
            '"physics:kinematics:state"',
        ):
            self.assertIn(token, source)
        self.assertLess(source.index('"economics:feasible-set"'), source.index('"economics:selected-bundle"'))
        self.assertIn("terminal_action=show_vector_result", source)
        self.assertIn("terminal_action=show_final_summary", source)


class HeapTraceIntegrationTests(unittest.TestCase):
    def test_heap_routes_are_backed_by_stable_identity_trace_events(self) -> None:
        insert = stem_course.cs_heap_semantics(priority_queue_short())
        decrease = stem_course.cs_heap_semantics(
            priority_queue_short("In min-heap [2, 4, 7, 9, 6], decrease key at index 3 to 1."),
        )
        extract = stem_course.cs_heap_semantics(
            priority_queue_short("From min-heap [1, 4, 2, 9, 6, 7], extract min."),
        )

        self.assertEqual(insert["operation"], "insert")
        self.assertEqual(decrease["operation"], "decrease_key")
        self.assertEqual(extract["operation"], "extract_min")
        for semantic in (insert, decrease, extract):
            self.assertTrue(semantic["verified"])
            self.assertTrue(semantic["events"])
            self.assertTrue(all(event["transition_id"] for event in semantic["events"]))
            self.assertEqual(
                semantic["heap_trace"]["after_identity_order"],
                [item["item_id"] for item in semantic["result_items"]],
            )

        for short in (
            priority_queue_short("In min-heap [2, 4, 7, 9, 6], decrease key at index 3 to 1."),
            priority_queue_short("From min-heap [1, 4, 2, 9, 6, 7], extract min."),
        ):
            plan = stem_course.build_animation_plan(short)
            self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])
            source = stem_course.manim_scene(short, "HeapTraceOperation", plan)
            compile(source, "<heap-trace-operation>", "exec")

    def test_generated_sources_use_persistent_route_carriers(self) -> None:
        short = priority_queue_short()
        source = stem_course.manim_scene(short, "TemporalCarrierRegression", stem_course.build_animation_plan(short))

        self.assertIn('trace_events = [event for event in semantic.get("events", [])', source)
        self.assertIn('"cs:merge:source-lane-label"', source)
        self.assertIn('"cs:merge:output-lane-label"', source)
        self.assertIn("dp_sustain_selector.animate.move_to(cell)", source)
        self.assertNotIn("cell.animate.shift(UP * 0.58)", source)
        self.assertIn("MoveAlongPath(root_token, root_path)", source)
        self.assertIn("LaggedStart(*[GrowFromCenter(cell) for cell in row]", source)
        self.assertIn("opening_probe.animate.move_to(row[-1][0])", source)
        self.assertIn("top_marker.animate.next_to(row[-1], UP", source)


if __name__ == "__main__":
    unittest.main()

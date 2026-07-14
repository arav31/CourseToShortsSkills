from __future__ import annotations

import ast
import inspect
import math
import unittest
from types import SimpleNamespace

from tools import stem_course


def semantic_helper_functions(*names: str) -> dict[str, object]:
    tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace: dict[str, object] = {
        "math": math,
        "config": SimpleNamespace(frame_rate=30),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<semantic-helpers>", "exec"), namespace)
    return {name: namespace[name] for name in names}


class SemanticTimingContractTests(unittest.TestCase):
    def test_scene_cues_reflow_and_simplify_before_font_fitting(self) -> None:
        lines = stem_course.simplified_scene_cue_lines(
            ["Dynamic programming state design preserves exactly the information future transitions need."],
        )

        self.assertLessEqual(len(lines), 2)
        self.assertEqual(
            " ".join(lines),
            "Dynamic programming state design preserves exactly the information future transitions need.",
        )
        self.assertNotIn("...", " ".join(lines))

    def test_transition_groups_follow_available_beat_time(self) -> None:
        transitions = [{"id": f"step:{index}"} for index in range(1, 19)]

        groups = stem_course.semantic_transition_groups(
            transitions,
            slot_weights=[3.63, 3.5, 3.2, 17.0],
        )

        self.assertEqual([len(group) for group in groups], [2, 2, 2, 12])
        self.assertEqual([transition for group in groups for transition in group], transitions)

    def test_transition_groups_preserve_nonempty_slots_for_skewed_time(self) -> None:
        transitions = [{"id": f"step:{index}"} for index in range(1, 8)]

        groups = stem_course.semantic_transition_groups(
            transitions,
            slot_weights=[0.01, 0.01, 0.01, 100.0],
        )

        self.assertEqual([len(group) for group in groups], [1, 1, 1, 4])
        self.assertEqual([transition for group in groups for transition in group], transitions)

    def test_cs_state_progression_is_beat_driven_and_finite(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS

        self.assertIn('"kind": "semantic_sequence"', helpers)
        self.assertIn('"kind": "semantic_actions"', helpers)
        self.assertIn('"action_batches": action_batches', helpers)
        self.assertIn("action(action_run_time)", helpers)
        self.assertIn('motion.get("exhausted")', helpers)
        self.assertNotIn("carrier.add_updater(update_state)", helpers)
        self.assertNotIn("cursor.add_updater(move_cursor)", helpers)
        self.assertNotIn("carrier.set_opacity(0.0)", helpers)
        self.assertIn("animations.extend(FadeIn(carrier)", helpers)

    def test_one_hold_cannot_loop_a_completed_semantic_sequence(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS

        self.assertNotIn("while remaining > 0.15", helpers)
        self.assertIn("self.advance_concept_motion(motion_seconds)", helpers)

    def test_semantic_actions_are_distributed_across_remaining_beats(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS

        self.assertIn("self.semantic_action_batches(prepared, hold_durations)", helpers)
        self.assertIn("action_count >= len(durations) - 2", helpers)
        self.assertIn("durations[index] / (1 + min(abs(index - anchor), 2))", helpers)
        self.assertIn("durations[index] / (counts[index] + 1)", helpers)
        self.assertIn("def semantic_frame_partition", helpers)
        self.assertIn("math.nextafter(frames / float(self.semantic_frame_rate()), 0.0)", helpers)
        self.assertIn("math.nextafter(frames / float(self.semantic_frame_rate()), math.inf)", helpers)
        self.assertIn("_semantic_callback_frame_budget", helpers)
        self.assertNotIn("run_time - sum(partitioned_run_times)", helpers)
        self.assertNotIn("slot = round(action_index * (remaining_holds - 1)", helpers)
        self.assertNotIn("min(2.4, remaining * 0.58)", helpers)
        self.assertIn("action_deadline_frame", helpers)
        self.assertNotIn("renderer_frame_slack", helpers)
        self.assertNotIn("4.0 / frame_rate + 0.0001", helpers)

    def test_duration_aware_batching_keeps_every_action_in_order(self) -> None:
        functions = semantic_helper_functions("semantic_action_batch_counts", "semantic_action_batches")

        class Scheduler:
            pass

        scheduler = Scheduler()
        scheduler.semantic_action_batch_counts = functions["semantic_action_batch_counts"].__get__(scheduler)
        scheduler.semantic_action_batches = functions["semantic_action_batches"].__get__(scheduler)
        durations = [6.35, 2.83, 7.23, 6.66, 5.35, 5.35, 4.48, 3.2]
        actions = [object() for _ in range(7)]

        batches = scheduler.semantic_action_batches(actions, durations)

        self.assertEqual([len(batch) for batch in batches], [1, 0, 1, 1, 1, 1, 1, 1])
        self.assertEqual([action for batch in batches for action in batch], actions)

        crowded = scheduler.semantic_action_batch_counts(11, [6.0, 2.0, 4.0])
        self.assertEqual(sum(crowded), 11)
        self.assertTrue(all(count >= 1 for count in crowded))

        economics = scheduler.semantic_action_batch_counts(
            7,
            [5.63, 4.96, 5.96, 10.49, 7.6, 3.0, 8.88, 4.05, 4.05],
        )
        self.assertEqual(economics, [1, 1, 1, 1, 1, 0, 1, 0, 1])

    def test_action_batching_conserves_actions_for_topic_independent_shapes(self) -> None:
        functions = semantic_helper_functions("semantic_action_batch_counts", "semantic_action_batches")

        class Scheduler:
            pass

        scheduler = Scheduler()
        scheduler.semantic_action_batch_counts = functions["semantic_action_batch_counts"].__get__(scheduler)
        scheduler.semantic_action_batches = functions["semantic_action_batches"].__get__(scheduler)
        duration_shapes = (
            [4.0],
            [6.35, 2.83, 7.23, 6.66, 5.35, 5.35, 4.48, 3.2],
            [2.4, 8.1, 3.0, 5.7],
        )

        for durations in duration_shapes:
            for action_count in range(1, 16):
                actions = list(range(action_count))
                batches = scheduler.semantic_action_batches(actions, durations)
                self.assertEqual(len(batches), len(durations))
                self.assertEqual([action for batch in batches for action in batch], actions)
                if action_count < len(durations):
                    self.assertTrue(all(len(batch) <= 1 for batch in batches))
                else:
                    self.assertTrue(all(batch for batch in batches))

    def test_transition_keyed_actions_follow_declared_beats_exactly(self) -> None:
        functions = semantic_helper_functions(
            "normalize_semantic_motion_metadata",
            "register_semantic_transition_actions",
        )
        function = functions["register_semantic_transition_actions"]

        class Scheduler:
            pass

        scheduler = Scheduler()
        scheduler.normalize_semantic_motion_metadata = functions[
            "normalize_semantic_motion_metadata"
        ].__get__(scheduler)
        scheduler._semantic_hold_index = 0
        scheduler._beat_schedule = [
            {"duration": 2.0, "semantic_transition_ids": []},
            {"duration": 3.0, "semantic_transition_ids": ["step:1", "step:2"]},
            {"duration": 4.0, "semantic_transition_ids": ["step:3"]},
            {"duration": 2.0, "semantic_transition_ids": []},
        ]
        actions = [lambda _run_time, index=index: index for index in range(5)]

        function(
            scheduler,
            {
                "step:1": [actions[0], actions[1]],
                "step:2": [actions[2]],
                "step:3": [actions[3]],
            },
            tail_actions=[actions[4]],
        )

        self.assertEqual(
            scheduler._concept_motion["action_batches"],
            [[], actions[:3], [actions[3]], [actions[4]]],
        )
        self.assertEqual(
            scheduler._concept_motion["semantic_transition_ids"],
            ["step:1", "step:2", "step:3"],
        )

    def test_transition_keyed_actions_fail_on_missing_or_duplicate_ids(self) -> None:
        functions = semantic_helper_functions(
            "normalize_semantic_motion_metadata",
            "register_semantic_transition_actions",
        )
        function = functions["register_semantic_transition_actions"]

        class Scheduler:
            pass

        action = lambda _run_time: None
        missing = Scheduler()
        missing.normalize_semantic_motion_metadata = functions[
            "normalize_semantic_motion_metadata"
        ].__get__(missing)
        missing._semantic_hold_index = 0
        missing._beat_schedule = [{"duration": 2.0, "semantic_transition_ids": []}]
        with self.assertRaisesRegex(ValueError, "not scheduled"):
            function(missing, {"step:1": [action]})

        duplicate = Scheduler()
        duplicate.normalize_semantic_motion_metadata = functions[
            "normalize_semantic_motion_metadata"
        ].__get__(duplicate)
        duplicate._semantic_hold_index = 0
        duplicate._beat_schedule = [
            {"duration": 2.0, "semantic_transition_ids": ["step:1"]},
            {"duration": 2.0, "semantic_transition_ids": ["step:1"]},
        ]
        with self.assertRaisesRegex(ValueError, "more than once"):
            function(duplicate, {"step:1": [action]})

    def test_action_hold_budget_preserves_readability_and_uses_the_hold(self) -> None:
        function = semantic_helper_functions("semantic_action_hold_segments")["semantic_action_hold_segments"]
        scheduler = SimpleNamespace()

        leading, motion, trailing = function(scheduler, 6.63, 1)
        self.assertAlmostEqual(leading + motion + trailing, 6.63, places=8)
        self.assertGreater(leading, 0.0)
        self.assertGreaterEqual(motion / 6.63, 0.60)
        self.assertGreaterEqual(trailing, 1.0)

        _leading, batched_motion, _trailing = function(scheduler, 6.63, 3)
        self.assertGreater(batched_motion, motion)
        short_leading, short_motion, short_trailing = function(scheduler, 2.75, 1)
        self.assertAlmostEqual(short_leading + short_motion + short_trailing, 2.75, places=8)
        self.assertGreaterEqual(short_motion / 2.75, 0.60)
        self.assertGreaterEqual(short_trailing, 0.45)
        self.assertEqual(function(scheduler, 6.63, 0), (0.0, 0.0, 6.63))

        for duration in (2.75, 6.63, 12.0, 30.0):
            _leading, _motion, trailing = function(scheduler, duration, 4)
            self.assertLessEqual(trailing, stem_course.MAX_SEMANTIC_FROZEN_TAIL_SECONDS)

    def test_semantic_grouping_does_not_read_its_own_duration_output(self) -> None:
        source = inspect.getsource(stem_course.animation_route_plan_components)

        self.assertNotIn("canonical_beat_schedule", source)
        self.assertNotIn("slot_weights=", source)
        self.assertIn("slots=len(SEMANTIC_TRANSITION_STATES)", source)

    def test_semantic_action_runtime_matches_canonical_holds_exactly(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "semantic_action_batch_counts",
            "semantic_action_batches",
            "semantic_action_hold_segments",
            "register_semantic_actions",
            "advance_concept_motion",
            "semantic_beat_hold",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)
                self._semantic_hold_index = 0
                self.waits: list[float] = []

            def wait(self, duration: float, frozen_frame: bool = False) -> None:
                self.assert_frozen(frozen_frame)
                self.waits.append(float(duration))
                self.renderer.time += float(duration)

            @staticmethod
            def assert_frozen(frozen_frame: bool) -> None:
                if not frozen_frame:
                    raise AssertionError("semantic reading waits must be frozen")

        for name, function in functions.items():
            setattr(Scheduler, name, function)

        durations = [6.35, 2.83, 7.23, 6.66, 5.35, 5.35, 4.48, 3.2]
        scheduler = Scheduler()
        scheduler._beat_schedule = [{"duration": duration} for duration in durations]
        events: list[tuple[int, float, float]] = []

        def action(label: int):
            def callback(run_time: float) -> None:
                events.append((label, scheduler.renderer.time, float(run_time)))
                scheduler.renderer.time += float(run_time)

            return callback

        scheduler.register_semantic_actions([action(index) for index in range(7)])
        hold_starts = []
        for duration in durations:
            hold_starts.append(scheduler.renderer.time)
            scheduler.semantic_beat_hold(duration)

        self.assertAlmostEqual(
            scheduler.renderer.time + scheduler._semantic_unfilled_hold_seconds,
            sum(durations),
            places=8,
        )
        self.assertEqual([label for label, _start, _duration in events], list(range(7)))
        self.assertEqual(scheduler._concept_motion["index"], len(durations))
        self.assertTrue(scheduler._concept_motion["exhausted"])
        self.assertLessEqual(max(scheduler.waits), stem_course.MAX_SEMANTIC_FROZEN_TAIL_SECONDS)
        self.assertLessEqual(max(scheduler.waits), durations[1])
        hold_for_action = [0, 2, 3, 4, 5, 6, 7]
        motion_by_hold: dict[int, float] = {}
        for label, start, run_time in events:
            hold_index = hold_for_action[label]
            self.assertGreater(start, hold_starts[hold_index])
            motion_by_hold[hold_index] = motion_by_hold.get(hold_index, 0.0) + run_time
        for hold_index, motion_time in motion_by_hold.items():
            self.assertGreaterEqual(motion_time / durations[hold_index], 0.60)

    def test_callback_underrun_does_not_create_a_long_frozen_tail(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "semantic_action_batch_counts",
            "semantic_action_batches",
            "semantic_action_hold_segments",
            "register_semantic_actions",
            "advance_concept_motion",
            "semantic_beat_hold",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)
                self._semantic_hold_index = 0
                self.waits: list[float] = []

            def wait(self, duration: float, frozen_frame: bool = False) -> None:
                if not frozen_frame:
                    raise AssertionError("semantic reading waits must be frozen")
                self.waits.append(float(duration))
                self.renderer.time += float(duration)

        for name, function in functions.items():
            setattr(Scheduler, name, function)

        scheduler = Scheduler()
        scheduler._beat_schedule = [{"duration": 6.0}]
        requested: list[float] = []

        def underrunning_action(run_time: float) -> None:
            requested.append(float(run_time))
            scheduler.renderer.time += float(run_time) * 0.4

        scheduler.register_semantic_actions([underrunning_action])
        scheduler.semantic_beat_hold(6.0)

        self.assertEqual(len(requested), 1)
        self.assertGreaterEqual(requested[0] / 6.0, 0.60)
        self.assertLess(scheduler.renderer.time, 6.0)
        self.assertLessEqual(max(scheduler.waits), stem_course.MAX_SEMANTIC_FROZEN_TAIL_SECONDS)
        self.assertGreater(scheduler._semantic_callback_underrun_seconds, 0.0)
        self.assertGreater(scheduler._semantic_unfilled_hold_seconds, 0.0)
        self.assertFalse(hasattr(scheduler, "_semantic_timing_overrun_seconds"))

    def test_zero_duration_motion_never_calls_manim_play(self) -> None:
        advance = semantic_helper_functions("advance_concept_motion")["advance_concept_motion"]

        class Scheduler:
            def play(self, *_args: object, **_kwargs: object) -> None:
                raise AssertionError("zero-duration motion must not call Scene.play")

        sequence = Scheduler()
        sequence._concept_motion = {
            "kind": "semantic_sequence",
            "tracks": [],
            "index": 0,
            "length": 1,
            "exhausted": False,
        }
        self.assertFalse(advance(sequence, 0.0))
        self.assertEqual(sequence._concept_motion["index"], 0)

        empty_batch = Scheduler()
        empty_batch._concept_motion = {
            "kind": "semantic_actions",
            "action_batches": [[]],
            "transition_id_batches": [[]],
            "index": 0,
            "exhausted": False,
        }
        self.assertFalse(advance(empty_batch, 0.0))
        self.assertEqual(empty_batch._concept_motion["index"], 1)
        self.assertTrue(empty_batch._concept_motion["exhausted"])

    def test_nested_child_plays_conserve_exact_callback_frames(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "semantic_timed_segments",
            "advance_concept_motion",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)

            def play(self, *_args: object, run_time: float, **_kwargs: object) -> None:
                frames = math.ceil(float(run_time) * 30)
                self.renderer.time += frames / 30.0

        for name, function in functions.items():
            setattr(Scheduler, name, function)

        for child_count in (2, 3, 7):
            with self.subTest(child_count=child_count):
                for budget in (83, 211):
                    scheduler = Scheduler()

                    def nested_callback(run_time: float, count: int = child_count) -> None:
                        for segment in scheduler.semantic_timed_segments(run_time, [1.0] * count):
                            scheduler.play(run_time=segment)

                    scheduler._concept_motion = {
                        "kind": "semantic_actions",
                        "action_batches": [[nested_callback]],
                        "transition_id_batches": [[None]],
                        "index": 0,
                        "exhausted": False,
                    }
                    scheduler.advance_concept_motion(scheduler.semantic_play_seconds(budget))
                    self.assertEqual(scheduler.runtime_renderer_frame(), budget)

    def test_repeated_beat_ids_execute_each_authored_occurrence_once(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "advance_concept_motion",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)
                self._runtime_active_beat_id = "repeated-beat"
                self.events = []

            def play(self, *_args: object, run_time: float, **_kwargs: object) -> None:
                self.renderer.time += math.ceil(float(run_time) * 30) / 30.0

        for name, function in functions.items():
            setattr(Scheduler, name, function)

        scheduler = Scheduler()

        def first(run_time: float) -> None:
            scheduler.events.append("first")
            scheduler.play(run_time=run_time)

        def second(run_time: float) -> None:
            scheduler.events.append("second")
            scheduler.play(run_time=run_time)

        scheduler._concept_motion = {
            "kind": "semantic_actions",
            "action_batches": [[first], [second]],
            "transition_id_batches": [[None], [None]],
            "callback_metadata_batches": [[{}], [{}]],
            "beat_id_batches": ["repeated-beat", "repeated-beat"],
            "completed_batch_indices": [],
            "index": 0,
            "exhausted": False,
        }
        run_time = scheduler.semantic_play_seconds(30)
        self.assertTrue(scheduler.advance_concept_motion(run_time))
        self.assertTrue(scheduler.advance_concept_motion(run_time))
        self.assertFalse(scheduler.advance_concept_motion(run_time))
        self.assertEqual(scheduler.events, ["first", "second"])
        self.assertEqual(scheduler._concept_motion["completed_batch_indices"], [0, 1])
        self.assertTrue(scheduler._concept_motion["exhausted"])

    def test_authored_complementary_weight_patterns_conserve_exact_frames(self) -> None:
        functions = semantic_helper_functions(
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "semantic_timed_segments",
        )

        class Scheduler:
            pass

        for name, function in functions.items():
            setattr(Scheduler, name, function)
        scheduler = Scheduler()
        weight_patterns = (
            (0.56, 0.44),
            (0.62, 0.38),
            (0.74, 0.26),
            (0.34, 0.66),
            (0.16, 0.68, 0.16),
            (0.28, 0.72),
            (0.42, 0.58),
            (0.25, 0.50, 0.08, 0.17),
            (0.48, 0.02, 0.48, 0.02),
            (0.72, 0.28),
            (0.35, 0.65),
            (0.52, 0.48),
            (0.24, 0.76),
            (0.18, 0.24, 0.58),
            (0.50, 0.50),
            (0.36, 0.64),
            (0.20, 0.50, 0.30),
            (0.88, 0.12),
            (0.20, 0.80),
            (0.90, 0.10),
            (0.92, 0.08),
        )
        for weights in weight_patterns:
            for budget in (17, 29, 79, 83, 88, 211):
                with self.subTest(weights=weights, budget=budget):
                    segments = scheduler.semantic_timed_segments(
                        scheduler.semantic_play_seconds(budget),
                        weights,
                    )
                    consumed = sum(math.ceil(segment * 30) for segment in segments)
                    self.assertEqual(consumed, budget)

    def test_heap_and_graph_callback_shapes_conserve_nested_budgets(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "semantic_timed_segments",
            "advance_concept_motion",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)

            def play(self, *_args: object, run_time: float, **_kwargs: object) -> None:
                self.renderer.time += math.ceil(float(run_time) * 30) / 30.0

        for name, function in functions.items():
            setattr(Scheduler, name, function)

        def execute(callback: object, budget: int) -> int:
            scheduler = Scheduler()
            scheduler._concept_motion = {
                "kind": "semantic_actions",
                "action_batches": [[callback.__get__(scheduler, Scheduler)]],
                "transition_id_batches": [[None]],
                "index": 0,
                "exhausted": False,
            }
            scheduler.advance_concept_motion(scheduler.semantic_play_seconds(budget))
            return scheduler.runtime_renderer_frame()

        def graph_callback(self: Scheduler, run_time: float) -> None:
            for segment in self.semantic_timed_segments(run_time, (0.18, 0.56, 0.26)):
                self.play(run_time=segment)

        def heap_callback(self: Scheduler, run_time: float) -> None:
            motion_time, cue_time = self.semantic_timed_segments(run_time, (0.72, 0.28))
            for segment in self.semantic_timed_segments(motion_time, [1.0] * 7):
                self.play(run_time=segment)
            self.play(run_time=cue_time)

        self.assertEqual(execute(graph_callback, 173), 173)
        self.assertEqual(execute(heap_callback, 257), 257)

    def test_graph_handoff_route_and_dfs_shapes_conserve_79_83_88_frames(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "semantic_timed_segments",
            "advance_concept_motion",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)

            def play(self, *_args: object, run_time: float, **_kwargs: object) -> None:
                self.renderer.time += math.ceil(float(run_time) * 30) / 30.0

        for name, function in functions.items():
            setattr(Scheduler, name, function)

        def execute(shape, budget: int) -> int:
            scheduler = Scheduler()

            def callback(run_time: float) -> None:
                shape(scheduler, run_time)

            scheduler._concept_motion = {
                "kind": "semantic_actions",
                "action_batches": [[callback]],
                "transition_id_batches": [[None]],
                "index": 0,
                "exhausted": False,
            }
            scheduler.advance_concept_motion(scheduler.semantic_play_seconds(budget))
            return scheduler.runtime_renderer_frame()

        def clean_handoff(self: Scheduler, run_time: float) -> None:
            for segment in self.semantic_timed_segments(run_time, (0.42, 0.58)):
                self.play(run_time=segment)

        def route_event(self: Scheduler, run_time: float) -> None:
            focus, handoff = self.semantic_timed_segments(run_time, (0.45, 0.55))
            self.play(run_time=focus)
            clean_handoff(self, handoff)

        def dfs_step(self: Scheduler, run_time: float) -> None:
            travel, handoff = self.semantic_timed_segments(run_time, (0.74, 0.26))
            state, path = self.semantic_timed_segments(travel, (0.30, 0.70))
            self.play(run_time=state)
            self.play(run_time=path)
            self.play(run_time=handoff)

        self.assertEqual(execute(clean_handoff, 79), 79)
        self.assertEqual(execute(route_event, 83), 83)
        self.assertEqual(execute(dfs_step, 88), 88)

    def test_callback_over_budget_fails_closed(self) -> None:
        names = (
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "advance_concept_motion",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)

            def play(self, *_args: object, run_time: float, **_kwargs: object) -> None:
                self.renderer.time += math.ceil(float(run_time) * 30) / 30.0

        for name, function in functions.items():
            setattr(Scheduler, name, function)
        scheduler = Scheduler()

        def over_budget(run_time: float) -> None:
            scheduler.play(run_time=run_time)
            scheduler.play(run_time=scheduler.semantic_play_seconds(1))

        scheduler._concept_motion = {
            "kind": "semantic_actions",
            "action_batches": [[over_budget]],
            "transition_id_batches": [[None]],
            "index": 0,
            "exhausted": False,
        }
        with self.assertRaisesRegex(ValueError, "explicit budget"):
            scheduler.advance_concept_motion(scheduler.semantic_play_seconds(90))

    def test_filler_wait_hits_the_exact_target_frame_with_floor_quantization(self) -> None:
        names = (
            "runtime_renderer_seconds",
            "runtime_renderer_frame",
            "runtime_target_frame",
            "runtime_wait_until",
            "semantic_frame_rate",
            "semantic_wait_seconds",
        )
        functions = semantic_helper_functions(*names)

        class Scheduler:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)
                self._runtime_errors: list[str] = []

            def wait(self, duration: float, frozen_frame: bool = False) -> None:
                self.assertTrue(frozen_frame)
                self.renderer.time += math.floor(float(duration) * 30) / 30.0

            @staticmethod
            def assertTrue(value: bool) -> None:
                if not value:
                    raise AssertionError("filler wait must preserve the frame")

        for name, function in functions.items():
            setattr(Scheduler, name, function)
        scheduler = Scheduler()
        scheduler.runtime_wait_until(137 / 30.0, "filler")

        self.assertEqual(scheduler.runtime_renderer_frame(), 137)
        self.assertEqual(scheduler._runtime_errors, [])

    def test_direct_access_takeaway_teaches_the_invariant(self) -> None:
        _setup, _calculation, takeaway, _question, _answer = stem_course.concrete_cs_example(
            "Direct Access Array", "array"
        )

        self.assertIn("one", takeaway.lower())
        self.assertIn("cell", takeaway.lower())
        self.assertIn("without", takeaway.lower())
        self.assertNotIn("unrelated", takeaway.lower())
        self.assertNotIn("replaced", takeaway.lower())

    def test_shared_narrative_handoffs_do_not_crossfade_text_in_place(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        short = stem_course.concept_to_short(stem_course.ALGORITHMS[0], 1)
        scene_source = stem_course.manim_scene(
            short,
            "NarrativeHandoffContract",
            stem_course.build_animation_plan(short),
        )

        self.assertNotIn("self.play(FadeOut(current), FadeIn(staged)", helpers)
        self.assertNotIn("formula_transition = [FadeOut(hook), FadeIn(formula)]", scene_source)
        self.assertNotIn("self.play(FadeOut(hook), FadeIn(next_hook)", scene_source)
        self.assertNotIn("self.play(FadeOut(intuition), FadeIn(next_intuition)", scene_source)


if __name__ == "__main__":
    unittest.main()

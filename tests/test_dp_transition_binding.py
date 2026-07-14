from __future__ import annotations

import ast
import math
import unittest
from types import SimpleNamespace

from tools import stem_course


def semantic_runtime_helpers(*names: str) -> dict[str, object]:
    tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace: dict[str, object] = {
        "config": SimpleNamespace(frame_rate=30.0),
        "math": math,
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<dp-runtime-helpers>", "exec"), namespace)
    return {name: namespace[name] for name in names}


def fibonacci_short(target: int) -> dict[str, object]:
    concept = stem_course.source_term_concept(
        "Memoization and Recursive Dynamic Programming",
        "algorithms",
    )
    short = stem_course.concept_to_short(concept, 14)
    worked = dict(short["worked_example"])
    worked["setup"] = (
        f"Compute Fibonacci F({target}) from F(0)=0 and F(1)=1 "
        "with top-down memoization."
    )
    short["worked_example"] = worked
    return short


class DPTransitionBindingTests(unittest.TestCase):
    def bindings_for_target(
        self,
        target: int,
    ) -> tuple[dict[str, object], list[str], list[dict[str, object]]]:
        short = fibonacci_short(target)
        plan = stem_course.build_animation_plan(short)
        planned_ids = [
            str(transition_id)
            for beat in plan["beats"]
            for transition_id in beat.get("semantic_transition_ids", [])
        ]
        semantic = stem_course.visual_data_for(short, str(short["visual_type"]))["cs"]
        bindings = stem_course.cs_dp_semantic_event_bindings(semantic, planned_ids)
        return plan, planned_ids, bindings

    def test_every_fibonacci_event_binds_once_in_exact_planned_order(self) -> None:
        plan, planned_ids, bindings = self.bindings_for_target(7)
        route_events = plan["concrete_example"]["renderer_state"]["route_events"]
        bound_ids = [str(binding["planned_transition_id"]) for binding in bindings]

        self.assertEqual(len(route_events), 53)
        self.assertEqual(bound_ids, planned_ids)
        self.assertEqual(len(bound_ids), len(set(bound_ids)))
        self.assertEqual(bound_ids[-1], "fib:event:0053")
        self.assertEqual(
            [binding["event"] for binding in bindings],
            route_events,
        )

    def test_real_mit_payload_normalizes_exact_nodes_before_renderer_registration(self) -> None:
        short = fibonacci_short(7)
        plan = stem_course.build_animation_plan(short)
        semantic = stem_course.visual_data_for(short, str(short["visual_type"]))["cs"]

        self.assertNotIn("recursion_preview", semantic)
        preview = stem_course.cs_dp_fibonacci_recursion_preview(semantic)
        self.assertEqual(len(preview), 15)
        self.assertEqual(preview[0]["id"], "fib:naive:0001")
        self.assertEqual(preview[0]["state"], 7)
        self.assertIsNone(preview[0]["parent"])

        source = stem_course.manim_scene(short, "RealMITDPSceneShape", plan)
        tree = ast.parse(source)
        embedded_visual_data = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "visual_data" for target in node.targets):
                continue
            embedded_visual_data = ast.literal_eval(node.value)
            break
        self.assertIsNotNone(embedded_visual_data)
        embedded_semantic = embedded_visual_data["cs"]
        self.assertEqual(len(embedded_semantic["recursion_preview"]), 15)
        self.assertEqual(len(embedded_semantic["semantic_event_bindings"]), 53)
        renderer = source.split('if semantic_family == "dp":', 1)[1].split(
            'if kind == "state_machine":', 1
        )[0]
        self.assertLess(renderer.index('raw_preview = semantic.get("recursion_preview")'), renderer.index("if not preview:"))
        self.assertIn('call_tree_preview = semantic.get("call_tree_preview")', renderer)

    def test_typed_events_have_observable_call_cache_or_table_updates(self) -> None:
        _plan, _planned_ids, bindings = self.bindings_for_target(7)
        observable_by_kind = {
            binding["event_kind"]: binding["observable_update"]
            for binding in bindings
        }

        self.assertEqual(observable_by_kind["call"], "call_stack")
        self.assertEqual(observable_by_kind["return"], "call_stack")
        self.assertEqual(observable_by_kind["cache_miss"], "cache_lookup")
        self.assertEqual(observable_by_kind["cache_hit"], "cache_lookup")
        self.assertEqual(observable_by_kind["store"], "memo_table")
        self.assertEqual(observable_by_kind["recursive_expansion"], "dependency_state")
        self.assertTrue(all(binding["observable_update"] for binding in bindings))
        phase_by_kind = {
            binding["event_kind"]: binding["visual_phase"]
            for binding in bindings
        }
        self.assertEqual(phase_by_kind["call"], "tree_call")
        self.assertEqual(phase_by_kind["recursive_expansion"], "tree_expand")
        self.assertEqual(phase_by_kind["cache_hit"], "tree_repeat_hit")
        self.assertEqual(phase_by_kind["store"], "table_store")

    def test_portrait_layout_and_event_sequence_build_tree_before_cache(self) -> None:
        short = fibonacci_short(7)
        semantic = stem_course.visual_data_for(short, str(short["visual_type"]))["cs"]
        layout = stem_course.cs_dp_fibonacci_layout_spec(semantic)
        plan, planned_ids, bindings = self.bindings_for_target(7)

        self.assertEqual((layout["table_rows"], layout["table_columns"]), (2, 4))
        self.assertGreaterEqual(float(layout["table_cell_width"]), 1.5)
        self.assertGreaterEqual(float(layout["table_height"]), 2.8)
        self.assertGreaterEqual(
            float(layout["tree_top_y"]) - float(layout["tree_bottom_y"]),
            5.0,
        )
        first_store = next(
            index for index, binding in enumerate(bindings)
            if binding["event_kind"] == "store"
        )
        self.assertGreater(first_store, 0)
        self.assertTrue(all(
            binding["visual_phase"] in {"tree_call", "tree_miss", "tree_expand"}
            for binding in bindings[:first_store]
        ))
        self.assertEqual(bindings[first_store]["visual_phase"], "table_store")
        self.assertIn("tree_repeat_hit", [binding["visual_phase"] for binding in bindings[first_store + 1:]])

        source = stem_course.manim_scene(short, "PortraitDPSequence", plan)
        compile(source, "<portrait-dp-sequence>", "exec")
        renderer = source.split('if semantic_family == "dp":', 1)[1].split(
            'if kind == "state_machine":', 1
        )[0]
        self.assertIn("cells.arrange_in_grid(rows=table_rows, cols=table_columns", renderer)
        self.assertIn('reveal_levels = [int(level) for level in call_tree_preview.get("reveal_levels", [1, 2, 4])]', renderer)
        self.assertIn("AnimationGroup(Create(recursion_edges[node_id]), FadeIn(recursion_nodes[node_id]", renderer)
        self.assertIn("def morph_tree_to_state_graph", renderer)
        self.assertIn('first_store = event_kind == "store" and not current["table_visible"]', renderer)
        self.assertIn("FadeOut(dag_surface)", renderer)
        self.assertIn("FadeIn(dag_mini_map)", renderer)
        self.assertIn("MoveAlongPath(transfer_token, transfer_path)", renderer)
        self.assertLess(
            renderer.index("def morph_tree_to_state_graph"),
            renderer.index("if first_store:"),
        )
        self.assertEqual(len(planned_ids), 53)

    def test_generated_fibonacci_scene_enforces_typography_atomicity_and_portrait_roles(self) -> None:
        short = fibonacci_short(7)
        plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "DPExplanatoryGeometry", plan)
        compile(source, "<dp-explanatory-geometry>", "exec")
        renderer = source.split('if semantic_family == "dp":', 1)[1].split(
            'if kind == "state_machine":', 1
        )[0]

        self.assertIn("dp_min_effective_font_size", renderer)
        self.assertIn("label._course_effective_font_size", renderer)
        self.assertNotIn('Text("hit", font_size=15', renderer)
        self.assertIn("mini_map_nodes[state_id] = Circle", renderer)
        self.assertNotIn("dag_mini_map.animate.scale", renderer)
        self.assertIn(
            'self.register_portrait_role("core_proof", dp_proof_surface, core=tree_surface)',
            renderer,
        )
        self.assertIn('self.register_portrait_role("evidence", cue)', renderer)
        self.assertIn(
            'self.reflow_portrait_roles(("core_proof", "evidence"), remember=True)',
            renderer,
        )
        atomic_reveal = "AnimationGroup(Create(recursion_edges[node_id]), FadeIn(recursion_nodes[node_id]"
        self.assertIn(atomic_reveal, renderer)
        self.assertNotIn("animations.append(Create(recursion_edges[call_id]))", renderer)
        self.assertLess(renderer.index("def expose_repeated_calls"), renderer.index("def morph_tree_to_state_graph"))
        self.assertLess(renderer.index("def morph_tree_to_state_graph"), renderer.index("if first_store:"))

    def test_long_trace_preserves_tail_and_generated_event_callbacks(self) -> None:
        plan, planned_ids, bindings = self.bindings_for_target(12)
        short = fibonacci_short(12)

        self.assertEqual(len(bindings), 93)
        self.assertEqual(len(bindings), len(planned_ids))
        self.assertEqual(bindings[-1]["planned_transition_id"], "fib:event:0093")

        source = stem_course.manim_scene(short, "LongDPTransitionBinding", plan)
        compile(source, "<long-dp-transition-binding>", "exec")
        event_renderer = source.split("for binding in event_bindings:", 1)[1].split(
            "if event_bindings:", 1
        )[0]
        self.assertIn("after_state", event_renderer)
        self.assertIn("call_stack", event_renderer)
        self.assertIn("cache", event_renderer)
        self.assertIn("transition_groups[transition_id] = [animate_fibonacci_event]", event_renderer)
        event_registration = source.split("if event_bindings:", 1)[1].split(
            "transition_groups = {", 1
        )[0]
        self.assertNotIn("continuation_actions", event_registration)

    def test_live_shape_scheduler_executes_every_event_on_its_authored_beat(self) -> None:
        plan, planned_ids, bindings = self.bindings_for_target(7)
        schedule = stem_course.animation_plan_scene_schedule(fibonacci_short(7), plan)
        helpers = semantic_runtime_helpers(
            "runtime_renderer_frame",
            "semantic_frame_rate",
            "semantic_play_seconds",
            "semantic_run_time_frames",
            "semantic_frame_partition",
            "register_semantic_transition_actions",
            "advance_concept_motion",
        )

        class LiveShapeHarness:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)
                self._semantic_hold_index = 0
                self._beat_schedule = schedule
                self._runtime_active_beat_id = None
                self.registered: dict[str, list[str]] = {}
                self.executed: list[tuple[str, str, float, float]] = []

            def runtime_register_semantic_callbacks(self, transition_id, actions) -> None:
                self.registered.setdefault(str(transition_id), []).extend(
                    str(getattr(action, "__name__", "semantic_action"))
                    for action in actions
                )

            def runtime_callback_started(self, transition_id=None, callback_name=None):
                return {
                    "beat_id": str(self._runtime_active_beat_id or ""),
                    "declared_transition_id": str(transition_id or ""),
                    "callback_name": str(callback_name or "semantic_action"),
                    "started_seconds": self.renderer.time,
                }

            def runtime_callback_finished(self, token, status="ok", error=None) -> None:
                if status != "ok" or error is not None:
                    raise AssertionError("focused live-shape callback failed")
                self.executed.append((
                    str(token["beat_id"]),
                    str(token["declared_transition_id"]),
                    float(token["started_seconds"]),
                    self.renderer.time,
                ))

        for name, function in helpers.items():
            setattr(LiveShapeHarness, name, function)

        harness = LiveShapeHarness()
        event_by_id = {
            str(binding["planned_transition_id"]): dict(binding["event"])
            for binding in bindings
        }
        observed_states: list[tuple[str, dict[str, object]]] = []
        transition_groups = {}
        for transition_id in planned_ids:
            def animate_event(run_time, event_id=transition_id):
                event = event_by_id[event_id]
                observed_states.append((event_id, dict(event["after_state"])))
                harness.renderer.time += float(run_time)

            transition_groups[transition_id] = [animate_event]

        def resolve_trace(run_time):
            harness.renderer.time += float(run_time)

        harness.register_semantic_transition_actions(
            transition_groups,
            build_actions=[resolve_trace],
            tail_actions=[resolve_trace],
        )
        self.assertEqual(set(harness.registered), set(planned_ids))
        self.assertTrue(all(len(callbacks) == 1 for callbacks in harness.registered.values()))

        expected_beat_by_id = {
            str(transition_id): str(beat["animation_plan_beat_id"])
            for beat in schedule
            for transition_id in beat.get("semantic_transition_ids", [])
        }
        for beat in schedule:
            harness._runtime_active_beat_id = str(beat["animation_plan_beat_id"])
            evidence = beat.get("planned_evidence_seconds", [])
            action_window = max(0.0, float(evidence[1]) - float(evidence[0]) - 4.0 / 30.0)
            harness.advance_concept_motion(action_window)

        executed_events = [transition_id for _beat, transition_id, _start, _end in harness.executed if transition_id]
        self.assertEqual(executed_events, planned_ids)
        self.assertEqual([event_id for event_id, _state in observed_states], planned_ids)
        self.assertEqual(len(executed_events), len(set(executed_events)))
        for beat_id, transition_id, started, finished in harness.executed:
            if not transition_id:
                continue
            self.assertEqual(beat_id, expected_beat_by_id[transition_id])
            self.assertGreater(finished, started)
        for state in ("core_formula", "core_idea", "example_setup", "example_calculation"):
            beat_id = next(
                str(beat["animation_plan_beat_id"])
                for beat in schedule
                if beat["scene_state"] == state
            )
            self.assertTrue(any(row[0] == beat_id and row[1] for row in harness.executed))
        self.assertEqual(executed_events[0], "fib:event:0001")
        self.assertEqual(executed_events[-1], "fib:event:0053")

    def test_missing_tail_or_duplicate_event_schedule_is_rejected(self) -> None:
        _plan, planned_ids, _bindings = self.bindings_for_target(7)
        semantic = stem_course.visual_data_for(
            fibonacci_short(7),
            str(fibonacci_short(7)["visual_type"]),
        )["cs"]

        with self.assertRaisesRegex(ValueError, "planned semantic transition order"):
            stem_course.cs_dp_semantic_event_bindings(semantic, planned_ids[:-1])
        duplicate_ids = list(planned_ids)
        duplicate_ids[-1] = duplicate_ids[-2]
        with self.assertRaisesRegex(ValueError, "planned semantic transition order"):
            stem_course.cs_dp_semantic_event_bindings(semantic, duplicate_ids)


if __name__ == "__main__":
    unittest.main()

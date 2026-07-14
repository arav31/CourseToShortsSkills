from __future__ import annotations

import unittest

from tools import stem_course


def graph_case(topic: str) -> tuple[dict[str, object], dict[str, object], dict[str, object], list[str]]:
    short = stem_course.concept_to_short(
        stem_course.source_term_concept(topic, "algorithms"),
        1,
    )
    plan = stem_course.build_animation_plan(short)
    semantic = plan["concrete_example"]["renderer_state"]
    planned_ids = [
        str(transition_id)
        for beat in stem_course.animation_plan_scene_schedule(short, plan)
        for transition_id in beat["semantic_transition_ids"]
    ]
    return short, plan, semantic, planned_ids


class CsGraphTransitionSchedulingTests(unittest.TestCase):
    def test_typed_graph_events_own_each_planned_transition_once(self) -> None:
        expected_updates = {
            "Bellman-Ford": {
                "pass_start": "algorithm_cue",
                "edge_scan": "active_edge",
                "relaxation": "distance_or_weight_label",
                "pass_complete": "algorithm_cue",
            },
            "Dijkstra's Algorithm": {
                "frontier": "frontier_nodes",
                "extract_min": "active_vertex",
                "settle": "settled_nodes",
                "outgoing_relaxation": "distance_or_weight_label",
            },
        }
        for topic, update_by_kind in expected_updates.items():
            with self.subTest(topic=topic):
                _short, _plan, semantic, planned_ids = graph_case(topic)
                bindings = stem_course.cs_graph_semantic_event_bindings(
                    semantic,
                    planned_ids,
                )

                bound_ids = [binding["planned_transition_id"] for binding in bindings]
                self.assertEqual(bound_ids, planned_ids)
                self.assertEqual(len(bound_ids), len(set(bound_ids)))
                for event_kind, observable_update in update_by_kind.items():
                    matching = [
                        binding
                        for binding in bindings
                        if binding["event_kind"] == event_kind
                    ]
                    self.assertTrue(matching)
                    self.assertTrue(
                        all(binding["observable_update"] == observable_update for binding in matching)
                    )

                visual_step_ids = [
                    binding["visual_step_id"]
                    for binding in bindings
                    if binding["visual_step_id"]
                ]
                trace_step_ids = [
                    step["step_id"]
                    for step in semantic["animation_trace"]["steps"]
                ]
                self.assertEqual(visual_step_ids, trace_step_ids)
                self.assertTrue(set(visual_step_ids).isdisjoint(planned_ids))

    def test_event_binding_generalizes_to_johnson_reweight_steps(self) -> None:
        _short, _plan, semantic, planned_ids = graph_case("Johnson's Algorithm")
        bindings = stem_course.cs_graph_semantic_event_bindings(semantic, planned_ids)

        self.assertEqual(
            [binding["planned_transition_id"] for binding in bindings],
            planned_ids,
        )
        self.assertEqual(
            [binding["visual_step_id"] for binding in bindings if binding["visual_step_id"]],
            [f"johnson_reweight:{index}" for index in range(1, 6)],
        )

    def test_graph_event_binding_fails_closed_on_schedule_drift(self) -> None:
        _short, _plan, semantic, planned_ids = graph_case("Bellman-Ford")
        reordered = list(planned_ids)
        reordered[0], reordered[1] = reordered[1], reordered[0]

        with self.assertRaisesRegex(ValueError, "do not match the planned semantic transition order"):
            stem_course.cs_graph_semantic_event_bindings(semantic, reordered)

    def test_generated_renderer_registers_event_ids_and_real_state_actions(self) -> None:
        for topic in ("Bellman-Ford", "Dijkstra's Algorithm"):
            with self.subTest(topic=topic):
                short, plan, _semantic, _planned_ids = graph_case(topic)
                source = stem_course.manim_scene(short, "GraphTransitionScheduling", plan)

                compile(source, "generated_graph_transition_scene.py", "exec")
                self.assertIn("graph_step_actions[transition_id] = advance_graph_step", source)
                self.assertIn("def advance_graph_route_event", source)
                self.assertIn(
                    "transition_groups[transition_id] = [advance_graph_route_event]",
                    source,
                )
                self.assertIn("step_action(run_time)", source)
                self.assertIn("self.clean_graph_text_handoff(", source)

    def test_weighted_graph_modes_fill_the_portrait_lane_with_live_evidence(self) -> None:
        for topic in ("Bellman-Ford", "Dijkstra's Algorithm", "Johnson's Algorithm"):
            with self.subTest(topic=topic):
                short, plan, _semantic, _planned_ids = graph_case(topic)
                source = stem_course.manim_scene(short, "GraphPortraitComposition", plan)

                self.assertIn("node_radius = 0.82 if weighted_graph_mode else 0.72", source)
                self.assertIn("node_font_size = 46 if weighted_graph_mode else 40", source)
                self.assertIn('font_size=44 if weighted_graph_mode else 40', source)
                self.assertIn('Text(f"{metric_prefix}={value_text}", font_size=42', source)
                self.assertIn("def place_cs_graph_metric_label", source)
                self.assertIn("self.place_cs_graph_metric_label(", source)
                self.assertIn("_graph_annotation_cardinal_lane", source)
                self.assertIn("def weighted_graph_evidence_mob", source)
                self.assertIn("weighted_graph_surface = VGroup(graph, metric_group)", source)
                self.assertIn("self.fit_in(weighted_graph_surface, max_width=7.28, max_height=3.72)", source)
                self.assertIn("live_evidence.move_to(DOWN * 1.58)", source)
                self.assertIn("graph_surface = weighted_graph_surface", source)
                self.assertIn('self.register_portrait_role("core_proof", graph_surface, core=graph)', source)
                self.assertIn('self.register_portrait_role("evidence", graph_evidence)', source)
                self.assertIn(
                    'self.reflow_portrait_roles(("core_proof", "evidence"), remember=True)',
                    source,
                )
                self.assertIn("def graph_evidence_state_text", source)
                self.assertIn('changing_labels.append(current["evidence"])', source)
                self.assertIn("def resolve_weighted_route", source)
                self.assertIn("weighted_verification_cursor", source)
                self.assertIn("MoveAlongPath(weighted_verification_cursor, verification_path)", source)
                self.assertIn("Transform(current[\"evidence\"], resolved_evidence)", source)
                self.assertIn('"carrier_type": "causal_verification"', source)
                self.assertIn("resolve_actions=resolve_actions", source)
                self.assertGreaterEqual(
                    source.count("self.assert_graph_annotation_lanes(nodes, metric_labels, edge_lookup)"),
                    2,
                )
                self.assertIn("edge-weight:", source)
                self.assertIn(
                    'self.assert_layout_disjoint((("graph proof surface", graph_surface), ("graph cue", state_cue)), pad=0.08)',
                    source,
                )


if __name__ == "__main__":
    unittest.main()

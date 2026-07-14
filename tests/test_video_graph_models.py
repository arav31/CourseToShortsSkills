from __future__ import annotations

import json
import re
import unittest
from dataclasses import replace
from fractions import Fraction
from typing import Mapping

from tools import video_graph_models as graph_models


BELLMAN_FORD_EDGES = (
    ("A", "B", 4),
    ("A", "C", 5),
    ("B", "C", -2),
    ("B", "D", 6),
    ("C", "D", 3),
)

DIJKSTRA_EDGES = (
    ("A", "B", 4),
    ("A", "C", 1),
    ("C", "B", 2),
    ("B", "D", 1),
    ("C", "D", 5),
)

JOHNSON_EDGES = (
    ("A", "B", -2),
    ("A", "C", 4),
    ("B", "C", 3),
    ("B", "D", 2),
    ("C", "D", -1),
)

PLACEHOLDER = re.compile(
    r"(?<![A-Za-z0-9_])(?:none|nan|[+-]?inf(?:inity)?)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def nested_values(value: object):
    yield value
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from nested_values(key)
            yield from nested_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from nested_values(child)


class VideoGraphModelTests(unittest.TestCase):
    def assert_display_payload_is_safe(self, payload: object) -> None:
        for value in nested_values(payload):
            self.assertIsNotNone(value)
            if isinstance(value, str):
                self.assertIsNone(PLACEHOLDER.search(value), msg=value)
        json.dumps(payload, ensure_ascii=False, allow_nan=False)

    def assert_every_update_replaces_one_persistent_label(self, trace) -> None:
        self.assertTrue(trace.steps)
        for step in trace.steps:
            self.assertTrue(step.successful)
            self.assertEqual(len(step.label_replacements), 1)
            replacement = step.label_replacements[0]
            self.assertEqual(replacement.operation, "replace")
            self.assertEqual(replacement.persistent_object_id, replacement.old_label.object_id)
            self.assertEqual(replacement.old_label.object_id, replacement.new_label.object_id)
            self.assertEqual(step.evidence.persistent_object_id, replacement.persistent_object_id)
            self.assertEqual(step.evidence.old_visible_text, replacement.old_label.text)
            self.assertEqual(step.evidence.new_visible_text, replacement.new_label.text)

    def test_canonical_johnson_replaces_visible_weights_with_exact_nonnegative_values(self) -> None:
        trace = graph_models.build_johnson_reweight_trace(JOHNSON_EDGES)

        self.assertEqual(
            dict(trace.potentials),
            {"A": Fraction(0), "B": Fraction(-2), "C": Fraction(0), "D": Fraction(-1)},
        )
        self.assertEqual(
            list(trace.final_edge_weights.values()),
            [Fraction(0), Fraction(4), Fraction(1), Fraction(1), Fraction(0)],
        )
        self.assertTrue(all(weight >= 0 for weight in trace.final_edge_weights.values()))
        self.assertTrue(all(isinstance(weight, Fraction) for weight in trace.final_edge_weights.values()))
        self.assertEqual(
            list(trace.final_displayed_edge_weights.values()),
            ["0", "4", "1", "1", "0"],
        )
        self.assertTrue(all(label.scope == "reweighted_edge_weight" for label in trace.final_edge_labels))
        self.assertEqual(trace.steps[0].old_edge_label.text, "-2")
        self.assertEqual(trace.steps[0].new_edge_label.text, "0")
        self.assert_every_update_replaces_one_persistent_label(trace)
        self.assertTrue(graph_models.validate_animation_trace(trace).ok)

    def test_canonical_dijkstra_uses_mathematical_infinity_and_persistent_distance_labels(self) -> None:
        trace = graph_models.build_dijkstra_trace(
            DIJKSTRA_EDGES,
            "A",
            vertices=("A", "B", "C", "D", "E"),
        )

        self.assertEqual(trace.settled_order, ("A", "C", "B", "D"))
        self.assertEqual(
            trace.final_distances,
            {
                "A": Fraction(0),
                "B": Fraction(3),
                "C": Fraction(1),
                "D": Fraction(4),
                "E": graph_models.INFINITY,
            },
        )
        self.assertEqual(trace.final_displayed_distances["E"], "∞")
        self.assertEqual(trace.steps[0].old_distance_label.text, "∞")
        self.assertEqual(trace.steps[0].new_distance_label.text, "4")
        self.assertTrue(all(step.old_distance_label.text != step.new_distance_label.text for step in trace.steps))
        self.assert_every_update_replaces_one_persistent_label(trace)
        self.assert_display_payload_is_safe(trace.to_payload())

    def test_canonical_bellman_ford_has_exact_relaxation_evidence(self) -> None:
        trace = graph_models.build_bellman_ford_trace(BELLMAN_FORD_EDGES, "A")

        self.assertEqual(
            trace.final_distances,
            {"A": Fraction(0), "B": Fraction(4), "C": Fraction(2), "D": Fraction(5)},
        )
        self.assertFalse(trace.negative_cycle)
        self.assertTrue(any("4 + (-2)" in step.arithmetic.display_text for step in trace.steps))
        self.assertTrue(all(step.arithmetic.exact_result == step.new_distance_label.value for step in trace.steps))
        self.assert_every_update_replaces_one_persistent_label(trace)
        self.assert_display_payload_is_safe(trace.to_payload())

    def test_bellman_ford_route_shows_complete_passes_convergence_and_cycle_check(self) -> None:
        trace = graph_models.build_bellman_ford_trace(BELLMAN_FORD_EDGES, "A")
        events = trace.route_events

        for pass_index in range(1, trace.passes + 1):
            scans = [event for event in events if event["event"] == "edge_scan" and event["pass"] == pass_index]
            self.assertEqual([event["edge_id"] for event in scans], [edge.edge_id for edge in trace.edges])
        self.assertEqual(events[-1]["event"], "negative_cycle_check")
        self.assertFalse(events[-1]["negative_cycle"])
        self.assertTrue(any(event["event"] == "pass_complete" and not event["changed"] for event in events))

    def test_bellman_ford_typed_route_has_exact_ordered_scan_states(self) -> None:
        trace = graph_models.build_bellman_ford_trace(BELLMAN_FORD_EDGES, "A")
        events = trace.typed_events

        self.assertEqual(
            [event.sequence for event in events],
            list(range(1, len(events) + 1)),
        )
        self.assertEqual(len({event.event_id for event in events}), len(events))
        for previous, current in zip(events, events[1:]):
            self.assertEqual(previous.after_state, current.before_state)

        for pass_index in range(1, trace.passes + 1):
            pass_events = [event for event in events if event.phase_index == pass_index]
            self.assertEqual(sum(event.kind == "pass_start" for event in pass_events), 1)
            self.assertEqual(sum(event.kind == "pass_complete" for event in pass_events), 1)
            self.assertEqual(
                [event.detail_map["edge_id"] for event in pass_events if event.kind == "edge_scan"],
                [edge.edge_id for edge in trace.edges],
            )
        self.assertTrue(
            any(
                event.kind == "edge_scan" and not event.detail_map["successful"]
                for event in events
            )
        )
        self.assertEqual(
            sum(event.kind == "relaxation" for event in events), len(trace.steps)
        )
        self.assertEqual(
            [event.detail_map["edge_id"] for event in events if event.kind == "negative_cycle_edge_scan"],
            [edge.edge_id for edge in trace.edges],
        )
        self.assertTrue(any(event.kind == "convergence" for event in events))
        self.assertTrue(graph_models.validate_graph_route_events(trace).ok)

    def test_dijkstra_route_exposes_frontier_extract_settle_and_all_outgoing_attempts(self) -> None:
        trace = graph_models.build_dijkstra_trace(DIJKSTRA_EDGES, "A")
        event_kinds = [event["event"] for event in trace.route_events]

        self.assertEqual(event_kinds.count("frontier"), len(trace.settled_order))
        self.assertEqual(
            [event["vertex"] for event in trace.route_events if event["event"] == "extract_min"],
            list(trace.settled_order),
        )
        self.assertEqual(
            [event["vertex"] for event in trace.route_events if event["event"] == "settle"],
            list(trace.settled_order),
        )
        attempted = [event["edge_id"] for event in trace.route_events if event["event"] == "outgoing_relaxation"]
        self.assertEqual(attempted, [edge.edge_id for vertex in trace.settled_order for edge in trace.edges if edge.source == vertex])

    def test_dijkstra_final_extraction_is_independent_of_relaxations(self) -> None:
        trace = graph_models.build_dijkstra_trace(DIJKSTRA_EDGES, "A")
        events = trace.typed_events
        extracted = [
            event.detail_map["vertex"]
            for event in events
            if event.kind == "extract_min"
        ]
        settled = [
            event.detail_map["vertex"] for event in events if event.kind == "settle"
        ]

        self.assertEqual(extracted, list(trace.settled_order))
        self.assertEqual(settled, list(trace.settled_order))
        self.assertEqual(len(extracted), len(set(extracted)))
        self.assertEqual(extracted[-1], "D")
        final_extract = next(
            event for event in events
            if event.kind == "extract_min" and event.detail_map["vertex"] == "D"
        )
        self.assertTrue(
            any(
                event.kind == "settle"
                and event.detail_map["vertex"] == "D"
                and event.sequence > final_extract.sequence
                for event in events
            )
        )
        self.assertFalse(
            any(
                event.kind == "outgoing_relaxation"
                and event.sequence > final_extract.sequence
                for event in events
            )
        )
        for event in events:
            if event.kind == "outgoing_relaxation":
                self.assertEqual(
                    event.detail_map["from"], event.before_state.active_vertex
                )
        self.assertTrue(graph_models.validate_graph_route_events(trace).ok)

    def test_complete_dijkstra_adapter_extracts_disconnected_vertices_once(self) -> None:
        trace = graph_models.build_complete_dijkstra_trace(
            (("A", "B", 1),),
            "A",
            vertices=("A", "B", "C"),
        )
        extracted = [
            event.detail_map["vertex"]
            for event in trace.typed_events
            if event.kind == "extract_min"
        ]

        self.assertTrue(trace.extracts_unreachable)
        self.assertEqual(extracted, ["A", "B", "C"])
        self.assertEqual(trace.settled_order, ("A", "B", "C"))
        self.assertIs(trace.final_distances["C"], graph_models.INFINITY)
        self.assertTrue(graph_models.validate_graph_route_events(trace).ok)

    def test_johnson_route_reveals_potentials_then_reweights_then_hands_off(self) -> None:
        trace = graph_models.build_johnson_reweight_trace(JOHNSON_EDGES)
        kinds = [event["event"] for event in trace.route_events]

        potential_end = max(index for index, kind in enumerate(kinds) if kind == "potential_reveal")
        reweight_start = kinds.index("reweight_phase_start")
        self.assertLess(potential_end, reweight_start)
        self.assertEqual(kinds.count("potential_reveal"), len(trace.vertices))
        self.assertEqual(kinds.count("reweight_edge"), len(trace.edges))
        self.assertEqual(kinds[-1], "shortest_paths_ready")

    def test_full_johnson_trace_retains_q_runs_each_source_and_unweights(self) -> None:
        trace = graph_models.build_johnson_trace(JOHNSON_EDGES)

        self.assertEqual(trace.super_source, "q")
        self.assertEqual(trace.super_source_object_id, "vertex:q")
        self.assertEqual(trace.potential_trace.vertices[0], "q")
        self.assertEqual(
            [
                edge.target
                for edge in trace.augmented_edges
                if edge.source == trace.super_source
            ],
            list(trace.vertices),
        )
        self.assertEqual(
            dict(trace.potentials),
            {"A": Fraction(0), "B": Fraction(-2), "C": Fraction(0), "D": Fraction(-1)},
        )
        self.assertEqual(
            [source for source, _source_trace in trace.dijkstra_traces],
            list(trace.vertices),
        )
        self.assertTrue(
            all(
                source_trace.algorithm == "dijkstra"
                for _source, source_trace in trace.dijkstra_traces
            )
        )
        self.assertEqual(len(trace.unweight_steps), len(trace.vertices) ** 2)
        self.assertEqual(trace.all_pairs_distances[("A", "D")], Fraction(0))
        self.assertEqual(trace.all_pairs_distances[("C", "D")], Fraction(-1))
        self.assertIs(trace.all_pairs_distances[("D", "A")], graph_models.INFINITY)
        self.assertTrue(trace.path_verifications)
        self.assertTrue(
            all(
                verification.telescopes and verification.path_order_preserved
                for verification in trace.path_verifications
            )
        )
        self.assertEqual(
            trace.route_events[-1]["event"], "complete"
        )
        self.assertTrue(graph_models.validate_johnson_trace(trace).ok)
        self.assert_display_payload_is_safe(trace.to_payload())

    def test_fractional_parallel_edges_remain_distinct_and_exact(self) -> None:
        edges = (
            {"id": "uv-slower", "from": "u", "to": "v", "weight": "2/3"},
            {"id": "uv-faster", "from": "u", "to": "v", "weight": "1/3"},
            {"id": "vw", "from": "v", "to": "w", "weight": "1/6"},
            {"id": "uw", "from": "u", "to": "w", "weight": 1},
        )

        trace = graph_models.build_dijkstra_trace(edges, "u")

        self.assertEqual([edge.edge_id for edge in trace.edges], ["uv-slower", "uv-faster", "vw", "uw"])
        self.assertEqual(trace.final_distances["v"], Fraction(1, 3))
        self.assertEqual(trace.final_distances["w"], Fraction(1, 2))
        self.assertEqual(trace.final_displayed_distances["w"], "1/2")
        self.assertTrue(graph_models.validate_animation_trace(trace).valid)

    def test_validator_rejects_replacement_evidence_that_loses_object_identity(self) -> None:
        trace = graph_models.build_johnson_reweight_trace(JOHNSON_EDGES)
        first_step = trace.steps[0]
        broken_replacement = replace(
            first_step.label_replacements[0],
            persistent_object_id="detached-label",
        )
        broken_step = replace(first_step, label_replacements=(broken_replacement,))
        broken_trace = replace(trace, steps=(broken_step,) + trace.steps[1:])

        validation = graph_models.validate_animation_trace(broken_trace)

        self.assertFalse(validation.ok)
        self.assertTrue(any("persistent object" in error for error in validation.errors))


if __name__ == "__main__":
    unittest.main()

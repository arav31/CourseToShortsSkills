from __future__ import annotations

import json
import unittest

from tools.video_dp_models import (
    build_fibonacci_call_tree_preview,
    build_fibonacci_memo_trace,
    build_fibonacci_state_graph,
    fibonacci_memo_model,
    validate_fibonacci_memo_trace,
)


class FibonacciMemoTraceTests(unittest.TestCase):
    def test_complete_top_down_trace_stores_then_terminates_repeats_at_cache(self) -> None:
        trace = build_fibonacci_memo_trace(7)
        kinds = [event.kind for event in trace.events]

        self.assertEqual(trace.result, 13)
        self.assertEqual(trace.final_cache, {0: 0, 1: 1, 2: 1, 3: 2, 4: 3, 5: 5, 6: 8, 7: 13})
        for required in (
            "call",
            "cache_miss",
            "recursive_expansion",
            "store",
            "return",
            "cache_hit",
        ):
            self.assertIn(required, kinds)

        event_by_id = {event.event_id: event for event in trace.events}
        node_by_id = {node.call_id: node for node in trace.nodes}
        self.assertTrue(trace.repeated_state_cues)
        for cue in trace.repeated_state_cues:
            original = node_by_id[cue.original_call_id]
            repeated = node_by_id[cue.repeated_call_id]
            store = event_by_id[cue.cache_store_event_id]
            hit = event_by_id[cue.cache_hit_event_id]
            self.assertEqual(original.n, cue.n)
            self.assertEqual(repeated.n, cue.n)
            self.assertTrue(repeated.terminated_at_cache)
            self.assertEqual(
                [event_by_id[event_id].kind for event_id in repeated.event_ids],
                ["call", "cache_hit", "return"],
            )
            self.assertEqual(store.kind, "store")
            self.assertEqual(hit.kind, "cache_hit")
            self.assertLess(store.sequence, hit.sequence)
            self.assertIn(cue.n, hit.before_state.cache_values)

        self.assertTrue(validate_fibonacci_memo_trace(trace).ok)
        self.assertTrue(trace.verified)

    def test_every_event_has_stable_id_and_exact_continuous_states(self) -> None:
        trace = build_fibonacci_memo_trace(5)

        self.assertEqual(
            [event.event_id for event in trace.events],
            [f"fib:event:{index:04d}" for index in range(1, len(trace.events) + 1)],
        )
        self.assertEqual(
            [node.call_id for node in trace.nodes],
            [f"fib:call:{index:04d}" for index in range(1, len(trace.nodes) + 1)],
        )
        self.assertEqual(trace.events[0].before_state, trace.initial_state)
        for previous, current in zip(trace.events, trace.events[1:]):
            self.assertEqual(previous.after_state, current.before_state)
        self.assertEqual(trace.events[-1].after_state, trace.final_state)

        store_events = [event for event in trace.events if event.kind == "store"]
        self.assertEqual(len(store_events), 6)
        for event in store_events:
            before = event.before_state.cache_values
            after = event.after_state.cache_values
            self.assertNotIn(event.n, before)
            self.assertEqual(after[event.n], event.detail_map["value"])
            self.assertEqual(set(after) - set(before), {event.n})

    def test_base_targets_and_dictionary_adapter_are_complete(self) -> None:
        zero = build_fibonacci_memo_trace(0)
        one = build_fibonacci_memo_trace(1)

        self.assertEqual([event.kind for event in zero.events], ["call", "cache_miss", "store", "return"])
        self.assertEqual(zero.result, 0)
        self.assertEqual(one.result, 1)
        self.assertEqual(zero.repeated_state_cues, ())
        payload = fibonacci_memo_model(4)
        self.assertEqual(payload["mode"], "fibonacci_memo")
        self.assertEqual(payload["result"], 3)
        self.assertTrue(payload["verified"])
        json.dumps(payload, ensure_ascii=True, allow_nan=False)

    def test_invalid_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_fibonacci_memo_trace(-1)
        with self.assertRaises(TypeError):
            build_fibonacci_memo_trace(True)

    def test_renderer_neutral_views_separate_naive_graph_and_execution_semantics(self) -> None:
        payload = fibonacci_memo_model(7)
        preview = payload["call_tree_preview"]
        graph = payload["state_graph"]
        execution = payload["execution_trace"]

        self.assertEqual(preview["representation"], "call_tree_preview")
        self.assertEqual(preview["total_call_count"], 41)
        self.assertEqual(preview["reveal_levels"], [1, 2, 4])
        self.assertEqual(len(preview["nodes"]), 15)
        self.assertEqual(graph["representation"], "state_graph")
        self.assertEqual(len(graph["nodes"]), 8)
        self.assertEqual(len(graph["edges"]), 12)
        self.assertEqual(execution["representation"], "execution_trace")
        self.assertEqual(len(execution["nodes"]), 13)
        self.assertNotEqual(
            {node["id"] for node in preview["nodes"]},
            {node["call_id"] for node in execution["nodes"]},
        )

    def test_naive_preview_uses_tidy_subtrees_and_distinct_duplicate_instances(self) -> None:
        preview = build_fibonacci_call_tree_preview(7)
        nodes = {node["id"]: node for node in preview["nodes"]}

        self.assertEqual(
            len(nodes) + sum(int(node["omitted_call_count"]) for node in nodes.values()),
            41,
        )
        duplicate_states = {}
        for node in nodes.values():
            duplicate_states.setdefault(node["state"], []).append(node["id"])
            children = [nodes[child_id] for child_id in node["children"]]
            if children:
                self.assertAlmostEqual(
                    float(node["x"]),
                    (float(children[0]["x"]) + float(children[-1]["x"])) / 2.0,
                )
                self.assertGreaterEqual(
                    float(children[-1]["x"]) - float(children[0]["x"]),
                    1.0,
                )
        self.assertGreater(len(duplicate_states[5]), 1)
        self.assertEqual(len(duplicate_states[5]), len(set(duplicate_states[5])))
        self.assertTrue(any(node["duplicate_of"] for node in nodes.values()))

    def test_state_graph_is_canonical_and_topological(self) -> None:
        graph = build_fibonacci_state_graph(7)
        node_ids = [node["id"] for node in graph["nodes"]]
        self.assertEqual(len(node_ids), len(set(node_ids)))
        self.assertEqual(graph["canonical_state_count"], 8)
        for edge in graph["edges"]:
            source = int(str(edge["source"]).rsplit(":", 1)[-1])
            target = int(str(edge["target"]).rsplit(":", 1)[-1])
            self.assertIn(source - target, {1, 2})


if __name__ == "__main__":
    unittest.main()

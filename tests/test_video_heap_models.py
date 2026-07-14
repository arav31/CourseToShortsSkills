from __future__ import annotations

import json
import random
import unittest
from dataclasses import replace

from tools.video_heap_models import (
    EVENT_KINDS,
    HeapItem,
    HeapOperationTrace,
    build_heap_decrease_key_trace,
    build_heap_extract_min_trace,
    build_heap_insert_trace,
    validate_heap_operation_trace,
)


def deterministic_heaps():
    rng = random.Random(8241)
    for size in range(0, 18):
        values = [rng.randint(-8, 12) for _ in range(size)]
        items = [HeapItem(f"case:{size}:item:{index}", value) for index, value in enumerate(values)]
        for child in range(1, size):
            index = child
            while index:
                parent = (index - 1) // 2
                if items[parent].value <= items[index].value:
                    break
                items[parent], items[index] = items[index], items[parent]
                index = parent
        yield items


class HeapOperationTraceTests(unittest.TestCase):
    def assert_trace_contract(self, trace: HeapOperationTrace) -> None:
        validation = validate_heap_operation_trace(trace)
        self.assertTrue(validation.ok, validation.errors)
        self.assertTrue(trace.verified)
        self.assertEqual(trace.events[-1].kind, "resolve")
        self.assertTrue(trace.final_state.heap_invariant_holds)
        self.assertEqual(trace.final_state.array_identity_order, trace.final_state.tree_identity_order)
        json.dumps(trace.to_payload())
        previous = trace.initial_state
        for sequence, event in enumerate(trace.events, start=1):
            self.assertEqual(event.sequence, sequence)
            self.assertEqual(event.before_state, previous)
            self.assertIn(event.kind, EVENT_KINDS)
            self.assertEqual(event.before_identity_order, event.before_state.identity_order)
            self.assertEqual(event.after_identity_order, event.after_state.identity_order)
            self.assertEqual(event.expected_heap_invariant, event.after_state.heap_invariant_holds)
            self.assertEqual(
                [node.index for node in event.after_state.topology],
                list(range(len(event.after_state.items))),
            )
            previous = event.after_state

    def test_insert_preserves_duplicate_value_identities_and_exposes_all_event_fields(self) -> None:
        heap = [HeapItem("old-five-a", 5), HeapItem("old-five-b", 5), HeapItem("nine", 9)]
        trace = build_heap_insert_trace(heap, 1, item_id="new-one")
        self.assert_trace_contract(trace)
        self.assertEqual(trace.before_identity_order, ("old-five-a", "old-five-b", "nine"))
        self.assertEqual(trace.final_state.items[0].item_id, "new-one")
        self.assertEqual(set(trace.after_identity_order), {"old-five-a", "old-five-b", "nine", "new-one"})
        self.assertEqual(trace.events[0].kind, "append")
        self.assertIn("compare", [event.kind for event in trace.events])
        self.assertIn("swap", [event.kind for event in trace.events])
        payload = trace.events[0].to_payload()
        for field in (
            "before_identity_order", "after_identity_order", "active_indices",
            "changed_ids", "expected_heap_invariant", "preferred_beat", "preferred_state",
        ):
            self.assertIn(field, payload)

    def test_decrease_key_targets_identity_not_duplicate_value(self) -> None:
        heap = [HeapItem("root", 2), HeapItem("duplicate-a", 7), HeapItem("duplicate-b", 7), HeapItem("tail", 11)]
        trace = HeapOperationTrace.decrease_key(heap, "duplicate-b", 1)
        self.assert_trace_contract(trace)
        values = {item.item_id: item.value for item in trace.final_state.items}
        self.assertEqual(values["duplicate-a"], 7)
        self.assertEqual(values["duplicate-b"], 1)
        self.assertEqual(trace.final_state.items[0].item_id, "duplicate-b")
        self.assertEqual(trace.events[0].changed_ids, ("duplicate-b",))

        no_op = HeapOperationTrace.decrease_key(heap, "duplicate-a", 7)
        self.assert_trace_contract(no_op)
        self.assertEqual(no_op.events[0].changed_ids, ("duplicate-a",))

    def test_extract_min_returns_original_root_identity_with_duplicate_minima(self) -> None:
        heap = [HeapItem("min-first", 1), HeapItem("min-second", 1), HeapItem("three", 3), HeapItem("four", 4)]
        trace = build_heap_extract_min_trace(heap)
        self.assert_trace_contract(trace)
        self.assertEqual(trace.result_item, HeapItem("min-first", 1))
        self.assertNotIn("min-first", trace.after_identity_order)
        self.assertIn("min-second", trace.after_identity_order)
        self.assertEqual([event.kind for event in trace.events].count("remove"), 1)

    def test_singleton_extract_has_remove_then_resolve_and_empty_topology(self) -> None:
        trace = build_heap_extract_min_trace([HeapItem("only", -3)])
        self.assert_trace_contract(trace)
        self.assertEqual([event.kind for event in trace.events], ["remove", "resolve"])
        self.assertEqual(trace.final_state.items, ())
        self.assertEqual(trace.final_state.topology, ())

    def test_deterministic_property_cases_cover_all_operations_and_intermediate_states(self) -> None:
        for case, heap in enumerate(deterministic_heaps()):
            with self.subTest(operation="insert", case=case):
                inserted = build_heap_insert_trace(heap, -20, item_id=f"inserted:{case}")
                self.assert_trace_contract(inserted)
                self.assertEqual(inserted.final_state.items[0].item_id, f"inserted:{case}")
            if not heap:
                continue
            target = len(heap) - 1
            with self.subTest(operation="decrease_key", case=case):
                decreased = build_heap_decrease_key_trace(heap, target, -21)
                self.assert_trace_contract(decreased)
                self.assertEqual(decreased.final_state.items[0].item_id, heap[target].item_id)
            with self.subTest(operation="extract_min", case=case):
                extracted = build_heap_extract_min_trace(heap)
                self.assert_trace_contract(extracted)
                self.assertEqual(extracted.result_item, heap[0])
                self.assertEqual(len(extracted.final_state.items), len(heap) - 1)

    def test_validator_rejects_unsynchronized_tree_order_and_false_invariant_claim(self) -> None:
        trace = build_heap_insert_trace([2, 4, 6], 1)
        event = trace.events[0]
        bad_state = replace(event.after_state, tree_identity_order=tuple(reversed(event.after_state.tree_identity_order)))
        bad_event = replace(event, after_state=bad_state)
        bad_trace = replace(trace, events=(bad_event,) + trace.events[1:])
        errors = validate_heap_operation_trace(bad_trace).errors
        self.assertTrue(any("tree order" in error for error in errors), errors)

        false_claim = replace(trace.events[0], expected_heap_invariant=not trace.events[0].expected_heap_invariant)
        errors = validate_heap_operation_trace(replace(trace, events=(false_claim,) + trace.events[1:])).errors
        self.assertTrue(any("expected heap invariant" in error for error in errors), errors)

    def test_rejects_invalid_requests(self) -> None:
        with self.assertRaises(ValueError):
            build_heap_insert_trace([3, 1], 2)
        with self.assertRaises(ValueError):
            build_heap_decrease_key_trace([1, 3], 1, 4)
        with self.assertRaises(KeyError):
            build_heap_decrease_key_trace([HeapItem("known", 1)], "missing", 0)
        with self.assertRaises(ValueError):
            build_heap_extract_min_trace([])
        with self.assertRaises(ValueError):
            build_heap_insert_trace([1], 2, item_id="heap:item:0001")


if __name__ == "__main__":
    unittest.main()

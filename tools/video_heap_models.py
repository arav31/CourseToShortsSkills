"""Renderer-neutral semantic traces for binary min-heap operations.

Items retain identity independently of their values, so duplicate keys can be
animated without a renderer guessing which object moved.  Every event contains
complete array and tree snapshots and declares whether heap order is expected
to hold at that intermediate point.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping as MappingABC, Sequence
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple, Union


HeapValue = Union[int, float]
HeapInput = Union[HeapValue, "HeapItem", Tuple[str, HeapValue]]
HEAP_INVARIANT = "for every child i > 0, key[parent(i)] <= key[i]"
EVENT_KINDS = frozenset(
    {"append", "update", "remove", "compare", "swap", "verify_edge", "resolve"}
)


def _value(value: object, name: str = "heap value") -> HeapValue:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite int or float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _identity(value: object, name: str = "item_id") -> str:
    if not isinstance(value, str) or not value or not value.isascii() or not value.isprintable():
        raise ValueError(f"{name} must be a nonempty printable ASCII string")
    return value


@dataclass(frozen=True)
class HeapItem:
    """One persistent heap object; equality includes its stable identity."""

    item_id: str
    value: HeapValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _identity(self.item_id))
        object.__setattr__(self, "value", _value(self.value))

    def to_payload(self) -> dict[str, object]:
        return {"item_id": self.item_id, "value": self.value}


@dataclass(frozen=True)
class HeapTopologyNode:
    """The complete-tree relationships for one array position."""

    index: int
    item_id: str
    parent_index: Optional[int]
    left_index: Optional[int]
    right_index: Optional[int]

    def to_payload(self) -> dict[str, object]:
        return {
            "index": self.index,
            "item_id": self.item_id,
            "parent_index": self.parent_index,
            "left_index": self.left_index,
            "right_index": self.right_index,
        }


def _topology(items: Sequence[HeapItem]) -> Tuple[HeapTopologyNode, ...]:
    size = len(items)
    return tuple(
        HeapTopologyNode(
            index=index,
            item_id=item.item_id,
            parent_index=None if index == 0 else (index - 1) // 2,
            left_index=2 * index + 1 if 2 * index + 1 < size else None,
            right_index=2 * index + 2 if 2 * index + 2 < size else None,
        )
        for index, item in enumerate(items)
    )


def _heap_order(items: Sequence[HeapItem]) -> bool:
    return all(items[(index - 1) // 2].value <= items[index].value for index in range(1, len(items)))


@dataclass(frozen=True)
class HeapState:
    """A synchronized array/tree snapshot with explicit complete topology."""

    items: Tuple[HeapItem, ...]
    array_identity_order: Tuple[str, ...]
    tree_identity_order: Tuple[str, ...]
    topology: Tuple[HeapTopologyNode, ...]

    @classmethod
    def from_items(cls, items: Sequence[HeapItem]) -> "HeapState":
        frozen = tuple(items)
        order = tuple(item.item_id for item in frozen)
        return cls(frozen, order, order, _topology(frozen))

    @property
    def values(self) -> Tuple[HeapValue, ...]:
        return tuple(item.value for item in self.items)

    @property
    def identity_order(self) -> Tuple[str, ...]:
        return self.array_identity_order

    @property
    def heap_invariant_holds(self) -> bool:
        return _heap_order(self.items)

    def index_of(self, item_id: str) -> int:
        return self.array_identity_order.index(item_id)

    def to_payload(self) -> dict[str, object]:
        return {
            "items": [item.to_payload() for item in self.items],
            "values": list(self.values),
            "identity_order": list(self.array_identity_order),
            "array_identity_order": list(self.array_identity_order),
            "tree_identity_order": list(self.tree_identity_order),
            "topology": [node.to_payload() for node in self.topology],
            "heap_invariant_holds": self.heap_invariant_holds,
        }


@dataclass(frozen=True)
class HeapTraceEvent(MappingABC[str, object]):
    """One visualizable heap action with exact before/after ownership."""

    event_id: str
    sequence: int
    kind: str
    before_state: HeapState
    after_state: HeapState
    before_identity_order: Tuple[str, ...]
    after_identity_order: Tuple[str, ...]
    active_indices: Tuple[int, ...]
    changed_ids: Tuple[str, ...]
    expected_heap_invariant: bool
    preferred_beat: str
    preferred_state: str
    details: Tuple[Tuple[str, object], ...] = ()

    @property
    def detail_map(self) -> dict[str, object]:
        return dict(self.details)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "event": self.kind,
            "kind": self.kind,
            "before_state": self.before_state.to_payload(),
            "after_state": self.after_state.to_payload(),
            "before_identity_order": list(self.before_identity_order),
            "after_identity_order": list(self.after_identity_order),
            "active_indices": list(self.active_indices),
            "changed_ids": list(self.changed_ids),
            "expected_heap_invariant": self.expected_heap_invariant,
            "heap_invariant": HEAP_INVARIANT,
            "preferred_beat": self.preferred_beat,
            "preferred_state": self.preferred_state,
        }
        for key, value in self.details:
            payload[key] = list(value) if isinstance(value, tuple) else value
        return payload

    def __getitem__(self, key: str) -> object:
        return self.to_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_payload())

    def __len__(self) -> int:
        return len(self.to_payload())


@dataclass(frozen=True)
class HeapValidationResult:
    errors: Tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def valid(self) -> bool:
        return self.ok

    def require_valid(self) -> None:
        if self.errors:
            raise ValueError("Invalid heap operation trace:\n- " + "\n- ".join(self.errors))


@dataclass(frozen=True)
class HeapOperationTrace:
    """A complete, validated execution of one min-heap operation."""

    operation: str
    initial_state: HeapState
    final_state: HeapState
    events: Tuple[HeapTraceEvent, ...]
    target_id: Optional[str] = None
    result_item: Optional[HeapItem] = None

    @classmethod
    def insert(
        cls, heap: Sequence[HeapInput], value: HeapValue, *, item_id: Optional[str] = None
    ) -> "HeapOperationTrace":
        return build_heap_insert_trace(heap, value, item_id=item_id)

    @classmethod
    def decrease_key(
        cls, heap: Sequence[HeapInput], target: Union[str, int], new_value: HeapValue
    ) -> "HeapOperationTrace":
        return build_heap_decrease_key_trace(heap, target, new_value)

    @classmethod
    def extract_min(cls, heap: Sequence[HeapInput]) -> "HeapOperationTrace":
        return build_heap_extract_min_trace(heap)

    @property
    def route_events(self) -> Tuple[HeapTraceEvent, ...]:
        return self.events

    @property
    def before_identity_order(self) -> Tuple[str, ...]:
        return self.initial_state.identity_order

    @property
    def after_identity_order(self) -> Tuple[str, ...]:
        return self.final_state.identity_order

    @property
    def verified(self) -> bool:
        return validate_heap_operation_trace(self).ok

    def to_payload(self) -> dict[str, object]:
        event_payloads = [event.to_payload() for event in self.events]
        return {
            "family": "heap",
            "mode": self.operation,
            "operation": self.operation,
            "invariant": HEAP_INVARIANT,
            "target_id": self.target_id or "",
            "result_item": self.result_item.to_payload() if self.result_item else None,
            "before_identity_order": list(self.before_identity_order),
            "after_identity_order": list(self.after_identity_order),
            "initial_state": self.initial_state.to_payload(),
            "final_state": self.final_state.to_payload(),
            "events": event_payloads,
            "steps": event_payloads,
            "route_events": event_payloads,
            "verified": self.verified,
        }


def _normalize_heap(heap: Sequence[HeapInput]) -> list[HeapItem]:
    items: list[HeapItem] = []
    used: set[str] = set()
    for index, raw in enumerate(heap, start=1):
        if isinstance(raw, HeapItem):
            item = raw
        elif isinstance(raw, tuple):
            if len(raw) != 2:
                raise ValueError("heap item tuples must be (item_id, value)")
            item = HeapItem(_identity(raw[0]), _value(raw[1]))
        else:
            item = HeapItem(f"heap:item:{index:04d}", _value(raw))
        if item.item_id in used:
            raise ValueError(f"duplicate heap item identity: {item.item_id}")
        used.add(item.item_id)
        items.append(item)
    if not _heap_order(items):
        raise ValueError("initial items must already satisfy min-heap order")
    return items


class _TraceBuilder:
    def __init__(self, operation: str, items: list[HeapItem]) -> None:
        self.operation = operation
        self.items = items
        self.events: list[HeapTraceEvent] = []
        self.initial_state = HeapState.from_items(items)

    def state(self) -> HeapState:
        return HeapState.from_items(self.items)

    def emit(
        self,
        kind: str,
        before: HeapState,
        active: Sequence[int] = (),
        changed: Sequence[str] = (),
        *,
        preferred_beat: Optional[str] = None,
        preferred_state: Optional[str] = None,
        **details: object,
    ) -> HeapTraceEvent:
        after = self.state()
        event = HeapTraceEvent(
            event_id=f"heap:{self.operation}:event:{len(self.events) + 1:04d}",
            sequence=len(self.events) + 1,
            kind=kind,
            before_state=before,
            after_state=after,
            before_identity_order=before.identity_order,
            after_identity_order=after.identity_order,
            active_indices=tuple(active),
            changed_ids=tuple(changed),
            expected_heap_invariant=after.heap_invariant_holds,
            preferred_beat=preferred_beat or ("resolve" if kind == "resolve" else "transform"),
            preferred_state=preferred_state or ("before" if kind == "compare" else "after"),
            details=tuple(details.items()),
        )
        self.events.append(event)
        return event

    def compare(self, left: int, right: int, *, role: str) -> None:
        state = self.state()
        self.emit(
            "compare", state, (left, right), role=role,
            left_id=self.items[left].item_id, right_id=self.items[right].item_id,
            left_value=self.items[left].value, right_value=self.items[right].value,
            comparison_result=self.items[left].value <= self.items[right].value,
        )

    def swap(self, left: int, right: int) -> None:
        before = self.state()
        changed = (self.items[left].item_id, self.items[right].item_id)
        self.items[left], self.items[right] = self.items[right], self.items[left]
        self.emit("swap", before, (left, right), changed, left_index=left, right_index=right)

    def verify_all_edges(self) -> None:
        for child in range(1, len(self.items)):
            parent = (child - 1) // 2
            state = self.state()
            self.emit(
                "verify_edge", state, (parent, child), parent_index=parent,
                child_index=child, parent_id=self.items[parent].item_id,
                child_id=self.items[child].item_id, edge_valid=self.items[parent].value <= self.items[child].value,
            )

    def resolve(self, **details: object) -> None:
        state = self.state()
        self.emit("resolve", state, preferred_beat="resolve", preferred_state="after", **details)


def _new_item_id(items: Sequence[HeapItem]) -> str:
    used = {item.item_id for item in items}
    index = len(items) + 1
    while f"heap:item:{index:04d}" in used:
        index += 1
    return f"heap:item:{index:04d}"


def _sift_up(builder: _TraceBuilder, index: int) -> None:
    while index > 0:
        parent = (index - 1) // 2
        builder.compare(parent, index, role="parent_child")
        if builder.items[parent].value <= builder.items[index].value:
            break
        builder.swap(parent, index)
        index = parent


def build_heap_insert_trace(
    heap: Sequence[HeapInput], value: HeapValue, *, item_id: Optional[str] = None
) -> HeapOperationTrace:
    items = _normalize_heap(heap)
    inserted = HeapItem(_identity(item_id) if item_id is not None else _new_item_id(items), _value(value))
    if inserted.item_id in {item.item_id for item in items}:
        raise ValueError(f"duplicate heap item identity: {inserted.item_id}")
    builder = _TraceBuilder("insert", items)
    before = builder.state()
    builder.items.append(inserted)
    builder.emit("append", before, (len(items) - 1,), (inserted.item_id,), preferred_beat="build", item_id=inserted.item_id, value=inserted.value)
    _sift_up(builder, len(builder.items) - 1)
    builder.verify_all_edges()
    builder.resolve(result_id=inserted.item_id)
    trace = HeapOperationTrace("insert", builder.initial_state, builder.state(), tuple(builder.events), inserted.item_id, inserted)
    validate_heap_operation_trace(trace).require_valid()
    return trace


def build_heap_decrease_key_trace(
    heap: Sequence[HeapInput], target: Union[str, int], new_value: HeapValue
) -> HeapOperationTrace:
    items = _normalize_heap(heap)
    if isinstance(target, bool) or not isinstance(target, (str, int)):
        raise TypeError("target must be an item identity or array index")
    if isinstance(target, int):
        if target < 0 or target >= len(items):
            raise IndexError("heap target index is out of range")
        index = target
    else:
        target_id = _identity(target, "target")
        try:
            index = next(i for i, item in enumerate(items) if item.item_id == target_id)
        except StopIteration as exc:
            raise KeyError(f"unknown heap item identity: {target_id}") from exc
    checked_value = _value(new_value, "new_value")
    old_item = items[index]
    if checked_value > old_item.value:
        raise ValueError("decrease_key cannot increase a key")
    builder = _TraceBuilder("decrease_key", items)
    before = builder.state()
    builder.items[index] = HeapItem(old_item.item_id, checked_value)
    builder.emit("update", before, (index,), (old_item.item_id,), item_id=old_item.item_id, old_value=old_item.value, new_value=checked_value)
    _sift_up(builder, index)
    builder.verify_all_edges()
    builder.resolve(result_id=old_item.item_id)
    result = next(item for item in builder.items if item.item_id == old_item.item_id)
    trace = HeapOperationTrace("decrease_key", builder.initial_state, builder.state(), tuple(builder.events), old_item.item_id, result)
    validate_heap_operation_trace(trace).require_valid()
    return trace


def build_heap_extract_min_trace(heap: Sequence[HeapInput]) -> HeapOperationTrace:
    items = _normalize_heap(heap)
    if not items:
        raise ValueError("extract_min requires a nonempty heap")
    builder = _TraceBuilder("extract_min", items)
    extracted = items[0]
    if len(items) > 1:
        builder.swap(0, len(items) - 1)
    before_remove = builder.state()
    removed_index = len(builder.items) - 1
    removed = builder.items.pop()
    builder.emit("remove", before_remove, (removed_index,), (removed.item_id,), item_id=removed.item_id, value=removed.value, removed_index=removed_index)

    index = 0
    while 2 * index + 1 < len(builder.items):
        left = 2 * index + 1
        right = left + 1
        child = left
        if right < len(builder.items):
            builder.compare(left, right, role="select_smaller_child")
            if builder.items[right].value < builder.items[left].value:
                child = right
        builder.compare(index, child, role="parent_child")
        if builder.items[index].value <= builder.items[child].value:
            break
        builder.swap(index, child)
        index = child

    builder.verify_all_edges()
    builder.resolve(result_id=extracted.item_id, result_value=extracted.value)
    trace = HeapOperationTrace("extract_min", builder.initial_state, builder.state(), tuple(builder.events), extracted.item_id, extracted)
    validate_heap_operation_trace(trace).require_valid()
    return trace


def _state_errors(state: HeapState, label: str) -> list[str]:
    errors: list[str] = []
    item_ids = tuple(item.item_id for item in state.items)
    if len(set(item_ids)) != len(item_ids):
        errors.append(f"{label} has duplicate item identities")
    if state.array_identity_order != item_ids:
        errors.append(f"{label} array order does not match its items")
    if state.tree_identity_order != item_ids:
        errors.append(f"{label} tree order is not synchronized with array order")
    expected_topology = _topology(state.items)
    if state.topology != expected_topology:
        errors.append(f"{label} does not encode complete binary-tree topology")
    return errors


def _item_map(state: HeapState) -> dict[str, HeapValue]:
    return {item.item_id: item.value for item in state.items}


def validate_heap_operation_trace(trace: HeapOperationTrace) -> HeapValidationResult:
    """Validate topology, heap expectation, identity and exact event semantics."""

    errors: list[str] = []
    if trace.operation not in {"insert", "decrease_key", "extract_min"}:
        errors.append(f"unknown heap operation {trace.operation!r}")
    errors.extend(_state_errors(trace.initial_state, "initial state"))
    errors.extend(_state_errors(trace.final_state, "final state"))
    if not trace.initial_state.heap_invariant_holds:
        errors.append("initial state violates min-heap order")

    previous = trace.initial_state
    event_ids: set[str] = set()
    for sequence, event in enumerate(trace.events, start=1):
        label = f"event {event.event_id}"
        if event.event_id in event_ids:
            errors.append(f"{label} has a duplicate ID")
        event_ids.add(event.event_id)
        if event.sequence != sequence:
            errors.append(f"{label} has a non-contiguous sequence")
        if event.kind not in EVENT_KINDS:
            errors.append(f"{label} has unknown kind {event.kind!r}")
        if event.before_state != previous:
            errors.append(f"{label} breaks exact state continuity")
        errors.extend(_state_errors(event.before_state, f"{label} before-state"))
        errors.extend(_state_errors(event.after_state, f"{label} after-state"))
        if event.before_identity_order != event.before_state.identity_order:
            errors.append(f"{label} has incorrect before identity order")
        if event.after_identity_order != event.after_state.identity_order:
            errors.append(f"{label} has incorrect after identity order")
        if event.expected_heap_invariant != event.after_state.heap_invariant_holds:
            errors.append(f"{label} declares the wrong expected heap invariant")
        if len(set(event.active_indices)) != len(event.active_indices) or any(
            not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= max(len(event.before_state.items), len(event.after_state.items))
            for index in event.active_indices
        ):
            errors.append(f"{label} has invalid active indices")
        if len(set(event.changed_ids)) != len(event.changed_ids):
            errors.append(f"{label} repeats a changed identity")
        if event.preferred_beat not in {"build", "transform", "resolve"}:
            errors.append(f"{label} has an invalid preferred beat")
        if event.preferred_state not in {"before", "after"}:
            errors.append(f"{label} has an invalid preferred state")

        before_ids = set(event.before_state.identity_order)
        after_ids = set(event.after_state.identity_order)
        before_values = _item_map(event.before_state)
        after_values = _item_map(event.after_state)
        added = after_ids - before_ids
        removed = before_ids - after_ids
        value_changed = {item_id for item_id in before_ids & after_ids if before_values[item_id] != after_values[item_id]}

        if event.kind == "append":
            if len(added) != 1 or removed or value_changed or event.after_state.identity_order[:-1] != event.before_state.identity_order:
                errors.append(f"{label} is not one tail append")
            expected_changed = added
        elif event.kind == "remove":
            if len(removed) != 1 or added or value_changed or event.before_state.identity_order[:-1] != event.after_state.identity_order:
                errors.append(f"{label} is not one tail removal")
            expected_changed = removed
        elif event.kind == "update":
            updated_id = event.detail_map.get("item_id")
            old_value = event.detail_map.get("old_value")
            new_value = event.detail_map.get("new_value")
            valid_update = (
                isinstance(updated_id, str)
                and updated_id in before_ids
                and old_value == before_values.get(updated_id)
                and new_value == after_values.get(updated_id)
                and isinstance(old_value, (int, float))
                and not isinstance(old_value, bool)
                and isinstance(new_value, (int, float))
                and not isinstance(new_value, bool)
                and new_value <= old_value
                and value_changed.issubset({updated_id})
            )
            if (
                added
                or removed
                or not valid_update
                or event.before_state.identity_order != event.after_state.identity_order
            ):
                errors.append(f"{label} is not one identity-preserving key update")
            expected_changed = {updated_id} if isinstance(updated_id, str) else set()
        elif event.kind == "swap":
            details = event.detail_map
            left, right = details.get("left_index"), details.get("right_index")
            expected = list(event.before_state.identity_order)
            if not isinstance(left, int) or not isinstance(right, int) or left == right or not (0 <= left < len(expected) and 0 <= right < len(expected)):
                errors.append(f"{label} has invalid swap indices")
                expected_changed = set()
            else:
                expected[left], expected[right] = expected[right], expected[left]
                expected_changed = {expected[left], expected[right]}
                if tuple(expected) != event.after_state.identity_order or before_values != after_values:
                    errors.append(f"{label} is not the declared transposition")
            if added or removed or value_changed:
                errors.append(f"{label} changes membership or keys during swap")
        else:
            expected_changed = set()
            if event.before_state != event.after_state:
                errors.append(f"{label} mutates state during {event.kind}")

        if set(event.changed_ids) != expected_changed:
            errors.append(f"{label} has incorrect changed IDs")
        if event.kind == "verify_edge":
            parent = event.detail_map.get("parent_index")
            child = event.detail_map.get("child_index")
            valid_edge = (
                isinstance(parent, int) and isinstance(child, int)
                and 0 <= parent < len(event.after_state.items) and 0 <= child < len(event.after_state.items)
                and parent == (child - 1) // 2
                and event.after_state.items[parent].value <= event.after_state.items[child].value
            )
            if not valid_edge or event.detail_map.get("edge_valid") is not True:
                errors.append(f"{label} does not verify a valid parent-child edge")
        elif event.kind == "compare":
            if len(event.active_indices) != 2:
                errors.append(f"{label} does not identify two compared indices")
            else:
                left, right = event.active_indices
                left_item = event.after_state.items[left]
                right_item = event.after_state.items[right]
                details = event.detail_map
                if (
                    details.get("left_id") != left_item.item_id
                    or details.get("right_id") != right_item.item_id
                    or details.get("left_value") != left_item.value
                    or details.get("right_value") != right_item.value
                    or details.get("comparison_result")
                    != (left_item.value <= right_item.value)
                    or details.get("role") not in {"parent_child", "select_smaller_child"}
                ):
                    errors.append(f"{label} has inconsistent comparison evidence")
        elif event.kind == "resolve":
            if not event.after_state.heap_invariant_holds:
                errors.append(f"{label} resolves before restoring heap order")
            if event.preferred_beat != "resolve" or event.preferred_state != "after":
                errors.append(f"{label} has incorrect resolve presentation metadata")
        previous = event.after_state

    if previous != trace.final_state:
        errors.append("final state does not match the last event")
    if not trace.events or trace.events[-1].kind != "resolve":
        errors.append("trace does not end with resolve")
    if not trace.final_state.heap_invariant_holds:
        errors.append("final state violates min-heap order")

    kinds = [event.kind for event in trace.events]
    expected_first = {"insert": "append", "decrease_key": "update", "extract_min": "swap" if len(trace.initial_state.items) > 1 else "remove"}.get(trace.operation)
    if kinds and expected_first is not None and kinds[0] != expected_first:
        errors.append(f"{trace.operation} starts with {kinds[0]!r}, expected {expected_first!r}")
    mutation_kind = {"insert": "append", "decrease_key": "update", "extract_min": "remove"}.get(trace.operation)
    if mutation_kind and kinds.count(mutation_kind) != 1:
        errors.append(f"{trace.operation} must contain exactly one {mutation_kind} event")

    initial_ids = set(trace.initial_state.identity_order)
    final_ids = set(trace.final_state.identity_order)
    if trace.operation == "insert":
        if final_ids - initial_ids != ({trace.target_id} if trace.target_id else set()) or initial_ids - final_ids:
            errors.append("insert final identity multiset is incorrect")
        if (
            trace.result_item is None
            or trace.result_item.item_id != trace.target_id
            or _item_map(trace.final_state).get(trace.target_id or "")
            != trace.result_item.value
        ):
            errors.append("insert result item does not match the inserted identity")
    elif trace.operation == "decrease_key":
        if initial_ids != final_ids or trace.target_id not in final_ids:
            errors.append("decrease_key final identity multiset is incorrect")
        elif _item_map(trace.final_state)[trace.target_id] > _item_map(trace.initial_state)[trace.target_id]:
            errors.append("decrease_key increased its target key")
        if (
            trace.result_item is None
            or trace.result_item.item_id != trace.target_id
            or _item_map(trace.final_state).get(trace.target_id or "")
            != trace.result_item.value
        ):
            errors.append("decrease_key result item does not match its target")
    elif trace.operation == "extract_min":
        if (
            trace.result_item is None
            or trace.result_item != trace.initial_state.items[0]
            or trace.target_id != trace.initial_state.items[0].item_id
        ):
            errors.append("extract_min result is not the original root identity")
        elif initial_ids - final_ids != {trace.result_item.item_id} or final_ids - initial_ids:
            errors.append("extract_min final identity multiset is incorrect")
    return HeapValidationResult(tuple(errors))


def heap_insert_model(heap: Sequence[HeapInput], value: HeapValue, *, item_id: Optional[str] = None) -> dict[str, object]:
    return build_heap_insert_trace(heap, value, item_id=item_id).to_payload()


def heap_decrease_key_model(heap: Sequence[HeapInput], target: Union[str, int], new_value: HeapValue) -> dict[str, object]:
    return build_heap_decrease_key_trace(heap, target, new_value).to_payload()


def heap_extract_min_model(heap: Sequence[HeapInput]) -> dict[str, object]:
    return build_heap_extract_min_trace(heap).to_payload()


build_insert_trace = build_heap_insert_trace
build_decrease_key_trace = build_heap_decrease_key_trace
build_extract_min_trace = build_heap_extract_min_trace
validate_heap_trace = validate_heap_operation_trace


__all__ = [
    "EVENT_KINDS", "HEAP_INVARIANT", "HeapInput", "HeapItem", "HeapOperationTrace",
    "HeapState", "HeapTopologyNode", "HeapTraceEvent", "HeapValidationResult",
    "build_decrease_key_trace", "build_extract_min_trace", "build_heap_decrease_key_trace",
    "build_heap_extract_min_trace", "build_heap_insert_trace", "build_insert_trace",
    "heap_decrease_key_model", "heap_extract_min_model", "heap_insert_model",
    "validate_heap_operation_trace", "validate_heap_trace",
]

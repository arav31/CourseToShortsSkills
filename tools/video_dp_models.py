"""Typed, renderer-neutral traces for recursive dynamic programming.

The trace models control flow and memo-table mutations separately.  Renderers
can therefore show calls, repeated states, cache operations, and returns
without reconstructing recursion from a bottom-up Fibonacci table.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping as MappingABC
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple


def _checked_nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


@dataclass(frozen=True)
class DPValidationResult:
    errors: Tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def valid(self) -> bool:
        return self.ok

    def require_valid(self) -> None:
        if self.errors:
            raise ValueError(
                "Invalid Fibonacci memo trace:\n- " + "\n- ".join(self.errors)
            )


@dataclass(frozen=True)
class FibonacciState:
    """Exact memo table and call stack at one point in the trace."""

    cache: Tuple[Tuple[int, int], ...]
    call_stack: Tuple[str, ...]
    completed_calls: Tuple[str, ...]

    @property
    def cache_values(self) -> dict[int, int]:
        return dict(self.cache)

    def to_payload(self) -> dict[str, object]:
        return {
            "cache": {str(index): value for index, value in self.cache},
            "call_stack": list(self.call_stack),
            "completed_calls": list(self.completed_calls),
        }


@dataclass(frozen=True)
class FibonacciTraceEvent(MappingABC[str, object]):
    """One typed event, also exposed as a mapping for renderer adapters."""

    event_id: str
    sequence: int
    kind: str
    call_id: str
    state_id: str
    n: int
    parent_call_id: Optional[str]
    depth: int
    before_state: FibonacciState
    after_state: FibonacciState
    details: Tuple[Tuple[str, object], ...] = ()

    @property
    def detail_map(self) -> dict[str, object]:
        return dict(self.details)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "event": self.kind,
            "call_id": self.call_id,
            "state_id": self.state_id,
            "n": self.n,
            "parent_call_id": self.parent_call_id or "",
            "depth": self.depth,
            "before_state": self.before_state.to_payload(),
            "after_state": self.after_state.to_payload(),
        }
        for key, value in self.details:
            if isinstance(value, tuple):
                payload[key] = list(value)
            else:
                payload[key] = value
        return payload

    def __getitem__(self, key: str) -> object:
        return self.to_payload()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_payload())

    def __len__(self) -> int:
        return len(self.to_payload())


@dataclass(frozen=True)
class FibonacciCallNode:
    """One actual invocation in the memoized recursion tree."""

    call_id: str
    state_id: str
    n: int
    parent_call_id: Optional[str]
    depth: int
    repeated_state_of: Optional[str]
    child_call_ids: Tuple[str, ...]
    event_ids: Tuple[str, ...]
    result: int
    terminated_at_cache: bool

    def to_payload(self) -> dict[str, object]:
        return {
            "call_id": self.call_id,
            "state_id": self.state_id,
            "n": self.n,
            "parent_call_id": self.parent_call_id or "",
            "depth": self.depth,
            "repeated_state_of": self.repeated_state_of or "",
            "child_call_ids": list(self.child_call_ids),
            "event_ids": list(self.event_ids),
            "result": self.result,
            "terminated_at_cache": self.terminated_at_cache,
        }


@dataclass(frozen=True)
class FibonacciRepeatedStateCue:
    """A cache-hit cue tied only to actual call and store events."""

    cue_id: str
    state_id: str
    n: int
    original_call_id: str
    repeated_call_id: str
    cache_store_event_id: str
    cache_hit_event_id: str

    def to_payload(self) -> dict[str, object]:
        return {
            "cue_id": self.cue_id,
            "state_id": self.state_id,
            "n": self.n,
            "original_call_id": self.original_call_id,
            "repeated_call_id": self.repeated_call_id,
            "cache_store_event_id": self.cache_store_event_id,
            "cache_hit_event_id": self.cache_hit_event_id,
        }


@dataclass(frozen=True)
class DPGeometryNode:
    """One renderer-neutral node with stable explanatory geometry."""

    node_id: str
    state_id: str
    n: int
    parent_id: Optional[str]
    child_ids: Tuple[str, ...]
    depth: int
    x: float
    y: float
    duplicate_of: Optional[str] = None
    omitted_call_count: int = 0

    def to_payload(self) -> dict[str, object]:
        return {
            "id": self.node_id,
            "state_id": self.state_id,
            "state": self.n,
            "parent": self.parent_id or "",
            "children": list(self.child_ids),
            "depth": self.depth,
            "x": self.x,
            "y": self.y,
            "duplicate_of": self.duplicate_of or "",
            "omitted_call_count": self.omitted_call_count,
        }


def _fibonacci_naive_call_counts(target: int) -> tuple[int, dict[int, int]]:
    counts = {index: 0 for index in range(target + 1)}

    def visit(n: int) -> int:
        counts[n] += 1
        if n <= 1:
            return 1
        return 1 + visit(n - 1) + visit(n - 2)

    return visit(target), counts


def build_fibonacci_call_tree_preview(
    target: int = 7,
    *,
    visible_levels: int = 4,
) -> dict[str, object]:
    """Build a bounded true naive-call tree with tidy subtree geometry."""

    checked_target = _checked_nonnegative_integer(target, "target")
    checked_levels = _checked_nonnegative_integer(visible_levels, "visible_levels")
    if checked_levels < 1:
        raise ValueError("visible_levels must be at least one")

    total_call_count, call_counts = _fibonacci_naive_call_counts(checked_target)
    mutable_nodes: list[dict[str, object]] = []
    first_instance_by_state: dict[int, str] = {}
    instance_count = 0

    def subtree_call_count(n: int) -> int:
        if n <= 1:
            return 1
        return 1 + subtree_call_count(n - 1) + subtree_call_count(n - 2)

    def visit(n: int, parent_id: Optional[str], depth: int) -> str:
        nonlocal instance_count
        instance_count += 1
        node_id = f"fib:naive:{instance_count:04d}"
        duplicate_of = first_instance_by_state.get(n)
        first_instance_by_state.setdefault(n, node_id)
        node: dict[str, object] = {
            "id": node_id,
            "state": n,
            "parent": parent_id,
            "children": [],
            "depth": depth,
            "duplicate_of": duplicate_of,
            "omitted_call_count": 0,
        }
        mutable_nodes.append(node)
        if n > 1 and depth + 1 < checked_levels:
            node["children"] = [
                visit(n - 1, node_id, depth + 1),
                visit(n - 2, node_id, depth + 1),
            ]
        elif n > 1:
            node["omitted_call_count"] = subtree_call_count(n) - 1
        return node_id

    root_id = visit(checked_target, None, 0)
    by_id = {str(node["id"]): node for node in mutable_nodes}
    next_leaf_x = 0.0

    def assign_x(node_id: str) -> float:
        nonlocal next_leaf_x
        node = by_id[node_id]
        child_ids = [str(child_id) for child_id in node["children"]]
        if not child_ids:
            x = next_leaf_x
            next_leaf_x += 1.0
        else:
            child_x = [assign_x(child_id) for child_id in child_ids]
            x = (child_x[0] + child_x[-1]) / 2.0
        node["x"] = x
        return x

    root_x = assign_x(root_id)
    nodes = tuple(
        DPGeometryNode(
            node_id=str(node["id"]),
            state_id=f"fib:state:{int(node['state'])}",
            n=int(node["state"]),
            parent_id=str(node["parent"]) if node["parent"] else None,
            child_ids=tuple(str(child_id) for child_id in node["children"]),
            depth=int(node["depth"]),
            x=round(float(node["x"]) - root_x, 6),
            y=float(-int(node["depth"])),
            duplicate_of=str(node["duplicate_of"]) if node["duplicate_of"] else None,
            omitted_call_count=int(node["omitted_call_count"]),
        )
        for node in mutable_nodes
    )
    duplicate_states = sorted(
        state for state, count in call_counts.items() if count > 1
    )
    return {
        "representation": "call_tree_preview",
        "algorithm": "naive_fibonacci",
        "target": checked_target,
        "root_id": root_id,
        "visible_levels": checked_levels,
        "reveal_levels": [1, 2, checked_levels],
        "total_call_count": total_call_count,
        "call_counts": {str(state): count for state, count in call_counts.items()},
        "duplicate_states": duplicate_states,
        "nodes": [node.to_payload() for node in nodes],
        "edges": [
            {"id": f"fib:naive-edge:{node.node_id}", "source": node.parent_id, "target": node.node_id}
            for node in nodes
            if node.parent_id is not None
        ],
        "geometry": {
            "algorithm": "tidy_subtree",
            "sibling_separation": 1.0,
            "parent_centered_over_children": True,
        },
    }


def build_fibonacci_state_graph(target: int = 7) -> dict[str, object]:
    """Build the canonical one-node-per-state Fibonacci dependency DAG."""

    checked_target = _checked_nonnegative_integer(target, "target")
    nodes = []
    for n in range(checked_target, -1, -1):
        row = checked_target - n
        nodes.append({
            "id": f"fib:state:{n}",
            "state": n,
            "x": -0.75 if row % 2 == 0 else 0.75,
            "y": float(-row),
            "base": n <= 1,
        })
    edges = [
        {
            "id": f"fib:dependency:{n}:{dependency}",
            "source": f"fib:state:{n}",
            "target": f"fib:state:{dependency}",
        }
        for n in range(2, checked_target + 1)
        for dependency in (n - 1, n - 2)
    ]
    return {
        "representation": "state_graph",
        "algorithm": "fibonacci_dependency_dag",
        "target": checked_target,
        "root_id": f"fib:state:{checked_target}",
        "nodes": nodes,
        "edges": edges,
        "topological_order": [f"fib:state:{n}" for n in range(checked_target + 1)],
        "canonical_state_count": checked_target + 1,
    }


@dataclass(frozen=True)
class FibonacciMemoTrace:
    """Complete top-down memoized Fibonacci execution."""

    algorithm: str
    target: int
    root_call_id: str
    nodes: Tuple[FibonacciCallNode, ...]
    events: Tuple[FibonacciTraceEvent, ...]
    repeated_state_cues: Tuple[FibonacciRepeatedStateCue, ...]
    initial_state: FibonacciState
    final_state: FibonacciState
    result: int

    @property
    def final_cache(self) -> dict[int, int]:
        return self.final_state.cache_values

    @property
    def route_events(self) -> Tuple[FibonacciTraceEvent, ...]:
        return self.events

    @property
    def verified(self) -> bool:
        return validate_fibonacci_memo_trace(self).ok

    def to_payload(self) -> dict[str, object]:
        event_payloads = [event.to_payload() for event in self.events]
        repeated_states = sorted({cue.n for cue in self.repeated_state_cues})
        execution_trace = {
            "representation": "execution_trace",
            "algorithm": self.algorithm,
            "root_call_id": self.root_call_id,
            "nodes": [node.to_payload() for node in self.nodes],
            "events": event_payloads,
            "initial_state": self.initial_state.to_payload(),
            "final_state": self.final_state.to_payload(),
        }
        return {
            "family": "dp",
            "mode": "fibonacci_memo",
            "algorithm": self.algorithm,
            "formula_text": "F(n) = F(n-1) + F(n-2)",
            "formula_latex": r"F_n=F_{n-1}+F_{n-2}",
            "target": self.target,
            "root_call_id": self.root_call_id,
            "nodes": [node.to_payload() for node in self.nodes],
            "recursion_nodes": [node.to_payload() for node in self.nodes],
            "events": event_payloads,
            "steps": event_payloads,
            "route_events": event_payloads,
            "repeated_state_cues": [
                cue.to_payload() for cue in self.repeated_state_cues
            ],
            "repeated_states": repeated_states,
            "call_tree_preview": build_fibonacci_call_tree_preview(self.target),
            "state_graph": build_fibonacci_state_graph(self.target),
            "execution_trace": execution_trace,
            "initial_state": self.initial_state.to_payload(),
            "final_state": self.final_state.to_payload(),
            "final_cache": {
                str(index): value for index, value in self.final_state.cache
            },
            "saved_state_count": len(self.final_state.cache),
            "result": self.result,
            "verified": self.verified,
            "invariant": (
                "a cache miss stores one exact state value before return; every later "
                "call to that state terminates at the populated cache entry"
            ),
        }


def build_fibonacci_memo_trace(target: int = 7) -> FibonacciMemoTrace:
    """Execute top-down memoized Fibonacci and retain every control-flow event."""

    checked_target = _checked_nonnegative_integer(target, "target")
    cache: dict[int, int] = {}
    stack: list[str] = []
    completed: list[str] = []
    events: list[FibonacciTraceEvent] = []
    nodes_by_id: dict[str, FibonacciCallNode] = {}
    first_call_by_state: dict[int, str] = {}
    store_event_by_state: dict[int, str] = {}
    repeated_cues: list[FibonacciRepeatedStateCue] = []
    call_count = 0

    def snapshot() -> FibonacciState:
        return FibonacciState(
            cache=tuple(sorted(cache.items())),
            call_stack=tuple(stack),
            completed_calls=tuple(completed),
        )

    initial_state = snapshot()

    def emit(
        kind: str,
        call_id: str,
        n: int,
        parent_call_id: Optional[str],
        depth: int,
        before_state: FibonacciState,
        after_state: FibonacciState,
        *details: Tuple[str, object],
    ) -> FibonacciTraceEvent:
        event = FibonacciTraceEvent(
            event_id=f"fib:event:{len(events) + 1:04d}",
            sequence=len(events) + 1,
            kind=kind,
            call_id=call_id,
            state_id=f"fib:state:{n}",
            n=n,
            parent_call_id=parent_call_id,
            depth=depth,
            before_state=before_state,
            after_state=after_state,
            details=tuple(details),
        )
        events.append(event)
        return event

    def visit(n: int, parent_call_id: Optional[str], depth: int) -> Tuple[int, str]:
        nonlocal call_count
        call_count += 1
        call_id = f"fib:call:{call_count:04d}"
        repeated_state_of = first_call_by_state.get(n)
        if repeated_state_of is None:
            first_call_by_state[n] = call_id
        node_event_ids: list[str] = []
        child_call_ids: list[str] = []

        before_call = snapshot()
        stack.append(call_id)
        after_call = snapshot()
        call_event = emit(
            "call",
            call_id,
            n,
            parent_call_id,
            depth,
            before_call,
            after_call,
            ("repeated_state_of", repeated_state_of or ""),
        )
        node_event_ids.append(call_event.event_id)

        if n in cache:
            hit_state = snapshot()
            hit_event = emit(
                "cache_hit",
                call_id,
                n,
                parent_call_id,
                depth,
                hit_state,
                hit_state,
                ("value", cache[n]),
                ("cache_store_event_id", store_event_by_state[n]),
                ("original_call_id", first_call_by_state[n]),
            )
            node_event_ids.append(hit_event.event_id)
            repeated_cues.append(
                FibonacciRepeatedStateCue(
                    cue_id=f"fib:repeat:{len(repeated_cues) + 1:04d}",
                    state_id=f"fib:state:{n}",
                    n=n,
                    original_call_id=first_call_by_state[n],
                    repeated_call_id=call_id,
                    cache_store_event_id=store_event_by_state[n],
                    cache_hit_event_id=hit_event.event_id,
                )
            )
            value = cache[n]
            before_return = snapshot()
            popped = stack.pop()
            if popped != call_id:
                raise AssertionError("Fibonacci call stack lost LIFO order")
            completed.append(call_id)
            after_return = snapshot()
            return_event = emit(
                "return",
                call_id,
                n,
                parent_call_id,
                depth,
                before_return,
                after_return,
                ("value", value),
                ("returned_from_cache", True),
            )
            node_event_ids.append(return_event.event_id)
            nodes_by_id[call_id] = FibonacciCallNode(
                call_id=call_id,
                state_id=f"fib:state:{n}",
                n=n,
                parent_call_id=parent_call_id,
                depth=depth,
                repeated_state_of=repeated_state_of,
                child_call_ids=(),
                event_ids=tuple(node_event_ids),
                result=value,
                terminated_at_cache=True,
            )
            return value, call_id

        miss_state = snapshot()
        miss_event = emit(
            "cache_miss",
            call_id,
            n,
            parent_call_id,
            depth,
            miss_state,
            miss_state,
        )
        node_event_ids.append(miss_event.event_id)

        if n <= 1:
            value = n
        else:
            expansion_state = snapshot()
            expansion_event = emit(
                "recursive_expansion",
                call_id,
                n,
                parent_call_id,
                depth,
                expansion_state,
                expansion_state,
                ("dependency_states", (f"fib:state:{n - 1}", f"fib:state:{n - 2}")),
            )
            node_event_ids.append(expansion_event.event_id)
            left, left_call_id = visit(n - 1, call_id, depth + 1)
            child_call_ids.append(left_call_id)
            right, right_call_id = visit(n - 2, call_id, depth + 1)
            child_call_ids.append(right_call_id)
            value = left + right

        before_store = snapshot()
        cache[n] = value
        after_store = snapshot()
        store_event = emit(
            "store",
            call_id,
            n,
            parent_call_id,
            depth,
            before_store,
            after_store,
            ("value", value),
            ("dependencies", tuple(child_call_ids)),
        )
        node_event_ids.append(store_event.event_id)
        store_event_by_state[n] = store_event.event_id

        before_return = snapshot()
        popped = stack.pop()
        if popped != call_id:
            raise AssertionError("Fibonacci call stack lost LIFO order")
        completed.append(call_id)
        after_return = snapshot()
        return_event = emit(
            "return",
            call_id,
            n,
            parent_call_id,
            depth,
            before_return,
            after_return,
            ("value", value),
            ("returned_from_cache", False),
        )
        node_event_ids.append(return_event.event_id)
        nodes_by_id[call_id] = FibonacciCallNode(
            call_id=call_id,
            state_id=f"fib:state:{n}",
            n=n,
            parent_call_id=parent_call_id,
            depth=depth,
            repeated_state_of=repeated_state_of,
            child_call_ids=tuple(child_call_ids),
            event_ids=tuple(node_event_ids),
            result=value,
            terminated_at_cache=False,
        )
        return value, call_id

    result, root_call_id = visit(checked_target, None, 0)
    ordered_nodes = tuple(
        nodes_by_id[f"fib:call:{index:04d}"]
        for index in range(1, call_count + 1)
    )
    trace = FibonacciMemoTrace(
        algorithm="top_down_memoized_fibonacci",
        target=checked_target,
        root_call_id=root_call_id,
        nodes=ordered_nodes,
        events=tuple(events),
        repeated_state_cues=tuple(repeated_cues),
        initial_state=initial_state,
        final_state=snapshot(),
        result=result,
    )
    validate_fibonacci_memo_trace(trace).require_valid()
    return trace


def validate_fibonacci_memo_trace(trace: FibonacciMemoTrace) -> DPValidationResult:
    """Validate event ordering, exact state mutations, and repeated-state cues."""

    errors: list[str] = []
    nodes = {node.call_id: node for node in trace.nodes}
    events = {event.event_id: event for event in trace.events}
    if len(nodes) != len(trace.nodes):
        errors.append("call node IDs are not unique")
    if len(events) != len(trace.events):
        errors.append("event IDs are not unique")

    previous_after = trace.initial_state
    for expected_sequence, event in enumerate(trace.events, start=1):
        if event.sequence != expected_sequence:
            errors.append(f"event {event.event_id} has a non-contiguous sequence")
        if event.before_state != previous_after:
            errors.append(f"event {event.event_id} breaks exact state continuity")
        previous_after = event.after_state
        before_cache = event.before_state.cache_values
        after_cache = event.after_state.cache_values

        if event.kind == "call":
            if event.after_state.call_stack != event.before_state.call_stack + (event.call_id,):
                errors.append(f"call event {event.event_id} does not push its call node")
            if before_cache != after_cache:
                errors.append(f"call event {event.event_id} mutates the cache")
        elif event.kind == "store":
            value = event.detail_map.get("value")
            expected_cache = dict(before_cache)
            expected_cache[event.n] = value  # type: ignore[assignment]
            if after_cache != expected_cache:
                errors.append(f"store event {event.event_id} has the wrong cache after-state")
        elif event.kind == "cache_hit":
            if event.n not in before_cache:
                errors.append(f"cache hit {event.event_id} has no populated entry")
            if before_cache != after_cache:
                errors.append(f"cache hit {event.event_id} mutates the cache")
        elif event.kind == "return":
            if not event.before_state.call_stack or event.before_state.call_stack[-1] != event.call_id:
                errors.append(f"return event {event.event_id} is not LIFO")
            if event.after_state.call_stack != event.before_state.call_stack[:-1]:
                errors.append(f"return event {event.event_id} does not pop its call")
            if event.after_state.completed_calls != event.before_state.completed_calls + (event.call_id,):
                errors.append(f"return event {event.event_id} does not complete its call")
            if before_cache != after_cache:
                errors.append(f"return event {event.event_id} mutates the cache")
        elif event.kind in {"cache_miss", "recursive_expansion"}:
            if before_cache != after_cache or event.before_state.call_stack != event.after_state.call_stack:
                errors.append(f"{event.kind} event {event.event_id} mutates execution state")
        else:
            errors.append(f"event {event.event_id} has unknown kind {event.kind!r}")

    if previous_after != trace.final_state:
        errors.append("final state does not match the last event")
    if trace.final_state.call_stack:
        errors.append("final call stack is not empty")

    for node in trace.nodes:
        node_events = [events[event_id] for event_id in node.event_ids if event_id in events]
        if len(node_events) != len(node.event_ids):
            errors.append(f"node {node.call_id} references a missing event")
            continue
        kinds = [event.kind for event in node_events]
        if not kinds or kinds[0] != "call" or kinds[-1] != "return":
            errors.append(f"node {node.call_id} does not span call through return")
        if node.terminated_at_cache:
            if kinds != ["call", "cache_hit", "return"]:
                errors.append(f"repeated call {node.call_id} does not terminate at cache hit")
            if node.child_call_ids:
                errors.append(f"cache-hit node {node.call_id} expands children")
        else:
            if "cache_miss" not in kinds or "store" not in kinds:
                errors.append(f"cache-miss node {node.call_id} is not stored before return")
            if node.n > 1:
                if "recursive_expansion" not in kinds or len(node.child_call_ids) != 2:
                    errors.append(f"recursive node {node.call_id} lacks two dependencies")
                else:
                    child_values = [nodes[child].result for child in node.child_call_ids]
                    if node.result != sum(child_values):
                        errors.append(f"node {node.call_id} violates Fibonacci recurrence")
            elif node.child_call_ids:
                errors.append(f"base node {node.call_id} unexpectedly has children")

    cue_ids: set[str] = set()
    for cue in trace.repeated_state_cues:
        if cue.cue_id in cue_ids:
            errors.append(f"repeated-state cue ID {cue.cue_id} is duplicated")
        cue_ids.add(cue.cue_id)
        original = nodes.get(cue.original_call_id)
        repeated = nodes.get(cue.repeated_call_id)
        store = events.get(cue.cache_store_event_id)
        hit = events.get(cue.cache_hit_event_id)
        if original is None or repeated is None or store is None or hit is None:
            errors.append(f"cue {cue.cue_id} does not derive from actual nodes/events")
            continue
        if original.n != cue.n or repeated.n != cue.n:
            errors.append(f"cue {cue.cue_id} connects different Fibonacci states")
        if not repeated.terminated_at_cache or hit.kind != "cache_hit":
            errors.append(f"cue {cue.cue_id} does not end at a cache hit")
        if store.kind != "store" or store.n != cue.n:
            errors.append(f"cue {cue.cue_id} cites the wrong cache store")
        if store.sequence >= hit.sequence:
            errors.append(f"cue {cue.cue_id} hits cache before its store")

    root = nodes.get(trace.root_call_id)
    if root is None or root.n != trace.target or root.result != trace.result:
        errors.append("root call does not certify the requested result")
    if trace.final_cache.get(trace.target) != trace.result:
        errors.append("final cache does not retain the requested result")
    return DPValidationResult(tuple(errors))


def fibonacci_memo_model(target: int = 7) -> dict[str, object]:
    """Dictionary adapter for existing semantic-model integrations."""

    return build_fibonacci_memo_trace(target).to_payload()


build_top_down_fibonacci_trace = build_fibonacci_memo_trace
top_down_fibonacci_trace = build_fibonacci_memo_trace
build_memoized_fibonacci_trace = build_fibonacci_memo_trace
memoized_fibonacci_trace = build_fibonacci_memo_trace
validate_fibonacci_trace = validate_fibonacci_memo_trace


__all__ = [
    "DPGeometryNode",
    "DPValidationResult",
    "FibonacciCallNode",
    "FibonacciMemoTrace",
    "FibonacciRepeatedStateCue",
    "FibonacciState",
    "FibonacciTraceEvent",
    "build_fibonacci_memo_trace",
    "build_fibonacci_call_tree_preview",
    "build_fibonacci_state_graph",
    "build_memoized_fibonacci_trace",
    "build_top_down_fibonacci_trace",
    "fibonacci_memo_model",
    "memoized_fibonacci_trace",
    "top_down_fibonacci_trace",
    "validate_fibonacci_memo_trace",
    "validate_fibonacci_trace",
]

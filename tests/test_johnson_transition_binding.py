from __future__ import annotations

import ast
import unittest

import numpy as np

from tools import stem_course


class JohnsonTransitionBindingTests(unittest.TestCase):
    @staticmethod
    def graph_helper(name: str, namespace: dict[str, object] | None = None):
        tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
        function_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
        helper_namespace = {} if namespace is None else dict(namespace)
        exec(
            compile(ast.Module(body=[function_node], type_ignores=[]), f"<graph-{name}>", "exec"),
            helper_namespace,
        )
        return helper_namespace[name]

    def test_final_restoration_hold_follows_shortest_paths_ready(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Johnson's Algorithm", "algorithms"),
            13,
        )
        plan = stem_course.build_animation_plan(short)
        ready_beat_index = next(
            index
            for index, beat in enumerate(plan["beats"])
            if "johnson:shortest-paths-ready" in beat.get("semantic_transition_ids", [])
        )
        final_beat_index = next(
            index
            for index, beat in enumerate(plan["beats"])
            if beat.get("scene_state") == "example_takeaway"
        )
        self.assertLess(ready_beat_index, final_beat_index)

        source = stem_course.manim_scene(short, "JohnsonScheduleOrder", plan)
        final_hold = source.split("def resolve_weighted_route", 1)[1].split(
            "resolve_actions.append(resolve_weighted_route)", 1
        )[0]
        self.assertIn("Original distances stay restored: d(u,v) = d'(u,v) - h(u) + h(v).", final_hold)
        self.assertNotIn("All reweighted edges are nonnegative", final_hold)

    def test_dense_route_cursor_trims_endpoints_and_avoids_graph_labels(self) -> None:
        tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
        function_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "graph_cursor_path"
        )

        class Bounds:
            def __init__(self, center=(0.0, 0.0, 0.0), radius=0.0, half_height=None) -> None:
                self.center = np.array(center, dtype=float)
                self.radius = float(radius)
                self.half_height = float(radius if half_height is None else half_height)
                self.submobjects = []

            def move_to(self, center):
                self.center = np.array(center, dtype=float)
                return self

            def get_left(self):
                return self.center + np.array([-self.radius, 0.0, 0.0])

            def get_right(self):
                return self.center + np.array([self.radius, 0.0, 0.0])

            def get_bottom(self):
                return self.center + np.array([0.0, -self.half_height, 0.0])

            def get_top(self):
                return self.center + np.array([0.0, self.half_height, 0.0])

            def get_center(self):
                return self.center

        class Line:
            def __init__(self, start, end) -> None:
                self.start = np.array(start, dtype=float)
                self.end = np.array(end, dtype=float)

            def get_start(self):
                return self.start

            def get_end(self):
                return self.end

            def point_from_proportion(self, alpha):
                return self.start + (self.end - self.start) * float(alpha)

        class VMobject:
            def set_points_as_corners(self, points):
                self.points = np.array(points, dtype=float)
                return self

            def get_start(self):
                return self.points[0]

            def get_end(self):
                return self.points[-1]

        class Circle(Bounds):
            def __init__(self, radius) -> None:
                super().__init__(radius=radius)

        class Node:
            def __init__(self, label) -> None:
                self.submobjects = [Bounds(), label]

            def __getitem__(self, index):
                return self.submobjects[index]

        class Probe:
            boxes_overlap = staticmethod(lambda left, right, pad=0.0: not (
                left.get_right()[0] + pad < right.get_left()[0]
                or right.get_right()[0] + pad < left.get_left()[0]
                or left.get_top()[1] + pad < right.get_bottom()[1]
                or right.get_top()[1] + pad < left.get_bottom()[1]
            ))

        namespace = {"Circle": Circle, "VMobject": VMobject, "math": __import__("math"), "np": np}
        exec(compile(ast.Module(body=[function_node], type_ignores=[]), "<graph-cursor>", "exec"), namespace)
        edge = Line(np.array([0.0, 0.0, 0.0]), np.array([4.0, 0.0, 0.0]))
        edge._semantic_endpoint_names = ("A", "B")
        weight_label = Bounds((2.0, 0.31, 0.0), radius=0.34, half_height=0.25)
        weight_label._persistent_object_id = "edge-label:A->B"
        other_weight_label = Bounds((3.0, 0.0, 0.0), radius=0.26, half_height=0.16)
        other_weight_label._persistent_object_id = "edge-label:C->B"
        edge._weight_label_carrier = weight_label
        edge._graph_label_obstacles = (weight_label, other_weight_label)
        nodes = {
            "A": Node(Bounds((0.0, 0.0, 0.0), radius=0.22)),
            "B": Node(Bounds((4.0, 0.0, 0.0), radius=0.22)),
            "C": Node(Bounds((2.0, 0.0, 0.0), radius=0.20)),
        }

        path = namespace["graph_cursor_path"](Probe(), edge, nodes, samples=61)
        self.assertGreater(path.get_start()[0], nodes["A"][1].get_right()[0] + 0.11)
        self.assertLess(path.get_end()[0], nodes["B"][1].get_left()[0] - 0.11)
        self.assertGreater(path.get_end()[0], path.get_start()[0])
        self.assertLess(np.min(path.points[:, 1]), -0.30)

        cursor = Circle(radius=0.11)
        obstacles = [node[1] for node in nodes.values()] + [weight_label, other_weight_label]
        for point in path.points:
            cursor.move_to(point)
            for obstacle in obstacles:
                self.assertFalse(Probe.boxes_overlap(cursor, obstacle, pad=0.025))

    def test_generated_graph_edges_expose_every_weight_label_to_cursor_routing(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Weighted Shortest Paths", "algorithms"),
            10,
        )
        source = stem_course.manim_scene(short, "WeightedCursorObstacles", stem_course.build_animation_plan(short))

        self.assertIn("graph_label_obstacles = tuple(weight_group)", source)
        self.assertIn("line._graph_label_obstacles = graph_label_obstacles", source)

    def test_metric_annotation_classification_is_structural_and_shared(self) -> None:
        classify = self.graph_helper("cs_graph_uses_metric_annotations")
        self.assertTrue(classify(None, {"mode": "shortest_path", "steps": [{"distances": {"A": 0}}]}))
        self.assertTrue(classify(None, {"mode": "custom", "potentials": {"A": -2}, "steps": []}))
        self.assertFalse(classify(None, {"mode": "dfs", "steps": [{"stack": ["A"]}]}))

        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Weighted Shortest Paths", "algorithms"),
            10,
        )
        source = stem_course.manim_scene(
            short,
            "WeightedMetricAnnotationLayout",
            stem_course.build_animation_plan(short),
        )
        compile(source, "generated_weighted_metric_annotation_layout.py", "exec")
        self.assertIn("metric_graph = self.cs_graph_uses_metric_annotations(semantic)", source)
        self.assertIn("weighted_mode = self.cs_graph_uses_metric_annotations(semantic)", source)
        self.assertGreaterEqual(source.count("self.place_cs_graph_metric_label("), 2)
        diagram_source = source.split("def cs_graph_diagram", 1)[1].split(
            "def cs_bfs_queue_mob", 1
        )[0]
        self.assertNotIn('mode in {"bellman_ford", "dijkstra", "johnson_reweight"}', diagram_source)

    def test_metric_lane_placement_is_generic_and_avoids_graph_obstacles(self) -> None:
        class Bounds:
            def __init__(self, center, half_width=0.35, half_height=0.2) -> None:
                self.center = np.array(center, dtype=float)
                self.half_width = float(half_width)
                self.half_height = float(half_height)

            def get_center(self):
                return self.center

            def get_left(self):
                return self.center + np.array([-self.half_width, 0.0, 0.0])

            def get_right(self):
                return self.center + np.array([self.half_width, 0.0, 0.0])

            def get_bottom(self):
                return self.center + np.array([0.0, -self.half_height, 0.0])

            def get_top(self):
                return self.center + np.array([0.0, self.half_height, 0.0])

            def next_to(self, other, direction, buff=0.14):
                direction = np.array(direction, dtype=float)
                if abs(direction[0]) > abs(direction[1]):
                    distance = other.half_width + self.half_width + buff
                else:
                    distance = other.half_height + self.half_height + buff
                self.center = other.center + direction * distance
                return self

        class Probe:
            boxes_overlap = staticmethod(lambda left, right, pad=0.0: not (
                left.get_right()[0] + pad < right.get_left()[0]
                or right.get_right()[0] + pad < left.get_left()[0]
                or left.get_top()[1] + pad < right.get_bottom()[1]
                or right.get_top()[1] + pad < left.get_bottom()[1]
            ))

        directions = {
            "UP": np.array([0.0, 1.0, 0.0]),
            "RIGHT": np.array([1.0, 0.0, 0.0]),
            "DOWN": np.array([0.0, -1.0, 0.0]),
            "LEFT": np.array([-1.0, 0.0, 0.0]),
            "np": np,
        }
        place = self.graph_helper("place_cs_graph_metric_label", directions)
        nodes = {
            name: Bounds(center, half_width=0.42, half_height=0.42)
            for name, center in {
                "A": (0.0, 2.0, 0.0),
                "B": (1.8, 1.0, 0.0),
                "C": (1.8, -1.0, 0.0),
                "D": (0.0, -2.0, 0.0),
                "E": (-1.8, -1.0, 0.0),
                "F": (-1.8, 1.0, 0.0),
            }.items()
        }
        incident = Bounds((0.0, 0.0, 0.0), half_width=0.05, half_height=2.0)
        incident._semantic_endpoint_names = ("A", "D")
        incident._semantic_edge_id = "A->D"
        carrier = Bounds((0.0, 2.72, 0.0), half_width=0.45, half_height=0.22)
        incident._weight_label_carrier = carrier
        prior = Bounds((-0.91, 2.0, 0.0), half_width=0.35, half_height=0.2)
        metric = Bounds((0.0, 0.0, 0.0))

        place(Probe(), "A", nodes["A"], metric, nodes, {"A->D": incident}, {"F": prior})

        self.assertEqual(metric._graph_annotation_cardinal_lane, "east")
        for obstacle in (incident, carrier, prior):
            self.assertFalse(Probe.boxes_overlap(metric, obstacle, pad=0.04))

    def test_annotation_lane_bounds_reject_potential_edge_weight_overlap(self) -> None:
        tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
        function_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "assert_graph_annotation_lanes"
        )
        namespace: dict[str, object] = {}
        exec(compile(ast.Module(body=[function_node], type_ignores=[]), "<graph-lanes>", "exec"), namespace)

        class Bounds:
            def __init__(self, left: float, bottom: float, right: float, top: float) -> None:
                self.left, self.bottom, self.right, self.top = left, bottom, right, top

            def get_left(self):
                return (self.left, 0.0, 0.0)

            def get_right(self):
                return (self.right, 0.0, 0.0)

            def get_bottom(self):
                return (0.0, self.bottom, 0.0)

            def get_top(self):
                return (0.0, self.top, 0.0)

        class LaneProbe:
            boxes_overlap = staticmethod(lambda left, right, pad=0.0: stem_course.geometry_intrusion_pairs(
                {
                    "left": (left.left, left.bottom, left.right, left.top),
                    "right": (right.left, right.bottom, right.right, right.top),
                },
                pad=pad,
            ) != [])

        edge = Bounds(-0.05, -1.0, 0.05, 1.0)
        edge._semantic_edge_id = "A->C"
        edge._semantic_endpoint_names = ("A", "C")
        edge._weight_label_carrier = Bounds(0.35, -0.2, 0.75, 0.2)
        edge._weight_label_carrier._persistent_object_id = "edge-label:A->C"
        check = namespace["assert_graph_annotation_lanes"]

        clear_metric = Bounds(-0.5, 1.25, 0.5, 1.65)
        clear_metric._graph_annotation_lane = "node-distance"
        clear_metric._graph_annotation_cardinal_lane = "north"
        self.assertTrue(check(LaneProbe(), {}, {"A": clear_metric}, {"A->C": edge}))

        colliding_metric = Bounds(-0.3, -0.3, 0.45, 0.3)
        colliding_metric._graph_annotation_lane = "node-potential"
        colliding_metric._graph_annotation_cardinal_lane = "east"
        with self.assertRaisesRegex(ValueError, "node-potential:east:A/edge-weight"):
            check(LaneProbe(), {}, {"A": colliding_metric}, {"A->C": edge})

        other_metric = Bounds(0.35, 1.25, 1.0, 1.65)
        other_metric._graph_annotation_lane = "node-distance"
        other_metric._graph_annotation_cardinal_lane = "west"
        with self.assertRaisesRegex(ValueError, "node-distance:north:A/node-distance:west:B"):
            check(LaneProbe(), {}, {"A": clear_metric, "B": other_metric}, {})

    def test_every_reweight_action_group_is_present_in_the_semantic_schedule(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Johnson's Algorithm", "algorithms"),
            13,
        )
        plan = stem_course.build_animation_plan(short)
        scheduled_ids = {
            transition_id
            for beat in plan["beats"]
            for transition_id in beat.get("semantic_transition_ids", [])
        }
        expected_reweights = {f"johnson_reweight:{index}" for index in range(1, 6)}

        self.assertTrue(expected_reweights.issubset(scheduled_ids))
        source = stem_course.manim_scene(short, "JohnsonTransitionBinding", plan)
        compile(source, "generated_johnson_transition_binding.py", "exec")
        self.assertIn("transition_groups[transition_id] = step_actions", source)
        self.assertIn("if semantic_event_bindings:", source)
        self.assertIn("def advance_graph_route_event", source)
        self.assertIn("transition_groups[transition_id] = [advance_graph_route_event]", source)
        self.assertIn('event_kind = str(state.get("event", "advance"))', source)
        self.assertIn('geometry.append(active_edge.animate.set_color("#F7C948")', source)
        self.assertIn("cursor_path = self.graph_cursor_path(candidate_edge, nodes)", source)
        self.assertIn("traveler_path = self.graph_cursor_path(active_edge, nodes)", source)
        self.assertNotIn('Circle(radius=0.42, color="#F7C948", stroke_width=7).move_to(candidate_edge.get_start())', source)
        self.assertNotIn("radius=0.18, color=\"#F8FBFF\"", source)
        self.assertNotIn('node.animate.scale(1.2)', source)
        self.assertNotIn('Indicate(metric_group', source)
        self.assertNotIn('Indicate(nodes[left]', source)

    def test_generated_johnson_scene_enforces_separate_annotation_lanes_and_complete_copy(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Johnson's Algorithm", "algorithms"),
            13,
        )
        plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "JohnsonFrameLayout", plan)

        self.assertIn('carrier._graph_annotation_lane = "edge-weight"', source)
        self.assertIn('metric_labels[name]._graph_annotation_lane = "node-potential"', source)
        self.assertGreaterEqual(source.count("self.assert_graph_annotation_lanes(nodes, metric_labels, edge_lookup)"), 2)
        self.assertIn("Each vertex has one fixed potential h(v).", source)
        self.assertNotIn("show each potential", source)
        self.assertNotIn('cue_text = f"run Dijkstra', source)
        route_events = plan["concrete_example"]["renderer_state"]["route_events"]
        self.assertTrue(any(event.get("event") == "dijkstra_trace" for event in route_events))
        self.assertNotIn("which paths...", source)
        self.assertNotIn("every path...", source)
        self.assertGreaterEqual(source.count("self.clean_graph_text_handoff("), 2)
        johnson_route = source.split("if semantic_event_bindings:", 1)[1].split(
            "scheduled_transition_ids =", 1
        )[0]
        self.assertNotIn('Transform(current["cue"], next_cue)', johnson_route)
        self.assertNotIn('Transform(current["cue"], resolved_cue)', johnson_route)


if __name__ == "__main__":
    unittest.main()

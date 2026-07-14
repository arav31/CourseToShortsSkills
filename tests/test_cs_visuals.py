from __future__ import annotations

import math
import unittest

from tools import stem_course


CURATED = {concept.name: concept for concept in stem_course.ALGORITHMS}

MIT_TOPIC_EXPECTATIONS = {
    "Asymptotic complexity": ("cs_array", "complexity", "growth_curves"),
    "Divide and conquer": ("cs_array", "divide", "recursion_tree"),
    "Breadth-first search": ("cs_graph", "graph", "bfs"),
    "Dynamic programming": ("cs_array", "dp", "fibonacci_table"),
    "Direct Access Array": ("cs_array", "array", "direct_access"),
    "Priority Queue": ("cs_graph", "heap", "min_heap_insert"),
    "Shortest Paths": ("cs_graph", "graph", "shortest_path"),
    "Topological Sort": ("cs_graph", "graph", "topological"),
    "Data Structures": ("cs_array", "array", "stack_push_pop"),
    "Running Time": ("cs_array", "complexity", "growth_curves"),
    "Binary Trees": ("cs_graph", "tree", "bst_search"),
    "Hash Tables": ("cs_array", "hash", "separate_chaining"),
    "Linear Time": ("cs_array", "complexity", "growth_curves"),
    "Hash Function": ("cs_array", "hash", "hash_function_mapping"),
    "Sorted Array": ("cs_array", "array", "sorted_insert"),
    "Dynamic Array": ("cs_array", "dynamic_array", "resize_append"),
    "Selection Sort": ("cs_array", "sort", "selection"),
    "Insertion Sort": ("cs_array", "sort", "insertion"),
    "Constant Time": ("cs_array", "complexity", "growth_curves"),
    "Avl Tree": ("cs_graph", "avl", "avl_rotation"),
}

COURSE_18_ROUTE_EXPECTATIONS = {
    "Data Structures": ("array", "stack_push_pop"),
    "Sorting": ("sort", "merge"),
    "Hashing": ("hash", "separate_chaining"),
    "Linear Sorting": ("sort", "counting"),
    "Binary Search Trees": ("tree", "bst_search"),
    "AVL Trees and Rotations": ("avl", "avl_rotation"),
    "Binary Heaps": ("heap", "min_heap_insert"),
    "Breadth-First Search": ("graph", "bfs"),
    "Depth-First Search": ("graph", "dfs"),
    "Weighted Shortest Paths": ("graph", "shortest_path"),
    "Bellman-Ford": ("graph", "bellman_ford"),
    "Dijkstra's Algorithm": ("graph", "dijkstra"),
    "Johnson's Algorithm": ("graph", "johnson_reweight"),
    "Memoization and Recursive Dynamic Programming": ("dp", "fibonacci_table"),
    "Dynamic Programming State Design": ("dp", "grid_paths"),
    "Dynamic Programming Applications": ("dp", "matrix_chain"),
    "Pseudopolynomial Dynamic Programming": ("dp", "knapsack"),
    "Complexity": ("complexity", "growth_curves"),
}


def short_for(topic: str) -> dict[str, object]:
    concept = CURATED.get(topic) or stem_course.source_term_concept(topic, "algorithms")
    return stem_course.concept_to_short(concept, 1)


class CsPlanRoutingTests(unittest.TestCase):
    def test_exact_18_unit_course_route_matrix_is_concept_specific(self) -> None:
        for index, (topic, (expected_family, expected_mode)) in enumerate(
            COURSE_18_ROUTE_EXPECTATIONS.items(),
            start=1,
        ):
            with self.subTest(topic=topic):
                short = stem_course.concept_to_short(
                    stem_course.source_term_concept(topic, "algorithms"),
                    index,
                )
                kind = stem_course.infer_visual_kind(short)
                semantic = stem_course.cs_semantic_data(short, kind)
                self.assertEqual((semantic["family"], semantic["mode"]), (expected_family, expected_mode))
                self.assertTrue(semantic["verified"])

        bfs = stem_course.source_term_concept("Breadth-First Search", "algorithms")
        self.assertIn("d[v]=d[u]+1", bfs.formula.replace(" ", ""))
        self.assertNotIn("min", bfs.formula.lower())
        memo = stem_course.source_term_concept("Memoization and Recursive Dynamic Programming", "algorithms")
        self.assertIn("M[i]", memo.formula)
        self.assertIn("once", memo.formula)

    def test_all_course_routes_bind_runtime_callbacks_across_multiple_core_beats(self) -> None:
        for index, topic in enumerate(COURSE_18_ROUTE_EXPECTATIONS, start=1):
            with self.subTest(topic=topic):
                short = stem_course.concept_to_short(
                    stem_course.source_term_concept(topic, "algorithms"),
                    index,
                )
                plan = stem_course.build_animation_plan(short)
                self.assertGreaterEqual(
                    plan["beats"][-1]["end_seconds"] - plan["beats"][-1]["start_seconds"],
                    stem_course.MIN_READABLE_BEAT_SECONDS - 1 / stem_course.RENDER_TIMELINE_FPS,
                )
                self.assertEqual(plan["beats"][-1]["semantic_transition_ids"], [])
                transitions = plan["semantic_transition_contract"]["transitions"]
                self.assertIn(transitions[-1]["id"], plan["beats"][-2]["semantic_transition_ids"])
                bindings = stem_course.render_runtime_semantic_transition_bindings(plan)
                self.assertGreaterEqual(len(transitions), 2)
                self.assertEqual(
                    {binding["planned_transition_id"] for binding in bindings},
                    {transition["id"] for transition in transitions},
                )
                active_beats = {binding["beat_id"] for binding in bindings}
                self.assertGreaterEqual(len(active_beats), 2)
                source = stem_course.manim_scene(short, f"CourseRoute{index:02d}", plan)
                compile(source, f"generated_course_route_{index:02d}.py", "exec")
                self.assertIn("initialize_render_runtime_trace", source)
                self.assertIn("runtime_callback_finished", source)
                self.assertIn("config.pixel_width = 1080", source)
                self.assertIn("config.pixel_width = 360", source)
                self.assertNotIn("def cs_proof_sweep", source)
                self.assertNotIn("ShowPassingFlash(outline", source)
                self.assertIn('"max_frozen_tail_seconds": 1.25', source)
                self.assertNotIn("play_numeric_rule_visual(mapped", source)

    def test_readable_terminal_is_the_render_duration_contract(self) -> None:
        sorting = stem_course.concept_to_short(
            stem_course.source_term_concept("Sorting", "algorithms"),
            2,
        )
        plan = stem_course.build_animation_plan(sorting)

        self.assertEqual(stem_course.animation_plan_duration(plan), plan["beats"][-1]["end_seconds"])
        self.assertAlmostEqual(
            stem_course.animation_plan_duration(plan),
            stem_course.short_video_pacing(sorting)["total"],
            delta=1 / stem_course.RENDER_TIMELINE_FPS,
        )
        self.assertGreaterEqual(
            plan["beats"][-1]["end_seconds"] - plan["beats"][-1]["start_seconds"],
            stem_course.MIN_READABLE_BEAT_SECONDS - 1 / stem_course.RENDER_TIMELINE_FPS,
        )
        source = stem_course.manim_scene(sorting, "ReadableTerminalContract", plan)
        self.assertNotIn("4.0 / frame_rate + 0.0001", source)
        self.assertIn("observed_frame != target_frame", source)

        for index, topic in enumerate(COURSE_18_ROUTE_EXPECTATIONS, start=1):
            with self.subTest(topic=topic):
                short = stem_course.concept_to_short(
                    stem_course.source_term_concept(topic, "algorithms"),
                    index,
                )
                terminal = [
                    beat
                    for beat in stem_course.canonical_beat_schedule(short)
                    if beat["scene_state"] == "example_takeaway"
                ]
                self.assertEqual(len(terminal), 1)
                self.assertGreater(terminal[0]["result_resolution_seconds"], 0.0)
                self.assertAlmostEqual(
                    terminal[0]["duration"],
                    terminal[0]["readability_floor_seconds"]
                    + terminal[0]["result_resolution_seconds"]
                    + stem_course.MIN_SEMANTIC_FROZEN_TAIL_SECONDS,
                    delta=0.02,
                )

    def test_phone_scale_cs_labels_and_full_beat_motion_are_regression_guarded(self) -> None:
        source = stem_course.manim_scene(
            short_for("Breadth-First Search"),
            "PhoneScaleCsRegression",
            stem_course.build_animation_plan(short_for("Breadth-First Search")),
        )

        self.assertIn('Text(f"d={depth}", font_size=42', source)
        self.assertNotIn('Text(label, font_size=28', source)
        self.assertNotIn('"undiscovered"), ("#F7C948", "queued")', source)
        self.assertIn('Text(f"{metric_prefix}={value_text}", font_size=42', source)
        self.assertIn('Text(str(index), font_size=30', source)
        self.assertIn("def continue_merge_comparison", source)
        self.assertIn("def continue_bfs_layer_scan", source)
        self.assertIn("def continue_bst_path_search", source)
        self.assertIn("def continue_hash_bucket_route", source)
        self.assertIn("def continue_count_prefix_scan", source)
        self.assertIn("def continue_graph_algorithm", source)
        self.assertIn("def continue_avl_balance_scan", source)
        self.assertIn("def continue_heap_sync_scan", source)
        self.assertIn("def continue_dp_state_scan", source)
        self.assertIn("def continue_memo_dependency_scan", source)
        self.assertIn("def continue_complexity_traversal", source)
        self.assertNotIn("cs_proof_sweep", source)

    def test_merge_output_label_tracks_run_geometry_without_overlap(self) -> None:
        short = short_for("Sorting")
        source = stem_course.manim_scene(
            short,
            "MergeOutputLaneGeometry",
            stem_course.build_animation_plan(short),
        )
        merge_block = source.split('if mode == "merge":', 1)[1].split(
            'if mode == "stack_push_pop":', 1
        )[0]

        self.assertIn("def merge_output_lane_label(text_value, frames, lower_guard):", merge_block)
        self.assertIn("label.next_to(frames, DOWN, buff=0.16)", merge_block)
        self.assertIn('self.validate_layout(label, name="merge output lane label")', merge_block)
        self.assertIn('("merge output runs", frames)', merge_block)
        self.assertIn('("merge lower rail", lower_guard)', merge_block)
        self.assertIn(
            'merge_output_lane_label("completed output runs", new_frames, complexity)',
            merge_block,
        )
        self.assertNotIn('move_to(UP * -1.72)', merge_block)
        self.assertNotIn('Text("completed output runs", font_size=31', merge_block)
        self.assertIn("VGroup(*ordered_cells).animate.shift(UP * 0.38)", merge_block)

    def test_every_mit_topic_routes_to_supported_semantic_family(self) -> None:
        for topic, (expected_kind, expected_family, expected_mode) in MIT_TOPIC_EXPECTATIONS.items():
            with self.subTest(topic=topic):
                short = short_for(topic)
                kind = stem_course.infer_visual_kind(short)
                semantic = stem_course.cs_semantic_data(short, kind)

                self.assertEqual(kind, expected_kind)
                self.assertNotEqual(kind, "numeric_rule")
                self.assertEqual(semantic["family"], expected_family)
                self.assertEqual(semantic["mode"], expected_mode)
                self.assertTrue(semantic["verified"])

                animation_plan = stem_course.build_animation_plan(short)
                self.assertEqual(stem_course.animation_plan_contract_errors(animation_plan, short), [])
                self.assertEqual(animation_plan["semantic_support"]["status"], "supported")

    def test_unknown_source_cs_topic_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported source-derived CS topic"):
            stem_course.source_term_concept("Unclassified Widget Lemma", "algorithms")

    def test_mit_fixture_has_no_duplicate_worked_state_sequences(self) -> None:
        examples: dict[tuple[str, str], str] = {}
        for topic in MIT_TOPIC_EXPECTATIONS:
            short = short_for(topic)
            worked = short["worked_example"]
            signature = (
                " ".join(str(worked["setup"]).lower().split()),
                " ".join(str(worked["calculation"]).lower().split()),
            )
            self.assertNotIn(signature, examples, msg=f"{topic} duplicates {examples.get(signature)}")
            examples[signature] = topic

    def test_topological_sort_uses_indegree_invariant_not_relaxation(self) -> None:
        short = short_for("Topological Sort")
        formula = str(short["formula"]).lower()
        semantic = stem_course.cs_semantic_data(short, stem_course.infer_visual_kind(short))

        self.assertIn("indegree", formula)
        self.assertNotIn("d[v]", formula)
        self.assertNotIn("min(d[v]", formula)
        self.assertIn("indegree zero", semantic["invariant"].lower())
        self.assertEqual(semantic["order"], ["A", "B", "C", "D"])

    def test_generated_scene_compiles_with_cs_semantic_helpers(self) -> None:
        short = short_for("Hash Tables")
        animation_plan = stem_course.build_animation_plan(short)
        source = stem_course.manim_scene(short, "HashTableVisualRegression", animation_plan)

        compile(source, "generated_hash_table_scene.py", "exec")
        self.assertIn("def cs_hash_table_mob", source)
        self.assertIn('semantic_family == "hash"', source)
        self.assertIn("MoveAlongPath(token, path)", source)
        self.assertIn("self.register_semantic_transition_actions(transition_groups", source)
        self.assertNotIn("self.configure_cs_state_cycle(table", source)
        self.assertNotIn("play_numeric_rule_visual(mapped", source)


class CsSemanticCorrectnessTests(unittest.TestCase):
    def semantic(self, topic: str) -> dict[str, object]:
        short = short_for(topic)
        return stem_course.cs_semantic_data(short, stem_course.infer_visual_kind(short))

    def test_selection_and_insertion_sort_preserve_values_and_sort(self) -> None:
        selection = self.semantic("Selection Sort")
        insertion = self.semantic("Insertion Sort")

        self.assertEqual(selection["result"], [1, 2, 4, 5])
        self.assertTrue(selection["preserves_values"])
        self.assertEqual([operation["indices"] for operation in selection["operations"]], [[0, 3], [2, 3]])
        self.assertEqual(insertion["result"], [1, 2, 4, 5, 6])
        self.assertTrue(insertion["preserves_values"])
        self.assertEqual(insertion["operations"][-1]["to"], 0)

    def test_divide_and_conquer_accumulates_a_persistent_recursion_tree(self) -> None:
        semantic = self.semantic("Divide and conquer")

        self.assertEqual(semantic["n"], 8)
        self.assertEqual([level["subproblem_count"] for level in semantic["levels"]], [1, 2, 4, 8])
        self.assertEqual([level["subproblem_size"] for level in semantic["levels"]], [8, 4, 2, 1])
        self.assertEqual(semantic["level_work"], [8, 8, 8, 8])
        self.assertEqual(semantic["total_work"], 32)
        self.assertEqual(semantic["resolution"], "Theta(n log n)")
        self.assertTrue(semantic["verified"])

    def test_sorted_and_dynamic_arrays_derive_shifts_and_resize(self) -> None:
        sorted_array = self.semantic("Sorted Array")
        dynamic = self.semantic("Dynamic Array")

        self.assertEqual(sorted_array["insert_index"], 2)
        self.assertEqual(sorted_array["shift_indices"], [3, 2])
        self.assertEqual(sorted_array["result"], [2, 4, 6, 7, 9])
        self.assertEqual(dynamic["capacity_before"], 4)
        self.assertEqual(dynamic["capacity_after"], 8)
        self.assertEqual(dynamic["result"], [3, 8, 1, 6, 5])
        self.assertEqual(len(dynamic["copy_steps"]), 4)

    def test_hash_collisions_are_computed_from_keys(self) -> None:
        semantic = self.semantic("Hash Tables")
        function = self.semantic("Hash Function")

        self.assertEqual([step["index"] for step in semantic["steps"]], [2, 2, 3])
        self.assertEqual(semantic["collision_count"], 1)
        self.assertEqual(semantic["result"], [[], [], [12, 7], [18], []])
        self.assertEqual(function["bucket_count"], 7)
        self.assertEqual([step["index"] for step in function["steps"]], [3, 4, 4])
        self.assertEqual(function["mode"], "hash_function_mapping")

    def test_data_structures_uses_distinct_stack_state_sequence(self) -> None:
        semantic = self.semantic("Data Structures")

        self.assertEqual(semantic["states"], [[4, 7, 2], [4, 7, 2, 9], [4, 7, 2]])
        self.assertEqual(semantic["popped"], 9)
        self.assertIn("lifo", semantic["invariant"].lower())

    def test_graph_frontier_relaxation_and_topological_state_are_exact(self) -> None:
        shortest = self.semantic("Shortest Paths")
        topological = self.semantic("Topological Sort")
        bfs = self.semantic("Breadth-first search")

        self.assertEqual(shortest["distances"], {"A": 0.0, "B": 3.0, "C": 1.0, "D": 4.0})
        self.assertIn(
            {"from": "C", "to": "B", "old": 4.0, "new": 3.0, "distances": {"A": 0.0, "B": 3.0, "C": 1.0, "D": None}},
            shortest["steps"],
        )
        self.assertEqual(topological["order"], ["A", "B", "C", "D"])
        self.assertFalse(topological["cycle"])
        self.assertEqual(bfs["layers"], [["A"], ["B", "C"], ["D", "E"]])

    def test_bfs_queue_discovery_processing_and_predecessors_are_exact(self) -> None:
        bfs = self.semantic("Breadth-first search")

        self.assertEqual(bfs["states"][0]["event"], "enqueue A")
        self.assertEqual(bfs["states"][0]["queue"], ["A"])
        self.assertEqual(bfs["states"][0]["discovered"], ["A"])
        self.assertEqual(bfs["states"][0]["processed"], [])

        enqueue_bc = next(state for state in bfs["states"] if state["event"] == "enqueue B, C")
        self.assertEqual(enqueue_bc["queue"], ["B", "C"])
        self.assertEqual(enqueue_bc["discovered"], ["A", "B", "C"])
        self.assertEqual(enqueue_bc["processed"], [])
        self.assertEqual(enqueue_bc["predecessor"], {"B": "A", "C": "A"})

        after_b = next(state for state in bfs["states"] if state["event"] == "process B")
        self.assertEqual(after_b["queue"], ["C", "D"])
        self.assertEqual(after_b["processed"], ["A", "B"])
        self.assertEqual(after_b["predecessor"]["D"], "B")

        self.assertEqual([step["dequeue"] for step in bfs["steps"]], ["A", "B", "C", "D", "E"])
        self.assertEqual(bfs["predecessor"], {"B": "A", "C": "A", "D": "B", "E": "C"})
        self.assertEqual(bfs["distances"], {"A": 0, "B": 1, "C": 1, "D": 2, "E": 2})
        self.assertEqual(bfs["states"][-1]["processed"], ["A", "B", "C", "D", "E"])
        self.assertEqual(bfs["states"][-1]["queue"], [])

    def test_dfs_and_weighted_algorithms_have_distinct_correct_semantics(self) -> None:
        dfs = self.semantic("Depth-First Search")
        bellman_ford = self.semantic("Bellman-Ford")
        dijkstra = self.semantic("Dijkstra's Algorithm")
        johnson = self.semantic("Johnson's Algorithm")

        self.assertEqual(dfs["mode"], "dfs")
        self.assertEqual(dfs["order"], ["A", "B", "D", "E", "C"])
        self.assertEqual(dfs["finish_order"], ["E", "D", "B", "C", "A"])
        self.assertTrue(all(step["action"] in {"push", "finish"} for step in dfs["steps"]))

        self.assertEqual(bellman_ford["mode"], "bellman_ford")
        self.assertEqual(bellman_ford["distances"], {"A": 0.0, "B": 4.0, "C": 2.0, "D": 5.0})
        self.assertFalse(bellman_ford["negative_cycle"])
        self.assertTrue(any(step["pass"] == 1 and step["to"] == "C" and step["new"] == 2.0 for step in bellman_ford["steps"]))
        self.assertEqual(bellman_ford["route_events"][-1]["event"], "negative_cycle_check")
        self.assertTrue(all(step["display_label"].startswith("Pass ") for step in bellman_ford["steps"]))

        self.assertEqual(dijkstra["mode"], "dijkstra")
        self.assertEqual(dijkstra["settled"], ["A", "C", "B", "D"])
        self.assertEqual(dijkstra["steps"][0]["old_display"], "∞")
        self.assertEqual(dijkstra["steps"][0]["new_display"], "4")
        self.assertTrue(all(step["display_label"] for step in dijkstra["steps"]))
        self.assertTrue(all(step["label_replacements"] for step in dijkstra["steps"]))
        self.assertTrue(all("extracted" in step and "frontier" in step and "settled" in step for step in dijkstra["steps"]))
        self.assertEqual(johnson["mode"], "johnson_reweight")
        self.assertEqual(johnson["potentials"], {"A": 0.0, "B": -2.0, "C": 0.0, "D": -1.0})
        self.assertEqual([edge["weight"] for edge in johnson["reweighted_edges"]], [0.0, 4.0, 1.0, 1.0, 0.0])
        self.assertEqual(
            [step["new_display"] for step in johnson["steps"]],
            [edge["display_weight"] for edge in johnson["reweighted_edges"]],
        )
        self.assertTrue(
            all(step["persistent_object_id"].startswith("edge-label:") for step in johnson["steps"])
        )
        self.assertTrue(johnson["verified"])
        self.assertEqual(johnson["route_events"][0]["event"], "potential_phase_start")
        self.assertEqual(johnson["route_events"][-1]["event"], "shortest_paths_ready")

    def test_dp_course_units_use_different_state_spaces(self) -> None:
        grid = self.semantic("Dynamic Programming State Design")
        matrix_chain = self.semantic("Dynamic Programming Applications")
        knapsack = self.semantic("Pseudopolynomial Dynamic Programming")

        self.assertEqual(grid["mode"], "grid_paths")
        self.assertEqual(grid["table_values"], [[1, 1, 1, 1], [1, 2, 3, 4], [1, 3, 6, 10]])
        self.assertEqual(matrix_chain["mode"], "matrix_chain")
        self.assertEqual(matrix_chain["result_value"], 4500)
        self.assertEqual(len(matrix_chain["updates"]), 3)
        self.assertTrue(matrix_chain["formula_matches_example"])
        self.assertNotIn("\\", matrix_chain["formula_text"])
        self.assertEqual(knapsack["mode"], "knapsack")
        self.assertEqual(knapsack["result_value"], 8)
        self.assertEqual(len(knapsack["updates"]), 18)
        self.assertTrue(knapsack["formula_matches_example"])
        self.assertEqual(
            {(update["row"], update["column"]) for update in knapsack["updates"]},
            {(row, column) for row in range(1, 4) for column in range(1, 7)},
        )
        self.assertEqual(len({grid["mode"], matrix_chain["mode"], knapsack["mode"]}), 3)

    def test_grid_dp_updates_use_one_stable_cell_namespace(self) -> None:
        short = short_for("Dynamic Programming State Design")
        grid = self.semantic("Dynamic Programming State Design")
        updates = grid["updates"]

        self.assertTrue(updates)
        self.assertTrue(all(update["cell_id"].startswith(stem_course.DP_CELL_ID_NAMESPACE + ":") for update in updates))
        self.assertEqual(len({update["cell_id"] for update in updates}), len(updates))
        self.assertTrue(all(len(update["source_cell_ids"]) == 2 for update in updates))
        self.assertTrue(
            all(
                source_id.startswith(stem_course.DP_CELL_ID_NAMESPACE + ":")
                for update in updates
                for source_id in update["source_cell_ids"]
            )
        )

        plan = stem_course.build_animation_plan(short)
        transition_ids = {
            object_id
            for transition in plan["semantic_transition_contract"]["transitions"]
            for object_id in transition["persistent_object_ids"]
            if object_id.startswith(stem_course.DP_CELL_ID_NAMESPACE + ":")
        }
        self.assertEqual(transition_ids, {update["cell_id"] for update in updates})
        source = stem_course.manim_scene(short, "GridCellIdentity", plan)
        self.assertNotIn("final None", source)
        self.assertIn("routes reach the bottom-right destination", source)
        self.assertNotIn('f"final {final_cell_id}', source)
        self.assertNotIn("dp-cell:", source)

    def test_linear_sorting_uses_count_buckets_not_merge_sort(self) -> None:
        counting = self.semantic("Linear Sorting")

        self.assertEqual(counting["mode"], "counting")
        self.assertEqual(counting["counts"], [1, 2, 2, 2])
        self.assertEqual(counting["result"], [0, 1, 1, 2, 2, 3, 3])
        self.assertEqual(counting["bucket_starts"], [0, 1, 3, 5])
        self.assertEqual(
            [step["formula"] for step in counting["prefix_steps"]],
            [
                "start[0] = 0",
                "start[1] = start[0] + count[0] = 1",
                "start[2] = start[1] + count[1] = 3",
                "start[3] = start[2] + count[2] = 5",
            ],
        )
        self.assertTrue(counting["verified"])

    def test_counting_sort_preserves_duplicate_item_identity_stably(self) -> None:
        short = short_for("Linear Sorting")
        counting = self.semantic("Linear Sorting")
        items = counting["items"]
        placements = counting["placements"]
        result_items = counting["result_items"]

        self.assertEqual(len({item["item_id"] for item in items}), len(items))
        self.assertEqual({placement["item_id"] for placement in placements}, {item["item_id"] for item in items})
        self.assertEqual(sorted(placement["output_index"] for placement in placements), list(range(len(items))))
        self.assertEqual(
            {
                key: [item["input_index"] for item in result_items if item["value"] == key]
                for key in (1, 2, 3)
            },
            {1: [1, 6], 2: [2, 5], 3: [0, 3]},
        )
        bucket_indices = [index for bucket in counting["buckets"] for index in bucket["output_indices"]]
        self.assertEqual(len(bucket_indices), len(set(bucket_indices)))
        self.assertTrue(counting["stable"])
        self.assertTrue(counting["preserves_item_ids"])
        self.assertTrue(counting["bucket_ranges_non_overlapping"])

        plan = stem_course.build_animation_plan(short)
        contract = plan["semantic_transition_contract"]
        placement_transitions = [
            transition
            for transition in contract["transitions"]
            if transition["kind"] == "stable_output_placement"
        ]
        prefix_transitions = [
            transition
            for transition in contract["transitions"]
            if transition["kind"] == "prefix_output_start"
        ]
        self.assertEqual(len(prefix_transitions), len(counting["universe"]))
        self.assertLess(
            contract["transitions"].index(prefix_transitions[-1]),
            contract["transitions"].index(placement_transitions[0]),
        )
        self.assertEqual(len(placement_transitions), len(items))
        self.assertEqual(
            {transition["persistent_object_ids"][-1] for transition in placement_transitions},
            {item["item_id"] for item in items},
        )
        source = stem_course.manim_scene(short, "StableCountingIdentity", plan)
        compile(source, "generated_stable_counting.py", "exec")
        self.assertIn("MoveAlongPath(tile, route)", source)
        self.assertIn("def reveal_bucket_start", source)
        self.assertIn("counting:prefix:", source)
        self.assertIn("output_positions[output_index]", source)
        self.assertNotIn("Transform(input_row", source)

    def test_new_cs_routes_generate_compilable_dedicated_scenes(self) -> None:
        markers = {
            "Depth-First Search": 'if mode == "dfs":',
            "Bellman-Ford": "def preview_weighted_edge",
            "Johnson's Algorithm": 'elif mode == "johnson_reweight":',
            "Dynamic Programming State Design": 'dp_mode != "fibonacci_table"',
            "Pseudopolynomial Dynamic Programming": "fill_dp_cell",
            "Linear Sorting": 'if mode == "counting":',
        }
        for index, (topic, marker) in enumerate(markers.items(), start=1):
            with self.subTest(topic=topic):
                short = short_for(topic)
                source = stem_course.manim_scene(short, f"NewCsRoute{index}", stem_course.build_animation_plan(short))
                compile(source, f"generated_new_cs_{index}.py", "exec")
                self.assertIn(marker, source)
                if topic == "Depth-First Search":
                    self.assertIn("def advance_graph_step", source)
                    self.assertIn('stack = " > ".join', source)
                    self.assertIn('finished = {str(name)', source)
                    self.assertIn('current = {"edge": None, "cue": state_cue, "path": dfs_path_state}', source)
                    self.assertIn("self.register_semantic_actions(actions)", source)
                    self.assertNotIn("review_state = self.cs_graph_state_mob", source)
                    self.assertNotIn("distance_labels = {}", source)
                if topic == "Johnson's Algorithm":
                    self.assertIn("def preview_weighted_edge", source)
                    self.assertIn("cursor_path = self.graph_cursor_path(candidate_edge, nodes)", source)
                    self.assertIn("MoveAlongPath(packet, cursor_path)", source)
                    self.assertIn('metric_prefix = "h"', source)
                    self.assertIn("active_edge._weight_label_carrier", source)
                    self.assertIn("carrier.become(replacement)", source)
                if topic in {"Dynamic Programming State Design", "Pseudopolynomial Dynamic Programming"}:
                    self.assertNotIn("def preview_dp_dependencies", source)
                    self.assertIn("dependency_halo = SurroundingRectangle", source)
                    self.assertIn("ArcBetweenPoints(source.get_center(), cells[target].get_center()", source)
                    self.assertIn("radius=0.31", source)
                    self.assertIn('f"{numeric_source_value / 1000:g}k"', source)
                    self.assertIn("token = VGroup(disk, token_label).move_to(path.get_start())", source)
                    self.assertIn("MoveAlongPath(token, path)", source)
                    self.assertIn("self.semantic_timed_segments(", source)
                    self.assertIn("(0.20, 0.64, 0.16)", source)
                    self.assertIn("(0.76, 0.24)", source)
                    self.assertIn('cells[target][0].animate.set_fill("#7EE787"', source)
                    self.assertIn("value_mobs[target].animate.set_opacity(1.0)", source)
                    self.assertIn("restore_sources", source)
                    self.assertNotIn("FadeIn(value_mobs[target]", source)
                    self.assertNotIn("token = source.copy()", source)
                    self.assertIn("self.register_semantic_transition_actions(transition_groups", source)
                    self.assertIn("compact_transition_mode = len(visible_updates) >= 12", source)
                    self.assertIn("transition_groups[transition_id] = [fill_dp_cell]", source)
                    self.assertIn("def seal_dp_result", source)
                    seal_result = source[source.index("def seal_dp_result"):source.index("takeaway_actions.append(seal_dp_result)")]
                    self.assertIn("self.semantic_timed_segments(", seal_result)
                    self.assertIn("(0.24, 0.76)", seal_result)
                    self.assertNotIn("run_time - handoff_time", seal_result)
                    self.assertNotIn("token = Dot(path.get_start(), radius=0.13", source)
                    if topic == "Pseudopolynomial Dynamic Programming":
                        self.assertIn("def animate_knapsack_decision", source)
                        self.assertIn('for choice, color in (("exclude", "#58A6FF"), ("include", "#A371F7"))', source)
                        self.assertIn('decision_boxes[winner_choice].animate.set_stroke("#7EE787", width=8)', source)
                    self.assertIn("decision_rail.animate.set_opacity(0.74)", source)
                if topic == "Linear Sorting":
                    self.assertIn("tile._persistent_object_id = str(item.get(\"item_id\"))", source)
                    self.assertIn("MoveAlongPath(packet, path)", source)
                    self.assertIn("MoveAlongPath(tile, route)", source)
                    self.assertIn("Counting-sort output slots overlap", source)
                    self.assertIn("self.register_semantic_transition_actions(transition_groups", source)
                    self.assertNotIn("Transform(input_row", source)

    def test_proof_surface_contract_requests_reflow_for_incompatible_aspect(self) -> None:
        layout = stem_course.proof_surface_layout(4.0, 2.5, "dp")
        contract = layout["contract"]

        self.assertGreater(float(layout["scale"]), 1.2)
        self.assertTrue(layout["requires_reflow"])
        self.assertFalse(layout["minimum_satisfied"])
        self.assertTrue(layout["maximum_satisfied"])
        self.assertFalse(layout["labels_included_in_bounds"])
        self.assertLessEqual(
            float(layout["height_occupancy"]),
            float(contract["max_height_occupancy"]),
        )

        applications = {
            "Depth-First Search": 'self.register_portrait_role("core_proof", graph_surface',
            "Selection Sort": 'self.proof_surface_layout(row, "sort"',
            "Linear Sorting": 'self.proof_surface_layout(counting_surface, "sort"',
            "Dynamic Programming Applications": 'self.register_portrait_role("core_proof", table_group',
        }
        for index, (topic, marker) in enumerate(applications.items(), start=1):
            with self.subTest(topic=topic):
                short = short_for(topic)
                source = stem_course.manim_scene(
                    short,
                    f"ProofSurfaceContract{index}",
                    stem_course.build_animation_plan(short),
                )
                self.assertIn(marker, source)

    def test_cs_title_retires_and_proof_surface_owns_later_beats(self) -> None:
        short = short_for("Pseudopolynomial Dynamic Programming")
        source = stem_course.manim_scene(
            short,
            "CsNarrativeRetirement",
            stem_course.build_animation_plan(short),
        )
        construct = source.split("    def construct(self):", 1)[1]
        cs_example = source.split('cs_kinds = {"cs_array", "cs_graph", "state_machine"}', 1)[1].split(
            'if getattr(self, "_semantic_story_live", False) and kind in physics_kinds:',
            1,
        )[0]

        self.assertIn("retired_title = [title] if cs_visual and title in self.mobjects else []", construct)
        self.assertIn("outgoing_formula_text = [hook] + retired_title", construct)
        self.assertLess(construct.index("outgoing_formula_text ="), construct.index('self.hold_scene_state("core_formula"'))
        self.assertIn("intuition, intuition_transition_seconds = self.present_cue_pages(\n                formula,", construct)
        self.assertLess(
            construct.index("intuition, intuition_transition_seconds = self.present_cue_pages(\n                formula,"),
            construct.index('self.hold_scene_state("core_idea", stage_index=0'),
        )
        self.assertNotIn("stage_setup_sequence", cs_example)
        self.assertNotIn("stage_bottom_sequence", cs_example)
        self.assertEqual(cs_example.count("self.hold_scene_state(state, stage_index"), 1)

    def test_dfs_and_knapsack_change_large_persistent_state_regions(self) -> None:
        dfs_short = short_for("Depth-First Search")
        dfs = self.semantic("Depth-First Search")
        dfs_stacks = [tuple(step.get("stack", [])) for step in dfs["steps"]]
        dfs_plan = stem_course.build_animation_plan(dfs_short)
        dfs_transitions = dfs_plan["semantic_transition_contract"]["transitions"]
        dfs_source = stem_course.manim_scene(dfs_short, "DfsMotionFootprint", dfs_plan)

        self.assertGreaterEqual(max(len(stack) for stack in dfs_stacks), 4)
        self.assertTrue(all(left != right for left, right in zip(dfs_stacks, dfs_stacks[1:])))
        self.assertTrue(
            all(
                "graph:dfs:path-state" in transition["persistent_object_ids"]
                for transition in dfs_transitions
            )
        )
        self.assertIn('width=7.30', dfs_source)
        self.assertIn('Transform(current["path"], next_path_state)', dfs_source)
        self.assertIn("MoveAlongPath(path_packet, path_route)", dfs_source)

        knapsack_short = short_for("Pseudopolynomial Dynamic Programming")
        knapsack = self.semantic("Pseudopolynomial Dynamic Programming")
        knapsack_plan = stem_course.build_animation_plan(knapsack_short)
        knapsack_source = stem_course.manim_scene(
            knapsack_short,
            "KnapsackMotionFootprint",
            knapsack_plan,
        )
        self.assertTrue(all(update.get("active_row_state") for update in knapsack["updates"]))
        self.assertTrue(
            all(
                {"knapsack:active-row-state", "knapsack:decision-state"}.issubset(
                    transition["persistent_object_ids"]
                )
                for transition in knapsack_plan["semantic_transition_contract"]["transitions"]
            )
        )
        for marker in (
            "def knapsack_active_state_mob",
            "active_row_outline",
            "active_cell_selector",
            "active_item_state.become(next_active_item)",
            "decision_values[choice].become(decision_value_targets[choice])",
        ):
            self.assertIn(marker, knapsack_source)

    def test_knapsack_choice_panels_keep_contrast_safe_dark_fills(self) -> None:
        short = short_for("Pseudopolynomial Dynamic Programming")
        source = stem_course.manim_scene(
            short,
            "KnapsackChoicePanelContrast",
            stem_course.build_animation_plan(short),
        )
        knapsack_block = source.split('if dp_mode == "knapsack":', 1)[1].split(
            "updates = list(semantic.get(\"updates\", []))", 1
        )[0]
        decision_block = source.split("def animate_knapsack_decision", 1)[1].split(
            "for update_index, update in enumerate(visible_updates):", 1
        )[0]

        self.assertIn('decision_panel_fill = "#141D34"', knapsack_block)
        self.assertIn("fill_color=decision_panel_fill", knapsack_block)
        self.assertIn(
            'set_fill(decision_panel_fill, opacity=0.96).set_stroke("#7EE787", width=7)',
            decision_block,
        )
        self.assertIn(
            'set_fill(decision_panel_fill, opacity=0.86).set_stroke("#7D8590", width=4)',
            decision_block,
        )
        self.assertNotIn('box.animate.set_fill("#7EE787"', decision_block)
        self.assertNotIn('box.animate.set_fill("#FF7B72"', decision_block)

    def test_reserved_proof_geometry_has_no_intrusion(self) -> None:
        groups = (
            ("dp_active_item", "dp_table", "dp_decision", "dp_cue"),
            ("sort_surface", "sort_cue"),
            ("graph_surface", "graph_cue"),
        )
        for names in groups:
            regions = {
                name: stem_course.PROOF_SURFACE_AUXILIARY_LANES[name]
                for name in names
            }
            self.assertEqual(stem_course.geometry_intrusion_pairs(regions, pad=0.06), [])

        overlapping = {"table": (0.0, 0.0, 2.0, 2.0), "cue": (1.5, 1.5, 3.0, 3.0)}
        self.assertEqual(
            stem_course.geometry_intrusion_pairs(overlapping),
            [("table", "cue")],
        )

        short = short_for("Dynamic Programming Applications")
        source = stem_course.manim_scene(
            short,
            "DpGeometryIntrusion",
            stem_course.build_animation_plan(short),
        )
        self.assertIn("self.assert_layout_disjoint", source)
        self.assertIn('("matrix comparison", comparison_guard)', source)

    def test_dp_scene_has_one_compact_formula_carrier(self) -> None:
        short = short_for("Dynamic Programming Applications")
        source = stem_course.manim_scene(
            short,
            "MatrixChainFormulaCarrier",
            stem_course.build_animation_plan(short),
        )
        dp_block = source.split('if semantic_family == "dp":', 1)[1].split(
            'if kind == "state_machine":', 1
        )[0]

        self.assertNotIn("formula = self.formula_block", dp_block)
        self.assertIn("def trace_matrix_chain_candidate", dp_block)
        self.assertIn("def compare_matrix_chain_candidates", dp_block)
        self.assertIn("source_outlines = VGroup", dp_block)
        self.assertIn("winning_outlines = VGroup", dp_block)
        self.assertIn("def matrix_chain_candidate_strip", dp_block)
        self.assertIn("def seal_matrix_chain_winner", dp_block)
        self.assertIn("winner_route_coordinates", dp_block)
        self.assertIn("MoveAlongPath(selector, selector_path)", dp_block)
        self.assertIn("comparison_strip.animate.shift(UP * 0.12)", dp_block)
        self.assertNotIn("winning_group = VGroup", dp_block)
        self.assertIn("verify_actions + [finish_dp_table]", dp_block)
        self.assertIn(
            "self.formula_block('C(i,j) = \\\\min(\\\\text{left}+\\\\text{right}+\\\\text{merge})'",
            source,
        )

    def test_heap_and_avl_operations_recompute_structure(self) -> None:
        heap = self.semantic("Priority Queue")
        avl = self.semantic("Avl Tree")
        tree = self.semantic("Binary Trees")

        self.assertEqual(heap["result"], [1, 4, 2, 9, 6, 7])
        self.assertEqual([swap["indices"] for swap in heap["swaps"]], [[5, 2], [2, 0]])
        self.assertEqual(avl["rotation"], "right")
        self.assertEqual(avl["root"], 20)
        self.assertEqual(avl["inorder"], [10, 20, 30])
        self.assertEqual(tree["search_path"], [4, 2, 3])
        self.assertTrue(tree["found"])

    def test_heap_array_and_fixed_topology_stay_synchronized(self) -> None:
        heap = self.semantic("Priority Queue")
        expected_states = [
            [2, 4, 7, 9, 6],
            [2, 4, 7, 9, 6, 1],
            [2, 4, 1, 9, 6, 7],
            [1, 4, 2, 9, 6, 7],
        ]

        self.assertEqual(heap["states"], expected_states)
        self.assertTrue(heap["topology_is_clean"])
        for state in heap["synchronized_states"]:
            with self.subTest(state=state["array"]):
                self.assertEqual(state["tree_values"], state["array"])
                self.assertEqual(state["edge_count"], len(state["array"]) - 1)
                self.assertEqual(len({tuple(edge) for edge in state["edges"]}), state["edge_count"])
                self.assertEqual(state["edges"], [[(index - 1) // 2, index] for index in range(1, len(state["array"]))])

    def test_direct_access_has_one_address_jump_and_no_scan_trace(self) -> None:
        direct = self.semantic("Direct Access Array")

        self.assertEqual(direct["initial"], [4, 7, 2, 9])
        self.assertEqual(direct["access_index"], 1)
        self.assertEqual(direct["result"], 7)
        self.assertEqual(direct["address_expression"], "base + 1 * cellsize")
        self.assertEqual(direct["highlight_trace"], [1])
        self.assertEqual(direct["untouched_indices"], [0, 2, 3])

    def test_complexity_and_dp_values_drive_the_visual(self) -> None:
        complexity = self.semantic("Asymptotic complexity")
        linear = self.semantic("Linear Time")
        constant = self.semantic("Constant Time")
        dp = self.semantic("Dynamic programming")

        self.assertEqual(complexity["target_n"], 1000)
        self.assertEqual(complexity["n_values"], [2, 10, 100, 1000])
        self.assertEqual(set(complexity["series"]), {"O(n log n)", "O(n^2)"})
        self.assertEqual(complexity["exact_worked_values"]["n_log2_n"], round(1000 * math.log2(1000)))
        self.assertEqual(complexity["exact_worked_values"]["n_log2_n_display"], 10000)
        self.assertEqual(complexity["exact_worked_values"]["n_squared"], 1000000)
        recomputed_winner = min(complexity["target_values"], key=complexity["target_values"].get)
        self.assertEqual(recomputed_winner, "O(n log n)")
        self.assertEqual(complexity["selected_curve"], recomputed_winner)
        self.assertEqual(complexity["highlight_target"]["series"], recomputed_winner)
        self.assertEqual(complexity["highlight_target"]["value"], round(1000 * math.log2(1000)))
        self.assertEqual(complexity["highlight_target"]["color"], complexity["series_colors"][recomputed_winner])
        self.assertAlmostEqual(complexity["highlight_target"]["y"], math.log10(round(1000 * math.log2(1000))))
        self.assertLess(complexity["highlight_target"]["y"], complexity["plot_points"]["O(n^2)"][-1]["y"])
        self.assertEqual(set(linear["series"]), {"O(n)"})
        self.assertEqual(linear["n_values"], [4, 8, 16])
        self.assertEqual(linear["target_n"], 16)
        self.assertEqual(set(constant["series"]), {"O(1)"})
        self.assertEqual(dp["result"], [0, 1, 1, 2, 3, 5])
        self.assertEqual(dp["dependencies"], {2: [0, 1], 3: [1, 2], 4: [2, 3], 5: [3, 4]})
        self.assertEqual(dp["steps"][-1]["sources"], [3, 4])
        self.assertEqual(dp["steps"][-1]["source_values"], [2, 3])
        self.assertEqual(dp["steps"][-1]["value"], 5)

    def test_generic_complexity_preserves_every_declared_series_and_sample(self) -> None:
        complexity = self.semantic("Complexity")

        self.assertEqual(complexity["declared_series"], ["O(1)", "O(n)", "O(n log n)", "O(n^2)"])
        self.assertEqual(complexity["n_values"], [2, 4, 8, 16])
        self.assertEqual(complexity["target_n"], 16)
        self.assertEqual(
            complexity["target_values"],
            {"O(1)": 1, "O(n)": 16, "O(n log n)": 64, "O(n^2)": 256},
        )
        self.assertTrue(complexity["verified"])

    def test_fibonacci_formula_matches_example_and_repeated_calls_collapse(self) -> None:
        short = short_for("Dynamic programming")
        dp = stem_course.cs_semantic_data(short, stem_course.infer_visual_kind(short))

        self.assertEqual(short["formula"], r"F_i=F_{i-1}+F_{i-2}")
        self.assertEqual(dp["formula_latex"], short["formula"])
        self.assertTrue(dp["formula_matches_example"])
        self.assertEqual(dp["naive_call_count"], 15)
        self.assertEqual(dp["naive_call_counts"][3], 2)
        self.assertEqual(dp["naive_call_counts"][2], 3)
        self.assertEqual(dp["repeated_states"], [2, 3])
        self.assertEqual(dp["saved_state_count"], 6)

    def test_rejected_cs_scenes_compile_with_dedicated_semantic_renderers(self) -> None:
        expectations = {
            "Asymptotic complexity": "def reveal_target_comparison",
            "Divide and conquer": "def accumulate_recursion_level",
            "Breadth-first search": "for target_state in visual_states[1:]",
            "Dynamic programming": "def expand_recursion_level",
            "Direct Access Array": "base_address = 4096",
            "Priority Queue": "def append_key",
        }
        for index, (topic, source_marker) in enumerate(expectations.items(), start=1):
            with self.subTest(topic=topic):
                short = short_for(topic)
                animation_plan = stem_course.build_animation_plan(short)
                source = stem_course.manim_scene(short, f"CsRejectedCase{index}", animation_plan)
                compile(source, f"generated_{index}.py", "exec")
                self.assertIn(source_marker, source)
                if topic == "Dynamic programming":
                    self.assertIn('"F[i] = F[i - 1] + F[i - 2]"', source)
                    self.assertIn("def expose_repeated_calls", source)
                    self.assertIn("def fill_saved_state", source)
                    self.assertIn("dependency_arrows", source)
                    self.assertIn("lane_y = max(float(start[1]), float(finish[1]))", source)
                    self.assertIn("cells[int(source_index)][0].get_top() + UP * 0.14", source)
                    self.assertIn("Dot(path.get_start(), radius=0.3", source)
                    self.assertIn("def morph_tree_to_state_graph", source)
                    self.assertIn("TransformFromCopy(VGroup(*sources), dag_node)", source)
                    self.assertIn("AnimationGroup(Create(recursion_edges[node_id]), FadeIn(recursion_nodes[node_id]", source)
                    self.assertIn("FadeIn(dag_mini_map)", source)
                    self.assertIn("table.animate.set_opacity(1.0)", source)
                    self.assertIn("geometry_time, packet_time, cleanup_time, reveal_time = self.semantic_timed_segments(", source)
                    self.assertIn("Transform(active_selector, selector_target)", source)
                    self.assertNotIn("token = value_labels[source_index].copy()", source)
                    dp_block = source.split('if semantic_family == "dp":', 1)[1].split('if kind == "state_machine":', 1)[0]
                    self.assertIn("dp_sustain_selector = SurroundingRectangle", dp_block)
                    self.assertIn("dp_dependency_frontier = SurroundingRectangle", dp_block)
                    self.assertIn("dp_sustain_selector.animate.move_to(cell)", dp_block)
                    self.assertNotIn("cell.animate.shift(UP * 0.58)", dp_block)
                    self.assertNotIn('Transform(current["header"]', dp_block)
                    self.assertIn('current["phase"] = "dag"', dp_block)
                    self.assertIn("MoveAlongPath(token, path)", source)
                    self.assertNotIn("collapse_tokens", dp_block)
                    self.assertNotIn("commit_token", dp_block)
                    self.assertNotIn("scan_path", dp_block)
                if topic == "Asymptotic complexity":
                    active_complexity = source.split('if semantic_family == "complexity":', 1)[1].split('if semantic_family == "_legacy_complexity":', 1)[0]
                    self.assertIn("x_length=6.75", active_complexity)
                    self.assertIn("y_length=4.08", active_complexity)
                    self.assertIn("target_group = VGroup", active_complexity)
                    self.assertIn("def reveal_target_comparison", active_complexity)
                    self.assertIn('f"{target_n} x log2({target_n})', active_complexity)
                    self.assertIn("calculation_band = VGroup", active_complexity)
                    self.assertIn("UP * -1.72", active_complexity)
                    self.assertIn("calculation_band.animate.set_opacity(0.82)", active_complexity)
                    self.assertNotIn("input_tracker", active_complexity)
                    self.assertNotIn("always_redraw", active_complexity)
                    self.assertNotIn("sweep_targets", active_complexity)
                    self.assertNotIn("def sweep_shared_input", active_complexity)
                    self.assertIn("def reveal_growth_conclusion", active_complexity)
                    self.assertIn("self.register_semantic_transition_actions(transition_groups", active_complexity)
                if topic == "Divide and conquer":
                    self.assertIn('if semantic_family == "divide":', source)
                    self.assertIn("def accumulate_recursion_level", source)
                    self.assertIn("def resolve_divide_recurrence", source)
                    self.assertIn('transition_groups[f"divide:level:{level_index}"]', source)
                    self.assertIn('transition_groups["divide:resolve"]', source)
                    self.assertIn("tree_surface = VGroup(*edges.values(), *node_mobs.values(), total_labels)", source)
                    self.assertIn("ReplacementTransform(carrier, child, path_arc=", source)
                    self.assertIn("MoveAlongPath(packet, path)", source)
                    self.assertIn("LaggedStart(*work_packets, lag_ratio=0.1)", source)
                    self.assertIn("rail_target = total_labels[target_index].get_left()", source)
                    self.assertIn("LaggedStart(*combine_motion, lag_ratio=0.12)", source)
                    self.assertIn("combine_target = resolution.get_top()", source)
                    self.assertIn('Dot(label.get_left(), radius=0.18, color="#7EE787")', source)
                    self.assertIn("the full tree remains visible", source)
                    divide_block = source.split('if semantic_family == "divide":', 1)[1].split('if semantic_family in {"array", "sort", "dynamic_array"}:', 1)[0]
                    self.assertNotIn("merge_layout", divide_block)
                    self.assertNotIn("cells[index].animate", divide_block)
                if topic == "Breadth-first search":
                    self.assertIn("def advance_bfs", source)
                    self.assertIn("queue_tokens", source)
                    self.assertIn("done_tokens", source)
                    self.assertIn("def bfs_transfer_packet", source)
                    self.assertIn("target_predecessors", source)
                    self.assertIn("trace = path.copy().set_stroke", source)
                    self.assertIn("return Dot(center, radius=0.18", source)
                    self.assertIn("def bfs_path_from_node", source)
                    self.assertIn("corridor_x = side * 3.62", source)
                    self.assertIn("process_states = {", source)
                    self.assertIn("visual_states = [state_data[0]]", source)
                    self.assertIn('state["event"] = "expand " + visit', source)
                    self.assertIn("Circle(radius=node_radius", source)
                    self.assertIn("node_radius = 0.9", source)
                    self.assertIn("travel_time, reveal_time = self.semantic_timed_segments(run_time, (0.74, 0.26))", source)
                    self.assertNotIn("queue_head_pulse", source)
                    self.assertNotIn("MoveAlongPath(pulse", source)
                    self.assertNotIn("MoveAlongPath(active_ring", source)
                    self.assertNotIn("state_indices =", source.split('if mode == "bfs":', 1)[1].split("graph, nodes, edge_lookup", 1)[0])
                if topic == "Direct Access Array":
                    direct_block = source.split('if mode == "direct_access":', 1)[1].split('if mode == "counting":', 1)[0]
                    self.assertIn("def compute_offset", direct_block)
                    self.assertIn("def jump_to_cell", direct_block)
                    self.assertIn("def show_base_address", direct_block)
                    self.assertIn("def select_index", direct_block)
                    self.assertIn("def read_selected_value", direct_block)
                    self.assertIn("bus_y = 1.55", direct_block)
                    self.assertIn("offset_bus = Line(base_port.get_center(), bus_corner", direct_block)
                    self.assertIn("jump_leg = Line(bus_corner, target_port", direct_block)
                    self.assertIn("access_path = VMobject().set_points_as_corners", direct_block)
                    self.assertIn("MoveAlongPath(query_pulse, access_path.copy())", direct_block)
                    self.assertIn("stride_label.next_to(stride_arrow, UP", direct_block)
                    self.assertIn('FadeOut(current["stride"])', direct_block)
                    self.assertIn("index_selector = SurroundingRectangle", direct_block)
                    self.assertIn("Create(target_halo)", direct_block)
                    self.assertIn("check_badge = VGroup", direct_block)
                    self.assertIn("base_address = 4096", direct_block)
                    self.assertIn("stride_bytes = 8", direct_block)
                    self.assertIn("resolved_address = base_address + byte_offset", direct_block)
                    self.assertIn("target_halo.set_fill(opacity=0.0).set_stroke(opacity=0.0)", direct_block)
                    self.assertIn('f"{base_address} + {access_index} x {stride_bytes} = {resolved_address}"', direct_block)
                    self.assertIn("def confirm_constant_time", direct_block)
                    self.assertNotIn("def resolve_address", direct_block)
                    self.assertNotIn("address_bus", direct_block)
                    self.assertNotIn("value_packet", direct_block)
                    self.assertIn("build_actions=[build_array_access_hook]", direct_block)
                    self.assertIn("sustain_actions=[sustain_array_access_hook]", direct_block)
                    self.assertIn("enforce_temporal_carriers=True", direct_block)
                    self.assertNotIn("probe_candidates", direct_block)
                    self.assertNotIn("self.register_semantic_track", direct_block)
                    self.assertNotIn("read_path", direct_block)
                    self.assertNotIn("underline", direct_block)
                    self.assertNotIn("stride_left_packet", direct_block)
                    self.assertEqual(direct_block.count("MoveAlongPath("), 1)
                    self.assertLess(direct_block.index('FadeOut(current["stride"])'), direct_block.index("MoveAlongPath(query_pulse"))
                if topic == "Priority Queue":
                    heap_block = source.split('if semantic_family == "heap":', 1)[1].split('if semantic_family == "complexity":', 1)[0]
                    self.assertNotIn("Transform(tree, next_tree)", heap_block)
                    self.assertNotIn("self.cs_heap_tree(state)", heap_block)
                    self.assertIn("def compare_parent", heap_block)
                    self.assertIn("def swap_parent", heap_block)
                    self.assertNotIn(".animate(path_arc=", heap_block)
                    self.assertIn("child_tree_token.animate.move_to(tree_positions[parent])", heap_block)
                    self.assertIn("child_array_token.animate.move_to(array_positions[parent])", heap_block)
                    self.assertNotIn("FadeOut(child_tree_token)", heap_block)
                    self.assertNotIn("FadeOut(child_array_token)", heap_block)
                    self.assertIn('edge.animate.set_color("#7EE787")', heap_block)
                    self.assertNotIn("swap_routes", heap_block)
                    self.assertNotIn("ArcBetweenPoints(", heap_block)
                    self.assertNotIn("route_packet", heap_block)
                    self.assertNotIn("root_cursor", heap_block)
                    self.assertNotIn("leaf_cursor", heap_block)
                    self.assertIn("heap_verification_tracer = Circle(radius=0.34", heap_block)
                    self.assertIn("heap_array_selector = SurroundingRectangle", heap_block)
                    self.assertIn("MoveAlongPath(heap_verification_tracer, path)", heap_block)
                    self.assertNotIn("radius=0.15", heap_block)
                    swap_block = heap_block.split("def swap_parent", 1)[1].split("transition_groups", 1)[0]
                    self.assertIn("child_tree_token.animate.move_to", swap_block)
                    self.assertIn('transition_groups["heap:append"]', heap_block)
                    self.assertIn('transition_groups["heap:verify-order"]', heap_block)
                    self.assertIn("self.register_semantic_transition_actions(transition_groups", heap_block)


if __name__ == "__main__":
    unittest.main()

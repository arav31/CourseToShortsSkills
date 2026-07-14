from __future__ import annotations

import json
import unittest

from tools.video_table_models import (
    build_knapsack_model,
    build_knapsack_pseudopolynomial_evidence,
    build_matrix_chain_model,
    knapsack_table_model,
    matrix_chain_table_model,
    validate_knapsack_pseudopolynomial_evidence,
)


def all_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from all_strings(key)
            yield from all_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from all_strings(item)


class PersistentTableContractMixin:
    def assert_complete_persistent_updates(self, model: dict[str, object]) -> None:
        table = model["table_values"]
        initial = model["initial_table_values"]
        base_cells = {tuple(cell) for cell in model["base_cells"]}
        updates = model["updates"]
        expected_updates = {
            (row, column)
            for row, values in enumerate(table)
            for column, value in enumerate(values)
            if value is not None and (row, column) not in base_cells
        }

        seen = set(base_cells)
        emitted: set[tuple[int, int]] = set()
        for expected_step, update in enumerate(updates, start=1):
            self.assertEqual(update["step"], expected_step)
            coordinate = (update["row"], update["column"])
            self.assertNotIn(coordinate, seen)
            emitted.add(coordinate)

            row, column = coordinate
            self.assertEqual(update["cell"], [row, column])
            self.assertEqual(update["value"], table[row][column])
            self.assertEqual(update["cell_value"], table[row][column])
            self.assertEqual(update["display_value"], str(table[row][column]))

            snapshot = update["table_values_after"]
            self.assertEqual(snapshot[row][column], update["value"])
            for prior_row, prior_column in seen:
                self.assertEqual(
                    snapshot[prior_row][prior_column],
                    table[prior_row][prior_column],
                    f"step {expected_step} erased {(prior_row, prior_column)}",
                )

            seen.add(coordinate)
            self.assertEqual(
                [tuple(cell) for cell in update["visible_cells_after"]],
                [tuple(cell["cell"]) for cell in update["persistent_cells"]],
            )
            self.assertEqual(set(map(tuple, update["visible_cells_after"])), seen)
            for cell in update["persistent_cells"]:
                cell_row, cell_column = cell["cell"]
                self.assertEqual(cell["value"], snapshot[cell_row][cell_column])
                self.assertEqual(cell["display_value"], str(cell["value"]))

            dependencies = update["dependency_cells"]
            self.assertEqual(
                update["sources"],
                [
                    [dependency["row"], dependency["column"]]
                    for dependency in dependencies
                ],
            )
            for dependency in dependencies:
                dependency_coordinate = (dependency["row"], dependency["column"])
                self.assertIn(dependency_coordinate, seen - {coordinate})
                self.assertEqual(
                    dependency["value"],
                    table[dependency["row"]][dependency["column"]],
                )

            candidates = update["candidates"]
            self.assertTrue(candidates)
            self.assertEqual(sum(candidate["is_winner"] for candidate in candidates), 1)
            winner = update["winner"]
            winning_candidate = candidates[winner["candidate_index"]]
            self.assertEqual(winning_candidate["candidate_id"], winner["candidate_id"])
            self.assertEqual(winning_candidate["value"], update["value"])
            self.assertTrue(winning_candidate["is_winner"])
            for candidate in candidates:
                self.assertTrue(candidate["arithmetic_ascii"])
                self.assertTrue(candidate["arithmetic_latex"])
                self.assertIn(candidate["evidence_token"], update["evidence_tokens"])

            cell_token = f"{update['cell_id']}={update['value']}"
            self.assertIn(cell_token, update["evidence_tokens"])
            self.assertIn(cell_token, model["evidence_tokens"])

        self.assertEqual(emitted, expected_updates)
        self.assertEqual(seen, base_cells | expected_updates)

        for row, values in enumerate(initial):
            for column, value in enumerate(values):
                if (row, column) in base_cells:
                    self.assertEqual(value, table[row][column])
                else:
                    self.assertIsNone(value)

        final_cells = {
            tuple(cell["cell"]): cell["value"] for cell in model["persistent_cells"]
        }
        self.assertEqual(
            final_cells,
            {
                (row, column): value
                for row, values in enumerate(table)
                for column, value in enumerate(values)
                if value is not None
            },
        )

    def assert_display_strings_are_safe(self, model: dict[str, object]) -> None:
        json.dumps(model)
        for value in all_strings(model):
            self.assertTrue(value.isascii(), repr(value))
            self.assertNotIn("\ufffd", value)

        formula_text = model["formula_text"]
        self.assertEqual(formula_text, model["formula_ascii"])
        self.assertNotIn("\\", formula_text)
        self.assertNotIn("{", formula_text)
        self.assertNotIn("}", formula_text)
        self.assertNotIn("...", formula_text)
        self.assertNotIn("placeholder", formula_text.lower())
        self.assertNotIn("formula cue", formula_text.lower())
        self.assertTrue(model["formula_latex"].isascii())
        self.assertEqual(
            model["formula_latex"].count("{"), model["formula_latex"].count("}")
        )
        self.assertTrue(model["video_formula_text"].isascii())
        self.assertTrue(model["video_formula_latex"].isascii())
        self.assertLess(len(model["video_formula_text"]), len(model["formula_text"]))


class MatrixChainModelTests(PersistentTableContractMixin, unittest.TestCase):
    def test_matrix_chain_keeps_full_notes_recurrence_and_compact_video_formula(
        self,
    ) -> None:
        model = build_matrix_chain_model()

        self.assertEqual(
            model["formula_text"],
            "C[i,j] = minimum over i <= k < j of "
            "C[i,k] + C[k+1,j] + p[i-1] * p[k] * p[j]",
        )
        self.assertEqual(
            model["formula_latex"],
            r"C_{i,j}=\min_{i\leq k<j}\{C_{i,k}+C_{k+1,j}+p_{i-1}p_kp_j\}",
        )

        video_text = model["video_formula_text"]
        video_latex = model["video_formula_latex"]
        self.assertEqual(video_text, "C(i,j) = min(left + right + merge)")
        self.assertEqual(
            video_latex,
            r"C(i,j)=\min(\text{left}+\text{right}+\text{merge})",
        )
        self.assertLessEqual(len(video_text), 40)
        self.assertTrue(video_text.isascii())
        self.assertTrue(video_text.isprintable())
        self.assertFalse(any(token in video_text for token in "\\_{}"))
        self.assertTrue(video_latex.isascii())
        self.assertNotIn("_", video_latex)

    def test_canonical_three_matrix_chain_has_both_full_chain_candidates(self) -> None:
        model = build_matrix_chain_model()

        self.assertEqual(model["mode"], "matrix_chain")
        self.assertEqual(model["dimensions"], [10, 30, 5, 60])
        self.assertEqual(model["row_labels"], ["A", "B", "C"])
        self.assertEqual(
            model["table_values"],
            [[0, 1500, 4500], [None, 0, 9000], [None, None, 0]],
        )
        self.assertEqual(model["result_value"], 4500)
        self.assertEqual(model["result_parenthesization"], "(AB)C")
        self.assertEqual(model["winner"]["parenthesization"], "(AB)C")
        self.assertEqual(model["winner"]["split"], 2)
        self.assertTrue(model["verified"])

        by_cell = {tuple(update["cell"]): update for update in model["updates"]}
        ab = by_cell[(0, 1)]
        bc = by_cell[(1, 2)]
        abc = by_cell[(0, 2)]
        self.assertEqual(ab["value"], 1500)
        self.assertEqual(ab["candidates"][0]["scalar_dimensions"], [10, 30, 5])
        self.assertEqual(ab["candidates"][0]["scalar_cost"], 1500)
        self.assertEqual(bc["value"], 9000)
        self.assertEqual(bc["candidates"][0]["scalar_dimensions"], [30, 5, 60])
        self.assertEqual(bc["candidates"][0]["scalar_cost"], 9000)

        self.assertEqual(
            [candidate["parenthesization"] for candidate in abc["candidates"]],
            ["A(BC)", "(AB)C"],
        )
        self.assertEqual(
            [candidate["value"] for candidate in abc["candidates"]], [27000, 4500]
        )
        self.assertEqual(
            abc["candidates"][1]["arithmetic_ascii"],
            "C[1,2] + C[3,3] + 10 * 5 * 60 = 1500 + 0 + 3000 = 4500",
        )
        self.assertEqual(
            {tuple(dependency["cell"]) for dependency in abc["dependency_cells"]},
            {(0, 0), (1, 2), (0, 1), (2, 2)},
        )
        self.assertEqual(abc["winner"]["parenthesization"], "(AB)C")
        self.assertEqual(abc["winner"]["value"], 4500)
        self.assertIn("4500 < 27000", abc["winner"]["reason_ascii"])

        self.assert_complete_persistent_updates(model)
        self.assert_display_strings_are_safe(model)

    def test_matrix_chain_is_data_driven_and_uses_a_stable_tie_rule(self) -> None:
        dimensions = [40, 20, 30, 10, 30]
        labels = ["A", "B", "C", "D"]
        first = matrix_chain_table_model(dimensions, labels)
        second = matrix_chain_table_model(dimensions, labels)

        self.assertEqual(first, second)
        self.assertEqual(dimensions, [40, 20, 30, 10, 30])
        self.assertEqual(labels, ["A", "B", "C", "D"])
        self.assertEqual(first["result_value"], 26000)
        self.assertEqual(first["result_parenthesization"], "(A(BC))D")
        self.assertEqual(len(first["updates"]), 6)
        self.assert_complete_persistent_updates(first)

        tied = build_matrix_chain_model([2, 2, 2, 2])
        self.assertEqual(tied["result_value"], 16)
        self.assertEqual(tied["winner"]["split"], 1)
        self.assertEqual(tied["result_parenthesization"], "A(BC)")
        self.assertIn("earliest split", tied["winner"]["reason_ascii"])

    def test_matrix_chain_rejects_invalid_dimensions_and_labels(self) -> None:
        with self.assertRaises(ValueError):
            build_matrix_chain_model([10])
        with self.assertRaises(ValueError):
            build_matrix_chain_model([10, 0, 5])
        with self.assertRaises(TypeError):
            build_matrix_chain_model([10, True, 5])
        with self.assertRaises(ValueError):
            build_matrix_chain_model([10, 20, 30], ["A"])
        with self.assertRaises(ValueError):
            build_matrix_chain_model([10, 20, 30], ["A", "A"])
        with self.assertRaises(ValueError):
            build_matrix_chain_model([10, 20], ["A\u2603"])


class KnapsackModelTests(PersistentTableContractMixin, unittest.TestCase):
    def test_pseudopolynomial_evidence_compares_columns_with_encoded_bits(self) -> None:
        evidence = build_knapsack_pseudopolynomial_evidence(
            6,
            item_count=3,
            second_capacity=12,
        )

        self.assertEqual(evidence.baseline.table_columns, 7)
        self.assertEqual(evidence.baseline.encoded_bits, 3)
        self.assertEqual(evidence.baseline.table_cells, 28)
        self.assertEqual(evidence.comparison.table_columns, 13)
        self.assertEqual(evidence.comparison.encoded_bits, 4)
        self.assertEqual(evidence.comparison.table_cells, 52)
        self.assertEqual(evidence.capacity_delta, 6)
        self.assertEqual(evidence.column_delta, 6)
        self.assertEqual(evidence.encoded_bit_delta, 1)
        self.assertTrue(evidence.pseudopolynomial)
        self.assertTrue(validate_knapsack_pseudopolynomial_evidence(evidence).ok)

        model = build_knapsack_model()
        model_evidence = model["pseudopolynomial_evidence"]
        self.assertEqual(model_evidence["baseline"]["table_columns"], 7)
        self.assertEqual(model_evidence["baseline"]["encoded_bits"], 3)
        self.assertIn("W=6", model_evidence["comparison_text"])
        self.assertIn("ceil(log2(W+1))", model_evidence["complexity_text"])

    def test_canonical_knapsack_emits_every_cell_and_reconstructs_items(self) -> None:
        model = build_knapsack_model()

        self.assertEqual(model["mode"], "knapsack")
        self.assertEqual(model["capacity"], 6)
        self.assertEqual(
            model["row_labels"],
            ["base", "I1 w2 v3", "I2 w3 v4", "I3 w4 v5"],
        )
        self.assertEqual(model["column_labels"], ["0", "1", "2", "3", "4", "5", "6"])
        self.assertEqual(
            model["table_values"],
            [
                [0, 0, 0, 0, 0, 0, 0],
                [0, 0, 3, 3, 3, 3, 3],
                [0, 0, 3, 4, 4, 7, 7],
                [0, 0, 3, 4, 5, 7, 8],
            ],
        )
        self.assertEqual(len(model["updates"]), 18)
        self.assertEqual(model["result_value"], 8)
        self.assertEqual(model["selected_item_indices"], [1, 3])
        self.assertEqual(model["winner"]["total_weight"], 6)
        self.assertEqual(model["winner"]["total_value"], 8)
        self.assertEqual(
            [item["item_id"] for item in model["items"]],
            ["knapsack:item:1", "knapsack:item:2", "knapsack:item:3"],
        )
        self.assertEqual(
            [identity["item_id"] for identity in model["row_identities"]],
            ["knapsack:base", "knapsack:item:1", "knapsack:item:2", "knapsack:item:3"],
        )
        self.assertEqual(
            [item["weight"] for item in model["winner"]["selected_items"]],
            [2, 4],
        )
        self.assertTrue(model["verified"])

        by_cell = {tuple(update["cell"]): update for update in model["updates"]}
        too_small = by_cell[(1, 1)]
        self.assertEqual(too_small["winner"]["choice"], "exclude")
        self.assertFalse(too_small["candidates"][1]["feasible"])
        self.assertEqual(too_small["sources"], [[0, 1]])
        self.assertIn("2 > capacity 1", too_small["candidates"][1]["arithmetic_ascii"])

        result = by_cell[(3, 6)]
        self.assertEqual(result["item"]["item_id"], "knapsack:item:3")
        self.assertEqual(
            result["active_row_state"],
            {
                "item_id": "knapsack:item:3",
                "index": 3,
                "label": "item 3",
                "weight": 4,
                "value": 5,
                "row": 3,
                "capacity": 6,
            },
        )
        self.assertTrue(
            all(
                candidate["item_id"] == result["item"]["item_id"]
                for candidate in result["candidates"]
            )
        )
        self.assertEqual(result["sources"], [[2, 6], [2, 2]])
        self.assertEqual(
            [candidate["value"] for candidate in result["candidates"]], [7, 8]
        )
        self.assertEqual(
            result["candidates"][1]["arithmetic_ascii"],
            "include: 5 + dp[2,2] = 5 + 3 = 8",
        )
        self.assertEqual(result["winner"]["choice"], "include")
        self.assertEqual(result["winner"]["value"], 8)

        self.assert_complete_persistent_updates(model)
        self.assert_display_strings_are_safe(model)

    def test_knapsack_is_data_driven_and_exclusion_wins_ties(self) -> None:
        items = [[1, 1], [2, 6], [3, 10], [5, 16]]
        first = knapsack_table_model(items, 7)
        second = knapsack_table_model(items, 7)

        self.assertEqual(first, second)
        self.assertEqual(items, [[1, 1], [2, 6], [3, 10], [5, 16]])
        self.assertEqual(first["result_value"], 22)
        self.assertEqual(first["selected_item_indices"], [2, 4])
        self.assertEqual(first["winner"]["total_weight"], 7)
        self.assert_complete_persistent_updates(first)

        tied = build_knapsack_model([(1, 1), (1, 1)], 1)
        final_update = tied["updates"][-1]
        self.assertEqual(
            [candidate["value"] for candidate in final_update["candidates"]], [1, 1]
        )
        self.assertEqual(final_update["winner"]["choice"], "exclude")
        self.assertEqual(tied["selected_item_indices"], [1])
        self.assertIn("deterministic tie", final_update["winner"]["reason_ascii"])

    def test_zero_capacity_and_empty_items_are_complete_base_models(self) -> None:
        zero_capacity = build_knapsack_model([(2, 3)], 0)
        self.assertEqual(zero_capacity["table_values"], [[0], [0]])
        self.assertEqual(zero_capacity["updates"], [])
        self.assertEqual(zero_capacity["result_value"], 0)
        self.assertTrue(zero_capacity["verified"])

        empty = build_knapsack_model([], 3)
        self.assertEqual(empty["table_values"], [[0, 0, 0, 0]])
        self.assertEqual(empty["updates"], [])
        self.assertEqual(empty["selected_item_indices"], [])
        self.assertTrue(empty["verified"])

    def test_knapsack_rejects_invalid_items_capacity_and_labels(self) -> None:
        with self.assertRaises(ValueError):
            build_knapsack_model([(0, 3)], 4)
        with self.assertRaises(TypeError):
            build_knapsack_model([(2, True)], 4)
        with self.assertRaises(ValueError):
            build_knapsack_model([(2, 3, 4)], 4)
        with self.assertRaises(ValueError):
            build_knapsack_model([(2, 3)], -1)
        with self.assertRaises(TypeError):
            build_knapsack_model([(2, 3)], True)
        with self.assertRaises(ValueError):
            build_knapsack_model([(2, 3)], 4, ["item\u2603"])


if __name__ == "__main__":
    unittest.main()

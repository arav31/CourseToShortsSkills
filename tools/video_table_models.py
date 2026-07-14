"""Deterministic semantic models for dynamic-programming table videos.

The helpers in this module are renderer-independent.  They expose both the
final table and the complete sequence of persistent table states, so a video
renderer never has to infer a cell value from caption text or animation state.
All display strings are ASCII; LaTeX is supplied separately from plain text.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Callable, Optional


CANONICAL_MATRIX_DIMENSIONS = (10, 30, 5, 60)
CANONICAL_KNAPSACK_ITEMS = ((2, 3), (3, 4), (4, 5))
CANONICAL_KNAPSACK_CAPACITY = 6

_LABEL_RE = re.compile(r"[A-Za-z][A-Za-z0-9 _.-]*\Z")


@dataclass(frozen=True)
class TableValidationResult:
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def valid(self) -> bool:
        return self.ok

    def require_valid(self) -> None:
        if self.errors:
            raise ValueError(
                "Invalid pseudopolynomial evidence:\n- " + "\n- ".join(self.errors)
            )


@dataclass(frozen=True)
class KnapsackCapacityEvidence:
    """Exact table-width versus binary-encoding evidence for one capacity."""

    evidence_id: str
    capacity: int
    table_columns: int
    encoded_bits: int
    item_rows: int
    table_cells: int
    lower_bit_bound: int
    upper_bit_bound: int

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "capacity": self.capacity,
            "table_columns": self.table_columns,
            "table_columns_formula": f"W+1={self.capacity}+1={self.table_columns}",
            "encoded_bits": self.encoded_bits,
            "encoded_bits_formula": (
                f"ceil(log2(W+1))=ceil(log2({self.table_columns}))={self.encoded_bits}"
            ),
            "item_rows": self.item_rows,
            "table_cells": self.table_cells,
            "table_cells_formula": (
                f"(n+1)(W+1)={self.item_rows}*{self.table_columns}={self.table_cells}"
            ),
            "bit_range": [self.lower_bit_bound, self.upper_bit_bound],
        }


@dataclass(frozen=True)
class KnapsackPseudopolynomialEvidence:
    """Two-capacity witness that distinguishes numeric width from bit length."""

    evidence_id: str
    baseline: KnapsackCapacityEvidence
    comparison: KnapsackCapacityEvidence
    capacity_delta: int
    column_delta: int
    encoded_bit_delta: int
    table_cell_delta: int
    column_growth_ratio: Fraction
    pseudopolynomial: bool

    def to_payload(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "baseline": self.baseline.to_payload(),
            "comparison": self.comparison.to_payload(),
            "capacity_delta": self.capacity_delta,
            "column_delta": self.column_delta,
            "encoded_bit_delta": self.encoded_bit_delta,
            "table_cell_delta": self.table_cell_delta,
            "column_growth_ratio": (
                str(self.column_growth_ratio.numerator)
                if self.column_growth_ratio.denominator == 1
                else f"{self.column_growth_ratio.numerator}/{self.column_growth_ratio.denominator}"
            ),
            "comparison_text": (
                f"W={self.baseline.capacity}: {self.baseline.table_columns} columns, "
                f"{self.baseline.encoded_bits} encoded bits; "
                f"W={self.comparison.capacity}: {self.comparison.table_columns} columns, "
                f"{self.comparison.encoded_bits} encoded bits"
            ),
            "complexity_text": (
                "Theta(nW) depends on numeric W while the input stores W in "
                "ceil(log2(W+1)) bits"
            ),
            "pseudopolynomial": self.pseudopolynomial,
        }


def _capacity_evidence(
    capacity: int,
    item_count: int,
    evidence_id: str,
) -> KnapsackCapacityEvidence:
    columns = capacity + 1
    encoded_bits = (columns - 1).bit_length()
    lower_bound = 0 if encoded_bits == 0 else 2 ** (encoded_bits - 1)
    upper_bound = 2 ** encoded_bits
    rows = item_count + 1
    return KnapsackCapacityEvidence(
        evidence_id=evidence_id,
        capacity=capacity,
        table_columns=columns,
        encoded_bits=encoded_bits,
        item_rows=rows,
        table_cells=rows * columns,
        lower_bit_bound=lower_bound,
        upper_bit_bound=upper_bound,
    )


def build_knapsack_pseudopolynomial_evidence(
    capacity: int,
    *,
    item_count: int = 0,
    second_capacity: Optional[int] = None,
) -> KnapsackPseudopolynomialEvidence:
    """Build exact ``W+1`` versus ``ceil(log2(W+1))`` comparison evidence."""

    checked_capacity = _integer(capacity, "capacity", minimum=0)
    checked_item_count = _integer(item_count, "item_count", minimum=0)
    if second_capacity is None:
        checked_second = max(checked_capacity + 1, 2 * checked_capacity)
    else:
        checked_second = _integer(second_capacity, "second_capacity", minimum=0)
    if checked_second <= checked_capacity:
        raise ValueError("second_capacity must be greater than capacity")

    baseline = _capacity_evidence(
        checked_capacity,
        checked_item_count,
        "knapsack:capacity:baseline",
    )
    comparison = _capacity_evidence(
        checked_second,
        checked_item_count,
        "knapsack:capacity:comparison",
    )
    evidence = KnapsackPseudopolynomialEvidence(
        evidence_id="knapsack:pseudopolynomial:evidence",
        baseline=baseline,
        comparison=comparison,
        capacity_delta=checked_second - checked_capacity,
        column_delta=comparison.table_columns - baseline.table_columns,
        encoded_bit_delta=comparison.encoded_bits - baseline.encoded_bits,
        table_cell_delta=comparison.table_cells - baseline.table_cells,
        column_growth_ratio=Fraction(
            comparison.table_columns, baseline.table_columns
        ),
        pseudopolynomial=True,
    )
    validate_knapsack_pseudopolynomial_evidence(evidence).require_valid()
    return evidence


def validate_knapsack_pseudopolynomial_evidence(
    evidence: KnapsackPseudopolynomialEvidence,
) -> TableValidationResult:
    """Validate both exact encodings and the second-capacity comparison."""

    errors: list[str] = []
    for witness in (evidence.baseline, evidence.comparison):
        if witness.table_columns != witness.capacity + 1:
            errors.append(f"{witness.evidence_id} does not expose W+1 columns")
        expected_bits = (witness.table_columns - 1).bit_length()
        if witness.encoded_bits != expected_bits:
            errors.append(
                f"{witness.evidence_id} does not expose ceil(log2(W+1)) bits"
            )
        if witness.table_cells != witness.item_rows * witness.table_columns:
            errors.append(f"{witness.evidence_id} has an incorrect table cell count")
        if witness.encoded_bits == 0:
            if witness.table_columns != 1:
                errors.append(f"{witness.evidence_id} has an invalid zero-bit range")
        elif not (
            witness.lower_bit_bound < witness.table_columns
            <= witness.upper_bit_bound
        ):
            errors.append(f"{witness.evidence_id} has invalid binary bounds")

    if evidence.comparison.capacity <= evidence.baseline.capacity:
        errors.append("comparison capacity does not increase")
    if evidence.column_delta != evidence.capacity_delta:
        errors.append("table-column growth does not track numeric capacity exactly")
    if evidence.table_cell_delta != (
        evidence.comparison.table_cells - evidence.baseline.table_cells
    ):
        errors.append("table-cell growth delta is inconsistent")
    expected_ratio = Fraction(
        evidence.comparison.table_columns,
        evidence.baseline.table_columns,
    )
    if evidence.column_growth_ratio != expected_ratio:
        errors.append("column growth ratio is inconsistent")
    if evidence.encoded_bit_delta != (
        evidence.comparison.encoded_bits - evidence.baseline.encoded_bits
    ):
        errors.append("encoded bit delta is inconsistent")
    if not evidence.pseudopolynomial:
        errors.append("evidence does not identify numeric-capacity dependence")
    return TableValidationResult(tuple(errors))


def _integer(value: object, name: str, *, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _labels(
    supplied: Optional[Sequence[str]],
    defaults: Sequence[str],
    expected: int,
    field_name: str,
) -> tuple[str, ...]:
    values = tuple(defaults if supplied is None else supplied)
    if len(values) != expected:
        raise ValueError(f"{field_name} must contain exactly {expected} labels")
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise TypeError(f"{field_name}[{index}] must be a string")
        if (
            not value.isascii()
            or not value.isprintable()
            or not _LABEL_RE.fullmatch(value)
        ):
            raise ValueError(
                f"{field_name}[{index}] must be a printable ASCII label beginning with a letter"
            )
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} labels must be unique")
    return values


def _matrix_labels(count: int) -> tuple[str, ...]:
    return tuple(
        chr(ord("A") + index) if index < 26 else f"M{index + 1}"
        for index in range(count)
    )


def _latex_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "^": r"\^{}",
        "~": r"\~{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def _snapshot(table: Sequence[Sequence[Optional[int]]]) -> list[list[Optional[int]]]:
    return [list(row) for row in table]


def _ordered_unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _dependency(
    row: int,
    column: int,
    value: int,
    cell_id: str,
) -> dict[str, object]:
    return {
        "row": row,
        "column": column,
        "cell": [row, column],
        "cell_id": cell_id,
        "value": value,
        "display_value": str(value),
        "evidence_token": f"{cell_id}={value}",
    }


def _merge_dependencies(
    candidates: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[tuple[int, int]] = set()
    for candidate in candidates:
        for raw in candidate["dependency_cells"]:  # type: ignore[index]
            dependency = dict(raw)
            coordinate = (int(dependency["row"]), int(dependency["column"]))
            if coordinate not in seen:
                seen.add(coordinate)
                merged.append(dependency)
    return merged


def _persistent_cells(
    table: Sequence[Sequence[Optional[int]]],
    visible: Sequence[tuple[int, int]],
    cell_id: Callable[[int, int], str],
) -> list[dict[str, object]]:
    cells: list[dict[str, object]] = []
    for row, column in visible:
        value = table[row][column]
        if value is None:
            raise AssertionError("visible table cells must have persistent values")
        identifier = cell_id(row, column)
        cells.append(
            {
                "row": row,
                "column": column,
                "cell": [row, column],
                "cell_id": identifier,
                "value": value,
                "display_value": str(value),
                "evidence_token": f"{identifier}={value}",
            }
        )
    return cells


def build_matrix_chain_model(
    dimensions: Sequence[int] = CANONICAL_MATRIX_DIMENSIONS,
    matrix_labels: Optional[Sequence[str]] = None,
) -> dict[str, object]:
    """Return every interval-DP calculation for a conformable matrix chain.

    ``dimensions`` is the standard matrix-chain vector ``p``: matrix ``i`` has
    shape ``dimensions[i]`` by ``dimensions[i + 1]``.  Equal-cost candidates
    use the earliest split, making reconstruction deterministic.
    """

    raw_dimensions = tuple(dimensions)
    if len(raw_dimensions) < 2:
        raise ValueError("dimensions must describe at least one matrix")
    dims = tuple(
        _integer(value, f"dimensions[{index}]", minimum=1)
        for index, value in enumerate(raw_dimensions)
    )
    matrix_count = len(dims) - 1
    labels = _labels(
        matrix_labels, _matrix_labels(matrix_count), matrix_count, "matrix_labels"
    )

    formula_ascii = (
        "C[i,j] = minimum over i <= k < j of "
        "C[i,k] + C[k+1,j] + p[i-1] * p[k] * p[j]"
    )
    formula_latex = r"C_{i,j}=\min_{i\leq k<j}\{C_{i,k}+C_{k+1,j}+p_{i-1}p_kp_j\}"
    video_formula_ascii = "C(i,j) = min(left + right + merge)"
    video_formula_latex = r"C(i,j)=\min(\text{left}+\text{right}+\text{merge})"
    table: list[list[Optional[int]]] = [
        [None for _column in range(matrix_count)] for _row in range(matrix_count)
    ]
    splits: list[list[Optional[int]]] = [
        [None for _column in range(matrix_count)] for _row in range(matrix_count)
    ]
    base_cells: list[list[int]] = []
    visible: list[tuple[int, int]] = []
    for index in range(matrix_count):
        table[index][index] = 0
        base_cells.append([index, index])
        visible.append((index, index))

    initial_table = _snapshot(table)

    def cell_id(row: int, column: int) -> str:
        return f"C[{row + 1},{column + 1}]"

    def parenthesization(left: int, right: int) -> str:
        if left == right:
            return labels[left]
        split = splits[left][right]
        if split is None:
            raise AssertionError("matrix-chain dependency was not solved before use")
        left_text = parenthesization(left, split)
        right_text = parenthesization(split + 1, right)
        if left < split:
            left_text = f"({left_text})"
        if split + 1 < right:
            right_text = f"({right_text})"
        return left_text + right_text

    updates: list[dict[str, object]] = []
    for chain_length in range(2, matrix_count + 1):
        for row in range(0, matrix_count - chain_length + 1):
            column = row + chain_length - 1
            candidates: list[dict[str, object]] = []
            for split in range(row, column):
                left_value = table[row][split]
                right_value = table[split + 1][column]
                if left_value is None or right_value is None:
                    raise AssertionError(
                        "matrix-chain updates are not in dependency order"
                    )
                scalar_dimensions = [dims[row], dims[split + 1], dims[column + 1]]
                scalar_cost = (
                    scalar_dimensions[0] * scalar_dimensions[1] * scalar_dimensions[2]
                )
                candidate_value = left_value + right_value + scalar_cost

                left_expression = parenthesization(row, split)
                right_expression = parenthesization(split + 1, column)
                if row < split:
                    left_expression = f"({left_expression})"
                if split + 1 < column:
                    right_expression = f"({right_expression})"
                expression = left_expression + right_expression

                dependencies = [
                    _dependency(row, split, left_value, cell_id(row, split)),
                    _dependency(
                        split + 1,
                        column,
                        right_value,
                        cell_id(split + 1, column),
                    ),
                ]
                arithmetic_ascii = (
                    f"{cell_id(row, split)} + {cell_id(split + 1, column)} + "
                    f"{scalar_dimensions[0]} * {scalar_dimensions[1]} * {scalar_dimensions[2]} = "
                    f"{left_value} + {right_value} + {scalar_cost} = {candidate_value}"
                )
                arithmetic_latex = (
                    rf"C_{{{row + 1},{split + 1}}}+C_{{{split + 2},{column + 1}}}+"
                    rf"{scalar_dimensions[0]}\cdot {scalar_dimensions[1]}\cdot {scalar_dimensions[2]}="
                    rf"{left_value}+{right_value}+{scalar_cost}={candidate_value}"
                )
                candidates.append(
                    {
                        "candidate_id": f"split_{split + 1}",
                        "candidate_index": len(candidates),
                        "split": split + 1,
                        "split_after_matrix": labels[split],
                        "parenthesization": expression,
                        "feasible": True,
                        "dependency_cells": dependencies,
                        "scalar_dimensions": scalar_dimensions,
                        "scalar_cost": scalar_cost,
                        "arithmetic_ascii": arithmetic_ascii,
                        "arithmetic_latex": arithmetic_latex,
                        "value": candidate_value,
                        "is_winner": False,
                        "evidence_token": arithmetic_ascii,
                    }
                )

            winner_index = min(
                range(len(candidates)),
                key=lambda index: (int(candidates[index]["value"]), index),
            )
            candidates[winner_index]["is_winner"] = True
            winning_candidate = candidates[winner_index]
            winning_split = int(winning_candidate["split"]) - 1
            winning_value = int(winning_candidate["value"])
            table[row][column] = winning_value
            splits[row][column] = winning_split

            competing_values = [int(candidate["value"]) for candidate in candidates]
            if len(candidates) == 1:
                reason_ascii = f"only legal split: {winning_candidate['parenthesization']} = {winning_value}"
                reason_latex = (
                    rf"\text{{only legal split: { _latex_text(str(winning_candidate['parenthesization'])) }}}"
                    rf"={winning_value}"
                )
            elif competing_values.count(winning_value) > 1:
                reason_ascii = f"choose earliest split {winning_candidate['split']} for tied minimum {winning_value}"
                reason_latex = (
                    rf"\text{{choose earliest split {winning_candidate['split']} for tied minimum }}"
                    rf"{winning_value}"
                )
            else:
                alternatives = [
                    value
                    for index, value in enumerate(competing_values)
                    if index != winner_index
                ]
                reason_ascii = (
                    f"choose {winning_candidate['parenthesization']} because {winning_value} < "
                    + ", ".join(str(value) for value in alternatives)
                )
                reason_latex = (
                    rf"\text{{choose { _latex_text(str(winning_candidate['parenthesization'])) } because }}"
                    + rf"{winning_value}<"
                    + ",".join(str(value) for value in alternatives)
                )

            dependencies = _merge_dependencies(candidates)
            visible.append((row, column))
            cell_token = f"{cell_id(row, column)}={winning_value}"
            winner_token = (
                f"winner:{winning_candidate['parenthesization']}={winning_value}"
            )
            step_tokens = _ordered_unique(
                [
                    cell_token,
                    *[str(dependency["evidence_token"]) for dependency in dependencies],
                    *[str(candidate["evidence_token"]) for candidate in candidates],
                    winner_token,
                ]
            )
            updates.append(
                {
                    "step": len(updates) + 1,
                    "row": row,
                    "column": column,
                    "cell": [row, column],
                    "cell_id": cell_id(row, column),
                    "cell_value": winning_value,
                    "value": winning_value,
                    "display_value": str(winning_value),
                    "sources": [
                        [int(dependency["row"]), int(dependency["column"])]
                        for dependency in dependencies
                    ],
                    "dependency_cells": dependencies,
                    "candidates": candidates,
                    "winner": {
                        "candidate_id": winning_candidate["candidate_id"],
                        "candidate_index": winner_index,
                        "split": winning_candidate["split"],
                        "parenthesization": winning_candidate["parenthesization"],
                        "value": winning_value,
                        "arithmetic_ascii": winning_candidate["arithmetic_ascii"],
                        "arithmetic_latex": winning_candidate["arithmetic_latex"],
                        "reason_ascii": reason_ascii,
                        "reason_latex": reason_latex,
                    },
                    "calculation_ascii": reason_ascii,
                    "calculation_latex": reason_latex,
                    "label": f"{cell_id(row, column)} = {winning_value}; {reason_ascii}",
                    "table_values_after": _snapshot(table),
                    "visible_cells_after": [list(coordinate) for coordinate in visible],
                    "persistent_cells": _persistent_cells(table, visible, cell_id),
                    "evidence_tokens": step_tokens,
                }
            )

    result_value = table[0][matrix_count - 1]
    if result_value is None:
        raise AssertionError("matrix-chain result cell was not computed")
    result_parenthesization = parenthesization(0, matrix_count - 1)
    final_winner: dict[str, object]
    if updates:
        final_winner = dict(updates[-1]["winner"])  # type: ignore[arg-type]
    else:
        final_winner = {
            "candidate_id": "base_case",
            "candidate_index": 0,
            "split": None,
            "parenthesization": result_parenthesization,
            "value": result_value,
            "arithmetic_ascii": f"{cell_id(0, 0)} = 0",
            "arithmetic_latex": r"C_{1,1}=0",
            "reason_ascii": "one matrix requires no scalar multiplications",
            "reason_latex": r"\text{one matrix requires no scalar multiplications}",
        }

    persistent = _persistent_cells(table, visible, cell_id)
    evidence_tokens = _ordered_unique(
        [
            formula_ascii,
            *[str(cell["evidence_token"]) for cell in persistent],
            *[
                token
                for update in updates
                for token in update["evidence_tokens"]  # type: ignore[index]
            ],
            f"result:{result_parenthesization}={result_value}",
        ]
    )
    expected_updates = matrix_count * (matrix_count - 1) // 2
    return {
        "family": "dp",
        "mode": "matrix_chain",
        "dimensions": list(dims),
        "matrices": [
            {
                "index": index + 1,
                "label": labels[index],
                "rows": dims[index],
                "columns": dims[index + 1],
            }
            for index in range(matrix_count)
        ],
        "table_values": _snapshot(table),
        "initial_table_values": initial_table,
        "row_labels": list(labels),
        "column_labels": list(labels),
        "base_cells": base_cells,
        "updates": updates,
        "persistent_cells": persistent,
        "formula_text": formula_ascii,
        "formula_ascii": formula_ascii,
        "formula_latex": formula_latex,
        "video_formula_text": video_formula_ascii,
        "video_formula_latex": video_formula_latex,
        "result_cell": [0, matrix_count - 1],
        "result_value": result_value,
        "result_parenthesization": result_parenthesization,
        "winner": final_winner,
        "evidence_tokens": evidence_tokens,
        "visible_evidence_tokens": list(evidence_tokens),
        "verified": (
            len(updates) == expected_updates
            and all(table[index][index] == 0 for index in range(matrix_count))
            and final_winner["value"] == result_value
        ),
        "invariant": (
            "each interval cell persists the cheapest value over every legal final split"
        ),
    }


def build_knapsack_model(
    items: Sequence[Sequence[int]] = CANONICAL_KNAPSACK_ITEMS,
    capacity: int = CANONICAL_KNAPSACK_CAPACITY,
    item_labels: Optional[Sequence[str]] = None,
) -> dict[str, object]:
    """Return every update in the 0/1-knapsack ``(item, capacity)`` table.

    Items are ``(weight, value)`` pairs.  Both candidates read the previous
    row, and equal values choose exclusion, so no item is reused and ties are
    deterministic.
    """

    checked_capacity = _integer(capacity, "capacity", minimum=0)
    checked_items: list[tuple[int, int]] = []
    for index, item in enumerate(tuple(items)):
        if isinstance(item, (str, bytes)) or len(item) != 2:
            raise ValueError(f"items[{index}] must be a (weight, value) pair")
        weight = _integer(item[0], f"items[{index}].weight", minimum=1)
        value = _integer(item[1], f"items[{index}].value")
        checked_items.append((weight, value))

    default_labels = tuple(
        f"item {index}" for index in range(1, len(checked_items) + 1)
    )
    labels = _labels(item_labels, default_labels, len(checked_items), "item_labels")
    item_records = [
        {
            "item_id": f"knapsack:item:{index}",
            "index": index,
            "label": labels[index - 1],
            "weight": weight,
            "value": value,
        }
        for index, (weight, value) in enumerate(checked_items, start=1)
    ]
    formula_ascii = (
        "dp[i,w] = max(dp[i-1,w], value[i] + dp[i-1,w-weight[i]]) "
        "if weight[i] <= w; otherwise dp[i,w] = dp[i-1,w]"
    )
    formula_latex = (
        r"\mathrm{dp}[i,w]=\begin{cases}"
        r"\max\{\mathrm{dp}[i-1,w],v_i+\mathrm{dp}[i-1,w-w_i]\},&w_i\leq w,\\"
        r"\mathrm{dp}[i-1,w],&w_i>w.\end{cases}"
    )
    video_formula_ascii = "dp[i,w] = max(exclude, include)"
    video_formula_latex = r"\mathrm{dp}[i,w]=\max\{\text{exclude},\text{include}\}"

    row_count = len(checked_items) + 1
    column_count = checked_capacity + 1
    table: list[list[Optional[int]]] = [
        [None for _column in range(column_count)] for _row in range(row_count)
    ]
    decisions: list[list[Optional[str]]] = [
        [None for _column in range(column_count)] for _row in range(row_count)
    ]
    base_cells: list[list[int]] = []
    visible: list[tuple[int, int]] = []
    for column in range(column_count):
        table[0][column] = 0
        base_cells.append([0, column])
        visible.append((0, column))
    for row in range(1, row_count):
        table[row][0] = 0
        base_cells.append([row, 0])
        visible.append((row, 0))

    initial_table = _snapshot(table)

    def cell_id(row: int, column: int) -> str:
        return f"dp[{row},{column}]"

    updates: list[dict[str, object]] = []
    for row, (weight, item_value) in enumerate(checked_items, start=1):
        item_record = dict(item_records[row - 1])
        for current_capacity in range(1, column_count):
            exclude_value = table[row - 1][current_capacity]
            if exclude_value is None:
                raise AssertionError("knapsack updates are not in dependency order")
            exclude_dependency = _dependency(
                row - 1,
                current_capacity,
                exclude_value,
                cell_id(row - 1, current_capacity),
            )
            exclude_ascii = (
                f"exclude: {cell_id(row - 1, current_capacity)} = {exclude_value}"
            )
            candidates: list[dict[str, object]] = [
                {
                    "candidate_id": "exclude",
                    "candidate_index": 0,
                    "choice": "exclude",
                    "feasible": True,
                    "item_id": item_record["item_id"],
                    "item_weight": weight,
                    "item_value": item_value,
                    "dependency_cells": [exclude_dependency],
                    "arithmetic_ascii": exclude_ascii,
                    "arithmetic_latex": (
                        rf"\text{{exclude: }}\mathrm{{dp}}[{row - 1},{current_capacity}]={exclude_value}"
                    ),
                    "value": exclude_value,
                    "is_winner": False,
                    "evidence_token": exclude_ascii,
                }
            ]

            if weight <= current_capacity:
                previous_capacity = current_capacity - weight
                prior_value = table[row - 1][previous_capacity]
                if prior_value is None:
                    raise AssertionError("knapsack include dependency was not solved")
                include_value = item_value + prior_value
                include_dependency = _dependency(
                    row - 1,
                    previous_capacity,
                    prior_value,
                    cell_id(row - 1, previous_capacity),
                )
                include_ascii = (
                    f"include: {item_value} + {cell_id(row - 1, previous_capacity)} = "
                    f"{item_value} + {prior_value} = {include_value}"
                )
                candidates.append(
                    {
                        "candidate_id": "include",
                        "candidate_index": 1,
                        "choice": "include",
                        "feasible": True,
                        "item_id": item_record["item_id"],
                        "dependency_cells": [include_dependency],
                        "item_weight": weight,
                        "item_value": item_value,
                        "arithmetic_ascii": include_ascii,
                        "arithmetic_latex": (
                            rf"\text{{include: }}{item_value}+\mathrm{{dp}}"
                            rf"[{row - 1},{previous_capacity}]="
                            rf"{item_value}+{prior_value}={include_value}"
                        ),
                        "value": include_value,
                        "is_winner": False,
                        "evidence_token": include_ascii,
                    }
                )
            else:
                infeasible_ascii = f"include infeasible: item weight {weight} > capacity {current_capacity}"
                candidates.append(
                    {
                        "candidate_id": "include",
                        "candidate_index": 1,
                        "choice": "include",
                        "feasible": False,
                        "item_id": item_record["item_id"],
                        "dependency_cells": [],
                        "item_weight": weight,
                        "item_value": item_value,
                        "arithmetic_ascii": infeasible_ascii,
                        "arithmetic_latex": (
                            rf"\text{{include infeasible: item weight }}{weight}>{current_capacity}"
                        ),
                        "value": None,
                        "is_winner": False,
                        "evidence_token": infeasible_ascii,
                    }
                )

            feasible_indices = [
                index
                for index, candidate in enumerate(candidates)
                if candidate["feasible"]
            ]
            winner_index = max(
                feasible_indices,
                key=lambda index: (int(candidates[index]["value"]), -index),
            )
            candidates[winner_index]["is_winner"] = True
            winning_candidate = candidates[winner_index]
            winning_value = int(winning_candidate["value"])
            winning_choice = str(winning_candidate["choice"])
            table[row][current_capacity] = winning_value
            decisions[row][current_capacity] = winning_choice

            include_candidate = candidates[1]
            if not include_candidate["feasible"]:
                reason_ascii = f"exclude wins because item weight {weight} > capacity {current_capacity}"
                reason_latex = (
                    rf"\text{{exclude because item weight }}{weight}>{current_capacity}"
                )
            else:
                include_value = int(include_candidate["value"])
                if exclude_value == include_value:
                    reason_ascii = (
                        f"exclude wins the deterministic tie at {winning_value}"
                    )
                    reason_latex = rf"\text{{exclude wins the tie at }}{winning_value}"
                elif winning_choice == "include":
                    reason_ascii = (
                        f"include wins because {include_value} > {exclude_value}"
                    )
                    reason_latex = (
                        rf"\text{{include because }}{include_value}>{exclude_value}"
                    )
                else:
                    reason_ascii = (
                        f"exclude wins because {exclude_value} > {include_value}"
                    )
                    reason_latex = (
                        rf"\text{{exclude because }}{exclude_value}>{include_value}"
                    )

            dependencies = _merge_dependencies(candidates)
            visible.append((row, current_capacity))
            cell_token = f"{cell_id(row, current_capacity)}={winning_value}"
            winner_token = f"winner:{winning_choice}={winning_value}"
            step_tokens = _ordered_unique(
                [
                    cell_token,
                    *[str(dependency["evidence_token"]) for dependency in dependencies],
                    *[str(candidate["evidence_token"]) for candidate in candidates],
                    winner_token,
                ]
            )
            updates.append(
                {
                    "step": len(updates) + 1,
                    "row": row,
                    "column": current_capacity,
                    "cell": [row, current_capacity],
                    "cell_id": cell_id(row, current_capacity),
                    "cell_value": winning_value,
                    "value": winning_value,
                    "display_value": str(winning_value),
                    "item": dict(item_record),
                    "active_row_state": {
                        **item_record,
                        "row": row,
                        "capacity": current_capacity,
                    },
                    "capacity": current_capacity,
                    "sources": [
                        [int(dependency["row"]), int(dependency["column"])]
                        for dependency in dependencies
                    ],
                    "dependency_cells": dependencies,
                    "candidates": candidates,
                    "winner": {
                        "candidate_id": winning_candidate["candidate_id"],
                        "candidate_index": winner_index,
                        "choice": winning_choice,
                        "value": winning_value,
                        "arithmetic_ascii": winning_candidate["arithmetic_ascii"],
                        "arithmetic_latex": winning_candidate["arithmetic_latex"],
                        "reason_ascii": reason_ascii,
                        "reason_latex": reason_latex,
                    },
                    "calculation_ascii": reason_ascii,
                    "calculation_latex": reason_latex,
                    "label": (
                        f"{cell_id(row, current_capacity)} = {winning_value}; {reason_ascii}"
                    ),
                    "table_values_after": _snapshot(table),
                    "visible_cells_after": [list(coordinate) for coordinate in visible],
                    "persistent_cells": _persistent_cells(table, visible, cell_id),
                    "evidence_tokens": step_tokens,
                }
            )

    selected_indices: list[int] = []
    remaining_capacity = checked_capacity
    for row in range(len(checked_items), 0, -1):
        if remaining_capacity > 0 and decisions[row][remaining_capacity] == "include":
            selected_indices.append(row)
            remaining_capacity -= checked_items[row - 1][0]
    selected_indices.reverse()
    selected_items = [
        dict(item_records[index - 1])
        for index in selected_indices
    ]
    selected_weight = sum(int(item["weight"]) for item in selected_items)
    selected_value = sum(int(item["value"]) for item in selected_items)
    result_value = table[-1][-1]
    if result_value is None:
        raise AssertionError("knapsack result cell was not computed")

    index_text = ", ".join(str(index) for index in selected_indices) or "none"
    weight_terms = " + ".join(str(item["weight"]) for item in selected_items) or "0"
    value_terms = " + ".join(str(item["value"]) for item in selected_items) or "0"
    selection_ascii = (
        f"selected items {index_text}: weight {weight_terms} = {selected_weight}; "
        f"value {value_terms} = {selected_value}"
    )
    selection_latex = (
        rf"\text{{selected items { _latex_text(index_text) }: weight }}"
        + weight_terms
        + rf"={selected_weight},\quad\text{{value }}"
        + value_terms
        + f"={selected_value}"
    )
    final_winner = {
        "value": result_value,
        "selected_item_indices": selected_indices,
        "selected_item_labels": [str(item["label"]) for item in selected_items],
        "selected_items": selected_items,
        "total_weight": selected_weight,
        "total_value": selected_value,
        "remaining_capacity": checked_capacity - selected_weight,
        "selection_ascii": selection_ascii,
        "selection_latex": selection_latex,
    }
    pseudopolynomial_evidence = build_knapsack_pseudopolynomial_evidence(
        checked_capacity,
        item_count=len(checked_items),
    )
    pseudopolynomial_payload = pseudopolynomial_evidence.to_payload()
    persistent = _persistent_cells(table, visible, cell_id)
    evidence_tokens = _ordered_unique(
        [
            formula_ascii,
            *[str(cell["evidence_token"]) for cell in persistent],
            *[
                token
                for update in updates
                for token in update["evidence_tokens"]  # type: ignore[index]
            ],
            f"result:dp[{len(checked_items)},{checked_capacity}]={result_value}",
            selection_ascii,
            str(pseudopolynomial_payload["comparison_text"]),
            str(pseudopolynomial_payload["complexity_text"]),
        ]
    )
    expected_updates = len(checked_items) * checked_capacity
    return {
        "family": "dp",
        "mode": "knapsack",
        "capacity": checked_capacity,
        "items": item_records,
        "row_identities": [
            {"row": 0, "item_id": "knapsack:base", "label": "base", "weight": 0, "value": 0},
            *[{"row": int(item["index"]), **item} for item in item_records],
        ],
        "table_values": _snapshot(table),
        "initial_table_values": initial_table,
        "row_labels": [
            "base",
            *[
                f"I{item['index']} w{item['weight']} v{item['value']}"
                for item in item_records
            ],
        ],
        "column_labels": [str(value) for value in range(column_count)],
        "base_cells": base_cells,
        "updates": updates,
        "persistent_cells": persistent,
        "formula_text": formula_ascii,
        "formula_ascii": formula_ascii,
        "formula_latex": formula_latex,
        "video_formula_text": video_formula_ascii,
        "video_formula_latex": video_formula_latex,
        "result_cell": [len(checked_items), checked_capacity],
        "result_value": result_value,
        "selected_item_indices": selected_indices,
        "winner": final_winner,
        "pseudopolynomial_evidence": pseudopolynomial_payload,
        "capacity_encoding": pseudopolynomial_payload["baseline"],
        "capacity_state_count": pseudopolynomial_evidence.baseline.table_columns,
        "capacity_encoded_bits": pseudopolynomial_evidence.baseline.encoded_bits,
        "second_capacity_comparison": pseudopolynomial_payload,
        "evidence_tokens": evidence_tokens,
        "visible_evidence_tokens": list(evidence_tokens),
        "verified": (
            len(updates) == expected_updates
            and selected_weight <= checked_capacity
            and selected_value == result_value
            and validate_knapsack_pseudopolynomial_evidence(
                pseudopolynomial_evidence
            ).ok
        ),
        "invariant": (
            "row i persists the best value using each of the first i items at most once"
        ),
    }


# Concise aliases for callers that name the returned artifact rather than the build action.
matrix_chain_table_model = build_matrix_chain_model
knapsack_table_model = build_knapsack_model
knapsack_pseudopolynomial_evidence = build_knapsack_pseudopolynomial_evidence


__all__ = [
    "CANONICAL_KNAPSACK_CAPACITY",
    "CANONICAL_KNAPSACK_ITEMS",
    "CANONICAL_MATRIX_DIMENSIONS",
    "KnapsackCapacityEvidence",
    "KnapsackPseudopolynomialEvidence",
    "TableValidationResult",
    "build_knapsack_model",
    "build_knapsack_pseudopolynomial_evidence",
    "build_matrix_chain_model",
    "knapsack_table_model",
    "knapsack_pseudopolynomial_evidence",
    "matrix_chain_table_model",
    "validate_knapsack_pseudopolynomial_evidence",
]

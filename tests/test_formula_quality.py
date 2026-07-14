from __future__ import annotations

import unittest

from tools import stem_course


class FormulaQualityTests(unittest.TestCase):
    def test_plain_math_normalizes_braced_and_unbraced_subscripts(self) -> None:
        normalized = stem_course.plain_math(r"x_1+x_{12}=y_2")

        self.assertEqual(normalized, "x sub 1 + x sub 12 = y sub 2")
        self.assertNotIn("_", normalized)
        self.assertNotIn("{", normalized)

    def test_formula_sanitizer_preserves_matrix_rows_and_columns(self) -> None:
        rendered = stem_course.sanitize_formula_latex("A=[[2, 1], [1, 3]]")

        self.assertEqual(
            rendered,
            r"A = \begin{bmatrix}2 & 1 \\ 1 & 3\end{bmatrix}",
        )

    def test_assignment_renderer_preserves_matrix_and_column_vector_shape(self) -> None:
        rendered = stem_course.latex_assignment_text(
            "Let A = [[2, 1], [1, 3]] and x = (4, 2).",
            vector_context=True,
        )

        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn(r"A = \begin{bmatrix}2 & 1 \\ 1 & 3\end{bmatrix}", rendered)
        self.assertIn(r"\vec{x} = \begin{bmatrix}4 \\ 2\end{bmatrix}", rendered)

    def test_screen_prose_keeps_matrix_contents_for_narration(self) -> None:
        spoken = stem_course.screen_prose("A=[[2, 1], [1, 3]]")

        self.assertEqual(spoken, "A is the matrix with rows (2, 1); (1, 3)")


if __name__ == "__main__":
    unittest.main()

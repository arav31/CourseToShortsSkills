from __future__ import annotations

import ast
import math
import unittest

from tools import stem_course


class MergeQualityContractTests(unittest.TestCase):
    def test_sorting_intuition_fits_one_complete_phone_page(self) -> None:
        tree = ast.parse(stem_course.ECONOMICS_SCENE_MODEL_HELPERS)
        selected = [
            node for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in {"PhoneCopyStage", "stage_phone_readable_copy"}
        ]
        namespace: dict[str, object] = {}
        exec(compile(ast.Module(body=selected, type_ignores=[]), "phone_copy", "exec"), namespace)
        stages = namespace["stage_phone_readable_copy"](
            "Split into ordered runs, then merge the same keys without losing identity.",
            min_font_size=38,
            max_chars_per_line=38,
            max_lines=2,
        )
        self.assertEqual(len(stages), 1)
        copy = " ".join(stages[0].lines)
        self.assertTrue(stem_course.complete_visible_prose_stage(copy))
        self.assertEqual(
            copy,
            "Split into ordered runs, then merge the same keys without losing identity.",
        )

    def test_merge_renderer_uses_state_deltas_hierarchy_and_phase_specific_sustain(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        self.assertIn('"1 run -> 2 halves"', source)
        self.assertIn('"2 halves -> 4 pairs"', source)
        self.assertIn('f"4 pairs -> {len(initial)} singletons"', source)
        self.assertNotIn('current["split_history"]', source)
        self.assertIn("FadeOut(previous_frames)", source)
        self.assertIn("FadeOut(connectors)", source)
        self.assertIn('if not current["at_output"]:', source)
        self.assertIn('ordered_merge_cells = sorted(cells, key=lambda cell: float(cell.get_center()[0]))', source)


if __name__ == "__main__":
    unittest.main()

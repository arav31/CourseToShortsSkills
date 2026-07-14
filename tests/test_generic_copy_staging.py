from __future__ import annotations

import math
import re
from types import SimpleNamespace
import unittest

import numpy as np

from tools import stem_course


class GenericCopyStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        namespace = {"math": math}
        exec(stem_course.ECONOMICS_SCENE_MODEL_HELPERS, namespace)
        cls.stage_copy = staticmethod(namespace["stage_phone_readable_copy"])

    def helper_function(self, name: str):
        return self.helper_function_with_globals(name, {"config": SimpleNamespace(frame_rate=30)})

    def helper_function_with_globals(self, name: str, namespace: dict[str, object]):
        source = stem_course.MANIM_SCENE_HELPERS
        start = source.index(f"def {name}(")
        match = re.search(rf"(?m)^def [A-Za-z_]\w*\(", source[start + 1 :])
        end = start + 1 + match.start() if match else len(source)
        exec(source[start:end], namespace)
        return namespace[name]

    def test_failed_group_bottom_copy_splits_without_word_loss(self) -> None:
        triggering_copy = {
            "Subgroups": "Apply the first move and then compose the second on the same labeled object.",
            "Cyclic Groups": "Result - checking identity, inverse, and repetition in the smallest useful setting.",
        }
        for title, copy in triggering_copy.items():
            with self.subTest(title=title):
                stages = self.stage_copy(
                    copy,
                    min_font_size=38,
                    max_chars_per_line=32,
                    max_lines=2,
                )
                self.assertGreaterEqual(len(stages), 2)
                self.assertTrue(all(stage.font_size == 38 for stage in stages))
                self.assertTrue(all(len(stage.lines) <= 2 for stage in stages))
                self.assertTrue(
                    all(len(line) <= 32 for stage in stages for line in stage.lines)
                )
                rebuilt = " ".join(line for stage in stages for line in stage.lines)
                self.assertEqual(rebuilt, re.sub(r"\s+", " ", copy).strip())

    def test_groups_top_copy_uses_the_same_word_preserving_pagination(self) -> None:
        copy = (
            "Let G={e,r,r^2} be the rotations of an equilateral triangle, "
            "with composition and r^3=e."
        )
        stages = self.stage_copy(
            copy,
            min_font_size=38,
            max_chars_per_line=32,
            max_lines=2,
        )
        self.assertGreaterEqual(len(stages), 2)
        self.assertEqual(
            " ".join(line for stage in stages for line in stage.lines),
            copy,
        )
        self.assertTrue(all(stage.font_size == 38 for stage in stages))

    def test_short_final_fragment_is_rebalanced_with_prior_line(self) -> None:
        stages = self.stage_copy(
            "A concrete example keeps every mathematical object visible while checking the preserved property.",
            min_font_size=38,
            max_chars_per_line=24,
            max_lines=2,
        )
        self.assertGreaterEqual(len(stages[-1].lines), 2)
        self.assertGreaterEqual(len(stages[-1].lines[-1].split()), 1)
        self.assertEqual(
            " ".join(line for stage in stages for line in stage.lines),
            "A concrete example keeps every mathematical object visible while checking the preserved property.",
        )

    def test_real_cross_domain_hook_and_intuition_copy_paginates_at_the_floor(self) -> None:
        cases = {
            "MIT 6.006 Hashing intuition": (
                "Understand Hashing by connecting definition, formula, and example.",
                42,
            ),
            "MIT 14.01 short01 hook": (
                "At equilibrium, the quantity read from demand equals the quantity read from supply at one price.",
                42,
            ),
            "MIT 14.01 short02 hook": (
                "The chosen bundle remains feasible and lies on the highest attainable indifference curve.",
                42,
            ),
            "MIT 14.01 short03 hook": (
                "The chosen bundle remains feasible and lies on the highest attainable indifference curve.",
                42,
            ),
        }
        for label, (copy, font_size) in cases.items():
            with self.subTest(label=label):
                stages = self.stage_copy(
                    copy,
                    min_font_size=font_size,
                    max_chars_per_line=32,
                    max_lines=2,
                )
                self.assertGreaterEqual(len(stages), 2)
                self.assertTrue(all(stage.font_size == font_size for stage in stages))
                self.assertTrue(
                    all(len(line) <= 32 for stage in stages for line in stage.lines)
                )
                self.assertEqual(
                    " ".join(line for stage in stages for line in stage.lines),
                    copy,
                )

    def test_pagination_preserves_the_single_authored_transition_budget(self) -> None:
        partition = self.helper_function("frame_partition_seconds")
        self.assertEqual(partition(None, 0.6, 2), [0.3, 0.3])
        self.assertAlmostEqual(sum(partition(None, 0.6, 3)), 0.6)
        self.assertAlmostEqual(sum(partition(None, 0.45, 2)), 14 / 30)

        reported_markers = {
            "short02_takeaway_after": (34.600, 35.567),
            "short02_takeaway_end": (34.933, 35.567),
            "short04_beat05_after": (28.400, 29.033),
            "short04_beat06_before": (29.067, 29.667),
            "short04_beat06_after": (33.733, 34.700),
            "short04_beat06_end": (34.067, 34.700),
        }
        observed_drifts = {
            marker: round(observed - expected, 3)
            for marker, (expected, observed) in reported_markers.items()
        }
        self.assertEqual(
            observed_drifts,
            {
                "short02_takeaway_after": 0.967,
                "short02_takeaway_end": 0.634,
                "short04_beat05_after": 0.633,
                "short04_beat06_before": 0.600,
                "short04_beat06_after": 0.967,
                "short04_beat06_end": 0.633,
            },
        )
        self.assertAlmostEqual(sum(partition(None, 0.6, 2)) - 0.6, 0.0)

    def test_bottom_pages_execute_one_budget_and_one_semantic_hold(self) -> None:
        animation = lambda *args, **kwargs: (args, kwargs)
        globals_for_helper = {
            "config": SimpleNamespace(frame_rate=30),
            "FadeIn": animation,
            "FadeOut": animation,
            "UP": np.array([0.0, 1.0, 0.0]),
            "np": np,
            "DOWN": -1.0,
        }
        partition = self.helper_function_with_globals(
            "frame_partition_seconds", globals_for_helper
        )
        stage_bottom = self.helper_function_with_globals(
            "stage_bottom_sequence", globals_for_helper
        )

        class Harness:
            frame_partition_seconds = partition

            def __init__(self) -> None:
                self.play_seconds = 0.0
                self._proof_surface_role_contract = {
                    "cue_formula": {
                        "bottom": 4.75,
                        "top": 6.25,
                        "lane_width": 8.1,
                    }
                }
                self.holds = []

            def bottom_text_mobjects(self):
                return []

            def readable_copy_stages(self, *args, **kwargs):
                return [["first page"], ["second page"]]

            def text_block(self, lines, **kwargs):
                return SimpleNamespace(lines=lines)

            def safe_place(self, staged, **kwargs):
                return staged

            def play(self, *animations, run_time):
                self.play_seconds += run_time

            def remove(self, *mobjects):
                pass

            def hold_scene_state(self, state, index, **kwargs):
                self.holds.append((state, index, kwargs["animation_seconds"]))

        harness = Harness()
        stage_bottom(
            harness,
            [["copy that needs two visual pages"]],
            "example_takeaway",
            "#7EE787",
        )
        self.assertAlmostEqual(harness.play_seconds, 0.6)
        self.assertEqual(harness.holds, [("example_takeaway", 0, 0.6)])

    def test_top_pages_execute_one_budget_and_one_semantic_hold(self) -> None:
        animation = lambda *args, **kwargs: (args, kwargs)
        globals_for_helper = {
            "config": SimpleNamespace(frame_rate=30),
            "FadeIn": animation,
            "FadeOut": animation,
            "UP": np.array([0.0, 1.0, 0.0]),
            "np": np,
        }
        partition = self.helper_function_with_globals(
            "frame_partition_seconds", globals_for_helper
        )
        stage_top = self.helper_function_with_globals(
            "stage_top_sequence", globals_for_helper
        )

        class Harness:
            frame_partition_seconds = partition

            def __init__(self) -> None:
                self.play_seconds = 0.0
                self._proof_surface_role_contract = {
                    "cue_formula": {
                        "bottom": 4.75,
                        "top": 6.25,
                        "lane_width": 8.1,
                    }
                }
                self.holds = []
                self._concept_objects = []

            def readable_copy_stages(self, *args, **kwargs):
                return [["first page"], ["second page"]]

            def text_block(self, lines, **kwargs):
                return SimpleNamespace(lines=lines)

            def safe_place(self, staged, **kwargs):
                return staged

            def play(self, *animations, run_time):
                self.play_seconds += run_time

            def remove(self, *mobjects):
                pass

            def hold_scene_state(self, state, index, **kwargs):
                self.holds.append(
                    (state, index, kwargs["animation_seconds"], self.play_seconds)
                )

        harness = Harness()
        stage_top(harness, [["copy that needs two visual pages"]])
        authored_transition_frames = 14 / 30
        self.assertEqual(
            harness.holds,
            [("example_setup", 0, authored_transition_frames, authored_transition_frames)],
        )
        self.assertAlmostEqual(harness.play_seconds, authored_transition_frames + 0.25)

    def test_direct_cue_presenter_keeps_all_pages_inside_one_budget(self) -> None:
        animation = lambda *args, **kwargs: (args, kwargs)
        globals_for_helper = {
            "config": SimpleNamespace(frame_rate=30),
            "FadeIn": animation,
            "FadeOut": animation,
            "UP": np.array([0.0, 1.0, 0.0]),
            "np": np,
        }
        partition = self.helper_function_with_globals(
            "frame_partition_seconds", globals_for_helper
        )
        presenter = self.helper_function_with_globals(
            "present_cue_pages", globals_for_helper
        )

        class Harness:
            frame_partition_seconds = partition

            def __init__(self) -> None:
                self.play_seconds = 0.0
                self._proof_surface_role_contract = {
                    "cue_formula": {
                        "bottom": 4.75,
                        "top": 6.25,
                        "lane_width": 8.1,
                    }
                }

            def text_block(self, lines, **kwargs):
                return SimpleNamespace(lines=lines)

            def safe_place(self, page, **kwargs):
                return page

            def play(self, *animations, run_time):
                self.play_seconds += run_time

            def remove(self, *mobjects):
                pass

        harness = Harness()
        final_page, elapsed = presenter(
            harness,
            None,
            [["page one"], ["page two"]],
            font_size=42,
            color="#EAF2FF",
            y=5.72,
            max_width=8.1,
            max_height=1.48,
            top=6.48,
            bottom=4.92,
            transition_seconds=0.35,
        )
        self.assertEqual(final_page.lines, ["page two"])
        self.assertAlmostEqual(elapsed, 10 / 30)
        self.assertAlmostEqual(harness.play_seconds, 10 / 30)

    def test_explicit_cue_role_builds_two_line_pages_inside_shift_safe_bounds(self) -> None:
        animation = lambda *args, **kwargs: (args, kwargs)
        namespace = {
            "config": SimpleNamespace(frame_rate=30),
            "FadeIn": animation,
            "FadeOut": animation,
            "UP": np.array([0.0, 1.0, 0.0]),
            "np": np,
        }
        partition = self.helper_function_with_globals("frame_partition_seconds", namespace)
        presenter = self.helper_function_with_globals("present_cue_pages", namespace)

        class Page:
            def __init__(self, lines, width=6.8, height=0.82) -> None:
                self.lines = lines
                self.width = width
                self.height = height
                self.center = np.zeros(3)

            def get_left(self):
                return self.center + np.array([-self.width / 2, 0.0, 0.0])

            def get_right(self):
                return self.center + np.array([self.width / 2, 0.0, 0.0])

            def get_bottom(self):
                return self.center + np.array([0.0, -self.height / 2, 0.0])

            def get_top(self):
                return self.center + np.array([0.0, self.height / 2, 0.0])

        class Harness:
            frame_partition_seconds = partition

            def __init__(self) -> None:
                self._proof_surface_role_contract = {
                    "title": {"bottom": 6.45, "top": 7.55, "lane_width": 8.1},
                    "cue_formula": {"bottom": 4.75, "top": 6.25, "lane_width": 8.1},
                }
                self.roles = {}
                self.text_calls = []
                self.play_seconds = 0.0

            def text_block(self, lines, **kwargs):
                self.text_calls.append(kwargs)
                return Page(lines)

            def safe_place(self, page, **kwargs):
                page.center = np.array([0.0, kwargs["y"], 0.0])
                return page

            def play(self, *_animations, run_time):
                self.play_seconds += run_time

            def remove(self, *_mobjects):
                pass

            def register_portrait_role(self, role, mob):
                self.roles[role] = mob

        harness = Harness()
        pages = [
            ["The chosen bundle remains feasible", "on the highest attainable curve."],
            ["Extract the minimum frontier vertex", "then relax its outgoing edges."],
        ]
        final_page, elapsed = presenter(
            harness,
            None,
            pages,
            font_size=42,
            color="#EAF2FF",
            y=5.5,
            max_width=8.1,
            max_height=1.4,
            top=6.2,
            bottom=4.8,
            transition_seconds=0.4,
            shift=np.array([0.18, 0.08, 0.0]),
            role="cue_formula",
        )

        self.assertEqual(final_page.lines, pages[-1])
        self.assertIs(harness.roles["cue_formula"], final_page)
        self.assertTrue(all(call["role"] == "cue_formula" for call in harness.text_calls))
        self.assertTrue(all(call["max_width"] < 8.1 for call in harness.text_calls))
        self.assertAlmostEqual(harness.play_seconds, elapsed)

    def test_generated_scene_stages_generic_cues_and_labels(self) -> None:
        helpers = stem_course.MANIM_SCENE_HELPERS
        self.assertIn("def readable_copy_stages(", helpers)
        self.assertIn("def present_cue_pages(", helpers)
        self.assertIn("def stage_top_sequence(", helpers)
        self.assertIn("return self.stage_top_sequence(", helpers)
        self.assertIn("max_chars_per_line=38", helpers)
        self.assertIn("frame_partition_seconds(0.45, len(visual_stages))", helpers)
        self.assertIn("frame_partition_seconds(0.6, len(visual_stages))", helpers)
        self.assertNotIn("duration_scale=duration_scale", helpers)
        self.assertIn("max_chars_per_line=30", helpers)
        self.assertIn("frame_partition_seconds(run_time, len(reveal_stages))", helpers)
        self.assertIn('role="equation"', helpers)
        self.assertIn("font_size=38", helpers)

    def test_generated_group_scenes_embed_the_reusable_staging_path(self) -> None:
        for index, title in ((1, "Groups"), (2, "Subgroups"), (4, "Cyclic Groups")):
            with self.subTest(title=title):
                short = stem_course.concept_to_short(
                    stem_course.source_term_concept(title, "group_theory"), index
                )
                plan = stem_course.build_animation_plan(short)
                source = stem_course.manim_scene(short, "CopyStagingScene", plan)
                compile(source, f"generated_{index:02d}.py", "exec")
                self.assertIn("def readable_copy_stages(", source)
                self.assertIn("def stage_top_sequence(", source)
                self.assertIn("visual_stages = self.readable_copy_stages(", source)
                self.assertIn("reveal_stages = self.readable_copy_stages(", source)

    def test_generated_cross_domain_scenes_remove_direct_hook_and_intuition_bypasses(self) -> None:
        cases = (
            ("Hashing", "computer_science", 3),
            ("Introduction and Supply & Demand", "economics", 1),
            ("Preferences and Utility Functions", "economics", 2),
            ("Budget Constraints and Constrained Choice", "economics", 3),
        )
        for title, domain, index in cases:
            with self.subTest(title=title):
                short = stem_course.concept_to_short(
                    stem_course.source_term_concept(title, domain), index
                )
                stem_course.attach_plan_model_identity(short)
                plan = stem_course.build_animation_plan(short)
                source = stem_course.manim_scene(short, "DirectCueStagingScene", plan)
                compile(source, f"generated_direct_cue_{index:02d}.py", "exec")
                construct = source[source.index("    def construct(self):") :]
                self.assertNotIn(
                    "hook = self.text_block(hook_stages[0]", construct
                )
                self.assertNotIn(
                    "intuition = self.text_block(intuition_stages[0]", construct
                )
                self.assertIn("hook_pages = self.readable_copy_stages(", construct)
                self.assertIn("intuition_pages = self.readable_copy_stages(", construct)
                self.assertEqual(
                    construct.count(
                        'self.hold_scene_state("hook", stage_index=0'
                    ),
                    0,
                )
                self.assertIn('"hook",\n            stage_index=0,', construct)
                self.assertEqual(
                    construct.count(
                        'self.hold_scene_state("core_idea", stage_index=0'
                    ),
                    1,
                )


if __name__ == "__main__":
    unittest.main()

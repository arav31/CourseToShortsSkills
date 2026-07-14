from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest import mock

from tools import audit_video_frames, stem_course
from tools.economics_model_specs import MIT_14_01_TITLE_MODEL_IDS
from tools.video_economics_models import stage_phone_readable_copy


SUBSCRIPT_RESIDUE_RE = re.compile(r"[_₀-₉ₐ-ₜₓ₍₎]")


class EconomicsLearnerCopyTests(unittest.TestCase):
    def short_for(self, title: str) -> dict[str, object]:
        concept = stem_course.source_term_concept(title, "economics")
        return stem_course.concept_to_short(concept, 1)

    def test_monopoly_uses_complete_concise_causal_copy(self) -> None:
        beats = stem_course.canonical_beat_schedule(self.short_for("Monopoly I"))
        copy = {str(beat["scene_state"]): str(beat["text"]) for beat in beats}

        self.assertEqual(
            copy["hook"],
            "Set MR = MC to choose quantity. Demand then gives price.",
        )
        self.assertEqual(
            copy["example_calculation"],
            "MR = MC gives quantity 20. Demand gives price 60.",
        )

    def test_cross_economics_representatives_are_complete_and_phone_sized(self) -> None:
        self.assertEqual(len(MIT_14_01_TITLE_MODEL_IDS), 26)
        for title in ("Monopoly I", "International Trade: Welfare and Policy"):
            with self.subTest(title=title):
                for beat in stem_course.canonical_beat_schedule(self.short_for(title)):
                    if beat["scene_state"] == "core_formula":
                        continue
                    text = str(beat["text"])
                    self.assertLessEqual(stem_course.spoken_word_count(text), 12)
                    self.assertRegex(text, r"[.!?]$")
                    self.assertNotRegex(text, r"(?:[,;:]|\b(?:and|of|the|to|with))\s*[.!?]$")
                    self.assertNotRegex(text, SUBSCRIPT_RESIDUE_RE)
                    self.assertNotIn("...", text)

    def test_machine_identifiers_become_words_but_formula_path_stays_structured(self) -> None:
        prose = stem_course.learner_identifier_display_name(
            "demand_intercept and monopoly_quantity"
        )
        self.assertEqual(prose, "demand intercept and monopoly quantity")
        self.assertEqual(stem_course.formula_unicode_text(r"MR(q_m)=MC(q_m)"), "MR (qₘ) = MC (qₘ)")

    def test_economics_phone_copy_keeps_the_requested_font_floor(self) -> None:
        stages = stage_phone_readable_copy(
            "Set MR=MC to choose quantity; demand then gives price.",
            min_font_size=44,
            max_chars_per_line=32,
            max_lines=2,
        )
        self.assertTrue(stages)
        self.assertTrue(all(stage.font_size == 44 for stage in stages))
        self.assertTrue(all(len(stage.lines) <= 2 for stage in stages))

    def test_transition_evidence_uses_one_line_at_the_44_point_floor(self) -> None:
        short = self.short_for("Monopoly I")
        source = stem_course.manim_scene(
            short,
            "EconomicsEvidenceLaneProbe",
            stem_course.build_animation_plan(short),
        )
        transition = source[source.index("def econ_transition_move"):]
        self.assertIn("min_font_size=44", transition)
        self.assertIn("max_lines=1", transition)
        self.assertIn("self.register_semantic_transition_actions(", transition)
        self.assertIn("transition_actions,", transition)
        self.assertNotIn('if state["step"] < len(transitions)', transition)
        self.assertIn('if isinstance(state, dict) and state.get("semantic_registered"):', source)
        self.assertIn('if kind == "econ_monopoly":', source)

    def test_monopoly_uses_exact_schedules_and_transition_bound_construction(self) -> None:
        short = self.short_for("Monopoly I")
        source = stem_course.manim_scene(
            short,
            "EconomicsMonopolyConstructionProbe",
            stem_course.build_animation_plan(short),
        )
        compile(source, "EconomicsMonopolyConstructionProbe.py", "exec")
        renderer_start = source.index("def build_exact_representative_econ_canvas")
        renderer = source[renderer_start:source.index("def play_econ_visual", renderer_start)]

        self.assertIn('if kind == "econ_monopoly":', renderer)
        self.assertIn("demand_intercept - demand_slope * q", renderer)
        self.assertIn("demand_intercept - 2 * demand_slope * q", renderer)
        self.assertIn("efficient_quantity = (demand_intercept - marginal_cost) / demand_slope", renderer)
        self.assertIn("axes.scale(0.9).shift(DOWN * 0.48)", renderer)
        self.assertIn("axes.c2p(0, y_max) + RIGHT * 0.62 + UP * 0.28", renderer)
        self.assertIn("demand_anchor_q = 0.78 * x_max", renderer)
        self.assertIn("mr_anchor_q = 0.18 * x_max", renderer)
        self.assertIn("mc_anchor_q = 0.82 * x_max", renderer)
        self.assertIn('"choose_monopoly_quantity": choose_quantity', renderer)
        self.assertIn('"project_monopoly_price": project_price', renderer)
        self.assertIn('"mark_deadweight_loss": mark_deadweight_loss', renderer)
        self.assertIn("Create(price_projection)", renderer)
        self.assertIn("GrowFromEdge(deadweight, LEFT)", renderer)
        monopoly = renderer[renderer.index('if kind == "econ_monopoly":'):renderer.index('elif kind in {"econ_international_trade"')]
        self.assertNotIn("Transform(", monopoly)

    def test_tariff_label_changes_crossfade_in_reserved_plot_header_lanes(self) -> None:
        short = self.short_for("International Trade: Welfare and Policy")
        source = stem_course.manim_scene(
            short,
            "EconomicsTariffGlyphSafetyProbe",
            stem_course.build_animation_plan(short),
        )
        renderer_start = source.index("def build_exact_representative_econ_canvas")
        renderer = source[
            renderer_start:
            source.index("def play_econ_visual", renderer_start)
        ]
        self.assertIn("def glyph_safe_label_handoff(current, replacement, geometry, run_time):", renderer)
        self.assertIn("FadeOut(current", renderer)
        self.assertIn("FadeIn(replacement", renderer)
        self.assertIn("self.remove(current)", renderer)
        self.assertIn("self.play(*geometry", renderer)
        self.assertIn('tag("IMPORTS = 12", "#A371F7", RIGHT * 1.75 + UP * 3.55', renderer)
        self.assertNotIn("Transform(price_tag, tariff_tag)", renderer)
        self.assertNotIn("Transform(free_tag, after_tag)", renderer)
        self.assertIn(
            "objects = VGroup(axes, axis_labels, demand, supply, d_tag, s_tag, "
            "free_region, tariff_band, price_line, left, right, gap, revenue, "
            "dwl_left, dwl_right, accounting)",
            renderer,
        )

    def test_transition_window_sampling_is_dense_and_output_sought(self) -> None:
        frame_size = 12 * 20
        completed = mock.Mock(stdout=b"\x0a" * frame_size * 11)
        with mock.patch.object(audit_video_frames.subprocess, "run", return_value=completed) as run:
            frames = audit_video_frames.sample_gray_frame_window(
                "ffmpeg",
                Path("short19.mp4"),
                start=21.5,
                end=22.6,
                fps=10,
                width=12,
                height=20,
            )

        command = run.call_args.args[0]
        self.assertLess(command.index("-i"), command.index("-ss"))
        self.assertEqual(command[command.index("-ss") + 1], "21.500000")
        self.assertEqual(command[command.index("-t") + 1], "1.100000")
        self.assertEqual(len(frames), 11)

    def test_transition_integrity_rejects_persistent_plot_destruction(self) -> None:
        width, height = 120, 80
        baseline = bytearray([10] * (width * height))
        for x0, y0, x1, y1 in (
            (8, 5, 112, 10),
            (12, 14, 16, 68),
            (12, 64, 112, 68),
            (20, 18, 96, 22),
            (28, 28, 100, 32),
            (36, 38, 104, 42),
        ):
            for y in range(y0, y1):
                baseline[y * width + x0 : y * width + x1] = b"\xe6" * (x1 - x0)
        destroyed = bytearray(baseline)
        for y in range(4, 55):
            destroyed[y * width + 6 : y * width + 88] = b"\x0a" * 82

        metrics = audit_video_frames.analyze_temporal_visual_integrity(
            [bytes(baseline)] * 6 + [bytes(destroyed)] + [bytes(baseline)] * 6,
            interval=0.1,
            width=width,
            height=height,
        )

        blocking = [finding for finding in metrics["findings"] if finding["publish_blocking"]]
        self.assertTrue(blocking)
        self.assertTrue(any(
            finding["evidence"]["kind"] in {
                "regional_shredding",
                "isolated_regional_loss_or_partial_wipe",
            }
            for finding in blocking
        ))


if __name__ == "__main__":
    unittest.main()

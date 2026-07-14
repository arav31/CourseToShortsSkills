from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import audit_video_frames
from tools.validate_course_run import CourseRunValidator


def ocr_line(text: str, *, x: int, y: int, width: int, height: int, confidence: float = 90.0) -> dict[str, object]:
    return {
        "text": text,
        "confidence": confidence,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "words": [],
    }


def ocr_word(text: str, *, x: int, y: int, width: int, height: int, confidence: float = 90.0) -> dict[str, object]:
    return {
        "text": text,
        "confidence": confidence,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "line_key": (1, 1, 1, 1),
    }


def synthetic_text_frame(
    *,
    visible_glyphs: int,
    text_luma: int = 230,
    include_context: bool = True,
    context_luma: int | None = None,
) -> bytes:
    width, height = 120, 80
    frame = bytearray([10] * (width * height))
    for glyph_index in range(visible_glyphs):
        left = 20 + glyph_index * 8
        for y in range(10, 24):
            for x in range(left, left + 5):
                frame[y * width + x] = text_luma
    if include_context:
        value = text_luma if context_luma is None else context_luma
        for y in range(62, 69):
            for x in range(8, 112):
                frame[y * width + x] = value
    return bytes(frame)


def temporal_ocr_frame(timestamp: float, text: str | None, *, confidence: float = 95.0) -> dict[str, object]:
    lines = [ocr_line(text, x=20, y=10, width=77, height=14, confidence=confidence)] if text else []
    return {
        "width": 120,
        "height": 80,
        "timestamp_seconds": timestamp,
        "lines": lines,
        "words": [],
    }


def synthetic_visual_frame(
    rectangles: list[tuple[int, int, int, int, int]],
    *,
    width: int = 120,
    height: int = 80,
) -> bytes:
    frame = bytearray([10] * (width * height))
    for x0, y0, x1, y1, luma in rectangles:
        for y in range(y0, y1):
            frame[y * width + x0 : y * width + x1] = bytes([luma]) * (x1 - x0)
    return bytes(frame)


class OcrParsingTests(unittest.TestCase):
    def test_tesseract_tsv_is_grouped_into_line_regions(self) -> None:
        tsv = "\n".join(
            [
                "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
                "1\t1\t0\t0\t0\t0\t0\t0\t1080\t1920\t-1\t",
                "5\t1\t1\t1\t1\t1\t100\t200\t80\t30\t96\tlinear",
                "5\t1\t1\t1\t1\t2\t195\t200\t95\t30\t94\talgebra",
            ]
        )

        parsed = audit_video_frames.parse_tesseract_tsv(tsv)

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual((parsed["width"], parsed["height"]), (1080, 1920))
        self.assertEqual(len(parsed["lines"]), 1)
        self.assertEqual(parsed["lines"][0]["text"], "linear algebra")
        self.assertEqual(parsed["lines"][0]["width"], 190)


class TextLayoutAnalysisTests(unittest.TestCase):
    def test_repeated_small_clipped_overlapping_lines_are_serious(self) -> None:
        lines = [
            ocr_line("tiny caption", x=8, y=100, width=420, height=12),
            ocr_line("second caption", x=20, y=104, width=420, height=12),
        ]
        frames = [{"width": 1000, "height": 1000, "lines": lines, "words": []} for _ in range(3)]

        metrics = audit_video_frames.analyze_ocr_frames(frames, interval=2.0)

        self.assertIn("rendered_text_too_small", metrics["serious_review_flags"])
        self.assertIn("rendered_text_outside_safe_area", metrics["serious_review_flags"])
        self.assertIn("rendered_text_overlap", metrics["serious_review_flags"])
        self.assertEqual(metrics["frames_with_text_overlap_ratio"], 1.0)
        self.assertTrue(metrics["findings"])

    def test_single_8_5s_essential_overlap_is_publish_blocking(self) -> None:
        frames = [
            {
                "width": 1000,
                "height": 1000,
                "timestamp_seconds": frame_index * 0.5,
                "lines": [ocr_line("Surface area", x=250, y=100, width=500, height=40)],
                "words": [],
            }
            for frame_index in range(20)
        ]
        frames[17]["lines"] = [
            ocr_line("Area strip formula", x=200, y=500, width=500, height=40),
            ocr_line("Width times height", x=220, y=520, width=480, height=40),
        ]

        metrics = audit_video_frames.analyze_ocr_frames(frames, interval=0.5)

        self.assertEqual(metrics["frames_with_text_overlap_ratio"], 0.05)
        self.assertEqual(metrics["publish_blocking_frame_count"], 1)
        self.assertIn("rendered_text_overlap", metrics["serious_review_flags"])
        finding = next(item for item in metrics["findings"] if item["timestamp_seconds"] == 8.5)
        self.assertTrue(finding["publish_blocking"])
        self.assertEqual(metrics["blocking_findings"], [finding])

    def test_single_14s_essential_safe_area_violation_is_publish_blocking(self) -> None:
        frames = [
            {
                "width": 1000,
                "height": 1000,
                "timestamp_seconds": frame_index * 0.5,
                "lines": [ocr_line("Surface area of a sphere", x=180, y=80, width=640, height=40)],
                "words": [],
            }
            for frame_index in range(30)
        ]
        frames[28]["lines"] = [
            ocr_line("Surface area of a sphere", x=10, y=80, width=640, height=40),
        ]

        metrics = audit_video_frames.analyze_ocr_frames(frames, interval=0.5)

        self.assertEqual(metrics["frames_with_safe_area_violations"], 1)
        self.assertEqual(metrics["publish_blocking_frame_count"], 1)
        self.assertIn("rendered_text_outside_safe_area", metrics["serious_review_flags"])
        finding = next(item for item in metrics["findings"] if item["timestamp_seconds"] == 14.0)
        self.assertTrue(finding["publish_blocking"])

    def test_low_confidence_edge_noise_does_not_block(self) -> None:
        frame = {
            "width": 1000,
            "height": 1000,
            "lines": [ocr_line("possible noise", x=0, y=0, width=200, height=30, confidence=65)],
            "words": [],
        }

        metrics = audit_video_frames.analyze_ocr_frames([frame], interval=0.5)

        self.assertEqual(metrics["essential_safe_area_violation_count"], 0)
        self.assertNotIn("rendered_text_outside_safe_area", metrics["serious_review_flags"])

    def test_superscript_region_is_not_reported_as_overlap(self) -> None:
        baseline = ocr_line("x", x=100, y=100, width=200, height=50)
        superscript = ocr_line("2", x=285, y=88, width=20, height=20)

        collisions = audit_video_frames.text_line_overlap_pairs([baseline, superscript])

        self.assertEqual(collisions, [])

    def test_high_confidence_superscript_pair_does_not_block_frame(self) -> None:
        frame = {
            "width": 1000,
            "height": 1000,
            "lines": [
                ocr_line("radius", x=100, y=100, width=200, height=50),
                ocr_line("squared", x=285, y=88, width=60, height=20),
            ],
            "words": [],
        }

        metrics = audit_video_frames.analyze_ocr_frames([frame], interval=0.5)

        self.assertEqual(metrics["overlap_pair_count"], 0)
        self.assertNotIn("rendered_text_overlap", metrics["serious_review_flags"])

    def test_small_overlapping_line_away_from_script_anchor_is_a_collision(self) -> None:
        baseline = ocr_line("main expression", x=100, y=100, width=400, height=50)
        overlapping_caption = ocr_line("other formula", x=250, y=88, width=100, height=20)

        collisions = audit_video_frames.text_line_overlap_pairs([baseline, overlapping_caption])

        self.assertEqual(collisions, [(0, 1, "overlap")])

    def test_cramped_but_separated_rows_remain_small_text_without_overlap(self) -> None:
        lines = [
            ocr_line("At n equals 1000, n log n is", x=180, y=500, width=620, height=26),
            ocr_line("about 10000 while n squared is", x=150, y=528, width=700, height=26),
        ]
        frames = [
            {"width": 1000, "height": 1600, "lines": lines, "words": []}
            for _ in range(3)
        ]

        self.assertEqual(audit_video_frames.text_line_overlap_pairs(lines), [])
        metrics = audit_video_frames.analyze_ocr_frames(frames, interval=0.5)

        self.assertIn("rendered_text_too_small", metrics["serious_review_flags"])
        self.assertNotIn("rendered_text_overlap", metrics["review_flags"])
        self.assertEqual(metrics["overlap_pair_count"], 0)

    def test_inflated_adjacent_ocr_boxes_do_not_create_false_overlap(self) -> None:
        lines = [
            ocr_line("Priority Queue:", x=320, y=51, width=280, height=28),
            ocr_line("A heap keeps the next priority at", x=240, y=70, width=520, height=28),
        ]

        self.assertEqual(audit_video_frames.text_line_overlap_pairs(lines), [])

    def test_single_inflated_word_box_does_not_create_false_overlap(self) -> None:
        first = ocr_line("The order of an element is the", x=102, y=62, width=156, height=9)
        first["words"] = [
            ocr_word("The", x=102, y=62, width=20, height=9),
            ocr_word("order", x=125, y=62, width=28, height=9),
            ocr_word("element", x=185, y=62, width=40, height=9),
            ocr_word("is", x=230, y=65, width=8, height=6),
        ]
        second = ocr_line("first time repetition returns", x=109, y=68, width=143, height=28)
        second["words"] = [
            ocr_word("first", x=109, y=68, width=20, height=28),
            ocr_word("time", x=135, y=68, width=19, height=28),
            ocr_word("repetition", x=160, y=79, width=51, height=10),
            ocr_word("returns", x=216, y=79, width=36, height=8),
        ]

        self.assertEqual(audit_video_frames.text_line_overlap_pairs([first, second]), [])

    def test_inflated_word_does_not_force_dissimilar_robust_rows_to_overlap(self) -> None:
        first = ocr_line("An isomorphism says two groups", x=90, y=62, width=180, height=12)
        first["words"] = [
            ocr_word("An", x=90, y=62, width=16, height=9),
            ocr_word("isomorphism", x=110, y=62, width=70, height=12),
            ocr_word("says", x=184, y=64, width=22, height=10),
            ocr_word("two", x=210, y=63, width=20, height=8),
            ocr_word("groups", x=234, y=64, width=36, height=10),
        ]
        second = ocr_line("have the same structure in", x=108, y=70, width=140, height=28)
        second["words"] = [
            ocr_word("have", x=108, y=70, width=26, height=28),
            ocr_word("the", x=139, y=80, width=16, height=9),
            ocr_word("same", x=159, y=83, width=26, height=6),
            ocr_word("structure", x=188, y=82, width=47, height=7),
            ocr_word("in", x=239, y=83, width=9, height=6),
        ]

        self.assertEqual(audit_video_frames.text_line_overlap_pairs([first, second]), [])

    def test_word_geometry_corrects_one_inflated_line_box(self) -> None:
        hook = ocr_line("A heap keeps the next priority at", x=104, y=69, width=152, height=28)
        hook["words"] = [
            ocr_word("A", x=104, y=79, width=7, height=9),
            ocr_word("keeps", x=142, y=69, width=21, height=28),
            ocr_word("priority", x=211, y=80, width=33, height=10),
        ]
        prefix = ocr_line("Priority Queue:", x=144, y=62, width=69, height=11)
        prefix["words"] = [
            ocr_word("Priority", x=144, y=62, width=35, height=11),
            ocr_word("Queue", x=182, y=62, width=31, height=10),
        ]

        self.assertEqual(audit_video_frames.text_line_overlap_pairs([hook, prefix]), [])

    def test_low_confidence_and_run_together_tokens_are_recorded(self) -> None:
        line = ocr_line("ThisTextHasNoSpaces", x=100, y=100, width=420, height=30)
        words = [
            ocr_word("ThisTextHasNoSpaces", x=100, y=100, width=420, height=30, confidence=35),
            ocr_word("blurred", x=540, y=100, width=100, height=30, confidence=30),
        ]
        frames = [{"width": 1000, "height": 1000, "lines": [line], "words": words} for _ in range(3)]

        metrics = audit_video_frames.analyze_ocr_frames(frames, interval=2.0)

        self.assertIn("suspected_run_together_text", metrics["review_flags"])
        self.assertIn("suspected_run_together_text", metrics["serious_review_flags"])
        self.assertIn("low_confidence_rendered_text", metrics["review_flags"])
        self.assertEqual(metrics["suspected_run_together_token_count"], 3)

    def test_fused_article_is_flagged_but_hyphenated_word_is_not(self) -> None:
        fused = ocr_word("Asubgroup", x=100, y=100, width=150, height=30)
        hyphenated = ocr_word("structure-preserving", x=100, y=160, width=320, height=30)
        math_noise = ocr_word("lBLs(G", x=100, y=220, width=120, height=30)

        self.assertTrue(audit_video_frames.suspicious_run_together_word(fused))
        self.assertFalse(audit_video_frames.suspicious_run_together_word(hyphenated))
        self.assertFalse(audit_video_frames.suspicious_run_together_word(math_noise))

    def test_long_video_ocr_interval_is_bounded_and_uniform(self) -> None:
        self.assertEqual(audit_video_frames.bounded_ocr_interval(20.0, 0.5), 0.5)
        self.assertEqual(audit_video_frames.bounded_ocr_interval(60.0, 2.0), 0.5)
        self.assertEqual(audit_video_frames.bounded_ocr_interval(300.0, 0.5), 2.5)
        self.assertEqual(audit_video_frames.bounded_temporal_text_interval(20.0, 0.5), 0.25)
        self.assertEqual(audit_video_frames.bounded_temporal_text_interval(60.0, 0.5), 0.25)
        self.assertEqual(audit_video_frames.bounded_temporal_text_interval(300.0, 2.5), 1.25)

    def test_persistent_title_fragmentation_is_publish_blocking_even_when_ocr_hallucinates_it(self) -> None:
        ocr_frames = [
            temporal_ocr_frame(0.0, "Persistent lesson title"),
            temporal_ocr_frame(0.5, "Persistent lesson title"),
            temporal_ocr_frame(1.0, "Persistent lesson title"),
        ]
        visual_frames = [
            synthetic_text_frame(visible_glyphs=10),
            synthetic_text_frame(visible_glyphs=10),
            synthetic_text_frame(visible_glyphs=2),
            synthetic_text_frame(visible_glyphs=10),
            synthetic_text_frame(visible_glyphs=10),
        ]

        metrics = audit_video_frames.analyze_ocr_frames(
            ocr_frames,
            interval=0.5,
            temporal_frames=visual_frames,
            temporal_interval=0.25,
            temporal_width=120,
            temporal_height=80,
        )

        self.assertIn("temporal_text_integrity_loss", metrics["serious_review_flags"])
        self.assertEqual(metrics["publish_blocking_frame_count"], 1)
        temporal = metrics["temporal_text_integrity"]
        self.assertEqual(temporal["integrity_loss_count"], 1)
        finding = temporal["findings"][0]
        self.assertEqual(finding["timestamp_seconds"], 0.5)
        self.assertTrue(finding["publish_blocking"])
        self.assertTrue(finding["evidence"]["ocr_confirmed_at_bad_sample"])
        self.assertLess(finding["evidence"]["connected_region_area_ratio"], 0.3)

    def test_different_text_handoff_is_not_a_temporal_integrity_failure(self) -> None:
        ocr_frames = [
            temporal_ocr_frame(0.0, "Runtime equals 1000000"),
            temporal_ocr_frame(0.5, None),
            temporal_ocr_frame(1.0, "Runtime equals 1000001"),
        ]
        visual_frames = [
            synthetic_text_frame(visible_glyphs=10),
            synthetic_text_frame(visible_glyphs=10, text_luma=60),
            synthetic_text_frame(visible_glyphs=0),
            synthetic_text_frame(visible_glyphs=10, text_luma=60),
            synthetic_text_frame(visible_glyphs=10),
        ]

        metrics = audit_video_frames.analyze_ocr_frames(
            ocr_frames,
            interval=0.5,
            temporal_frames=visual_frames,
            temporal_interval=0.25,
            temporal_width=120,
            temporal_height=80,
        )

        self.assertNotIn("temporal_text_integrity_loss", metrics["review_flags"])
        self.assertEqual(metrics["temporal_text_integrity"]["integrity_loss_count"], 0)

    def test_coherent_whole_frame_fade_is_suppressed(self) -> None:
        ocr_frames = [
            temporal_ocr_frame(0.0, "Persistent lesson title"),
            temporal_ocr_frame(0.5, None),
            temporal_ocr_frame(1.0, "Persistent lesson title"),
        ]
        visual_frames = [
            synthetic_text_frame(visible_glyphs=10),
            synthetic_text_frame(visible_glyphs=10, text_luma=60, context_luma=60),
            synthetic_text_frame(visible_glyphs=0, include_context=False),
            synthetic_text_frame(visible_glyphs=10, text_luma=60, context_luma=60),
            synthetic_text_frame(visible_glyphs=10),
        ]

        metrics = audit_video_frames.analyze_ocr_frames(
            ocr_frames,
            interval=0.5,
            temporal_frames=visual_frames,
            temporal_interval=0.25,
            temporal_width=120,
            temporal_height=80,
        )

        temporal = metrics["temporal_text_integrity"]
        self.assertNotIn("temporal_text_integrity_loss", metrics["review_flags"])
        self.assertEqual(temporal["integrity_loss_count"], 0)
        self.assertGreaterEqual(temporal["coherent_transition_suppression_count"], 1)

    def test_interior_empty_band_ignores_outer_margin_but_finds_layout_gulf(self) -> None:
        width = height = 100
        frame = bytearray(width * height)
        for y in list(range(10, 20)) + list(range(80, 90)):
            for x in range(20, 80):
                frame[y * width + x] = 255

        ratio = audit_video_frames.interior_empty_vertical_band_ratio(bytes(frame), width, height)

        self.assertGreater(ratio, 0.55)


class TemporalVisualIntegrityTests(unittest.TestCase):
    width = 120
    height = 80

    def persistent_scene(self) -> bytes:
        rectangles = [
            (x, 15, x + 5, 28, 230)
            for x in range(10, 106, 8)
        ]
        rectangles.extend(
            [
                (8, 55, 112, 62, 180),
                (8, 65, 112, 69, 180),
            ]
        )
        return synthetic_visual_frame(rectangles)

    def analyze(self, frames: list[bytes]) -> dict[str, object]:
        return audit_video_frames.analyze_temporal_visual_integrity(
            frames,
            interval=0.1,
            width=self.width,
            height=self.height,
        )

    def test_isolated_regional_shredding_is_publish_blocking(self) -> None:
        baseline = self.persistent_scene()
        shredded = bytearray(baseline)
        for x in range(25, 86, 12):
            for y in range(12, 32):
                shredded[y * self.width + x : y * self.width + x + 6] = b"\x0a" * 6

        metrics = self.analyze([baseline] * 6 + [bytes(shredded)] + [baseline] * 6)

        self.assertEqual(metrics["integrity_loss_count"], 1)
        finding = metrics["findings"][0]
        self.assertTrue(finding["publish_blocking"])
        self.assertEqual(finding["evidence"]["kind"], "regional_shredding")
        self.assertGreater(finding["evidence"]["regional_loss_ratio"], 0.25)

    def test_coherent_whole_scene_fade_is_suppressed(self) -> None:
        baseline = self.persistent_scene()
        faded = bytes(
            10 if value == 10 else 55
            for value in baseline
        )
        blank = bytes([10]) * (self.width * self.height)

        metrics = self.analyze([baseline] * 5 + [faded, blank, faded] + [baseline] * 5)

        self.assertEqual(metrics["integrity_loss_count"], 0)
        self.assertGreater(metrics["coherent_transition_suppression_count"], 0)

    def test_compact_causal_carrier_cleanup_is_suppressed(self) -> None:
        baseline = bytearray(self.persistent_scene())
        for x in range(35, 80):
            baseline[40 * self.width + x] = 160
        with_carrier = bytearray(baseline)
        for y in range(36, 44):
            with_carrier[y * self.width + 52 : y * self.width + 60] = b"\xe6" * 8

        metrics = self.analyze([bytes(with_carrier)] * 6 + [bytes(baseline)] + [bytes(with_carrier)] * 6)

        self.assertEqual(metrics["integrity_loss_count"], 0)
        self.assertGreater(metrics["causal_motion_suppression_count"], 0)

    def test_balanced_causal_translation_is_not_integrity_loss(self) -> None:
        frames = [
            synthetic_visual_frame(
                [
                    (x, 20, x + 10, 30, 230),
                    (8, 60, 112, 64, 180),
                ]
            )
            for x in range(10, 71, 5)
        ]

        metrics = self.analyze(frames)

        self.assertEqual(metrics["integrity_loss_count"], 0)

    def test_permanent_object_retirement_is_not_a_transient_integrity_loss(self) -> None:
        before = synthetic_visual_frame(
            [
                (12, 14, 22, 46, 230),
                (48, 18, 72, 44, 230),
                (8, 60, 112, 64, 180),
            ]
        )
        after = synthetic_visual_frame(
            [
                (12, 14, 22, 46, 230),
                (8, 60, 112, 64, 180),
            ]
        )

        metrics = self.analyze([before] * 6 + [after] * 7)

        self.assertEqual(metrics["integrity_loss_count"], 0)

    def test_endpoint_state_changes_plus_small_causal_carrier_are_not_a_collision(self) -> None:
        before = synthetic_visual_frame(
            [
                (12, 14, 22, 46, 230),
                (82, 27, 112, 38, 180),
                (8, 60, 112, 64, 180),
            ]
        )
        after = synthetic_visual_frame(
            [
                (8, 27, 38, 38, 180),
                (96, 14, 106, 46, 230),
                (8, 60, 112, 64, 180),
            ]
        )
        carrier_midpoint = synthetic_visual_frame(
            [
                (12, 14, 22, 46, 230),
                (82, 27, 112, 38, 180),
                (8, 27, 38, 38, 180),
                (96, 14, 106, 46, 230),
                (56, 27, 62, 33, 230),
                (8, 60, 112, 64, 180),
            ]
        )

        metrics = self.analyze([before] * 8 + [carrier_midpoint] + [after] * 8)

        collision_findings = [
            finding
            for finding in metrics["findings"]
            if finding["evidence"]["kind"] == "destructive_transition_collision"
        ]
        self.assertEqual(collision_findings, [])
        self.assertGreater(metrics["causal_motion_suppression_count"], 0)

    def test_full_strength_endpoint_ghosts_plus_center_copy_are_a_collision(self) -> None:
        before = synthetic_visual_frame(
            [
                (12, 14, 22, 46, 230),
                (82, 27, 112, 38, 180),
                (8, 60, 112, 64, 180),
            ]
        )
        after = synthetic_visual_frame(
            [
                (8, 27, 38, 38, 180),
                (96, 14, 106, 46, 230),
                (8, 60, 112, 64, 180),
            ]
        )
        colliding = synthetic_visual_frame(
            [
                (12, 14, 22, 46, 230),
                (82, 27, 112, 38, 180),
                (8, 27, 38, 38, 180),
                (96, 14, 106, 46, 230),
                (48, 18, 72, 44, 230),
                (8, 60, 112, 64, 180),
            ]
        )

        metrics = self.analyze([before] * 8 + [colliding] + [after] * 8)

        collision = next(
            finding
            for finding in metrics["findings"]
            if finding["evidence"]["kind"] == "destructive_transition_collision"
        )
        self.assertTrue(collision["publish_blocking"])
        self.assertGreater(collision["evidence"]["source_residue_ratio"], 0.9)
        self.assertGreater(collision["evidence"]["destination_residue_ratio"], 0.9)
        self.assertGreater(collision["evidence"]["center_only_pixels"], 20)

    def test_dense_visual_sampling_catches_ocr_missed_point_three_five_second_overlap(self) -> None:
        before = synthetic_visual_frame([
            (12, 14, 22, 46, 230), (82, 27, 112, 38, 180), (8, 60, 112, 64, 180),
        ])
        after = synthetic_visual_frame([
            (8, 27, 38, 38, 180), (96, 14, 106, 46, 230), (8, 60, 112, 64, 180),
        ])
        overlap = synthetic_visual_frame([
            (12, 14, 22, 46, 230), (82, 27, 112, 38, 180),
            (8, 27, 38, 38, 180), (96, 14, 106, 46, 230),
            (48, 18, 72, 44, 230), (8, 60, 112, 64, 180),
        ])

        # Four 0.1 s samples model a 0.35 s overlap that a 0.5 s OCR pass can miss.
        metrics = self.analyze([before] * 8 + [overlap] * 4 + [after] * 8)

        self.assertTrue(any(
            finding["evidence"]["kind"] == "destructive_transition_collision"
            and finding["publish_blocking"]
            for finding in metrics["findings"]
        ))

    @unittest.skipUnless(
        shutil.which("ffmpeg")
        and Path(
            "/private/tmp/mit-8-01-physics-corrected-20260711-v12/videos/"
            "short_05_rocket-equation_preview.mp4"
        ).is_file(),
        "known bad physics preview fixture is not available",
    )
    def test_known_bad_rocket_preview_has_blocking_regional_loss(self) -> None:
        video = Path(
            "/private/tmp/mit-8-01-physics-corrected-20260711-v12/videos/"
            "short_05_rocket-equation_preview.mp4"
        )
        frames = audit_video_frames.sample_gray_frames(
            shutil.which("ffmpeg") or "ffmpeg",
            video,
            interval=0.1,
            width=audit_video_frames.TEMPORAL_VISUAL_FRAME_WIDTH,
            height=audit_video_frames.TEMPORAL_VISUAL_FRAME_HEIGHT,
        )
        window_start = 24.0
        start_index = round(window_start / 0.1)
        window = frames[start_index : start_index + 35]

        metrics = audit_video_frames.analyze_temporal_visual_integrity(
            window,
            interval=0.1,
            width=audit_video_frames.TEMPORAL_VISUAL_FRAME_WIDTH,
            height=audit_video_frames.TEMPORAL_VISUAL_FRAME_HEIGHT,
        )

        blocking = [finding for finding in metrics["findings"] if finding["publish_blocking"]]
        self.assertTrue(blocking)
        source_timestamps = [window_start + float(finding["timestamp_seconds"]) for finding in blocking]
        self.assertTrue(any(25.5 <= timestamp <= 26.2 for timestamp in source_timestamps))


class VisualAuditSeverityTests(unittest.TestCase):
    def make_run(self, flags: list[str], serious_flags: list[str]) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        run = Path(temporary.name)
        video = run / "videos" / "short_01_example_final.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(b"video")
        contact = run / "visual_audit" / "short_01_example_final_contact.jpg"
        contact.parent.mkdir(parents=True)
        contact.write_bytes(b"image")
        report = {
            "settings": {"contact_sheet_interval_seconds": 0.5},
            "videos": [
                {
                    "video": "videos/short_01_example_final.mp4",
                    "contact_sheet": "visual_audit/short_01_example_final_contact.jpg",
                    "contact_sheet_coverage": {"covers_entire_video": True},
                    "metrics": {
                        "sampled_frames": 12,
                        "review_flags": flags,
                        "serious_review_flags": serious_flags,
                        "ocr_text_layout": {"available": True, "sampled_frames": 6},
                    },
                }
            ]
        }
        (run / "visual_frame_audit.json").write_text(json.dumps(report), encoding="utf-8")
        return temporary, run

    def test_strict_validation_fails_publish_blocking_layout_flag(self) -> None:
        temporary, run = self.make_run(["rendered_text_overlap"], ["rendered_text_overlap"])
        self.addCleanup(temporary.cleanup)
        validator = CourseRunValidator(run)

        validator.validate_visual_frame_audit(None)

        self.assertTrue(any(issue.severity == "FAIL" and issue.area == "visual-audit" for issue in validator.issues))

    def test_draft_validation_warns_for_publish_blocking_layout_flag(self) -> None:
        temporary, run = self.make_run(["rendered_text_overlap"], ["rendered_text_overlap"])
        self.addCleanup(temporary.cleanup)
        validator = CourseRunValidator(run, draft=True)

        validator.validate_visual_frame_audit(None)

        self.assertFalse(any(issue.severity == "FAIL" for issue in validator.issues))
        self.assertTrue(any(issue.severity == "WARN" and "publish-blocking" in issue.message for issue in validator.issues))

    def test_review_only_flag_warns_in_strict_mode(self) -> None:
        temporary, run = self.make_run(["low_confidence_rendered_text"], [])
        self.addCleanup(temporary.cleanup)
        validator = CourseRunValidator(run)

        validator.validate_visual_frame_audit(None)

        self.assertFalse(any(issue.severity == "FAIL" for issue in validator.issues))
        self.assertTrue(any(issue.severity == "WARN" for issue in validator.issues))

    def test_sparse_contact_sheet_sampling_fails_strict_validation(self) -> None:
        temporary, run = self.make_run([], [])
        self.addCleanup(temporary.cleanup)
        report_path = run / "visual_frame_audit.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["settings"]["contact_sheet_interval_seconds"] = 4.0
        report_path.write_text(json.dumps(report), encoding="utf-8")
        validator = CourseRunValidator(run)

        validator.validate_visual_frame_audit(None)

        self.assertTrue(
            any(issue.severity == "FAIL" and issue.area == "visual-audit.sampling" for issue in validator.issues)
        )

    def test_incomplete_contact_sheet_coverage_fails_strict_validation(self) -> None:
        temporary, run = self.make_run([], [])
        self.addCleanup(temporary.cleanup)
        report_path = run / "visual_frame_audit.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["videos"][0]["contact_sheet_coverage"]["covers_entire_video"] = False
        report_path.write_text(json.dumps(report), encoding="utf-8")
        validator = CourseRunValidator(run)

        validator.validate_visual_frame_audit(None)

        self.assertTrue(
            any(issue.severity == "FAIL" and issue.area == "visual-audit.coverage" for issue in validator.issues)
        )


if __name__ == "__main__":
    unittest.main()

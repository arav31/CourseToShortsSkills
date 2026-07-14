from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from tools.validate_course_run import (
    CourseRunValidator,
    notes_pdf_layout_findings,
    pdf_page_layout_geometry,
    pdf_text_intersections,
)


class NotesPdfLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary_directory = tempfile.TemporaryDirectory(prefix="notes-pdf-layout-")
        cls.addClassCleanup(cls._temporary_directory.cleanup)
        cls.pdf_path = Path(cls._temporary_directory.name) / "notes.pdf"
        cls._build_fixture(cls.pdf_path)
        with fitz.open(cls.pdf_path) as document:
            cls.findings = notes_pdf_layout_findings(document)

    @staticmethod
    def _add_dense_prose(page: fitz.Page, *, skip_math_band: bool = False) -> None:
        for row, y in enumerate(range(70, 721, 15), start=1):
            if skip_math_band and 360 <= y <= 435:
                continue
            page.insert_text(
                (72, y),
                f"Dense course prose line {row}: definitions, derivations, evidence, and worked reasoning.",
                fontsize=9,
            )

    @staticmethod
    def _add_calibrated_collision(page: fitz.Page, *, baseline: float = 150.0) -> None:
        page.insert_text((100, baseline), "10", fontsize=21)
        page.insert_text((121.61, baseline + 17.75), "in-order sequence", fontsize=21)

    @classmethod
    def _add_dense_inline_math(cls, page: fitz.Page) -> None:
        cls._add_dense_prose(page, skip_math_band=True)
        prefix = "A permutation in S"
        script_x = 72 + fitz.get_text_length(prefix, fontsize=10)
        page.insert_text((72, 400), prefix, fontsize=10)
        page.insert_text((script_x, 406), "n", fontsize=7)
        page.insert_text((script_x + 7, 400), " is a product of disjoint cycles.", fontsize=10)

    @staticmethod
    def _add_figure_local_collision(page: fitz.Page) -> None:
        page.draw_rect(fitz.Rect(215, 450, 400, 570), width=1)
        page.insert_text((250, 520), "G", fontsize=21)
        page.insert_text((264.5, 537.75), "kernel", fontsize=21)
        page.insert_text((185, 600), "Figure 8: Kernel and image map.", fontsize=10)

    @staticmethod
    def _add_prose_through(page: fitz.Page, bottom: int) -> None:
        for row, y in enumerate(range(70, bottom + 1, 15), start=1):
            page.insert_text((72, y), f"Flowing course prose line {row} with substantive explanation.", fontsize=9)

    @classmethod
    def _build_fixture(cls, path: Path) -> None:
        document = fitz.open()
        for page_number in range(1, 57):
            page = document.new_page(width=612, height=792)
            if page_number == 1:
                page.insert_text((165, 120), "Rendered Course Notes", fontsize=24)
                cls._add_calibrated_collision(page, baseline=190)
                page.draw_rect(fitz.Rect(90, 145, 430, 230), width=1)
                page.insert_text((205, 270), "Figure 1: Cover artwork.", fontsize=10)
            elif page_number == 2:
                cls._add_dense_prose(page)
            elif page_number == 3:
                cls._add_dense_prose(page, skip_math_band=True)
                page.insert_text((180, 400), "H", fontsize=18)
                page.insert_text((191.5, 406), "2", fontsize=10)
                page.insert_text((202, 400), "+ dense display math = 0", fontsize=18)
            elif page_number == 4:
                page.draw_rect(fitz.Rect(90, 80, 430, 230), width=1)
                page.insert_text((185, 270), "This figure explains the model.", fontsize=10)
            elif page_number == 9:
                cls._add_dense_inline_math(page)
            elif page_number == 15:
                cls._add_figure_local_collision(page)
            elif page_number == 19:
                cls._add_prose_through(page, 475)
            elif page_number == 20:
                page.draw_rect(fitz.Rect(90, 80, 430, 230), width=1)
                cls._add_calibrated_collision(page)
                page.insert_text((185, 270), "Figure 20: State model for AVL trees.", fontsize=10)
            elif page_number == 30:
                cls._add_prose_through(page, 475)
            elif page_number == 31:
                page.insert_text((72, 70), "A New Explicit Section", fontsize=16)
                page.draw_rect(fitz.Rect(90, 105, 430, 235), width=1)
                page.insert_text((185, 270), "Figure 31: Intentional section-opening figure.", fontsize=10)
            elif page_number == 56:
                page.draw_rect(fitz.Rect(90, 80, 500, 260), width=1)
                page.insert_text((180, 115), "Complexity plot", fontsize=18)
                page.insert_text((190, 298), "Figure 56: State model for complexity.", fontsize=10)
            else:
                page.insert_text((72, 80), f"Course notes page {page_number}", fontsize=10)
        document.save(path)
        document.close()

    def findings_for(self, page_number: int, kind: str | None = None) -> list[dict[str, object]]:
        return [
            finding
            for finding in self.findings
            if finding["page_number"] == page_number and (kind is None or finding["kind"] == kind)
        ]

    def test_page_20_detects_the_narrow_but_tall_text_run_intersection(self) -> None:
        overlaps = self.findings_for(20, "text-intersection")

        self.assertEqual(len(overlaps), 1)
        self.assertAlmostEqual(float(overlaps[0]["width"]), 1.74, delta=0.03)
        self.assertAlmostEqual(float(overlaps[0]["height"]), 11.10, delta=0.08)
        self.assertIn("Page 20", str(overlaps[0]["message"]))
        self.assertIn("'10'", str(overlaps[0]["message"]))
        self.assertIn("'in-order sequence'", str(overlaps[0]["message"]))

    def test_sparse_figure_spill_pages_report_calibrated_blank_runs(self) -> None:
        page_20 = self.findings_for(20, "sparse-figure-page")
        page_56 = self.findings_for(56, "sparse-figure-page")

        self.assertEqual(len(page_20), 1)
        self.assertEqual(len(page_56), 1)
        self.assertAlmostEqual(float(page_20[0]["blank_ratio"]), 0.68, delta=0.01)
        self.assertAlmostEqual(float(page_56[0]["blank_ratio"]), 0.64, delta=0.01)
        self.assertIn("Page 20", str(page_20[0]["message"]))
        self.assertIn("Page 56", str(page_56[0]["message"]))

    def test_trailing_blank_before_next_page_figure_is_detected(self) -> None:
        findings = self.findings_for(19, "trailing-blank-before-figure")

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["next_page_number"], 20)
        self.assertEqual(findings[0]["caption"], "Figure 20")
        self.assertGreaterEqual(float(findings[0]["blank_ratio"]), 0.35)
        self.assertLess(float(findings[0]["blank_ratio"]), 0.45)
        self.assertIn("begins page 20", str(findings[0]["message"]))

    def test_explicit_section_break_is_excluded_but_final_page_figure_is_checked(self) -> None:
        self.assertEqual(self.findings_for(30, "trailing-blank-before-figure"), [])
        findings = self.findings_for(55, "trailing-blank-before-figure")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["next_page_number"], 56)
        self.assertEqual(findings[0]["caption"], "Figure 56")

    def test_title_dense_prose_and_display_math_pages_pass(self) -> None:
        self.assertEqual(self.findings_for(1), [])
        self.assertEqual(self.findings_for(2), [])
        self.assertEqual(self.findings_for(3), [])

    def test_dense_inline_math_without_a_figure_caption_passes(self) -> None:
        with fitz.open(self.pdf_path) as document:
            runs, _, captions = pdf_page_layout_geometry(document[8])

        self.assertTrue(any(run["text"] == "n" and run["size"] == 7 for run in runs))
        self.assertEqual(captions, [])
        self.assertEqual(self.findings_for(9), [])

    def test_captioned_figure_local_collision_is_detected(self) -> None:
        overlaps = self.findings_for(15, "text-intersection")

        self.assertEqual(len(overlaps), 1)
        self.assertEqual({overlaps[0]["first"], overlaps[0]["second"]}, {"G", "kernel"})
        self.assertIn("Page 15", str(overlaps[0]["message"]))

    def test_figure_caption_must_be_anchored_and_numbered(self) -> None:
        with fitz.open(self.pdf_path) as document:
            _, _, incidental_captions = pdf_page_layout_geometry(document[3])
            _, _, anchored_captions = pdf_page_layout_geometry(document[19])

        self.assertEqual(incidental_captions, [])
        self.assertEqual(len(anchored_captions), 1)
        self.assertEqual(anchored_captions[0]["label"], "Figure 20")
        self.assertEqual(anchored_captions[0]["number"], 20)
        self.assertEqual(self.findings_for(4), [])

    def test_same_line_tex_and_ordinary_touching_are_filtered(self) -> None:
        same_line_tex = [
            {"text": "H", "font": "CMR10", "bbox": (100.0, 100.0, 114.0, 120.0), "line_id": (1, 1)},
            {"text": "2", "font": "CMR7", "bbox": (112.0, 108.0, 119.0, 122.0), "line_id": (1, 1)},
        ]
        ordinary_touching = [
            {"text": "node", "font": "CMR10", "bbox": (100.0, 100.0, 120.0, 115.0), "line_id": (1, 1)},
            {"text": "label", "font": "CMR10", "bbox": (119.5, 104.0, 150.0, 119.0), "line_id": (2, 1)},
        ]
        control_only = [
            {"text": "label", "font": "CMR10", "bbox": (100.0, 100.0, 130.0, 120.0), "line_id": (1, 1)},
            {"text": "\x00\x01", "font": "LMMathExtension10", "bbox": (110.0, 105.0, 125.0, 122.0), "line_id": (2, 1)},
        ]
        delimiter_artifact = [
            {"text": "prose", "font": "LMRoman10", "bbox": (100.0, 100.0, 140.0, 120.0), "line_id": (1, 1)},
            {"text": "!", "font": "LMMathExtension10", "bbox": (115.0, 108.0, 125.0, 125.0), "line_id": (2, 1)},
        ]

        self.assertEqual(pdf_text_intersections(same_line_tex), [])
        self.assertEqual(pdf_text_intersections(ordinary_touching), [])
        self.assertEqual(pdf_text_intersections(control_only), [])
        self.assertEqual(pdf_text_intersections(delimiter_artifact), [])

    def test_validator_emits_page_numbered_nonempty_failures(self) -> None:
        validator = CourseRunValidator(self.pdf_path.parent)

        validator.check_pdf_file(self.pdf_path)

        layout_issues = [issue for issue in validator.issues if issue.area == "notes.pdf.layout"]
        self.assertGreaterEqual(len(layout_issues), 4)
        self.assertTrue(all(issue.severity == "FAIL" for issue in layout_issues))
        self.assertTrue(all(issue.message.strip() for issue in layout_issues))
        self.assertTrue(all("Page " in issue.message for issue in layout_issues))
        self.assertTrue(any("Page 20" in issue.message for issue in layout_issues))
        self.assertTrue(any("Page 56" in issue.message for issue in layout_issues))
        self.assertFalse(any(issue.message.startswith("Page 1 ") for issue in layout_issues))


class NotesPdfGenericFlowTests(unittest.TestCase):
    @staticmethod
    def _title_page(document: fitz.Document) -> None:
        page = document.new_page(width=612, height=792)
        page.insert_text((170, 120), "Intentional Course Title", fontsize=24)

    @staticmethod
    def _dense_page(document: fitz.Document, *, discussion: str | None = None) -> fitz.Page:
        page = document.new_page(width=612, height=792)
        for row, y in enumerate(range(70, 721, 15), start=1):
            text = f"Substantive prose line {row} with definitions, derivations, and interpretation."
            if row == 8 and discussion:
                text = discussion
            page.insert_text((72, y), text, fontsize=9)
        return page

    @staticmethod
    def _captioned_figure(page: fitz.Page, *, number: int) -> None:
        page.draw_rect(fitz.Rect(330, 250, 520, 390), width=1)
        page.insert_text((335, 420), f"Figure {number}: A local state diagram.", fontsize=10)

    @staticmethod
    def _findings(document: fitz.Document) -> list[dict[str, object]]:
        with tempfile.TemporaryDirectory(prefix="generic-notes-layout-") as temporary:
            path = Path(temporary) / "notes.pdf"
            document.save(path)
            document.close()
            with fitz.open(path) as rendered:
                return notes_pdf_layout_findings(rendered)

    def test_sparse_final_prose_page_is_detected(self) -> None:
        document = fitz.open()
        self._title_page(document)
        self._dense_page(document)
        final_page = document.new_page(width=612, height=792)
        for row, y in enumerate((70, 85, 100), start=1):
            final_page.insert_text((72, y), f"Final fragment line {row} with a little prose.", fontsize=9)

        findings = self._findings(document)

        sparse_final = [finding for finding in findings if finding["kind"] == "sparse-final-prose-page"]
        self.assertEqual(len(sparse_final), 1)
        self.assertEqual(sparse_final[0]["page_number"], 3)
        self.assertLess(float(sparse_final[0]["body_occupancy_ratio"]), 0.18)

    def test_healthy_final_prose_page_passes(self) -> None:
        document = fitz.open()
        self._title_page(document)
        self._dense_page(document)

        findings = self._findings(document)

        self.assertFalse(any(finding["kind"] == "sparse-final-prose-page" for finding in findings))

    def test_intentional_title_page_is_exempt(self) -> None:
        document = fitz.open()
        self._title_page(document)

        self.assertEqual(self._findings(document), [])

    def test_figure_discussion_and_caption_on_same_page_pass(self) -> None:
        document = fitz.open()
        self._title_page(document)
        page = self._dense_page(document, discussion="As the figure shows, every state has one successor.")
        self._captioned_figure(page, number=2)

        findings = self._findings(document)

        self.assertFalse(any(finding["kind"] == "detached-figure-discussion" for finding in findings))

    def test_unnumbered_figure_discussion_detached_from_caption_fails(self) -> None:
        document = fitz.open()
        self._title_page(document)
        self._dense_page(document, discussion="As the figure shows, every state has one successor.")
        figure_page = self._dense_page(document)
        self._captioned_figure(figure_page, number=3)

        findings = self._findings(document)

        detached = [finding for finding in findings if finding["kind"] == "detached-figure-discussion"]
        self.assertEqual(len(detached), 1)
        self.assertEqual(detached[0]["page_number"], 2)
        self.assertEqual(detached[0]["caption_page_number"], 3)

    def test_explicit_figure_reference_can_point_to_another_page(self) -> None:
        document = fitz.open()
        self._title_page(document)
        self._dense_page(document, discussion="As the figure in Figure 3 shows, every state has one successor.")
        figure_page = self._dense_page(document)
        self._captioned_figure(figure_page, number=3)

        findings = self._findings(document)

        self.assertFalse(any(finding["kind"] == "detached-figure-discussion" for finding in findings))


if __name__ == "__main__":
    unittest.main()

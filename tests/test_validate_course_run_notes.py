from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import fitz

from tools.validate_course_run import (
    CourseRunValidator,
    latex_bmatrix_findings,
    notes_pdf_layout_findings,
)


def passing_coverage() -> dict[str, object]:
    return {
        "status": "ok",
        "topic_count": 1,
        "outline_coverage_status": "ok",
        "missing_outline_topic_count": 0,
        "source_subtopic_status": "not-applicable",
        "missing_source_subtopic_count": 0,
        "page_integrity_status": "ok",
        "page_integrity_findings": [],
        "topics": [
            {
                "concept": "Linear systems",
                "status": "ok",
                "checks": {"formal_definition": True, "figure_generated": True, "figure_example_binding": True},
                "missing": [],
            }
        ],
    }


class NotesCoverageValidatorTests(unittest.TestCase):
    def test_missing_report_fails_strict_validation_but_warns_in_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            strict = CourseRunValidator(run)
            draft = CourseRunValidator(run, draft=True)

            strict.validate_notes_coverage_report()
            draft.validate_notes_coverage_report()

            self.assertEqual([(issue.area, issue.severity) for issue in strict.issues], [("notes.coverage", "FAIL")])
            self.assertEqual([(issue.area, issue.severity) for issue in draft.issues], [("notes.coverage", "WARN")])

    def test_missing_or_failed_overall_status_fails_closed(self) -> None:
        for status in (None, "failed"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary:
                run = Path(temporary)
                report = passing_coverage()
                if status is None:
                    report.pop("status")
                else:
                    report["status"] = status
                (run / "notes_coverage_report.json").write_text(json.dumps(report), encoding="utf-8")
                validator = CourseRunValidator(run)

                validator.validate_notes_coverage_report()

                failures = [issue for issue in validator.issues if issue.area == "notes.coverage"]
                self.assertEqual(len(failures), 1)
                self.assertEqual(failures[0].severity, "FAIL")

    def test_topic_gaps_page_integrity_and_figure_bindings_fail_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            report = passing_coverage()
            report.update(
                {
                    "status": "failed",
                    "outline_coverage_status": "failed",
                    "missing_outline_topic_count": 2,
                    "source_subtopic_status": "failed",
                    "missing_source_subtopic_count": 1,
                    "page_integrity_status": "failed",
                    "page_integrity_findings": [{"page": 4, "kind": "overlap"}],
                }
            )
            topic = report["topics"][0]
            topic["status"] = "ok"
            topic["checks"]["figure_example_binding"] = False
            topic["missing"] = []
            (run / "notes_coverage_report.json").write_text(json.dumps(report), encoding="utf-8")
            validator = CourseRunValidator(run)

            validator.validate_notes_coverage_report()

            areas = [issue.area for issue in validator.issues if issue.severity == "FAIL"]
            self.assertIn("notes.coverage", areas)
            self.assertIn("notes.coverage.topics", areas)
            self.assertIn("notes.coverage.figures", areas)
            self.assertEqual(areas.count("notes.coverage.gaps"), 2)
            self.assertIn("notes.coverage.page-integrity", areas)

    def test_complete_report_passes_coverage_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "notes_coverage_report.json").write_text(json.dumps(passing_coverage()), encoding="utf-8")
            validator = CourseRunValidator(run)

            validator.validate_notes_coverage_report()

            self.assertEqual(validator.issues, [])


class NotesLatexStructureValidatorTests(unittest.TestCase):
    def test_generated_top_level_sections_are_counted_as_topics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "notes.tex"
            sections = "\n".join(rf"\section{{Topic {index}}}" for index in range(16))
            subsections = "\n".join(rf"\subsection{{Extension {index}}}" for index in range(24))
            figures = "\n".join(r"\begin{tikzpicture}\end{tikzpicture}" for _ in range(4))
            path.write_text(sections + subsections + figures + (" substantive" * 3000), encoding="utf-8")
            validator = CourseRunValidator(path.parent)

            validator.scan_notes_comprehensiveness(path)

            self.assertFalse(any(issue.area == "notes.figures" for issue in validator.issues))

    def test_bmatrix_structure_rejects_ragged_and_malformed_rows(self) -> None:
        ragged = r"\[\begin{bmatrix}1 & 2 \\ 3 & 4 & 5\end{bmatrix}\]"
        malformed = r"\[\begin{bmatrix}1 & 2 \ 3 & 4\end{bmatrix}\]"

        ragged_messages = [finding["message"] for finding in latex_bmatrix_findings(ragged)]
        malformed_messages = [finding["message"] for finding in latex_bmatrix_findings(malformed)]

        self.assertTrue(any("ragged rows" in message for message in ragged_messages))
        self.assertTrue(any("malformed" in message for message in malformed_messages))

    def test_oversized_inline_matrix_fails_while_display_matrix_passes(self) -> None:
        body = r"\begin{bmatrix}1 & 2 & 3 \\ 4 & 5 & 6 \\ 7 & 8 & 9\end{bmatrix}"

        inline_messages = [finding["message"] for finding in latex_bmatrix_findings(f"${body}$")]
        display_messages = [finding["message"] for finding in latex_bmatrix_findings(rf"\[{body}\]")]

        self.assertTrue(any("oversized" in message for message in inline_messages))
        self.assertEqual(display_messages, [])

    def test_algorithm_array_slices_do_not_look_like_matrices(self) -> None:
        algorithm = r"For each slice $A[i:j]$, update $table[i][j]$ from $cost[i, j]$."

        self.assertEqual(latex_bmatrix_findings(algorithm), [])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "notes.tex"
            path.write_text(algorithm, encoding="utf-8")
            validator = CourseRunValidator(path.parent)
            validator.scan_latex_quality(path)
            self.assertFalse(any(issue.area.startswith("notes.latex.matrix") for issue in validator.issues))


class NotesPdfAdjacentPageValidatorTests(unittest.TestCase):
    def test_penultimate_page_is_checked_before_a_final_page_figure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pdf_path = Path(temporary) / "notes.pdf"
            document = fitz.open()
            title = document.new_page(width=612, height=792)
            title.insert_text((170, 120), "Course Notes", fontsize=24)
            prose = document.new_page(width=612, height=792)
            for row, y in enumerate(range(70, 476, 15), start=1):
                prose.insert_text((72, y), f"Substantive prose line {row} with definitions and derivations.", fontsize=9)
            figure = document.new_page(width=612, height=792)
            figure.draw_rect(fitz.Rect(90, 80, 430, 230), width=1)
            figure.insert_text((175, 270), "Figure 3: Final-page state model.", fontsize=10)
            document.save(pdf_path)
            document.close()

            with fitz.open(pdf_path) as rendered:
                findings = notes_pdf_layout_findings(rendered)

            transitions = [finding for finding in findings if finding["kind"] == "trailing-blank-before-figure"]
            self.assertEqual(len(transitions), 1)
            self.assertEqual(transitions[0]["page_number"], 2)
            self.assertEqual(transitions[0]["next_page_number"], 3)

    def test_sparse_prose_before_an_explicit_section_boundary_is_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pdf_path = Path(temporary) / "notes.pdf"
            document = fitz.open()
            title = document.new_page(width=612, height=792)
            title.insert_text((170, 120), "Course Notes", fontsize=24)
            short_section_end = document.new_page(width=612, height=792)
            for row, y in enumerate((70, 85, 100), start=1):
                short_section_end.insert_text((72, y), f"Closing section thought {row} with context.", fontsize=9)
            next_section = document.new_page(width=612, height=792)
            next_section.insert_text((72, 70), "A New Explicit Section", fontsize=16)
            for row, y in enumerate(range(100, 721, 15), start=1):
                next_section.insert_text((72, y), f"New section prose line {row} with full reasoning.", fontsize=9)
            document.save(pdf_path)
            document.close()

            with fitz.open(pdf_path) as rendered:
                findings = notes_pdf_layout_findings(rendered)

            generic_sparse = {
                "low-body-occupancy",
                "excessive-trailing-blank",
                "sparse-final-prose-page",
            }
            self.assertFalse(
                any(finding["page_number"] == 2 and finding["kind"] in generic_sparse for finding in findings)
            )

    def test_excessive_trailing_blank_on_prose_page_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pdf_path = Path(temporary) / "notes.pdf"
            document = fitz.open()
            title = document.new_page(width=612, height=792)
            title.insert_text((170, 120), "Course Notes", fontsize=24)
            short_page = document.new_page(width=612, height=792)
            for row, y in enumerate(range(70, 341, 15), start=1):
                short_page.insert_text((72, y), f"Body prose line {row} with substantive explanation.", fontsize=9)
            final_page = document.new_page(width=612, height=792)
            for row, y in enumerate(range(70, 721, 15), start=1):
                final_page.insert_text((72, y), f"Healthy final prose line {row} with reasoning.", fontsize=9)
            document.save(pdf_path)
            document.close()

            with fitz.open(pdf_path) as rendered:
                findings = notes_pdf_layout_findings(rendered)

            trailing = [
                finding
                for finding in findings
                if finding["page_number"] == 2 and finding["kind"] == "excessive-trailing-blank"
            ]
            self.assertEqual(len(trailing), 1)
            self.assertGreaterEqual(float(trailing[0]["trailing_blank_ratio"]), 0.55)


if __name__ == "__main__":
    unittest.main()

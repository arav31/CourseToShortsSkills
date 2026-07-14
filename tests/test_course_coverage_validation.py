from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_course_run import CourseRunValidator, semantic_course_coverage


class SemanticCourseCoverageTests(unittest.TestCase):
    def test_broad_concept_can_cover_multiple_related_units(self) -> None:
        units = [
            "Momentum and Impulse",
            "Conservation of Momentum",
            "Elastic Collisions",
            "Rotational Dynamics",
            "Angular Momentum of a Rigid Body",
        ]
        videos = ["Momentum, impulse, conservation and elastic collisions", "Rigid body rotational dynamics and angular momentum"]

        report = semantic_course_coverage(units, videos)

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["uncovered_course_unit_count"], 0)

    def test_materially_missing_units_fail_without_a_chapter_quota(self) -> None:
        names = [
            "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india",
            "juliet", "kilo", "lima", "mike", "november", "oscar", "papa", "quebec", "romeo",
            "sierra", "tango", "uniform", "victor", "whiskey", "xray", "yankee", "zulu",
        ]
        units = [f"{name} phenomenon" for name in names]
        videos = [f"{name} phenomenon" for name in names[:20]]

        report = semantic_course_coverage(units, videos)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["uncovered_course_unit_count"], 6)
        self.assertEqual(report["longest_uncovered_run"], 6)

    def test_validator_joins_notes_topics_to_short_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            names = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]
            topics = [{"concept": f"{name} phenomenon"} for name in names]
            shorts = [{"concept": f"{name} phenomenon"} for name in names[:6]]
            (run / "notes_coverage_report.json").write_text(json.dumps({"topics": topics}), encoding="utf-8")
            validator = CourseRunValidator(run)

            validator.validate_course_concept_coverage(shorts)

            failures = [issue for issue in validator.issues if issue.area == "course.coverage" and issue.severity == "FAIL"]
            self.assertEqual(len(failures), 1)
            self.assertIn("4/10 units", failures[0].message)


if __name__ == "__main__":
    unittest.main()

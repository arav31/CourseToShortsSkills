from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools import stem_course
from tests.test_notes_comprehensiveness import mit_18_703_source_pack


class PlannerCoverageSelectionTests(unittest.TestCase):
    @staticmethod
    def pack(title: str, topics: list[str]) -> dict[str, object]:
        calendar = "\n".join(
            f"Unit {index}: {topic}" for index, topic in enumerate(topics, start=1)
        )
        return {
            "title": title,
            "materials": [{"kind": "page", "title": "Course Schedule", "text": calendar}],
        }

    def test_authoritative_economics_units_are_selected_before_library_derivatives(self) -> None:
        topics = [
            "Consumer Choice", "Demand", "Input Markets", "Intertemporal Choice",
            "Production", "Trade", "Uncertainty", "Social Insurance",
        ]

        names = [concept.name for concept in stem_course.choose_concepts(
            self.pack("Intermediate Microeconomics", topics), 12
        )]

        self.assertEqual(names[: len(topics)], topics)
        self.assertGreater(len(names), len(topics))

    def test_selection_is_domain_neutral_and_spans_an_over_budget_outline(self) -> None:
        topics = [
            "Atomic Structure", "Chemical Bonding", "Stoichiometry", "Gas Laws",
            "Thermochemistry", "Reaction Kinetics", "Chemical Equilibrium",
            "Acids and Bases", "Electrochemistry", "Organic Reactions",
        ]

        names = [concept.name for concept in stem_course.choose_concepts(
            self.pack("General Chemistry", topics), 4
        )]

        self.assertEqual(len(names), 4)
        self.assertEqual(names[0], "Atomic Structure")
        self.assertEqual(names[-1], "Organic Reactions")
        self.assertTrue(any(name in topics[3:7] for name in names))

    def test_plan_auto_mode_keeps_every_authoritative_unit_and_does_not_pad(self) -> None:
        topics = [f"Mechanics Unit {index}" for index in range(1, 39)]
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(
                json.dumps(self.pack("Classical Mechanics", topics)), encoding="utf-8"
            )

            stem_course.cmd_plan(
                argparse.Namespace(run=str(run), max_shorts=0, allow_partial_plan=False)
            )

            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            self.assertEqual([short["concept"] for short in plan["shorts"]], topics)
            self.assertEqual(plan["authoritative_unit_count"], 38)
            self.assertEqual(plan["covered_unit_count"], 38)
            self.assertEqual(plan["omitted_units"], [])
            self.assertFalse(plan["coverage_truncated"])

    def test_plan_refuses_silent_authoritative_outline_truncation(self) -> None:
        topics = [f"Economics Unit {index}" for index in range(1, 27)]
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(
                json.dumps(self.pack("Principles of Microeconomics", topics)), encoding="utf-8"
            )

            with self.assertRaisesRegex(SystemExit, "26 authoritative course units"):
                stem_course.cmd_plan(
                    argparse.Namespace(run=str(run), max_shorts=12, allow_partial_plan=False)
                )

    def test_explicit_partial_plan_records_omitted_authoritative_units(self) -> None:
        topics = [f"Chemistry Unit {index}" for index in range(1, 11)]
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(
                json.dumps(self.pack("General Chemistry", topics)), encoding="utf-8"
            )

            stem_course.cmd_plan(
                argparse.Namespace(run=str(run), max_shorts=4, allow_partial_plan=True)
            )

            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            selected = [short["concept"] for short in plan["shorts"]]
            self.assertEqual(len(selected), 4)
            self.assertEqual(plan["authoritative_unit_count"], 10)
            self.assertEqual(plan["covered_unit_count"], 4)
            self.assertEqual(plan["omitted_units"], [topic for topic in topics if topic not in selected])
            self.assertTrue(plan["coverage_truncated"])

    def test_full_plan_stops_at_authoritative_outline_count(self) -> None:
        topics = [f"Course Unit {index}" for index in range(1, 9)]
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(
                json.dumps(self.pack("A Complete Course", topics)), encoding="utf-8"
            )

            stem_course.cmd_plan(
                argparse.Namespace(run=str(run), max_shorts=40, allow_partial_plan=False)
            )

            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            self.assertEqual([short["concept"] for short in plan["shorts"]], topics)
            self.assertEqual(len(plan["shorts"]), len(topics))

    def test_real_mit_mechanics_and_economics_outlines_plan_exactly_in_auto_mode(self) -> None:
        from tests.test_notes_pipeline_integration import (
            ECONOMICS_OUTLINE,
            MECHANICS_OUTLINE,
            outline_pack,
        )

        fixtures = (
            ("MIT 8.01 Classical Mechanics", "https://ocw.mit.edu/8.01", MECHANICS_OUTLINE),
            ("MIT 14.01 Principles of Microeconomics", "https://ocw.mit.edu/14.01", ECONOMICS_OUTLINE),
        )
        for title, source_url, topics in fixtures:
            with self.subTest(title=title), tempfile.TemporaryDirectory() as temp_dir:
                run = Path(temp_dir)
                stem_course.write_json(
                    run / "source_pack.json", outline_pack(title, source_url, topics)
                )
                stem_course.cmd_plan(argparse.Namespace(
                    run=str(run), max_shorts=0, allow_partial_plan=False
                ))
                plan = stem_course.read_json(run / "short_plan.json")
                self.assertEqual([short["concept"] for short in plan["shorts"]], topics)
                self.assertEqual(plan["authoritative_unit_count"], len(topics))
                self.assertEqual(plan["covered_unit_count"], len(topics))
                self.assertEqual(plan["omitted_units"], [])
                self.assertFalse(plan["coverage_truncated"])

    def test_auto_mode_without_outline_uses_sensible_library_default_metadata(self) -> None:
        pack = {"title": "Linear Algebra", "materials": []}
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            stem_course.write_json(run / "source_pack.json", pack)
            stem_course.cmd_plan(argparse.Namespace(
                run=str(run), max_shorts=0, allow_partial_plan=False
            ))
            plan = stem_course.read_json(run / "short_plan.json")
            self.assertGreater(len(plan["shorts"]), 0)
            self.assertLessEqual(len(plan["shorts"]), stem_course.DEFAULT_SHORTS)
            self.assertEqual(plan["authoritative_unit_count"], 0)
            self.assertEqual(plan["covered_unit_count"], 0)
            self.assertEqual(plan["omitted_units"], [])
            self.assertFalse(plan["coverage_truncated"])

    def test_semantically_nested_outline_units_can_share_one_short(self) -> None:
        topics = ["International Trade", "Trade", "Risk and Uncertainty", "Uncertainty"]

        names = [concept.name for concept in stem_course.choose_concepts(
            self.pack("Applied Economics", topics), 2
        )]

        self.assertEqual(names, ["International Trade", "Uncertainty"])

        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(
                json.dumps(self.pack("Applied Economics", topics)), encoding="utf-8"
            )
            stem_course.cmd_plan(argparse.Namespace(
                run=str(run), max_shorts=2, allow_partial_plan=True
            ))
            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            shorts = plan["shorts"]
            mapped = [unit for short in shorts for unit in short["source_outline_units"]]
            self.assertEqual(sorted(mapped), sorted(topics))
            self.assertEqual(plan["covered_unit_count"], 4)
            self.assertEqual(plan["omitted_units"], [])
            self.assertFalse(plan["coverage_truncated"])

    def test_plan_and_all_cli_default_to_auto_full_and_expose_partial_opt_in(self) -> None:
        parser = stem_course.build_parser()
        plan_args = parser.parse_args(["plan", "--run", "/tmp/course"])
        all_args = parser.parse_args(["all", "--out", "/tmp/course"])

        self.assertEqual(plan_args.max_shorts, 0)
        self.assertFalse(plan_args.allow_partial_plan)
        self.assertEqual(all_args.max_shorts, 0)
        self.assertFalse(all_args.allow_partial_plan)
        partial = parser.parse_args([
            "plan", "--run", "/tmp/course", "--max-shorts", "3",
            "--allow-partial-plan",
        ])
        self.assertTrue(partial.allow_partial_plan)

    def test_public_physics_plan_storyboard_accepts_model_route_aliases(self) -> None:
        pack = self.pack("Classical Mechanics", ["Vectors", "Uniform Circular Motion"])
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(json.dumps(pack), encoding="utf-8")
            stem_course.cmd_plan(argparse.Namespace(run=str(run), max_shorts=2))
            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [short["model_id"] for short in plan["shorts"]],
                ["vectors", "uniform_circular_motion"],
            )

            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            supports = [
                json.loads(path.read_text(encoding="utf-8"))["semantic_support"]
                for path in sorted((run / stem_course.ANIMATION_PLAN_DIRECTORY).glob("short_*.json"))
            ]
            self.assertEqual(
                [support["route_key"] for support in supports],
                ["physics:mit-8-01:01:vectors", "physics:mit-8-01:10:uniform_circular_motion"],
            )
            self.assertTrue(all(support["status"] == "supported" for support in supports))

    def test_mit_group_plan_reserves_every_authoritative_calendar_unit(self) -> None:
        pack = mit_18_703_source_pack()
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(json.dumps(pack), encoding="utf-8")

            stem_course.cmd_plan(argparse.Namespace(run=str(run), max_shorts=0))

            shorts = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))["shorts"]
            self.assertEqual(
                [short["concept"] for short in shorts],
                list(stem_course.MIT_18_703_CALENDAR_ORDER),
            )
            self.assertEqual(
                [short["source_outline_units"] for short in shorts],
                [[topic] for topic in stem_course.MIT_18_703_CALENDAR_ORDER],
            )
            self.assertTrue(all(short["coverage_basis"] == "authoritative-outline" for short in shorts))
            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["authoritative_unit_count"], 24)
            self.assertEqual(plan["covered_unit_count"], 24)
            self.assertFalse(plan["coverage_truncated"])
            stem_course.cmd_storyboard(argparse.Namespace(run=str(run)))
            storyboards = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((run / stem_course.ANIMATION_PLAN_DIRECTORY).glob("short_*.json"))
            ]
            self.assertEqual(len(storyboards), 24)
            self.assertTrue(all(plan["semantic_support"]["status"] == "supported" for plan in storyboards))

    def test_cs_plan_covers_all_units_without_metadata_or_numeric_fallbacks(self) -> None:
        from tests.test_course_outline import CourseOutlinePlanningTests

        pack = CourseOutlinePlanningTests().algorithms_pack()
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            (run / "source_pack.json").write_text(json.dumps(pack), encoding="utf-8")

            stem_course.cmd_plan(argparse.Namespace(run=str(run), max_shorts=0))

            shorts = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))["shorts"]
            expected = stem_course.source_outline_topics(pack)
            self.assertEqual([short["concept"] for short in shorts], expected)
            self.assertEqual([short["source_outline_units"] for short in shorts], [[topic] for topic in expected])
            self.assertFalse(any(short["visual_type"] == "numeric_rule" for short in shorts))
            blocked = stem_course.SOURCE_TERM_METADATA_LABELS | {"erik demaine", "jason ku", "justin solomon"}
            self.assertTrue(all(str(short["concept"]).lower() not in blocked for short in shorts))
            plan = json.loads((run / "short_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["authoritative_unit_count"], 18)
            self.assertEqual(plan["covered_unit_count"], 18)
            self.assertFalse(plan["coverage_truncated"])


if __name__ == "__main__":
    unittest.main()

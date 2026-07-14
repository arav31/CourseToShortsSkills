from __future__ import annotations

import argparse
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course
from tests.test_notes_comprehensiveness import mit_18_703_source_pack


MECHANICS_OUTLINE = [
    "Vectors",
    "1D Kinematics - Position and Velocity",
    "1D Kinematics - Acceleration",
    "2D Kinematics",
    "Newton's Laws of Motion",
    "Gravity",
    "Contact Forces",
    "Tension and Springs",
    "Circular Motion - Position and Velocity",
    "Uniform Circular Motion",
    "Circular Motion \u2013 Acceleration",
    "Newton's 2nd Law and Circular Motion",
    "Pulleys and Constraints",
    "Massive Rope",
    "Resistive Forces",
    "Momentum and Impulse",
    "Conservation of Momentum",
    "Center of Mass and Motion",
    "Relative Velocity and Recoil",
    "Continuous Mass Transfer",
    "Kinetic Energy and Work in 1D",
    "Kinetic Energy and Work in 2D and 3D",
    "Conservative and Non-Conservative Forces",
    "Potential Energy",
    "Conservation of Energy",
    "Potential Energy Diagrams",
    "Types of Collision",
    "Elastic Collisions",
    "Motion of a Rigid Body",
    "Moment of Inertia",
    "Torque",
    "Rotational Dynamics",
    "Angular Momentum of a Point Particle",
    "Angular Momentum of a Rigid Body",
    "Torque and Angular Impulse",
    "Rolling Kinematics",
    "Rolling Dynamics",
    "Rolling Kinetic Energy & Angular Momentum",
]


ECONOMICS_OUTLINE = [
    "Introduction and Supply & Demand",
    "Preferences and Utility Functions",
    "Budget Constraints and Constrained Choice",
    "Demand Curves and Income/Substitution Effects",
    "Production Theory",
    "Costs",
    "Competition I",
    "Competition II",
    "Supply and Demand & Consumer/Producer Surplus",
    "Welfare Economics",
    "Monopoly I",
    "Monopoly II",
    "Oligopoly I",
    "Oligopoly II",
    "Input Markets I\u2014Labor Market",
    "Input Markets II\u2014Labor and Capital",
    "Making Choices over Time",
    "Introduction to Trade",
    "International Trade: Welfare and Policy",
    "Uncertainty",
    "Social Insurance",
    "Efficiency and Equity",
    "Government Redistribution and Taxation",
    "Externalities",
    "Behavioral Economics",
    "Healthcare Economics",
]


def outline_pack(title: str, source_url: str, topics: list[str]) -> dict[str, object]:
    calendar = "\n".join(
        f"Lecture {index}: {topic}" for index, topic in enumerate(topics, start=1)
    )
    return {
        "title": title,
        "source_url": source_url,
        "materials": [{"kind": "page", "title": "Course calendar", "text": calendar}],
    }


class NotesOutlineIntegrationTests(unittest.TestCase):
    def test_all_mechanics_and_economics_notes_pass_comprehensive_coverage(self) -> None:
        courses = [
            (
                "MIT 8.01 Classical Mechanics",
                "https://ocw.mit.edu/courses/8-01sc-classical-mechanics/",
                MECHANICS_OUTLINE,
            ),
            (
                "MIT 14.01 Principles of Microeconomics",
                "https://ocw.mit.edu/courses/14-01-principles-of-microeconomics/",
                ECONOMICS_OUTLINE,
            ),
        ]

        for title, source_url, outline in courses:
            with self.subTest(course=title):
                pack = outline_pack(title, source_url, outline)
                shorts = stem_course.full_note_shorts(pack, {"shorts": []})
                report = stem_course.notes_coverage_ledger(shorts, pack)

                self.assertEqual(report["status"], "ok")
                self.assertEqual(report["failed_topic_count"], 0)
                self.assertEqual(len(report["topics"]), len(outline))
                self.assertGreater(sum(row["word_count"] for row in report["topics"]), 20_000)
                for short, row in zip(shorts, report["topics"]):
                    self.assertTrue(all(row["checks"].values()), row)
                    self.assertEqual(row["quality_contract"]["source_noise_hits"], [])
                    self.assertGreaterEqual(short["note_depth"]["source_context_count"], 1)
                    self.assertIsInstance(short.get("model_scenario"), dict)
                    self.assertTrue(short["note_depth"]["figure"])

    def test_trusted_heading_escapes_plain_ampersands(self) -> None:
        self.assertEqual(
            stem_course.notes_trusted_tex("Kinetic Energy & Angular Momentum"),
            r"Kinetic Energy \& Angular Momentum",
        )

    def test_all_38_mechanics_outline_units_are_retained_in_order(self) -> None:
        pack = outline_pack(
            "MIT 8.01 Classical Mechanics",
            "https://ocw.mit.edu/courses/8-01sc-classical-mechanics/",
            MECHANICS_OUTLINE,
        )

        shorts = stem_course.full_note_shorts(pack, {"shorts": []})

        self.assertEqual([short["concept"] for short in shorts], MECHANICS_OUTLINE)
        self.assertEqual(len(shorts), 38)
        self.assertTrue(all(short["notes_resolution_status"] == "ok" for short in shorts))
        self.assertTrue(all(short.get("model_id") for short in shorts))
        self.assertTrue(all(isinstance(short.get("model_scenario"), dict) for short in shorts))

    def test_all_26_economics_outline_units_are_retained_in_order(self) -> None:
        pack = outline_pack(
            "MIT 14.01 Principles of Microeconomics",
            "https://ocw.mit.edu/courses/14-01-principles-of-microeconomics/",
            ECONOMICS_OUTLINE,
        )

        shorts = stem_course.full_note_shorts(pack, {"shorts": []})

        self.assertEqual([short["concept"] for short in shorts], ECONOMICS_OUTLINE)
        self.assertEqual(len(shorts), 26)
        self.assertTrue(all(short["notes_resolution_status"] == "ok" for short in shorts))
        self.assertTrue(all(
            short.get("model_id") or short.get("source_grounded_notes_fallback")
            for short in shorts
        ))

    def test_model_notes_replace_planned_visual_with_resolved_visual(self) -> None:
        pack = outline_pack(
            "MIT 14.01 Principles of Microeconomics",
            "https://ocw.mit.edu/courses/14-01-principles-of-microeconomics/",
            ["Production Theory"],
        )
        shorts = stem_course.full_note_shorts(
            pack,
            {"shorts": [{"index": 1, "concept": "Production Theory", "visual_type": "numeric_rule"}]},
        )

        report = stem_course.notes_coverage_ledger(shorts, pack)

        self.assertEqual(shorts[0]["visual_type"], "econ_curve")
        self.assertTrue(report["topics"][0]["checks"]["figure_generated"])

    def test_model_development_claim_targets_computed_state(self) -> None:
        pack = outline_pack(
            "MIT 8.01 Classical Mechanics",
            "https://ocw.mit.edu/courses/8-01sc-classical-mechanics/",
            ["1D Kinematics - Acceleration"],
        )
        shorts = stem_course.full_note_shorts(pack, {"shorts": []})

        report = stem_course.notes_coverage_ledger(shorts, pack)
        contract = shorts[0]["note_depth"]["development_claim_contract"]

        self.assertEqual(contract["target"], shorts[0]["note_depth"]["results"][1]["name"])
        self.assertEqual(contract["status"], "ok")
        self.assertTrue(report["topics"][0]["checks"]["development_claim_binding"])

    def test_compact_model_fields_bind_development_claims(self) -> None:
        pack = outline_pack(
            "MIT 14.01 Principles of Microeconomics",
            "https://ocw.mit.edu/courses/14-01-principles-of-microeconomics/",
            ["Supply and Demand & Consumer/Producer Surplus"],
        )
        shorts = stem_course.full_note_shorts(pack, {"shorts": []})

        report = stem_course.notes_coverage_ledger(shorts, pack)
        contract = shorts[0]["note_depth"]["development_claim_contract"]

        self.assertEqual(contract["status"], "ok")
        self.assertIn("equation", contract["matched"])
        self.assertIn("1350", contract["matched"])
        self.assertTrue(report["topics"][0]["checks"]["development_claim_binding"])

    def test_reference_choices_do_not_read_as_source_dump_metadata(self) -> None:
        pack = outline_pack(
            "MIT 8.01 Classical Mechanics",
            "https://ocw.mit.edu/courses/8-01sc-classical-mechanics/",
            ["Newton's Laws of Motion"],
        )
        shorts = stem_course.full_note_shorts(pack, {"shorts": []})

        report = stem_course.notes_coverage_ledger(shorts, pack)
        row = report["topics"][0]

        self.assertIn("declared reference choices", shorts[0]["note_depth"]["development"])
        self.assertNotIn("declared references", shorts[0]["note_depth"]["development"])
        self.assertTrue(row["checks"]["no_source_dump_noise"])
        self.assertEqual(row["quality_contract"]["source_noise_hits"], [])

    def test_source_subtopic_failure_reason_is_domain_neutral_and_names_topic(self) -> None:
        pack = outline_pack(
            "MIT Classical Mechanics",
            "https://example.test/mechanics",
            ["Newton's Laws", "Angular Momentum"],
        )
        shorts = stem_course.full_note_shorts(pack, {"shorts": []})
        with mock.patch.object(
            stem_course,
            "notes_source_subtopic_coverage",
            return_value={
                "source_subtopic_status": "failed",
                "source_subtopics": [{"source_term": "Angular Momentum", "status": "missing"}],
            },
        ):
            report = stem_course.notes_coverage_ledger(shorts, pack)

        reason = next(item for item in report["failure_reasons"] if "subtopics" in item)
        self.assertIn("Angular Momentum", reason)
        self.assertNotIn("algorithm", reason.lower())

    def test_unsupported_authoritative_units_are_preserved_and_fail_closed(self) -> None:
        topics = [f"Unregistered Spectroscopy Unit {index}" for index in range(1, 9)]
        pack = outline_pack("General Chemistry", "https://example.test/chemistry", topics)

        shorts = stem_course.full_note_shorts(pack, {"shorts": []})

        self.assertEqual([short["concept"] for short in shorts], topics)
        self.assertTrue(all(short["notes_resolution_status"] == "failed" for short in shorts))
        self.assertTrue(all("Unsupported authoritative notes topic" in short["notes_resolution_error"] for short in shorts))

    def test_authoritative_source_subtopic_coverage_is_domain_neutral_and_visible(self) -> None:
        topics = ["Newton's Laws", "Energy Conservation", "Angular Momentum"]
        pack = outline_pack(
            "MIT Classical Mechanics",
            "https://example.test/mechanics",
            topics,
        )
        shorts = [
            {
                "index": index,
                "concept": topic,
                "note_depth": {
                    "definition": f"{topic} defines the physical system and its measurable variables.",
                    "development": f"A substantive derivation applies {topic} to the stated source context.",
                    "results": [],
                    "examples": [],
                    "extensions": [],
                },
            }
            for index, topic in enumerate(topics, start=1)
        ]
        report = stem_course.notes_source_subtopic_coverage(pack, shorts)
        self.assertEqual(report["source_subtopic_status"], "ok")
        self.assertEqual(report["required_source_subtopic_count"], len(topics))

        shorts[-1]["concept"] = "Unrelated padding page"
        shorts[-1]["note_depth"]["definition"] = "Generic prose with no source-specific topic."
        shorts[-1]["note_depth"]["development"] = "More generic prose cannot replace source coverage."
        missing = stem_course.notes_source_subtopic_coverage(pack, shorts)
        self.assertEqual(missing["source_subtopic_status"], "failed")
        self.assertEqual(missing["missing_source_subtopic_count"], 1)

    def test_aggregate_failure_reasons_are_never_blank(self) -> None:
        pack = mit_18_703_source_pack()
        shorts = stem_course.full_note_shorts(pack, {"shorts": []})
        repetition_failure = {
            "status": "failed",
            "repeated_sentence_ratio": 0.75,
            "dominant_ngram_count": 12,
        }

        with mock.patch.object(stem_course, "notes_repetition_audit", return_value=repetition_failure):
            report = stem_course.notes_coverage_ledger(shorts, pack)

        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["failure_reasons"])
        self.assertIn("Course-wide prose repetition", report["failure_reasons"][0])

    def test_cmd_notes_prints_aggregate_reason_when_topic_rows_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-reason-") as temp:
            run = Path(temp)
            stem_course.write_json(run / "source_pack.json", {"title": "Course", "materials": []})
            stem_course.write_json(run / "short_plan.json", {"course_title": "Course", "shorts": []})
            report = {
                "status": "failed",
                "topics": [{"concept": "Topic", "status": "ok", "missing": []}],
                "failure_reasons": ["Course-wide repetition exceeded the contract."],
            }
            with (
                mock.patch.object(stem_course, "full_note_shorts", return_value=[]),
                mock.patch.object(stem_course, "notes_coverage_ledger", return_value=report),
                self.assertRaisesRegex(SystemExit, "Course-wide repetition exceeded"),
            ):
                stem_course.cmd_notes(argparse.Namespace(run=str(run), compile=False, pdf_engine="none"))

    def test_visible_word_count_ignores_machine_metadata(self) -> None:
        payload = {
            "definition": "A visible definition has exactly these learner facing words.",
            "development": "A visible derivation checks the stated result with a concrete case.",
            "results": [{"id": "hidden-machine-id", "name": "Visible result", "statement": "The visible claim follows."}],
            "properties": ["A visible property remains."],
            "numeric_evidence": {"massive_hidden_key": "metadata words must not count " * 100},
            "figure_binding_contract": {"status": "ok", "facts": ["hidden metadata"]},
        }
        baseline = stem_course.note_depth_word_count(payload)
        payload["runtime_contract"] = {"more_hidden_metadata": "ignored " * 1000}

        self.assertEqual(stem_course.note_depth_word_count(payload), baseline)
        self.assertLess(baseline, 40)


class NotesLatexLayoutTests(unittest.TestCase):
    def test_algorithm_notes_exclude_generator_and_provenance_language(self) -> None:
        topics = [
            "Data Structures",
            "Dynamic Array",
            "Sorting",
            "Hashing",
            "Binary Search Trees",
            "AVL Trees and Rotations",
            "Binary Heaps",
            "Breadth-First Search",
            "Complexity",
            "Dynamic Programming State Design",
        ]
        pack = {
            "title": "Algorithms",
            "materials": [{
                "kind": "pdf",
                "title": "Algorithms notes",
                "text": ". ".join(topics) * 12,
            }],
        }
        visible_tex: list[str] = []
        for index, topic in enumerate(topics, start=1):
            short = stem_course.concept_to_short(
                stem_course.source_term_concept(topic, "algorithms"), index
            )
            short["note_depth"] = stem_course.source_derived_note_depth(short, pack)
            visible_tex.append(stem_course.latex_comprehensive_topic(short))
        text = "\n".join(visible_tex).lower()
        banned = (
            r"\b(?:figure|diagram)\s+(?:is|was)\s+(?:generated|produced|rendered)\b",
            r"\bgenerated\s+from\b",
            r"\bverified(?:\s+[a-z]+){0,4}\s+(?:state|trace|example|transition)s?\b",
            r"\bvisual\s+invariant\b",
            r"\bdisplayed\s+state\b",
            r"\brecomput\w*\s+(?:this|the)\s+section",
            r"\bsection(?:'s|s)\s+trace\b",
            r"\brenderer\b",
            r"\bprovenance\b",
            r"\bsource[- ]grounded\b",
        )
        for pattern in banned:
            self.assertIsNone(re.search(pattern, text), pattern)

    def test_publish_gate_requires_50_pages_for_comprehensive_courses(self) -> None:
        latex_report = {
            "status": "ok",
            "engine": "tectonic",
            "pdf": "notes.pdf",
            "warning_counts": {
                "latex_warnings": 0,
                "engine_warnings": 0,
                "missing_characters": 0,
                "overfull_hboxes": 0,
                "underfull_hboxes": 0,
            },
        }
        plan = {"shorts": [{"index": index} for index in range(1, 9)]}
        with tempfile.TemporaryDirectory(prefix="notes-page-gate-") as temp:
            run = Path(temp)
            with (
                mock.patch.object(stem_course, "run_latex_engine", return_value=latex_report),
                mock.patch.object(
                    stem_course,
                    "run_notes_visual_integrity_audit",
                    return_value={"status": "ok", "rendered_page_count": 49, "page_audits": []},
                ),
                mock.patch.object(
                    stem_course,
                    "run_notes_pdf_layout_audit",
                    return_value={"status": "ok", "page_count": 49, "findings": []},
                ),
            ):
                report = stem_course.compile_notes_pdf(run, plan, "latex")

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["page_count_status"], "failed")
        self.assertEqual(report["minimum_page_count"], 50)
        self.assertIn("at least 50 substantive pages", report["message"])

    def test_course_tex_keeps_bounded_figures_with_their_discussion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-flow-") as temp:
            run = Path(temp)
            stem_course.write_json(run / "source_pack.json", mit_18_703_source_pack())
            stem_course.write_json(run / "short_plan.json", {"course_title": "Modern Algebra", "shorts": []})

            stem_course.cmd_notes(argparse.Namespace(run=str(run), compile=False, pdf_engine="none"))
            tex = (run / "notes.tex").read_text(encoding="utf-8")

        self.assertEqual(tex.count(r"\clearpage"), 2)
        self.assertIn(r"\tableofcontents", tex)
        self.assertNotIn(r"\resizebox", tex)
        self.assertIn(r"max width=0.98\linewidth,max totalheight=0.32\textheight", tex)
        self.assertNotIn(r"\Needspace", tex)
        self.assertIn(r"\begin{minipage}{0.98\linewidth}", tex)
        discussion = "emphasizes closure and invertible motion"
        discussion_position = tex.index(discussion)
        minipage_position = tex.rindex(r"\begin{minipage}{0.98\linewidth}", 0, discussion_position)
        minipage_end = tex.index(r"\end{minipage}", minipage_position)
        self.assertLess(minipage_position, discussion_position)
        self.assertLess(discussion_position, minipage_end)
        self.assertIn(r"\captionof{figure}", tex[minipage_position:minipage_end])
        self.assertEqual(tex.count(r"\captionof{figure}"), 24)
        self.assertIn(r"\begin{flushright}", tex)
        self.assertIn("Emmy Noether", tex)
        self.assertNotIn("Source list", tex)
        self.assertNotIn("Letter to Helmut Hasse", tex)

    def test_cs_figures_use_separate_heading_and_explanation_lanes(self) -> None:
        avl = stem_course.concept_to_short(
            stem_course.source_term_concept("AVL Trees and Rotations", "algorithms"), 1
        )
        heap = stem_course.concept_to_short(
            stem_course.source_term_concept("Binary Heaps", "algorithms"), 2
        )
        shortest = stem_course.concept_to_short(
            stem_course.source_term_concept("Weighted Shortest Paths", "algorithms"), 3
        )

        avl_figure = stem_course.latex_topic_figure(avl)
        heap_figure = stem_course.latex_topic_figure(heap)
        shortest_figure = stem_course.latex_topic_figure(shortest)

        self.assertIn(r"\node at (4.65,-0.25) {in-order sequence:", avl_figure)
        self.assertIn(r"\node at (1.55,3.55) {before rotation};", avl_figure)
        self.assertIn(r"\node at (3,3.75) {insert", heap_figure)
        self.assertIn(r"\node at (4.85,0.35) {same heap in level-order array};", heap_figure)
        self.assertIn("worked graph", shortest_figure)
        self.assertNotIn("verified", shortest_figure.lower())
        self.assertIn(r"(gn0) at (0.650,1.700)", shortest_figure)
        self.assertIn(r"(gn3) at (5.200,1.700)", shortest_figure)
        self.assertIn("sloped,above", shortest_figure)
        self.assertIn("sloped,below", shortest_figure)

    def test_group_figures_put_explanatory_labels_outside_objects_and_edges(self) -> None:
        def figure(visual: str, index: int) -> str:
            return stem_course.latex_topic_figure({
                "index": index,
                "concept": f"Topic {index}",
                "visual_type": visual,
            })

        kernel = figure("group_kernel_image", 1)
        euclidean = figure("algebra_euclidean", 2)
        polynomial = figure("algebra_polynomial_division", 3)

        self.assertIn(r"\node[anchor=south] at (0.9,3.25) {$\ker\varphi$};", kernel)
        self.assertIn(r"\node[anchor=south west] at (-0.05,3.18) {$G$};", kernel)
        self.assertNotIn(r"(gbox) at (0.9,1.5) {$G$}", kernel)
        self.assertIn(r"\node at (1.85,2.55) {$a=bq_0+r_0$};", euclidean)
        self.assertNotIn(r"--node[above]{$a=bq_0+r_0$}", euclidean)
        self.assertIn(r"\node at (1.55,3.70) {1. select the leading term};", polynomial)
        self.assertIn(r"\node at (3.85,3.15) {2. divide leading terms};", polynomial)
        self.assertIn(r"\node[anchor=west] at (5.75,1.55) {3. subtract};", polynomial)
        self.assertIn(r"\node at (3.0,0.05) {$\deg r_{i+1}<\deg r_i$};", polynomial)


if __name__ == "__main__":
    unittest.main()

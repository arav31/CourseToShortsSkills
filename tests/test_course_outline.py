from __future__ import annotations

import unittest

from tools import stem_course


class CourseOutlinePlanningTests(unittest.TestCase):
    def algorithms_pack(self) -> dict[str, object]:
        calendar = """
        Lecture 1: Introduction
        Lecture 2: Data Structures
        Lecture 3: Sorting
        Lecture 4: Hashing
        Lecture 5: Linear Sorting
        Lecture 6: Binary Trees, Part 1
        Lecture 7: Binary Trees, Part 2: AVL
        Lecture 8: Binary Heaps
        Lecture 9: Breadth-First Search
        Lecture 10: Depth-First Search
        Lecture 11: Weighted Shortest Paths
        Lecture 12: Bellman-Ford
        Lecture 13: Dijkstra's Algorithm
        Lecture 14: Johnson's Algorithm
        Lecture 15: Dynamic Programming, Part 1: Recursive Algorithms
        Lecture 16: Dynamic Programming, Part 2: Subproblems
        Lecture 17: Dynamic Programming, Part 3: APSP, Parens, Piano
        Lecture 18: Dynamic Programming, Part 4: Pseudopolynomials
        Lecture 19: Complexity
        Lecture 20: Course Review
        Lecture 21: Algorithms-Next Steps
        """
        return {
            "title": "Introduction to Algorithms",
            "materials": [
                {"kind": "page", "title": "Calendar", "text": calendar},
                {"kind": "pdf", "title": "Lecture notes", "text": calendar * 2},
            ],
        }

    def test_numbered_calendar_is_an_ordered_authoritative_topic_source(self) -> None:
        topics = stem_course.source_outline_topics(self.algorithms_pack())

        self.assertEqual(topics[0], "Data Structures")
        self.assertIn("Johnson's Algorithm", topics)
        self.assertIn("Memoization and Recursive Dynamic Programming", topics)
        self.assertIn("Dynamic Programming State Design", topics)
        self.assertIn("Dynamic Programming Applications", topics)
        self.assertIn("Pseudopolynomial Dynamic Programming", topics)
        self.assertNotIn("Introduction", topics)
        self.assertNotIn("Course Review", topics)
        self.assertEqual(len(topics), len(set(topic.lower() for topic in topics)))

    def test_course_plan_exceeds_sample_library_without_duplicate_bfs(self) -> None:
        concepts = stem_course.choose_concepts(self.algorithms_pack(), 40)
        names = [concept.name for concept in concepts]

        self.assertGreaterEqual(len(names), 18)
        self.assertEqual(sum("breadth-first search" == name.lower() for name in names), 1)
        self.assertIn("Depth-First Search", names)
        self.assertIn("Johnson's Algorithm", names)
        self.assertTrue(all(concept.visual_type in stem_course.CS_VISUAL_KINDS for concept in concepts))

    def test_outline_extraction_is_not_tied_to_mit_or_algorithms(self) -> None:
        pack = {
            "title": "Intermediate Microeconomics",
            "materials": [{
                "kind": "page",
                "title": "Schedule",
                "text": "Unit 1: Consumer Choice\nUnit 2: Slutsky Equation\nUnit 3: Market Demand",
            }],
        }

        self.assertEqual(
            stem_course.source_outline_topics(pack),
            ["Consumer Choice", "Slutsky Equation", "Market Demand"],
        )

    def test_notes_coverage_fails_closed_when_calendar_units_are_missing(self) -> None:
        pack = self.algorithms_pack()
        concepts = stem_course.choose_concepts(pack, 40)
        shorts = [stem_course.concept_to_short(concept, index) for index, concept in enumerate(concepts, start=1)]

        complete = stem_course.notes_outline_coverage(pack, shorts)
        truncated = stem_course.notes_outline_coverage(pack, shorts[:4])

        self.assertEqual(complete["outline_coverage_status"], "ok")
        self.assertEqual(complete["missing_outline_topic_count"], 0)
        self.assertEqual(truncated["outline_coverage_status"], "failed")
        self.assertGreater(truncated["missing_outline_topic_count"], 10)

    def test_authoritative_outline_creates_each_notes_chapter_once(self) -> None:
        pack = self.algorithms_pack()
        concepts = stem_course.choose_concepts(pack, 40)
        plan = {
            "shorts": [
                stem_course.concept_to_short(concept, index)
                for index, concept in enumerate(concepts, start=1)
            ],
        }

        notes_shorts = stem_course.full_note_shorts(pack, plan)
        expected = [topic.lower() for topic in stem_course.source_outline_topics(pack)]
        actual = [str(short["concept"]).lower() for short in notes_shorts]

        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), len(set(actual)))


if __name__ == "__main__":
    unittest.main()

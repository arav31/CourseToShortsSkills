import json
import unittest
from unittest import mock

from tools import stem_course


def mit_pack() -> dict[str, object]:
    return {
        "title": "MIT 18.703 Modern Algebra",
        "source_url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/",
        "materials": [],
    }


class Mit18703TopicFramingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shorts = stem_course.mit_18_703_note_shorts(mit_pack())

    def test_every_calendar_title_uses_its_exact_framing_contract(self) -> None:
        self.assertEqual(len(self.shorts), 24)
        self.assertEqual(
            tuple(short["concept"] for short in self.shorts),
            stem_course.MIT_18_703_CALENDAR_ORDER,
        )
        for short in self.shorts:
            title = str(short["concept"])
            framing = stem_course.MIT_18_703_TOPIC_FRAMING[title]
            payload = short["note_depth"]
            worked = short["worked_example"]
            with self.subTest(title=title):
                self.assertEqual(short["hook"], framing["hook"])
                self.assertEqual(short["formula"], framing["formula"])
                self.assertEqual(short["prerequisites"], list(framing["prerequisites"]))
                self.assertEqual(short["misconception"], framing["misconception"])
                self.assertEqual(short["question_prompt"]["question"], framing["question"])
                self.assertEqual(short["question_prompt"]["answer"], framing["answer"])
                self.assertTrue(any(
                    all(example.get(field) == worked[field] for field in ("setup", "calculation", "takeaway"))
                    for example in payload["examples"]
                ))
                self.assertGreaterEqual(len(payload["examples"]), 2)
                self.assertEqual(payload["topic_framing_basis"], "exact-calendar-title")

    def test_legacy_base_mutation_cannot_change_review_semantics(self) -> None:
        altered_sequence = tuple(
            {**spec, "base": "groups and operations"} if spec["title"] == "Review" else dict(spec)
            for spec in stem_course.MIT_18_703_NOTE_SEQUENCE
        )
        with mock.patch.object(stem_course, "MIT_18_703_NOTE_SEQUENCE", altered_sequence):
            review = stem_course.mit_18_703_note_shorts(mit_pack())[-1]

        self.assertIn("modern-algebra review", review["hook"])
        self.assertIn("mixed modern-algebra proof", review["question_prompt"]["question"])
        self.assertIn("evaluation", review["worked_example"]["setup"].lower())
        serialized = json.dumps(review)
        self.assertNotIn("determinant as a map", serialized)
        self.assertNotIn("rotations of a square", serialized.lower())

    def test_known_base_leaks_are_absent_from_their_rendered_sections(self) -> None:
        rendered = {
            str(short["concept"]): stem_course.latex_comprehensive_topic(short)
            for short in self.shorts
        }
        checks = {
            "Cosets": ("Subgroup size must divide group size", "When do two left cosets"),
            "Alternating Groups": ("symmetry of a triangle", "Why is A n a normal subgroup"),
            "Basic Properties of Rings": ("even integers not a ring", "a times zero equals zero"),
            "Special Domains": ("Why does Euclidean imply", "factorization existence"),
            "A Quick Primality Test": ("finite field sizes", "polynomial congruence"),
            "Group Actions and Automorphisms": ("What is an inner automorphism", "orbit-stabilizer"),
            "Review": ("determinant as a map", "mixed modern-algebra proof"),
        }
        for title, (leaked, expected) in checks.items():
            with self.subTest(title=title):
                self.assertNotIn(leaked, rendered[title])
                self.assertIn(expected, rendered[title])

    def test_missing_calendar_framing_fails_closed(self) -> None:
        incomplete = dict(stem_course.MIT_18_703_TOPIC_FRAMING)
        incomplete.pop("Review")
        with mock.patch.object(stem_course, "MIT_18_703_TOPIC_FRAMING", incomplete):
            with self.assertRaisesRegex(RuntimeError, "topic framing mismatch"):
                stem_course.mit_18_703_note_shorts(mit_pack())


if __name__ == "__main__":
    unittest.main()

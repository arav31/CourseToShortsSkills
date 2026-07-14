import unittest

from tools.stem_course import complete_visible_prose_stage


class VisibleProseCompletionTests(unittest.TestCase):
    def test_accepts_complete_because_sentence_with_main_clause(self):
        self.assertTrue(
            complete_visible_prose_stage(
                "Because Z / (5) is a field, (5) is maximal and therefore prime."
            )
        )

    def test_rejects_orphan_because_clause(self):
        self.assertFalse(
            complete_visible_prose_stage("Because Z / (5) is a field.")
        )


if __name__ == "__main__":
    unittest.main()

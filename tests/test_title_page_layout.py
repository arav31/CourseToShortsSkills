from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course


class NotesTitlePageLayoutTests(unittest.TestCase):
    def test_pioneer_quote_is_bounded_middle_right_and_disables_hyphenation(self) -> None:
        pack = {"title": "Classical Mechanics", "materials": []}
        plan = {"course_title": "Classical Mechanics", "shorts": []}
        quote = stem_course.latex_opening_quote_block(pack, plan)

        self.assertIn("standing on the shoulders", quote)
        self.assertIn("Isaac Newton", quote)
        self.assertIn(r"\hyphenpenalty=10000", quote)
        self.assertIn(r"\exhyphenpenalty=10000", quote)
        self.assertNotIn("Hooke", quote)
        self.assertNotIn("1675", quote)
        self.assertNotIn("shoul-", quote)

    def test_generated_title_page_uses_responsive_quote_width_without_source_clutter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-title-layout-") as temporary:
            run = Path(temporary)
            pack = {"title": "Classical Mechanics", "materials": []}
            plan = {"course_title": "Classical Mechanics", "shorts": []}
            stem_course.write_json(run / "source_pack.json", pack)
            stem_course.write_json(run / "short_plan.json", plan)

            with (
                mock.patch.object(stem_course, "full_note_shorts", return_value=[]),
                mock.patch.object(stem_course, "notes_coverage_ledger", return_value={
                    "status": "ok",
                    "failure_reasons": [],
                }),
            ):
                stem_course.cmd_notes(
                    argparse.Namespace(run=str(run), compile=False, pdf_engine="none")
                )

            tex = (run / "notes.tex").read_text(encoding="utf-8")

        self.assertIn(r"\newlength{\NotesQuoteWidth}", tex)
        self.assertIn(r"\setlength{\NotesQuoteWidth}{0.48\textwidth}", tex)
        self.assertIn(r"\ifdim\NotesQuoteWidth>25em", tex)
        self.assertIn(r"\ifdim\NotesQuoteWidth<18em", tex)
        self.assertIn(r"\begin{flushright}", tex)
        self.assertIn(r"\begin{minipage}{\NotesQuoteWidth}", tex)
        self.assertLess(tex.index(r"\vspace{0.7in}"), tex.index(r"\begin{flushright}"))
        self.assertNotIn("Source list", tex)
        self.assertNotIn("Letter to Robert Hooke", tex)


if __name__ == "__main__":
    unittest.main()

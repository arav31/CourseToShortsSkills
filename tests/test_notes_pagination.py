from __future__ import annotations

import unittest

from tools.notes_pagination import (
    TERMINAL_PAGE_BREAK,
    balance_terminal_topic,
    terminal_page_break_preamble,
)


def prose(words: int) -> str:
    return " ".join(f"word{index}" for index in range(words))


class NotesPaginationTests(unittest.TestCase):
    def test_balances_example_and_checkpoint_tail_at_semantic_boundary(self) -> None:
        topic = rf"""
\section{{Review}}
\begin{{proofblock}}[Synthesis]
{prose(430)}
\end{{proofblock}}
\begin{{example}}[Worked case]
{prose(125)}
\end{{example}}
\begin{{counterexample}}[Boundary case]
{prose(95)}
\end{{counterexample}}
\subsection{{Checkpoint}}
\begin{{description}}
\item[Problem.] {prose(18)}
\item[Solution.] {prose(24)}
\end{{description}}
"""

        balanced = balance_terminal_topic(topic)

        self.assertEqual(balanced.count(TERMINAL_PAGE_BREAK), 1)
        self.assertIn(TERMINAL_PAGE_BREAK + "\n\\begin{example}", balanced)

    def test_can_split_algorithm_at_description_boundary(self) -> None:
        topic = rf"""
\section{{Complexity}}
{prose(520)}
\begin{{algorithm}}[Procedure]
\begin{{enumerate}}
\item {prose(45)}
\item {prose(45)}
\end{{enumerate}}
\begin{{description}}
\item[Inputs.] {prose(55)}
\item[Invariant.] {prose(70)}
\end{{description}}
\end{{algorithm}}
\begin{{example}}[Worked verification]
{prose(75)}
\end{{example}}
\begin{{counterexample}}[Boundary test]
{prose(60)}
\end{{counterexample}}
\subsection{{Checkpoint}}
\begin{{description}}{prose(35)}\end{{description}}
"""

        balanced = balance_terminal_topic(topic)

        self.assertEqual(balanced.count(TERMINAL_PAGE_BREAK), 1)
        self.assertIn(TERMINAL_PAGE_BREAK + "\n\\begin{description}", balanced)

    def test_leaves_short_terminal_topic_unchanged(self) -> None:
        topic = rf"""
\section{{Short topic}}
{prose(80)}
\subsection{{Checkpoint}}
\begin{{description}}{prose(30)}\end{{description}}
"""

        self.assertEqual(balance_terminal_topic(topic), topic)

    def test_ignores_tikz_source_volume_when_estimating_tail(self) -> None:
        diagram = "\\draw (0,0)--(1,1);\n" * 400
        topic = rf"""
\section{{Diagram topic}}
{prose(80)}
\begin{{tikzpicture}}
{diagram}
\end{{tikzpicture}}
\subsection{{Checkpoint}}
\begin{{description}}{prose(20)}\end{{description}}
"""

        self.assertEqual(balance_terminal_topic(topic), topic)

    def test_is_idempotent_and_defines_real_latex_command(self) -> None:
        topic = rf"""
\section{{Review}}
{prose(430)}
\begin{{example}} {prose(125)} \end{{example}}
\begin{{counterexample}} {prose(95)} \end{{counterexample}}
\subsection{{Checkpoint}}
\begin{{description}} {prose(42)} \end{{description}}
"""
        once = balance_terminal_topic(topic)

        self.assertIn(TERMINAL_PAGE_BREAK, once)
        self.assertEqual(balance_terminal_topic(once), once)
        self.assertEqual(terminal_page_break_preamble(), r"\newcommand{\NotesTerminalPageBreak}{\par\newpage}")


if __name__ == "__main__":
    unittest.main()

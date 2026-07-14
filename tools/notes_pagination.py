"""Topic-agnostic pagination helpers for generated LaTeX notes."""

from __future__ import annotations

import math
import re


TERMINAL_PAGE_BREAK = "\\NotesTerminalPageBreak"

_SEMANTIC_BOUNDARY_RE = re.compile(
    r"(?m)^(?:"
    r"\\subsection(?:\[[^\]]*\])?\{"
    r"|\\begin\{(?:algorithm|description|example|counterexample|proofblock|proofsketch)\}"
    r")"
)
_TIKZ_RE = re.compile(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", re.S)
_COMMENT_RE = re.compile(r"(?m)(?<!\\)%.*$")
_LATEX_COMMAND_RE = re.compile(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?")
_STRUCTURAL_RE = re.compile(r"\\(?:begin|end)\{[^}]+\}|\\(?:label|ref)\{[^}]+\}")


def _estimated_lines(tex: str) -> int:
    """Estimate prose lines while ignoring diagram implementation detail."""
    prose = _TIKZ_RE.sub("", _COMMENT_RE.sub("", tex))
    structural_lines = len(
        re.findall(
            r"\\(?:subsection|item|paragraph)\b|\\begin\{(?:algorithm|example|counterexample|description)\}",
            prose,
        )
    )
    prose = _STRUCTURAL_RE.sub(" ", prose)
    prose = _LATEX_COMMAND_RE.sub(" ", prose)
    prose = re.sub(r"[{}$&_^~]", " ", prose)
    prose = re.sub(r"\s+", " ", prose).strip()
    return math.ceil(len(prose) / 86) + structural_lines


def balance_terminal_topic(
    topic_tex: str,
    *,
    target_tail_lines: int = 29,
    minimum_tail_lines: int = 23,
    maximum_tail_lines: int = 38,
    minimum_prefix_lines: int = 22,
) -> str:
    """Start the terminal page at a semantic boundary when its natural tail is likely sparse.

    The selected tail is large enough to make the final page substantive while the
    prefix remains large enough to avoid merely moving the sparse-page defect one
    page earlier. LaTeX remains responsible for ordinary pagination elsewhere.
    """
    if TERMINAL_PAGE_BREAK in topic_tex:
        return topic_tex

    candidates: list[tuple[int, int, int]] = []
    for match in _SEMANTIC_BOUNDARY_RE.finditer(topic_tex):
        prefix_lines = _estimated_lines(topic_tex[: match.start()])
        tail_lines = _estimated_lines(topic_tex[match.start() :])
        if prefix_lines < minimum_prefix_lines:
            continue
        if not minimum_tail_lines <= tail_lines <= maximum_tail_lines:
            continue
        candidates.append((abs(tail_lines - target_tail_lines), -prefix_lines, match.start()))

    if not candidates:
        return topic_tex

    _, _, offset = min(candidates)
    return topic_tex[:offset] + TERMINAL_PAGE_BREAK + "\n" + topic_tex[offset:]


def terminal_page_break_preamble() -> str:
    """Return the explicit semantic page-break command used by the balancer."""
    return r"\newcommand{\NotesTerminalPageBreak}{\par\newpage}"

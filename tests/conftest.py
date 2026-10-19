import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
for script_dir in sorted(SKILLS.glob("*/scripts")):
    sys.path.insert(0, str(script_dir))

HAS_MANIM = importlib.util.find_spec("manim") is not None
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
HAS_TEX = any(shutil.which(n) for n in ("tectonic", "pdflatex"))
HAS_PYMUPDF = importlib.util.find_spec("pymupdf") is not None


def write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def plan_run(tmp_path: Path) -> Path:
    """A minimal, valid run directory (sources + outline + plan)."""
    run = tmp_path / "run"
    (run / "sources").mkdir(parents=True)
    (run / "sources" / "001-lecture-1.txt").write_text("# title: Lecture 1\n\nColumns and combinations.\n")
    (run / "sources" / "002-lecture-2.txt").write_text("# title: Lecture 2\n\nElimination.\n")
    write_json(run / "outline.json", {
        "course": {"title": "Linear Algebra"},
        "units": [
            {"id": "u01", "title": "Geometry of linear equations",
             "summary": "Row and column pictures of Ax = b; a solution combines the columns to reach b.",
             "sources": ["sources/001-lecture-1.txt"]},
            {"id": "u02", "title": "Elimination",
             "summary": "Gaussian elimination turns A into an upper triangular U by subtracting multiples of rows.",
             "sources": ["sources/002-lecture-2.txt"]},
        ],
    })
    write_json(run / "short_plan.json", {
        "course_title": "Linear Algebra",
        "series": {"title": "Linear Algebra in pictures"},
        "shorts": [short("s01", "ax-mixes-columns", ["u01"], [], "A has columns (2, 1) and (1, 3); x = (4, 2).",
                         ["4 a1 = (8, 4) and 2 a2 = (2, 6)", "(8, 4) + (2, 6) = (10, 10)"], "Ax = (10, 10)"),
                   short("s02", "elimination-pivots", ["u02"], ["s01"], "Solve x + 2y = 5 and 3x + 4y = 6.",
                         ["Subtract 3 times row 1 from row 2: -2y = -9", "Back-substitute: y = 4.5, x = -4"],
                         "x = -4, y = 4.5")],
    })
    return run


def short(sid, slug, units, prereq, setup, steps, result):
    return {
        "id": sid, "slug": slug, "title": slug.replace("-", " ").title(), "units": units, "prerequisites": prereq,
        "hook": "What does this operation really do to the picture?",
        "claim": "The answer is a combination of simple moves you can see.",
        "worked_example": {"setup": setup, "steps": steps, "result": result},
        "visual": "A number plane with two arrows that stretch and chain tip to tail to reach the answer.",
        "misconception": "It is not a black-box rule; each step has a geometric meaning.",
        "practice": {"question": "What happens if the weights are swapped?", "answer": "A different point."},
    }

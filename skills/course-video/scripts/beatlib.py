"""Shared, dependency-free helpers for reading a scene's BEATS list.

A scene file declares its narration as a module-level literal:

    BEATS = [
        ("hook", "What does multiplying a matrix by a vector actually do?"),
        ("columns", "Read A as two arrows: its columns."),
    ]

voice.py, render.py and shortkit.py all read the same list, so narration,
animation timing and captions can never drift apart.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

WORDS_PER_SECOND = 2.5  # edge-tts reads plain prose at ~2.9 w/s, but numbers and symbols are slower
MIN_BEAT_SECONDS = 1.5
BEAT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


class BeatError(ValueError):
    pass


def normalize_beats(raw: object, origin: str = "BEATS") -> list[dict[str, str]]:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise BeatError(f"{origin} must be a non-empty list of (id, narration) pairs")
    beats: list[dict[str, str]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if isinstance(item, dict):
            beat_id, text = item.get("id"), item.get("say") or item.get("text")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            beat_id, text = item
        else:
            raise BeatError(f"{origin}[{i}] must be (id, narration) or {{'id':..., 'say':...}}")
        if not isinstance(beat_id, str) or not BEAT_ID_RE.match(beat_id):
            raise BeatError(f"{origin}[{i}] id {beat_id!r} must be lowercase letters, digits, '-' or '_'")
        if beat_id in seen:
            raise BeatError(f"{origin} has duplicate beat id {beat_id!r}")
        if not isinstance(text, str) or not text.strip():
            raise BeatError(f"{origin}[{i}] ({beat_id}) has empty narration")
        seen.add(beat_id)
        beats.append({"id": beat_id, "text": " ".join(text.split())})
    return beats


def read_beats(scene_path: str | Path) -> list[dict[str, str]]:
    """Parse the module-level BEATS literal without importing the scene."""
    path = Path(scene_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        if "BEATS" in targets and value is not None:
            try:
                raw = ast.literal_eval(value)
            except ValueError as exc:
                raise BeatError(f"{path.name}: BEATS must be a plain literal list (no f-strings or calls)") from exc
            return normalize_beats(raw, f"{path.name}: BEATS")
    raise BeatError(f"{path.name}: no module-level BEATS list found")


def find_scene_class(scene_path: str | Path) -> str:
    """Return the first class in the file that subclasses ShortScene."""
    path = Path(scene_path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                if name == "ShortScene":
                    return node.name
    raise BeatError(f"{path.name}: no class subclassing ShortScene found")


def estimate_seconds(text: str) -> float:
    words = len(re.findall(r"[\w'’-]+", text))
    return max(MIN_BEAT_SECONDS, words / WORDS_PER_SECOND + 0.5)


def split_word_timings(words: list | None) -> list | None:
    """Split TTS boundaries that cover several words ("So park") into one entry per word.

    edge-tts occasionally reports two words as one boundary; cue("park") and caption alignment
    need single words. The span is shared out in proportion to each word's length.
    """
    if not words:
        return words
    out = []
    for start, end, text in words:
        parts = str(text).split()
        if len(parts) <= 1:
            out.append([start, end, text])
            continue
        total = sum(len(p) for p in parts)
        t = float(start)
        for part in parts:
            step = (float(end) - float(start)) * len(part) / total
            out.append([round(t, 3), round(t + step, 3), part])
            t += step
    return out

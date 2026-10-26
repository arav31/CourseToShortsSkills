import json
import textwrap

import pytest

import beatlib
from conftest import HAS_FFMPEG, HAS_MANIM, HAS_TEX

SCENE = textwrap.dedent('''
    from shortkit import *

    BEATS = [
        ("hook", "Two labels sit on top of each other here on purpose."),
        ("fix", "Now the second label moves away and nothing overlaps."),
    ]

    class Probe(ShortScene):
        def construct(self):
            with self.beat("hook"):
                self.title("Layout probe")
                a = text("first label")
                b = text("second label").move_to(a)
                self.add(a, b)
            with self.beat("fix"):
                self.play(b.animate.shift(DOWN * 2), run_time=0.5)
                eq = tex(r"\\cB{x}^2 + 1")
                eq.next_to(b, DOWN)
                self.play(Write(eq), run_time=0.5)
''')


def test_read_beats_and_class(tmp_path):
    scene = tmp_path / "scene.py"
    scene.write_text(SCENE)
    beats = beatlib.read_beats(scene)
    assert [b["id"] for b in beats] == ["hook", "fix"]
    assert beatlib.find_scene_class(scene) == "Probe"


@pytest.mark.parametrize("bad, message", [
    ("BEATS = []", "non-empty"),
    ("BEATS = [('Hook', 'x')]", "lowercase"),
    ("BEATS = [('a', 'x'), ('a', 'y')]", "duplicate"),
    ("BEATS = [('a', '')]", "empty narration"),
    ("BEATS = [('a', f'{1}')]", "plain literal"),
])
def test_bad_beats_are_rejected(tmp_path, bad, message):
    scene = tmp_path / "scene.py"
    scene.write_text(bad + "\n")
    with pytest.raises(beatlib.BeatError, match=message):
        beatlib.read_beats(scene)


def test_estimate_seconds_has_floor():
    assert beatlib.estimate_seconds("Hi.") == beatlib.MIN_BEAT_SECONDS
    assert beatlib.estimate_seconds("one two three four five six seven eight nine ten eleven twelve thirteen") > 5


def test_caption_cues_follow_word_timings_and_never_overlap():
    import render

    trace = {"beats": [{"id": "a", "start": 0.0, "end": 4.0}, {"id": "b", "start": 4.0, "end": 7.0}]}
    words = [[0.1, 0.4, "Take"], [0.45, 0.6, "the"], [0.6, 1.0, "matrix"], [1.0, 1.2, "A,"], [1.6, 1.9, "with"],
             [1.9, 2.2, "columns"], [2.2, 2.5, "two"], [2.5, 2.8, "one"], [2.9, 3.1, "and"], [3.1, 3.4, "three"]]
    timing = {"beats": [
        {"id": "a", "text": "Take the matrix A, with columns two one and three.", "words": words, "audio_seconds": 3.5},
        {"id": "b", "text": "Then add them.", "words": None, "audio_seconds": 1.2},
    ]}
    cues = render.caption_cues(trace, timing)
    assert cues[0][0] == pytest.approx(0.1)
    assert all(len(text) <= render.CAPTION_MAX_CHARS + 8 for _, _, text in cues)
    for (a0, a1, _), (b0, _, _) in zip(cues, cues[1:]):
        assert a1 <= b0 + 1e-9, "cues must not overlap"
    assert cues[-1][0] >= 4.0, "the second beat's caption starts with its beat"
    assert " ".join(c[2] for c in cues) == "Take the matrix A, with columns two one and three. Then add them."


@pytest.mark.skipif(not (HAS_MANIM and HAS_FFMPEG and HAS_TEX), reason="needs manim, ffmpeg and a TeX engine")
def test_render_end_to_end_reports_layout_and_writes_outputs(tmp_path):
    import render

    short = tmp_path / "01-probe"
    short.mkdir()
    (short / "scene.py").write_text(SCENE)
    report = render.render(short, quality="preview", engine="none")
    assert (short / "preview.mp4").exists() and (short / "preview.srt").exists()
    assert report["probe"]["width"] == 540 and report["probe"]["height"] == 960
    assert [b["id"] for b in report["beats"]] == ["hook", "fix"]
    overlaps = [i for i in report["issues"] if i["kind"] == "text-overlap"]
    assert overlaps and overlaps[0]["beat"] == "hook", report["issues"]
    assert not [i for i in overlaps if i["beat"] == "fix"]
    # two small labels in the middle of the stage: the picture is far too small for a 9:16 frame
    assert all(0 < b["stage_fill"] < 0.65 for b in report["beats"])
    assert [i for i in report["issues"] if i["kind"] == "small-diagram"]
    assert report["contact_sheets"] and (short / report["contact_sheets"][0]).exists()
    saved = json.loads((short / "render_report.json").read_text())
    assert saved["sha256"] == report["sha256"]


@pytest.mark.skipif(not (HAS_MANIM and HAS_TEX), reason="needs manim and a TeX engine")
def test_tex_rules_become_filled_bars(tmp_path, monkeypatch):
    monkeypatch.setenv("SHORTKIT_CACHE", str(tmp_path / "cache"))
    import importlib

    import shortkit
    importlib.reload(shortkit)
    eq = shortkit.tex(r"\frac{1}{2} + \sqrt{3}")
    bars = [m for m in eq.family_members_with_points()
            if isinstance(m, shortkit.Rectangle) and m.get_fill_opacity() > 0.9 and m.width > 3 * m.height]
    assert len(bars) == 2, "fraction bar and square-root bar must be visible filled rules"


def test_captions_never_join_sentences():
    import render

    tokens = "Feed a matrix every arrow on a circle. However messy the matrix, the result is an ellipse.".split()
    cues = [" ".join(tokens[i] for i in cue) for cue in render._chunk_tokens(tokens)]
    assert all(len(c) <= render.CAPTION_MAX_CHARS for c in cues)
    assert not any("circle. However" in c for c in cues)
    assert " ".join(cues) == " ".join(tokens)


@pytest.mark.skipif(not (HAS_MANIM and HAS_TEX), reason="needs manim and a TeX engine")
def test_copying_text_does_not_explode(tmp_path, monkeypatch):
    """Ownership marks must not ride along in deep copies (save_state/TransformMatchingShapes)."""
    import time

    monkeypatch.setenv("SHORTKIT_CACHE", str(tmp_path / "cache"))
    import shortkit

    eq = shortkit.plate(shortkit.tex(r"A^{\mathsf T}(b - A\hat{x}) = 0 \quad\Longrightarrow\quad A^{\mathsf T}A\hat{x} = A^{\mathsf T}b"))
    start = time.time()
    for _ in range(8):
        eq.save_state()
        eq = eq.copy()
    assert time.time() - start < 5, "copies grew: glyphs must not reference their owner"
    assert shortkit._owner_of(eq) is None  # copies are not registered; the checker treats them as raw text


@pytest.mark.skipif(not HAS_MANIM, reason="needs manim")
def test_live_text_hides_the_value_it_replaces():
    """Manim keeps drawing the children it saw when a play() began; a replaced value must go invisible."""
    import shortkit

    tracker = shortkit.ValueTracker(3)
    counter = shortkit.live_text(lambda: f"{tracker.get_value():.0f}")
    before = counter.submobjects[0]
    tracker.set_value(12)
    counter.update()
    assert counter.submobjects[0] is not before and counter.submobjects[0].text == "12"
    assert before.get_fill_opacity() == 0 and counter.submobjects[0].get_fill_opacity() > 0.9


@pytest.mark.skipif(not HAS_MANIM, reason="needs manim")
def test_transient_tex_failures_are_told_apart_from_latex_errors():
    import shortkit

    assert shortkit._TRANSIENT_TEX.search("error: file `article.cls` not found")
    assert shortkit._TRANSIENT_TEX.search("failed to download bundle file")
    assert not shortkit._TRANSIENT_TEX.search("! Undefined control sequence.")
    assert not shortkit._TRANSIENT_TEX.search("! Missing $ inserted.")


def test_multi_word_tts_boundaries_are_split():
    words = [[0.0, 0.4, "So park"], [0.4, 0.7, "drops"], [0.7, 1.3, "from five"]]
    split = beatlib.split_word_timings(words)
    assert [w for _, _, w in split] == ["So", "park", "drops", "from", "five"]
    assert split[0][0] == 0.0 and split[1][1] == 0.4 and split[1][0] == round(0.4 * 2 / 6, 3)
    assert beatlib.split_word_timings(None) is None


@pytest.mark.skipif(not HAS_MANIM, reason="needs manim")
def test_log_plane_places_powers_of_ten_on_grid_lines():
    import shortkit

    plane = shortkit.log_plane((9, 12), (10, 13))
    assert shortkit.log_point(plane, 1e9, 1e10) == pytest.approx(plane.c2p(0, 0))
    assert shortkit.log_point(plane, 1e11, 1e12) == pytest.approx(plane.c2p(2, 2))
    labels = shortkit.axis_numbers(plane, {0: "1B", 3: "1T"}, {0: "10B"})
    assert len(labels) == 3 and labels[0].get_top()[1] < plane.c2p(0, 0)[1]


@pytest.mark.skipif(not HAS_MANIM, reason="needs manim")
def test_cue_finds_parts_of_hyphenated_words():
    import types

    import shortkit

    fake = types.SimpleNamespace(_words={"b": [[0.5, 0.9, "Kaplan"], [1.0, 1.6, "counted"], [1.7, 2.4, "non-embedding"]]})
    find = shortkit.ShortScene._word_time
    assert find(fake, "b", "non", 0) == 1.7 and find(fake, "b", "embedding", 0) == 1.7
    assert find(fake, "b", "non-embedding", 0) == 1.7 and find(fake, "b", "count", 0) is None

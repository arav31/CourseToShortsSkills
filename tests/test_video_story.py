from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import stem_course
from tools.audit_video_frames import metrics_for


def group_short() -> dict[str, object]:
    return {
        "index": 1,
        "concept": "Groups and operations",
        "hook": "A group is a collection of moves whose combinations never leave the collection.",
        "intuition": "Closure, identity, inverses, and associativity make every legal move reversible and composable.",
        "formula": r"(G,\ast),\qquad a\ast b\in G",
        "plain_formula": "a star b is in G",
        "visual_type": "group_structure",
        "worked_example": {
            "setup": "Use the rotations of a square: 0, 90, 180, and 270 degrees.",
            "calculation": "A 90 degree turn followed by a 270 degree turn gives the 0 degree identity.",
            "takeaway": "Combining any two rotations produces another rotation in the same set.",
        },
    }


class VideoStoryTests(unittest.TestCase):
    def test_supported_topic_opens_on_one_persistent_semantic_canvas(self) -> None:
        short = group_short()
        source = stem_course.manim_scene(short, "GroupsAndOperationsShort", stem_course.build_animation_plan(short))
        compile(source, "<generated-group-story>", "exec")
        construct = source.split("    def construct(self):", 1)[1]

        self.assertNotIn("play_concept_anchor", source)
        self.assertNotIn('["elements", "operation", "structure"]', source)
        self.assertLess(construct.index("self.add(title, hook)"), construct.index("self.play_intro_visual"))
        self.assertIn("self._semantic_canvas", source)
        self.assertIn("self._semantic_story_live", source)
        self.assertIn('if getattr(self, "_semantic_story_live", False):', source)
        self.assertNotIn('section_label("Worked example"', construct)
        self.assertNotIn("retire_concept_objects", construct)

    def test_silent_duration_ignores_redundant_narration_when_visible_steps_are_unchanged(self) -> None:
        concise = group_short()
        detailed = group_short()
        detailed["hook"] = " ".join([str(detailed["hook"])] * 3)
        detailed["intuition"] = " ".join([str(detailed["intuition"])] * 3)
        detailed["worked_example"] = {
            key: " ".join([str(value)] * 3)
            for key, value in dict(detailed["worked_example"]).items()
        }
        extended = group_short()
        extended["hook"] = " ".join([str(extended["hook"])] * 12)
        extended["intuition"] = " ".join([str(extended["intuition"])] * 12)
        extended["worked_example"] = {
            key: " ".join([str(value)] * 12)
            for key, value in dict(extended["worked_example"]).items()
        }

        concise_total = stem_course.short_video_pacing(concise)["total"]
        detailed_total = stem_course.short_video_pacing(detailed)["total"]
        extended_total = stem_course.short_video_pacing(extended)["total"]

        self.assertGreater(concise_total, 0.0)
        self.assertLessEqual(concise_total, stem_course.MAX_SILENT_VIDEO_SECONDS)
        self.assertEqual(detailed_total, concise_total)
        self.assertEqual(extended_total, detailed_total)

    def test_story_captions_share_the_scene_schedule(self) -> None:
        short = group_short()
        beats = stem_course.canonical_beat_schedule(short)
        cues = stem_course.caption_cues(short)

        self.assertEqual([beat["text"] for beat in beats], [cue[2] for cue in cues])
        self.assertAlmostEqual(
            sum(float(beat["duration"]) for beat in beats),
            stem_course.short_video_pacing(short)["total"],
            places=2,
        )

    @unittest.skipUnless(os.environ.get("RUN_MANIM_RENDER_TESTS") == "1", "set RUN_MANIM_RENDER_TESTS=1 for the draft render")
    def test_group_story_draft_has_no_prolonged_static_or_blank_stage(self) -> None:
        manim = Path(sys.executable).with_name("manim")
        ffmpeg = shutil.which("ffmpeg")
        if not manim.exists() or not ffmpeg:
            self.skipTest("Manim and ffmpeg are required")

        with tempfile.TemporaryDirectory(prefix="video-story-") as tmp:
            root = Path(tmp)
            scene = root / "group_story.py"
            media = root / "media"
            short = group_short()
            scene.write_text(
                stem_course.manim_scene(short, "GroupsAndOperationsShort", stem_course.build_animation_plan(short)),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(manim), "-ql", "--disable_caching", "--media_dir", str(media), str(scene), "GroupsAndOperationsShort"],
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            videos = [path for path in media.glob("videos/**/*.mp4") if "partial_movie_files" not in path.parts]
            self.assertEqual(len(videos), 1, msg=f"rendered videos: {videos}")

            metrics = metrics_for(ffmpeg, videos[0], interval=1)
            self.assertLess(float(metrics["max_static_hold_seconds"]), 8.0)
            self.assertLess(float(metrics["max_blank_hold_seconds"]), 4.0)
            self.assertGreaterEqual(float(metrics["motion_window_coverage_ratio"]), 0.5)


if __name__ == "__main__":
    unittest.main()

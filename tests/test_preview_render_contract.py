from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import audit_video_frames, stem_course


class PreviewRenderContractTests(unittest.TestCase):
    @staticmethod
    def function_source(name: str) -> str:
        source = Path(stem_course.__file__).read_text(encoding="utf-8")
        return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]

    def test_all_audits_production_but_never_queues_unreviewed_output(self) -> None:
        source = self.function_source("cmd_all")
        self.assertIn('if args.quality == "production":', source)
        production_gate = source.index('if args.quality == "production":')
        self.assertGreater(source.index("audit_video_frames.py", production_gate), production_gate)
        self.assertGreater(source.index("cmd_visual_review", production_gate), production_gate)
        self.assertNotIn("cmd_queue", source)

    def test_queue_is_guarded_by_strict_validation(self) -> None:
        guard = self.function_source("require_strict_validation")
        source = self.function_source("cmd_queue")
        self.assertIn("validate_course_run.py", guard)
        self.assertIn("Refusing to {action}", guard)
        self.assertLess(source.index("require_strict_validation"), source.index('read_json(run / "short_plan.json")'))

    def test_publish_revalidates_the_current_queue_and_artifacts(self) -> None:
        source = self.function_source("cmd_publish")
        self.assertLess(source.index("require_strict_validation"), source.index('read_json(queue_path)'))

    def test_generated_scene_uses_native_preview_dimensions_only_when_requested(self) -> None:
        concept = stem_course.ALGORITHMS[2]
        short = {
            "index": 1,
            "concept": concept.name,
            "hook": concept.hook,
            "intuition": concept.intuition,
            "formula": concept.formula,
            "plain_formula": stem_course.plain_math(concept.formula),
            "prerequisites": concept.prerequisites,
            "visual_type": concept.visual_type,
            "worked_example": {
                "setup": concept.example_setup,
                "calculation": concept.example_calc,
                "takeaway": concept.example_takeaway,
            },
        }
        source = stem_course.manim_scene(short, "BreadthFirstSearchShort", stem_course.build_animation_plan(short))
        self.assertIn('os.environ.get("COURSE_SHORTS_RENDER_MODE") == "preview"', source)
        self.assertIn("config.pixel_width = 1080", source)
        self.assertIn("config.pixel_width = 360", source)
        self.assertIn("config.frame_rate = 15", source)
        self.assertNotIn("active_index = pulse_index % len(focus)", source)
        self.assertIn("self.wait(remaining, frozen_frame=True)", source)
        self.assertNotIn("formula_transition = [ReplacementTransform(hook, formula)]", source)

    def test_audit_prefers_preview_only_when_no_production_final_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            videos = run / "videos"
            videos.mkdir()
            preview = videos / "short_01_preview.mp4"
            preview.write_bytes(b"preview")
            self.assertEqual(audit_video_frames.video_files(run), [preview])
            final = videos / "short_01_final.mp4"
            final.write_bytes(b"final")
            self.assertEqual(audit_video_frames.video_files(run), [final])

    def test_render_has_bounded_per_scene_timeout_and_no_blind_retry(self) -> None:
        source = self.function_source("cmd_render")

        self.assertIn("render_timeout = 300 if preview else 1200", source)
        self.assertIn("except subprocess.TimeoutExpired", source)
        self.assertIn('"stage": "manim_timeout"', source)
        self.assertNotIn("retry after clearing Manim scene media", source)


if __name__ == "__main__":
    unittest.main()

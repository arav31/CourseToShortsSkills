from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course


class RenderFailurePropagationTests(unittest.TestCase):
    def run_failed_render(self, quality: str) -> tuple[Path, list[list[str]], tempfile.TemporaryDirectory[str]]:
        temporary = tempfile.TemporaryDirectory()
        run = Path(temporary.name)
        shorts = [
            {"index": index, "concept": f"Concept {index}", "class_name": f"Concept{index}Short"}
            for index in (1, 2)
        ]
        plan = {"shorts": shorts}
        animation_plans = {index: {} for index in (1, 2)}
        commands: list[list[str]] = []

        def fail_manim(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            return subprocess.CompletedProcess(command, 1, stdout="render stdout", stderr="render stderr")

        with (
            mock.patch.object(stem_course, "require_animation_plans", return_value=animation_plans),
            mock.patch.object(stem_course, "require_current_generated_scene"),
            mock.patch.object(stem_course, "manim_scene", return_value="# generated scene\n"),
            mock.patch.object(stem_course, "make_voiceover", return_value={"status": "skipped", "engine": "none"}),
            mock.patch.object(stem_course, "short_video_pacing", return_value={"total": 10.0}),
            mock.patch.object(stem_course, "make_srt", return_value=""),
            mock.patch.object(stem_course, "script_markdown", return_value=""),
            mock.patch.object(stem_course, "prune_managed_short_artifacts"),
            mock.patch.object(stem_course, "subprocess") as mocked_subprocess,
        ):
            mocked_subprocess.run.side_effect = fail_manim
            stem_course.write_json(run / "short_plan.json", plan)
            stem_course.write_json(run / stem_course.ANIMATION_PLAN_INDEX_NAME, {})
            with self.assertRaisesRegex(SystemExit, rf"{quality.capitalize()} render failed for 2 of 2"):
                stem_course.cmd_render(
                    argparse.Namespace(run=str(run), quality=quality, voice_engine="none")
                )

        return run, commands, temporary

    def assert_failed_render_diagnostics(self, run: Path, commands: list[list[str]]) -> None:
        self.assertEqual(len(commands), 2, "each requested short gets exactly one Manim attempt")
        report = json.loads((run / "render_report.json").read_text(encoding="utf-8"))
        self.assertEqual([result["status"] for result in report["results"]], ["failed", "failed"])
        self.assertEqual([result["stage"] for result in report["results"]], ["manim", "manim"])
        for index in (1, 2):
            log = (run / "logs" / f"short_{index:02d}_manim.log").read_text(encoding="utf-8")
            self.assertIn("render stdout", log)
            self.assertIn("render stderr", log)

    def test_preview_failures_exit_nonzero_after_preserving_all_diagnostics(self) -> None:
        run, commands, temporary = self.run_failed_render("preview")
        try:
            self.assert_failed_render_diagnostics(run, commands)
        finally:
            temporary.cleanup()

    def test_production_failures_exit_nonzero_after_preserving_all_diagnostics(self) -> None:
        run, commands, temporary = self.run_failed_render("production")
        try:
            self.assert_failed_render_diagnostics(run, commands)
            trace = json.loads((run / stem_course.RENDER_RUNTIME_TRACE_NAME).read_text(encoding="utf-8"))
            self.assertEqual(trace["renders"], [])
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course


class ManimCacheInvalidationTests(unittest.TestCase):
    def test_changed_scene_reusing_media_dir_cannot_select_stale_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="manim-cache-policy-") as tmp:
            run = Path(tmp)
            short = {"index": 1, "concept": "Cache policy", "class_name": "CachePolicyShort"}
            stem_course.write_json(run / "short_plan.json", {"shorts": [short]})
            stem_course.write_json(run / stem_course.ANIMATION_PLAN_INDEX_NAME, {})
            scene = run / "scenes" / "short_01_cache-policy.py"
            scene.parent.mkdir()
            scene.write_text("footer = 'old text'\n", encoding="utf-8")
            commands: list[list[str]] = []

            def fake_manim(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                media_dir = Path(command[command.index("--media_dir") + 1])
                scene_path = Path(command[-2])
                class_name = command[-1]
                persistent_partial = media_dir / "simulated_cached_partial.bin"
                current_bytes = scene_path.read_bytes()
                if "--disable_caching" in command:
                    rendered_bytes = current_bytes
                else:
                    rendered_bytes = persistent_partial.read_bytes() if persistent_partial.exists() else current_bytes
                persistent_partial.parent.mkdir(parents=True, exist_ok=True)
                persistent_partial.write_bytes(current_bytes)
                rendered = media_dir / "videos" / scene_path.stem / "480p15" / f"{class_name}.mp4"
                rendered.parent.mkdir(parents=True, exist_ok=True)
                rendered.write_bytes(rendered_bytes)
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            patches = (
                mock.patch.object(stem_course, "require_animation_plans", return_value={1: {}}),
                mock.patch.object(stem_course, "require_current_generated_scene"),
                mock.patch.object(stem_course, "make_voiceover", return_value={"status": "skipped", "engine": "none"}),
                mock.patch.object(stem_course, "short_video_pacing", return_value={"total": 10.0}),
                mock.patch.object(stem_course, "make_srt", return_value=""),
                mock.patch.object(stem_course, "script_markdown", return_value=""),
                mock.patch.object(stem_course, "prune_managed_short_artifacts"),
                mock.patch.object(stem_course, "audio_duration", return_value=10.0),
                mock.patch.object(stem_course, "probe_media", return_value={}),
                mock.patch.object(stem_course, "manim_cli_prefix", return_value=["manim"]),
                mock.patch.object(stem_course.subprocess, "run", side_effect=fake_manim),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10]:
                stem_course.cmd_render(argparse.Namespace(run=str(run), quality="preview", voice_engine="none"))
                first_final = run / "videos" / "short_01_cache-policy_preview.mp4"
                self.assertEqual(first_final.read_bytes(), b"footer = 'old text'\n")

                scene.write_text("footer = 'new text'\n", encoding="utf-8")
                stem_course.cmd_render(argparse.Namespace(run=str(run), quality="preview", voice_engine="none"))

            self.assertEqual(first_final.read_bytes(), b"footer = 'new text'\n")
            self.assertEqual(len(commands), 2)
            self.assertTrue(all("--disable_caching" in command for command in commands))
            self.assertEqual(commands[0][commands[0].index("--media_dir") + 1], commands[1][commands[1].index("--media_dir") + 1])

            report = stem_course.read_json(run / "render_report.json")
            provenance = report["results"][0]["provenance"]
            self.assertEqual(
                provenance["effective_cache_policy"],
                {
                    "mode": "disabled",
                    "manim_option": "--disable_caching",
                    "partial_movie_reuse": False,
                    "media_dir": str(run / "manim_media"),
                },
            )
            self.assertEqual(provenance["scene_source_sha256"], stem_course.file_sha256(scene))
            self.assertEqual(provenance["animation_plan_fingerprint"], stem_course.animation_plan_fingerprint({}))


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from tools import stem_course


class ManagedArtifactTests(unittest.TestCase):
    def test_scene_class_name_is_valid_when_concept_starts_with_digit(self) -> None:
        name = stem_course.scene_class_name("1D Kinematics: Position and Velocity")
        self.assertEqual(name, "Concept1DKinematicsPositionAndVelocityShort")
        self.assertTrue(name.isidentifier())

    def test_pruning_removes_only_obsolete_skill_owned_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            for directory in ("scenes", "scripts", "captions", "audio", "videos", "logs"):
                (run / directory).mkdir()
            expected = "short_01_newton-s-laws"
            obsolete = "short_05_rocket-equation"
            preserved = run / "videos" / "instructor_reference.mp4"
            files = (
                run / "scenes" / f"{expected}.py",
                run / "videos" / f"{expected}_preview.mp4",
                run / "scenes" / f"{obsolete}.py",
                run / "videos" / f"{obsolete}_preview.mp4",
                run / "logs" / "short_05_manim.log",
                preserved,
            )
            for path in files:
                path.write_bytes(b"test")

            removed = stem_course.prune_managed_short_artifacts(
                run,
                {"shorts": [{"index": 1, "concept": "Newton's Laws"}]},
            )

            self.assertTrue((run / "scenes" / f"{expected}.py").exists())
            self.assertTrue((run / "videos" / f"{expected}_preview.mp4").exists())
            self.assertFalse((run / "scenes" / f"{obsolete}.py").exists())
            self.assertFalse((run / "videos" / f"{obsolete}_preview.mp4").exists())
            self.assertFalse((run / "logs" / "short_05_manim.log").exists())
            self.assertTrue(preserved.exists())
            self.assertEqual(len(removed), 3)


if __name__ == "__main__":
    unittest.main()

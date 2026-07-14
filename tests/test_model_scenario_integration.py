from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tools import stem_course
from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY
from tools.physics_model_specs import PHYSICS_MODEL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]


class ModelScenarioIntegrationTests(unittest.TestCase):
    def test_direct_stem_course_script_imports_scenario_modules(self) -> None:
        result = subprocess.run(
            [sys.executable, "tools/stem_course.py", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("storyboard", result.stdout)

    def test_every_registered_model_reaches_the_real_semantic_payload(self) -> None:
        rows: list[tuple[str, str]] = []
        for domain, registry in (
            ("physics", PHYSICS_MODEL_REGISTRY),
            ("economics", ECONOMICS_MODEL_REGISTRY),
        ):
            for index, model_id in enumerate(registry, start=1):
                # A humanized model ID can be identical to an official course title
                # whose exact-title contract intentionally selects a different model.
                # Registry round trips must therefore use the canonical ID itself.
                concept = stem_course.source_term_concept(model_id, domain)
                short = stem_course.concept_to_short(concept, index)
                data = stem_course.visual_data_for(short, concept.visual_type)
                payload = data[domain]

                self.assertEqual(short["model_id"], model_id)
                self.assertEqual(payload["model_id"], model_id)
                self.assertEqual(payload["model_scenario"]["model_id"], model_id)
                self.assertEqual(payload["scenario_mode"], payload["model_scenario"]["mode"])
                self.assertTrue(payload["numeric_setup"])
                self.assertTrue(payload["result_fields"])
                self.assertEqual(len(payload["animation_states"]), 3)
                self.assertTrue(payload["visible_evidence_tokens"])
                rows.append((model_id, str(payload["scenario_mode"])))

        expected_count = len(PHYSICS_MODEL_REGISTRY) + len(ECONOMICS_MODEL_REGISTRY)
        self.assertEqual(len(rows), expected_count)
        self.assertEqual(len({mode for _model_id, mode in rows}), expected_count)


if __name__ == "__main__":
    unittest.main()

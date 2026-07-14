from __future__ import annotations

import re
import unittest

from tests.test_notes_pipeline_integration import ECONOMICS_OUTLINE, MECHANICS_OUTLINE
from tools import stem_course


def planned_examples(outline: list[str], domain: str) -> dict[str, dict[str, str]]:
    examples: dict[str, dict[str, str]] = {}
    for index, topic in enumerate(outline, 1):
        concept = stem_course.source_term_concept(topic, domain)
        short = stem_course.concept_to_short(concept, index)
        examples[topic] = {
            key: re.sub(r"\s+", " ", str(value)).strip()
            for key, value in short["worked_example"].items()
        }
    return examples


class WorkedExampleSpecializationTests(unittest.TestCase):
    def test_full_cross_domain_plans_have_unique_worked_examples(self) -> None:
        for domain, outline in (
            ("physics", MECHANICS_OUTLINE),
            ("economics", ECONOMICS_OUTLINE),
        ):
            with self.subTest(domain=domain):
                examples = planned_examples(outline, domain)
                signatures = {
                    tuple(example[field].lower() for field in ("setup", "calculation", "takeaway"))
                    for example in examples.values()
                }
                self.assertEqual(len(signatures), len(outline))

    def test_related_mechanics_models_specialize_setup_calculation_and_takeaway(self) -> None:
        examples = planned_examples(MECHANICS_OUTLINE, "physics")
        related_groups = (
            ("Momentum and Impulse", "Conservation of Momentum"),
            ("Kinetic Energy and Work in 1D", "Kinetic Energy and Work in 2D and 3D"),
            ("Potential Energy", "Potential Energy Diagrams"),
            (
                "Momentum and Impulse",
                "Types of Collision",
                "Elastic Collisions",
                "Angular Momentum of a Point Particle",
                "Angular Momentum of a Rigid Body",
                "Rolling Kinetic Energy & Angular Momentum",
            ),
            (
                "Motion of a Rigid Body",
                "Moment of Inertia",
                "Torque",
                "Rotational Dynamics",
                "Torque and Angular Impulse",
                "Rolling Dynamics",
            ),
        )
        for group in related_groups:
            for field in ("setup", "calculation", "takeaway"):
                with self.subTest(group=group, field=field):
                    self.assertEqual(len({examples[topic][field] for topic in group}), len(group))

        self.assertIn("F dot d=6(3)+8(4)=50 J", examples["Kinetic Energy and Work in 2D and 3D"]["calculation"])
        self.assertIn("K=mv^2/2+Iomega^2/2=9+4.5=13.5 J", examples["Rolling Kinetic Energy & Angular Momentum"]["calculation"])
        self.assertIn("3.27 m/s^2", examples["Rolling Dynamics"]["calculation"])

    def test_sequenced_economics_units_use_different_submodel_mechanisms(self) -> None:
        examples = planned_examples(ECONOMICS_OUTLINE, "economics")
        pairs = (
            ("Competition I", "Competition II"),
            ("Monopoly I", "Monopoly II"),
            ("Oligopoly I", "Oligopoly II"),
        )
        for first, second in pairs:
            for field in ("setup", "calculation", "takeaway"):
                with self.subTest(first=first, second=second, field=field):
                    self.assertNotEqual(examples[first][field], examples[second][field])

        self.assertIn("P=MC", examples["Competition I"]["calculation"])
        self.assertIn("average variable cost", examples["Competition II"]["takeaway"])
        self.assertIn("MR=MC", examples["Monopoly I"]["calculation"])
        self.assertIn("MR1=MR2=MC=20", examples["Monopoly II"]["calculation"])
        self.assertIn("Mutual best responses", examples["Oligopoly I"]["calculation"])
        self.assertIn("QN=60", examples["Oligopoly II"]["calculation"])
        self.assertIn("QC=45", examples["Oligopoly II"]["calculation"])
        self.assertIn("profit to 1012.5", examples["Oligopoly II"]["calculation"])

    def test_all_mit_economics_units_use_their_exact_model_scenario_example(self) -> None:
        generic_revenue_fallback = re.compile(
            r"a firm sells .* units at price|considers lowering price|gain from extra units",
            flags=re.I,
        )
        self.assertEqual(len(ECONOMICS_OUTLINE), 26)
        for index, topic in enumerate(ECONOMICS_OUTLINE, 1):
            with self.subTest(index=index, topic=topic):
                concept = stem_course.source_term_concept(topic, "economics")
                short = stem_course.concept_to_short(concept, index)
                expected = stem_course.economics_model_source_example(topic)
                self.assertIsNotNone(expected)
                assert expected is not None
                authored = " ".join(
                    str(value) for value in short["worked_example"].values()
                )
                self.assertNotRegex(authored, generic_revenue_fallback)
                self.assertEqual(short["worked_example"]["setup"], expected[0])
                self.assertEqual(short["worked_example"]["calculation"], expected[1])
                self.assertEqual(
                    short["worked_example"]["takeaway"],
                    stem_course.concise_result_claim(expected[2]),
                )
                self.assertEqual(short["question_prompt"]["question"], expected[3])
                self.assertEqual(short["question_prompt"]["answer"], expected[4])
                scenario = stem_course.get_economics_model_scenario(
                    str(short["model_id"])
                ).as_dict()
                self.assertEqual(short["model_scenario"], scenario)


if __name__ == "__main__":
    unittest.main()

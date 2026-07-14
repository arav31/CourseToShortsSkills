from __future__ import annotations

import unittest

from tools import stem_course


class GenericPlannerAuthoritativeRevealTests(unittest.TestCase):
    def plan_for(self, title: str) -> tuple[dict[str, object], dict[str, object]]:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept(title, "group_theory"),
            1,
        )
        return short, stem_course.build_animation_plan(short)

    def test_resolve_uses_semantic_verdict_role_instead_of_roster_position(self) -> None:
        short, plan = self.plan_for("Cosets")
        payload = plan["concrete_example"]["renderer_state"]
        verdict_id = next(
            row["id"]
            for row in payload["objects"]
            if "verdict" in row["role"]
        )

        self.assertEqual(verdict_id, payload["objects"][4]["id"])
        self.assertNotEqual(verdict_id, payload["objects"][3]["id"])
        self.assertIn(verdict_id, plan["reveal"]["object_ids"])
        semantic_contract = plan["semantic_transition_contract"]
        self.assertEqual(
            plan["continuity_spine"]["object_ids"],
            list(dict.fromkeys((semantic_contract["anchor_id"], semantic_contract["subject_id"]))),
        )
        self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])

    def test_resolve_preserves_authoritative_snapshot_and_claim_across_subjects(self) -> None:
        for title in ("Cosets", "Presentations and Groups of Small Order"):
            with self.subTest(title=title):
                short, plan = self.plan_for(title)
                payload = plan["concrete_example"]["renderer_state"]
                reveal_contract = payload["reveal_contract"]
                resolve = plan["beats"][-1]

                self.assertEqual(resolve["end_state"], reveal_contract["final_state"])
                self.assertEqual(resolve["claim"], reveal_contract["final_claim"])
                self.assertEqual(
                    plan["reveal"]["statement"],
                    stem_course.animation_cue(reveal_contract["final_claim"], width=180),
                )
                self.assertEqual(stem_course.animation_plan_contract_errors(plan, short), [])


if __name__ == "__main__":
    unittest.main()

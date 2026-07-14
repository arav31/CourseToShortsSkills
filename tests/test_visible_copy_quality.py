from __future__ import annotations

import copy
import unittest

from tools import stem_course


def planned_short(title: str, index: int) -> dict[str, object]:
    short = stem_course.concept_to_short(
        stem_course.source_term_concept(title, "algorithms"),
        index,
    )
    stem_course.attach_plan_model_identity(short)
    return short


class VisibleCopyQualityTests(unittest.TestCase):
    def test_wrap_preserves_all_copy_without_an_ellipsis(self) -> None:
        source = (
            "Potentials reweight every directed edge without changing which complete path "
            "has the smallest original cost."
        )
        lines = stem_course.wrap(source, width=22, lines=2)
        self.assertGreater(len(lines), 2)
        self.assertEqual(" ".join(lines), source)
        self.assertNotIn("...", " ".join(lines))

    def test_visible_cue_turns_storyboard_commands_into_complete_claims(self) -> None:
        cue, lines = stem_course.animation_plan_visible_cue(
            "Show each potential h(v), then highlight every reweighted edge."
        )
        self.assertEqual(cue, "Each potential h (v) is explicit in the model.")
        self.assertFalse(stem_course.storyboard_instruction_leak(cue))
        self.assertNotIn("...", cue)
        self.assertRegex(cue, r"[.!?]$")
        self.assertEqual(" ".join(lines), cue)

    def test_animation_cue_selects_a_complete_clause_without_truncation(self) -> None:
        cue = stem_course.animation_cue(
            "Potentials preserve every path comparison. This second sentence is deliberately "
            "long enough that the old character limit appended dots.",
            width=48,
        )
        self.assertEqual(cue, "Potentials preserve every path comparison.")
        self.assertNotIn("...", cue)

    def test_validator_rejects_instruction_leakage_and_trailing_ellipsis(self) -> None:
        short = planned_short("Johnson's Algorithm", 13)
        plan = stem_course.build_animation_plan(short)

        imperative = copy.deepcopy(plan)
        imperative["beats"][0]["text"] = "Show every potential."
        imperative["beats"][0]["cue_lines"] = ["Show every potential."]
        errors = stem_course.animation_plan_contract_errors(imperative, short)
        self.assertTrue(any("storyboard instruction" in error for error in errors))

        truncated = copy.deepcopy(plan)
        truncated["beats"][0]["text"] = "Potentials preserve paths..."
        truncated["beats"][0]["cue_lines"] = ["Potentials preserve paths..."]
        errors = stem_course.animation_plan_contract_errors(truncated, short)
        self.assertTrue(any("ellipsis" in error for error in errors))

    def test_johnson_and_dp_generated_scenes_keep_complete_hooks(self) -> None:
        expectations = (
            (13, "Johnson's Algorithm", "Potentials reweight every edge without changing which paths are shortest."),
            (15, "Dynamic Programming State Design", "A state must preserve exactly the information future transitions need."),
        )
        for index, title, expected_hook in expectations:
            with self.subTest(title=title):
                short = planned_short(title, index)
                plan = stem_course.build_animation_plan(short)
                source = stem_course.manim_scene(short, f"VisibleCopy{index}", plan)
                hook_beats = [beat for beat in plan["beats"] if beat["scene_state"] == "hook"]
                self.assertEqual([beat["text"] for beat in hook_beats], [expected_hook])
                self.assertIn(expected_hook, source)
                self.assertNotIn(expected_hook.rstrip(".") + "...", source)
                self.assertFalse(any(
                    stem_course.storyboard_instruction_leak(beat["text"])
                    for beat in plan["beats"]
                ))

    def test_cosets_scene_schedule_never_exposes_the_comma_fragment(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Cosets", "group_theory"),
            3,
        )
        stem_course.attach_plan_model_identity(short)
        plan = stem_course.build_animation_plan(short)
        schedule = stem_course.animation_plan_scene_schedule(short, plan)
        core_idea = [beat for beat in schedule if beat["scene_state"] == "core_idea"]

        expected = "0 + H = 3ℤ."
        self.assertEqual([beat["text"] for beat in core_idea], [expected])
        self.assertNotIn("Study Cosets by naming the objects, the operation,", {
            beat["text"] for beat in schedule
        })
        self.assertTrue(all(
            stem_course.complete_visible_prose_stage(beat["text"])
            for beat in schedule
            if beat["scene_state"] != "core_formula"
        ))
        source = stem_course.manim_scene(short, "CosetsVisibleCopyRegression", plan)
        compile(source, "generated_cosets_visible_copy.py", "exec")
        self.assertIn(expected, source)
        self.assertNotIn("names its objects, operation, and preserved property", source)
        self.assertNotIn("'text': 'Study Cosets by naming the objects, the operation,'", source)


if __name__ == "__main__":
    unittest.main()

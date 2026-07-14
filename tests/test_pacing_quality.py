from __future__ import annotations

import unittest
from tools import stem_course
from tools.validate_course_run import srt_time_to_seconds


def sample_short() -> dict[str, object]:
    return {
        "index": 1,
        "concept": "Matrix-vector multiplication",
        "hook": (
            "A matrix does not merely store numbers; its columns describe directions "
            "that are scaled, combined, and carried into a new output vector."
        ),
        "intuition": (
            "Each coordinate of the input selects how much of the matching matrix "
            "column contributes to the result, so the geometry and arithmetic agree."
        ),
        "formula": r"A\vec{x}=x_1\vec{a}_1+x_2\vec{a}_2",
        "plain_formula": "A x = x sub 1 a sub 1 + x sub 2 a sub 2",
        "visual_type": "matrix_vector",
        "worked_example": {
            "setup": "Let A = [[2, 1], [1, 3]] and x = (4, 2).",
            "calculation": "Ax = (2*4 + 1*2, 1*4 + 3*2) = (10, 10).",
            "takeaway": "The output is the same weighted combination of the two columns.",
        },
    }


class PacingQualityTests(unittest.TestCase):
    def test_readable_text_stages_keeps_one_unpunctuated_claim_together(self) -> None:
        source = "one two three four five six seven eight nine ten eleven twelve thirteen"
        stages = stem_course.readable_text_stages(source, width=12, lines_per_stage=3)

        self.assertEqual(len(stages), 1)
        self.assertLessEqual(len(stages[0]), 3)
        self.assertEqual(
            " ".join(line for stage in stages for line in stage).casefold(),
            source.casefold(),
        )

    def test_readable_text_stages_respect_clause_boundaries(self) -> None:
        source = (
            "Asymptotic notation compares how work scales as input size grows, "
            "which predicts algorithm behavior across machines."
        )
        stages = stem_course.readable_text_stages(source, width=38, lines_per_stage=3)

        self.assertEqual(len(stages), 1)
        self.assertTrue(all(len(stage) <= 3 for stage in stages))
        self.assertEqual(" ".join(line for stage in stages for line in stage), source)

    def test_group_narrative_is_staged_without_shrinking_or_truncation(self) -> None:
        examples = (
            stem_course.GROUP_THEORY[4],
            stem_course.GROUP_THEORY[11],
        )

        for index, concept in enumerate(examples, start=1):
            short = stem_course.concept_to_short(concept, index)
            beats = stem_course.canonical_beat_schedule(short)
            idea_beats = [beat for beat in beats if beat["scene_state"] == "core_idea"]

            self.assertGreaterEqual(len(idea_beats), 1, concept.name)
            self.assertTrue(all(len(beat["lines"]) <= 2 for beat in idea_beats))
            self.assertTrue(all("..." not in str(beat["text"]) for beat in idea_beats))
            self.assertTrue(all(float(beat["read_seconds"]) <= float(beat["duration"]) for beat in idea_beats))

    def test_repeated_title_prefix_is_removed_before_all_hook_staging(self) -> None:
        short = sample_short()
        short["concept"] = "Direct Access Array"
        short["hook"] = (
            "Direct-access array: A direct-access array turns an integer index "
            "into one storage address."
        )

        beats = stem_course.canonical_beat_schedule(short)
        hook_beats = [beat for beat in beats if beat["scene_state"] == "hook"]
        scene = stem_course.manim_scene(
            short,
            "DirectAccessArrayShort",
            stem_course.build_animation_plan(short),
        )

        self.assertEqual(len(hook_beats), 1)
        self.assertEqual(
            hook_beats[0]["text"],
            "A direct-access array turns an integer index into one storage address.",
        )
        self.assertNotIn("[['Direct-access array:',", scene)
        self.assertIn(f"hook_stages = {[hook_beats[0]['lines']]!r}", scene)

    def test_canonical_beats_are_ordered_unique_and_phone_readable(self) -> None:
        short = sample_short()
        beats = stem_course.canonical_beat_schedule(short)

        self.assertEqual(len({beat["id"] for beat in beats}), len(beats))
        phases = [beat["phase"] for beat in beats]
        self.assertEqual(phases, sorted(phases, key={"concept": 0, "example": 1}.get))
        self.assertEqual(
            {beat["scene_state"] for beat in beats},
            {
                "hook",
                "core_formula",
                "core_idea",
                "example_setup",
                "example_calculation",
                "example_takeaway",
            },
        )
        self.assertTrue(all(float(beat["duration"]) >= float(beat["read_seconds"]) for beat in beats))
        self.assertTrue(all(float(beat["duration"]) >= float(beat["readability_floor_seconds"]) for beat in beats))
        self.assertTrue(all(len(beat["lines"]) <= 2 for beat in beats))
        self.assertTrue(all(str(beat["text"]).strip() for beat in beats))

    def test_missing_transition_callbacks_do_not_create_an_inferred_action_floor(self) -> None:
        short = sample_short()
        beats = stem_course.canonical_beat_schedule(short)

        calculation = next(beat for beat in beats if beat["scene_state"] == "example_calculation")
        self.assertEqual(calculation["semantic_step_count"], 0)
        self.assertEqual(calculation["semantic_transition_ids"], [])
        self.assertEqual(float(calculation["action_floor_seconds"]), 0.0)
        self.assertAlmostEqual(
            float(calculation["duration"]),
            float(calculation["readability_floor_seconds"]),
            places=2,
        )

    def test_exact_cs_transitions_are_assigned_before_duration_floors(self) -> None:
        concept = stem_course.source_term_concept(
            "Pseudopolynomial Dynamic Programming",
            "algorithms",
        )
        short = stem_course.concept_to_short(concept, 1)
        baseline = stem_course.canonical_beat_schedule(short)

        inflated_step_estimate = stem_course.canonical_beat_schedule(short)

        active = [
            beat
            for beat in baseline
            if beat["scene_state"] in stem_course.SEMANTIC_TRANSITION_STATES
        ]
        self.assertEqual(
            [beat["duration"] for beat in inflated_step_estimate],
            [beat["duration"] for beat in baseline],
        )
        self.assertEqual([beat["semantic_transition_count"] for beat in active], [4, 5, 4, 5])
        for beat in active:
            expected_floor = (
                float(beat["visual_action_seconds"])
                + float(beat["readability_floor_seconds"])
                + stem_course.MAX_SEMANTIC_FROZEN_TAIL_SECONDS
            )
            self.assertAlmostEqual(float(beat["action_floor_seconds"]), expected_floor, delta=0.011)
            self.assertGreaterEqual(
                float(beat["transition_motion_floor_seconds"]),
                stem_course.MIN_SEMANTIC_ACTION_SECONDS
                * float(beat["semantic_transition_weight"]),
            )
            self.assertEqual(
                float(beat["max_frozen_tail_seconds"]),
                stem_course.MAX_SEMANTIC_FROZEN_TAIL_SECONDS,
            )

        plan = stem_course.build_animation_plan(short)
        planned_ids = [
            transition_id
            for beat in plan["beats"][1:5]
            for transition_id in beat["semantic_transition_ids"]
        ]
        scheduled_ids = [
            transition_id
            for beat in active
            for transition_id in beat["semantic_transition_ids"]
        ]
        self.assertEqual(scheduled_ids, planned_ids)

    def test_captions_follow_beats_and_scale_to_the_final_mux_duration(self) -> None:
        short = sample_short()
        beats = stem_course.canonical_beat_schedule(short)
        cues = stem_course.caption_cues(short)

        self.assertEqual(len(cues), len(beats))
        previous_end = 0.0
        for cue, beat in zip(cues, beats):
            start = srt_time_to_seconds(cue[0])
            end = srt_time_to_seconds(cue[1])
            self.assertAlmostEqual(start, previous_end, places=3)
            self.assertAlmostEqual(end - start, float(beat["duration"]), places=3)
            self.assertEqual(cue[2], beat["text"])
            previous_end = end

        stretched = stem_course.caption_cues(short, target_duration=99.0)
        self.assertEqual([cue[2] for cue in stretched], [beat["text"] for beat in beats])
        self.assertAlmostEqual(srt_time_to_seconds(stretched[-1][1]), 99.0, places=3)

    def test_render_duration_cannot_redefine_the_semantic_plan(self) -> None:
        exact = stem_course.planned_duration_sync(40.0, 41.0)
        short = stem_course.planned_duration_sync(40.0, 12.0)

        self.assertEqual(exact["status"], "ok")
        self.assertEqual(short["status"], "mismatch")
        self.assertAlmostEqual(float(short["delta_seconds"]), -28.0)

    def test_optional_audio_alignment_pads_the_shorter_stream_without_truncation(self) -> None:
        voice_longer = stem_course.media_alignment_durations(40.0, 52.5)
        video_longer = stem_course.media_alignment_durations(52.5, 40.0)
        silent = stem_course.media_alignment_durations(40.0, 0.0)

        self.assertEqual(voice_longer, {"target_duration": 52.5, "video_pad_seconds": 12.5, "audio_pad_seconds": 0.0})
        self.assertEqual(video_longer, {"target_duration": 52.5, "video_pad_seconds": 0.0, "audio_pad_seconds": 12.5})
        self.assertEqual(silent, {"target_duration": 40.0, "video_pad_seconds": 0.0, "audio_pad_seconds": 0.0})

    def test_total_pacing_is_exactly_the_sum_of_content_derived_beats(self) -> None:
        short = sample_short()
        beats = stem_course.canonical_beat_schedule(short)
        pacing = stem_course.short_video_pacing(short)
        concept = sum(float(beat["duration"]) for beat in beats if beat["phase"] == "concept")
        example = sum(float(beat["duration"]) for beat in beats if beat["phase"] == "example")

        self.assertAlmostEqual(pacing["intro_duration"], concept, places=2)
        self.assertAlmostEqual(pacing["example_duration"], example, places=2)
        self.assertAlmostEqual(pacing["total"], concept + example, places=2)

    def test_fit_schedule_does_not_pad_to_a_manufactured_minimum(self) -> None:
        beats = [{"duration": 1.5}, {"duration": 2.0}]
        self.assertEqual(stem_course.fit_beat_schedule_duration(beats), beats)

    def test_boilerplate_takeaway_is_normalized_and_staged_as_result_copy(self) -> None:
        short = sample_short()
        short["worked_example"]["takeaway"] = (
            "This teaches Matrix-vector multiplication by showing each weighted column "
            "arrive in the final output while the arithmetic stays visible."
        )
        beats = [beat for beat in stem_course.canonical_beat_schedule(short) if beat["scene_state"] == "example_takeaway"]

        self.assertGreaterEqual(len(beats), 1)
        self.assertTrue(str(beats[0]["text"]).startswith("Result -"))
        self.assertTrue(all("This teaches" not in str(beat["text"]) for beat in beats))
        self.assertTrue(all(len(beat["lines"]) == 1 for beat in beats))
        self.assertNotIn("...", " ".join(str(beat["text"]) for beat in beats))

    def test_newton_boilerplate_is_normalized_in_short_plan_data(self) -> None:
        concept = stem_course.source_term_concept("Laws of Motion", "physics")
        short = stem_course.concept_to_short(concept, 1)
        takeaway = str(short["worked_example"]["takeaway"])

        self.assertIn("differs from", takeaway)
        self.assertNotIn("This teaches", takeaway)
        self.assertNotIn("...", takeaway)

    def test_screen_cue_lines_requires_staging_instead_of_widening(self) -> None:
        with self.assertRaisesRegex(ValueError, "stage the copy"):
            stem_course.screen_cue_lines(" ".join(["readable"] * 30), width=20, max_lines=2)

    def test_generated_scene_requires_30_fps_and_keeps_inactive_holds_static(self) -> None:
        short = sample_short()
        source = stem_course.manim_scene(short, "MatrixVectorShort", stem_course.build_animation_plan(short))

        self.assertIn("config.frame_rate = 30", source)
        self.assertNotIn("active_index = pulse_index % len(focus)", source)
        self.assertNotIn("interval = min(1.6, remaining)", source)
        self.assertIn("self._beat_schedule =", source)
        self.assertIn('motion.get("kind") == "semantic_sequence"', source)
        self.assertIn("remaining * 0.72", source)
        self.assertNotIn("return_path = list(reversed", source)
        self.assertIn("_course_effective_font_size", source)


if __name__ == "__main__":
    unittest.main()

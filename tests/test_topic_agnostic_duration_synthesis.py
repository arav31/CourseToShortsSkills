from __future__ import annotations

import unittest

from tools import stem_course


def planned_duration(title: str, domain: str) -> tuple[float, dict[str, object]]:
    concept = stem_course.source_term_concept(title, domain)
    short = stem_course.concept_to_short(concept, 1)
    return stem_course.short_video_pacing(short)["total"], stem_course.semantic_duration_profile(short)


class TopicAgnosticDurationSynthesisTests(unittest.TestCase):
    def test_simple_and_multistep_topics_earn_distinct_cross_domain_durations(self) -> None:
        pairs = {
            "math": (
                planned_duration("Isomorphisms", "group_theory"),
                planned_duration("Presentations and Groups of Small Order", "group_theory"),
            ),
            "cs": (
                planned_duration("Breadth-First Search", "algorithms"),
                planned_duration("Johnson's Algorithm", "algorithms"),
            ),
            "physics": (
                planned_duration("Gravity", "physics"),
                planned_duration("Rolling Kinetic Energy & Angular Momentum", "physics"),
            ),
            "economics": (
                planned_duration("Introduction to Trade", "economics"),
                planned_duration("Input Markets II—Labor and Capital", "economics"),
            ),
        }

        for domain, ((simple_duration, _simple), (complex_duration, _complex)) in pairs.items():
            with self.subTest(domain=domain):
                self.assertGreater(complex_duration, simple_duration + 4.0)

        durations = [duration for pair in pairs.values() for duration, _profile in pair]
        self.assertGreater(max(durations) - min(durations), 45.0)
        self.assertGreaterEqual(len({round(duration, 1) for duration in durations}), 7)
        self.assertLess(sum(36.0 <= duration <= 40.0 for duration in durations), len(durations) / 2)

    def test_profile_accounts_for_each_topic_agnostic_timing_input(self) -> None:
        duration, profile = planned_duration("Johnson's Algorithm", "algorithms")

        self.assertGreater(profile["object_count"], 0)
        self.assertGreater(profile["object_construction_seconds"], 0)
        self.assertGreater(profile["transition_count"], 4)
        self.assertGreater(profile["visual_action_seconds"], 0)
        self.assertGreater(profile["comparison_step_count"], 0)
        self.assertGreater(profile["formula"]["relation_count"], 0)
        self.assertGreater(profile["formula"]["seconds"], 0)
        self.assertGreater(profile["resolution_seconds"], 0)
        self.assertGreater(duration, 60.0)

    def test_beats_expose_auditable_timing_components(self) -> None:
        concept = stem_course.source_term_concept("Rolling Dynamics", "physics")
        short = stem_course.concept_to_short(concept, 1)
        beats = stem_course.canonical_beat_schedule(short)

        self.assertGreater(next(row for row in beats if row["scene_state"] == "hook")["object_construction_seconds"], 0)
        self.assertGreater(next(row for row in beats if row["scene_state"] == "core_formula")["formula_derivation_seconds"], 0)
        self.assertGreater(
            max(row["result_resolution_seconds"] for row in beats if row["scene_state"] == "example_takeaway"),
            0,
        )
        self.assertTrue(any(row["semantic_transition_count"] for row in beats))
        for beat in beats:
            self.assertGreaterEqual(float(beat["duration"]), float(beat["readability_floor_seconds"]))
            if float(beat["visual_action_seconds"]) > 0:
                self.assertAlmostEqual(
                    float(beat["action_floor_seconds"]),
                    float(beat["readability_floor_seconds"])
                    + float(beat["visual_action_seconds"])
                    + float(beat["max_frozen_tail_seconds"]),
                    delta=0.011,
                )


if __name__ == "__main__":
    unittest.main()

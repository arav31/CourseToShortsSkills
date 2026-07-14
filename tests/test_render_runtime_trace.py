from __future__ import annotations

import ast
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools import stem_course
from tools.validate_course_run import CourseRunValidator, planned_state_change_contracts


def runtime_helper_functions(*names: str) -> dict[str, object]:
    tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace: dict[str, object] = {"json": json, "math": math, "os": os}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "<runtime-helpers>", "exec"), namespace)
    return {name: namespace[name] for name in names}


def short_from_concept(concept: stem_course.Concept, index: int = 1) -> dict[str, object]:
    return {
        "index": index,
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


def execution_marker_payload(
    animation_plan: dict[str, object],
    *,
    short_index: int = 1,
) -> dict[str, object]:
    semantic_bindings = stem_course.render_runtime_semantic_transition_bindings(animation_plan)
    semantic_ids_by_beat: dict[str, list[str]] = {}
    for binding in semantic_bindings:
        semantic_ids_by_beat.setdefault(binding["beat_id"], []).append(binding["planned_transition_id"])
    events = []
    for contract in stem_course.render_runtime_transition_contracts(animation_plan):
        before = float(contract["before_seconds"])
        after = float(contract["after_seconds"])
        event = {
            key: contract[key]
            for key in (
                "beat_id",
                "planned_transition_id",
                "persistent_object_ids",
                "changed_attribute",
                "observed_before",
                "observed_after",
                "arc_phase",
            )
        }
        declared_ids = semantic_ids_by_beat.get(str(contract["beat_id"]), [])
        execution_records = [
            {
                "kind": "callback",
                "callback_name": "fixture_transform",
                "declared_transition_id": transition_id,
                "started_seconds": before,
                "finished_seconds": after,
                "started_frame": round(before * stem_course.RENDER_TIMELINE_FPS),
                "finished_frame": round(after * stem_course.RENDER_TIMELINE_FPS),
                "choreography_intervals": [{
                    "started_frame": round(before * stem_course.RENDER_TIMELINE_FPS),
                    "finished_frame": round(after * stem_course.RENDER_TIMELINE_FPS),
                    "frame_count": round((after - before) * stem_course.RENDER_TIMELINE_FPS),
                    "animation_types": ["Transform"],
                    "persistent_carrier_ids": list(contract["persistent_object_ids"]),
                    "carrier_type": "causal_verification",
                    "semantic_before": dict(contract["observed_before"]),
                    "semantic_after": dict(contract["observed_after"]),
                    "qualifying_motion": True,
                }],
                "status": "ok",
            }
            for transition_id in declared_ids
        ]
        if (contract["arc_phase"] == "transform" or contract.get("motion_evidence_required")) and not execution_records:
            execution_records.append(
                {
                    "kind": "callback",
                    "callback_name": "fixture_transform",
                    "declared_transition_id": None,
                    "started_seconds": before,
                    "finished_seconds": after,
                    "started_frame": round(before * stem_course.RENDER_TIMELINE_FPS),
                    "finished_frame": round(after * stem_course.RENDER_TIMELINE_FPS),
                    "choreography_intervals": [{
                        "started_frame": round(before * stem_course.RENDER_TIMELINE_FPS),
                        "finished_frame": round(after * stem_course.RENDER_TIMELINE_FPS),
                        "frame_count": round((after - before) * stem_course.RENDER_TIMELINE_FPS),
                        "animation_types": ["Transform"],
                        "persistent_carrier_ids": list(contract["persistent_object_ids"]),
                        "carrier_type": "causal_verification",
                        "semantic_before": dict(contract["observed_before"]),
                        "semantic_after": dict(contract["observed_after"]),
                        "qualifying_motion": True,
                    }],
                    "status": "ok",
                }
            )
        event.update(
            {
                "before_seconds": before,
                "after_seconds": after,
                "renderer_markers": [
                    {"phase": "before", "renderer_seconds": before},
                    {"phase": "after", "renderer_seconds": after},
                ],
                "execution_records": execution_records,
                "timing_source": "manim.renderer.time",
            }
        )
        events.append(event)
    return {
        "schema_version": stem_course.RENDER_EXECUTION_MARKER_SCHEMA_VERSION,
        "short_index": short_index,
        "animation_plan_fingerprint": stem_course.animation_plan_fingerprint(animation_plan),
        "render_mode": "production",
        "timing_source": "manim.renderer.time",
        "scene_finished_seconds": animation_plan["target_duration_seconds"],
        "status": "complete",
        "errors": [],
        "transitions": events,
        "semantic_transition_bindings": [
            {
                **binding,
                "registered_callback_count": 1,
                "executed_callback_count": 1,
                "successful_callback_count": 1,
                "status": "ok",
            }
            for binding in semantic_bindings
        ],
    }


class RenderRuntimeTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.short = short_from_concept(stem_course.ALGORITHMS[2])
        self.animation_plan = stem_course.build_animation_plan(self.short)

    def runtime_row_fixture(
        self,
        run: Path,
        animation_plan: dict[str, object] | None = None,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        animation_plan = animation_plan or self.animation_plan
        video_path = run / "videos" / "short_01_final.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"silent-final-video-fixture")
        row = stem_course.build_render_runtime_trace_row(
            short_index=1,
            video_file="videos/short_01_final.mp4",
            video_path=video_path,
            animation_plan=animation_plan,
            marker_payload=execution_marker_payload(animation_plan),
        )
        return json.loads(json.dumps(row)), planned_state_change_contracts(animation_plan)

    def validate_runtime_row(
        self,
        run: Path,
        row: dict[str, object],
        expected_contracts: list[dict[str, object]],
    ) -> tuple[CourseRunValidator, set[tuple[str, str]]]:
        validator = CourseRunValidator(run)
        valid_keys = validator.validate_render_runtime_trace_row(
            row,
            index=1,
            video_file=str(row["video_file"]),
            video_hash=str(row["video_sha256"]),
            plan_fingerprint=str(row["animation_plan_fingerprint"]),
            expected_contracts=expected_contracts,
            remediation="fixture",
        )
        return validator, valid_keys

    def test_producer_semantic_contract_exactly_matches_validator_consumer(self) -> None:
        producer_contracts = stem_course.render_runtime_semantic_event_contracts(self.animation_plan)

        self.assertEqual(producer_contracts, planned_state_change_contracts(self.animation_plan))
        self.assertEqual(len(producer_contracts), 5)

    def test_consumer_preserves_every_transition_in_a_multi_transition_beat(self) -> None:
        semantic_bindings = stem_course.render_runtime_semantic_transition_bindings(self.animation_plan)
        consumer_contracts = planned_state_change_contracts(self.animation_plan)
        semantic_count_by_beat: dict[str, int] = {}
        for binding in semantic_bindings:
            semantic_count_by_beat[binding["beat_id"]] = semantic_count_by_beat.get(binding["beat_id"], 0) + 1

        self.assertGreater(len(semantic_bindings), 0)
        self.assertGreater(max(semantic_count_by_beat.values()), 1)
        self.assertEqual(
            [
                (contract["beat_id"], contract["planned_transition_id"])
                for contract in consumer_contracts
            ],
            [
                (binding["beat_id"], binding["planned_transition_id"])
                for binding in semantic_bindings
            ],
        )
        multi_transition_beat = next(
            beat_id for beat_id, count in semantic_count_by_beat.items() if count > 1
        )
        self.assertEqual(
            [
                contract["planned_transition_id"]
                for contract in consumer_contracts
                if contract["beat_id"] == multi_transition_beat
            ],
            ["bfs:4", "bfs:5"],
        )

    def test_generic_plan_without_semantic_ids_uses_beat_level_events(self) -> None:
        animation_plan = json.loads(json.dumps(self.animation_plan))
        for beat in animation_plan["beats"]:
            beat["semantic_transition_ids"] = []

        with tempfile.TemporaryDirectory(prefix="runtime-trace-generic-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run, animation_plan)
            validator, valid_keys = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(contracts)
        self.assertTrue(
            all(contract["planned_transition_id"] == contract["beat_id"] for contract in contracts)
        )
        self.assertEqual(valid_keys, {
            (str(contract["beat_id"]), str(contract["planned_transition_id"]))
            for contract in contracts
        })
        self.assertFalse(validator.issues)

    def test_resolve_beat_gets_visual_contract_when_domain_state_is_already_final(self) -> None:
        animation_plan = json.loads(json.dumps(self.animation_plan))
        resolve = next(beat for beat in animation_plan["beats"] if beat["arc_phase"] == "resolve")
        resolve["semantic_transition_ids"] = []
        resolve["end_state"] = dict(resolve["start_state"])
        resolve["state_delta"] = stem_course.animation_state_delta(
            resolve["start_state"], resolve["end_state"]
        )

        contract = next(
            item
            for item in stem_course.render_runtime_transition_contracts(animation_plan)
            if item["beat_id"] == resolve["id"]
        )

        self.assertEqual(contract["arc_phase"], "resolve")
        self.assertTrue(contract["motion_evidence_required"])
        self.assertNotEqual(contract["observed_before"], contract["observed_after"])
        self.assertEqual(len(contract["persistent_object_ids"]), len(set(contract["persistent_object_ids"])))

    def test_plan_shaped_timestamps_without_renderer_evidence_are_rejected(self) -> None:
        payload = execution_marker_payload(self.animation_plan)
        transform_event = next(
            event for event in payload["transitions"] if event["arc_phase"] == "transform"
        )
        transform_event["renderer_markers"] = []
        transform_event["execution_records"] = []

        errors = stem_course.render_execution_marker_errors(
            payload,
            self.animation_plan,
            short_index=1,
        )

        self.assertTrue(any("renderer marker" in error for error in errors))
        self.assertTrue(any("no successful renderer callback" in error for error in errors))

    def test_callback_success_without_qualifying_motion_is_rejected(self) -> None:
        payload = execution_marker_payload(self.animation_plan)
        event = next(
            item for item in payload["transitions"]
            if item.get("motion_evidence_required") or item["arc_phase"] == "resolve"
        )
        for record in event["execution_records"]:
            record["choreography_intervals"] = []

        errors = stem_course.render_execution_marker_errors(
            payload, self.animation_plan, short_index=1,
        )

        self.assertTrue(any("no qualifying motion evidence" in error for error in errors))

    def test_renderer_marker_must_match_the_exact_planned_frame(self) -> None:
        payload = execution_marker_payload(self.animation_plan)
        event = payload["transitions"][0]
        event["before_seconds"] += 1.0 / stem_course.RENDER_TIMELINE_FPS
        event["renderer_markers"][0]["renderer_seconds"] = event["before_seconds"]

        errors = stem_course.render_execution_marker_errors(
            payload, self.animation_plan, short_index=1,
        )

        self.assertTrue(any("before_seconds does not match" in error for error in errors))

    def test_post_validator_rejects_a_one_frame_runtime_marker_shift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-frame-shift-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            event = row["semantic_transition_events"][0]
            event["before_seconds"] += 1.0 / stem_course.RENDER_TIMELINE_FPS
            event["renderer_markers"][0]["renderer_seconds"] = event["before_seconds"]

            validator, _valid_keys = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(any("planned evidence" in issue.message for issue in validator.issues))

    def test_final_row_is_hash_bound_and_accepted_by_strict_consumer(self) -> None:
        marker_payload = execution_marker_payload(self.animation_plan)
        index_payload = {"schema_version": "fixture-index", "plans": [{"short_index": 1}]}
        with tempfile.TemporaryDirectory(prefix="runtime-trace-") as tmp:
            run = Path(tmp)
            video_path = run / "videos" / "short_01_final.mp4"
            video_path.parent.mkdir()
            video_path.write_bytes(b"silent-final-video-fixture")
            video_file = "videos/short_01_final.mp4"
            row = stem_course.build_render_runtime_trace_row(
                short_index=1,
                video_file=video_file,
                video_path=video_path,
                animation_plan=self.animation_plan,
                marker_payload=marker_payload,
            )
            payload = stem_course.render_runtime_trace_payload(index_payload, [row])
            stem_course.write_json(run / stem_course.RENDER_RUNTIME_TRACE_NAME, payload)

            expected_index_fingerprint = stem_course.canonical_json_hash(index_payload)
            validator = CourseRunValidator(run)
            rows = validator.load_render_runtime_trace(expected_index_fingerprint)
            self.assertIsNotNone(rows)
            valid_keys = validator.validate_render_runtime_trace_row(
                rows[1],
                index=1,
                video_file=video_file,
                video_hash=stem_course.file_sha256(video_path),
                plan_fingerprint=stem_course.animation_plan_fingerprint(self.animation_plan),
                expected_contracts=planned_state_change_contracts(self.animation_plan),
                remediation="fixture",
            )

            self.assertEqual(len(valid_keys), len(planned_state_change_contracts(self.animation_plan)))
            self.assertFalse(validator.issues)
            self.assertEqual(row["video_sha256"], stem_course.file_sha256(video_path))
            self.assertNotIn("voiceover", row)
            self.assertEqual(
                len(row["semantic_transition_events"]),
                len(stem_course.render_runtime_semantic_transition_bindings(self.animation_plan)),
            )
            self.assertTrue(
                all(
                    len(event["execution_records"]) == 1
                    and event["execution_records"][0]["declared_transition_id"]
                    == event["planned_transition_id"]
                    for event in row["semantic_transition_events"]
                )
            )

    def test_missing_per_id_event_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-missing-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            row["semantic_transition_events"].pop(1)

            validator, _ = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(any("omits" in issue.message for issue in validator.issues))

    def test_duplicate_per_id_event_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-duplicate-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            duplicate = json.loads(json.dumps(row["semantic_transition_events"][0]))
            row["semantic_transition_events"].insert(1, duplicate)

            validator, _ = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(any("duplicates planned transition" in issue.message for issue in validator.issues))

    def test_extra_per_id_event_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-extra-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            extra = json.loads(json.dumps(row["semantic_transition_events"][0]))
            extra["planned_transition_id"] = "unplanned:extra"
            row["semantic_transition_events"].append(extra)

            validator, _ = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(
            any("does not identify a planned transition" in issue.message for issue in validator.issues)
        )

    def test_wrong_order_per_id_events_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-order-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            events = row["semantic_transition_events"]
            events[0], events[1] = events[1], events[0]

            validator, _ = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(any("exact planned transition order" in issue.message for issue in validator.issues))

    def test_stale_per_id_event_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-stale-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            event = row["semantic_transition_events"][0]
            object_id = next(iter(event["observed_after"]))
            event["observed_after"][object_id] = "stale rendered state"

            validator, _ = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(any("planned after-state" in issue.message for issue in validator.issues))

    def test_per_id_callback_count_must_match_binding_exactly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="runtime-trace-callback-") as tmp:
            run = Path(tmp)
            row, contracts = self.runtime_row_fixture(run)
            records = row["semantic_transition_events"][0]["execution_records"]
            records.append(json.loads(json.dumps(records[0])))

            validator, _ = self.validate_runtime_row(run, row, contracts)

        self.assertTrue(any("exact registered callback count" in issue.message for issue in validator.issues))

    def test_generated_scene_emits_callback_backed_renderer_markers(self) -> None:
        source = stem_course.manim_scene(self.short, "RuntimeTraceShort", self.animation_plan)

        compile(source, "<runtime-trace-scene>", "exec")
        self.assertIn("initialize_render_runtime_trace", source)
        self.assertIn("COURSE_SHORTS_RUNTIME_TRACE_PATH", source)
        self.assertIn("runtime_callback_started", source)
        self.assertIn("finish_render_runtime_trace", source)
        self.assertIn("required transform has no executed callback", source)
        construct = source[source.index("    def construct(self):") :]
        self.assertLess(
            construct.index('self.runtime_begin_scene_state("hook")'),
            construct.index("self.play_intro_visual"),
        )

    def test_renderer_callbacks_emit_the_sidecar_from_the_live_clock(self) -> None:
        helper_names = (
            "runtime_renderer_seconds",
            "runtime_renderer_frame",
            "runtime_target_frame",
            "semantic_frame_rate",
            "semantic_wait_seconds",
            "initialize_render_runtime_trace",
            "runtime_register_semantic_callbacks",
            "runtime_contract_key",
            "runtime_beat_contracts",
            "runtime_wait_until",
            "runtime_begin_beat",
            "runtime_callback_started",
            "runtime_callback_finished",
            "runtime_finish_beat",
            "finish_render_runtime_trace",
        )
        functions = runtime_helper_functions(*helper_names)

        class RendererHarness:
            def __init__(self) -> None:
                self.renderer = SimpleNamespace(time=0.0)

            def wait(self, duration: float, frozen_frame: bool = False) -> None:
                if not frozen_frame:
                    raise AssertionError("runtime marker waits must preserve the frame")
                self.renderer.time += float(duration)

        for name, function in functions.items():
            setattr(RendererHarness, name, function)

        contracts = stem_course.render_runtime_transition_contracts(self.animation_plan)
        semantic_bindings = stem_course.render_runtime_semantic_transition_bindings(self.animation_plan)
        schedule = stem_course.animation_plan_scene_schedule(self.short, self.animation_plan)
        bindings_by_beat: dict[str, list[str]] = {}
        for binding in semantic_bindings:
            bindings_by_beat.setdefault(binding["beat_id"], []).append(binding["planned_transition_id"])

        with tempfile.TemporaryDirectory(prefix="renderer-markers-") as tmp:
            marker_path = Path(tmp) / "execution.json"
            harness = RendererHarness()
            with mock.patch.dict(
                os.environ,
                {
                    stem_course.RENDER_EXECUTION_MARKER_ENV: str(marker_path),
                    "COURSE_SHORTS_RENDER_MODE": "production",
                },
            ):
                harness.initialize_render_runtime_trace(
                    1,
                    stem_course.animation_plan_fingerprint(self.animation_plan),
                    contracts,
                    semantic_bindings,
                )
                for binding in semantic_bindings:
                    harness.runtime_register_semantic_callbacks(
                        binding["planned_transition_id"],
                        [lambda _run_time: None],
                    )
                for beat in schedule:
                    harness.runtime_begin_beat(beat)
                    if not beat.get("animation_plan_beat_id"):
                        continue
                    contract = next(
                        item
                        for item in contracts
                        if item["beat_id"] == beat["animation_plan_beat_id"]
                    )
                    if contract["arc_phase"] == "transform" or contract.get("motion_evidence_required"):
                        transition_ids = bindings_by_beat.get(str(contract["beat_id"]), [None])
                        for transition_id in transition_ids:
                            token = harness.runtime_callback_started(transition_id, "executed_fixture_callback")
                            harness.renderer.time += 0.01
                            token["choreography_intervals"] = [{
                                "started_frame": token["started_frame"],
                                "finished_frame": harness.runtime_renderer_frame(),
                                "frame_count": max(1, harness.runtime_renderer_frame() - token["started_frame"]),
                                "animation_types": ["Transform"],
                                "persistent_carrier_ids": list(contract["persistent_object_ids"]),
                                "carrier_type": "displacement",
                                "semantic_before": dict(contract["observed_before"]),
                                "semantic_after": dict(contract["observed_after"]),
                                "qualifying_motion": True,
                            }]
                            harness.runtime_callback_finished(token)
                    harness.runtime_finish_beat(beat)
                harness.finish_render_runtime_trace()

            payload = json.loads(marker_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "complete")
            self.assertEqual(payload["timing_source"], "manim.renderer.time")
            self.assertEqual(
                stem_course.render_execution_marker_errors(payload, self.animation_plan, short_index=1),
                [],
            )


if __name__ == "__main__":
    unittest.main()

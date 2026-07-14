from __future__ import annotations

import ast
import math
import unittest

from tools import stem_course


def generated_helper_functions(*names: str) -> dict[str, object]:
    tree = ast.parse(stem_course.MANIM_SCENE_HELPERS)
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    namespace: dict[str, object] = {"math": math}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "semantic_helpers", "exec"), namespace)
    return {name: namespace[name] for name in names}


class SupplyDemandScenarioTests(unittest.TestCase):
    def short_and_semantics(self) -> tuple[dict[str, object], dict[str, object]]:
        concept = stem_course.source_term_concept(
            "Introduction and Supply & Demand", "economics"
        )
        short = stem_course.concept_to_short(concept, 1)
        return short, stem_course.econ_semantic_data(short, "econ_supply_demand")

    def test_model_scenario_drives_inverse_curves_marker_and_numeric_evidence(self) -> None:
        _short, values = self.short_and_semantics()

        self.assertEqual(
            values["numeric_setup"],
            {
                "price": 6.0,
                "demand_intercept": 100.0,
                "demand_slope": 8.0,
                "supply_intercept": 10.0,
                "supply_slope": 7.0,
            },
        )
        demand, supply = values["curves"]
        self.assertEqual(demand["equation"], "P=(100-Q)/8")
        self.assertEqual(supply["equation"], "P=(Q-10)/7")
        self.assertAlmostEqual(demand["intercept"], 12.5)
        self.assertAlmostEqual(demand["slope"], -0.125)
        self.assertAlmostEqual(supply["intercept"], -10.0 / 7.0)
        self.assertAlmostEqual(supply["slope"], 1.0 / 7.0)
        self.assertEqual(values["equilibria"], [{"quantity": 52.0, "price": 6.0}])
        self.assertEqual(values["quantity_demanded"], 52.0)
        self.assertEqual(values["quantity_supplied"], 52.0)
        self.assertEqual(values["market_gap"], 0.0)
        self.assertIn("P=(100-Q)/8", demand["label"])
        self.assertIn("P=(Q-10)/7", supply["label"])

    def test_generated_renderer_retains_consistent_final_resolution(self) -> None:
        short, _values = self.short_and_semantics()
        source = stem_course.manim_scene(
            short,
            "SupplyDemandLifecycleRegression",
            stem_course.build_animation_plan(short),
        )

        compile(source, "generated_supply_demand.py", "exec")
        self.assertIn("P=(100-Q)/8", source)
        self.assertIn("P=(Q-10)/7", source)
        self.assertIn("def resolve_market_takeaway(run_time):", source)
        self.assertIn("ReplacementTransform(result_formula, resolution_formula)", source)
        self.assertIn('"carrier_type": "causal_verification"', source)
        self.assertIn('"economics:final-equilibrium-resolution"', source)
        self.assertIn("build_actions=[build_market_hook]", source)
        self.assertIn("resolve_actions=[resolve_market_takeaway]", source)


class RequiredLifecycleBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        helpers = generated_helper_functions(
            "normalize_semantic_motion_metadata",
            "register_semantic_transition_actions",
        )
        self.register = helpers["register_semantic_transition_actions"]
        self.normalize = helpers["normalize_semantic_motion_metadata"]

    def scheduler(self) -> object:
        class Scheduler:
            pass

        scheduler = Scheduler()
        scheduler.normalize_semantic_motion_metadata = self.normalize.__get__(scheduler)
        scheduler._semantic_hold_index = 0
        scheduler._beat_schedule = [
            {
                "animation_plan_beat_id": "build-beat",
                "planned_arc_phase": "build",
                "visual_action_seconds": 1.0,
                "duration": 2.0,
                "semantic_transition_ids": [],
            },
            {
                "animation_plan_beat_id": "transform-beat",
                "planned_arc_phase": "transform",
                "visual_action_seconds": 1.0,
                "duration": 2.0,
                "semantic_transition_ids": ["step:transform"],
            },
            {
                "animation_plan_beat_id": "resolve-beat",
                "planned_arc_phase": "resolve",
                "visual_action_seconds": 1.0,
                "duration": 2.0,
                "semantic_transition_ids": [],
            },
        ]
        return scheduler

    def test_registration_rejects_every_empty_motion_required_lifecycle_phase(self) -> None:
        action = lambda _run_time: None
        cases = (
            ("build", None, {"step:transform": action}, [action]),
            ("transform", [action], {}, [action]),
            ("resolve", [action], {"step:transform": action}, None),
        )
        for phase, build_actions, groups, resolve_actions in cases:
            with self.subTest(phase=phase):
                scheduler = self.scheduler()
                if phase == "transform":
                    scheduler._beat_schedule[1]["semantic_transition_ids"] = []
                with self.assertRaisesRegex(
                    ValueError, "Motion-required " + phase + " beat has an empty"
                ):
                    self.register(
                        scheduler,
                        groups,
                        build_actions=build_actions,
                        resolve_actions=resolve_actions,
                    )
                self.assertFalse(hasattr(scheduler, "_concept_motion"))

    def test_registration_records_only_nonempty_required_batches(self) -> None:
        build = lambda _run_time: None
        transform = lambda _run_time: None
        resolve = lambda _run_time: None
        scheduler = self.scheduler()

        self.register(
            scheduler,
            {"step:transform": transform},
            build_actions=[build],
            resolve_actions=[resolve],
        )

        motion = scheduler._concept_motion
        self.assertEqual(motion["required_batch_indices"], [0, 1, 2])
        self.assertTrue(all(motion["action_batches"][index] for index in [0, 1, 2]))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from unittest import mock

from tools import stem_course
from tools.physics_model_scenarios import get_physics_model_scenario
from tools.video_physics_models import PHYSICS_SCENARIO_RENDER_ROUTES
from tools.video_physics_models import physics_scenario_render_route, resolve_physics_scenario_adapter


ROUTED_MODELS = (
    "kinematics_1d", "kinematics_2d", "projectile_motion", "rolling_kinematics",
    "force_balance", "newton_first_law", "newton_second_law",
    "action_reaction", "gravity_force", "contact_force", "tension_force",
    "spring_force", "pulley_constraint", "linear_drag", "quadratic_drag", "drag_force",
)


def visual_kind(model_id: str) -> str:
    return "physics_kinematics" if model_id in {
        "kinematics_1d", "kinematics_2d", "projectile_motion", "rolling_kinematics",
    } else "physics_force"


class PhysicsScenarioRendererRouteTests(unittest.TestCase):
    def test_public_adapter_aliases_resolve_without_expanding_canonical_registry(self) -> None:
        self.assertEqual(set(ROUTED_MODELS), set(PHYSICS_SCENARIO_RENDER_ROUTES))
        aliases = {
            "Newton's laws": "newton_laws_of_motion",
            "continuous mass transfer": "continuous_mass_accumulation",
            "normal force": "contact_force",
            "normal-and-friction contact forces": "contact_force",
            "vector_work_energy": "work_energy_multidimensional",
            "dot product work": "work_energy_multidimensional",
        }
        for alias, canonical_model_id in aliases.items():
            with self.subTest(alias=alias):
                self.assertEqual(resolve_physics_scenario_adapter(alias), canonical_model_id)
                route = physics_scenario_render_route(alias)
                self.assertNotIn("legacy", str(route).casefold())

    def test_unknown_adapter_alias_fails_closed(self) -> None:
        self.assertIsNone(resolve_physics_scenario_adapter("invented force adapter"))
        with self.assertRaisesRegex(ValueError, "no explicit scenario renderer route"):
            physics_scenario_render_route("invented force adapter")

    def test_every_planned_collision_model_has_a_nonfallback_adapter(self) -> None:
        self.assertEqual(set(ROUTED_MODELS), set(PHYSICS_SCENARIO_RENDER_ROUTES))
        for model_id in ROUTED_MODELS:
            with self.subTest(model_id=model_id):
                values = stem_course.physics_renderer_values_from_scenario(
                    visual_kind(model_id), get_physics_model_scenario(model_id).as_dict()
                )
                stem_course.validate_physics_renderer_values(visual_kind(model_id), values)
                expected_variant, expected_causal_mode = PHYSICS_SCENARIO_RENDER_ROUTES[model_id]
                self.assertEqual(values["renderer_variant"], expected_variant)
                self.assertEqual(values["causal_mode"], expected_causal_mode)
                self.assertNotIn("legacy", str(values).casefold())

    def test_known_collision_groups_have_distinct_structural_signatures(self) -> None:
        collision_group = (
            "contact_force", "spring_force", "linear_drag", "gravity_force",
            "pulley_constraint", "kinematics_1d", "kinematics_2d",
        )
        signatures: dict[str, tuple[object, ...]] = {}
        for model_id in collision_group:
            values = stem_course.physics_renderer_values_from_scenario(
                visual_kind(model_id), get_physics_model_scenario(model_id).as_dict()
            )
            signatures[model_id] = (
                values["renderer_variant"], values["causal_mode"], values["mode"],
                tuple(sorted(key for key in values if key not in {"renderer_variant", "causal_mode"})),
            )
        self.assertEqual(len(set(signatures.values())), len(collision_group), signatures)

    def test_resolved_contact_route_never_reenters_legacy_parser(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Normal and Friction Contact Forces", "physics"), 1
        )
        with mock.patch.object(
            stem_course, "_legacy_physics_semantic_data", side_effect=AssertionError("legacy fallback used")
        ):
            values = stem_course.physics_semantic_data(short, "physics_force")
        self.assertEqual(values["renderer_variant"], "contact_surface_components")

    def test_missing_explicit_adapter_fails_closed(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Normal and Friction Contact Forces", "physics"), 1
        )
        with mock.patch.object(
            stem_course, "physics_renderer_values_from_scenario", side_effect=ValueError("adapter missing")
        ), mock.patch.object(stem_course, "_legacy_physics_semantic_data") as legacy:
            with self.assertRaisesRegex(ValueError, "adapter missing"):
                stem_course.physics_semantic_data(short, "physics_force")
        legacy.assert_not_called()

    def test_dedicated_choreography_contains_each_physical_structure(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        required_fragments = {
            "contact_surface_components": "normal_arrow",
            "hooke_spring_deformation": "ParametricFunction",
            "linear_drag_velocity": "drag_arrow",
            "gravity_freefall": "ease_in_quad",
            "pulley_inextensible_rope": "string length fixed",
            "kinematics_1d": "acceleration_contribution",
            "kinematics_2d_components": "x_component",
            "projectile_components": "vx fixed; gravity changes vy",
        }
        for variant, fragment in required_fragments.items():
            with self.subTest(variant=variant):
                self.assertIn(fragment, source)

    def test_exact_variant_formulas_require_structured_math_without_ascii_fallback(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        formulas = (
            r'\vec{F}_c=N\hat{n}+f\hat{t}',
            r'F_s=-kx=',
            r'\vec{F}_g=m\vec{g}',
            r'\Delta\ell=0\qquad a_1=-a_2',
            r'\vec{T}=T\hat{\ell}',
            r'\vec{F}_{ext}=\Delta\vec{p}/\Delta t',
        )
        for formula in formulas:
            with self.subTest(formula=formula):
                self.assertIn(formula, source)
        exact_renderer = source[source.index("def play_physics_exact_force_model("):source.index("def play_physics_force_visual(")]
        self.assertEqual(exact_renderer.count("require_mathtex=True"), len(formulas))
        self.assertNotIn("physics_ascii_formula_fallback", exact_renderer)

    def test_contact_renderer_binds_visible_forces_to_substantial_motion(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index('if variant == "contact_surface_components":'):
            source.index('if variant == "hooke_spring_deformation":')
        ]
        for fragment in (
            'normal_label = always_redraw',
            'friction_label = always_redraw',
            'resultant_label = always_redraw',
            '"F c", font_size=50',
            'RIGHT * 3.25 * slide.get_value()',
            'self.configure_physics_motion(',
            '[load, slide]',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, renderer)
        self.assertNotIn('handoff="contact_geometry"', renderer)
        self.assertGreaterEqual(renderer.count("contact_states"), 2)

    def test_drag_renderer_animates_position_and_numeric_magnitudes(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index('if variant in {"linear_drag_velocity"'):
            source.index('if variant == "gravity_freefall":')
        ]
        self.assertIn('RIGHT * 3.8 * travel.get_value()', renderer)
        self.assertIn('lambda: speed * progress.get_value()', renderer)
        self.assertIn('lambda: drag * progress.get_value() ** power', renderer)
        self.assertIn('[progress, travel]', renderer)
        self.assertGreaterEqual(renderer.count("drag_states"), 2)

    def test_planar_kinematics_uses_continuous_path_and_position_guides(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        renderer = source[
            source.index("def play_physics_kinematics_visual("):
            source.index("def play_physics_kinematics_1d_visual(")
        ]
        self.assertIn("def sample_vector(samples):", renderer)
        self.assertIn("path_trace = always_redraw", renderer)
        self.assertIn("pointwise_become_partial", renderer)
        self.assertIn("component_area = always_redraw", renderer)
        self.assertIn("fill_opacity=0.14", renderer)
        self.assertIn("axes.c2p(0.0, current_point()[1])", renderer)
        self.assertIn("axes.c2p(current_point()[0], 0.0)", renderer)
        self.assertNotIn("def sample_index", renderer)

    def test_spring_and_kinematics_text_have_phone_readable_floors(self) -> None:
        source = stem_course.MANIM_SCENE_HELPERS
        spring = source[
            source.index('if variant == "hooke_spring_deformation":'):
            source.index('if variant in {"linear_drag_velocity"')
        ]
        one_d = source[
            source.index("def play_physics_kinematics_1d_visual("):
            source.index("def play_physics_vector_visual(")
        ]
        self.assertIn("font_size=62", spring)
        self.assertIn("min_height=0.7", spring)
        self.assertIn('self.physics_phone_text("x0", font_size=50', one_d)
        self.assertIn('font_size=44', one_d)
        self.assertIn(".arrange(DOWN, buff=0.12)", one_d)
        self.assertIn("current_time_band = always_redraw", one_d)


if __name__ == "__main__":
    unittest.main()

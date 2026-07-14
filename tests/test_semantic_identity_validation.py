from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.validate_course_run import (
    CourseRunValidator,
    semantic_identity_contract_errors,
    semantic_numeric_evidence_fingerprint,
    semantic_scene_contract_errors,
)


def semantic_fixture() -> tuple[dict[str, object], dict[str, object]]:
    scenario = {
        "model_id": "spring_response",
        "mode": "spring_response",
        "setup": {"k": 4.0, "x": 3.0},
        "calculation": {"F": 12.0},
        "result": {"F": 12.0},
        "required_example_tokens": ["spring", "displacement", "force"],
        "required_figure_tokens": ["spring", "force"],
        "animation_states": [
            {
                "state_id": "visible-result",
                "values": {"k": 4.0, "x": 3.0, "F": 12.0},
                "visible_evidence_tokens": ["spring", "force"],
            }
        ],
    }
    short: dict[str, object] = {
        "index": 7,
        "concept": "Spring response",
        "model_id": "spring_response",
        "scenario_mode": "spring_response",
        "semantic_mode": "spring_response",
        "route_key": "physics:spring_response",
        "formula": "F=kx",
        "worked_example": {
            "setup": "A spring has k=4 and displacement x=3.",
            "calculation": "The force is F=k*x=12.",
            "takeaway": "The spring force follows the displacement.",
        },
        "model_scenario": copy.deepcopy(scenario),
    }
    renderer_state = {
        "payload_type": "physics",
        "route_key": "physics:spring_response",
        "model_id": "spring_response",
        "scenario_mode": "spring_response",
        "semantic_mode": "spring_response",
        "canonical_formula": "F=kx",
        "equation_evidence": "F = k x",
        "model_scenario": copy.deepcopy(scenario),
        "required_example_tokens": ["spring", "displacement", "force"],
        "required_figure_tokens": ["spring", "force"],
        "animation_states": copy.deepcopy(scenario["animation_states"]),
    }
    transitions = []
    previous = "spring at rest"
    for index, state in enumerate(("stretch", "mark force", "calculate force", "verify result"), start=1):
        transitions.append(
            {
                "id": f"spring:{index}",
                "action": state,
                "persistent_object_ids": ["spring"],
                "before": {"spring": previous},
                "after": {"spring": state},
            }
        )
        previous = state
    artifact: dict[str, object] = {
        "semantic_support": {
            "status": "supported",
            "route_key": "physics:spring_response",
            "semantic_mode": "spring_response",
            "model_id": "spring_response",
            "mechanism_vocabulary": {
                "required_tokens": ["spring", "force"],
                "forbidden_cross_family_tokens": ["payoff matrix"],
            },
        },
        "concrete_example": {
            "setup": "Show the spring with k=4 and displacement x=3.",
            "calculation": "Use F = k x = 12.",
            "takeaway": "The spring force is 12.",
            "screen_values": ["4", "3", "12"],
            "renderer_state": renderer_state,
        },
        "beats": [
            {
                "text": "Spring displacement x = 3.",
                "cue_lines": ["Spring displacement x = 3."],
                "action": "Stretch the spring.",
            },
            {
                "text": "F = k x.",
                "cue_lines": ["F = k x."],
                "action": "Mark the force.",
            },
            {
                "text": "F = 4 x 3 = 12.",
                "cue_lines": ["F = 4 x 3 = 12."],
                "action": "Calculate the force.",
            },
            {
                "text": "The spring force is 12.",
                "cue_lines": ["The spring force is 12."],
                "action": "Verify the result.",
            },
        ],
        "semantic_transition_contract": {"transitions": transitions},
        "invariant": {"statement": "The same spring persists."},
        "reveal": {"statement": "F = 12."},
    }
    return short, artifact


def scene_source(short: dict[str, object], artifact: dict[str, object]) -> str:
    renderer = artifact["concrete_example"]["renderer_state"]  # type: ignore[index]
    return (
        "# generated_by: tools/stem_course.py; "
        "scene_metadata_version=2026-07-12-silent-visual-story-v5; "
        "route_key=physics:spring_response; visual_kind=physics_force; concept='Spring response'\n"
        f"visual_data = {{'physics': {renderer!r}}}\n"
        "class Fixture:\n"
        "    def construct(self):\n"
        f"        self._animation_plan = {artifact!r}\n"
    )


class SemanticIdentityValidationTests(unittest.TestCase):
    def test_passing_control_has_complete_cross_artifact_identity(self) -> None:
        short, artifact = semantic_fixture()

        self.assertEqual(semantic_identity_contract_errors(short, artifact), [])
        self.assertEqual(semantic_scene_contract_errors(short, artifact, scene_source(short, artifact)), [])

    def test_exact_model_route_and_mode_mismatches_fail_closed(self) -> None:
        short, artifact = semantic_fixture()
        renderer = artifact["concrete_example"]["renderer_state"]  # type: ignore[index]
        renderer["model_id"] = "different_model"  # type: ignore[index]
        renderer["route_key"] = "physics:different_route"  # type: ignore[index]
        renderer["semantic_mode"] = "different_mode"  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("exact model_id mismatch" in error for error in errors))
        self.assertTrue(any("exact route_key mismatch" in error for error in errors))
        self.assertTrue(any("exact semantic_mode mismatch" in error for error in errors))

    def test_physics_authored_values_must_match_scenario_and_visible_storyboard(self) -> None:
        short, artifact = semantic_fixture()
        short["worked_example"] = {
            "setup": "A cart has m=1 with pushes F=8 and drag d=3.",
            "calculation": "The net force is N=5.",
            "takeaway": "The result must use this scenario.",
        }

        errors = semantic_identity_contract_errors(short, artifact)

        numeric = " ".join(error for error in errors if "numeric evidence mismatch" in error)
        self.assertIn("'1'", numeric)
        self.assertIn("'8'", numeric)
        self.assertIn("'5'", numeric)
        self.assertTrue(any("named-variable mismatch" in error for error in errors))

    def test_declared_numeric_evidence_fingerprint_is_recomputed(self) -> None:
        short, artifact = semantic_fixture()
        expected = semantic_numeric_evidence_fingerprint(short["model_scenario"])  # type: ignore[arg-type]
        short["model_scenario"]["numeric_evidence_fingerprint"] = expected  # type: ignore[index]
        artifact["concrete_example"]["renderer_state"]["model_scenario"]["numeric_evidence_fingerprint"] = expected  # type: ignore[index]

        self.assertEqual(semantic_identity_contract_errors(short, artifact), [])

        artifact["concrete_example"]["renderer_state"]["model_scenario"]["numeric_evidence_fingerprint"] = "stale"  # type: ignore[index]
        errors = semantic_identity_contract_errors(short, artifact)
        self.assertTrue(any("numeric evidence fingerprint mismatch" in error for error in errors))

    def test_only_validated_derived_or_alternate_exemptions_are_accepted(self) -> None:
        short, artifact = semantic_fixture()
        short["worked_example"]["setup"] += " An alternate guide value is g=99."  # type: ignore[index]
        short["semantic_identity_exemptions"] = [
            {
                "kind": "numeric_value",
                "value": 99,
                "intent": "alternate",
                "reason": "A labeled alternate guide is intentionally non-scenario evidence.",
                "artifacts": ["model_scenario", "visible_storyboard"],
            },
            {
                "kind": "named_variable",
                "value": "g",
                "intent": "alternate",
                "reason": "The guide label is intentionally alternate evidence.",
                "artifacts": ["model_scenario", "visible_storyboard"],
            },
        ]

        self.assertEqual(semantic_identity_contract_errors(short, artifact), [])

        short["semantic_identity_exemptions"][0]["intent"] = "convenience"  # type: ignore[index]
        errors = semantic_identity_contract_errors(short, artifact)
        self.assertTrue(any("exemption 1 must declare" in error for error in errors))
        self.assertTrue(any("'99'" in error for error in errors))

    def test_oligopoly_cross_family_payoff_vocabulary_is_rejected(self) -> None:
        short, artifact = semantic_fixture()
        artifact["semantic_support"]["mechanism_vocabulary"] = {  # type: ignore[index]
            "required_tokens": ["spring", "force"],
            "forbidden_cross_family_tokens": ["high low", "payoff matrix"],
        }
        artifact["beats"][0]["text"] = "Use a High-Low payoff matrix."  # type: ignore[index]
        artifact["beats"][0]["cue_lines"] = ["Use a High-Low payoff matrix."]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("forbidden cross-family mechanism token 'high low'" in error for error in errors))
        self.assertTrue(any("forbidden cross-family mechanism token 'payoff matrix'" in error for error in errors))

    def test_algebra_route_rejects_declared_additive_group_mechanism(self) -> None:
        short, artifact = semantic_fixture()
        artifact["semantic_support"]["mechanism_vocabulary"] = {  # type: ignore[index]
            "required_tokens": ["Euclidean division"],
            "forbidden_cross_family_tokens": ["additive group"],
        }
        short["worked_example"]["setup"] += " Consider the Z11 additive group."  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("required token 'Euclidean division' is absent" in error for error in errors))
        self.assertTrue(any("forbidden cross-family mechanism token 'additive group'" in error for error in errors))

    def test_cs_formula_cue_truncation_raw_tex_and_symbol_loss_are_rejected(self) -> None:
        short, artifact = semantic_fixture()
        short["formula"] = r"T(n)=T(n/2)+n"
        renderer = artifact["concrete_example"]["renderer_state"]  # type: ignore[index]
        renderer.pop("canonical_formula")  # type: ignore[union-attr]
        renderer.pop("equation_evidence")  # type: ignore[union-attr]
        artifact["beats"][1]["text"] = r"T=\frac{"  # type: ignore[index]
        artifact["beats"][1]["cue_lines"] = [r"T=\frac{"]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("unbalanced delimiter" in error for error in errors))
        self.assertTrue(any("raw TeX fragments" in error for error in errors))
        self.assertTrue(any("truncated mid-operator or mid-token" in error for error in errors))
        self.assertTrue(any("core formula token structure is absent" in error for error in errors))

    def test_multiline_cues_join_articles_operators_and_brackets_before_completeness_checks(self) -> None:
        short, artifact = semantic_fixture()
        artifact["beats"][1]["text"] = "F = (k + x) / 2."  # type: ignore[index]
        artifact["beats"][1]["cue_lines"] = ["Use the", "average (k +", "x) /", "2."]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertFalse(any("beat 2" in error and ("truncated" in error or "delimiter" in error) for error in errors))

    def test_balanced_absolute_value_bars_are_not_treated_as_trailing_operators(self) -> None:
        short, artifact = semantic_fixture()
        short["formula"] = "|x|=3"
        artifact["concrete_example"]["renderer_state"]["canonical_formula"] = r"\lvert x\rvert=3"  # type: ignore[index]
        artifact["beats"][1]["text"] = "|x| = 3."  # type: ignore[index]
        artifact["beats"][1]["cue_lines"] = ["Distance is", "|x| = 3."]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertFalse(any("beat 2" in error and "truncated mid-operator" in error for error in errors))
        self.assertFalse(any("canonical formula mismatch" in error for error in errors))

    def test_unclosed_absolute_value_bar_still_fails_closed(self) -> None:
        short, artifact = semantic_fixture()
        artifact["beats"][1]["cue_lines"] = ["Distance |x + 2 is shown."]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("beat 2" in error and "unbalanced delimiter '|'" in error for error in errors))

    def test_set_builder_divisibility_and_presentation_bars_are_relations_not_delimiters(self) -> None:
        short, artifact = semantic_fixture()
        artifact["beats"][1]["cue_lines"] = [  # type: ignore[index]
            "a + H = {a + h | h in H}.",
            "D4 = <r, s | r^4 = s^2 = e>.",
            "n_p | |G| / p^a.",
        ]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertFalse(any("beat 2" in error and "delimiter '|'" in error for error in errors))
        self.assertFalse(any("beat 2" in error and "raw TeX" in error for error in errors))

    def test_visible_set_braces_are_not_raw_tex_but_tex_commands_still_are(self) -> None:
        short, artifact = semantic_fixture()
        artifact["beats"][1]["cue_lines"] = ["H = {e, a, b}.", r"Then show \\frac{a}{b}."]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        raw_tex = [error for error in errors if "beat 2" in error and "raw TeX" in error]
        self.assertEqual(len(raw_tex), 1)
        self.assertIn(r"\\frac", raw_tex[0])

    def test_unicode_and_tex_formula_presentations_have_the_same_structure(self) -> None:
        equivalents = (
            (r"\operatorname{pop}(\operatorname{push}(S,x))=(S,x)", "pop(push(S, x)) = (S, x)"),
            (r"a_0\leq a_1\leq\cdots\leq a_{n-1}", "a₀ ≤ a₁ ≤ … ≤ aₙ₋₁"),
            (r"parent(i)=\lfloor(i-1)/2\rfloor", "parent(i) = ⌊(i - 1) / 2⌋"),
            (r"d[v]\leftarrow\min(d[v],d[u]+w(u,v))", "d[v] arrow min(d[v], d[u] + w(u, v))"),
            (r"dp[i,w]=\max\{dp[i-1,w],v_i+dp[i-1,w-w_i]\}", "dp[i, w] = max dp[i - 1, w], vᵢ + dp[i - 1, w - wᵢ]"),
        )
        for tex, visible in equivalents:
            with self.subTest(tex=tex):
                short, artifact = semantic_fixture()
                short["formula"] = tex
                renderer = artifact["concrete_example"]["renderer_state"]  # type: ignore[index]
                renderer.pop("canonical_formula")  # type: ignore[union-attr]
                renderer.pop("equation_evidence")  # type: ignore[union-attr]
                artifact["beats"][1]["cue_lines"] = [visible]  # type: ignore[index]

                errors = semantic_identity_contract_errors(short, artifact)

                self.assertFalse(any("core formula token structure is absent" in error for error in errors), errors)

    def test_sentence_or_formula_ending_in_a_or_at_is_not_truncated(self) -> None:
        short, artifact = semantic_fixture()
        artifact["beats"][1]["cue_lines"] = ["Evaluate at", "Label the result a"]  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertFalse(any("beat 2" in error and "truncated after" in error for error in errors))

        artifact["beats"][1]["cue_lines"] = ["Continue with the"]  # type: ignore[index]
        errors = semantic_identity_contract_errors(short, artifact)
        self.assertTrue(any("beat 2" in error and "truncated after 'the'" in error for error in errors))

    def test_tex_prose_macro_contents_do_not_count_as_formula_symbols(self) -> None:
        short, artifact = semantic_fixture()
        short["formula"] = r"a=b,\quad\text{force explains x}"
        artifact["concrete_example"]["renderer_state"]["canonical_formula"] = "a=x"  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("canonical formula mismatch" in error for error in errors))

    def test_tex_fraction_and_plain_fraction_have_the_same_formula_structure(self) -> None:
        short, artifact = semantic_fixture()
        short["formula"] = r"T(n)=T(n/2)+n"
        artifact["concrete_example"]["renderer_state"]["canonical_formula"] = r"T(n)=T(\frac{n}{2})+n"  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertFalse(any("canonical formula mismatch" in error for error in errors))

    def test_group_theory_payload_without_numeric_capability_skips_numeric_fingerprints(self) -> None:
        short, artifact = semantic_fixture()
        group_scenario = {
            "model_id": "cosets",
            "mode": "cosets",
            "setup": "Take H in G and choose g.",
            "calculation": "Form the left coset gH.",
            "result": "The cosets partition G.",
        }
        short["model_scenario"] = copy.deepcopy(group_scenario)
        short["worked_example"] = {
            "setup": "Use Z12 and its subgroup H.",
            "calculation": "List 3 cosets.",
            "takeaway": "They partition the group.",
        }
        artifact["concrete_example"]["renderer_state"]["payload_type"] = "group_theory"  # type: ignore[index]
        artifact["concrete_example"]["renderer_state"]["model_scenario"] = copy.deepcopy(group_scenario)  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertFalse(any("numeric evidence" in error for error in errors))

    def test_explicit_route_key_is_authoritative_over_internal_semantic_route_alias(self) -> None:
        short, artifact = semantic_fixture()
        short["semantic_route"] = "internal:spring_renderer"

        self.assertEqual(semantic_identity_contract_errors(short, artifact), [])

    def test_explicit_public_and_exact_route_keys_form_a_legitimate_alias(self) -> None:
        short, artifact = semantic_fixture()
        renderer = artifact["concrete_example"]["renderer_state"]  # type: ignore[index]
        short["route_key"] = "physics:internal:spring_response"
        renderer["exact_route_key"] = "physics:internal:spring_response"  # type: ignore[index]

        self.assertEqual(semantic_identity_contract_errors(short, artifact), [])

    def test_real_formula_route_numeric_and_transition_drift_remain_fail_closed(self) -> None:
        short, artifact = semantic_fixture()
        short["formula"] = "F=ma"
        artifact["concrete_example"]["renderer_state"]["route_key"] = "physics:other"  # type: ignore[index]
        artifact["concrete_example"]["renderer_state"]["model_scenario"]["result"]["F"] = 13.0  # type: ignore[index]
        artifact["semantic_transition_contract"]["transitions"][0]["after"] = {}  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("canonical formula mismatch" in error for error in errors))
        self.assertTrue(any("exact route_key mismatch" in error for error in errors))
        self.assertTrue(any("numeric evidence fingerprint mismatch" in error or "model_scenario mismatch" in error for error in errors))
        self.assertTrue(any("lacks complete changed before/after" in error for error in errors))

    def test_required_example_and_figure_tokens_use_separate_evidence(self) -> None:
        short, artifact = semantic_fixture()
        renderer = artifact["concrete_example"]["renderer_state"]  # type: ignore[index]
        renderer["required_example_tokens"] = ["diagram-only"]  # type: ignore[index]
        renderer["required_figure_tokens"] = ["prose-only"]  # type: ignore[index]
        renderer["animation_states"][0]["visible_evidence_tokens"].append("diagram-only")  # type: ignore[index]
        short["worked_example"]["setup"] += " prose-only"  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("missing required example token 'diagram-only'" in error for error in errors))
        self.assertTrue(any("missing required figure token 'prose-only'" in error for error in errors))

    def test_supported_plan_requires_four_complete_causal_transitions(self) -> None:
        short, artifact = semantic_fixture()
        artifact["semantic_transition_contract"]["transitions"] = artifact["semantic_transition_contract"]["transitions"][:3]  # type: ignore[index]
        artifact["semantic_transition_contract"]["transitions"][0]["after"] = {}  # type: ignore[index]

        errors = semantic_identity_contract_errors(short, artifact)

        self.assertTrue(any("has 3 causal transitions" in error for error in errors))
        self.assertTrue(any("lacks complete changed before/after snapshots" in error for error in errors))

    def test_validated_route_contract_can_prove_equivalent_typed_transitions(self) -> None:
        short, artifact = semantic_fixture()
        transitions = artifact.pop("semantic_transition_contract")["transitions"]  # type: ignore[index]
        artifact["semantic_support"]["validated_route_contract"] = {  # type: ignore[index]
            "validated": True,
            "route_key": "physics:spring_response",
            "equivalent_typed_transitions": transitions,
        }

        self.assertEqual(semantic_identity_contract_errors(short, artifact), [])

    def test_scene_runtime_contract_mismatch_names_course_short_and_artifacts(self) -> None:
        short, artifact = semantic_fixture()
        source = scene_source(short, artifact).replace("'model_id': 'spring_response'", "'model_id': 'wrong'", 1)
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / "short_07.py"
            scene.write_text(source, encoding="utf-8")
            validator = CourseRunValidator(Path(folder))
            validator.course_title = "Fixture course"
            with mock.patch(
                "tools.validate_course_run.stem_course_contract.infer_visual_kind",
                return_value="physics_force",
            ):
                with mock.patch(
                    "tools.validate_course_run.stem_course_contract.animation_route_descriptor",
                    return_value={
                        "route_key": "physics:spring_response",
                        "semantic_mode": "spring_response",
                        "supported": True,
                    },
                ):
                    validator.validate_exact_scene_route(
                        short,
                        scene,
                        "physics_force",
                        artifact,
                        {"visual_kind": "physics_force", "route_key": "physics:spring_response"},
                    )

        messages = "\n".join(issue.message for issue in validator.issues)
        self.assertIn("Course 'Fixture course'", messages)
        self.assertIn("short 7 ('Spring response')", messages)
        self.assertIn("short_plan.json ↔ animation plan ↔", messages)
        self.assertIn("exact model_id mismatch", messages)


if __name__ == "__main__":
    unittest.main()

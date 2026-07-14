from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import re
import unittest

from tools import course_notes_models
from tools.course_notes_models import (
    build_model_note_payload,
    visible_note_word_count,
)
from tools.economics_model_scenarios import build_economics_model_scenario
from tools.economics_model_specs import ECONOMICS_MODEL_REGISTRY
from tools.physics_model_scenarios import build_physics_model_scenario
from tools.physics_model_specs import PHYSICS_MODEL_REGISTRY


PHYSICS_PINNED_ALIASES = {
    "Kinematics in One Dimension": "kinematics_1d",
    "Two-Dimensional Kinematics": "kinematics_2d",
    "Projectile Motion": "projectile_motion",
    "Rolling Kinematics": "rolling_kinematics",
    "Newton's First Law": "newton_first_law",
    "Newton's Second Law": "newton_second_law",
    "Newton's Laws of Motion": "newton_laws",
    "Newton's Third Law and Action-Reaction": "action_reaction",
    "Gravity": "gravity_force",
    "Normal and Friction Contact Forces": "contact_force",
    "Tension in a Rope": "tension_force",
    "Hooke's Law for a Spring": "spring_force",
    "Ideal Pulley Constraints": "pulley_constraint",
    "Linear Drag": "linear_drag",
    "Quadratic Drag": "quadratic_drag",
    "Drag Force": "drag_force",
    "Net Force": "force_balance",
    "Linear Momentum": "momentum_definition",
    "Impulse-Momentum Theorem": "impulse_momentum",
    "Conservation of Momentum": "momentum_conservation",
    "Elastic Collisions": "elastic_collision",
    "Inelastic Collisions": "inelastic_collision",
    "Perfectly Inelastic Collision": "perfectly_inelastic_collision",
    "Collision Mechanics": "collision_momentum",
    "Mechanical Work": "work_definition",
    "Kinetic Energy and Work": "work_energy_theorem",
    "Gravitational Potential Energy": "gravitational_potential_energy",
    "Spring Potential Energy": "spring_potential_energy",
    "Conservation of Energy": "energy_conservation",
    "Potential Energy": "potential_energy",
    "Potential Energy Diagrams": "potential_energy_diagram",
    "Circular Motion Position": "circular_position",
    "Uniform Circular Motion": "uniform_circular_motion",
    "Circular Motion Acceleration": "radial_acceleration",
    "Circular Motion Dynamics": "circular_dynamics",
    "Rigid Body Motion": "rigid_body_motion",
    "Motion of a Rigid Body": "rigid_body_motion",
    "Moment of Inertia": "moment_of_inertia",
    "Torque": "torque",
    "Rotational Dynamics": "rotational_dynamics",
    "Angular Momentum of a Point Particle": "point_particle_angular_momentum",
    "Angular Momentum of a Rigid Body": "rigid_body_angular_momentum",
    "Torque and Angular Impulse": "angular_impulse",
    "Rolling Dynamics": "rolling_dynamics",
    "Rolling Kinetic Energy": "rolling_kinetic_energy",
    "Rolling Angular Momentum": "rolling_angular_momentum",
    "Continuous Mass Transfer": "continuous_mass_transfer",
    "Rocket Equation": "rocket_equation",
    "Center of Mass": "center_of_mass",
    "Relative Velocity": "relative_velocity",
    "Relative Velocity and Recoil": "recoil",
    "Ordinary Differential Equation": "ordinary_differential_equation",
    "Unit Vector": "unit_vector",
    "Vector Components": "vectors",
    "Traveling Waves": "waves",
    "Rigid Body\N{EN DASH}Motion": "rigid_body_motion",
    "Lesson 28\N{EM DASH}Motion of a Rigid Body": "rigid_body_motion",
}


ECONOMICS_PINNED_ALIASES = {
    "Budget Constraints and Constrained Choice": "consumer_choice",
    "Production Theory": "production_function",
    "Competition I": "perfect_competition",
    "Competition II": "competitive_shutdown",
    "Welfare Economics": "welfare_surplus",
    "Input Markets I": "labor_input_market",
    "Input Markets I\N{EM DASH}Labor Market": "labor_input_market",
    "Input Markets II": "factor_input_markets",
    "Input Markets II\N{EN DASH}Labor and Capital": "factor_input_markets",
    "Making Choices over Time": "intertemporal_choice",
    "Introduction to Trade": "international_trade",
    "Government Redistribution and Taxation": "tax_incidence",
    "Lec 7: Competition I": "perfect_competition",
    "Lecture VII: Competition II": "competitive_shutdown",
    "Lecture Summary 15: Input Markets I\N{EM DASH}Labor Market": "labor_input_market",
    "Lesson XVI: Input Markets II\N{EN DASH}Labor and Capital": "factor_input_markets",
    "Budget Constraints": "budget_constraint",
    "Taxes and deadweight loss": "tax_deadweight_loss",
    "Efficiency and Equity": "equity_efficiency",
}


def learner_text(payload: dict[str, object]) -> str:
    fields = [
        str(payload.get(key, ""))
        for key in (
            "canonical_formula",
            "course_framing",
            "definition",
            "development_title",
            "development",
            "figure_caption",
            "figure_discussion",
        )
    ]
    for result in payload.get("results", []):
        if isinstance(result, dict):
            fields.extend(str(result.get(key, "")) for key in ("name", "statement"))
    fields.extend(str(value) for value in payload.get("properties", []))
    for example in payload.get("examples", []):
        if isinstance(example, dict):
            fields.extend(
                str(example.get(key, ""))
                for key in ("title", "setup", "calculation", "takeaway")
            )
    for symbol in payload.get("symbols", []):
        if isinstance(symbol, dict):
            fields.extend(str(symbol.get(key, "")) for key in ("symbol", "meaning"))
    return " ".join(value for value in fields if value.strip())


def normalized_topic_words(model_id: str, payload: dict[str, object]) -> list[str]:
    text = learner_text(payload).lower()
    text = re.sub(r"\\[A-Za-z]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    title = model_id.replace("_", " ")
    text = re.sub(rf"\b{re.escape(title)}\b", " topic ", text)
    text = re.sub(r"\b\d+(?:\s+\d+)*\b", " number ", text)
    return re.sub(r"\s+", " ", text).strip().split()


class CourseNotesModelTests(unittest.TestCase):
    def test_gyroscope_notes_cover_precession_with_two_worked_cases(self):
        payload = build_model_note_payload("Gyroscopes", "physics")
        self.assertIn(r"\Omega_p=\frac{\tau}{L}", payload["canonical_formula"])
        self.assertIn("precession", str(payload["definition"]).casefold())
        self.assertGreaterEqual(len(payload["examples"]), 2)
        self.assertTrue(all(
            len(" ".join(str(example.get(field, "")) for field in (
                "setup", "calculation", "takeaway", "extension"
            )).split()) >= 18
            for example in payload["examples"][:2]
        ))

    @classmethod
    def setUpClass(cls) -> None:
        cls.payloads: dict[tuple[str, str], dict[str, object]] = {}
        for model_id in PHYSICS_MODEL_REGISTRY:
            cls.payloads[("physics", model_id)] = build_model_note_payload(
                model_id, "physics"
            )
        for model_id in ECONOMICS_MODEL_REGISTRY:
            cls.payloads[("economics", model_id)] = build_model_note_payload(
                model_id, "economics"
            )

    def test_every_pinned_official_alias_resolves_exactly(self) -> None:
        for title, expected in PHYSICS_PINNED_ALIASES.items():
            with self.subTest(domain="physics", title=title):
                payload = build_model_note_payload(title, "physics")
                self.assertEqual(payload["model_id"], expected)

        for title, expected in ECONOMICS_PINNED_ALIASES.items():
            with self.subTest(domain="economics", title=title):
                payload = build_model_note_payload(title, "economics")
                self.assertEqual(payload["model_id"], expected)

    def test_unknown_topics_and_domains_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported physics notes topic"):
            build_model_note_payload("Thermodynamic Partition Function", "physics")
        with self.assertRaisesRegex(ValueError, "Unsupported economics notes topic"):
            build_model_note_payload("A topic outside the registry", "economics")
        with self.assertRaisesRegex(ValueError, "Unsupported notes domain"):
            build_model_note_payload("Projectile Motion", "chemistry")
        with self.assertRaisesRegex(ValueError, "must not be blank"):
            build_model_note_payload("  ", "physics")
        with self.assertRaises(TypeError):
            build_model_note_payload(None, "physics")  # type: ignore[arg-type]

    def test_payload_shape_is_rich_and_uses_no_invented_theorem_names(self) -> None:
        for (domain, model_id), payload in self.payloads.items():
            with self.subTest(domain=domain, model_id=model_id):
                self.assertTrue(payload["definition"])
                self.assertGreaterEqual(len(payload["results"]), 3)
                self.assertTrue(payload["development_title"])
                self.assertTrue(payload["development"])
                self.assertGreaterEqual(len(payload["properties"]), 5)
                self.assertEqual(
                    {example["kind"] for example in payload["examples"]},
                    {"worked", "boundary"},
                )
                self.assertTrue(payload["figure"])
                self.assertTrue(payload["figure_caption"])
                self.assertTrue(payload["figure_discussion"])
                self.assertEqual(
                    payload["content_basis"], "source-derived-domain-scaffold"
                )
                self.assertIs(payload["trusted_tex"], True)
                names = " ".join(result["name"] for result in payload["results"])
                self.assertNotRegex(names.lower(), r"\b(lemma|proposition)\b")
                if "theorem" in names.lower():
                    self.assertIn("theorem", model_id)

    def test_formula_symbols_and_default_scenario_are_exact(self) -> None:
        registries = {
            "physics": PHYSICS_MODEL_REGISTRY,
            "economics": ECONOMICS_MODEL_REGISTRY,
        }
        for (domain, model_id), payload in self.payloads.items():
            with self.subTest(domain=domain, model_id=model_id):
                spec = registries[domain][model_id]
                expected_symbols = [row.as_dict() for row in spec.exact_symbol_rows]
                self.assertEqual(payload["canonical_formula"], spec.canonical_formula)
                self.assertEqual(payload["symbols"], expected_symbols)
                if domain == "physics":
                    scenario = build_physics_model_scenario(model_id)
                    expected_result = scenario.result.as_dict()
                    expected_calculation = scenario.calculation.as_dict()
                else:
                    scenario = build_economics_model_scenario(model_id)
                    expected_result = dict(scenario.results)
                    expected_calculation = dict(scenario.calculation)
                self.assertEqual(payload["model_scenario"], scenario.as_dict())
                self.assertEqual(payload["numeric_evidence"]["result"], expected_result)
                self.assertEqual(
                    payload["numeric_evidence"]["calculation"], expected_calculation
                )

    def test_prerequisites_are_metadata_not_learner_assumptions(self) -> None:
        payload = build_model_note_payload("Producer Surplus", "economics")
        spec = ECONOMICS_MODEL_REGISTRY["producer_surplus"]

        self.assertEqual(payload["prerequisites"], list(spec.prerequisites))
        self.assertEqual(
            payload["learner_assumptions"], list(spec.learner_assumptions)
        )
        self.assertNotEqual(
            tuple(payload["prerequisites"]), tuple(payload["learner_assumptions"])
        )
        self.assertNotIn("integration or areas", payload["definition"].lower())
        self.assertIn(r"[P^*-P_S(q)]\,dq", payload["canonical_formula"])

    def test_generic_sections_have_distinct_numeric_roles(self) -> None:
        payload = build_model_note_payload("Market Equilibrium", "economics")
        consequence = next(
            row for row in payload["results"] if row["id"].endswith("-consequence")
        )["statement"]
        claims = set(re.findall(r"\\\([^)]*?=[^)]*?\\\)", consequence))
        self.assertTrue(claims)

        non_result_text = " ".join(
            [
                payload["development"],
                payload["figure_discussion"],
                *payload["properties"],
                *(
                    example[field]
                    for example in payload["examples"]
                    for field in ("calculation", "takeaway")
                ),
            ]
        )
        for claim in claims:
            self.assertNotIn(claim, non_result_text)
        self.assertNotRegex(payload["figure_discussion"], r"\\\([^)]*=\d")

    def test_boundary_examples_are_recomputed_not_mutated_prose(self) -> None:
        for (domain, model_id), payload in self.payloads.items():
            with self.subTest(domain=domain, model_id=model_id):
                evidence = payload["numeric_evidence"]
                self.assertNotEqual(evidence["setup"], evidence["comparison_setup"])
                self.assertNotEqual(evidence["result"], evidence["comparison_result"])
                if domain == "physics":
                    rebuilt = build_physics_model_scenario(
                        model_id, evidence["comparison_setup"]
                    )
                else:
                    rebuilt = build_economics_model_scenario(
                        model_id, evidence["comparison_setup"]
                    )
                self.assertEqual(
                    payload["comparison_model_scenario"], rebuilt.as_dict()
                )

    def test_source_context_digests_include_only_model_matched_evidence(self) -> None:
        contexts = (
            "Market equilibrium compares quantity demanded with quantity supplied at the clearing price.",
            "A distinctive blue-umbrella anecdote should never be copied into the study notes.",
        )
        payload = build_model_note_payload(
            "Market Equilibrium", "microeconomics", contexts
        )
        self.assertEqual(payload["course_framing"], "")
        self.assertNotIn("blue-umbrella anecdote", learner_text(payload).lower())
        self.assertEqual(len(payload["source_evidence_digests"]), 1)
        normalized = re.sub(r"[^a-z0-9]+", " ", contexts[0].lower()).strip()
        expected_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        self.assertEqual(
            payload["source_evidence_digests"][0]["sha256"], expected_digest
        )
        self.assertTrue(
            payload["source_evidence_digests"][0]["matched_model_terms"]
        )
        self.assertNotIn("sources", payload)
        self.assertNotIn("citations", payload)

    def test_visible_word_count_ignores_machine_metadata(self) -> None:
        payload = build_model_note_payload("Projectile Motion", "mechanics")
        baseline = visible_note_word_count(payload)
        noisy = deepcopy(payload)
        noise = "metadata only " * 2000
        noisy["model_id"] = noise
        noisy["model_scenario"] = {"internal_contract": noise}
        noisy["comparison_model_scenario"] = {"renderer_state": noise}
        noisy["numeric_evidence"] = {"debug_trace": noise}
        noisy["source_evidence_digests"] = [{"sha256": noise}]
        noisy["content_basis"] = noise
        self.assertEqual(visible_note_word_count(noisy), baseline)

        noisy["definition"] += " Learners compare one additional visible outcome."
        self.assertGreater(visible_note_word_count(noisy), baseline)
        with self.assertRaises(TypeError):
            visible_note_word_count([])  # type: ignore[arg-type]

    def test_every_registered_model_has_substantive_visible_volume(self) -> None:
        counts = {
            key: visible_note_word_count(payload)
            for key, payload in self.payloads.items()
        }
        self.assertEqual(
            len(counts), len(PHYSICS_MODEL_REGISTRY) + len(ECONOMICS_MODEL_REGISTRY)
        )
        self.assertGreaterEqual(min(counts.values()), 550)

    def test_learner_text_rejects_generator_and_qa_language(self) -> None:
        banned = (
            "registered",
            "calculator",
            "fidelity",
            "evidence token",
            "claim terminates",
            "inferred from the lecture heading",
            "state diagram",
            "model vocabulary",
            "recomputed under the",
        )
        for (domain, model_id), payload in self.payloads.items():
            text = learner_text(payload).lower()
            with self.subTest(domain=domain, model_id=model_id):
                for phrase in banned:
                    self.assertNotIn(phrase, text)

    def test_motion_of_a_rigid_body_reads_as_mechanics_notes(self) -> None:
        payload = build_model_note_payload("Motion of a Rigid Body", "physics")
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn("distance between every pair of material points remains fixed", lowered)
        self.assertIn("translation and rotation", lowered)
        self.assertIn(r"\vec v_P=\vec v_O+\vec\omega\times\vec r_{P/O}", text)
        self.assertIn("right-hand rule", lowered)
        self.assertIn("units of angular speed times length", lowered)
        self.assertIn("head-to-tail addition", lowered)
        self.assertNotIn("material point velocity moves", lowered)
        self.assertNotIn("cannot serve as a premise", lowered)

    def test_constrained_choice_reads_as_microeconomics_notes(self) -> None:
        payload = build_model_note_payload(
            "Budget Constraints and Constrained Choice", "economics"
        )
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn("most preferred affordable bundle", lowered)
        self.assertIn(r"p_xx+p_yy\leq I", text)
        self.assertIn(r"x^*=\alpha I/p_x", text)
        self.assertIn("budget line", lowered)
        self.assertIn("indifference curve", lowered)
        self.assertIn("positive choice result", lowered)
        self.assertIn("does not compare welfare across consumers", lowered)
        self.assertIn("outward in parallel", lowered)
        self.assertNotIn("income from 100 to 0", lowered)
        self.assertNotIn("direct scenario evaluation", lowered)

    def test_comparison_contract_names_only_actual_changes(self) -> None:
        for (domain, model_id), payload in self.payloads.items():
            contract = payload["comparison_contract"]
            before = contract["before"]
            after = contract["after"]
            actual_changed = [
                key for key in before if key in after and before[key] != after[key]
            ]
            actual_invariants = [
                key for key in before if key in after and before[key] == after[key]
            ]
            comparison_result = next(
                result
                for result in payload["results"]
                if result["id"].endswith("-comparison")
            )
            boundary = next(
                example
                for example in payload["examples"]
                if example["kind"] == "boundary"
            )
            comparison_text = " ".join(
                (
                    comparison_result["statement"],
                    boundary["calculation"],
                    boundary["takeaway"],
                    payload["figure_discussion"],
                )
            )

            with self.subTest(domain=domain, model_id=model_id):
                self.assertTrue(actual_changed)
                self.assertEqual(contract["changed_outputs"], actual_changed)
                self.assertEqual(contract["invariant_outputs"], actual_invariants)
                self.assertEqual(
                    contract["described_changed_outputs"], actual_changed
                )
                self.assertIn(contract["focus_output"], actual_changed)
                focus_name = course_notes_models._quantity_name(
                    contract["focus_output"]
                )
                self.assertIn(focus_name, comparison_text)
                for key in contract["described_changed_outputs"]:
                    self.assertNotEqual(before[key], after[key])
                for key in contract["described_invariant_outputs"]:
                    self.assertEqual(before[key], after[key])
                    name = course_notes_models._quantity_name(key)
                    self.assertNotIn(f"changes {name}", comparison_text)
                    self.assertNotIn(f"change in {name}", comparison_text)

    def test_symbol_definition_grammar_agrees_for_every_model(self) -> None:
        def is_plural(symbol: str) -> bool:
            depth = 0
            for character in symbol:
                if character in "([{":
                    depth += 1
                elif character in ")]}":
                    depth = max(0, depth - 1)
                elif character == "," and depth == 0:
                    return True
            return False

        registries = {
            "physics": PHYSICS_MODEL_REGISTRY,
            "economics": ECONOMICS_MODEL_REGISTRY,
        }
        for (domain, model_id), payload in self.payloads.items():
            definition = payload["definition"]
            for row in registries[domain][model_id].exact_symbol_rows[:4]:
                verb = "denote" if is_plural(row.symbol) else "denotes"
                with self.subTest(
                    domain=domain, model_id=model_id, symbol=row.symbol
                ):
                    self.assertIn(rf"\({row.symbol}\) {verb}", definition)

    def test_generic_residues_and_inapplicable_force_language_are_absent(self) -> None:
        banned = (
            "individual objective",
            "objective or equilibrium condition",
            "direction, sign, or reference value",
            "solving the conditions for",
            "intermediate quantities are",
        )
        registries = {
            "physics": PHYSICS_MODEL_REGISTRY,
            "economics": ECONOMICS_MODEL_REGISTRY,
        }
        for (domain, model_id), payload in self.payloads.items():
            text = learner_text(payload).lower()
            with self.subTest(domain=domain, model_id=model_id):
                for phrase in banned:
                    self.assertNotIn(phrase, text)
                spec = registries[domain][model_id]
                if spec.visual_kind not in {"physics_force", "physics_rotation"}:
                    self.assertNotIn("forces or torques", text)

    def test_sampled_profiles_do_not_inherit_neighboring_topic_rules(self) -> None:
        action_text = learner_text(
            build_model_note_payload(
                "Newton's Third Law and Action-Reaction", "physics"
            )
        ).lower()
        self.assertIn("separate free-body diagrams", action_text)
        self.assertIn("do not cancel in either body's force sum", action_text)
        self.assertNotIn("individual objective", action_text)

        utility_text = learner_text(
            build_model_note_payload("Utility Representation", "economics")
        ).lower()
        self.assertIn("utility labels preserve only order", utility_text)
        self.assertIn("same preferences", utility_text)
        self.assertIn(r"\(u(x,y)=\sqrt{xy}\)", utility_text)
        self.assertNotIn("expenditure in currency", utility_text)
        self.assertNotIn("conditional on preferences, income, prices", utility_text)

        inertia_text = learner_text(
            build_model_note_payload("Moment of Inertia", "physics")
        ).lower()
        self.assertIn("mass times length squared", inertia_text)
        self.assertIn("moment of inertia is nonnegative", inertia_text)
        self.assertIn("distance enters as", inertia_text)
        self.assertNotIn("every torque and angular momentum", inertia_text)
        self.assertNotIn("angular and translational readouts", inertia_text)

        rolling_text = learner_text(
            build_model_note_payload("Rolling Kinematics", "physics")
        ).lower()
        self.assertIn("no-slip contact", rolling_text)
        self.assertIn("kinematic constraint", rolling_text)
        self.assertIn("instantaneous contact point", rolling_text)
        self.assertNotIn(
            "every lever arm, angular velocity, torque, and angular momentum",
            rolling_text,
        )
        self.assertNotIn("perpendicular distances", rolling_text)

    def test_fallback_budget_labor_and_comparison_language_is_semantic(self) -> None:
        budget = learner_text(
            build_model_note_payload("Budget Constraints", "economics")
        ).lower()
        self.assertIn("affordability requires expenditure no greater than income", budget)
        self.assertIn("marked candidate only as affordable or unaffordable", budget)
        self.assertNotIn("any preference ranking needed", budget)
        self.assertNotIn("utility only in the ordinal representation", budget)

        labor = learner_text(
            build_model_note_payload("labor_market", "economics")
        )
        self.assertIn(r"L_d=a_d-b_dw", labor)
        self.assertIn(r"L_s=a_s+b_sw", labor)
        self.assertIn(r"L_d(w^*)=L_s(w^*)", labor)
        self.assertNotIn("strategy profile", labor.lower())

        bad_agreement = re.compile(
            r"\b(?:masses|components|elements|inputs|velocities)\s+changes\b"
        )
        for (domain, model_id), payload in self.payloads.items():
            with self.subTest(domain=domain, model_id=model_id):
                self.assertNotRegex(learner_text(payload).lower(), bad_agreement)

    def test_policy_and_elasticity_comparisons_change_the_teaching_primitive(self) -> None:
        ceiling = build_model_note_payload("Price Ceiling Shortage", "economics")
        ceiling_text = learner_text(ceiling).lower()
        self.assertEqual(ceiling["comparison_contract"]["changed_input"], "ceiling_price")
        self.assertEqual(ceiling["comparison_contract"]["focus_output"], "shortage")
        self.assertIn("horizontal distance between them is the shortage", ceiling_text)
        self.assertIn("rationing rule", ceiling_text)
        self.assertNotIn("structure of a policy wedge", ceiling_text)
        self.assertNotIn("locate the common price-quantity point", ceiling_text)

        elasticity = build_model_note_payload("Own Price Elasticity", "economics")
        elasticity_text = learner_text(elasticity)
        contract = elasticity["comparison_contract"]
        self.assertEqual(contract["changed_input"], "new_price")
        self.assertEqual(contract["focus_output"], "own_price_elasticity")
        self.assertNotEqual(
            contract["before"]["own_price_elasticity"],
            contract["after"]["own_price_elasticity"],
        )
        self.assertIn(r"\%\Delta Q_d=(Q_1-Q_0)/Q_0", elasticity_text)
        self.assertIn(r"\%\Delta P=(P_1-P_0)/P_0", elasticity_text)

    def test_continuous_mass_transfer_uses_control_volume_momentum_flux(self) -> None:
        payload = build_model_note_payload("Continuous Mass Transfer", "physics")
        text = learner_text(payload)
        lowered = text.lower()
        contract = payload["comparison_contract"]

        self.assertEqual(contract["focus_output"], "external_force")
        self.assertIn("fixed control volume", lowered)
        self.assertIn(
            r"F_{\mathrm{ext}}=\dot m(v_{\mathrm{out}}-v_{\mathrm{in}})",
            text,
        )
        self.assertIn(r"\dot m v_{\mathrm{in}}=7.5", text)
        self.assertIn(r"\dot m v_{\mathrm{out}}=22.5", text)
        self.assertIn(r"F_{\mathrm{ext}}=2.5(9-3)=15", text)
        self.assertIn("dimensions of force", lowered)
        self.assertIn("inlet arrow", lowered)
        self.assertIn("outlet arrow", lowered)
        self.assertIn("system boundary", lowered)
        for contamination in (
            "rocket",
            "exhaust speed",
            "mass ratio",
            "propellant",
            "logarithmically",
        ):
            self.assertNotIn(contamination, lowered)

    def test_production_function_derives_cobb_douglas_mechanism(self) -> None:
        payload = build_model_note_payload("Production Theory", "economics")
        text = learner_text(payload)
        lowered = text.lower()

        self.assertIn(r"q=A L^\alpha K^{1-\alpha}", text)
        self.assertIn(r"MP_L=\alpha q/L", text)
        self.assertIn(r"MP_K=(1-\alpha)q/K", text)
        self.assertIn(r"\(q=24\)", text)
        self.assertIn(r"\(MP_L=1.33333\)", text)
        self.assertIn(r"\(MP_K=0.75\)", text)
        self.assertIn("constant returns to scale", lowered)
        self.assertIn("marginal-product tangent", lowered)
        self.assertIn("isoquant", lowered)
        self.assertIn("fixing \\(k=16\\)", lowered)
        self.assertNotIn("price, cost, or benefit", lowered)
        self.assertNotIn("associated price, cost", lowered)

    def test_welfare_surplus_derives_integral_and_surplus_regions(self) -> None:
        payload = build_model_note_payload("Welfare Economics", "economics")
        text = learner_text(payload)
        lowered = text.lower()

        self.assertIn(r"MB(Q)=100-2Q", text)
        self.assertIn(r"MC(Q)=10+Q", text)
        self.assertIn(r"\(Q^*=30\)", text)
        self.assertIn(r"\(P^*=40\)", text)
        self.assertIn(r"\(CS=900\)", text)
        self.assertIn(r"\(PS=450\)", text)
        self.assertIn(r"\(TS=1350\)", text)
        self.assertIn(r"\int_0^{30}[90-3q]\,dq=1350", text)
        self.assertIn("above \\(p^*\\) and below \\(mb\\)", lowered)
        self.assertIn("below \\(p^*\\) and above \\(mc\\)", lowered)
        self.assertIn("shifts the demand/benefit schedule upward", lowered)
        self.assertIn(r"\(TS=2204.17\)", text)
        self.assertIn("does not by itself settle distributional or equity", lowered)

    def test_registry_wide_vocabulary_compatibility(self) -> None:
        rules = (
            (
                ("rocket", "exhaust speed", "mass ratio", "propellant", "vehicle mass"),
                {"rocket_equation"},
            ),
            (
                ("fixed control volume", "momentum flux", "inlet arrow", "outlet arrow"),
                {"continuous_mass_transfer"},
            ),
            (
                ("cobb-douglas production", "isoquant"),
                {"production_function", "factor_input_markets"},
            ),
            (
                ("world price", "world-price line", "import gap"),
                {"international_trade", "tariff"},
            ),
            (
                ("payoff matrix", "mutual best-response"),
                {"oligopoly", "oligopoly_collusion", "strategic_game", "nash_equilibrium", "dominant_strategy"},
            ),
            (
                ("turning point", "allowed/forbidden"),
                {"potential_energy_diagram"},
            ),
            (
                ("phase speed", "equal-phase"),
                {"waves"},
            ),
        )
        for (_domain, model_id), payload in self.payloads.items():
            text = learner_text(payload).lower()
            with self.subTest(model_id=model_id):
                for phrases, allowed_models in rules:
                    if model_id in allowed_models:
                        continue
                    for phrase in phrases:
                        self.assertNotIn(phrase, text)
                self.assertNotIn("price, cost, or benefit", text)
                self.assertNotIn("associated price, cost, benefit, or payoff", text)

    def test_registry_wide_template_fragments_are_absent(self) -> None:
        banned_fragments = (
            "start from ",
            "the relation has the structure of ",
            "to examine parameter dependence",
            "the numerical point or annotation corresponds to",
            "price, cost, or benefit",
        )
        prevalence = Counter()
        for (_domain, _model_id), payload in self.payloads.items():
            text = learner_text(payload).lower()
            for fragment in banned_fragments:
                if fragment in text:
                    prevalence[fragment] += 1
        for fragment in banned_fragments:
            with self.subTest(fragment=fragment):
                self.assertEqual(prevalence[fragment], 0)

    def test_generic_notes_use_content_specific_scan_structure(self) -> None:
        samples = (
            ("Newton's Second Law", "physics", "Dynamical Law", "System and interactions"),
            ("Conservation of Momentum", "physics", "Conservation Law", "System boundary"),
            ("Market Equilibrium", "economics", "Equilibrium Condition", "Joint conditions"),
            ("Budget Constraints", "economics", "Budget Constraint", "Feasible set"),
        )
        titles = set()
        kinds = set()
        for topic, domain, relation_heading, stage_heading in samples:
            payload = build_model_note_payload(topic, domain)
            with self.subTest(topic=topic):
                self.assertEqual(payload["results"][0]["name"], relation_heading)
                self.assertIn(rf"\textbf{{{relation_heading}.}}", payload["definition"])
                self.assertIn(rf"\textbf{{{stage_heading}.}}", payload["development"])
                self.assertIn(r"\textbf{Interpretation.}", payload["development"])
                self.assertNotIn(r"\n", payload["development"])
                self.assertNotIn("The governing relation is", payload["definition"])
                self.assertNotIn("Worked analysis and interpretation", payload["development_title"])
            titles.add(payload["development_title"])
            kinds.add(payload["development_kind"])
        self.assertEqual(len(titles), len(samples))
        self.assertEqual(len(kinds), len(samples))

    def test_comparison_headings_match_the_model_operation(self) -> None:
        expected = {
            ("Conservation of Momentum", "physics"): "Boundary-preserving change",
            ("Ordinary Differential Equation", "physics"): "Initial-data sensitivity",
            ("Market Equilibrium", "economics"): "Equilibrium shift",
            ("Price Ceiling Shortage", "economics"): "Policy response",
        }
        for (topic, domain), heading in expected.items():
            payload = build_model_note_payload(topic, domain)
            comparison = next(
                row for row in payload["results"] if row["id"].endswith("-comparison")
            )
            with self.subTest(topic=topic):
                self.assertEqual(comparison["name"], heading)

    def test_rocket_equation_uses_mass_flow_momentum_reasoning(self) -> None:
        payload = build_model_note_payload("Rocket Equation", "physics")
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn(r"m\,dv=-v_e\,dm", text)
        self.assertIn(r"\ln(m_i/m_f)", text)
        self.assertIn("mass ratio is dimensionless", lowered)
        self.assertIn(r"m_i=m_f", text)
        self.assertIn("logarithmically", lowered)
        self.assertNotIn("declared rotation origin", lowered)
        self.assertNotIn("forces or torques", lowered)
        self.assertNotIn("torque", lowered)

    def test_potential_diagram_uses_energy_intersections_and_axis_origin(self) -> None:
        payload = build_model_note_payload("Potential Energy Diagrams", "physics")
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn(r"K(x)=E-U(x)", text)
        self.assertIn(r"U(x_t)=E", text)
        self.assertIn("curvature controls steepness, not the coordinate convention", lowered)
        self.assertIn("turning points move inward", lowered)
        self.assertIn("sampled allowed/forbidden pattern remains unchanged", lowered)
        self.assertNotIn("coordinates fixed by", lowered)

    def test_traveling_wave_comparison_focuses_displacement_and_invariants(self) -> None:
        payload = build_model_note_payload("Traveling Waves", "physics")
        text = learner_text(payload)
        lowered = text.lower()
        contract = payload["comparison_contract"]
        self.assertEqual(contract["focus_output"], "displacement")
        self.assertIn(r"\(y(x,t)\) denotes", payload["definition"])
        self.assertIn("equivalent canonical cosine phase", lowered)
        self.assertIn(r"\phi_c=\phi_s-\pi/2", text)
        self.assertNotIn(r"\Delta x", text)
        self.assertIn("amplitude only rescales the vertical displacement", lowered)
        self.assertIn("wave speed", lowered)
        self.assertIn("period", lowered)
        self.assertIn("remain unchanged", lowered)
        self.assertNotIn("read the change in \\(v_w\\) against \\(a\\)", lowered)

    def test_tax_incidence_derives_elasticity_shares(self) -> None:
        payload = build_model_note_payload(
            "Tax incidence and the tax wedge", "economics"
        )
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn(r"\varepsilon_s/(|\varepsilon_d|+\varepsilon_s)", text)
        self.assertIn(r"|\varepsilon_d|/(|\varepsilon_d|+\varepsilon_s)", text)
        self.assertIn("less elastic side", lowered)
        self.assertIn(r"P_b-P_s", text)
        self.assertIn("statutory remittance does not determine", lowered)

    def test_nash_equilibrium_marks_two_mutual_best_responses(self) -> None:
        payload = build_model_note_payload(
            "Nash equilibrium in an oligopoly game", "economics"
        )
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn("compares", lowered)
        self.assertIn(r"u_R(A,A)", text)
        self.assertIn(r"u_C(B,B)", text)
        self.assertIn(r"\((A,A)\) and \((B,B)\)", text)
        self.assertIn("two pure-strategy nash equilibria", lowered)
        self.assertIn("sum of payoffs", lowered)
        self.assertIn("not the criterion defining nash equilibrium", lowered)

    def test_trade_uses_world_price_quantities_and_horizontal_gap(self) -> None:
        payload = build_model_note_payload("Introduction to Trade", "economics")
        text = learner_text(payload)
        lowered = text.lower()
        self.assertIn(r"Q_d(P_w)", text)
        self.assertIn(r"Q_s(P_w)", text)
        self.assertIn(r"M=Q_d(P_w)-Q_s(P_w)", text)
        self.assertIn("horizontal gap", lowered)
        self.assertIn("autarky intersection is a benchmark", lowered)
        self.assertIn("not the open-economy allocation mechanism", lowered)
        self.assertIn("world-price line", lowered)

    def test_generation_is_deterministic(self) -> None:
        first = build_model_note_payload(
            "Government Redistribution and Taxation",
            "economics",
            ("Tax incidence separates the buyer price from the seller price.",),
        )
        second = build_model_note_payload(
            "Government Redistribution and Taxation",
            "economics",
            ("Tax incidence separates the buyer price from the seller price.",),
        )
        self.assertEqual(first, second)

    def test_symbolic_figure_tokens_are_emitted_in_math_mode(self) -> None:
        payload = build_model_note_payload("Competition I", "economics")
        text = learner_text(payload)
        self.assertIn(r"\(q^*\)", text)
        self.assertNotIn("pairs MC with q^*.", text)

    def test_cross_model_sentence_and_ten_gram_repetition_stays_low(self) -> None:
        rows = [
            (domain, model_id, payload)
            for (domain, model_id), payload in self.payloads.items()
        ]
        sentence_counts: Counter[str] = Counter()
        for _domain, model_id, payload in rows:
            topic_sentences: set[str] = set()
            title = model_id.replace("_", " ")
            for raw in re.split(r"(?<=[.!?])\s+|\n+", learner_text(payload)):
                normalized = re.sub(r"\\[A-Za-z]+", " ", raw.lower())
                normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
                normalized = re.sub(
                    rf"\b{re.escape(title)}\b", " topic ", normalized
                )
                normalized = re.sub(
                    r"\b\d+(?:\s+\d+)*\b", " number ", normalized
                )
                normalized = re.sub(r"\s+", " ", normalized).strip()
                if len(normalized.split()) >= 8:
                    topic_sentences.add(normalized)
            sentence_counts.update(topic_sentences)

        repeated_instances = sum(
            count for count in sentence_counts.values() if count > 1
        )
        sentence_total = sum(sentence_counts.values())
        self.assertLess(repeated_instances / sentence_total, 0.25)
        self.assertLessEqual(max(sentence_counts.values()) / len(rows), 0.20)

        for domain in ("physics", "economics", "combined"):
            selected = rows if domain == "combined" else [row for row in rows if row[0] == domain]
            owners: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
            topic_grams: dict[str, set[tuple[str, ...]]] = {}
            for _row_domain, model_id, payload in selected:
                words = normalized_topic_words(model_id, payload)
                grams = {
                    tuple(words[start : start + 10])
                    for start in range(max(0, len(words) - 9))
                }
                topic_grams[model_id] = grams
                for gram in grams:
                    owners[gram].add(model_id)
            total_windows = sum(len(grams) for grams in topic_grams.values())
            repeated_windows = sum(
                1
                for model_id, grams in topic_grams.items()
                for gram in grams
                if len(owners[gram]) > 1 and model_id in owners[gram]
            )
            with self.subTest(domain=domain):
                self.assertLess(repeated_windows / total_windows, 0.25)


if __name__ == "__main__":
    unittest.main()

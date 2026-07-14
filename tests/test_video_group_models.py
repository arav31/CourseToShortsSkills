from __future__ import annotations

import json
import unittest
from copy import deepcopy

from tools.video_group_models import (
    GROUP_VIDEO_ROUTES,
    MIT_18_703_CALENDAR_TITLES,
    build_all_group_video_payloads,
    build_group_video_payload,
    resolve_group_video_model,
    validate_finite_map_render_geometry,
    validate_group_video_payload,
)


EXPECTED_TITLES = (
    "Groups",
    "Subgroups",
    "Cosets",
    "Cyclic Groups",
    "Permutation Groups",
    "Conjugation in S_n",
    "Isomorphisms",
    "Homomorphisms and Kernels",
    "Quotient Groups",
    "Isomorphism Theorems",
    "Alternating Groups",
    "Presentations and Groups of Small Order",
    "Sylow Theorems and Applications",
    "Rings",
    "Basic Properties of Rings",
    "Ring Homomorphisms and Ideals",
    "Field of Fractions",
    "Prime and Maximal Ideals",
    "Special Domains",
    "Euclidean Domains",
    "Polynomial Rings",
    "A Quick Primality Test",
    "Group Actions and Automorphisms",
    "Review",
)


class ExactTitleRoutingTests(unittest.TestCase):
    def test_all_24_calendar_titles_resolve_exactly_in_order(self) -> None:
        self.assertEqual(MIT_18_703_CALENDAR_TITLES, EXPECTED_TITLES)
        self.assertEqual(tuple(route.title for route in GROUP_VIDEO_ROUTES), EXPECTED_TITLES)
        self.assertEqual(len(GROUP_VIDEO_ROUTES), 24)

        route_keys = set()
        for title in EXPECTED_TITLES:
            with self.subTest(title=title):
                route = resolve_group_video_model(title)
                self.assertIsNotNone(route)
                self.assertEqual(route.title, title)
                self.assertTrue(route.route_key)
                self.assertTrue(route.visual_family)
                self.assertTrue(route.canonical_formula)
                route_keys.add(route.route_key)
        self.assertEqual(len(route_keys), 24)

    def test_resolver_fails_closed_without_fuzzy_or_generic_fallbacks(self) -> None:
        for unsupported in (
            "groups",
            " Groups ",
            "Group Structure",
            "Special Domain",
            "Quick Primality Test",
            "A topic outside the calendar",
        ):
            with self.subTest(title=unsupported):
                with self.assertRaisesRegex(ValueError, "Unsupported MIT 18.703 video title"):
                    resolve_group_video_model(unsupported)
                self.assertIsNone(resolve_group_video_model(unsupported, fail_closed=False))

        with self.assertRaises(TypeError):
            resolve_group_video_model(None)  # type: ignore[arg-type]


class GroupPayloadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payloads = build_all_group_video_payloads()

    def test_every_payload_has_exact_worked_content_and_validation(self) -> None:
        self.assertEqual(tuple(self.payloads), EXPECTED_TITLES)
        for title, payload in self.payloads.items():
            with self.subTest(title=title):
                route = resolve_group_video_model(title)
                self.assertEqual(payload["payload_type"], "group_theory")
                self.assertEqual(payload["title"], title)
                self.assertEqual(payload["exact_title"], title)
                self.assertEqual(payload["route_key"], route.route_key)
                self.assertEqual(payload["visual_family"], route.visual_family)
                self.assertEqual(payload["family"], route.visual_family)
                self.assertEqual(payload["visual_kind"], route.visual_family)
                self.assertEqual(payload["canonical_formula"], route.canonical_formula)
                self.assertTrue(payload["invariant"])
                self.assertTrue(payload["reveal"])
                self.assertEqual(payload["question"], payload["worked_example"]["question"])
                self.assertEqual(payload["answer"], payload["worked_example"]["answer"])
                for key in ("setup", "calculation", "takeaway", "question", "answer"):
                    self.assertTrue(payload["worked_example"][key])
                self.assertTrue(payload["validation"]["valid"])
                self.assertTrue(all(payload["validation"].values()))
                self.assertEqual(validate_group_video_payload(payload), [])
                json.dumps(payload, ensure_ascii=False, allow_nan=False)

    def test_every_transition_carries_complete_continuous_snapshots(self) -> None:
        for title, payload in self.payloads.items():
            with self.subTest(title=title):
                objects = payload["objects"]
                object_ids = {row["id"] for row in objects}
                self.assertGreaterEqual(len(object_ids), 4)
                self.assertEqual(objects, payload["persistent_objects"])
                self.assertTrue(all(row["persistent"] is True for row in objects))

                transitions = payload["transitions"]
                self.assertGreaterEqual(len(transitions), 4)
                self.assertEqual(
                    payload["reveal_contract"]["sequence"],
                    [transition["reveal"] for transition in transitions],
                )
                self.assertEqual(
                    payload["reveal_contract"]["final_state"],
                    transitions[-1]["after"],
                )
                for index, transition in enumerate(transitions):
                    self.assertEqual(set(transition["persistent_object_ids"]), object_ids)
                    self.assertEqual(set(transition["before"]), object_ids)
                    self.assertEqual(set(transition["after"]), object_ids)
                    self.assertNotEqual(transition["before"], transition["after"])
                    actual_changed = {
                        object_id
                        for object_id in object_ids
                        if transition["before"][object_id] != transition["after"][object_id]
                    }
                    self.assertEqual(set(transition["changed_object_ids"]), actual_changed)
                    self.assertTrue(transition["claim"])
                    self.assertTrue(transition["action"])
                    self.assertTrue(transition["reveal"])
                    if index:
                        self.assertEqual(transitions[index - 1]["after"], transition["before"])

    def test_required_group_calculations_are_exact_and_topic_specific(self) -> None:
        checks = {
            "Groups": ("r r^2=e", "four group axioms"),
            "Subgroups": ("x-y=2a-2b=2(a-b)", "2Z<=Z"),
            "Cosets": ("0+H=3Z", "partition Z"),
            "Cyclic Groups": ("6[1]=[0]", "reaches every residue"),
            "Permutation Groups": ("sigma tau=(23)", "right-to-left"),
            "Conjugation in S_n": ("tau(123)tau^{-1}=(132)", "cycle type preserved"),
            "Isomorphisms": ("phi(r^3r^2)", "square rotations with Z/4Z"),
            "Homomorphisms and Kernels": ("ker(phi)={[0],[2],[4],[6]}", "surjective image Z/2Z"),
            "Quotient Groups": ("((12)N)^2", "Normality"),
            "Isomorphism Theorems": ("ker(phi)=3Z", "first isomorphism"),
            "Alternating Groups": ("ker(sgn)=A3", "homomorphism kernel"),
            "Presentations and Groups of Small Order": ("srs=r^{-1}", "|D4|=8"),
            "Sylow Theorems and Applications": ("n5|3", "n5=1"),
            "Group Actions and Automorphisms": ("8=4*2", "c_s(r)=srs^{-1}=r^{-1}"),
            "Review": ("ker(phi)={[0],[4],[8]}", "Map -> kernel/image"),
        }
        for title, fragments in checks.items():
            with self.subTest(title=title):
                payload = self.payloads[title]
                semantic_text = " ".join(
                    (
                        payload["worked_example"]["setup"],
                        payload["worked_example"]["calculation"],
                        payload["worked_example"]["takeaway"],
                        payload["reveal"],
                        payload["canonical_formula"],
                    )
                )
                for fragment in fragments:
                    self.assertIn(fragment, semantic_text)

    def test_homomorphism_render_geometry_is_the_exact_total_parity_map(self) -> None:
        geometry = self.payloads["Homomorphisms and Kernels"]["render_geometry"]

        self.assertEqual(geometry["kind"], "finite_map")
        self.assertEqual(
            [element["label"] for element in geometry["domain"]],
            [f"[{index}]_8" for index in range(8)],
        )
        self.assertEqual(
            [element["label"] for element in geometry["codomain"]],
            ["[0]_2", "[1]_2"],
        )
        self.assertEqual(geometry["mapping"], [0, 1, 0, 1, 0, 1, 0, 1])
        self.assertEqual(geometry["identity_target"], 0)
        self.assertEqual(geometry["kernel_indices"], [0, 2, 4, 6])
        self.assertEqual(geometry["image_indices"], [0, 1])
        self.assertEqual(validate_finite_map_render_geometry(geometry), [])

        element_ids = [
            element["id"]
            for side in (geometry["domain"], geometry["codomain"])
            for element in side
        ]
        self.assertEqual(len(element_ids), len(set(element_ids)))

    def test_finite_map_geometry_validator_rejects_malformed_variants(self) -> None:
        geometry = self.payloads["Homomorphisms and Kernels"]["render_geometry"]
        mutations = {
            "duplicate element id": lambda row: row["codomain"][0].update(
                id=row["domain"][0]["id"]
            ),
            "partial mapping": lambda row: row["mapping"].pop(),
            "out of range target": lambda row: row["mapping"].__setitem__(0, 2),
            "wrong identity": lambda row: row.update(identity_target=2),
            "wrong kernel": lambda row: row.update(kernel_indices=[0, 2]),
            "wrong image": lambda row: row.update(image_indices=[0]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                malformed = deepcopy(geometry)
                mutate(malformed)
                self.assertTrue(validate_finite_map_render_geometry(malformed))

                payload = deepcopy(self.payloads["Homomorphisms and Kernels"])
                payload["render_geometry"] = malformed
                self.assertTrue(validate_group_video_payload(payload))

    def test_ring_and_domain_units_have_legitimate_non_group_families(self) -> None:
        algebra_titles = EXPECTED_TITLES[13:22]
        expected_domains = {
            "Rings": "ring_laws_ideals",
            "Basic Properties of Rings": "ring_laws_ideals",
            "Ring Homomorphisms and Ideals": "ring_laws_ideals",
            "Field of Fractions": "domain_factorization",
            "Prime and Maximal Ideals": "ring_laws_ideals",
            "Special Domains": "domain_factorization",
            "Euclidean Domains": "domain_factorization",
            "Polynomial Rings": "domain_factorization",
            "A Quick Primality Test": "algorithmic_algebra",
        }
        self.assertEqual(set(algebra_titles), set(expected_domains))
        for title, family in expected_domains.items():
            with self.subTest(title=title):
                payload = self.payloads[title]
                self.assertEqual(payload["topic_domain"], "ring_theory")
                self.assertEqual(payload["visual_family"], family)
                self.assertNotEqual(payload["visual_family"], "group_structure")

        semantic_text = {
            title: " ".join(
                (
                    self.payloads[title]["canonical_formula"],
                    self.payloads[title]["worked_example"]["calculation"],
                    self.payloads[title]["reveal"],
                )
            )
            for title in expected_domains
        }
        self.assertIn("distributivity", semantic_text["Rings"].casefold())
        self.assertIn("ker(f)=6Z", semantic_text["Ring Homomorphisms and Ideals"])
        self.assertIn("15/18=5/6", semantic_text["Field of Fractions"])
        self.assertIn("maximal and prime", semantic_text["Prime and Maximal Ideals"])
        self.assertIn(r"\mathrm{ED}\Longrightarrow\mathrm{PID}\Longrightarrow\mathrm{UFD}", semantic_text["Special Domains"])
        self.assertIn("gcd(252,105)=21", semantic_text["Euclidean Domains"])
        self.assertIn("x^2+x+1", semantic_text["Polynomial Rings"])
        self.assertIn("perfect power", semantic_text["A Quick Primality Test"])
        self.assertIn("ord_29(31)=ord_29(2)=28", semantic_text["A Quick Primality Test"])
        self.assertIn("X^29-1", json.dumps(self.payloads["A Quick Primality Test"]))

    def test_builder_ignores_unrelated_worked_example_override(self) -> None:
        unrelated = {
            "setup": "Add residues modulo 7.",
            "calculation": "[2]+[3]=[5].",
            "takeaway": "A generic modular-addition example.",
        }
        payload = build_group_video_payload("Euclidean Domains", unrelated)
        self.assertIn("252=2*105+42", payload["worked_example"]["calculation"])
        self.assertNotIn("[2]+[3]", json.dumps(payload))

    def test_validator_rejects_semantic_substitution_and_broken_continuity(self) -> None:
        substituted = deepcopy(self.payloads["Polynomial Rings"])
        substituted["visual_family"] = "group_structure"
        self.assertTrue(
            any("visual_family" in error for error in validate_group_video_payload(substituted))
        )

        discontinuous = deepcopy(self.payloads["Subgroups"])
        transitions = discontinuous["transitions"]
        object_id = transitions[1]["persistent_object_ids"][0]
        transitions[1]["before"][object_id] = "detached replacement object"
        errors = validate_group_video_payload(discontinuous)
        self.assertTrue(any("causal" in error or "exact-title" in error for error in errors))

        incomplete = deepcopy(self.payloads["Cosets"])
        del incomplete["transitions"][0]["after"][incomplete["subject_id"]]
        self.assertTrue(
            any("complete before/after" in error for error in validate_group_video_payload(incomplete))
        )


if __name__ == "__main__":
    unittest.main()

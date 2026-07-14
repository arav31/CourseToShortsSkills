from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import stem_course


def mit_18_703_source_pack() -> dict[str, object]:
    calendar = list(stem_course.MIT_18_703_CALENDAR_ORDER)
    materials: list[dict[str, str]] = [
        {"kind": "page", "title": "Course landing page", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/", "text": "Modern Algebra. " + "; ".join(calendar)},
        {"kind": "page", "title": "Lecture Notes", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/pages/lecture-notes/", "text": "Lecture Notes. " + "; ".join(calendar[:23])},
        {"kind": "page", "title": "Readings", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/pages/readings/", "text": "Readings for groups, rings, ideals, domains, and polynomial rings."},
        {"kind": "page", "title": "Syllabus", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/pages/syllabus/", "text": "Syllabus: groups, quotient groups, rings, ideals, and group actions."},
        {"kind": "page", "title": "Calendar", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/pages/calendar/", "text": "Calendar: " + "; ".join(calendar)},
        {"kind": "page", "title": "Assignments", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/pages/assignments/", "text": "Homework 1 through Homework 11."},
        {"kind": "page", "title": "Related Resources", "url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/pages/related-resources/", "text": "Related Resources."},
    ]
    for lecture, title in enumerate(calendar[:23], start=1):
        materials.append({
            "kind": "page",
            "title": f"Mit18_703S13_Pra_L_{lecture}",
            "url": f"https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/resources/mit18_703s13_pra_l_{lecture}/",
            "text": f"18.703 Modern Algebra, {title}.",
        })
    for homework in range(1, 12):
        materials.append({
            "kind": "page",
            "title": f"Mit18_703S13_H{homework}",
            "url": f"https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/resources/mit18_703s13_h{homework}/",
            "text": f"18.703 Modern Algebra, Homework {homework}.",
        })
    for lecture, title in enumerate(calendar[:23], start=1):
        extension_terms = [
            stem_course.MIT_18_703_EXTENSION_SOURCE_TERMS[extension["title"]]
            for extension in stem_course.MIT_18_703_LECTURE_EXTENSIONS.get(lecture, [])
        ]
        materials.append({
            "kind": "pdf",
            "title": f"MIT18_703S13_pra_l_{lecture}.pdf",
            "url": f"https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/MIT18_703S13_pra_l_{lecture}.pdf",
            "text": f"{lecture}. {title}. Definition {lecture}.1 and Theorem {lecture}.2 with proof and examples. " + " ".join(extension_terms),
        })
    for homework in range(1, 12):
        materials.append({
            "kind": "pdf",
            "title": f"MIT18_703S13_h{homework}.pdf",
            "url": f"https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/MIT18_703S13_h{homework}.pdf",
            "text": f"HOMEWORK #{homework}: course exercises grounded in the corresponding unit.",
        })
    assert len(materials) == 75
    return {
        "title": "Modern Algebra",
        "source_url": "https://ocw.mit.edu/courses/18-703-modern-algebra-spring-2013/",
        "materials": materials,
    }


class NotesDepthContractTests(unittest.TestCase):
    def test_curated_domain_membership_does_not_bypass_source_grounding(self) -> None:
        concept = next(concept for concept in stem_course.GROUP_THEORY if concept.name == "Galois groups")
        short = stem_course.concept_to_short(concept, 1)
        pack = {
            "title": "Introductory Groups",
            "source_url": "https://example.test/groups",
            "materials": [{"kind": "pdf", "title": "Groups", "text": "Groups, subgroups, cosets, and homomorphisms."}],
        }

        ledger = stem_course.notes_coverage_ledger([short], pack)

        self.assertEqual(ledger["status"], "failed")
        self.assertEqual(ledger["topics"][0]["content_basis"], "curated-domain")
        self.assertFalse(ledger["topics"][0]["source_grounding"]["matched"])
        self.assertFalse(ledger["topics"][0]["checks"]["grounded"])
        self.assertIn("grounded", ledger["topics"][0]["missing"])

    def test_mit_calendar_and_all_75_materials_are_authoritative(self) -> None:
        pack = mit_18_703_source_pack()
        shorts = stem_course.full_note_shorts(pack, {"course_title": "Modern Algebra", "shorts": []})

        ledger = stem_course.notes_coverage_ledger(shorts, pack)

        self.assertEqual(ledger["status"], "ok")
        self.assertEqual(ledger["topic_count"], 24)
        self.assertEqual(ledger["calendar_order_actual"], list(stem_course.MIT_18_703_CALENDAR_ORDER))
        self.assertTrue(ledger["calendar_sequence_ok"])
        self.assertTrue(ledger["lecture_sequence_ok"])
        self.assertEqual(ledger["source_material_count"], 75)
        self.assertEqual(ledger["reviewed_material_count"], 75)
        self.assertEqual(ledger["substantive_material_count"], 34)
        self.assertEqual(ledger["substantive_material_covered_count"], 34)
        self.assertEqual(ledger["uncovered_material_count"], 0)
        self.assertEqual(ledger["required_course_result_count"], 21)
        self.assertEqual(ledger["covered_course_result_count"], 21)
        self.assertEqual(ledger["missing_course_result_count"], 0)
        self.assertTrue(all(topic["checks"]["grounded"] for topic in ledger["topics"]))
        rendered_topics = " ".join(topic["concept"] for topic in ledger["topics"])
        self.assertNotIn("Galois", rendered_topics)
        self.assertNotIn("Solvable", rendered_topics)

    def test_unsupported_topic_still_fails_without_source_grounding(self) -> None:
        concept = stem_course.Concept(
            "Unspecified spectral gadget",
            "A vague hook.",
            "A vague intuition.",
            "x=y",
            ["unknown prerequisite"],
            "Do not guess.",
            "Choose an object.",
            "Perform a check.",
            "Observe the result.",
            "What happens?",
            "Something happens.",
            "numeric_rule",
        )
        short = stem_course.concept_to_short(concept, 1)
        pack = {"title": "Unknown Course", "materials": [{"kind": "page", "title": "Home", "text": "No substantive notes."}]}

        ledger = stem_course.notes_coverage_ledger([short], pack)

        self.assertEqual(ledger["status"], "failed")
        self.assertIn("grounded", ledger["topics"][0]["missing"])
        self.assertEqual(ledger["topics"][0]["source_grounding"]["matched"], False)

    def test_authoritative_economics_resolution_cannot_be_rescued_by_an_excerpt(self) -> None:
        topics = [
            "Supply and Demand Equilibrium",
            "Elasticity",
            "Consumer Choice",
            "Externalities",
            "Monopoly",
            "Production Theory",
            "Labor Market",
            "Quantum Barter Topology",
        ]
        calendar = " ".join(
            f"Lecture {index}: {topic}" for index, topic in enumerate(topics, start=1)
        )
        pack = {
            "title": "Microeconomics",
            "materials": [{
                "kind": "page",
                "title": "Course calendar",
                "text": calendar + "\n" + "Quantum Barter Topology is discussed in this economics course. " * 20,
            }],
        }

        shorts = stem_course.full_note_shorts(pack, {"course_title": "Microeconomics", "shorts": []})
        unsupported = next(short for short in shorts if short["concept"] == "Quantum Barter Topology")
        ledger = stem_course.notes_coverage_ledger(shorts, pack)
        row = next(topic for topic in ledger["topics"] if topic["concept"] == "Quantum Barter Topology")

        self.assertTrue(unsupported.get("source_evidence"))
        self.assertEqual(unsupported["notes_resolution_status"], "failed")
        self.assertEqual(row["status"], "failed")
        self.assertFalse(row["checks"]["outline_topic_resolved"])
        self.assertFalse(row["quality_contract"]["topic_model_supported"])

    def test_placeholder_diagnostics_and_generic_symbols_fail_coverage(self) -> None:
        short = stem_course.concept_to_short(stem_course.GROUP_THEORY[0], 1)
        payload = json.loads(json.dumps(stem_course.GROUP_THEORY_NOTE_DEPTH["groups and operations"]))
        payload["development"] += " Publication remains blocked until a diagnostic placeholder is resolved."
        payload["symbols"] = [
            {"symbol": "f", "meaning": "function or rule"},
            {"symbol": "n", "meaning": "index, count, dimension, or rank-like value"},
            {"symbol": "x", "meaning": "unknown, input, output, or coordinate variable"},
            {"symbol": "Delta", "meaning": "change between successive states"},
        ]
        short["note_depth"] = payload
        pack = {
            "title": "Group Theory",
            "materials": [{"title": "Groups", "text": "Groups and operations define a group. " * 30}],
        }

        ledger = stem_course.notes_coverage_ledger([short], pack)
        row = ledger["topics"][0]

        self.assertEqual(ledger["status"], "failed")
        self.assertFalse(row["checks"]["publishable_prose"])
        self.assertFalse(row["checks"]["no_generic_symbol_placeholders"])
        self.assertIn("Publication remains blocked", row["quality_contract"]["placeholder_hits"])

    def test_true_source_dump_markers_still_fail_coverage(self) -> None:
        short = stem_course.concept_to_short(stem_course.GROUP_THEORY[0], 1)
        payload = json.loads(json.dumps(stem_course.GROUP_THEORY_NOTE_DEPTH["groups and operations"]))
        payload["development"] += " Works cited and download transcript controls follow."
        short["note_depth"] = payload
        pack = {
            "title": "Group Theory",
            "materials": [{"title": "Groups", "text": "Groups and operations define a group. " * 30}],
        }

        ledger = stem_course.notes_coverage_ledger([short], pack)
        row = ledger["topics"][0]

        self.assertFalse(row["checks"]["no_source_dump_noise"])
        self.assertIn("Works cited", row["quality_contract"]["source_noise_hits"])

    def test_source_context_is_digested_without_johnson_hash_table_contamination(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Johnson's Algorithm", "algorithms"),
            1,
        )
        pack = {
            "title": "Algorithms",
            "materials": [{
                "title": "Johnson's Algorithm",
                "text": (
                    "Johnson's algorithm computes sparse all-pairs shortest paths by adding an auxiliary source. "
                    "Bellman-Ford produces vertex potentials, transformed edge weights become nonnegative, and "
                    "Dijkstra is then run from each source. Potential terms telescope along every path, preserving "
                    "path order while allowing distances to be converted back to their original weights. "
                    "The method rejects a graph when Bellman-Ford detects a negative cycle.\n"
                    "[1] Hash tables were discussed earlier in the course.\n"
                    "A hash table stores keys in buckets selected by a hash function. Collisions use chaining.\n"
                    "Bibliography\nCormen discusses Johnson's algorithm and hashing in separate chapters."
                ),
            }],
        }

        payload = stem_course.source_derived_note_depth(short, pack)
        visible = json.dumps({
            key: payload[key]
            for key in ("definition", "results", "development", "properties", "examples")
        }).lower()

        self.assertGreaterEqual(payload["source_context_count"], 1)
        self.assertTrue(payload["source_context_digests"])
        self.assertNotIn("hash table", visible)
        self.assertNotIn("collisions use chaining", visible)
        self.assertNotIn("cormen", visible)
        self.assertNotIn("bibliography", visible)

    def test_unicode_and_plain_group_notation_become_semantic_latex(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "Let phi(n) map D4 to S3; x -> x+1, x in G, and use Z/2Z x Z/3Z. "
            "Also write phi: G → H with x ∈ G. An isomorphism acts on F[x]."
        )

        self.assertIn(r"\varphi", rendered)
        self.assertIn(r"D_{4}", rendered)
        self.assertIn(r"S_{3}", rendered)
        self.assertIn(r"\mathbb{Z}/2\mathbb{Z}\times\mathbb{Z}/3\mathbb{Z}", rendered)
        self.assertIn(r"\to", rendered)
        self.assertIn(r"\in", rendered)
        self.assertIn(r"F[x]", rendered)
        self.assertIn("An isomorphism", rendered)
        self.assertNotIn(r"A_{n}", rendered)
        for raw in ("φ", "→", "∈", "D4", "S3", "D_4"):
            self.assertNotIn(raw, rendered)

        equation = stem_course.notes_latex_prose("Define phi(k)=2k modulo 5.")
        self.assertIn(r"\varphi(k) = 2k", equation)
        self.assertNotIn("NOTESMATH", equation)

        operators = stem_course.notes_latex_prose("det(AB)=det(A)det(B), so multiplication is preserved.")
        self.assertIn(r"\operatorname{det}(AB) = \operatorname{det}(A)\operatorname{det}(B)", operators)
        conjugation = stem_course.notes_latex_prose("Check whether ghg^{-1} stays in H for every g in G and h in H.")
        self.assertIn(r"\(ghg^{-1}\)", conjugation)
        self.assertIn(r"\(g\in G\)", conjugation)
        self.assertIn(r"\(h\in H\)", conjugation)
        quotient = stem_course.notes_latex_prose("G/[G,G] is the abelianization of G.")
        self.assertIn(r"\(G/[G,G]\)", quotient)

    def test_pdf_extraction_noise_is_latex_safe(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "First\u2022 Johnson's distance is \u03b4(x,v) = -\u221e.\u00ad Next\x00 use \u0394, \u0398, \u03b8, and n \u226b 1."
        )

        self.assertNotIn("\u2022", rendered)
        self.assertNotIn("\u00ad", rendered)
        self.assertNotIn("\x00", rendered)
        self.assertNotIn("\u03b4", rendered)
        self.assertNotIn("\u221e", rendered)
        self.assertIn(r"\delta", rendered)
        self.assertIn(r"\infty", rendered)
        self.assertIn(r"\Delta", rendered)
        self.assertIn(r"\Theta", rendered)
        self.assertIn(r"\theta", rendered)
        self.assertIn(r"\gg", rendered)

    def test_algorithm_indices_and_smart_punctuation_are_latex_safe(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "Dijkstra’s update compares dp[i,w] with value_i+dp[i-1,w-weight_i]."
        )

        self.assertNotIn("’", rendered)
        self.assertIn("Dijkstra's", rendered)
        self.assertIn(r"\mathrm{dp}[i,w]", rendered)
        self.assertIn(r"\mathrm{value}_{i}", rendered)
        self.assertIn(r"\mathrm{weight}_{i}", rendered)

    def test_asymptotic_criterion_is_rendered_as_complete_math_spans(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "The statement T(n)=O(g(n)) means constants c>0 and n_0 exist such that "
            "0<=T(n)<=c g(n) for every n>=n_0."
        )

        self.assertIn(r"\(T(n) = O(g(n))\)", rendered)
        self.assertIn(r"\(0\le T(n)\le c g(n)\)", rendered)
        self.assertIn(r"\(n\ge n_{0}\)", rendered)
        for residue in ("<=", ">=", r"\)(n)", "n0", "NOTESMATH"):
            self.assertNotIn(residue, rendered)

    def test_maximal_relations_and_standalone_notation_are_domain_general(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "T(n) depends on g(n) after n_0; E(t)>=0, Q(p)<=S(p), and profit(q)>=cost."
        )

        self.assertIn(r"\(T(n)\)", rendered)
        self.assertIn(r"\(g(n)\)", rendered)
        self.assertIn(r"\(n_{0}\)", rendered)
        self.assertIn(r"\(E(t)\ge 0\)", rendered)
        self.assertIn(r"\(Q(p)\le S(p)\)", rendered)
        self.assertIn(r"\(\mathrm{profit}(q)\ge \mathrm{cost}\)", rendered)

    def test_matrix_assignment_is_consumed_before_partial_equation_matching(self) -> None:
        rendered = stem_course.notes_latex_prose("Use A=[[2,1],[1,3]] in the update.")

        self.assertIn(r"\(A = \begin{bmatrix}2 & 1 \\ 1 & 3\end{bmatrix}\)", rendered)
        self.assertNotIn("[[", rendered)

    def test_interval_dp_recurrence_and_ellipsis_chain_remain_single_expressions(self) -> None:
        recurrence = stem_course.notes_latex_prose(
            "C[i,j]=min_k(C[i,k]+C[k+1,j]+p_{i-1} * p_k * p_j)."
        )
        ordering = stem_course.notes_latex_prose("a_0 <= a_1 <= ... <= a_{n-1}.")

        self.assertIn(
            r"\(C[i, j] = \operatorname{min}_{k}(C[i, k] + C[k + 1, j] + "
            r"p_{i-1} \cdot p_{k} \cdot p_{j})\)",
            recurrence,
        )
        self.assertEqual(ordering, r"\(a_{0} \le a_{1} \le \cdots \le a_{n-1}\).")
        for rendered in (recurrence, ordering):
            self.assertNotIn(r"\_", rendered)
            self.assertNotIn("<=", rendered)

    def test_unicode_scripts_and_uppercase_growth_operators_survive_note_cleaning(self) -> None:
        source = stem_course.formula_unicode_text(r"a_0\leq a_1\leq\cdots\leq a_{n-1}")
        rendered = stem_course.notes_latex_prose(source + "; T(n)=Theta(g(n)); n0 exists.")

        self.assertIn(r"a_{n-1}", rendered)
        self.assertIn(r"\Theta", rendered)
        self.assertNotIn(r"\theta", rendered)
        self.assertIn(r"\(n_{0}\)", rendered)

    def test_function_calls_inside_subscripts_do_not_create_nested_placeholders(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "Bucket B_{h(k)} stores key k, and insertion recomputes h(k)."
        )

        self.assertIn(r"\(B_{h(k)}\)", rendered)
        self.assertIn(r"\(h(k)\)", rendered)
        self.assertNotIn(r"\)\}", rendered)

    def test_note_scaffold_cleaning_preserves_mathematical_source_text(self) -> None:
        rendered = stem_course.notes_scaffold_prose("Use T(n)=n^2 with n_0=4.")

        self.assertEqual(rendered, "Use T(n) = n^2 with n_0 = 4.")
        self.assertNotIn("squared", rendered)
        self.assertNotIn("T (n)", rendered)

    def test_labeled_source_block_must_name_topic_near_the_label(self) -> None:
        late_mention = (
            "Definition 9.1. A graph is a vertex set and an edge relation. "
            + "One additional representation detail is that "
            + "A direct access array may store the adjacency map."
        )
        actual_definition = (
            "Definition 2.1. A direct-access array stores an item at the integer address equal to its key, "
            "so lookup reads the corresponding table cell directly. Empty cells represent absent keys, "
            "and the allocated universe determines the storage cost."
        )
        pack = {
            "materials": [
                {"kind": "pdf", "title": "Graphs", "text": late_mention},
                {"kind": "pdf", "title": "Data Structures", "text": actual_definition},
            ]
        }

        blocks = stem_course.notes_source_labeled_blocks(pack, "Direct Access Array")

        self.assertEqual(len(blocks), 1)
        self.assertIn("integer address", blocks[0][1])
        self.assertNotIn("vertex set", blocks[0][1])

    def test_source_term_plan_topic_is_retained_for_notes(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Direct Access Array", "algorithms"), 1
        )
        pack = {
            "title": "Algorithms",
            "source_url": "https://example.test/algorithms",
            "materials": [{
                "kind": "pdf",
                "title": "Data Structures",
                "text": "A Direct Access Array maps an integer key directly to one table address. " * 12,
            }],
        }

        shorts = stem_course.full_note_shorts(pack, {"shorts": [short]})

        self.assertIn("Direct Access Array", [str(item["concept"]) for item in shorts])

    def test_dynamic_programming_outline_names_bind_to_lecture_labels(self) -> None:
        pack = {
            "materials": [{
                "kind": "page",
                "title": "Course calendar",
                "text": (
                    "Lecture 15: Dynamic Programming, Part 1: Recursive Algorithms. "
                    "Lecture 16: Dynamic Programming Subproblems. "
                    "Lecture 17: Dynamic Programming, Part 3: APSP, Parens, Piano. "
                    "Lecture 18: Pseudopolynomial."
                ),
            }],
        }

        concepts = (
            "Memoization and Recursive Dynamic Programming",
            "Dynamic Programming State Design",
            "Dynamic Programming Applications",
            "Pseudopolynomial Dynamic Programming",
        )

        for concept in concepts:
            grounding = stem_course.notes_source_grounding(pack, concept)
            self.assertTrue(grounding["matched"], concept)

    def test_generic_notes_use_domain_reasoning_instead_of_repeated_filler(self) -> None:
        algorithm = stem_course.concept_to_short(
            stem_course.source_term_concept("Bellman-Ford", "algorithms"), 1
        )
        physics = stem_course.concept_to_short(stem_course.PHYSICS_MECHANICS[0], 1)
        economics = stem_course.concept_to_short(stem_course.ECONOMICS[0], 1)
        pack = {
            "title": "Technical Course",
            "materials": [{
                "kind": "pdf",
                "title": "Notes",
                "text": "Bellman-Ford relaxation, Newton's second law, and supply and demand equilibrium. " * 20,
            }],
        }

        algorithm_depth = stem_course.source_derived_note_depth(algorithm, pack)
        physics_depth = stem_course.source_derived_note_depth(physics, pack)
        economics_depth = stem_course.source_derived_note_depth(economics, pack)

        self.assertIn("state transition", algorithm_depth["definition"])
        self.assertIn("loop-invariant", algorithm_depth["development"])
        self.assertIn("coordinate", physics_depth["definition"])
        self.assertIn("unit", physics_depth["development"])
        self.assertIn("endogenous", economics_depth["definition"])
        self.assertIn("comparative statics", economics_depth["development"])
        for payload in (algorithm_depth, physics_depth, economics_depth):
            serialized = json.dumps(payload).lower()
            self.assertNotIn("course mechanism summarized", serialized)
            self.assertNotIn("source-grounded derivation", serialized)
            self.assertGreaterEqual(stem_course.note_depth_word_count(payload), 220)

    def test_algorithm_notes_require_semantic_symbols_procedures_and_figures(self) -> None:
        topics = (
            ("Bellman-Ford", "G=(V,E)", "d[v]"),
            ("Dynamic Programming State Design", r"\mathrm{dp}[r,c]", "r,c"),
            ("Hash Tables", "h(k)", r"\alpha=n/m"),
            ("Dynamic Array", "C_{new}", r"\Phi"),
            ("Binary Search Trees", "key(v)", "L(v)"),
        )
        pack = {
            "title": "Algorithms",
            "materials": [{
                "kind": "pdf",
                "title": "Algorithms lecture notes",
                "text": " ".join(topic for topic, _first, _second in topics) * 20,
            }],
        }

        development_titles: set[str] = set()
        figures: set[str] = set()
        for index, (topic, first_symbol, second_symbol) in enumerate(topics, start=1):
            short = stem_course.concept_to_short(
                stem_course.source_term_concept(topic, "algorithms"), index
            )
            payload = stem_course.source_derived_note_depth(short, pack)
            symbols = {row["symbol"]: row["meaning"] for row in payload["symbols"]}
            serialized_symbols = json.dumps(symbols).lower()

            self.assertIn(first_symbol, symbols)
            self.assertIn(second_symbol, symbols)
            self.assertEqual(len(payload["algorithms"]), 1)
            self.assertGreaterEqual(len(payload["algorithms"][0]["steps"]), 4)
            self.assertNotIn("named quantity defined by the course context", serialized_symbols)
            self.assertNotIn("vector, direction, or comparison quantity", serialized_symbols)
            self.assertNotIn("indexed component, coefficient, or sequence term", serialized_symbols)
            self.assertTrue(payload["figure"])
            development_titles.add(payload["development_title"])
            figures.add(stem_course.latex_topic_figure(short))

        self.assertEqual(len(development_titles), len(topics))
        self.assertEqual(len(figures), len(topics))

        dynamic_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Dynamic Array", "algorithms"), 1
        )
        dynamic_results = stem_course.note_scaffold_results(dynamic_short, "algorithms")
        self.assertIn("Amortized append bound", [row["name"] for row in dynamic_results])
        self.assertNotIn("Direct-access bound", [row["name"] for row in dynamic_results])

    def test_algorithm_figures_bind_to_the_exact_worked_state(self) -> None:
        hash_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Hash Function", "algorithms"), 1
        )
        insertion_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Insertion Sort", "algorithms"), 2
        )

        hash_body, hash_facts = stem_course.latex_cs_semantic_figure_body(hash_short, "cs_hash")
        insertion_body, insertion_facts = stem_course.latex_cs_semantic_figure_body(insertion_short, "cs_sort")

        self.assertIn(r"k\bmod 7", hash_body)
        for value in ("10", "18", "25"):
            self.assertIn(value, hash_body)
            self.assertIn(value, hash_facts)
        self.assertNotIn(r"\bmod 4", hash_body)
        for value in ("5", "2", "4", "6", "1"):
            self.assertIn(value, insertion_body)
            self.assertIn(value, insertion_facts)
        self.assertEqual(stem_course.notes_figure_binding_contract(hash_short)["status"], "ok")
        self.assertEqual(stem_course.notes_figure_binding_contract(insertion_short)["status"], "ok")

        complexity_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Complexity", "algorithms"), 3
        )
        complexity_figure = stem_course.latex_topic_figure(complexity_short)
        for series in (r"O(1)", r"O(n)", r"O(n \log n)", r"O(n^2)"):
            self.assertIn(series, complexity_figure)
        self.assertEqual(complexity_figure.count("plot[smooth]"), 4)
        self.assertIn("worked sample: $n=16$", complexity_figure)
        self.assertIn(r"\node[below left] at (6,-0.06) {$\log_{10} n$}", complexity_figure)
        self.assertIn(r"node[above right]{$ O(1) $}", complexity_figure)
        self.assertNotIn("worked target: $n=2$", complexity_figure)
        self.assertNotIn(r"\^\{\}", complexity_figure)
        self.assertEqual(stem_course.notes_figure_binding_contract(complexity_short)["status"], "ok")

        with mock.patch.object(
            stem_course,
            "latex_cs_semantic_figure_body",
            return_value=(r"\node {O(n), O(n \log n), O(n^2), n=16};", []),
        ):
            dropped = stem_course.notes_figure_binding_contract(complexity_short)
        self.assertEqual(dropped["status"], "failed")
        self.assertIn("O(1)", dropped["missing"])

    def test_declared_figures_bind_all_visible_lanes_across_domains(self) -> None:
        cases = (
            ("algorithms", "Hash Tables", "cs_hash", "collision", "collision"),
            ("algebra", "Subgroup Operation", "group_subgroup", "subgroup", "operation"),
            ("physics", "Net Force", "physics_force", "force", r"\(F\)"),
            ("economics", "Supply Demand Equilibrium", "econ_supply_demand", "equilibrium", "demand"),
            ("probability", "Transition Probability", "markov", "probability", r"\(p\)"),
            ("chemistry", "Reaction Work Sequence", "state_machine", "reaction", "work"),
            ("technical", "Residual Vector", "vector_components", "residual", "vector"),
        )
        for index, (domain, concept, visual, anchor, evidence) in enumerate(cases, start=1):
            with self.subTest(domain=domain):
                short = {"index": index, "concept": concept, "visual_type": visual}
                payload = {
                    "figure": True,
                    "results": [{"name": f"{anchor} result", "statement": f"The {anchor} result preserves {evidence}."}],
                    "examples": [{
                        "setup": f"Start with the {anchor} input.",
                        "calculation": f"Track {evidence} through the visible step.",
                        "takeaway": f"The {anchor} output is checkable.",
                    }],
                    "figure_caption": f"{concept}: visible {evidence} evidence.",
                    "figure_discussion": f"The {anchor} discussion reads {evidence} from the diagram.",
                }
                contract = stem_course.notes_figure_binding_contract(short, payload)
                self.assertEqual(contract["status"], "ok", contract)
                self.assertEqual(contract["missing_lanes"], [])
                self.assertTrue(contract["evidence_bindings"])

                payload["figure_discussion"] = "Zeolite chromatography pigment classification."
                rejected = stem_course.notes_figure_binding_contract(short, payload)
                self.assertEqual(rejected["status"], "failed")
                self.assertIn("discussion", rejected["missing_lanes"])

    def test_algorithm_specification_requires_five_visible_contract_parts(self) -> None:
        short = stem_course.concept_to_short(
            stem_course.source_term_concept("Bellman-Ford", "algorithms"), 1
        )
        payload = stem_course.source_derived_note_depth(short, {
            "title": "Algorithms",
            "materials": [{"title": "Lecture", "text": "Bellman-Ford shortest paths" * 20}],
        })
        contract = stem_course.notes_algorithm_specification_contract(payload)
        self.assertEqual(contract["status"], "ok")
        self.assertEqual(
            contract["required_fields"],
            ["inputs", "outputs", "invariant", "termination", "complexity"],
        )
        payload["algorithms"][0]["specification"]["termination"] = ""
        self.assertEqual(stem_course.notes_algorithm_specification_contract(payload)["status"], "failed")

    def test_claim_binding_rejects_an_unrelated_proof(self) -> None:
        sorted_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Sorted Array", "algorithms"), 1
        )
        dynamic_short = stem_course.concept_to_short(
            stem_course.source_term_concept("Dynamic Array", "algorithms"), 2
        )
        sorted_results = stem_course.note_scaffold_results(sorted_short, "algorithms")
        _dynamic_title, dynamic_proof = stem_course.algorithm_specific_development(
            dynamic_short,
            stem_course.note_scaffold_results(dynamic_short, "algorithms"),
        )

        contract = stem_course.notes_development_claim_contract(sorted_results[0], dynamic_proof)

        self.assertEqual(contract["status"], "failed")
        self.assertEqual(contract["target"], "Binary-search interval invariant")

    def test_repetition_gate_rejects_page_count_padding(self) -> None:
        shorts = []
        for index in range(1, 9):
            short = {
                "index": index,
                "concept": f"Topic {index}",
                "visual_type": "numeric_rule",
                "note_depth": {
                    "content_basis": "source-derived-domain-scaffold",
                    "definition": (
                        f"Topic {index} begins here. This repeated filler sentence supplies the same "
                        "generic explanation without any topic-specific reasoning or evidence."
                    ),
                    "development": (
                        "This repeated filler sentence supplies the same generic explanation without "
                        "any topic-specific reasoning or evidence."
                    ),
                    "results": [],
                    "properties": [],
                    "algorithms": [],
                    "examples": [],
                    "extensions": [],
                },
            }
            shorts.append(short)

        report = stem_course.notes_repetition_audit(shorts)

        self.assertEqual(report["status"], "failed")
        self.assertGreater(report["repeated_sentence_ratio"], 0.28)

    def test_algorithm_source_subtopics_are_rendered_and_covered(self) -> None:
        source_terms = [spec["source_term"] for spec in stem_course.algorithm_companion_extension_specs()]
        parent_terms = sorted({spec["parent"] for spec in stem_course.algorithm_companion_extension_specs()})
        pack = {
            "title": "Algorithms",
            "materials": [{
                "kind": "pdf",
                "title": "Complete algorithms notes",
                "text": ". ".join([*source_terms, *parent_terms]) * 12,
            }],
        }
        shorts = [
            stem_course.concept_to_short(
                stem_course.source_term_concept(parent, "algorithms"),
                index,
            )
            for index, parent in enumerate(parent_terms, start=1)
        ]
        for short in shorts:
            short["note_depth"] = stem_course.build_note_depth_payload(short, pack)
        report = stem_course.notes_source_subtopic_coverage(pack, shorts)

        self.assertEqual(report["source_subtopic_status"], "ok")
        self.assertGreaterEqual(report["required_source_subtopic_count"], 8)
        self.assertEqual(report["missing_source_subtopic_count"], 0)
        rendered_terms = {row["source_term"] for row in report["source_subtopics"]}
        for term in (
            "Sequence Interface",
            "Set Interface",
            "Static Array",
            "Comparison Sort Lower Bound",
            "Radix Sort",
        ):
            self.assertIn(term, rendered_terms)

    def test_physics_and_economics_visual_families_have_notes_figures(self) -> None:
        for index, visual in enumerate(sorted(stem_course.PHYSICS_VISUAL_KINDS), start=1):
            figure = stem_course.latex_topic_figure({
                "index": index,
                "concept": f"Physics model {index}",
                "visual_type": visual,
            })
            self.assertIn(r"\begin{tikzpicture}", figure, visual)

        rendered_economics_visuals = set()
        for index, visual in enumerate(sorted(stem_course.ECON_VISUAL_KINDS), start=1):
            figure = stem_course.latex_topic_figure({
                "index": index,
                "concept": f"Economics model {index}",
                "visual_type": visual,
            })
            if figure:
                rendered_economics_visuals.add(visual)
                self.assertIn(r"\begin{tikzpicture}", figure, visual)
        self.assertTrue({"econ_supply_demand", "econ_budget", "econ_elasticity"} <= rendered_economics_visuals)

        force = stem_course.concept_to_short(stem_course.PHYSICS_MECHANICS[0], 1)
        force_figure = stem_course.latex_topic_figure(force)
        self.assertIn(r"\begin{adjustbox}{center,max width=0.98\linewidth,max totalheight=0.32\textheight}", force_figure)
        self.assertNotIn(r"\resizebox", force_figure)
        self.assertIn("net force arrow", force_figure)
        self.assertEqual(stem_course.notes_figure_binding_contract(force)["status"], "ok")
        force_symbols = {row["symbol"]: row["meaning"] for row in stem_course.physics_note_symbols(force)}
        self.assertEqual(force_symbols["m"], "constant system mass in the final equality")
        self.assertIn(r"\sum \vec F_{\mathrm{ext}}", force_symbols)

        market = stem_course.concept_to_short(stem_course.ECONOMICS[0], 1)
        market_figure = stem_course.latex_topic_figure(market)
        self.assertIn(r"\begin{adjustbox}{center,max width=0.98\linewidth,max totalheight=0.32\textheight}", market_figure)
        self.assertNotIn(r"\resizebox", market_figure)
        self.assertIn("equilibrium price", market_figure)
        self.assertEqual(stem_course.notes_figure_binding_contract(market)["status"], "ok")
        market_symbols = {row["symbol"]: row["meaning"] for row in stem_course.economics_note_symbols(market)}
        self.assertIn("Q_d(P)", market_symbols)
        self.assertIn("Q_s(P)", market_symbols)
        self.assertNotIn("price or shadow value in the stated model", json.dumps(market_symbols))

    def test_mit_proofs_bind_by_stable_ids_and_validate_claim_semantics(self) -> None:
        shorts = stem_course.mit_18_703_note_shorts(mit_18_703_source_pack())
        results = {
            str(result["id"]): result
            for short in shorts
            for result in short["note_depth"]["results"]
        }
        proofs = {
            str(proof["result_id"]): proof
            for short in shorts
            for proof in short["note_depth"]["proofs"]
        }

        self.assertEqual(len(results), 61)
        self.assertEqual(set(results), set(proofs))
        self.assertTrue(all(result_id.startswith("mit18-703.u") for result_id in results))
        self.assertTrue(all(proof["claim_contract"]["status"] == "ok" for proof in proofs.values()))

        expected_proof_anchors = {
            "mit18-703.u03.coset-partition": ("equal or disjoint", "bijection"),
            "mit18-703.u07.inverse-isomorphism": (r"\varphi^{-1}(xy)", "homomorphism"),
            "mit18-703.u13.sylow-theorems": ("For existence", "conjugacy", r"n_p\equiv1\pmod p"),
            "mit18-703.u14.basic-ring-identities": ("a0=0", r"(-a)(-b)", "=ab"),
            "mit18-703.u21.polynomial-division": ("For existence", "For uniqueness", "terminates"),
        }
        for result_id, anchors in expected_proof_anchors.items():
            for anchor in anchors:
                self.assertIn(anchor, proofs[result_id]["body"])

        swapped = stem_course.mit_18_703_validate_result_claim(
            "mit18-703.u03.coset-partition",
            results["mit18-703.u03.coset-partition"]["statement"],
            proofs["mit18-703.u03.finite-group-exponent"]["body"],
        )
        self.assertEqual(swapped["status"], "failed")
        self.assertTrue(any(issue["kind"] == "conclusion-anchor-missing" for issue in swapped["issues"]))

        uniqueness_only = stem_course.mit_18_703_validate_result_claim(
            "mit18-703.u21.polynomial-division",
            results["mit18-703.u21.polynomial-division"]["statement"],
            "For uniqueness, compare two remainders and conclude q=q' and r=r'.",
        )
        self.assertEqual(uniqueness_only["status"], "failed")
        self.assertTrue(any("For existence" in issue.get("missing", []) for issue in uniqueness_only["issues"]))

    def test_mit_prerequisite_contract_rejects_undefined_or_premature_cosets(self) -> None:
        shorts = stem_course.mit_18_703_note_shorts(mit_18_703_source_pack())
        missing_definition = json.loads(json.dumps(shorts))
        missing_definition[2]["note_depth"]["definition"] = (
            missing_definition[2]["note_depth"]["definition"].replace(
                r"gH=\{gh:h\in H\}",
                "a translated subset",
            )
        )
        with self.assertRaisesRegex(RuntimeError, "incomplete-definition-literal"):
            stem_course.mit_18_703_validate_concept_prerequisites(missing_definition)

        premature_use = json.loads(json.dumps(shorts))
        premature_use[0]["note_depth"]["properties"].append("Use gH before defining a left coset.")
        with self.assertRaisesRegex(RuntimeError, "notation-used-before-definition"):
            stem_course.mit_18_703_validate_concept_prerequisites(premature_use)

    def test_nested_and_bracketed_math_markers_restore_as_one_expression(self) -> None:
        source = "exactly ([G:H]) blocks; product ((a+P)(b+P)); namely (Z(G)); and (ordinary prose)."
        rendered = stem_course.mit_18_703_restore_inline_math(source)

        self.assertIn(r"\([G:H]\)", rendered)
        self.assertIn(r"\((a+P)(b+P)\)", rendered)
        self.assertIn(r"\(Z(G)\)", rendered)
        self.assertIn("(ordinary prose)", rendered)


class NotesTexStructureTests(unittest.TestCase):
    def test_optional_environment_titles_protect_bracketed_math(self) -> None:
        short = {
            "concept": "Polynomial Rings",
            "note_depth": {
                "trusted_tex": True,
                "examples": [{
                    "kind": "example",
                    "title": r"Reading the hierarchy in \(F[x]\)",
                    "setup": r"Let \(F\) be a field.",
                    "calculation": r"Then \(F[x]\) is Euclidean.",
                    "takeaway": "Degree controls division.",
                }],
            },
        }

        rendered = stem_course.latex_note_examples(short)

        self.assertIn(r"\begin{example}[{Reading the hierarchy in \(F[x]\)}]", rendered)

    def test_single_letter_indexed_identifiers_in_prose_are_inline_math(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "The price is read from demand at q_m, while P_m and a_d remain labeled."
        )

        self.assertIn(r"\(q_{m}\)", rendered)
        self.assertIn(r"\(P_{m}\)", rendered)
        self.assertIn(r"\(a_{d}\)", rendered)
        self.assertNotIn("q_m", rendered)
        self.assertNotIn("P_m", rendered)

    def test_economics_symbol_meanings_do_not_emit_raw_tex_subscripts(self) -> None:
        short = {
            "concept": "Monopoly I",
            "formula": r"MR(q_m)=MC(q_m),\quad P_m=P(q_m)",
            "note_depth": {
                "trusted_tex": True,
                "symbols": [
                    {"symbol": "q_m", "meaning": "monopoly profit-maximizing quantity"},
                    {"symbol": "P_m", "meaning": "price read from demand at q_m"},
                ],
            },
        }

        table = stem_course.latex_note_symbol_table(short)

        self.assertIn(r"price read from demand at \(q_{m}\)", table)
        self.assertNotIn("at q_m", table)

    def test_group_and_linear_algebra_prose_preserve_tex_and_structured_matrices(self) -> None:
        group = stem_course.notes_latex_prose(
            r"The kernel is \(\ker f=\{g\in G:f(g)=e\}\), so "
            r"\[G/\ker f\cong \operatorname{im}f.\]"
        )
        linear = stem_course.notes_render_value({
            "parts": [
                {"text": "In the ordered basis, the transformation has matrix"},
                {"matrix": [[2, 1], [1, 3]]},
                {"text": "and determinant"},
                {"math": r"\det A=5"},
                {"text": "."},
            ],
        }, trusted=False)

        self.assertIn(r"\(\ker f = \{g\in G: f(g) = e\}\)", group)
        self.assertIn(r"\[G/\ker f\cong \operatorname{im}f.\]", group)
        self.assertIn(r"\begin{bmatrix}2 & 1 \\ 1 & 3\end{bmatrix}", linear)
        self.assertIn(r"\(\det A=5\)", linear)
        for rendered in (group, linear):
            self.assertNotIn(r"\textbackslash{}", rendered)
            self.assertNotIn("[[", rendered)
            self.assertNotIn("{'", rendered)

    def test_figure_discussion_diagram_and_caption_share_one_nonbreaking_unit(self) -> None:
        short = stem_course.concept_to_short(stem_course.GROUP_THEORY[0], 1)
        short["note_depth"] = json.loads(json.dumps(stem_course.GROUP_THEORY_NOTE_DEPTH["groups and operations"]))
        short["note_depth"]["trusted_tex"] = True
        discussion = "The discussion stays attached to the operation diagram."

        figure = stem_course.latex_topic_figure(short, discussion)
        start = figure.index(r"\begin{minipage}{0.98\linewidth}")
        end = figure.index(r"\end{minipage}", start)
        unit = figure[start:end]

        self.assertIn(discussion, unit)
        self.assertIn(r"\begin{tikzpicture}", unit)
        self.assertIn(r"\captionof{figure}", unit)
        self.assertNotIn(r"\Needspace", figure)

    def test_mit_static_array_excerpt_keeps_growth_bounds_in_single_math_spans(self) -> None:
        source = (
            "StaticArray(n): allocate a new static array of size n initialized to 0 in \u0398(n) time. "
            "StaticArray.get at(i): return the word stored at array index i in \u0398(1) time."
        )

        rendered = stem_course.notes_latex_prose(source)

        self.assertIn(r"\(\Theta(n)\) time.", rendered)
        self.assertIn(r"\(\Theta(1)\) time.", rendered)
        self.assertNotRegex(rendered, r"\\\((?:(?!\\\)).)*\\\(")

    def test_nested_and_escaped_growth_delimiters_normalize_without_flattening_math(self) -> None:
        source = (
            r"Tight bounds \(\(\Theta\)(n log n)\), upper \(O(n^2)\), and lower \(\Omega(n)\). "
            r"Keep \(A = \begin{bmatrix}2 & 1 \\ 1 & 3\end{bmatrix}\), then continue."
        )

        rendered = stem_course.notes_latex_prose(source)

        self.assertIn(r"\(\Theta(n \log n)\),", rendered)
        self.assertIn(r"\(O(n^{2})\),", rendered)
        self.assertIn(r"\(\Omega(n)\).", rendered)
        self.assertIn(r"\(A = \begin{bmatrix}2 & 1 \\ 1 & 3\end{bmatrix}\),", rendered)
        self.assertNotRegex(rendered, r"\\\((?:(?!\\\)).)*\\\(")

    def test_nested_source_symbols_and_function_arguments_share_one_math_span(self) -> None:
        source = (
            r"Let \(w(\(\pi\))\) be the path weight; "
            r"then \(\(\delta\)(s,v)\) is finite, and \(\(w\)(a,b)\) is an edge weight."
        )

        rendered = stem_course.notes_latex_prose(source)

        self.assertIn(r"\(w(\pi)\) be the path weight;", rendered)
        self.assertIn(r"\(\delta(s, v)\) is finite,", rendered)
        self.assertIn(r"\(w(a, b)\) is an edge weight.", rendered)
        self.assertNotRegex(rendered, r"\\\((?:(?!\\\)).)*\\\(")

    def test_algorithm_array_slices_are_not_rendered_as_matrices(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "The logical sequence is stored in A[0:n], while A[i] names one item."
        )

        self.assertIn(r"\(A[0:n]\)", rendered)
        self.assertIn(r"\(A[i]\)", rendered)
        self.assertNotIn(r"\begin{bmatrix}", rendered)

    def test_true_nested_matrix_literals_still_use_bmatrix(self) -> None:
        rendered = stem_course.latex_text_with_inline_math(
            "Use [[1, 2], [3, 4]] in the matrix calculation."
        )

        self.assertIn(r"\begin{bmatrix}1 & 2 \\ 3 & 4\end{bmatrix}", rendered)

    def test_ragged_structured_lists_serialize_as_one_bmatrix(self) -> None:
        rendered = stem_course.notes_latex_prose(
            "The buckets are [[], [], [12, 7], [18], []]."
        )

        self.assertIn(
            r"\begin{bmatrix}\varnothing & \varnothing & \{12, 7\} & \{18\} & \varnothing\end{bmatrix}",
            rendered,
        )
        self.assertNotIn("[[],", rendered)

    def test_generated_figure_discussion_typesets_algorithm_indices(self) -> None:
        short = stem_course.concept_to_short(
            next(
                concept
                for concept in stem_course.ALGORITHMS
                if concept.name == "Dynamic programming"
            ),
            1,
        )
        short["note_depth"] = {
            "figure": True,
            "figure_discussion": "The figure recomputes dp[i,w] from value_i and dp[i-1,w-weight_i].",
        }
        with mock.patch.object(
            stem_course,
            "latex_topic_figure",
            side_effect=lambda _short, discussion="": "FIGURE\n" + discussion,
        ):
            rendered = stem_course.latex_comprehensive_topic(short)

        self.assertIn(r"\(\mathrm{dp}[i,w]\)", rendered)
        self.assertIn(r"\mathrm{value}_{i}", rendered)
        self.assertNotIn("value_i", rendered)

    def test_reference_structure_starts_with_substantive_numbered_section(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-reference-structure-") as temp:
            run = Path(temp)
            pack = {
                "title": "Algebra Basics",
                "source_url": "https://example.test/algebra-basics",
                "materials": [{"kind": "pdf", "title": "Lecture 1", "text": "Definition 1.1. A group is a set with an associative operation, identity, and inverses."}],
            }
            short = stem_course.concept_to_short(stem_course.GROUP_THEORY[0], 1)
            plan = {"course_title": "Modern Algebra", "shorts": [short]}
            stem_course.write_json(run / "source_pack.json", pack)
            stem_course.write_json(run / "short_plan.json", plan)
            args = argparse.Namespace(run=str(run), compile=False, pdf_engine="none")

            with mock.patch.object(stem_course, "full_note_shorts", return_value=[short]):
                stem_course.cmd_notes(args)

            tex = (run / "notes.tex").read_text(encoding="utf-8")
            coverage = json.loads((run / "notes_coverage_report.json").read_text(encoding="utf-8"))
            self.assertEqual(coverage["status"], "ok")
            self.assertNotIn("Course Order", tex)
            self.assertNotIn("Notation and Formula Index", tex)
            self.assertNotIn("Course Topics", tex)
            self.assertNotIn("Course context", tex)
            self.assertNotIn("meaning should be checked", tex)
            self.assertIn(r"\section{Groups and operations}", tex)
            self.assertIn(r"\newtheorem{definition}{Definition}[section]", tex)
            self.assertEqual(tex.count(r"(G,\cdot)"), 1)
            self.assertIn("Modern Algebra Comprehensive Notes", tex)
            self.assertNotIn("Cumulative exercises", tex)

    def test_mit_notes_match_reference_grammar_without_padding_appendices(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-mit-calendar-") as temp:
            run = Path(temp)
            stem_course.write_json(run / "source_pack.json", mit_18_703_source_pack())
            stem_course.write_json(run / "short_plan.json", {"course_title": "Modern Algebra", "shorts": []})

            stem_course.cmd_notes(argparse.Namespace(run=str(run), compile=False, pdf_engine="none"))

            tex = (run / "notes.tex").read_text(encoding="utf-8")
            coverage = json.loads((run / "notes_coverage_report.json").read_text(encoding="utf-8"))
            self.assertEqual(coverage["status"], "ok")
            self.assertIn(r"{\LARGE Modern Algebra Comprehensive Notes\par}", tex)
            self.assertIn(r"{\large \today\par}", tex)
            self.assertIn("My methods are really methods of working and thinking", tex)
            self.assertIn("Emmy Noether", tex)
            self.assertNotIn("Letter to Helmut Hasse", tex)
            self.assertNotIn("Generated by", tex)
            self.assertNotIn("Definitions and Formulas", tex)
            self.assertNotIn("Course Order", tex)
            self.assertNotIn("Source list", tex)
            self.assertNotIn("Cumulative exercises", tex)
            self.assertNotIn("T01-Q", tex)
            self.assertNotIn("which hypothesis fails", tex)
            self.assertNotIn("Reproduce the worked case", tex)
            self.assertEqual(tex.count(r"\subsection{Checkpoint}"), 24)
            self.assertIn("Why do clock-hour rotations modulo 12 form a group under addition?", tex)
            self.assertIn("How do you test whether 2 generates integers modulo 6?", tex)
            self.assertIn(r"\item[Problem.]", tex)
            self.assertIn(r"\item[Solution.]", tex)
            self.assertNotIn(r"\Needspace", tex)
            self.assertNotRegex(tex, r"\\\((?:(?!\\\)).)*\\\(")
            for repeated_heading in (
                "Definition and notation", "Results and consequences", "Proof and derivation",
                "Further course results", "Worked examples and boundary cases", "Structural figure",
                "Core relation.",
            ):
                self.assertNotIn(repeated_heading, tex)
            for repeated_label in (r"\textbf{Setup.}", r"\textbf{Calculation or argument.}", r"\textbf{Interpretation.}"):
                self.assertNotIn(repeated_label, tex)
            self.assertNotIn("Galois", tex)
            self.assertNotIn("Solvable", tex)
            self.assertIn(r"\begin{pmatrix}", tex)
            self.assertIn(r"\begin{cases}", tex)
            self.assertIn(r"\begin{aligned}", tex)
            self.assertIn(r"\begin{algorithm}", tex)
            self.assertIn("\\begin{algorithm}[Subgroup verification]\n\\leavevmode\\par\\smallskip", tex)
            self.assertEqual(tex.count(r"\captionof{figure}"), 24)
            self.assertIn(r"\begin{tikzpicture}", tex)
            self.assertIn(r"Figure~\ref{fig:mit-18-703-03}", tex)
            self.assertIn(r"\section{Conjugation in \(S_n\)}", tex)
            self.assertIn(r"\begin{example}[{Abelianization of \(S_3\)}]", tex)
            self.assertIn(r"\begin{example}[{Reading the domain hierarchy in \(F[x]\)}]", tex)
            self.assertNotIn(r"S\_n", tex)
            self.assertNotIn(r"\textbackslash{}", tex)
            self.assertIn(r"gH=\{gh:h\in H\}", tex)
            self.assertIn(r"Hg=\{hg:h\in H\}", tex)
            self.assertIn(r"\(\langle g\rangle\)", tex)
            self.assertNotIn(r"cyclic subgroup (\langle g\rangle\)", tex)
            self.assertIn(r"\(\displaystyle \gcd(k,n)\)", tex)
            self.assertNotIn(r"\gcd\(", tex)
            self.assertNotIn(r"\operatorname{ord}_r\(", tex)
            self.assertIn(r"\[\tau\sigma\tau^{-1}=(\tau(a_1)", tex)
            self.assertNotIn(r"=\(\tau(a_1)", tex)
            self.assertIn(r"\subsection{Notation for Groups}", tex)
            self.assertIn(r"\subsection{Proof of cancellation}", tex)
            self.assertIn(r"\subsection{Extensions of Cyclic Groups}", tex)
            self.assertIn(r"\newtheorem{proofblock}{Proof}[section]", tex)
            self.assertIn(r"\newtheorem{proofsketch}[proofblock]{Proof Sketch}", tex)
            self.assertLess(tex.index(r"\theoremstyle{definition}"), tex.index(r"\newtheorem{algorithm}[theorem]{Algorithm}"))
            self.assertEqual(tex.count(r"\begin{proofblock}") + tex.count(r"\begin{proofsketch}"), 82)
            self.assertNotIn(r"\begin{proof}", tex)
            self.assertIn(
                r"\subsection[Extensions of A Quick Primality Test]{\NotesWrappedHeading{Extensions of A Quick \\ Primality Test}}",
                tex,
            )
            self.assertIn(
                r"\subsection[Extensions of Presentations and Groups of Small Order]{\NotesWrappedHeading{Extensions of Presentations \\ and Groups of Small Order}}",
                tex,
            )
            self.assertIn(r"\DeclareRobustCommand{\NotesWrappedHeading}", tex)
            self.assertNotIn(r"\subsection[Extensions of A Quick Primality Test]{\raggedright", tex)
            self.assertNotIn(r"\protect\linebreak", tex)

            section_positions = [tex.index(rf"\section{{{title}}}") for title in (
                "Groups", "Subgroups", "Cosets", "Cyclic Groups", "Permutation Groups",
            )]
            self.assertEqual(section_positions, sorted(section_positions))
            self.assertLess(tex.index(r"\section{Group Actions and Automorphisms}"), tex.index(r"\section{Review}"))
            self.assertEqual(coverage["figure_count"], 24)
            self.assertEqual(coverage["bound_proof_count"], 61)
            self.assertEqual(
                coverage["semantic_claim_contract_count"],
                len(stem_course.MIT_18_703_RESULT_CLAIM_CONTRACTS),
            )
            self.assertEqual(coverage["prerequisite_concepts"]["status"], "ok")

    def test_structured_heading_parts_keep_math_out_of_text_escaping(self) -> None:
        heading = stem_course.latex_structured_heading({
            "parts": ({"text": "Conjugation in "}, {"math": r"S_n"}),
        })

        self.assertEqual(heading, r"Conjugation in \(S_n\)")
        self.assertNotIn(r"S\_n", heading)
        with self.assertRaisesRegex(ValueError, "raw math delimiters"):
            stem_course.latex_structured_heading({"parts": ({"text": r"Bad \(S_n\)"},)})

    def test_long_subsection_headings_wrap_without_losing_words(self) -> None:
        for title in (
            "Extensions of A Quick Primality Test",
            "Extensions of Presentations and Groups of Small Order",
        ):
            lines = stem_course.latex_balanced_heading_lines(title)

            self.assertGreater(len(lines), 1)
            self.assertEqual(" ".join(lines), title)
            self.assertTrue(all(stem_course.latex_heading_visible_length(line) <= 34 for line in lines))

        subsection = stem_course.latex_note_subsection(
            {"concept": "A Quick Primality Test"},
            "extensions",
        )
        self.assertIn(r"\NotesWrappedHeading", subsection)
        self.assertNotIn(r"\raggedright", subsection)
        normalized = subsection.replace(r" \\ ", " ")
        self.assertEqual(normalized.count("Extensions of A Quick Primality Test"), 2)

    def test_wrapped_heading_page_audit_detects_clipped_leading_text(self) -> None:
        title = "Extensions of Presentations and Groups of Small Order"
        anchors = [
            "a finite presentation can define an",
            "different presentations can define isomorphic groups",
        ]
        clean_page = {
            18: """
12.4 Extensions of Presentations
and Groups of Small Order
Proposition 12.1 (Universal property).
* A finite presentation can define an infinite group.
* Different presentations can define isomorphic groups.
""",
        }

        expected_numbers = {title: "12.4"}
        clean = stem_course.notes_page_text_integrity_report(
            clean_page,
            [title],
            anchors,
            expected_numbers,
        )

        self.assertEqual(clean["status"], "ok")
        self.assertEqual(clean["wrapped_heading_pages"], [18])
        self.assertGreater(clean["checked_line_count"], 0)

        clipped_page = {
            18: """
2.4 Extensions of Presentations
and Groups of Small Order
position 12.1 (Universal property).
finite presentation can define an infinite group.
* Different presentations can define isomorphic groups.
""",
        }
        clipped = stem_course.notes_page_text_integrity_report(
            clipped_page,
            [title],
            anchors,
            expected_numbers,
        )
        issue_kinds = {issue["kind"] for issue in clipped["issues"]}

        self.assertEqual(clipped["status"], "failed")
        self.assertIn("wrapped-heading-number-missing", issue_kinds)
        self.assertIn("clipped-leading-label", issue_kinds)
        self.assertIn("leading-text-missing", issue_kinds)

    def test_wrapped_heading_page_audit_ignores_title_repeated_in_body_prose(self) -> None:
        title = "State-dependency proof for Dynamic programming"
        report = stem_course.notes_page_text_integrity_report(
            {
                10: """
15.3 State-dependency proof
for Dynamic programming
Proof 15.1. The recurrence follows from the final decision.
""",
                11: """
The earlier state-dependency proof for Dynamic programming can now be reused.
""",
            },
            [title],
            [],
            {title: "15.3"},
        )

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["title_pages"][title], 10)

    def test_wrapped_heading_page_audit_keeps_duplicate_titles_distinct_by_number(self) -> None:
        title = "Dependency induction for Memoized Dynamic Programming"
        report = stem_course.notes_page_text_integrity_report(
            {
                14: "14.3 Dependency induction\nfor Memoized Dynamic Programming\nProof 14.1.",
                21: "21.3 Dependency induction\nfor Memoized Dynamic Programming\nProof 21.1.",
            },
            [
                {"title": title, "number": "14.3"},
                {"title": title, "number": "21.3"},
            ],
            [],
        )

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["title_pages"][f"14.3 {title}"], 14)
        self.assertEqual(report["title_pages"][f"21.3 {title}"], 21)

    def test_probability_and_chemistry_use_field_quotes_without_source_line(self) -> None:
        probability = {"title": "Probability and Statistics", "materials": []}
        chemistry = {"title": "General Chemistry", "materials": []}
        probability_plan = {"course_title": "Probability and Statistics", "shorts": []}
        chemistry_plan = {"course_title": "General Chemistry", "shorts": []}

        self.assertEqual(stem_course.opening_quote(probability, probability_plan)[1], "Pierre-Simon Laplace")
        self.assertEqual(stem_course.opening_quote(chemistry, chemistry_plan)[1], "Antoine Lavoisier")
        self.assertNotIn("1814", stem_course.latex_opening_quote_block(probability, probability_plan))
        self.assertNotIn("1789", stem_course.latex_opening_quote_block(chemistry, chemistry_plan))

    def test_warning_parser_counts_missing_glyphs_and_overfull_boxes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-warning-counts-") as temp:
            run = Path(temp)
            (run / "notes_tectonic.log").write_text(
                "warning: notes.tex:10: Missing character: There is no phi in font.\n"
                "warning: could not represent character phi in font.\n"
                "warning: notes.tex:20: Overfull \\hbox (8.0pt too wide)\n",
                encoding="utf-8",
            )

            counts = stem_course.latex_warning_counts_from_logs(run, ["notes_tectonic.log"])

            self.assertEqual(counts["missing_characters"], 2)
            self.assertEqual(counts["overfull_hboxes"], 1)
            self.assertEqual(counts["engine_warnings"], 3)
            self.assertFalse(stem_course.latex_warning_counts_are_clean(counts))
            self.assertTrue(stem_course.latex_warning_counts_are_clean({
                "latex_warnings": 0,
                "engine_warnings": 0,
                "missing_characters": 0,
                "overfull_hboxes": 0,
                "underfull_hboxes": 0,
            }))

    def test_offline_tectonic_bundle_is_used_by_notes_and_scene_math(self) -> None:
        with mock.patch.dict(stem_course.os.environ, {"TECTONIC_BUNDLE": "/tmp/tectonic-offline.zip"}):
            self.assertEqual(
                stem_course.tectonic_cached_bundle_args(),
                ["--bundle", "/tmp/tectonic-offline.zip", "--only-cached"],
            )
        with mock.patch.dict(stem_course.os.environ, {}, clear=True):
            self.assertEqual(stem_course.tectonic_cached_bundle_args(), [])

        helpers = stem_course.MANIM_SCENE_HELPERS
        self.assertIn('tectonic_bundle = _os.environ.get("TECTONIC_BUNDLE", "").strip()', helpers)
        self.assertIn('tectonic_command.extend(["--bundle", tectonic_bundle, "--only-cached"])', helpers)

    def test_publishable_compile_fails_when_wrapped_page_audit_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="notes-visual-gate-") as temp:
            run = Path(temp)
            latex_report = {
                "status": "ok",
                "engine": "tectonic",
                "executable": "/opt/homebrew/bin/tectonic",
                "pdf": "notes.pdf",
                "warning_counts": {
                    "latex_warnings": 0,
                    "engine_warnings": 0,
                    "missing_characters": 0,
                    "overfull_hboxes": 0,
                    "underfull_hboxes": 0,
                },
            }

            with (
                mock.patch.object(stem_course, "run_latex_engine", return_value=latex_report),
                mock.patch.object(
                    stem_course,
                    "run_notes_visual_integrity_audit",
                    return_value={"status": "failed", "issues": [{"kind": "leading-text-missing"}]},
                ),
            ):
                report = stem_course.compile_notes_pdf(run, {"shorts": []}, "latex")

            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["visual_integrity_status"], "failed")
            self.assertIn("raster integrity audit", report["message"])


if __name__ == "__main__":
    unittest.main()

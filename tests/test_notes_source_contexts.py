import unittest

from tools.notes_source_contexts import notes_source_contexts


def prose(topic: str, detail: str) -> str:
    return (
        f"{topic} is defined through a precise relationship between the relevant quantities. "
        f"{detail} This relationship matters because it determines how the system behaves. "
        "A worked derivation connects the assumptions to the result and explains each term. "
        "The conclusion can then be checked against a concrete example and its limiting cases. "
        "This gives enough detail to distinguish the concept from a passing mention elsewhere."
    )


class NotesSourceContextsTests(unittest.TestCase):
    def test_calendar_only_match_keeps_topic_without_source_metadata(self) -> None:
        pack = {
            "materials": [{
                "title": "Course calendar",
                "text": "Week 1 Vectors. Week 2 Contact Forces. Week 3 Momentum.",
            }],
        }

        contexts = notes_source_contexts(pack, "Contact Forces")

        self.assertEqual(contexts, ["Contact Forces"])
        self.assertNotIn("source", contexts[0].lower())
        self.assertNotIn("calendar", contexts[0].lower())

    def test_source_digest_metadata_cannot_supply_topic_grounding(self) -> None:
        pack = {"materials": [{
            "title": "Extraction record",
            "text": "source_digest: sha256=abc123 concept=Contact Forces",
        }]}

        self.assertEqual(notes_source_contexts(pack, "Contact Forces"), [])

    def test_rejects_navigation_calendar_and_problem_set_mentions(self) -> None:
        pack = {"materials": [
            {"title": "Course Calendar", "text": "Week 1 vectors. Week 2 eigenvalues. Week 3 diagonalization. " * 30},
            {"title": "Problem Set 2", "text": "Problem set 2 eigenvalues due date Friday. " * 30},
            {"title": "Lecture Notes", "text": "# Eigenvalues and eigenvectors\n\n" + prose("An eigenvalue", "For a matrix A, Av = lambda v for a nonzero eigenvector v.")},
        ]}
        contexts = notes_source_contexts(pack, "eigenvalues and eigenvectors")
        self.assertEqual(len(contexts), 1)
        self.assertIn("Av = lambda v", contexts[0])
        self.assertNotIn("due date", contexts[0].lower())

    def test_requires_proximity_for_broad_cs_tokens(self) -> None:
        unrelated = prose("Algorithms", "The first course unit studies sorting in arrays.") + " " + prose("Trees", "Much later, dynamic allocation is introduced.")
        strong = prose("Dynamic programming", "Overlapping subproblems are stored once and reused through a recurrence.")
        pack = {"materials": [
            {"title": "Early Course Overview", "text": unrelated},
            {"title": "Lecture 12", "text": "# Dynamic programming\n\n" + strong},
        ]}
        contexts = notes_source_contexts(pack, "dynamic programming")
        self.assertEqual(len(contexts), 1)
        self.assertIn("Overlapping subproblems", contexts[0])

    def test_selects_strong_physics_and_economics_sections(self) -> None:
        cases = [
            ("conservation of momentum", "# Conservation of momentum\n\n" + prose("Momentum", "In an isolated system, total momentum before and after a collision is equal."), "isolated system"),
            ("price elasticity of demand", "# Price elasticity of demand\n\n" + prose("Elasticity", "The percentage change in quantity demanded is divided by the percentage change in price."), "quantity demanded"),
        ]
        for concept, text, expected in cases:
            with self.subTest(concept=concept):
                contexts = notes_source_contexts({"materials": [{"title": "Lecture Notes", "text": text}]}, concept)
                self.assertEqual(len(contexts), 1)
                self.assertIn(expected, contexts[0])

    def test_output_is_deterministic_and_omits_sources(self) -> None:
        text = "# Bayes theorem\n\n" + prose("Bayes theorem", "The posterior combines a likelihood with a prior and normalizing evidence.") + "\nSources\nhttps://example.edu/book"
        pack = {"materials": [{"title": "Probability Notes", "text": text}]}
        first = notes_source_contexts(pack, "Bayes theorem")
        self.assertEqual(first, notes_source_contexts(pack, "Bayes theorem"))
        self.assertNotIn("Sources", first[0])
        self.assertNotIn("http", first[0])

    def test_mit_6006_weighted_shortest_paths_stops_before_footnote_hash_table_commentary(self) -> None:
        # Exact shape of the captured MIT 6.006 source: lecture prose and the
        # following footnote were flattened into one scraped text field.
        text = """Weighted Shortest Paths

Weighted shortest paths assign a numerical weight to every edge of a graph. The weight of a path is the sum of the weights of its edges. Single-source shortest paths ask for the minimum-weight path from a source vertex to every other vertex. Relaxation tests whether reaching v through u improves the current distance estimate, and predecessor pointers retain the corresponding paths. With nonnegative edge weights, Dijkstra's algorithm repeatedly extracts the vertex with minimum tentative distance. This greedy choice is safe because extending a path cannot make it shorter.
[1] Hash tables were discussed earlier in the course.
A hash table stores keys in slots selected by a hash function. Collisions require chaining or another resolution strategy. Expected lookup takes constant time under the usual hashing assumptions.

Bibliography
Cormen, Leiserson, Rivest, and Stein discuss weighted shortest paths and hash tables in separate chapters.
"""
        contexts = notes_source_contexts(
            {"materials": [{"title": "MIT 6.006 Introduction to Algorithms", "text": text}]},
            "weighted shortest paths",
        )

        self.assertEqual(len(contexts), 1)
        self.assertIn("predecessor pointers", contexts[0])
        self.assertIn("Dijkstra's algorithm", contexts[0])
        self.assertNotIn("Hash tables", contexts[0])
        self.assertNotIn("hash function", contexts[0])
        self.assertNotIn("Cormen", contexts[0])

    def test_topic_drift_stops_without_losing_neighboring_explanation(self) -> None:
        text = (
            "# Weighted shortest paths\n\n"
            "A weighted graph associates a cost with each edge. "
            "A path cost is the sum of those edge costs, so relaxation compares a known distance with a route through the current vertex. "
            "The predecessor changes only when that candidate route is smaller. "
            "Repeated relaxation therefore builds the shortest-path evidence used by the algorithm. "
            "Hash tables organize keys by bucket index. "
            "Collisions in a bucket can be resolved with chaining. "
            "A good hash family spreads stored keys across the table."
        )

        context = notes_source_contexts(
            {"materials": [{"title": "Lecture notes", "text": text}]},
            "weighted shortest paths",
        )[0]

        self.assertIn("predecessor changes", context)
        self.assertIn("Repeated relaxation", context)
        self.assertNotIn("Hash tables", context)
        self.assertNotIn("Collisions", context)

    def test_rejects_transcript_player_navigation_and_browser_download_noise(self) -> None:
        noisy = """Skip to main content
Browse course material
Transcript player
Weighted shortest paths weighted shortest paths. Play playback speed 1x. Download transcript. Previous lecture Next lecture.
Your browser is out of date. Update your browser. Download video.
"""
        substantive = "# Weighted shortest paths\n\n" + prose(
            "Weighted shortest paths",
            "Relaxation lowers a tentative distance when an edge provides a cheaper route.",
        )
        contexts = notes_source_contexts({"materials": [
            {"title": "Video transcript", "text": noisy},
            {"title": "Lecture notes", "text": substantive},
        ]}, "weighted shortest paths")

        self.assertEqual(len(contexts), 1)
        self.assertIn("Relaxation lowers", contexts[0])
        self.assertNotIn("playback", contexts[0].lower())
        self.assertNotIn("download", contexts[0].lower())

    def test_flattened_navigation_keeps_neighboring_lecture_prose(self) -> None:
        flattened = (
            "Browse course material. Transcript player. "
            "Conservation of momentum applies when the selected system receives no net external impulse. "
            "The vector sum before the interaction equals the vector sum afterward. "
            "Choose the system boundary before assigning internal and external forces. "
            "Integrating the external force over time gives the external impulse. "
            "A component calculation must use one inertial frame and one sign convention throughout. "
            "The resulting balance can be checked component by component against the initial data. "
            "Playback speed. Download transcript. Previous lecture. Next lecture."
        )
        contexts = notes_source_contexts(
            {"materials": [{"title": "Lecture transcript", "text": flattened}]},
            "conservation of momentum",
        )

        self.assertEqual(len(contexts), 1)
        self.assertIn("no net external impulse", contexts[0])
        self.assertIn("Choose the system boundary", contexts[0])
        self.assertGreaterEqual(len(contexts[0].split()), 45)
        self.assertNotRegex(
            contexts[0].lower(),
            r"transcript|playback|download|previous lecture|next lecture",
        )


if __name__ == "__main__":
    unittest.main()

import json
import textwrap

import pytest

import build_notes
import ingest
import reels
import run_status
from conftest import HAS_PYMUPDF, HAS_TEX, write_json


# ---------------------------------------------------------------- notes


def make_notes(tmp_path, unit_body):
    notes = tmp_path / "notes"
    (notes / "units").mkdir(parents=True)
    (notes / "notes.tex").write_text(textwrap.dedent(r"""
        \documentclass{article}
        \usepackage{amsmath,amsthm,tikz}
        \theoremstyle{definition}
        \newtheorem{definition}{Definition}[section]
        \newtheorem{example}[definition]{Example}
        \newtheorem{exercise}[definition]{Exercise}
        \newenvironment{solution}{\begin{proof}[Solution]}{\end{proof}}
        \begin{document}
        \input{units/u01}
        \end{document}
    """))
    (notes / "units" / "u01.tex").write_text(unit_body)
    return notes


def test_lint_flags_placeholders_code_math_and_unsolved_exercises(tmp_path):
    notes = make_notes(tmp_path, textwrap.dedent(r"""
        % unit: u01
        \section{Vectors}
        TODO write this. The matrix is [[1, 2], [3, 4]] and sqrt(2) appears.
        \begin{exercise} Compute something. \end{exercise}
    """))
    issues, stats = build_notes.lint(build_notes.tex_files(notes), notes)
    kinds = {i["kind"] for i in issues if i["severity"] == "error"}
    assert {"placeholder", "code-style-math", "unsolved-exercise", "no-worked-example"} <= kinds
    assert stats["units"][0]["exercises"] == 1


def test_lint_accepts_clean_unit(tmp_path):
    body = r"""
        % unit: u01
        \section{Vectors}
        A vector \(v = \begin{bmatrix}1\\2\end{bmatrix}\) has length \(\sqrt{5}\).
        \begin{example} Add \((1,2)+(3,4)=(4,6)\). \end{example}
        \begin{tikzpicture}\draw[->] (0,0) -- (1,2);\end{tikzpicture}
        \begin{exercise} Find \(2v\). \end{exercise}
        \begin{solution} \(2v=(2,4)\). \end{solution}
    """
    notes = make_notes(tmp_path, textwrap.dedent(body))
    issues, _ = build_notes.lint(build_notes.tex_files(notes), notes)
    assert not [i for i in issues if i["severity"] == "error"], issues


@pytest.mark.skipif(not (HAS_TEX and HAS_PYMUPDF), reason="needs a TeX engine and pymupdf")
def test_build_notes_compiles_and_reports(tmp_path):
    body = (r"% unit: u01" "\n" r"\section{Vectors}" "\n" + ("Vectors add tip to tail. " * 40) +
            "\n" r"\begin{example} \((1,2)+(3,4)=(4,6)\). \end{example}" "\n"
            r"\begin{tikzpicture}\draw[->] (0,0) -- (1,2);\end{tikzpicture}" "\n")
    make_notes(tmp_path, body)
    code = build_notes.main([str(tmp_path), "--no-preview"])
    report = json.loads((tmp_path / "notes" / "notes_report.json").read_text())
    assert code == 0, report["issues"]
    assert report["pages"] >= 1 and report["engine"] in {"tectonic", "latexmk", "pdflatex"}


# ---------------------------------------------------------------- ingest


def test_parse_html_skips_nav_and_titles_from_head():
    html = b"""<html><head><title>Lecture 3: Elimination | Linear Algebra | MIT</title></head>
    <body><nav>Home About Donate</nav><h1>Linear Algebra</h1><p>Elimination subtracts rows.</p>
    <a href="notes.pdf">Session summary (PDF)</a><a href="x.pdf">Download</a><footer>License</footer></body></html>"""
    text, links, title, anchors = ingest.parse_html(html, "text/html", "https://ocw.mit.edu/courses/x/pages/a/")
    assert title == "Lecture 3: Elimination"
    assert "Elimination subtracts rows." in text and "Donate" not in text and "License" not in text
    assert anchors["https://ocw.mit.edu/courses/x/pages/a/notes.pdf"] == "Session summary"
    assert "https://ocw.mit.edu/courses/x/pages/a/x.pdf" not in anchors


def test_boilerplate_lines_repeated_across_pages_are_removed():
    items = [{"html": True, "text": f"Course menu\nLicense: CC BY\nUnique content number {i}"} for i in range(6)]
    removed = ingest.strip_boilerplate(items)
    assert removed == 12
    assert all(it["text"].startswith("Unique content") for it in items)


def test_garbled_pdf_text_is_detected():
    assert ingest.looks_garbled("ÐÑÒÓ ÔÕÖ ×ØÙ ÚÛÜ " * 50)
    assert ingest.looks_garbled(" ".join(["qzx vbnm wrtp lkjh"] * 40))
    assert not ingest.looks_garbled("We find the nullspace of the matrix and then the rank is two. " * 20)
    assert not ingest.looks_garbled("我们有一个4乘4的矩阵，那么第一个问题就是要计算这个矩阵 A的行列式。" * 20)


def test_nav_sequence_and_filename_titles():
    html = b"""<html><head><title>Course</title></head><body><nav>
    <a href="/courses/c/pages/syllabus/">Syllabus</a><a href="/courses/c/s1/">The Geometry of Linear Equations</a>
    <a href="/courses/c/s2/">Elimination with Matrices</a><a href="/courses/c/s3/">Inverses</a>
    <a href="/courses/c/s4/">A = LU</a></nav><p>Body text.</p></body></html>"""
    _, _, _, _, nav = ingest.parse_html_full(html, "text/html", "https://ocw.mit.edu/courses/c/")
    assert [a for _, a in nav][:3] == ["Syllabus", "The Geometry of Linear Equations", "Elimination with Matrices"]
    assert ingest.filename_like("MIT18_06SCF11_Ses2.12sum.pdf") and not ingest.filename_like("Session summary")
    assert ingest.clean_anchor("MIT18_06SCF11_Ses2.12sum.pdf: Download File") == "MIT18_06SCF11_Ses2.12sum"


@pytest.mark.parametrize("url, kind", [
    ("https://x/courses/c/pages/syllabus/", "syllabus"),
    ("https://x/courses/c/resources/solving-ax-0-pivot-variables-special-solutions/", "page"),
    ("https://x/courses/c/final_ex.pdf", "exam"),
    ("https://x/courses/c/final_exs.pdf", "solution"),
    ("https://x/courses/c/resources/exam-1-review/", "review"),
    ("https://x/courses/c/MIT18_06SCF11_Ses1.3prob.pdf", "assignment"),
    ("https://x/courses/c/MIT18_06SCF11_ex1s.pdf", "solution"),
    ("https://x/courses/c/MIT18_06SCF11_ex1.pdf", "exam"),
    ("https://x/courses/c/MIT18_06SCF11_Ses2.12sum.pdf", "lecture-notes"),
])
def test_classify(url, kind):
    assert ingest.classify(url, "") == kind


@pytest.mark.parametrize("url, title, kind", [
    # MIT 6.006 (Spring 2020) names lecture-note PDFs <hash>_MIT6_006S20_lec9.pdf
    ("https://x/courses/c/196a95_MIT6_006S20_lec9.pdf", "Lecture 9: Breadth-First Search", "lecture-notes"),
    ("https://x/courses/c/ab12_MIT6_006S20_ps1.pdf", "Problem Session 1: Introduction to Algorithms", "assignment"),
    ("https://x/courses/c/ab12_MIT6_006S20_ps1_sol.pdf", "Problem Session 1 Solutions: Introduction to Algorithms",
     "solution"),
    ("https://x/courses/c/pages/practice-problems/", "Practice Problems", "assignment"),
    ("https://x/courses/c/resources/complete-solution-to-ax-b/", "Complete Solution to Ax = b", "page"),
    ("https://x/courses/c/sol.pdf", "Solutions to the exercises", "solution"),
])
def test_classify_with_titles(url, title, kind):
    assert ingest.classify(url, title) == kind


def test_index_sorts_numbers_naturally():
    titles = ["Lecture 10: DFS", "Lecture 2: Data Structures", "Lecture 1: Introduction"]
    assert sorted(titles, key=ingest.natural_key) == ["Lecture 1: Introduction", "Lecture 2: Data Structures",
                                                      "Lecture 10: DFS"]


def test_local_folder_ingest(tmp_path):
    src = tmp_path / "course"
    src.mkdir()
    (src / "lecture-notes-1.md").write_text("# Groups\n\n" + "A group is a set with an associative operation. " * 10)
    run = tmp_path / "run"
    assert ingest.main([str(src), "--run", str(run)]) == 0
    pack = json.loads((run / "source_pack.json").read_text())
    assert pack["stats"]["materials"] == 1
    assert pack["materials"][0]["kind"] == "lecture-notes"
    assert (run / pack["materials"][0]["file"]).read_text().startswith("# title:")


# ---------------------------------------------------------------- reels + status


def rendered_short(run, plan, index, approved=True):
    short = plan["shorts"][index - 1]
    sdir = run / "shorts" / f"{index:02d}-{short['slug']}"
    sdir.mkdir(parents=True)
    (sdir / "scene.py").write_text("BEATS = [('a', 'b')]\n")
    video = sdir / f"{sdir.name}.mp4"
    video.write_bytes(b"fake mp4 " + short["slug"].encode())
    digest = reels.sha256(video)
    write_json(sdir / "render_report.json", {"quality": "final", "video": video.name, "sha256": digest,
                                               "duration": 42.0, "issues": []})
    if approved:
        write_json(sdir / "review.json", {"status": "approved", "sha256": digest})
    return sdir


def test_reels_queue_only_takes_approved_and_composes_captions(plan_run):
    plan = json.loads((plan_run / "short_plan.json").read_text())
    rendered_short(plan_run, plan, 1, approved=True)
    rendered_short(plan_run, plan, 2, approved=False)
    assert reels.main(["queue", str(plan_run), "--public-base-url", "https://cdn.example.com/la"]) == 0
    queue = json.loads((plan_run / "reels_queue.json").read_text())
    assert [i["short_id"] for i in queue["items"]] == ["s01"]
    item = queue["items"][0]
    assert item["video_url"] == "https://cdn.example.com/la/01-ax-mixes-columns.mp4"
    assert "Part 1/2" in item["caption"] and "#math" in item["caption"]
    assert queue["skipped"] and "s02" in queue["skipped"][0]


def test_publish_dry_run_needs_no_credentials(plan_run, monkeypatch):
    plan = json.loads((plan_run / "short_plan.json").read_text())
    rendered_short(plan_run, plan, 1)
    reels.main(["queue", str(plan_run), "--public-base-url", "https://cdn.example.com/la/"])
    monkeypatch.delenv("IG_USER_ID", raising=False)
    assert reels.main(["publish", str(plan_run), "--dry-run"]) == 0
    results = json.loads((plan_run / "reels_results.json").read_text())["results"]
    assert results[0]["status"] == "dry-run"


def test_status_gate_tracks_staleness(plan_run):
    import check_plan

    check_plan.main([str(plan_run)])
    plan = json.loads((plan_run / "short_plan.json").read_text())
    s1 = rendered_short(plan_run, plan, 1)
    rendered_short(plan_run, plan, 2, approved=False)
    data = run_status.status(plan_run)
    assert data["stages"]["plan"]["state"] == "pass"
    states = {row["id"]: row["state"] for row in data["shorts"]}
    assert states == {"s01": "ready", "s02": "awaiting review"}
    assert not data["publish_ready"]
    # re-rendering (new bytes) voids the approval and the report hash
    (s1 / f"{s1.name}.mp4").write_bytes(b"changed")
    states = {row["id"]: row["state"] for row in run_status.status(plan_run)["shorts"]}
    assert states["s01"] == "stale render"
    # editing the plan makes the plan check stale
    (plan_run / "short_plan.json").write_text((plan_run / "short_plan.json").read_text() + "\n")
    assert run_status.status(plan_run)["stages"]["plan"]["state"] == "unchecked"


def test_shorts_only_gate_ignores_missing_notes(plan_run):
    import check_plan

    check_plan.main([str(plan_run)])
    plan = json.loads((plan_run / "short_plan.json").read_text())
    rendered_short(plan_run, plan, 1)
    rendered_short(plan_run, plan, 2)
    write_json(plan_run / "source_pack.json", {"stats": {"materials": 2, "total_chars": 60}, "warnings": []})
    full = run_status.status(plan_run)
    assert not full["publish_ready"] and any(b.startswith("notes:") for b in full["blockers"])
    only = run_status.status(plan_run, shorts_only=True)
    assert only["publish_ready"] and only["stages"]["notes"]["state"] == "missing"
    assert run_status.main([str(plan_run), "--gate", "--shorts-only"]) == 0
    assert run_status.main([str(plan_run), "--gate"]) == 1


@pytest.mark.skipif(not (HAS_TEX and HAS_PYMUPDF), reason="needs a TeX engine and pymupdf")
def test_partial_build_with_relative_path(tmp_path, monkeypatch):
    body = (r"% unit: u01" "\n" r"\section{Vectors}\label{sec:u01}" "\n" + ("Vectors add tip to tail. " * 40) +
            "\n" r"\begin{example} \((1,2)+(3,4)=(4,6)\). See Section~\ref{sec:u02} and~\ref{thm:u01-missing}. \end{example}" "\n")
    make_notes(tmp_path, body)
    monkeypatch.chdir(tmp_path.parent)
    code = build_notes.main([tmp_path.name, "--units", "u01", "--no-preview"])
    assert code == 1, "a missing label inside the built unit must be reported"
    assert (tmp_path / "notes" / "partial" / "u01" / "_partial_u01.pdf").exists()


# ---------------------------------------------------------------- papers


def test_paper_sections_are_detected_and_footnotes_ignored():
    text = "\n".join([
        "The Market for Lemons", "Abstract", "We study markets.", "I. INTRODUCTION", "Some prose.",
        "II. THE MODEL WITH AUTOMOBILES AS AN EXAMPLE", "A. The Automobiles Market", "3.2.1", "Scaled Dot-Product Attention",
        "1. Arrow's fine article, \"Uncertainty and Medical Care\" (American Eco-", "490 Quarterly journal of economics",
        "37 Y2 for ryots with no right of", "References",
    ])
    found = ingest.detect_sections(text)
    assert found == ["Abstract", "I. Introduction", "II. The model with automobiles as an example",
                     "A. The Automobiles Market", "3.2.1 Scaled Dot-Product Attention", "References"]


def test_running_heads_and_licence_lines_are_not_content_or_titles():
    words = ["apples", "bridges", "cosets", "dynamics", "entropy", "fields"]
    pages = [f"{400 + i} Quarterly journal of economics\nBody text about {w}.\nThis content downloaded from 1.2.3.4"
             for i, w in enumerate(words)]
    cleaned = ingest.strip_running_lines(pages)
    assert all("Quarterly" not in p and "downloaded" not in p and "Body text" in p for p in cleaned)
    head = "Provided proper attribution is provided, Google hereby grants permission\nAttention Is All You Need\n"
    assert ingest.first_heading(head) == "Attention Is All You Need"


def test_single_html_document_mode(tmp_path, monkeypatch):
    html = (b"<html><head><title>Short title</title></head><body><h1>The Anatomy of a Search Engine</h1>"
            b"<h2>1. Introduction</h2><p>" + b"Search engines index the web. " * 30 + b"</p><h2>2. System Features</h2>"
            b"<p>A googol is 10<sup>100</sup>.</p><h2>References</h2></body></html>")
    monkeypatch.setattr(ingest, "fetch", lambda url, *a, **k: (html, "text/html", url))
    run = tmp_path / "run"
    assert ingest.main(["https://example.edu/~x/google.html", "--run", str(run), "--single"]) == 0
    pack = json.loads((run / "source_pack.json").read_text())
    assert pack["course"]["type"] == "paper" and pack["course"]["title"] == "The Anatomy of a Search Engine"
    assert [s["title"] for s in pack["sequence"]] == ["1. Introduction", "2. System Features", "References"]
    assert "10^100" in (run / pack["materials"][0]["file"]).read_text()


REVIEW_MD = textwrap.dedent("""\
    ---
    title: How language models scale
    author: A. Writer and B. Writer
    ---
    # How language models scale

    ## Early evidence
    Hestness et al. (2017) found power laws across domains [1]; see also [2-3].

    ## Bigger models
    Kaplan and colleagues argued for growing parameters faster [@kaplan2020].

    ```
    ## a heading inside code is not a section
    ```

    ## Compute-optimal training
    The allocation was revised (Hoffmann et al., 2022)[^chin].

    ## References
    1. Hestness, J., Narang, S., et al. (2017). Deep Learning Scaling is Predictable, Empirically. arXiv:1712.00409
    2. Smith, A. (2019). A related result. https://example.org/smith
    3. Doe, J. (2018). Another one. doi:10.1000/xyz123.
    [@kaplan2020] Kaplan, J., et al. (2020). Scaling Laws for Neural Language Models. https://arxiv.org/abs/2001.08361

    [^chin]: Hoffmann, J., et al. (2022). Training Compute-Optimal Large Language Models. arXiv:2203.15556
    """)


def test_markdown_literature_review_sections_and_citations(tmp_path):
    review = tmp_path / "review.md"
    review.write_text(REVIEW_MD)
    run = tmp_path / "run"
    assert ingest.main([str(review), "--run", str(run)]) == 0  # detected as a review without --review
    pack = json.loads((run / "source_pack.json").read_text())
    assert pack["course"]["type"] == "review" and pack["course"]["title"] == "How language models scale"
    assert pack["course"]["authors"] == ["A. Writer", "B. Writer"]
    assert [s["title"] for s in pack["sequence"]] == ["Early evidence", "Bigger models", "Compute-optimal training"]
    assert [s["cites"] for s in pack["sequence"]] == [["1", "2", "3"], ["kaplan2020"], ["chin"]]
    refs = {r["key"]: r for r in pack["references"]}
    assert refs["1"]["arxiv"] == "1712.00409" and refs["3"]["doi"] == "10.1000/xyz123"
    assert refs["kaplan2020"]["arxiv"] == "2001.08361" and refs["chin"]["year"] == "2022"
    index = (run / "sources" / "INDEX.md").read_text()
    assert "## Review sections" in index and "## Cited works" in index and "Bigger models  [kaplan2020]" in index


def test_author_year_citations_get_keys():
    refs = ingest.parse_references("- Kaplan, J. et al. (2020). Scaling Laws. arXiv:2001.08361\n"
                                   "- Hoffmann, J. et al. (2022). Compute-Optimal. arXiv:2203.15556\n")
    assert [r["key"] for r in refs] == ["kaplan2020", "hoffmann2022"]
    text = "Loss follows a power law (Kaplan et al., 2020); Hoffmann et al. (2022) changed the allocation."
    assert ingest.find_citations(text, refs) == ["kaplan2020", "hoffmann2022"]


def test_review_shorts_must_cite_known_works(plan_run):
    import check_plan

    outline = json.loads((plan_run / "outline.json").read_text())
    outline["course"]["type"] = "review"
    write_json(plan_run / "outline.json", outline)
    write_json(plan_run / "source_pack.json", {"references": [{"key": "kaplan2020"}, {"key": "hoffmann2022"}]})
    assert check_plan.main([str(plan_run)]) == 1
    errors = json.loads((plan_run / "plan_check.json").read_text())["errors"]
    assert any("'cites'" in e for e in errors)
    plan = json.loads((plan_run / "short_plan.json").read_text())
    plan["shorts"][0]["cites"] = ["kaplan2020", "hoffmann2022"]
    plan["shorts"][1]["cites"] = ["chinchilla"]
    write_json(plan_run / "short_plan.json", plan)
    assert check_plan.main([str(plan_run)]) == 1
    errors = json.loads((plan_run / "plan_check.json").read_text())["errors"]
    assert errors == ["short s02: cites [chinchilla], which is not in the review's reference list"]
    plan["shorts"][1]["cites"] = ["hoffmann2022"]
    write_json(plan_run / "short_plan.json", plan)
    assert check_plan.main([str(plan_run)]) == 0

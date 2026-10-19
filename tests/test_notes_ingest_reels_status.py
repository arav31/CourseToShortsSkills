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


@pytest.mark.skipif(not (HAS_TEX and HAS_PYMUPDF), reason="needs a TeX engine and pymupdf")
def test_partial_build_with_relative_path(tmp_path, monkeypatch):
    body = (r"% unit: u01" "\n" r"\section{Vectors}\label{sec:u01}" "\n" + ("Vectors add tip to tail. " * 40) +
            "\n" r"\begin{example} \((1,2)+(3,4)=(4,6)\). See Section~\ref{sec:u02} and~\ref{thm:u01-missing}. \end{example}" "\n")
    make_notes(tmp_path, body)
    monkeypatch.chdir(tmp_path.parent)
    code = build_notes.main([tmp_path.name, "--units", "u01", "--no-preview"])
    assert code == 1, "a missing label inside the built unit must be reported"
    assert (tmp_path / "notes" / "partial" / "u01" / "_partial_u01.pdf").exists()

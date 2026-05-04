#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_FETCH_BYTES = 1_500_000
DEFAULT_MAX_PAGES = 80
DEFAULT_MAX_PDFS = 40
DEFAULT_SHORTS = 30
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


@dataclass(frozen=True)
class Concept:
    name: str
    hook: str
    intuition: str
    formula: str
    prerequisites: list[str]
    misconception: str
    example_setup: str
    example_calc: str
    example_takeaway: str
    application_question: str
    application_answer: str
    visual_type: str


LINEAR_ALGEBRA: list[Concept] = [
    Concept("Vectors and coordinates", "A vector is a quantity with direction, size, and coordinates you can compute with.", "Coordinates tell how much of each basis direction builds the vector.", r"\vec{x}=(x_1,x_2,\ldots,x_n)", ["numbers", "coordinate axes", "arrows"], "A vector is not just an arrow drawing; coordinates depend on the chosen basis.", "Let v = (3, 4), meaning 3 steps east and 4 steps north.", "Length = sqrt(3^2 + 4^2) = sqrt(25) = 5.", "Coordinates tell direction; length tells straight-line size.", "A drone moves 3 meters east and 4 meters north. What is its displacement vector and length?", "Use (3, 4); the length is 5.", "vector_components"),
    Concept("Linear combinations and span", "Span asks what you can build by mixing fixed vectors.", "A linear combination scales vectors and adds them; the span is every reachable mix.", r"c_1\vec{v}_1+c_2\vec{v}_2+\cdots+c_k\vec{v}_k", ["vectors", "scalar multiplication", "addition"], "Span means every possible combination, not just the vectors drawn.", "Use a = (1, 0) and b = (1, 1). Can we reach (5, 2)?", "3a + 2b = 3(1, 0) + 2(1, 1) = (5, 2).", "The target is in the span because weights exist.", "A robot can move by (1,0) and (1,1). Which points can it reach?", "All points in the plane, because the directions are independent.", "linear_combination"),
    Concept("Matrix-vector multiplication", "Matrix-vector multiplication is a weighted recipe using the columns.", "Ax is a linear combination of columns of A, with x entries as weights.", r"A\vec{x}=x_1\vec{a}_1+\cdots+x_n\vec{a}_n", ["linear combinations", "columns", "vectors"], "Do not see Ax as random row arithmetic first; column combinations explain meaning.", "Let A = [[2, 1], [1, 3]] and x = (4, 2).", "Ax = (2*4 + 1*2, 1*4 + 3*2) = (10, 10).", "The output is a weighted mix of matrix columns.", "If A stores ad effects and x is budget, what does Ax mean?", "It predicts response as a weighted combination of ad-effect columns.", "matrix_vector"),
    Concept("Systems of linear equations", "A linear system is a set of constraints asking for one point.", "Solving Ax=b means finding coefficients that combine columns of A to make b.", r"A\vec{x}=\vec{b}", ["equations", "vectors", "matrix notation"], "A system can have no solution, one solution, or infinitely many.", "Solve 2x + y = 7 and x + y = 5.", "Subtract equations: x = 2. Then y = 3.", "The point (2, 3) satisfies both constraints.", "How can Ax=b model bundle counts matching a target order?", "Columns are bundle contents, x gives counts, and b is the target.", "systems"),
    Concept("Gaussian elimination", "Elimination removes one variable at a time until structure is visible.", "Row operations preserve the solution set while simplifying the matrix.", r"U\vec{x}=\vec{c}", ["systems", "row operations", "pivots"], "Elimination changes representation, not the solution set.", "Start with 2x + y = 7 and x + y = 5.", "Replace row1 by row1 - row2 to get x = 2; then y = 3.", "Equivalent equations can be easier to solve.", "How would elimination help solve several current-balance equations?", "It preserves feasible currents while simplifying variables in order.", "elimination"),
    Concept("Pivot columns", "Pivots mark where the system finds new directions.", "Pivot positions identify independent columns and basic variables.", r"\operatorname{rank}(A)=r", ["elimination", "columns", "independence"], "Pivot columns refer back to original columns, not the changed reduced columns.", "Reduce a matrix to [[1, 2, 0], [0, 0, 1]].", "Leading entries are in columns 1 and 3.", "Columns 1 and 3 are pivot columns.", "In a dataset, what does a pivot feature suggest?", "It contributes a new direction not explained by earlier pivot features.", "elimination"),
    Concept("Column space", "The column space is the set of targets your matrix can reach.", "Every Ax is a combination of columns, so Ax=b is solvable when b is in that span.", r"C(A)=\operatorname{span}\{\vec{a}_1,\ldots,\vec{a}_n\}", ["span", "linear combinations", "systems"], "Column space lives in output space, not input space.", "Let a1=(1,0), a2=(1,1), b=(3,2).", "b = 1*a1 + 2*a2 = (3, 2).", "b is reachable because it is a column combination.", "How do you tell whether a machine can produce a requested output?", "Check whether the target lies in the column space.", "subspace"),
    Concept("Nullspace", "The nullspace is everything a matrix sends to zero.", "Nullspace directions disappear under A.", r"A\vec{x}=0", ["matrix-vector multiplication", "homogeneous systems"], "The zero vector is always there; the question is whether anything else is.", "Let A=[1 1] and x=(2,-2).", "Ax = 1*2 + 1*(-2) = 0.", "The nonzero vector disappears under A.", "What does a nullspace image-change vector mean for a filter?", "The filter does not notice that change.", "subspace"),
    Concept("Linear independence", "Independent vectors bring genuinely new directions.", "No vector in an independent set can be built from the others.", r"c_1\vec{v}_1+\cdots+c_k\vec{v}_k=0 \Rightarrow c_i=0", ["linear combinations", "span", "zero vector"], "Independence is about redundancy, not visual distance.", "Compare v1=(1,0), v2=(2,0), w=(0,1).", "v2=2v1, so v1 and v2 are dependent; v1 and w are independent.", "A new direction cannot be a scaled repeat.", "Why are height in inches and centimeters not independent features?", "One is a scalar multiple of the other.", "linear_combination"),
    Concept("Bases and dimension", "A basis is a minimal vocabulary for a vector space.", "A basis spans with no redundancy; dimension counts basis vectors.", r"\dim(V)=k", ["span", "linear independence", "vector spaces"], "A basis is not unique; dimension is.", "In the plane, e1=(1,0), e2=(0,1).", "(4,7)=4e1+7e2, so they span with no redundancy.", "The plane has dimension 2.", "Why can a game position use many coordinate systems but dimension stays 2?", "Every basis for the plane needs exactly two directions.", "basis"),
    Concept("Rank-nullity", "Rank-nullity is the dimension budget of a matrix.", "Pivot directions plus free directions account for all input dimensions.", r"\operatorname{rank}(A)+\operatorname{nullity}(A)=n", ["rank", "nullspace", "dimension"], "It counts input dimensions, not rows.", "A has 3 input variables and rank(A)=2.", "rank + nullity = 3, so nullity = 1.", "One input direction is invisible to the output.", "A 10-variable model has rank 7. How many free directions remain?", "Nullity is 3.", "dimension_bar"),
    Concept("Linear transformations", "A matrix is a machine that moves space.", "A linear transformation preserves linear combinations; basis vectors determine everything.", r"T(cu+dv)=cT(u)+dT(v)", ["vectors", "functions", "basis"], "If grid lines bend or the origin moves, it is not linear in this strict sense.", "Let A=[[2,0],[0,1]] and x=(3,4).", "Ax=(6,4): x doubles and y stays fixed.", "Watch basis directions to know every vector's movement.", "Why do graphics use matrices for rotations and scalings?", "They preserve linear combinations, so basis movement controls the whole scene.", "transform_grid"),
    Concept("Matrix multiplication", "Matrix multiplication is function composition wearing a grid costume.", "AB means do B, then A; the order matters.", r"C=AB", ["linear transformations", "basis vectors"], "Order matters because transformations usually do not commute.", "A scales x by 2; B sends (x,y) to (x+y,y).", "AB(1,2)=A(3,2)=(6,2), but BA(1,2)=B(2,2)=(4,2).", "Changing order changes the result.", "Why does rotate-then-scale differ from scale-then-rotate?", "The second transformation receives a different input.", "transform_grid"),
    Concept("Invertibility", "An invertible matrix is a transformation you can perfectly undo.", "Each output has exactly one input.", r"A^{-1}A=I", ["linear transformations", "systems", "rank"], "A square matrix can still flatten space and fail to be invertible.", "A=[[2,0],[0,3]] sends (x,y) to (2x,3y).", "Undo (8,15) by computing (8/2,15/3)=(4,5).", "No information was lost.", "Why is blur usually not invertible?", "Many original images can produce the same blurred output.", "transform_grid"),
    Concept("Determinants", "The determinant is the signed area or volume scale factor.", "It says how much a linear transformation scales area and whether orientation flips.", r"\det(A)", ["linear transformations", "area", "orientation"], "A zero determinant means space was flattened.", "A=[[2,0],[0,3]].", "det(A)=2*3-0*0=6.", "A unit square becomes area 6.", "What does determinant 3 mean in a 2D transform?", "Every area is scaled by 3, up to orientation sign.", "area"),
    Concept("Change of basis", "Change of basis translates the same vector into a different coordinate language.", "The geometric vector stays fixed while coordinate numbers change.", r"[\vec{x}]_B=P^{-1}\vec{x}", ["bases", "coordinates", "invertible matrices"], "Changing coordinates is not moving the vector itself.", "Use b1=(1,1), b2=(1,-1) for v=(4,2).", "v=3b1+1b2=(4,2).", "The vector stayed fixed; coordinates changed.", "What stays the same when a map changes coordinate axes?", "The physical displacement vector.", "basis"),
    Concept("Dot products", "The dot product measures alignment.", "It combines length and angle to detect component in a direction.", r"\vec{u}\cdot\vec{v}=\|u\|\|v\|\cos\theta", ["vectors", "angles"], "A large dot product can mean long vectors or strong alignment.", "F=(3,4), d=(1,0).", "F dot d = 3*1 + 4*0 = 3.", "Only the component along motion contributes.", "How does dot product decide work from angled force?", "It keeps only the aligned component.", "projection"),
    Concept("Orthogonality", "Orthogonality is independence with a right angle.", "Orthogonal vectors have dot product zero.", r"\vec{u}\cdot\vec{v}=0", ["dot product", "geometry"], "Orthogonal does not mean unit length.", "u=(2,1), v=(1,-2).", "u dot v = 2*1 + 1*(-2)=0.", "The directions are perpendicular.", "How can you check whether two signals are orthogonal?", "Compute their dot product under the chosen inner product.", "projection"),
    Concept("Projection", "Projection is a vector dropping its shadow onto a direction.", "It keeps only the component in a chosen subspace.", r"\operatorname{proj}_u(v)=\frac{v\cdot u}{u\cdot u}u", ["dot product", "vectors"], "Projection is not just shrinking; it chooses information to keep.", "Project v=(3,4) onto u=(1,0).", "proj_u(v) = 3(1,0) = (3,0).", "The perpendicular part is discarded.", "How does projection explain a 3D object's 2D shadow?", "It keeps screen-direction components and discards depth.", "projection"),
    Concept("Least squares", "When no exact answer exists, least squares finds the closest one.", "It minimizes total squared residual error.", r"A^TA\hat{x}=A^Tb", ["projection", "column space"], "It minimizes total squared error, not every single error.", "Fit one constant c to y=2,4,5.", "c=(2+4+5)/3=11/3.", "The best constant is the average.", "What does least squares minimize for noisy points?", "The sum of squared residuals.", "least_squares"),
    Concept("Gram-Schmidt", "Gram-Schmidt turns messy independent vectors into perpendicular ones.", "It repeatedly subtracts projections already explained.", r"q_i=\frac{v_i-\operatorname{proj}(v_i)}{\|v_i-\operatorname{proj}(v_i)\|}", ["projection", "orthogonality", "bases"], "It changes basis vectors but preserves the span.", "Start with v1=(1,0), v2=(1,1).", "v2 - proj_v1(v2) = (1,1)-(1,0)=(0,1).", "The result is perpendicular and spans the same plane.", "Why prefer orthonormal axes in simulation?", "They make projections and lengths stable.", "projection"),
    Concept("QR factorization", "QR separates clean directions from coordinates.", "Q stores orthonormal directions; R stores upper-triangular coordinates.", r"A=QR", ["Gram-Schmidt", "matrix multiplication"], "Q must have orthonormal columns.", "A has columns a1=(1,0), a2=(1,1).", "Gram-Schmidt gives q1=(1,0), q2=(0,1), R=[[1,1],[0,1]].", "Q stores directions; R stores coordinates.", "Why is QR useful for least squares?", "It turns the problem into a stable triangular solve.", "matrix_factor"),
    Concept("Eigenvectors", "Most vectors turn; eigenvectors only stretch.", "An eigenvector's direction survives a transformation.", r"A\vec{v}=\lambda\vec{v}", ["transformations", "scalar multiplication"], "Eigenvectors depend on the transformation.", "A=[[2,0],[0,3]], v=(1,0).", "Av=(2,0)=2v.", "v is an eigenvector with lambda=2.", "In a population model, what can an eigenvector represent?", "A stable direction that only scales after transition.", "eigen"),
    Concept("Eigenvalues", "An eigenvalue is the stretch factor attached to an eigenvector.", "It tells how much the surviving direction scales or flips.", r"A\vec{v}=\lambda\vec{v}", ["eigenvectors", "linear transformations"], "Eigenvalues alone are not the whole transformation.", "A=[[2,0],[0,3]], v=(0,1).", "Av=(0,3)=3v.", "The stretch factor is 3.", "What can eigenvalues tell you in vibrations?", "Natural scaling or frequency behavior of modes.", "eigen"),
    Concept("Diagonalization", "Diagonalization changes coordinates so a matrix becomes scaling.", "In an eigenbasis, repeated matrix powers become powers of eigenvalues.", r"A=S\Lambda S^{-1}", ["eigenvectors", "basis"], "Not every matrix has enough eigenvectors.", "If A=diag(2,3), compute A^5 on x=(1,1).", "A^5x=(2^5,3^5)=(32,243).", "Repeated multiplication becomes repeated scaling.", "Why does diagonalization simplify A^50?", "It reduces powers to eigenvalue powers.", "eigen"),
    Concept("Positive definite matrices", "Positive definite matrices make bowls instead of saddles.", "x^T A x is positive in every nonzero direction.", r"\vec{x}^TA\vec{x}>0", ["quadratic forms", "eigenvalues"], "Positive entries do not guarantee positive definiteness.", "A=[[2,0],[0,1]], x=(3,4).", "x^T A x = 2*3^2 + 1*4^2 = 34 > 0.", "Every nonzero direction gives positive height.", "Why do they matter in optimization?", "They give bowl-shaped problems with a unique minimum.", "quadratic"),
    Concept("Markov matrices", "A Markov matrix moves probability without losing it.", "Multiplying by the transition matrix updates a state distribution.", r"\vec{x}_{k+1}=P\vec{x}_k", ["matrix multiplication", "probability"], "It is about conserved total probability, not arbitrary transitions.", "P=[[0.8,0.3],[0.2,0.7]], x=(100,0).", "Px=(80,20).", "Population moved between states without losing total.", "How can this model users moving between app states?", "Entries are transition probabilities; multiplication updates the distribution.", "markov"),
    Concept("Singular value decomposition", "SVD says every matrix is rotate, stretch, rotate.", "It ranks transformation directions by importance.", r"A=U\Sigma V^T", ["orthogonality", "eigenvectors"], "SVD works for non-square matrices too.", "An image matrix has singular values 10, 2, 0.5.", "Keeping only 10 gives a rank-1 approximation.", "Large singular values preserve strongest structure.", "How does SVD compress an image?", "Keep large singular values and discard small detail.", "svd"),
]


class HtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self.skip += 1
            return
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag in {"title", "h1", "h2", "h3", "p", "li", "td", "th"}:
            self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"} and self.skip:
            self.skip -= 1
        elif tag in {"title", "h1", "h2", "h3", "p", "li", "td", "th"}:
            self.text.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            cleaned = re.sub(r"\s+", " ", data).strip()
            if cleaned:
                self.text.append(cleaned)

    def clean_text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", " ".join(self.text)).strip()


def slugify(text: str, fallback: str = "course") -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or fallback


def plain_math(value: str) -> str:
    replacements = [
        (r"\operatorname", ""),
        (r"\cdots", "..."),
        (r"\ldots", "..."),
        (r"\Rightarrow", "=>"),
        (r"\lambda", "lambda"),
        (r"\Sigma", "Sigma"),
        (r"\vec", ""),
        (r"\hat", ""),
        (r"\cdot", " dot "),
        (r"\frac", "frac"),
        (r"\det", "det"),
        (r"\dim", "dim"),
    ]
    out = value
    for old, new in replacements:
        out = out.replace(old, new)
    out = out.replace("{", "").replace("}", "")
    out = out.replace("=", " = ")
    return re.sub(r"\s+", " ", out).strip()


def fetch_bytes(url: str, accept: str = "*/*") -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "course-shorts-skills/0.1", "Accept": accept})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read(MAX_FETCH_BYTES), response.headers.get("Content-Type", ""), response.geturl()


def parse_html(raw: bytes, content_type: str, base: str) -> tuple[str, list[str]]:
    encoding = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        encoding = match.group(1)
    parser = HtmlExtractor()
    parser.feed(raw.decode(encoding, errors="replace"))
    links = []
    for link in parser.links:
        normalized = urllib.parse.urljoin(base, link).split("#", 1)[0]
        if normalized and normalized not in links:
            links.append(normalized)
    return parser.clean_text(), links


def pdf_text(raw: bytes) -> str:
    try:
        import fitz  # type: ignore
    except Exception:
        return ""
    doc = fitz.open(stream=raw, filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc[:35])


def title_from_url(url: str) -> str:
    parts = [part for part in urllib.parse.urlparse(url).path.split("/") if part]
    name = parts[-1] if parts else "course"
    name = re.sub(r"-spring-\d{4}|-fall-\d{4}|-january-iap-\d{4}", "", name)
    name = re.sub(r"^\d+[-.]?\d*\w*-?", "", name)
    return name.replace("-", " ").strip().title() or "Course"


def course_prefix(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if "courses" in parts:
        idx = parts.index("courses")
        parts = parts[: idx + 2]
    else:
        parts = parts[:2]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(parts), "", "", ""))


def link_score(url: str) -> int:
    lower = url.lower()
    score = 0
    for term in ("syllabus", "lecture", "note", "resource", "problem", "assignment", "exam", "transcript", "pdf"):
        if term in lower:
            score += 3
    if lower.endswith(".pdf"):
        score += 5
    return score


def sample_pack() -> dict[str, object]:
    return {
        "title": "Linear Algebra",
        "source_url": "sample:linear_algebra",
        "materials": [
            {"kind": "sample", "title": "Linear Algebra core sample", "url": "sample:linear_algebra", "text": "Vectors, linear combinations, matrix-vector multiplication, systems, elimination, column space, nullspace, projections, least squares, eigenvectors, eigenvalues, SVD."}
        ],
        "warnings": [],
    }


def cmd_extract(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.sample:
        pack = sample_pack()
        write_json(out / "source_pack.json", pack)
        print(out / "source_pack.json")
        return

    root = args.url
    prefix = course_prefix(root)
    parsed_root = urllib.parse.urlparse(root)
    materials: list[dict[str, str]] = []
    warnings: list[str] = []
    seen: set[str] = set()
    try:
        raw, ctype, final = fetch_bytes(root, "text/html,text/plain,application/xhtml+xml")
        text, links = parse_html(raw, ctype, final)
    except Exception as exc:
        raise SystemExit(f"extract failed: {exc}")
    materials.append({"kind": "page", "title": "Course landing page", "url": final, "text": text[:120_000]})
    seen.add(final)

    def allowed(link: str) -> bool:
        parsed = urllib.parse.urlparse(link)
        return parsed.scheme in {"http", "https"} and parsed.netloc == parsed_root.netloc and link.startswith(prefix)

    candidates = sorted([link for link in links if allowed(link)], key=link_score, reverse=True)
    pages = 0
    pdfs = 0
    cursor = 0
    while cursor < len(candidates) and (pages < args.max_pages or pdfs < args.max_pdfs):
        url = candidates[cursor]
        cursor += 1
        if url in seen:
            continue
        try:
            raw, ctype, final = fetch_bytes(url)
        except Exception:
            continue
        seen.add(url)
        lower = final.lower()
        if "pdf" in ctype.lower() or lower.endswith(".pdf"):
            if pdfs >= args.max_pdfs:
                continue
            text = pdf_text(raw)
            if text.strip():
                pdfs += 1
                materials.append({"kind": "pdf", "title": Path(urllib.parse.urlparse(final).path).name or "PDF", "url": final, "text": text[:120_000]})
            else:
                warnings.append(f"Could not extract PDF text: {final}")
        elif "html" in ctype.lower() or raw[:200].lower().lstrip().startswith((b"<!doctype", b"<html")):
            if pages >= args.max_pages:
                continue
            text, nested = parse_html(raw, ctype, final)
            if text.strip():
                pages += 1
                materials.append({"kind": "page", "title": title_from_url(final), "url": final, "text": text[:120_000]})
            for link in nested:
                if allowed(link) and link not in seen and link not in candidates:
                    candidates.append(link)
    pack = {"title": title_from_url(root), "source_url": root, "materials": materials, "warnings": warnings}
    write_json(out / "source_pack.json", pack)
    print(out / "source_pack.json")


def choose_concepts(pack: dict[str, object], max_shorts: int) -> list[Concept]:
    text = json.dumps(pack).lower()
    if any(term in text for term in ("linear algebra", "matrix", "eigen", "vector")):
        return LINEAR_ALGEBRA[:max_shorts]
    terms = frequent_terms(" ".join(str(m.get("text", "")) for m in pack.get("materials", []) if isinstance(m, dict)))
    concepts: list[Concept] = []
    for term in terms[:max_shorts]:
        title = term.title()
        concepts.append(Concept(title, f"{title} is a core idea in this course.", f"Understand {title} by connecting definition, formula, and example.", title, ["course definitions", "worked examples"], "Do not memorize the term without testing it on a concrete example.", f"Pick a small numerical or symbolic example involving {title}.", "Work through one substitution or transformation step.", "The example should make the definition testable.", f"Where does {title} appear in an application from the course?", "Name the inputs, rule, and output.", "generic"))
    return concepts


def frequent_terms(text: str) -> list[str]:
    stop = {"course", "lecture", "the", "and", "for", "with", "this", "that", "from", "have", "notes", "page", "problem", "example"}
    counts: dict[str, int] = {}
    for word in re.findall(r"\b[a-zA-Z][a-zA-Z-]{4,}\b", text.lower()):
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)]


def cmd_plan(args: argparse.Namespace) -> None:
    run = Path(args.run)
    pack = read_json(run / "source_pack.json")
    concepts = choose_concepts(pack, args.max_shorts)
    plan = {
        "course_title": pack.get("title", "Course"),
        "source_url": pack.get("source_url"),
        "shorts": [
            {
                "index": i,
                "concept": c.name,
                "hook": c.hook,
                "intuition": c.intuition,
                "formula": c.formula,
                "plain_formula": plain_math(c.formula),
                "prerequisites": c.prerequisites,
                "misconception": c.misconception,
                "worked_example": {"setup": c.example_setup, "calculation": c.example_calc, "takeaway": c.example_takeaway},
                "question_prompt": {"question": c.application_question, "answer": c.application_answer},
                "visual_type": c.visual_type,
            }
            for i, c in enumerate(concepts, start=1)
        ],
    }
    write_json(run / "short_plan.json", plan)
    print(run / "short_plan.json")


def latex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("$", r"\$")
             .replace("#", r"\#").replace("_", r"\_").replace("{", r"\{").replace("}", r"\}"))


def cmd_notes(args: argparse.Namespace) -> None:
    run = Path(args.run)
    pack = read_json(run / "source_pack.json")
    plan = read_json(run / "short_plan.json")
    title = str(plan.get("course_title") or pack.get("title") or "Course")
    materials = pack.get("materials", [])
    source_inventory = "\n".join(
        rf"\item \textbf{{{latex_escape(str(m.get('kind', 'source')).upper())}}}: {latex_escape(str(m.get('title', 'Untitled')))}\\ {latex_escape(str(m.get('url', '')))}"
        for m in materials if isinstance(m, dict)
    )
    shorts = plan["shorts"]
    course_map = "\n".join(
        rf"\item \textbf{{{short['index']}. {latex_escape(short['concept'])}}}: prerequisites -- {latex_escape(', '.join(short.get('prerequisites', [])) or 'none')}. Outcome -- {latex_escape(short['intuition'])}"
        for short in shorts
    )
    formula_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & ${{{short['formula']}}}$ & {latex_escape(short['plain_formula'])} \\" 
        for short in shorts
    )
    sections = []
    practice_items = []
    for short in shorts:
        ex = short["worked_example"]
        qp = short["question_prompt"]
        prereqs = latex_escape(", ".join(short.get("prerequisites", [])) or "none")
        sections.append(rf"""
\subsection{{{latex_escape(short['concept'])}}}
\paragraph{{Prerequisites.}} {prereqs}

\begin{{definition}}
{latex_escape(short['intuition'])}
\end{{definition}}

\paragraph{{Why this matters.}} {latex_escape(short['hook'])}

\begin{{formula}}
\[
{short['formula']}
\]
\textbf{{Plain-language read:}} {latex_escape(short['plain_formula'])}.
\end{{formula}}

\begin{{example}}
\textbf{{Setup.}} {latex_escape(ex['setup'])}

\textbf{{Calculation.}} {latex_escape(ex['calculation'])}

\textbf{{Interpretation.}} {latex_escape(ex['takeaway'])}
\end{{example}}

\paragraph{{Visual model.}} This topic should be visualized with \texttt{{{latex_escape(short.get('visual_type', 'generic'))}}}: show the inputs, animate the rule, then highlight the resulting quantity or structure.

\begin{{warning}}
{latex_escape(short['misconception'])}
\end{{warning}}

\begin{{questions}}
\item Conceptual: Explain {latex_escape(short['concept'])} without using the formula. What problem does the idea solve?
\item Calculation: Recreate the worked example above, then change one number and predict how the answer changes.
\item Interpretation: Which part of the example is the input, which part is the rule, and which part is the output?
\item Application: {latex_escape(qp['question'])}
\item Error check: What mistake would someone make if they believed the common trap above?
\end{{questions}}

\paragraph{{Answers and explanations.}}
The calculation answer follows the worked example: {latex_escape(ex['calculation'])} The key interpretation is: {latex_escape(ex['takeaway'])} For the application question, {latex_escape(qp['answer'])}
""")
        practice_items.append(rf"\item \textbf{{{latex_escape(short['concept'])}.}} {latex_escape(qp['question'])} \emph{{Answer idea:}} {latex_escape(qp['answer'])}")
    tex = rf"""\documentclass[11pt]{{article}}
\usepackage[margin=0.75in]{{geometry}}
\usepackage{{amsmath,amssymb,amsthm,longtable,booktabs,xcolor,enumitem,hyperref}}
\definecolor{{courseblue}}{{HTML}}{{2D9CDB}}
\definecolor{{coursegold}}{{HTML}}{{F2C94C}}
\newtheorem{{definition}}{{Definition}}[section]
\newtheorem{{formula}}{{Formula}}[section]
\newtheorem{{example}}{{Example}}[section]
\newtheorem{{warning}}{{Common Trap}}[section]
\newenvironment{{questions}}{{\begin{{enumerate}}[label=\textbf{{Q\arabic*.}}, leftmargin=*]}}{{\end{{enumerate}}}}
\title{{{latex_escape(title)} Definitions, Formulas, and Worked Examples}}
\author{{Generated by Course Shorts Skills}}
\date{{\today}}
\begin{{document}}
\maketitle
\tableofcontents
\newpage

\section{{How To Use These Notes}}
Read the course map first, then work through the core concepts in order. For each topic, cover the definition, formula, worked example, common trap, and questions before moving on. The questions are designed to test conceptual understanding and practical application, not just memorization.

\section{{Source Inventory}}
\begin{{itemize}}
{source_inventory}
\end{{itemize}}

\section{{Course Map And Prerequisite Order}}
\begin{{enumerate}}[leftmargin=*]
{course_map}
\end{{enumerate}}

\section{{Formula Table}}
\begin{{longtable}}{{@{{}}p{{0.08\linewidth}}p{{0.24\linewidth}}p{{0.34\linewidth}}p{{0.26\linewidth}}@{{}}}}
\toprule
No. & Concept & Formula & Plain read \\
\midrule
\endhead
{formula_rows}
\bottomrule
\end{{longtable}}

\section{{Core Concepts}}
{''.join(sections)}

\section{{Cumulative Practice Bank}}
\begin{{enumerate}}[leftmargin=*]
{chr(10).join(practice_items)}
\end{{enumerate}}
\end{{document}}
"""
    (run / "notes.tex").write_text(tex, encoding="utf-8")
    (run / "notes.md").write_text(markdown_notes(plan), encoding="utf-8")
    if args.compile and shutil.which("pdflatex"):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "notes.tex"], cwd=run, check=False)
    print(run / "notes.tex")

def markdown_notes(plan: dict[str, object]) -> str:
    lines = [f"# {plan.get('course_title', 'Course')} Notes\n"]
    for short in plan["shorts"]:
        ex = short["worked_example"]
        lines.append(f"## {short['index']}. {short['concept']}\n")
        lines.append(f"**Definition.** {short['intuition']}\n")
        lines.append(f"**Formula.** `{short['plain_formula']}`\n")
        lines.append(f"**Worked example.** {ex['setup']} {ex['calculation']} {ex['takeaway']}\n")
        lines.append(f"**Question.** {short['question_prompt']['question']}\n")
    return "\n".join(lines)


def wrap(text: str, width: int = 34, lines: int = 4) -> list[str]:
    out = textwrap.wrap(text, width=width)
    if len(out) > lines:
        out = out[: lines - 1] + [out[lines - 1].rstrip(".") + "..."]
    return out or [""]


def manim_scene(short: dict[str, object], class_name: str) -> str:
    visual = str(short["visual_type"])
    setup = short["worked_example"]["setup"]
    calc = short["worked_example"]["calculation"]
    takeaway = short["worked_example"]["takeaway"]
    question = short["question_prompt"]["question"]
    visual_code = visual_template(visual)
    return f'''from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 9
config.frame_height = 16
config.background_color = "#0B1020"


class {class_name}(Scene):
    def text_block(self, lines, font_size=25, color="#EAF2FF"):
        return VGroup(*[Text(line, font_size=font_size, color=color) for line in lines]).arrange(DOWN, buff=0.11)

    def construct(self):
        self.camera.background_color = "#0B1020"
        title = Text({short["concept"]!r}, font_size=48, weight="BOLD", color="#EAF2FF").to_edge(UP, buff=0.55)
        hook = self.text_block({wrap(str(short["hook"]), 31, 3)!r}, font_size=28, color="#8FD3FF").next_to(title, DOWN, buff=0.25)
        self.play(FadeIn(title, shift=DOWN * 0.1), LaggedStart(*[FadeIn(x) for x in hook], lag_ratio=0.12), run_time=1.2)

{textwrap.indent(visual_code, "        ")}

        formula = self.text_block({wrap(plain_math(str(short["formula"])), 34, 2)!r}, font_size=30, color="#F7C948").move_to(DOWN * 4.25)
        intuition = self.text_block({wrap(str(short["intuition"]), 36, 3)!r}, font_size=24, color="#EAF2FF").move_to(DOWN * 5.35)
        self.play(Write(formula), run_time=0.9)
        self.play(FadeIn(intuition, shift=UP * 0.12), run_time=0.9)
        self.wait(3.0)
        self.play(*[FadeOut(m) for m in self.mobjects if m not in [title, hook]], run_time=0.7)

        card = RoundedRectangle(width=8.0, height=6.25, corner_radius=0.18, color="#58A6FF", fill_color="#101A33", fill_opacity=0.96)
        card.move_to(DOWN * 0.45)
        label = Text("Worked example", font_size=31, weight="BOLD", color="#F7C948").move_to(card.get_top() + DOWN * 0.48)
        setup = self.text_block({wrap("Setup: " + str(setup), 36, 4)!r}, font_size=22).next_to(label, DOWN, buff=0.36)
        calc = self.text_block({wrap("Calculate: " + str(calc), 36, 4)!r}, font_size=22, color="#8FD3FF").next_to(setup, DOWN, buff=0.48)
        take = self.text_block({wrap("So: " + str(takeaway), 36, 3)!r}, font_size=22, color="#7EE787").next_to(calc, DOWN, buff=0.48)
        self.play(FadeIn(card), FadeIn(label), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(x, shift=UP * 0.08) for x in setup], lag_ratio=0.12), run_time=1.2)
        self.wait(7.0)
        self.play(LaggedStart(*[FadeIn(x, shift=UP * 0.08) for x in calc], lag_ratio=0.12), run_time=1.2)
        self.wait(8.0)
        self.play(LaggedStart(*[FadeIn(x, shift=UP * 0.08) for x in take], lag_ratio=0.12), run_time=1.0)
        self.wait(6.0)
        self.play(FadeOut(card), FadeOut(label), FadeOut(setup), FadeOut(calc), FadeOut(take), run_time=0.7)

        recall = RoundedRectangle(width=8.0, height=5.7, corner_radius=0.18, color="#F7C948", fill_color="#1C1A10", fill_opacity=0.96).move_to(DOWN * 0.45)
        rtitle = Text("Active recall", font_size=31, weight="BOLD", color="#F7C948").move_to(recall.get_top() + DOWN * 0.5)
        prompt = self.text_block({wrap("Try: " + str(question), 36, 5)!r}, font_size=22).next_to(rtitle, DOWN, buff=0.45)
        answer = self.text_block({wrap("Answer idea: " + str(short["question_prompt"]["answer"]), 36, 4)!r}, font_size=21, color="#8FD3FF").next_to(prompt, DOWN, buff=0.55)
        self.play(FadeIn(recall), FadeIn(rtitle), FadeIn(prompt), run_time=1.0)
        self.wait(8.0)
        self.play(FadeIn(answer, shift=UP * 0.1), run_time=0.9)
        self.wait(7.0)
        self.play(Indicate(answer), run_time=0.8)
        self.wait(5.0)
'''


def visual_template(kind: str) -> str:
    if kind == "vector_components":
        return '''plane = NumberPlane(x_range=[-1,5,1], y_range=[-1,5,1], background_line_style={"stroke_color":"#1F3558","stroke_width":1,"stroke_opacity":0.7}).scale(0.82).shift(DOWN*0.85)
origin = plane.c2p(0,0)
end = plane.c2p(3,4)
vec = Arrow(origin, end, buff=0, color="#58A6FF", stroke_width=8)
x_leg = Arrow(origin, plane.c2p(3,0), buff=0, color="#F7C948", stroke_width=7)
y_leg = Arrow(plane.c2p(3,0), end, buff=0, color="#7EE787", stroke_width=7)
dash = DashedLine(plane.c2p(0,4), end, color="#EAF2FF", stroke_width=3)
labels = VGroup(Text("3", font_size=28, color="#F7C948").next_to(x_leg, DOWN), Text("4", font_size=28, color="#7EE787").next_to(y_leg, RIGHT), Text("length 5", font_size=28, color="#8FD3FF").next_to(vec, UP))
self.play(Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.2)
self.play(GrowArrow(vec), Create(dash), FadeIn(labels), run_time=1.3)
self.play(Indicate(labels[2]), run_time=0.8)'''
    if kind == "linear_combination":
        return '''plane = NumberPlane(x_range=[-1,6,1], y_range=[-1,4,1], background_line_style={"stroke_color":"#1F3558","stroke_width":1,"stroke_opacity":0.7}).scale(0.8).shift(DOWN*0.85)
origin = plane.c2p(0,0)
a = Arrow(origin, plane.c2p(1,0), buff=0, color="#58A6FF", stroke_width=7)
b = Arrow(origin, plane.c2p(1,1), buff=0, color="#F7C948", stroke_width=7)
three_a = Arrow(origin, plane.c2p(3,0), buff=0, color="#58A6FF", stroke_width=8)
two_b = Arrow(plane.c2p(3,0), plane.c2p(5,2), buff=0, color="#F7C948", stroke_width=8)
target = Dot(plane.c2p(5,2), radius=0.09, color="#7EE787")
label = Text("3a + 2b = (5, 2)", font_size=28, color="#7EE787").move_to(DOWN*3.0)
self.play(Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
self.play(TransformFromCopy(a, three_a), TransformFromCopy(b, two_b), FadeIn(target, scale=1.4), run_time=1.4)
self.play(FadeIn(label), Flash(target, color="#7EE787"), run_time=0.9)'''
    if kind == "matrix_vector":
        return '''matrix = VGroup(Text("A = [[2, 1], [1, 3]]", font_size=30, color="#EAF2FF"), Text("x = [4, 2]", font_size=30, color="#EAF2FF")).arrange(DOWN, buff=0.18).move_to(UP*0.3)
cols = VGroup(Text("4 * [2, 1]", font_size=28, color="#58A6FF"), Text("+", font_size=30), Text("2 * [1, 3]", font_size=28, color="#F7C948"), Text("=", font_size=30), Text("[10, 10]", font_size=30, color="#7EE787")).arrange(RIGHT, buff=0.16).move_to(DOWN*1.45)
box = SurroundingRectangle(cols[-1], color="#7EE787", buff=0.16)
self.play(FadeIn(matrix, shift=UP*0.1), run_time=1.0)
self.play(LaggedStart(*[FadeIn(m, shift=UP*0.1) for m in cols], lag_ratio=0.18), run_time=1.4)
self.play(Create(box), Indicate(cols[-1]), run_time=0.8)'''
    if kind == "basis":
        return '''plane = NumberPlane(x_range=[-3,5,1], y_range=[-2,5,1], background_line_style={"stroke_color":"#1F3558","stroke_width":1,"stroke_opacity":0.7}).scale(0.78).shift(DOWN*0.85)
origin = plane.c2p(0,0)
e1 = Arrow(origin, plane.c2p(1,0), buff=0, color="#58A6FF", stroke_width=8)
e2 = Arrow(origin, plane.c2p(0,1), buff=0, color="#F7C948", stroke_width=8)
target = Arrow(origin, plane.c2p(4,3), buff=0, color="#7EE787", stroke_width=8)
coords = Text("4e1 + 3e2", font_size=28, color="#7EE787").move_to(DOWN*3.0)
self.play(Create(plane), GrowArrow(e1), GrowArrow(e2), run_time=1.1)
self.play(GrowArrow(target), FadeIn(coords), run_time=1.2)
self.play(Indicate(coords), run_time=0.8)'''
    if kind == "subspace":
        return '''plane = NumberPlane(x_range=[-4,4,1], y_range=[-3,3,1], background_line_style={"stroke_color":"#1F3558","stroke_width":1,"stroke_opacity":0.65}).scale(0.8).shift(DOWN*0.8)
line = Line(plane.c2p(-3,-1.5), plane.c2p(3,1.5), color="#58A6FF", stroke_width=7)
reachable = VGroup(*[Dot(plane.c2p(x, 0.5*x), radius=0.05, color="#7EE787") for x in [-2,-1,0,1,2]])
outside = Dot(plane.c2p(1,2.4), radius=0.08, color="#FF7B72")
label = Text("reachable targets live in the span", font_size=25, color="#8FD3FF").move_to(DOWN*3.05)
self.play(Create(plane), Create(line), run_time=1.1)
self.play(LaggedStart(*[FadeIn(d, scale=1.4) for d in reachable], lag_ratio=0.1), FadeIn(outside), run_time=1.2)
self.play(FadeIn(label), Indicate(line), run_time=0.9)'''
    if kind == "transform_grid":
        return '''plane = NumberPlane(x_range=[-4,4,1], y_range=[-3,3,1], background_line_style={"stroke_color":"#1F3558","stroke_width":1,"stroke_opacity":0.7}).scale(0.78).shift(DOWN*0.75)
origin = plane.c2p(0,0)
a = Arrow(origin, plane.c2p(2.5,1.4), buff=0, color="#58A6FF", stroke_width=8)
b = Arrow(origin, plane.c2p(0.9,2.3), buff=0, color="#F7C948", stroke_width=7)
ghost = Arrow(origin, plane.c2p(3.4,2.6), buff=0, color="#7EE787", stroke_width=8)
self.play(Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.3)
self.play(TransformFromCopy(a, ghost), b.animate.set_opacity(0.55), run_time=1.2)
self.play(Indicate(ghost), run_time=0.8)'''
    if kind in {"systems", "least_squares"}:
        return '''axes = Axes(x_range=[-3,5,1], y_range=[-1,6,1], x_length=6.5, y_length=4.6, tips=False).shift(DOWN*0.8)
l1 = axes.plot(lambda x: -x + 5, x_range=[-0.5,4.8], color="#58A6FF", stroke_width=5)
l2 = axes.plot(lambda x: 0.5*x + 2, x_range=[-0.5,4.8], color="#F7C948", stroke_width=5)
dot = Dot(axes.c2p(2,3), color="#FF7B72", radius=0.09)
self.play(Create(axes), Create(l1), Create(l2), run_time=1.3)
self.play(FadeIn(dot, scale=1.4), Flash(dot, color="#FF7B72"), run_time=1.0)'''
    if kind in {"elimination", "matrix_factor"}:
        return '''rows = VGroup()
for vals in [["2","1","|","7"],["1","1","|","5"]]:
    row = VGroup(*[Text(v, font_size=30, color="#EAF2FF") for v in vals]).arrange(RIGHT, buff=0.28)
    rows.add(row)
rows.arrange(DOWN, buff=0.28).move_to(DOWN*0.7)
box = SurroundingRectangle(rows[0][0], color="#F7C948", buff=0.12)
self.play(FadeIn(rows), run_time=1.0)
self.play(Create(box), run_time=0.5)
self.play(rows[0].animate.set_color("#8FD3FF"), run_time=0.9)'''
    if kind in {"projection"}:
        return '''plane = NumberPlane(x_range=[-4,4,1], y_range=[-3,3,1], background_line_style={"stroke_color":"#1F3558","stroke_width":1,"stroke_opacity":0.6}).scale(0.78).shift(DOWN*0.8)
origin = plane.c2p(0,0)
line = Line(plane.c2p(-3,0), plane.c2p(3,0), color="#F7C948", stroke_width=5)
v = Arrow(origin, plane.c2p(2.4,2.2), buff=0, color="#58A6FF", stroke_width=8)
p = Arrow(origin, plane.c2p(2.4,0), buff=0, color="#7EE787", stroke_width=8)
d = DashedLine(v.get_end(), p.get_end(), color="#EAF2FF")
self.play(Create(plane), Create(line), GrowArrow(v), run_time=1.2)
self.play(Create(d), GrowArrow(p), run_time=1.1)'''
    if kind in {"eigen", "svd"}:
        return '''circle = Circle(radius=1.25, color="#58A6FF", stroke_width=5).shift(DOWN*0.7)
ellipse = Ellipse(width=3.8, height=1.45, color="#F7C948", stroke_width=5).shift(DOWN*0.7).rotate(0.35)
arrow = Arrow(LEFT*2.8+DOWN*2.35, RIGHT*2.8+DOWN*2.35, color="#7EE787")
label = Text("special directions survive", font_size=25, color="#8FD3FF").next_to(arrow, DOWN)
self.play(Create(circle), run_time=0.9)
self.play(Transform(circle, ellipse), GrowArrow(arrow), FadeIn(label), run_time=1.5)
self.play(Indicate(circle), run_time=0.8)'''
    if kind == "area":
        return '''square = Square(1.6, color="#58A6FF", fill_opacity=0.18).shift(DOWN*0.7)
para = Polygon(LEFT*1.3+DOWN*1.5, RIGHT*1.7+DOWN*1.5, RIGHT*2.4+UP*0.5, LEFT*0.6+UP*0.5, color="#F7C948", fill_opacity=0.22)
self.play(Create(square), run_time=0.9)
self.play(Transform(square, para), run_time=1.4)
self.play(Indicate(square), run_time=0.8)'''
    if kind == "dimension_bar":
        return '''blocks = VGroup(*[Square(0.55, color="#58A6FF", fill_opacity=0.3) for _ in range(5)]).arrange(RIGHT, buff=0.12).move_to(DOWN*0.7)
rank = Brace(VGroup(*blocks[:3]), UP, color="#F7C948")
null = Brace(VGroup(*blocks[3:]), DOWN, color="#7EE787")
self.play(FadeIn(blocks), GrowFromCenter(rank), GrowFromCenter(null), run_time=1.3)
self.play(blocks[:3].animate.set_color("#F7C948"), blocks[3:].animate.set_color("#7EE787"), run_time=1.0)'''
    if kind == "quadratic":
        return '''axes = Axes(x_range=[-3,3,1], y_range=[0,7,1], x_length=6.2, y_length=4.2, tips=False).shift(DOWN*1.05)
curve = axes.plot(lambda x: 0.7*x*x + 0.6, x_range=[-2.6,2.6], color="#F7C948", stroke_width=6)
point = Dot(axes.c2p(1.5, 0.7*1.5*1.5+0.6), color="#58A6FF", radius=0.09)
label = Text("positive in every direction", font_size=26, color="#7EE787").move_to(DOWN*3.2)
self.play(Create(axes), Create(curve), run_time=1.2)
self.play(FadeIn(point, scale=1.4), FadeIn(label), run_time=1.0)
self.play(Indicate(curve), run_time=0.8)'''
    if kind == "markov":
        return '''left = Circle(radius=0.62, color="#58A6FF", fill_opacity=0.18).shift(LEFT*1.8+DOWN*0.8)
right = Circle(radius=0.62, color="#F7C948", fill_opacity=0.18).shift(RIGHT*1.8+DOWN*0.8)
labels = VGroup(Text("A", font_size=34, color="#58A6FF").move_to(left), Text("B", font_size=34, color="#F7C948").move_to(right))
ar1 = CurvedArrow(left.get_right(), right.get_left(), angle=-0.6, color="#7EE787", stroke_width=5)
ar2 = CurvedArrow(right.get_left(), left.get_right(), angle=-0.6, color="#FF7B72", stroke_width=5)
nums = VGroup(Text("20%", font_size=25, color="#7EE787").next_to(ar1, UP), Text("30%", font_size=25, color="#FF7B72").next_to(ar2, DOWN), Text("[100, 0] -> [80, 20]", font_size=28, color="#EAF2FF").move_to(DOWN*3.0))
self.play(FadeIn(left), FadeIn(right), FadeIn(labels), run_time=1.0)
self.play(Create(ar1), Create(ar2), FadeIn(nums), run_time=1.3)
self.play(Indicate(nums[-1]), run_time=0.8)'''
    return '''cards = VGroup()
for label, color in [("definition","#58A6FF"),("formula","#F7C948"),("example","#7EE787")]:
    box = RoundedRectangle(width=5.8, height=0.8, corner_radius=0.14, color=color, fill_color="#101A33", fill_opacity=0.95)
    cards.add(VGroup(box, Text(label, font_size=26, color=color).move_to(box)))
cards.arrange(DOWN, buff=0.22).move_to(DOWN*0.7)
self.play(LaggedStart(*[FadeIn(c, shift=UP*0.12) for c in cards], lag_ratio=0.15), run_time=1.3)
self.play(Indicate(cards[2]), run_time=0.8)'''


def cmd_manim(args: argparse.Namespace) -> None:
    run = Path(args.run)
    plan = read_json(run / "short_plan.json")
    scenes = run / "scenes"
    scripts = run / "scripts"
    captions = run / "captions"
    scenes.mkdir(exist_ok=True)
    scripts.mkdir(exist_ok=True)
    captions.mkdir(exist_ok=True)
    for short in plan["shorts"]:
        slug = slugify(short["concept"])
        class_name = "".join(part.title() for part in slug.split("-")) + "Short"
        short["class_name"] = class_name
        short["scene_file"] = f"scenes/short_{short['index']:02d}_{slug}.py"
        short["srt_file"] = f"captions/short_{short['index']:02d}_{slug}.srt"
        (run / short["scene_file"]).write_text(manim_scene(short, class_name), encoding="utf-8")
        (run / short["srt_file"]).write_text(make_srt(short), encoding="utf-8")
        (scripts / f"short_{short['index']:02d}_{slug}.md").write_text(script_markdown(short), encoding="utf-8")
    write_json(run / "short_plan.json", plan)
    print(scenes)


def make_srt(short: dict[str, object]) -> str:
    ex = short["worked_example"]
    qp = short["question_prompt"]
    cues = [
        ("00:00:00,000", "00:00:04,000", short["hook"]),
        ("00:00:04,000", "00:00:13,000", short["intuition"]),
        ("00:00:13,000", "00:00:20,000", short["plain_formula"]),
        ("00:00:20,000", "00:00:34,000", f"Example: {ex['setup']} {ex['calculation']}"),
        ("00:00:34,000", "00:00:46,000", f"Takeaway: {ex['takeaway']}"),
        ("00:00:46,000", "00:00:55,000", f"Try this: {qp['question']}"),
        ("00:00:55,000", "00:01:00,000", f"Answer: {qp['answer']}"),
    ]
    return "\n\n".join(f"{i}\n{a} --> {b}\n{textwrap.fill(str(t), width=42)}" for i, (a, b, t) in enumerate(cues, start=1)) + "\n"


def script_markdown(short: dict[str, object]) -> str:
    ex = short["worked_example"]
    qp = short["question_prompt"]
    return f"""# Short {short['index']:02d}: {short['concept']}

Target length: 60 seconds

## Beats

| Time | Beat |
| --- | --- |
| 0:00-0:04 | {short['hook']} |
| 0:04-0:13 | {short['intuition']} |
| 0:13-0:20 | Formula: `{short['plain_formula']}` |
| 0:20-0:34 | Example: {ex['setup']} {ex['calculation']} |
| 0:34-0:46 | Takeaway: {ex['takeaway']} |
| 0:46-0:55 | Try this: {qp['question']} |
| 0:55-1:00 | Answer: {qp['answer']} |
"""


def audio_duration(path: Path) -> float:
    ffprobe = Path(FFMPEG).with_name("ffprobe") if FFMPEG else None
    if not ffprobe or not ffprobe.exists() or not path.exists():
        return 0.0
    result = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True, capture_output=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def make_voiceover(text: str, out: Path, engine: str) -> dict[str, object]:
    out.parent.mkdir(exist_ok=True)
    if engine == "none":
        return {"status": "skipped", "engine": engine}
    if engine == "say":
        say = shutil.which("say")
        if not say:
            return {"status": "failed", "engine": engine, "message": "say not found"}
        subprocess.run([say, text, "-o", str(out.with_suffix(".aiff"))], check=False)
        dur = audio_duration(out.with_suffix(".aiff"))
        if dur < 0.75:
            return {"status": "failed", "engine": engine, "message": f"say produced invalid duration {dur:.3f}s"}
        return {"status": "ok", "engine": engine, "file": str(out.with_suffix(".aiff")), "duration": dur}
    if engine == "edge-tts":
        edge = shutil.which("edge-tts")
        if not edge:
            return {"status": "failed", "engine": engine, "message": "edge-tts not found; install requirements.txt"}
        subprocess.run([edge, "--text", text, "--write-media", str(out)], check=False)
        dur = audio_duration(out)
        return {"status": "ok" if dur > 0.75 else "failed", "engine": engine, "file": str(out), "duration": dur}
    if engine == "openai":
        token = os.environ.get("OPENAI_API_KEY")
        if not token:
            return {"status": "failed", "engine": engine, "message": "OPENAI_API_KEY is not set"}
        import requests
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"), "voice": os.environ.get("OPENAI_TTS_VOICE", "alloy"), "input": text},
            timeout=120,
        )
        if response.status_code >= 300:
            return {"status": "failed", "engine": engine, "message": response.text[:500]}
        out.write_bytes(response.content)
        dur = audio_duration(out)
        return {"status": "ok" if dur > 0.75 else "failed", "engine": engine, "file": str(out), "duration": dur}
    return {"status": "failed", "engine": engine, "message": "unknown voice engine"}


def cmd_render(args: argparse.Namespace) -> None:
    run = Path(args.run)
    plan = read_json(run / "short_plan.json")
    videos = run / "videos"
    audio = run / "audio"
    logs = run / "logs"
    videos.mkdir(exist_ok=True)
    audio.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    results = []
    for short in plan["shorts"]:
        scene = run / short["scene_file"]
        class_name = short["class_name"]
        qflag = "-ql" if args.quality == "l" else "-qm"
        cmd = [sys.executable, "-m", "manim", qflag, "--media_dir", str(run / "manim_media"), str(scene), class_name]
        manim = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=1200)
        (logs / f"short_{short['index']:02d}_manim.log").write_text(manim.stdout + "\n" + manim.stderr, encoding="utf-8")
        if manim.returncode != 0:
            results.append({"index": short["index"], "status": "failed", "stage": "manim"})
            continue
        rendered = newest_mp4(run / "manim_media", class_name)
        if not rendered:
            results.append({"index": short["index"], "status": "failed", "stage": "locate"})
            continue
        slug = slugify(short["concept"])
        raw = videos / f"short_{short['index']:02d}_{slug}_raw.mp4"
        final = videos / f"short_{short['index']:02d}_{slug}_final.mp4"
        shutil.copy2(rendered, raw)
        narration = " ".join([short["hook"], short["intuition"], short["worked_example"]["setup"], short["worked_example"]["calculation"], short["worked_example"]["takeaway"], short["question_prompt"]["question"], short["question_prompt"]["answer"]])
        voice = make_voiceover(narration, audio / f"short_{short['index']:02d}_{slug}.mp3", args.voice_engine)
        raw_duration = audio_duration(raw)
        voice_duration = float(voice.get("duration", 0) or 0)
        if voice.get("status") == "ok" and raw_duration and voice_duration < max(2.0, raw_duration * 0.15):
            voice = {**voice, "status": "failed", "message": f"voiceover too short for video: {voice_duration:.3f}s vs {raw_duration:.3f}s"}
        if voice.get("status") == "ok" and FFMPEG:
            subprocess.run([FFMPEG, "-y", "-i", str(raw), "-i", str(voice["file"]), "-filter_complex", "[1:a]apad[a]", "-map", "0:v:0", "-map", "[a]", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(final)], text=True, capture_output=True, timeout=900)
        else:
            shutil.copy2(raw, final)
        duration = audio_duration(final)
        short["video_file"] = str(final.relative_to(run))
        short["voiceover"] = voice
        short["duration_seconds"] = duration
        results.append({"index": short["index"], "status": "rendered", "duration_seconds": duration, "voiceover": voice})
    write_json(run / "short_plan.json", plan)
    write_json(run / "render_report.json", {"results": results})
    print(run / "render_report.json")


def newest_mp4(root: Path, class_name: str) -> Path | None:
    files = list(root.rglob(f"{class_name}.mp4")) or list(root.rglob("*.mp4"))
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def public_video_url(base_url: str | None, video_file: str) -> str | None:
    base = base_url or os.environ.get("PUBLIC_VIDEO_BASE_URL")
    if not base:
        return None
    return urllib.parse.urljoin(base.rstrip("/") + "/", Path(video_file).name)


def cmd_queue(args: argparse.Namespace) -> None:
    run = Path(args.run)
    plan = read_json(run / "short_plan.json")
    items = []
    for short in plan["shorts"]:
        if "video_file" not in short:
            continue
        ex = short["worked_example"]
        caption = textwrap.shorten(
            f"{plan['course_title']} [{short['index']:02d}/{len(plan['shorts']):02d}] - {short['concept']}\n\n"
            f"{short['hook']}\n\nExample: {ex['setup']} {ex['calculation']} {ex['takeaway']}\n\n"
            f"Try this: {short['question_prompt']['question']}\nAnswer idea: {short['question_prompt']['answer']}\n\n"
            f"#stem #math #manim #education #reels",
            width=2200,
            placeholder="...",
        )
        video_file = short["video_file"]
        item = {"short_index": short["index"], "concept": short["concept"], "playlist": args.playlist or plan["course_title"], "video_file": video_file, "caption": caption, "worked_example": ex, "question_prompt": short["question_prompt"], "voiceover": short.get("voiceover"), "status": "ready", "platform": "instagram_reels"}
        video_url = public_video_url(args.public_base_url, video_file)
        if video_url:
            item["video_url"] = video_url
        items.append(item)
    queue = {"run": str(run), "playlist": args.playlist or plan["course_title"], "created_at": int(time.time()), "items": items}
    write_json(run / "instagram_publish_queue.json", queue)
    print(run / "instagram_publish_queue.json")


def graph_base_url() -> str:
    version = os.environ.get("META_GRAPH_VERSION", "v21.0").strip("/")
    return f"https://graph.facebook.com/{version}"


def graph_request(path: str, params: dict[str, str], method: str = "POST") -> dict[str, object]:
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    if method == "GET":
        url = graph_base_url() + path + "?" + encoded.decode("utf-8")
        req = urllib.request.Request(url, headers={"User-Agent": "course-shorts-skills/0.1"})
    else:
        req = urllib.request.Request(graph_base_url() + path, data=encoded, headers={"User-Agent": "course-shorts-skills/0.1"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": body, "http_status": exc.code}


def cmd_publish(args: argparse.Namespace) -> None:
    run = Path(args.run)
    queue_path = run / "instagram_publish_queue.json"
    queue = read_json(queue_path)
    token = os.environ.get("META_ACCESS_TOKEN") or os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = os.environ.get("IG_USER_ID")
    results = []
    for item in queue.get("items", []):
        if not isinstance(item, dict):
            continue
        video_url = item.get("video_url")
        result = {"short_index": item.get("short_index"), "concept": item.get("concept"), "video_url": video_url}
        if args.dry_run:
            result.update({"status": "dry-run", "message": "Would create a Reel media container, poll processing, then publish."})
            results.append(result)
            continue
        if not token or not ig_user_id:
            result.update({"status": "skipped", "message": "Set IG_USER_ID and META_ACCESS_TOKEN or IG_ACCESS_TOKEN."})
            results.append(result)
            continue
        if not video_url:
            result.update({"status": "skipped", "message": "Queue item has no public video_url. Host videos and rerun queue with --public-base-url."})
            results.append(result)
            continue
        create = graph_request(f"/{ig_user_id}/media", {"media_type": "REELS", "video_url": str(video_url), "caption": str(item.get("caption", "")), "access_token": token})
        creation_id = create.get("id")
        if not creation_id:
            result.update({"status": "failed", "stage": "create", "response": create})
            results.append(result)
            continue
        status_payload = {}
        for _ in range(args.poll_attempts):
            time.sleep(args.poll_seconds)
            status_payload = graph_request(f"/{creation_id}", {"fields": "status_code,status", "access_token": token}, method="GET")
            if status_payload.get("status_code") == "FINISHED":
                break
            if status_payload.get("status_code") in {"ERROR", "EXPIRED"}:
                break
        if status_payload.get("status_code") != "FINISHED":
            result.update({"status": "failed", "stage": "process", "creation_id": creation_id, "response": status_payload})
            results.append(result)
            continue
        publish = graph_request(f"/{ig_user_id}/media_publish", {"creation_id": str(creation_id), "access_token": token})
        if publish.get("id"):
            result.update({"status": "published", "creation_id": creation_id, "media_id": publish.get("id")})
        else:
            result.update({"status": "failed", "stage": "publish", "creation_id": creation_id, "response": publish})
        results.append(result)
    write_json(run / "instagram_publish_results.json", {"created_at": int(time.time()), "results": results})
    print(run / "instagram_publish_results.json")


def cmd_all(args: argparse.Namespace) -> None:
    out = Path(args.out)
    extract_args = argparse.Namespace(url=args.url, out=str(out), sample=args.sample, max_pages=args.max_pages, max_pdfs=args.max_pdfs)
    cmd_extract(extract_args)
    cmd_plan(argparse.Namespace(run=str(out), max_shorts=args.max_shorts))
    cmd_notes(argparse.Namespace(run=str(out), compile=False))
    cmd_manim(argparse.Namespace(run=str(out)))
    if not args.no_render:
        cmd_render(argparse.Namespace(run=str(out), quality=args.quality, voice_engine=args.voice_engine))
        cmd_queue(argparse.Namespace(run=str(out), playlist=args.playlist, public_base_url=args.public_base_url))


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Course-to-notes-and-shorts workflow for Codex skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("url", nargs="?", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--sample", choices=["linear_algebra"])
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--max-pdfs", type=int, default=DEFAULT_MAX_PDFS)
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("plan")
    p.add_argument("--run", required=True)
    p.add_argument("--max-shorts", type=int, default=DEFAULT_SHORTS)
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("notes")
    p.add_argument("--run", required=True)
    p.add_argument("--compile", action="store_true")
    p.set_defaults(func=cmd_notes)
    p = sub.add_parser("manim")
    p.add_argument("--run", required=True)
    p.set_defaults(func=cmd_manim)
    p = sub.add_parser("render")
    p.add_argument("--run", required=True)
    p.add_argument("--quality", choices=["l", "m"], default="l")
    p.add_argument("--voice-engine", choices=["none", "say", "edge-tts", "openai"], default="none")
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("queue")
    p.add_argument("--run", required=True)
    p.add_argument("--playlist", default=None)
    p.add_argument("--public-base-url", default=None)
    p.set_defaults(func=cmd_queue)
    p = sub.add_parser("publish")
    p.add_argument("--run", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--poll-seconds", type=int, default=10)
    p.add_argument("--poll-attempts", type=int, default=30)
    p.set_defaults(func=cmd_publish)
    p = sub.add_parser("all")
    p.add_argument("url", nargs="?", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--sample", choices=["linear_algebra"])
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--max-pdfs", type=int, default=DEFAULT_MAX_PDFS)
    p.add_argument("--max-shorts", type=int, default=DEFAULT_SHORTS)
    p.add_argument("--quality", choices=["l", "m"], default="l")
    p.add_argument("--voice-engine", choices=["none", "say", "edge-tts", "openai"], default="none")
    p.add_argument("--playlist", default=None)
    p.add_argument("--public-base-url", default=None)
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(func=cmd_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

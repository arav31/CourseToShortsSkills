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
MAX_FETCH_BYTES = 25_000_000
PDF_TEXT_PAGES = 180
DEFAULT_MAX_PAGES = 160
DEFAULT_MAX_PDFS = 100
DEFAULT_SHORTS = 40
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
EXTRA_TEX_PATHS = ["/Library/TeX/texbin", "/opt/homebrew/bin", "/usr/local/bin"]



def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for folder in EXTRA_TEX_PATHS:
        candidate = Path(folder) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


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
        (r"\{", "{"),
        (r"\}", "}"),
        (r"\left", ""),
        (r"\right", ""),
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
    out = re.sub(r"\b(span|rank|det|dim|nullity|proj)(?=[A-Za-z])", r"\1 ", out)
    out = out.replace("=", " = ")
    return re.sub(r"\s+", " ", out).strip()


def screen_math(value: str) -> str:
    out = plain_math(value)
    out = re.sub(r"_([A-Za-z0-9])", r"\1 ", out)
    out = out.replace("+", " + ").replace("-", " - ")
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
    page_count = min(doc.page_count, PDF_TEXT_PAGES)
    return "\n".join(doc[i].get_text("text") for i in range(page_count))


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
    stop = {
        "course", "lecture", "lectures", "chapter", "section", "the", "and", "for", "with", "this", "that",
        "from", "have", "notes", "page", "problem", "problems", "example", "examples", "using", "where",
        "there", "which", "then", "than", "into", "will", "shall", "their", "about", "between", "through",
    }
    words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{3,}\b", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    phrase_counts: dict[str, int] = {}
    usable = [w for w in words if w not in stop]
    for size in (2, 3):
        for i in range(max(0, len(usable) - size + 1)):
            phrase = " ".join(usable[i : i + size])
            if len(set(phrase.split())) > 1:
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    ranked_phrases = [p for p, n in sorted(phrase_counts.items(), key=lambda item: (item[1], len(item[0])), reverse=True) if n >= 2]
    ranked_words = [w for w, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)]
    out: list[str] = []
    for term in ranked_phrases + ranked_words:
        normalized = term.strip()
        if normalized and all(normalized not in existing and existing not in normalized for existing in out):
            out.append(normalized)
    return out


def source_text(pack: dict[str, object]) -> str:
    return "\n".join(str(m.get("text", "")) for m in pack.get("materials", []) if isinstance(m, dict))


def source_coverage_terms(pack: dict[str, object], shorts: list[dict[str, object]], limit: int = 80) -> list[str]:
    existing = {str(short.get("concept", "")).lower() for short in shorts}
    terms: list[str] = []
    for term in frequent_terms(source_text(pack)):
        if not term or any(term in concept or concept in term for concept in existing):
            continue
        if term not in terms:
            terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def source_snippets(pack: dict[str, object], term: str, limit: int = 2) -> list[str]:
    snippets: list[str] = []
    pattern = re.compile(r"[^.?!]*(?:" + re.escape(term) + r")[^.?!]*[.?!]", re.I)
    for material in pack.get("materials", []):
        if not isinstance(material, dict):
            continue
        for match in pattern.finditer(str(material.get("text", ""))):
            cleaned = re.sub(r"\s+", " ", match.group(0)).strip()
            if 40 <= len(cleaned) <= 320 and cleaned not in snippets:
                snippets.append(cleaned)
                if len(snippets) >= limit:
                    return snippets
    return snippets


def cmd_plan(args: argparse.Namespace) -> None:
    run = Path(args.run)
    pack = read_json(run / "source_pack.json")
    concepts = choose_concepts(pack, args.max_shorts)
    shorts = [
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
    ]
    for i, short in enumerate(shorts):
        next_concepts = [s["concept"] for s in shorts[i + 1 : i + 4]]
        short["key_concept"] = f"{short['concept']}: {short['hook']}"
        short["concept_explanation"] = (
            f"{short['intuition']} The worked example makes the idea testable: "
            f"{short['worked_example']['takeaway']}"
        )
        short["recognition_cue"] = (
            f"Use this concept when a problem asks you to identify the rule, structure, or quantity behind "
            f"{short['concept'].lower()} and then check it with a concrete example."
        )
        short["concept_connections"] = {
            "builds_on": short["prerequisites"],
            "prepares_for": next_concepts,
        }
    plan = {
        "course_title": pack.get("title", "Course"),
        "source_url": pack.get("source_url"),
        "shorts": shorts,
    }
    write_json(run / "short_plan.json", plan)
    print(run / "short_plan.json")


def latex_escape(s: str) -> str:
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("$", r"\$")
             .replace("#", r"\#").replace("_", r"\_").replace("^", r"\^{}").replace("~", r"\textasciitilde{}")
             .replace("{", r"\{").replace("}", r"\}"))


MATRIX_LITERAL_RE = re.compile(r"\[\[[^\]]+\](?:\s*,\s*\[[^\]]+\])*\]")
ROW_MATRIX_RE = re.compile(r"\[[^\[\],]+(?:\s+[^\[\],]+)+\]")
TUPLE_LITERAL_RE = re.compile(r"\([^()]*,[^()]*\)")
ASSIGNMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_])([A-Za-z](?:_?[A-Za-z0-9]+)?)\s*=\s*"
    r"(\[\[[^\]]+\](?:\s*,\s*\[[^\]]+\])*\]|\[[^\[\]]+\]|\([^()]*,[^()]*\)|diag\([^()]+\))"
)
MATH_FUNCTIONS = {
    "sin", "cos", "tan", "log", "ln", "exp", "sqrt", "rank", "det", "dim", "diag", "span", "nullity",
    "proj", "lim", "min", "max", "argmin", "argmax", "mean", "var", "cov", "prob",
}
GREEK_LATEX = {
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "delta": r"\delta",
    "epsilon": r"\epsilon",
    "theta": r"\theta",
    "lambda": r"\lambda",
    "mu": r"\mu",
    "sigma": r"\sigma",
    "omega": r"\omega",
}
SYMBOL_MACROS = {
    "lambda": r"\lambda",
    "theta": r"\theta",
    "mu": r"\mu",
    "sigma": r"\sigma",
    "Sigma": r"\Sigma",
}


def split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for i, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def matrix_rows(value: str) -> list[list[str]] | None:
    source = value.strip()
    if source.startswith("[[") and source.endswith("]]"):
        row_texts = re.split(r"\]\s*,\s*\[", source[2:-2].strip())
    elif ROW_MATRIX_RE.fullmatch(source):
        row_texts = [source[1:-1].strip()]
    else:
        return None
    rows: list[list[str]] = []
    for row_text in row_texts:
        cleaned = row_text.strip().strip("[]")
        cells = split_top_level_commas(cleaned) if "," in cleaned else cleaned.split()
        if not cells:
            return None
        rows.append(cells)
    return rows or None


def vector_items(value: str) -> list[str] | None:
    source = value.strip()
    if source.startswith("(") and source.endswith(")") and "," in source:
        return split_top_level_commas(source[1:-1])
    if source.startswith("[") and source.endswith("]") and "," in source and not source.startswith("[["):
        return split_top_level_commas(source[1:-1])
    return None


def stash_latex(placeholders: dict[str, str], latex: str) -> str:
    key = f"@@@{len(placeholders)}@@@"
    placeholders[key] = latex
    return key


def latex_bmatrix(rows: list[list[str]]) -> str:
    rendered_rows = [" & ".join(latex_math_expr(cell, tuple_style="tuple") for cell in row) for row in rows]
    return r"\begin{bmatrix}" + r" \\ ".join(rendered_rows) + r"\end{bmatrix}"


def latex_tuple(items: list[str]) -> str:
    return r"\left(" + ", ".join(latex_math_expr(item, tuple_style="tuple") for item in items) + r"\right)"


def latex_column_vector(items: list[str]) -> str:
    return r"\begin{bmatrix}" + r" \\ ".join(latex_math_expr(item, tuple_style="tuple") for item in items) + r"\end{bmatrix}"


def latex_value(value: str, *, vector: bool = False) -> str:
    rows = matrix_rows(value)
    if rows:
        return latex_bmatrix(rows)
    items = vector_items(value)
    if items:
        return latex_column_vector(items) if vector else latex_tuple(items)
    if value.strip().lower().startswith("diag(") and value.strip().endswith(")"):
        inner = value.strip()[5:-1]
        return r"\operatorname{diag}\left(" + ", ".join(latex_math_expr(part, tuple_style="tuple") for part in split_top_level_commas(inner)) + r"\right)"
    return latex_math_expr(value, tuple_style="tuple")


def latex_variable(name: str, value: str | None = None) -> str:
    vector = value is not None and vector_items(value) is not None
    match = re.fullmatch(r"([A-Za-z])(?:_?([A-Za-z0-9]+))?", name.strip())
    if vector and match:
        base = rf"\vec{{{match.group(1)}}}"
        if match.group(2):
            base += rf"_{{{match.group(2)}}}"
        return base
    return latex_math_expr(name, tuple_style="tuple")


def latex_math_expr(expr: str, *, tuple_style: str = "tuple") -> str:
    work = str(expr).strip().strip(".;")
    work = work.replace("−", "-").replace("×", "*").replace("·", r"\cdot")
    placeholders: dict[str, str] = {}

    def matrix_repl(match: re.Match[str]) -> str:
        rows = matrix_rows(match.group(0))
        return stash_latex(placeholders, latex_bmatrix(rows)) if rows else match.group(0)

    def row_matrix_repl(match: re.Match[str]) -> str:
        rows = matrix_rows(match.group(0))
        return stash_latex(placeholders, latex_bmatrix(rows)) if rows else match.group(0)

    def diag_repl(match: re.Match[str]) -> str:
        parts = split_top_level_commas(match.group(1))
        rendered = r"\operatorname{diag}\left(" + ", ".join(latex_math_expr(part, tuple_style="tuple") for part in parts) + r"\right)"
        return stash_latex(placeholders, rendered)

    def proj_repl(match: re.Match[str]) -> str:
        sub = latex_math_expr(match.group(1), tuple_style="tuple")
        arg = latex_math_expr(match.group(2), tuple_style="tuple")
        return stash_latex(placeholders, rf"\operatorname{{proj}}_{{{sub}}}\left({arg}\right)")

    def sqrt_repl(match: re.Match[str]) -> str:
        return stash_latex(placeholders, r"\sqrt{" + latex_math_expr(match.group(1), tuple_style="tuple") + "}")

    def tuple_repl(match: re.Match[str]) -> str:
        items = vector_items(match.group(0))
        if not items:
            return match.group(0)
        rendered = latex_column_vector(items) if tuple_style == "vector" else latex_tuple(items)
        return stash_latex(placeholders, rendered)

    work = MATRIX_LITERAL_RE.sub(matrix_repl, work)
    work = ROW_MATRIX_RE.sub(row_matrix_repl, work)
    work = re.sub(r"\bdiag\(([^()]*)\)", diag_repl, work)
    work = re.sub(r"\bproj_([A-Za-z0-9]+)\(([^()]*)\)", proj_repl, work)
    while re.search(r"\bsqrt\(([^()]*)\)", work):
        work = re.sub(r"\bsqrt\(([^()]*)\)", sqrt_repl, work)
    work = TUPLE_LITERAL_RE.sub(tuple_repl, work)

    for word, latex in GREEK_LATEX.items():
        work = re.sub(rf"\b{word}\b", lambda _match, value=latex: value, work, flags=re.I)
    work = re.sub(r"\bdot\b", r"\\cdot", work, flags=re.I)
    work = work.replace("*", r"\cdot ")
    work = work.replace("<=", r"\le ").replace(">=", r"\ge ").replace("=>", r"\Rightarrow ")
    work = re.sub(r"\b(rank|det|dim|nullity|span|mean|var|cov|prob)\s*\(", r"\\operatorname{\1}(", work)
    work = re.sub(r"\b(rank|nullity)\b", r"\\operatorname{\1}", work)
    work = re.sub(r"\b(sin|cos|tan|log|ln|exp)\s*\(", r"\\\1(", work)
    work = re.sub(r"\b([APU])([xvb])\b", r"\1\\vec{\2}", work)
    work = re.sub(r"\b([A-Za-z])([0-9]+)\b", r"\1_{\2}", work)
    work = re.sub(r"\^T(?=[A-Za-z])", r"^{T}", work)
    work = re.sub(r"\^(?!\{)([0-9]+|[A-Za-z])", r"^{\1}", work)

    label = re.match(r"^([A-Za-z][A-Za-z ]{2,24})\s*=", work)
    if label and label.group(1).lower() not in MATH_FUNCTIONS:
        words = label.group(1).split()
        if len(words) > 1 or len(label.group(1)) > 3:
            work = r"\mathrm{" + " ".join(words) + "}" + work[label.end() - 1 :]

    work = re.sub(r"\s+", " ", work).strip()
    for key, value in placeholders.items():
        work = work.replace(key, value)
    return work


def math_span_is_safe(core: str) -> bool:
    if len(core) > 150:
        return False
    words = re.findall(r"[A-Za-z]{2,}", core)
    allowed = MATH_FUNCTIONS | set(GREEK_LATEX) | {"frac", "vec", "hat", "operatorname"}
    return all(word.lower() in allowed or len(word) <= 2 or re.fullmatch(r"[A-Z][a-z]?", word) for word in words)


def latex_text_with_inline_math(text: str, *, tuple_style: str = "tuple") -> str:
    work = str(text).strip()
    placeholders: dict[str, str] = {}

    atom = r"(?:[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?[A-Za-z]?|\d+(?:\.\d+)?|\([^()]+\)|\[[^\]]+\])"
    term = rf"{atom}(?:\s*(?:\^|_)\s*{atom})?"
    expr = rf"{term}(?:\s*(?:\+|-|\*|/|dot)\s*{term}){{0,8}}"
    equation_re = re.compile(rf"(?<![A-Za-z0-9_])({expr}\s*(?:=|<=|>=|<|>)\s*{expr}(?:\s*(?:=|<=|>=|<|>)\s*{expr})*)")

    def store_math(latex: str) -> str:
        return stash_latex(placeholders, rf"\({latex}\)")

    def equation_repl(match: re.Match[str]) -> str:
        core = match.group(1).strip()
        if not math_span_is_safe(core):
            return match.group(0)
        return store_math(latex_math_expr(core, tuple_style=tuple_style))

    work = equation_re.sub(equation_repl, work)
    work = MATRIX_LITERAL_RE.sub(lambda m: store_math(latex_math_expr(m.group(0), tuple_style="vector")), work)
    work = ROW_MATRIX_RE.sub(lambda m: store_math(latex_math_expr(m.group(0), tuple_style="vector")), work)
    work = re.sub(r"\b(?:sqrt|rank|det|dim|diag)\([^()]+\)", lambda m: store_math(latex_math_expr(m.group(0), tuple_style=tuple_style)), work)
    work = TUPLE_LITERAL_RE.sub(lambda m: store_math(latex_math_expr(m.group(0), tuple_style=tuple_style)), work)

    escaped = latex_escape(work)
    for key, value in placeholders.items():
        escaped = escaped.replace(latex_escape(key), value)
    return escaped


def short_vector_context(short: dict[str, object]) -> bool:
    haystack = " ".join(
        str(short.get(key, ""))
        for key in ("concept", "formula", "intuition", "hook", "visual_type")
    ).lower()
    return any(term in haystack for term in ("vector", "matrix", "basis", "span", "dot", "projection", "eigen", r"\vec"))


def latex_assignment_text(text: str, *, vector_context: bool) -> str | None:
    matches = [match for match in ASSIGNMENT_RE.finditer(text) if matrix_rows(match.group(2)) or vector_items(match.group(2)) or match.group(2).lower().startswith("diag(")]
    if not matches:
        return None
    first, last = matches[0], matches[-1]
    prefix = text[: first.start()].strip()
    prefix = re.sub(r"(?:,|and|with|where)\s*$", "", prefix, flags=re.I).strip()
    suffix = text[last.end() :].strip()
    suffix = re.sub(r"^[\s,.;]*(?:and\s+)?", "", suffix, flags=re.I).strip()
    suffix = suffix if suffix not in {".", ";", ","} else ""
    math_parts = []
    for match in matches:
        var, value = match.group(1), match.group(2)
        as_vector = vector_context and vector_items(value) is not None
        math_parts.append(f"{latex_variable(var, value)} = {latex_value(value, vector=as_vector)}")
    pieces: list[str] = []
    if prefix:
        pieces.append(latex_escape(prefix))
    pieces.append(r"\[" + "\n" + r",\qquad ".join(math_parts) + "\n" + r"\]")
    if suffix:
        pieces.append(latex_text_with_inline_math(suffix, tuple_style="tuple"))
    return "\n".join(pieces)


def display_math_sentence(sentence: str) -> bool:
    core = sentence.strip().rstrip(".")
    if not core or ("=" not in core and "sqrt(" not in core and " dot " not in core.lower()):
        return False
    if ":" in core and "=" in core and core.index(":") < core.index("="):
        return False
    prose_markers = {"because", "then", "where", "when", "only", "gives", "are", "is", "so", "but", "with", "from"}
    words = [word.lower() for word in re.findall(r"[A-Za-z]{2,}", core)]
    if any(word in prose_markers for word in words):
        return False
    prose = [word for word in words if word not in MATH_FUNCTIONS and word not in GREEK_LATEX and len(word) > 2]
    return len(prose) <= 1


def latex_calculation_text(text: str, *, vector_context: bool) -> str:
    rendered: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", str(text).strip()):
        if not sentence:
            continue
        if display_math_sentence(sentence):
            tuple_style = "vector" if vector_context else "tuple"
            rendered.append(r"\[" + "\n" + latex_math_expr(sentence, tuple_style=tuple_style) + "\n" + r"\]")
        else:
            rendered.append(latex_text_with_inline_math(sentence, tuple_style="tuple"))
    return "\n".join(rendered)


def latex_example_text(text: str, short: dict[str, object], role: str) -> str:
    vector_context = short_vector_context(short)
    if role == "calculation":
        return latex_calculation_text(str(text), vector_context=vector_context)
    assignment = latex_assignment_text(str(text), vector_context=vector_context)
    if assignment:
        return assignment
    return latex_text_with_inline_math(str(text), tuple_style="tuple")


def compact_key_concept(short: dict[str, object]) -> str:
    concept = str(short.get("concept", "Concept"))
    key = str(short.get("key_concept", short.get("hook", ""))).strip()
    prefix = f"{concept}: "
    if key.startswith(prefix):
        key = key[len(prefix) :]
    explanation = str(short.get("concept_explanation", short.get("intuition", ""))).strip()
    if explanation and explanation != key:
        return f"{key} {explanation}"
    return key or str(short.get("intuition", ""))


def plain_formula_read(short: dict[str, object]) -> str:
    formula = str(short.get("formula", ""))
    return plain_math(formula) if formula else str(short.get("plain_formula", ""))


def latex_formula_reference(short: dict[str, object]) -> str:
    formula = str(short.get("formula", ""))
    plain = latex_escape(plain_formula_read(short))
    return rf"\(\displaystyle {formula}\)\par{{\footnotesize {plain}}}"


def notes_pdf_report_path(run: Path) -> Path:
    return run / "notes_compile_report.json"


def compile_notes_pdf(run: Path, plan: dict[str, object], engine: str = "auto") -> dict[str, object]:
    report: dict[str, object] = {"requested_engine": engine, "status": "not-run"}
    if engine in {"auto", "latex"}:
        latex_report = run_latex_engine(run)
        if latex_report.get("status") == "ok":
            write_json(notes_pdf_report_path(run), latex_report)
            return latex_report
        report = latex_report
        if engine == "latex":
            write_json(notes_pdf_report_path(run), report)
            raise SystemExit(f"LaTeX PDF compile failed: {latex_report.get('message', 'unknown error')}")
    if engine in {"auto", "fallback"}:
        fallback_report = write_fallback_notes_pdf(run, plan, reason=str(report.get("message", "LaTeX engine unavailable")))
        write_json(notes_pdf_report_path(run), fallback_report)
        return fallback_report
    write_json(notes_pdf_report_path(run), report)
    return report


def run_latex_engine(run: Path) -> dict[str, object]:
    tex = run / "notes.tex"
    latexmk = find_executable("latexmk")
    if latexmk:
        cmd = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", "notes.tex"]
        result = subprocess.run(cmd, cwd=run, text=True, capture_output=True, timeout=300)
        (run / "notes_latexmk.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        if result.returncode == 0 and (run / "notes.pdf").exists():
            return {"status": "ok", "engine": "latexmk", "pdf": "notes.pdf"}
        return {"status": "failed", "engine": "latexmk", "message": "latexmk failed; see notes_latexmk.log"}
    pdflatex = find_executable("pdflatex")
    if pdflatex:
        last = None
        for i in range(2):
            last = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "notes.tex"], cwd=run, text=True, capture_output=True, timeout=300)
            (run / f"notes_pdflatex_pass_{i + 1}.log").write_text(last.stdout + "\n" + last.stderr, encoding="utf-8")
            if last.returncode != 0:
                break
        if last and last.returncode == 0 and (run / "notes.pdf").exists():
            return {"status": "ok", "engine": "pdflatex", "pdf": "notes.pdf"}
        return {"status": "failed", "engine": "pdflatex", "message": "pdflatex failed; see notes_pdflatex_pass_*.log"}
    tectonic = find_executable("tectonic")
    if tectonic:
        result = subprocess.run([tectonic, "notes.tex"], cwd=run, text=True, capture_output=True, timeout=300)
        (run / "notes_tectonic.log").write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        if result.returncode == 0 and (run / "notes.pdf").exists():
            return {"status": "ok", "engine": "tectonic", "pdf": "notes.pdf"}
        return {"status": "failed", "engine": "tectonic", "message": "tectonic failed; see notes_tectonic.log"}
    return {"status": "missing-engine", "engine": None, "message": "No LaTeX engine found: install latexmk, pdflatex, or tectonic."}


def write_fallback_notes_pdf(run: Path, plan: dict[str, object], reason: str) -> dict[str, object]:
    try:
        import fitz  # type: ignore
    except Exception as exc:
        raise SystemExit(f"Could not create notes.pdf: no LaTeX engine and PyMuPDF fallback unavailable ({exc}).")

    doc = fitz.open()
    width, height = 612, 792
    margin = 54
    y = margin

    def add_page() -> fitz.Page:
        nonlocal y
        new_page = doc.new_page(width=width, height=height)
        y = margin
        return new_page

    page = add_page()

    def write_line(text: str, size: int = 10, color: tuple[float, float, float] = (0, 0, 0), leading: float = 1.35) -> None:
        nonlocal page, y
        wrapped = textwrap.wrap(re.sub(r"\s+", " ", text).strip(), width=max(40, int(96 - size * 2.4))) or [""]
        for line in wrapped:
            if y > height - margin:
                page = add_page()
            page.insert_text((margin, y), line, fontsize=size, fontname="helv", color=color)
            y += size * leading

    def heading(text: str, size: int = 16) -> None:
        nonlocal page, y
        if y > height - margin - 50:
            page = add_page()
        y += 8
        write_line(text, size=size, color=(0.05, 0.19, 0.38), leading=1.45)
        y += 3

    title = str(plan.get("course_title", "Course"))
    heading(f"{title} Notes", 22)
    write_line("PDF generated from notes.tex data. LaTeX engine note: " + reason, 9, color=(0.45, 0.2, 0.0))
    heading("Key Concepts And Explanations", 15)
    for short in plan.get("shorts", []):
        if not isinstance(short, dict):
            continue
        write_line(f"{short.get('index')}. {short.get('concept')}", 12, color=(0.05, 0.19, 0.38))
        write_line(f"Key concept: {short.get('key_concept', short.get('hook', ''))}")
        write_line(f"Explanation: {short.get('concept_explanation', short.get('intuition', ''))}")
        write_line(f"How to recognize it: {short.get('recognition_cue', '')}")
        y += 5
    heading("Core Concepts", 15)
    for short in plan.get("shorts", []):
        if not isinstance(short, dict):
            continue
        ex = short.get("worked_example", {}) if isinstance(short.get("worked_example"), dict) else {}
        qp = short.get("question_prompt", {}) if isinstance(short.get("question_prompt"), dict) else {}
        heading(f"{short.get('index')}. {short.get('concept')}", 14)
        write_line(f"Definition: {short.get('intuition', '')}")
        write_line(f"Formula: {short.get('plain_formula', short.get('formula', ''))}")
        write_line(f"Worked example: {ex.get('setup', '')} {ex.get('calculation', '')} {ex.get('takeaway', '')}")
        write_line(f"Common trap: {short.get('misconception', '')}")
        write_line(f"Question: {qp.get('question', '')}")
        write_line(f"Answer idea: {qp.get('answer', '')}")
    pdf = run / "notes.pdf"
    doc.save(pdf)
    doc.close()
    return {"status": "ok", "engine": "pymupdf-fallback", "pdf": "notes.pdf", "message": reason}


def latex_items(items: list[str]) -> str:
    if not items:
        return r"\item None recorded."
    return "\n".join(rf"\item {latex_escape(item)}" for item in items)


def formula_symbol_tokens(formula: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(key: str, latex: str) -> None:
        if key not in seen:
            seen.add(key)
            tokens.append((key, latex))

    for match in re.finditer(r"\\(vec|hat)\{([A-Za-z])\}(?:_\{?([A-Za-z0-9]+)\}?)?", formula):
        macro, base, sub = match.group(1), match.group(2), match.group(3)
        latex = rf"\{macro}{{{base}}}" + (rf"_{{{sub}}}" if sub else "")
        add(f"{macro}:{base}:{sub or ''}", latex)
    for macro, latex in SYMBOL_MACROS.items():
        if rf"\{macro}" in formula:
            add(f"macro:{macro}", latex)

    stripped = re.sub(r"\\operatorname\{[^}]+\}", " ", formula)
    stripped = re.sub(r"\\(?:vec|hat)\{[A-Za-z]\}(?:_\{?[A-Za-z0-9]+\}?)?", " ", stripped)
    stripped = re.sub(r"\\[A-Za-z]+", " ", stripped)
    for match in re.finditer(r"(?<![A-Za-z])([A-Za-z])(?:_\{?([A-Za-z0-9]+)\}?)?", stripped):
        base, sub = match.group(1), match.group(2)
        latex = base + (rf"_{{{sub}}}" if sub else "")
        add(f"plain:{base}:{sub or ''}", latex)
    return tokens


def symbol_meaning(key: str, latex: str, short: dict[str, object]) -> str:
    haystack = " ".join(str(short.get(k, "")) for k in ("concept", "formula", "intuition", "hook", "visual_type")).lower()
    vector_match = re.search(r"\\(?:vec|hat)\{([A-Za-z])\}", latex)
    base_match = re.search(r"([A-Za-z])", latex.replace("lambda", ""))
    base = vector_match.group(1) if vector_match else (base_match.group(1) if base_match else latex)
    if latex.startswith(r"\vec"):
        if base in {"x", "b"}:
            return "vector of unknowns, inputs, or target values"
        if base in {"u", "v", "a", "q"}:
            return "vector or direction used by the rule"
        return "vector quantity with ordered components"
    if latex == r"\lambda":
        return "parameter; in eigenvalue topics, the stretch factor"
    if latex == r"\theta":
        return "angle or angular parameter"
    if latex in {r"\mu", r"\sigma"}:
        return "distribution parameter or course-defined constant"
    if latex == r"\Sigma":
        return "summation, covariance, or singular-value matrix depending on context"
    if "_{" in latex:
        return "indexed component, coefficient, or sequence term"
    if base in {"A", "B", "C", "P", "Q", "R", "U", "V", "S"}:
        if any(term in haystack for term in ("matrix", "linear", "eigen", "svd", "markov", "qr")):
            return "matrix, linear transformation, or structured array"
        if "probability" in haystack and base == "P":
            return "probability or transition rule"
        return "named quantity defined by the course context"
    if base in {"x", "y", "z"}:
        return "unknown, input, output, or coordinate variable"
    if base in {"u", "v", "w"}:
        return "vector, direction, or comparison quantity"
    if base in {"i", "j", "k", "n", "r"}:
        return "index, count, dimension, or rank-like value"
    if base in {"c", "d", "a", "b"}:
        return "coefficient, scalar, vector, or course-defined quantity"
    if base == "t":
        return "time or independent variable"
    if base == "f":
        return "function or rule"
    return "symbol whose meaning should be checked in the source context"


def formula_operator_entries(formula: str, short: dict[str, object]) -> list[str]:
    entries: list[str] = []
    operators = {
        "rank": r"$\operatorname{rank}$: number of independent directions or constraints",
        "det": r"$\det$: signed scale factor for area or volume",
        "dim": r"$\dim$: dimension or number of degrees of freedom",
        "span": r"$\operatorname{span}$: all combinations generated by listed objects",
        "proj": r"$\operatorname{proj}$: component kept in a chosen direction or subspace",
        "nullity": r"$\operatorname{nullity}$: number of free or invisible input directions",
    }
    for name, entry in operators.items():
        if name in formula:
            entries.append(entry)
    if r"\frac" in formula:
        entries.append(r"$\frac{\cdot}{\cdot}$: ratio; check numerator and denominator roles before substituting")
    if "=" in formula:
        entries.append(r"$=$: equality to verify by substitution, transformation, or units")
    return entries


def symbol_glossary(short: dict[str, object]) -> str:
    formula = str(short.get("formula", ""))
    entries: list[str] = []
    seen_latex: set[str] = set()
    for key, latex in formula_symbol_tokens(formula):
        if latex in seen_latex:
            continue
        seen_latex.add(latex)
        entries.append(rf"${latex}$: {symbol_meaning(key, latex, short)}")
        if len(entries) >= 8:
            break
    for entry in formula_operator_entries(formula, short):
        if entry not in entries:
            entries.append(entry)
    if not entries:
        entries.append("No stable formula symbols were detected; define the course-specific quantities before applying the rule.")
    return "; ".join(entries)


def visual_label(value: object) -> str:
    labels = {
        "vector_components": "vector-component diagram",
        "linear_combination": "linear-combination diagram",
        "matrix_vector": "matrix-vector diagram",
        "calculus_tangent": "tangent-line diagram",
        "calculus_area": "area-accumulation diagram",
        "physics_force": "force diagram",
        "physics_energy": "energy diagram",
        "physics_wave": "wave diagram",
        "cs_graph": "graph diagram",
        "cs_array": "array-state diagram",
        "state_machine": "state-transition diagram",
        "probability": "probability diagram",
        "chemistry_reaction": "reaction diagram",
        "numeric_rule": "input-rule-output diagram",
    }
    key = str(value or "concept diagram").strip().lower()
    if key in labels:
        return labels[key]
    label = re.sub(r"[_-]+", " ", key).strip()
    return f"{label} diagram" if label and "diagram" not in label else (label or "concept diagram")


def cmd_notes(args: argparse.Namespace) -> None:
    run = Path(args.run)
    pack = read_json(run / "source_pack.json")
    plan = read_json(run / "short_plan.json")
    title = str(plan.get("course_title") or pack.get("title") or "Course")
    materials = pack.get("materials", [])
    shorts = plan["shorts"]
    source_inventory = "\n".join(
        rf"\item \textbf{{{latex_escape(str(m.get('kind', 'source')).upper())}}}: {latex_escape(str(m.get('title', 'Untitled')))}\\ {latex_escape(str(m.get('url', '')))}"
        for m in materials if isinstance(m, dict)
    ) or r"\item No source inventory was recorded. Re-run extraction with the course URL before treating these as complete notes."
    course_map = "\n".join(
        rf"\item \textbf{{{latex_escape(short['concept'])}}}: prerequisites -- {latex_escape(', '.join(short.get('prerequisites', [])) or 'none')}. Outcome -- {latex_escape(short['intuition'])}"
        for short in shorts
    )
    definition_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & {latex_escape(compact_key_concept(short))} \\"
        for short in shorts
    )
    formula_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & {latex_formula_reference(short)} \\"
        for short in shorts
    )
    symbol_rows = "\n".join(
        rf"{short['index']} & {latex_escape(short['concept'])} & {symbol_glossary(short)} \\"
        for short in shorts
    )
    coverage_terms = source_coverage_terms(pack, shorts)
    coverage_items = "\n".join(rf"\item {latex_escape(term.title())}" for term in coverage_terms[:80]) or r"\item No additional source-derived terms were detected beyond the planned topics."
    coverage_sections = []
    for term in coverage_terms[:18]:
        snippets = source_snippets(pack, term)
        context = " ".join(snippets) if snippets else "This term appears in the course source pack and should be checked against the original lecture notes, assignments, or readings."
        coverage_sections.append(rf"""
\subsection{{{latex_escape(term.title())}}}
\paragraph{{Source context.}} {latex_escape(context)}
\paragraph{{Study task.}} Write the formal definition, identify the symbols used by the course, solve one small example, and add one conceptual question before relying on this topic in a video script.
""")
    sections = []
    practice_items = []
    for short in shorts:
        ex = short["worked_example"]
        qp = short["question_prompt"]
        prereq_items = latex_items([str(x) for x in short.get("prerequisites", [])])
        connections = short.get("concept_connections", {})
        builds_on = latex_escape(", ".join(connections.get("builds_on", short.get("prerequisites", []))) or "none")
        prepares_for = latex_escape(", ".join(connections.get("prepares_for", [])) or "later course topics")
        key_concept = latex_escape(short.get("key_concept", short["hook"]))
        concept_explanation = latex_escape(short.get("concept_explanation", short["intuition"]))
        recognition_cue = latex_escape(short.get("recognition_cue", "Use the definition and worked example to decide when this idea applies."))
        setup_tex = latex_example_text(str(ex.get("setup", "")), short, "setup")
        calculation_tex = latex_example_text(str(ex.get("calculation", "")), short, "calculation")
        takeaway_tex = latex_example_text(str(ex.get("takeaway", "")), short, "takeaway")
        answer_tex = latex_example_text(str(qp.get("answer", "")), short, "answer")
        question_tex = latex_text_with_inline_math(str(qp.get("question", "")), tuple_style="tuple")
        sections.append(rf"""
\subsection{{{latex_escape(short['concept'])}}}
\subsubsection*{{Prerequisites}}
\begin{{itemize}}
{prereq_items}
\end{{itemize}}

\subsubsection*{{Key concept and use}}
\textbf{{Key concept.}} {key_concept}

\textbf{{Explanation.}} {concept_explanation}

\textbf{{Recognition cue.}} {recognition_cue}

\textbf{{Connections.}} Builds on {builds_on}. Prepares for {prepares_for}.

\begin{{definition}}
{latex_escape(short['intuition'])}
\end{{definition}}

\begin{{formula}}
\[
{short['formula']}
\]
\textbf{{Plain-language read.}} {latex_escape(plain_formula_read(short))}.\\
\textbf{{Symbols.}} {symbol_glossary(short)}.
\end{{formula}}

\begin{{example}}
\textbf{{Setup.}} {setup_tex}

\textbf{{Calculation.}} {calculation_tex}

\textbf{{Interpretation.}} {takeaway_tex}
\end{{example}}

\paragraph{{Visual interpretation.}} Use a {latex_escape(visual_label(short.get('visual_type', 'concept diagram')))}: show the input, animate the rule, label the intermediate quantity, and highlight the output.

\paragraph{{Common trap.}} {latex_escape(short['misconception'])}

\subsubsection*{{Questions}}
\begin{{questions}}
\item Conceptual: Explain {latex_escape(short['concept'])} without using the formula. What problem does the idea solve?
\item Symbol check: In the displayed formula, what does each symbol mean and what are its allowed inputs?
\item Calculation: Recreate the worked example, then change one number and predict which part of the answer changes.
\item Interpretation: Which part of the example is the input, which part is the rule, and which part is the output?
\item Application: {question_tex}
\item Error check: What mistake would someone make if they believed the common trap above?
\end{{questions}}

\paragraph{{Answers and explanations.}}
The displayed calculation gives the mechanical steps. The key interpretation is: {takeaway_tex} For the application question, {answer_tex}
""")
        practice_items.append(rf"\item \textbf{{{latex_escape(short['concept'])}.}} {question_tex} \emph{{Answer idea:}} {answer_tex}")
    tex = rf"""\documentclass[11pt]{{article}}
\usepackage[letterpaper,margin=0.95in]{{geometry}}
\usepackage{{amsmath,amssymb,amsthm,longtable,booktabs,array}}
\setlength{{\parskip}}{{0.35em}}
\setlength{{\parindent}}{{0pt}}
\renewcommand{{\arraystretch}}{{1.14}}
\newcolumntype{{L}}[1]{{>{{\raggedright\arraybackslash}}p{{#1}}}}
\newtheorem{{definition}}{{Definition}}[section]
\newtheorem{{formula}}{{Formula}}[section]
\newtheorem{{example}}{{Example}}[section]
\newenvironment{{questions}}{{\begin{{enumerate}}}}{{\end{{enumerate}}}}
\begin{{document}}
\begin{{center}}
\vspace*{{1.35in}}
{{\LARGE {latex_escape(title)} Comprehensive Notes\par}}
\vspace{{0.45in}}
{{\large \today\par}}
\end{{center}}
\vspace{{0.5in}}
\begin{{flushright}}
\begin{{minipage}}{{0.42\textwidth}}
\small Generated as a course-wide study document: definitions, formulas, examples, applications, and checks for understanding.\\[0.4em]
\hrule
\vspace{{0.3em}}
\hfill Course Shorts Skills
\end{{minipage}}
\end{{flushright}}
\vfill
\newpage

\section{{Course Overview}}
These notes are designed to be read as a course proxy: first learn the vocabulary, then the formulas, then the examples, then the questions. Each topic includes conceptual meaning, notation, a worked example, common traps, and application checks. The reference tables are compact; the topic sections carry the deeper explanations and worked calculations.

\subsection{{Source Inventory}}
\begin{{itemize}}
{source_inventory}
\end{{itemize}}

\subsection{{Prerequisite Order}}
\begin{{enumerate}}
{course_map}
\end{{enumerate}}

\section{{Key Concepts and Definitions}}
\small
\begin{{longtable}}{{@{{}}L{{0.07\linewidth}}L{{0.25\linewidth}}L{{0.62\linewidth}}@{{}}}}
\toprule
No. & Concept & Meaning and use \\
\midrule
\endhead
{definition_rows}
\bottomrule
\end{{longtable}}
\normalsize

\section{{Formula Reference}}
\small
\begin{{longtable}}{{@{{}}L{{0.08\linewidth}}L{{0.28\linewidth}}L{{0.58\linewidth}}@{{}}}}
\toprule
No. & Concept & Formula \\
\midrule
\endhead
{formula_rows}
\bottomrule
\end{{longtable}}
\normalsize

\section{{Notation and Symbol Meanings}}
\small
\begin{{longtable}}{{@{{}}L{{0.07\linewidth}}L{{0.25\linewidth}}L{{0.62\linewidth}}@{{}}}}
\toprule
No. & Concept & Symbols and meanings \\
\midrule
\endhead
{symbol_rows}
\bottomrule
\end{{longtable}}
\normalsize

\section{{Core Topics}}
{''.join(sections)}

\section{{Source-Derived Coverage Checklist}}
The following terms were detected in the source pack beyond the main planned topics. Use this checklist to prevent gaps when turning a full course into notes and shorts.
\begin{{itemize}}
{coverage_items}
\end{{itemize}}
{''.join(coverage_sections)}

\section{{Cumulative Practice Bank}}
\begin{{enumerate}}
{chr(10).join(practice_items)}
\end{{enumerate}}
\end{{document}}
"""
    (run / "notes.tex").write_text(tex, encoding="utf-8")
    (run / "notes.md").write_text(markdown_notes(plan, pack), encoding="utf-8")
    pdf_engine = "auto" if args.compile and args.pdf_engine == "none" else args.pdf_engine
    if args.compile or pdf_engine != "none":
        compile_notes_pdf(run, plan, pdf_engine)
    print(run / "notes.tex")


def markdown_notes(plan: dict[str, object], pack: dict[str, object] | None = None) -> str:
    lines = [f"# {plan.get('course_title', 'Course')} Definitions and Formulas\n"]
    lines.append("## Key Concepts\n")
    for short in plan["shorts"]:
        lines.append(f"- **{short['concept']}**: {short.get('concept_explanation', short['intuition'])}")
    lines.append("\n## Formula Reference\n")
    for short in plan["shorts"]:
        lines.append(f"- **{short['concept']}**: `{plain_formula_read(short)}` - {symbol_glossary(short)}")
    lines.append("\n")
    for short in plan["shorts"]:
        ex = short["worked_example"]
        qp = short["question_prompt"]
        lines.append(f"## {short['index']}. {short['concept']}\n")
        lines.append(f"**Key concept.** {short.get('key_concept', short['hook'])}\n")
        lines.append(f"**Concept explanation.** {short.get('concept_explanation', short['intuition'])}\n")
        lines.append(f"**How to recognize it.** {short.get('recognition_cue', 'Use the definition and worked example to decide when this idea applies.')}\n")
        lines.append(f"**Definition.** {short['intuition']}\n")
        lines.append(f"**Formula.** `{plain_formula_read(short)}`\n")
        lines.append(f"**Symbols.** {symbol_glossary(short)}\n")
        setup_md = latex_example_text(str(ex.get("setup", "")), short, "setup")
        calculation_md = latex_example_text(str(ex.get("calculation", "")), short, "calculation")
        takeaway_md = latex_example_text(str(ex.get("takeaway", "")), short, "takeaway")
        question_md = latex_text_with_inline_math(str(qp.get("question", "")), tuple_style="tuple")
        answer_md = latex_example_text(str(qp.get("answer", "")), short, "answer")
        lines.append(f"**Worked example.**\n\nSetup: {setup_md}\n\nCalculation: {calculation_md}\n\nInterpretation: {takeaway_md}\n")
        lines.append("**Questions.** Explain the concept without the formula; define every symbol; redo the example with one changed number; identify input/rule/output; answer the application prompt.\n")
        lines.append(f"**Application.** {question_md} Answer idea: {answer_md}\n")
    if pack:
        terms = source_coverage_terms(pack, plan.get("shorts", []), limit=40)
        if terms:
            lines.append("\n## Source-Derived Coverage Checklist\n")
            for term in terms:
                lines.append(f"- {term.title()}")
    return "\n".join(lines)


def wrap(text: str, width: int = 34, lines: int = 4) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    out = textwrap.wrap(normalized, width=width, break_long_words=False, break_on_hyphens=False)
    if len(out) > lines:
        out = out[: lines - 1] + [out[lines - 1].rstrip(".") + "..."]
    return out or [""]


MATRIX_LITERAL_RE = re.compile(r"\[\s*\[[^\[\]\n]+?\]\s*(?:,\s*\[[^\[\]\n]+?\]\s*)+\]")


def screen_matrix_literal(literal: str) -> str:
    try:
        rows = json.loads(literal)
    except json.JSONDecodeError:
        return "matrix"
    if not isinstance(rows, list) or not all(isinstance(row, list) for row in rows):
        return "matrix"
    row_text = ["(" + ", ".join(str(cell) for cell in row) + ")" for row in rows]
    return "matrix with rows " + "; ".join(row_text)


def screen_prose(text: object) -> str:
    normalized = str(text)
    normalized = MATRIX_LITERAL_RE.sub(lambda match: screen_matrix_literal(match.group(0)), normalized)
    normalized = re.sub(r"\b([A-Za-z]\w*)\s*=\s*matrix with rows", r"\1 is the matrix with rows", normalized)
    normalized = re.sub(r"\b([A-Za-z]\w*)\s*=\s*\[([^\]\n]{1,80})\]", r"\1 is the row matrix with entries \2", normalized)
    normalized = re.sub(r"\bsqrt\(([^)]*)\)", r"square root of \1", normalized)
    normalized = re.sub(r"([A-Za-z0-9_.]+)\s*\^\s*2\b", r"\1 squared", normalized)
    normalized = normalized.replace("*", " times ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def numeric_literals(text: str) -> list[object]:
    values: list[object] = []
    pairs = {"[": "]", "(": ")"}
    for start, opener in enumerate(text):
        if opener not in pairs:
            continue
        closer = pairs[opener]
        depth = 0
        for end in range(start, len(text)):
            char = text[end]
            if char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : end + 1]
                    try:
                        values.append(ast.literal_eval(candidate))
                    except Exception:
                        pass
                    break
    return values


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def numeric_vector(value: object) -> list[float] | None:
    if isinstance(value, (list, tuple)) and value and all(is_number(item) for item in value):
        return [float(item) for item in value]
    return None


def numeric_matrix(value: object) -> list[list[float]] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    rows: list[list[float]] = []
    width: int | None = None
    for row in value:
        if not isinstance(row, (list, tuple)) or not row or not all(is_number(item) for item in row):
            return None
        numeric_row = [float(item) for item in row]
        width = width or len(numeric_row)
        if len(numeric_row) != width:
            return None
        rows.append(numeric_row)
    return rows


def format_scalar(value: object) -> str:
    try:
        number = float(value)
    except Exception:
        return str(value)
    if math.isfinite(number) and abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.3g}"


def display_matrix(rows: list[list[float]]) -> list[list[str]]:
    return [[format_scalar(cell) for cell in row] for row in rows]


def display_vector(values: list[float]) -> list[str]:
    return [format_scalar(value) for value in values]


def extract_numbers(text: str, limit: int = 6) -> list[str]:
    out: list[str] = []
    for match in re.findall(r"(?<![A-Za-z])-?\d+(?:\.\d+)?", text):
        value = format_scalar(match)
        if value not in out:
            out.append(value)
        if len(out) >= limit:
            break
    return out or ["2", "5", "8"]


def short_text(short: dict[str, object]) -> str:
    ex = short.get("worked_example", {}) if isinstance(short.get("worked_example"), dict) else {}
    qp = short.get("question_prompt", {}) if isinstance(short.get("question_prompt"), dict) else {}
    return " ".join(
        str(part)
        for part in [
            short.get("concept", ""),
            short.get("hook", ""),
            short.get("intuition", ""),
            short.get("formula", ""),
            ex.get("setup", ""),
            ex.get("calculation", ""),
            ex.get("takeaway", ""),
            qp.get("question", ""),
            qp.get("answer", ""),
        ]
    )


def matrix_vector_data(short: dict[str, object]) -> dict[str, object]:
    text = short_text(short)
    literals = numeric_literals(text)
    matrices = [matrix for value in literals if (matrix := numeric_matrix(value))]
    vectors = [vector for value in literals if (vector := numeric_vector(value))]
    matrix = matrices[0] if matrices else [[2.0, 1.0], [1.0, 3.0]]
    row_count = len(matrix)
    col_count = len(matrix[0]) if matrix else 0
    vector: list[float] | None = None
    output: list[float] | None = None
    for candidate in vectors:
        if vector is None and len(candidate) == col_count:
            vector = candidate
            continue
        if output is None and len(candidate) == row_count:
            output = candidate
    if vector is None:
        vector = [4.0, 2.0][:col_count] or [1.0]
    if output is None:
        output = [sum(row[i] * vector[i] for i in range(min(len(row), len(vector)))) for row in matrix]
    columns = [[matrix[row][col] for row in range(row_count)] for col in range(col_count)]
    row_calcs = []
    for row, result in zip(matrix, output):
        terms = [f"{format_scalar(a)}*{format_scalar(b)}" for a, b in zip(row, vector)]
        row_calcs.append(f"{' + '.join(terms)} = {format_scalar(result)}")
    return {
        "matrix": display_matrix(matrix),
        "vector": display_vector(vector),
        "output": display_vector(output),
        "columns": [display_vector(column) for column in columns],
        "row_calcs": row_calcs,
    }


def vector_example_data(short: dict[str, object]) -> dict[str, object]:
    vectors = [vector for value in numeric_literals(short_text(short)) if (vector := numeric_vector(value))]
    vector = vectors[0] if vectors else [3.0, 4.0]
    if len(vector) < 2:
        vector = [vector[0], 0.0]
    length = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])
    return {
        "vector": display_vector(vector[:2]),
        "length": format_scalar(length),
        "x_range": [-1, max(5, int(abs(vector[0])) + 2), 1],
        "y_range": [-1, max(5, int(abs(vector[1])) + 2), 1],
    }


def linear_combo_data(short: dict[str, object]) -> dict[str, object]:
    text = short_text(short)
    vectors = [vector for value in numeric_literals(text) if (vector := numeric_vector(value))]
    a = vectors[0] if len(vectors) > 0 else [1.0, 0.0]
    b = vectors[1] if len(vectors) > 1 else [1.0, 1.0]
    target = vectors[2] if len(vectors) > 2 else [5.0, 2.0]
    weights = [3.0, 2.0]
    match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*\*?\s*a\s*\+\s*([+-]?\d+(?:\.\d+)?)\s*\*?\s*b", text, re.I)
    if match:
        weights = [float(match.group(1)), float(match.group(2))]
    return {
        "a": display_vector(a[:2]),
        "b": display_vector(b[:2]),
        "target": display_vector(target[:2]),
        "weights": display_vector(weights),
    }


def infer_visual_kind(short: dict[str, object]) -> str:
    explicit = str(short.get("visual_type", "generic")).strip().lower()
    if explicit and explicit != "generic":
        return explicit
    text = short_text(short).lower()
    if any(term in text for term in ("matrix", "linear system", "ax=", "a\\vec", "row operation")):
        return "matrix_vector"
    if "vector" in text or "coordinate" in text:
        return "vector_components"
    if any(term in text for term in ("derivative", "tangent", "slope", "gradient", "rate of change")):
        return "calculus_tangent"
    if any(term in text for term in ("integral", "area under", "accumulation", "riemann")):
        return "calculus_area"
    if any(term in text for term in ("force", "newton", "acceleration", "velocity", "momentum")):
        return "physics_force"
    if any(term in text for term in ("energy", "work", "potential", "kinetic")):
        return "physics_energy"
    if any(term in text for term in ("wave", "frequency", "amplitude", "oscillation")):
        return "physics_wave"
    if any(term in text for term in ("graph", "tree", "network", "path", "node", "edge")):
        return "cs_graph"
    if any(term in text for term in ("algorithm", "array", "sort", "search", "complexity", "runtime")):
        return "cs_array"
    if any(term in text for term in ("state", "automaton", "transition", "markov")):
        return "state_machine"
    if any(term in text for term in ("probability", "bayes", "distribution", "random", "expectation")):
        return "probability"
    if any(term in text for term in ("reaction", "molecule", "atom", "equilibrium", "chemical")):
        return "chemistry_reaction"
    return "numeric_rule"


def visual_data_for(short: dict[str, object], kind: str) -> dict[str, object]:
    return {
        "matrix_vector": matrix_vector_data(short),
        "vector": vector_example_data(short),
        "linear_combo": linear_combo_data(short),
        "numbers": extract_numbers(short_text(short)),
    }


MANIM_SCENE_HELPERS = '''
def fmt(self, value):
    text = str(value)
    try:
        number = float(text)
    except Exception:
        return text
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.3g}"

def palette(self, index):
    colors = ["#58A6FF", "#F7C948", "#7EE787", "#FF7B72", "#A371F7"]
    return colors[index % len(colors)]

def fit_in(self, mob, max_width=7.8, max_height=6.0):
    if mob.width > max_width:
        mob.scale(max_width / mob.width)
    if mob.height > max_height:
        mob.scale(max_height / mob.height)
    return mob

def validate_layout(self, mob, name="mobject", pad=0.24):
    left_limit = -config.frame_width / 2 + pad
    right_limit = config.frame_width / 2 - pad
    bottom_limit = -config.frame_height / 2 + pad
    top_limit = config.frame_height / 2 - pad
    if mob.get_left()[0] < left_limit or mob.get_right()[0] > right_limit:
        self.fit_in(mob, max_width=config.frame_width - 2 * pad, max_height=config.frame_height - 2 * pad)
    if mob.get_bottom()[1] < bottom_limit:
        mob.shift(UP * (bottom_limit - mob.get_bottom()[1]))
    if mob.get_top()[1] > top_limit:
        mob.shift(DOWN * (mob.get_top()[1] - top_limit))
    return mob

def safe_place(self, mob, y=0, max_width=7.8, max_height=6.0, top=6.15, bottom=-7.25):
    self.fit_in(mob, max_width=max_width, max_height=max_height)
    mob.move_to(UP * y)
    if mob.get_top()[1] > top:
        mob.shift(DOWN * (mob.get_top()[1] - top))
    if mob.get_bottom()[1] < bottom:
        mob.shift(UP * (bottom - mob.get_bottom()[1]))
    return self.validate_layout(mob)

def text_block(self, lines, font_size=25, color="#EAF2FF", max_width=7.4, line_buff=0.12):
    group = VGroup(*[Text(str(line), font_size=font_size, color=color) for line in lines]).arrange(DOWN, buff=line_buff)
    return self.fit_in(group, max_width=max_width, max_height=2.3)

def formula_block(self, latex, plain, font_size=32, color="#F7C948", max_width=7.6):
    try:
        mob = MathTex(str(latex), font_size=font_size, color=color)
    except Exception:
        mob = Text(str(plain or latex), font_size=font_size, color=color)
    return self.fit_in(mob, max_width=max_width, max_height=1.15)

def section_label(self, text, color="#F7C948"):
    label = Text(text, font_size=30, weight="BOLD", color=color)
    return self.safe_place(label, y=5.7, max_width=7.6, max_height=0.65, top=6.05, bottom=5.15)

def fade_all_except(self, keep=None, run_time=0.6):
    keep = set(keep or [])
    fading = [mob for mob in self.mobjects if mob not in keep]
    if fading:
        self.play(*[FadeOut(mob) for mob in fading], run_time=run_time)

def matrix_block(self, rows, font_size=30, color="#EAF2FF", bracket_color="#8FD3FF", column_colors=None, cell_colors=None):
    row_groups = VGroup()
    cell_colors = cell_colors or {}
    for r, row in enumerate(rows):
        cells = VGroup()
        for c, cell in enumerate(row):
            cell_color = cell_colors.get((r, c))
            if cell_color is None and column_colors:
                cell_color = column_colors[c % len(column_colors)]
            cells.add(Text(str(cell), font_size=font_size, color=cell_color or color))
        row_groups.add(cells.arrange(RIGHT, buff=0.42))
    row_groups.arrange(DOWN, buff=0.22)
    left = Text("[", font_size=78, color=bracket_color).stretch_to_fit_height(row_groups.height + 0.35).next_to(row_groups, LEFT, buff=0.12)
    right = Text("]", font_size=78, color=bracket_color).stretch_to_fit_height(row_groups.height + 0.35).next_to(row_groups, RIGHT, buff=0.12)
    return VGroup(left, row_groups, right)

def matrix_equation(self, data, font_size=28):
    col_colors = [self.palette(i) for i in range(max(1, len(data.get("columns", []))))]
    matrix = self.matrix_block(data["matrix"], font_size=font_size, bracket_color="#58A6FF", column_colors=col_colors)
    vector = self.matrix_block([[v] for v in data["vector"]], font_size=font_size, color="#F7C948", bracket_color="#F7C948")
    output = self.matrix_block([[v] for v in data["output"]], font_size=font_size, color="#7EE787", bracket_color="#7EE787")
    return VGroup(matrix, Text("x", font_size=font_size + 2, color="#EAF2FF"), vector, Text("=", font_size=font_size + 2, color="#EAF2FF"), output).arrange(RIGHT, buff=0.24)

def matrix_column_combo(self, data, font_size=24, include_output=True):
    parts = VGroup()
    columns = data.get("columns", [])
    for i, column in enumerate(columns):
        if i:
            parts.add(Text("+", font_size=font_size, color="#EAF2FF"))
        parts.add(Text(str(data["vector"][i]), font_size=font_size + 1, color="#EAF2FF"))
        parts.add(self.matrix_block([[v] for v in column], font_size=font_size, color=self.palette(i), bracket_color=self.palette(i)))
    if include_output:
        parts.add(Text("=", font_size=font_size, color="#EAF2FF"))
        parts.add(self.matrix_block([[v] for v in data["output"]], font_size=font_size, color="#7EE787", bracket_color="#7EE787"))
    return parts.arrange(RIGHT, buff=0.14)

def play_matrix_vector_intro(self, data):
    equation = self.matrix_equation(data, font_size=30)
    self.safe_place(equation, y=1.55, max_width=8.0, max_height=2.25, top=3.95, bottom=-0.35)
    combo = self.matrix_column_combo(data, font_size=24)
    self.safe_place(combo, y=-1.65, max_width=8.15, max_height=2.35, top=0.0, bottom=-3.65)
    box = SurroundingRectangle(combo[-1], color="#7EE787", buff=0.12)
    self.play(FadeIn(equation, shift=UP * 0.1), run_time=1.0)
    self.play(LaggedStart(*[FadeIn(mob, shift=UP * 0.08) for mob in combo], lag_ratio=0.12), run_time=1.5)
    self.play(Create(box), Indicate(combo[-1]), run_time=0.9)

def play_matrix_vector_example(self, data, setup_lines, calc_lines, takeaway_lines):
    setup_caption = Text("Let the matrix A act on the input vector x.", font_size=20, color="#8FD3FF")
    setup_math = VGroup(
        Text("A =", font_size=20, color="#EAF2FF"),
        self.matrix_block(data["matrix"], font_size=18, bracket_color="#58A6FF", column_colors=[self.palette(i) for i in range(len(data.get("columns", [])))]),
        Text("x =", font_size=20, color="#EAF2FF"),
        self.matrix_block([[v] for v in data["vector"]], font_size=18, color="#F7C948", bracket_color="#F7C948"),
    ).arrange(RIGHT, buff=0.14)
    setup = VGroup(setup_caption, setup_math).arrange(DOWN, buff=0.14)
    self.safe_place(setup, y=4.55, max_width=7.7, max_height=1.25, top=5.2, bottom=3.85)
    equation = self.matrix_equation(data, font_size=27)
    self.safe_place(equation, y=2.55, max_width=8.05, max_height=2.0, top=3.8, bottom=1.25)
    row_group = VGroup(*[Text(line, font_size=25, color=self.palette(i)) for i, line in enumerate(data.get("row_calcs", []))]).arrange(DOWN, buff=0.22)
    self.safe_place(row_group, y=0.0, max_width=7.8, max_height=1.45, top=0.9, bottom=-1.0)
    combo = self.matrix_column_combo(data, font_size=23)
    self.safe_place(combo, y=-2.55, max_width=8.1, max_height=2.15, top=-1.25, bottom=-4.0)
    takeaway = self.text_block(takeaway_lines, font_size=23, color="#7EE787", max_width=7.4)
    self.safe_place(takeaway, y=-5.65, max_height=1.05, top=-5.0, bottom=-6.55)
    self.play(FadeIn(setup, shift=UP * 0.08), FadeIn(equation, shift=UP * 0.08), run_time=1.0)
    matrix = equation[0]
    row_box = None
    for i, row_text in enumerate(row_group):
        new_box = SurroundingRectangle(matrix[1][i], color=self.palette(i), buff=0.08)
        if row_box is None:
            row_box = new_box
            self.play(Create(row_box), FadeIn(row_text, shift=UP * 0.08), run_time=0.75)
        else:
            self.play(Transform(row_box, new_box), FadeIn(row_text, shift=UP * 0.08), run_time=0.75)
    if row_box is not None:
        self.play(FadeOut(row_box), run_time=0.35)
    self.play(LaggedStart(*[FadeIn(mob, shift=UP * 0.08) for mob in combo], lag_ratio=0.08), run_time=1.2)
    self.play(Indicate(combo[-1]), FadeIn(takeaway, shift=UP * 0.08), run_time=1.0)

def play_matrix_vector_recall(self, data, question_lines, answer_lines):
    prompt = self.text_block(question_lines, font_size=22, color="#EAF2FF", max_width=7.4)
    self.safe_place(prompt, y=4.65, max_height=1.1, top=5.1, bottom=3.8)
    matrix = self.matrix_block(data["matrix"], font_size=24, bracket_color="#58A6FF", column_colors=[self.palette(i) for i in range(len(data.get("columns", [])))])
    vector = self.matrix_block([[v] for v in data["vector"]], font_size=24, color="#F7C948", bracket_color="#F7C948")
    unknown = self.matrix_block([["?"] for _ in data["output"]], font_size=24, color="#7EE787", bracket_color="#7EE787")
    pipeline = VGroup(VGroup(Text("effects", font_size=18, color="#58A6FF"), matrix).arrange(DOWN, buff=0.12), Text("x", font_size=28), VGroup(Text("weights", font_size=18, color="#F7C948"), vector).arrange(DOWN, buff=0.12), Text("->", font_size=28), VGroup(Text("response", font_size=18, color="#7EE787"), unknown).arrange(DOWN, buff=0.12)).arrange(RIGHT, buff=0.2)
    self.safe_place(pipeline, y=1.35, max_width=8.1, max_height=2.8, top=3.1, bottom=-0.6)
    combo = self.matrix_column_combo(data, font_size=22)
    self.safe_place(combo, y=-1.8, max_width=8.1, max_height=2.0, top=-0.8, bottom=-3.3)
    answer = self.text_block(answer_lines, font_size=22, color="#7EE787", max_width=7.4)
    self.safe_place(answer, y=-5.25, max_height=1.35, top=-4.35, bottom=-6.35)
    self.play(FadeIn(prompt, shift=UP * 0.08), FadeIn(pipeline, shift=UP * 0.08), run_time=1.1)
    self.play(LaggedStart(*[FadeIn(mob, shift=UP * 0.06) for mob in combo], lag_ratio=0.08), run_time=1.15)
    self.play(Transform(unknown, self.matrix_block([[v] for v in data["output"]], font_size=24, color="#7EE787", bracket_color="#7EE787").move_to(unknown)), FadeIn(answer, shift=UP * 0.08), run_time=1.0)
    self.play(Indicate(combo[-1]), run_time=0.8)

def vector_plane_objects(self, data):
    vx = float(data["vector"][0])
    vy = float(data["vector"][1])
    plane = NumberPlane(x_range=data.get("x_range", [-1, 5, 1]), y_range=data.get("y_range", [-1, 5, 1]), x_length=6.7, y_length=4.9, background_line_style={"stroke_color": "#1F3558", "stroke_width": 1, "stroke_opacity": 0.7})
    self.safe_place(plane, y=0.9, max_width=7.3, max_height=5.0, top=3.9, bottom=-2.1)
    origin = plane.c2p(0, 0)
    x_end = plane.c2p(vx, 0)
    end = plane.c2p(vx, vy)
    x_leg = Arrow(origin, x_end, buff=0, color="#F7C948", stroke_width=7)
    y_leg = Arrow(x_end, end, buff=0, color="#7EE787", stroke_width=7)
    vec = Arrow(origin, end, buff=0, color="#58A6FF", stroke_width=8)
    labels = VGroup(Text(str(data["vector"][0]), font_size=26, color="#F7C948").next_to(x_leg, DOWN), Text(str(data["vector"][1]), font_size=26, color="#7EE787").next_to(y_leg, RIGHT), Text("length " + str(data["length"]), font_size=26, color="#8FD3FF").next_to(vec, UP))
    return plane, x_leg, y_leg, vec, labels

def play_vector_intro(self, data):
    plane, x_leg, y_leg, vec, labels = self.vector_plane_objects(data)
    self.play(Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.1)
    self.play(GrowArrow(vec), FadeIn(labels), run_time=1.2)
    self.play(Indicate(labels[2]), run_time=0.8)

def play_vector_example(self, data, setup_lines, calc_lines, takeaway_lines):
    setup = self.text_block(setup_lines, font_size=21, color="#8FD3FF")
    self.safe_place(setup, y=4.65, max_height=0.85, top=5.1, bottom=4.0)
    plane, x_leg, y_leg, vec, labels = self.vector_plane_objects(data)
    formula = Text(f"{data['vector'][0]}^2 + {data['vector'][1]}^2 -> length {data['length']}", font_size=27, color="#F7C948")
    self.safe_place(formula, y=-3.4, max_width=7.4, max_height=0.55, top=-3.05, bottom=-3.8)
    takeaway = self.text_block(takeaway_lines, font_size=23, color="#7EE787")
    self.safe_place(takeaway, y=-5.45, max_height=1.0, top=-4.8, bottom=-6.3)
    self.play(FadeIn(setup), Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.1)
    self.play(GrowArrow(vec), FadeIn(labels), run_time=1.0)
    self.play(Write(formula), FadeIn(takeaway, shift=UP * 0.08), run_time=1.0)

def play_vector_recall(self, data, question_lines, answer_lines):
    prompt = self.text_block(question_lines, font_size=22)
    self.safe_place(prompt, y=4.55, max_height=1.1, top=5.1, bottom=3.75)
    plane, x_leg, y_leg, vec, labels = self.vector_plane_objects(data)
    answer = self.text_block(answer_lines, font_size=22, color="#7EE787")
    self.safe_place(answer, y=-5.1, max_height=1.4, top=-4.25, bottom=-6.3)
    self.play(FadeIn(prompt), Create(plane), GrowArrow(x_leg), GrowArrow(y_leg), run_time=1.1)
    self.play(GrowArrow(vec), FadeIn(labels), run_time=1.0)
    self.play(FadeIn(answer, shift=UP * 0.08), Indicate(labels[2]), run_time=0.9)

def linear_combo_objects(self, data):
    ax, ay = [float(v) for v in data["a"]]
    bx, by = [float(v) for v in data["b"]]
    tx, ty = [float(v) for v in data["target"]]
    plane = NumberPlane(x_range=[-1, max(6, int(max(abs(ax), abs(bx), abs(tx))) + 2), 1], y_range=[-1, max(5, int(max(abs(ay), abs(by), abs(ty))) + 2), 1], x_length=6.8, y_length=4.8, background_line_style={"stroke_color": "#1F3558", "stroke_width": 1, "stroke_opacity": 0.7})
    self.safe_place(plane, y=0.8, max_width=7.3, max_height=5.0, top=3.8, bottom=-2.1)
    origin = plane.c2p(0, 0)
    a = Arrow(origin, plane.c2p(ax, ay), buff=0, color="#58A6FF", stroke_width=7)
    b = Arrow(origin, plane.c2p(bx, by), buff=0, color="#F7C948", stroke_width=7)
    first = Arrow(origin, plane.c2p(ax * float(data["weights"][0]), ay * float(data["weights"][0])), buff=0, color="#58A6FF", stroke_width=8)
    second = Arrow(first.get_end(), plane.c2p(tx, ty), buff=0, color="#F7C948", stroke_width=8)
    target = Dot(plane.c2p(tx, ty), radius=0.09, color="#7EE787")
    label = Text(f"{data['weights'][0]}a + {data['weights'][1]}b = ({data['target'][0]}, {data['target'][1]})", font_size=25, color="#7EE787")
    self.safe_place(label, y=-3.35, max_width=7.4, max_height=0.55, top=-3.05, bottom=-3.8)
    return plane, a, b, first, second, target, label

def play_linear_combo_intro(self, data):
    plane, a, b, first, second, target, label = self.linear_combo_objects(data)
    self.play(Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
    self.play(TransformFromCopy(a, first), TransformFromCopy(b, second), FadeIn(target, scale=1.3), run_time=1.25)
    self.play(FadeIn(label), Flash(target, color="#7EE787"), run_time=0.9)

def play_linear_combo_example(self, data, setup_lines, calc_lines, takeaway_lines):
    setup = self.text_block(setup_lines, font_size=21, color="#8FD3FF")
    self.safe_place(setup, y=4.65, max_height=0.85, top=5.1, bottom=4.0)
    plane, a, b, first, second, target, label = self.linear_combo_objects(data)
    takeaway = self.text_block(takeaway_lines, font_size=23, color="#7EE787")
    self.safe_place(takeaway, y=-5.45, max_height=1.0, top=-4.8, bottom=-6.3)
    self.play(FadeIn(setup), Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
    self.play(GrowArrow(first), GrowArrow(second), FadeIn(target), run_time=1.1)
    self.play(FadeIn(label), FadeIn(takeaway, shift=UP * 0.08), Indicate(target), run_time=1.0)

def play_linear_combo_recall(self, data, question_lines, answer_lines):
    prompt = self.text_block(question_lines, font_size=22)
    self.safe_place(prompt, y=4.55, max_height=1.1, top=5.1, bottom=3.75)
    plane, a, b, first, second, target, label = self.linear_combo_objects(data)
    answer = self.text_block(answer_lines, font_size=22, color="#7EE787")
    self.safe_place(answer, y=-5.1, max_height=1.4, top=-4.25, bottom=-6.3)
    self.play(FadeIn(prompt), Create(plane), GrowArrow(a), GrowArrow(b), run_time=1.1)
    self.play(GrowArrow(first), GrowArrow(second), FadeIn(target), FadeIn(label), run_time=1.1)
    self.play(FadeIn(answer, shift=UP * 0.08), Flash(target, color="#7EE787"), run_time=0.9)

def play_calculus_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    axes = Axes(x_range=[-1, 4, 1], y_range=[0, 5, 1], x_length=6.7, y_length=4.6, tips=False).shift(DOWN * 0.1)
    self.safe_place(axes, y=0.65, max_width=7.2, max_height=4.8, top=3.3, bottom=-2.2)
    curve = axes.plot(lambda x: 0.45 * (x - 0.5) * (x - 0.5) + 0.8, x_range=[-0.4, 3.7], color="#F7C948", stroke_width=6)
    if kind == "calculus_area":
        rects = axes.get_riemann_rectangles(curve, x_range=[0.2, 3.2], dx=0.5, color="#58A6FF", fill_opacity=0.45, stroke_width=1)
        result = self.text_block(result_lines or secondary_lines or ["accumulated area"], font_size=22, color="#7EE787")
        self.safe_place(result, y=-5.15, max_height=1.3, top=-4.25, bottom=-6.35)
        self.play(FadeIn(caption), Create(axes), Create(curve), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(rect, shift=UP * 0.05) for rect in rects], lag_ratio=0.05), run_time=1.2)
        self.play(FadeIn(result, shift=UP * 0.08), Indicate(rects), run_time=0.9)
        return
    p1 = Dot(axes.c2p(1.0, 0.45 * (1.0 - 0.5) * (1.0 - 0.5) + 0.8), color="#58A6FF")
    p2 = Dot(axes.c2p(2.6, 0.45 * (2.6 - 0.5) * (2.6 - 0.5) + 0.8), color="#7EE787")
    secant = Line(p1.get_center(), p2.get_center(), color="#58A6FF", stroke_width=5)
    tangent = Line(axes.c2p(0.0, 0.55), axes.c2p(2.2, 1.55), color="#7EE787", stroke_width=5)
    result = self.text_block(result_lines or secondary_lines or ["local slope"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.15, max_height=1.3, top=-4.25, bottom=-6.35)
    self.play(FadeIn(caption), Create(axes), Create(curve), FadeIn(p1), FadeIn(p2), run_time=1.0)
    self.play(Create(secant), run_time=0.7)
    self.play(Transform(secant, tangent), FadeIn(result, shift=UP * 0.08), run_time=1.1)

def play_physics_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    block = RoundedRectangle(width=1.4, height=0.9, corner_radius=0.1, color="#EAF2FF", fill_color="#101A33", fill_opacity=0.9)
    self.safe_place(block, y=0.65, max_width=2.0, max_height=1.2, top=1.4, bottom=-0.1)
    floor = Line(LEFT * 3.2, RIGHT * 3.2, color="#1F3558", stroke_width=4).next_to(block, DOWN, buff=0.05)
    force = Arrow(block.get_right(), block.get_right() + RIGHT * 2.1, buff=0.05, color="#58A6FF", stroke_width=8)
    friction = Arrow(block.get_left(), block.get_left() + LEFT * 1.2, buff=0.05, color="#FF7B72", stroke_width=6)
    accel = Arrow(block.get_top(), block.get_top() + RIGHT * 1.4 + UP * 0.7, buff=0.05, color="#7EE787", stroke_width=7)
    result = self.text_block(result_lines or secondary_lines or ["net change"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(block), Create(floor), run_time=0.9)
    self.play(GrowArrow(force), GrowArrow(friction), run_time=0.9)
    self.play(GrowArrow(accel), FadeIn(result, shift=UP * 0.08), Indicate(block), run_time=1.0)

def play_wave_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    axes = Axes(x_range=[0, 7, 1], y_range=[-1.5, 1.5, 1], x_length=7.0, y_length=3.8, tips=False)
    self.safe_place(axes, y=0.55, max_width=7.4, max_height=4.0, top=2.8, bottom=-2.0)
    wave = axes.plot(lambda x: math.sin(2 * x), x_range=[0, 6.6], color="#58A6FF", stroke_width=6)
    dot = Dot(axes.c2p(1.0, math.sin(2.0)), color="#F7C948")
    dot2 = Dot(axes.c2p(2.2, math.sin(4.4)), color="#F7C948")
    result = self.text_block(result_lines or secondary_lines or ["amplitude and phase move together"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), Create(axes), Create(wave), FadeIn(dot), run_time=1.0)
    self.play(Transform(dot, dot2), FadeIn(result, shift=UP * 0.08), run_time=1.1)

def play_cs_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    if kind == "cs_graph":
        nodes = VGroup(*[Circle(radius=0.28, color=self.palette(i), fill_opacity=0.15) for i in range(5)])
        positions = [LEFT * 2.4 + UP * 0.7, LEFT * 0.8 + UP * 1.2, RIGHT * 0.8 + UP * 0.25, LEFT * 0.4 + DOWN * 1.0, RIGHT * 2.3 + DOWN * 0.55]
        for i, node in enumerate(nodes):
            node.move_to(positions[i])
            node.add(Text(chr(65 + i), font_size=20, color=self.palette(i)).move_to(node))
        edges = VGroup(Line(nodes[0].get_center(), nodes[1].get_center(), color="#1F3558"), Line(nodes[1].get_center(), nodes[2].get_center(), color="#1F3558"), Line(nodes[1].get_center(), nodes[3].get_center(), color="#1F3558"), Line(nodes[2].get_center(), nodes[4].get_center(), color="#1F3558"))
        graph = VGroup(edges, nodes)
        self.safe_place(graph, y=0.4, max_width=7.0, max_height=4.0, top=2.8, bottom=-2.4)
        path = VGroup(*[Line(nodes[i].get_center(), nodes[j].get_center(), color="#7EE787", stroke_width=6) for i, j in [(0, 1), (1, 2), (2, 4)]])
        result = self.text_block(result_lines or secondary_lines or ["trace the reachable path"], font_size=22, color="#7EE787")
        self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
        self.play(FadeIn(caption), Create(edges), FadeIn(nodes), run_time=1.0)
        self.play(LaggedStart(*[Create(edge) for edge in path], lag_ratio=0.18), FadeIn(result, shift=UP * 0.08), run_time=1.2)
        return
    values = data.get("numbers", ["4", "1", "7", "3", "9"])
    cells = VGroup(*[VGroup(Square(0.72, color=self.palette(i), fill_opacity=0.18), Text(str(values[i % len(values)]), font_size=22, color="#EAF2FF")) for i in range(5)]).arrange(RIGHT, buff=0.08)
    self.safe_place(cells, y=0.75, max_width=7.4, max_height=1.2, top=1.55, bottom=0.0)
    pointer = Triangle(color="#F7C948", fill_opacity=0.9).scale(0.18).rotate(PI).next_to(cells[0], UP, buff=0.18)
    result = self.text_block(result_lines or secondary_lines or ["state changes one step at a time"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(cells), FadeIn(pointer), run_time=0.9)
    for cell in cells[1:4]:
        self.play(pointer.animate.next_to(cell, UP, buff=0.18), cell[0].animate.set_fill(self.palette(2), opacity=0.35), run_time=0.35)
    self.play(FadeIn(result, shift=UP * 0.08), Indicate(cells[3]), run_time=0.8)

def play_probability_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    heights = [1.0, 1.9, 2.8, 1.4]
    bars = VGroup()
    for i, height in enumerate(heights):
        rect = Rectangle(width=0.62, height=height, color=self.palette(i), fill_opacity=0.45).align_to(ORIGIN, DOWN)
        bars.add(rect)
    bars.arrange(RIGHT, buff=0.22).move_to(ORIGIN)
    self.safe_place(bars, y=0.5, max_width=5.2, max_height=3.2, top=2.4, bottom=-1.9)
    brace = Brace(bars[1:3], UP, color="#F7C948")
    result = self.text_block(result_lines or secondary_lines or ["update the mass, then compare"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.1), run_time=1.1)
    self.play(GrowFromCenter(brace), bars[2].animate.set_fill("#7EE787", opacity=0.7), FadeIn(result, shift=UP * 0.08), run_time=1.0)

def play_chemistry_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    left = VGroup(Circle(0.28, color="#58A6FF", fill_opacity=0.25), Circle(0.28, color="#F7C948", fill_opacity=0.25).shift(RIGHT * 0.48)).arrange(RIGHT, buff=-0.08)
    right = VGroup(Circle(0.28, color="#58A6FF", fill_opacity=0.25), Circle(0.28, color="#F7C948", fill_opacity=0.25), Circle(0.28, color="#7EE787", fill_opacity=0.25)).arrange(RIGHT, buff=-0.08)
    reaction = VGroup(left, Text("+", font_size=28), Circle(0.25, color="#7EE787", fill_opacity=0.25), Text("->", font_size=28), right).arrange(RIGHT, buff=0.24)
    self.safe_place(reaction, y=0.75, max_width=7.3, max_height=1.4, top=1.7, bottom=-0.2)
    result = self.text_block(result_lines or secondary_lines or ["rearrange pieces, conserve counts"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(reaction[:3]), run_time=0.9)
    self.play(FadeIn(reaction[3:]), FadeIn(result, shift=UP * 0.08), Indicate(right), run_time=1.0)

def play_numeric_rule_visual(self, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    caption = self.text_block(primary_lines, font_size=21, color="#8FD3FF")
    self.safe_place(caption, y=4.55, max_height=1.0, top=5.1, bottom=3.85)
    nums = data.get("numbers", ["2", "5", "8"])
    inputs = VGroup(*[VGroup(Circle(0.26, color=self.palette(i), fill_opacity=0.18), Text(str(num), font_size=18, color="#EAF2FF")) for i, num in enumerate(nums[:3])]).arrange(DOWN, buff=0.12)
    rule_box = RoundedRectangle(width=1.65, height=1.0, corner_radius=0.12, color="#F7C948", fill_color="#101A33", fill_opacity=0.92)
    rule = VGroup(rule_box, Text("rule", font_size=23, color="#F7C948").move_to(rule_box))
    outputs = VGroup(*[VGroup(Circle(0.26, color="#7EE787", fill_opacity=0.18), Text("?", font_size=18, color="#7EE787")) for _ in nums[:3]]).arrange(DOWN, buff=0.12)
    diagram = VGroup(inputs, Text("->", font_size=28), rule, Text("->", font_size=28), outputs).arrange(RIGHT, buff=0.22)
    self.safe_place(diagram, y=0.65, max_width=7.4, max_height=2.4, top=2.15, bottom=-1.3)
    result = self.text_block(result_lines or secondary_lines or ["watch input, rule, output"], font_size=22, color="#7EE787")
    self.safe_place(result, y=-5.05, max_height=1.35, top=-4.2, bottom=-6.25)
    self.play(FadeIn(caption), FadeIn(inputs), FadeIn(rule), run_time=0.9)
    self.play(LaggedStart(*[Transform(outputs[i][1], Text(str(nums[min(i + 1, len(nums) - 1)]), font_size=18, color="#7EE787").move_to(outputs[i][1])) for i in range(len(outputs))], lag_ratio=0.12), FadeIn(outputs), run_time=1.1)
    self.play(FadeIn(result, shift=UP * 0.08), Indicate(rule), run_time=0.9)

def play_generic_visual(self, kind, phase, data, primary_lines, secondary_lines=None, result_lines=None):
    if kind in {"calculus_tangent", "calculus_area"}:
        return self.play_calculus_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"physics_force", "physics_energy"}:
        return self.play_physics_visual(kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind == "physics_wave":
        return self.play_wave_visual(phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"cs_array", "cs_graph", "state_machine"}:
        return self.play_cs_visual("cs_graph" if kind == "state_machine" else kind, phase, data, primary_lines, secondary_lines, result_lines)
    if kind in {"probability", "markov"}:
        return self.play_probability_visual(phase, data, primary_lines, secondary_lines, result_lines)
    if kind == "chemistry_reaction":
        return self.play_chemistry_visual(phase, data, primary_lines, secondary_lines, result_lines)
    return self.play_numeric_rule_visual(phase, data, primary_lines, secondary_lines, result_lines)

def play_intro_visual(self, kind, data):
    if kind == "matrix_vector":
        return self.play_matrix_vector_intro(data["matrix_vector"])
    if kind == "vector_components":
        return self.play_vector_intro(data["vector"])
    if kind == "linear_combination":
        return self.play_linear_combo_intro(data["linear_combo"])
    if kind in {"basis", "subspace", "transform_grid", "systems", "least_squares", "elimination", "matrix_factor", "projection", "eigen", "svd", "area", "dimension_bar", "quadratic"}:
        mapped = {"projection": "calculus_tangent", "area": "calculus_area", "quadratic": "calculus_tangent"}.get(kind, "numeric_rule")
        return self.play_generic_visual(mapped, "intro", data, ["visualize the structure"], ["follow the colored objects"], ["highlight the output"])
    return self.play_generic_visual(kind, "intro", data, ["input -> rule -> output"], ["the diagram carries the example"], ["watch the state change"])

def play_example_visual(self, kind, data, setup_lines, calc_lines, takeaway_lines):
    if kind == "matrix_vector":
        return self.play_matrix_vector_example(data["matrix_vector"], setup_lines, calc_lines, takeaway_lines)
    if kind == "vector_components":
        return self.play_vector_example(data["vector"], setup_lines, calc_lines, takeaway_lines)
    if kind == "linear_combination":
        return self.play_linear_combo_example(data["linear_combo"], setup_lines, calc_lines, takeaway_lines)
    mapped = {"projection": "calculus_tangent", "area": "calculus_area", "quadratic": "calculus_tangent", "markov": "probability"}.get(kind, kind)
    return self.play_generic_visual(mapped, "example", data, setup_lines, calc_lines, takeaway_lines)

def play_recall_visual(self, kind, data, question_lines, answer_lines):
    if kind == "matrix_vector":
        return self.play_matrix_vector_recall(data["matrix_vector"], question_lines, answer_lines)
    if kind == "vector_components":
        return self.play_vector_recall(data["vector"], question_lines, answer_lines)
    if kind == "linear_combination":
        return self.play_linear_combo_recall(data["linear_combo"], question_lines, answer_lines)
    mapped = {"projection": "calculus_tangent", "area": "calculus_area", "quadratic": "calculus_tangent", "markov": "probability"}.get(kind, kind)
    return self.play_generic_visual(mapped, "recall", data, question_lines, answer_lines, answer_lines)
'''


def manim_scene(short: dict[str, object], class_name: str) -> str:
    visual_kind = infer_visual_kind(short)
    setup = screen_prose(short["worked_example"]["setup"])
    calc = screen_prose(short["worked_example"]["calculation"])
    takeaway = screen_prose(short["worked_example"]["takeaway"])
    question = screen_prose(short["question_prompt"]["question"])
    answer = screen_prose(short["question_prompt"]["answer"])
    visual_data = visual_data_for(short, visual_kind)
    return f'''from manim import *
import math

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 9
config.frame_height = 16
config.background_color = "#0B1020"


class {class_name}(Scene):
{textwrap.indent(MANIM_SCENE_HELPERS, "    ")}

    def construct(self):
        self.camera.background_color = "#0B1020"
        visual_kind = {visual_kind!r}
        visual_data = {visual_data!r}
        setup_lines = {wrap(setup, 44, 2)!r}
        calc_lines = {wrap(calc, 42, 3)!r}
        takeaway_lines = {wrap(takeaway, 40, 2)!r}
        question_lines = {wrap(question, 40, 3)!r}
        answer_lines = {wrap(answer, 40, 3)!r}

        title = Text({short["concept"]!r}, font_size=45, weight="BOLD", color="#EAF2FF")
        self.safe_place(title, y=7.15, max_width=8.25, max_height=0.85, top=7.55, bottom=6.55)
        hook = self.text_block({wrap(str(short["hook"]), 34, 3)!r}, font_size=26, color="#8FD3FF", max_width=7.6).next_to(title, DOWN, buff=0.22)
        self.fit_in(hook, max_width=7.6, max_height=1.25)
        self.play(FadeIn(title, shift=DOWN * 0.1), LaggedStart(*[FadeIn(x) for x in hook], lag_ratio=0.12), run_time=1.2)

        {visual_template(visual_kind, "intro")}

        formula = self.formula_block({str(short["formula"])!r}, {screen_math(str(short["formula"]))!r}, font_size=32, color="#F7C948")
        self.safe_place(formula, y=-5.25, max_width=7.6, max_height=1.0, top=-4.7, bottom=-5.95)
        intuition = self.text_block({wrap(str(short["intuition"]), 42, 3)!r}, font_size=23, color="#EAF2FF", max_width=7.35)
        self.safe_place(intuition, y=-6.55, max_width=7.35, max_height=1.15, top=-5.95, bottom=-7.25)
        self.play(Write(formula), run_time=0.9)
        self.play(FadeIn(intuition, shift=UP * 0.12), run_time=0.9)
        self.wait(7.0)
        self.fade_all_except([title], run_time=0.7)
        self.play(title.animate.scale(0.72).to_edge(UP, buff=0.35), run_time=0.45)

        section = self.section_label("Worked example", "#F7C948")
        self.play(FadeIn(section, shift=DOWN * 0.08), run_time=0.45)
        {visual_template(visual_kind, "example")}
        self.wait(8.0)
        self.fade_all_except([title], run_time=0.7)

        section = self.section_label("Active recall", "#F7C948")
        self.play(FadeIn(section, shift=DOWN * 0.08), run_time=0.45)
        {visual_template(visual_kind, "recall")}
        self.wait(8.0)
'''


def visual_template(kind: str, phase: str = "intro") -> str:
    if phase == "example":
        return "self.play_example_visual(visual_kind, visual_data, setup_lines, calc_lines, takeaway_lines)"
    if phase == "recall":
        return "self.play_recall_visual(visual_kind, visual_data, question_lines, answer_lines)"
    return "self.play_intro_visual(visual_kind, visual_data)"


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
        ("00:00:00,000", "00:00:06,000", screen_prose(short["hook"])),
        ("00:00:06,000", "00:00:20,000", screen_prose(short["intuition"])),
        ("00:00:20,000", "00:00:34,000", screen_prose(short["plain_formula"])),
        ("00:00:34,000", "00:01:04,000", f"Example: {screen_prose(ex['setup'])} {screen_prose(ex['calculation'])}"),
        ("00:01:04,000", "00:01:22,000", f"Takeaway: {screen_prose(ex['takeaway'])}"),
        ("00:01:22,000", "00:01:42,000", f"Try this: {screen_prose(qp['question'])}"),
        ("00:01:42,000", "00:02:00,000", f"Answer: {screen_prose(qp['answer'])}"),
    ]
    return "\n\n".join(f"{i}\n{a} --> {b}\n{textwrap.fill(str(t), width=42)}" for i, (a, b, t) in enumerate(cues, start=1)) + "\n"


def script_markdown(short: dict[str, object]) -> str:
    ex = short["worked_example"]
    qp = short["question_prompt"]
    return f"""# Short {short['index']:02d}: {short['concept']}

Target length: no fixed one-minute limit; keep going until the concept, worked example, and recall question are clear.

## Beats

| Time | Beat |
| --- | --- |
| 0:00-0:06 | {screen_prose(short['hook'])} |
| 0:06-0:20 | {screen_prose(short['intuition'])} |
| 0:20-0:34 | Formula: `{screen_prose(short['plain_formula'])}` |
| 0:34-1:04 | Example: {screen_prose(ex['setup'])} {screen_prose(ex['calculation'])} |
| 1:04-1:22 | Takeaway: {screen_prose(ex['takeaway'])} |
| 1:22-1:42 | Try this: {screen_prose(qp['question'])} |
| 1:42-2:00 | Answer: {screen_prose(qp['answer'])} |
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
    cmd_notes(argparse.Namespace(run=str(out), compile=not args.no_pdf, pdf_engine=args.pdf_engine if not args.no_pdf else "none"))
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
    p.add_argument("--pdf-engine", choices=["auto", "latex", "fallback", "none"], default="none")
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
    p.add_argument("--pdf-engine", choices=["auto", "latex", "fallback", "none"], default="auto")
    p.add_argument("--no-pdf", action="store_true")
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(func=cmd_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

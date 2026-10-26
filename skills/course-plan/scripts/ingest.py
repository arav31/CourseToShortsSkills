#!/usr/bin/env python3
"""Collect a course's material into plain-text files an agent can read and grep.

    python ingest.py <url-or-path> [<url-or-path> ...] --run runs/<course-slug>
                     [--max-pages 800] [--max-pdfs 400] [--title "Course title"]

Sources may be a course website (crawled within its own path prefix, e.g. an
MIT OpenCourseWare course root), single PDF/HTML URLs, local files, or local
folders (PDF, TXT, MD, TEX, HTML, SRT/VTT).

A literature review written in Markdown is read as one document:

    python ingest.py review.md --review [--fetch-cited] --run runs/review-<slug>

Its headings become the sections, its reference list the cited works, and each
section records which works it cites ([1], [@key], [^key], (Author, 2020),
Author et al. (2020)). --fetch-cited also collects the cited papers that have an
arXiv id or a link, so claims can be checked against the originals.

Writes, inside the run directory:
    sources/<id>-<slug>.txt  one file per page/PDF; <id> is stable across re-runs
    sources/INDEX.md         the course sequence (from the site's navigation) and
                             a table of everything collected
    source_pack.json         the same as JSON, plus warnings

Each file's header records its title, kind, URL and the page that linked to it
("context"), so PDFs named like MIT18_06SCF11_Ses2.12sum.pdf still say which
session they belong to. Navigation menus, footers and other lines repeated
across many pages are removed from page text. A re-run only replaces sources/
once the new crawl has finished.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "course-shorts-ingest/2.0 (+https://github.com/arav31/CourseToShortsSkills)"
MAX_BYTES = 40_000_000
MAX_TEXT_CHARS = 400_000
MAX_PDF_PAGES = 400
SKIP_EXT = {".zip", ".mp4", ".mp3", ".m4a", ".mov", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
            ".css", ".js", ".json", ".xml", ".rss", ".tgz", ".gz", ".tar", ".ppt", ".pptx", ".doc", ".docx",
            ".xls", ".xlsx", ".ipynb", ".py", ".m", ".csv", ".woff", ".woff2", ".ttf"}
TEXT_EXT = {".txt", ".md", ".tex", ".srt", ".vtt"}
HTML_EXT = {".html", ".htm"}
# (kind, regex) on "<file name> <title>", lower-cased; first match wins.
KIND_PATTERNS = [
    ("solution", r"_ex\d*s\.pdf|[_-]sol(n|ns|utions?)?\.pdf|\b(problem|exam|quiz|homework) solutions?\b|"
                 r"\b(problem (set|session)|recitation|quiz|exam|homework|pset)s? \d+[a-z]? solutions?\b|"
                 r"^solutions?\b| solutions? (to|for) (the )?(problems?|exercises?|exams?|quiz|homework|psets?|"
                 r"assignments?|recitation)\b|answer key"),
    ("review", r"\b(exam|final|course|midterm|quiz)( \d+)? review\b|\breview session\b"),
    ("exam", r"_ex\d*\.pdf|\b(exam|quiz|midterm)\b"),
    ("assignment", r"prob\.pdf|_ps\d+\.pdf|\b(problem sets?|problem sessions?|practice problems|psets?|homework|"
                   r"assignments?|exercises?)\b"),
    ("recitation", r"\brecitation\b"),
    ("syllabus", r"\bsyllabus\b|\bcourse info\b"),
    ("calendar", r"\bcalendar\b|\bschedule\b"),
    ("lecture-notes", r"sum\.pdf|[_-]lec(ture)?_?\d+[a-z]*\.pdf|"
                      r"\b(lecture notes|lecture summary|session summary|summary|slides|handouts?|notes)\b"),
    ("reading", r"\b(readings?|textbook|chapter)\b"),
]
KIND_ORDER = ["lit-review", "paper", "syllabus", "calendar", "lecture-notes", "transcript", "recitation", "reading", "assignment",
              "solution", "review", "exam", "page", "overview"]
LINK_HINTS = ("syllabus", "calendar", "unit", "session", "lecture", "notes", "reading", "resource", "problem",
              "assignment", "exam", "quiz", "transcript", "video", "recitation", "summary", "solution", "pages", ".pdf")
COMMON_WORDS = {"the", "of", "and", "to", "a", "is", "in", "that", "for", "we", "this", "it", "be", "with", "as",
                "on", "are", "by", "so", "if", "then", "not", "or", "an", "at", "from", "have", "what", "which",
                "can", "will", "its", "you", "one", "two", "there", "these", "has", "find", "let", "all", "when"}
GENERIC_ANCHORS = re.compile(r"^(download( file)?|pdf|here|link|file|view|open|resource|english|transcript|"
                             r"\W*|[\d.\s]+(kb|mb))$", re.I)
ANCHOR_JUNK = re.compile(r"(\.pdf)?\s*:?\s*(pdf|PDF)?\s*\d+(\.\d+)?\s*[kKmM]B\s*$|\s*\((pdf|PDF)[^)]*\)\s*$|"
                         r"\s*:\s*download( file)?\s*$|\.pdf\s*$", re.I)


# ---------------------------------------------------------------- HTML


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "button", "select"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "tr", "div", "section", "article",
             "br", "pre", "blockquote", "dt", "dd", "caption", "figcaption"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.nav_links: list[tuple[str, str]] = []
        self._anchor: list[str] | None = None
        self._href = ""
        self.skip_depth = 0
        self.nav_depth = 0
        self.title = ""
        self.h1 = ""
        self.headings: list[tuple[int, str]] = []
        self._heading: list[str] | None = None
        self._in_title = False
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        if tag == "nav":
            self.nav_depth += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._href, self._anchor = href, []
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._in_h1 = True
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag in {"h1", "h2", "h3", "h4"} and not self.skip_depth:
            self.parts.append("#" * int(tag[1]) + " ")
            self._heading = []
        if tag == "sup" and not self.skip_depth:
            self.parts.append("^")

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor is not None:
            item = (self._href, " ".join(" ".join(self._anchor).split()))
            self.links.append(item)
            if self.nav_depth:
                self.nav_links.append(item)
            self._anchor = None
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        if tag == "nav" and self.nav_depth:
            self.nav_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False
        if tag in {"h1", "h2", "h3", "h4"} and self._heading is not None:
            heading = " ".join(" ".join(self._heading).split())
            if heading:
                self.headings.append((int(tag[1]), heading))
            self._heading = None
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor.append(data)
        if self._in_title:
            self.title += data
            return
        if self._heading is not None and not self.skip_depth:
            self._heading.append(data)
        if self._in_h1 and not self.h1:
            self.h1 = " ".join(data.split())
        if not self.skip_depth:
            cleaned = re.sub(r"[ \t\r\f\v]+", " ", data)
            if cleaned.strip():
                self.parts.append(cleaned)

    def text(self) -> str:
        lines = [ln.strip() for ln in "".join(self.parts).splitlines()]
        out, blank = [], False
        for ln in lines:
            if not ln:
                if not blank:
                    out.append("")
                blank = True
            else:
                out.append(ln)
                blank = False
        return "\n".join(out).strip()


def clean_anchor(anchor: str) -> str:
    for _ in range(3):  # suffixes stack up: "x.pdf: pdf 159 kB", "x.pdf: Download File"
        anchor = ANCHOR_JUNK.sub("", anchor).strip()
    return "" if not anchor or GENERIC_ANCHORS.match(anchor) else anchor[:120]


def parse_html(raw: bytes, content_type: str, base: str) -> tuple[str, list[str], str, dict[str, str]]:
    """Return (text, links, page title, {link: anchor text})."""
    text, links, title, anchors, _ = parse_html_full(raw, content_type, base)
    return text, links, title, anchors


def parse_html_full(raw: bytes, content_type: str, base: str):
    match = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    html = raw.decode(match.group(1) if match else "utf-8", errors="replace")
    p = _Extractor()
    p.feed(html)

    def absolute(href: str) -> str:
        return urllib.parse.urljoin(base, href.strip()).split("#", 1)[0]

    links: list[str] = []
    anchors: dict[str, str] = {}
    for href, anchor in p.links:
        url = absolute(href)
        if not url:
            continue
        if url not in links:
            links.append(url)
        anchor = clean_anchor(anchor)
        if anchor and url not in anchors:
            anchors[url] = anchor
    nav: list[tuple[str, str]] = []
    for href, anchor in p.nav_links:
        url = absolute(href)
        if url and anchor and all(url != u for u, _ in nav):
            nav.append((url, anchor))
    head = " ".join(p.title.split()).split(" | ")[0].strip()
    title = head or " ".join(p.h1.split())
    return p.text(), links, title, anchors, nav


# ---------------------------------------------------------------- PDF / text


def pdf_text(raw: bytes) -> tuple[str, int]:
    import pymupdf

    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        pages = doc.page_count
        chunks = [doc[i].get_text("text") for i in range(min(pages, MAX_PDF_PAGES))]
    # control characters (ligature/maths glyphs) make grep treat the file as binary
    chunks = [re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", c) for c in chunks]
    return "\n\f\n".join(strip_running_lines(chunks)), pages


def strip_running_lines(pages: list[str]) -> list[str]:
    """Drop headers/footers repeated on most pages ("This content downloaded from ...", journal running heads)."""
    if len(pages) < 3:
        return pages
    counts: collections.Counter[str] = collections.Counter()
    for page in pages:
        counts.update({re.sub(r"\d+", "#", ln.strip()) for ln in page.splitlines() if ln.strip()})
    # 0.3: running heads often alternate between even and odd pages
    common = {ln for ln, c in counts.items() if c >= max(3, 0.3 * len(pages)) and len(ln) > 3}
    return ["\n".join(ln for ln in page.splitlines() if re.sub(r"\d+", "#", ln.strip()) not in common)
            for page in pages]


def pdf_outline(raw: bytes) -> tuple[str, list[str]]:
    """(metadata title, section titles from the PDF's own outline) - both may be empty."""
    import pymupdf

    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        title = (doc.metadata or {}).get("title", "") or ""
        toc = [t.strip() for lvl, t, _ in doc.get_toc() if lvl <= 2]
    junk = re.compile(r"^(image|page|figure|table)\s*\d+$|contents|front matter|cover|vol\.|issue|^untitled", re.I)
    toc = [t for t in toc if t and not junk.search(t)]
    if len(toc) < 3:  # scanned reprints carry outlines like "image 1, image 2"; read the headings instead
        toc = []
    title = title.strip()
    if len(title) < 6 or filename_like(title) or re.search(r"microsoft word|untitled|\.dvi", title, re.I):
        title = ""
    return title, toc


SECTION_RE = re.compile(r"^(?:(\d{1,2}(?:\.\d{1,2}){0,2})\.?|([IVX]{1,5})\.|([A-H])\.)\s+([A-Z][^\n]{2,80})$")
NAMED_SECTIONS = re.compile(r"^(abstract|introduction|background|related work|conclusions?|discussion|"
                            r"acknowledge?ments?|references|appendix(?: [a-z])?)$", re.I)


def detect_sections(text: str) -> list[str]:
    """Section headings of a paper, in order: '3.2 Multi-Head Attention', 'II. The Model', 'References'."""
    lines = [ln.strip() for ln in text.splitlines()]
    joined, i = [], 0
    while i < len(lines):  # "3.2.1" on one line and its heading on the next
        if re.fullmatch(r"\d+(?:\.\d+){0,2}\.?|[IVX]{1,5}\.", lines[i]) and i + 1 < len(lines):
            joined.append(f"{lines[i]} {lines[i + 1]}")
            i += 2
        else:
            joined.append(lines[i])
            i += 1
    found: list[str] = []
    for ln in joined:
        m = SECTION_RE.match(ln)
        heading = None
        if (m and len(m.group(4).split()) <= 10 and not re.search(r"[=<>%,;:()\"“”\d]", m.group(4))
                and not ln.endswith("-")):
            heading = ln if not m.group(4).isupper() else ln.replace(m.group(4), m.group(4).capitalize())
        elif NAMED_SECTIONS.match(ln):
            heading = ln.title() if ln.isupper() else ln
        if heading and heading not in found:
            found.append(heading)
    return found[:60]


def looks_like_paper(url: str, text: str) -> bool:
    if re.search(r"arxiv\.org|doi\.org|openreview\.net|/doi/|semanticscholar|ssrn\.com", url or "", re.I):
        return True
    head, tail = text[:6000].lower(), text[-60000:].lower()
    return ("abstract" in head) and bool(re.search(r"\n\s*(references|bibliography)\s*\n", tail))


def subtitle_text(raw: str) -> str:
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln or ln.isdigit() or "-->" in ln or ln.upper() == "WEBVTT":
            continue
        lines.append(re.sub(r"<[^>]+>", "", ln))
    return " ".join(lines)


def looks_garbled(text: str) -> bool:
    """True for text from broken font encodings: mostly symbols, or letters that never form common words."""
    sample = text[:20_000]
    if not sample.strip():
        return True
    plain = sum(1 for ch in sample if ch.isalnum() or ch.isspace() or ch in ".,;:()[]=+-*/'\"!?，。：；（）")
    if plain / len(sample) < 0.6:
        return True
    letters = [ch for ch in sample if ch.isalpha()]
    if letters:
        accented = sum(1 for ch in letters if 0x00C0 <= ord(ch) <= 0x024F)
        other_script = sum(1 for ch in letters if ord(ch) >= 0x0370)
        if accented / len(letters) > 0.3:
            return True   # Latin-1 letter salad from a broken font encoding
        if other_script / len(letters) > 0.5:
            return False  # mostly another script (e.g. Chinese): the English word test does not apply
    words = re.findall(r"[A-Za-z]+", sample)
    if len(words) < 80:
        return False
    return sum(1 for w in words if w.lower() in COMMON_WORDS) / len(words) < 0.04


NOT_A_TITLE = re.compile(r"permission|licen[cs]|arxiv:|preprint|copyright|all rights|downloaded from|jstor|"
                         r"proceedings of|journal of|vol\.|issn|doi", re.I)


def first_heading(text: str) -> str:
    for line in text.splitlines()[:60]:
        line = " ".join(line.split())
        if (8 <= len(line) <= 90 and len(line.split()) >= 2 and not line.upper().startswith("MITOCW")
                and "opencourseware" not in line.lower() and "http" not in line.lower()
                and not NOT_A_TITLE.search(line)
                and sum(ch.isalpha() for ch in line) / len(line) > 0.6):
            return line
    return ""


def arxiv_meta(url: str) -> dict | None:
    """For arxiv.org/abs|pdf links: the PDF URL plus title and authors from the abstract page."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#\s]+?)(?:\.pdf)?/?$", url)
    if not m:
        return None
    arxiv_id = m.group(1)
    meta = {"arxiv": arxiv_id, "pdf": f"https://arxiv.org/pdf/{arxiv_id}", "title": "", "authors": []}
    try:
        raw, _, _ = fetch(f"https://arxiv.org/abs/{arxiv_id}")
        html = raw.decode("utf-8", errors="replace")
        t = re.search(r'<meta name="citation_title" content="([^"]+)"', html)
        meta["title"] = t.group(1).strip() if t else ""
        meta["authors"] = re.findall(r'<meta name="citation_author" content="([^"]+)"', html)
    except Exception:
        pass
    return meta


# ---------------------------------------------------------------- helpers


def natural_key(text: str) -> list:
    """Sort key that orders embedded numbers numerically: "Lecture 2" < "Lecture 10"."""
    return [(0, int(tok), "") if tok.isdigit() else (1, 0, tok) for tok in re.split(r"(\d+)", text.lower()) if tok]


def slugify(text: str, fallback: str = "item") -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or fallback


def stable_id(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:6]


def filename_like(title: str) -> bool:
    t = title.strip()
    return bool(re.search(r"\.(pdf|txt|html?)\b", t, re.I)) or (" " not in t and bool(re.search(r"[_\d]", t)))


def classify(url: str, title: str, text: str = "") -> str:
    if text.lstrip().startswith("MITOCW") or re.match(r"\s*(PROFESSOR|INSTRUCTOR|SPEAKER \d)\s*:", text[:400]):
        return "transcript"
    name = Path(urllib.parse.urlparse(url).path.rstrip("/")).name.lower()
    hay = f"{name} {re.sub(r'[-_]+', ' ', name)} {title.lower()}"
    if "transcript" in hay or name.endswith((".srt", ".vtt")):
        return "transcript"
    for kind, pattern in KIND_PATTERNS:
        if re.search(pattern, hay):
            return kind
    return "page"


def course_prefix(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if "courses" in parts:
        parts = parts[: parts.index("courses") + 2]
    elif parts and "." in parts[-1]:
        parts = parts[:-1]
    path = "/" + "/".join(parts)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", ""))


def link_score(url: str) -> int:
    lower = url.lower()
    score = sum(3 for hint in LINK_HINTS if hint in lower)
    if lower.endswith(".pdf"):
        score += 4
        if re.search(r"(sum|summary|notes|lec|prob|sol|exam|quiz|ex\d)", Path(urllib.parse.urlparse(lower).path).stem):
            score += 4
    if any(bad in lower for bad in ("download", "instructor-insights", "/about", "/donate", "/search", "login")):
        score -= 10
    return score


def fetch(url: str) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(MAX_BYTES), resp.headers.get("Content-Type", ""), resp.geturl()


def title_from_url(url: str) -> str:
    name = Path(urllib.parse.urlparse(url).path.rstrip("/")).name or "page"
    name = re.sub(r"^[0-9a-f]{32}_", "", name)
    return re.sub(r"[-_]+", " ", Path(name).stem).strip().title() or "Page"


# ---------------------------------------------------------------- collectors


class Collector:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.warnings: list[str] = []
        self.sequence: list[dict] = []
        self.paper: dict | None = None  # set when the source is a single research paper
        self._hashes: set[str] = set()

    def add(self, kind: str, title: str, url: str | None, text: str, pages: int | None = None,
            is_html: bool = False, context: str = "", link: str | None = None, name: str = "") -> None:
        text = text.strip()
        if len(text) < 80:
            return
        digest = hashlib.sha1(re.sub(r"\s+", " ", text).encode()).hexdigest()
        if digest in self._hashes:
            return
        self._hashes.add(digest)
        if not is_html and looks_garbled(text):
            self.warnings.append(f"text looks garbled (font encoding; needs OCR), skipped: {title} <{url}>")
            return
        if len(text) > MAX_TEXT_CHARS:
            self.warnings.append(f"truncated very long source to {MAX_TEXT_CHARS} chars: {title}")
            text = text[:MAX_TEXT_CHARS]
        self.items.append({"kind": kind, "title": title.strip() or "Untitled", "url": url, "text": text,
                           "pages": pages, "html": is_html, "context": context, "link": link or url, "name": name})


def fetch_or_explain(url: str) -> tuple[bytes, str, str]:
    try:
        return fetch(url)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        archived = f"https://web.archive.org/web/2024id_/{url}"
        raise SystemExit(f"could not fetch {url}: {exc}\n"
                         f"If the site is down, try an archived copy: {archived}")


def ingest_single(url: str, col: Collector) -> str:
    """One document (a paper as a PDF or a single web page): no crawling, sections from its headings."""
    arxiv = arxiv_meta(url)
    raw, ctype, final = fetch_or_explain(arxiv["pdf"] if arxiv else url)
    if "pdf" in ctype.lower() or final.lower().endswith(".pdf") or arxiv:
        text, pages = pdf_text(raw)
        meta_title, toc = pdf_outline(raw)
        title = (arxiv or {}).get("title") or meta_title or first_heading(text) or title_from_url(final)
        sections = toc or detect_sections(text)
    else:
        p = _Extractor()
        match = re.search(r"charset=([\w-]+)", ctype or "", re.I)
        p.feed(raw.decode(match.group(1) if match else "utf-8", errors="replace"))
        text, pages = p.text(), None
        top = [h for lvl, h in p.headings if lvl == 1]
        title = (top[0] if top else "") or " ".join(p.title.split()) or title_from_url(final)
        levels = sorted({lvl for lvl, _ in p.headings if lvl > 1}) or [1]
        sections = [h for lvl, h in p.headings if lvl in levels[:2] and h != title]
    col.items.append({"kind": "paper", "title": title, "url": final, "text": text.strip(), "pages": pages,
                      "html": False, "context": "", "link": url, "name": ""})
    col.paper = {"authors": (arxiv or {}).get("authors", []), "arxiv": (arxiv or {}).get("arxiv")}
    col.sequence = [{"title": t, "url": None} for t in sections]
    return title


# ---------------------------------------------------------------- literature reviews

REF_HEADING = re.compile(r"^(references|bibliography|works cited|sources|cited works|literature cited)\b", re.I)
SKIP_SECTION = re.compile(r"^(references|bibliography|works cited|sources|cited works|literature cited|"
                          r"acknowledg|further reading|appendix)", re.I)
ARXIV_ID = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arXiv:\s*)(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\])>,;]+)")
URL_RE = re.compile(r"https?://[^\s\])>]+")
YEAR_RE = re.compile(r"\b(1[89]\d\d|20\d\d)[a-z]?\b")


def _md_front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip().strip("\"'")
    return meta, text[m.end():]


def _md_headings(body: str) -> list[tuple[int, str, int]]:
    """(level, text, offset) for ATX headings outside fenced code."""
    out, fenced, pos = [], False, 0
    for line in body.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        m = None if fenced else re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            out.append((len(m.group(1)), re.sub(r"[*_`]", "", m.group(2)).strip(), pos))
        pos += len(line)
    return out


def _surname(author: str) -> str:
    author = author.strip()
    if "," in author:  # "Kaplan, J."
        return author.split(",")[0].strip()
    parts = [w for w in re.split(r"\s+", author) if w and not re.fullmatch(r"[A-Z]\.?", w)]
    return parts[-1] if parts else author


def parse_references(block: str) -> list[dict]:
    """Reference entries: list items, [n]/[^key]/[@key]-labelled lines, or blank-line separated paragraphs."""
    lines = [ln.rstrip() for ln in block.splitlines()]
    entries: list[tuple[str | None, str]] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            entries.append((None, ""))
            continue
        m = (re.match(r"^\[\^([^\]]+)\]:\s*(.+)$", s) or re.match(r"^\[@?([\w:.-]+)\]:?\s+(.+)$", s)
             or re.match(r"^(\d{1,3})[.)]\s+(.+)$", s))
        if m:
            entries.append((m.group(1), m.group(2)))
        elif re.match(r"^[-*+]\s+", s):
            entries.append(("", re.sub(r"^[-*+]\s+", "", s)))
        elif entries and entries[-1][1]:
            entries[-1] = (entries[-1][0], entries[-1][1] + " " + s)  # continuation line
        else:
            entries.append(("", s))
    refs = []
    for label, text in entries:
        if not text:
            continue
        n = len(refs) + 1
        year = YEAR_RE.search(text)
        lead = re.split(r"\(\d{4}|\.\s|,\s*\d{4}", text, maxsplit=1)[0]
        first_author = re.split(r",| and | & |;", re.sub(r"^\W+", "", lead))[0]
        arxiv, doi, url = ARXIV_ID.search(text), DOI_RE.search(text), URL_RE.search(text)
        key = label if label else (f"{slugify(_surname(first_author), 'ref').replace('-', '')}{year.group(1) if year else ''}"
                                   or str(n))
        refs.append({"key": key, "n": n, "text": re.sub(r"\s+", " ", text).strip(),
                     "surname": _surname(first_author) if first_author else "", "year": year.group(1) if year else None,
                     "arxiv": arxiv.group(1) if arxiv else None, "doi": doi.group(1).rstrip(".") if doi else None,
                     "url": url.group(0).rstrip(".") if url else None})
    keys = collections.Counter(r["key"] for r in refs)
    for r in refs:  # two works by the same first author in one year: kaplan2020a, kaplan2020b
        if keys[r["key"]] > 1:
            same = [x for x in refs if x["key"] == r["key"]]
            for i, x in enumerate(same):
                x["key"] = f"{x['key']}{'abcdefgh'[i]}"
    return refs


def find_citations(text: str, refs: list[dict]) -> list[str]:
    """Keys of the works a passage cites, in order of first mention."""
    by_label = {r["key"]: r for r in refs}
    by_n = {str(r["n"]): r for r in refs}
    found: list[str] = []

    def hit(r: dict | None) -> None:
        if r and r["key"] not in found:
            found.append(r["key"])

    for m in re.finditer(r"\[\^([^\]]+)\]|\[@([\w:.-]+)\]|@([\w:-]+\d{4}\w*)", text):
        hit(by_label.get(next(g for g in m.groups() if g)))
    for m in re.finditer(r"\[(\d{1,3}(?:\s*[-–,]\s*\d{1,3})*)\](?!\()", text):
        for part in re.split(r"\s*,\s*", m.group(1)):
            a, b = (re.split(r"\s*[-–]\s*", part) + [part])[:2]  # "3" or "2-4"
            for i in range(int(a), int(b) + 1):
                hit(by_label.get(str(i)) or by_n.get(str(i)))
    for m in re.finditer(r"([A-Z][A-Za-z'’-]+)(?:\s+et al\.?|\s+(?:and|&)\s+[A-Z][A-Za-z'’-]+)?,?\s*\(?((?:1[89]|20)\d\d)[a-z]?\)?",
                         text):
        name, year = m.group(1), m.group(2)
        for r in refs:
            if r["year"] == year and r["surname"] and r["surname"].lower() == name.lower():
                hit(r)
    return found


def looks_like_review(path: Path) -> bool:
    """A Markdown file with a reference list or footnote citations reads as a literature review."""
    text = path.read_text(errors="replace")
    return any(REF_HEADING.match(h) for _, h, _ in _md_headings(text)) or bool(re.search(r"^\[\^[^\]]+\]:", text, re.M))


def ingest_review(path: Path, col: Collector, fetch_cited: bool = False, max_cited: int = 15) -> str:
    """A literature review in Markdown: sections from its headings, cited works from its reference list."""
    meta, body = _md_front_matter(path.read_text(errors="replace"))
    heads = _md_headings(body)
    title = meta.get("title") or next((h for lvl, h, _ in heads if lvl == 1), "") or path.stem.replace("-", " ").title()
    ref_at = next(((i, off) for i, (lvl, h, off) in enumerate(heads) if REF_HEADING.match(h)), None)
    refs: list[dict] = []
    if ref_at:
        i, off = ref_at
        end = next((o for lvl, h, o in heads[i + 1:] if lvl <= heads[i][0]), len(body))
        block = body[off:end].split("\n", 1)[1] if "\n" in body[off:end] else ""
        refs = parse_references(block)
    # footnote-style definitions anywhere also count as references
    known = {r["key"] for r in refs}
    for m in re.finditer(r"^\[\^([^\]]+)\]:\s*(.+)$", body, re.M):
        if m.group(1) not in known:
            refs += [dict(r, key=m.group(1), n=len(refs) + 1) for r in parse_references(m.group(2))]
    body_levels = sorted({lvl for lvl, h, _ in heads if lvl > 1 and not SKIP_SECTION.match(h)})
    level = body_levels[0] if body_levels else 1
    sections = []
    for j, (lvl, h, off) in enumerate(heads):
        if lvl != level or SKIP_SECTION.match(h) or h == title:
            continue
        end = next((o for l2, _, o in heads[j + 1:] if l2 <= level), len(body))
        sections.append({"title": h, "url": None, "cites": find_citations(body[off:end], refs)})
    if not sections:
        col.warnings.append("no section headings (## ...) found in the review; build the outline from its paragraphs")
    if not refs:
        col.warnings.append("no reference list found (a 'References' heading or [^key]: footnotes); "
                            "shorts must still credit the works they explain")
    cited_anywhere = {k for s in sections for k in s["cites"]}
    unused = [r["key"] for r in refs if r["key"] not in cited_anywhere]
    if refs and unused:
        col.warnings.append(f"references never cited in the text: {', '.join(unused[:12])}")
    col.items.append({"kind": "lit-review", "title": title, "url": str(path), "text": body.strip(), "pages": None,
                      "html": False, "context": "", "link": str(path), "name": ""})
    col.paper = {"type": "review", "authors": [a.strip() for a in re.split(r",| and ", meta.get("author", meta.get("authors", ""))) if a.strip()],
                 "references": refs}
    col.sequence = sections
    if fetch_cited:
        fetched = 0
        for r in refs:
            if fetched >= max_cited:
                col.warnings.append(f"stopped after {max_cited} cited works (--max-cited)")
                break
            target = (f"https://arxiv.org/abs/{r['arxiv']}" if r["arxiv"] else r["url"])
            if not target:
                continue
            fetched += 1
            try:
                arxiv = arxiv_meta(target)
                raw, ctype, final = fetch(arxiv["pdf"] if arxiv else target)
                if "pdf" in ctype.lower() or final.lower().endswith(".pdf") or arxiv:
                    text, pages = pdf_text(raw)
                    name = (arxiv or {}).get("title") or pdf_outline(raw)[0] or first_heading(text)
                else:
                    text, _, name, _ = parse_html(raw, ctype, final)
                    pages = None
                col.add("paper", name or r["text"][:80], final, text, pages, context=f"cited as [{r['key']}]")
                r["fetched"] = True
            except Exception as exc:  # paywalls, dead links: the review still stands on its own
                col.warnings.append(f"could not fetch cited work [{r['key']}] {target}: {exc}")
    return title


def crawl(root: str, col: Collector, max_pages: int, max_pdfs: int, delay: float) -> str:
    arxiv = arxiv_meta(root)
    if arxiv:
        root = arxiv["pdf"]
    prefix = course_prefix(root)
    netloc = urllib.parse.urlparse(root).netloc
    try:
        raw, ctype, final = fetch(root)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(f"could not fetch {root}: {exc}")
    if "pdf" in ctype.lower() or final.lower().endswith(".pdf") or arxiv:
        text, pages = pdf_text(raw)
        meta_title, toc = pdf_outline(raw)
        title = (arxiv or {}).get("title") or meta_title or first_heading(text) or title_from_url(final)
        paper = True  # a course is a site; a PDF given directly as the source is a single document
        col.add("paper" if paper else classify(final, title, text), title, final, text, pages)
        if paper:
            col.paper = {"authors": (arxiv or {}).get("authors", []), "arxiv": (arxiv or {}).get("arxiv")}
            col.sequence = [{"title": t, "url": None} for t in (toc or detect_sections(text))]
        return title
    text, links, course_title, anchors, nav = parse_html_full(raw, ctype, final)
    col.add("syllabus" if "syllabus" in text.lower()[:4000] else "overview", course_title or "Course home", final,
            text, is_html=True)

    def allowed(link: str) -> bool:
        parsed = urllib.parse.urlparse(link)
        ext = Path(parsed.path).suffix.lower()
        return (parsed.scheme in {"http", "https"} and parsed.netloc == netloc and link.startswith(prefix)
                and ext not in SKIP_EXT)

    def take_sequence(entries: list[tuple[str, str]]) -> None:
        inside = [(u, a) for u, a in entries if allowed(u) and u.rstrip("/") != prefix]
        if len(inside) >= 5 and len(inside) > len(col.sequence):
            col.sequence = [{"title": a, "url": u} for u, a in inside]

    take_sequence(nav)
    names: dict[str, str] = dict(anchors)  # link -> best human name seen so far
    # link -> [(title of a page linking to it, how many course links that page has)]; the page with the
    # fewest links is the most specific context (a session page beats a site-wide resource index)
    referrers: dict[str, list[tuple[str, int]]] = {}
    landing_links = [ln for ln in links if allowed(ln)]
    for ln in landing_links:
        referrers.setdefault(ln, []).append((course_title, len(landing_links)))

    def best_context(link: str) -> str:
        refs = referrers.get(link) or []
        return min(refs, key=lambda r: r[1])[0] if refs else ""

    seen = {final, root}
    queue = sorted({ln for ln in links if allowed(ln)}, key=link_score, reverse=True)
    pages = pdfs = last_report = 0
    while queue and (pages < max_pages or pdfs < max_pdfs):
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        is_pdf_link = url.lower().endswith(".pdf")
        if (is_pdf_link and pdfs >= max_pdfs) or (not is_pdf_link and pages >= max_pages):
            continue
        time.sleep(delay)
        fetched = pages + pdfs
        if fetched and fetched % 25 == 0 and fetched != last_report:
            last_report = fetched
            print(f"  crawled {pages} pages, {pdfs} PDFs; {len(queue)} links queued", file=sys.stderr, flush=True)
        try:
            raw, ctype, final = fetch(url)
        except Exception as exc:  # keep crawling past broken links
            col.warnings.append(f"fetch failed: {url} ({exc.__class__.__name__})")
            continue
        seen.add(final)
        ctx = best_context(url)
        if "pdf" in ctype.lower() or final.lower().endswith(".pdf"):
            if pdfs >= max_pdfs:
                continue
            try:
                text, n = pdf_text(raw)
            except Exception as exc:
                col.warnings.append(f"unreadable PDF: {final} ({exc})")
                continue
            if len(text.strip()) < 200:
                col.warnings.append(f"PDF has no extractable text (scanned? needs OCR): {final}")
                continue
            pdfs += 1
            name = names.get(url) or names.get(final) or ""
            if not name or filename_like(name):
                name = first_heading(text) or name or title_from_url(final)
            col.add(classify(final, name, text), name, final, text, n, context=ctx, link=url, name=name)
        elif "html" in ctype.lower():
            text, nested, title, anchors, nav = parse_html_full(raw, ctype, final)
            pages += 1
            take_sequence(nav)
            title = title or names.get(url) or title_from_url(final)
            effective = ctx if filename_like(title) and ctx else title  # resource landing pages inherit
            col.add(classify(final, title, text), title, final, text, is_html=True, context=ctx, link=url)
            for ln, anchor in anchors.items():
                names.setdefault(ln, anchor)
            inside = [ln for ln in nested if allowed(ln)]
            for ln in inside:
                referrers.setdefault(ln, []).append((effective, len(inside)))
            fresh = [ln for ln in nested if allowed(ln) and ln not in seen and ln not in queue]
            queue.extend(fresh)
            queue.sort(key=link_score, reverse=True)
        elif "text" in ctype.lower():
            raw_text = raw.decode("utf-8", errors="replace")
            ext = Path(urllib.parse.urlparse(final).path).suffix.lower()
            body = subtitle_text(raw_text) if ext in {".srt", ".vtt"} else raw_text
            name = title_from_url(final)
            col.add(classify(final, name, body), name, final, body, context=ctx, link=url, name=name)
    finalize_titles(col, best_context)
    if pages >= max_pages or pdfs >= max_pdfs:
        col.warnings.append(f"stopped at limits (pages={pages}, pdfs={pdfs}); raise --max-pages/--max-pdfs "
                            "if important material is missing")
    return course_title


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def finalize_titles(col: Collector, best_context) -> None:
    """Now that every link is known, give non-HTML files the most specific context and a readable title."""
    for it in col.items:
        if it["html"] or not it.get("name") or not it.get("link"):
            continue
        ctx = best_context(it["link"]) or it["context"]
        name = it["name"]
        if it["kind"] == "transcript":
            title = f"{ctx}: transcript" if ctx else f"{name}: transcript"
        elif ctx and _squash(name) not in _squash(ctx):
            title = f"{ctx}: {name}"
        else:
            title = name or ctx
        it["context"], it["title"] = ctx, title
        if it["kind"] != "transcript":
            it["kind"] = classify(it["url"] or "", title, it["text"])


def ingest_local(path: Path, col: Collector) -> None:
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for f in files:
        ext = f.suffix.lower()
        try:
            if ext == ".pdf":
                text, n = pdf_text(f.read_bytes())
                if len(text.strip()) < 200:
                    col.warnings.append(f"PDF has no extractable text (scanned? needs OCR): {f}")
                    continue
                raw_pdf = f.read_bytes()
                meta_title, toc = pdf_outline(raw_pdf)
                title = meta_title or first_heading(text) or f.stem.replace("_", " ")
                if path.is_file() and looks_like_paper(str(f), text):
                    col.add("paper", title, str(f), text, n)
                    col.paper = {"authors": [], "arxiv": None}
                    col.sequence = [{"title": t, "url": None} for t in (toc or detect_sections(text))]
                else:
                    col.add(classify(str(f), title, text), title, str(f), text, n)
            elif ext in HTML_EXT:
                text, _, title, _ = parse_html(f.read_bytes(), "", f.as_uri())
                col.add(classify(str(f), title, text), title or f.stem, str(f), text, is_html=True)
            elif ext in TEXT_EXT:
                raw = f.read_text(errors="replace")
                body = subtitle_text(raw) if ext in {".srt", ".vtt"} else raw
                title = f.stem.replace("_", " ")
                col.add(classify(str(f), title, body), title, str(f), body)
        except Exception as exc:
            col.warnings.append(f"could not read {f}: {exc}")


def strip_boilerplate(items: list[dict]) -> int:
    """Drop lines that repeat across many HTML pages (menus, footers, banners)."""
    html = [it for it in items if it["html"]]
    if len(html) < 4:
        return 0
    counts: collections.Counter[str] = collections.Counter()
    for it in html:
        counts.update({ln.strip() for ln in it["text"].splitlines() if ln.strip()})
    threshold = max(3, int(0.4 * len(html)))
    common = {ln for ln, c in counts.items() if c >= threshold and len(ln) < 300}
    removed = 0
    for it in html:
        kept = [ln for ln in it["text"].splitlines() if ln.strip() not in common]
        removed += len(it["text"].splitlines()) - len(kept)
        it["text"] = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return removed


# ---------------------------------------------------------------- output


def write_sources(run: Path, col: Collector, title: str, first_url: str | None, sources: list[str],
                  removed: int) -> dict:
    staging = run / "sources.partial"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    materials = []
    for it in col.items:
        sid = stable_id(it["url"] or it["title"])
        name = f"{sid}-{slugify(it['title'])}.txt"
        header = f"# title: {it['title']}\n# kind: {it['kind']}\n# source: {it['url']}\n"
        if it["context"]:
            header += f"# context: {it['context']}\n"
        if it["pages"]:
            header += f"# pdf_pages: {it['pages']}\n"
        (staging / name).write_text(header + "\n" + it["text"] + "\n", encoding="utf-8")
        materials.append({"id": sid, "kind": it["kind"], "title": it["title"], "context": it["context"] or None,
                          "url": it["url"], "file": f"sources/{name}", "chars": len(it["text"]),
                          "pdf_pages": it["pages"]})
    by_kind = collections.Counter(m["kind"] for m in materials)
    total = sum(m["chars"] for m in materials)
    if not materials:
        col.warnings.append("nothing usable was collected")
    if col.paper is not None and col.paper.get("type") == "review":
        pass  # ingest_review already warned about missing sections/references
    elif col.paper is not None:
        if not col.sequence:
            col.warnings.append("single paper, but no section headings were detected; build the outline from its text")
    elif not col.sequence and by_kind.get("syllabus", 0) + by_kind.get("calendar", 0) == 0:
        col.warnings.append("no course navigation, syllabus or calendar found; build the outline from lecture titles")
    if total < 20_000 and col.paper is None:
        col.warnings.append(f"only {total} characters collected; notes need more source material "
                            "(add PDFs/folders or raise limits)")
    pack = {
        "course": {"title": title or "Course", "url": first_url, "sources": sources,
                   "type": "paper" if col.paper is not None else "course",
                   **{k: v for k, v in (col.paper or {}).items() if k != "references"},
                   "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
        "stats": {"materials": len(materials), "total_chars": total, "by_kind": dict(by_kind),
                  "boilerplate_lines_removed": removed},
        "sequence": col.sequence,
        "references": (col.paper or {}).get("references", []),
        "materials": materials,
        "warnings": col.warnings,
    }
    order = {k: i for i, k in enumerate(KIND_ORDER)}
    rows = sorted(materials, key=lambda m: (order.get(m["kind"], 99), natural_key(m["context"] or ""),
                                           natural_key(m["title"])))
    index = [f"# Sources for {pack['course']['title']}", "",
             f"{len(materials)} files, {total:,} characters."]
    if col.sequence:
        is_review = (col.paper or {}).get("type") == "review"
        heading = ("## Review sections (in order, with the works each cites)" if is_review
                   else "## Paper sections (detected, in order)" if col.paper is not None
                   else "## Course sequence (from the site navigation, in order)")
        index += ["", heading, ""]
        index += [f"{i}. {s['title']}" + (f"  [{', '.join(s['cites'])}]" if s.get("cites") else "")
                  for i, s in enumerate(col.sequence, 1)]
    if pack["references"]:
        fetched_files = {m["context"]: m["file"] for m in materials if m["context"]}
        index += ["", "## Cited works", "", "| key | year | reference | link | fetched |", "|---|---|---|---|---|"]
        for r in pack["references"]:
            link = (f"arXiv:{r['arxiv']}" if r["arxiv"] else f"doi:{r['doi']}" if r["doi"] else r["url"] or "")
            fetched = fetched_files.get("cited as [" + r["key"] + "]", "")
            index.append(f"| {r['key']} | {r['year'] or ''} | {r['text']} | {link} | {fetched} |")
    index += ["", "## Files", "", "| id | kind | title | context | chars | file |", "|---|---|---|---|---|---|"]
    index += [f"| {m['id']} | {m['kind']} | {m['title'][:70]} | {(m['context'] or '')[:50]} | {m['chars']:,} | {m['file']} |"
              for m in rows]
    if col.warnings:
        index += ["", "## Warnings", ""] + [f"- {w}" for w in col.warnings]
    (staging / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    final = run / "sources"
    if final.exists():
        shutil.rmtree(final)
    staging.rename(final)
    (run / "source_pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return pack


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--max-pages", type=int, default=800)
    ap.add_argument("--max-pdfs", type=int, default=400)
    ap.add_argument("--delay", type=float, default=0.1, help="seconds between requests")
    ap.add_argument("--title", default=None)
    ap.add_argument("--single", action="store_true",
                    help="each URL is one document (a paper or article): fetch it, do not crawl its site")
    ap.add_argument("--review", action="store_true",
                    help="the source is a literature review in Markdown: sections plus cited works")
    ap.add_argument("--fetch-cited", action="store_true",
                    help="with --review: also collect the cited works that have an arXiv id or a link")
    ap.add_argument("--max-cited", type=int, default=15)
    args = ap.parse_args(argv)

    run: Path = args.run
    run.mkdir(parents=True, exist_ok=True)
    col = Collector()
    title, first_url = args.title, None
    for source in args.sources:
        if re.match(r"https?://", source):
            first_url = first_url or source
            found = (ingest_single(source, col) if args.single
                     else crawl(source, col, args.max_pages, args.max_pdfs, args.delay))
            title = title or found
        else:
            path = Path(source).expanduser()
            if not path.exists():
                print(f"error: {path} does not exist", file=sys.stderr)
                return 1
            if args.review or (path.is_file() and path.suffix.lower() in {".md", ".markdown"}
                               and len(args.sources) == 1 and looks_like_review(path)):
                title = title or ingest_review(path, col, args.fetch_cited, args.max_cited)
            else:
                ingest_local(path, col)
                title = title or path.stem.replace("-", " ").title()
    removed = strip_boilerplate(col.items)
    col.items = [it for it in col.items if len(it["text"]) >= (300 if it["html"] else 80)]
    pack = write_sources(run, col, title, first_url, args.sources, removed)

    order = {k: i for i, k in enumerate(KIND_ORDER)}
    print(f"{pack['course']['title']}: {pack['stats']['materials']} sources, {pack['stats']['total_chars']:,} chars, "
          f"{len(pack['sequence'])} entries in the "
          f"{ {'paper': 'paper outline', 'review': 'review outline'}.get(pack['course']['type'], 'course sequence')}"
          + (f", {len(pack['references'])} cited works" if pack["references"] else ""))
    for kind, count in sorted(pack["stats"]["by_kind"].items(), key=lambda kv: order.get(kv[0], 99)):
        print(f"  {kind:<14} {count}")
    for w in col.warnings[:15]:
        print(f"  warning: {w}")
    if len(col.warnings) > 15:
        print(f"  ... {len(col.warnings) - 15} more warnings in source_pack.json")
    print(f"index: {run / 'sources' / 'INDEX.md'}")
    return 0 if pack["materials"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

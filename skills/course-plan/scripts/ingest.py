#!/usr/bin/env python3
"""Collect a course's material into plain-text files an agent can read and grep.

    python ingest.py <url-or-path> [<url-or-path> ...] --run runs/<course-slug>
                     [--max-pages 150] [--max-pdfs 120] [--title "Course title"]

Sources may be a course website (crawled within its own path prefix, e.g. an
MIT OpenCourseWare course root), single PDF/HTML URLs, local files, or local
folders (PDF, TXT, MD, TEX, HTML, SRT/VTT).

Writes, inside the run directory:
    sources/NNN-<slug>.txt   one file per page/PDF, with a small header
    sources/INDEX.md         a readable table of everything collected
    source_pack.json         the same index as JSON, plus warnings

Navigation menus, footers and other lines repeated across many pages are
removed so they cannot be mistaken for course content.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import re
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
KIND_RULES = [
    ("syllabus", ("syllabus", "course-info", "course_info", "overview", "course-description")),
    ("calendar", ("calendar", "schedule")),
    ("exam", ("exam", "quiz", "midterm", "final-review", "practice-final")),
    ("solution", ("solution", "_sol", "-sol", "soln", "answers")),
    ("assignment", ("assignment", "problem-set", "problem_set", "pset", "homework", "hw", "exercise", "recitation")),
    ("transcript", ("transcript", ".srt", ".vtt")),
    ("lecture-notes", ("lecture-notes", "lecture_notes", "lec", "notes", "slides", "handout", "summary", "sum.pdf")),
    ("reading", ("reading", "textbook", "chapter", "book")),
    ("video", ("video", "lecture-videos", "resources/lecture")),
]
LINK_HINTS = ("syllabus", "calendar", "unit", "session", "lecture", "notes", "reading", "resource", "problem",
              "assignment", "exam", "quiz", "transcript", "video", "recitation", "summary", "solution", "pages", ".pdf")


# ---------------------------------------------------------------- HTML


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "button", "select"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "tr", "div", "section", "article",
             "br", "pre", "blockquote", "dt", "dd", "caption", "figcaption"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._anchor: list[str] | None = None
        self._href = ""
        self.skip_depth = 0
        self.title = ""
        self.h1 = ""
        self._in_title = False
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
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

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor is not None:
            self.links.append((self._href, " ".join("".join(self._anchor).split())))
            self._anchor = None
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor.append(data)
        if self._in_title:
            self.title += data
            return
        if self._in_h1 and not self.h1:
            self.h1 = " ".join(data.split())
        if not self.skip_depth:
            cleaned = re.sub(r"[ \t\r\f\v]+", " ", data)
            if cleaned.strip():
                self.parts.append(cleaned)

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [ln.strip() for ln in raw.splitlines()]
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


GENERIC_ANCHORS = re.compile(r"^(download|pdf|here|link|file|view|open|resource|english|transcript|\W*|[\d.\s]+(kb|mb))$", re.I)
ANCHOR_JUNK = re.compile(r"(\.pdf)?\s*:?\s*(pdf|PDF)?\s*\d+(\.\d+)?\s*[kKmM]B\s*$|\s*\((pdf|PDF)[^)]*\)\s*$")


def parse_html(raw: bytes, content_type: str, base: str) -> tuple[str, list[str], str, dict[str, str]]:
    """Return (text, links, page title, {link: anchor text})."""
    match = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    html = raw.decode(match.group(1) if match else "utf-8", errors="replace")
    p = _Extractor()
    p.feed(html)
    links: list[str] = []
    anchors: dict[str, str] = {}
    for href, anchor in p.links:
        url = urllib.parse.urljoin(base, href.strip()).split("#", 1)[0]
        if not url:
            continue
        if url not in links:
            links.append(url)
        anchor = ANCHOR_JUNK.sub("", anchor).strip()
        if anchor and not GENERIC_ANCHORS.match(anchor) and url not in anchors:
            anchors[url] = anchor[:120]
    head = " ".join(p.title.split()).split(" | ")[0].strip()
    title = head or " ".join(p.h1.split())
    return p.text(), links, title, anchors


# ---------------------------------------------------------------- PDF / text


def pdf_text(raw: bytes) -> tuple[str, int]:
    import pymupdf

    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        pages = doc.page_count
        chunks = [doc[i].get_text("text") for i in range(min(pages, MAX_PDF_PAGES))]
    return "\n\f\n".join(chunks), pages


def subtitle_text(raw: str) -> str:
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln or ln.isdigit() or "-->" in ln or ln.upper() == "WEBVTT":
            continue
        lines.append(re.sub(r"<[^>]+>", "", ln))
    return " ".join(lines)


# ---------------------------------------------------------------- helpers


def slugify(text: str, fallback: str = "item") -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or fallback


def classify(url: str, title: str, text: str = "") -> str:
    if text.lstrip().startswith("MITOCW") or re.match(r"\s*(PROFESSOR|INSTRUCTOR)\s*:", text[:400]):
        return "transcript"
    hay = f"{url} {title}".lower()
    for pattern, kind in ((r"ex\d+s\.pdf|_sol\.pdf|sol\.pdf", "solution"), (r"_ex\d+\.pdf|exam", "exam"),
                          (r"prob\.pdf|_ps\d+\.pdf", "assignment"), (r"sum\.pdf", "lecture-notes")):
        if re.search(pattern, hay):
            return kind
    for kind, needles in KIND_RULES:
        if any(n in hay for n in needles):
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
    def __init__(self, run: Path):
        self.run = run
        self.items: list[dict] = []
        self.warnings: list[str] = []
        self._hashes: set[str] = set()

    def add(self, kind: str, title: str, url: str | None, text: str, pages: int | None = None,
            is_html: bool = False) -> None:
        text = text.strip()
        if len(text) < 80:
            return
        digest = hashlib.sha1(re.sub(r"\s+", " ", text).encode()).hexdigest()
        if digest in self._hashes:
            return
        self._hashes.add(digest)
        if len(text) > MAX_TEXT_CHARS:
            self.warnings.append(f"truncated very long source to {MAX_TEXT_CHARS} chars: {title}")
            text = text[:MAX_TEXT_CHARS]
        self.items.append({"kind": kind, "title": title.strip() or "Untitled", "url": url, "text": text,
                           "pages": pages, "html": is_html})


def crawl(root: str, col: Collector, max_pages: int, max_pdfs: int, delay: float) -> str:
    prefix = course_prefix(root)
    netloc = urllib.parse.urlparse(root).netloc
    try:
        raw, ctype, final = fetch(root)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(f"could not fetch {root}: {exc}")
    if "pdf" in ctype.lower() or final.lower().endswith(".pdf"):
        text, pages = pdf_text(raw)
        col.add(classify(final, ""), title_from_url(final), final, text, pages)
        return title_from_url(final)
    text, links, course_title, anchors = parse_html(raw, ctype, final)
    col.add("syllabus" if "syllabus" in text.lower()[:4000] else "overview", course_title or "Course home", final,
            text, is_html=True)
    names: dict[str, str] = dict(anchors)  # link -> best human title seen so far
    context: dict[str, str] = {ln: course_title for ln in links}  # link -> title of the page linking to it

    def allowed(link: str) -> bool:
        parsed = urllib.parse.urlparse(link)
        ext = Path(parsed.path).suffix.lower()
        return (parsed.scheme in {"http", "https"} and parsed.netloc == netloc and link.startswith(prefix)
                and ext not in SKIP_EXT)

    seen = {final, root}
    queue = sorted({ln for ln in links if allowed(ln)}, key=link_score, reverse=True)
    pages = pdfs = 0
    while queue and (pages < max_pages or pdfs < max_pdfs):
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        is_pdf_link = url.lower().endswith(".pdf")
        if (is_pdf_link and pdfs >= max_pdfs) or (not is_pdf_link and pages >= max_pages):
            continue
        time.sleep(delay)
        try:
            raw, ctype, final = fetch(url)
        except Exception as exc:  # keep crawling past broken links
            col.warnings.append(f"fetch failed: {url} ({exc.__class__.__name__})")
            continue
        seen.add(final)
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
            ctx = context.get(url, "")
            title = f"{ctx}: {name}" if ctx and name and name.lower() not in ctx.lower() else (name or ctx or title_from_url(final))
            col.add(classify(final, title, text), title, final, text, n)
        elif "html" in ctype.lower():
            text, nested, title, anchors = parse_html(raw, ctype, final)
            pages += 1
            title = title or names.get(url) or title_from_url(final)
            col.add(classify(final, title, text), title, final, text, is_html=True)
            for ln, anchor in anchors.items():
                names.setdefault(ln, anchor)
            for ln in nested:
                context.setdefault(ln, title)
            fresh = [ln for ln in nested if allowed(ln) and ln not in seen and ln not in queue]
            queue.extend(fresh)
            queue.sort(key=link_score, reverse=True)
        elif "text" in ctype.lower():
            raw_text = raw.decode("utf-8", errors="replace")
            ext = Path(urllib.parse.urlparse(final).path).suffix.lower()
            col.add(classify(final, ""), title_from_url(final), final,
                    subtitle_text(raw_text) if ext in {".srt", ".vtt"} else raw_text)
    if pages >= max_pages or pdfs >= max_pdfs:
        col.warnings.append(f"stopped at limits (pages={pages}, pdfs={pdfs}); raise --max-pages/--max-pdfs "
                            "if important material is missing")
    return course_title


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
                col.add(classify(str(f), f.stem), f.stem.replace("_", " "), str(f), text, n)
            elif ext in HTML_EXT:
                text, _, title, _ = parse_html(f.read_bytes(), "", f.as_uri())
                col.add(classify(str(f), title), title or f.stem, str(f), text, is_html=True)
            elif ext in TEXT_EXT:
                raw = f.read_text(errors="replace")
                col.add(classify(str(f), f.stem), f.stem.replace("_", " "), str(f),
                        subtitle_text(raw) if ext in {".srt", ".vtt"} else raw)
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


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--max-pages", type=int, default=250)
    ap.add_argument("--max-pdfs", type=int, default=200)
    ap.add_argument("--delay", type=float, default=0.15, help="seconds between requests")
    ap.add_argument("--title", default=None)
    args = ap.parse_args(argv)

    run: Path = args.run
    src_dir = run / "sources"
    src_dir.mkdir(parents=True, exist_ok=True)
    for old in src_dir.glob("*.txt"):
        old.unlink()
    col = Collector(run)
    title, first_url = args.title, None
    for source in args.sources:
        if re.match(r"https?://", source):
            first_url = first_url or source
            found = crawl(source, col, args.max_pages, args.max_pdfs, args.delay)
            title = title or found
        else:
            path = Path(source).expanduser()
            if not path.exists():
                print(f"error: {path} does not exist", file=sys.stderr)
                return 1
            ingest_local(path, col)
            title = title or path.stem.replace("-", " ").title()
    removed = strip_boilerplate(col.items)
    col.items = [it for it in col.items if len(it["text"]) >= (300 if it["html"] else 80)]

    order = {k: i for i, (k, _) in enumerate(KIND_RULES)}
    materials = []
    for n, it in enumerate(col.items, 1):
        name = f"{n:03d}-{slugify(it['title'])}.txt"
        header = f"# title: {it['title']}\n# kind: {it['kind']}\n# source: {it['url']}\n"
        if it["pages"]:
            header += f"# pdf_pages: {it['pages']}\n"
        (src_dir / name).write_text(header + "\n" + it["text"] + "\n", encoding="utf-8")
        materials.append({"id": f"{n:03d}", "kind": it["kind"], "title": it["title"], "url": it["url"],
                          "file": f"sources/{name}", "chars": len(it["text"]), "pdf_pages": it["pages"]})

    by_kind = collections.Counter(m["kind"] for m in materials)
    total = sum(m["chars"] for m in materials)
    if not materials:
        col.warnings.append("nothing usable was collected")
    if by_kind.get("syllabus", 0) + by_kind.get("calendar", 0) == 0:
        col.warnings.append("no syllabus or calendar found; build the outline from lecture titles and notes")
    if total < 20_000:
        col.warnings.append(f"only {total} characters collected; notes need more source material "
                            "(add PDFs/folders or raise limits)")
    pack = {
        "course": {"title": title or "Course", "url": first_url, "sources": args.sources,
                   "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
        "stats": {"materials": len(materials), "total_chars": total, "by_kind": dict(by_kind),
                  "boilerplate_lines_removed": removed},
        "materials": materials,
        "warnings": col.warnings,
    }
    (run / "source_pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
    rows = sorted(materials, key=lambda m: (order.get(m["kind"], 99), m["id"]))
    index = [f"# Sources for {pack['course']['title']}", "",
             f"{len(materials)} files, {total:,} characters. Read the syllabus/calendar first.", "",
             "| id | kind | title | chars | file |", "|---|---|---|---|---|"]
    index += [f"| {m['id']} | {m['kind']} | {m['title'][:70]} | {m['chars']:,} | {m['file']} |" for m in rows]
    if col.warnings:
        index += ["", "## Warnings", ""] + [f"- {w}" for w in col.warnings]
    (src_dir / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")

    print(f"{pack['course']['title']}: {len(materials)} sources, {total:,} chars")
    for kind, count in sorted(by_kind.items(), key=lambda kv: order.get(kv[0], 99)):
        print(f"  {kind:<14} {count}")
    for w in col.warnings[:15]:
        print(f"  warning: {w}")
    if len(col.warnings) > 15:
        print(f"  ... {len(col.warnings) - 15} more warnings in source_pack.json")
    print(f"index: {src_dir / 'INDEX.md'}")
    return 0 if materials else 1


if __name__ == "__main__":
    raise SystemExit(main())

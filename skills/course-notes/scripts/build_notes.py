#!/usr/bin/env python3
"""Compile, lint and preview the course notes.

    python build_notes.py runs/<course> [--pages 3 7] [--no-preview]

Expects runs/<course>/notes/notes.tex (plus notes/units/*.tex it \\input s).
  1. Compiles with tectonic (or latexmk / pdflatex). A failed compile prints
     the TeX errors with file and line, and the script exits 1.
  2. Lints the sources for problems that compile fine but read badly:
     leftover <<markers>>, placeholder text, code-style maths, escaped
     maths in headings, repeated boilerplate sentences, missing figures,
     definitions/theorems without examples, exercises without solutions,
     and source-list sections.
  3. Checks the PDF: page count, near-empty pages, overfull boxes.
  4. Renders page contact sheets to notes/preview/ for visual review, and
     full-size pages for any --pages you name.
Writes notes/notes_report.json. Exit 1 = errors to fix.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXTRA_PATHS = ["/Library/TeX/texbin", "/opt/homebrew/bin", "/usr/local/bin"]
PLACEHOLDER_RE = re.compile(
    r"<<[^>]{2,}>>|\b(TODO|TBD|FIXME|XXX)\b|lorem ipsum|Generated figure|insert (an? )?(figure|example|proof) here|"
    r"\[citation needed\]", re.I)
CODE_MATH_RE = re.compile(r"(?<!\\)\[\[\s*-?\d|(?<![\\\w])sqrt\(|\*\*\s*\d")
ESCAPED_IN_HEADING_RE = re.compile(r"\\(?:sub)*section\*?\{[^}]*(\\textbackslash|\\_|\\\^)")
SOURCE_SECTION_RE = re.compile(r"\\(?:sub)*section\*?\{\s*(sources|references|bibliography|source list)\s*\}", re.I)
ENV_RE = re.compile(r"\\begin\{(definition|theorem|proposition|lemma|corollary|example|exercise|solution|proof|trap|remark|figure|tikzpicture|axis)\}")


def find_engine() -> tuple[str, str] | None:
    path = os.pathsep.join([os.environ.get("PATH", "")] + EXTRA_PATHS)
    for name in ("tectonic", "latexmk", "pdflatex"):
        found = shutil.which(name, path=path)
        if found:
            return name, found
    return None


def compile_tex(notes_dir: Path, main: str = "notes.tex", outdir: Path | None = None) -> tuple[str, str]:
    """Compile ``main`` (relative to notes_dir); outputs go to ``outdir`` (default notes_dir)."""
    engine = find_engine()
    if engine is None:
        raise SystemExit("No TeX engine found. Install tectonic (brew install tectonic) or a TeX distribution.")
    name, exe = engine
    out = (outdir or notes_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if name == "tectonic":
        runs = [[exe, "-X", "compile", "--keep-logs", "--outdir", str(out), main]]
    elif name == "latexmk":
        runs = [[exe, "-pdf", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={out}", main]]
    else:
        base = [exe, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={out}", main]
        runs = [base, base]
    log_file = out / (Path(main).stem + ".log")
    log = ""
    for cmd in runs:
        proc = subprocess.run(cmd, cwd=notes_dir, capture_output=True, text=True, timeout=900)
        log += proc.stdout + proc.stderr
        if proc.returncode != 0:
            if log_file.exists():
                log += log_file.read_text(errors="replace")
            raise CompileError(name, log)
    # analyse the TeX log only (the console repeats the same warnings)
    return name, log_file.read_text(errors="replace") if log_file.exists() else log


class CompileError(RuntimeError):
    def __init__(self, engine: str, log: str):
        super().__init__(engine)
        self.engine, self.log = engine, log

    def summary(self) -> str:
        lines = self.log.splitlines()
        picked = []
        for i, ln in enumerate(lines):
            if ln.startswith("!") or re.search(r"error:|Error:|\.tex:\d+:", ln):
                picked.extend(lines[i:i + 3])
        return "\n".join(picked[:40]) or "\n".join(lines[-40:])


def tex_files(notes_dir: Path, main: str = "notes.tex") -> list[Path]:
    """The main file plus every \\input/\\include it reaches."""
    seen, order = set(), []

    def visit(path: Path) -> None:
        if path in seen or not path.exists():
            return
        seen.add(path)
        order.append(path)
        for m in re.finditer(r"^[^%\n]*\\(?:input|include)\{([^}]+)\}", path.read_text(errors="replace"), re.M):
            target = notes_dir / m.group(1)
            visit(target if target.suffix == ".tex" else target.with_suffix(".tex"))

    visit(notes_dir / main)
    return order


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def prose_sentences(text: str) -> list[str]:
    body = re.sub(r"\\begin\{(tikzpicture|axis|align\*?|equation\*?|gather\*?|tabularx?|longtable)\}.*?\\end\{\1\}",
                  " ", text, flags=re.S)
    body = re.sub(r"\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)", " M ", body, flags=re.S)
    body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", body)
    body = re.sub(r"[{}]", " ", body)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.split()) >= 8]


def lint(files: list[Path], notes_dir: Path) -> tuple[list[dict], dict]:
    issues: list[dict] = []
    counts: collections.Counter[str] = collections.Counter()
    sentences: collections.Counter[str] = collections.Counter()
    unit_stats = []
    for f in files:
        raw = f.read_text(errors="replace")
        text = strip_comments(raw)
        rel = str(f.relative_to(notes_dir))
        for i, line in enumerate(raw.splitlines(), 1):
            code = strip_comments(line)
            if PLACEHOLDER_RE.search(code):
                issues.append({"severity": "error", "kind": "placeholder", "where": f"{rel}:{i}", "detail": code.strip()[:120]})
            if CODE_MATH_RE.search(code):
                issues.append({"severity": "error", "kind": "code-style-math", "where": f"{rel}:{i}",
                               "detail": "use LaTeX (bmatrix, \\sqrt{}, x^{2}) instead of code notation: " + code.strip()[:100]})
            heading = re.match(r"\s*\\(part|(sub)*section)\*?\{(.*)\}", code)
            if heading and "$" in heading.group(3) and "texorpdfstring" not in heading.group(3):
                issues.append({"severity": "warning", "kind": "math-in-heading", "where": f"{rel}:{i}",
                               "detail": "wrap heading maths as \\texorpdfstring{$...$}{plain} so PDF bookmarks work"})
            if ESCAPED_IN_HEADING_RE.search(code):
                issues.append({"severity": "error", "kind": "escaped-math-in-heading", "where": f"{rel}:{i}",
                               "detail": "write maths in headings as \\(...\\), not escaped text"})
            if SOURCE_SECTION_RE.search(code):
                issues.append({"severity": "warning", "kind": "source-list", "where": f"{rel}:{i}",
                               "detail": "notes should teach, not list sources; keep provenance in comments"})
        envs = collections.Counter(m.group(1) for m in ENV_RE.finditer(text))
        counts.update(envs)
        for s in prose_sentences(text):
            sentences[re.sub(r"\s+", " ", s.lower())] += 1
        if f.parent.name == "units":
            words = len(re.findall(r"[A-Za-z]{2,}", re.sub(r"\\[a-zA-Z]+", " ", text)))
            figures = envs["tikzpicture"] + len(re.findall(r"\\includegraphics", text))  # axis lives inside tikzpicture
            results = sum(envs[k] for k in ("theorem", "proposition", "lemma", "corollary"))
            stat = {"file": rel, "words": words, "definitions": envs["definition"], "results": results,
                    "proofs": envs["proof"], "examples": envs["example"], "figures": figures,
                    "exercises": envs["exercise"], "solutions": envs["solution"]}
            unit_stats.append(stat)
            if words < 600:
                issues.append({"severity": "warning", "kind": "thin-unit", "where": rel,
                               "detail": f"only {words} words; a unit should teach its material in full"})
            solved = min(envs["exercise"], envs["solution"])
            if envs["example"] == 0 and solved < 3:  # exam/review units may be solved-problem sets
                issues.append({"severity": "error", "kind": "no-worked-example", "where": rel,
                               "detail": "every unit needs at least one fully worked example"})
            if figures == 0:
                issues.append({"severity": "warning", "kind": "no-figure", "where": rel,
                               "detail": "add a figure that teaches (diagram, plot, structure) unless the unit truly has none"})
            if envs["exercise"] > envs["solution"]:
                issues.append({"severity": "error", "kind": "unsolved-exercise", "where": rel,
                               "detail": f"{envs['exercise']} exercises but {envs['solution']} solutions"})
            if results and envs["proof"] == 0:
                issues.append({"severity": "warning", "kind": "no-proofs", "where": rel,
                               "detail": "theorems/propositions are stated without any proof or derivation"})
    total = sum(sentences.values()) or 1
    repeated = {s: c for s, c in sentences.items() if c >= 3}
    ratio = sum(c - 1 for c in sentences.values() if c > 1) / total
    if ratio > 0.03:
        issues.append({"severity": "error", "kind": "repetition", "where": "all",
                       "detail": f"{ratio:.1%} of sentences are repeats; replace template prose with content-specific writing"})
    for s, c in sorted(repeated.items(), key=lambda kv: -kv[1])[:5]:
        issues.append({"severity": "warning", "kind": "repeated-sentence", "where": "all", "detail": f"x{c}: {s[:110]}"})
    return issues, {"environments": dict(counts), "units": unit_stats, "repeated_sentence_ratio": round(ratio, 4)}


def undefined_refs(log: str) -> list[str]:
    return sorted(set(re.findall(r"Reference `([^']+)' on page \d+ undefined", log)))


def log_issues(log: str, units: set[str] | None = None) -> list[dict]:
    """Issues from the TeX log. With ``units`` (a partial build), references into other units are ignored."""
    issues = []
    current, seen = "notes.tex", set()
    for line in log.splitlines():
        opened = re.findall(r"\((?:\./)?(units/[\w-]+\.tex)", line)
        if opened:
            current = opened[-1]
        m = re.search(r"Overfull \\hbox \((\d+(?:\.\d+)?)pt too wide\).*?lines (\d+)--(\d+)", line)
        if m and float(m.group(1)) > 8:
            key = (current, m.group(3))
            if key not in seen:
                seen.add(key)
                issues.append({"severity": "warning", "kind": "overfull-box", "where": f"{current}:{m.group(3)}",
                               "detail": f"line sticks into the margin by {float(m.group(1)):.0f}pt"})
    refs = undefined_refs(log)
    if units is not None:
        def unit_of(key: str) -> str | None:
            m = re.search(r"(u\d{2,3})", key)
            return m.group(1) if m else None
        refs = [r for r in refs if unit_of(r) is None or unit_of(r) in units]
    if refs:
        issues.append({"severity": "error", "kind": "undefined-reference", "where": "pdf",
                       "detail": f"no \\label for: {', '.join(refs[:8])}"})
    missing = set(re.findall(r"Missing character: There is no (\S+)", log))
    if missing:
        issues.append({"severity": "error", "kind": "missing-glyph", "where": "pdf",
                       "detail": f"characters not in font: {' '.join(sorted(missing))[:80]}"})
    return issues


def pdf_checks(pdf: Path) -> tuple[list[dict], dict]:
    import pymupdf

    issues = []
    with pymupdf.open(pdf) as doc:
        pages = doc.page_count
        sparse = []
        for i, page in enumerate(doc):
            if i < 2:
                continue  # title page and contents
            words = len(page.get_text("words"))
            drawings = len(page.get_drawings())
            if words < 60 and drawings < 15:
                sparse.append(i + 1)
        if sparse:
            issues.append({"severity": "warning", "kind": "sparse-page", "where": "pdf",
                           "detail": f"pages {sparse[:12]} are nearly empty (stranded figure or tail?)"})
    return issues, {"pages": pages}


def previews(pdf: Path, out: Path, pages: list[int]) -> list[str]:
    import pymupdf
    from PIL import Image, ImageDraw

    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    made = []
    with pymupdf.open(pdf) as doc:
        thumbs = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=60)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            thumbs.append((i + 1, img))
        per, cols = 6, 3
        for s in range(0, len(thumbs), per):
            chunk = thumbs[s:s + per]
            tw, th = chunk[0][1].size
            sheet = Image.new("RGB", (cols * (tw + 10) + 10, ((len(chunk) + cols - 1) // cols) * (th + 30) + 10), (90, 90, 90))
            draw = ImageDraw.Draw(sheet)
            for j, (num, img) in enumerate(chunk):
                x, y = 10 + (j % cols) * (tw + 10), 10 + (j // cols) * (th + 30)
                draw.text((x, y), f"p.{num}", fill=(255, 230, 120))
                sheet.paste(img, (x, y + 18))
            path = out / f"sheet-{s // per + 1:02d}.png"
            sheet.save(path)
            made.append(str(path))
        for num in pages:
            if 1 <= num <= doc.page_count:
                path = out / f"page-{num:03d}.png"
                doc[num - 1].get_pixmap(dpi=110).save(path)
                made.append(str(path))
    return made


def build_partial(notes_dir: Path, units: list[str], pages: list[int], no_preview: bool) -> int:
    """Compile notes.tex with only the chosen units, in its own folder, without touching the full report."""
    tag = "-".join(units) if len(units) <= 3 else f"{units[0]}-to-{units[-1]}-{hashlib.sha1(' '.join(units).encode()).hexdigest()[:6]}"
    main_text = (notes_dir / "notes.tex").read_text(errors="replace")
    wanted = set(units)

    def keep(match: re.Match) -> str:
        unit = Path(match.group(1)).stem
        return match.group(0) if unit in wanted else "% (partial build) " + match.group(0)

    partial = re.sub(r"^[^%\n]*\\input\{(units/[^}]+)\}", keep, main_text, flags=re.M)
    partial = re.sub(r"\\appendix.*?(?=\\end\{document\})", "", partial, flags=re.S)  # no formula-sheet page
    # drop \part headings that introduce no unit of this build (they would leave empty pages)
    lines, out = partial.splitlines(), []
    for i, line in enumerate(lines):
        if re.match(r"\s*\\part\b", line):
            following = []
            for nxt in lines[i + 1:]:
                if re.match(r"\s*\\part\b|\s*\\appendix|\s*\\end\{document\}", nxt):
                    break
                following.append(nxt)
            if not any(re.match(r"\s*\\input\{units/", ln) for ln in following):
                line = "% (partial build) " + line
        out.append(line)
    partial = "\n".join(out) + "\n"
    missing = [u for u in units if not (notes_dir / "units" / f"{u}.tex").exists()]
    if missing:
        print(f"error: no unit file for {', '.join(missing)} under {notes_dir / 'units'}", file=sys.stderr)
        return 1
    main_name = f"_partial_{tag}.tex"
    (notes_dir / main_name).write_text(partial, encoding="utf-8")
    out = notes_dir / "partial" / tag
    try:
        engine, log = compile_tex(notes_dir, main_name, out)
    except CompileError as exc:
        print(f"LaTeX compile failed ({exc.engine}):\n{exc.summary()}", file=sys.stderr)
        return 1
    finally:
        (notes_dir / main_name).unlink(missing_ok=True)
    files = [notes_dir / "units" / f"{u}.tex" for u in units]
    issues, stats = lint(files, notes_dir)
    issues += log_issues(log, units=wanted)  # references into units outside this build are expected
    pdf = out / f"_partial_{tag}.pdf"
    pdf_issues, pdf_stats = pdf_checks(pdf)
    pdf_issues = [i for i in pdf_issues if i["kind"] != "sparse-page"]  # front/back matter of a partial build
    sheets = [] if no_preview else previews(pdf, out / "preview", pages)
    print(f"partial build {tag}: {pdf_stats['pages']} pages via {engine} -> {pdf}")
    print("  unit   words  defs results proofs examples figures exercises/solutions")
    for u in stats["units"]:
        print(f"  {Path(u['file']).stem:<6} {u['words']:>5} {u['definitions']:>5} {u['results']:>7} {u['proofs']:>6} "
              f"{u['examples']:>8} {u['figures']:>7} {u['exercises']:>9}/{u['solutions']}")
    for i in issues + pdf_issues:
        print(f"  {i['severity'].upper():7} {i['kind']} [{i['where']}] {i['detail']}")
    for sheet in sheets:
        print(f"  look at: {sheet}")
    return 0 if not [i for i in issues if i["severity"] == "error"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--pages", type=int, nargs="*", default=[], help="also render these pages at full size")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--units", nargs="+", default=None,
                    help="compile only these unit ids (e.g. u03 u04) into notes/partial/; safe to run in parallel")
    args = ap.parse_args(argv)
    run = args.run.resolve()
    notes_dir = run / "notes" if (run / "notes" / "notes.tex").exists() else run
    if not (notes_dir / "notes.tex").exists():
        print(f"error: {args.run}/notes/notes.tex not found (start from assets/notes-template.tex)", file=sys.stderr)
        return 1
    if args.units:
        return build_partial(notes_dir, args.units, args.pages, args.no_preview)
    report: dict = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    try:
        engine, log = compile_tex(notes_dir)
    except CompileError as exc:
        print(f"LaTeX compile failed ({exc.engine}):\n{exc.summary()}", file=sys.stderr)
        report.update({"status": "compile-failed", "engine": exc.engine, "errors": exc.summary()})
        (notes_dir / "notes_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1
    pdf = notes_dir / "notes.pdf"
    files = tex_files(notes_dir)
    issues, stats = lint(files, notes_dir)
    issues += log_issues(log)
    pdf_issues, pdf_stats = pdf_checks(pdf)
    issues += pdf_issues
    sheets = [] if args.no_preview else previews(pdf, notes_dir / "preview", args.pages)
    errors = [i for i in issues if i["severity"] == "error"]
    source_hash = hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()
    report.update({
        "status": "ok" if not errors else "has-errors", "engine": engine, "pdf": "notes.pdf",
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "source_sha256": source_hash,
        "files": [str(f.relative_to(notes_dir)) for f in files], **pdf_stats, **stats,
        "issues": issues, "previews": sheets,
    })
    (notes_dir / "notes_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    env = stats["environments"]
    print(f"notes.pdf: {pdf_stats['pages']} pages via {engine}; "
          f"{env.get('definition', 0)} definitions, {sum(env.get(k, 0) for k in ('theorem', 'proposition', 'lemma', 'corollary'))} results, "
          f"{env.get('proof', 0)} proofs, {env.get('example', 0)} examples, "
          f"{env.get('tikzpicture', 0) + env.get('axis', 0)} figures, {env.get('exercise', 0)} exercises")
    for i in issues:
        print(f"  {i['severity'].upper():7} {i['kind']} [{i['where']}] {i['detail']}")
    if sheets:
        print("look at:")
        for s in sheets:
            print(f"  {s}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

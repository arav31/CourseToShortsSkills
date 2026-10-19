#!/usr/bin/env python3
"""Check outline.json and short_plan.json before anything is animated.

    python check_plan.py runs/<course> [--strict]

Catches the mistakes that are expensive to discover after rendering:
missing fields, placeholder or vague worked examples, examples reused across
shorts, prerequisites that point forward, units nobody covers, and shorts that
reference sources which do not exist. Writes plan_check.json next to the plan
(the course-to-shorts status/gate reads it). Exit code 1 means fix the plan.
See references/plan-schema.md for the format.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

PLACEHOLDERS = re.compile(
    r"\b(TODO|TBD|FIXME|lorem ipsum|placeholder|e\.g\. a small example|choose (a|an|some) (small|simple)|"
    r"work through the definition|insert (an |the )?example|some numbers|a concrete example here|xxx)\b",
    re.I,
)
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CONCRETE_RE = re.compile(r"\d|[=<>≤≥∈⊂∑∫√πλθ∞]|\\[a-zA-Z]+|\{[^}]*\}|\([^)]*,[^)]*\)")
VAGUE_WORDS = {"something", "stuff", "things", "various", "etc"}


def load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"missing {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}")


def words(text: str) -> int:
    return len(re.findall(r"[\w'’-]+", text or ""))


def text_of(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(text_of(v) for v in value)
    if isinstance(value, dict):
        return " ".join(text_of(v) for v in value.values())
    return "" if value is None else str(value)


def example_fingerprint(ex: dict) -> tuple[str, frozenset[str]]:
    blob = text_of([ex.get("setup"), ex.get("steps"), ex.get("result")]).lower()
    numbers = frozenset(re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", blob))
    norm = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9=+*/^().,\- ]", "", blob)).strip()
    return hashlib.sha1(norm.encode()).hexdigest(), numbers


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def check_outline(run: Path, outline: dict, rep: Report) -> list[str]:
    course = outline.get("course") if isinstance(outline, dict) else None
    if not isinstance(course, dict) or not str(course.get("title", "")).strip():
        rep.err("outline.course", "needs a title")
    units = outline.get("units") if isinstance(outline, dict) else None
    if not isinstance(units, list) or not units:
        rep.err("outline.units", "must be a non-empty list in course order")
        return []
    ids: list[str] = []
    for i, unit in enumerate(units):
        where = f"outline.units[{i}]"
        if not isinstance(unit, dict):
            rep.err(where, "must be an object")
            continue
        uid = str(unit.get("id", ""))
        where = f"unit {uid or i}"
        if not uid:
            rep.err(where, "missing id")
        elif uid in ids:
            rep.err(where, "duplicate id")
        ids.append(uid)
        if not str(unit.get("title", "")).strip():
            rep.err(where, "missing title")
        if words(unit.get("summary", "")) < 12:
            rep.warn(where, "summary is very short; say what the unit actually teaches")
        sources = unit.get("sources") or []
        if not sources:
            rep.warn(where, "no sources listed; every unit should point at the files it came from")
        for src in sources:
            if not (run / str(src)).exists():
                rep.err(where, f"source file {src} does not exist")
    return ids


def check_plan(plan: dict, unit_ids: list[str], rep: Report) -> None:
    if not isinstance(plan, dict):
        rep.err("short_plan", "must be an object")
        return
    series = plan.get("series")
    if not isinstance(series, dict) or not str(series.get("title", "")).strip():
        rep.err("short_plan.series", "needs a title (the playlist name)")
    shorts = plan.get("shorts")
    if not isinstance(shorts, list) or not shorts:
        rep.err("short_plan.shorts", "must be a non-empty list in teaching order")
        return
    seen_ids: list[str] = []
    slugs: set[str] = set()
    prints: dict[str, str] = {}
    number_sets: list[tuple[str, frozenset[str]]] = []
    covered: set[str] = set()
    for i, short in enumerate(shorts):
        sid = str(short.get("id", "")) if isinstance(short, dict) else ""
        where = f"short {sid or i + 1}"
        if not isinstance(short, dict):
            rep.err(where, "must be an object")
            continue
        if not re.match(r"^s\d{2,3}$", sid):
            rep.err(where, "id must look like s01, s02, ...")
        elif sid in seen_ids:
            rep.err(where, "duplicate id")
        slug = str(short.get("slug", ""))
        if not SLUG_RE.match(slug):
            rep.err(where, "slug must be kebab-case (letters, digits, hyphens)")
        elif slug in slugs:
            rep.err(where, f"duplicate slug {slug}")
        slugs.add(slug)
        title = str(short.get("title", "")).strip()
        if not title:
            rep.err(where, "missing title")
        elif len(title) > 60:
            rep.warn(where, f"title is {len(title)} chars; keep it under 60 so it fits the title band")
        units = short.get("units") or []
        if not units:
            rep.err(where, "list the outline unit ids it teaches in 'units'")
        for u in units:
            if unit_ids and u not in unit_ids:
                rep.err(where, f"unit {u} is not in outline.json")
            covered.add(str(u))
        for pre in short.get("prerequisites") or []:
            if pre not in seen_ids:
                rep.err(where, f"prerequisite {pre} must be an earlier short id")
        hook = str(short.get("hook", ""))
        if words(hook) < 5:
            rep.err(where, "hook missing or too thin; open with the question or tension")
        elif words(hook) > 30:
            rep.warn(where, "hook is long; the first line must land in about 3 seconds")
        claim = str(short.get("claim", ""))
        if words(claim) < 6:
            rep.err(where, "claim missing; state the one idea the video makes obvious")
        if not str(short.get("visual", "")).strip() or words(short.get("visual", "")) < 10:
            rep.err(where, "visual must name the on-screen objects and the motion that carries the argument")
        if words(short.get("misconception", "")) < 6:
            rep.warn(where, "misconception is missing or thin")
        practice = short.get("practice") or {}
        if not (isinstance(practice, dict) and words(practice.get("question", "")) >= 5
                and words(practice.get("answer", "")) >= 1):
            rep.warn(where, "practice needs a question and its answer")
        ex = short.get("worked_example")
        if not isinstance(ex, dict):
            rep.err(where, "worked_example must be an object with setup, steps, result")
            seen_ids.append(sid)
            continue
        steps = ex.get("steps")
        if not str(ex.get("setup", "")).strip():
            rep.err(where, "worked_example.setup is empty")
        if not isinstance(steps, list) or len(steps) < 2:
            rep.err(where, "worked_example.steps needs at least two concrete steps")
        if not str(ex.get("result", "")).strip():
            rep.err(where, "worked_example.result is empty")
        blob = text_of(ex)
        if not CONCRETE_RE.search(blob):
            rep.err(where, "worked example has no concrete values, symbols or objects")
        if PLACEHOLDERS.search(blob) or PLACEHOLDERS.search(text_of(short)):
            rep.err(where, "contains placeholder language")
        if VAGUE_WORDS & set(re.findall(r"[a-z]+", blob.lower())):
            rep.warn(where, "worked example uses vague words (something/stuff/etc.); be specific")
        fp, nums = example_fingerprint(ex)
        if fp in prints:
            rep.err(where, f"worked example is identical to {prints[fp]}")
        prints.setdefault(fp, sid)
        for other_id, other_nums in number_sets:
            if len(nums) >= 4 and nums == other_nums:
                rep.err(where, f"worked example reuses exactly the numbers of {other_id}; make it fresh")
        number_sets.append((sid, nums))
        seen_ids.append(sid)

    skipped = {str(s.get("unit")): s for s in plan.get("skipped_units") or [] if isinstance(s, dict)}
    for uid, s in skipped.items():
        if words(s.get("reason", "")) < 4:
            rep.warn(f"skipped unit {uid}", "give a reason (e.g. 'proof-only; covered in notes')")
    for uid in unit_ids:
        if uid not in covered and uid not in skipped:
            rep.warn(f"unit {uid}", "no short covers it and it is not in skipped_units")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)
    rep = Report()
    outline = load(args.run / "outline.json")
    plan_path = args.run / "short_plan.json"
    plan = load(plan_path)
    unit_ids = check_outline(args.run, outline, rep)
    check_plan(plan, unit_ids, rep)
    errors = rep.errors + (rep.warnings if args.strict else [])
    result = {
        "status": "pass" if not errors else "fail",
        "errors": rep.errors, "warnings": rep.warnings, "strict": args.strict,
        "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "shorts": len(plan.get("shorts", [])) if isinstance(plan, dict) else 0,
        "units": len(unit_ids),
    }
    (args.run / "plan_check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for e in rep.errors:
        print(f"ERROR   {e}")
    for w in rep.warnings:
        print(f"WARNING {w}")
    print(f"\n{result['units']} units, {result['shorts']} shorts: {result['status'].upper()}"
          f" ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Show where a course run stands, and gate it before publishing.

    python run_status.py runs/<course>           # stage-by-stage status
    python run_status.py runs/<course> --gate    # exit 1 unless publish-ready
    python run_status.py runs/<course> --gate --shorts-only   # the user asked for shorts, not notes
    python run_status.py runs/<course> --json

Reads the reports each skill writes (plan_check.json, notes/notes_report.json,
shorts/*/render_report.json, shorts/*/review.json) and checks they are still
current: a report or approval made before the artifact changed counts as
missing. Publish-ready means: the plan passes its check, the notes compiled
with a real TeX engine without errors, and every planned short has a final
render with no errors and an approved review of that exact MP4. With
--shorts-only the notes stage is reported but does not block.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def short_dir(run: Path, index: int, short: dict) -> Path:
    for candidate in (run / "shorts" / f"{index:02d}-{short.get('slug', '')}", run / "shorts" / str(short.get("slug", ""))):
        if candidate.exists():
            return candidate
    return run / "shorts" / f"{index:02d}-{short.get('slug', '')}"


def status(run: Path, shorts_only: bool = False) -> dict:
    out: dict = {"run": str(run), "stages": {}, "shorts": [], "blockers": [], "shorts_only": shorts_only}
    st = out["stages"]
    blockers = out["blockers"]
    note_blockers: list[str] = []  # notes problems block the gate unless the run is shorts-only

    pack = read(run / "source_pack.json")
    if pack:
        st["sources"] = {"state": "done", "materials": pack["stats"]["materials"],
                         "chars": pack["stats"]["total_chars"], "warnings": len(pack.get("warnings", []))}
    else:
        st["sources"] = {"state": "missing"}
        blockers.append("sources: run course-plan ingest")

    plan = read(run / "short_plan.json")
    check = read(run / "plan_check.json")
    if not plan or not (run / "outline.json").exists():
        st["plan"] = {"state": "missing"}
        blockers.append("plan: write outline.json and short_plan.json (course-plan)")
    elif not check or check.get("plan_sha256") != sha256(run / "short_plan.json"):
        st["plan"] = {"state": "unchecked", "shorts": len(plan.get("shorts", []))}
        blockers.append("plan: run course-plan check_plan.py on the current plan")
    else:
        st["plan"] = {"state": check["status"], "shorts": check["shorts"], "units": check["units"],
                      "warnings": len(check.get("warnings", []))}
        if check["status"] != "pass":
            blockers.append(f"plan: check_plan.py reports {len(check.get('errors', []))} errors")

    notes_dir = run / "notes"
    report = read(notes_dir / "notes_report.json")
    if not (notes_dir / "notes.tex").exists():
        st["notes"] = {"state": "missing"}
        note_blockers.append("notes: write notes/notes.tex (course-notes)")
    elif not report:
        st["notes"] = {"state": "unbuilt"}
        note_blockers.append("notes: run course-notes build_notes.py")
    else:
        files = [notes_dir / f for f in report.get("files", [])]
        current = hashlib.sha256(b"".join(f.read_bytes() for f in files if f.exists())).hexdigest()
        stale = current != report.get("source_sha256") or any(not f.exists() for f in files)
        unit_files = sorted((notes_dir / "units").glob("*.tex")) if (notes_dir / "units").exists() else []
        unlisted = [f.name for f in unit_files if str(f.relative_to(notes_dir)) not in report.get("files", [])]
        state = "stale" if stale else report.get("status")
        st["notes"] = {"state": state, "pages": report.get("pages"), "engine": report.get("engine"),
                       "errors": len([i for i in report.get("issues", []) if i["severity"] == "error"])}
        if stale:
            note_blockers.append("notes: sources changed since the last build; rebuild")
        elif report.get("status") != "ok":
            note_blockers.append(f"notes: {st['notes']['errors']} lint/compile errors")
        if unlisted:
            note_blockers.append(f"notes: unit files not \\input by notes.tex: {', '.join(unlisted)}")
        if plan and (run / "outline.json").exists():
            outline = read(run / "outline.json") or {}
            text = " ".join(f.read_text(errors="replace") for f in files if f.exists())
            missing = [u["title"] for u in outline.get("units", [])
                       if u.get("id") and not re.search(rf"%\s*unit:\s*{re.escape(u['id'])}\b", text)]
            if missing:
                st["notes"]["units_missing"] = missing
                note_blockers.append(f"notes: {len(missing)} outline units have no '% unit: <id>' chapter (e.g. {missing[0]})")
    if shorts_only:
        st["notes"]["gated"] = False
    else:
        blockers.extend(note_blockers)

    for i, short in enumerate((plan or {}).get("shorts", []), 1):
        sdir = short_dir(run, i, short)
        row = {"id": short.get("id"), "slug": short.get("slug"), "dir": str(sdir.relative_to(run)) if sdir.exists() else None}
        rep = read(sdir / "render_report.json")
        if not (sdir / "scene.py").exists():
            row["state"] = "no scene"
        elif not rep:
            row["state"] = "not rendered"
        else:
            video = sdir / rep["video"]
            fresh = video.exists() and sha256(video) == rep.get("sha256")
            errors = [x for x in rep.get("issues", []) if x["severity"] == "error"]
            row.update({"quality": rep.get("quality"), "duration": rep.get("duration"), "errors": len(errors),
                        "warnings": len(rep.get("issues", [])) - len(errors)})
            scene_newer = (sdir / "scene.py").stat().st_mtime > video.stat().st_mtime if video.exists() else True
            review = read(sdir / "review.json")
            approved = bool(review and review.get("status") == "approved" and video.exists()
                            and review.get("sha256") == sha256(video))
            row["review"] = ("approved" if approved else (review or {}).get("status", "none"))
            if not fresh or scene_newer:
                row["state"] = "stale render"
            elif rep.get("quality") != "final":
                row["state"] = "preview only"
            elif errors:
                row["state"] = "render errors"
            elif not approved:
                row["state"] = "awaiting review"
            else:
                row["state"] = "ready"
        if row["state"] != "ready":
            blockers.append(f"short {short.get('id')} ({short.get('slug')}): {row['state']}")
        out["shorts"].append(row)

    queue = read(run / "reels_queue.json")
    if queue:
        st["reels"] = {"queued": len(queue.get("items", [])), "skipped": len(queue.get("skipped", []))}
    out["publish_ready"] = not blockers
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--gate", action="store_true", help="exit 1 unless everything is publish-ready")
    ap.add_argument("--shorts-only", action="store_true",
                    help="the run makes shorts only: report the notes stage but do not block on it")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    data = status(args.run, shorts_only=args.shorts_only)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"run: {args.run}")
        for name, info in data["stages"].items():
            extras = ", ".join(f"{k}={v}" for k, v in info.items()
                               if k not in {"state", "gated"} and not isinstance(v, list))
            if info.get("gated") is False:
                extras = (extras + ", " if extras else "") + "not gated (--shorts-only)"
            print(f"  {name:<8} {info['state']:<12} {extras}")
        if data["shorts"]:
            print("  shorts:")
            for row in data["shorts"]:
                extra = f"{row.get('duration', '')}s" if row.get("duration") else ""
                print(f"    {row['id']:<5} {str(row['slug'])[:34]:<34} {row['state']:<16} {extra}")
        print("publish-ready" if data["publish_ready"] else "blockers:")
        for b in data["blockers"]:
            print(f"  - {b}")
    return 0 if (data["publish_ready"] or not args.gate) else 1


if __name__ == "__main__":
    sys.exit(main())

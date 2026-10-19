#!/usr/bin/env python3
"""Turn approved shorts into an Instagram Reels series and (optionally) publish it.

    python reels.py queue   runs/<course> [--public-base-url URL] [--include-unapproved]
    python reels.py publish runs/<course> [--dry-run] [--only s01 s02]

queue    writes reels_queue.json: one item per short, in series order, with the
         caption (from the plan's reel_caption or composed from hook/claim/
         practice), "Part i/N" numbering, hashtags, local file, hash and, when
         --public-base-url is given, the public video_url Instagram will fetch.
         Only shorts with an approved review.json matching the current MP4 are
         queued unless --include-unapproved is passed (drafts only).
publish  uses the Instagram Graph API (container -> poll -> media_publish).
         Needs IG_USER_ID and META_ACCESS_TOKEN (or IG_ACCESS_TOKEN), and
         public HTTPS video URLs. Results go to reels_results.json; already
         published items are skipped on re-runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CAPTION_LIMIT = 2200
DEFAULT_TAGS = ["#math", "#stem", "#learning", "#education", "#manim"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def short_dir(run: Path, index: int, short: dict) -> Path:
    for candidate in (run / "shorts" / f"{index:02d}-{short['slug']}", run / "shorts" / short["slug"]):
        if candidate.exists():
            return candidate
    return run / "shorts" / f"{index:02d}-{short['slug']}"


def compose_caption(plan: dict, short: dict, part: int, total: int) -> str:
    series = plan.get("series", {})
    tags = series.get("hashtags") or DEFAULT_TAGS
    if short.get("reel_caption"):
        body = short["reel_caption"].strip()
    else:
        practice = short.get("practice") or {}
        lines = [short.get("hook", ""), "", short.get("claim", "")]
        if practice.get("question"):
            lines += ["", f"Try it: {practice['question']}", f"(Answer: {practice.get('answer', '')})"]
        body = "\n".join(lines).strip()
    head = f"{series.get('title', plan.get('course_title', 'Course'))} · Part {part}/{total}: {short['title']}"
    caption = f"{head}\n\n{body}\n\n{' '.join(tags)}"
    return caption if len(caption) <= CAPTION_LIMIT else caption[: CAPTION_LIMIT - 1] + "…"


def cmd_queue(args: argparse.Namespace) -> int:
    run: Path = args.run
    plan = json.loads((run / "short_plan.json").read_text())
    shorts = plan.get("shorts", [])
    items, skipped = [], []
    base = args.public_base_url or os.environ.get("PUBLIC_VIDEO_BASE_URL")
    for i, short in enumerate(shorts, 1):
        sdir = short_dir(run, i, short)
        report_path = sdir / "render_report.json"
        if not report_path.exists():
            skipped.append(f"{short['id']}: not rendered")
            continue
        report = json.loads(report_path.read_text())
        video = sdir / report["video"]
        if report.get("quality") != "final" or not video.exists():
            skipped.append(f"{short['id']}: no final-quality render")
            continue
        digest = sha256(video)
        review = json.loads((sdir / "review.json").read_text()) if (sdir / "review.json").exists() else {}
        approved = review.get("status") == "approved" and review.get("sha256") == digest
        if not approved and not args.include_unapproved:
            skipped.append(f"{short['id']}: review missing, rejected or stale")
            continue
        item = {
            "short_id": short["id"], "part": i, "title": short["title"],
            "video_file": str(video.relative_to(run)), "sha256": digest, "duration": report.get("duration"),
            "caption": compose_caption(plan, short, i, len(shorts)), "approved": approved, "status": "queued",
        }
        if base:
            item["video_url"] = urllib.parse.urljoin(base.rstrip("/") + "/", video.name)
        items.append(item)
    queue = {"series": plan.get("series", {}), "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "items": items, "skipped": skipped}
    (run / "reels_queue.json").write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"queued {len(items)} of {len(shorts)} shorts -> {run / 'reels_queue.json'}")
    for s in skipped:
        print(f"  skipped {s}")
    if items and not base:
        print("  note: no --public-base-url; host the MP4s publicly and re-run queue before publishing")
    return 0 if items else 1


def graph(path: str, params: dict, method: str = "POST") -> dict:
    version = os.environ.get("META_GRAPH_VERSION", "v21.0").strip("/")
    url = f"https://graph.facebook.com/{version}{path}"
    data = urllib.parse.urlencode(params).encode()
    req = (urllib.request.Request(f"{url}?{data.decode()}") if method == "GET"
           else urllib.request.Request(url, data=data, method="POST"))
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"error": exc.read().decode(errors="replace"), "http_status": exc.code}


def cmd_publish(args: argparse.Namespace) -> int:
    run: Path = args.run
    queue = json.loads((run / "reels_queue.json").read_text())
    results_path = run / "reels_results.json"
    previous = json.loads(results_path.read_text()) if results_path.exists() else {"results": []}
    done = {r["short_id"] for r in previous.get("results", []) if r.get("status") == "published"}
    token = os.environ.get("META_ACCESS_TOKEN") or os.environ.get("IG_ACCESS_TOKEN")
    user = os.environ.get("IG_USER_ID")
    results = [r for r in previous.get("results", []) if r.get("status") == "published"]
    for item in queue.get("items", []):
        sid = item["short_id"]
        if args.only and sid not in args.only:
            continue
        if sid in done:
            print(f"{sid}: already published, skipping")
            continue
        result = {"short_id": sid, "video_url": item.get("video_url")}
        problems = []
        if not item.get("approved"):
            problems.append("not approved")
        if not item.get("video_url", "").startswith("https://"):
            problems.append("no public https video_url")
        if not args.dry_run and not (token and user):
            problems.append("IG_USER_ID / META_ACCESS_TOKEN not set")
        if problems:
            result.update({"status": "skipped", "message": "; ".join(problems)})
        elif args.dry_run:
            result.update({"status": "dry-run", "message": "would create a REELS container, wait for FINISHED, then publish"})
        else:
            created = graph(f"/{user}/media", {"media_type": "REELS", "video_url": item["video_url"],
                                               "caption": item["caption"], "share_to_feed": "true", "access_token": token})
            cid = created.get("id")
            if not cid:
                result.update({"status": "failed", "stage": "create", "response": created})
            else:
                state = {}
                for _ in range(args.poll_attempts):
                    time.sleep(args.poll_seconds)
                    state = graph(f"/{cid}", {"fields": "status_code,status", "access_token": token}, method="GET")
                    if state.get("status_code") in {"FINISHED", "ERROR", "EXPIRED"}:
                        break
                if state.get("status_code") != "FINISHED":
                    result.update({"status": "failed", "stage": "processing", "creation_id": cid, "response": state})
                else:
                    pub = graph(f"/{user}/media_publish", {"creation_id": cid, "access_token": token})
                    result.update({"status": "published" if pub.get("id") else "failed", "creation_id": cid,
                                   "media_id": pub.get("id"), "response": None if pub.get("id") else pub})
        print(f"{sid}: {result['status']} {result.get('message', '')}".rstrip())
        results.append(result)
    results_path.write_text(json.dumps({"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                        "results": results}, indent=2), encoding="utf-8")
    return 0 if all(r["status"] in {"published", "dry-run"} for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue")
    q.add_argument("run", type=Path)
    q.add_argument("--public-base-url", default=None)
    q.add_argument("--include-unapproved", action="store_true")
    p = sub.add_parser("publish")
    p.add_argument("run", type=Path)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--poll-seconds", type=int, default=10)
    p.add_argument("--poll-attempts", type=int, default=30)
    args = ap.parse_args(argv)
    return cmd_queue(args) if args.cmd == "queue" else cmd_publish(args)


if __name__ == "__main__":
    sys.exit(main())

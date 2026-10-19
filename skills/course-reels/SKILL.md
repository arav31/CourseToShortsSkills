---
name: course-reels
description: Package approved course explainer shorts as an ordered Instagram Reels series (captions, part numbers, hashtags, posting queue) and optionally publish them through the Instagram Graph API. Use when someone wants to post, publish, schedule or caption the rendered shorts, or needs a posting queue for manual upload.
---

# Course Reels

**Paths.** `$SKILL_DIR` means this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`; otherwise the folder containing this SKILL.md). `$PY` is the Python interpreter printed by the course-to-shorts doctor (`PY=...`). Run directories such as `runs/<course>` are relative to the user's working directory.

Turns the approved videos in `runs/<course>/shorts/` into `reels_queue.json`, and publishes
it when the user has Instagram API access.

## 1. Check readiness

Only approved final renders are queued (a `review.json` whose hash matches the current MP4).
Run the course-to-shorts gate first and fix any blockers it lists:
`$PY "<course-to-shorts skill folder>/scripts/run_status.py" runs/<course> --gate` (the course-to-shorts skill is a sibling folder of this one).

## 2. Captions

Captions come from each short's `reel_caption` in `short_plan.json`, or are composed from
hook, claim and practice question, prefixed with "<series> · Part i/N: <title>" and followed
by `series.hashtags`. Writing a `reel_caption` per short gives better results: a one-line
hook, two or three lines on the idea, the practice question, then hashtags. Instagram allows
2,200 characters; the first ~125 show before "more".

## 3. Queue

```bash
$PY "$SKILL_DIR/scripts/reels.py" queue runs/<course> --public-base-url "https://<host>/<path>/"
```

Instagram's API fetches each video from a public HTTPS URL, so the MP4s must be hosted
first (for example an S3/R2/GCS bucket, a CDN, or GitHub Release assets). The queue maps
each file name onto the base URL. Without a URL the queue still works for manual posting:
it lists files, order and captions.

## 4. Publish (only on explicit request)

Publishing posts publicly from the user's account, so always confirm with the user first and
start with a dry run:

```bash
$PY "$SKILL_DIR/scripts/reels.py" publish runs/<course> --dry-run
$PY "$SKILL_DIR/scripts/reels.py" publish runs/<course>            # after the user confirms
$PY "$SKILL_DIR/scripts/reels.py" publish runs/<course> --only s03  # retry one item
```

Requirements: an Instagram professional (Business/Creator) account linked to a Facebook
Page, an access token with `instagram_content_publish`, and environment variables
`IG_USER_ID` and `META_ACCESS_TOKEN` (or `IG_ACCESS_TOKEN`); `META_GRAPH_VERSION` is optional.
Results, including API errors, go to `reels_results.json`; re-runs skip published items.
Never ask the user to paste tokens into the chat. They should set them in their shell.

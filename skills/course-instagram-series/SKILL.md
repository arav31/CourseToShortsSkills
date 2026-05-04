---
name: course-instagram-series
description: Use when preparing or publishing a rendered course-shorts series as an Instagram Reels queue with captions, playlist labels, worked examples, questions, and optional Meta Graph API publishing.
---

# Course Instagram Series

## Purpose

Create a publish queue for a course video series, then optionally publish Reels through the Instagram/Meta API when the user has a Business/Creator setup, access token, Instagram user ID, and publicly reachable video URLs.

## Workflow

1. Make sure rendering is complete and `render_report.json` shows finished videos.
2. Create the queue:

```bash
python tools/stem_course.py queue --run runs/<course> --playlist "Course Name"
```

If videos are already hosted at a public base URL, include it so the queue can be published by API:

```bash
python tools/stem_course.py queue --run runs/<course> --playlist "Course Name" --public-base-url "https://cdn.example.com/course/"
```

3. Inspect `runs/<course>/instagram_publish_queue.json`. Captions should include the worked example and active-recall question.
4. Publish only when the user explicitly wants API publishing and has configured:

- `IG_USER_ID`
- `META_ACCESS_TOKEN` or `IG_ACCESS_TOKEN`
- public HTTPS `video_url` values in the queue

Dry-run first:

```bash
python tools/stem_course.py publish --run runs/<course> --dry-run
```

Then publish:

```bash
python tools/stem_course.py publish --run runs/<course>
```

## Important Constraints

- Instagram's API fetches video from a public URL. A local file path is not enough.
- API publishing is for eligible professional accounts and requires the right permissions.
- Treat the queue as the source of truth for captions, order, playlist label, examples, and questions.
- If publishing fails, keep the status and error message in `instagram_publish_results.json`.

## Outputs

- `runs/<course>/instagram_publish_queue.json`
- optional `runs/<course>/instagram_publish_results.json`

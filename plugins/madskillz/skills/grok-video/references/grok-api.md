# xAI Grok Imagine video API

Facts verified 2026-08-10 against https://docs.x.ai/developers/model-capabilities/video/generation.
If requests start failing with schema errors, re-check the docs — the API may have moved.

## Auth

Bearer token from the `XAI_API_KEY` environment variable. The skill checks the key exists
in Phase 0, and `generate.py` checks again before submitting anything. A missing key is a
hard stop with a clear message — never a silent skip.

## Submit

```
POST https://api.x.ai/v1/videos/generations
Authorization: Bearer $XAI_API_KEY
Content-Type: application/json

{
  "model": "grok-imagine-video-1.5",
  "prompt": "<assembled from the brief — see brief-format.md>",
  "duration": 4,
  "aspect_ratio": "16:9",
  "resolution": "480p"
}
```

- `duration` is an integer, 1–15 seconds.
- `resolution`: `480p` | `720p` | `1080p`. `aspect_ratio` default is `16:9`.
- Optional fields exist for `image` (image-to-video), `reference_images`, and
  `reference_audios` (up to 3 voices). v1 of this skill does not use them —
  see `consistency.md` for the seams.

The response is just an id:

```json
{"request_id": "d97415a1-5796-b7ec-379f-4e6819e08fdf"}
```

`generate.py` writes this id into the brief's frontmatter **immediately**, before polling.
If the script crashes mid-poll, a re-run resumes polling the saved id instead of paying
for a second generation.

## Poll

```
GET https://api.x.ai/v1/videos/{request_id}
```

`status` is one of `pending`, `done`, `expired`, `failed`. Generation typically takes up
to several minutes. `generate.py` polls with backoff and gives up after about 10 minutes
per clip, reporting "still pending" with the saved `request_id` so a later run can resume.

A `done` response:

```json
{
  "status": "done",
  "video": {"url": "https://vidgen.x.ai/.../video.mp4", "duration": 4},
  "model": "grok-imagine-video-1.5"
}
```

## Download

`video.url` is a **temporary** URL. Download it right away. `generate.py` retries the
download a few times; if it still fails, the brief is marked `failed` with the reason.
A brief is only ever marked `generated` when a real mp4 exists on disk.

## Failure handling

| Failure | Handling |
|---|---|
| Missing `XAI_API_KEY` | Exit 2 before any submit. |
| Poll returns `failed` or `expired` | Brief → `status: failed`, reason in `error`. Continue other scenes. Nonzero exit. |
| Download fails after retries | Same as above. Never mark `generated` without the file. |
| Poll timeout (~10 min) | Report "still pending" + `request_id`. Re-run resumes polling; it does not resubmit. |
| HTTP error on submit | Report the real status code and body. Do not invent a request id. |

The integrity stance from `promote-study-to-public` applies: never fake a success. If 3 of
5 clips succeed, say exactly that and list the failures with the API's own error text.

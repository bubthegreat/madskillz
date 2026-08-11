# Grok Imagine video API — surface, provenance, and verification

> **This file and `scripts/grok_client.py` are the only places filmcraft knows the API
> wire format.** If xAI changes something, the fix goes here and there — nowhere else.

## Provenance and confidence

The details below come from published documentation. On **2026-08-10** the official docs
page (<https://docs.x.ai/developers/model-capabilities/video/generation>) was read
directly and the table updated. Docs-verified is still not live-verified — no
authenticated call has been made yet, so run the checklist below before the first real
generation.

| Fact | Confidence | Source |
|---|---|---|
| `POST /v1/videos/generations` → `{"request_id": ...}` | **Docs-verified 2026-08-10** | official docs |
| `GET /v1/videos/{request_id}` → `status: pending\|done\|expired\|failed` | **Docs-verified 2026-08-10** | official docs |
| Model `grok-imagine-video-1.5` | **Docs-verified 2026-08-10** | official docs |
| Clip duration 1–15s (integer) | **Docs-verified 2026-08-10** | official docs |
| `resolution`: `480p` (default) / `720p` / `1080p` | **Docs-verified 2026-08-10** | official docs |
| `aspect_ratio`: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3` (default `16:9`) | **Docs-verified 2026-08-10** | official docs — earlier mirror conflict resolved |
| Request keys `image` (image-to-video), `reference_images`, `reference_audios` (max 3) | **Docs-verified 2026-08-10** | official docs; `image_url`/`voice` from mirrors were wrong and are fixed in `build_payload` |
| `done` response: `video.url` is a **temporary** URL — download promptly | **Docs-verified 2026-08-10** | official docs |
| Generation takes up to several minutes per clip | **Docs-verified 2026-08-10** | official docs |
| Native synchronized audio, no surcharge | High | xAI pricing |
| $0.07/sec at 720p | Medium — 1.0 pricing; re-check for 1.5 | DeepLearning.AI, OpenRouter |
| Extend-from-frame adds 6–10s | Medium | 1.5 announcement |
| Request keys `video_url` (extend), `n`, `seed` | **Low — verify first** | mirrors only; not on the docs page read 2026-08-10 |

## Verification checklist — run once, at the start of the first live session

Do this before generating a whole film. It costs one clip.

1. `echo $XAI_API_KEY` — confirm credentials are present.
2. Fetch the live docs: <https://docs.x.ai/developers/model-capabilities/video/generation>
3. Diff the request keys in `grok_client.build_payload` against the documented body.
   Correct any mismatch **in that function only**.
4. Confirm the current per-second price and update `estimate_cost.DEFAULT_VIDEO_RATES`.
5. Generate one 1-second 480p clip — the cheapest possible live call — and confirm:
   - the submit response carries `request_id` (or `id`)
   - polling reaches a terminal `done`
   - `extract_video_urls` finds the output URL in the real response envelope
6. Only then run a full scene.

## The three generation modes filmcraft uses

| Mode in `shots.yaml` | What it does | Continuity strength |
|---|---|---|
| `reference` | Passes locked character plates (and optionally a voice ref) | **Strongest** — the default for any shot with a character in it |
| `extend` | Continues a previous clip from its final frame | Strong within a chain, but drift compounds per hop — capped by `max_extend_chain` |
| `image` | Animates a specific still | Strong, but you must supply the still |
| `text` | Prompt only | Weakest — use only for establishing shots with no recurring subject |

**Rule of thumb:** any shot containing a recurring character should be `reference`, never
`text`. `text` mode re-rolls the casting every call.

## Response envelope

Response shapes drift more than request shapes do, so `extract_video_urls` walks the whole
structure looking for `url` / `video_url` / `output_url` keys rather than asserting one
path. If a future response nests URLs under a new key, add it to that function's tuple.

Terminal statuses: `done` / `succeeded` / `completed` (success);
`failed` / `expired` / `cancelled` (failure). Anything else is treated as still pending
and polled until `timeout`.

## Cost model

Billing is per second of **generated** output, not per second of finished film. Takes
multiply cost: three takes of an 8-second shot bills 24 seconds regardless of how much
ends up in the cut.

```
cost = duration × takes × rate_per_second
```

At $0.07/sec (720p):

| Project | Shots | Takes | Generated seconds | Cost |
|---|---|---|---|---|
| Single scene | 10 | 3 | 240 | ~$17 |
| 3-minute short | 30 | 3 | 720 | ~$50 |
| 10-minute short | 100 | 3 | 2,400 | ~$168 |
| 90-minute feature | 900 | 3 | 21,600 | ~$1,500 |

Dropping to 480p for previz and re-generating selects at 720p is the standard way to
halve the bill on a first pass.

## Rate limits and failure handling

Rate limits are account-tier dependent and not documented here. `generate.py` generates
shots sequentially rather than fanning out, which keeps well under any published tier and
makes failures easy to attribute. If a live session hits 429s, add backoff in
`grok_client.poll` / `submit` — again, that file only.

Generation failures are logged to `generated/generation-log.jsonl` with the real error and
a `cost_usd` of 0, then the run continues with remaining shots. Never retry blindly in a
loop: a content-policy rejection will fail identically every time and burn the budget.

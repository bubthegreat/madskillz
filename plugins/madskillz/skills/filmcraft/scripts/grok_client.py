# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Thin xAI video-generation adapter — the ONLY file that knows the wire format.

Everything filmcraft believes about the Grok Imagine API lives here and in
`references/grok-api.md`. If xAI renames a parameter or moves an endpoint, this file
is the whole blast radius; no other script constructs a request.

Transport is injectable so the full pipeline is testable without an API key.

Stdlib only (urllib) — no SDK dependency, so an SDK version bump cannot break a render.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai")
SUBMIT_PATH = "/v1/videos/generations"
EXTEND_PATH = "/v1/videos/extensions"
POLL_PATH = "/v1/videos/{request_id}"

DEFAULT_MODEL = "grok-imagine-video-1.5"
EXTEND_MODEL = "grok-imagine-video"  # 1.5 refuses extension (live-verified 2026-08-10)

TERMINAL_OK = frozenset({"done", "succeeded", "completed"})
TERMINAL_FAIL = frozenset({"failed", "expired", "cancelled", "canceled"})


class MissingAPIKey(RuntimeError):
    """Raised when generation is attempted with no credentials configured."""


class GenerationFailed(RuntimeError):
    """Raised when the service reports a terminal failure for a request."""


class Transport(Protocol):
    def __call__(self, method: str, url: str, body: dict | None, headers: dict) -> dict: ...


def http_transport(method: str, url: str, body: dict | None, headers: dict) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise GenerationFailed(f"HTTP {exc.code} from {url}: {detail}") from exc


def build_payload(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    duration: int | None = None,
    resolution: str | None = None,
    aspect_ratio: str | None = None,
    image_url: str | None = None,
    reference_images: list[str] | None = None,
    voice: str | None = None,
    n: int | None = None,
    seed: int | None = None,
) -> dict:
    """Assemble a generation request.

    Key names checked against the published docs at
    https://docs.x.ai/developers/model-capabilities/video/generation on 2026-08-10:
    `model`, `prompt`, `duration` (1-15), `aspect_ratio`, `resolution`,
    `image` (image-to-video), `reference_images`, `reference_audios` (max 3).
    `video_url`, `n`, and `seed` did not appear in that page — still unverified;
    confirm on the first live run and correct here, the single point of truth.
    """
    payload: dict[str, Any] = {"model": model, "prompt": prompt}
    if duration is not None:
        payload["duration"] = duration
    if resolution is not None:
        payload["resolution"] = resolution
    if aspect_ratio is not None:
        payload["aspect_ratio"] = aspect_ratio
    if image_url is not None:
        payload["image"] = image_url              # image-to-video (docs: `image`)
    if reference_images:
        payload["reference_images"] = reference_images  # reference-to-video
    if voice is not None:
        payload["reference_audios"] = [voice]     # docs: list, max 3 voices
    if n is not None:
        payload["n"] = n                          # takes: n seeds, one call — UNVERIFIED
    if seed is not None:
        payload["seed"] = seed                    # UNVERIFIED
    return payload


def build_extend_payload(
    prompt: str,
    video: str,
    *,
    model: str = EXTEND_MODEL,
    duration: int | None = None,
) -> dict:
    """Assemble an extension request for `POST /v1/videos/extensions`.

    Live-verified 2026-08-10: the `video` field is a struct — a bare URL string
    is rejected with `expected struct VideoUrl` (HTTP 422) — and the model must
    be `grok-imagine-video`; `grok-imagine-video-1.5` answers "Video extension
    is not supported for this model" (HTTP 400). Pass the previous generation's
    delivered video URL (docs also allow base64 data URI or file_id). Per docs,
    `duration` controls the length of the extended portion only. The extension
    starts from the source clip's final frame.
    """
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "video": {"url": video}}
    if duration is not None:
        payload["duration"] = duration
    return payload


def fetch_binary(url: str) -> bytes:
    """Download a delivered clip. Output URLs are temporary — fetch promptly."""
    with urllib.request.urlopen(url) as resp:
        return resp.read()


def extract_video_urls(result: dict) -> list[str]:
    """Pull output URLs out of a completed response, tolerating shape drift.

    Response envelopes vary more than request shapes do, so this searches the common
    containers rather than asserting one.
    """
    urls: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("url", "video_url", "output_url"):
                val = node.get(key)
                if isinstance(val, str) and val.startswith(("http://", "https://")):
                    urls.append(val)
            for val in node.values():
                walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(result)
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(urls))


@dataclass
class GrokVideoClient:
    """Submit-and-poll client for xAI video generation."""

    api_key: str | None = None
    model: str = DEFAULT_MODEL
    base_url: str = BASE_URL
    transport: Transport = http_transport
    poll_interval: float = 5.0
    timeout: float = 600.0
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], float] = time.monotonic
    _log: list[dict] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")

    @property
    def available(self) -> bool:
        """True when credentials exist. False routes the skill to the paste-packet path."""
        return bool(self.api_key)

    def _headers(self) -> dict:
        if not self.api_key:
            raise MissingAPIKey(
                "Neither XAI_API_KEY nor GROK_API_KEY is set. Export one, or run the "
                "skill in packet mode to "
                "produce paste-ready prompts instead."
            )
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def submit(self, payload: dict, path: str = SUBMIT_PATH) -> str:
        resp = self.transport("POST", f"{self.base_url}{path}", payload, self._headers())
        request_id = resp.get("request_id") or resp.get("id")
        if not request_id:
            raise GenerationFailed(f"No request_id in submit response: {json.dumps(resp)[:300]}")
        return request_id

    def submit_extend(self, payload: dict) -> str:
        return self.submit(payload, path=EXTEND_PATH)

    def poll_once(self, request_id: str) -> dict:
        """Single status check — for callers that manage their own resume loop."""
        url = f"{self.base_url}{POLL_PATH.format(request_id=request_id)}"
        return self.transport("GET", url, None, self._headers())

    def poll(self, request_id: str) -> dict:
        url = f"{self.base_url}{POLL_PATH.format(request_id=request_id)}"
        deadline = self.now() + self.timeout
        while True:
            resp = self.transport("GET", url, None, self._headers())
            status = str(resp.get("status", "")).lower()
            if status in TERMINAL_OK:
                return resp
            if status in TERMINAL_FAIL:
                raise GenerationFailed(
                    f"Request {request_id} ended as {status}: {resp.get('error') or 'no detail given'}"
                )
            if self.now() >= deadline:
                raise GenerationFailed(
                    f"Request {request_id} still {status or 'pending'} after {self.timeout}s."
                )
            self.sleep(self.poll_interval)

    def generate(self, prompt: str, **kwargs: Any) -> dict:
        """Submit a generation and block until it completes."""
        payload = build_payload(prompt, model=kwargs.pop("model", self.model), **kwargs)
        request_id = self.submit(payload)
        result = self.poll(request_id)
        record = {
            "request_id": request_id,
            "status": "done",
            "urls": extract_video_urls(result),
            "payload": payload,
        }
        self._log.append(record)
        return record

    def extend(self, source_video: str, prompt: str,
               duration: int | None = None, **kwargs: Any) -> dict:
        """Continue an existing clip from its final frame.

        `source_video` must be a delivered (still-valid, temporary) video URL
        from a prior generation. Always uses EXTEND_MODEL unless overridden —
        the session model (1.5) does not support extension.
        """
        payload = build_extend_payload(prompt, source_video,
                                       model=kwargs.pop("model", EXTEND_MODEL),
                                       duration=duration)
        request_id = self.submit_extend(payload)
        result = self.poll(request_id)
        record = {
            "request_id": request_id,
            "status": "done",
            "urls": extract_video_urls(result),
            "payload": payload,
        }
        self._log.append(record)
        return record

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
POLL_PATH = "/v1/videos/{request_id}"

DEFAULT_MODEL = "grok-imagine-video-1.5"

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
    source_video: str | None = None,
    n: int | None = None,
    seed: int | None = None,
) -> dict:
    """Assemble a generation request.

    ---------------------------------------------------------------------------
    VERIFY BEFORE FIRST LIVE RUN. These key names are taken from published docs and
    third-party mirrors, not from an authenticated call. Confirm each against
    https://docs.x.ai/developers/model-capabilities/video/generation and correct
    here — this function is the single point of truth.
    ---------------------------------------------------------------------------
    """
    payload: dict[str, Any] = {"model": model, "prompt": prompt}
    if duration is not None:
        payload["duration"] = duration
    if resolution is not None:
        payload["resolution"] = resolution
    if aspect_ratio is not None:
        payload["aspect_ratio"] = aspect_ratio
    if image_url is not None:
        payload["image_url"] = image_url          # image-to-video
    if reference_images:
        payload["reference_images"] = reference_images  # reference-to-video
    if voice is not None:
        payload["voice"] = voice
    if source_video is not None:
        payload["video_url"] = source_video       # extend-from-frame
    if n is not None:
        payload["n"] = n                          # takes: n seeds, one call
    if seed is not None:
        payload["seed"] = seed
    return payload


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
            self.api_key = os.environ.get("XAI_API_KEY")

    @property
    def available(self) -> bool:
        """True when credentials exist. False routes the skill to the paste-packet path."""
        return bool(self.api_key)

    def _headers(self) -> dict:
        if not self.api_key:
            raise MissingAPIKey(
                "XAI_API_KEY is not set. Export it, or run the skill in packet mode to "
                "produce paste-ready prompts instead."
            )
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def submit(self, payload: dict) -> str:
        resp = self.transport("POST", f"{self.base_url}{SUBMIT_PATH}", payload, self._headers())
        request_id = resp.get("request_id") or resp.get("id")
        if not request_id:
            raise GenerationFailed(f"No request_id in submit response: {json.dumps(resp)[:300]}")
        return request_id

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

    def extend(self, source_video: str, prompt: str, **kwargs: Any) -> dict:
        """Continue an existing clip from its final frame."""
        return self.generate(prompt, source_video=source_video, **kwargs)

"""The live generation path, exercised with a fake transport and no API key."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import grok_client as gc  # noqa: E402


class FakeTransport:
    """Records calls and replays a scripted sequence of poll responses."""

    def __init__(self, poll_responses, submit_response=None):
        self.poll_responses = list(poll_responses)
        self.submit_response = submit_response or {"request_id": "req_123"}
        self.calls = []

    def __call__(self, method, url, body, headers):
        self.calls.append({"method": method, "url": url, "body": body})
        if method == "POST":
            return self.submit_response
        return self.poll_responses.pop(0)


def client(transport, **kw):
    return gc.GrokVideoClient(api_key="test-key", transport=transport,
                              sleep=lambda _: None, poll_interval=0, **kw)


DONE = {"status": "done", "video": {"url": "https://cdn.example/clip.mp4"}}


def test_generate_submits_then_polls_until_done():
    t = FakeTransport([{"status": "pending"}, {"status": "processing"}, DONE])
    result = client(t).generate("a wide shot of rain", duration=8)

    assert result["urls"] == ["https://cdn.example/clip.mp4"]
    assert t.calls[0]["method"] == "POST"
    assert t.calls[0]["url"].endswith("/v1/videos/generations")
    assert all(c["method"] == "GET" for c in t.calls[1:])
    assert t.calls[1]["url"].endswith("/v1/videos/req_123")


def test_terminal_failure_raises_with_detail():
    t = FakeTransport([{"status": "failed", "error": "content policy"}])
    with pytest.raises(gc.GenerationFailed, match="content policy"):
        client(t).generate("something")


def test_expired_status_is_terminal():
    t = FakeTransport([{"status": "expired"}])
    with pytest.raises(gc.GenerationFailed, match="expired"):
        client(t).generate("something")


def test_polling_times_out_rather_than_looping_forever():
    ticks = iter([0, 1, 2, 999])
    t = FakeTransport([{"status": "pending"}] * 10)
    c = gc.GrokVideoClient(api_key="k", transport=t, sleep=lambda _: None,
                           poll_interval=0, timeout=100, now=lambda: next(ticks))
    with pytest.raises(gc.GenerationFailed, match="still pending"):
        c.generate("something")


def test_missing_request_id_is_an_error():
    t = FakeTransport([DONE], submit_response={"nope": True})
    with pytest.raises(gc.GenerationFailed, match="No request_id"):
        client(t).generate("something")


def test_no_api_key_reports_available_false_and_refuses_to_call():
    c = gc.GrokVideoClient(api_key="", transport=FakeTransport([]))
    assert c.available is False
    with pytest.raises(gc.MissingAPIKey, match="XAI_API_KEY"):
        c.generate("something")


def test_api_key_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "from-env")
    assert gc.GrokVideoClient().available is True


def test_grok_api_key_accepted_as_fallback(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_KEY", "from-grok-env")
    c = gc.GrokVideoClient()
    assert c.available is True
    assert c.api_key == "from-grok-env"


def test_extend_uses_extensions_endpoint_with_video_field():
    t = FakeTransport([DONE])
    client(t).extend("https://cdn.example/prev.mp4", "she goes still")
    assert t.calls[0]["url"].endswith("/v1/videos/extensions")
    # Live-verified: bare string is rejected with `expected struct VideoUrl`.
    assert t.calls[0]["body"]["video"] == {"url": "https://cdn.example/prev.mp4"}
    assert t.calls[0]["body"]["prompt"] == "she goes still"
    assert "duration" not in t.calls[0]["body"]  # extensions take no override


def test_build_payload_omits_unset_options():
    payload = gc.build_payload("a shot", duration=8)
    assert payload == {"model": gc.DEFAULT_MODEL, "prompt": "a shot", "duration": 8}


def test_build_payload_carries_reference_and_voice():
    payload = gc.build_payload("a shot", reference_images=["p.png"], voice="v.wav", n=3)
    assert payload["reference_images"] == ["p.png"]
    assert payload["reference_audios"] == ["v.wav"]  # docs-verified wire key
    assert payload["n"] == 3


def test_build_payload_image_uses_docs_verified_key():
    payload = gc.build_payload("a shot", image_url="frame.png")
    assert payload["image"] == "frame.png"
    assert "image_url" not in payload


def test_extract_video_urls_finds_nested_and_deduplicates():
    resp = {"status": "done", "outputs": [
        {"video_url": "https://a/1.mp4"},
        {"nested": {"url": "https://a/2.mp4"}},
        {"video_url": "https://a/1.mp4"},
    ]}
    assert gc.extract_video_urls(resp) == ["https://a/1.mp4", "https://a/2.mp4"]


def test_extract_video_urls_ignores_non_http_values():
    assert gc.extract_video_urls({"url": "not-a-url", "status": "done"}) == []


def test_authorization_header_is_sent():
    t = FakeTransport([DONE])
    client(t).generate("x")
    # FakeTransport does not capture headers; assert construction directly instead.
    assert gc.GrokVideoClient(api_key="abc")._headers()["Authorization"] == "Bearer abc"

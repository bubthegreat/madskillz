import pathlib
import shutil
import sys

import httpx
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import generate

FIX = pathlib.Path(__file__).parent / "fixtures" / "tinybook"


@pytest.fixture
def book(tmp_path):
    dst = tmp_path / "tinybook"
    shutil.copytree(FIX, dst)
    return dst


def set_status(brief_path, status, request_id=""):
    front, body = generate.parse_brief(brief_path)
    front["status"] = status
    front["request_id"] = request_id
    generate.write_brief(brief_path, front, body)


def approve(book, name="01-brief.md"):
    p = book / "video" / "01-the-sneeze" / name
    set_status(p, "approved")
    return p


class FakeAPI:
    """Mock transport handler: submit -> poll (pending, then done) -> download."""

    def __init__(self, poll_statuses=("pending", "done"), download_ok=True):
        self.poll_statuses = list(poll_statuses)
        self.download_ok = download_ok
        self.submits = 0
        self.polls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/v1/videos/generations":
            self.submits += 1
            return httpx.Response(200, json={"request_id": f"req-{self.submits}"})
        if request.method == "GET" and path.startswith("/v1/videos/"):
            status = self.poll_statuses[min(self.polls, len(self.poll_statuses) - 1)]
            self.polls += 1
            body = {"status": status}
            if status == "done":
                body["video"] = {"url": "https://vidgen.test/files/clip.mp4", "duration": 4}
            if status == "failed":
                body["error"] = "moderation block"
            return httpx.Response(200, json=body)
        if path == "/files/clip.mp4":
            if self.download_ok:
                return httpx.Response(200, content=b"FAKEMP4")
            return httpx.Response(403)
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    def client(self):
        return httpx.Client(
            base_url="https://api.test", transport=httpx.MockTransport(self)
        )


def run(book, api, **kw):
    kw.setdefault("sleep", lambda s: None)
    with api.client() as client:
        return generate.process(book, client=client, **kw)


def test_parse_brief_reads_frontmatter_and_sections(book):
    front, body = generate.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    assert front["status"] == "draft"
    assert front["duration"] == 4
    sections = generate.parse_sections(body)
    assert sections["Scene"].startswith("Pip creeps")
    assert "Morg" in sections["What NOT to show"]


def test_assemble_prompt_order_and_not_prefix(book):
    style = "STYLEBLOCK"
    _, body = generate.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    prompt = generate.assemble_prompt(style, generate.parse_sections(body))
    assert prompt.startswith("STYLEBLOCK")
    assert prompt.index("Pip creeps") < prompt.index("Slow push-in")
    assert "Do not show: Do not show Morg" not in prompt  # no double prefixing
    assert "Do not show Morg or the burrow." in prompt
    # A NOT section without its own prefix gets one added.
    plain = generate.assemble_prompt("S", {"Scene": "x", "What NOT to show": "the cave"})
    assert "Do not show: the cave" in plain


def test_only_approved_briefs_selected(book):
    approve(book, "01-brief.md")  # 02 stays draft
    todo = generate.select_briefs(book)
    assert [p.name for p in todo] == ["01-brief.md"]


def test_dry_run_touches_nothing(book, capsys):
    approve(book)
    api = FakeAPI()
    rc = run(book, api, dry_run=True)
    assert rc == 0
    assert api.submits == 0
    out = capsys.readouterr().out
    assert "Pip creeps" in out
    front, _ = generate.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    assert front["status"] == "approved"


def test_success_flow_writes_mp4_and_flips_status(book):
    brief = approve(book)
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 0
    mp4 = book / "video" / "01-the-sneeze" / "01.mp4"
    assert mp4.read_bytes() == b"FAKEMP4"
    front, _ = generate.parse_brief(brief)
    assert front["status"] == "generated"
    assert front["request_id"] == "req-1"


def test_failed_poll_marks_failed_and_nonzero_exit(book):
    brief = approve(book)
    api = FakeAPI(poll_statuses=("failed",))
    rc = run(book, api)
    assert rc == 1
    front, _ = generate.parse_brief(brief)
    assert front["status"] == "failed"
    assert "moderation block" in front["error"]
    assert not (book / "video" / "01-the-sneeze" / "01.mp4").exists()


def test_download_failure_marks_failed_without_mp4(book):
    brief = approve(book)
    api = FakeAPI(download_ok=False)
    rc = run(book, api)
    assert rc == 1
    front, _ = generate.parse_brief(brief)
    assert front["status"] == "failed"
    assert not (book / "video" / "01-the-sneeze" / "01.mp4").exists()


def test_idempotent_skips_generated(book):
    brief = approve(book)
    set_status(brief, "generated", request_id="req-old")
    (book / "video" / "01-the-sneeze" / "01.mp4").write_bytes(b"OLD")
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 0
    assert api.submits == 0 and api.polls == 0
    assert (book / "video" / "01-the-sneeze" / "01.mp4").read_bytes() == b"OLD"


def test_resume_polls_saved_request_id_without_resubmit(book):
    brief = approve(book)
    set_status(brief, "approved", request_id="req-old")
    api = FakeAPI(poll_statuses=("done",))
    rc = run(book, api)
    assert rc == 0
    assert api.submits == 0
    assert api.polls >= 1
    front, _ = generate.parse_brief(brief)
    assert front["status"] == "generated"


def test_max_clips_caps_submissions(book):
    approve(book, "01-brief.md")
    approve(book, "02-brief.md")
    api = FakeAPI()
    rc = run(book, api, max_clips=1)
    assert rc == 0
    assert api.submits == 1


def test_missing_key_exits_2(book, monkeypatch, capsys):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    rc = generate.main(["generate.py", str(book)])
    assert rc == 2
    assert "XAI_API_KEY" in capsys.readouterr().err


def test_poll_timeout_reports_pending(book):
    brief = approve(book)
    api = FakeAPI(poll_statuses=("pending",))
    rc = run(book, api, poll_timeout=0)
    assert rc == 1
    front, _ = generate.parse_brief(brief)
    assert front["status"] == "approved"  # still resumable
    assert front["request_id"] == "req-1"

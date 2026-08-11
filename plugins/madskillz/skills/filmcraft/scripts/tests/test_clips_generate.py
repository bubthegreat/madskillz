import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import clips_generate as cg
from grok_client import GenerationFailed, GrokVideoClient

FIX = pathlib.Path(__file__).parent / "fixtures" / "tinybook"


@pytest.fixture
def book(tmp_path):
    dst = tmp_path / "tinybook"
    shutil.copytree(FIX, dst)
    return dst


def set_status(brief_path, status, request_id=""):
    front, body = cg.parse_brief(brief_path)
    front["status"] = status
    front["request_id"] = request_id
    cg.write_brief(brief_path, front, body)


def approve(book, name="01-brief.md"):
    p = book / "video" / "01-the-sneeze" / name
    set_status(p, "approved")
    return p


class FakeAPI:
    """Fake grok_client transport: submit -> poll (pending, then done) -> download."""

    def __init__(self, poll_statuses=("pending", "done"), download_ok=True,
                 submit_error=None):
        self.poll_statuses = list(poll_statuses)
        self.download_ok = download_ok
        self.submit_error = submit_error
        self.submits = 0
        self.polls = 0
        self.fetches = 0
        self.submitted = []

    def transport(self, method, url, body, headers):
        assert headers.get("Authorization") == "Bearer test-key"
        if method == "POST" and url.endswith(("/v1/videos/generations",
                                             "/v1/videos/extensions")):
            if self.submit_error:
                raise GenerationFailed(self.submit_error)
            self.submits += 1
            self.submitted.append({"url": url, "body": body})
            return {"request_id": f"req-{self.submits}"}
        if method == "GET" and "/v1/videos/" in url:
            status = self.poll_statuses[min(self.polls, len(self.poll_statuses) - 1)]
            self.polls += 1
            resp = {"status": status}
            if status == "done":
                resp["video"] = {"url": "https://vidgen.test/files/clip.mp4", "duration": 4}
            if status == "failed":
                resp["error"] = "moderation block"
            return resp
        raise AssertionError(f"unexpected request {method} {url}")

    def fetch(self, url):
        self.fetches += 1
        if not self.download_ok:
            raise OSError("403 forbidden")
        return b"FAKEMP4"

    def client(self):
        return GrokVideoClient(api_key="test-key", transport=self.transport)


def run(book, api, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("fetch", api.fetch)
    return cg.process(book, client=api.client(), **kw)


def test_parse_brief_reads_frontmatter_and_sections(book):
    front, body = cg.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    assert front["status"] == "draft"
    assert front["duration"] == 4
    sections = cg.parse_sections(body)
    assert sections["Scene"].startswith("Pip creeps")
    assert "Morg" in sections["What NOT to show"]


def test_assemble_prompt_order_and_not_prefix(book):
    style = "STYLEBLOCK"
    _, body = cg.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    prompt = cg.assemble_prompt(style, cg.parse_sections(body))
    assert prompt.startswith("STYLEBLOCK")
    assert prompt.index("Pip creeps") < prompt.index("Slow push-in")
    assert "Do not show: Do not show Morg" not in prompt  # no double prefixing
    assert "Do not show Morg or the burrow." in prompt
    # A NOT section without its own prefix gets one added.
    plain = cg.assemble_prompt("S", {"Scene": "x", "What NOT to show": "the cave"})
    assert "Do not show: the cave" in plain


def test_only_approved_briefs_selected(book):
    approve(book, "01-brief.md")  # 02 stays draft
    todo, malformed = cg.select_briefs(book)
    assert [p.name for p in todo] == ["01-brief.md"]
    assert malformed == []


def test_malformed_brief_reported_not_crashing(book, capsys):
    approve(book, "01-brief.md")
    bad = book / "video" / "01-the-sneeze" / "02-brief.md"
    bad.write_text("---\nstatus: approved\n## Scene\nno closing fence")
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 1
    assert "malformed brief skipped" in capsys.readouterr().err
    assert api.submits == 1  # the good brief still generated
    assert (book / "video" / "01-the-sneeze" / "01.mp4").exists()


def test_dry_run_touches_nothing(book, capsys):
    approve(book)
    api = FakeAPI()
    rc = run(book, api, dry_run=True)
    assert rc == 0
    assert api.submits == 0
    out = capsys.readouterr().out
    assert "Pip creeps" in out
    front, _ = cg.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    assert front["status"] == "approved"


def test_success_flow_writes_mp4_and_flips_status(book):
    brief = approve(book)
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 0
    mp4 = book / "video" / "01-the-sneeze" / "01.mp4"
    assert mp4.read_bytes() == b"FAKEMP4"
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "generated"
    assert front["request_id"] == "req-1"


def test_failed_poll_marks_failed_and_nonzero_exit(book):
    brief = approve(book)
    api = FakeAPI(poll_statuses=("failed",))
    rc = run(book, api)
    assert rc == 1
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "failed"
    assert "moderation block" in front["error"]
    assert not (book / "video" / "01-the-sneeze" / "01.mp4").exists()


def test_submit_error_marks_failed(book):
    brief = approve(book)
    api = FakeAPI(submit_error="HTTP 500 from submit: server exploded")
    rc = run(book, api)
    assert rc == 1
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "failed"
    assert "500" in front["error"]


def test_download_failure_marks_failed_without_mp4(book):
    brief = approve(book)
    api = FakeAPI(download_ok=False)
    rc = run(book, api)
    assert rc == 1
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "failed"
    assert "403" in front["error"]
    assert not (book / "video" / "01-the-sneeze" / "01.mp4").exists()


def test_disk_write_error_marks_failed(book, monkeypatch):
    import pathlib as _pl

    brief = approve(book)
    orig = _pl.Path.write_bytes

    def flaky(self, data):
        if self.suffix == ".mp4":
            raise OSError("disk full")
        return orig(self, data)

    monkeypatch.setattr(_pl.Path, "write_bytes", flaky)
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 1
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "failed"
    assert "disk full" in front["error"]


def test_idempotent_skips_generated(book):
    brief = approve(book)
    set_status(brief, "generated", request_id="req-old")
    (book / "video" / "01-the-sneeze" / "01.mp4").write_bytes(b"OLD")
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 0
    assert api.submits == 0  # never regenerates; chain-recovery re-poll is a free GET
    assert (book / "video" / "01-the-sneeze" / "01.mp4").read_bytes() == b"OLD"


def test_resume_polls_saved_request_id_without_resubmit(book):
    brief = approve(book)
    set_status(brief, "approved", request_id="req-old")
    api = FakeAPI(poll_statuses=("done",))
    rc = run(book, api)
    assert rc == 0
    assert api.submits == 0
    assert api.polls >= 1
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "generated"


def test_chain_second_brief_extends_first(book):
    approve(book, "01-brief.md")
    approve(book, "02-brief.md")
    api = FakeAPI()
    rc = run(book, api)
    assert rc == 0
    assert api.submits == 2
    assert api.submitted[0]["url"].endswith("/v1/videos/generations")
    assert api.submitted[1]["url"].endswith("/v1/videos/extensions")
    # Live-verified: the API wants a VideoUrl struct, not a bare string.
    assert api.submitted[1]["body"]["video"] == {"url": "https://vidgen.test/files/clip.mp4"}
    f1, _ = cg.parse_brief(book / "video" / "01-the-sneeze" / "01-brief.md")
    f2, _ = cg.parse_brief(book / "video" / "01-the-sneeze" / "02-brief.md")
    assert f1["mode"] == "fresh"
    assert f2["mode"] == "extend"
    # Cumulative extension: the last segment is copied out as the film.
    assert (book / "video" / "tinybook.mp4").read_bytes() == b"FAKEMP4"


def test_independent_flag_disables_chaining(book):
    approve(book, "01-brief.md")
    approve(book, "02-brief.md")
    api = FakeAPI()
    rc = run(book, api, independent=True)
    assert rc == 0
    assert all(s["url"].endswith("/v1/videos/generations") for s in api.submitted)


def test_chain_breaks_on_failure(book):
    approve(book, "01-brief.md")
    approve(book, "02-brief.md")
    api = FakeAPI(poll_statuses=("failed",))
    rc = run(book, api)
    assert rc == 1
    assert api.submits == 1  # second scene never attempted
    f2, _ = cg.parse_brief(book / "video" / "01-the-sneeze" / "02-brief.md")
    assert f2["status"] == "approved"  # untouched, retryable


def test_already_generated_brief_recovers_chain_via_repoll(book):
    b1 = approve(book, "01-brief.md")
    set_status(b1, "generated", request_id="req-old")
    (book / "video" / "01-the-sneeze" / "01.mp4").write_bytes(b"OLD")
    approve(book, "02-brief.md")
    api = FakeAPI(poll_statuses=("done",))  # re-poll of req-old still says done
    rc = run(book, api)
    assert rc == 0
    assert api.submits == 1
    # URL recovered from the old request id → scene 2 extends instead of fresh.
    assert api.submitted[0]["url"].endswith("/v1/videos/extensions")
    assert api.submitted[0]["body"]["video"] == {"url": "https://vidgen.test/files/clip.mp4"}


def test_already_generated_brief_restarts_fresh_when_url_gone(book):
    b1 = approve(book, "01-brief.md")
    set_status(b1, "generated", request_id="req-old")
    (book / "video" / "01-the-sneeze" / "01.mp4").write_bytes(b"OLD")
    approve(book, "02-brief.md")
    # First GET: re-poll of req-old is expired. Second GET: scene 2's own poll.
    api = FakeAPI(poll_statuses=("expired", "done"))
    rc = run(book, api)
    assert rc == 0
    assert api.submitted[0]["url"].endswith("/v1/videos/generations")  # fresh restart


def test_max_clips_caps_submissions(book):
    approve(book, "01-brief.md")
    approve(book, "02-brief.md")
    api = FakeAPI()
    rc = run(book, api, max_clips=1)
    assert rc == 0
    assert api.submits == 1


def test_missing_key_exits_2(book, monkeypatch, capsys):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    rc = cg.main(["clips_generate.py", str(book)])
    assert rc == 2
    assert "XAI_API_KEY" in capsys.readouterr().err


def test_poll_timeout_reports_pending(book):
    brief = approve(book)
    api = FakeAPI(poll_statuses=("pending",))
    rc = run(book, api, poll_timeout=0)
    assert rc == 1
    front, _ = cg.parse_brief(brief)
    assert front["status"] == "approved"  # still resumable
    assert front["request_id"] == "req-1"

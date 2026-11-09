"""Typefully publish scripts: mocked HTTP, input validation, no network."""
import io
import json
import urllib.error

import pytest

API = "https://api.typefully.com/v2/social-sets/set1/drafts"


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeTypefully:
    """Records requests; answers by method+call count."""

    def __init__(self, post=None, gets=None, post_error=None, get_error=None):
        self.post_payload = post or {"id": "d1", "publish_state": "queued"}
        self.gets = gets or [
            {
                "publish_state": "finished",
                "x_published_url": "https://x.com/ok",
                "status": "published",
            }
        ]
        self.post_error = post_error
        self.get_error = get_error
        self.calls = []
        self.get_i = 0

    def __call__(self, req, timeout=60):
        self.calls.append(req)
        if req.data is not None:  # POST
            self.last_post = json.loads(req.data.decode("utf-8"))
            if self.post_error:
                raise self.post_error
            return FakeResp(self.post_payload)
        if self.get_error:
            raise self.get_error
        body = self.gets[min(self.get_i, len(self.gets) - 1)]
        self.get_i += 1
        return FakeResp(body)


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("YOUR_TYPEFULLY_API_KEY", "test-key")
    monkeypatch.setenv("YOUR_TYPEFULLY_SOCIAL_SET_ID", "set1")
    monkeypatch.delenv("X_MADE_WITH_AI", raising=False)
    monkeypatch.setattr("sys.argv", ["prog"])
    return monkeypatch


def run_publish(pub, monkeypatch, ft, *extra):
    monkeypatch.setattr(pub.urllib.request, "urlopen", ft)
    monkeypatch.setattr(pub.time, "sleep", lambda s: None)
    monkeypatch.setattr("sys.argv", ["prog", "--text", "hello niche world", *extra])
    return pub.main()


def test_publish_happy_path(pub, env, monkeypatch, capsys):
    ft = FakeTypefully()
    rc = run_publish(pub, monkeypatch, ft)
    assert rc == 0
    assert ft.last_post["platforms"]["x"]["settings"]["made_with_ai"] is False
    assert ft.last_post["publish_at"] == "now"
    out = capsys.readouterr().out
    assert "x_published_url" in out


def test_publish_made_with_ai_is_operators_choice(pub, env, monkeypatch):
    env.setenv("X_MADE_WITH_AI", "true")
    ft = FakeTypefully()
    assert run_publish(pub, monkeypatch, ft) == 0
    assert ft.last_post["platforms"]["x"]["settings"]["made_with_ai"] is True


def test_publish_empty_text_refused(pub, env, monkeypatch):
    monkeypatch.setattr("sys.argv", ["prog", "--text", "   "])
    with pytest.raises(SystemExit) as e:
        pub.main()
    assert e.value.code == 2


def test_publish_over_limit_refused_with_clear_error(pub, env, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["prog", "--text", "x" * 300])
    with pytest.raises(SystemExit) as e:
        pub.main()
    assert e.value.code == 2
    assert "280" in capsys.readouterr().err


def test_publish_allow_long_overrides_limit(pub, env, monkeypatch):
    ft = FakeTypefully()
    rc = run_publish(pub, monkeypatch, ft, "--allow-long")
    assert rc == 0


def test_publish_missing_key_exit_2(pub, env, monkeypatch):
    env.delenv("YOUR_TYPEFULLY_API_KEY")
    monkeypatch.setattr("sys.argv", ["prog", "--text", "hi"])
    with pytest.raises(SystemExit) as e:
        pub.main()
    assert e.value.code == 2


def test_publish_placeholder_social_set(pub, env, monkeypatch):
    env.setenv("YOUR_TYPEFULLY_SOCIAL_SET_ID", "YOUR_SOCIAL_SET_ID")
    monkeypatch.setattr("sys.argv", ["prog", "--text", "hi"])
    assert pub.main() == 2


def test_publish_http_error_clean_message(pub, env, monkeypatch, capsys):
    err = urllib.error.HTTPError(API, 401, "bad key", {}, io.BytesIO(b"unauthorized"))
    with pytest.raises(SystemExit) as e:
        run_publish(pub, monkeypatch, FakeTypefully(post_error=err))
    assert e.value.code == 1
    assert "401" in capsys.readouterr().err


def test_publish_network_error_no_traceback(pub, env, monkeypatch, capsys):
    err = urllib.error.URLError("name resolution failed")
    with pytest.raises(SystemExit) as e:
        run_publish(pub, monkeypatch, FakeTypefully(post_error=err))
    assert e.value.code == 1
    assert "cannot reach Typefully" in capsys.readouterr().err


def test_publish_poll_timeout_reports_pending_not_failure(pub, env, monkeypatch, capsys):
    ft = FakeTypefully(gets=[{"publish_state": "publishing"}])
    rc = run_publish(pub, monkeypatch, ft)
    assert rc == 4
    assert "not confirmed" in capsys.readouterr().err
    assert ft.get_i >= 1


def test_publish_poll_failed_state(pub, env, monkeypatch, capsys):
    ft = FakeTypefully(gets=[{"publish_state": "failed"}])
    rc = run_publish(pub, monkeypatch, ft)
    assert rc == 1
    assert "failed" in capsys.readouterr().err


def test_publish_no_wait_skips_polling(pub, env, monkeypatch):
    ft = FakeTypefully()
    rc = run_publish(pub, monkeypatch, ft, "--no-wait")
    assert rc == 0
    assert len(ft.calls) == 1


def test_publish_response_without_draft_id(pub, env, monkeypatch, capsys):
    ft = FakeTypefully(post={"unexpected": "shape"})
    rc = run_publish(pub, monkeypatch, ft)
    assert rc == 1
    assert "no draft id" in capsys.readouterr().err


def test_publish_non_json_response(pub, env, monkeypatch, capsys):
    class Bad(FakeResp):
        def read(self):
            return b"<html>gateway</html>"

    def bad_urlopen(req, timeout=60):
        return Bad({})

    monkeypatch.setattr(pub.urllib.request, "urlopen", bad_urlopen)
    monkeypatch.setattr("sys.argv", ["prog", "--text", "hi", "--no-wait"])
    with pytest.raises(SystemExit) as e:
        pub.main()
    assert e.value.code == 1
    assert "non-JSON" in capsys.readouterr().err


def test_load_dotenv_handles_export_prefix(pub, tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_EXPORT_VAR", raising=False)
    p = tmp_path / ".env"
    p.write_text('export TEST_EXPORT_VAR=abc\nPLAIN=def\n# comment\n', encoding="utf-8")
    pub.load_dotenv(p)
    import os
    assert os.environ["TEST_EXPORT_VAR"] == "abc"
    assert os.environ["PLAIN"] == "def"


GOOD = "https://x.com/someone/status/1234567890"


def run_reply(rep, monkeypatch, ft, reply_to=GOOD, text="adding the missing next step"):
    monkeypatch.setattr(rep.urllib.request, "urlopen", ft)
    monkeypatch.setattr("sys.argv", ["prog", "--text", text, "--reply-to", reply_to])
    return rep.main()


def test_reply_draft_happy_path(rep, env, monkeypatch, capsys):
    ft = FakeTypefully(post={"id": "d2", "private_url": "https://typefully.com/d/d2"})
    rc = run_reply(rep, monkeypatch, ft)
    assert rc == 0
    assert ft.last_post["platforms"]["x"]["settings"]["reply_to_url"] == GOOD
    assert "publish_at" not in ft.last_post  # never schedule a reply
    out = json.loads(capsys.readouterr().out)
    assert "Publish NOW" in out["next"]


def test_reply_draft_accepts_twitter_url(rep, env, monkeypatch, capsys):
    ft = FakeTypefully(post={"id": "d2", "private_url": "https://typefully.com/d/d2"})
    rc = run_reply(rep, monkeypatch, ft, reply_to="https://twitter.com/someone/status/99")
    assert rc == 0
    assert "private_url" in capsys.readouterr().out


@pytest.mark.parametrize(
    "bad",
    [
        "x.com/someone/status/123",            # no scheme
        "https://x.com/status/123",             # no user
        "https://x.com/someone/",               # no status
        "https://x.com/someone/status/abc",     # non-numeric id
        "https://example.com/someone/status/1", # wrong host
        "not a url",
    ],
)
def test_reply_draft_rejects_bad_urls(rep, env, monkeypatch, capsys, bad):
    with pytest.raises(SystemExit) as e:
        run_reply(rep, monkeypatch, FakeTypefully(), reply_to=bad)
    assert e.value.code == 2
    assert "reply-to" in capsys.readouterr().err


def test_reply_draft_rejects_long_text(rep, env, monkeypatch, capsys):
    with pytest.raises(SystemExit) as e:
        run_reply(rep, monkeypatch, FakeTypefully(), text="y" * 300)
    assert e.value.code == 2
    assert "280" in capsys.readouterr().err


def test_reply_draft_rejects_empty_text(rep, env, monkeypatch):
    with pytest.raises(SystemExit) as e:
        run_reply(rep, monkeypatch, FakeTypefully(), text="")
    assert e.value.code == 2


def test_reply_draft_http_error(rep, env, monkeypatch, capsys):
    err = urllib.error.HTTPError(API, 403, "nope", {}, io.BytesIO(b"forbidden"))
    rc = run_reply(rep, monkeypatch, FakeTypefully(post_error=err))
    assert rc == 1
    assert "403" in capsys.readouterr().err


def test_reply_draft_network_error(rep, env, monkeypatch, capsys):
    err = urllib.error.URLError("connection refused")
    rc = run_reply(rep, monkeypatch, FakeTypefully(post_error=err))
    assert rc == 1
    assert "cannot reach Typefully" in capsys.readouterr().err


def test_reply_draft_missing_private_url(rep, env, monkeypatch, capsys):
    ft = FakeTypefully(post={"id": "d3"})
    rc = run_reply(rep, monkeypatch, ft)
    assert rc == 1
    assert "no draft URL" in capsys.readouterr().err


def test_reply_draft_made_with_ai_operator_choice(rep, env, monkeypatch):
    env.setenv("X_MADE_WITH_AI", "1")
    ft = FakeTypefully(post={"id": "d2", "private_url": "https://typefully.com/d/d2"})
    assert run_reply(rep, monkeypatch, ft) == 0
    assert ft.last_post["platforms"]["x"]["settings"]["made_with_ai"] is True

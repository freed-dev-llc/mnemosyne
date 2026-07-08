"""Loaders must capture citable metadata and reject the unsupported."""

from __future__ import annotations

import email.message
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from mnemosyne.loaders import load_documents, load_file, load_url


def test_markdown_loads_with_metadata(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text("# Title\n\nbody text", encoding="utf-8")
    docs = load_file(f)
    assert len(docs) == 1
    assert "body text" in docs[0].page_content
    assert docs[0].metadata["source"] == str(f)
    assert docs[0].metadata["title"] == "note"


def test_html_is_stripped_to_text(tmp_path: Path) -> None:
    f = tmp_path / "page.html"
    f.write_text(
        "<html><head><title>Adopt</title><style>x{}</style></head>"
        "<body><p>Hello</p><script>bad()</script></body></html>",
        encoding="utf-8",
    )
    (doc,) = load_file(f)
    assert "Hello" in doc.page_content
    assert "bad()" not in doc.page_content
    assert doc.metadata["title"] == "Adopt"


def test_unsupported_suffix_raises(tmp_path: Path) -> None:
    f = tmp_path / "data.xyz"
    f.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_file(f)


def test_load_documents_flattens(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    b = tmp_path / "b.txt"
    a.write_text("alpha", encoding="utf-8")
    b.write_text("beta", encoding="utf-8")
    docs = load_documents([a, b])
    assert {d.page_content for d in docs} == {"alpha", "beta"}


class _FakeResponse:
    """Minimal context-manager stand-in for an ``http.client.HTTPResponse``."""

    def __init__(self, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
        self._body = body
        self.headers = email.message.Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="http://example.com", code=code, msg="err", hdrs=None, fp=None
    )


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record sleep durations without ever sleeping for real."""
    slept: list[float] = []
    monkeypatch.setattr("mnemosyne.loaders.time.sleep", lambda s: slept.append(s))
    return slept


def _patch_urlopen(monkeypatch: pytest.MonkeyPatch, side_effects: list[Any]) -> list[int]:
    """Replace ``urlopen`` with a scripted sequence; return a per-call counter list."""
    calls: list[int] = []

    def fake_urlopen(req: object, timeout: int = 30) -> object:
        calls.append(1)
        effect = side_effects[len(calls) - 1]
        if isinstance(effect, Exception):
            raise effect
        return effect

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def test_load_url_permanent_4xx_fails_fast(
    monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    calls = _patch_urlopen(monkeypatch, [_http_error(404)] * 3)
    with pytest.raises(urllib.error.HTTPError):
        load_url("http://example.com", retries=3)
    assert len(calls) == 1
    assert no_sleep == []


def test_load_url_5xx_retries_then_raises(
    monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    calls = _patch_urlopen(monkeypatch, [_http_error(500)] * 3)
    with pytest.raises(urllib.error.HTTPError):
        load_url("http://example.com", retries=3)
    assert len(calls) == 3
    assert no_sleep == [1.0, 2.0]


@pytest.mark.parametrize("code", [403, 429])
def test_load_url_retryable_4xx_retries(
    monkeypatch: pytest.MonkeyPatch, no_sleep: list[float], code: int
) -> None:
    calls = _patch_urlopen(monkeypatch, [_http_error(code)] * 3)
    with pytest.raises(urllib.error.HTTPError):
        load_url("http://example.com", retries=3)
    assert len(calls) == 3


def test_load_url_transient_failure_then_success(
    monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    body = b"<html><title>Doc</title><body>hi there</body></html>"
    calls = _patch_urlopen(monkeypatch, [urllib.error.URLError("boom"), _FakeResponse(body)])
    doc = load_url("http://example.com", retries=3)
    assert len(calls) == 2
    assert "hi there" in doc.page_content
    assert doc.metadata["title"] == "Doc"


def test_load_url_honors_response_charset(
    monkeypatch: pytest.MonkeyPatch, no_sleep: list[float]
) -> None:
    body = "café".encode("iso-8859-1")
    _patch_urlopen(
        monkeypatch,
        [_FakeResponse(body, content_type="text/html; charset=iso-8859-1")],
    )
    doc = load_url("http://example.com")
    assert "café" in doc.page_content


def test_load_url_rejects_retries_below_one(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_urlopen(monkeypatch, [])
    with pytest.raises(ValueError, match="retries must be >= 1"):
        load_url("http://example.com", retries=0)
    assert calls == []

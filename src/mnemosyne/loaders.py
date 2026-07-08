"""Load — get clean text (and citable metadata) out of messy files and URLs.

The loader's only job is to produce plain text plus metadata (``source``, ``title``,
optional ``page``). That metadata is what later becomes a *citation*, so it is captured
here at the very first stage.

Markdown / text / HTML are handled with the standard library. PDF support is optional
(``pip install 'mnemosyne-rag[pdf]'``) and degrades to a clear error if missing.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

from langchain_core.documents import Document

_TEXTLIKE = {".md", ".markdown", ".txt", ".rst"}


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML → text: drops script/style, keeps the ``<title>``."""

    _SKIP: ClassVar[set[str]] = {"script", "style", "head", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data.strip()
        elif self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    @property
    def text(self) -> str:
        return "\n".join(self._chunks)


def _html_to_text(html: str) -> tuple[str, str]:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.text, parser.title


def _load_pdf(path: Path) -> list[Document]:
    # Use LangChain's PyPDFLoader (one Document per page), as in the rag_ollama tutorial,
    # then enrich metadata with a citable title and a 1-indexed page number.
    from langchain_community.document_loaders import PyPDFLoader

    docs: list[Document] = []
    for doc in PyPDFLoader(str(path)).load():
        if not doc.page_content.strip():
            continue
        doc.metadata.setdefault("source", str(path))
        doc.metadata["title"] = path.stem
        page = doc.metadata.get("page")
        if isinstance(page, int):  # PyPDFLoader pages are 0-indexed
            doc.metadata["page"] = page + 1
        docs.append(doc)
    return docs


# Every suffix the ``load_file`` dispatch below accepts. Pack scanning
# (``packs/base.py``) imports this set, so a loader branch added here is picked up by
# directory scans without a second edit. Keep it in step with the branches in ``load_file``.
SUPPORTED_SUFFIXES = _TEXTLIKE | {".html", ".htm", ".pdf"}


def load_file(path: str | Path) -> list[Document]:
    """Load a single local file into one or more :class:`Document` objects."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in _TEXTLIKE:
        return [
            Document(
                page_content=path.read_text(encoding="utf-8", errors="ignore"),
                metadata={"source": str(path), "title": path.stem},
            )
        ]
    if suffix in {".html", ".htm"}:
        text, title = _html_to_text(path.read_text(encoding="utf-8", errors="ignore"))
        return [
            Document(
                page_content=text,
                metadata={"source": str(path), "title": title or path.stem},
            )
        ]
    if suffix == ".pdf":
        return _load_pdf(path)

    raise ValueError(f"Unsupported file type: {path.name} ({suffix or 'no suffix'})")


# A browser-like UA + Accept headers; many doc sites (e.g. help centers behind a CDN)
# return 403 to an obvious bot UA.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# 4xx codes worth retrying: doc sites behind a CDN sometimes return a transient 403 under
# throttling, 408 is an explicit request timeout, and 429 is rate limiting. Every other 4xx
# is a permanent client error (404, 410, ...) where retrying only wastes time.
_RETRYABLE_4XX = {403, 408, 429}


def load_url(url: str, *, timeout: int = 30, retries: int = 3) -> Document:
    """Fetch an http(s) URL and return its text content as a :class:`Document`.

    Retries a few times with linear backoff. Permanent HTTP 4xx responses (404, 410, ...)
    fail fast on the first attempt; transient throttling/timeout codes (403, 408, 429) and
    5xx or network errors are retried. The page is decoded using the charset declared in the
    response headers, falling back to UTF-8.
    """
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"Only http(s) URLs are supported, got: {url!r}")
    if retries < 1:
        raise ValueError(f"retries must be >= 1, got {retries}")
    req = urllib.request.Request(url, headers=dict(_BROWSER_HEADERS))  # noqa: S310 - scheme checked above
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - scheme checked above
                charset = resp.headers.get_content_charset() or "utf-8"
                data = resp.read()
            try:
                raw = data.decode(charset, errors="ignore")
            except LookupError:  # bogus charset label in the response header
                raw = data.decode("utf-8", errors="ignore")
            text, title = _html_to_text(raw)
            return Document(
                page_content=text or raw,
                metadata={"source": url, "title": title or url},
            )
        except urllib.error.HTTPError as exc:
            # Permanent client errors (4xx that is not throttling/timeout) will never
            # succeed on retry, so fail fast instead of sleeping through the loop.
            if exc.code < 500 and exc.code not in _RETRYABLE_4XX:
                raise
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
        except Exception as exc:  # transient fetch failure — back off and retry
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def load_documents(paths: list[str | Path]) -> list[Document]:
    """Load many local files, flattening multi-page documents."""
    docs: list[Document] = []
    for path in paths:
        docs.extend(load_file(path))
    return docs

"""HTTP server: routes + offline endpoints (no Ollama/network needed)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from mnemosyne import service
from mnemosyne.http_server import app
from mnemosyne.pipeline import RagPipeline

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_packs_lists_known_packs() -> None:
    resp = client.get("/packs")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert {"ubiquiti", "general"} <= names


def test_ask_unknown_pack_is_404() -> None:
    resp = client.post("/ask", json={"pack": "does-not-exist", "question": "hi"})
    assert resp.status_code == 404
    assert "does-not-exist" in resp.json()["detail"]


def test_ask_requires_fields() -> None:
    resp = client.post("/ask", json={"pack": "ubiquiti"})  # missing question
    assert resp.status_code == 422  # FastAPI validation


class _EmptyStore:
    """A store the fake pipeline never actually reaches: k<1 is rejected before any search."""

    def similarity_search(self, query: str, k: int) -> list[object]:
        return []

    def similarity_search_with_score(self, query: str, k: int) -> list[object]:
        return []


def test_search_rejects_non_positive_k_as_400(monkeypatch: pytest.MonkeyPatch) -> None:
    """``k=0`` on /search is a client error (400) via the real retrieve validation, not a 500."""

    def _fake_pipeline(pack: object, settings: object) -> RagPipeline:
        # A real RagPipeline (so the actual retrieve() runs its k<1 check) with a fake store,
        # bypassing the Ollama-touching __init__ as the pipeline unit tests do.
        pipe = RagPipeline.__new__(RagPipeline)
        pipe.store = _EmptyStore()  # type: ignore[assignment]
        pipe.top_k = 5
        pipe.score_floor = None
        return pipe

    monkeypatch.setattr(service, "get_pack", lambda name: SimpleNamespace(name=name))
    monkeypatch.setattr(service, "RagPipeline", _fake_pipeline)

    resp = client.post("/search", json={"pack": "any", "query": "x", "k": 0})
    assert resp.status_code == 400
    assert "positive integer" in resp.json()["detail"]

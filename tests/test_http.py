"""HTTP server: routes + offline endpoints (no Ollama/network needed)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mnemosyne.http_server import app

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

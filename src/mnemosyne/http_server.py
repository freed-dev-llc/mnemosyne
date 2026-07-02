"""FastAPI HTTP server exposing Mnemosyne to web UIs and services.

Where ``mcp_server.py`` serves *agents* over stdio, this serves anything that speaks HTTP and
can't do MCP — e.g. an "ask the brain" box in the Argus React dashboard (which proxies to this
server-to-server). A thin wrapper over :mod:`mnemosyne.service`.

Run:  ``mnemosyne-http``  (binds MNEMOSYNE_HTTP_HOST:MNEMOSYNE_HTTP_PORT, default 127.0.0.1:8088).
API docs at ``/docs``; the app icon is served at ``/favicon.svg``.
"""

from __future__ import annotations

from importlib import resources
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel

from . import __version__, service
from .config import get_settings

app = FastAPI(
    title="Mnemosyne",
    version=__version__,
    summary="Local RAG knowledge brain.",
    docs_url=None,  # replaced below so the API docs page uses the Mnemosyne icon as its favicon
)

# The application icon, packaged as data (src/mnemosyne/static/) and served at /favicon.svg so
# the running service and its API docs carry the Mnemosyne mark.
_FAVICON_SVG = (resources.files("mnemosyne") / "static" / "mnemosyne_icon.svg").read_bytes()


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> Response:
    return Response(content=_FAVICON_SVG, media_type="image/svg+xml")


@app.get("/docs", include_in_schema=False)
def swagger_ui() -> Any:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} API",
        swagger_favicon_url="/favicon.svg",
    )


class AskRequest(BaseModel):
    pack: str
    question: str
    k: int | None = None


class SearchRequest(BaseModel):
    pack: str
    query: str
    k: int | None = None


def _handle(call: Any) -> Any:
    """Map service exceptions to HTTP status codes."""
    try:
        return call()
    except KeyError as exc:  # unknown pack
        raise HTTPException(status_code=404, detail=str(exc.args[0] if exc.args else exc)) from exc
    except FileNotFoundError as exc:  # index not built yet
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:  # bad input / empty corpus
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/packs")
def packs() -> list[dict[str, Any]]:
    return service.list_packs()


@app.post("/ask")
def ask(req: AskRequest) -> dict[str, Any]:
    return _handle(lambda: service.ask(req.pack, req.question, req.k))


@app.post("/search")
def search(req: SearchRequest) -> dict[str, Any]:
    return _handle(lambda: service.search(req.pack, req.query, req.k))


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)


if __name__ == "__main__":
    main()

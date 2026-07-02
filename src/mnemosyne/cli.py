"""``mnemosyne`` command-line surface: packs · ingest · ask · chat.

Thin glue over the library (:mod:`mnemosyne.pipeline` + :mod:`mnemosyne.packs`). Every
command resolves a knowledge pack from the registry, then either builds its index or
queries it.
"""

from __future__ import annotations

from typing import NoReturn

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__, service
from .config import get_settings
from .eval import (
    DEFAULT_MIN_HIT_RATE,
    GATE_OK,
    EvalReport,
    FaithfulnessReport,
    expand_grid,
    format_sweep_table,
    gate_exit_code,
    run_faithfulness_eval,
    run_retrieval_eval,
    run_sweep,
)
from .packs.registry import get_pack
from .pipeline import RagPipeline, Source, ingest

app = typer.Typer(
    add_completion=False,
    help="Mnemosyne — a local RAG pipeline that turns any model into an instant expert.",
)
console = Console()


@app.command("packs")
def list_packs() -> None:
    """List installed knowledge packs and whether each has a built index."""
    # The same discovery + index-status pass HTTP and MCP serve; the CLI only renders it.
    packs = service.list_packs()
    if not packs:
        console.print("[yellow]No knowledge packs found.[/]")
        raise typer.Exit()

    table = Table(title="Knowledge packs")
    table.add_column("Pack", style="bold")
    table.add_column("Title")
    table.add_column("Index", justify="center")
    for pack in packs:
        status = "[green]built[/]" if pack["built"] else "[dim]not built[/]"
        table.add_row(pack["name"], pack["title"], status)
    console.print(table)


@app.command("ingest")
def ingest_cmd(
    pack: str = typer.Argument(..., help="Knowledge pack name (see `mnemosyne packs`)."),
    chunk_size: int | None = typer.Option(None, help="Override chunk size (chars)."),
    chunk_overlap: int | None = typer.Option(None, help="Override chunk overlap (chars)."),
    embedding_model: str | None = typer.Option(None, help="Override the Ollama embedding model."),
    local_only: bool = typer.Option(
        False,
        "--local-only",
        help="Index only the local seed corpus; skip all URL fetches (deterministic, offline).",
    ),
) -> None:
    """Embed and index a pack's corpus (build the memory)."""
    try:
        target = get_pack(pack)
        with console.status(f"Ingesting '{pack}' …"):
            stats = ingest(
                target,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                embedding_model=embedding_model,
                local_only=local_only,
            )
    except (KeyError, ValueError) as exc:
        _die(exc)
    console.print(
        Panel.fit(
            f"[green]Indexed[/] [bold]{stats.pack}[/]\n"
            f"documents: {stats.documents}   chunks: {stats.chunks}\n"
            f"embeddings: {stats.embedding_model}\n"
            f"index: {stats.index_path}",
            title="ingest complete",
        )
    )


@app.command("ask")
def ask_cmd(
    pack: str = typer.Argument(..., help="Knowledge pack to query."),
    question: list[str] = typer.Argument(..., help="Your question."),
    k: int | None = typer.Option(None, "--k", help="Number of chunks to retrieve."),
    model: str | None = typer.Option(None, "--model", help="Override the Ollama chat model."),
    show_sources: bool = typer.Option(False, "--show-sources", help="Print retrieved sources."),
) -> None:
    """Ask the expert a single question."""
    try:
        pipe = RagPipeline(get_pack(pack), chat_model=model, top_k=k)
        answer = pipe.ask(" ".join(question))
    except (KeyError, FileNotFoundError, ValueError) as exc:
        _die(exc)
    console.print(answer.text)
    if show_sources:
        _print_sources(answer.sources)


@app.command("chat")
def chat_cmd(
    pack: str = typer.Argument(..., help="Knowledge pack to chat with."),
    k: int | None = typer.Option(None, "--k", help="Number of chunks to retrieve."),
    model: str | None = typer.Option(None, "--model", help="Override the Ollama chat model."),
    show_sources: bool = typer.Option(False, "--show-sources", help="Print sources each turn."),
) -> None:
    """Interactive Q&A loop against a pack (Ctrl-D / 'exit' to quit)."""
    try:
        pipe = RagPipeline(get_pack(pack), chat_model=model, top_k=k)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        _die(exc)
    console.print(f"[dim]Chatting with [bold]{pack}[/]. Type 'exit' or Ctrl-D to quit.[/]")
    # RAG has no automatic memory — we thread a running transcript ourselves so the model
    # remembers earlier turns (the chat-history best practice from rag_ollama).
    chat_history = ""
    while True:
        try:
            question = console.input("[bold cyan]you >[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        answer = pipe.ask(question, chat_history=chat_history)
        chat_history += f"\nUser: {question}\n\nAssistant: {answer.text}\n"
        console.print(f"[bold magenta]{pack} >[/] {answer.text}")
        if show_sources:
            _print_sources(answer.sources)


@app.command("eval")
def eval_cmd(
    pack: str = typer.Argument(..., help="Knowledge pack to evaluate."),
    k: int | None = typer.Option(None, "--k", help="Number of chunks to retrieve."),
    show_misses: bool = typer.Option(
        False, "--show-misses", help="List the missing expected strings per failed question."
    ),
    faithfulness: bool = typer.Option(
        False,
        "--faithfulness",
        "-f",
        help="Also score answer faithfulness (runs the chat model — slower).",
    ),
    gate: bool = typer.Option(
        False,
        "--gate",
        help="Gate the run: exit 2 if the retrieval hit-rate is below the floor (CI gate).",
    ),
    min_hit_rate: float | None = typer.Option(
        None,
        "--min-hit-rate",
        help="Floor as a fraction, e.g. 0.9 = 90%; passing it implies --gate. "
        "Defaults to the committed baseline.",
    ),
) -> None:
    """Report a pack's retrieval hit-rate against its labelled question set.

    Report-only by default (always exits 0 — the ADR-0006/0007 promise). Pass ``--gate`` (or a
    ``--min-hit-rate`` floor) to add a regression gate: exit ``2`` when the hit-rate is below the
    floor, exit ``0`` when it meets it. See ADR-0008.
    """
    try:
        report = run_retrieval_eval(pack, k=k)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        _die(exc)
    pct = round(report.hit_rate * 100)
    console.print(f"retrieval hit-rate: [bold]{report.hits}/{report.total}[/] ({pct}%)")
    _print_eval(report, show_misses=show_misses)
    if faithfulness:
        try:
            faith = run_faithfulness_eval(pack, k=k)
        except (KeyError, FileNotFoundError, ValueError) as exc:
            _die(exc)
        console.print(
            f"answer faithfulness: mean {faith.mean_faithfulness:.2f} over {faith.total} questions"
        )
        _print_faithfulness(faith, show_misses=show_misses)
    # Gating is opt-in: neither --gate nor --min-hit-rate ⇒ report-only, exit 0 (unchanged).
    # An explicit --min-hit-rate implies --gate; it wins over the committed default floor.
    if gate or min_hit_rate is not None:
        floor = DEFAULT_MIN_HIT_RATE if min_hit_rate is None else min_hit_rate
        if not 0.0 <= floor <= 1.0:
            _die(ValueError("--min-hit-rate must be a fraction in [0.0, 1.0]."))
        code = gate_exit_code(report.hit_rate, floor)
        verdict = "[green]PASS[/]" if code == GATE_OK else "[red]BELOW FLOOR[/]"
        console.print(f"gate: hit-rate {report.hit_rate:.2f} vs floor {floor:.2f} — {verdict}")
        raise typer.Exit(code)


@app.command("sweep")
def sweep_cmd(
    pack: str = typer.Argument(..., help="Knowledge pack to sweep."),
    chunk_size: list[int] = typer.Option(
        [], "--chunk-size", help="Chunk size to try (repeatable; default: the settings value)."
    ),
    chunk_overlap: list[int] = typer.Option(
        [],
        "--chunk-overlap",
        help="Chunk overlap to try (repeatable; default: the settings value).",
    ),
    k: list[int] = typer.Option(
        [], "--k", help="Chunks to retrieve (repeatable; default: the settings value)."
    ),
    embedding_model: list[str] = typer.Option(
        [],
        "--embedding-model",
        help="Embedding model to try (repeatable; default: the settings value).",
    ),
    chat_model: list[str] = typer.Option(
        [],
        "--chat-model",
        help="Chat model to try (repeatable). Only changes results under --faithfulness; "
        "retrieval ignores it.",
    ),
    faithfulness: bool = typer.Option(
        False,
        "--faithfulness",
        "-f",
        help="Also score answer faithfulness (runs the chat model per config — slower).",
    ),
) -> None:
    """Sweep chunking / k / model configs and print a comparison table.

    Report-only: each config is re-ingested into an ephemeral workspace (never the canonical
    index) and no default is changed. Every axis is repeatable and falls back to the shipped
    default, so a bare ``mnemosyne sweep <pack>`` runs a one-config sanity sweep. See ADR-0010.
    """
    settings = get_settings()
    try:
        configs = expand_grid(
            chunk_sizes=chunk_size or [settings.chunk_size],
            chunk_overlaps=chunk_overlap or [settings.chunk_overlap],
            ks=k or [settings.top_k],
            embedding_models=embedding_model or [settings.embedding_model],
            chat_models=chat_model or [settings.chat_model],
        )
        with console.status(f"Sweeping '{pack}' over {len(configs)} config(s) …"):
            report = run_sweep(pack, configs, faithfulness=faithfulness)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        _die(exc)
    # markup/highlight off so rich never interprets `:` / `[` in model names or the `*` best marker.
    console.print(format_sweep_table(report), markup=False, highlight=False)
    if report.best is None:
        console.print("no configs evaluated")
    else:
        b = report.best
        console.print(
            f"best: chunk_size={b.chunk_size} overlap={b.chunk_overlap} k={b.k} "
            f"emb={b.embedding_model} chat={b.chat_model}"
        )


@app.command("version")
def version_cmd() -> None:
    """Print the Mnemosyne version."""
    console.print(f"mnemosyne {__version__}")


def _die(exc: Exception) -> NoReturn:
    """Print a clean one-line error and exit non-zero (no traceback)."""
    # KeyError stringifies with surrounding quotes; prefer the raw message.
    message = exc.args[0] if exc.args else str(exc)
    console.print(f"[red]error:[/] {message}")
    raise typer.Exit(1)


def _print_sources(sources: list[Source]) -> None:
    table = Table(title="sources", show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("title")
    table.add_column("source", style="dim")
    for s in sources:
        label = f"{s.title}, p.{s.page}" if s.page else s.title
        table.add_row(str(s.n), str(label), str(s.source))
    console.print(table)


def _print_eval(report: EvalReport, *, show_misses: bool) -> None:
    table = Table(title=f"retrieval eval@{report.k} — {report.pack}", show_lines=False)
    table.add_column("id", style="bold")
    table.add_column("question")
    table.add_column("hit", justify="center")
    if show_misses:
        table.add_column("missing", style="dim")
    for r in report.results:
        mark = "[green]pass[/]" if r.hit else "[red]fail[/]"
        row = [r.id, r.question, mark]
        if show_misses:
            row.append(", ".join(r.missing))
        table.add_row(*row)
    console.print(table)


def _print_faithfulness(report: FaithfulnessReport, *, show_misses: bool) -> None:
    table = Table(title=f"faithfulness eval@{report.k} — {report.pack}", show_lines=False)
    table.add_column("id", style="bold")
    table.add_column("question")
    table.add_column("score", justify="right")
    if show_misses:
        table.add_column("ungrounded", style="dim")
    for r in report.results:
        # Score only — no pass/fail mark: there is no threshold this step (that is Step 3).
        row = [r.id, r.question, f"{r.score:.2f}"]
        if show_misses:
            row.append(", ".join(r.ungrounded))
        table.add_row(*row)
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

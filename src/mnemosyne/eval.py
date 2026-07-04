"""Retrieval hit-rate eval — did the right chunk get retrieved?

The smallest demonstrable RAG-quality metric: it scores only what ``.retrieve`` returns, so
it needs no LLM generation. Ground truth is *expected substrings* (not chunk IDs, not
document identity) — the corpus may be a single seed file, and substring matching survives
the re-chunking that future sweeps will do. See ADR-0006.

A question *hits* iff **every** string in its ``expected`` list appears (case-insensitive)
in the concatenated ``page_content`` of the top-k retrieved chunks. The scorer is a pure
function over an injected ``retrieve`` callable, so it runs fully offline in tests.

This module also carries the **generation-side** companion: answer *faithfulness* (see
ADR-0007). Given the context retrieved for a question and the answer generated from it,
:func:`faithfulness_score` reports the fraction of the answer's word-bigrams that also appear
in the context. It is a **grounding proxy, not a correctness oracle** — it measures whether an
answer is *supported by* its retrieved context, not whether it is *true* (faithfulness ≠
correctness). It is **report-only**: a continuous ``score`` per answer and a
``mean_faithfulness`` aggregate, with no threshold and no pass/fail label (that is deferred to
Step 3). An answer with fewer than ``n`` tokens makes no bigram-level claim, so it scores
``1.0`` (vacuously faithful) and is included in the mean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import yaml

from .config import Settings, get_settings
from .packs.registry import get_pack
from .pipeline import RagPipeline, ingest

if TYPE_CHECKING:
    from collections.abc import Callable

    from langchain_core.documents import Document

    from .packs.base import KnowledgePack

    Retrieve = Callable[[str, int], list[Document]]
    Generate = Callable[[str], tuple[str, str]]


@dataclass
class EvalQuestion:
    """One labelled question and its ground truth.

    Each ``expected`` item is either a required substring, or a list of interchangeable
    alternatives (an OR-group) of which any one satisfies the item. The OR-group lets a
    correct answer count regardless of source wording: a fetched doc that says "Native
    (untagged) VLAN" satisfies the same item as a seed doc's "untagged network".
    """

    id: str
    question: str
    expected: list[str | list[str]]
    note: str | None = None


@dataclass
class EvalResult:
    """The outcome of scoring one question against its retrieved chunks."""

    id: str
    question: str
    hit: bool
    missing: list[str]


@dataclass
class EvalReport:
    """Aggregate retrieval hit-rate over a question set."""

    pack: str
    k: int
    total: int
    hits: int
    hit_rate: float
    results: list[EvalResult]


def load_questions(pack: str) -> list[EvalQuestion]:
    """Load the labelled question set shipped with ``pack``.

    Reads ``packs/<pack>/eval/questions.yaml`` by convention (no manifest field — the
    location is fixed, which keeps the manifest schema untouched). Raises
    ``FileNotFoundError`` if the pack ships no question set.
    """
    path = get_pack(pack).directory / "eval" / "questions.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No eval question set for pack '{pack}'. Expected a file at {path}."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        EvalQuestion(
            id=item["id"],
            question=item["question"],
            expected=list(item["expected"]),
            note=item.get("note"),
        )
        for item in raw.get("questions", []) or []
    ]


def _alternatives(item: str | list[str]) -> list[str]:
    """The acceptable forms of one expected item.

    A plain string is its own single alternative; a list is an OR-group. Normalizing both to
    a list lets the scorer treat "one required substring" and "any of these" uniformly.
    """
    return [item] if isinstance(item, str) else list(item)


def score(
    questions: list[EvalQuestion],
    retrieve: Retrieve,
    k: int,
    *,
    pack: str = "",
) -> EvalReport:
    """Score each question against its top-k retrieved chunks (pure, offline-friendly).

    ``retrieve`` is injected — ``(question, k) -> list[Document]`` — so the scorer never
    touches Ollama. A question hits iff, for every ``expected`` item, at least one of its
    alternatives is found (case-insensitive) in the concatenated ``page_content`` of the
    retrieved chunks; a plain string is a one-alternative item. Each unmatched item is
    recorded on a miss, its alternatives joined with `` | ``.
    """
    results: list[EvalResult] = []
    for q in questions:
        haystack = "\n".join(doc.page_content for doc in retrieve(q.question, k)).lower()
        missing: list[str] = []
        for item in q.expected:
            alternatives = _alternatives(item)
            if not any(alt.lower() in haystack for alt in alternatives):
                missing.append(" | ".join(alternatives))
        results.append(EvalResult(id=q.id, question=q.question, hit=not missing, missing=missing))
    total = len(questions)
    hits = sum(1 for r in results if r.hit)
    hit_rate = hits / total if total else 0.0
    return EvalReport(pack=pack, k=k, total=total, hits=hits, hit_rate=hit_rate, results=results)


def run_retrieval_eval(
    pack: str,
    *,
    k: int | None = None,
    settings: Settings | None = None,
    retrieve: Retrieve | None = None,
) -> EvalReport:
    """Score ``pack``'s labelled question set against retrieval.

    When ``retrieve`` is omitted, build a :class:`RagPipeline` and use its ``.retrieve`` —
    that path needs Ollama and a built index, exactly like ``ask``/``search``. Injecting a
    ``retrieve`` callable (the way tests do) keeps the whole run offline.
    """
    questions = load_questions(pack)
    if retrieve is None:
        pipeline = RagPipeline(get_pack(pack), settings, top_k=k)
        retrieve = pipeline.retrieve
        k = pipeline.top_k
    elif k is None:
        k = (settings or get_settings()).top_k
    return score(questions, retrieve, k, pack=pack)


# --- Answer faithfulness (generation-side metric; see ADR-0007) ----------------------------

# Identifier-preserving tokenizer (chosen over bare \w+): a run of alphanumerics that may
# carry internal . : _ - separators between two alphanumeric runs. Keeps identifiers WHOLE —
# 192.168.1.1, udm-pro, qwen2.5:1.5b, bge-m3 — instead of shredding them into the colliding
# fragments bare \w+ produces, so a fabricated IP / model-SKU breaks the bigram and surfaces as
# `ungrounded` (catching it is the point of a grounding metric over network docs). It also stops
# at trailing punctuation ("192.168.1.1." -> "192.168.1.1", "udm-pro," -> "udm-pro"); only
# . : _ - are internal, so "/" and "+" are not — CIDR "10.0.0.0/8" splits at the slash (accepted,
# ADR-0007). No stopword filtering — polarity words (not/off/on) and bigram adjacency matter.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.:_-][a-z0-9]+)*")


def _ngrams(text: str, n: int) -> list[str]:
    """Lowercase ``text``, tokenize with :data:`_TOKEN_RE`, and return its n-grams.

    The single tokenization source of truth: both :func:`faithfulness_score` and the
    ``ungrounded`` extraction call this, so the reported score and the reported list can never
    diverge. Fewer than ``n`` tokens yields an empty list.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def faithfulness_score(answer: str, context: str, *, n: int = 2) -> float:
    """Fraction of the answer's word-n-grams that also appear in the context.

    A grounding proxy, **not** a correctness oracle: it measures whether the answer is
    *supported by* its retrieved context, not whether it is *true* (faithfulness ≠ correctness;
    see ADR-0007). ``n`` defaults to bigrams and is a keyword so Step 4 can sweep it.

    An answer with fewer than ``n`` tokens (empty, one word, a terse refusal) has no
    bigram-level claim to check, so it scores ``1.0`` — vacuously faithful, nothing to
    contradict. ``0.0`` is reserved for a real (>= ``n``-token) answer none of whose n-grams are
    in context — genuinely ungrounded, including the empty-context case.
    """
    a = _ngrams(answer, n)
    if not a:
        return 1.0
    c = set(_ngrams(context, n))
    return sum(1 for g in a if g in c) / len(a)


@dataclass
class FaithfulnessResult:
    """The faithfulness outcome for one question (mirror of :class:`EvalResult`)."""

    id: str
    question: str
    # Fraction of the answer's n-grams found in context; 1.0 for an empty/sub-n answer.
    score: float
    # Answer n-grams absent from context (unique, order-preserving); [] when every n-gram is
    # grounded and when a sub-n answer made no claim.
    ungrounded: list[str]


@dataclass
class FaithfulnessReport:
    """Aggregate answer faithfulness over a question set (mirror of :class:`EvalReport`)."""

    pack: str
    k: int
    n: int
    total: int
    mean_faithfulness: float  # mean of `score` over ALL results (0.0 if total == 0)
    results: list[FaithfulnessResult]


def score_faithfulness(
    questions: list[EvalQuestion],
    generate: Generate,
    k: int,
    *,
    n: int = 2,
    pack: str = "",
) -> FaithfulnessReport:
    """Score each question's generated answer against its retrieved context (pure, offline).

    Mirrors :func:`score`. ``generate`` is injected — ``(question) -> (answer, context)`` — so
    the aggregator never touches Ollama; the context must be the exact text the answer was scored
    against. Per item, the score comes from :func:`faithfulness_score` and ``ungrounded`` is
    derived through the same :func:`_ngrams` tokenizer, so the float and the list can never
    diverge. ``mean_faithfulness`` is the mean over **all** results — sub-``n`` answers score
    ``1.0`` and are included. No threshold; pass/fail labelling is deferred to Step 3.
    """
    results: list[FaithfulnessResult] = []
    for q in questions:
        answer, context = generate(q.question)
        value = faithfulness_score(answer, context, n=n)
        context_ngrams = set(_ngrams(context, n))
        ungrounded = list(dict.fromkeys(g for g in _ngrams(answer, n) if g not in context_ngrams))
        results.append(
            FaithfulnessResult(id=q.id, question=q.question, score=value, ungrounded=ungrounded)
        )
    total = len(questions)
    mean_faithfulness = sum(r.score for r in results) / total if total else 0.0
    return FaithfulnessReport(
        pack=pack,
        k=k,
        n=n,
        total=total,
        mean_faithfulness=mean_faithfulness,
        results=results,
    )


def run_faithfulness_eval(
    pack: str,
    *,
    k: int | None = None,
    n: int = 2,
    settings: Settings | None = None,
    generate: Generate | None = None,
) -> FaithfulnessReport:
    """Score ``pack``'s generated answers for faithfulness against their retrieved context.

    Mirrors :func:`run_retrieval_eval`. When ``generate`` is omitted, build a
    :class:`RagPipeline` and bind a closure that asks for the answer and re-retrieves the same
    top-k chunks as the scoring context — that path needs Ollama and a built index, exactly like
    ``ask``. Injecting a ``generate`` callable (the way tests do) keeps the whole run offline.
    ``n`` threads through to :func:`score_faithfulness`; its default lives on the signature,
    deliberately not a CLI flag (see ADR-0007).
    """
    questions = load_questions(pack)
    if generate is None:
        pipeline = RagPipeline(get_pack(pack), settings, top_k=k)
        k = pipeline.top_k

        def generate_from_pipeline(question: str) -> tuple[str, str]:
            answer = pipeline.ask(question, k).text
            context = "\n".join(doc.page_content for doc in pipeline.retrieve(question, k))
            return answer, context

        generate = generate_from_pipeline
    elif k is None:
        k = (settings or get_settings()).top_k
    return score_faithfulness(questions, generate, k, n=n, pack=pack)


# --- Retrieval hit-rate CI gate (run-level regression floor; see ADR-0008) ------------------

# Exit-code contract for the optional gate (single source of truth — the CLI imports these).
# `mnemosyne eval` stays report-only by default (always exit 0, the ADR-0006/0007 promise);
# `--gate` opts a run into a pass/fail verdict so CI can flag a retrieval regression. GATE_OK
# keeps the conventional 0 = success; GATE_BELOW_FLOOR is 2 = "ran fine but below the floor",
# deliberately distinct from 1 (the operational-error code `_die` raises before a report exists).
GATE_OK = 0
GATE_BELOW_FLOOR = 2

# Floating-point slack for the floor comparison. `hit_rate` is a rational `k / total`, so a floor
# seeded from a past `k / total` compares exactly; the epsilon only guards a decimal
# `--min-hit-rate` input (e.g. 0.9 vs 9/10) at the boundary.
_GATE_EPSILON = 1e-9

# The committed retrieval hit-rate floor of record (a fraction in [0.0, 1.0], e.g. 1.0 for 10/10).
# It is a regression ratchet, not an absolute bar: the *measured* baseline of the ubiquiti corpus,
# measured by the `eval-gate` CI job's deterministic `--local-only` ingest + `mnemosyne eval
# ubiquiti` (re-measure the same way to reset it). Step 4c's sweep confirmed 9/10 at the shipped
# defaults on the seed-only corpus (ADR-0011); ADR-0012 re-confirmed 9/10 after the corpus grew to 4
# documents; ADR-0014 measured 18/19 (0.95) once the question set expanded to 19 covering all three
# primers. The floor stays 0.9 (the expanded set clears it with headroom, kept round rather than
# ratcheted to 0.947 so the gate tolerates a single-question embedding difference across hardware).
DEFAULT_MIN_HIT_RATE = 0.9


def gate_exit_code(hit_rate: float, min_hit_rate: float) -> int:
    """Pure gate verdict: :data:`GATE_OK` if ``hit_rate`` is at/above the floor, else
    :data:`GATE_BELOW_FLOOR`.

    Total and offline: it only ever sees a successfully-computed ``hit_rate``, so it never
    returns the operational-error code (1) — that path is exceptions caught by ``_die`` before a
    report exists. The :data:`_GATE_EPSILON` slack keeps a run that exactly meets the floor a pass.
    """
    return GATE_OK if hit_rate >= min_hit_rate - _GATE_EPSILON else GATE_BELOW_FLOOR


# --- Config sweeps (choose defaults from data; see issue #24) -------------------------------

# This is the pure, offline core of the sweep: a grid over the knobs that move retrieval quality
# (chunk size/overlap, k, and the two models), a scorer that runs each config through the existing
# `score` / `score_faithfulness` aggregators, and a plain-text comparison table. Everything here is
# a pure function over injected `retrieve` / `generate` factories, so it runs with no Ollama and no
# network (the same contract as `score`). The live runner that re-ingests per config, the CLI, and
# the design ADR are a follow-up; this section reads and decides nothing about the shipped defaults.


@dataclass(frozen=True)
class SweepConfig:
    """One point in the sweep grid: a full set of knob values to evaluate together.

    Frozen so it is hashable: the live runner (a follow-up) keys a per-config re-ingest cache on
    it, and two configs with identical knobs must collapse to one index build.
    """

    chunk_size: int
    chunk_overlap: int
    k: int
    embedding_model: str
    chat_model: str


def expand_grid(
    *,
    chunk_sizes: list[int],
    chunk_overlaps: list[int],
    ks: list[int],
    embedding_models: list[str],
    chat_models: list[str],
) -> list[SweepConfig]:
    """Expand five keyword axes into the Cartesian grid of :class:`SweepConfig`.

    The product runs in argument order (``chunk_sizes``, then ``chunk_overlaps``, ``ks``,
    ``embedding_models``, ``chat_models``), so the last axis varies fastest. That order is part
    of the contract (callers and the table depend on it) and is covered by a test.

    Raises ``ValueError`` if any axis is empty: a sweep needs at least one value per axis. Any
    config with ``chunk_overlap >= chunk_size`` is **dropped**: overlap must be smaller than the
    chunk, and such a config would break ``RecursiveCharacterTextSplitter`` at ingest, so it is
    kept out of the grid (and the table) entirely rather than evaluated and shown.
    """
    axes = {
        "chunk_sizes": chunk_sizes,
        "chunk_overlaps": chunk_overlaps,
        "ks": ks,
        "embedding_models": embedding_models,
        "chat_models": chat_models,
    }
    empty = [name for name, values in axes.items() if not values]
    if empty:
        raise ValueError(f"sweep axis cannot be empty: {', '.join(empty)}")
    return [
        SweepConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            k=k,
            embedding_model=embedding_model,
            chat_model=chat_model,
        )
        for chunk_size, chunk_overlap, k, embedding_model, chat_model in product(
            chunk_sizes, chunk_overlaps, ks, embedding_models, chat_models
        )
        if chunk_overlap < chunk_size
    ]


@dataclass
class SweepRow:
    """One config's headline numbers: the only columns the comparison table needs."""

    config: SweepConfig
    hit_rate: float
    # Mean answer faithfulness, or None when faithfulness was not scored (retrieval-only sweep).
    mean_faithfulness: float | None


@dataclass
class SweepReport:
    """A scored sweep: one :class:`SweepRow` per config, plus the best config (None if empty)."""

    pack: str
    rows: list[SweepRow]
    best: SweepConfig | None


def score_sweep(
    questions: list[EvalQuestion],
    configs: list[SweepConfig],
    retrieve_for: Callable[[SweepConfig], Retrieve],
    *,
    generate_for: Callable[[SweepConfig], Generate] | None = None,
    pack: str = "",
) -> SweepReport:
    """Score every config in ``configs`` and return a :class:`SweepReport` (pure, offline).

    Mirrors :func:`score` / :func:`score_faithfulness`: the per-config work is injected as
    *factories* (``retrieve_for(cfg) -> retrieve`` and the optional ``generate_for(cfg) ->
    generate``), so the aggregator never touches Ollama and a test can hand it canned callables.
    For each config its ``k`` drives both scorers. When ``generate_for`` is omitted, faithfulness
    is not run and each row's ``mean_faithfulness`` is None; ``n`` stays the
    :func:`score_faithfulness` default (n is not a swept axis). ``best`` is filled by
    :func:`_best_config`.
    """
    rows: list[SweepRow] = []
    for cfg in configs:
        rep = score(questions, retrieve_for(cfg), cfg.k, pack=pack)
        if generate_for is not None:
            frep = score_faithfulness(questions, generate_for(cfg), cfg.k, pack=pack)
            mean_faithfulness: float | None = frep.mean_faithfulness
        else:
            mean_faithfulness = None
        rows.append(
            SweepRow(config=cfg, hit_rate=rep.hit_rate, mean_faithfulness=mean_faithfulness)
        )
    return SweepReport(pack=pack, rows=rows, best=_best_config(rows))


def _best_config(rows: list[SweepRow]) -> SweepConfig | None:
    """Return the strongest measured config, or None for empty ``rows``.

    Best is a **presentation aid** that highlights the strongest measured config; it does **not**
    change any default (chunk size/overlap, k, models all stay as shipped). Acting on the result
    is a deliberate later follow-up, not part of scoring.

    The ranking is pinned: ``hit_rate`` descending, then ``mean_faithfulness`` descending (a row
    that was not faithfulness-scored, i.e. None, ranks worst), then the cheaper config wins on
    ties (``k`` ascending, then ``chunk_size`` ascending, then ``chunk_overlap`` ascending).
    """
    if not rows:
        return None

    def rank(row: SweepRow) -> tuple[float, float, int, int, int]:
        # Sort ascending: negate the "higher is better" fields; None faithfulness sorts last.
        faithfulness = row.mean_faithfulness if row.mean_faithfulness is not None else float("-inf")
        cfg = row.config
        return (-row.hit_rate, -faithfulness, cfg.k, cfg.chunk_size, cfg.chunk_overlap)

    return min(rows, key=rank).config


def format_sweep_table(report: SweepReport) -> str:
    """Render ``report`` as a plain-text monospaced table (one line per config).

    Columns: chunk_size, overlap, k, emb_model, chat_model, hit_rate, faithfulness. The best
    config's row is marked with a leading ``*``; faithfulness shows ``-`` when it was not scored
    (None). Empty ``rows`` yields a header-only table (no crash). Returns a ``str`` so an offline
    test can assert the rendered text directly; any richer rendering is a CLI concern, not here.
    """
    headers = ["chunk_size", "overlap", "k", "emb_model", "chat_model", "hit_rate", "faithfulness"]
    body: list[list[str]] = []
    for row in report.rows:
        cfg = row.config
        faithfulness = "-" if row.mean_faithfulness is None else f"{row.mean_faithfulness:.2f}"
        body.append(
            [
                str(cfg.chunk_size),
                str(cfg.chunk_overlap),
                str(cfg.k),
                cfg.embedding_model,
                cfg.chat_model,
                f"{row.hit_rate:.2f}",
                faithfulness,
            ]
        )
    widths = [len(h) for h in headers]
    for cells in body:
        widths = [max(w, len(cell)) for w, cell in zip(widths, cells, strict=True)]

    def line(cells: list[str], marker: str) -> str:
        columns = "  ".join(cell.ljust(w) for cell, w in zip(cells, widths, strict=True))
        return f"{marker} {columns}".rstrip()

    lines = [line(headers, " ")]
    for row, cells in zip(report.rows, body, strict=True):
        marker = "*" if report.best is not None and row.config == report.best else " "
        lines.append(line(cells, marker))
    return "\n".join(lines)


# --- Config sweep runner (live re-ingest + index cache; see issue #24, ADR-0010) ------------

# The live half of the sweep: a runner that re-ingests the pack once per *unique* index build,
# wires the built pipelines into the Step-4a `score_sweep` core, and is the engine behind the
# `mnemosyne sweep` command. It re-ingests into an ephemeral temp workspace, never the canonical
# `knowledge/<pack>/` index that `ask`/`eval`/the CI gate depend on, and is report-only: it
# changes no default (choosing defaults and recalibrating the floor is a later step). See ADR-0010.


def _index_key(cfg: SweepConfig) -> tuple[int, int, str]:
    """Dedup key for an index build: ``(chunk_size, chunk_overlap, embedding_model)``.

    These three knobs are the only ones that change the *built* index; ``k`` is retrieval-time
    and ``chat_model`` is generation-time, so two configs that differ only in ``k`` or
    ``chat_model`` share one index build (the cache in :class:`_SweepWorkspace`).
    """
    return (cfg.chunk_size, cfg.chunk_overlap, cfg.embedding_model)


class _SweepWorkspace:
    """Builds and caches one :class:`RagPipeline` per config inside an ephemeral workspace.

    Each unique index build (keyed by :func:`_index_key`) re-ingests the pack into its own
    subdirectory of ``workspace`` (never the canonical ``knowledge/<pack>/`` index), so a grid
    costs O(unique index keys) embeds, not O(grid). Configs that differ only in ``k`` or
    ``chat_model`` reuse a build. ``workspace`` is a temp directory owned by the caller
    (:func:`run_sweep`); when its context exits, every scratch index is removed.
    """

    def __init__(
        self,
        pack: KnowledgePack,
        base_settings: Settings,
        workspace: Path,
        *,
        local_only: bool,
    ) -> None:
        self._pack = pack
        self._base_settings = base_settings
        self._workspace = workspace
        self._local_only = local_only
        # An index build is shared across configs with the same `_index_key`; a pipeline is one
        # per full config, so `retrieve_for` and `generate_for` reuse a single instance per cfg.
        self._index_settings: dict[tuple[int, int, str], Settings] = {}
        self._pipelines: dict[SweepConfig, RagPipeline] = {}
        self._builds = 0

    def _settings_for_index(self, cfg: SweepConfig) -> Settings:
        """Settings whose ``knowledge_dir`` holds ``cfg``'s built index (re-ingest on a miss)."""
        key = _index_key(cfg)
        cached = self._index_settings.get(key)
        if cached is not None:
            return cached
        # A fresh integer-named subdir per build: model names carry `:` / `/`, so never slug them
        # into the path. `model_copy` isolates this index from the canonical `knowledge_dir`.
        scratch = self._base_settings.model_copy(
            update={"knowledge_dir": self._workspace / f"idx{self._builds}"}
        )
        self._builds += 1
        ingest(
            self._pack,
            scratch,
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
            embedding_model=cfg.embedding_model,
            local_only=self._local_only,
        )
        self._index_settings[key] = scratch
        return scratch

    def _pipeline_for(self, cfg: SweepConfig) -> RagPipeline:
        cached = self._pipelines.get(cfg)
        if cached is not None:
            return cached
        pipeline = RagPipeline(
            self._pack, self._settings_for_index(cfg), top_k=cfg.k, chat_model=cfg.chat_model
        )
        self._pipelines[cfg] = pipeline
        return pipeline

    def retrieve_for(self, cfg: SweepConfig) -> Retrieve:
        """The ``retrieve`` of ``cfg``'s pipeline (a ``score_sweep`` retrieval factory)."""
        return self._pipeline_for(cfg).retrieve

    def generate_for(self, cfg: SweepConfig) -> Generate:
        """A ``(question) -> (answer, context)`` closure mirroring ``run_faithfulness_eval``."""
        pipe = self._pipeline_for(cfg)

        def generate(question: str) -> tuple[str, str]:
            answer = pipe.ask(question, cfg.k).text
            context = "\n".join(doc.page_content for doc in pipe.retrieve(question, cfg.k))
            return answer, context

        return generate


def run_sweep(
    pack: str,
    configs: list[SweepConfig],
    *,
    faithfulness: bool = False,
    settings: Settings | None = None,
    local_only: bool = True,
    retrieve_for: Callable[[SweepConfig], Retrieve] | None = None,
    generate_for: Callable[[SweepConfig], Generate] | None = None,
) -> SweepReport:
    """Score ``pack``'s labelled question set across every config in ``configs``.

    Mirrors :func:`run_retrieval_eval` / :func:`run_faithfulness_eval`. When ``retrieve_for`` is
    omitted (the live path), this re-ingests the pack into an **ephemeral temp workspace** (never
    the canonical ``knowledge/<pack>/`` index) once per unique :func:`_index_key`, builds a
    :class:`RagPipeline` per config, and runs them through :func:`score_sweep`; that path needs
    Ollama and a corpus, exactly like ``ask``. ``faithfulness`` also scores answer faithfulness,
    which runs the chat model per config. Injecting ``retrieve_for`` (and optionally
    ``generate_for``) keeps the whole run offline, the way tests do.

    Report-only: it builds no canonical index and changes no default. ``local_only`` defaults to
    ``True`` for a deterministic, offline-corpus run, matching the eval-gate contract (ADR-0010).
    """
    questions = load_questions(pack)
    if retrieve_for is not None:
        return score_sweep(questions, configs, retrieve_for, generate_for=generate_for, pack=pack)
    base_settings = settings or get_settings()
    pack_obj = get_pack(pack)
    # The temp workspace must outlive the whole `score_sweep` call, so it owns the `with` block.
    with TemporaryDirectory() as tmp:
        workspace = _SweepWorkspace(pack_obj, base_settings, Path(tmp), local_only=local_only)
        gen = workspace.generate_for if faithfulness else None
        return score_sweep(questions, configs, workspace.retrieve_for, generate_for=gen, pack=pack)

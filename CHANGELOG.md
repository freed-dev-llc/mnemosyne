# Changelog

All notable changes to Mnemosyne are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- [ADR-0017](docs/architecture/adr/0017-retrieval-quality-known-limitations.md) documenting
  retrieval quality on the served corpus: the `eval-gate` local-only number (0.95) overstates
  served ubiquiti recall (~0.84), why (measurement artifact plus real dilution from fetched
  content), and the deferred work with rationale (a prototyped-but-unshipped reranker, rejected
  corpus pruning, the `adoption-loop` known miss, and a deferred served-corpus eval). ROADMAP
  updated to match.
- Retrieval relevance floor (`score_floor`, default `1.0`): retrieval drops any chunk whose
  embedding distance exceeds the floor, so a query with nothing close enough retrieves nothing
  and `ask` answers "I don't have anything about that in this knowledge base" without an LLM
  call, instead of feeding the model unrelated context. Measured on the ubiquiti eval set, the
  `1.0` default keeps full in-domain recall (18/19, unchanged from no floor) while rejecting
  11/12 deliberately off-topic queries; validated end to end through Argus's `/api/ask` proxy
  against the production index. Adjacent-domain queries (generic BGP/Kubernetes) fall inside the
  in-domain distance band and are not rejected. Set `MNEMOSYNE_SCORE_FLOOR` to retune, or unset
  it to `null` to disable and restore the always-return-top-k behavior.
- Optional embedding normalization (`faiss_normalize`, default off): unit-normalizes vectors at
  build and query time so the FAISS L2 metric ranks identically to cosine, pairing the metric to
  a cosine-trained embedding model. The value is recorded in each index's `meta.json` and must
  match at build and query time. It is a measured no-op for the default `bge-m3` (Ollama returns
  unit-norm vectors, so L2 already equals cosine: identical hit-rate on the ubiquiti eval set),
  kept as opt-in insurance for a future non-normalized embedding model. Set
  `MNEMOSYNE_FAISS_NORMALIZE=true` and rebuild the index to enable.
- Release helper `scripts/sync-spark.sh`: updates a remote install to a git ref (default
  `origin/main`, or a tag/branch/sha) and brings the `mnemosyne-http` service up to date in one
  command. It aborts on a dirty tree, hard-resets to the ref, reinstalls the editable package
  only when `pyproject.toml` changed, restarts the service when the code moved or the running
  version lags the installed one, and health-checks the result. Host and paths are overridable
  via env vars; `--no-restart` syncs without touching the service. Documented in `deploy/README.md`.
- Manual doc staging via `MNEMOSYNE_STAGING_DIR`: a directory outside the repo where a
  contributor drops third-party docs that must never enter git; `ingest` folds any supported
  file under `<staging_dir>/<pack-name>/` into the corpus, exactly like `sources/`. Unset by
  default (and always in CI), so `--local-only` / `eval-gate` determinism is unaffected. See
  [ADR-0016](docs/architecture/adr/0016-manual-doc-staging-via-env-var.md).
- Coverage and a real installable fixture (`examples/dummy-pack/`) for the out-of-tree
  entry-point pack loader, exercising the unpatched `importlib.metadata.entry_points()`
  discovery path end to end. A non-required `dummy-pack-install` CI job installs it and asserts
  it is discovered.
- Test-coverage reporting to Codecov: the `build` job measures `src/mnemosyne` under pytest and
  uploads `coverage.xml` via `codecov-action@v5`. The upload is best-effort (`fail_ci_if_error:
  false`) and Codecov's PR statuses are informational (`codecov.yml`), so `build` stays the only
  required gate. A coverage badge is in the README.

### Changed

- Off-topic questions now return "not in the knowledge base" by default rather than a
  best-effort answer over unrelated chunks: the new `score_floor` (default `1.0`) gates
  retrieval on relevance. Set `MNEMOSYNE_SCORE_FLOOR` to `null` to restore the prior behavior.
- Eval ground truth (ADR-0006) accepts OR-groups: an `expected` item may now be a list of
  interchangeable alternatives, satisfied when any one appears, alongside plain required
  substrings (backward compatible). This lets a correct answer count regardless of source
  wording, e.g. a fetched doc's "Native (untagged) VLAN" satisfies the same item as the seed's
  "untagged network". Applied to the ubiquiti `trunk-vs-access` question, which the fetched
  Switch Port VLAN Assignment page answers correctly in different words.
- README documents the ADR-0009 chat-backend switch (chat can target any OpenAI-compatible
  server; embeddings stay Ollama-only; the `ollama` default is unchanged).
- Single-source-of-truth dedup refactor (zero behavior change): supported corpus suffixes,
  directory scans, the `packs` table, and citation extraction each now live in one place.
- Langchain version-floor pins aligned to the resolved 1.x stack (dependency hygiene only).
- `cli.py` type-hygiene (`X | None` on optional Typer options) plus first CLI test coverage.

### Fixed

- `service.ask` / `service.search` reuse a cached `RagPipeline` per pack (keyed by the index
  mtime) instead of rebuilding it on every request, so a running server picks up a re-ingest on
  the next request without a restart.
- `chunk_documents()`'s own default chunk size/overlap corrected to match `Settings` (500/150).

## [0.3.1] - 2026-06-29

### Added

- Production deployment guide (`deploy/`): a `mnemosyne-http.service` systemd unit template and
  `deploy/README.md` covering prerequisites, running the HTTP server as a managed service, and
  reachability/security, including how Argus consumes it over a mesh network. Pairs with
  [ADR-0015](docs/architecture/adr/0015-paired-vendor-knowledge-packs.md).
- Docs: consuming Mnemosyne from another host over MCP-stdio-over-SSH
  ([`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).
- Release workflow (`.github/workflows/release.yml`): a pushed version tag builds the sdist +
  wheel and opens a draft GitHub release with both artifacts attached.
- Ubiquiti corpus depth: three self-authored primers (network security and segmentation,
  WiFi/RF and roaming, operations), growing the local-only corpus to 4 documents / 42 chunks.
- Ubiquiti eval questions expanded to 19, covering the new primers.

### Changed

- Defaults re-confirmed against the matured corpus and the 19-question set: `chunk_size=500 /
  chunk_overlap=150 / k=5` scores 18/19 (0.95); `DEFAULT_MIN_HIT_RATE` holds at 0.9;
  faithfulness stays report-only. See
  [ADR-0012](docs/architecture/adr/0012-resweep-against-matured-ubiquiti-corpus.md),
  [ADR-0014](docs/architecture/adr/0014-expand-ubiquiti-question-set.md).

### Fixed

- Ingest survives an un-embeddable chunk: a chunk the embedding backend cannot embed (it errors
  or returns a NaN/Inf vector) is skipped with a warning naming its source and offset, instead
  of aborting the whole ingest. See
  [ADR-0013](docs/architecture/adr/0013-ingest-survives-unembeddable-chunk.md).

## [0.3.0] - 2026-06-29

### Added

- Config sweep (`mnemosyne sweep <pack>`, `src/mnemosyne/eval.py`): re-ingests a pack into an
  ephemeral workspace over a chunk-size / overlap / k / model grid, caches index builds, and
  prints a comparison table with a best-config suggestion. Report-only and offline
  (`local_only`). See
  [ADR-0010](docs/architecture/adr/0010-config-sweep-runner.md),
  [ADR-0011](docs/architecture/adr/0011-default-review-against-eval-sweep.md).
- Selectable chat backend (`MNEMOSYNE_CHAT_PROVIDER=ollama|openai`): `openai` targets any
  OpenAI-compatible server (vLLM, llama.cpp, LM Studio); the default `ollama` path is unchanged;
  embeddings stay Ollama-only. See
  [ADR-0009](docs/architecture/adr/0009-selectable-chat-backend.md).
- Retrieval-eval CI gate (`mnemosyne eval <pack> --gate [--min-hit-rate]`): an opt-in regression
  floor over the retrieval hit-rate (exit 2 below the floor). A non-required `eval-gate` CI job
  runs the real retrieval path and is non-blocking by construction. See
  [ADR-0008](docs/architecture/adr/0008-eval-ci-gate-retrieval-regression-floor.md).
- Deterministic `--local-only` ingest: indexes only the local seed corpus and skips URL
  fetches, so the eval-gate corpus is byte-stable and offline.
- Retrieval hit-rate eval (`mnemosyne eval <pack>`): scores "did the right chunk get retrieved?"
  against a labelled question set, no generation. See
  [ADR-0006](docs/architecture/adr/0006-eval-data-contract.md).
- Answer-faithfulness scoring (`mnemosyne eval <pack> -f`): an opt-in grounding proxy (the
  fraction of the answer's word-bigrams present in the retrieved context) with an
  identifier-preserving tokenizer. Report-only. See
  [ADR-0007](docs/architecture/adr/0007-faithfulness-lexical-ngram-overlap.md).

### Fixed

- FAISS import under the conda-forge env: pin the openblas BLAS variant (`libblas=*=*openblas`)
  so `import faiss` no longer fails on a missing oneMKL library. Added an offline regression test
  that builds, persists, loads, and searches a real index.

## [0.2.0] - 2026-06-25

### Added

- HTTP server (`mnemosyne-http`, `src/mnemosyne/http_server.py`): a FastAPI server (`/health`,
  `/packs`, `/ask`, `/search`) for web UIs/services that can't speak MCP (e.g. an Argus dashboard
  "ask the brain" box, called server-to-server). Query logic lives in a shared `service.py` used
  by both transports.
- MCP server (`mnemosyne-mcp`, `src/mnemosyne/mcp_server.py`): a FastMCP stdio server exposing
  `list_packs` / `ask` / `search` so MCP clients (e.g. Argus's agents) can ground answers in
  Mnemosyne. See ADR-0005.
- In-tree `general` knowledge pack: a curated, project-agnostic corpus of operating principles
  and decision heuristics.
- `mnemosyne chat` threads conversation history into the prompt (multi-turn memory).
- Ubiquiti pack populated with 14 public UniFi Help Center URLs; documents are fetched at ingest
  and never committed (only the gitignored FAISS index persists).

### Changed

- `load_url` sends browser-like headers and retries with backoff; a URL that still fails is
  skipped with a warning so one unreachable source can't abort the whole ingest.
- Default models are `bge-m3` (embeddings) and `qwen2.5:1.5b` (chat), `chunk_size=500 /
  chunk_overlap=150 / k=5`, aligned with the
  [rag_ollama](https://github.com/MariyaSha/rag_ollama) tutorial the pipeline is based on.
- PDF loading uses LangChain's `PyPDFLoader` (one Document per page).
- Environment managed with mamba/conda via `environment.yml` (CPU) and `environment-gpu.yml`
  (GPU); FAISS comes from conda-forge (`faiss-cpu` moved to an optional `cpu` extra). See
  ADR-0004.

### Fixed

- Documentation accuracy pass: describe the shipped MCP/HTTP serving layer as built rather than
  roadmap; correct default models across examples / README / docs; correct the FAISS index path;
  align the README Python version with the badge/pyproject (3.11+).

## [0.1.0] - 2026-06-23

### Added

- Initial scaffold of Mnemosyne: a local, teaching-first RAG pipeline (Ollama + LangChain +
  FAISS).
- Pipeline modules (`loaders`, `chunking`, `embeddings`, `index`, `pipeline`, `prompts`, `llm`,
  `config`): load → chunk → embed → FAISS → retrieve → generate, end to end.
- Knowledge-pack framework (`packs/base`, `packs/registry`) with in-tree + entry-point
  discovery, mirroring Argus vendor packs (ADR-0005).
- In-tree Ubiquiti / UniFi knowledge pack with a self-authored seed corpus so the quickstart
  runs with no network access.
- CLI (`mnemosyne`): `packs`, `ingest`, `ask`, `chat`, `version`.
- Teaching docs: `RAG-101`, `ARCHITECTURE`, `KNOWLEDGE_PACKS`, `ROADMAP`, ADRs 0001-0003.
- Branding (logo, icon) and the freed-dev-llc repo baseline (Apache-2.0, CI, Dependabot,
  issue/PR templates, CODEOWNERS).

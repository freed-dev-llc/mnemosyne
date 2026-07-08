# Changelog

All notable changes to Mnemosyne are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-07-08

### Added

- Third knowledge pack, `opnsense`
  ([ADR-0027](docs/architecture/adr/0027-third-knowledge-pack-opnsense.md),
  [ADR-0024](docs/architecture/adr/0024-second-knowledge-pack-pfsense.md)): a sibling of
  `pfsense` and the first fork-sibling pack, proving the knowledge-pack model holds even when
  two vendors share a codebase. Curated seed of 3 self-authored primers (core concepts,
  plugins, firewall model and intrusion detection) plus 11 curated questions that clear the
  0.9 retrieval gate at 11/11 on a local-only scratch index (bge-m3, 500/150; 3 docs / 16
  chunks). The gated anchors favor facts that distinguish OPNsense from pfSense rather than
  facts the two share: the `os-` plugin system installed from System > Firmware > Plugins,
  the Zenarmor plugin (formerly Sensei, package `os-sensei`), Suricata built into the base
  under Services > Intrusion Detection, the Phalcon MVC web GUI, and the Community versus
  Business editions. The primers are original prose stating public, non-copyrightable
  OPNsense facts, grounded in but copied from none of the OPNsense documentation, which is
  itself BSD-2-Clause (permissive, unlike the Netgate and Ubiquiti Help Center declines).
  Curated-only (`sources.yaml urls: []`). Wired into the CI `eval-gate` as a third gated pack.
- Ubiquiti pack curated re-grow ([ADR-0014](docs/architecture/adr/0014-expand-ubiquiti-question-set.md),
  [ADR-0020](docs/architecture/adr/0020-fetched-coverage-questions.md),
  [ADR-0026](docs/architecture/adr/0026-ubiquiti-help-center-harvest-declined-curated-only.md)):
  3 new self-authored primers (VPN and remote access: Site Magic, WireGuard, Teleport; DNS,
  resolution, and multicast; QoS and traffic management) and 9 identifier-anchored curated
  questions, growing the ubiquiti set from 19 to 28 and clearing the 0.9 retrieval gate at
  28/28 on a local-only scratch index (bge-m3, 500/150; 4 docs / 43 chunks to 7 docs / 65
  chunks). Restores VPN, DNS, and QoS coverage the declined help.ui.com harvest used to serve,
  without reproducing any of it: every fact is public and non-copyrightable (product names,
  IANA/IEEE numbers, DNS record types) in original prose. Curated-only, as before
  (`sources.yaml urls: []` unchanged).
- pfSense pack R2 curated coverage expansion
  ([ADR-0025](docs/architecture/adr/0025-netgate-docs-harvest-declined-curated-only.md),
  [ADR-0024](docs/architecture/adr/0024-second-knowledge-pack-pfsense.md)): 3 new self-authored
  primers (aliases and advanced rules; multi-WAN and traffic shaping; diagnostics and backup)
  and 8 identifier-anchored curated questions, growing the pfSense set from 17 to 25 and
  clearing the 0.9 retrieval gate at 25/25 on a local-only scratch index (bge-m3, 500/150; 6
  docs / 22 chunks to 9 docs / 37 chunks). Recovers the Step-12/13 deferred `aliases` /
  `floating-rules` pair: the new aliases-and-advanced-rules primer gives those facts a
  co-located chunk that now reaches k=5. A fetched Netgate documentation harvest was reviewed
  and declined on licensing grounds (ADR-0025): the current docs carry an all-rights-reserved
  notice with no reuse grant, so the pack stays curated-only (`sources.yaml urls: []`
  unchanged).
- pfSense pack R1 curated coverage expansion
  ([ADR-0024](docs/architecture/adr/0024-second-knowledge-pack-pfsense.md),
  [ADR-0020](docs/architecture/adr/0020-fetched-coverage-questions.md)): 3 new self-authored
  primers (high availability: CARP, pfsync, XMLRPC config sync; packages: Snort/Suricata
  IDS/IPS, pfBlockerNG DNSBL/GeoIP; DNS services: Unbound resolver, dnsmasq forwarder) and 7
  identifier-anchored curated questions, growing the pfSense set from 10 to 17 and clearing the
  0.9 retrieval gate at 17/17 on a local-only scratch index (bge-m3, 500/150; 3 docs / 14 chunks
  to 6 docs / 22 chunks). The Step-12 deferred pair (`aliases`, `floating-rules`) was retested
  against the larger index and still misses at k=5, so it stays out of the gated set as a
  documented recall-rank gap, same class as
  [ADR-0021](docs/architecture/adr/0021-hybrid-retrieval-evaluation.md). Curated-only: no
  fetched URLs added (`sources.yaml urls: []` unchanged).
- Second knowledge pack, `pfsense`
  ([ADR-0024](docs/architecture/adr/0024-second-knowledge-pack-pfsense.md)): the first in-tree
  vendor expert beyond the `ubiquiti` worked example, proving the knowledge-pack model
  ([ADR-0003](docs/architecture/adr/0003-knowledge-packs.md)) generalizes to a real second
  vendor with no pipeline edits. Curated seed of 3 self-authored primers (core concepts,
  firewall rules, NAT and VPN) plus 10 curated questions that clear the 0.9 retrieval gate at
  10/10 on a local-only scratch index (bge-m3, 500/150). The primers are original prose stating
  public, non-copyrightable pfSense facts grounded in (not copied from) the Netgate docs, so the
  "ship no third-party documentation" rule holds. Wired into the CI `eval-gate` as a second gated
  pack. Two candidate questions (`aliases`, `floating-rules`) are deferred as a known
  retrieval-rank gap, same class as `ubiquiti`'s `port-profiles` / `poe-cycle`
  ([ADR-0021](docs/architecture/adr/0021-hybrid-retrieval-evaluation.md)).
- Fetched-coverage eval questions for the batch-1 Help Center articles, extending the
  [ADR-0020](docs/architecture/adr/0020-fetched-coverage-questions.md) contract to the
  [ADR-0023](docs/architecture/adr/0023-help-center-harvest-batch-1.md) harvest: 9
  identifier-anchored questions added to the ubiquiti pack's `questions.yaml`, each tagged
  `corpus: fetched` and guarding one previously-unguarded batch-1 article (Site Magic /
  SD-WAN, WireGuard 51820, Teleport 24h, backup `.unf`, factory-reset hold time, DNS
  Forward Domain, DNS UDP Port 53, Channel AI, switch-port QoS DSCP / IP Precedence). Every
  anchor co-locates in one served-index chunk at k=5 and union-misses the local-only index
  (scratch-verified on the Spark; the existing 32 questions are unchanged at 30/32,
  projected served eval 39/41 after the post-merge re-ingest). The `dns-record-types`
  `[CNAME, SRV]` candidate was a measured k=5 recall gap and is deferred — same class as
  ADR-0020's rejected candidates — so DNS Records is guarded by `dns-forward-domain`
  instead. The loader still excludes fetched questions by default, so the CI gate's
  local-only population (19 curated, floor 0.9) is unchanged by construction; no new ADR.
- Help Center harvest, batch 1 completion — the deferred `Maximizing-Wireless-Speeds`
  article ([ADR-0023](docs/architecture/adr/0023-help-center-harvest-batch-1.md)): held out
  of batch 1 because it displaced the `channel-2-4ghz` primer chunk from top-5, it now lands
  together with the ground-truth wording fix that disposition called for. The
  `channel-2-4ghz` question's first expected item is shortened to `"1, 6, and 11"` — the
  common factual substring of both the local RF primer ("non-overlapping channels: 1, 6, and
  11") and the fetched article ("channels 1, 6, and 11") — so the fact counts regardless of
  which source serves it, without an OR-group. Same ground-truth treatment the
  `trunk-vs-access` question received
  ([ADR-0006](docs/architecture/adr/0006-eval-data-contract.md) OR-group precedent) when a
  fetched page answered correctly in different words. Article text is fetched at ingest and
  never enters git. Scratch-verified per question on the Spark: local-only 19/19, full
  expanded 30/32 with zero flips (the two remaining misses are the known served rank
  problems, `port-profiles` and `poe-cycle`, ADR-0021). Production re-ingest follows
  post-merge under the backup/restore protocol.

### Changed

- The ubiquiti pack reverts to curated-only: the fetched Ubiquiti Help Center harvest
  (help.ui.com) was reviewed and declined on licensing grounds
  ([ADR-0026](docs/architecture/adr/0026-ubiquiti-help-center-harvest-declined-curated-only.md),
  mirroring the Netgate decline in
  [ADR-0025](docs/architecture/adr/0025-netgate-docs-harvest-declined-curated-only.md)).
  Ubiquiti's Terms of Service expressly forbid reproducing Help Center Content without written
  permission. Removed the 24 `help.ui.com` URLs (`sources.yaml urls: []`), the 22
  `corpus: fetched` eval questions, and the vestigial title-cleanup `pack.py`; the 4
  self-authored primers and 19 curated questions are unchanged. On re-ingest the served index
  goes 28 docs / 438 chunks → 4 docs / 43 chunks and the served eval goes 39/41 → 19/19 (the
  two curated dilution victims `port-profiles` / `poe-cycle` recover). The generic ADR-0020
  `--include-fetched` loader is retained for any future, properly-licensed corpus.

## [0.5.0] - 2026-07-07

### Added

- Help Center harvest, batch 1
  ([ADR-0023](docs/architecture/adr/0023-help-center-harvest-batch-1.md)): 9 verified
  help.ui.com articles added to the ubiquiti pack's `sources.yaml` (VPN incl. WireGuard and
  Teleport, console backups/migration and factory reset, DNS records and troubleshooting,
  WiFi optimization, QoS/traffic shaping; article text is fetched at ingest and never enters
  git). Landed against a pre-agreed dilution bar, measured per-question on a scratch index:
  30/32 at 27 docs / 421 chunks, zero unexplained flips, fetched coverage 13/13. The bar
  tripped once on the 10-article draft: `Maximizing-Wireless-Speeds` genuinely answers the
  `channel-2-4ghz` question in different words, so it is deferred to land with that
  question's OR-group fix rather than rejected. Fetch-health finding recorded: help.ui.com's
  403s are client-header-dependent (a CDN challenge to bare HTTP clients; the loader's
  browser-like headers pass), not network-dependent.
- [ADR-0021](docs/architecture/adr/0021-hybrid-retrieval-evaluation.md): re-measured hybrid
  BM25+dense retrieval on the 32-question instrument (ADR-0020) under a pre-registered
  method (pinned BM25 parameters, blend, alpha grid, stratified dev/held-out split with a
  fixed seed, dev-only config selection, one held-out evaluation) and decided not to
  productize: the dev table was flat at baseline across the whole grid, the dev-chosen
  config regressed both the held-out subset (13/15 -> 12/15) and the full served set
  (29/32 -> 28/32), and ADR-0017's prototype lift (0.79 -> 0.84) did not reproduce under
  the pinned normalization and tokenizer. A decision record only; the shipped retrieval
  path is unchanged. Per-miss rank diagnostics and the two unscored probe outcomes are
  recorded for future corpus and question-set work, with revisit triggers.
- Fetched-coverage eval questions with a per-question `corpus` tag
  ([ADR-0020](docs/architecture/adr/0020-fetched-coverage-questions.md)): 13 ubiquiti
  questions authored from the served index's fetched Help Center chunks under an
  identifier-anchored ground-truth policy (port numbers, protocol/standard names, commands,
  feature names; no third-party prose), each tagged `corpus: fetched` in `questions.yaml` and
  verified live before landing (expected strings co-locate in one served-index chunk at k=5;
  union-miss on local-only). The loader excludes them by default, so the CI gate's local-only
  population (19 questions, floor 0.9) is unchanged by construction; `mnemosyne eval
  --include-fetched` opts in (it refuses `--gate`/`--min-hit-rate`, whose floor is calibrated
  to the curated population), JSON results carry the `corpus` field, and
  `scripts/eval-served.sh` passes the flag so the served history measures coverage plus
  survival (series `total` 19 -> 32).
- Served-corpus eval, report-only (`mnemosyne eval <pack> --json`;
  [ADR-0019](docs/architecture/adr/0019-served-corpus-eval-report-only.md)): one
  machine-readable JSON line per run carrying the scores plus the provenance that says which
  index was measured (index meta with the chunk-count discriminator, effective `score_floor` /
  `faiss_normalize`, installed version, UTC timestamp; no host coordinates).
  `scripts/eval-served.sh` appends it to gitignored `knowledge/eval-history/<pack>.jsonl`, and
  opt-in systemd templates (`deploy/mnemosyne-eval.service` + `.timer`) run it weekly. Exit 0
  on every completed run, and retrieval-only: `--json` refuses `--faithfulness` and `--gate`
  (a posture clash is an operational error, exit 1, before any eval runs). Documented in
  `deploy/README.md`, including the caveat that the 19 ubiquiti questions measure curated-fact
  survival under fetched-content dilution, not fetched-content coverage.
- [ADR-0018](docs/architecture/adr/0018-nemotron-embedder-evaluation.md): evaluated
  `llama-embed-nemotron-8b` as an embedder candidate and decided not to adopt (the community
  GGUF produces no embeddings via Ollama, and the research-only license blocks production
  use); `bge-m3` and all retrieval defaults are unchanged. A decision record only, with the
  reusable low-k headroom baseline (hit@1 0.53 / hit@2 0.84) for scoring future candidates;
  no behavior change.

### Fixed

- The `adoption-loop` eval question no longer misses by construction
  ([ADR-0022](docs/architecture/adr/0022-seed-corpus-boundary-repair.md)): the seed
  primer's adoption-loop sentence now names the factory-reset remedy inline (one
  contiguous two-line rewrite in `seed-unifi-concepts.md`; the question and its expected
  strings are byte-identical), so the fact fits inside one 500/150 chunk instead of
  splitting across a boundary, the root cause on record since ADR-0011. Scratch-verified
  per question on the Spark: local-only 19/19 with all 18 previously-hitting questions
  re-verified, full ingest 30/32 with fetched coverage 13/13 unchanged (the two remaining
  misses are the known served rank problems, ADR-0021). Production re-ingest follows
  post-merge under the backup/restore protocol recorded in the ADR.
- Docs accuracy after the 2026-07-04 history re-creation: six accepted ADRs (0010, 0012,
  0013, 0014, 0016, 0017) now carry a dated editorial note that their issue/PR numbers use
  pre-rewrite numbering and no longer resolve (decision text untouched; ADR-0018's
  `ollama/ollama` references are upstream-qualified and stay). The ROADMAP's served-corpus
  eval box is flipped to shipped, citing
  [ADR-0019](docs/architecture/adr/0019-served-corpus-eval-report-only.md) instead of
  calling the eval deferred, with the frozen-snapshot alternative described as rejected.
- The documented `score_floor` disable now parses from the environment:
  `MNEMOSYNE_SCORE_FLOOR=none` (synonyms: `null` or an empty value, case-insensitive) disables
  the relevance floor and restores the always-return-top-k behavior. Previously every such
  spelling failed pydantic `float_parsing`, so the floor could not be turned off via env
  despite config.py and the 0.4.0 notes saying it could. Numeric values and the Python-side
  `score_floor=None` are unchanged; anything else still fails validation.
- Docs caught up to the 0.4.0 retrieval behavior: `.env.example` now lists
  `MNEMOSYNE_SCORE_FLOOR` and `MNEMOSYNE_FAISS_NORMALIZE`, and the README, `docs/ARCHITECTURE.md`,
  and `docs/RAG-101.md` note the relevance floor (an off-topic question answers "not in the
  knowledge base" instead of guessing over unrelated chunks).

## [0.4.0] - 2026-07-04

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

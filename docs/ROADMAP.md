# Roadmap

Mnemosyne starts as a *teaching* RAG pipeline and grows toward a *useful* one — a local
knowledge brain for the freed-dev-llc family, starting as a cited expert for
[Argus](https://github.com/freed-dev-llc/argus). Versions are intentionally small and
demonstrable.

## v0.1 — the loop works (shipped)

The end-to-end RAG loop, legible and local.

- [x] Repo + branding, Apache-2.0, CI/Dependabot baseline.
- [x] Pipeline modules: load → chunk → embed (Ollama) → FAISS → retrieve → generate.
- [x] Knowledge-pack framework + in-tree `ubiquiti` pack (structure + starter source list).
- [x] CLI: `ingest`, `ask`, `chat`, `packs`.
- [x] First green ingest + cited answer against a real local Ubiquiti corpus.

## v0.2 — measure it (shipped)

You cannot improve what you cannot measure. RAG quality is invisible without evals.

- [x] Eval harness — **retrieval hit-rate** (did the right chunk get retrieved?): substring
      ground truth scored over the top-k retrieved chunks, exposed as `mnemosyne eval`. See
      [ADR-0006](architecture/adr/0006-eval-data-contract.md).
- [x] Eval harness, **answer faithfulness** (did the answer stick to the context?): lexical
      bigram overlap with an identifier-preserving tokenizer, reported by `mnemosyne eval -f`.
      See [ADR-0007](architecture/adr/0007-faithfulness-lexical-ngram-overlap.md).
- [x] A small labelled question set for the Ubiquiti pack.
- [x] CI gate: a non-blocking `eval-gate` job that fails soft when retrieval hit-rate drops below
      a regression floor (faithfulness stays report-only, since weak retrieval can inflate it).
      See [ADR-0008](architecture/adr/0008-eval-ci-gate-retrieval-regression-floor.md).
- [x] Chunking/`k`/model sweeps so defaults are chosen from data, not vibes. Sweep shipped
      (4a/4b); defaults (`500/150/k=5`) and the 0.9 floor reviewed against the ubiquiti
      labelled set and kept, faithfulness stays report-only. See
      [ADR-0011](architecture/adr/0011-default-review-against-eval-sweep.md).

## v0.3 — serve it (shipped)

Make Mnemosyne callable by other services and agents.

- [x] MCP transport (stdio, `mnemosyne-mcp`) exposing `list_packs`, `ask`, `search` tools — so
      coding agents such as [Argus](https://github.com/freed-dev-llc/argus) can consult
      Mnemosyne. See [ADR-0005](architecture/adr/0005-mcp-server.md).
- [x] MCP client registration mirroring the Argus pattern.
- [x] FastAPI HTTP server (`mnemosyne-http`: `/health`, `/packs`, `/ask`, `/search`) — for web
      UIs/services that can't speak MCP (e.g. an "ask the brain" box in the Argus dashboard).

## v0.x — vendor-pack parity with Argus (current)

The long game: every vendor [Argus](https://github.com/freed-dev-llc/argus) can *discover*,
Mnemosyne can *explain*. Knowledge packs expand in lockstep with Argus vendor packs.

- [ ] Ubiquiti corpus matured (real docs, evaluated). v0.3.1 grew it from the single seed note to
      4 self-authored primers (security, WiFi/RF, operations) / 42 chunks and an eval set of 19
      questions at 0.95 retrieval hit-rate
      ([ADR-0012](architecture/adr/0012-resweep-against-matured-ubiquiti-corpus.md),
      [ADR-0014](architecture/adr/0014-expand-ubiquiti-question-set.md)); a first-party harvest of
      official UniFi docs is still outstanding (help.ui.com 403s from some networks).
- [ ] Second vendor pack proving the out-of-tree entry-point path.
- [ ] Shared vendor list / cross-links with Argus so the two stay in step.
- [ ] Ship the UniFi/Ubiquiti vendor as one distribution advertising both `argus.vendor_packs`
      and `mnemosyne.knowledge_packs`, so installing it sets up both deployments
      ([ADR-0015](architecture/adr/0015-paired-vendor-knowledge-packs.md)).
- [ ] Optional: hybrid retrieval (BM25 + vector), reranking, and per-pack model tuning. A hybrid
      dense + BM25 reranker was prototyped (it lifts served ubiquiti recall 0.79 -> 0.84) but not
      shipped, pending a larger held-out question set; see
      [ADR-0017](architecture/adr/0017-retrieval-quality-known-limitations.md); an embedder swap
      to llama-embed-nemotron-8b was evaluated and rejected, see
      [ADR-0018](architecture/adr/0018-nemotron-embedder-evaluation.md).
- [ ] Served-corpus eval visibility: `eval-gate` measures the local-only corpus, so it overstates
      what a running server retrieves (served ubiquiti is ~0.84, not the 0.95 CI reports). A
      non-gating served eval or a frozen staged snapshot is deferred on determinism grounds
      (ADR-0016, issue #60); see
      [ADR-0017](architecture/adr/0017-retrieval-quality-known-limitations.md).

## Non-goals (for now)

- Not a hosted/multi-tenant service — home/lab + family use.
- Not a general document chat UI — the value is *packaged experts*, not a file dropbox.
- No cloud LLM dependency — local-first via Ollama is a feature, not a limitation.

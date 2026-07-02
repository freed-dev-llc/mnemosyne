# 10. Config-sweep runner: ephemeral per-config re-ingest with an index cache

Date: 2026-06-28

## Status

Accepted

## Context

Step 4a (ADR is this file's predecessor work, issue #24) shipped the pure, offline sweep core:
`SweepConfig`, `expand_grid`, `score_sweep`, `_best_config`, and `format_sweep_table`. That core
scores a grid over injected `retrieve` / `generate` factories, so it runs with no Ollama and no
network, but it does not build anything: it has no way to turn a chunking config into a real
index, and no user surface.

This step adds the live half. A sweep needs to *measure* configs that differ in chunk size,
chunk overlap, k, and the two models, which means re-ingesting the corpus, because chunk size,
chunk overlap, and the embedding model all change the built FAISS index. The constraints: a
sweep must not touch the single canonical `knowledge/<pack>/` index that `ask`, `eval`, and the
`eval-gate` CI job depend on; it must not re-embed the whole grid when many configs share an
index; and it must change no shipped default (choosing `chunk_size` / `chunk_overlap` / `k` from
the table, and recalibrating `DEFAULT_MIN_HIT_RATE` against it, is a deliberate follow-up).

## Decision

1. **A dedicated `mnemosyne sweep <pack>` subcommand; `eval` stays single-config.** The sweep is
   a separate user surface, not a `--sweep` flag on `eval`. `eval` keeps its report-or-gate
   contract (ADR-0008) untouched. Each sweep axis is a repeatable option (`--chunk-size`,
   `--chunk-overlap`, `--k`, `--embedding-model`, `--chat-model`) that falls back to the shipped
   default, so a bare invocation runs a one-config sanity sweep.

2. **Ephemeral per-config re-ingest in a temp workspace; the canonical index is never touched.**
   `run_sweep` re-ingests into a `tempfile.TemporaryDirectory`, removed when the run ends. The
   only lever is `settings.model_copy(update={"knowledge_dir": <temp subdir>})`: both `ingest`
   and `RagPipeline` resolve their path through `index_dir(pack, settings)`, so a per-config
   `knowledge_dir` fully isolates each index. No change to `index_dir`, `Settings`, or the
   canonical `knowledge_dir`.

3. **Index cache keyed on `(chunk_size, chunk_overlap, embedding_model)`.** Those three knobs are
   the only ones that change the built index; `k` is retrieval-time and `chat_model` is
   generation-time. Configs that differ only in `k` or `chat_model` reuse one index build, so the
   grid costs O(unique index keys) embeds, not O(grid). `_index_key` is a pure, tested function;
   the cache lives in `_SweepWorkspace`, which builds at most one `RagPipeline` per config.

4. **`local_only=True` for the sweep.** Re-fetching URLs across N configs is slow and flaky, and
   the labelled `expected` substrings are authored from the local seed corpus, the same contract
   the `eval-gate` CI job uses (ADR-0008). It is a `run_sweep` parameter, not a CLI flag this
   step, so a later step can surface a flag without a signature change.

5. **Report-only; always exit 0; changes no default.** No gate, no `--min-hit-rate`, no threshold
   on the sweep; the gate stays on `eval`. The best-config line is a suggestion, not an applied
   change. Acting on the table, revisiting the `500/150`, `k=5` defaults and re-measuring
   `DEFAULT_MIN_HIT_RATE` against it, is the follow-up step.

6. **`n` (faithfulness n-gram size) is not a swept axis and not a CLI flag.** It stays the
   `score_faithfulness` keyword default, carrying over ADR-0007 §2 and the Step 4a lock.

## Consequences

- A grid embeds once per unique index key, not once per config: sweeping `k` or `chat_model` over
  a fixed chunking is close to free on the embedding side.
- The comparison table is a presentation aid. No default changes from running a sweep; the
  data-chosen cut point is a separate, reviewable step.
- Sweeping `chat_model` without `--faithfulness` produces rows that differ only in the chat-model
  column (retrieval ignores the chat model). This is accepted and documented in the `--chat-model`
  help; faithfulness scoring runs the chat model per config and is opt-in via `--faithfulness`.
- The temp workspace means a sweep leaves no artifact on disk. Persisting sweep results (CSV/JSON)
  is out of scope this step and noted as a later gap.
- The runner takes the same injected-factory seam as `run_retrieval_eval` / `run_faithfulness_eval`
  (`retrieve_for` / `generate_for`), so the dedup logic, the temp-workspace isolation, and the CLI
  wiring are all unit-tested offline with no Ollama and no network.

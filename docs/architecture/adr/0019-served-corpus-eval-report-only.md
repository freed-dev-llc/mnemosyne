# 19. Served-corpus eval: report-only snapshots with recorded provenance

Date: 2026-07-06

## Status

Accepted

## Context

The `eval-gate` CI job (ADR-0008) scores retrieval against the deterministic local-only
corpus (ADR-0016, `--local-only`): ubiquiti 18/19 (0.95). The production server answers
from a different index: 294 chunks (42 curated + 252 fetched Help Center chunks), where
recall measured 16/19 (0.84) as a one-off by hand. That 0.84 is ADR-0017's number and is
the reference point here; nothing was re-measured for this ADR. The gap itself is
ADR-0017's subject; the operational problem this ADR closes is that the served number was
invisible: nothing recorded it, nothing showed drift when fetched content changed or a
re-ingest landed. ADR-0017 item 4 defers exactly this and names the shape: "a non-gating
served eval."

`mnemosyne eval <pack>` already scores the canonical built index, so run on the serving
host it is a served eval. What was missing: provenance (nothing said whether a report
measured the 42-chunk local or the 294-chunk served index), machine-readable output, and
history.

## Decision

- **Measure the live canonical index, in place.** `mnemosyne eval <pack> --json` emits one
  JSON line per run: the scores (`k`, `total`, `hits`, `hit_rate`, per-question results
  with misses) plus the provenance that identifies the run: the index block from
  `meta.json` (documents, chunks, embedding_model, chunk_size, chunk_overlap; `chunks` is
  the served-vs-local discriminator, 294 vs 42), the effective `score_floor` and
  `faiss_normalize`, the installed version, and a UTC timestamp. Deliberately absent: any
  host coordinate, because history lines get pasted into issues.
- **Runs on the serving host, in-process, via the CLI.** `scripts/eval-served.sh` appends
  the line to `knowledge/eval-history/<pack>.jsonl`: gitignored under `knowledge/`, outside
  any pack's index directory so a re-ingest cannot clobber it. Opt-in systemd templates
  (`deploy/mnemosyne-eval.service` + `.timer`) run it weekly with `Persistent=true`;
  `deploy/README.md` documents the timer, the manual run after every production re-ingest,
  and how to read the history with `jq`.
- **Report-only, exit 0 always.** No gate, no alert threshold: the number moves with
  content drift, so a hard floor would flake (ADR-0017's own rationale for not gating the
  served corpus). Trend review is human, over the history file.
- **The `--json` surface is retrieval-only and minimal.** Combining it with
  `--faithfulness` or `--gate`/`--min-hit-rate` is an error (those are different postures);
  `--show-misses` is ignored because misses are always serialized.

## Rejected alternatives

- **Fresh fetched rebuild at eval time.** Conflates fetch health (Help Center 403
  flakiness) with retrieval quality: the eval would measure the network, not the index.
- **Frozen third-party snapshot.** Stores Help Center content durably, a licensing line we
  do not cross without an explicit call, and it goes stale (ADR-0016).
- **Run it in CI.** CI cannot reach the serving host, cannot rebuild the fetched corpus
  deterministically, and hits the same licensing wall.
- **Score over HTTP (`/search`).** Would also exercise the serving path and is noted as
  future work, but it is a bigger surface than this step needs; the in-process CLI on the
  same host measures the same index.

## Consequences

- Production retrieval quality becomes a recorded trend instead of a one-off number: `jq`
  over the history file answers "did the last re-ingest move recall?".
- The 19 questions measure curated-fact survival under fetched-content dilution, not
  fetched-content coverage: a drop means fetched chunks are displacing curated answers; a
  flat line says nothing about how well the fetched pages themselves are retrieved.
- The first live history entry happens post-merge, after `sync-spark.sh` updates the host;
  offline tests verify the serializer and the CLI surface.
- Deferred, in ADR-0017's spirit of not overfitting the 19-question set: eval-over-HTTP,
  question-set expansion over fetched content (also what a productized reranker waits on),
  and any alerting or gating on the served number.

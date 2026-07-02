# 13. Ingest survives an un-embeddable chunk: skip and warn

Date: 2026-06-29

## Status

Accepted

Fixes issue #40. Removes the constraint [ADR-0012](0012-resweep-against-matured-ubiquiti-corpus.md)
worked around when it excluded the `chunk_size=300` sweep axis.

## Context

ADR-0012's re-sweep hit a hard crash. bge-m3 via Ollama returns NaN (HTTP 500,
`failed to encode response: json: unsupported value: NaN`) for a specific valid chunk that forms
only at `chunk_size=300`, and the unhandled `ResponseError` aborted the entire ingest, and with it
the whole sweep. `build_index` used `FAISS.from_documents`, which embeds the chunk texts as one
batch, so a single NaN fails the whole call.

This is not specific to that one chunk: any corpus can contain text the embedding backend maps to
NaN, and the failure mode (one bad chunk takes down the whole index build) is the problem. The
loader already takes the opposite, resilient stance one layer up: `KnowledgePack.load` logs and
skips a URL it cannot fetch so one unreachable source does not abort the ingest. Embedding had no
equivalent.

## Decision

`build_index` now embeds defensively. The fast path is unchanged in spirit: one batch
`embed_documents` call, and if it succeeds and every vector is finite, all chunks are kept. Only on
a batch error or a non-finite vector does it fall back to embedding chunk by chunk, skipping any
chunk that raises or returns a NaN/Inf vector with a warning that names the chunk's source and
offset, then building the index from the survivors via `FAISS.from_embeddings`. It raises
`ValueError` only when no chunk could be embedded at all.

Skip-and-warn, not fail-clear: this matches the resilience the loader already gives an unreachable
URL (one un-embeddable chunk, like one un-fetchable source, must not abort the whole ingest). The
warning makes the dropped chunk visible rather than silent, and the shipped default (`chunk_size`
500) never trips the bug, so production and CI ingests are unchanged.

The ingest summary and `meta.json` now report the count of chunks actually embedded and indexed
(`store.index.ntotal`), which equals the created-chunk count on a clean run and is lower only when a
chunk was skipped.

## Rejected alternative

Fail the ingest with a clear, chunk-identifying error instead of skipping. It avoids any silent data
loss, but one un-embeddable chunk would still block the whole corpus until someone edited it, which
is exactly the brittleness the loader's URL handling already rejects. The logged skip warning gives
the same visibility without the hard stop.

## Consequences

- An ingest no longer aborts when the embedding backend cannot embed a chunk; the chunk is dropped
  with a named warning and the rest is indexed.
- The `chunk_size=300` sweep axis that ADR-0012 had to exclude now runs. Re-measured, it scores
  0.80, which confirms ADR-0012's read that it is the weakest axis and does not change the kept
  defaults.
- `meta.json` `chunks` is the indexed count. No reader depends on it equaling the created-chunk
  count (it is display-only in `service.py`).
- The upstream bge-m3/Ollama NaN is not otherwise worked around: Mnemosyne survives it, it remains a
  backend defect. Closes #40.

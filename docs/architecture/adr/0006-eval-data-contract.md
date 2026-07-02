# 6. Retrieval-eval ground truth is expected substrings

Date: 2026-06-27

## Status

Accepted

## Context

v0.2 is about *measuring* RAG quality. The first metric is **retrieval hit-rate**: given a
labelled question, did retrieval surface the chunk(s) that actually contain the answer? To
score that we need a ground-truth representation for "the right text," and there are three
obvious candidates:

1. **Document identity** — mark which source document should be retrieved. Useless here: the
   Ubiquiti pack is a single self-authored seed file, so every question would trivially
   "hit" the one document.
2. **Chunk IDs** — pin the expected chunk indices. Brittle: chunk boundaries are a function
   of `chunk_size`/`chunk_overlap`, and Step 4 of this milestone *sweeps those values*. Any
   re-chunking would invalidate every label, so the labelled set could never outlive a sweep.
3. **Expected substrings** — short strings, drawn verbatim from the corpus, that the answer
   text must contain.

## Decision

Ground truth is **expected substrings**. Each labelled question carries an `expected` list,
and a question **hits** iff **every** string in that list appears (case-insensitive) in the
concatenated `page_content` of the top-k retrieved chunks. **retrieval hit-rate@k** =
hits / total.

The labelled set lives at `packs/<pack>/eval/questions.yaml`, loaded by convention (no new
manifest field — the manifest schema stays untouched). Every `expected` string is authored
verbatim from the pack's own corpus text, so the labels assert "this corpus content was
retrieved," independent of how it was chunked.

## Consequences

- **Chunking-invariant.** The labelled set survives the Step 4 chunking/`k`/model sweeps —
  the property that makes a sweep measurable rather than self-invalidating.
- **Corpus-agnostic.** Works for a one-file seed corpus today and a multi-document corpus
  later, with no change to the scorer.
- **Exact and legible.** The match is a plain case-insensitive substring test over the
  retrieved text — no embeddings, no LLM, no fuzzy threshold to tune. The scorer is a pure
  function and tests run fully offline.
- **Authoring discipline.** A question is only valid if its `expected` strings exist in the
  corpus; an ungroundable question is dropped, not invented. This keeps the eval honest but
  means labels must be revised when the corpus text changes.
- **Scope.** This contract covers *retrieval* only. Answer faithfulness (did the generated
  answer stay grounded?) is a separate, harder decision and is deferred to a later step.

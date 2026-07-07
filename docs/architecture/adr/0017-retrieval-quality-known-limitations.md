# 17. Retrieval quality on the served corpus: known limitations and deferred work

Date: 2026-07-04

## Status

Accepted

Editorial note (2026-07-07): issue/PR numbers cited in this ADR use pre-rewrite
numbering; the repository history was re-created on 2026-07-04, so those references no
longer resolve.

## Context

The `eval-gate` (ADR-0008) scores retrieval against the deterministic local-only corpus
(ADR-0016, `--local-only`): the ubiquiti pack is 18/19 (0.95). But a running `mnemosyne-http`
serves a different index. Production additionally ingests 14 fetched UniFi Help Center pages
(252 chunks) on top of the 42 hand-authored seed chunks. Measured on that served 294-chunk
index, retrieval scores 16/19 (0.84) with the eval fix below, 15/19 before it. CI overstates
what a running server actually retrieves.

The gap has two causes, established by inspecting the retrieved chunks:

- **Measurement artifact.** The substring ground truth was welded to the seed docs' wording.
  `trunk-vs-access` expected the seed's "untagged network", but the fetched Switch Port VLAN
  Assignment page answers it correctly as "Native (untagged) VLAN", so a better answer scored
  as a miss.
- **Real dilution.** For some questions a fetched chunk that is semantically near but off-topic
  outranks the curated answer chunk. `poe-cycle`'s answer (the seed operations note) is buried
  at rank 12 under Layer-3 / ACL / setup pages that do not answer it.

## Decision

Shipped this round:

- **Relevance floor** (`score_floor`, default 1.0): rejects off-topic queries so the model is
  not handed unrelated context. Live on the served instance.
- **OR-group eval ground truth** (ADR-0006 extension): a correct answer counts regardless of
  source wording. Fixed the `trunk-vs-access` false miss; served ubiquiti moved 15/19 -> 16/19
  with no change to the local 18/19.

Deferred, with rationale. These are the known limitations:

1. **Reranking is not productized.** A hybrid dense + BM25 reranker (top-20 candidates,
   `alpha=0.7`) was prototyped; it lifted served recall 0.79 -> 0.84 and recovered `poe-cycle`.
   It is not shipped: `alpha` is tuned on the same 19-question set it is scored against, and the
   remaining marginal gain is a single question. A change to the retrieval path for every query
   needs a larger held-out question set before it earns production, or it just overfits the eval.
2. **Corpus pruning is rejected, not deferred.** An ablation showed that dropping the noisiest
   fetched sources raises the number, but the single biggest "displacer", the Switch Port VLAN
   Assignment page, is the best answer in the corpus for `trunk-vs-access`. Pruning it would
   delete good content to game a seed-biased metric.
3. **`adoption-loop` stays a known miss.** It fails on the clean local corpus too. The retrieved
   chunk explains the cause (a device that "cannot reach the controller's inform endpoint or is
   still carrying a previous controller's credentials") but never uses the literal phrase
   "adoption loop". Broadening its ground truth to force a pass would hide a genuinely hard
   retrieval case rather than fix it.
4. **A served-corpus eval gate is deferred.** CI cannot deterministically rebuild the
   fetched-inclusive index: that content is gitignored and unsafe to commit (ADR-0016, issue
   #60). A non-gating served eval or a frozen staged snapshot is possible but not built.

## Consequences

- `eval-gate` measures the local-only corpus, not the served index. Read its number as a
  regression floor on curated retrieval, not as production recall; served ubiquiti recall is
  about 0.84.
- Adding fetched breadth can lower recall on curated questions. `poe-cycle` and `port-profiles`
  regress on the served index and are not fixed this round (`port-profiles`'s answer chunk sits
  below the top 25, a candidate-recall problem reranking cannot reach).
- `score_floor` is a coarse out-of-domain guard, not a precision filter. Adjacent-domain queries
  (generic BGP or Kubernetes questions against the UniFi pack) fall inside the in-domain distance
  band and are answered rather than refused.
- The reranker and the served-corpus eval remain available future work; see
  [ROADMAP](../../ROADMAP.md).

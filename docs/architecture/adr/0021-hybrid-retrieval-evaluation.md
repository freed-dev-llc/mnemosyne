# 21. Hybrid retrieval evaluation: pre-registered measurement, don't productize now

Date: 2026-07-07

## Status

Accepted

## Context

ADR-0017 item 1 prototyped a hybrid dense+BM25 reranker (top-20 candidates, `alpha=0.7`)
that lifted served ubiquiti recall 0.79 -> 0.84 and recovered `poe-cycle`, and refused to
ship it because `alpha` was tuned on the same 19 questions it was scored on; the stated
unlock was a larger held-out set. ADR-0020 built that instrument: 32 questions with
per-class corpus tags. The baseline for this step (served 294-chunk index, k=5,
`score_floor` 1.0) was 29/32 (0.906), curated 16/19, fetched 13/13, with three standing
curated misses (`adoption-loop`, `port-profiles`, `poe-cycle`) as concrete targets.

Fresh evidence, re-checked before measuring: cross-encoder rerankers stay non-servable on
this stack (ollama/ollama PR #7219, the rerank endpoint, was closed as stale by a
maintainer on 2025-09-16, with no successor merged), so the only servable candidate class
is hybrid BM25+dense, pure Python over the existing FAISS store. No BM25 dependency exists
in pyproject or on the serving host; Phase A hand-rolled Okapi BM25 in a scratch script,
and the dependency choice was explicitly deferred to a productization step.
`adoption-loop`'s missing substring ("factory reset") exists only in the served corpus,
which made all three curated misses live targets on the served index.

Jon pre-agreed the adoption bar before any measurement, so the outcome is mechanical:
productize (via a Step-7 brief) iff, at the dev-chosen config, (i) the full served 32-set
reaches at least 31/32 (+2 over the 29/32 baseline; ADR-0017 already ruled +1 not worth a
retrieval-path change), (ii) the held-out subset does not regress vs baseline, (iii) the
local-only 19-question population does not regress (18/19; protects the CI-gate floor),
and (iv) the flat-region requirement holds. Jon also confirmed the receipts-only landing
(no code ships this step even on a pass) and the methodology below as written.

## Pre-registered method (D1-D5, locked before measurement)

Transcribed from the brief as pinned before Phase A ran:

- **D1. Candidate class: hybrid BM25+dense only**, two variants: (a) *rescore*: blend
  scores over the dense top-N pool; (b) *union*: candidates = dense top-N plus BM25
  top-N over the whole corpus, blended, take top-5. Pool N in {20, 50}.
- **D2. Every degree of freedom pre-registered here, before measurement.** Okapi BM25
  with k1=1.5, b=0.75, tokenized by the shipped identifier-preserving `_TOKEN_RE` from
  eval.py (consistency with the eval contract). Blend: min-max normalize dense
  similarity and BM25 score within the candidate pool; final score = alpha*dense +
  (1-alpha)*bm25; alpha grid {0.3, 0.5, 0.7, 0.9}. Scoring = the shipped `eval.score`
  semantics at k=5. The floor is not applied inside the measurement (Step 1 showed it
  non-binding in-domain; its semantics under reranking is a Step-7 productization
  question and is recorded as such).
- **D3. Overfit discipline (the reason ADR-0017 refused to ship).** Stratified 50/50
  dev/held-out split by corpus class, fixed seed 2026, pinned in the Phase-A script.
  Config selection uses dev only: best dev hits, ties broken toward smaller pool, then
  rescore over union, then alpha nearest 0.5. Flat-region requirement: the chosen
  alpha's +-0.2 neighbors must be within 1 dev hit, else the optimum is a spike and the
  config is rejected. ONE final evaluation on held-out; no re-tuning after seeing it.
- **D4. Diagnostics recorded regardless of outcome:** the dense rank (at pool 100) of
  the best answer chunk for every current miss, which classifies each as
  rescoring-fixable (in pool), union-fixable (BM25 reaches it), or unreachable (absent);
  plus the two ADR-0020 rejected candidates (`speedtest-port`, `zbf-builtin-zones`) run
  as unscored probes: recovering them would justify re-adding them to the question set
  in a later step.
- **D5. Measured on the Spark against the production served index** (294 chunks,
  bge-m3, 500/150), read-only (the scratch script queries the store; no re-ingest, no
  service impact). The same script also scores the chosen config on the local-only
  19-question population (scratch `--local-only` index) for the no-regression bar
  condition.

### Phase A receipt (Sage, 2026-07-07 UTC, on the Spark, read-only; served index 294 chunks at `930c3f6`, local-only scratch 42 chunks)

Method exactly as pre-registered above (D1-D5); scorer = shipped `eval.score` semantics
at k=5; no floor inside the measurement. Baselines reproduced first: served 29/32
(miss: `adoption-loop`, `port-profiles`, `poe-cycle`), local-only 18/19.

```
split: dev=17 held=15 (stratified by corpus class, seed 2026)
dev baseline 16/17    held-out baseline 13/15

DEV TABLE (hits/17; selection on dev only)
  rescore  N=20  a=0.3:16  a=0.5:16  a=0.7:16  a=0.9:16
  rescore  N=50  a=0.3:16  a=0.5:16  a=0.7:16  a=0.9:16
  union    N=20  a=0.3:16  a=0.5:16  a=0.7:16  a=0.9:16
  union    N=50  a=0.3:16  a=0.5:16  a=0.7:16  a=0.9:16

chosen (mechanical tie-break): rescore N=20 alpha=0.5; flat-region True (all 16 configs tie)
held-out at chosen:  12/15  (miss: poe-cycle, stuck-adopting, port-profiles)  <- REGRESSION vs 13/15
full set at chosen:  28/32  (recovered: none; NEW miss: stuck-adopting)       <- REGRESSION vs 29/32
local-only at chosen: 18/19 (miss: adoption-loop; unchanged)

DIAGNOSTICS (dense rank of best co-located answer chunk, pool 100)
  adoption-loop      dense_rank=>100/absent  bm25_top50=False  hit_at_chosen=False
  port-profiles      dense_rank=26           bm25_top50=True   hit_at_chosen=False  (seed chunk)
  poe-cycle          dense_rank=12           bm25_top50=True   hit_at_chosen=False  (seed chunk)
  speedtest-port*    dense_rank=10           bm25_top50=True   hit_at_chosen=TRUE   (Required-Ports)
  zbf-builtin-zones* dense_rank=56           bm25_top50=True   hit_at_chosen=False  (ZBF page)
  (* = ADR-0020 rejected candidates, unscored probes)
```

**Bar verdict (mechanical): FAIL.** Condition (i) 28/32 < 31/32; condition (ii)
held-out regressed 13 -> 12. Conditions (iii) local-only 18/19 unchanged and (iv)
flat-region hold, but are moot. **Don't productize now.**

Readings for ADR-0021 (Nova transcribes; no interpretation beyond these):
- The dev table is uniformly flat at the dev baseline: at pinned settings, hybrid
  blending buys nothing anywhere on the grid, and off-dev it costs a dense-solved
  question (`stuck-adopting` drops out of the top-5 when BM25 weight enters).
- ADR-0017's prototype result (poe-cycle recovered at alpha=0.7/top-20) does not
  reproduce under the pre-registered normalization and tokenizer; its lift was an
  artifact of tuning freedom, which is what this step's discipline exists to catch.
- The three standing misses decompose cleanly: `adoption-loop` has NO single chunk
  co-locating its expected items even on the served corpus (a ground-truth/corpus
  shape issue, not a ranking one; note the eval's union-of-top-5 semantics could in
  principle satisfy it across two chunks, but no measured config did);
  `port-profiles` (rank 26) and `poe-cycle` (rank 12) are moderate rank problems the
  blend cannot lift without collateral damage.
- Probe observation: hybrid recovers `speedtest-port` (rejected from the set in
  ADR-0020 for dense unreachability). Recorded as evidence about the miss class, not
  as a reason to adopt; re-adding probes stays out of scope while the bar fails.
- Revisit triggers: a materially larger question set or matured corpus; an upstream
  Ollama rerank endpoint making cross-encoders servable (PR #7219 is closed-stale,
  2025-09-16); or corpus/question fixes that leave rank-only misses as the dominant
  class.

## Decision

**Don't productize now.** The verdict is mechanical against the pre-agreed bar: condition
(i) failed (28/32 at the dev-chosen config, below the required 31/32 and below the 29/32
baseline) and condition (ii) failed (held-out regressed 13/15 -> 12/15). Conditions (iii)
local-only 18/19 unchanged and (iv) flat-region held, but are moot. Nothing ships: no
`src/` change, no dependency, no config change; the retrieval path stays dense-only k=5
over bge-m3 with `score_floor` 1.0. Reranking remains not productized, now on the strength
of a pre-registered measurement over the instrument ADR-0017 asked for, rather than a
tuning-freedom prototype.

## Consequences

- Revisit triggers, from the receipt: a materially larger question set or matured corpus;
  an upstream Ollama rerank endpoint making cross-encoders servable (PR #7219 is
  closed-stale, 2025-09-16); or corpus/question fixes that leave rank-only misses as the
  dominant class.
- The diagnostics point future work away from reranking: `adoption-loop` is a
  ground-truth/corpus shape issue (no single chunk co-locates its expected items even on
  the served corpus), while `port-profiles` (dense rank 26) and `poe-cycle` (dense rank
  12) are moderate rank problems the pinned blend could not lift without collateral
  damage (`stuck-adopting` dropped out of the top-5 whenever BM25 weight entered).
- The probe recovery of `speedtest-port` (rejected in ADR-0020 for dense unreachability)
  is recorded as evidence about that miss class only; re-adding probes to the question
  set stays out of scope while the bar fails.
- ADR-0017's prototype lift did not reproduce under the pre-registered normalization and
  tokenizer: a standing caution that any future retrieval-path proposal pins its degrees
  of freedom before measuring, as this step did.
- The Phase-A scratch script was removed per the brief; the pre-registered method above
  is the reproduction recipe.

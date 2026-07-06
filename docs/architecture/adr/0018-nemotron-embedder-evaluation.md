# 18. Nemotron embedder evaluation: keep bge-m3, don't adopt llama-embed-nemotron-8b

Date: 2026-07-06

## Status

Accepted

## Context

Jon asked whether NVIDIA's `llama-embed-nemotron-8b` should replace `bge-m3` as the default
embedding model, and whether a reranker should ship alongside it. The evaluation ran
measure-then-propose: the adoption bar was agreed before anything was pulled, and Jon
confirmed it as written. The bar: strictly higher retrieval hit rate at two or more of
k=1/k=2/k=3 on the ubiquiti eval set, no regression at k=5, and a workable footprint.

ADR-0017 is the retrieval-quality background: a hybrid dense + BM25 reranker was prototyped
but not shipped (its `alpha` was tuned on the same 19-question set it is scored on), and
served-corpus recall is about 0.84 versus the local-only 0.95. Any retrieval-path change
carries that overfitting caution. Separately, v0.4.0 shipped `score_floor` (default 1.0,
calibrated to bge-m3's L2 distance distribution) and `faiss_normalize` (opt-in, for future
non-unit-norm embedders), both of which an embedder swap would have to account for.

### Phase A receipt (Sage, 2026-07-06, on the Spark (GB10 / 121 GB unified), Ollama 0.30.11)

Connection coordinates (user@host) are deliberately omitted from tracked history; tracked
docs carry no internal hostnames or addresses.

**1. License (checked before pulling).** `nvidia/llama-embed-nemotron-8b` model card:
license `customized-nscl-v1`, "This model is for non-commercial/research use only", plus
NVIDIA License and Llama-3.1 Community License (base `meta-llama/Llama-3.1-8B`). Local
evaluation is permitted, so Phase A proceeded. **Production use by freed-dev-llc would not
be**, which blocks adoption independent of any measurement.

**2. Feasibility: not adoptable via Ollama today.** The model is not in the Ollama library
(open request ollama/ollama#16103, 2026-05-11). The community GGUF pulled for evaluation:
`hf.co/mradermacher/llama-embed-nemotron-8b-GGUF:Q8_0`, 8.0 GB, pulled clean; `ollama show`
reports architecture `llama-embed`, 7.5B params, embedding dim 4096, context 131072, but
capability **completion only** (bge-m3 shows `embedding`). Every embedding endpoint refuses:

```
POST /api/embed        -> HTTP 501 {"error":"This server does not support embeddings.
                                     Start it with `--embeddings`"}
POST /api/embeddings   -> HTTP 500 (same body)
```

Root cause: Ollama grants the embedding capability from a `pooling_type` KV in the GGUF
metadata; this conversion lacks it, and Ollama has no Modelfile escape hatch to force the
capability. So no embedding vectors can be produced at all: the A/B sweep for nemotron
**cannot run**, and per the approved protocol this is the decisive receipt. The 1B sibling
(`mradermacher/llama-nemotron-embed-1b-v2-GGUF`) is presumed to share the defect
(same converter pipeline) but was not pulled to verify.

**3. Embedding sanity baseline, bge-m3 (the control ran; the candidate could not).**
Script: 4 paraphrase pairs vs 4 unrelated pairs, cosine over `/api/embed`, stdlib only.

```
bge-m3: dim 1024, vector norm 1.0000 (unit-norm: L2 already ranks like cosine,
        faiss_normalize is moot for the current default)
  similar pairs   0.847 0.803 0.895 0.848   mean 0.848
  dissimilar      0.385 0.385 0.371 0.334   mean 0.368
  gap 0.480 (healthy separation)
  per-embed latency: median 194 ms over 16 calls (first call includes model load)
```

**4. Low-k retrieval headroom baseline (the reusable half of the measurement).**
`mnemosyne sweep ubiquiti --k 1 --k 2 --k 3 --k 5` on the Spark repo at `abe585b`,
local-only deterministic ingest (42 chunks / 19 questions, 500/150, bge-m3), run twice:
production floor (`score_floor=1.0`) and floor disabled (sentinel 999). **Identical tables**
(the floor is not binding on in-domain queries), wall clock 15-20 s per sweep:

```
k=1  hit_rate 0.53      k=2  0.84      k=3  0.95      k=5  0.95
```

Reading: hit@1 has 9 questions of headroom and hit@2 has 3; k>=3 is saturated at 18/19 by
the `adoption-loop` known miss (ADR-0017 item 3). Any future embedder or reranker candidate
should be scored at k=1/k=2, where the instrument can actually show a win; k=5 can only
show regressions. A fair embedder A/B must also disable or retune `score_floor` (its 1.0
default is calibrated to bge-m3's distance distribution) and check the candidate's vector
norms to decide `faiss_normalize`.

**5. Footprint.** 8.0 GB on disk (Q8_0) vs bge-m3's 1.2 GB; ~7x. Latency and quality:
unmeasurable (no embeddings produced).

**6. Cleanup done.** `ollama rm hf.co/mradermacher/llama-embed-nemotron-8b-GGUF:Q8_0`
executed; `ollama list` on the Spark shows only `qwen2.5:1.5b` and `bge-m3` again.

**7. Outcome against the pre-agreed adoption bar: DON'T ADOPT now.** The bar (strictly
higher hit rate at two or more of k=1/2/3, no k=5 regression, workable footprint) is
unreachable: the model produces no embeddings on our stack, and the research-only license
independently blocks production adoption even if it did. Reranking stays deferred per Jon's
flag-2 ruling, now with two receipts: Ollama has no rerank endpoint (ollama/ollama PR #7219
unmerged), and ADR-0017 item 1 already rejected shipping a retrieval-path change tuned on
the 19-question set. Revisit triggers: ollama#16103 lands official library support, AND the
license permits commercial use (or a differently-licensed nemotron embedder appears).

## Decision

Don't adopt. The bar is unreachable on two independent grounds: the model produces no
embeddings on our stack (the community GGUF lacks the `pooling_type` metadata Ollama needs
to grant the embedding capability, and there is no official Ollama library build), and the
`customized-nscl-v1` research-only license blocks production use by freed-dev-llc even if
it did.

Reranking stays deferred per Jon's ruling, with two receipts: Ollama has no rerank endpoint
(ollama/ollama PR #7219 unmerged), and
[ADR-0017](0017-retrieval-quality-known-limitations.md) item 1 already rejected shipping a
retrieval-path change tuned on the 19-question set.

Defaults are unchanged: `bge-m3` embeddings, `score_floor=1.0`, `faiss_normalize` off.

## Rejected alternatives

- **Serve the model outside Ollama (NVIDIA NIM or Text Embeddings Inference).** A new
  runtime in the stack for a model that is still research-only licensed; the license blocks
  production adoption regardless of where it runs.
- **Re-convert the GGUF with pooling metadata.** The fidelity of the bidirectional-attention
  conversion is unverified, and the license still blocks production use, so a working
  conversion would change the evaluation result but not the decision.

## Consequences

- Revisit triggers, both required: ollama/ollama#16103 lands official library support for
  the model, AND the license permits commercial use (or a differently-licensed nemotron
  embedder appears).
- The low-k headroom baseline in the receipt is the standing instrument for any future
  retrieval-quality candidate, embedder or reranker: score it at k=1 (0.53, 9 questions of
  headroom) and k=2 (0.84, 3 questions of headroom), where a win is visible. k=5 is
  saturated at 0.95 by the `adoption-loop` known miss (ADR-0017 item 3) and can only show
  regressions.
- A fair embedder A/B must disable or retune `score_floor` (its 1.0 default is calibrated
  to bge-m3's distance distribution) and check the candidate's vector norms to decide
  `faiss_normalize`.

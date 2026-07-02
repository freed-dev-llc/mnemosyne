# 12. Re-sweep against the matured ubiquiti corpus: keep 500/150/k=5, floor 0.9, faithfulness report-only

Date: 2026-06-29

## Status

Accepted

Follows up [ADR-0011](0011-default-review-against-eval-sweep.md) and closes the re-sweep deferred in
issue #29.

## Context

ADR-0011 kept the shipped defaults but flagged its own evidence as thin: the sweep ran against a
single 63-line seed note, so the conclusion was explicitly conditioned on re-running "when the
Ubiquiti corpus has real multi-document content." Issue #29 tracked that re-run.

This step matures the corpus, then re-runs the sweep. The corpus grew by three self-authored
primers added to `packs/ubiquiti/sources/`, original prose covering network security and
segmentation, WiFi/RF and roaming, and operations (adoption recovery, firmware, diagnostics).
They cover the domains the seed omitted. The local-only corpus is now 4 documents / 42 chunks at the default chunking.

The `sources.yaml` Help Center URLs were not used to mature the corpus: help.ui.com returns HTTP 403
to this host, so the 15-article fetch cannot run here. Local primers also keep the eval-gate corpus
deterministic and network-free, which is the property the floor depends on (ADR-0008).

### The receipt (measured this step)

Run provenance: worktree `issue-29-resweep-ubiquiti`, 2026-06-29, Ollama at `http://localhost:11434`,
embeddings `bge-m3`, chat `qwen2.5:1.5b`, pack `ubiquiti` (10-question labelled set), `--local-only`
deterministic ingest, 4 documents / 42 chunks at 500/150. Retrieval hit-rate is deterministic;
faithfulness is one non-deterministic chat run.

Retrieval sweep (`mnemosyne sweep ubiquiti` over chunk_size {500,700,1000} x overlap {50,150} x
k {3,5,8}):

```
chunk_size  overlap  k      hit_rate
500         {50,150} {3,5,8} 0.90     <- current default at k=5: 0.90 (9/10), flat across k
700         {50,150} 3       0.80
700         {50,150} {5,8}   1.00
1000        50       3       0.90
1000        50       {5,8}   1.00
1000        150      {3,5,8} 1.00     <- best: 1000/150/k=3
```

`chunk_size=300` is absent on purpose: bge-m3 via Ollama returns NaN (HTTP 500,
`failed to encode response: json: unsupported value: NaN`) for the `unifi-network-security.md` VLAN
intro chunk, which only forms at that chunk size. It reproduces 3/3 and a reworded paraphrase also
fails, so it is an upstream embedding defect, not a corpus or retrieval signal; at 500/700/1000 the
text merges into a larger chunk and embeds normally. Tracked as issue #40. ADR-0011 already measured
`chunk_size=300` as the weakest axis (0.80-0.90), so its absence does not change the decision.

The single default-config miss is unchanged from ADR-0011: question `adoption-loop`, missing
substring `factory reset`, the two seed phrases straddling a 500-char chunk boundary. New this step:
the miss is now flat across k (0.90 at k=3, 5, and 8). On the seed-only corpus, k=8 had rescued
`chunk_size=500` to 1.00; the larger corpus fills the extra top-k slots with other-document chunks,
so raising k no longer recovers the miss. That removes the "just raise k" escape and confirms the
miss is intrinsic to the seed text, not a retrieval-depth shortfall.

Faithfulness at the default config (500/150/k=5), one run, mean 0.59 (ADR-0011: 0.47):

```
unifi-model 1.00 · controller-vs-device 0.75 · adoption-lifecycle 0.32 ·
adoption-prerequisites 0.82 · adoption-loop 0.27 · set-inform 0.43 ·
port-profiles 0.94 · trunk-vs-access 0.78 · poe-cycle 0.20 · wlan-vlan 0.44
```

## Decision

1. **Keep `chunk_size=500 / chunk_overlap=150 / k=5`.** The default scores 9/10 on the matured
   corpus, and the lone miss is now flat across k (0.90 at k=3/5/8), which strengthens ADR-0011's
   read that it is a seed chunk-boundary artifact rather than a tuning gap. Moving a global default
   to win that one question still overfits the knob to one seed boundary.

2. **Keep `DEFAULT_MIN_HIT_RATE = 0.9`.** Re-measured at 9/10 (0.90) on the matured corpus via the
   eval-gate path (`--local-only` ingest + `mnemosyne eval ubiquiti`). No value change; the floor
   comment in `eval.py` now points here.

3. **Keep faithfulness report-only with no cut point.** Mean rose to 0.59 but the spread is still
   wide (0.20-1.00) on one non-deterministic 1.5B run. A 1.5B model's paraphrase tanks lexical
   bigram overlap on correct answers (faithfulness is a grounding proxy, not a correctness oracle;
   ADR-0007), so there is still no defensible threshold. Revisit with a larger question set and
   repeated runs (issue #41).

## Rejected alternative

Adopt `chunk_size=700` or `chunk_size=1000` to reach 10/10. On the matured corpus this is weaker
than it looked seed-only: `700/k=3` now drops to 0.80 (the extra documents push a needed chunk out
of the top 3), so 700 is no longer the uniform 10/10 it was in ADR-0011. The new best,
`1000/150/k=3`, reaches 1.00 but a 1000-char chunk yields a blurrier embedding and less precise
retrieval (RAG-101), and it still only wins the single seed-boundary question. Each option would
edit `config.py` and force a floor re-measure to buy one question. The signal does not justify
moving a global default.

## Consequences

- No hyperparameter, model, or floor value changes. The only code touch is the `DEFAULT_MIN_HIT_RATE`
  comment in `eval.py` pointing here.
- The `ubiquiti` corpus gains three tracked, self-authored primers (security, RF, operations) under
  `packs/ubiquiti/sources/`. The local-only and eval-gate corpus is now 4 documents / 42 chunks;
  CI's eval-gate ingests and scores this larger corpus and still measures 0.90.
- The eval question set stays seed-derived, so the retrieval eval measures seed-fact robustness
  against the larger corpus, not coverage of the new primers. Expanding the question set to exercise
  the security/RF/operations material is issue #41.
- The bge-m3/Ollama NaN-on-embed crash that aborts ingest (and blocks the `chunk_size=300` sweep
  axis) is issue #40.
- Closes issue #29: the default review has now run against a representative multi-document corpus,
  and the inherited values hold.

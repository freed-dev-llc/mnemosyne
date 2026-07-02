# 11. Default review against the eval sweep: keep 500/150/k=5, floor 0.9, faithfulness report-only

Date: 2026-06-28

## Status

Accepted

## Context

Issue #24's last v0.2 acceptance box asks for chunking/`k`/model sweeps "so defaults are chosen
from data, not vibes," and says outright that if the data calls for a default change, it lands in
a follow-up. Two earlier ADRs forward-referenced this review. ADR-0008 §2 seeded
`DEFAULT_MIN_HIT_RATE` as a measured *ratchet*, not a guess, and deferred the absolute,
data-chosen cut point to "Step 4 (the chunking/`k`/model sweeps)." ADR-0010 §5 shipped
`mnemosyne sweep` as report-only and named "revisiting the `500/150`, `k=5` defaults and
re-measuring `DEFAULT_MIN_HIT_RATE` against it" as the follow-up step.

The sweep harness those ADRs point at shipped in two parts: the pure offline core (grid +
scoring + table) in Step 4a (`d2e084e`) and the live re-ingest runner plus the `mnemosyne sweep`
command in Step 4b (`cae232b`). This step runs that harness against the `ubiquiti` labelled set,
records the measurement, and decides whether to move any default. It changes no hyperparameter
default, no model, and no floor value. Acting on the table to *change* a default would be a
separate, code-changing follow-up with its own ADR.

### The receipt (measured this step)

Run provenance: worktree `eval-sweeps-4c`, 2026-06-28, Ollama at `http://localhost:11434`,
embeddings `bge-m3`, chat `qwen2.5:1.5b`, pack `ubiquiti` (10-question labelled set),
`--local-only` deterministic ingest. Retrieval hit-rate is deterministic; faithfulness is one
non-deterministic chat run.

Retrieval sweep (`mnemosyne sweep ubiquiti` over chunk_size {300,500,700,1000} x overlap {50,150}
x k {3,5,8}):

```
chunk_size  overlap  k  hit_rate
300         {50,150} 3  0.80
300         {50,150} {5,8} 0.90
500         {50,150} {3,5} 0.90      <- current default at k=5: 0.90 (9/10)
500         {50,150} 8  1.00
700         {50,150} {3,5,8} 1.00    <- best: 700/50/k=3
1000        50       3  0.90
1000        50       {5,8} 1.00
1000        150      {3,5,8} 1.00
```

The single default-config miss: question `adoption-loop`, missing substring `factory reset`. Seed
proximity: "adoption loop" (seed line 24) and "factory reset" (line 27) straddle a 500-char chunk
boundary; chunk_size=700 merges them into one retrieved chunk, reaching 10/10. A chunk-boundary
artifact on a single file, not a corpus gap.

Faithfulness at the default config (500/150/k=5), one run, mean 0.47:

```
unifi-model 0.82 · controller-vs-device 0.57 · adoption-lifecycle 0.63 ·
adoption-prerequisites 0.62 · adoption-loop 0.26 · set-inform 0.21 ·
port-profiles 0.94 · trunk-vs-access 0.34 · poe-cycle 0.12 · wlan-vlan 0.18
```

## Decision

1. **Keep `chunk_size=500 / chunk_overlap=150 / k=5`.** The shipped default scores 9/10. The lone
   miss is a chunk-boundary artifact: the two `adoption-loop` substrings straddle a 500-char
   boundary, so a wider chunk merges them. Changing a global default to win one question on a
   single 63-line seed file would overfit the knob to this corpus, which is the opposite of
   choosing a default from data. Re-sweep and revisit when the Ubiquiti corpus has real
   multi-document content (roadmap §v0.x).

2. **Keep `DEFAULT_MIN_HIT_RATE = 0.9`.** It is already the measured floor at the shipped
   defaults, reproduced this step (9/10 = 0.90). ADR-0008 §2 set it as a measured ratchet, and
   this sweep confirms it still holds. No value change. (The kickoff's "inert 0.0 today" was
   stale: the floor has been 0.9 since the eval gate shipped in `c8f67b0`.)

3. **Keep faithfulness report-only with no cut point.** The measured distribution (mean 0.47,
   range 0.12-0.94, one non-deterministic run) has no defensible threshold: a 1.5B model's verbose
   paraphrase tanks lexical bigram overlap even on correct answers (faithfulness is a grounding
   proxy, not a correctness oracle; ADR-0007). A pass/fail bar on this signal would gate honest
   answers on phrasing. Revisit on a real corpus with multiple runs or a stronger model.

## Rejected alternative

Adopt `chunk_size=700` (10/10 at every k tested) or keep 500 and raise `k` to 8 (also 10/10).
Rejected as overfit to one chunk boundary on a single-document corpus: both win only the lone
`adoption-loop` miss, and each would edit `config.py`, force a `DEFAULT_MIN_HIT_RATE` re-measure,
and warrant its own ADR. The signal (10 questions over one seed file) is too thin to move a global
default. Revisit when the corpus matures.

## Consequences

- No code default changes: `config.py` (`chunk_size` / `chunk_overlap` / `k`), the two default
  models, and `DEFAULT_MIN_HIT_RATE` all stay as shipped. The only code touch this step is a
  one-line comment on the floor constant pointing here.
- The sweep receipt and its procedure are recorded and reproducible: re-run `mnemosyne sweep
  ubiquiti` with the provenance above to reproduce the retrieval table.
- The faithfulness cut point moves to v0.x corpus-maturity work, scored on a real multi-document
  corpus with repeated runs, not a single non-deterministic run over one seed file.
- This ADR closes the forward references that deferred the act-on-the-table decision: ADR-0008 §2,
  ADR-0010 §5, and the faithfulness-threshold pointers in ADR-0007 and the `eval.py` module
  docstring. Those wordings stay as written (the standing scope lock); this ADR records that the
  review ran and that the conclusion is to keep the inherited values and re-open the question when
  the corpus is real.

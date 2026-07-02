# 14. Expand the ubiquiti eval question set to the full corpus: 19 questions, defaults and floor hold

Date: 2026-06-29

## Status

Accepted

Follows up [ADR-0012](0012-resweep-against-matured-ubiquiti-corpus.md) and closes issue #41. Relies
on [ADR-0013](0013-ingest-survives-unembeddable-chunk.md) (issue #40) to run the full sweep grid.

## Context

ADR-0012 grew the `ubiquiti` corpus to four documents but left the labelled question set seed-only
(10 questions, all drawn from `seed-unifi-concepts.md`). So the retrieval eval measured how robustly
the seed facts survive a larger corpus, not whether the new security, RF, and operations primers are
themselves retrievable. Issue #41 tracked closing that gap. With ADR-0013 fixing the
NaN-on-embed crash, the full sweep grid (including `chunk_size=300`) runs again.

This step adds nine labelled questions (three per primer) whose `expected` substrings are drawn
verbatim from the primers, bringing the set to 19, and re-measures the defaults and the floor
against it.

Question design: each question's `expected` substrings are chosen to sit together in one chunk at
the default chunking, so the question measures retrieval of a coherent fact, not the ability to
fetch two adjacent chunks. The first measurement flagged two questions (`firewall-default-deny`,
`firmware-backup`) whose substrings straddled a chunk boundary (the relevant section was retrieved,
but the second substring lived in the next chunk); both were retargeted to co-located substrings.
The one remaining miss is the inherited seed `adoption-loop` artifact (ADR-0011), kept as-is for
continuity.

### The receipt (measured this step)

Run provenance: worktree `issue-41-expand-ubiquiti-questions`, 2026-06-29, Ollama at
`http://localhost:11434`, embeddings `bge-m3`, chat `qwen2.5:1.5b`, pack `ubiquiti` (19-question
labelled set), `--local-only` deterministic ingest, 4 documents / 42 chunks at 500/150. Retrieval
hit-rate is deterministic; faithfulness is one non-deterministic chat run.

Retrieval sweep (`mnemosyne sweep ubiquiti` over chunk_size {300,500,700,1000} x overlap {50,150} x
k {3,5,8}):

```
chunk_size  overlap  k       hit_rate
300         50       {3,5,8} 0.84
300         150      3       0.79
300         150      {5,8}   0.89
500         {50,150} {3,5,8} 0.95     <- default at k=5: 18/19 (0.95), flat across k and overlap
700         {50,150} 3       0.89
700         {50,150} {5,8}   1.00
1000        50       3       0.95
1000        50       {5,8}   1.00
1000        150      {3,5,8} 1.00     <- best: 1000/150/k=3
```

The default config's single miss is the seed `adoption-loop` question (substring `factory reset`),
the same chunk-boundary artifact carried since ADR-0011. The eight other new primer questions and
the nine other seed questions all hit at the default config.

Faithfulness at the default config (500/150/k=5), one run, mean 0.50 over 19 questions (ADR-0012:
0.59 over 10).

## Decision

1. **Keep `chunk_size=500 / chunk_overlap=150 / k=5`.** On the 19-question set it scores 18/19 (0.95),
   flat across every k (3/5/8) and overlap (50/150) tested, the most stable config in the grid. The
   lone miss is the seed artifact, not a gap in the new material.

2. **Keep `DEFAULT_MIN_HIT_RATE = 0.9`.** The expanded set measures 0.95 at the default config,
   clearing the floor. It is kept at 0.9 rather than ratcheted to the exact 18/19 = 0.947 so the
   non-blocking eval-gate keeps headroom against a single-question embedding difference across
   hardware; 0.9 stays a valid regression floor the set clears. The `eval.py` floor comment now
   points here.

3. **Keep faithfulness report-only.** Mean 0.50 over 19 questions on one non-deterministic 1.5B run,
   still a wide spread with no defensible threshold (faithfulness is a grounding proxy, not a
   correctness oracle; ADR-0007). A cut point still needs repeated runs or a stronger judge.

## Rejected alternative

Adopt `chunk_size=700` or `1000`. On the 19-question set `700/k=3` falls to 0.89 (k-sensitive), and
the best, `1000/150/k=3` at 1.00, only wins the seed-artifact question with a blurrier 1000-char
embedding (RAG-101). Same conclusion as ADR-0011 and ADR-0012: the signal does not justify moving a
global default.

## Consequences

- The question set grows from 10 to 19, covering the security, RF, and operations primers. The
  question-set header rule now allows `expected` substrings from any local source file, not just the
  seed note.
- No default or floor value changes; the only code touch is the `eval.py` floor comment.
- Retrieval is now measured against the whole corpus, so the floor is a representative ratchet rather
  than a seed-only one.
- The faithfulness cut point remains future work (repeated runs or a stronger judge model).
- Closes issue #41.

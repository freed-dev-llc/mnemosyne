# 7. Answer faithfulness is lexical n-gram overlap

Date: 2026-06-27

## Status

Accepted

## Context

Step 1 (ADR-0006) scored *retrieval*: did the right chunk get retrieved? Faithfulness is the
deferred *generation-side* question — does the generated answer stay grounded in its retrieved
context? Two candidates were on the table:

- **(A) LLM-as-judge** (RAGAS-style) — a second model reads the answer and the context and
  rates how well one supports the other.
- **(B) Lexical n-gram overlap** — a pure function of `(answer, context)`: what fraction of the
  answer's word-n-grams also appear in the context?

## Decision

1. **B over A.** Faithfulness is a pure function of `(answer, context)`: deterministic and
   CI-stable, the scorer is unit-testable fully offline, and it adds no new model or dependency
   (so no model-default escalation). It is legible for a teaching repo and cheap to run inside
   the Step-4 sweeps. A's one real advantage — semantic credit for faithful paraphrase — is
   exactly what a 1.5B local judge is least reliable at, so it would trade a deterministic signal
   for a noisy one. A stays an **additive, later** second metric (v0.x), not foreclosed.

2. **Lever 1 — bigrams (`n=2`).** A fabricated token *and* a fabricated combination of real
   tokens both break a bigram, while trigrams over-punish legitimate paraphrase. `n` is exposed
   as a keyword argument so the Step-4 sweeps can tune it; it is **not** a CLI flag.

3. **Lever 3 — identifier-preserving lowercase tokenizer (a deliberate choice over bare `\w+`), no
   stopword removal.** The tokenizer lowercases and keeps a run of alphanumerics that carries
   internal `. : _ -` separators whole — pinned as `[a-z0-9]+(?:[.:_-][a-z0-9]+)*`. Bare `\w+`
   shreds `192.168.1.1`, `udm-pro`, and `qwen2.5:1.5b` into colliding fragments and manufactures
   false "faithful" matches; keeping them whole means a **fabricated identifier** (e.g. an answer
   claiming `192.168.1.99` when the context has only `192.168.1.1`) breaks the bigram and is
   reported as `ungrounded`. **Catching fabricated IPs / model-SKUs is the point of a grounding
   metric over network docs.** Its one minor new caveat is **trailing-punctuation handling**: the
   regex trims trailing separators (`192.168.1.1.` → `192.168.1.1`, `udm-pro,` → `udm-pro`) and
   treats only `. : _ -` as internal, so `/`-bearing forms such as CIDR `10.0.0.0/8` split at the
   slash — bigram-localized and minor. No stoplist is applied: a stoplist needs an English-only
   dependency, drops polarity words (`not` / `off` / `on`) that flip an answer's meaning, and
   breaks the bigram adjacency the metric depends on.

4. **Lever 2 — sub-`n` / empty answers score `1.0` (vacuously faithful), included in the mean.**
   An answer with fewer than `n` tokens (empty, one word, a terse refusal) has no bigram-level
   claim to check, so it is scored `1.0` and counted in `mean_faithfulness`. The accepted
   limitation: a degenerate refuse-everything model would post a perfect mean, and poor retrieval
   that drives more refusals can *raise* the mean. `mean_faithfulness` is therefore read
   **alongside** Step 1's retrieval hit-rate, never as a standalone quality score. This is the one
   inversion we knowingly accept; revisit if it bites (Step 3/4).

5. **Lever 4 — no threshold / no pass-fail label this step.** The metric is **report-only**: a
   continuous `score` per answer, a `mean_faithfulness` aggregate, and always exit 0 — no
   `faithful` label, no `faithful_rate`, no exit-code gating. Per-question pass/fail labelling
   **and** the run-level CI gate are deferred to **Step 3**, which sets the cut point against the
   score distribution Step 4 produces. The continuous score is retained in full, so nothing is
   lost and the cut point is sweepable when it is chosen from data rather than guessed.

6. **Context for scoring is the raw retrieved `page_content`** (the same concatenation Step 1
   uses as its haystack), **not** `format_context()` — so the citation scaffolding that
   `format_context` adds can never be miscounted as grounding.

## Consequences

- **Deterministic, offline-testable, legible, dependency-free.** The scorer is a pure function
  over `re` alone; every test runs with no Ollama and no network.
- **A proxy, not proof.** Because it is lexical, it **under-credits faithful paraphrase** (right
  meaning, different words) and **over-credits copied-but-wrong** text (lifted verbatim from a
  context that was itself wrong). The signal is **directional only**: low grounding strongly
  signals off-context generation; high grounding does **not** prove the answer is correct.
  **Faithfulness ≠ correctness** — it measures support by the retrieved context, not truth. No
  docstring, CLI string, or changelog line claims otherwise.
- **The identifier-preserving tokenizer keeps identifiers whole and catches fabricated ones**,
  at the cost only of the minor trailing-punctuation / `/`-splitting handling noted above. This
  resolves the `\w+`-shred consequence of the rejected draft rather than tolerating it.
- **The `empty → 1.0` rule is the one accepted inversion**, fenced as "read alongside retrieval
  hit-rate": a refuse-everything model or poor retrieval can flatter the mean, so faithfulness is
  never read alone.
- **No un-calibrated threshold ships.** Keeping the metric report-only means the cut point is
  chosen from the real distribution in Step 3/4, not guessed in Step 2.

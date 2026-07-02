# 8. Eval CI gate: a non-blocking retrieval-hit-rate regression floor

Date: 2026-06-27

## Status

Accepted

## Context

Step 1 (ADR-0006) shipped `mnemosyne eval` as **report-only** — it scores retrieval hit-rate and
always exits 0. Step 2 (ADR-0007) added report-only answer faithfulness and, in its §4/§5,
explicitly forward-referenced the threshold, pass/fail label, and run-level CI gate to **Step 3**.
This is that step: wire the retrieval hit-rate into CI as a regression gate **without**
destabilising the required `build` check and **without** guessing a floor before it has been
measured.

The load-bearing constraint: neither the required `build` job nor a unit test has Ollama or a built
index, and every test must run with no Ollama and no network. The live gate path
(`run_retrieval_eval` → `RagPipeline.retrieve`) needs `bge-m3` + a FAISS index, so it can run only
in a dedicated Ollama job — never in `build`, never in a unit test.

## Decision

1. **Gate retrieval hit-rate only.** Faithfulness stays report-only and out of the gate: per
   ADR-0007 §4 the `empty → 1.0` refusal inversion lets *worse* retrieval *inflate* the mean, and
   it runs a nondeterministic chat model — both make it unfit as a gate. Gating retrieval closes the
   cut-point loop that ADR-0006 and ADR-0007 §5 both forward-referenced to "Step 3."

2. **A regression floor, not an absolute bar.** The floor is the measured baseline — a *ratchet*: a
   relative "don't backslide" claim needs no calibration, whereas an absolute bar over a single
   un-calibrated 10-question set would be a guess. The floor is a committed constant
   (`DEFAULT_MIN_HIT_RATE`) seeded from a local measurement; the absolute, data-chosen cut point is
   deferred to **Step 4** (the chunking/`k`/model sweeps).

3. **Non-blocking, in a separate Ollama job; `build` untouched.** One 10-question set plus
   model-pull infrastructure would false-fail honest PRs if it blocked. The required `build` job
   stays fast, deterministic, and offline; the new `eval-gate` job runs in parallel (no `needs:`)
   and is never a required check. Non-blocking is achieved *by construction* — the gate step is
   `continue-on-error`, so it never reds the run — and loudness comes from a step summary plus a
   GitHub `::error::` annotation, not from a red required check.

4. **Exit-code contract (user-facing).** The bare command stays report-only → exit `0` (the
   ADR-0006/0007 promise is preserved). The gate is opt-in via `--gate` / `--min-hit-rate` (a
   `--min-hit-rate` floor implies `--gate`; an explicit floor wins over the committed default, and
   an out-of-`[0,1]` floor is an operational error). Exit `2` = *ran fine but below the floor*; exit
   `1` stays the operational-error code (missing pack, no index, no Ollama, bad floor — exceptions
   caught by `_die`). The `hit_rate` vs floor → exit-code decision is a **pure, offline
   unit-testable** function (`gate_exit_code`) layered on Step 1's already-injectable scorer.

5. **Execution model: the committed floor is the authority, the job only reports.** The live gate
   needs Ollama + a built index, so it runs only in the dedicated, non-required job. The committed
   constant — not the job's output — is the floor of record, so the verdict is deterministic and
   self-contained; a flaky or failed model pull can never silently leave the gate with no floor. The
   job merely *reports* the live number (step summary + annotation) so drift from the committed
   baseline is visible. The procedure for setting the constant — measure locally with
   `mnemosyne eval ubiquiti`, then paste the observed `hit_rate` — lives on the constant's comment.

## Consequences

- **The decision function is offline-testable** and the required `build` check is untouched, fast,
  and deterministic; the quality gate is purely additive and isolated.
- **CI-minutes cost** of a live model pull is mitigated by caching `~/.ollama/models` (bge-m3 only —
  the gate never pulls the chat model).
- **The floor is a ratchet, not a calibrated bar.** It is seeded by a documented local measurement
  and superseded by Step 4's data-chosen cut point; one constant covers the only pack with a
  question set (`ubiquiti`), and per-pack floors are out of scope.
- **Accepted limitation:** a non-required, non-blocking job can be ignored. This is mitigated by the
  loud `::error::` annotation and step summary, which surface a regression on the PR without
  pretending to the authority of a blocking check.

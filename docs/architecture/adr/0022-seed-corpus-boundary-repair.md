# 22. Seed corpus boundary repair: make the adoption-loop fact whole in one chunk

Date: 2026-07-07

## Status

Accepted

## Context

`adoption-loop` has been the eval's constant miss since ADR-0011, through every
measurement since (ADR-0012, ADR-0014, ADR-0017 item 3, the ADR-0019 baseline, the
ADR-0021 diagnostics). The root cause has been on record the whole time: the self-authored
seed put `"adoption loop"` on line 24 of `seed-unifi-concepts.md` and `factory reset` on
lines 27-28, and the shipped 500/150 chunking splits them into different chunks; the
factory-reset chunk never ranks top-5 for the question. A question that cannot hit at the
shipped defaults is a constant, not a measurement: it ate one of the two questions of
eval-gate floor headroom (17/19 = 0.894 would breach the 0.9 floor) and clouded every
aggregate. ADR-0021 measured that no retrieval-side change fixes it and pointed here:
corpus/ground-truth shape work.

## Decision

Fix the self-authored corpus text, not the test. The seed's adoption-loop sentence now
names the remedy inline, so the loop's name and its factory-reset fix sit about 42
characters apart in one sentence; every chunking that keeps a sentence intact co-locates
them. This is the same one-chunk co-location rule ADR-0014/ADR-0020 impose on every other
question's ground truth; the seed predated that rule and violated it. The exact edit, one
contiguous replacement pinned in Phase A and applied verbatim in Phase B, is in the
receipt below. Locked constraints held: `questions.yaml` stays byte-identical (D1,
re-verified by diff at review); no other seed section is reworded (D2), in particular the
`poe-cycle` and `port-profiles` prose is not made "more retrievable", because those are
served dilution-ranking problems and rewording prose to win specific eval questions is
teaching the test; verification is per-question, not aggregate (D3), since re-chunking the
whole file could silently swap another question's ground truth across a boundary while
18/19 still clears the 0.9 floor; production stayed untouched pending the gated
follow-through (D4); the floor stays 0.9 (D5) and every default stays put (D6).

### Reconciliation with ADR-0017 item 3

ADR-0017 item 3 refused to broaden `adoption-loop`'s ground truth because "broadening its
ground truth to force a pass would hide a genuinely hard retrieval case". That ruling
rejected bending the *test*; this step does not touch the question or its expected items.
It fixes the *documented fact* so it physically fits the chunking, which is the
corpus-shape work ADR-0021's diagnostics prescribe. Rejected alternatives: reshaping the
question (teaching the test, the exact thing ADR-0017 forbade) and accepting the miss
forever (a constant miss in the gate population measures nothing and permanently halves
the floor headroom).

### Phase A receipt (Sage, 2026-07-07 UTC, on the Spark; scratch indices only, production index and repo tree untouched and verified clean after)

**The edit (Nova applies to `src/mnemosyne/packs/ubiquiti/sources/seed-unifi-concepts.md`
exactly; one contiguous replacement, nothing else in the file changes):**

```
OLD (line 24):
oscillates between states (an "adoption loop"), the usual causes are:

NEW (lines 24-25):
oscillates between states (an "adoption loop", most often cleared by a factory reset or a
corrected inform URL), the usual causes are:
```

`"adoption loop"` and `factory reset` now sit ~42 chars apart in one sentence, so every
chunking that keeps a sentence intact co-locates them. Meaning preserved: the
parenthetical summarizes the remedy the cause list two lines below already states. No
em-dash introduced; no other section touched (D2 verified: the file diff is this one
replacement).

**Verification receipts (per-question, per D3):**

```
scratch local-only ingest (edited seed): 4 docs / 43 chunks (was 42; one boundary shifted)
  eval (19-question gate population):    19/19  misses: none
  all 18 previously-hitting ids re-verified hit; adoption-loop recovered

scratch FULL ingest with URL fetch (temp knowledge dir): 18 docs / 295 chunks
  fetch health: all 14 help.ui.com URLs fetched, no warnings/skips
  (production re-ingest de-risked; count matches production 294 + 1 seed-edit chunk)
  eval --include-fetched (32 questions):  30/32
  fetched-coverage subset:                13/13 (unchanged)
  misses: port-profiles, poe-cycle (the known served rank problems, ADR-0021)
  adoption-loop: recovered on the served-style index as predicted
```

Spark working tree restored via `git checkout` (porcelain count 0) and both scratch
knowledge dirs removed. `questions.yaml` untouched throughout (D1; Vera re-verifies by
diff at the gate).

## Consequences

- The local gate population scores 19/19 on the scratch build (from a constant 18/19),
  restoring two questions of floor headroom; the eval-gate CI job re-proves the local
  number on every PR. The served history should move 29/32 -> 30/32 once production
  re-ingests.
- **Floor-ratchet option recorded (D5).** `DEFAULT_MIN_HIT_RATE` stays 0.9 this step, per
  the ADR-0012/ADR-0014 precedent that floors move in their own reviewed step once the new
  level proves stable. Once 19/19 holds across a few history lines, a ratchet (e.g. to
  0.94) is a candidate one-line step with its own ADR note.
- **Production re-ingest protocol (post-merge, Jon-gated, on his host):** back up the
  production `knowledge/ubiquiti` index dir; full production re-ingest (picks up the
  edited seed and refetches URLs); verify the chunk count is sane against the Phase-A
  scratch build (expect ~295); run `eval-served.sh ubiquiti` for the new history line
  (expect 30/32); restore the backup if ingest degrades the corpus. Recorded drift caveat:
  the refetch may change fetched content, so the new history line can move for reasons
  beyond the seed edit; the JSONL keeps lines distinguishable (ADR-0019 posture).
- The two remaining served misses, `port-profiles` and `poe-cycle`, are the known rank
  problems ADR-0021 closed for now; nothing here touches them.
- The living-doc number citations (`deploy/README.md` served-eval section, ROADMAP
  served-eval box) now carry the Phase-A numbers, labeled as scratch measurements pending
  the production re-ingest.

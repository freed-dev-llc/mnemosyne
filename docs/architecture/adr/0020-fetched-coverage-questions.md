# 20. Fetched-coverage eval questions: a corpus tag keeps the CI gate deterministic

Date: 2026-07-07

## Status

Accepted

## Context

All 19 ubiquiti eval questions were authored from the four curated primers, so every eval,
including the served-corpus history (ADR-0019), measured *curated-fact survival under
fetched-content dilution*. Nothing measured whether the 252 fetched chunks (14 Help Center
pages) are themselves retrievable: fetched-content coverage. ADR-0017 makes that coverage
instrument the prerequisite for ever productizing the prototyped reranker, whose `alpha`
was tuned on the same 19-question set it was scored on; a question population the
prototype was never tuned on is the unlock.

Adding fetched-coverage questions naively would break CI: the `eval-gate` scores the
deterministic local-only corpus (42 curated chunks) against `DEFAULT_MIN_HIT_RATE = 0.9`,
and fetched ground truth cannot hit there. The mechanism below keeps the gate population
fixed by construction.

## Decision

- **Contract extension (ADR-0006).** A question may carry the optional field
  `corpus: fetched`, marking ground truth that exists only when the pack's URL corpus is
  ingested. An absent field means curated; the tag is single-spelling by validation
  (anything else, including an explicit `curated`, is a load error), so provenance stays
  visible per question in one reviewable file. (D1)
- **Default-excluded by construction.** `load_questions(pack)` returns only curated
  questions; `load_questions(pack, include_fetched=True)` returns all. The CI gate and the
  default `mnemosyne eval` population cannot change through flag discipline failure, only
  by code. (D2)
- **CLI surface: `--include-fetched` on `eval`.** Combining it with `--gate` /
  `--min-hit-rate` is a posture clash and dies before any eval work (the floor is
  calibrated to the curated local-only population). It combines with `--json`, and every
  JSON result carries a `corpus` field so history trends can be sliced by question class
  (`jq 'select(.corpus == "fetched")'`). (D3)
- **`scripts/eval-served.sh` passes `--include-fetched`.** The served history series
  measures coverage plus survival together; the `total` field (19 before, 32 after) and
  the per-result `corpus` tags keep old and new lines distinguishable. The weekly timer
  needs no change. (D4)
- **Sourcing policy: identifier-anchored ground truth (Jon's Flag-1 ruling, Option 2).**
  `expected` strings are restricted to non-creative technical material: port numbers,
  protocol/standard names, commands, product/feature/UI names, acronyms, and, where a
  question truly needs it, a factual phrase of a few words. OR-groups bridge wording
  variants. No third-party prose enters git.
- **Authoring rules (D5, inherited from ADR-0014, adapted).** Each question's expected
  substrings must co-locate in one chunk of the *served* index at default chunking,
  verified live before the file is written; and each must miss on the local-only corpus,
  proving it is fetched coverage rather than curated overlap. A fetched page that answers
  a curated question better does not get a duplicate question.

### Phase A receipt (Sage, 2026-07-07 UTC, on the Spark, served index at 294 chunks / v0.4.0 install at `aa7d332`)

Protocol per the brief: for each candidate, retrieve k=5 with production settings
(score_floor 1.0) on the SERVED index and require every expected item to co-locate in
one retrieved chunk; then retrieve on a scratch LOCAL-ONLY index (`ingest --local-only`,
4 docs / 42 chunks) and require a union-miss, proving fetched coverage rather than
curated overlap. Scorer semantics identical to `eval.score` (case-insensitive substring,
OR-groups). 16 candidates drafted, 13 verified PASS, 3 rejected:

```
PASS  dhcp-option-43          served coloc rank=1  Remote-Adoption-Layer-3     local-miss
PASS  l3-adoption-port        served coloc rank=2  Remote-Adoption-Layer-3     local-miss
PASS  setup-blocked-ports     served coloc rank=1  How-to-Set-Up-UniFi         local-miss
PASS  stun-port               served coloc rank=1  Required-Ports-Reference    local-miss
PASS  mdns-forwarding         served coloc rank=1  UniFi-Switch-Settings       local-miss
PASS  igmp-snooping           served coloc rank=1  UniFi-Switch-Settings       local-miss
PASS  acl-unsupported-models  served coloc rank=1  UniFi-Switches-and-ACLs     local-miss
PASS  mac-acl-same-vlan       served coloc rank=1  UniFi-Switches-and-ACLs     local-miss  (reworded once)
PASS  radius-dynamic-vlan     served coloc rank=1  Creating-Virtual-Networks   local-miss
PASS  vlan-magic              served coloc rank=2  Creating-Virtual-Networks   local-miss
PASS  zone-matrix             served coloc rank=3  Zone-Based-Firewalls        local-miss
PASS  l3-switch-routing       served coloc rank=1  Layer-3-Routing             local-miss
PASS  guest-client-isolation  served coloc rank=4  Best-Practices-Guest-WiFi   local-miss
```

Rejected, with reasons (useful signal, record in ADR-0020):
- `network-isolation-oneclick`: HIT on the local-only corpus (the security primer covers
  Network Isolation + inter-VLAN); the D5 curated-overlap guard worked as intended.
- `speedtest-port` (6789): its Required-Ports chunk is not retrievable at k=5 for any
  natural phrasing tried; candidate-recall gap, same class as ADR-0017's `port-profiles`.
- `zbf-builtin-zones` / `zbf-locked-zones`: the ZBF built-in-zones chunk unreachable at
  k=5 under two phrasings; same candidate-recall class. The ZBF page keeps coverage via
  `zone-matrix`.

Coverage: 9 of 14 fetched pages, all five topic areas (adoption 2, setup 1,
switching/VLANs 6, routing/firewall 3, wireless/isolation 1). Not covered:
VLAN-Troubleshooting (no stable identifier anchors), Advanced-Firewall-Rules (the page
calls itself outdated, superseded by ZBF), Device-Adoption (curated adoption overlap;
the L3 page carries the fetched-only adoption facts), Network-and-Client-Isolation
(curated overlap, above). Every expected string complies with the Option-2 policy:
port numbers, protocol/standard names (STUN, mDNS, IGMP, RADIUS, 802.1X, option 43),
commands, product/feature names (FlexMini, USW Industrial, VLAN Magic, Zone Matrix,
Chromecast, Client Device Isolation), and generic technical terms; no third-party prose.

## Rejected alternatives

- **A second questions file for fetched coverage.** Splits the ADR-0006 contract and
  doubles the loader conventions; one file with a per-question tag keeps a single
  reviewable source of truth.
- **Host-side untracked questions (Flag-1 Option 3).** Zero third-party exposure, but the
  labelled set loses its review trail and survives no reinstall; against the ADR-0006
  contract spirit.
- **Verbatim short-phrase quoting (Flag-1 Option 1).** Easiest authoring and exact-match
  fidelity, but it puts Ubiquiti prose fragments in git and is the least drift-stable
  ground truth; the identifier-anchored policy keeps the licensing surface minimal
  (identifiers and facts, not expression).

## Consequences

- The served history series (ADR-0019) now measures both question classes: totals move
  from 19 to 32, old and new lines stay distinguishable, and the per-result `corpus` tags
  make the two trends separable in `jq`.
- Report-only absorbs drift (D6). Help Center pages change; identifier-anchored ground
  truth minimizes but cannot eliminate breakage. A drift-induced miss in the served
  history is review signal, not a broken gate: nothing gates on fetched questions, by
  D2/D3 construction. Expect ground-truth maintenance after re-ingests.
- The CI gate population and its 0.9 floor are unchanged by construction; the default
  `mnemosyne eval` output is byte-identical to before this ADR.
- The reranker decision (ADR-0017 item 1) gains its instrument: a served-index question
  population the prototype's `alpha` was never tuned on. Productization still requires
  its own step and discipline about which questions tune vs score.
- The three rejected candidates document a real candidate-recall gap (`speedtest-port`,
  the ZBF built-in-zones chunk) in the same class as ADR-0017's `port-profiles` miss:
  useful targets for any future retrieval-quality work.

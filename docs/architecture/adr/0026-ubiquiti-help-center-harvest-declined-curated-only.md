# 26. The Ubiquiti Help Center harvest is declined on licensing; the ubiquiti pack reverts to curated-only

Date: 2026-07-07

## Status

Accepted

## Context

The ubiquiti pack shipped a fetched harvest of the Ubiquiti Help Center (help.ui.com): 24
article URLs in `sources.yaml`, fetched at `ingest` and served from the local index (28 docs /
438 chunks), guarded by 22 `corpus: fetched` eval questions (13 under ADR-0020, 9 under
ADR-0023). That harvest (ADR-0023) was gated on fetch-health and dilution — never on a
licensing review. ADR-0025, which declined the parallel Netgate harvest, named this exact gap
in its Consequences: the ubiquiti harvest "was gated on fetch-health and dilution, not on a
licensing review, and help.ui.com content is likewise copyright-asserted. Whether to
license-review or narrow that pack is a separate Jon-gated decision." This ADR records that
review and its outcome.

The review looked for a positive right to reproduce the Help Center article text into a
persistent local index. Findings (2026-07-07), from Ubiquiti's Terms of Service
(ui.com/legal/termsofservice), the Help Center, and help.ui.com/robots.txt:

1. Ubiquiti asserts sole copyright over all Content: "All copyrights ... in and to the Services
   and the Content are the sole property of Ubiquiti or its licensors."
2. The Terms expressly forbid reproduction: users shall not "copy, reproduce, broadcast,
   transmit, republish, distribute, modify, prepare derivative works of ... any Content in any
   way without the prior written permission of Ubiquiti."
3. The only license granted is narrow and is not a reproduction grant: a "worldwide,
   non-sublicensable, non-transferable, non-exclusive, revocable, limited license to use the
   Services solely for Your personal use, to use, manage and monitor Your Products and collect
   and receive data from Your Products." It licenses operating the apps/site for the gear you
   own — not copying the documentation into a database.
4. help.ui.com is a ui.com sub-domain, within the Terms' "Services" / "Content" scope; and the
   copyright in finding 1 holds independently of the Terms in any case.
5. help.ui.com/robots.txt does not disallow the article pages and sets no crawl-delay, so a
   fetch is not robots-prohibited — but robots is an indexing-courtesy signal, not a copyright
   license, and does not cure findings 1-3 (the ADR-0025 ruling).
6. No open-licensed (Creative Commons or equivalent) mirror of the Help Center content was
   found, so there is no permitted subset to narrow to.

The project's own bar (CONTRIBUTING.md; the pack's `sources.yaml` header) is to point
`sources.yaml` at "docs you have the right to use." A positive right to reproduce is absent and
here expressly denied; building a persistent full-text index (whose docstore holds the article
chunk text for citation) is reproduction beyond transient browsing, and personal fair use is a
fact-specific defense, not a license. This is the same bar and the same read as the Netgate
decline (ADR-0025) — if anything a clearer failure: Netgate was silent on reuse, whereas
Ubiquiti expressly prohibits it. Using third-party content is a Jon-gated call: Sage researched
and recommended removal; Jon decided.

## Decision

Decline the fetched help.ui.com harvest and revert the ubiquiti pack to curated-only, mirroring
ADR-0025. Concretely: `sources.yaml` drops all 24 help.ui.com URLs (`urls: []`); the 22
`corpus: fetched` questions are removed from `eval/questions.yaml`, leaving the 19 self-authored
curated questions; the pack's `pack.py` — a `KnowledgePack` subclass whose only purpose was
stripping the "... Ubiquiti Help Center" suffix off fetched page titles — is deleted, reverting
ubiquiti to the base `KnowledgePack` (the pfSense shape), since a curated-only corpus has no
fetched titles to clean. The self-authored primers (the seed model plus the unifi-* security /
RF / operations primers) are unchanged; the pack stays fully offline-buildable and ships no
third-party text. The generic `corpus` / `--include-fetched` loader machinery (ADR-0020) is
retained for any future, properly-licensed corpus; only ubiquiti's fetched data is removed.

Jon chose this removal (Option C) over accepting the harvest with a documented risk rationale
(Option A) and over narrowing to a permitted subset (Option B, which has no basis — no
open-licensed subset exists). Accepting would hold already-shipped work to a lower standard than
the Netgate work declined one step earlier.

## Consequences

- At the next production re-ingest the ubiquiti served index reverts from 28 docs / 438 chunks
  (fetched-inclusive) to 4 docs / 43 chunks (curated-only), proved on a scratch index in this
  step's Phase A. The served eval moves from 39/41 (curated 17/19, fetched 22/22) to 19/19: the
  22 fetched-coverage questions are dropped, and the two standing curated misses (`port-profiles`,
  `poe-cycle`) recover — they were dilution victims of the fetched corpus (ADR-0021), not curated
  defects, so removing that corpus restores them (`channel-2-4ghz` still hits from the primer).
  The rising hit-rate (0.951 -> 1.000) is a coverage amputation, not a quality gain: the pack
  loses first-party-grounded coverage across VPN, WireGuard, Teleport, DNS records /
  troubleshooting, switch ACLs, zone-based firewalls, L3 routing / adoption, QoS / DSCP, and
  guest WiFi (24 articles), while keeping the curated UniFi expertise. This is a larger,
  honestly-acknowledged product cost than the Netgate decline, where nothing had shipped.
- The roadmap's UniFi Help Center harvest item is closed with evidence: it is not pursued, and a
  future fetched help.ui.com harvest would require an explicit license basis this review did not
  find. Recorded here so no later step re-opens it blindly (the ADR-0018 / ADR-0021 / ADR-0025
  "declined with receipts" pattern), and closing the "parallel latent question" ADR-0025 flagged.
- Both in-tree packs (ubiquiti, pfSense) are now curated-only and fully offline-buildable — the
  strongest form of the standing "ship no third-party documentation" rule. The ubiquiti pack
  remains the in-tree worked example; it now also exemplifies the project's own licensing
  discipline rather than quietly departing from it.
- The ADR-0020 fetched-question machinery and its synthetic-fixture tests remain, so a future
  properly-licensed corpus can use them without re-derivation. ADRs 0020, 0022, 0023 stand as
  history (the harvest happened and was measured); this ADR supersedes their disposition for
  ubiquiti.

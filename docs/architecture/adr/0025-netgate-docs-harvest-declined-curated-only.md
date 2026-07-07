# 25. The Netgate pfSense documentation harvest is declined on licensing; the pack matures curated-only

Date: 2026-07-07

## Status

Accepted

## Context

The v0.x roadmap carried a pfSense-pack "R2" item: a fetched Netgate documentation harvest,
mirroring the ubiquiti Help Center harvest (ADR-0023) — add `docs.netgate.com` URLs to the
pack's `sources.yaml`, fetch the article text at ingest (never committing it, per the standing
"ship no third-party documentation" rule), and guard the new coverage with `corpus: fetched`
questions (ADR-0020). That harvest was explicitly deferred pending a licensing review of
Netgate's documentation. This ADR records that review and its outcome.

The review looked for a positive right to reproduce the documentation text into a persistent
local index. Findings (2026-07-07):

1. Every current pfSense documentation page — the landing page and deep article pages alike —
   carries an all-rights-reserved footer: "© 2026 Electric Sheep Fencing LLC and Rubicon
   Communications LLC. All Rights Reserved." No page states a content license.
2. The documentation's own "Licensing" page covers the pfSense *software* and its bundled
   packages (BSD/GPL/MIT/Apache), not the documentation prose.
3. The only Creative Commons grant found — CC BY-NC-SA 4.0 — is on the `github.com/pfsense/docs`
   repository, which has been archived read-only since 2020-09-24 and is self-described as
   deprecated, its contents "merged with the pfSense Book" (the current docs). That license
   attaches to superseded 2020 wiki content, not to what a harvest would fetch today.
4. Netgate's Website Terms & Conditions assert copyright over all site content ("... the
   property of Netgate, ESF, or its or their content suppliers, and is protected by United
   States and international copyright laws") and offer no personal or non-commercial reuse grant.
5. "Free to access" is not "free to reuse": Netgate released the book content for free reading
   in 2018, but under the all-rights-reserved notice above, with no reproduction grant.
6. `docs.netgate.com/robots.txt` does not disallow `/pfsense/` and sets no crawl-delay, so a
   fetch is not robots-prohibited — but robots is an indexing-courtesy signal, not a copyright
   license, and does not cure findings 1-5.

The project's own bar (CONTRIBUTING.md) is to point `sources.yaml` at "docs you have the right
to use." A positive right to reproduce is absent, and building a persistent full-text index is
reproduction beyond transient browsing; personal fair use is a fact-specific defense, not a
license. Shipping or using third-party content is a Jon-gated call: Sage researched and
recommended, Jon decided.

## Decision

Decline the fetched Netgate harvest. The pfSense pack matures toward the ubiquiti pack's depth
the way it was seeded (ADR-0024): self-authored original primers stating public,
non-copyrightable pfSense facts (default addresses, mode/protocol/feature names, menu paths),
grounded in — but copied from none of — the Netgate documentation, plus identifier-anchored
curated questions (ADR-0006). `sources.yaml` keeps `urls: []`; the pack stays offline-buildable;
no `corpus: fetched` questions and no title-cleanup `pack.py` are added (both were needed only
for a fetched harvest). Jon chose this curated-only path over the two alternatives considered: a
narrow harvest of the CC BY-NC-SA archived repo (legally possible for private, non-redistributed
local use, but stale 2020 content — a product-quality hazard), and the declined full
`docs.netgate.com` harvest.

This R2 adds three new primers — aliases and advanced rules; multi-WAN and traffic shaping;
diagnostics and backup — and eight curated questions (pfSense 17 -> 25), including the `aliases`
and `floating-rules` pair that Steps 12-13 deferred as a recall-rank gap (ADR-0021 class): a
dedicated aliases-and-advanced-rules primer gives those facts a co-located chunk, and both
questions now retrieve at k=5.

## Consequences

- The roadmap's pfSense "R2 fetched harvest" item is closed with evidence: it is not pursued,
  and a future fetched Netgate harvest would require an explicit license basis this review did
  not find. Recorded here so no later step re-opens it blindly (the ADR-0018 / ADR-0021
  "declined with receipts" pattern).
- The pfSense pack remains fully offline-buildable and ships no third-party text — the strongest
  form of the standing corpus rule.
- Parallel latent question, out of scope here: the ubiquiti Help Center harvest (ADR-0023) was
  gated on fetch-health and dilution, not on a licensing review, and help.ui.com content is
  likewise copyright-asserted. Whether to license-review or narrow that pack is a separate
  Jon-gated decision, not settled by this ADR.
- Curated-only growth measures no fetched-content coverage (there is none) and adds no ADR-0020
  fetched population; the pfSense served gate stays the curated local-only set.

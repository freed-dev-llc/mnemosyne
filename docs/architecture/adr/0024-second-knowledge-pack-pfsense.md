# 24. A second knowledge pack: pfSense

Date: 2026-07-07

## Status

Accepted

## Context

Until now Mnemosyne shipped one real vendor expert, the in-tree `ubiquiti` pack (ADR-0003),
alongside a `general` operating-knowledge pack that carries no eval set. That is enough to prove
the pipeline runs, but not that the knowledge-pack model generalizes. A framework whose only
worked example is the vendor it was designed around has not yet earned the claim at the heart of
ADR-0003: that you add an expert by adding a pack, not by editing the pipeline.

pfSense is a strong second vendor to test that claim. It is an open-source firewall and router
built on FreeBSD and the `pf` packet filter, with deep public documentation and a stable,
well-defined core: interfaces and defaults, a stateful first-match rule engine, NAT modes, and
built-in VPNs. Its concepts are short and procedural, so they chunk the same way the UniFi help
content does, and the same 500/150 chunking and 0.9 retrieval floor apply unchanged.

## Decision

Ship `pfsense` as the first in-tree vendor pack beyond the `ubiquiti` worked example, with a
deliberately minimal but real seed. The scope decisions, which future vendor packs can copy:

- **Platform scope: pfSense only.** OPNsense shares most of the same FreeBSD/`pf` core, but one
  canonical answer per question keeps the ground truth clean and procedural. A sibling `opnsense`
  pack is cheap to add later. We do not fold both vendors into one pack, which would muddy the
  ground truth and force a broader, less precise name.
- **In-tree.** The pack is a subdirectory of `mnemosyne.packs` with a `manifest.yaml`, so
  `discover_packs()` registers it automatically. It needs no `pack.py`: the base `KnowledgePack`
  reads the manifest and the local primers. No pipeline, service, CLI, HTTP, or MCP code changed;
  the pack is purely additive (ADR-0003).
- **Curated-only seed.** Three self-authored primers (core concepts, firewall rules, NAT and VPN)
  and ten curated retrieval questions. The corpus is offline-buildable: `sources.yaml` lists no
  URLs, so `mnemosyne ingest pfsense --local-only` builds the index with zero network, and the
  question set clears the 0.9 retrieval floor (ADR-0008) at 10/10 on a scratch index. Fetched
  Netgate pages and their coverage questions are a later roadmap step.
- **Self-authored prose sourcing.** The primers are original prose stating public,
  non-copyrightable facts (default addresses, mode names, protocol names), grounded in the Netgate
  documentation but copied from none of it. This upholds the standing rule that Mnemosyne ships no
  third-party documentation (ADR-0003). A licensing review of Netgate docs is deferred to the
  fetched-harvest step, where it actually applies.
- **The pack `name` is a public contract.** `pfsense` is the identifier Argus can pair against a
  `pfsense`/`netgate` vendor and the key stored in served-eval history, so renaming it later is
  breaking (ADR-0015). It is chosen for the long-term shape, not just this seed.

`pfsense` is wired into the CI `eval-gate` job as a second gated pack, giving it a regression floor
from day one. The gate stays non-blocking by construction (ADR-0008).

Two authored candidate questions, `aliases` and `floating-rules`, are held back. Their anchors are
in the corpus, but the short Aliases and Floating sections rank below k=5 on the scratch index, so
this is a retrieval-rank gap, not a ground-truth gap (the same class as `ubiquiti`'s
`port-profiles` and `poe-cycle`, ADR-0021). Both primer sections stay in the corpus for
completeness; reshaped questions that guard them are a follow-on step.

## Consequences

- The knowledge-pack model is shown to generalize. A real second vendor was added by creating one
  directory of declarative files, with no pipeline edits, exactly as ADR-0003 intended.
- Future vendor packs have a copyable precedent for the scope decisions above: platform scope,
  in-tree, a curated-only first seed, self-authored sourcing, and naming as a public contract.
- The pfSense expert answers only from its curated seed for now, so its coverage is intentionally
  narrow. The roadmap widens it one reviewable step at a time: a fetched Netgate harvest, primers
  for high availability (CARP, pfsync) and packages (Suricata, pfBlockerNG), and a sibling OPNsense
  pack.
- This does **not** close the ROADMAP's "second vendor pack proving the out-of-tree entry-point
  path" item. `pfsense` ships in-tree; the out-of-tree distribution path and the paired Argus
  `knowledge_pack` link (ADR-0015) remain a separate, packaging-level step.

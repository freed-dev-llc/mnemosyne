# 27. A third knowledge pack: OPNsense (the first fork-sibling)

Date: 2026-07-07

## Status

Accepted

## Context

Mnemosyne ships two vendor experts, the in-tree `ubiquiti` (ADR-0003) and `pfsense` (ADR-0024)
packs, alongside a `general` operating-knowledge pack. ADR-0024 proved the knowledge-pack model
generalizes to a second real vendor with no pipeline edits, and it reserved the next move
explicitly: "OPNsense shares most of the same FreeBSD/`pf` core [...] A sibling `opnsense` pack is
cheap to add later. We do not fold both vendors into one pack."

OPNsense is that sibling, and it raises a question the first two packs did not. OPNsense is a 2015
fork of pfSense by Deciso; the two share FreeBSD and the pf packet filter, so a naive `opnsense`
pack would be the `pfsense` pack with the labels changed. Two packs whose ground truth is the same
set of shared pf facts are redundant: they cost twice the maintenance and teach nothing new. A
fork-sibling pack has to earn its place.

Sourcing is the other open question. The `pfsense` (ADR-0025) and `ubiquiti` (ADR-0026) fetched
harvests were both declined on licensing grounds: the Netgate docs are all-rights-reserved, and the
Ubiquiti Help Center Terms of Service forbid reproduction. OPNsense's licensing differs and needs
recording so its disposition is not assumed to match.

## Decision

Ship `opnsense` as the third in-tree vendor pack, a sibling of `pfsense`, with a curated seed of
3 self-authored primers (core concepts; the plugin system; firewall model and intrusion detection)
and 11 identifier-anchored curated questions that clear the 0.9 retrieval floor (ADR-0008) at 11/11
on a scratch index. It reuses the ADR-0024 shape unchanged: in-tree, manifest-driven, no `pack.py`,
`sources.yaml urls: []`, offline-buildable, wired into the CI `eval-gate`. Two decisions are new:

- **A fork-sibling pack anchors on vendor-distinct facts.** The gated question set for a pack that
  forks another must be dominated by facts that distinguish the two vendors, not facts they share.
  For `opnsense` the distinct anchors are the `os-` plugin system installed from System > Firmware >
  Plugins, Zenarmor (formerly Sensei) installed as the `os-sensei` plugin, Suricata built into the
  base under Services > Intrusion Detection (where pfSense adds Snort or Suricata as packages), the
  Phalcon MVC web GUI (where pfSense has the webConfigurator), and the Community versus Business
  editions. Shared pf facts (FreeBSD, the pf packet filter, stateful first-match rules, inbound
  filtering) stay in the corpus because they are genuinely OPNsense's answers to foundational
  questions, but they are the minority of the gated anchors. A reader can tell the two packs apart
  from the answers alone. This keeps two near-identical packs from collapsing into one and upholds
  ADR-0024's one-canonical-answer-per-question stance and its refusal to fold both vendors into a
  single pack. Every anchor is still verbatim in a co-located chunk (ADR-0006, ADR-0020, ADR-0022).

- **OPNsense sourcing: self-authored, over BSD-2-Clause sources.** The OPNsense documentation
  (github.com/opnsense/docs) and core (github.com/opnsense/core) are both licensed BSD-2-Clause, a
  permissive license that would allow a fetched harvest with attribution. That is a different
  disposition from the Netgate (ADR-0025) and Ubiquiti (ADR-0026) declines, recorded here so a
  future harvest step starts from the right footing. For this seed the pack is self-authored anyway,
  for consistency with the `pfsense` and `ubiquiti` packs and to keep the "ship no third-party
  documentation" rule (ADR-0003) uniform across packs. The primers state public, non-copyrightable
  facts (platform and protocol names, plugin identifiers, menu paths, editions) in original prose
  grounded in but copied from none of the OPNsense docs.

The pack `name` `opnsense` is a public contract (ADR-0015): it is the key Argus pairs against an
OPNsense vendor and the key stored in served-eval history, chosen for the long-term shape.

## Consequences

- The knowledge-pack model holds for a fork-sibling, not only for an unrelated second vendor. Two
  vendors that share a codebase coexist as separate experts because their gated ground truth is
  distinct.
- Future fork or near-duplicate vendor packs have a rule to follow: anchor on what distinguishes the
  vendor, keep shared facts as the minority, and require that a reader can tell the packs apart from
  the answers.
- The OPNsense expert answers only from its curated seed for now, so its coverage is intentionally
  narrow. The roadmap widens it one reviewable step at a time: HA and CARP, the NAT and VPN model
  (WireGuard in the base system versus the `os-wireguard` plugin), DNS, and backups, plus a possible
  fetched harvest that its BSD-2-Clause license now permits.
- The `opnsense` gated set is 11 questions from day one, because all 11 candidates cleared the floor
  at 11/11; none were held back as a retrieval-rank gap. This contrasts the `pfsense` `aliases` and
  `floating-rules` deferrals (ADR-0024) and the `ubiquiti` `port-profiles` case (ADR-0021).

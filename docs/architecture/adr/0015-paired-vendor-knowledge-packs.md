# 15. Paired vendor + knowledge packs (Mnemosyne ↔ Argus)

Date: 2026-06-29

## Status

Accepted

## Context

Mnemosyne knowledge packs ([ADR-0003](0003-knowledge-packs.md)) and Argus vendor packs
([Argus ADR-0005](https://github.com/freed-dev-llc/argus/blob/main/docs/architecture/adr/0005-vendor-packs.md))
were designed in parallel. Both are entry-point plugins (`mnemosyne.knowledge_packs` /
`argus.vendor_packs`), both ship in-tree or as installed distributions, and both are keyed by
vendor — Mnemosyne's `ubiquiti` is the knowledge counterpart to Argus's `unifi`. Nothing
connected the two halves, though: the names differ, and the Argus dashboard hardcoded the
`ubiquiti` pack when it proxied questions to `mnemosyne-http`. The moment a second vendor
existed, the dashboard would have asked the wrong expert.

## Decision

A vendor has two faces — a *discovery* face (Argus) and a *knowledge* face (Mnemosyne) — that
share a vendor but not necessarily a name. The **link is owned on the Argus side**
([Argus ADR-0013](https://github.com/freed-dev-llc/argus/blob/main/docs/architecture/adr/0013-paired-vendor-knowledge-packs.md):
a `VendorPack.knowledge_pack` field names the Mnemosyne pack, surfaced so the dashboard queries
the right one). Mnemosyne's commitments that keep the link working:

- **Stable pack names.** A pack's `name` (e.g. `ubiquiti`) is the public identifier Argus
  stores and queries; renaming a pack is a breaking change.
- **A stable `/ask` contract** — `{pack, question} -> {answer, sources}` over both HTTP and MCP
  — so any Argus-declared pack name resolves the same way ([ADR-0005](0005-mcp-server.md)).
- **One distribution may ship both faces.** As vendors grow, a vendor's distribution can
  advertise both entry points (`mnemosyne.knowledge_packs` and `argus.vendor_packs`) under the
  same vendor, so a single install gives Argus its collector and Mnemosyne its knowledge. The
  two install into their own service environments; the services stay independently deployed.
- **Shared settings ride with the pack (goal).** A vendor's shared deployment settings (its
  connection/config and the Argus↔Mnemosyne wiring, such as the `MNEMOSYNE_URL` target and the
  pack name) can travel in that one distribution, so installing the shared pack configures both
  faces rather than each being set up by hand. UniFi/Ubiquiti is the reference pair for this.

## Consequences

- The coupling is loose and name-based: Mnemosyne owns the knowledge face and its pack names;
  Argus references them. No shared runtime dependency in either direction.
- Pack names are part of the contract now — worth keeping stable and, over time, aligning the
  discovery and knowledge names per vendor.
- Shipping both faces from one distribution is a convention realized when the second vendor
  lands; nothing here forces a packaging layout today.
- The install-together target is "install the shared vendor pack on each side," with
  UniFi/Ubiquiti as the first such pack. Building that single dual-entry-point distribution is
  roadmap work (see `docs/ROADMAP.md`).

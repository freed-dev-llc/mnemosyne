# 3. Knowledge packs as the unit of expertise

Date: 2026-06-23

## Status

Accepted

## Context

Mnemosyne's value is *packaged experts*, not a generic document chatbox. Each expert has
its own corpus, its own ideal chunking and models, and its own persona/system prompt. We
need a unit that bundles all of that, can be discovered at runtime, and can grow to many
vendors without turning the pipeline into a pile of special cases.

[Argus](https://github.com/freed-dev-llc/argus) already solved the analogous problem for
*discovery* with **vendor packs** ([Argus ADR-0005](https://github.com/freed-dev-llc/argus/blob/main/docs/architecture/adr/0005-vendor-packs.md)):
a self-contained plugin per vendor, discovered via an `argus.vendor_packs` entry point, so
packs live in-tree or out-of-tree and ship independently. Mnemosyne's first real use case
*is* being an expert for the vendors Argus discovers — so aligning the two models is both
natural and strategically useful.

## Decision

Adopt **knowledge packs** as the unit of expertise, deliberately parallel to Argus vendor
packs:

- A pack is a directory with a declarative `manifest.yaml` (name, models, chunking,
  persona, sources), an optional `pack.py` (`KnowledgePack` subclass for custom loading),
  and a `sources/` corpus.
- Packs are discovered two ways: **in-tree** (subpackages of `mnemosyne.packs` with a
  manifest) and **out-of-tree** (distributions exposing a `mnemosyne.knowledge_packs`
  entry point).
- The pack owns *what* (corpus, models, persona); the pipeline owns *how* (the generic
  load→chunk→embed→retrieve→generate machinery). Adding an expert never edits the pipeline.
- **Ubiquiti** ships in-tree as the worked example, matching Argus's in-tree **UniFi**
  vendor pack.

## Consequences

- New experts are additive and isolated — copy a directory, edit a manifest, point at docs.
- The Argus/Mnemosyne pairing is symmetric and legible: Argus *discovers* a vendor,
  Mnemosyne *explains* it, and the two can expand vendor coverage in lockstep.
- Mnemosyne ships no third-party documentation — packs ship structure and a source list;
  the corpus is populated locally and kept out of git, respecting licensing.
- A manifest schema must be kept stable-ish; manifest changes are themselves ADR-worthy.

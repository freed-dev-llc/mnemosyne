# Knowledge Packs

A **knowledge pack** is a self-contained expert: a corpus of documents plus a manifest
that says how to load, chunk, embed, and *speak about* that corpus. One pack → one expert.

The design mirrors **Argus vendor packs**
([ADR-0005](https://github.com/freed-dev-llc/argus/blob/main/docs/architecture/adr/0005-vendor-packs.md)):
a pack is a small, declarative plugin discovered at runtime, so packs can live in-tree
(like `ubiquiti`) or ship out-of-tree and independently. Argus *discovers* a vendor;
Mnemosyne *explains* it.

## Anatomy of a pack

```
src/mnemosyne/packs/general/
├── __init__.py
├── manifest.yaml     # declarative config: name, models, chunking, sources, persona
├── pack.py           # KnowledgePack subclass — loaders + any custom normalization
└── sources/          # the corpus: local docs and/or a list of URLs to fetch
    └── sources.yaml
```

### `manifest.yaml`

The manifest is the whole pack in one readable file:

```yaml
name: ubiquiti
title: Ubiquiti / UniFi Networking Expert
description: >
  An expert on Ubiquiti UniFi networking — switching, routing, wireless,
  adoption, and controller operations.

# Models (override the global defaults for this pack)
embedding_model: bge-m3
chat_model: qwen2.5:1.5b

# Chunking
chunk_size: 800
chunk_overlap: 120

# Retrieval
top_k: 5

# The expert's persona — becomes the system prompt
system_prompt: >
  You are a Ubiquiti UniFi networking expert. Answer using ONLY the provided
  context. Cite sources as [n]. If the context does not contain the answer,
  say so plainly and do not invent configuration steps.
```

### `pack.py`

Most packs need no Python at all — the base class reads the manifest and the `sources/`
list. Override `pack.py` only when a corpus needs custom handling (a bespoke loader, a
cleanup pass, scraping logic). The shipped `general` pack keeps this minimal: no override,
just the subclass for discovery and as an extension point:

```python
from mnemosyne.packs.base import KnowledgePack

class GeneralPack(KnowledgePack):
    """A curated, growing corpus for grounding decisions (how to decide, not how tech works)."""
    # Inherits manifest-driven loading as-is. Override load() only if a corpus later needs
    # custom preprocessing.
```

### `sources/`

The corpus. Three ways to provide it, mixable:

- **Local files** — drop `.md` / `.pdf` / `.html` / `.txt` into `sources/`.
- **URLs** — list them in `sources/sources.yaml`; `ingest` fetches and caches them.
- **Manually-staged third-party docs**: set `MNEMOSYNE_STAGING_DIR` to a directory
  *outside* the repo, and drop files under `<dir>/<pack-name>/`; `ingest` folds them into
  the corpus exactly like `sources/`. This is for docs you can fetch yourself but Mnemosyne
  can't (a blocked host, a document you don't want anywhere near git even transiently): save
  each page as `.html` or print it to `.pdf`, drop it in `<dir>/<pack-name>/`, then run
  `mnemosyne ingest <pack>`. See [ADR-0016](architecture/adr/0016-manual-doc-staging-via-env-var.md).

```yaml
# sources/sources.yaml
urls:
  - https://docs.example.com/articles/<id>   # title captured for citations
local:
  - ./sources/unifi-switching-notes.md
```

> **Licensing matters.** Only ingest documents you have the right to use. Mnemosyne ships
> *no* vendor documentation — the `ubiquiti` pack ships the structure and a starter source
> list; you populate the corpus locally. Keep third-party docs out of git (the
> `knowledge/` and fetched-cache paths are gitignored). If a doc can't even be fetched from
> where Mnemosyne runs, or you'd rather it never touch git at all, stage it via
> `MNEMOSYNE_STAGING_DIR` instead.

## Building your own pack

1. Copy `src/mnemosyne/packs/ubiquiti/` to `src/mnemosyne/packs/<yourpack>/`.
2. Edit `manifest.yaml` — name, persona, models, chunking.
3. Point `sources/sources.yaml` at your documents.
4. Register it (in-tree packs are auto-discovered; out-of-tree packs expose a
   `mnemosyne.knowledge_packs` entry point in their own `pyproject.toml`).
5. Build and query:

```bash
mnemosyne ingest <yourpack>
mnemosyne ask <yourpack> "your question"
```

## Discovery

Packs are found two ways, unioned at runtime:

- **In-tree** — any subpackage of `mnemosyne.packs` with a `manifest.yaml`.
- **Out-of-tree** — any installed distribution advertising a `mnemosyne.knowledge_packs`
  entry point, e.g.:

  ```toml
  # in an external pack's pyproject.toml
  [project.entry-points."mnemosyne.knowledge_packs"]
  paloalto = "mnemosyne_pack_paloalto:PaloAltoPack"
  ```

`mnemosyne packs` lists everything discovered and whether each has a built index.

## Relationship to Argus vendor packs

| | Argus vendor pack | Mnemosyne knowledge pack |
| --- | --- | --- |
| **Answers** | "What is on the network?" | "How does this technology work?" |
| **Input** | Live device/API (a collector) | Documents (a corpus) |
| **Output** | NetBox truth (DCIM/IPAM) | Grounded, cited answers |
| **Entry point** | `argus.vendor_packs` | `mnemosyne.knowledge_packs` |
| **First pack** | UniFi (in-tree) | Ubiquiti (in-tree) |

The two are meant to expand in lockstep: when Argus learns a new vendor, Mnemosyne grows
the matching expert. See [ROADMAP.md](ROADMAP.md).

**One distribution, both faces.** A vendor's collector and its knowledge can ship as a single
installable distribution that advertises **both** entry points (`argus.vendor_packs` and
`mnemosyne.knowledge_packs`), so one `pip install` gives Argus its collector and Mnemosyne its
knowledge; the names need not match (`unifi` ↔ `ubiquiti`), and the link is a data field on the
Argus side ([ADR-0015](architecture/adr/0015-paired-vendor-knowledge-packs.md)). The intent is
that installing the shared UniFi/Ubiquiti pack sets up **both** deployments, with the vendor's
shared settings carried by the pack rather than configured on each side by hand. The two still
install into their own service environments and stay independently deployed.

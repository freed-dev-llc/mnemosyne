"""Minimal end-to-end example: build the Ubiquiti index, then ask it a question.

Run from the repo root with Ollama running and the default models pulled:

    python examples/ask_ubiquiti.py

This is the library API behind the `mnemosyne ingest` / `mnemosyne ask` CLI commands.
"""

from __future__ import annotations

from mnemosyne import RagPipeline, ingest
from mnemosyne.index import index_dir, index_exists
from mnemosyne.packs import get_pack


def main() -> None:
    pack = get_pack("ubiquiti")

    # Build the index once (skip if it already exists).
    if not index_exists(index_dir(pack.name)):
        stats = ingest(pack)
        print(f"Indexed {stats.documents} docs into {stats.chunks} chunks → {stats.index_path}")

    # Ask the expert.
    pipeline = RagPipeline(pack)
    answer = pipeline.ask("What causes a UniFi device to get stuck in an adoption loop?")

    print("\n" + answer.text + "\n")
    print("Sources:")
    for s in answer.sources:
        print(f"  [{s.n}] {s.title} ({s.source})")


if __name__ == "__main__":
    main()

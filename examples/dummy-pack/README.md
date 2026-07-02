# dummy-pack (throwaway proof-of-packaging fixture)

This is **not** a real knowledge pack. It exists solely to prove, end to end, that a
knowledge pack packaged as its own separately-installable distribution registers itself
with Mnemosyne through a real `mnemosyne.knowledge_packs` entry point (issue #61,
Candidate Step B): the packaging path a real vendor pack would use, exercised for real
rather than monkeypatched.

It has no corpus and is never ingested or asked. Do not point `mnemosyne ingest` or
`mnemosyne ask` at it.

## What it proves

Installing this package (`pip install -e examples/dummy-pack`) makes
`mnemosyne.packs.registry.discover_packs()` see `dummy-installed-pack` alongside the
in-tree packs, through the unpatched `importlib.metadata.entry_points()` call, no test
monkeypatching involved. See the `dummy-installed-pack` job in
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

# Contributing to Mnemosyne

This is a personal project run with the discipline of a shared one. Mnemosyne is also a
*teaching* repo — clarity is a feature, so favor small, readable changes with a short note
on the *why*.

## Ground rules

- **Land via pull request**, squash-merged. Don't push directly to `main`.
- **Sign your commits** (`git commit -S`). `main` requires signed commits.
- **No agent attribution.** Do not add `Co-Authored-By: <agent>` or "Generated with …"
  trailers to commits or PRs. Author commits as yourself.
- **Update [`CHANGELOG.md`](CHANGELOG.md)** under `[Unreleased]` for any user-visible change.
- **Capture significant decisions** as an ADR in
  [`docs/architecture/adr/`](docs/architecture/adr/) (copy 0001's format).

## Development setup

The environment is managed with `mamba` — the easiest way to install it is
[Miniforge](https://github.com/conda-forge/miniforge) (conda + mamba, conda-forge
preconfigured). It provides FAISS from conda-forge for both CPU and GPU (see
[ADR-0004](docs/architecture/adr/0004-conda-mamba-environment.md)).

```bash
mamba env create -f environment.yml      # GPU: environment-gpu.yml
mamba activate mnemosyne

# Ollama must be running locally with the default models pulled:
ollama pull bge-m3
ollama pull qwen2.5:1.5b
```

No conda? `pip install -e ".[dev,cpu]"` works as a fallback (the `cpu` extra adds faiss-cpu).

## Before you open a PR

```bash
ruff check src tests          # lint
ruff format --check src tests # formatting
mypy src                      # types
pytest                        # tests (no Ollama needed — network calls are not unit-tested)
```

The unit tests deliberately avoid hitting Ollama or the network; they cover chunking,
loaders, the index helpers, and pack discovery. Test pipeline behavior that needs a model
manually via the CLI against a local corpus.

## Adding a knowledge pack

See [`docs/KNOWLEDGE_PACKS.md`](docs/KNOWLEDGE_PACKS.md). In short: copy
`src/mnemosyne/packs/ubiquiti/`, edit `manifest.yaml`, point `sources/sources.yaml` at docs
you have the right to use, and `mnemosyne ingest <pack>`. **Do not commit third-party
documentation** — keep corpora local (the `knowledge/` path and fetched caches are
gitignored).

## Style

- Small, single-purpose modules; the pipeline stays legible.
- Type hints on public functions; `ruff` + `mypy` clean.
- Match the surrounding code's idiom and comment density.

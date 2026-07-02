# 4. Conda/mamba environment (and why not a bare venv)

Date: 2026-06-23

## Status

Accepted

## Context

Mnemosyne needs a reproducible Python environment, and it needs FAISS. The original
scaffold used a plain `venv` + `pip install -e .` with `faiss-cpu` from PyPI. That works on
CPU, but it paints us into a corner the moment we want GPU acceleration: **`faiss-gpu` is
not practically installable from PyPI** — the supported distribution path for GPU FAISS is
conda (`conda install -c pytorch -c nvidia -c conda-forge faiss-gpu`). The
[rag_ollama](https://github.com/MariyaSha/rag_ollama) tutorial this project is based on
makes exactly this point in its "GPU processing" best practice, and uses a conda env.

## Decision

Manage the environment with **[mamba](https://github.com/mamba-org/mamba)** (a fast,
drop-in conda) via committed environment files:

- `environment.yml` — CPU: conda-forge `python=3.12` + `faiss-cpu`, then `pip install -e
  ".[dev]"` for the langchain stack and the package itself.
- `environment-gpu.yml` — identical but with `faiss-gpu` from the pytorch/nvidia/conda-forge
  channels. Swapping this one file is the entire CPU→GPU change; the code is untouched.

FAISS is therefore **provided by the environment (conda)**, not by pip — so `faiss-cpu` is
*not* a core dependency in `pyproject.toml`. It lives in an optional `cpu` extra so a
conda-less user can still `pip install -e ".[dev,cpu]"`.

Tooling split: **locally**, the simplest way to get `mamba` is
[Miniforge](https://github.com/conda-forge/miniforge) (conda + mamba, conda-forge
preconfigured); **CI** uses `micromamba` via `mamba-org/setup-micromamba`. Both consume the
same `environment.yml`, so CI and local dev stay identical — the choice of installer is just
ergonomics (full distribution locally vs. a tiny standalone binary in CI).

## Consequences

- One-file CPU↔GPU swap; GPU FAISS becomes installable, which a venv could not offer.
- CI and local environments are the same artifact (`environment.yml`), reducing drift.
- The langchain packages still come from pip (they are not all reliably on conda-forge),
  giving a conda-for-binaries / pip-for-Python hybrid — the same split rag_ollama uses.
- Cost: contributors need mamba/conda. The `cpu` extra keeps a pip-only fallback for those
  who don't, at the price of no GPU path.
- `faiss-cpu` not being a core dependency means a bare `pip install -e .` (no extra, no
  conda) has no vector store — by design; the env or the `cpu` extra supplies it.

# 16. Manual doc staging via `MNEMOSYNE_STAGING_DIR`

Date: 2026-07-01

## Status

Accepted

Editorial note (2026-07-07): issue/PR numbers cited in this ADR use pre-rewrite
numbering; the repository history was re-created on 2026-07-04, so those references no
longer resolve.

## Context

Mnemosyne ships no third-party docs (ADR-0003). The two existing corpus paths (`sources/`,
git-tracked; `urls:`, fetched-not-cached) both assume content that's either fine to hold in
git or safe to refetch. Issue #60: `help.ui.com` 403s from some networks, blocking the `urls:`
path for the UniFi Help Center corpus; a maintainer fetches those pages from an unblocked
network and needs to feed the saved files into `ingest` without the text ever entering git.

## Decision

Add `Settings.staging_dir: Path | None` (env `MNEMOSYNE_STAGING_DIR`, default unset), a
directory living entirely outside the repository. `pipeline.ingest()` resolves
`settings.staging_dir / pack.name` and passes it to `KnowledgePack.load()` /
`resolve_sources()`, which fold in any supported-suffix file found there, same as
`sources/`. Unset (default) contributes nothing and changes no existing behavior.

## Rejected alternatives

- A pack-relative gitignored `sources/staging/` directory: still inside the repo's working
  tree, so a careless `git add -A`/`-f` could still commit it.
- Anchoring under the existing gitignored `knowledge/<pack>/` build-output directory: same
  in-repo risk as above, plus it mixes disposable rebuild output with a corpus the maintainer
  wants to keep, under a knob (`MNEMOSYNE_KNOWLEDGE_DIR`) meant for index storage, not corpus
  provisioning.

## Consequences

- `KnowledgePack.resolve_sources()` / `load()` gain their first externally-resolved
  parameter (still no `Settings` import in `base.py`, plain `Path | None`); any pack,
  in-tree or out-of-tree, gets manual staging for free by convention.
- CI never sets the env var, so `--local-only` / `eval-gate` determinism is unaffected.
- The staged corpus lives only on the contributor's machine with no backup mechanism other
  than re-fetching. Acceptable: preserving third-party text was never Mnemosyne's job.
- Residual risk, not fixed this step: if `MNEMOSYNE_STAGING_DIR` were misconfigured to a path
  inside the repo, no code currently detects or warns about that. Out of scope for this ADR;
  noted as a known gap.

# Deploying Mnemosyne (`mnemosyne-http`)

Mnemosyne ships two transports over one service layer: an MCP stdio server (`mnemosyne-mcp`,
for agents) and an HTTP server (`mnemosyne-http`, for web UIs / services that can't speak MCP).
This guide covers running `mnemosyne-http` as a managed service — for example, to back the
[Argus](https://github.com/freed-dev-llc/argus) dashboard's "Ask the Brain" panel.

## Prerequisites

- The `mnemosyne` environment installed (see the top-level `README.md` / `environment.yml`).
- **Ollama** running with the pack's models pulled (defaults: `bge-m3` embeddings +
  `qwen2.5:1.5b` chat):

  ```bash
  ollama pull bge-m3
  ollama pull qwen2.5:1.5b
  ```

- Each pack you want to serve **built** — its FAISS index under `knowledge/<pack>/`:

  ```bash
  mnemosyne ingest ubiquiti      # then `mnemosyne packs` shows it as built
  ```

  `mnemosyne-http` answers from built indexes only; querying an unbuilt pack returns `409`.

## Run as a systemd service

A unit template is in [`mnemosyne-http.service`](mnemosyne-http.service). Adjust the `User`,
`WorkingDirectory`, and `ExecStart` paths to your install, then:

```bash
sudo cp deploy/mnemosyne-http.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mnemosyne-http
curl -s http://127.0.0.1:8088/health        # {"status":"ok", ...}
```

`WorkingDirectory` must be the directory that holds the built `knowledge/` tree — the pack
index path is resolved relative to it.

## Updating a deployed install

[`scripts/sync-spark.sh`](../scripts/sync-spark.sh) updates a remote install to a git ref
and brings the `mnemosyne-http` service up to date in one command. Run it locally after
merging to `main` or tagging a release:

```bash
scripts/sync-spark.sh              # sync to origin/main, restart the service if needed
scripts/sync-spark.sh v0.3.2       # sync to a tag, branch, or commit sha
scripts/sync-spark.sh --no-restart # sync only, leave the service running
```

On the target host the script:

- aborts if the working tree is dirty, then fetches and hard-resets the repo to the ref;
- reinstalls the editable package only when `pyproject.toml` changed;
- restarts `mnemosyne-http` when the code moved, the package was reinstalled, or the
  running service version lags the installed version;
- health-checks the service and prints installed vs. running versions.

The restart step matters because the service reports its version from installed package
metadata: an editable install picks up new code on `git pull`, but the running process
keeps serving the old version until it is restarted.

Defaults target the Spark box; override with the `SPARK_HOST`, `SPARK_REPO`, `SPARK_ENV`,
`MNEMOSYNE_SERVICE`, and `MNEMOSYNE_HEALTH_URL` environment variables for another host.

## Served-corpus eval (report-only)

CI's `eval-gate` scores a deterministic local-only corpus, which overstates what a running
server retrieves (ubiquiti: 0.95 local-only vs ~0.84 served; see
[ADR-0017](../docs/architecture/adr/0017-retrieval-quality-known-limitations.md)). Running
the eval on the serving host scores the live index the service answers from, and `--json`
records which index that was:

```bash
scripts/eval-served.sh ubiquiti   # append one snapshot to knowledge/eval-history/ubiquiti.jsonl
```

The script runs `mnemosyne eval <pack> --json` (one JSON line: the scores plus provenance,
so index chunk counts, effective `score_floor` / `faiss_normalize`, installed version, and
a UTC timestamp), appends it to `knowledge/eval-history/<pack>.jsonl` (gitignored, outside
any pack's index directory so a re-ingest cannot clobber it), and echoes the hit rate. It
is report-only and exits 0 on every completed run; see
[ADR-0019](../docs/architecture/adr/0019-served-corpus-eval-report-only.md).

Run it **manually after every production re-ingest** (that is when the number can move),
and on a schedule to catch slow drift. The weekly timer is opt-in, same
adjust-paths-then-install pattern as `mnemosyne-http.service`:

```bash
sudo cp deploy/mnemosyne-eval.service deploy/mnemosyne-eval.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mnemosyne-eval.timer
systemctl list-timers mnemosyne-eval.timer    # next scheduled run
```

Read the history with `jq`:

```bash
jq -r '[.timestamp, .mnemosyne_version, .index.chunks, .hit_rate] | @tsv' \
  knowledge/eval-history/ubiquiti.jsonl
```

`index.chunks` says which index a line measured (42 = local-only seed corpus, ~294 =
fetched-inclusive served index), so local test runs and production snapshots in the same
file stay distinguishable.

**The caveat when reading the number:** the 19 ubiquiti questions are written against the
curated seed corpus, so this eval measures *curated-fact survival under fetched-content
dilution*. A drop means fetched chunks are displacing the curated answer chunks. It does
not measure fetched-content coverage (how well the fetched Help Center pages themselves
are retrieved); that needs question-set expansion, which stays future work (ADR-0019).

## Reachability and security

`mnemosyne-http` has **no authentication** and is meant to be called server-to-server on a
trusted network. The unit sets `MNEMOSYNE_HTTP_HOST=0.0.0.0` so the service is reachable on an
overlay/mesh interface (e.g. [NetBird](https://netbird.io)) as well as localhost. Restrict
access with a firewall or mesh ACLs; do not expose it to the public internet.

### Consumed by Argus

The Argus dashboard reaches Mnemosyne by setting `MNEMOSYNE_URL` to this service's base URL; it
proxies `POST ${MNEMOSYNE_URL}/ask` server-to-server (no browser CORS). When Argus runs in a
container that can't reach the host LAN directly (Docker Desktop), point it at a **mesh IP** of
the Mnemosyne host — e.g. `MNEMOSYNE_URL=http://<netbird-ip>:8088`. See the Argus
`deploy/README.md` "Ask the Brain (Mnemosyne)" section, plus Argus
[ADR-0008](https://github.com/freed-dev-llc/argus/blob/main/docs/architecture/adr/0008-ask-the-brain-mnemosyne.md)
and [ADR-0013](https://github.com/freed-dev-llc/argus/blob/main/docs/architecture/adr/0013-paired-vendor-knowledge-packs.md),
and the knowledge-side counterpart
[ADR-0015](../docs/architecture/adr/0015-paired-vendor-knowledge-packs.md).

Longer term, a vendor (UniFi/Ubiquiti first) can ship as one distribution that installs both
faces, Argus's collector and Mnemosyne's knowledge, so the pair is set up from a single shared
pack rather than wired by hand. Today they are two independently deployed services connected by
`MNEMOSYNE_URL`; see [ADR-0015](../docs/architecture/adr/0015-paired-vendor-knowledge-packs.md).

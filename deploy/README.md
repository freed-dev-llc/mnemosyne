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

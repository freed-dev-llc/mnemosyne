# Security Policy

## Reporting a vulnerability

Mnemosyne is a personal/lab project. If you find a security issue, please report it
privately via [GitHub Security Advisories](https://github.com/freed-dev-llc/mnemosyne/security/advisories/new)
rather than opening a public issue. You'll get an acknowledgement and a fix timeline.

## Scope and posture

Mnemosyne is **local-first by design**: it runs against a local Ollama instance and a
file-based FAISS index, with no cloud LLM calls and no API keys. That removes a large class
of risk, but a few things are worth keeping in mind:

- **FAISS deserialization.** Loading an index uses pickle
  (`allow_dangerous_deserialization=True`). Only load indices **you built yourself**. Treat
  a FAISS index from an untrusted source as untrusted code.
- **Ingested documents.** Anything you ingest becomes context the model may surface
  verbatim. Don't ingest secrets you wouldn't want echoed into an answer.
- **URL fetching.** `ingest` can fetch URLs listed in a pack's `sources.yaml`. Only list
  URLs you trust; fetched content is treated as a document, not executed.
- **Third-party docs / licensing.** Mnemosyne ships no vendor documentation. Keep ingested
  corpora out of version control (the `knowledge/` path is gitignored).

## Dependencies

Dependencies are monitored via Dependabot and patched through normal PRs.

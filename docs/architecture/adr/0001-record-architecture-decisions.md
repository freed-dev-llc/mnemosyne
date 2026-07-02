# 1. Record architecture decisions

Date: 2026-06-23

## Status

Accepted

## Context

Mnemosyne is a personal project run with the discipline of a shared one (the freed-dev-llc
baseline). Design choices in a *teaching* repo are part of the lesson — future readers
(including future me, and the agents that work here) need to know not just *what* the code
does but *why* it is shaped that way.

## Decision

We record architecturally significant decisions as **Architecture Decision Records (ADRs)**
in `docs/architecture/adr/`, using Michael Nygard's lightweight format: a title, a status,
the context, the decision, and its consequences. One file per decision, numbered and
immutable — superseded decisions are marked, not deleted.

## Consequences

- Decisions are discoverable and reviewable in pull requests alongside the code.
- The reasoning survives even after the people involved forget it.
- A small recurring cost: an ADR for each significant choice, kept short.

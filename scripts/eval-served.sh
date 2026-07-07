#!/usr/bin/env bash
#
# Append one served-corpus eval snapshot to the history file (report-only; ADR-0019).
#
# Runs `mnemosyne eval <pack> --json` against the pack's canonical built index (run on
# the serving host, that IS the served index) and appends the JSON line to
# knowledge/eval-history/<pack>.jsonl. The history dir lives under gitignored knowledge/
# but outside any pack's index dir, so a re-ingest cannot clobber it.
#
# Run it manually after every production re-ingest (that is when the number can move),
# and/or on the weekly timer (deploy/mnemosyne-eval.timer). See deploy/README.md.
#
# Usage:
#   scripts/eval-served.sh            # pack defaults to ubiquiti
#   scripts/eval-served.sh <pack>
#
# Overridable via env:
#   MNEMOSYNE_BIN (mnemosyne)  MNEMOSYNE_HISTORY_DIR (knowledge/eval-history)
set -euo pipefail

PACK="${1:-ubiquiti}"
MNEMOSYNE_BIN="${MNEMOSYNE_BIN:-mnemosyne}"

# Run from the repo/install root: the knowledge/ tree the eval reads and the history dir
# it appends to are both resolved relative to the CWD (the same working-directory contract
# as mnemosyne-http.service).
cd "$(dirname "$0")/.."

HISTORY_DIR="${MNEMOSYNE_HISTORY_DIR:-knowledge/eval-history}"
HISTORY_FILE="$HISTORY_DIR/$PACK.jsonl"

line=$("$MNEMOSYNE_BIN" eval "$PACK" --json)

mkdir -p "$HISTORY_DIR"
printf '%s\n' "$line" >>"$HISTORY_FILE"

hit_rate=$(printf '%s' "$line" \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["hit_rate"])')
echo "$PACK hit_rate=$hit_rate -> $HISTORY_FILE"

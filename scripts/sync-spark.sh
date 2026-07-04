#!/usr/bin/env bash
#
# Sync the Spark install to a git ref and bring the mnemosyne-http service
# up to date. Run this locally after merging to main (or tagging a release).
#
# Steps performed on the Spark box:
#   1. Abort if the Spark working tree is dirty (nothing gets clobbered).
#   2. Fetch and hard-reset the repo to the target ref (default origin/main).
#   3. Reinstall the editable package only when pyproject.toml changed.
#   4. Restart mnemosyne-http when the code moved, the package was reinstalled,
#      or the running service version lags the installed version.
#   5. Health-check the service and report installed vs. running versions.
#
# Usage:
#   scripts/sync-spark.sh                 # sync Spark to origin/main
#   scripts/sync-spark.sh v0.3.2          # sync Spark to a tag/branch/sha
#   scripts/sync-spark.sh --no-restart    # sync only, leave the service alone
#
# Overridable via env:
#   SPARK_HOST (spark-aria)  SPARK_REPO  SPARK_ENV
#   MNEMOSYNE_SERVICE (mnemosyne-http)  MNEMOSYNE_HEALTH_URL
set -euo pipefail

SPARK_HOST="${SPARK_HOST:-spark-aria}"
SPARK_REPO="${SPARK_REPO:-/home/aria/Repos/mnemosyne}"
SPARK_ENV="${SPARK_ENV:-/home/aria/miniconda3/envs/mnemosyne}"
SERVICE="${MNEMOSYNE_SERVICE:-mnemosyne-http}"
HEALTH_URL="${MNEMOSYNE_HEALTH_URL:-http://127.0.0.1:8088/health}"

RESTART=1
REF="origin/main"
for arg in "$@"; do
  case "$arg" in
    --no-restart) RESTART=0 ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) REF="$arg" ;;
  esac
done

# Local courtesy check: warn (don't block) if the current branch has commits
# that were never pushed, since Spark syncs from the remote, not this tree.
if git -C "$(dirname "$0")/.." rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  unpushed=$(git -C "$(dirname "$0")/.." rev-list '@{u}..HEAD' --count 2>/dev/null || echo 0)
  [ "$unpushed" -gt 0 ] && echo "warning: $unpushed local commit(s) not pushed; Spark syncs from the remote." >&2
fi

echo "==> Syncing $SPARK_HOST:$SPARK_REPO to $REF"

ssh "$SPARK_HOST" REF="$REF" REPO="$SPARK_REPO" ENVDIR="$SPARK_ENV" \
    SERVICE="$SERVICE" HEALTH_URL="$HEALTH_URL" RESTART="$RESTART" 'bash -s' <<'REMOTE'
set -euo pipefail
cd "$REPO"

if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: Spark working tree is dirty; refusing to reset. Resolve it first:" >&2
  git status --short >&2
  exit 1
fi

OLD=$(git rev-parse HEAD)
git fetch --quiet --tags origin
git reset --quiet --hard "$REF"
NEW=$(git rev-parse HEAD)

changed=0
if [ "$OLD" != "$NEW" ]; then
  changed=1
  echo "    code: $OLD -> $NEW"
else
  echo "    code: already at $NEW"
fi

reinstalled=0
if [ "$changed" -eq 1 ] && ! git diff --quiet "$OLD" "$NEW" -- pyproject.toml; then
  echo "    pyproject.toml changed -> reinstalling editable package"
  "$ENVDIR/bin/pip" install -e . --quiet
  reinstalled=1
fi

installed=$("$ENVDIR/bin/python" -c "from importlib.metadata import version; print(version('mnemosyne-rag'))" 2>/dev/null || echo "?")
running=$(curl -s --max-time 4 "$HEALTH_URL" \
  | "$ENVDIR/bin/python" -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "-")

need_restart=0
[ "$changed" -eq 1 ] && need_restart=1
[ "$reinstalled" -eq 1 ] && need_restart=1
if [ "$running" != "-" ] && [ "$running" != "$installed" ]; then
  echo "    running $running lags installed $installed -> restart needed"
  need_restart=1
fi

if systemctl list-unit-files "$SERVICE.service" >/dev/null 2>&1 \
   && systemctl is-active --quiet "$SERVICE"; then
  if [ "$RESTART" -eq 1 ] && [ "$need_restart" -eq 1 ]; then
    echo "    restarting $SERVICE"
    sudo -n systemctl restart "$SERVICE"
    sleep 2
  elif [ "$need_restart" -eq 1 ]; then
    echo "    (restart skipped: --no-restart)"
  else
    echo "    $SERVICE already current, no restart"
  fi
fi

health=$(curl -s --max-time 5 "$HEALTH_URL" || echo "")
running=$(printf '%s' "$health" \
  | "$ENVDIR/bin/python" -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "-")
echo "==> installed=$installed  service=$running  health=${health:-<no response>}"
REMOTE

echo "==> Done."

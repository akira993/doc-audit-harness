#!/usr/bin/env bash
# write-anchor.sh — write the audit anchor ONLY on a CONSISTENT verdict (spec §5.5/§7).
set -euo pipefail

REPO_ROOT="$(pwd)"; ANCHOR_PATH=""; VERDICT=""; MODE="incremental"; DATE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root) REPO_ROOT="$2"; shift 2;;
    --anchor-path) ANCHOR_PATH="$2"; shift 2;;
    --verdict) VERDICT="$2"; shift 2;;
    --mode) MODE="$2"; shift 2;;
    --date) DATE="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$ANCHOR_PATH" ]] || { echo "error: --anchor-path required" >&2; exit 2; }

if [[ "$VERDICT" != "CONSISTENT" ]]; then
  echo "verdict=$VERDICT — anchor not updated (only CONSISTENT updates the baseline)" >&2
  exit 0
fi

[[ -n "$DATE" ]] || DATE="$(date +%F)"
SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
DEST="$REPO_ROOT/$ANCHOR_PATH"
mkdir -p "$(dirname "$DEST")"
cat > "$DEST" <<JSON
{
  "sha": "$SHA",
  "date": "$DATE",
  "verdict": "CONSISTENT",
  "tool": "docaudit",
  "mode": "$MODE"
}
JSON
echo "anchor written: $ANCHOR_PATH @ $SHA" >&2

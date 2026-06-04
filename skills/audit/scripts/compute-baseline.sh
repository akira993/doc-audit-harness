#!/usr/bin/env bash
# compute-baseline.sh — change set since the audit anchor (spec §5.1).
# Output JSON: {"mode":"full|incremental","baselineSha":str|null,"changed":[...]}
set -euo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$CONFIG" ]] || { echo "error: --config required" >&2; exit 2; }

if ! git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: not a git repository: $REPO_ROOT" >&2; exit 1
fi

py() { python3 -c "$@"; }
ANCHOR_PATH="$(py 'import json,sys; print(json.load(open(sys.argv[1])).get("anchorPath",""))' "$CONFIG")"
GLOBS_JSON="$(py 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])).get("diffGlobs",[])))' "$CONFIG")"

ANCHOR_SHA=""
if [[ -n "$ANCHOR_PATH" && -f "$REPO_ROOT/$ANCHOR_PATH" ]]; then
  ANCHOR_SHA="$(py 'import json,sys; print(json.load(open(sys.argv[1])).get("sha",""))' "$REPO_ROOT/$ANCHOR_PATH")"
fi

MODE="full"; BASELINE="null"; BASE=""
if [[ -n "$ANCHOR_SHA" ]]; then
  if git -C "$REPO_ROOT" cat-file -e "${ANCHOR_SHA}^{commit}" 2>/dev/null; then
    BASE="$(git -C "$REPO_ROOT" merge-base "$ANCHOR_SHA" HEAD 2>/dev/null || true)"
    if [[ -n "$BASE" ]]; then MODE="incremental"; BASELINE="\"$BASE\""; fi
  else
    echo "warn: anchor sha not found in history; falling back to --full" >&2
  fi
fi

{
  if [[ "$MODE" == "incremental" ]]; then
    git -C "$REPO_ROOT" diff --name-only "${BASE}..HEAD"
  fi
  git -C "$REPO_ROOT" diff --name-only HEAD
  git -C "$REPO_ROOT" ls-files --others --exclude-standard
} | sort -u > /tmp/.docaudit_changed.$$ || true

CHANGED_JSON="$(py '
import json,sys,re
def g2r(p):
    out=[];i=0;n=len(p)
    while i<n:
        c=p[i]
        if c=="*":
            if i+1<n and p[i+1]=="*": out.append(".*"); i+=2
            else: out.append("[^/]*"); i+=1
        elif c=="?": out.append("[^/]"); i+=1
        else: out.append(re.escape(c)); i+=1
    return re.compile("^"+"".join(out)+"$")
globs=[g2r(x) for x in json.loads(sys.argv[1])]
paths=[l.strip() for l in open(sys.argv[2]) if l.strip()]
keep=[p for p in paths if (not globs) or any(rx.match(p) for rx in globs)]
print(json.dumps(sorted(set(keep))))
' "$GLOBS_JSON" /tmp/.docaudit_changed.$$)"
rm -f /tmp/.docaudit_changed.$$

printf '{"mode":"%s","baselineSha":%s,"changed":%s}\n' "$MODE" "$BASELINE" "$CHANGED_JSON"

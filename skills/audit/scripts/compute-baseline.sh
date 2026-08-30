#!/usr/bin/env bash
# compute-baseline.sh — change set since the audit anchor (spec §5.1).
# Output JSON: {"mode":"full|incremental","baselineSha":str|null,"changed":[...],
#               "filteredOutCount":int,"filteredOutSample":[...],
#               "machineryExcludedCount":int,"machineryExcludedSample":[...]}
# filteredOutCount/filteredOutSample surface changed paths that diffGlobs dropped
# (see issue #7): a stale/too-narrow diffGlobs must not silently hide code changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONFIG=""; EXPECT_CONFIG_SHA=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --expect-config-sha) EXPECT_CONFIG_SHA="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$CONFIG" ]] || { echo "error: --config required" >&2; exit 2; }
[[ -n "$EXPECT_CONFIG_SHA" ]] || { echo "error: --expect-config-sha required" >&2; exit 2; }
CONFIG_JSON="$(python3 "$SCRIPT_DIR/sealed_config.py" --config "$CONFIG" --expect-sha "$EXPECT_CONFIG_SHA" --print)" || { rc=$?; exit "$rc"; }

if ! git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "error: not a git repository: $REPO_ROOT" >&2; exit 1
fi

TMPFILE="$(mktemp "${TMPDIR:-/tmp}/docaudit_changed.XXXXXX")"
trap 'rm -f "$TMPFILE"' EXIT

py() { python3 -c "$@"; }
if ! ANCHOR_PATH="$(printf '%s' "$CONFIG_JSON" | py 'import json,sys; print(json.load(sys.stdin).get("anchorPath",""))')"; then
  echo "error: failed to read anchorPath from sealed config" >&2
  exit 2
fi
if ! GLOBS_JSON="$(printf '%s' "$CONFIG_JSON" | py 'import json,sys; print(json.dumps(json.load(sys.stdin).get("diffGlobs",[])))')"; then
  echo "error: failed to read diffGlobs from sealed config" >&2
  exit 2
fi

ANCHOR_SHA=""
if [[ -n "$ANCHOR_PATH" && -f "$REPO_ROOT/$ANCHOR_PATH" ]]; then
  ANCHOR_SHA="$(py 'import json,sys; f=open(sys.argv[1]); print(json.load(f).get("sha","")); f.close()' "$REPO_ROOT/$ANCHOR_PATH")"
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

# In full mode the committed-diff line is skipped; 'changed' then holds only working-copy edits — consumers MUST treat mode=full as "scan the whole corpus", not "scan only changed".
{
  if [[ "$MODE" == "incremental" ]]; then
    git -C "$REPO_ROOT" diff --name-only "${BASE}..HEAD"
  fi
  git -C "$REPO_ROOT" diff --name-only HEAD
  git -C "$REPO_ROOT" ls-files --others --exclude-standard
} | sort -u > "$TMPFILE" || true

# Filter changed paths by diffGlobs. g2r maps globs to regex: star-star spans slashes, single star does not; diffGlobs here are dir-prefix or exact, so this is adequate.
# NOTE: this g2r is intentionally simpler than resolve-impact.py's (no zero-width '/**/' handling); do NOT reuse it for docGlobs-style patterns like docs/STARSTAR/*.md.
# Paths dropped by the filter are not discarded silently (issue #7): filteredOutCount
# is the full dropped count, filteredOutSample is capped at 5 for a readable report line.
if ! printf '%s' "$CONFIG_JSON" | py '
import importlib.util,json,sys,re
sys.path.insert(0, sys.argv[5])
spec=importlib.util.spec_from_file_location("change_set_sha", sys.argv[5]+"/change-set-sha.py")
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
config=json.load(sys.stdin)
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
def kept(p):
    return (not globs) or any(rx.match(p) for rx in globs)
machinery=sorted(set(p for p in paths if module.excluded(p, config)))
machinery_set=set(machinery)
remaining=[p for p in paths if p not in machinery_set]
changed=sorted(set(p for p in remaining if kept(p)))
dropped=sorted(set(p for p in remaining if not kept(p)))
out={"mode":sys.argv[3],"baselineSha":json.loads(sys.argv[4]),"changed":changed,
     "filteredOutCount":len(dropped),"filteredOutSample":dropped[:5],
     "machineryExcludedCount":len(machinery),"machineryExcludedSample":machinery[:5]}
print(json.dumps(out))
' "$GLOBS_JSON" "$TMPFILE" "$MODE" "$BASELINE" "$SCRIPT_DIR"; then
  echo "error: failed to compute baseline from sealed config" >&2
  exit 2
fi

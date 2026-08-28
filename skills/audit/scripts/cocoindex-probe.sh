#!/usr/bin/env bash
# cocoindex-probe.sh — Phase-0 preflight: keep the CocoIndex (`ccc`) semantic-search
# index fresh for Phase 2's impact-supplement.py (mdq-index.sh pattern: actually runs
# the index-refresh call, not just `--version` — `ccc --version` does not exist,
# confirmed real-machine). If CocoIndex is present AND already initialized, bind
# SEMANTIC_SEARCH_AVAILABLE/SEMANTIC_SEARCH_BIN so Phase 2 may supplement
# mapGapCandidates via `ccc search`. If ccc is absent / disabled / not yet
# initialized / the index refresh fails, emit semanticSearchAvailable:false and let
# the audit continue unaffected — the semantic-search candidate source is a bonus,
# never a requirement.
#
# THE SINGLE MOST IMPORTANT RULE IN THIS SCRIPT (spec §2 unconditional invariant 5):
# this probe NEVER calls `ccc init`. `ccc init` auto-appends `/.cocoindex_code/` to
# the target repo's `.gitignore` (confirmed real side effect) — a write the
# report-only audit phase must never trigger mid-run. A missing
# `.cocoindex_code/settings.yml` marker is therefore its own terminal `not-initialized` state, distinct from
# `not-installed`; initialization only ever happens inside `/docaudit:init`, behind
# explicit user approval that discloses the `.gitignore` write.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: `ccc index` can auto-initialize at the nearest parent git root; when
# `--repo-root` is a subdirectory, a parent `.gitignore` change is outside this probe's anchor.
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

read -r STATE BIN < <(python3 -c '
import json, math, sys
default = "ccc"
try:
    if not sys.argv[1]: raise ValueError()
    with open(sys.argv[1], encoding="utf-8") as f: config = json.load(f)
    if not isinstance(config, dict): raise ValueError()
    if "semanticSearch" not in config: print("not-configured", default); raise SystemExit
    seam = config["semanticSearch"]
    if not isinstance(seam, dict): raise ValueError()
    enabled = seam.get("enabled", True)
    if not isinstance(enabled, bool): raise ValueError()
    if not enabled: print("disabled-by-config", seam.get("bin", default) if isinstance(seam.get("bin", default), str) and seam.get("bin", default) else default); raise SystemExit
    bin_name = seam.get("bin", default)
    if not isinstance(bin_name, str) or not bin_name: raise ValueError()
    if "minScore" in seam:
        value = seam["minScore"]
        if not (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)): raise ValueError()
    print("enabled", bin_name)
except Exception:
    print("invalid-config", default)
' "$CONFIG")

emit() { python3 -c 'import json,sys; print(json.dumps({"semanticSearchAvailable":sys.argv[1] == "true", "semanticSearchBin":sys.argv[2], "reason":sys.argv[3]}, separators=(",", ":")))' "$@"; }

if [[ "$STATE" != "enabled" ]]; then
  emit false "$BIN" "$STATE"
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  emit false "$BIN" not-installed
  exit 0
fi

if [[ ! -f "$REPO_ROOT/.cocoindex_code/settings.yml" ]]; then
  # Terminal state — do NOT call `ccc init` here (see file header). Expected,
  # silent degrade until the user runs /docaudit:init.
  emit false "$BIN" not-initialized
  exit 0
fi

ERRF="$(mktemp "${TMPDIR:-/tmp}/cocoindex_probe_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT

# NOTE: `ccc index` takes NO path argument at all (real-machine confirmed: `ccc
# index .` errors "Got unexpected extra argument(s) (.)" — unlike codegraph/
# graphify, which both accept a trailing `.`). It always operates on the cwd, so
# the `cd "$REPO_ROOT"` below is load-bearing on its own.
GITIGNORE="$REPO_ROOT/.gitignore"
fingerprint_gitignore() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}
if [[ -e "$GITIGNORE" ]]; then
  if ! GITIGNORE_BEFORE="$(fingerprint_gitignore "$GITIGNORE" 2>/dev/null)" || [[ -z "$GITIGNORE_BEFORE" ]]; then
    echo "unable to fingerprint .gitignore before ccc index; index not run" >&2
    emit false "$BIN" index-failed
    exit 0
  fi
  GITIGNORE_EXISTED=1
else
  GITIGNORE_BEFORE=""
  GITIGNORE_EXISTED=0
fi

if ( cd "$REPO_ROOT" && "$BIN" index ) >/dev/null 2>"$ERRF"; then
  rc=0
else
  rc=$?
fi

if [[ -e "$GITIGNORE" ]]; then
  if ! GITIGNORE_AFTER="$(fingerprint_gitignore "$GITIGNORE" 2>/dev/null)" || [[ -z "$GITIGNORE_AFTER" ]]; then
    echo "unable to fingerprint .gitignore after ccc index" >&2
    emit false "$BIN" index-failed
    exit 0
  fi
  GITIGNORE_EXISTS_AFTER=1
else
  GITIGNORE_AFTER=""
  GITIGNORE_EXISTS_AFTER=0
fi
if [[ "$GITIGNORE_EXISTED" != "$GITIGNORE_EXISTS_AFTER" || "$GITIGNORE_BEFORE" != "$GITIGNORE_AFTER" ]]; then
  echo "ccc index modified .gitignore; leaving it unchanged for manual review" >&2
  emit false "$BIN" gitignore-modified
  exit 0
fi

if [[ "$rc" -eq 0 ]]; then
  emit true "$BIN" ok
  exit 0
else
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "ccc index failed (rc=$rc): $TAIL" >&2
  emit false "$BIN" index-failed
  exit 0
fi

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
# report-only audit phase must never trigger mid-run. An absent `.cocoindex_code/`
# directory is therefore its own terminal `not-initialized` state, distinct from
# `not-installed`; initialization only ever happens inside `/docaudit:init`, behind
# explicit user approval that discloses the `.gitignore` write.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# semanticSearch.enabled (default true) + semanticSearch.bin (default "ccc");
# tolerate a missing/invalid config by falling back to defaults.
ENABLED="1"; BIN="ccc"
if [[ -n "$CONFIG" ]]; then
  IFS=$'\t' read -r ENABLED BIN < <(python3 -c '
import json,sys
e=True; b="ccc"
try:
    s=(json.load(open(sys.argv[1])).get("semanticSearch") or {})
    e=bool(s.get("enabled",True)); b=str(s.get("bin","ccc") or "ccc")
except Exception:
    pass
print(("1" if e else "0")+"\t"+b)
' "$CONFIG")
fi
[[ -n "$BIN" ]] || BIN="ccc"
[[ -n "$ENABLED" ]] || ENABLED="1"
# JSON-safe copy of BIN for echoing into the JSON (BIN comes from user config).
BIN_J="$(printf '%s' "$BIN" | tr -d '"\\' | tr -d '[:cntrl:]')"

if [[ "$ENABLED" != "1" ]]; then
  printf '{"semanticSearchAvailable":false,"semanticSearchBin":"%s","reason":"disabled-by-config"}\n' "$BIN_J"
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  printf '{"semanticSearchAvailable":false,"semanticSearchBin":"%s","reason":"not-installed"}\n' "$BIN_J"
  exit 0
fi

if [[ ! -d "$REPO_ROOT/.cocoindex_code" ]]; then
  # Terminal state — do NOT call `ccc init` here (see file header). Expected,
  # silent degrade until the user runs /docaudit:init.
  printf '{"semanticSearchAvailable":false,"semanticSearchBin":"%s","reason":"not-initialized"}\n' "$BIN_J"
  exit 0
fi

ERRF="$(mktemp "${TMPDIR:-/tmp}/cocoindex_probe_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT

# NOTE: `ccc index` takes NO path argument at all (real-machine confirmed: `ccc
# index .` errors "Got unexpected extra argument(s) (.)" — unlike codegraph/
# graphify, which both accept a trailing `.`). It always operates on the cwd, so
# the `cd "$REPO_ROOT"` below is load-bearing on its own.
if ( cd "$REPO_ROOT" && "$BIN" index ) >/dev/null 2>"$ERRF"; then
  printf '{"semanticSearchAvailable":true,"semanticSearchBin":"%s","reason":"ok"}\n' "$BIN_J"
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "ccc index failed (rc=$rc): $TAIL" >&2
  printf '{"semanticSearchAvailable":false,"semanticSearchBin":"%s","reason":"index-failed","rc":%d}\n' "$BIN_J" "$rc"
  exit 0
fi

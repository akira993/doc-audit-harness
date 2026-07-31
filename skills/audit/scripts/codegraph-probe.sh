#!/usr/bin/env bash
# codegraph-probe.sh — Phase-0 preflight: keep the codegraph symbol-graph index fresh
# for doc-impact-verifier's read-only symbol-level corroboration seam (mdq-index.sh
# pattern: actually runs the index-build/refresh call, not just `--version`). If
# codegraph is present, bind SYMBOL_GRAPH_AVAILABLE/SYMBOL_GRAPH_BIN so the verifier
# may corroborate a changed file's own symbols via `codegraph impact`/`node`. If
# codegraph is absent / disabled / the index build fails, emit
# symbolGraphAvailable:false and let the audit continue unaffected — symbol-level
# corroboration is a bonus, never a requirement.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: init/sync branch (confirmed real-machine behavior, spec §5.1): a bare
# `codegraph init .` against an already-initialized `.codegraph/` is REJECTED
# ("Already initialized"). So this probe checks whether `.codegraph/` already exists
# and calls `init` only the first time; every subsequent run calls `sync` (confirmed
# idempotent: "Already up to date" when nothing changed).
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# symbolGraph.enabled (default true) + symbolGraph.bin (default "codegraph");
# tolerate a missing/invalid config by falling back to defaults.
ENABLED="1"; BIN="codegraph"
if [[ -n "$CONFIG" ]]; then
  IFS=$'\t' read -r ENABLED BIN < <(python3 -c '
import json,sys
e=True; b="codegraph"
try:
    s=(json.load(open(sys.argv[1])).get("symbolGraph") or {})
    e=bool(s.get("enabled",True)); b=str(s.get("bin","codegraph") or "codegraph")
except Exception:
    pass
print(("1" if e else "0")+"\t"+b)
' "$CONFIG")
fi
[[ -n "$BIN" ]] || BIN="codegraph"
[[ -n "$ENABLED" ]] || ENABLED="1"
# JSON-safe copy of BIN for echoing into the JSON (BIN comes from user config).
BIN_J="$(printf '%s' "$BIN" | tr -d '"\\' | tr -d '[:cntrl:]')"

if [[ "$ENABLED" != "1" ]]; then
  printf '{"symbolGraphAvailable":false,"symbolGraphBin":"%s","reason":"disabled-by-config"}\n' "$BIN_J"
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  printf '{"symbolGraphAvailable":false,"symbolGraphBin":"%s","reason":"not-installed"}\n' "$BIN_J"
  exit 0
fi

ERRF="$(mktemp "${TMPDIR:-/tmp}/codegraph_probe_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT

if [[ -d "$REPO_ROOT/.codegraph" ]]; then
  CMD=(sync .)
else
  CMD=(init .)
fi

if ( cd "$REPO_ROOT" && "$BIN" "${CMD[@]}" ) >/dev/null 2>"$ERRF"; then
  printf '{"symbolGraphAvailable":true,"symbolGraphBin":"%s","reason":"ok"}\n' "$BIN_J"
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "codegraph ${CMD[*]} failed (rc=$rc): $TAIL" >&2
  printf '{"symbolGraphAvailable":false,"symbolGraphBin":"%s","reason":"index-failed","rc":%d}\n' "$BIN_J" "$rc"
  exit 0
fi

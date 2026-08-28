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

read -r STATE BIN < <(python3 -c '
import json, sys
default = "codegraph"
try:
    if not sys.argv[1]: raise ValueError()
    with open(sys.argv[1], encoding="utf-8") as f: config = json.load(f)
    if not isinstance(config, dict): raise ValueError()
    if "symbolGraph" not in config: print("not-configured", default); raise SystemExit
    seam = config["symbolGraph"]
    if not isinstance(seam, dict): raise ValueError()
    enabled = seam.get("enabled", True)
    if not isinstance(enabled, bool): raise ValueError()
    if not enabled: print("disabled-by-config", seam.get("bin", default) if isinstance(seam.get("bin", default), str) and seam.get("bin", default) and not any(ord(c) <= 31 or ord(c) == 127 for c in seam.get("bin", default)) else default); raise SystemExit
    bin_name = seam.get("bin", default)
    if not isinstance(bin_name, str) or not bin_name or any(ord(c) <= 31 or ord(c) == 127 for c in bin_name): raise ValueError()
    print("enabled", bin_name)
except Exception:
    print("invalid-config", default)
' "$CONFIG")

emit() { python3 -c 'import json,sys; print(json.dumps({"symbolGraphAvailable":sys.argv[1] == "true", "symbolGraphBin":sys.argv[2], "reason":sys.argv[3]}, separators=(",", ":")))' "$@"; }

if [[ "$STATE" != "enabled" ]]; then
  emit false "$BIN" "$STATE"
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  emit false "$BIN" not-installed
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
  emit true "$BIN" ok
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "codegraph ${CMD[*]} failed (rc=$rc): $TAIL" >&2
  emit false "$BIN" index-failed
  exit 0
fi

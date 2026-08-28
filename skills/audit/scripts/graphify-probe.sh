#!/usr/bin/env bash
# graphify-probe.sh — Phase-0 preflight: keep the graphify code+doc graph fresh for
# Phase 2's impact-supplement.py (mdq-index.sh pattern: actually runs the graph
# refresh, not just `--version`). If graphify is present, bind
# DOC_GRAPH_AVAILABLE/DOC_GRAPH_BIN so Phase 2 may supplement mapGapCandidates via
# `graphify affected`/`graphify query`. If graphify is absent / disabled / the
# refresh fails, emit docGraphAvailable:false and let the audit continue unaffected
# — the graph-based candidate source is a bonus, never a requirement.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: `graphify update .` is confirmed LLM-free and diff-based/idempotent (no
# init/sync branch needed here, unlike codegraph) — safe to call unconditionally
# every run. CONFIRMED SIDE EFFECT: on any detected topology change it writes a
# dated backup under graphify-out/<date>/ (accumulates over repeated runs; disk-only
# concern when graphify-out/ is gitignored — this probe does not address it, spec §6).
# NOTE: graphify does NOT self-gitignore its `graphify-out/` output dir (unlike
# codegraph's `.codegraph/`), so this probe also reports whether it's ignored, via
# `git check-ignore` (NOT a direct `.gitignore` read — that would miss global
# gitignore / .git/info/exclude / pattern-wording differences, confirmed method).
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# A seam is key-gated: a missing or invalid config never falls back to enabled.
read -r STATE BIN < <(python3 -c '
import json, sys
default = "graphify"
try:
    if not sys.argv[1]: raise ValueError()
    with open(sys.argv[1], encoding="utf-8") as f: config = json.load(f)
    if not isinstance(config, dict): raise ValueError()
    if "docGraph" not in config: print("not-configured", default); raise SystemExit
    seam = config["docGraph"]
    if not isinstance(seam, dict): raise ValueError()
    enabled = seam.get("enabled", True)
    if not isinstance(enabled, bool): raise ValueError()
    if not enabled: print("disabled-by-config", seam.get("bin", default) if isinstance(seam.get("bin", default), str) and seam.get("bin", default) else default); raise SystemExit
    bin_name = seam.get("bin", default)
    if not isinstance(bin_name, str) or not bin_name: raise ValueError()
    print("enabled", bin_name)
except Exception:
    print("invalid-config", default)
' "$CONFIG")

emit() { python3 -c 'import json,sys; print(json.dumps({"docGraphAvailable":sys.argv[1] == "true", "docGraphBin":sys.argv[2], "reason":sys.argv[3], "gitignoreOk":sys.argv[4] == "true"}, separators=(",", ":")))' "$@"; }

if [[ "$STATE" != "enabled" ]]; then
  emit false "$BIN" "$STATE" false
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  emit false "$BIN" not-installed false
  exit 0
fi

ERRF="$(mktemp "${TMPDIR:-/tmp}/graphify_probe_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT

# NOTE: do not negate this `if` with `!` — `$?` after a negated pipeline reflects
# the NEGATED status, not the underlying command's real exit code (mdq-index.sh's
# if/else shape is used here specifically to keep `rc` faithful).
if ( cd "$REPO_ROOT" && "$BIN" update . ) >/dev/null 2>"$ERRF"; then
  # gitignoreOk: exit 0 (ignored) -> true; exit 1 (not ignored) -> false; anything
  # else (e.g. not a git repo) -> false, safe default (Phase 5 WARNs on false).
  if ( cd "$REPO_ROOT" && git check-ignore -q graphify-out ) 2>/dev/null; then
    GITIGNORE_OK="true"
  else
    GITIGNORE_OK="false"
  fi
  emit true "$BIN" ok "$GITIGNORE_OK"
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "graphify update . failed (rc=$rc): $TAIL" >&2
  emit false "$BIN" update-failed false
  exit 0
fi

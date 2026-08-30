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

# A seam is key-gated: a missing or invalid config never falls back to enabled.
if ! DECISION="$(printf '%s' "$CONFIG_JSON" | python3 -c '
import json, sys
default = "graphify"
try:
    config = json.load(sys.stdin)
    if not isinstance(config, dict): raise ValueError()
    if "docGraph" not in config: print("not-configured", default); raise SystemExit
    seam = config["docGraph"]
    if not isinstance(seam, dict): raise ValueError()
    enabled = seam.get("enabled", True)
    if not isinstance(enabled, bool): raise ValueError()
    bin_name = seam.get("bin", default)
    valid = isinstance(bin_name, str) and bool(bin_name) and bin_name == bin_name.strip() and not any(ord(c) <= 31 or ord(c) == 127 for c in bin_name)
    if valid:
        try: bin_name.encode("utf-8")
        except UnicodeEncodeError: valid = False
    if not enabled: sys.stdout.buffer.write(("disabled-by-config " + (bin_name if valid else default) + "\n").encode("utf-8")); raise SystemExit
    if not valid: raise ValueError()
    sys.stdout.buffer.write(("enabled " + bin_name + "\n").encode("utf-8"))
except Exception:
    sys.stdout.buffer.write(("invalid-config " + default + "\n").encode("utf-8"))
')"; then
  echo "error: failed to parse sealed config for graphify probe" >&2
  exit 2
fi
read -r STATE BIN <<< "$DECISION"

emit() { python3 -c 'import json,sys
line=json.dumps({"docGraphAvailable":sys.argv[1] == "true", "docGraphBin":sys.argv[2], "reason":sys.argv[3], "gitignoreOk":sys.argv[4] == "true"}, separators=(",", ":"))+"\n"
line.encode("utf-8"); sys.stdout.buffer.write(line.encode("utf-8"))' "$@"; }

if [[ "$STATE" != "enabled" ]]; then
  emit false "$BIN" "$STATE" false
  exit 0
fi

if ! command -v -- "$BIN" >/dev/null 2>&1; then
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

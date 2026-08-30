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

if ! DECISION="$(printf '%s' "$CONFIG_JSON" | python3 -c '
import json, math, sys
default = "ccc"
try:
    config = json.load(sys.stdin)
    if not isinstance(config, dict): raise ValueError()
    if "semanticSearch" not in config: print("not-configured", default); raise SystemExit
    seam = config["semanticSearch"]
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
    if "minScore" in seam:
        value = seam["minScore"]
        if not (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)): raise ValueError()
    sys.stdout.buffer.write(("enabled " + bin_name + "\n").encode("utf-8"))
except Exception:
    sys.stdout.buffer.write(("invalid-config " + default + "\n").encode("utf-8"))
')"; then
  echo "error: failed to parse sealed config for cocoindex probe" >&2
  exit 2
fi
read -r STATE BIN <<< "$DECISION"

emit() { python3 -c 'import json,sys
line=json.dumps({"semanticSearchAvailable":sys.argv[1] == "true", "semanticSearchBin":sys.argv[2], "reason":sys.argv[3]}, separators=(",", ":"))+"\n"
line.encode("utf-8"); sys.stdout.buffer.write(line.encode("utf-8"))' "$@"; }

if [[ "$STATE" != "enabled" ]]; then
  emit false "$BIN" "$STATE"
  exit 0
fi

if ! command -v -- "$BIN" >/dev/null 2>&1; then
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

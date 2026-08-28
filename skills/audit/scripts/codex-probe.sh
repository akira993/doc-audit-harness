#!/usr/bin/env bash
# codex-probe.sh — Phase-0 preflight: detect the `codex` CLI (plain `codex exec`,
# no plugin dependency) for docaudit's Phase-4 adversarial Codex review seam
# (ax-pattern: conditional-force). If codex is present, bind
# CODEX_REVIEW_AVAILABLE/CODEX_REVIEW_BIN so Phase 4 may run a Codex review. If
# codex is absent / disabled, emit codexReviewAvailable:false and let the audit
# continue unaffected — codex being unavailable is never a FAIL reason (though a
# *completed* codex review's critical/high findings can be, per spec §5.4).
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: no network use — `codex --version` and `codex exec --help` inspect only the
# local binary and do not start a model invocation.
set -uo pipefail

CONFIG=""; CONFIG_SET=0; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG_SET=1; CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

DECISION="$(python3 -c '
import base64,json,sys
state="enabled"; binary="codex"
try:
    if sys.argv[1] == "1":
        if not sys.argv[2]: raise ValueError
        config=json.load(open(sys.argv[2]))
        if not isinstance(config,dict): raise ValueError
        if "codexReview" in config:
            seam=config["codexReview"]
            if not isinstance(seam,dict): raise ValueError
            if "enabled" in seam and not isinstance(seam["enabled"],bool): raise ValueError
            if seam.get("enabled") is False: state="disabled"
            elif "bin" in seam:
                value=seam["bin"]
                if (not isinstance(value,str) or not value or value != value.strip()
                    or any(ord(c) <= 31 or ord(c) == 127 for c in value)): raise ValueError
                value.encode("utf-8")
                binary=value
except Exception:
    state="invalid"; binary="codex"
line=state+"\t"+base64.b64encode(binary.encode("utf-8")).decode("ascii")+"\n"
sys.stdout.buffer.write(line.encode("utf-8"))
' "$CONFIG_SET" "$CONFIG")"
IFS=$'\t' read -r CONFIG_STATE BIN_B64 <<< "$DECISION"
BIN="$(python3 -c 'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.argv[1]))' "$BIN_B64")"

CALLER_HOME=""; CALLER_SOURCE="unknown"; CALLER_AUTH="unknown"; CALLER_NULL=1
if [[ -n "${CODEX_HOME:-}" ]]; then
  CALLER_HOME="$CODEX_HOME"; CALLER_SOURCE="env"; CALLER_NULL=0
elif [[ -n "${HOME:-}" ]]; then
  CALLER_HOME="$HOME/.codex"; CALLER_SOURCE="default"; CALLER_NULL=0
fi
if [[ "$CALLER_NULL" == "0" ]]; then
  if [[ -f "$CALLER_HOME/auth.json" ]]; then CALLER_AUTH="present"; else CALLER_AUTH="absent"; fi
fi

emit_json() {
  python3 -c 'import json,sys
version=None if sys.argv[3]=="__NULL__" else sys.argv[3]
commands=[] if sys.argv[4]=="0" else [sys.argv[2]+" --version",sys.argv[2]+" exec --help"]
home=None if sys.argv[9]=="1" else sys.argv[6]
sys.stdout.buffer.write((json.dumps({"codexReviewAvailable":sys.argv[1]=="1","codexReviewBin":sys.argv[2],"codexReviewVersion":version,"probeCommands":commands,"reason":sys.argv[5],"callerCodexHome":home,"callerCodexHomeSource":sys.argv[7],"callerAuthFile":sys.argv[8]}, ensure_ascii=False)+"\n").encode("utf-8"))' \
    "$1" "$2" "$3" "$4" "$5" "$CALLER_HOME" "$CALLER_SOURCE" "$CALLER_AUTH" "$CALLER_NULL"
}

if [[ "$CONFIG_STATE" == "invalid" ]]; then
  emit_json 0 codex __NULL__ 0 invalid-config
  exit 0
fi
if [[ "$CONFIG_STATE" == "disabled" ]]; then
  emit_json 0 codex __NULL__ 0 disabled-by-config
  exit 0
fi

if ! command -v -- "$BIN" >/dev/null 2>&1; then
  emit_json 0 "$BIN" __NULL__ 0 not-installed
  exit 0
fi

# `codex --version` reports the local binary version only — no network call.
VERSION="$("$BIN" --version 2>/dev/null | tr -d '\r' | head -n1)"
if ! "$BIN" exec --help >/dev/null 2>&1; then
  emit_json 0 "$BIN" "$VERSION" 1 probe-exec-failed
  exit 0
fi
emit_json 1 "$BIN" "$VERSION" 1 ok
exit 0

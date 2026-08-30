#!/usr/bin/env bash
# ax-probe.sh — Phase-0 preflight: detect the `ax` CLI (structured web/API extraction)
# for doc-impact-verifier's key-gated, read-only external-URL corroboration seam.
# Only a config containing webExtract may enable the tool. If ax is present, bind
# AX_AVAILABLE/AX_BIN so the verifier may corroborate doc claims against upstream
# URLs. If ax is absent / disabled / not configured, emit axAvailable:false and let
# the audit continue unaffected. Output: single-line JSON.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0.
# NOTE: no network use — `ax --version` prints the local binary's own version and
# does not fetch a URL.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG=""; CONFIG_SET=0; EXPECT_CONFIG_SHA=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      CONFIG_SET=1
      if [[ $# -ge 2 ]]; then CONFIG="$2"; shift 2; else CONFIG=""; shift; fi
      ;;
    --expect-config-sha) EXPECT_CONFIG_SHA="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

[[ -n "$CONFIG" ]] || { echo "error: --config required" >&2; exit 2; }
[[ -n "$EXPECT_CONFIG_SHA" ]] || { echo "error: --expect-config-sha required" >&2; exit 2; }
CONFIG_JSON="$(python3 "$SCRIPT_DIR/sealed_config.py" --config "$CONFIG" --expect-sha "$EXPECT_CONFIG_SHA" --print)" || { rc=$?; exit "$rc"; }

if ! DECISION="$(printf '%s' "$CONFIG_JSON" | python3 -c '
import base64,json,sys
state="invalid"; binary="ax"
try:
    config=json.load(sys.stdin)
    if not isinstance(config,dict): raise ValueError
    if "webExtract" not in config:
        state="not-configured"
    else:
        seam=config["webExtract"]
        if not isinstance(seam,dict): raise ValueError
        if "enabled" in seam and not isinstance(seam["enabled"],bool): raise ValueError
        if seam.get("enabled") is False: state="disabled"
        else:
            state="enabled"
            if "bin" in seam:
                value=seam["bin"]
                if (not isinstance(value,str) or not value or value != value.strip()
                    or any(ord(c) <= 31 or ord(c) == 127 for c in value)): raise ValueError
                value.encode("utf-8")
                binary=value
except Exception:
    state="invalid"; binary="ax"
line=state+"\t"+base64.b64encode(binary.encode("utf-8")).decode("ascii")+"\n"
sys.stdout.buffer.write(line.encode("utf-8"))
')"; then
  echo "error: failed to parse sealed config for ax probe" >&2
  exit 2
fi
IFS=$'\t' read -r CONFIG_STATE BIN_B64 <<< "$DECISION"
BIN="$(python3 -c 'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.argv[1]))' "$BIN_B64")"

if [[ "$CONFIG_STATE" == "invalid" ]]; then
  printf '{"axAvailable":false,"axBin":"ax","axVersion":null,"reason":"invalid-config"}\n'
  exit 0
fi
if [[ "$CONFIG_STATE" == "not-configured" ]]; then
  printf '{"axAvailable":false,"axBin":"ax","axVersion":null,"reason":"not-configured"}\n'
  exit 0
fi
if [[ "$CONFIG_STATE" == "disabled" ]]; then
  printf '{"axAvailable":false,"axBin":"ax","axVersion":null,"reason":"disabled-by-config"}\n'
  exit 0
fi

if ! command -v -- "$BIN" >/dev/null 2>&1; then
  python3 -c 'import json,sys; sys.stdout.buffer.write((json.dumps({"axAvailable":False,"axBin":sys.argv[1],"axVersion":None,"reason":"not-installed"})+"\n").encode("utf-8"))' "$BIN"
  exit 0
fi

# `ax --version` reports the local binary version only — no network call.
VERSION="$("$BIN" --version 2>/dev/null | tr -d '\r' | head -n1)"
python3 -c 'import json,sys; sys.stdout.buffer.write((json.dumps({"axAvailable":True,"axBin":sys.argv[1],"axVersion":sys.argv[2],"reason":"ok"})+"\n").encode("utf-8"))' "$BIN" "$VERSION"
exit 0

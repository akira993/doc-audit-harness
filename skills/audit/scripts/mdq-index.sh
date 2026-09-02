#!/usr/bin/env bash
# mdq-index.sh — Phase-0 preflight: build the mdq index of the doc corpus (spec §4.1).
# Conditional-force: if mdq is present, index the doc corpus so Phase 3 can read
# token-optimized chunks. If mdq is absent / disabled / indexing fails, emit
# mdqAvailable:false and let the audit degrade to grep. Output: single-line JSON.
#
# IMPORTANT: mdq's own `index` default --root is a short list (docs, users-guide — and
# a repo's own mdq.toml can override it) that MISSES README.md, skills/**, agents/**. So
# we index from the repo ROOT by default (--root .), overridable via config
# indexing.roots[]. This honors "index all docs". Note it is not literally every file:
# mdq unconditionally skips dependency and build trees (.git .mdq .cq .toolsearch
# node_modules __pycache__ dist build .next .cache venv and .venv*) at every depth below
# the root it was given, so a `.` root indexes the repo minus those.
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0
# (except on bad CLI args → exit 2, like compute-baseline.sh). If a `mdq watch` is
# running, a concurrent index may hit a SQLite lock → rc!=0 → we degrade to grep.
# Targets bash 3.2 (macOS): no mapfile; guard "${arr[@]}" under set -u with a count.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG=""; CONFIG_SET=0; EXPECT_CONFIG_SHA=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG_SET=1; CONFIG="$2"; shift 2;;
    --expect-config-sha) EXPECT_CONFIG_SHA="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

[[ -n "$CONFIG" ]] || { echo "error: --config required" >&2; exit 2; }
[[ -n "$EXPECT_CONFIG_SHA" ]] || { echo "error: --expect-config-sha required" >&2; exit 2; }
CONFIG_JSON="$(python3 "$SCRIPT_DIR/sealed_config.py" --config "$CONFIG" --expect-sha "$EXPECT_CONFIG_SHA" --print)" || { rc=$?; exit "$rc"; }

# Validate config before probing. Keep option presence separate from its value.
if ! DECISION="$(printf '%s' "$CONFIG_JSON" | python3 -c '
import base64,json,sys
state="enabled"; binary="mdq"
try:
    config=json.load(sys.stdin)
    if not isinstance(config,dict): raise ValueError
    if "indexing" in config:
        seam=config["indexing"]
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
    state="invalid"; binary="mdq"
line=state+"\t"+base64.b64encode(binary.encode("utf-8")).decode("ascii")+"\n"
sys.stdout.buffer.write(line.encode("utf-8"))
')"; then
  echo "error: failed to parse sealed config for mdq index" >&2
  exit 2
fi
IFS=$'\t' read -r CONFIG_STATE BIN_B64 <<< "$DECISION"
BIN="$(python3 -c 'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.argv[1]))' "$BIN_B64")"

if [[ "$CONFIG_STATE" == "invalid" ]]; then
  printf '{"mdqAvailable":false,"reason":"invalid-config","bin":"mdq"}\n'
  exit 0
fi
if [[ "$CONFIG_STATE" == "disabled" ]]; then
  printf '{"mdqAvailable":false,"reason":"disabled-by-config"}\n'
  exit 0
fi

if ! command -v -- "$BIN" >/dev/null 2>&1; then
  python3 -c 'import json,sys; sys.stdout.buffer.write((json.dumps({"mdqAvailable":False,"reason":"not-installed","bin":sys.argv[1]})+"\n").encode("utf-8"))' "$BIN"
  exit 0
fi

# indexing.roots[] override; default to the repo root (--root .).
ROOTS=()
if [[ "$CONFIG_SET" == "1" ]]; then
  if ! ROOTS_TEXT="$(printf '%s' "$CONFIG_JSON" | python3 -c '
import json,sys
r=[]
try:
    v=((json.load(sys.stdin).get("indexing") or {}).get("roots"))
    if isinstance(v,list): r=[str(x) for x in v if str(x).strip()]
except Exception:
    pass
print("\n".join(r))
')"; then
    echo "error: failed to read indexing roots from sealed config" >&2
    exit 2
  fi
  while IFS= read -r r; do [[ -n "$r" ]] && ROOTS+=("$r"); done <<< "$ROOTS_TEXT"
fi
ROOT_ARGS=()
if [[ ${#ROOTS[@]} -gt 0 ]]; then
  for r in "${ROOTS[@]}"; do ROOT_ARGS+=(--root "$r"); done
else
  ROOT_ARGS=(--root .)
fi

# Index the corpus. No --db: mdq resolves its own default DB under .mdq/ at the repo
# root (index-<lang>-<strategy>.sqlite; the bare index.sqlite is a legacy layout that
# no supported mdq resolves to on its own) — the health
# probe and the Phase-3 verifiers also omit --db, so all three see the same file. Doc
# bodies never enter the model context (only this JSON summary does). Incremental:
# mdq skips files whose content hash is unchanged.
ERRF="$(mktemp "${TMPDIR:-/tmp}/mdq_index_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT
if ( cd "$REPO_ROOT" && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "$BIN" index "${ROOT_ARGS[@]}" ) >/dev/null 2>"$ERRF"; then
  python3 -c 'import json,sys; sys.stdout.buffer.write((json.dumps({"mdqAvailable":True,"reason":"indexed","bin":sys.argv[1],"dbDir":".mdq"})+"\n").encode("utf-8"))' "$BIN"
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "mdq index failed (rc=$rc): $TAIL" >&2
  python3 -c 'import json,sys; sys.stdout.buffer.write((json.dumps({"mdqAvailable":False,"reason":"index-failed","rc":int(sys.argv[2]),"bin":sys.argv[1]})+"\n").encode("utf-8"))' "$BIN" "$rc"
  exit 0
fi

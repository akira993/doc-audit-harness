#!/usr/bin/env bash
# mdq-index.sh — Phase-0 preflight: build the mdq index of the doc corpus (spec §4.1).
# Conditional-force: if mdq is present, index the doc corpus so Phase 3 can read
# token-optimized chunks. If mdq is absent / disabled / indexing fails, emit
# mdqAvailable:false and let the audit degrade to grep. Output: single-line JSON.
#
# IMPORTANT: mdq's own `index` default --root is a fixed dir list (docs, knowledge, …)
# that MISSES README.md, skills/**, agents/**. So we index the WHOLE repo by default
# (--root .), overridable via config indexing.roots[]. This honors "index all docs".
#
# NOTE: no `set -e` — failures are handled explicitly; we ALWAYS emit JSON + exit 0
# (except on bad CLI args → exit 2, like compute-baseline.sh). If a `mdq watch` is
# running, a concurrent index may hit a SQLite lock → rc!=0 → we degrade to grep.
# Targets bash 3.2 (macOS): no mapfile; guard "${arr[@]}" under set -u with a count.
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

# indexing.enabled (default true) + indexing.bin (default "mdq"); tolerate a
# missing/invalid config by falling back to defaults.
ENABLED="1"; BIN="mdq"
if [[ -n "$CONFIG" ]]; then
  IFS=$'\t' read -r ENABLED BIN < <(python3 -c '
import json,sys
e=True; b="mdq"
try:
    i=(json.load(open(sys.argv[1])).get("indexing") or {})
    e=bool(i.get("enabled",True)); b=str(i.get("bin","mdq") or "mdq")
except Exception:
    pass
print(("1" if e else "0")+"\t"+b)
' "$CONFIG")
fi
[[ -n "$BIN" ]] || BIN="mdq"
[[ -n "$ENABLED" ]] || ENABLED="1"
# JSON-safe copy of BIN for echoing into the JSON (BIN comes from user config).
BIN_J="$(printf '%s' "$BIN" | tr -d '"\\' | tr -d '[:cntrl:]')"

if [[ "$ENABLED" != "1" ]]; then
  printf '{"mdqAvailable":false,"reason":"disabled-by-config"}\n'
  exit 0
fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  printf '{"mdqAvailable":false,"reason":"not-installed","bin":"%s"}\n' "$BIN_J"
  exit 0
fi

# indexing.roots[] override; default to the whole repo (--root .).
ROOTS=()
if [[ -n "$CONFIG" ]]; then
  while IFS= read -r r; do [[ -n "$r" ]] && ROOTS+=("$r"); done < <(python3 -c '
import json,sys
r=[]
try:
    v=((json.load(open(sys.argv[1])).get("indexing") or {}).get("roots"))
    if isinstance(v,list): r=[str(x) for x in v if str(x).strip()]
except Exception:
    pass
print("\n".join(r))
' "$CONFIG")
fi
ROOT_ARGS=()
if [[ ${#ROOTS[@]} -gt 0 ]]; then
  for r in "${ROOTS[@]}"; do ROOT_ARGS+=(--root "$r"); done
else
  ROOT_ARGS=(--root .)
fi

# Index the corpus. No --db: mdq resolves its own default DB under .mdq/ at the repo
# root (new mdq: index-<lang>-<strategy>.sqlite, old mdq: index.sqlite) — the health
# probe and the Phase-3 verifiers also omit --db, so all three see the same file. Doc
# bodies never enter the model context (only this JSON summary does). Incremental:
# mdq skips files whose content hash is unchanged.
ERRF="$(mktemp "${TMPDIR:-/tmp}/mdq_index_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT
if ( cd "$REPO_ROOT" && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 "$BIN" index "${ROOT_ARGS[@]}" ) >/dev/null 2>"$ERRF"; then
  printf '{"mdqAvailable":true,"reason":"indexed","bin":"%s","dbDir":".mdq"}\n' "$BIN_J"
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "mdq index failed (rc=$rc): $TAIL" >&2
  printf '{"mdqAvailable":false,"reason":"index-failed","rc":%d,"bin":"%s"}\n' "$rc" "$BIN_J"
  exit 0
fi

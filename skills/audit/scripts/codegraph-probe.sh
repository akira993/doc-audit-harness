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
# NOTE: codegraph initialization is determined by the presence of `codegraph.db`.
# `init` idempotency has changed between versions (1.5.0 accepts it; older versions
# rejected it), so the probe does not depend on it. Symlinks and non-regular files
# may be followed or overwritten by codegraph, so the probe does not touch them.
set -uo pipefail

CONFIG=""; REPO_ROOT="$(pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2;;
    --repo-root) REPO_ROOT="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

{ IFS= read -r -d '' STATE; IFS= read -r -d '' BIN; IFS= read -r -d '' DIRNAME; IFS= read -r -d '' DIRNAME_ESC; } < <(python3 -c '
import json, os, re, sys
default = "codegraph"
trim_chars = "\t\n\v\f\r \u00a0\u1680" + "".join(chr(c) for c in range(0x2000, 0x200b)) + "\u2028\u2029\u202f\u205f\u3000\ufeff"
raw_dir = os.environb.get(b"CODEGRAPH_DIR", b"").decode("utf-8", errors="replace")
dirname = re.sub("^[" + re.escape(trim_chars) + "]+|[" + re.escape(trim_chars) + "]+$", "", raw_dir)
if not dirname or dirname == "." or ".." in dirname or "/" in dirname or "\\" in dirname or os.path.isabs(dirname):
    dirname = ".codegraph"
def output(state, bin_name, dir_name=dirname):
    fields = (state, bin_name, dir_name, ascii(dir_name))
    sys.stdout.buffer.write(b"".join(value.encode("utf-8") + b"\0" for value in fields))
try:
    if not sys.argv[1]: raise ValueError()
    with open(sys.argv[1], encoding="utf-8") as f: config = json.load(f)
    if not isinstance(config, dict): raise ValueError()
    if "symbolGraph" not in config: output("not-configured", default, ".codegraph"); raise SystemExit
    seam = config["symbolGraph"]
    if not isinstance(seam, dict): raise ValueError()
    enabled = seam.get("enabled", True)
    if not isinstance(enabled, bool): raise ValueError()
    bin_name = seam.get("bin", default)
    valid = isinstance(bin_name, str) and bool(bin_name) and bin_name == bin_name.strip() and not any(ord(c) <= 31 or ord(c) == 127 for c in bin_name)
    if valid:
        try: bin_name.encode("utf-8")
        except UnicodeEncodeError: valid = False
    if not enabled: output("disabled-by-config", bin_name if valid else default, ".codegraph"); raise SystemExit
    if not valid: raise ValueError()
    output("enabled", bin_name)
except Exception:
    output("invalid-config", default, ".codegraph")
' "$CONFIG")

emit() { python3 -c 'import json,sys
line=json.dumps({"symbolGraphAvailable":sys.argv[1] == "true", "symbolGraphBin":sys.argv[2], "reason":sys.argv[3]}, separators=(",", ":"))+"\n"
line.encode("utf-8"); sys.stdout.buffer.write(line.encode("utf-8"))' "$@"; }

if [[ "$STATE" != "enabled" ]]; then
  emit false "$BIN" "$STATE"
  exit 0
fi

if ! command -v -- "$BIN" >/dev/null 2>&1; then
  emit false "$BIN" not-installed
  exit 0
fi

ERRF="$(mktemp "${TMPDIR:-/tmp}/codegraph_probe_err.XXXXXX")"
trap 'rm -f "$ERRF"' EXIT

DIR="$REPO_ROOT/$DIRNAME"
DB="$DIR/codegraph.db"

if [[ -L "$DIR" ]]; then
  echo "codegraph dir $DIRNAME_ESC is a symlink; not touching it" >&2
  emit false "$BIN" index-failed
  exit 0
elif [[ -e "$DIR" && ! -d "$DIR" ]]; then
  echo "codegraph dir $DIRNAME_ESC exists but is not a directory" >&2
  emit false "$BIN" index-failed
  exit 0
elif [[ ! -e "$DIR" ]]; then
  CMD=(init .)
elif [[ -L "$DB" ]]; then
  echo "codegraph.db is a symlink; not touching it" >&2
  emit false "$BIN" index-failed
  exit 0
elif [[ ! -e "$DB" ]]; then
  CMD=(init .)
elif [[ -f "$DB" ]]; then
  CMD=(sync .)
else
  echo "codegraph.db exists but is not a regular file" >&2
  emit false "$BIN" index-failed
  exit 0
fi

if ( cd "$REPO_ROOT" && CODEGRAPH_DIR="$DIRNAME" "$BIN" "${CMD[@]}" </dev/null ) >/dev/null 2>"$ERRF"; then
  emit true "$BIN" ok
  exit 0
else
  rc=$?
  TAIL="$(tail -n 3 "$ERRF" 2>/dev/null | tr '\n' ' ' | tr -d '"\\' | tr -d '[:cntrl:]')"
  echo "codegraph ${CMD[*]} failed (rc=$rc): $TAIL" >&2
  emit false "$BIN" index-failed
  exit 0
fi

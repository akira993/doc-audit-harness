#!/usr/bin/env python3
# mdq-health.py — Phase-0 health probe (spec §4.1). Read-only: given an mdq binary
# (and optionally an explicit --db), report whether mdq is actually firing. Emits a single-line JSON object and ALWAYS
# exits 0 (a probe failure must never break the audit) — main() wraps the probe in a
# blanket try/except so any unexpected error degrades to status "probe-error".
#
#   {"files": F, "chunks": C, "searchSmoke": bool, "healthy": bool, "status": S,
#    "stale": bool}
#   status in {ok, empty-index, search-broken, probe-error}
#   healthy == (files > 0 and chunks > 0 and searchSmoke)
#   stale   == observation only (v0.18.0): mdq warned that the index is behind the
#              working tree. It NEVER feeds healthy or status — the new indexer can
#              report a permanent stale, so gating on it would stop every audit.
import argparse, json, os, re, subprocess


def run(bin_, *args):
    """Run `<bin> <args...>`; return (rc, stdout, stderr). rc=127 if it can't run."""
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run([bin_, *args], capture_output=True, text=True, env=env)
        return p.returncode, p.stdout, p.stderr
    except Exception:
        return 127, "", ""


def _has_stale_warning(text):
    """True if any stderr line is mdq's `{"warning": "stale", ...}` freshness notice.

    mdq mixes JSON warnings (freshness.py) with plain-text ones
    (`[mdq:search] fusion disabled (...)`) on the same stream, and a JSON line need
    not decode to a dict — so unparseable and non-dict lines are skipped rather than
    matched by substring. Never raises: a parse problem must degrade to False, not
    reach main()'s blanket except, which would flip status to probe-error and turn
    an observation-only field into something that stops the audit.
    """
    try:
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except Exception:
                continue
            if isinstance(parsed, dict) and parsed.get("warning") == "stale":
                return True
    except Exception:
        return False
    return False


def _probe(out, bin_, db):
    """Fill `out` in place. May raise; main() catches and keeps status=probe-error."""
    # `--db` is an explicit override only (tests / special setups). When omitted, mdq
    # resolves its own default DB relative to the CWD — `.mdq/index-<lang>-<strategy>.sqlite`
    # (`_resolve_db` is the same implementation in mdq 78edaabc and c559e767 — the
    # installs differ only in line endings; the bare
    # `.mdq/index.sqlite` is a legacy layout reached only via an explicit path) — so the
    # probe inspects the SAME DB the Phase-0 indexer wrote. Run it from the repo root.
    db_args = ["--db", db] if db else []
    # 1) stats — files/chunks. Unparseable or nonzero rc => probe-error (status unchanged).
    rc, so, _ = run(bin_, "stats", *db_args)
    st = None
    if rc == 0 and so.strip():
        try:
            st = json.loads(so.strip().splitlines()[-1])
        except Exception:
            st = None
    if st is None:
        return
    # A non-numeric files/chunks raises ValueError here -> caught by main() -> probe-error.
    out["files"] = int(st.get("files", 0) or 0)
    out["chunks"] = int(st.get("chunks", 0) or 0)

    # 2) empty index — no search needed.
    if out["files"] <= 0 or out["chunks"] <= 0:
        out["status"] = "empty-index"
        return

    # 3) self-derived search smoke: take real terms from the index itself, search one.
    rc, lo, _ = run(bin_, "list", *db_args, "--limit", "5")
    cand = []
    for line in lo.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        text = " ".join(str(d.get(k, "")) for k in ("heading_path", "path"))
        cand += re.findall(r"[^\W_]{3,}", text)  # Unicode-aware (incl. CJK), excludes underscore
    if not cand:  # fallback: basename stems of listed paths
        for line in lo.splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            stem = re.sub(r"\.[A-Za-z0-9]+$", "", os.path.basename(str(d.get("path", ""))))
            cand += re.findall(r"[^\W_]{2,}", stem)
    seen, terms = set(), []
    for w in cand:
        if w.lower() not in seen:
            seen.add(w.lower())
            terms.append(w)
        if len(terms) >= 8:
            break

    smoke, stale = False, False
    for w in terms:
        rc, so, se = run(bin_, "search", *db_args, "--q", w, "--top-k", "1")
        # Aggregate before the break: the loop stops at the first hit, so a stale
        # warning from an earlier term would be lost if only the last call were read.
        stale = stale or _has_stale_warning(se)
        if rc == 0 and any(ln.strip() for ln in so.splitlines()):
            smoke = True
            break

    out["stale"] = stale
    out["searchSmoke"] = smoke
    out["healthy"] = bool(smoke)  # files>0 and chunks>0 already hold here
    out["status"] = "ok" if smoke else "search-broken"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default="mdq")
    ap.add_argument("--db", default=None,
                    help="explicit DB override; omit to let mdq resolve its own default DB")
    a = ap.parse_args()

    out = {"files": 0, "chunks": 0, "searchSmoke": False, "healthy": False,
           "status": "probe-error", "stale": False}
    try:
        _probe(out, a.bin, a.db)
    except Exception:
        # Any unexpected error -> degrade to probe-error but still emit valid JSON + exit 0.
        out["healthy"] = False
        out["status"] = "probe-error"
    print(json.dumps(out))


if __name__ == "__main__":
    main()

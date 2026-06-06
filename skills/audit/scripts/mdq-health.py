#!/usr/bin/env python3
# mdq-health.py — Phase-0 health probe (spec §4.1). Read-only: given an mdq index db,
# report whether mdq is actually firing. Emits a single-line JSON object and ALWAYS
# exits 0 (a probe failure must never break the audit) — main() wraps the probe in a
# blanket try/except so any unexpected error degrades to status "probe-error".
#
#   {"files": F, "chunks": C, "searchSmoke": bool, "healthy": bool, "status": S}
#   status in {ok, empty-index, search-broken, probe-error}
#   healthy == (files > 0 and chunks > 0 and searchSmoke)
import argparse, json, os, re, subprocess


def run(bin_, *args):
    """Run `<bin> <args...>`; return (rc, stdout). rc=127 if the binary can't run."""
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run([bin_, *args], capture_output=True, text=True, env=env)
        return p.returncode, p.stdout
    except Exception:
        return 127, ""


def _probe(out, bin_, db):
    """Fill `out` in place. May raise; main() catches and keeps status=probe-error."""
    # 1) stats — files/chunks. Unparseable or nonzero rc => probe-error (status unchanged).
    rc, so = run(bin_, "stats", "--db", db)
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
    rc, lo = run(bin_, "list", "--db", db, "--limit", "5")
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

    smoke = False
    for w in terms:
        rc, so = run(bin_, "search", "--db", db, "--q", w, "--top-k", "1")
        if rc == 0 and any(ln.strip() for ln in so.splitlines()):
            smoke = True
            break

    out["searchSmoke"] = smoke
    out["healthy"] = bool(smoke)  # files>0 and chunks>0 already hold here
    out["status"] = "ok" if smoke else "search-broken"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default="mdq")
    ap.add_argument("--db", default=".mdq/index.sqlite")
    a = ap.parse_args()

    out = {"files": 0, "chunks": 0, "searchSmoke": False, "healthy": False, "status": "probe-error"}
    try:
        _probe(out, a.bin, a.db)
    except Exception:
        # Any unexpected error -> degrade to probe-error but still emit valid JSON + exit 0.
        out["healthy"] = False
        out["status"] = "probe-error"
    print(json.dumps(out))


if __name__ == "__main__":
    main()

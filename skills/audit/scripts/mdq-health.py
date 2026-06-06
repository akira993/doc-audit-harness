#!/usr/bin/env python3
# mdq-health.py — Phase-0 health probe (spec §4.1). Read-only: given an mdq index db,
# report whether mdq is actually firing. Emits a single-line JSON object and ALWAYS
# exits 0 (a probe failure must never break the audit).
#
#   {"files": F, "chunks": C, "searchSmoke": bool, "healthy": bool, "status": S}
#   status in {ok, empty-index, search-broken, probe-error}
#   healthy == (files > 0 and chunks > 0 and searchSmoke)
import argparse, json, os, re, subprocess, sys


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default="mdq")
    ap.add_argument("--db", default=".mdq/index.sqlite")
    a = ap.parse_args()

    out = {"files": 0, "chunks": 0, "searchSmoke": False, "healthy": False, "status": "probe-error"}

    # 1) stats — files/chunks. Unparseable or nonzero rc => probe-error.
    rc, so = run(a.bin, "stats", "--db", a.db)
    st = None
    if rc == 0 and so.strip():
        try:
            st = json.loads(so.strip().splitlines()[-1])
        except Exception:
            st = None
    if st is None:
        print(json.dumps(out))
        return
    out["files"] = int(st.get("files", 0) or 0)
    out["chunks"] = int(st.get("chunks", 0) or 0)

    # 2) empty index — no search needed.
    if out["files"] <= 0 or out["chunks"] <= 0:
        out["status"] = "empty-index"
        print(json.dumps(out))
        return

    # 3) self-derived search smoke: take real terms from the index itself, search one.
    rc, lo = run(a.bin, "list", "--db", a.db, "--limit", "5")
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
        cand += re.findall(r"[A-Za-z0-9]{4,}", text)
    if not cand:  # fallback: basename stems of listed paths
        for line in lo.splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            stem = re.sub(r"\.[A-Za-z0-9]+$", "", os.path.basename(str(d.get("path", ""))))
            cand += re.findall(r"[A-Za-z0-9]{3,}", stem)
    seen, terms = set(), []
    for w in cand:
        if w.lower() not in seen:
            seen.add(w.lower())
            terms.append(w)
        if len(terms) >= 8:
            break

    smoke = False
    for w in terms:
        rc, so = run(a.bin, "search", "--db", a.db, "--q", w, "--top-k", "1")
        if rc == 0 and any(ln.strip() for ln in so.splitlines()):
            smoke = True
            break

    out["searchSmoke"] = smoke
    out["healthy"] = bool(smoke)  # files>0 and chunks>0 already hold here
    out["status"] = "ok" if smoke else "search-broken"
    print(json.dumps(out))


if __name__ == "__main__":
    main()

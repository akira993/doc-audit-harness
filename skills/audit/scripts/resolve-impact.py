#!/usr/bin/env python3
"""resolve-impact.py — map a change set to impacted docs (spec §5.2, UNION rule).

Reads:
  --config PATH     .claude/doc-audit.json
  --changed PATH    newline-separated changed repo-relative paths, or '-' for stdin
  --repo-root PATH  repo root used to verify impacted doc paths exist (default: cwd)

Writes JSON to stdout:
  {"impacted":[{"path","provenance"}], "mapGapCandidates":[path],
   "ssotRecheck":[{"name","reason"}], "truncated":bool, "counts":{...}}

Rules:
  - UNION: impacted = mapped ∪ heuristic. Heuristic only ADDS docs, never removes.
  - mapped: a changed path matches an impactMap entry `changed` (exact or glob);
    that entry's `impacts` are added (provenance=mapped).
  - heuristic: for each changed file, its basename + stem (>= minIdentifierLength,
    not in excludeBasenames) is searched as a substring in each docGlobs file;
    hits are added (provenance=heuristic) and listed in mapGapCandidates.
  - provenance "both" when a doc is reached by mapped AND heuristic.
  - ssotRecheck: an ssotSource is flagged if a changed path matches an entry in
    docsThatCite (':line' stripped) or a path token inside liveSource.
  - Only impacts paths existing on disk under repo-root are emitted; missing
    mapped paths are warned to stderr.
  - maxImpactedDocs cap: keep mapped first, then heuristic; extras dropped,
    truncated=true, dropped count logged to stderr.
  - counts.mapped / counts.heuristicOnly reflect docs in the emitted (post-cap)
    impacted list; counts.candidatesBeforeCap is the pre-cap total of candidates.
"""
import argparse, json, os, re, sys

DEFAULT_MIN_IDENT = 5
DEFAULT_EXCLUDE_BASENAMES = {
    "readme.md", "index.md", "changelog.md", "license", "license.md",
    "__init__.py", "makefile", "main.md", "test.md",
    # generic Claude Code convention filenames: a SKILL.md exists in every skill
    # dir, so its basename/stem token would heuristic-match every doc that merely
    # mentions skills. Precise impact stays covered by impactMap (.claude/skills/**).
    "skill", "skill.md",
}


def glob_to_regex(pattern):
    """`**` -> any incl '/', `*` -> any except '/', `?` -> single except '/'."""
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                if i + 2 < n and pattern[i + 2] == "/":
                    out.append("(.*/)?"); i += 3
                else:
                    out.append(".*"); i += 2
            else:
                out.append("[^/]*"); i += 1
        elif c == "?":
            out.append("[^/]"); i += 1
        else:
            out.append(re.escape(c)); i += 1
    return re.compile("^" + "".join(out) + "$")


def matches(path, pattern):
    if pattern == path:
        return True
    return glob_to_regex(pattern).match(path) is not None


def list_doc_files(repo_root, doc_globs):
    skip = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
    docs = []
    regexes = [glob_to_regex(g) for g in doc_globs]
    # followlinks=False (default): symlinked doc trees are not traversed
    for dirpath, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in skip]  # prune .git/node_modules/etc
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo_root)
            if any(rx.match(rel) for rx in regexes):
                docs.append(rel)
    return docs


def tokens_for(changed_path, min_len, exclude):
    base = os.path.basename(changed_path)
    stem = base.rsplit(".", 1)[0] if "." in base else base
    cands = {base, stem}
    return {t for t in cands if len(t) >= min_len and t.lower() not in exclude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--changed", required=True)
    ap.add_argument("--repo-root", default=os.getcwd())
    args = ap.parse_args()

    try:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(2)

    if args.changed == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(args.changed, encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            print(f"error: {e}", file=sys.stderr); sys.exit(2)
    changed = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    repo = args.repo_root
    heur = cfg.get("heuristics", {})
    min_len = int(heur.get("minIdentifierLength", DEFAULT_MIN_IDENT))
    exclude = {b.lower() for b in heur.get("excludeBasenames", [])} | DEFAULT_EXCLUDE_BASENAMES
    max_docs = int(cfg.get("maxImpactedDocs", 200))

    prov = {}  # path -> set of provenances

    def exists(rel):
        return os.path.isfile(os.path.join(repo, rel))

    # --- mapped ---
    for entry in cfg.get("impactMap", []):
        pat = entry.get("changed", "")
        if not any(matches(c, pat) for c in changed):
            continue
        for doc in entry.get("impacts", []):
            if exists(doc):
                prov.setdefault(doc, set()).add("mapped")
            else:
                print(f"warn: mapped impact path missing on disk: {doc}", file=sys.stderr)

    # --- heuristic ---
    doc_files = list_doc_files(repo, cfg.get("docGlobs", ["docs/**/*.md", "*.md"]))
    all_tokens = set()
    for c in changed:
        all_tokens |= tokens_for(c, min_len, exclude)
    if all_tokens:
        token_list = sorted(all_tokens, key=len, reverse=True)
        for doc in doc_files:
            try:
                with open(os.path.join(repo, doc), encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue
            if any(tok in content for tok in token_list):
                prov.setdefault(doc, set()).add("heuristic")

    # --- ssotRecheck ---
    # Spec §5.2: trigger on CHANGED files, not impacted docs.
    # reason="docsThatCite" if any changed path ∈ docsThatCite (strip ':line').
    # reason="liveSource"   if any changed path ∈ file paths extracted from liveSource.
    ssot = []
    for s in cfg.get("ssotSources", []):
        cite_paths = {c.split(":", 1)[0] for c in s.get("docsThatCite", [])}
        live = s.get("liveSource", "")
        # extract path-like tokens from liveSource; server commands like "occ status" yield none (correctly inert)
        live_paths = set(re.findall(r"[\w./-]+\.[\w]+", live))
        reason = None
        if any(c in cite_paths for c in changed):
            reason = "docsThatCite"
        elif any(c in live_paths for c in changed):
            reason = "liveSource"
        if reason:
            ssot.append({"name": s.get("name", "?"), "reason": reason})

    # --- assemble with provenance + cap (mapped first) ---
    def provenance(p):
        s = prov[p]
        return "both" if {"mapped", "heuristic"} <= s else next(iter(s))

    mapped_paths = sorted(p for p in prov if "mapped" in prov[p])
    heur_only = sorted(p for p in prov if "mapped" not in prov[p])
    ordered = mapped_paths + heur_only
    candidates_before_cap = len(mapped_paths) + len(heur_only)
    truncated = len(ordered) > max_docs
    if truncated:
        dropped = len(ordered) - max_docs
        print(f"warn: {dropped} impacted docs dropped by maxImpactedDocs={max_docs}", file=sys.stderr)
        ordered = ordered[:max_docs]

    impacted = [{"path": p, "provenance": provenance(p)} for p in ordered]
    map_gap = [p for p in ordered if provenance(p) == "heuristic"]

    mapped_n = sum(1 for d in impacted if d["provenance"] in ("mapped", "both"))
    heur_n = sum(1 for d in impacted if d["provenance"] == "heuristic")

    json.dump({
        "impacted": impacted,
        "mapGapCandidates": map_gap,
        "ssotRecheck": ssot,
        "truncated": truncated,
        "counts": {"changed": len(changed), "impacted": len(impacted),
                   "mapped": mapped_n, "heuristicOnly": heur_n,
                   "candidatesBeforeCap": candidates_before_cap},
    }, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""resolve-impact.py — map a change set to impacted docs (spec §5.2, UNION rule).

Reads:
  --config PATH     .claude/doc-audit.json
  --changed PATH    newline-separated changed repo-relative paths, or '-' for stdin
  --repo-root PATH  repo root used to verify impacted doc paths exist (default: cwd)

Writes JSON to stdout:
  {"impacted":[{"path","provenance"}], "mapGapCandidates":[path],
   "ssotRecheck":[{"name","reason"}], "warnings":[str], "truncated":bool, "counts":{...}}

Rules:
  - priority: `mapped`/`full`/`self` ≥ `regression` ≥ `heuristic` ≥ `graphify` ≥ `semantic`.
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
import argparse, hashlib, json, os, re, sys

from docaudit_cache import content_sha, parse_history_document
from docaudit_paths import (corpus_settings, is_excluded_doc,
                            list_doc_files as safe_list_doc_files, matches_glob,
                            validate_repo_path)
from sealed_config import SealedConfigMismatch, load_sealed_config

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
        # prune nested checkouts: a subdir containing a .git entry (dir for a
        # nested clone/submodule, file for a linked worktree's `gitdir: ...`
        # pointer) is a separate checkout and must not be walked into. The
        # walk root itself is exempt: this only filters dirs we'd descend
        # into next, never the current dirpath.
        dirs[:] = [d for d in dirs if not os.path.exists(os.path.join(dirpath, d, ".git"))]
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, repo_root)
            if any(rx.match(rel) for rx in regexes):
                docs.append(rel)
    return docs


def report_pattern(config):
    value = config.get("reportPath")
    globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
    if not isinstance(value, str) or not value.endswith(".md"):
        return None
    sample = value.replace("<YYYY-MM-DD>", "2000-01-01").replace("[_NN]", "_01")
    if not any(matches_glob(sample, item) for item in globs if isinstance(item, str)):
        return None
    directory, name = os.path.split(value)
    marker = "<YYYY-MM-DD>"
    suffix_marker = "[_NN]"
    if marker not in name:
        return None
    prefix = name.split(marker, 1)[0]
    if not prefix:
        return None
    suffix_at = None
    if suffix_marker not in value:
        suffix_at = len(value) - len(name) + name.find(marker) + len(marker)
    out = []
    i = 0
    while i < len(value):
        if value.startswith(marker, i):
            out.append("[0-9]{4}-[0-9]{2}-[0-9]{2}")
            i += len(marker)
            if suffix_at == i:
                out.append("(_[0-9]{2,})?")
        elif value.startswith(suffix_marker, i):
            out.append("(_[0-9]{2,})?")
            i += len(suffix_marker)
        else:
            out.append(re.escape(value[i]))
            i += 1
    return "^" + "".join(out) + "$"


def tokens_for(changed_path, min_len, exclude):
    base = os.path.basename(changed_path)
    stem = base.rsplit(".", 1)[0] if "." in base else base
    cands = {base, stem}
    return {t for t in cands if len(t) >= min_len and t.lower() not in exclude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--expect-config-sha", required=True)
    ap.add_argument("--changed", required=True)
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--mode", choices=["incremental", "full"], default="incremental")
    ap.add_argument("--history")
    args = ap.parse_args()

    try:
        _config_raw, cfg = load_sealed_config(args.config, args.expect_config_sha)
    except SealedConfigMismatch as e:
        print(str(e), file=sys.stderr); sys.exit(7)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as e:
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
    if not isinstance(heur, dict):
        heur = {}
    min_len = int(heur.get("minIdentifierLength", DEFAULT_MIN_IDENT))
    exclude = {b.lower() for b in heur.get("excludeBasenames", [])} | DEFAULT_EXCLUDE_BASENAMES
    max_docs = int(cfg.get("maxImpactedDocs", 200))
    if max_docs < 1:
        print("error: maxImpactedDocs must be at least 1", file=sys.stderr); sys.exit(2)

    prov = {}  # path -> set of provenances
    warnings = []
    saturation = heur.get("saturationWarnRatio", 0.5)
    if isinstance(saturation, bool):
        warnings.append(f"heuristics.saturationWarnRatio invalid ({saturation!r}); using default 0.5")
        saturation = 0.5
    elif saturation == 0:
        saturation = None
    elif not isinstance(saturation, (int, float)) or not 0 <= saturation <= 1:
        warnings.append(f"heuristics.saturationWarnRatio invalid ({saturation!r}); using default 0.5")
        saturation = 0.5
    exclude_doc_tokens = heur.get("excludeDocPathTokens", False)
    if not isinstance(exclude_doc_tokens, bool):
        warnings.append(f"heuristics.excludeDocPathTokens invalid ({exclude_doc_tokens!r}); using default false")
        exclude_doc_tokens = False
    regression = cfg.get("regressionRecheck", {})
    if not isinstance(regression, dict):
        warnings.append("regressionRecheck invalid; using default disabled")
        regression = {}
    regression_enabled = regression.get("enabled", False)
    if not isinstance(regression_enabled, bool):
        warnings.append("regressionRecheck.enabled invalid; using default false")
        regression_enabled = False
    doc_globs = cfg.get("docGlobs", ["docs/**/*.md", "*.md"])
    try:
        exclude_globs, respect_gitignore = corpus_settings(cfg)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr); sys.exit(2)
    report_rx = None if cfg.get("auditReportsInCorpus") is True else report_pattern(cfg)
    corpus_stats = {}
    doc_files = [doc for doc in safe_list_doc_files(
        repo, doc_globs, warnings, exclude_globs=exclude_globs,
        respect_gitignore=respect_gitignore, stats=corpus_stats)
                 if not (report_rx and re.fullmatch(report_rx, doc))]

    def exists(rel):
        try:
            validate_repo_path(repo, rel)
            return True
        except ValueError:
            return False

    if args.mode == "full":
        for doc in doc_files:
            prov.setdefault(doc, set()).add("full")
    else:
        # --- mapped ---
        for entry in cfg.get("impactMap", []):
            pat = entry.get("changed", "")
            if not any(matches(c, pat) for c in changed):
                continue
            for doc in entry.get("impacts", []):
                if exists(doc) and not is_excluded_doc(
                        repo, doc, exclude_globs, respect_gitignore):
                    prov.setdefault(doc, set()).add("mapped")
                elif exists(doc):
                    warnings.append(f"mapped impact path dropped as excluded: {doc}")
                else:
                    warnings.append(f"mapped impact path dropped as missing/unsafe: {doc}")
                    print(f"warn: mapped impact path missing/unsafe: {doc}", file=sys.stderr)

    # --- heuristic and changed corpus documents themselves ---
    if args.mode != "full":
        for path in changed:
            if path in doc_files:
                prov.setdefault(path, set()).add("self")
    all_tokens = set()
    for c in changed:
        if exclude_doc_tokens and any(matches(c, glob) for glob in doc_globs if isinstance(glob, str)):
            continue
        all_tokens |= tokens_for(c, min_len, exclude)
    if args.mode != "full" and all_tokens:
        token_list = sorted(all_tokens, key=len, reverse=True)
        for doc in doc_files:
            try:
                with open(os.path.join(repo, doc), encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue
            if any(tok in content for tok in token_list):
                prov.setdefault(doc, set()).add("heuristic")

    history_sha = None
    if args.mode != "full" and regression_enabled and args.history:
        if os.path.isfile(args.history):
            try:
                with open(args.history, "rb") as handle:
                    history_raw = handle.read()
                history_sha = "sha256:" + hashlib.sha256(history_raw).hexdigest()
                entries, _phase4_runs, history_warnings = parse_history_document(
                    json.loads(history_raw.decode("utf-8")))
                warnings.extend(history_warnings)
                last = {}
                for entry in entries:
                    last[entry["path"]] = entry
                for path, entry in last.items():
                    if (entry["verdict"] == "FAIL" and path in doc_files and exists(path)
                            and content_sha(repo, path) == entry["contentSha"]):
                        prov.setdefault(path, set()).add("regression")
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                warnings.append(f"regression recheck skipped: history unreadable ({exc})")

    # --- ssotRecheck ---
    # Spec §5.2: trigger on CHANGED files, not impacted docs.
    # reason="docsThatCite" if any changed path ∈ docsThatCite (strip ':line').
    # reason="liveSource"   if any changed path ∈ file paths extracted from liveSource.
    ssot = []
    for s in cfg.get("ssotSources", []):
        cite_paths = {c.split(":", 1)[0] for c in s.get("docsThatCite", [])}
        live = s.get("liveSource", "")
        if re.match(r"^https?://", live):
            # URL liveSource is unsupported: never fetched or verified — warn loudly
            # instead of silently skipping, and don't pretend its tokens are repo paths.
            warnings.append(
                f"ssotSource '{s.get('name', '?')}': liveSource is a URL — not supported; "
                "the value is not fetched or verified. Track it manually.")
            live_paths = set()
        else:
            # extract path-like tokens from liveSource; server commands like "occ status" yield none (correctly inert)
            live_paths = set(re.findall(r"[\w./-]+\.[\w]+", live))
        reason = None
        if any(c in cite_paths for c in changed):
            reason = "docsThatCite"
        elif any(c in live_paths for c in changed):
            reason = "liveSource"
        if reason:
            ssot.append({"name": s.get("name", "?"), "reason": reason})

    # --- assemble with provenance + cap ---
    def provenance(p):
        s = prov[p]
        if "full" in s:
            return "full"
        if "self" in s:
            return "self"
        if "mapped" in s:
            return "both" if "heuristic" in s else "mapped"
        if "heuristic" in s:
            return "heuristic"
        if "regression" in s:
            return "regression"
        return "heuristic"

    tier_one = sorted(p for p in prov if {"mapped", "full", "self"} & prov[p])
    regression_only = sorted(p for p in prov if "regression" in prov[p]
                             and not ({"mapped", "full", "self"} & prov[p]))
    heur_only = sorted(p for p in prov if "heuristic" in prov[p]
                       and not ({"mapped", "full", "self", "regression"} & prov[p]))
    saturation_heuristic = sorted(p for p in prov if "heuristic" in prov[p]
                                  and not ({"mapped", "full", "regression"} & prov[p]))
    ordered = tier_one + regression_only + heur_only
    candidates_before_cap = len(ordered)
    known = {path for path, sources in prov.items() if {"mapped", "self"} & sources}
    if args.mode != "full" and len(known) > max_docs:
        mapped_raw = sum(1 for sources in prov.values() if "mapped" in sources)
        self_raw = sum(1 for sources in prov.values() if "self" in sources)
        print(f"maxImpactedDocs={max_docs} is below the known-coupling set ({len(known)} docs: mapped={mapped_raw}, self={self_raw}); raise maxImpactedDocs or run --full", file=sys.stderr)
        sys.exit(2)
    truncated = args.mode != "full" and len(ordered) > max_docs
    if truncated:
        dropped = len(ordered) - max_docs
        cap_warning = f"{dropped} impacted docs dropped by maxImpactedDocs={max_docs}"
        print(f"warn: {cap_warning}", file=sys.stderr)
        warnings.append(cap_warning)
        ordered = ordered[:max_docs]

    impacted = [{"path": p, "provenance": provenance(p)} for p in ordered]
    map_gap = [p for p in ordered if provenance(p) == "heuristic"]

    mapped_n = sum(1 for d in impacted if d["provenance"] in ("mapped", "both"))
    heur_n = sum(1 for d in impacted if d["provenance"] == "heuristic")
    regression_n = sum(1 for d in impacted if d["provenance"] == "regression")
    self_n = sum(1 for d in impacted if "self" in prov[d["path"]])
    doc_corpus = len(doc_files)
    heuristic_saturation = round(len(saturation_heuristic) / doc_corpus, 3) if doc_corpus else 0.0
    raw_saturation = len(saturation_heuristic) / doc_corpus if doc_corpus else 0.0
    if saturation is not None and saturation_heuristic and raw_saturation >= saturation:
        pct = round(raw_saturation * 100, 1)
        warnings.append(
            f"heuristic saturation: {len(saturation_heuristic)}/{doc_corpus} docs ({pct}%) reached only by the token heuristic — impactMap is not carrying the selection; promote couplings from mapGapCandidates to impactMap")

    result = {
        "impacted": impacted,
        "mapGapCandidates": map_gap,
        "ssotRecheck": ssot,
        "warnings": list(dict.fromkeys(warnings)),
        "truncated": truncated,
        "counts": {"changed": len(changed), "impacted": len(impacted),
                   "mapped": mapped_n, "self": self_n,
                   "heuristicOnly": heur_n, "regression": regression_n,
                   "docCorpus": doc_corpus, "heuristicSaturation": heuristic_saturation,
                   "candidatesBeforeCap": candidates_before_cap},
        "corpusFilter": {"excludeDocGlobs": exclude_globs,
                         "respectGitignore": respect_gitignore,
                         "gitignoreApplied": corpus_stats.get("gitignoreApplied", False),
                         "excludedByGlobs": corpus_stats.get("excludedByGlobs", 0),
                         "excludedByGitignore": corpus_stats.get("excludedByGitignore", 0)},
    }
    if args.mode != "full" and regression_enabled and args.history:
        result["historySha"] = history_sha
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

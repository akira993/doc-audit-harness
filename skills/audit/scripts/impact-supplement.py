#!/usr/bin/env python3
"""impact-supplement.py — supplement resolve-impact.py's output with graphify
(graph-adjacency) and CocoIndex (semantic-search) candidates (spec §5.7).

resolve-impact.py's own `mapped`/`regression`/`heuristic` result (already cap-applied) is
UNCONDITIONALLY kept as-is — this script never displaces an existing `impacted`
entry. New candidates from graphify and/or CocoIndex are added ONLY into the
residual slots left under `maxImpactedDocs`, strictly in priority order
`mapped` >= `regression` >= `heuristic` >= `graphify` >= `semantic` (Issue #8 anti-regression).

Reads:
  --impact-json PATH       resolve-impact.py's output (rewritten in place)
  --changed PATH           newline-separated changed repo-relative paths, or '-' for stdin
  --change-summary TEXT    a change summary string, or a path to a file containing one
  --repo-root PATH         repo root (for running graphify/ccc with cwd there)
  --max-impacted-docs N    cap (must match resolve-impact.py's own cap; default 200)
  --doc-globs GLOB[,GLOB]  comma-separated docGlobs patterns (default docs/**/*.md,*.md)
  --config PATH            optional doc-audit config for report-corpus exclusion
  --graphify-bin BIN       optional; omit to skip the graphify source entirely
  --cocoindex-bin BIN      optional; omit to skip the CocoIndex source entirely
  --min-score FLOAT        CocoIndex score threshold (default 0.4)

Both sources are independent and optional. Any individual call failure (non-zero
exit, unparseable/invalid output, uniqueness error, all-below-threshold) degrades
that source to zero candidates and the script continues — it always exits 0. When
neither --graphify-bin nor --cocoindex-bin is passed, this is a pure no-op
passthrough (impact.json left byte-identical).
"""
import argparse, json, os, re, subprocess, sys

from docaudit_paths import matches_glob, validate_repo_path
from sealed_config import SealedConfigMismatch, load_sealed_config

DEFAULT_DOC_GLOBS = ["docs/**/*.md", "*.md"]
DEFAULT_MIN_SCORE = 0.4
DEFAULT_MAX_IMPACTED_DOCS = 200

# graphify's confirmed fixed-format TEXT lines (neither `affected` nor `query
# --budget` supports --json — spec §5.7):
#   `graphify affected "<file>"`:  - <label> [<relation>] <filePath>:L<line>
#   `graphify query "<text>" --budget N`: NODE <label> [src=<path> loc=L<n> community=...]
AFFECTED_LINE_RE = re.compile(r"^- .+? \[.+?\] (?P<filePath>.+):L\d+$")
QUERY_NODE_RE = re.compile(r"^NODE .+? \[src=(?P<src>\S+) loc=L\d+ community=.*\]$")


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


def is_doc(path, doc_regexes):
    return any(rx.match(path) is not None or path == g for rx, g in doc_regexes)


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


def run(cmd, cwd, timeout=60):
    """Run a subprocess; return (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception:
        return 1, "", ""


def graphify_candidates(bin_path, repo_root, changed, change_summary, doc_regexes):
    """Collect provenance="graphify" candidate doc paths. Never raises; degrades
    to an empty set on any per-call failure (uniqueness error, non-zero exit,
    unparseable output) and keeps going with the remaining calls."""
    candidates = set()
    for f in changed:
        rc, out, _ = run([bin_path, "affected", f], cwd=repo_root)
        if rc != 0:
            continue
        for line in out.splitlines():
            m = AFFECTED_LINE_RE.match(line.strip())
            if not m:
                continue
            path = m.group("filePath").strip()
            if is_doc(path, doc_regexes):
                candidates.add(path)

    summary = (change_summary or "")[:2000]
    if summary.strip():
        rc, out, _ = run([bin_path, "query", summary, "--budget", "800"], cwd=repo_root)
        if rc == 0:
            for line in out.splitlines():
                m = QUERY_NODE_RE.match(line.strip())
                if not m:
                    continue
                path = m.group("src").strip()
                if is_doc(path, doc_regexes):
                    candidates.add(path)
    return candidates


def cocoindex_candidates(bin_path, repo_root, change_summary, min_score, doc_regexes):
    """Collect provenance="semantic" candidate doc paths whose score clears
    min_score (mandatory — `ccc search` has no built-in relevance cutoff, spec
    §5.7/§6). Never raises; degrades to an empty set on any failure."""
    candidates = set()
    summary = (change_summary or "").strip()
    if not summary:
        return candidates
    rc, out, _ = run([bin_path, "search", summary, "--json", "--limit", "10"], cwd=repo_root)
    if rc != 0:
        return candidates
    try:
        parsed = json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return candidates
    # Real-machine confirmed shape (cocoindex-code 0.2.39): a wrapped object
    # {"type":"search","success":bool,"results":[...],"total_returned":int,
    # "offset":int,"message":...} — NOT a bare array. Accept a bare array too
    # (defensive, in case a different version reverts to it).
    if isinstance(parsed, dict):
        results = parsed.get("results")
    else:
        results = parsed
    if not isinstance(results, list):
        return candidates
    for r in results:
        if not isinstance(r, dict):
            continue
        try:
            score = float(r.get("score", -1))
        except (TypeError, ValueError):
            continue
        if score < min_score:
            continue
        path = r.get("file_path")
        if isinstance(path, str) and is_doc(path, doc_regexes):
            candidates.add(path)
    return candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impact-json", required=True)
    ap.add_argument("--changed", required=True)
    ap.add_argument("--change-summary", default="")
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--max-impacted-docs", type=int, default=DEFAULT_MAX_IMPACTED_DOCS)
    ap.add_argument("--doc-globs", default=",".join(DEFAULT_DOC_GLOBS))
    ap.add_argument("--config")
    ap.add_argument("--expect-config-sha")
    ap.add_argument("--graphify-bin", default=None)
    ap.add_argument("--cocoindex-bin", default=None)
    ap.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    args = ap.parse_args()

    config = None
    if args.config and args.expect_config_sha is None:
        print("impact-supplement: --config requires --expect-config-sha", file=sys.stderr)
        sys.exit(2)
    if (args.expect_config_sha is not None
            and not re.fullmatch(r"sha256:[0-9a-f]{64}", args.expect_config_sha)):
        print("impact-supplement: --expect-config-sha must be sha256:<64 lowercase hex>",
              file=sys.stderr)
        sys.exit(2)
    if args.config:
        try:
            _config_raw, config = load_sealed_config(args.config, args.expect_config_sha)
        except SealedConfigMismatch as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(7)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            print(f"warn: impact-supplement: cannot read/parse config ({exc}); no-op",
                  file=sys.stderr)
            sys.exit(0)

    # Always exit 0. Any failure reading/parsing impact.json is a no-op: leave
    # the file untouched (spec §5.7/§7 fallback rule).
    try:
        with open(args.impact_json, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"warn: impact-supplement: cannot read/parse impact.json ({e}); no-op", file=sys.stderr)
        sys.exit(0)

    if not isinstance(data, dict) or "impacted" not in data:
        print("warn: impact-supplement: impact.json missing 'impacted'; no-op", file=sys.stderr)
        sys.exit(0)

    if not args.graphify_bin and not args.cocoindex_bin:
        # Pure passthrough — leave impact.json byte-identical.
        sys.exit(0)

    report_rx = None
    if config is not None:
        if config.get("auditReportsInCorpus") is not True:
            report_rx = report_pattern(config)

    if args.changed == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(args.changed, encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            raw = ""
    changed = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    change_summary = args.change_summary
    if change_summary and os.path.isfile(change_summary):
        try:
            with open(change_summary, encoding="utf-8") as f:
                change_summary = f.read()
        except OSError:
            pass

    doc_globs = [g.strip() for g in args.doc_globs.split(",") if g.strip()] or DEFAULT_DOC_GLOBS
    doc_regexes = [(glob_to_regex(g), g) for g in doc_globs]

    impacted = data.get("impacted") or []
    existing_paths = {e.get("path") for e in impacted if isinstance(e, dict)}
    map_gap = list(data.get("mapGapCandidates") or [])
    warnings = list(data.get("warnings") or [])
    counts = dict(data.get("counts") or {})

    graphify_before_cap = 0
    semantic_before_cap = 0
    graphify_admitted = []
    semantic_admitted = []
    truncated_sources = []

    def safe_candidates(values, source):
        admitted = []
        for value in sorted(values):
            if report_rx and re.fullmatch(report_rx, value):
                continue
            try:
                admitted.append(validate_repo_path(args.repo_root, value))
            except ValueError as exc:
                warnings.append(f"{source} candidate dropped as unsafe: {value} ({exc})")
        return admitted

    if args.graphify_bin:
        raw_candidates = graphify_candidates(
            args.graphify_bin, args.repo_root, changed, change_summary, doc_regexes)
        new_candidates = [p for p in safe_candidates(raw_candidates, "graphify")
                          if p not in existing_paths]
        graphify_before_cap = len(new_candidates)
        residual = max(0, args.max_impacted_docs - len(impacted))
        admitted = new_candidates[:residual]
        if len(new_candidates) > len(admitted):
            truncated_sources.append(("graphify", len(new_candidates) - len(admitted)))
        for p in admitted:
            impacted.append({"path": p, "provenance": "graphify"})
            existing_paths.add(p)
            map_gap.append(p)
        graphify_admitted = admitted

    if args.cocoindex_bin:
        raw_candidates = cocoindex_candidates(
            args.cocoindex_bin, args.repo_root, change_summary, args.min_score, doc_regexes)
        new_candidates = [p for p in safe_candidates(raw_candidates, "semantic")
                          if p not in existing_paths]
        semantic_before_cap = len(new_candidates)
        residual = max(0, args.max_impacted_docs - len(impacted))
        admitted = new_candidates[:residual]
        if len(new_candidates) > len(admitted):
            truncated_sources.append(("semantic", len(new_candidates) - len(admitted)))
        for p in admitted:
            impacted.append({"path": p, "provenance": "semantic"})
            existing_paths.add(p)
            map_gap.append(p)
        semantic_admitted = admitted

    data["impacted"] = impacted
    data["mapGapCandidates"] = map_gap
    counts["candidatesBeforeCap"] = (
        int(counts.get("candidatesBeforeCap", 0)) + graphify_before_cap + semantic_before_cap
    )
    counts["graphifyOnly"] = len(graphify_admitted)
    counts["semanticOnly"] = len(semantic_admitted)
    counts["impacted"] = len(impacted)
    data["counts"] = counts

    if truncated_sources:
        data["truncated"] = True
        for name, n in truncated_sources:
            warnings.append(
                f"{n} {name} candidate(s) dropped by maxImpactedDocs={args.max_impacted_docs}"
                " (residual-slots-only cap; mapped/heuristic entries untouched)"
            )
        print(
            f"warn: impact-supplement: {sum(n for _, n in truncated_sources)} candidate(s) "
            f"dropped by maxImpactedDocs={args.max_impacted_docs}",
            file=sys.stderr,
        )
    data["warnings"] = warnings

    with open(args.impact_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    sys.exit(0)


if __name__ == "__main__":
    main()

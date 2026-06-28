#!/usr/bin/env python3
"""generic-layers.py — portable, config-driven doc checks (docaudit Plan 2 fallback).

Used by the audit SKILL when a repo has no project-specific docAuditCommands.
Intentionally minimal (weaker than a bespoke /check-docs); the rich version is the
project's own tooling.

Layers:
  format    — relative markdown links must resolve on disk (broken => FAIL); if
              config.frontMatterFields is set, each .md must have YAML front matter
              containing those fields (missing => WARN). Link syntax inside code
              (inline `...` spans and ``` / ~~~ fenced blocks) is literal text, not a
              link, and is ignored. (image links and percent-encoded targets are checked
              as-is; names with spaces or %20 may report as broken).
  existence — backtick path-like tokens that look repo-relative must resolve on disk
              (non-resolving => WARN). Conservative, to limit noise: a trailing
              ':line'/':symbol' locator resolves against the base file, and
              ellipsis/brace/glob shorthand (`...`, `{a,b}`, `*`) is ignored.
  semantic  — orphan: a .md linked from no index file and no other doc (=> WARN).

Reads:  --config, --repo-root, --layer {format,existence,semantic,all},
        --paths PATH|-  (optional; restrict to these docs; default = all docGlobs docs)
Writes JSON: {"findings":[{layer,severity,path,line,message}], "counts":{docs,findings,fail,warn}}
"""
import argparse, json, os, re, sys

# NOTE: small copies of glob helpers, intentionally not shared with resolve-impact.py
# to avoid destabilizing verified Plan 1 code (future: extract _docaudit_common.py).
def glob_to_regex(pattern):
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


def list_doc_files(repo_root, doc_globs):
    skip = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
    regexes = [glob_to_regex(g) for g in doc_globs]
    docs = []
    for dp, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in skip]  # prune .git/node_modules/etc
        for fn in files:
            rel = os.path.relpath(os.path.join(dp, fn), repo_root)
            if any(rx.match(rel) for rx in regexes):
                docs.append(rel)
    return sorted(docs)


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
def parse_front_matter(text):
    m = _FM_RE.match(text)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z0-9_-]+)\s*:", line)
        if mm:
            fields[mm.group(1)] = True
    return fields


def _blank_keep_newlines(s):
    # Replace every non-newline char with a space, preserving length and newline
    # positions so downstream line numbers (text.count("\n", 0, m.start())) stay exact.
    return "".join("\n" if c == "\n" else " " for c in s)


# A line that, after up to 3 spaces of indent, opens a fenced code block (CommonMark:
# 3+ backticks or 3+ tildes). group(3) is the info string after the fence.
_FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
# An inline code span on a single line: a backtick run, content, the same-length run.
# Single-line (no re.DOTALL) so a stray backtick cannot swallow links on later lines.
_INLINE_CODE_RE = re.compile(r"(`+)[^\n]+?\1")


def _mask_fenced(text):
    # Blank fenced code blocks in place (length + newlines preserved). Tracks the open
    # fence char/length so only a matching closer (same char, >= length, line by itself)
    # ends the block; an unterminated fence masks to end of file (CommonMark behaviour).
    lines = text.split("\n")
    out, fence = [], None
    for line in lines:
        if fence is None:
            m = _FENCE_OPEN_RE.match(line)
            # A backtick fence's info string may not contain a backtick (CommonMark);
            # if it does, this is not actually a fence opener.
            if m and not (m.group(2)[0] == "`" and "`" in m.group(3)):
                fence = (m.group(2)[0], len(m.group(2)))
                out.append(_blank_keep_newlines(line))
            else:
                out.append(line)
        else:
            fch, flen = fence
            out.append(_blank_keep_newlines(line))
            if re.match(r"^ {0,3}%s{%d,}\s*$" % (re.escape(fch), flen), line):
                fence = None
    return "\n".join(out)


def _mask_code(text):
    # Markdown link syntax inside code (inline spans / fenced blocks) is literal text,
    # not a link. Blank code regions before link extraction so quoted link examples do
    # not trip the broken-link check, while keeping length + newline offsets intact so
    # reported line numbers stay exact. Fences first, then inline spans on what remains.
    masked = _mask_fenced(text)
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), masked)


_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
def extract_links(text):
    masked = _mask_code(text)
    out = []
    for m in _LINK_RE.finditer(masked):
        target = m.group(1).strip()
        target = re.sub(r"""\s+["'].*$""", "", target)  # strip optional Markdown link title
        out.append((target, masked.count("\n", 0, m.start()) + 1))
    return out


_TOKEN_RE = re.compile(r"`([^`\n]+)`")
def extract_path_tokens(text):
    out = []
    for m in _TOKEN_RE.finditer(text):
        out.append((m.group(1).strip(), text.count("\n", 0, m.start()) + 1))
    return out


def looks_like_repo_path(tok, repo_root):
    # conservative: must contain '/', no whitespace/shell chars, and start with an
    # existing top-level directory of the repo (so prose/commands are not flagged).
    if "/" not in tok or any(ch in tok for ch in " \t|<>"):
        return False
    top = tok.lstrip("/").split("/", 1)[0]
    return os.path.isdir(os.path.join(repo_root, top))


def is_local_link(target):
    return not target.startswith(("http://", "https://", "mailto:", "#", "//"))


def resolve_rel(repo_root, doc_rel, target):
    t = target.split("#", 1)[0].split("?", 1)[0]
    if not t:
        return True  # pure in-page anchor
    if t.startswith("/"):
        cand = os.path.join(repo_root, t.lstrip("/"))
    else:
        cand = os.path.join(repo_root, os.path.dirname(doc_rel), t)
    return os.path.exists(cand)


def _read(repo_root, rel):
    try:
        with open(os.path.join(repo_root, rel), encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def check_format(repo_root, docs, cfg):
    findings = []
    fm_fields = cfg.get("frontMatterFields") or []
    for d in docs:
        text = _read(repo_root, d)
        if text is None:
            continue
        if fm_fields:
            fm = parse_front_matter(text)
            if fm is None:
                findings.append({"layer": "format", "severity": "WARN", "path": d,
                                 "line": 1, "message": "missing YAML front matter"})
            else:
                for f in fm_fields:
                    if f not in fm:
                        findings.append({"layer": "format", "severity": "WARN", "path": d,
                                         "line": 1, "message": f"front matter missing field: {f}"})
        for target, line in extract_links(text):
            if not is_local_link(target):
                continue
            if not resolve_rel(repo_root, d, target):
                findings.append({"layer": "format", "severity": "FAIL", "path": d,
                                 "line": line, "message": f"broken relative link: {target}"})
    return findings


def check_existence(repo_root, docs, cfg):
    findings = []
    for d in docs:
        text = _read(repo_root, d)
        if text is None:
            continue
        for tok, line in extract_path_tokens(text):
            t = tok.split("#", 1)[0]
            # Skip non-literal path tokens: globs, ellipsis, and brace-expansion are
            # illustrative shorthand, not a single concrete path (limit noise).
            if any(ch in t for ch in "*{}") or "..." in t or "…" in t:
                continue
            if not looks_like_repo_path(t, repo_root):
                continue
            if os.path.exists(os.path.join(repo_root, t.lstrip("/"))):
                continue
            # A trailing ":<locator>" (line number/range or symbol name) points INTO a
            # file and is not part of the path; resolve the base path when present.
            base = t.split(":", 1)[0]
            if base != t and looks_like_repo_path(base, repo_root) \
                    and os.path.exists(os.path.join(repo_root, base.lstrip("/"))):
                continue
            findings.append({"layer": "existence", "severity": "WARN", "path": d,
                             "line": line, "message": f"path-like token does not resolve: {tok}"})
    return findings


def check_semantic(repo_root, docs, cfg, all_docs=None):
    findings = []
    scan = all_docs if all_docs is not None else docs
    index_files = cfg.get("indexFiles")
    if index_files is None:
        index_files = [d for d in scan if os.path.basename(d).lower() == "readme.md"]
    index_files = set(index_files)
    referenced = set()
    for d in scan:  # build 'referenced' from ALL docs so index links always count
        text = _read(repo_root, d)
        if text is None:
            continue
        for target, _line in extract_links(text):
            if not is_local_link(target):
                continue
            t = target.split("#", 1)[0].split("?", 1)[0]
            if not t:
                continue
            if t.startswith("/"):
                ref = os.path.normpath(t.lstrip("/"))
            else:
                ref = os.path.normpath(os.path.join(os.path.dirname(d), t))
            referenced.add(ref)
    for d in docs:  # report orphans only among the (scoped) docs
        if d in index_files:
            continue
        if os.path.normpath(d) not in referenced:
            findings.append({"layer": "semantic", "severity": "WARN", "path": d,
                             "line": 1, "message": "orphan: not linked from any index file or other doc"})
    return findings


LAYERS = {"format": check_format, "existence": check_existence, "semantic": check_semantic}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--layer", choices=["format", "existence", "semantic", "all"], default="all")
    ap.add_argument("--paths", default=None,
                    help="file with newline doc paths, or '-' for stdin; default = all docGlobs docs")
    args = ap.parse_args()
    try:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(2)
    repo = args.repo_root
    if args.paths:
        if args.paths == "-":
            raw = sys.stdin.read()
        else:
            try:
                with open(args.paths, encoding="utf-8") as f:
                    raw = f.read()
            except OSError as e:
                print(f"error: {e}", file=sys.stderr); sys.exit(2)
        docs = [l.strip() for l in raw.splitlines() if l.strip()]
        all_docs = list_doc_files(repo, cfg.get("docGlobs", ["docs/**/*.md", "*.md"]))
    else:
        docs = list_doc_files(repo, cfg.get("docGlobs", ["docs/**/*.md", "*.md"]))
        all_docs = docs
    layers = list(LAYERS) if args.layer == "all" else [args.layer]
    findings = []
    for L in layers:
        if L == "semantic":
            findings.extend(check_semantic(repo, docs, cfg, all_docs=all_docs))
        else:
            findings.extend(LAYERS[L](repo, docs, cfg))
    counts = {"docs": len(docs), "findings": len(findings),
              "fail": sum(1 for f in findings if f["severity"] == "FAIL"),
              "warn": sum(1 for f in findings if f["severity"] == "WARN")}
    json.dump({"findings": findings, "counts": counts}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

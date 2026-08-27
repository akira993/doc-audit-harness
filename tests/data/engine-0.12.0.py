#!/usr/bin/env python3
"""generic-layers.py — portable, config-driven doc checks (docaudit Plan 2 fallback).

Used by the audit SKILL when a repo has no project-specific docAuditCommands.
Intentionally minimal (weaker than a bespoke /check-docs); the rich version is the
project's own tooling.

Layers:
  format    — relative markdown links must resolve on disk (broken => FAIL); if
              config.frontMatterFields is set, each .md must have YAML front matter
              containing the selected fields (missing => WARN). Link syntax inside code
              (inline `...` spans and ``` / ~~~ fenced blocks) is literal text, not a
              link, and is ignored.
  existence — backtick path-like tokens that look repo-relative must resolve on disk
              (missing concrete file => FAIL; directory-shaped token => WARN). Bare
              ASCII path references are also harvested as WARN-only findings. A trailing
              ':line'/':symbol' locator resolves against the base file; code, links,
              URLs, ellipsis, brace, and glob shorthand are ignored as applicable.
  semantic  — orphan: a .md linked from no index file and no other doc (=> WARN).

Reads:  --config, --repo-root, --layer {format,existence,semantic,all},
        --paths PATH|-  (optional; restrict to these docs; default = all docGlobs docs)
Writes JSON: {"findings":[{layer,severity,path,line,message}], "counts":{docs,findings,fail,warn}}
"""
import argparse, json, os, re, sys, urllib.parse

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


def list_doc_files(repo_root, doc_globs, report_rx=None):
    skip = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
    regexes = [glob_to_regex(g) for g in doc_globs]
    docs = []
    for dp, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in skip]  # prune .git/node_modules/etc
        for fn in files:
            rel = os.path.relpath(os.path.join(dp, fn), repo_root)
            if any(rx.match(rel) for rx in regexes) and not (report_rx and re.fullmatch(report_rx, rel)):
                docs.append(rel)
    return sorted(docs)


# Self-contained copy of the reportPath validity contract whose canonical source is
# change-set-sha.py:43-57. Keep the validity checks and placeholder rules aligned.
def report_pattern(config):
    value = config.get("reportPath")
    globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
    if not isinstance(value, str) or not value.endswith(".md"):
        return None
    sample = value.replace("<YYYY-MM-DD>", "2000-01-01").replace("[_NN]", "_01")
    if not any(glob_to_regex(item).match(sample) for item in globs if isinstance(item, str)):
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


def _corpus_report_filter(config):
    value = config.get("auditReportsInCorpus", False)
    if isinstance(value, bool):
        return (None if value else report_pattern(config)), []
    return report_pattern(config), [_config_finding(
        "config", "auditReportsInCorpus must be a boolean; false used")]


def _config_finding(layer, message):
    return {"layer": layer, "severity": "WARN", "path": "(config)",
            "line": 1, "message": message}


def _layer_excludes(cfg, layer):
    raw = cfg.get("layerGlobs")
    if raw is None:
        return [], []
    if not isinstance(raw, dict):
        return [], [_config_finding(layer, "layerGlobs must be an object; ignored")]
    entry = raw.get(layer)
    if entry is None:
        return [], []
    if not isinstance(entry, dict):
        return [], [_config_finding(layer, f"layerGlobs.{layer} must be an object; ignored")]
    excludes = entry.get("exclude")
    if excludes is None:
        return [], []
    if not isinstance(excludes, list):
        return [], [_config_finding(layer, f"layerGlobs.{layer}.exclude must be an array; ignored")]
    valid = [item for item in excludes if isinstance(item, str)]
    findings = []
    if len(valid) != len(excludes):
        findings.append(_config_finding(
            layer, f"layerGlobs.{layer}.exclude contains a non-string entry; entry ignored"))
    return [glob_to_regex(item) for item in valid], findings


def _docs_for_layer(docs, cfg, layer):
    excludes, findings = _layer_excludes(cfg, layer)
    return [d for d in docs if not any(rx.match(d) for rx in excludes)], findings


def _front_matter_overrides(cfg):
    raw = cfg.get("frontMatterOverrides")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], [_config_finding("format", "frontMatterOverrides must be an array; ignored")]
    valid = []
    findings = []
    for entry in raw:
        if not isinstance(entry, dict) or not isinstance(entry.get("globs"), list) \
                or not all(isinstance(glob, str) for glob in entry.get("globs", [])) \
                or not isinstance(entry.get("fields"), list) \
                or not all(isinstance(field, str) for field in entry.get("fields", [])):
            findings.append(_config_finding(
                "format", "frontMatterOverrides entry must have string-array globs and fields; ignored"))
            continue
        valid.append(([glob_to_regex(glob) for glob in entry["globs"]], entry["fields"]))
    return valid, findings


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


_FENCE_OPEN_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
# An inline code span on a single line: a backtick run, content, the same-length run.
# Single-line (no re.DOTALL) so a stray backtick cannot swallow links on later lines.
_INLINE_CODE_RE = re.compile(r"(`+)[^\n]+?\1")


def _strip_container_markers(line):
    rest = line
    while True:
        blockquote = re.match(r"^ {0,3}>[ \t]*", rest)
        if blockquote:
            rest = rest[blockquote.end():]
            continue
        list_item = re.match(r"^ {0,3}(?:[-*+]|[0-9]+[.)])[ \t]+", rest)
        if list_item:
            rest = rest[list_item.end():]
            continue
        return rest


def _mask_fenced(text):
    # Blank fenced code blocks in place (length + newlines preserved). Tracks the open
    # fence char/length so only a matching closer (same char, >= length, line by itself)
    # ends the block; an unterminated fence masks to end of file (CommonMark behaviour).
    lines = text.split("\n")
    out, fence = [], None
    for line in lines:
        content = _strip_container_markers(line)
        if fence is None:
            m = _FENCE_OPEN_RE.match(content)
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
            if re.match(r"^ {0,3}%s{%d,}\s*$" % (re.escape(fch), flen), content):
                fence = None
    return "\n".join(out)


def _mask_indented(text):
    out = []
    for line in text.split("\n"):
        content = _strip_container_markers(line)
        if content.startswith("    ") or content.startswith("\t"):
            out.append(_blank_keep_newlines(line))
        else:
            out.append(line)
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
    masked = _mask_indented(_mask_fenced(text))
    out = []
    for m in _TOKEN_RE.finditer(masked):
        out.append((m.group(1).strip(), masked.count("\n", 0, m.start()) + 1))
    return out


_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[A-Za-z0-9_./+%@~?#=&:;,()-]*")
_BARE_PATH_RE = re.compile(r"[A-Za-z0-9_./+%@~-]+")


def extract_bare_paths(text):
    masked = _mask_indented(_mask_fenced(text))
    masked = _LINK_RE.sub(lambda m: " " * len(m.group(0)), masked)
    masked = _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), masked)
    masked = _URL_RE.sub(lambda m: " " * len(m.group(0)), masked)
    out = []
    for m in _BARE_PATH_RE.finditer(masked):
        token = m.group(0)
        if "/" not in token:
            continue
        if token.endswith("."):
            token = token[:-1]
        if token:
            out.append((token, masked.count("\n", 0, m.start()) + 1))
    return out


def looks_like_repo_path(tok, repo_root):
    # conservative: must contain '/', no whitespace/shell chars, and start with an
    # existing top-level directory of the repo (so prose/commands are not flagged).
    if "/" not in tok or tok.startswith("//") or any(ch in tok for ch in " \t|<>"):
        return False
    if ".." in tok.split("/"):
        return False
    top = tok.lstrip("/").split("/", 1)[0]
    try:
        return os.path.isdir(os.path.join(repo_root, top))
    except (OSError, ValueError):
        return False


def _without_suffix(tok):
    ends = [pos for pos in (tok.find("#"), tok.find("?")) if pos >= 0]
    return tok[:min(ends)] if ends else tok


def _token_base(tok, repo_root):
    base = _without_suffix(tok)
    locator_base = base.split(":", 1)[0]
    if locator_base != base and looks_like_repo_path(locator_base, repo_root):
        return locator_base
    return base


def _decoded_candidate(base):
    if "%" not in base:
        return None
    decoded = urllib.parse.unquote(base)
    if any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in decoded):
        return None
    if ".." in decoded.split("/"):
        return None
    return decoded


def _resolve_path_token(tok, repo_root):
    try:
        repo_real = os.path.realpath(repo_root)
    except (OSError, ValueError):
        return None, None
    full_base = _without_suffix(tok)
    locator_base = full_base.split(":", 1)[0]
    bases = [full_base]
    if locator_base != full_base and looks_like_repo_path(locator_base, repo_root):
        bases.append(locator_base)
    last = None
    for base in bases:
        if not looks_like_repo_path(base, repo_root):
            continue
        candidates = [base]
        decoded = _decoded_candidate(base)
        if decoded is not None and decoded != base:
            candidates.append(decoded)
        for candidate in candidates:
            last = candidate
            try:
                full = os.path.join(repo_root, candidate.lstrip("/"))
                resolved = os.path.realpath(full)
                if os.path.commonpath([repo_real, resolved]) != repo_real:
                    return None, None
                if os.path.exists(full):
                    return True, candidate
            except (OSError, ValueError):
                return None, None
    return (False, last) if last is not None else (None, None)


def _is_concrete_file_path(path):
    if path.endswith("/"):
        return False
    name = os.path.basename(path)
    if name.startswith("."):
        return False
    return bool(re.search(r"\.[A-Za-z][A-Za-z0-9]{0,7}$", name))


def _is_shorthand(tok):
    return any(ch in tok for ch in "*{}") or "..." in tok or "…" in tok


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
    try:
        return os.path.exists(cand)
    except (OSError, ValueError):
        return True


def _read(repo_root, rel):
    try:
        with open(os.path.join(repo_root, rel), encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return None


def check_format(repo_root, docs, cfg):
    docs, findings = _docs_for_layer(docs, cfg, "format")
    fm_fields = cfg.get("frontMatterFields") or []
    overrides, override_findings = _front_matter_overrides(cfg)
    findings.extend(override_findings)
    for d in docs:
        text = _read(repo_root, d)
        if text is None:
            continue
        selected_fields = fm_fields
        for regexes, fields in overrides:
            if any(rx.match(d) for rx in regexes):
                selected_fields = fields
                break
        if selected_fields:
            fm = parse_front_matter(text)
            if fm is None:
                findings.append({"layer": "format", "severity": "WARN", "path": d,
                                 "line": 1, "message": "missing YAML front matter"})
            else:
                for f in selected_fields:
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
    docs, findings = _docs_for_layer(docs, cfg, "existence")
    for d in docs:
        text = _read(repo_root, d)
        if text is None:
            continue
        for tok, line in extract_path_tokens(text):
            # Skip non-literal path tokens: globs, ellipsis, and brace-expansion are
            # illustrative shorthand, not a single concrete path (limit noise).
            if _is_shorthand(_without_suffix(tok)):
                continue
            resolved, base = _resolve_path_token(tok, repo_root)
            if resolved is None or resolved:
                continue
            severity = "FAIL" if _is_concrete_file_path(base) else "WARN"
            findings.append({"layer": "existence", "severity": severity, "path": d,
                             "line": line, "message": f"path-like token does not resolve: {tok}"})
        for tok, line in extract_bare_paths(text):
            if _is_shorthand(_without_suffix(tok)):
                continue
            resolved, _base = _resolve_path_token(tok, repo_root)
            if resolved is None or resolved:
                continue
            findings.append({"layer": "existence", "severity": "WARN", "path": d,
                             "line": line, "message": f"bare path reference does not resolve: {tok}"})
    return findings


def check_semantic(repo_root, docs, cfg, all_docs=None):
    report_docs, findings = _docs_for_layer(docs, cfg, "semantic")
    scan = all_docs if all_docs is not None else docs
    index_files = cfg.get("indexFiles")
    if index_files is None:
        index_files = [d for d in scan if os.path.basename(d).lower() == "readme.md"]
    valid_indexes = set()
    repo_real = os.path.realpath(repo_root)
    for raw_index in index_files:
        if not isinstance(raw_index, str) or not raw_index:
            findings.append({"layer": "semantic", "severity": "WARN", "path": str(raw_index),
                             "line": 1, "message": "indexFiles entry is invalid and was excluded"})
            continue
        normalized = os.path.normpath(raw_index)
        if os.path.isabs(raw_index) or normalized == ".." or normalized.startswith(".." + os.sep):
            findings.append({"layer": "semantic", "severity": "WARN", "path": raw_index,
                             "line": 1, "message": "indexFiles entry is outside the repository and was excluded"})
            continue
        full = os.path.join(repo_root, normalized)
        if not os.path.exists(full):
            findings.append({"layer": "semantic", "severity": "WARN", "path": normalized,
                             "line": 1, "message": "indexFiles entry does not exist and was excluded"})
            continue
        # A path may be lexically inside the repository while resolving through
        # a symlink to an external file.  Do not index external content.
        try:
            resolved = os.path.realpath(full)
            if os.path.commonpath([repo_real, resolved]) != repo_real:
                findings.append({"layer": "semantic", "severity": "WARN", "path": normalized,
                                 "line": 1,
                                 "message": "indexFiles entry resolves outside the repository and was excluded"})
                continue
        except ValueError:
            findings.append({"layer": "semantic", "severity": "WARN", "path": normalized,
                             "line": 1,
                             "message": "indexFiles entry resolves outside the repository and was excluded"})
            continue
        if not os.path.isfile(full):
            findings.append({"layer": "semantic", "severity": "WARN", "path": normalized,
                             "line": 1, "message": "indexFiles entry is not a regular file and was excluded"})
            continue
        valid_indexes.add(normalized)
    scan = sorted(set(scan) | valid_indexes)
    index_files = valid_indexes
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
    for d in report_docs:  # report orphans only among the (scoped) docs
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
    ap.add_argument("--format", choices=["json", "text"], default="json")
    ap.add_argument("--exit-code", action="store_true",
                    help="exit 1 when at least one FAIL finding exists")
    args = ap.parse_args()
    try:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(2)
    repo = args.repo_root
    report_rx, config_findings = _corpus_report_filter(cfg)
    doc_globs = cfg.get("docGlobs", ["docs/**/*.md", "*.md"])
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
        all_docs = sorted(set(list_doc_files(repo, doc_globs, report_rx)) | set(docs))
    else:
        docs = list_doc_files(repo, doc_globs, report_rx)
        all_docs = docs
    layers = list(LAYERS) if args.layer == "all" else [args.layer]
    findings = list(config_findings)
    for L in layers:
        if L == "semantic":
            findings.extend(check_semantic(repo, docs, cfg, all_docs=all_docs))
        else:
            findings.extend(LAYERS[L](repo, docs, cfg))
    seen_config = set()
    deduplicated = []
    for finding in findings:
        if finding["path"] == "(config)":
            if finding["message"] in seen_config:
                continue
            seen_config.add(finding["message"])
        deduplicated.append(finding)
    findings = deduplicated
    counts = {"docs": len(docs), "findings": len(findings),
              "fail": sum(1 for f in findings if f["severity"] == "FAIL"),
              "warn": sum(1 for f in findings if f["severity"] == "WARN")}
    if args.format == "json":
        json.dump({"findings": findings, "counts": counts}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        for finding in findings:
            print("HIT {severity} {path}:{line} {message}".format(**finding))
        doc_set = set(docs)
        finding_paths = {finding["path"] for finding in findings if finding["path"] in doc_set}
        passed = max(0, len(docs) - len(finding_paths))
        print(f"SUMMARY pass={passed} warn={counts['warn']} fail={counts['fail']}")
        print("VERDICT " + ("NEEDS FIX" if counts["fail"] else "CONSISTENT"))
    if args.exit_code and counts["fail"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

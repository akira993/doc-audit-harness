#!/usr/bin/env python3
"""inventory.py — deterministic repo inventory for docaudit `init` (Plan 3).

Scans a target repo and emits structured JSON the init SKILL uses to DRAFT a
.claude/doc-audit.json proposal (which the user reviews/approves before it is
written). grep/find only — MCP-free; mdq/CocoIndex/Serena may enrich the draft.

Output keys: docDirs, docGlobs, frontMatter{present,total,fields},
suggestedFrontMatterFields, codeDirs, suggestedDiffGlobs,
existingDocTools{commands,skills}, existingDocToolCandidates[{kind,path,name}],
boundaryCommandGuess, indexFiles, mentions{name->[docs]}.
"""
import argparse, json, os, re, sys

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    tomllib = None

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def walk_rel(root, skip_hidden=False):
    for dp, dirs, files in os.walk(root):
        parts = os.path.relpath(dp, root).replace("\\", "/").split("/")
        if any(p in SKIP_DIRS for p in parts):
            dirs[:] = []
            continue
        if skip_hidden and any(p.startswith(".") for p in parts if p != "."):
            dirs[:] = []
            continue
        for fn in files:
            yield os.path.relpath(os.path.join(dp, fn), root)


def list_docs(root):
    return sorted(f for f in walk_rel(root, skip_hidden=True) if f.endswith(".md"))


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
def fm_fields(text):
    m = _FM_RE.match(text)
    if not m:
        return None
    out = []
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z0-9_-]+)\s*:", line)
        if mm:
            out.append(mm.group(1))
    return out


def _read(p):
    try:
        with open(p, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


_TOOL_NAME_RE = re.compile(r"docs|doc-|lint", re.I)


def _toolish(name):
    return bool(_TOOL_NAME_RE.search(name))


def _candidate(kind, path, name):
    return {"kind": kind, "path": path.replace("\\", "/"), "name": name}


def _mapping_script_candidates(mapping, path, kind):
    if not isinstance(mapping, dict):
        return []
    return [_candidate(kind, path, str(name)) for name in sorted(mapping)
            if _toolish(str(name))]


def _target_candidates(root, filename, kind):
    path = os.path.join(root, filename)
    if not os.path.isfile(path):
        return []
    text = _read(path)
    if filename == "Makefile":
        names = re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", text, re.M)
    elif filename == "Justfile":
        names = re.findall(r"^([A-Za-z0-9_.-]+)(?:\s+[^:=\n]+)?\s*:(?!=)", text, re.M)
    else:  # Taskfile.yml: task keys conventionally sit two spaces under `tasks:`.
        names = re.findall(r"^  ([A-Za-z0-9_.:-]+)\s*:\s*(?:#.*)?$", text, re.M)
    return [_candidate(kind, filename, name) for name in sorted(set(names)) if _toolish(name)]


def _pyproject_candidates(root):
    rel = "pyproject.toml"
    path = os.path.join(root, rel)
    if not os.path.isfile(path) or tomllib is None:
        return []
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    out = _mapping_script_candidates(data.get("project", {}).get("scripts"), rel,
                                     "pyproject-script")

    def visit_tool(node):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key == "scripts":
                out.extend(_mapping_script_candidates(value, rel, "pyproject-script"))
            elif isinstance(value, dict):
                visit_tool(value)

    visit_tool(data.get("tool", {}))
    return out


def _workflow_candidates(root):
    directory = os.path.join(root, ".github", "workflows")
    if not os.path.isdir(directory):
        return []
    out = []
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith((".yml", ".yaml")):
            continue
        rel = f".github/workflows/{filename}"
        text = _read(os.path.join(directory, filename))
        # Split on YAML list items. This deliberately remains a conservative text
        # inventory: candidates are shown to the user and are never auto-wired.
        for block in re.split(r"(?m)^(?=\s*-\s+(?:name|run|uses)\s*:)", text):
            name_match = re.search(r"(?m)^\s*-?\s*name\s*:\s*['\"]?([^\n'\"]+)", block)
            run_match = re.search(r"(?ms)^\s*run\s*:\s*(.*?)(?=^\s*(?:-|[A-Za-z][\w-]*)\s*:|\Z)", block)
            name = name_match.group(1).strip() if name_match else ""
            run = run_match.group(1).strip() if run_match else ""
            if re.search(r"docs|doc-|lint|markdown", name, re.I) \
                    or re.search(r"docs|doc-|lint|markdown", run, re.I):
                label = name or run.splitlines()[0][:120]
                out.append(_candidate("github-workflow-step", rel, label))
    return out


def existing_doc_tool_candidates(root):
    candidates = []
    cmddir = os.path.join(root, ".claude", "commands")
    if os.path.isdir(cmddir):
        for filename in sorted(os.listdir(cmddir)):
            stem, ext = os.path.splitext(filename)
            if ext == ".md" and re.search(r"doc|docs|lint", stem, re.I):
                candidates.append(_candidate("claude-command",
                                             f".claude/commands/{filename}", stem))

    skdir = os.path.join(root, ".claude", "skills")
    if os.path.isdir(skdir):
        for name in sorted(os.listdir(skdir)):
            rel = f".claude/skills/{name}/SKILL.md"
            if re.search(r"doc|docs|lint", name, re.I) \
                    and os.path.isfile(os.path.join(root, rel)):
                candidates.append(_candidate("claude-skill", rel, name))

    package_path = os.path.join(root, "package.json")
    if os.path.isfile(package_path):
        try:
            package = json.loads(_read(package_path))
        except json.JSONDecodeError:
            package = {}
        candidates.extend(_mapping_script_candidates(package.get("scripts"), "package.json",
                                                      "package-script"))

    candidates.extend(_target_candidates(root, "Makefile", "make-target"))
    candidates.extend(_target_candidates(root, "Taskfile.yml", "taskfile-target"))
    candidates.extend(_target_candidates(root, "Justfile", "just-target"))
    candidates.extend(_pyproject_candidates(root))
    candidates.extend(_workflow_candidates(root))

    scripts = os.path.join(root, "scripts")
    if os.path.isdir(scripts):
        for filename in sorted(os.listdir(scripts)):
            if filename.startswith("check-docs") and os.path.isfile(os.path.join(scripts, filename)):
                candidates.append(_candidate("script", f"scripts/{filename}", filename))

    unique = {(c["kind"], c["path"], c["name"]): c for c in candidates}
    return [unique[key] for key in sorted(unique)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.getcwd())
    args = ap.parse_args()
    root = args.repo_root

    docs = list_docs(root)
    docdirs = sorted({d.split("/")[0] for d in docs if "/" in d})

    present, field_count = 0, {}
    for d in docs:
        ff = fm_fields(_read(os.path.join(root, d)))
        if ff is not None:
            present += 1
            for f in ff:
                field_count[f] = field_count.get(f, 0) + 1
    suggested_fm = [f for f, c in sorted(field_count.items(), key=lambda x: (-x[1], x[0]))
                    if present and c >= 0.8 * present]

    entries = [e for e in sorted(os.listdir(root)) if not e.startswith(".")]
    topdirs = [e for e in entries if os.path.isdir(os.path.join(root, e))]
    code_dirs = [d for d in topdirs if d != "docs" and d not in SKIP_DIRS]
    key_files = [f for f in ("Makefile", "CLAUDE.md", "DESIGN.md", "README.md")
                 if os.path.isfile(os.path.join(root, f))]

    diff = [f"{d}/**" for d in code_dirs] + key_files
    if "docs" in topdirs:
        diff.append("docs/**")
    if os.path.isdir(os.path.join(root, ".claude")):
        diff.append(".claude/**")

    # derive doc globs from dirs that ACTUALLY contain docs (handles non-standard
    # layouts like vps/; symlinked dirs are not walked so they are excluded).
    docglobs = [f"{d}/**/*.md" for d in docdirs]
    docglobs.append("*.md")
    if os.path.isdir(os.path.join(root, ".claude")):
        docglobs.append(".claude/**/*.md")

    candidates = existing_doc_tool_candidates(root)
    cmds = [c["path"] for c in candidates if c["kind"] == "claude-command"]
    # Keep the legacy value shape: skill directory paths, not SKILL.md paths.
    sks = [os.path.dirname(c["path"]) for c in candidates if c["kind"] == "claude-skill"]

    boundary = None
    mk = os.path.join(root, "Makefile")
    if os.path.isfile(mk):
        m = re.search(r"^(check-boundary|boundary[\w-]*)\s*:", _read(mk), re.M)
        if m:
            boundary = f"make {m.group(1)}"

    index = [d for d in docs if os.path.basename(d).lower() == "readme.md"]

    names = code_dirs + key_files
    mentions = {n: [] for n in names}
    for d in docs:
        text = _read(os.path.join(root, d))
        for n in names:
            if n in text:
                mentions[n].append(d)

    out = {
        "docDirs": docdirs,
        "docGlobs": docglobs,
        "frontMatter": {"present": present, "total": len(docs), "fields": field_count},
        "suggestedFrontMatterFields": suggested_fm,
        "codeDirs": code_dirs,
        "suggestedDiffGlobs": diff,
        "existingDocTools": {"commands": cmds, "skills": sks},
        "existingDocToolCandidates": candidates,
        "boundaryCommandGuess": boundary,
        "indexFiles": index,
        "mentions": {k: v for k, v in mentions.items() if v},
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""inventory.py — deterministic repo inventory for docaudit `init` (Plan 3).

Scans a target repo and emits structured JSON the init SKILL uses to DRAFT a
.claude/doc-audit.json proposal (which the user reviews/approves before it is
written). grep/find only — MCP-free; mdq/CocoIndex/Serena may enrich the draft.

Output keys: docDirs, docGlobs, frontMatter{present,total,fields},
suggestedFrontMatterFields, codeDirs, suggestedDiffGlobs,
existingDocTools{commands,skills}, boundaryCommandGuess, indexFiles,
mentions{name->[docs]}.
"""
import argparse, json, os, re, sys

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

    cmds, sks = [], []
    cmddir = os.path.join(root, ".claude", "commands")
    if os.path.isdir(cmddir):
        for fn in sorted(os.listdir(cmddir)):
            if fn.endswith(".md") and any(k in fn for k in ("check-docs", "review-docs", "doc")):
                cmds.append(f".claude/commands/{fn}")
    skdir = os.path.join(root, ".claude", "skills")
    if os.path.isdir(skdir):
        for name in sorted(os.listdir(skdir)):
            if any(k in name for k in ("doc-lint", "lint", "doc")):
                sks.append(f".claude/skills/{name}")

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
        "boundaryCommandGuess": boundary,
        "indexFiles": index,
        "mentions": {k: v for k, v in mentions.items() if v},
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

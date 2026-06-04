#!/usr/bin/env python3
"""scaffold.py — generate project-tailored doc-audit layer SKILL skeletons (docaudit Plan 4, --scaffold).

Writes .claude/skills/<prefix>-<layer>/SKILL.md skeletons into the TARGET repo as a
STARTING POINT for project-specific doc checks (richer than the generic fallback).
The init SKILL then uses skill-creator-max / superpowers:writing-skills to tailor +
trigger-test them, and wires docAuditCommands to them.

SAFE: never overwrites an existing file; --dry-run writes nothing.
Reads: --repo-root, --prefix, --layers (comma-sep; default format,existence,semantic), --dry-run
Writes JSON: {"created":[rel], "skipped":[rel], "skillNames":{layer:name}}
"""
import argparse, json, os, sys

LAYER_DESC = {
    "format": "front matter, links, and formatting conventions",
    "existence": "documented paths/values match the repo and its sources of truth",
    "semantic": "cross-doc consistency: contradictions, stale claims, orphans, cross-refs",
}

EXAMPLES = {
    "format": "- required front-matter fields and their formats\n- internal link and anchor resolution\n- naming / heading conventions",
    "existence": "- documented file paths exist on disk\n- documented version/stack values match the SSoT (e.g. occ status, info.xml)\n- command tables match the Makefile",
    "semantic": "- the same fact stated consistently across docs\n- 'planned / TODO' claims that are actually done\n- orphan pages; one-directional cross-references",
}

TEMPLATE = """---
name: {name}
description: Project-tailored {layer} documentation check for this repository ({desc}). Use when auditing this project's docs for {layer} issues, or when docaudit's {layer} layer runs. Report-only; proposes fixes, never edits.
---

# {name} — project {layer} doc check

Scaffolded by `/docaudit:init --scaffold` as a STARTING POINT. Report-only: propose
fixes; never edit existing docs or ADRs. Customize the checks below for this repo.

## Checks (CUSTOMIZE — TODO)
Replace this with the repository's concrete {layer} rules. Candidate checks for {layer}:
{examples}

docaudit's generic {layer} layer already covers a portable baseline ({desc}); this
skill is where project-specific rules go on top.

## Output
Emit findings as `path:line - SEVERITY - message`, each with a fix proposal, then a
roll-up PASS / WARN / FAIL. Never edit files.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--prefix", default="docaudit")
    ap.add_argument("--layers", default="format,existence,semantic")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    layers = [l.strip() for l in args.layers.split(",") if l.strip()]
    created, skipped, names = [], [], {}
    for layer in layers:
        if layer not in LAYER_DESC:
            print(f"error: unknown layer: {layer}", file=sys.stderr)
            sys.exit(2)
        name = f"{args.prefix}-{layer}"
        names[layer] = name
        rel = os.path.join(".claude", "skills", name, "SKILL.md")
        dest = os.path.join(args.repo_root, rel)
        if os.path.exists(dest):
            skipped.append(rel)
            continue
        created.append(rel)
        if not args.dry_run:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(TEMPLATE.format(name=name, layer=layer,
                                        desc=LAYER_DESC[layer], examples=EXAMPLES[layer]))
    json.dump({"created": created, "skipped": skipped, "skillNames": names},
              sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate additive docaudit skill scaffolds and the optional local harness.

Legacy scaffold mode creates .claude/skills/<prefix>-<layer>/SKILL.md and never
overwrites. Harness mode creates /check-docs, doc-lint, and a standalone copy of
generic-layers.py. --refresh overwrites only an unmodified stamped harness file.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from docaudit_paths import validate_repo_path


AUDIT_DIR = os.path.dirname(SCRIPT_DIR)
REPO_DIR = os.path.dirname(os.path.dirname(AUDIT_DIR))
PLUGIN_JSON = os.path.join(REPO_DIR, ".claude-plugin", "plugin.json")
ENGINE_SHAS = os.path.join(AUDIT_DIR, "references", "engine-shas.json")
ENGINE_SOURCE = os.path.join(SCRIPT_DIR, "generic-layers.py")

HARNESS_COMMANDS = {
    "existence": "/check-docs --only existence",
    "format": "/check-docs --only format",
    "semantic": "doc-lint",
}

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

SKILL_TEMPLATE = """---
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

CHECK_DOCS_TEMPLATE = """---
description: Run the repository's deterministic documentation checks by layer and report their output without editing files.
argument-hint: "[--only <format|existence|semantic|all>]"
---

# check-docs

Interpret `$ARGUMENTS` before running the check. If it contains `--only <layer>`, set
`<LAYER>=<layer>`; if it does not, set `<LAYER>=all`.

Run exactly this command:

`python3 scripts/check-docs.py --layer <LAYER> --format text --exit-code --config .claude/doc-audit.json --repo-root .`

Quote the engine output verbatim; do not recreate its checks or verdict in the model:

## PASS

Quote the `SUMMARY` pass count and any `VERDICT CONSISTENT` line verbatim.

## WARN

Quote every `HIT WARN` line and the `SUMMARY` warn count verbatim.

## FAIL

Quote every `HIT FAIL` line and the `SUMMARY` fail count verbatim.

## Verdict

Quote the final `VERDICT` line verbatim as the result. Only when it is
`VERDICT CONSISTENT`, propose running `doc-lint` for the deeper language-model check.
Never edit documentation; report findings and proposed fixes only.
"""

DOC_LINT_TEMPLATE = """---
name: doc-lint
description: Report-only semantic documentation review for contradictions, stale claims, orphan pages, and missing cross-references after the deterministic check.
---

# doc-lint

First run this deterministic semantic check and quote its output verbatim:

`python3 scripts/check-docs.py --layer semantic --format text --config .claude/doc-audit.json --repo-root .`

Then inspect the repository documentation for contradictions, stale claims, orphan
pages, and missing cross-references. List every finding on one line exactly as
`path:line - FAIL|WARN - message`, including a proposed fix in the message. After all
findings, print one final standalone line: `VERDICT CONSISTENT` when there are no FAIL
findings, or `VERDICT NEEDS FIX` when there is at least one FAIL finding. This skill is
report-only: never edit a file and never replace or reinterpret the deterministic
engine's `SUMMARY` or `VERDICT` lines.
"""

STAMP_RE = re.compile(
    r"^(?:<!--\s*|#\s*)docaudit-template:\s*([\w-]+)@([^\s]+)\s+sha256:([0-9a-f]{64})(?:\s*-->)?\s*$"
)


def _read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _normalized_sha(text):
    lines = text.splitlines(keepends=True)
    normalized = "".join(line for line in lines if not STAMP_RE.match(line.rstrip("\r\n")))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _markdown_with_stamp(text, name, version, digest):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"{name}: front matter must be first")
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            stamp = f"<!-- docaudit-template: {name}@{version} sha256:{digest} -->\n"
            return "".join(lines[:index + 1] + [stamp] + lines[index + 1:])
    raise ValueError(f"{name}: front matter is not closed")


def _python_with_stamp(text, name, version, digest):
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("#!"):
        raise ValueError("check-docs engine must start with a shebang")
    stamp = f"# docaudit-template: {name}@{version} sha256:{digest}\n"
    return "".join([lines[0], stamp] + lines[1:])


def _harness_sources():
    return {
        "check-docs": CHECK_DOCS_TEMPLATE,
        "doc-lint": DOC_LINT_TEMPLATE,
        "check-docs-engine": _read_text(ENGINE_SOURCE),
    }


def _current_templates(version, shipped):
    sources = _harness_sources()
    expected = shipped.get(version)
    if not isinstance(expected, dict):
        raise ValueError(f"engine-shas.json has no entry for plugin version {version}")
    actual = {name: _normalized_sha(text) for name, text in sources.items()}
    mismatches = [name for name in sorted(actual) if expected.get(name) != actual[name]]
    if mismatches:
        raise ValueError("engine-shas.json is stale for: " + ", ".join(mismatches))
    return {
        "check-docs": _markdown_with_stamp(sources["check-docs"], "check-docs", version,
                                            actual["check-docs"]),
        "doc-lint": _markdown_with_stamp(sources["doc-lint"], "doc-lint", version,
                                          actual["doc-lint"]),
        "check-docs-engine": _python_with_stamp(sources["check-docs-engine"],
                                                  "check-docs-engine", version,
                                                  actual["check-docs-engine"]),
    }


def _stamp(text):
    for line in text.splitlines():
        match = STAMP_RE.match(line)
        if match:
            return {"name": match.group(1), "version": match.group(2), "sha": match.group(3)}
    return None


def _destination(repo_root, rel):
    safe_rel = validate_repo_path(repo_root, rel, must_exist=False, regular_file=False)
    return os.path.join(os.path.realpath(repo_root), *safe_rel.split("/"))


def _write_new(repo_root, rel, text, executable=False):
    path = _destination(repo_root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    path = _destination(repo_root, rel)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    if executable:
        current = stat.S_IMODE(os.stat(path).st_mode)
        os.chmod(path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _scaffold_layers(args, created, skipped, reasons):
    names = {}
    layers = [layer.strip() for layer in args.layers.split(",") if layer.strip()]
    for layer in layers:
        if layer not in LAYER_DESC:
            raise ValueError(f"unknown layer: {layer}")
        name = f"{args.prefix}-{layer}"
        names[layer] = name
        rel = f".claude/skills/{name}/SKILL.md"
        try:
            dest = _destination(args.repo_root, rel)
        except ValueError as exc:
            skipped.append(rel)
            reasons.append({"path": rel, "reason": f"unsafe destination: {exc}"})
            continue
        if os.path.exists(dest):
            skipped.append(rel)
            reasons.append({"path": rel, "reason": "exists"})
            continue
        if not args.dry_run:
            try:
                _write_new(args.repo_root, rel, SKILL_TEMPLATE.format(
                    name=name, layer=layer, desc=LAYER_DESC[layer], examples=EXAMPLES[layer]))
            except ValueError as exc:
                skipped.append(rel)
                reasons.append({"path": rel, "reason": f"unsafe destination: {exc}"})
                continue
        created.append(rel)
    return names


def _harness(args, version, shipped, created, skipped, reasons):
    templates = _current_templates(version, shipped)
    targets = (
        ("check-docs", ".claude/commands/check-docs.md", False),
        ("doc-lint", ".claude/skills/doc-lint/SKILL.md", False),
        ("check-docs-engine", "scripts/check-docs.py", True),
    )
    for name, rel, executable in targets:
        try:
            dest = _destination(args.repo_root, rel)
        except ValueError as exc:
            skipped.append(rel)
            reasons.append({"path": rel, "reason": f"unsafe destination: {exc}"})
            continue
        if not os.path.exists(dest):
            if not args.dry_run:
                try:
                    _write_new(args.repo_root, rel, templates[name], executable)
                except ValueError as exc:
                    skipped.append(rel)
                    reasons.append({"path": rel, "reason": f"unsafe destination: {exc}"})
                    continue
            created.append(rel)
            continue
        if not args.refresh:
            skipped.append(rel)
            reasons.append({"path": rel, "reason": "exists"})
            continue
        try:
            existing = _read_text(dest)
        except OSError as exc:
            skipped.append(rel)
            reasons.append({"path": rel, "reason": f"unreadable: {exc}"})
            continue
        stamp = _stamp(existing)
        if not stamp:
            skipped.append(rel)
            reasons.append({"path": rel, "reason": "missing template stamp"})
            continue
        historical = shipped.get(stamp["version"], {}).get(name)
        actual = _normalized_sha(existing)
        if stamp["name"] != name or not historical or stamp["sha"] != historical \
                or actual != historical:
            skipped.append(rel)
            reasons.append({"path": rel, "reason": "modified or unknown template stamp"})
            continue
        if not args.dry_run:
            try:
                _write_new(args.repo_root, rel, templates[name], executable)
            except ValueError as exc:
                skipped.append(rel)
                reasons.append({"path": rel, "reason": f"unsafe destination: {exc}"})
                continue
        created.append(rel)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=os.getcwd())
    parser.add_argument("--prefix", default="docaudit")
    parser.add_argument("--layers", default="format,existence,semantic")
    parser.add_argument("--scaffold", action="store_true",
                        help="create the legacy project-tailored layer skill skeletons")
    parser.add_argument("--harness", action="store_true",
                        help="create /check-docs, doc-lint, and scripts/check-docs.py")
    parser.add_argument("--refresh", action="store_true",
                        help="with --harness, refresh only unmodified stamped files")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.refresh and not args.harness:
        parser.error("--refresh requires --harness")

    try:
        version = str(_load_json(PLUGIN_JSON)["version"])
        shipped = _load_json(ENGINE_SHAS) if args.harness else {}
        created, skipped, reasons = [], [], []
        # No mode flag preserves the historical scaffold.py contract.
        do_scaffold = args.scaffold or not args.harness
        names = _scaffold_layers(args, created, skipped, reasons) if do_scaffold else {}
        if args.harness:
            _harness(args, version, shipped, created, skipped, reasons)
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        print(f"scaffold: {exc}", file=sys.stderr)
        return 2

    if args.harness:
        commands = dict(HARNESS_COMMANDS)
        if do_scaffold and "semantic" in names:
            commands["semantic"] = names["semantic"]
    else:
        commands = {layer: name for layer, name in names.items()}
    output = {
        "created": created,
        "skipped": skipped,
        "skipReasons": reasons,
        "stampVersion": version,
        "docAuditCommands": commands,
    }
    if do_scaffold:
        output["skillNames"] = names
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Mechanical release gate for docaudit v0.15.1 Issue #65."""

import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROUTE = "tasks/route/2026-08-30-issue-65-v0.15.1"
HANDOFF = f"{ROUTE}/release-handoff.sh"
REQUIRED_ROUTE = {
    f"{ROUTE}/PLAN.md",
    f"{ROUTE}/REVIEW.md",
    f"{ROUTE}/release-handoff.sh",
    f"{ROUTE}/gate.py",
    f"{ROUTE}/prompts/sol-r1.md",
    f"{ROUTE}/prompts/sol-r2.md",
    f"{ROUTE}/prompts/sol-r3.md",
    f"{ROUTE}/prompts/sol-r4.md",
    f"{ROUTE}/sol-r1-out.md",
    f"{ROUTE}/sol-r2-out.md",
    f"{ROUTE}/sol-r3-out.md",
    f"{ROUTE}/sol-r4-out.md",
    "tasks/route/2026-08-30-issues-59-63-65-66/00-issue-review.md",
}
OPTIONAL_ROUTE = {
    f"{ROUTE}/prompts/sol-r5.md",
    f"{ROUTE}/prompts/opus-r1.md",
    f"{ROUTE}/prompts/opus-r2.md",
    f"{ROUTE}/prompts/impl-r1.md",
    f"{ROUTE}/prompts/impl-r2.md",
    f"{ROUTE}/prompts/impl-r3.md",
    f"{ROUTE}/prompts/impl-r4.md",
    f"{ROUTE}/prompts/impl-r5.md",
    f"{ROUTE}/sol-r5-out.md",
    f"{ROUTE}/opus-r1-out.md",
    f"{ROUTE}/opus-r2-out.md",
    f"{ROUTE}/impl-r1-out.md",
    f"{ROUTE}/impl-r2-out.md",
    f"{ROUTE}/impl-r3-out.md",
    f"{ROUTE}/impl-r4-out.md",
    f"{ROUTE}/impl-r5-out.md",
    f"{ROUTE}/codex-review-out.md",
}
ALLOWED = {
    "skills/audit/scripts/codegraph-probe.sh",
    "tests/test_codegraph_probe.py",
    "tests/test_scaffold.py",
    "tests/test_v013_contracts.py",
    "tests/test_v0131_docs_contracts.py",
    "tests/test_v015_contracts.py",
    "tests/test_release_handoff.py",
    "skills/audit/SKILL.md",
    "skills/audit/references/config-schema.md",
    "skills/audit/references/engine-shas.json",
    "README.md",
    "docs/ADOPTION.md",
    "docs/ADOPTION.ja.md",
    ".claude-plugin/plugin.json",
} | REQUIRED_ROUTE | OPTIONAL_ROUTE


def run(root, args, **kwargs):
    return subprocess.run(args, cwd=root, capture_output=True, **kwargs)


def test_names(text):
    return set(re.findall(r"^    def (test_[A-Za-z0-9_]+)\(", text, re.MULTILINE))


def semver(value):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(value)
    return tuple(int(part) for part in match.groups())


def status_paths(root):
    proc = run(root, ["git", "status", "--porcelain=v2", "-z",
                      "--untracked-files=all"])
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace"))
    records = proc.stdout.decode("utf-8", "surrogateescape").split("\0")
    paths = set()
    index = 0
    while index < len(records):
        record = records[index]
        if not record:
            index += 1
            continue
        if record.startswith("1 "):
            paths.add(record.split(" ", 8)[8])
        elif record.startswith("2 "):
            paths.add(record.split(" ", 9)[9])
            index += 1
            if index < len(records) and records[index]:
                paths.add(records[index])
        elif record.startswith("u "):
            paths.add(record.rsplit(" ", 1)[1])
        elif record.startswith("? "):
            paths.add(record[2:])
        index += 1
    return paths


def diff_paths(root, base):
    proc = run(root, ["git", "diff", "--name-status", "-z", "-M", "-C",
                      f"{base}...HEAD"])
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace"))
    records = proc.stdout.decode("utf-8", "surrogateescape").split("\0")
    paths = set()
    index = 0
    while index < len(records):
        status = records[index]
        if not status:
            index += 1
            continue
        if status[0] in "RC":
            if index + 2 < len(records):
                paths.update((records[index + 1], records[index + 2]))
            index += 3
        else:
            if index + 1 < len(records):
                paths.add(records[index + 1])
            index += 2
    return paths


def git_show(root, base, path):
    proc = run(root, ["git", "show", f"{base}:{path}"], text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    return proc.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=os.getcwd())
    parser.add_argument("--base", default="e1c0b19")
    parser.add_argument("--only", help="comma-separated gate IDs, for example G2,G8")
    args = parser.parse_args()
    gate_ids = {f"G{number}" for number in range(1, 13)}
    selected = gate_ids
    if args.only is not None:
        requested = args.only.split(",")
        invalid = [gate_id for gate_id in requested
                   if gate_id not in gate_ids]
        if invalid:
            parser.error("--only contains unknown gate ID(s): " + ",".join(invalid))
        selected = set(requested)
    root = Path(args.repo_root).resolve()
    failures = []

    def wanted(name):
        return name in selected

    def result(name, ok, detail):
        print(f"{name}: {'PASS' if ok else 'FAIL'} {detail}")
        if not ok:
            failures.append(name)

    if wanted("G1"):
        suite = run(root, [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                    text=True)
        ran_match = re.search(r"Ran (\d+) tests", suite.stderr)
        ran = int(ran_match.group(1)) if ran_match else -1
        skip_match = re.search(r"skipped=(\d+)", suite.stderr)
        skipped = int(skip_match.group(1)) if skip_match else 0
        result("G1", suite.returncode == 0 and ran >= 655 and skipped == 0,
               f"returncode={suite.returncode} Ran {ran} tests skipped={skipped}")
        if suite.returncode:
            print(suite.stderr.rstrip())

    probe_path = "tests/test_codegraph_probe.py"
    if wanted("G2"):
        probe_text = (root / probe_path).read_text(encoding="utf-8")
        probe_names = test_names(probe_text)
        base_probe_names = test_names(git_show(root, args.base, probe_path))
        missing_probe = sorted(base_probe_names - probe_names)
        result("G2", len(probe_names) >= 38 and not missing_probe,
               f"methods={len(probe_names)} base_methods={len(base_probe_names)} missing={missing_probe}")

    handoff_test_path = "tests/test_release_handoff.py"
    if wanted("G3"):
        handoff_test_text = (root / handoff_test_path).read_text(encoding="utf-8")
        handoff_names = test_names(handoff_test_text)
        base_handoff_names = test_names(git_show(root, args.base, handoff_test_path))
        rename_map = {
            "test_close_calls_target_only_issue_56": "test_close_calls_target_only_issue_65",
            "test_release_notes_close_directive_and_issue_59_continuation":
                "test_release_notes_close_directive_and_open_issue_continuation",
        }
        expected_handoff = {rename_map.get(name, name) for name in base_handoff_names} | {
            "test_issue_66_open_allows_publication_and_remains_open",
            "test_issue_66_not_open_stops_before_publication",
            "test_no_v0150_residue_in_handoff",
            "test_destination_equal_to_root_stops_before_publication",
        }
        missing_handoff = sorted(expected_handoff - handoff_names)
        result("G3", len(handoff_names) >= 28 and not missing_handoff,
               f"methods={len(handoff_names)} expected={len(expected_handoff)} missing={missing_handoff}")

    if wanted("G4"):
        residue_files = ["README.md", "docs/ADOPTION.md", "docs/ADOPTION.ja.md",
                         "skills/audit/SKILL.md",
                         "skills/audit/references/config-schema.md"]
        old_terms = ["not model-invocable", "user-invocation-only",
                     "モデルから起動できない", "モデルからは起動", "ユーザー実行のみ"]
        residue_counts = {term: sum((root / path).read_text(encoding="utf-8").count(term)
                                    for path in residue_files)
                          for term in old_terms}
        result("G4", all(count == 0 for count in residue_counts.values()),
               "counts=" + json.dumps(residue_counts, ensure_ascii=False, sort_keys=True))

    if wanted("G5"):
        plugin_version = json.loads((root / ".claude-plugin/plugin.json").read_text())["version"]
        shas = json.loads((root / "skills/audit/references/engine-shas.json").read_text())
        sha_version = max(shas, key=semver)
        adoption_versions = []
        for path in ("docs/ADOPTION.md", "docs/ADOPTION.ja.md"):
            matches = re.findall(r"^claude plugin list\s+# .* Version (\d+\.\d+\.\d+)\s+Scope:",
                                 (root / path).read_text(encoding="utf-8"), re.MULTILINE)
            adoption_versions.append(matches[0] if len(matches) == 1 else f"matches:{len(matches)}")
        with __import__("tempfile").TemporaryDirectory() as temp_repo:
            scaffold = run(root, [sys.executable, "skills/audit/scripts/scaffold.py",
                                  "--repo-root", temp_repo, "--harness", "--dry-run"],
                           text=True)
        try:
            stamp_version = json.loads(scaffold.stdout)["stampVersion"]
        except Exception:
            stamp_version = "invalid"
        versions = [plugin_version, sha_version, *adoption_versions, stamp_version]
        result("G5", versions == ["0.15.1"] * 5,
               f"plugin={plugin_version} shas={sha_version} adoption={adoption_versions[0]} adoption_ja={adoption_versions[1]} stamp={stamp_version}")

    if wanted("G6"):
        indexed = run(root, ["git", "ls-files", "-s", "--", HANDOFF], text=True)
        index_lines = [line for line in indexed.stdout.splitlines() if line]
        index_mode = index_lines[0].split()[0] if len(index_lines) == 1 else "missing"
        executable = os.access(root / HANDOFF, os.X_OK)
        result("G6", len(index_lines) == 1 and index_mode == "100755" and executable,
               f"index_lines={len(index_lines)} mode={index_mode} executable={executable}")

    if wanted("G7"):
        handoff_body = (root / HANDOFF).read_text(encoding="utf-8")
        handoff_residue = {term: handoff_body.count(term)
                           for term in ("v0.15.0", "#56", "webExtract", "codexReview")}
        result("G7", all(count == 0 for count in handoff_residue.values()),
               "counts=" + json.dumps(handoff_residue, sort_keys=True))

    if wanted("G8"):
        changed = diff_paths(root, args.base) | status_paths(root)
        outside = sorted(changed - ALLOWED)
        result("G8", not outside,
               f"changed={len(changed)} outside={len(outside)} paths={outside}")

    if wanted("G9"):
        shell = run(root, ["bash", "-n", "skills/audit/scripts/codegraph-probe.sh"],
                    text=True)
        result("G9", shell.returncode == 0,
               f"returncode={shell.returncode} stderr={shell.stderr.strip()!r}")

    if wanted("G10"):
        tracked_proc = run(root, ["git", "ls-files"], text=True)
        tracked = set(tracked_proc.stdout.splitlines())
        missing_required = sorted(REQUIRED_ROUTE - tracked)
        optional_present = {path for path in OPTIONAL_ROUTE if (root / path).exists()}
        missing_optional = sorted(optional_present - tracked)
        tracked_in_route = {path for path in tracked if path.startswith(ROUTE + "/")}
        unexpected_route = sorted(tracked_in_route - REQUIRED_ROUTE - OPTIONAL_ROUTE)
        result("G10", not missing_required and not missing_optional and not unexpected_route,
               f"required_missing={len(missing_required)} optional_present={len(optional_present)} optional_missing={len(missing_optional)} unexpected={len(unexpected_route)} missing={missing_required + missing_optional} unexpected_paths={unexpected_route}")

    if wanted("G11"):
        line_specs = {
            "skills/audit/SKILL.md": {3, 216, 217, 218, 560, 561, 562, 563, 778},
            "skills/audit/references/config-schema.md": {280, 281, 282},
        }
        line_violations = []
        skill_current = None
        skill_old = None
        for path, allowed_lines in line_specs.items():
            old_lines = git_show(root, args.base, path).splitlines()
            current_lines = (root / path).read_text(encoding="utf-8").splitlines()
            if path == "skills/audit/SKILL.md":
                skill_current, skill_old = current_lines, old_lines
            if len(old_lines) != len(current_lines):
                line_violations.append(f"{path}:line-count:{len(old_lines)}->{len(current_lines)}")
            for number, (old, current) in enumerate(zip(old_lines, current_lines), 1):
                if number not in allowed_lines and old != current:
                    line_violations.append(f"{path}:{number}")
        expected_line3 = skill_old[2].replace("(not model-invocable)",
                                                   "(not started by the audit itself yet)")
        expected_line778 = ("- `CODE_REVIEW_STATE=not-model-invocable` → `💡 code-review: not run — "
                            "the audit does not start /code-review itself yet (tracked in #66); "
                            "run it when offered in an interactive audit, or before the audit, if you "
                            "want this layer included. (expected)`")
        if skill_current[2] != expected_line3:
            line_violations.append("skills/audit/SKILL.md:3:exact")
        if skill_current[777] != expected_line778:
            line_violations.append("skills/audit/SKILL.md:778:exact")
        result("G11", not line_violations,
               f"violations={len(line_violations)} paths={line_violations}")

    if wanted("G12"):
        empty_tests = []
        for path in (probe_path, handoff_test_path):
            tree = ast.parse((root / path).read_text(encoding="utf-8"), filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                    continue
                body = list(node.body)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                    body = body[1:]
                empty = not body or all(
                    isinstance(item, ast.Pass)
                    or (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant)
                        and item.value.value is Ellipsis)
                    for item in body)
                if empty:
                    empty_tests.append(f"{path}:{node.name}")
        result("G12", not empty_tests,
               f"empty_tests={len(empty_tests)} methods={empty_tests}")

    if failures:
        print("GATE FAIL")
        return 1
    print("GATE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Import a constrained audit-scope.json into doc-audit.json deterministically.

DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT is test-only and must be unset in production.
"""

import argparse
import collections
import datetime
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

from docaudit_paths import (RESERVED_DIRECTORY_NAMES, corpus_settings,
                            is_excluded_doc, list_doc_files, matches_glob,
                            validate_repo_path)


CATCH_ALL = {"*", "**", "**/*"}
HEX_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
TAGGED_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FAULT_ENV = "DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT"


class JSONObject(list):
    """A JSON object retaining pairs so duplicate keys are observable."""


class LockBusy(Exception):
    """The run lock could not be acquired safely."""


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def parse_json(raw, label, errors):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=JSONObject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return None


def normal_object(value):
    if isinstance(value, JSONObject):
        return {key: normal_object(item) for key, item in value}
    if isinstance(value, list):
        return [normal_object(item) for item in value]
    return value


def config_object(raw, errors):
    if raw is None:
        return {}
    parsed = parse_json(raw, "config", errors)
    if parsed is not None and not isinstance(parsed, JSONObject):
        errors.append("config top level must be an object")
        return {}
    return normal_object(parsed or [])


def scope_rules(raw, errors):
    parsed = parse_json(raw, "scope", errors)
    if parsed is None:
        return []
    if not isinstance(parsed, JSONObject):
        errors.append("scope top level must be an object")
        return []
    seen = set()
    rules = []
    for key, value in parsed:
        if key in seen:
            errors.append(f"duplicate scope rule: {key}")
        seen.add(key)
        rules.append((key, value))
    return rules


def convert(pattern, errors):
    if not isinstance(pattern, str) or not pattern:
        errors.append(f"invalid scope rule: {pattern!r}")
        return None
    if pattern in CATCH_ALL:
        errors.append(f"bare catch-all is not allowed: {pattern}")
        return None
    if "\r" in pattern or "\n" in pattern:
        errors.append(f"CR/LF in scope rule: {pattern!r}")
        return None
    if pattern.startswith("./") or pattern.endswith("/"):
        errors.append(f"unsupported fnmatch syntax: {pattern}")
        return None
    if "?" in pattern or "[" in pattern:
        errors.append(f"unsupported fnmatch syntax: {pattern}")
        return None
    converted = re.sub(r"\*+", "**", pattern)
    if "**/" in converted:
        errors.append(f"unsupported slash after wildcard: {pattern}")
        return None
    if converted in CATCH_ALL:
        errors.append(f"bare catch-all is not allowed: {pattern}")
        return None
    return converted


def convert_rules(rules, errors):
    return [(original, value, convert(original, errors))
            for original, value in rules]


def metadata(config, repo, errors, path_validator=None):
    if "auditScope" not in config:
        return None
    value = config["auditScope"]
    if not isinstance(value, dict):
        errors.append("auditScope must be an object")
        return None
    path = value.get("path")
    sha = value.get("sha256")
    rules = value.get("rules")
    imported = value.get("importedAt")
    try:
        if path_validator is None:
            validate_repo_path(repo, path, must_exist=False)
        else:
            path_validator(path)
    except ValueError as exc:
        errors.append(f"auditScope.path invalid: {exc}")
    if not isinstance(sha, str) or not HEX_SHA_RE.fullmatch(sha):
        errors.append("auditScope.sha256 invalid")
    if isinstance(rules, bool) or not isinstance(rules, int) or rules < 0:
        errors.append("auditScope.rules invalid")
    if not isinstance(imported, str):
        errors.append("auditScope.importedAt invalid")
    return value


def report_regex(config):
    """Return the shared report-path regex, compiled for corpus filtering."""
    value = config.get("reportPath")
    globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
    if not isinstance(value, str) or not value.endswith(".md"):
        return None
    sample = value.replace("<YYYY-MM-DD>", "2000-01-01").replace("[_NN]", "_01")
    if not any(matches_glob(sample, item) for item in globs if isinstance(item, str)):
        return None
    _directory, name = os.path.split(value)
    date_marker = "<YYYY-MM-DD>"
    suffix_marker = "[_NN]"
    if date_marker not in name:
        return None
    prefix = name.split(date_marker, 1)[0]
    if not prefix:
        return None
    suffix_at = None
    if suffix_marker not in value:
        suffix_at = len(value) - len(name) + name.find(date_marker) + len(date_marker)
    out = []
    index = 0
    while index < len(value):
        if value.startswith(date_marker, index):
            out.append("[0-9]{4}-[0-9]{2}-[0-9]{2}")
            index += len(date_marker)
            if suffix_at == index:
                out.append("(_[0-9]{2,})?")
        elif value.startswith(suffix_marker, index):
            out.append("(_[0-9]{2,})?")
            index += len(suffix_marker)
        else:
            out.append(re.escape(value[index]))
            index += 1
    return re.compile("^" + "".join(out) + "$")


def validate_rule_shapes(converted_rules, errors):
    """Validate scope values without consulting a config or the filesystem."""
    for changed, raw_value, _converted in converted_rules:
        if isinstance(raw_value, JSONObject):
            keys = [key for key, _value in raw_value]
            duplicates = sorted({key for key in keys if keys.count(key) > 1})
            for key in duplicates:
                errors.append(f"duplicate key in scope value {changed}: {key}")
            if list(raw_value) != [("impact", "none")]:
                errors.append(f"invalid scope value: {changed}")
            continue
        if not isinstance(raw_value, list) or not raw_value:
            errors.append(f"scope impacts must be a non-empty string array: {changed}")
            continue
        for target in raw_value:
            if not isinstance(target, str):
                errors.append(f"scope impact is not a string: {changed}")
            elif "\r" in target or "\n" in target:
                errors.append(f"CR/LF in scope impact: {changed}")


def _validate_rules_core(converted_rules, errors, *, doc_globs, corpus,
                          normalize_path, is_excluded, report_rx):
    translated = []
    skipped = []
    for changed, raw_value, converted in converted_rules:
        if isinstance(raw_value, JSONObject):
            keys = [key for key, _value in raw_value]
            duplicates = sorted({key for key in keys if keys.count(key) > 1})
            for key in duplicates:
                errors.append(f"duplicate key in scope value {changed}: {key}")
            if list(raw_value) == [("impact", "none")]:
                if converted is not None:
                    skipped.append(changed)
                continue
            errors.append(f"invalid scope value: {changed}")
            continue
        value = normal_object(raw_value)
        if not isinstance(value, list) or not value:
            errors.append(f"scope impacts must be a non-empty string array: {changed}")
            continue
        impacts = []
        for target in value:
            if not isinstance(target, str):
                errors.append(f"scope impact is not a string: {changed}")
                continue
            if "\r" in target or "\n" in target:
                errors.append(f"CR/LF in scope impact: {changed}")
                continue
            try:
                normalized = normalize_path(target)
            except ValueError as exc:
                errors.append(f"invalid scope impact {changed}: {exc}")
                continue
            outside_corpus = (f"scope impact outside document corpus ({normalized}); "
                              "extend docGlobs and rerun")
            if not any(matches_glob(normalized, glob) for glob in doc_globs):
                errors.append(f"scope impact outside docGlobs ({normalized}); extend docGlobs and rerun")
                continue
            if normalized not in corpus and is_excluded(normalized):
                errors.append("scope impact excluded from corpus (excludeDocGlobs or Git exclude rules): "
                              f"{normalized}; remove it from audit-scope.json and re-import; "
                              "if it is the last target, remove the whole rule")
                continue
            if normalized not in corpus:
                errors.append(outside_corpus)
                continue
            if report_rx and report_rx.fullmatch(normalized):
                errors.append(outside_corpus)
                continue
            impacts.append(normalized)
        if converted is not None and impacts:
            translated.append({"changed": converted, "impacts": impacts, "from": changed})
    return translated, skipped


def validate_rules(converted_rules, repo, config, doc_globs, errors):
    exclude_globs, respect_gitignore = corpus_settings(config)
    corpus = set(list_doc_files(repo, doc_globs, exclude_globs=exclude_globs,
                                respect_gitignore=respect_gitignore))
    report_rx = (None if config.get("auditReportsInCorpus") is True
                 else report_regex(config))
    return _validate_rules_core(
        converted_rules, errors, doc_globs=doc_globs, corpus=corpus,
        normalize_path=lambda target: validate_repo_path(repo, target),
        is_excluded=lambda path: is_excluded_doc(
            repo, path, exclude_globs, respect_gitignore), report_rx=report_rx)


def git_paths(repo, errors):
    paths = set()
    commands = (
        ("git", "ls-files", "-z"),
        ("git", "ls-files", "-z", "--others", "--exclude-standard"),
    )
    for command in commands:
        try:
            completed = subprocess.run(command, cwd=repo, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"git enumeration failed: {exc}")
            return []
        for item in completed.stdout.decode("utf-8", "surrogateescape").split("\0"):
            if not item:
                continue
            paths.add(item)
            if "\r" in item or "\n" in item:
                errors.append(f"unsupported filename: {item!r}")
    if not paths:
        errors.append("git enumeration returned zero paths")
    return sorted(paths)


def lexical_repo_path(repo, repo_apparent, path):
    """Normalize a repository path without consulting working-tree entries."""
    if not isinstance(path, str) or not path:
        raise ValueError("path must be a non-empty repository-relative string")
    if "\r" in path or "\n" in path:
        raise ValueError("path contains CR/LF")
    path = path.replace("\\", "/")
    if os.path.isabs(path):
        if any(component in ("", ".", "..") for component in path.split("/")[1:]):
            raise ValueError(
                'absolute path must not contain empty, "." or ".." components'
            )
        for root in (repo_apparent.replace("\\", "/"), repo.replace("\\", "/")):
            if path.startswith(root + "/"):
                path = path[len(root) + 1:]
                break
        else:
            raise ValueError("absolute path is outside repo")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path contains an empty, dot, or parent component")
    return "/".join(parts)


def index_snapshot(repo, errors):
    """Return all entries and the accepted regular-blob path/OID snapshot."""
    try:
        completed = subprocess.run(
            ["git", "-C", repo, "ls-files", "--stage", "-z"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"git enumeration failed: {exc}")
        return {}, {}
    entries = collections.defaultdict(list)
    for record in completed.stdout.split(b"\0"):
        if not record:
            continue
        header, separator, raw_path = record.partition(b"\t")
        path = raw_path.decode("utf-8", "surrogateescape")
        if not separator:
            errors.append("git index entry is malformed")
            continue
        if "\r" in path or "\n" in path:
            errors.append(f"unsupported filename: {path!r}")
        try:
            mode, oid, stage = header.decode("ascii").split(" ")
        except (UnicodeDecodeError, ValueError):
            errors.append(f"git index entry is malformed: {path!r}")
            continue
        entries[path].append((mode, oid, stage))
    accepted = {}
    for path, values in entries.items():
        if (len(values) == 1 and values[0][2] == "0"
                and values[0][0] in ("100644", "100755")):
            accepted[path] = values[0][1]
    return dict(entries), accepted


def index_blob(repo, oid, label, errors):
    try:
        completed = subprocess.run(
            ["git", "-C", repo, "cat-file", "blob", oid],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"{label} blob read failed: {exc}")
        return None
    return completed.stdout


def index_corpus(paths, doc_globs, exclude_globs):
    found = set()
    for path in paths:
        directories = path.split("/")[:-1]
        if any(name in RESERVED_DIRECTORY_NAMES for name in directories):
            continue
        if not any(matches_glob(path, glob) for glob in doc_globs):
            continue
        if any(matches_glob(path, glob) for glob in exclude_globs):
            continue
        found.add(path)
    return found


def validate_rules_from_index(converted_rules, paths, config, doc_globs,
                              repo, repo_apparent, errors):
    exclude_globs, _respect_gitignore = corpus_settings(config)
    corpus = index_corpus(paths, doc_globs, exclude_globs)
    report_rx = (None if config.get("auditReportsInCorpus") is True
                 else report_regex(config))
    return _validate_rules_core(
        converted_rules, errors, doc_globs=doc_globs, corpus=corpus,
        normalize_path=lambda target: lexical_repo_path(
            repo, repo_apparent, target),
        is_excluded=lambda path: any(
            matches_glob(path, glob) for glob in exclude_globs), report_rx=report_rx)


def equivalence(converted_rules, paths, errors):
    for original, _value, converted in converted_rules:
        if converted is None:
            continue
        fnmatch_paths = {path for path in paths if fnmatch.fnmatchcase(path, original)}
        docaudit_paths = {path for path in paths if matches_glob(path, converted)}
        if fnmatch_paths != docaudit_paths:
            examples = sorted(fnmatch_paths ^ docaudit_paths)[:3]
            errors.append(f"glob equivalence mismatch {original}: {examples}")


def result(state, rules, translated, skipped, errors, checked,
           config_raw, scope_raw, missing=(), extra=(), scope_path=None,
           recorded_scope_path=None):
    output = {
        "state": state,
        "rules": len(rules),
        "translated": translated,
        "skippedNoImpact": skipped,
        "errors": errors,
        "equivalenceChecked": checked,
        "configSha": digest(config_raw) if config_raw is not None else "none",
        "scopePath": scope_path,
        "scopeSha": digest(scope_raw) if scope_raw is not None else None,
        "diff": {"missing": list(missing), "extra": list(extra)},
    }
    if recorded_scope_path is not None:
        output["recordedScopePath"] = recorded_scope_path
    return output


def emit(output, json_output):
    if json_output:
        print(json.dumps(output, ensure_ascii=False))
    elif output["errors"]:
        print("\n".join(output["errors"]))
    else:
        print(f"audit scope: {output['state']}")


def compare(config, translated):
    wanted = collections.Counter((entry["changed"], tuple(entry["impacts"]))
                                 for entry in translated)
    existing = collections.Counter(
        (entry.get("changed"), tuple(entry.get("impacts", [])))
        for entry in config.get("impactMap", [])
        if isinstance(entry, dict) and entry.get("source") == "audit-scope")
    return list((wanted - existing).elements()), list((existing - wanted).elements())


def safe_path(repo, repo_apparent, path, errors, label):
    if os.path.isabs(path):
        if any(component in ("", ".", "..") for component in path.split("/")[1:]):
            errors.append(
                f'{label} invalid: absolute path must not contain empty, "." or ".." components'
            )
            return None
        for root in (repo_apparent, repo):
            if path == root:
                rel = ""
            elif path.startswith(root + "/"):
                rel = path[len(root) + 1:]
            else:
                continue
            try:
                return validate_repo_path(repo, rel, must_exist=False)
            except ValueError as exc:
                errors.append(f"{label} invalid: {exc}")
                return None
        errors.append(f"{label} invalid: absolute path is outside repo")
        return None
    try:
        return validate_repo_path(repo, path, must_exist=False)
    except ValueError as exc:
        errors.append(f"{label} invalid: {exc}")
        return None


def check_from_index(args, repo, repo_apparent):
    errors = []
    entries, accepted = index_snapshot(repo, errors)
    try:
        config_rel = lexical_repo_path(repo, repo_apparent, args.config)
    except ValueError as exc:
        errors.append(f"config invalid: {exc}")
        config_rel = None
    config_raw = None
    if config_rel is not None:
        oid = accepted.get(config_rel)
        if oid is None:
            errors.append(f"config not in index: {config_rel}")
        else:
            config_raw = index_blob(repo, oid, "config", errors)
    if (args.expect_config_sha is not None
            and (config_raw is None or args.expect_config_sha != digest(config_raw))):
        errors.append("config SHA mismatch")
    config = config_object(config_raw, errors)
    try:
        corpus_settings(config)
    except ValueError as exc:
        errors.append(str(exc))
    configured_scope = config.get("auditScope")
    if args.scope is not None:
        scope_argument = args.scope
    elif (isinstance(configured_scope, dict)
          and isinstance(configured_scope.get("path"), str)):
        scope_argument = configured_scope["path"]
    else:
        scope_argument = ".claude/audit-scope.json"
    try:
        scope_rel = lexical_repo_path(repo, repo_apparent, scope_argument)
    except ValueError as exc:
        errors.append(f"scope invalid: {exc}")
        scope_rel = None
    audit_scope = metadata(
        config, repo, errors,
        path_validator=lambda path: lexical_repo_path(repo, repo_apparent, path))
    scope_raw = None
    scope_indexed = scope_rel in entries if scope_rel is not None else False
    scope_accepted = scope_rel in accepted if scope_rel is not None else False
    if scope_indexed and not scope_accepted:
        errors.append(f"scope not a regular blob in index: {scope_rel}")
    elif scope_accepted:
        scope_raw = index_blob(repo, accepted[scope_rel], "scope", errors)
    if (args.expect_scope_sha is not None
            and (scope_raw is None or args.expect_scope_sha != digest(scope_raw))):
        errors.append("scope SHA mismatch")
    if errors:
        output = result("error", [], [], [], errors, len(accepted),
                        config_raw, scope_raw, scope_path=scope_rel)
        emit(output, args.json)
        return 1
    if not scope_indexed:
        state = "absent" if audit_scope is None else "drift"
        output = result(state, [], [], [], [], len(accepted),
                        config_raw, None, scope_path=scope_rel)
        emit(output, args.json)
        return 0 if state == "absent" else 2
    rules = scope_rules(scope_raw, errors)
    converted_rules = convert_rules(rules, errors)
    default_globs = args.doc_glob or ["docs/**/*.md", "*.md"]
    doc_globs = config.get("docGlobs", default_globs)
    if (not isinstance(doc_globs, list)
            or not all(isinstance(item, str) for item in doc_globs)):
        errors.append("docGlobs must be a string array")
        doc_globs = []
    translated, skipped = validate_rules_from_index(
        converted_rules, set(accepted), config, doc_globs,
        repo, repo_apparent, errors)
    equivalence(converted_rules, set(accepted), errors)
    if errors:
        output = result("error", rules, translated, skipped, errors,
                        len(accepted), config_raw, scope_raw,
                        scope_path=scope_rel)
        emit(output, args.json)
        return 1
    missing, extra = compare(config, translated)
    recorded_scope_path = None
    if audit_scope is None:
        state = "not-imported"
    else:
        scope_matches = audit_scope.get("sha256") == digest(scope_raw)[len("sha256:"):]
        path_matches = audit_scope.get("path") == scope_rel
        if not missing and not extra and scope_matches and path_matches:
            state = "in-sync"
        elif not missing and not extra and scope_matches:
            state = "path-mismatch"
            recorded_scope_path = audit_scope.get("path")
        else:
            state = "drift"
    output = result(state, rules, translated, skipped, [], len(accepted),
                    config_raw, scope_raw, missing, extra,
                    scope_path=scope_rel,
                    recorded_scope_path=recorded_scope_path)
    emit(output, args.json)
    if state in ("in-sync", "absent"):
        return 0
    return 4 if state == "path-mismatch" else 2


def remove_owned_lock(fd, lock_path):
    try:
        fd_inode = os.fstat(fd).st_ino
        path_inode = os.lstat(lock_path).st_ino
    except FileNotFoundError:
        return
    if fd_inode == path_inode:
        os.unlink(lock_path)


def acquire(repo, fault):
    run_base = os.path.join(repo, ".claude", "state", "docaudit-run")
    components = (
        os.path.join(repo, ".claude"),
        os.path.join(repo, ".claude", "state"),
        run_base,
    )
    for component in components:
        if os.path.lexists(component) and os.path.islink(component):
            raise ValueError(f"run-base symlink: {component}")
        if not os.path.exists(component):
            os.mkdir(component, 0o700)
    lock_path = os.path.join(run_base, "lock")
    flags = os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_RDWR
    try:
        fd = os.open(lock_path, flags, 0o600)
    except FileExistsError as exc:
        raise LockBusy("run in progress") from exc
    try:
        if fault == "unlink-before-flock":
            os.unlink(lock_path)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            path_inode = os.lstat(lock_path).st_ino
        except FileNotFoundError as exc:
            raise LockBusy("run in progress: lock inode changed") from exc
        if os.fstat(fd).st_ino != path_inode:
            raise LockBusy("run in progress: lock inode changed")
        holder = {
            "owner": "import-audit-scope",
            "runid": None,
            "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        os.write(fd, (json.dumps(holder, sort_keys=True) + "\n").encode("utf-8"))
        os.fsync(fd)
        if fault.startswith("hold-lock:"):
            release_path = fault.split(":", 1)[1]
            deadline = time.monotonic() + 30
            while not os.path.exists(release_path):
                if time.monotonic() >= deadline:
                    raise OSError("hold-lock timed out")
                time.sleep(0.05)
        return fd, lock_path
    except Exception:
        remove_owned_lock(fd, lock_path)
        os.close(fd)
        raise


def release(fd, lock_path):
    if fd is None:
        return
    try:
        remove_owned_lock(fd, lock_path)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def expected_arguments_valid(args, errors):
    if not args.write:
        return
    if not args.expect_scope_sha or not TAGGED_SHA_RE.fullmatch(args.expect_scope_sha):
        errors.append("--write requires --expect-scope-sha sha256:<64hex>")
    if args.base_config == "-":
        if (not args.expect_base_config_sha
                or not TAGGED_SHA_RE.fullmatch(args.expect_base_config_sha)):
            errors.append("--base-config - requires --expect-base-config-sha sha256:<64hex>")
        if args.expect_config_sha is not None:
            errors.append("--expect-config-sha cannot be used with --base-config -")
    else:
        if args.expect_base_config_sha is not None:
            errors.append("--expect-base-config-sha requires --base-config -")
        if (args.expect_config_sha != "none"
                and (not args.expect_config_sha
                     or not TAGGED_SHA_RE.fullmatch(args.expect_config_sha))):
            errors.append("--write requires --expect-config-sha sha256:<64hex>|none")


def prepare_scope_for_config(scope_bytes, config, repo, errors):
    rules = scope_rules(scope_bytes, errors)
    converted_rules = convert_rules(rules, errors)
    if errors:
        return rules, converted_rules, [], []
    doc_globs = config.get("docGlobs", ["docs/**/*.md", "*.md"])
    if (not isinstance(doc_globs, list)
            or not all(isinstance(item, str) for item in doc_globs)):
        errors.append("docGlobs must be a string array")
        return rules, converted_rules, [], []
    translated, skipped = validate_rules(
        converted_rules, repo, config, doc_globs, errors)
    return rules, converted_rules, translated, skipped


def write_config(args, repo, config_path, scope_path, scope_rel, errors):
    fault = os.environ.get(FAULT_ENV, "")
    valid_fault = (not fault or fault in {
        "before-replace", "after-replace", "unlink-before-flock"}
        or fault.startswith("hold-lock:"))
    if not valid_fault:
        print(f"unknown {FAULT_ENV} value: {fault}", file=sys.stderr)
        return 1
    fd = None
    lock_path = None
    try:
        fd, lock_path = acquire(repo, fault)
        fresh_config = read_bytes(config_path) if os.path.isfile(config_path) else None
        base_config = None
        if args.base_config == "-":
            base_config = sys.stdin.buffer.read()
        if fresh_config is None and base_config is None:
            print("config absent: use --base-config - with --expect-base-config-sha",
                  file=sys.stderr)
            return 1
        if base_config is not None and fresh_config is not None:
            print("config already exists", file=sys.stderr)
            return 1
        current_scope = read_bytes(scope_path)
        if args.expect_scope_sha != digest(current_scope):
            print("scope SHA mismatch", file=sys.stderr)
            return 4
        if base_config is not None:
            if args.expect_base_config_sha != digest(base_config):
                print("base config SHA mismatch", file=sys.stderr)
                return 4
            config_bytes = base_config
        else:
            current_config_sha = digest(fresh_config) if fresh_config is not None else "none"
            if args.expect_config_sha != current_config_sha:
                print("config SHA mismatch", file=sys.stderr)
                return 4
            config_bytes = fresh_config
        final = config_object(config_bytes, errors)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        rules, _converted, translated, _skipped = prepare_scope_for_config(
            current_scope, final, repo, errors)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        impact_map = final.get("impactMap", [])
        if not isinstance(impact_map, list):
            errors.append("impactMap must be an array")
            return 1
        final["impactMap"] = [
            entry for entry in impact_map
            if not (isinstance(entry, dict) and entry.get("source") == "audit-scope")
        ]
        final["impactMap"].extend({
            "changed": entry["changed"],
            "impacts": entry["impacts"],
            "source": "audit-scope",
            "note": f"generated from {scope_rel}",
        } for entry in translated)
        final["auditScope"] = {
            "path": scope_rel,
            "sha256": digest(current_scope)[len("sha256:"):],
            "importedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "rules": len(rules),
        }
        directory = os.path.dirname(config_path)
        os.makedirs(directory, exist_ok=True)
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False)
        temp_path = temp.name
        try:
            json.dump(final, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
            temp.close()
            if fault == "before-replace":
                raise OSError("injected failure before replace")
            os.replace(temp_path, config_path)
            if fault == "after-replace":
                raise OSError("injected failure after replace")
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if not temp.closed:
                temp.close()
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except LockBusy as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        print(f"import-audit-scope: {exc}", file=sys.stderr)
        return 1
    finally:
        release(fd, lock_path)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=os.getcwd())
    parser.add_argument("--config", default=".claude/doc-audit.json")
    parser.add_argument("--scope")
    parser.add_argument("--doc-glob", action="append", default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--from-index", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--expect-config-sha")
    parser.add_argument("--expect-scope-sha")
    parser.add_argument("--base-config", choices=["-"])
    parser.add_argument("--expect-base-config-sha")
    args = parser.parse_args()
    if args.from_index and args.write:
        parser.error("--from-index cannot be used with --write")
    args.check = not args.write
    repo_apparent = os.path.abspath(args.repo_root)
    repo = os.path.realpath(args.repo_root)
    if args.from_index:
        return check_from_index(args, repo, repo_apparent)
    errors = []
    config_rel = safe_path(repo, repo_apparent, args.config, errors, "config")
    expected_arguments_valid(args, errors)
    config_path = os.path.join(repo, config_rel) if config_rel else ""
    config_raw = None
    if config_rel and os.path.isfile(config_path):
        config_raw = read_bytes(config_path)
    if config_rel and os.path.lexists(config_path) and not os.path.isfile(config_path):
        errors.append("config path is not a regular file")
    config = config_object(config_raw, errors)
    try:
        corpus_settings(config)
    except ValueError as exc:
        errors.append(str(exc))
    configured_scope = config.get("auditScope")
    if args.scope is not None:
        scope_argument = args.scope
    elif (isinstance(configured_scope, dict)
          and isinstance(configured_scope.get("path"), str)):
        scope_argument = configured_scope["path"]
    else:
        scope_argument = ".claude/audit-scope.json"
    scope_rel = safe_path(repo, repo_apparent, scope_argument, errors, "scope")
    scope_path = os.path.join(repo, scope_rel) if scope_rel else ""
    if scope_rel and os.path.lexists(scope_path) and not os.path.isfile(scope_path):
        errors.append("scope path is not a regular file")
    audit_scope = metadata(config, repo, errors)
    scope_exists = bool(scope_rel and os.path.isfile(scope_path))
    if not scope_exists and audit_scope is None and not errors:
        output = result("absent", [], [], [], [], 0, config_raw, None,
                        scope_path=scope_rel)
        emit(output, args.json)
        return 0
    if errors:
        output = result("error", [], [], [], errors, 0, config_raw, None,
                        scope_path=scope_rel)
        emit(output, args.json)
        return 1
    if not scope_exists:
        output = result("drift", [], [], [], [], 0, config_raw, None,
                        scope_path=scope_rel)
        emit(output, args.json)
        return 2
    scope_raw = read_bytes(scope_path)
    rules = scope_rules(scope_raw, errors)
    converted_rules = convert_rules(rules, errors)
    if errors:
        output = result("error", rules, [], [], errors, 0, config_raw, scope_raw,
                        scope_path=scope_rel)
        emit(output, args.json)
        return 1
    default_globs = args.doc_glob or ["docs/**/*.md", "*.md"]
    doc_globs = config.get("docGlobs", default_globs)
    if (not isinstance(doc_globs, list)
            or not all(isinstance(item, str) for item in doc_globs)):
        errors.append("docGlobs must be a string array")
        doc_globs = []
    if args.write and args.base_config == "-":
        validate_rule_shapes(converted_rules, errors)
        translated = []
        skipped = []
    else:
        translated, skipped = validate_rules(
            converted_rules, repo, config, doc_globs, errors)
    if errors:
        output = result("error", rules, translated, skipped, errors, 0,
                        config_raw, scope_raw, scope_path=scope_rel)
        emit(output, args.json)
        return 1
    paths = git_paths(repo, errors)
    equivalence(converted_rules, paths, errors)
    if errors:
        output = result("error", rules, translated, skipped, errors, len(paths),
                        config_raw, scope_raw, scope_path=scope_rel)
        emit(output, args.json)
        return 1
    missing, extra = compare(config, translated)
    if not args.write:
        if audit_scope is None:
            state = "not-imported"
        else:
            scope_matches = audit_scope.get("sha256") == digest(scope_raw)[len("sha256:"):]
            path_matches = audit_scope.get("path") == scope_rel
            if not missing and not extra and scope_matches and path_matches:
                state = "in-sync"
            elif not missing and not extra and scope_matches:
                state = "path-mismatch"
            else:
                state = "drift"
        output = result(state, rules, translated, skipped, [], len(paths),
                        config_raw, scope_raw, missing, extra, scope_path=scope_rel,
                        recorded_scope_path=(audit_scope.get("path")
                                             if state == "path-mismatch" else None))
        emit(output, args.json)
        if state == "in-sync":
            return 0
        return 4 if state == "path-mismatch" else 2
    if config_raw is None and args.base_config is None:
        print("config absent: use --base-config - with --expect-base-config-sha",
              file=sys.stderr)
        return 1
    return write_config(args, repo, config_path, scope_path, scope_rel, errors)


if __name__ == "__main__":
    sys.exit(main())

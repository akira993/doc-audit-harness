#!/usr/bin/env python3
"""Repository-relative path validation shared by docaudit scripts."""

import json
import os
import re
import unicodedata
import subprocess


def glob_to_regex(pattern):
    out = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                if i + 2 < len(pattern) and pattern[i + 2] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(char))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_glob(path, pattern):
    return glob_to_regex(pattern).match(path.replace(os.sep, "/")) is not None


def validate_repo_path(repo_root, path, *, must_exist=True, regular_file=True):
    """Return normalized repo path or raise ValueError.

    Absolute paths, dot traversal, every symlink component, repository escapes,
    missing paths, and non-regular final files are rejected.
    """
    if not isinstance(path, str) or not path or os.path.isabs(path):
        raise ValueError("path must be a non-empty repository-relative string")
    path = path.replace("\\", "/")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path contains an empty, dot, or parent component")
    root = os.path.realpath(repo_root)
    current = root
    for part in parts:
        current = os.path.join(current, part)
        if os.path.lexists(current) and os.path.islink(current):
            raise ValueError("symlink paths are not accepted")
    resolved = os.path.realpath(current)
    try:
        if os.path.commonpath([root, resolved]) != root:
            raise ValueError("path resolves outside the repository")
    except ValueError as exc:
        raise ValueError("path resolves outside the repository") from exc
    if must_exist and not os.path.exists(current):
        raise ValueError("path does not exist")
    if must_exist and regular_file and not os.path.isfile(current):
        raise ValueError("path is not a regular file")
    return "/".join(parts)


def normalize_finding_path(repo_root, value):
    """Return a safe canonical finding path, or ``None`` if unresolved.

    A trailing line/column suffix is removed only when the path including that
    suffix is not itself a valid repository file.
    """
    if not isinstance(value, str) or not value:
        return None
    if (re.match(r"^[A-Za-z]:", value) or value.startswith(("/", "\\\\"))
            or "\\" in value or '"' in value
            or any(unicodedata.category(char) == "Cc" for char in value)
            or len(json.dumps(value, ensure_ascii=True).encode("utf-8")) > 512):
        return None
    candidate = value[2:] if value.startswith("./") else value
    try:
        return validate_repo_path(repo_root, candidate)
    except ValueError:
        stripped = re.sub(r":\d+(?::\d+)?$", "", candidate)
        if stripped == candidate:
            return None
        try:
            return validate_repo_path(repo_root, stripped)
        except ValueError:
            return None


def corpus_settings(config):
    """Return the raw corpus-filter settings, validating both public keys."""
    exclude = config.get("excludeDocGlobs", [])
    respect = config.get("respectGitignore", True)
    if not isinstance(exclude, list) or not all(isinstance(item, str) for item in exclude):
        raise ValueError("excludeDocGlobs must be a string array")
    if not isinstance(respect, bool):
        raise ValueError("respectGitignore must be a boolean")
    return exclude, respect


def _gitignored_paths(repo_root, paths, warnings, stats):
    """Return ignored untracked paths using Git's own exclude rules."""
    if not paths:
        return set()
    try:
        inside = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0
    except OSError:
        inside = False
    if not inside:
        stats["gitignoreApplied"] = False
        if warnings is not None:
            warnings.append("respectGitignore: gitignore not applied (not a git work tree)")
        return set()
    stats["gitignoreApplied"] = True
    encoded = []
    unsafe = set()
    for path in paths:
        try:
            encoded.append(path.encode("utf-8"))
        except UnicodeEncodeError:
            unsafe.add(path)
            if warnings is not None:
                warnings.append(f"document path dropped as unsafe: {path} (not UTF-8 encodable)")
    if not encoded:
        return unsafe
    try:
        proc = subprocess.run(
            ["git", "-C", repo_root, "check-ignore", "--stdin", "-z"],
            input=b"\0".join(encoded) + b"\0", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise ValueError(f"git check-ignore failed: {exc}") from exc
    if proc.returncode not in (0, 1):
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise ValueError(f"git check-ignore failed (exit {proc.returncode}): {detail}")
    return unsafe | {item.decode("utf-8") for item in proc.stdout.split(b"\0") if item}


def is_excluded_doc(repo_root, path, exclude_globs=(), respect_gitignore=False,
                    warnings=None, stats=None):
    """Whether one repository-relative document is excluded from the corpus."""
    stats = stats if stats is not None else {}
    stats.setdefault("excludedByGlobs", 0)
    stats.setdefault("excludedByGitignore", 0)
    stats.setdefault("gitignoreApplied", False)
    path = path.replace(os.sep, "/")
    if any(matches_glob(path, glob) for glob in exclude_globs):
        stats["excludedByGlobs"] += 1
        return True
    if not respect_gitignore:
        return False
    ignored = _gitignored_paths(repo_root, [path], warnings, stats)
    if path in ignored:
        stats["excludedByGitignore"] += 1
        return True
    return False


def list_doc_files(repo_root, doc_globs, warnings=None, *, exclude_globs=(),
                   respect_gitignore=False, stats=None):
    root = os.path.realpath(repo_root)
    skip = {".git", ".hg", ".svn", "node_modules", ".venv", "venv",
            "__pycache__", "dist", "build"}
    stats = stats if stats is not None else {}
    stats.setdefault("excludedByGlobs", 0)
    stats.setdefault("excludedByGitignore", 0)
    stats.setdefault("gitignoreApplied", False)
    found = []
    for dirpath, dirs, files in os.walk(root, followlinks=False):
        kept_dirs = []
        for name in dirs:
            full_dir = os.path.join(dirpath, name)
            if name in skip or os.path.exists(os.path.join(full_dir, ".git")):
                continue
            if os.path.islink(full_dir):
                if warnings is not None:
                    rel = os.path.relpath(full_dir, root).replace(os.sep, "/")
                    warnings.append(f"document directory dropped as unsafe: {rel} (symlink)")
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in files:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if not any(matches_glob(rel, glob) for glob in doc_globs):
                continue
            if any(matches_glob(rel, glob) for glob in exclude_globs):
                stats["excludedByGlobs"] += 1
                continue
            try:
                found.append(validate_repo_path(root, rel))
            except ValueError as exc:
                if warnings is not None:
                    warnings.append(f"document path dropped as unsafe: {rel} ({exc})")
                continue
    found = sorted(set(found))
    if respect_gitignore:
        ignored = _gitignored_paths(root, found, warnings, stats)
        stats["excludedByGitignore"] += len(ignored)
        found = [path for path in found if path not in ignored]
    return found

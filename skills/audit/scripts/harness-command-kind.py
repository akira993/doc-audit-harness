#!/usr/bin/env python3
"""Classify configured harness commands without executing them."""

import argparse
import json
import sys


LAYERS = ("format", "existence", "semantic")


def classify(command):
    if not isinstance(command, str) or not command.strip():
        return "invalid"
    value = command.strip()
    first = value.split(None, 1)[0]
    if first.startswith("/") and len(first) > 1 and "/" not in first[1:]:
        return "model-driven"
    if not any(char.isspace() for char in value) and "/" not in value:
        return "model-driven"
    return "script-backed"


def command_record(command, layer=None):
    record = {"command": command, "kind": classify(command)}
    if layer is not None:
        record = {"layer": layer, **record}
    return record


def stdin_records():
    raw = sys.stdin.read()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return [command_record(command) for command in raw.splitlines()]
    if isinstance(value, list):
        return [command_record(command) for command in value]
    if isinstance(value, dict):
        return [command_record(value.get(layer), layer) for layer in LAYERS]
    return [command_record(None, layer) for layer in LAYERS]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("commands", nargs="*")
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()
    records = [command_record(command) for command in args.commands]
    if args.stdin:
        records.extend(stdin_records())
    print(json.dumps(records, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

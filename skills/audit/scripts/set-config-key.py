#!/usr/bin/env python3
"""Atomically update one or more top-level JSON configuration keys."""

import argparse
import json
import os
import sys
import tempfile

from sealed_config import SealedConfigMismatch, load_sealed_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-config-sha")
    parser.add_argument("--set", action="append", required=True)
    args = parser.parse_args()
    try:
        if args.expect_config_sha is not None:
            _config_raw, config = load_sealed_config(args.config, args.expect_config_sha)
        else:
            with open(args.config, encoding="utf-8") as handle:
                config = json.load(handle)
        if not isinstance(config, dict):
            raise ValueError("config must be an object")
        changed = []
        for setting in args.set:
            if "=" not in setting:
                raise ValueError("--set must be key=<json>")
            key, raw_value = setting.split("=", 1)
            if not key:
                raise ValueError("empty configuration key")
            config[key] = json.loads(raw_value)
            changed.append(key)
        raw = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        directory = os.path.dirname(os.path.abspath(args.config))
        fd, temporary = tempfile.mkstemp(prefix=".doc-audit.", dir=directory)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, args.config)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"set-config-key: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"updated": changed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

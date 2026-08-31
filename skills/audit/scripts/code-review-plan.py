#!/usr/bin/env python3
"""Plan the configured Phase-4 code-review action from sealed config."""

import argparse
import json
import sys

from docaudit_review import classify_review_command
from sealed_config import SealedConfigMismatch, load_sealed_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--expect-config-sha", required=True)
    args = parser.parse_args()
    try:
        _raw, config = load_sealed_config(args.config, args.expect_config_sha)
        classified = classify_review_command(config)
        result = {key: classified[key] for key in
                  ("action", "state", "effort", "required", "command", "reason")}
    except SealedConfigMismatch as exc:
        print(str(exc), file=sys.stderr)
        return 7
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"code-review-plan: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

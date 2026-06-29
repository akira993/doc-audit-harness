#!/usr/bin/env bash
# write-anchor.sh — RETIRED.
#
# This script used to accept `--verdict CONSISTENT` and write the anchor on a
# verdict HANDED IN by the caller. That is exactly the hole the cure closes: an
# orchestrator could hand-feed CONSISTENT with no verification behind it.
#
# The anchor is now written ONLY by the deterministic gate, which DERIVES the
# verdict from on-disk evidence and is the sole writer:
#
#   python3 "$SD/scripts/decide-verdict.py" \
#     --run-dir "<run-dir>" --repo-root "$CLAUDE_PROJECT_DIR" --anchor-path "$ANCHOR_PATH"
#
# This stub stays only to fail loud if anything still calls the old interface.
echo "write-anchor.sh is RETIRED — the anchor is written only by decide-verdict.py" >&2
echo "(verdict is derived from evidence, never passed in). See skills/audit/SKILL.md Phase 5." >&2
exit 2

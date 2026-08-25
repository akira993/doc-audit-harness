#!/usr/bin/env bash
# docaudit v0.11.0 — release handoff (run by the user; Claude's auto mode cannot merge/release).
# 実行: bash tasks/route/2026-08-25-issues-33-34-35/release-handoff.sh
# （PR #36 は作成済み・push 済み。ここから先はマージ権限が必要な手順）
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
D=tasks/route/2026-08-25-issues-33-34-35

# 1) merge PR #36 (merge commit convention, like v0.10.0/v0.10.1)
gh pr merge 36 --merge --delete-branch

# 2) sync main and re-run the suite on merged main
git checkout main && git pull --ff-only origin main
python3 -m unittest discover -s tests -t . 2>&1 | tail -3          # expect: Ran 298 tests ... OK

# 3) tag (lightweight = current convention; the tag drives GitHub's version) + Release
git tag docaudit--v0.11.0 && git push origin docaudit--v0.11.0
gh release create docaudit--v0.11.0 \
  --title "docaudit v0.11.0 — bare-path detection, per-layer corpus config, report self-exclusion" \
  --notes-file "$D/pr-body.md"

# 4) close #33 #34 #35 if the merge's "Fixes" keywords did not auto-close them (#28 stays open)
for n in 33 34 35; do
  if [ "$(gh issue view "$n" --json state -q .state)" = "OPEN" ]; then
    gh issue close "$n" --reason completed \
      --comment "Shipped in docaudit v0.11.0 (PR #36, tag docaudit--v0.11.0)."
  else
    echo "issue #$n already closed"
  fi
done

# 5) re-sync the local skills-dir install (independent copy; engine changed this release)
rsync -a --delete \
  --exclude .git --exclude __pycache__ --exclude tasks --exclude docs/superpowers \
  --exclude .mdq --exclude .serena --exclude .claude --exclude .envrc \
  --exclude .gitignore --exclude data --exclude tests \
  ./ ~/.claude/skills/docaudit/

# 6) verify sync (same exclusions as the v0.10.1 handoff) + smoke-test in the skills dir
diff -rq . ~/.claude/skills/docaudit --exclude=.git --exclude=__pycache__ --exclude=tasks \
  --exclude=docs/superpowers --exclude=.mdq --exclude=.serena --exclude=.claude --exclude=.envrc \
  --exclude=.gitignore --exclude=data --exclude=tests | grep -v 'Only in .*: $' || echo "skills-dir == main"
python3 ~/.claude/skills/docaudit/skills/audit/scripts/generic-layers.py --help >/dev/null && echo "engine OK"

echo "done — v0.11.0 released, issues closed, skills-dir synced"

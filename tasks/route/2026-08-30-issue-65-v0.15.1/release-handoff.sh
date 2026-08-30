#!/usr/bin/env bash
# Verified, restart-safe release handoff for docaudit v0.15.1.
set -euo pipefail

die() { echo "release-handoff: $*" >&2; exit 1; }

if [ "$#" -lt 1 ] || ! [[ "$1" =~ ^[0-9A-Fa-f]{40}$ ]]; then
  die "usage: $0 <approved-v0.15.1-merge-full-sha> <pr-number>"
fi
if [ "$#" -lt 2 ] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
  die "PR number must be the numeric second argument"
fi

APPROVED_SHA="$(printf '%s' "$1" | tr 'A-F' 'a-f')"
PR_NUMBER="$2"
TAG_NEW="docaudit--v0.15.1"
RELEASE_TITLE="docaudit v0.15.1 — self-healing codegraph probe"
TMP_DIR=""
RESTORE_MAIN=0

cleanup() {
  status=$?
  trap - EXIT
  if [ "$RESTORE_MAIN" -eq 1 ]; then git checkout main >/dev/null 2>&1 || true; fi
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then rm -rf -- "$TMP_DIR"; fi
  exit "$status"
}
trap cleanup EXIT

git fetch origin || die "git fetch origin failed"
REPO_ROOT="$(git rev-parse --show-toplevel)" || die "not inside the release repository"
cd "$REPO_ROOT"

branch="$(git branch --show-current)"
[ "$branch" = "main" ] || die "current branch must be main (got: ${branch:-detached})"
head_sha="$(git rev-parse HEAD)"
origin_sha="$(git rev-parse 'refs/remotes/origin/main^{commit}')"
[ "$head_sha" = "$APPROVED_SHA" ] || die "HEAD does not equal the approved merge SHA"
[ "$origin_sha" = "$APPROVED_SHA" ] || die "origin/main does not equal the approved merge SHA"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "tracked working tree is not clean"

DEFAULT_HOME="$(cd && pwd -P)"
SKILLS_DIR="${DOCAUDIT_SKILLS_DIR:-$DEFAULT_HOME/.claude/skills/docaudit}"
SKILLS_ROOT="${DOCAUDIT_SKILLS_ROOT:-$DEFAULT_HOME/.claude/skills}"
[ ! -L "$SKILLS_DIR" ] || die "skills-dir destination must not be a symlink"
mkdir -p "$SKILLS_ROOT"
ROOT_REAL="$(cd "$SKILLS_ROOT" && pwd -P)"
case "$SKILLS_DIR/" in "$ROOT_REAL/"*) ;; *) die "skills-dir destination is outside DOCAUDIT_SKILLS_ROOT" ;; esac
mkdir -p "$SKILLS_DIR"
[ ! -L "$SKILLS_DIR" ] || die "skills-dir destination became a symlink"
DEST_REAL="$(cd "$SKILLS_DIR" && pwd -P)"
[ "$DEST_REAL" != "$ROOT_REAL" ] || die "skills-dir destination must be a subdirectory of DOCAUDIT_SKILLS_ROOT, not the root itself"
[ -d "$DEST_REAL" ] || die "skills-dir destination is not a directory"
case "$DEST_REAL/" in "$ROOT_REAL/"*) ;; *) die "skills-dir destination is outside DOCAUDIT_SKILLS_ROOT" ;; esac
[ -w "$DEST_REAL" ] || die "skills-dir destination is not writable"

RESTORE_MAIN=1
git checkout --detach "$APPROVED_SHA"
python3 -m unittest discover -s tests -t .
git checkout main
RESTORE_MAIN=0
[ "$(git branch --show-current)" = "main" ] || die "failed to restore main after tests"
[ "$(git rev-parse HEAD)" = "$APPROVED_SHA" ] || die "HEAD changed while restoring main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "tests changed tracked files"

for issue in 59 63 66; do
  tracking_state="$(gh issue view "$issue" --json state -q .state)" || die "cannot read tracking issue #$issue"
  [ "$tracking_state" = "OPEN" ] || die "tracking issue #$issue must be OPEN (got: $tracking_state)"
done

TMP_DIR="$(mktemp -d)"
NOTES="$TMP_DIR/v0.15.1-notes.md"
cat >"$NOTES" <<EOF
docaudit v0.15.1.

- Approved commit: $APPROVED_SHA
- Closes #65.
- #65 makes the symbolGraph probe self-heal from an index directory without codegraph.db and honors CODEGRAPH_DIR.
- #66 wording corrected; behavior unchanged.
- #59 remains open for the mechanical cross-version resume prohibition.
- #63 remains open for the all-seam sealed-config / TOCTOU design.
- #66 remains open for autonomous /code-review invocation.
EOF

local_tag_sha() { git rev-parse -q --verify "refs/tags/$1^{commit}" 2>/dev/null || true; }
remote_tag_sha() { git ls-remote --tags origin "refs/tags/$1" | awk 'NR == 1 {print $1}'; }
verify_existing_tag() {
  tag="$1"; expected="$2"
  local_sha="$(local_tag_sha "$tag")"; remote_sha="$(remote_tag_sha "$tag")"
  if [ -n "$local_sha" ] && [ "$local_sha" != "$expected" ]; then die "local tag $tag points to $local_sha, expected $expected"; fi
  if [ -n "$remote_sha" ] && [ "$remote_sha" != "$expected" ]; then die "remote tag $tag points to $remote_sha, expected $expected"; fi
}
ensure_tag() {
  tag="$1"; expected="$2"; verify_existing_tag "$tag" "$expected"
  local_sha="$(local_tag_sha "$tag")"; remote_sha="$(remote_tag_sha "$tag")"
  if [ -z "$local_sha" ]; then git tag "$tag" "$expected"; fi
  if [ -z "$remote_sha" ]; then git push origin "refs/tags/$tag:refs/tags/$tag"; fi
  [ "$(local_tag_sha "$tag")" = "$expected" ] || die "local tag verification failed for $tag"
  [ "$(remote_tag_sha "$tag")" = "$expected" ] || die "remote tag verification failed for $tag"
}
release_exists() { gh release view "$1" --json tagName --jq .tagName >/dev/null 2>&1; }
release_is_valid() {
  tag="$1"; shift
  [ "$(gh release view "$tag" --json tagName --jq .tagName)" = "$tag" ] || return 1
  [ "$(gh release view "$tag" --json name --jq .name)" = "$RELEASE_TITLE" ] || return 1
  [ "$(gh release view "$tag" --json isDraft --jq .isDraft)" = "false" ] || return 1
  [ "$(gh release view "$tag" --json isPrerelease --jq .isPrerelease)" = "false" ] || return 1
  body="$(gh release view "$tag" --json body --jq .body)" || return 1
  for required in "$@"; do case "$body" in *"$required"*) ;; *) return 1 ;; esac; done
}
ensure_release() {
  tag="$1"
  if release_exists "$tag"; then
    release_is_valid "$tag" "$APPROVED_SHA" "Closes #65." \
      "#66 wording corrected; behavior unchanged" "#59" "#63" "#66" \
      "codegraph.db" "CODEGRAPH_DIR" || die "existing release $tag is invalid"
  else
    gh release create "$tag" --verify-tag --title "$RELEASE_TITLE" --notes-file "$NOTES"
    release_is_valid "$tag" "$APPROVED_SHA" "Closes #65." \
      "#66 wording corrected; behavior unchanged" "#59" "#63" "#66" \
      "codegraph.db" "CODEGRAPH_DIR" || die "release $tag is invalid after create"
  fi
}

verify_existing_tag "$TAG_NEW" "$APPROVED_SHA"
ensure_tag "$TAG_NEW" "$APPROVED_SHA"
ensure_release "$TAG_NEW"

state="$(gh issue view 65 --json state -q .state)" || die "cannot read issue #65"
case "$state" in
  OPEN) gh issue close 65 --reason completed --comment "Shipped in docaudit v0.15.1 (PR #$PR_NUMBER, tag docaudit--v0.15.1)." ;;
  CLOSED) echo "issue #65 already closed" ;;
  *) die "unexpected state for issue #65: $state" ;;
esac

printf '%s' "Confirm that no docaudit run is in progress before skills-dir sync [y/N]: " >&2
IFS= read -r confirmation
[ "$confirmation" = "y" ] || die "skills-dir sync was not confirmed"

ARCHIVE_DIR="$TMP_DIR/archive"
mkdir -p "$ARCHIVE_DIR"
git archive --format=tar "$TAG_NEW" | tar -xf - -C "$ARCHIVE_DIR"
rm -rf -- "$ARCHIVE_DIR/tasks" "$ARCHIVE_DIR/data" "$ARCHIVE_DIR/tests" "$ARCHIVE_DIR/docs/superpowers"
rm -f -- "$ARCHIVE_DIR/.gitignore"
[ ! -L "$ARCHIVE_DIR" ] || die "archive source must not be a symlink"
SOURCE_REAL="$(cd "$ARCHIVE_DIR" && pwd -P)"
[ -d "$SOURCE_REAL" ] || die "archive source is not a directory"
[ "$SOURCE_REAL" != "$DEST_REAL" ] || die "archive source and skills-dir destination are identical"

FILTERS=(
  --filter='P /.git/' --filter='H /.git/' --filter='P __pycache__/' --filter='H __pycache__/'
  --filter='P *.pyc' --filter='H *.pyc' --filter='P /.venv/' --filter='H /.venv/'
  --filter='P /.brv/' --filter='H /.brv/' --filter='P .DS_Store' --filter='H .DS_Store'
  --filter='P /AGENTS.md' --filter='H /AGENTS.md' --filter='P /.claude/' --filter='H /.claude/'
  --filter='P /.mdq/' --filter='H /.mdq/' --filter='P /.serena/' --filter='H /.serena/'
  --filter='P /.envrc' --filter='H /.envrc' --filter='H /tasks/' --filter='H /data/'
  --filter='H /tests/' --filter='H /docs/superpowers/' --filter='H /.gitignore'
)
rsync -a --delete --delete-excluded "${FILTERS[@]}" "$SOURCE_REAL/" "$DEST_REAL/"
DIFF_OUTPUT="$(rsync -a --dry-run --itemize-changes --delete --delete-excluded "${FILTERS[@]}" "$SOURCE_REAL/" "$DEST_REAL/")"
[ -z "$DIFF_OUTPUT" ] || die "skills-dir differs from the v0.15.1 archive: $DIFF_OUTPUT"
python3 "$DEST_REAL/skills/audit/scripts/generic-layers.py" --help >/dev/null
echo "done — v0.15.1 released; issue #65 closed; skills-dir synced"

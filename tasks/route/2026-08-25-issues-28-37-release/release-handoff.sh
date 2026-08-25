#!/usr/bin/env bash
# Verified, restart-safe two-stage release handoff for docaudit v0.11.0/v0.12.0.
set -euo pipefail

die() {
  echo "release-handoff: $*" >&2
  exit 1
}

if [ "$#" -lt 1 ] || ! [[ "$1" =~ ^[0-9A-Fa-f]{40}$ ]]; then
  die "usage: $0 <approved-v0.12.0-merge-full-sha> <pr-number>"
fi
if [ "$#" -lt 2 ] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
  die "PR number must be the numeric second argument"
fi

APPROVED_SHA="$(printf '%s' "$1" | tr 'A-F' 'a-f')"
PR_NUMBER="$2"
TAG_OLD="docaudit--v0.11.0"
TAG_NEW="docaudit--v0.12.0"
TMP_DIR=""
RESTORE_MAIN=0

cleanup() {
  status=$?
  trap - EXIT
  if [ "$RESTORE_MAIN" -eq 1 ]; then
    git checkout main >/dev/null 2>&1 || true
  fi
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf -- "$TMP_DIR"
  fi
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

OLD_SHA="$(git rev-parse '01344ea^{commit}')" || die "cannot resolve v0.11.0 commit 01344ea"
[[ "$OLD_SHA" =~ ^[0-9a-f]{40}$ ]] || die "01344ea did not resolve to a full commit SHA"

TMP_DIR="$(mktemp -d)"
OLD_NOTES="$TMP_DIR/v0.11.0-notes.md"
NEW_NOTES="$TMP_DIR/v0.12.0-notes.md"
published_date="$(date -u +%Y-%m-%d)"

cat >"$OLD_NOTES" <<EOF
Retrospective release of docaudit v0.11.0.

- Published retrospectively on $published_date.
- Commit: $OLD_SHA
- Known issue: #37 (report publication could race a later sealed run).
- Superseded by the follow-up v0.12.0 release containing the #37 fix.
EOF

cat >"$NEW_NOTES" <<EOF
docaudit v0.12.0.

- Commit: $APPROVED_SHA
- Fixes #37: the deterministic gate writes reports while holding the run lock.
- Ships #28: opt-in Codex Phase-3 dispatcher via phase3Backend.
- In-flight docaudit runs from an older installed version must be discarded with /docaudit:audit --break-lock after synchronizing the skills directory.
EOF

local_tag_sha() {
  git rev-parse -q --verify "refs/tags/$1^{commit}" 2>/dev/null || true
}

remote_tag_sha() {
  git ls-remote --tags origin "refs/tags/$1" | awk 'NR == 1 {print $1}'
}

verify_existing_tag() {
  tag="$1"
  expected="$2"
  local_sha="$(local_tag_sha "$tag")"
  remote_sha="$(remote_tag_sha "$tag")"
  if [ -n "$local_sha" ] && [ "$local_sha" != "$expected" ]; then
    die "local tag $tag points to $local_sha, expected $expected"
  fi
  if [ -n "$remote_sha" ] && [ "$remote_sha" != "$expected" ]; then
    die "remote tag $tag points to $remote_sha, expected $expected"
  fi
}

ensure_tag() {
  tag="$1"
  expected="$2"
  verify_existing_tag "$tag" "$expected"
  local_sha="$(local_tag_sha "$tag")"
  remote_sha="$(remote_tag_sha "$tag")"
  if [ -z "$local_sha" ]; then
    git tag "$tag" "$expected"
  fi
  if [ -z "$remote_sha" ]; then
    git push origin "$tag"
  fi
  [ "$(local_tag_sha "$tag")" = "$expected" ] || die "local tag verification failed for $tag"
  [ "$(remote_tag_sha "$tag")" = "$expected" ] || die "remote tag verification failed for $tag"
}

release_exists() {
  gh release view "$1" --json tagName --jq .tagName >/dev/null 2>&1
}

release_is_valid() {
  tag="$1"
  shift
  [ "$(gh release view "$tag" --json tagName --jq .tagName)" = "$tag" ] || return 1
  [ "$(gh release view "$tag" --json isDraft --jq .isDraft)" = "false" ] || return 1
  [ "$(gh release view "$tag" --json isPrerelease --jq .isPrerelease)" = "false" ] || return 1
  body="$(gh release view "$tag" --json body --jq .body)" || return 1
  for required in "$@"; do
    case "$body" in
      *"$required"*) ;;
      *) return 1 ;;
    esac
  done
}

ensure_release() {
  tag="$1"
  title="$2"
  notes="$3"
  shift 3
  if release_exists "$tag"; then
    if ! release_is_valid "$tag" "$@"; then
      gh release edit "$tag" --title "$title" --notes-file "$notes" \
        --draft=false --prerelease=false || die "could not repair invalid release $tag"
    fi
  else
    gh release create "$tag" --verify-tag --title "$title" --notes-file "$notes"
  fi
  release_is_valid "$tag" "$@" || die "release $tag is still invalid after create/edit"
}

# A mismatched existing tag is a preflight failure: do not mutate either release first.
verify_existing_tag "$TAG_OLD" "$OLD_SHA"
verify_existing_tag "$TAG_NEW" "$APPROVED_SHA"

# Stage 1: retrospective v0.11.0 publication.
ensure_tag "$TAG_OLD" "$OLD_SHA"
ensure_release "$TAG_OLD" "docaudit v0.11.0 — retrospective release" "$OLD_NOTES" \
  "Retrospective release" "Published retrospectively on" "$OLD_SHA" "#37" "v0.12.0"

# Stage 2: always re-run the full suite at the approved v0.12.0 commit before tag/release.
RESTORE_MAIN=1
git checkout --detach "$APPROVED_SHA"
python3 -m unittest discover -s tests -t .
git checkout main
RESTORE_MAIN=0
[ "$(git branch --show-current)" = "main" ] || die "failed to restore main after tests"
[ "$(git rev-parse HEAD)" = "$APPROVED_SHA" ] || die "HEAD changed while restoring main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "tests changed tracked files"

ensure_tag "$TAG_NEW" "$APPROVED_SHA"
ensure_release "$TAG_NEW" "docaudit v0.12.0 — gate-written reports and Codex Phase 3" "$NEW_NOTES" \
  "$APPROVED_SHA" "#37" "#28" "phase3Backend" "/docaudit:audit --break-lock"

for issue in 37 28; do
  state="$(gh issue view "$issue" --json state -q .state)" || die "cannot read issue #$issue"
  case "$state" in
    OPEN)
      gh issue close "$issue" --reason completed \
        --comment "Shipped in docaudit v0.12.0 (PR #$PR_NUMBER, tag docaudit--v0.12.0)."
      ;;
    CLOSED) echo "issue #$issue already closed" ;;
    *) die "unexpected state for issue #$issue: $state" ;;
  esac
done

printf '%s' "Confirm that no docaudit run is in progress before skills-dir sync [y/N]: " >&2
IFS= read -r confirmation
[ "$confirmation" = "y" ] || die "skills-dir sync was not confirmed"

ARCHIVE_DIR="$TMP_DIR/archive"
mkdir -p "$ARCHIVE_DIR"
git archive --format=tar "$TAG_NEW" | tar -xf - -C "$ARCHIVE_DIR"
rm -rf -- "$ARCHIVE_DIR/tasks" "$ARCHIVE_DIR/data" "$ARCHIVE_DIR/tests" \
  "$ARCHIVE_DIR/docs/superpowers"
rm -f -- "$ARCHIVE_DIR/.gitignore"

[ ! -L "$ARCHIVE_DIR" ] || die "archive source must not be a symlink"
SOURCE_REAL="$(cd "$ARCHIVE_DIR" && pwd -P)"
[ -d "$SOURCE_REAL" ] || die "archive source is not a directory"

DEFAULT_HOME="$(cd && pwd -P)"
SKILLS_DIR="${DOCAUDIT_SKILLS_DIR:-$DEFAULT_HOME/.claude/skills/docaudit}"
[ ! -L "$SKILLS_DIR" ] || die "skills-dir destination must not be a symlink"
mkdir -p "$SKILLS_DIR"
[ ! -L "$SKILLS_DIR" ] || die "skills-dir destination became a symlink"
DEST_REAL="$(cd "$SKILLS_DIR" && pwd -P)"
[ -d "$DEST_REAL" ] || die "skills-dir destination is not a directory"
[ "$SOURCE_REAL" != "$DEST_REAL" ] || die "archive source and skills-dir destination are identical"

FILTERS=(
  --filter='P /.git/' --filter='H /.git/'
  --filter='P __pycache__/' --filter='H __pycache__/'
  --filter='P *.pyc' --filter='H *.pyc'
  --filter='P /.venv/' --filter='H /.venv/'
  --filter='P /.brv/' --filter='H /.brv/'
  --filter='P .DS_Store' --filter='H .DS_Store'
  --filter='P /AGENTS.md' --filter='H /AGENTS.md'
  --filter='P /.claude/' --filter='H /.claude/'
  --filter='P /.mdq/' --filter='H /.mdq/'
  --filter='P /.serena/' --filter='H /.serena/'
  --filter='P /.envrc' --filter='H /.envrc'
  --filter='H /tasks/' --filter='H /data/' --filter='H /tests/'
  --filter='H /docs/superpowers/' --filter='H /.gitignore'
)

rsync -a --delete --delete-excluded "${FILTERS[@]}" "$SOURCE_REAL/" "$DEST_REAL/"
DIFF_OUTPUT="$(rsync -a --dry-run --itemize-changes --delete --delete-excluded \
  "${FILTERS[@]}" "$SOURCE_REAL/" "$DEST_REAL/")"
[ -z "$DIFF_OUTPUT" ] || die "skills-dir differs from the v0.12.0 archive: $DIFF_OUTPUT"

python3 "$DEST_REAL/skills/audit/scripts/generic-layers.py" --help >/dev/null
echo "done — v0.11.0 retrospective and v0.12.0 released; issues closed; skills-dir synced"

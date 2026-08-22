#!/usr/bin/env bash
set -euo pipefail

# Instructor-only. Pushes the current state of lab/ out to every
# already-created student repo, so infra bugfixes reach students who
# already generated their repo from the template -- not just future ones.
#
# Deliberately does NOT use `git subtree pull` against student repos: GitHub
# "generate repository from template" commonly hands each student repo a
# single fresh commit, with none of the template's history behind it, and
# subtree pull depends on finding a prior subtree merge point in that
# history to work correctly. Instead this exports the current lab/ tree
# (via `git subtree split`, run only against this repo's own history, which
# is fine) and mirrors it into each student repo's lab/ directory with
# rsync --delete, so renames/deletions in lab/ propagate too, then commits
# and pushes if anything changed. Each student repo ends up with an
# ordinary commit, no subtree metadata required on their end.
#
# Usage: instructor/scripts/sync-lab-infra.sh <roster-file>
#
# roster-file: one student repo git URL per line (blank lines and #comments
# ok). NEVER commit this file -- it's a list of private student repos. Keep
# it outside the repo, or under instructor/ where .gitignore excludes it.

ROSTER="${1:?usage: sync-lab-infra.sh <roster-file>}"
[ -f "$ROSTER" ] || { echo "Roster file not found: $ROSTER" >&2; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! git diff-index --quiet HEAD -- lab; then
  echo "You have uncommitted changes under lab/. Commit them first, then re-run." >&2
  exit 1
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Exporting current lab/ contents..."
git subtree split --prefix=lab -b lab-sync-export-tmp >/dev/null
mkdir -p "$WORKDIR/lab-export"
git archive lab-sync-export-tmp | tar -x -C "$WORKDIR/lab-export"
git branch -D lab-sync-export-tmp >/dev/null

updated=0
skipped=0
failed=0

while IFS= read -r line; do
  repo_url="$(echo "$line" | sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
  [ -z "$repo_url" ] && continue

  name="$(basename "$repo_url" .git)"
  echo "== $name =="
  clone_dir="$WORKDIR/repos/$name"

  if ! git clone --quiet "$repo_url" "$clone_dir" 2>/dev/null; then
    echo "  FAILED to clone, skipping"
    failed=$((failed + 1))
    continue
  fi

  mkdir -p "$clone_dir/lab"
  rsync -a --delete "$WORKDIR/lab-export/" "$clone_dir/lab/"

  set +e
  (
    cd "$clone_dir" || exit 1
    git add lab
    git diff --cached --quiet && exit 10 # no changes
    git commit --quiet -m "Sync lab/ infra updates from uav-native-ai" || exit 1
    git push --quiet || exit 1
  )
  rc=$?
  set -e

  case "$rc" in
    0)  echo "  pushed update"; updated=$((updated + 1)) ;;
    10) echo "  no changes"; skipped=$((skipped + 1)) ;;
    *)  echo "  FAILED to commit/push"; failed=$((failed + 1)) ;;
  esac
done < "$ROSTER"

echo
echo "Done. Updated: $updated, no changes: $skipped, failed: $failed"

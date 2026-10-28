#!/usr/bin/env bash
# Safe, single-directory, fail-closed deployment for the public static river atlas.
# Backups and candidates are private (outside public_html).
set -euo pipefail
IFS=$'\n\t'

operation="${1:-}"
release_id="${2:-}"
[[ "$release_id" =~ ^[0-9]{5,20}$ ]] || { echo 'Invalid numeric release ID' >&2; exit 2; }
case "$operation" in preflight|prepare|publish|rollback-auto|rollback-manual) ;; *) echo 'Unsupported operation' >&2; exit 2;; esac

root="$HOME/tsurikue.com/public_html"
state="$HOME/.tsurikue-river-atlas-releases"
live="$root/river-fish-atlas"
preview="$root/river-fish-atlas-ci-preview"
candidate="$state/candidate-$release_id"
backup="$state/backup-$release_id"
failed="$state/failed-$release_id"
active="$state/active-release-id"
lock="$state/deploy.lock"

assert_dir() { [[ -d "$1" && ! -L "$1" ]] || { echo "Missing/linked directory: $1" >&2; exit 1; }; }
assert_not_link() { [[ ! -L "$1" ]] || { echo "Refusing symlink: $1" >&2; exit 1; }; }
assert_files() {
  local base="$1" f
  assert_dir "$base"
  for f in index.html sitemap.xml river/index.html data/atlas.json; do
    [[ -f "$base/$f" && ! -L "$base/$f" ]] || { echo "Missing/linked atlas file: $f" >&2; exit 1; }
  done
  if find "$base" -mindepth 1 \( -type l -o ! \( -type f -o -type d \) \) -print -quit | grep -q .; then
    echo 'Unsupported file type in atlas' >&2; exit 1
  fi
  if [[ "$base" == "$preview" ]]; then
    [[ -f "$base/.htaccess" && ! -L "$base/.htaccess" ]] || { echo 'Preview lacks noindex .htaccess' >&2; exit 1; }
    grep -Eq 'X-Robots-Tag.*noindex' "$base/.htaccess" || { echo 'Preview noindex missing' >&2; exit 1; }
  fi
  if find "$base" -type f ! \( -name '*.html' -o -name '*.json' -o -name '*.xml' -o -name '*.csv' -o -name '*.txt' \) \( ! -name '.htaccess' -o ! -path "$preview/.htaccess" \) -print -quit | grep -q .; then
    echo 'Unexpected file type in atlas' >&2; exit 1
  fi
  if find "$base" -mindepth 1 -name '.*' \( ! -name '.htaccess' -o ! -path "$preview/.htaccess" \) -print -quit | grep -q .; then
    echo 'Hidden files in atlas; manual review required' >&2; exit 1
  fi
}

assert_dir "$HOME"
assert_dir "$HOME/tsurikue.com"
assert_dir "$root"
assert_dir "$live"
assert_not_link "$preview"
assert_not_link "$state"
assert_not_link "$candidate"
assert_not_link "$backup"
assert_not_link "$failed"
assert_not_link "$active"

if [[ "$operation" == preflight ]]; then
  assert_files "$preview"
  # Live may contain .htaccess, PHP or JS requiring manual assessment;
  # never silently delete files absent from the imported static source.
  assert_files "$live"
  [[ ! -e "$backup" && ! -e "$candidate" && ! -e "$failed" ]] || { echo 'Release ID already used' >&2; exit 1; }
  echo 'Read-only production directory checks passed.'
  exit 0
fi

mkdir -p "$state"
assert_dir "$state"
if ! mkdir "$lock" 2>/dev/null; then
  echo 'Release lock exists; investigate before retrying.' >&2; exit 1
fi
unlock() { rmdir "$lock" 2>/dev/null || true; }
trap unlock EXIT

case "$operation" in
  prepare)
    [[ ! -e "$candidate" && ! -e "$backup" && ! -e "$failed" ]] || { echo 'Release ID already used' >&2; exit 1; }
    assert_files "$live"
    mkdir -m 700 "$candidate"
    echo "Prepared private candidate for $release_id"
    ;;
  publish)
    assert_files "$live"
    assert_files "$candidate"
    [[ ! -e "$backup" && ! -e "$failed" ]] || { echo 'Release ID already used' >&2; exit 1; }
    switched=0
    emergency_restore() {
      local status=$?
      trap - EXIT
      if [[ "$status" -ne 0 && "$switched" == 1 ]]; then
        echo 'Publish failed: attempting immediate restoration' >&2
        if [[ -d "$backup" && ! -L "$backup" ]]; then
          if [[ -e "$live" ]]; then
            [[ ! -e "$failed" ]] && mv "$live" "$failed" || true
          fi
          if [[ ! -e "$live" ]]; then mv "$backup" "$live" || true; fi
        fi
      fi
      unlock
      exit "$status"
    }
    trap emergency_restore EXIT
    mv "$live" "$backup"
    switched=1
    mv "$candidate" "$live"
    printf '%s\n' "$release_id" > "$state/.active-$release_id.tmp"
    mv -f "$state/.active-$release_id.tmp" "$active"
    switched=0
    echo "Published atlas release $release_id; backup retained privately."
    ;;
  rollback-auto|rollback-manual)
    [[ -f "$active" && ! -L "$active" ]] || { echo 'No active release marker to rollback' >&2; exit 1; }
    [[ "$(cat "$active")" == "$release_id" ]] || { echo 'Active release differs; refusing rollback' >&2; exit 1; }
    assert_dir "$backup"
    assert_dir "$live"
    [[ ! -e "$failed" ]] || { echo 'Failed release already archived; refusing overwrite' >&2; exit 1; }
    mv "$live" "$failed"
    if ! mv "$backup" "$live"; then
      echo 'Backup restoration failed; attempting to restore published release' >&2
      if [[ ! -e "$live" && -d "$failed" ]]; then mv "$failed" "$live" || true; fi
      exit 1
    fi
    rm -f "$active"
    echo "Rolled back release $release_id; previous atlas restored."
    ;;
esac

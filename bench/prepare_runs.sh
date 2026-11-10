#!/usr/bin/env bash
# Build one fresh, isolated git repo per (case, configuration) so reviewers can't
# interfere with each other or see answer keys.
#
# Usage: bench/prepare_runs.sh <runs_dir> [config ...]
#   Real-world cases come from bench/real_cases.tsv:
#   <case-name> <source-repo-path> <base-sha> <head-sha> <pr-branch-name>
#   History after <head-sha> is removed so the reviewer can't see later fixes.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RUNS="$1"; shift
if [ "$#" -gt 0 ]; then CONFIGS=("$@"); else CONFIGS=(with_skill without_skill); fi

mkdir -p "$RUNS"
for fx in "$HERE"/fixtures/*/; do
  name="$(basename "$fx")"
  for cfg in "${CONFIGS[@]}"; do
    python3 "$HERE/build_fixture.py" "$fx" "$RUNS/$name/$cfg/repo" >/dev/null
  done
done

if [ -f "$HERE/real_cases.tsv" ]; then
  while read -r name src base head branch; do
    [ -z "${name:-}" ] || [ "${name:0:1}" = "#" ] && continue
    tmpl="$RUNS/.tmpl-$name"
    rm -rf "$tmpl"
    git clone -q --no-local "$src" "$tmpl"
    git -C "$tmpl" checkout -q -B "$branch" "$head"
    git -C "$tmpl" branch -q -f main "$base"
    git -C "$tmpl" remote remove origin
    for b in $(git -C "$tmpl" for-each-ref --format='%(refname:short)' refs/heads/); do
      [ "$b" = "$branch" ] || [ "$b" = "main" ] || git -C "$tmpl" branch -q -D "$b"
    done
    git -C "$tmpl" tag -l | xargs -r git -C "$tmpl" tag -d >/dev/null
    git -C "$tmpl" reflog expire --expire=now --all
    git -C "$tmpl" gc -q --prune=now
    for cfg in "${CONFIGS[@]}"; do
      rm -rf "$RUNS/$name/$cfg/repo"; mkdir -p "$RUNS/$name/$cfg"
      cp -R "$tmpl" "$RUNS/$name/$cfg/repo"
    done
    rm -rf "$tmpl"
  done < "$HERE/real_cases.tsv"
fi
echo "prepared under $RUNS"

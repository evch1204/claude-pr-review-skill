#!/usr/bin/env bash
# Install the pr-review skill for Claude Code and/or Codex by symlinking it,
# so `git pull` in this repo updates every installed copy.
#
#   ./install.sh            # both Claude Code and Codex
#   ./install.sh claude     # Claude Code only  (~/.claude/skills/pr-review)
#   ./install.sh codex      # Codex only        (~/.codex/skills/pr-review)
#   ./install.sh --uninstall [claude|codex]
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/skills/pr-review"
UNINSTALL=0
if [ "${1:-}" = "--uninstall" ]; then UNINSTALL=1; shift; fi
if [ "$#" -gt 0 ]; then TARGETS=("$@"); else TARGETS=(claude codex); fi

for t in "${TARGETS[@]}"; do
  case "$t" in
    claude) dir="$HOME/.claude/skills" ;;
    codex)  dir="$HOME/.codex/skills" ;;
    *) echo "unknown target: $t (use claude or codex)" >&2; exit 1 ;;
  esac
  dest="$dir/pr-review"
  if [ "$UNINSTALL" = 1 ]; then
    if [ -L "$dest" ]; then rm "$dest"; echo "removed $dest"; else echo "nothing to remove at $dest"; fi
    continue
  fi
  mkdir -p "$dir"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "skip $t: $dest exists and is not a symlink (move it away first)" >&2
    continue
  fi
  ln -sfn "$SRC" "$dest"
  echo "installed for $t: $dest -> $SRC"
done

[ "$UNINSTALL" = 1 ] && exit 0
cat <<'EOF'

Use it:
  Claude Code:  /pr-review 123   |  /pr-review <PR URL>  |  /pr-review  (current branch)  |  "review my PR"
  Codex:        $pr-review 123   |  /skills  |  "review my PR"
GitHub PRs need the gh CLI logged in:  gh auth login
EOF

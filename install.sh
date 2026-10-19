#!/usr/bin/env bash
# Link the course-* skills into Claude Code and/or Codex, then set up the Python env.
#   ./install.sh            # both ~/.claude/skills and ~/.codex/skills
#   ./install.sh claude     # Claude Code only
#   ./install.sh codex      # Codex only
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
case "${1:-all}" in
  claude) targets=("$HOME/.claude/skills") ;;
  codex)  targets=("${CODEX_HOME:-$HOME/.codex}/skills") ;;
  all)    targets=("$HOME/.claude/skills" "${CODEX_HOME:-$HOME/.codex}/skills") ;;
  *) echo "usage: $0 [all|claude|codex]" >&2; exit 2 ;;
esac
for target in "${targets[@]}"; do
  mkdir -p "$target"
  for skill in "$ROOT"/skills/*/; do
    skill="${skill%/}"
    ln -sfn "$skill" "$target/$(basename "$skill")"
    echo "linked $target/$(basename "$skill")"
  done
done
python3 "$ROOT/skills/course-to-shorts/scripts/doctor.py" --install

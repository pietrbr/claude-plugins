#!/usr/bin/env bash
#
# PostToolUse wrapper for the comment-deslop engine. A broken or absent Python
# toolchain must never break the edit loop, so every interpreter candidate is
# tried in turn and a wrapper-level failure exits 0.
#
# Exit 0 = clean (or nothing could run). Exit 2 = findings on stderr.
#
# Interpreter order:
#   $COMMENT_DESLOP_PYTHON  -- explicit override, taken as given
#   the plugin-owned venv   -- created by `comment-deslop doctor --install`,
#                              needs no uv, and costs no resolve step
#   uv run --with tree-sitter-language-pack  -- provisions the AST rules per call
#   python3                 -- lexer only; the AST rules degrade or drop
#
# The venv is never created here: a PostToolUse hook must not download a native
# wheel because someone edited a file. `doctor --install` does that, on request.

set -u

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
engine="$root/bin/comment-deslop"

[ -r "$engine" ] || exit 0

payload=""
if [ "${1:-}" = "--hook" ]; then
  payload="$(cat)"
  [ -n "$payload" ] || exit 0
fi

errlog="$(mktemp -t comment-deslop.XXXXXX)"
trap 'rm -f "$errlog"' EXIT

attempt() {
  if [ -n "$payload" ]; then
    printf '%s' "$payload" | "$@" 2>"$errlog"
  else
    "$@" 2>"$errlog"
  fi
}

# Only the candidate that produces the verdict may write to stderr; a candidate
# we fall through from would otherwise pollute the report with its own failure.
try() {
  attempt "$@"
  local code=$?
  if [ "$code" -eq 0 ] || [ "$code" -eq 2 ]; then
    cat "$errlog" >&2
    exit "$code"
  fi
  return "$code"
}

if [ -n "${COMMENT_DESLOP_PYTHON:-}" ]; then
  try ${COMMENT_DESLOP_PYTHON} "$engine" "$@"
fi

# A venv that exists but lacks the parsers must not silently cost the AST rules,
# so the engine exits 3 under REQUIRE_AST and we fall through to the next option.
cache="${XDG_CACHE_HOME:-$HOME/.cache}"
venv="$cache/comment-deslop/venv/bin/python"
if [ -x "$venv" ]; then
  try env COMMENT_DESLOP_REQUIRE_AST=1 "$venv" "$engine" "$@"
fi

if [ "${COMMENT_DESLOP_NO_UV:-}" != "1" ] && command -v uv >/dev/null 2>&1; then
  try uv run --quiet --no-project --with tree-sitter-language-pack \
    python3 "$engine" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  try python3 "$engine" "$@"
fi

exit 0

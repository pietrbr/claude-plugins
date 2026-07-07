#!/usr/bin/env bash
#
# claude-format.sh — format files using the same tools as the user's LazyVim
# (conform.nvim + mason) setup. Deterministic, user-invoked (via the /format
# skill or directly). Respects repo-local formatter config when present and
# falls back to the LazyVim defaults otherwise.
#
# Usage:
#   claude-format.sh [options] [paths...]
#
#   paths      Files and/or directories. Directories are walked recursively.
#              Globs are expanded by the shell before they reach the script.
#              With no paths, defaults to git-changed files in the current repo.
#
# Options:
#   --ext LIST   Comma-separated extensions to include (e.g. --ext py,md,toml).
#                Filters the collected set.
#   --all        Format ALL supported files under the given dirs (or cwd).
#   --changed    Format git-changed files (default when no paths are given).
#   --dry-run    List the files that would be formatted; run no formatters.
#   -h, --help   Show this help.
#
# Formatter map (mirrors the user's conform config):
#   py            -> isort, autopep8 (--max-line-length 100),
#                    ruff check --fix, ruff format
#   lua           -> stylua (repo stylua.toml, else 2-space / col 120)
#   sh, bash      -> shfmt (.editorconfig if present, else -i 2)
#   json[c5]      -> prettier
#   yaml, yml     -> prettier
#   md[x]         -> treated as txt (trailing-ws trim + final newline only)
#   css,scss,less -> prettier
#   html, htm     -> prettier
#   js,jsx,ts,... -> prettier
#   toml          -> taplo fmt
#   tex,sty,cls   -> latexindent
#   bib           -> bibtex-tidy
#   rs            -> rustfmt (if installed)
#   txt           -> trim trailing whitespace + ensure final newline
#
# Missing tools are reported as skips and summarized as a WARNING at the end.
# Edit the *_fmt functions below to tune the chains/args.

set -uo pipefail

MASON="$HOME/.local/share/nvim/mason/bin"

# --- output helpers -----------------------------------------------------------
c_reset=$'\033[0m'
c_dim=$'\033[2m'
c_grn=$'\033[32m'
c_yel=$'\033[33m'
c_red=$'\033[31m'
if [ ! -t 1 ]; then
  c_reset=""
  c_dim=""
  c_grn=""
  c_yel=""
  c_red=""
fi
ok() { printf '%s  ok   %s %s\n' "$c_grn" "$c_reset" "$1"; }
skip() { printf '%s  skip %s %s%s%s%s\n' "$c_yel" "$c_reset" "$1" "$c_dim" "${2:+  ($2)}" "$c_reset"; }
fail() { printf '%s  FAIL %s %s%s%s%s\n' "$c_red" "$c_reset" "$1" "$c_dim" "${2:+  ($2)}" "$c_reset"; }
note() { printf '%s%s%s\n' "$c_dim" "$1" "$c_reset"; }

NUM_OK=0
NUM_SKIP=0
NUM_FAIL=0

# Track formatters that could not be found, to warn about at the end.
MISSING=" "
record_missing() { case "$MISSING" in *" $1 "*) ;; *) MISSING="$MISSING$1 " ;; esac }

# --- tool resolution ----------------------------------------------------------
# Prefer the mason-managed binary, fall back to anything on PATH.
resolve() {
  if [ -x "$MASON/$1" ]; then
    printf '%s\n' "$MASON/$1"
    return 0
  fi
  command -v "$1" 2>/dev/null
}

# find_up DIR NAME [NAME...] : true if any NAME exists in DIR or an ancestor.
find_up() {
  local dir="$1"
  shift
  dir="$(cd "$dir" 2>/dev/null && pwd)" || return 1
  while :; do
    local n
    for n in "$@"; do [ -e "$dir/$n" ] && return 0; done
    [ "$dir" = "/" ] && return 1
    dir="$(dirname "$dir")"
  done
}

# --- per-language formatters --------------------------------------------------
# Each takes the absolute file path. Tools are run from the file's directory so
# upward config discovery (.prettierrc, pyproject.toml, stylua.toml, ...) works.

py_fmt() {
  local f="$1" dir base rc=0 ran=0 tool
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  if tool="$(resolve isort)" && [ -n "$tool" ]; then
    (cd "$dir" && "$tool" -q "$base") || rc=1
    ran=1
  else
    record_missing isort
  fi
  if tool="$(resolve autopep8)" && [ -n "$tool" ]; then
    (cd "$dir" && "$tool" --in-place --max-line-length 100 "$base") || rc=1
    ran=1
  else
    record_missing autopep8
  fi
  if tool="$(resolve ruff)" && [ -n "$tool" ]; then
    local ruff_cfg=0
    if find_up "$dir" ruff.toml .ruff.toml || { find_up "$dir" pyproject.toml && grep -ql '\[tool\.ruff' "$(_first_up "$dir" pyproject.toml)" 2>/dev/null; }; then
      ruff_cfg=1
    fi
    if [ "$ruff_cfg" = 1 ]; then
      # repo ruff config present: respect it, no line-length override
      (cd "$dir" && "$tool" check -q --fix --exit-zero "$base")
      (cd "$dir" && "$tool" format -q "$base") || rc=1
    else
      (cd "$dir" && "$tool" check -q --fix --exit-zero --line-length 100 "$base")
      (cd "$dir" && "$tool" format -q --line-length 100 "$base") || rc=1
    fi
    ran=1
  else
    record_missing ruff
  fi
  [ "$ran" = 0 ] && {
    skip "$f" "no python formatter installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  if [ "$rc" = 0 ]; then
    ok "$f"
    NUM_OK=$((NUM_OK + 1))
  else
    fail "$f" "python formatter error"
    NUM_FAIL=$((NUM_FAIL + 1))
  fi
}

# echo the path of the nearest NAME at or above DIR (helper for grep checks)
_first_up() {
  local dir="$1" name="$2"
  dir="$(cd "$dir" 2>/dev/null && pwd)" || return 1
  while :; do
    [ -e "$dir/$name" ] && {
      printf '%s\n' "$dir/$name"
      return 0
    }
    [ "$dir" = "/" ] && return 1
    dir="$(dirname "$dir")"
  done
}

lua_fmt() {
  local f="$1" dir base tool
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  tool="$(resolve stylua)"
  [ -z "$tool" ] && {
    record_missing stylua
    skip "$f" "stylua not installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  if find_up "$dir" stylua.toml .stylua.toml; then
    (cd "$dir" && "$tool" --search-parent-directories "$base")
  else
    (cd "$dir" && "$tool" --indent-type Spaces --indent-width 2 --column-width 120 "$base")
  fi
  _report "$f" $?
}

shell_fmt() {
  local f="$1" dir base tool
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  tool="$(resolve shfmt)"
  [ -z "$tool" ] && {
    record_missing shfmt
    skip "$f" "shfmt not installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  if find_up "$dir" .editorconfig; then
    (cd "$dir" && "$tool" -w "$base")
  else
    (cd "$dir" && "$tool" -w -i 2 "$base")
  fi
  _report "$f" $?
}

prettier_fmt() {
  local f="$1" dir base tool
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  tool="$(resolve prettier)"
  [ -z "$tool" ] && {
    record_missing prettier
    skip "$f" "prettier not installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  (cd "$dir" && "$tool" --log-level warn --write "$base")
  _report "$f" $?
}

taplo_fmt() {
  local f="$1" dir base tool
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  tool="$(resolve taplo)"
  [ -z "$tool" ] && {
    record_missing taplo
    skip "$f" "taplo not installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  (cd "$dir" && "$tool" fmt "$base") >/dev/null 2>&1
  _report "$f" $?
}

latex_fmt() {
  local f="$1" dir base tool tmp
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  tool="$(resolve latexindent)"
  [ -z "$tool" ] && {
    record_missing latexindent
    skip "$f" "latexindent not installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  tmp="$(mktemp)" || {
    fail "$f" "mktemp"
    NUM_FAIL=$((NUM_FAIL + 1))
    return
  }
  if (cd "$dir" && "$tool" -s "$base") >"$tmp" 2>/dev/null && [ -s "$tmp" ]; then
    mv "$tmp" "$f"
    ok "$f"
    NUM_OK=$((NUM_OK + 1))
  else
    rm -f "$tmp"
    fail "$f" "latexindent error"
    NUM_FAIL=$((NUM_FAIL + 1))
  fi
}

bib_fmt() {
  local f="$1" tool
  tool="$(resolve bibtex-tidy)"
  [ -z "$tool" ] && {
    record_missing bibtex-tidy
    skip "$f" "bibtex-tidy not installed"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  "$tool" --modify "$f" >/dev/null 2>&1
  _report "$f" $?
}

rust_fmt() {
  local f="$1" tool
  tool="$(resolve rustfmt)"
  [ -z "$tool" ] && {
    record_missing rustfmt
    skip "$f" "rustfmt not installed (install via rustup)"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  }
  "$tool" "$f"
  _report "$f" $?
}

txt_fmt() {
  local f="$1"
  # trim trailing whitespace; ensure exactly one trailing newline
  perl -i -pe 's/[ \t]+$//' "$f" 2>/dev/null
  if [ -s "$f" ] && [ "$(tail -c1 "$f" | wc -l | tr -d ' ')" = "0" ]; then printf '\n' >>"$f"; fi
  _report "$f" $?
}

_report() {
  local f="$1" rc="$2"
  if [ "$rc" = 0 ]; then
    ok "$f"
    NUM_OK=$((NUM_OK + 1))
  else
    fail "$f" "formatter exited $rc"
    NUM_FAIL=$((NUM_FAIL + 1))
  fi
}

# --- dispatch -----------------------------------------------------------------
SUPPORTED_EXT_RE='^(py|lua|sh|bash|json|jsonc|json5|yaml|yml|md|markdown|mdx|css|scss|less|html|htm|js|jsx|mjs|cjs|ts|tsx|vue|toml|tex|sty|cls|bib|rs|txt|text)$'

# is_supported PATH : true if we have a formatter for it (used when walking dirs)
is_supported() {
  local ext="${1##*.}"
  ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  [ "$ext" = "$1" ] && return 1 # no extension -> unsupported
  printf '%s' "$ext" | grep -Eq "$SUPPORTED_EXT_RE"
}

format_one() {
  local f="$1"
  if [ ! -f "$f" ]; then
    skip "$f" "not a file"
    NUM_SKIP=$((NUM_SKIP + 1))
    return
  fi
  local ext="${f##*.}"
  ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  case "$ext" in
  py) py_fmt "$f" ;;
  lua) lua_fmt "$f" ;;
  sh | bash) shell_fmt "$f" ;;
  json | jsonc | json5) prettier_fmt "$f" ;;
  yaml | yml) prettier_fmt "$f" ;;
  md | markdown | mdx) txt_fmt "$f" ;; # treated as txt: trailing-ws trim + final newline only
  css | scss | less) prettier_fmt "$f" ;;
  html | htm) prettier_fmt "$f" ;;
  js | jsx | mjs | cjs | ts | tsx | vue) prettier_fmt "$f" ;;
  toml) taplo_fmt "$f" ;;
  tex | sty | cls) latex_fmt "$f" ;;
  bib) bib_fmt "$f" ;;
  rs) rust_fmt "$f" ;;
  txt | text) txt_fmt "$f" ;;
  *)
    skip "$f" "no formatter for .$ext"
    NUM_SKIP=$((NUM_SKIP + 1))
    ;;
  esac
}

# --- target collection --------------------------------------------------------
PRUNE_DIRS='.git node_modules .venv venv env __pycache__ dist build .next out target .mypy_cache .ruff_cache .pytest_cache .tox vendor'

walk_dir() { # emit supported files under a dir, NUL-separated
  local d="$1" prune=()
  local p
  for p in $PRUNE_DIRS; do prune+=(-name "$p" -prune -o); done
  find "$d" \( "${prune[@]}" -type f -print0 \)
}

main() {
  local ext_filter="" mode="" dry=0
  local -a paths=()
  while [ $# -gt 0 ]; do
    case "$1" in
    --ext)
      ext_filter="$(printf '%s' "${2:-}" | tr ',' ' ' | tr '[:upper:]' '[:lower:]')"
      shift 2
      ;;
    --ext=*)
      ext_filter="$(printf '%s' "${1#*=}" | tr ',' ' ' | tr '[:upper:]' '[:lower:]')"
      shift
      ;;
    --all)
      mode="all"
      shift
      ;;
    --changed)
      mode="changed"
      shift
      ;;
    --dry-run | --list)
      dry=1
      shift
      ;;
    -h | --help)
      # print the leading comment block (after the shebang), stripped of '# '
      awk 'NR>1 && /^#/{sub(/^# ?/,"");print;next} NR>1{exit}' "$0"
      exit 0
      ;;
    --)
      shift
      while [ $# -gt 0 ]; do
        paths+=("$1")
        shift
      done
      ;;
    -*)
      printf 'unknown option: %s\n' "$1" >&2
      exit 2
      ;;
    *)
      paths+=("$1")
      shift
      ;;
    esac
  done

  # Build the candidate file list (NUL-separated) into an array.
  local -a files=()
  local f
  if [ "${#paths[@]}" -gt 0 ]; then
    local p
    for p in "${paths[@]}"; do
      if [ -d "$p" ]; then
        while IFS= read -r -d '' f; do is_supported "$f" && files+=("$f"); done < <(walk_dir "$p")
      elif [ -f "$p" ]; then
        files+=("$p") # explicitly named: format even if unusual
      else
        printf '%s%s%s does not exist\n' "$c_yel" "$p" "$c_reset" >&2
      fi
    done
  elif [ "$mode" = "all" ]; then
    while IFS= read -r -d '' f; do is_supported "$f" && files+=("$f"); done < <(walk_dir ".")
  else
    # default: git-changed files in the current repo
    local root
    if root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
      while IFS= read -r -d '' f; do
        [ -f "$root/$f" ] || continue
        is_supported "$root/$f" && files+=("$root/$f")
      done < <({
        git -C "$root" diff --name-only -z --diff-filter=ACMR
        git -C "$root" diff --name-only -z --diff-filter=ACMR --cached
        git -C "$root" ls-files --others --exclude-standard -z
      } | sort -zu)
    else
      printf 'Not in a git repo and no paths given.\nSpecify files/dirs, or use --all to format everything under the current directory.\n' >&2
      exit 2
    fi
  fi

  # Apply --ext filter.
  if [ -n "$ext_filter" ]; then
    local -a filtered=()
    for f in "${files[@]:-}"; do
      [ -z "$f" ] && continue
      local e="${f##*.}"
      e="$(printf '%s' "$e" | tr '[:upper:]' '[:lower:]')"
      local keep=0 want
      for want in $ext_filter; do
        [ "$e" = "$want" ] && keep=1
      done
      [ "$keep" = 1 ] && filtered+=("$f")
    done
    files=("${filtered[@]:-}")
  fi

  # De-dup while preserving order.
  local -a uniq=()
  local seen=" "
  for f in "${files[@]:-}"; do
    [ -z "$f" ] && continue
    case "$seen" in *" $f "*) ;; *)
      uniq+=("$f")
      seen="$seen$f "
      ;;
    esac
  done
  files=("${uniq[@]:-}")

  if [ "${#files[@]}" -eq 0 ] || { [ "${#files[@]}" -eq 1 ] && [ -z "${files[0]}" ]; }; then
    note "No matching files to format."
    exit 0
  fi

  if [ "$dry" = 1 ]; then
    note "Would format ${#files[@]} file(s):"
    for f in "${files[@]}"; do printf '  %s\n' "$f"; done
    exit 0
  fi

  for f in "${files[@]}"; do format_one "$f"; done

  if [ "$MISSING" != " " ]; then
    printf '\n%sWARNING: formatter(s) not installed, files skipped:%s%s\n' "$c_yel" "$MISSING" "$c_reset" >&2
    printf '%s  install via mason (:Mason / :MasonInstall) or your PATH.%s\n' "$c_dim" "$c_reset" >&2
  fi

  printf '\n%sFormatted %d, skipped %d, failed %d.%s\n' "$c_dim" "$NUM_OK" "$NUM_SKIP" "$NUM_FAIL" "$c_reset"
  [ "$NUM_FAIL" -gt 0 ] && exit 1 || exit 0
}

main "$@"

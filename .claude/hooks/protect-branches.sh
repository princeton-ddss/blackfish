#!/bin/bash
# PreToolUse(Bash) guard: refuse pushes that would land on a protected branch.
#
# Registered once, in .claude/settings.json, via $CLAUDE_PROJECT_DIR so it
# resolves regardless of the working directory the tool call runs from.
#
# Exit 2 blocks the tool call; exit 0 allows it.

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // ""')

PROTECTED_BRANCHES=("main" "dev" "production" "release")

is_protected() {
  local branch="$1"
  for protected in "${PROTECTED_BRANCHES[@]}"; do
    [[ "$branch" == "$protected" ]] && return 0
  done
  return 1
}

# Resolve what a single `git push ...` invocation would actually write to, and
# block only on that. Matching the branch name anywhere in the command text
# would both over-block (`git push origin feat/fix-main-nav`) and under-block
# (a bare `git push` while main is checked out).
check_push() {
  local segment="$1"
  # shellcheck disable=SC2206
  local tokens=($segment)
  local seen_push=0
  local args=()

  for token in "${tokens[@]}"; do
    if [[ $seen_push -eq 0 ]]; then
      [[ "$token" == "push" ]] && seen_push=1
      continue
    fi
    # Options never name a destination, except --delete, which makes the
    # refspecs deletions of those very branches — still the right thing to
    # check, so it needs no special case.
    [[ "$token" == -* ]] && continue
    args+=("$token")
  done

  [[ $seen_push -eq 0 ]] && return 0

  # args = [remote] [refspec ...]. With no refspec, git pushes the current
  # branch (push.default=simple/current), so that is what we must check.
  if [[ ${#args[@]} -le 1 ]]; then
    local current
    current=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || return 0
    if is_protected "$current"; then
      echo "ERROR: Refusing to push the checked-out protected branch: $current" >&2
      return 1
    fi
    return 0
  fi

  local refspec dest
  for refspec in "${args[@]:1}"; do
    # src:dst pushes to dst; a bare ref pushes to itself; ':dst' deletes dst.
    dest="${refspec##*:}"
    dest="${dest#+}"        # +ref forces
    dest="${dest#refs/heads/}"
    if is_protected "$dest"; then
      echo "ERROR: Cannot push to protected branch: $dest" >&2
      return 1
    fi
  done
  return 0
}

# A compound command may contain several invocations; check each separately so
# one segment's arguments aren't read as another's.
while IFS= read -r segment; do
  [[ "$segment" =~ git[[:space:]] ]] || continue
  [[ "$segment" =~ [[:space:]]push([[:space:]]|$) ]] || continue
  check_push "$segment" || exit 2
done < <(echo "$command" | tr ';&|\n' '\n')

exit 0

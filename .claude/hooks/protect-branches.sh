#!/bin/bash

input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // ""')

PROTECTED_BRANCHES=("main" "dev" "production" "release")

for branch in "${PROTECTED_BRANCHES[@]}"; do
  # Block push to protected branches
  if echo "$command" | grep -qE "git\s+push.*${branch}"; then
    echo "ERROR: Cannot push to protected branch: $branch" >&2
    exit 2
  fi
done

exit 0

#!/usr/bin/env bash
# Apply the committed repo rulesets in this directory to GitHub (OPS-F3:
# rulesets as version-controlled infrastructure-as-code).
#
# Idempotent: for each <name>.json, creates the ruleset if no ruleset of that
# name exists yet, or updates the existing one in place if it does. Matching is
# by the "name" field, so renaming a ruleset creates a second one — rename in
# the API too, or delete the stale one.
#
# Usage:  ./apply.sh [owner/repo]   (default: dhh1128/entviz)
# Requires: gh (authenticated) and jq.
set -euo pipefail

REPO="${1:-dhh1128/entviz}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

shopt -s nullglob
for f in "$DIR"/*.json; do
  name="$(jq -r .name "$f")"
  echo "==> ${name}"
  id="$(gh api "repos/${REPO}/rulesets" \
        --jq ".[] | select(.name==\"${name}\") | .id" | head -n1)"
  if [ -n "${id}" ]; then
    echo "    updating existing ruleset ${id}"
    gh api -X PUT "repos/${REPO}/rulesets/${id}" --input "$f" >/dev/null
  else
    echo "    creating new ruleset"
    gh api -X POST "repos/${REPO}/rulesets" --input "$f" >/dev/null
  fi
done
echo "Done."

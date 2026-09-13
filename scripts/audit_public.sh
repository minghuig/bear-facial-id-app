#!/usr/bin/env bash
# Review staged content before a public commit. Does not contact GitHub or mutate files.
set -euo pipefail

if git diff --cached --quiet; then
  echo 'Nothing is staged. Run git add -A, then rerun this audit.' >&2
  exit 2
fi

names=$(git diff --cached --name-only)
if printf '%s\n' "$names" | rg -n '(^|/)(\.env$|\.private/|\.venv/|node_modules/|dist/|artifacts/|reports/private/)|\.(pth|npz|npy|zip|tar|tfstate|tfplan|pem|key)$'; then
  echo 'Forbidden private/generated file staged.' >&2
  exit 1
fi

# .env.example is an intentional template; .env itself is forbidden by the filename check above.
if git diff --cached --name-only | rg -n '(^|/)\.env$'; then
  echo 'A real .env file is staged.' >&2
  exit 1
fi

if git grep --cached -n -I -E 'AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,}' -- ':!frontend/package-lock.json'; then
  echo 'Credential signature found in staged content.' >&2
  exit 1
fi

users_path="/""Users/"
prototype_path="/""Documents/bear-id"
if git grep --cached -n -E "$users_path|$prototype_path"; then
  echo 'Personal local path found in staged content.' >&2
  exit 1
fi

# The vendored upstream model files retain their original CRLF/trailing whitespace
# so their source hash and provenance remain verifiable.
if ! git diff --cached --check -- ':!workers/vendor/**'; then
  echo 'Whitespace error in staged content.' >&2
  exit 1
fi

echo "Public audit passed for $(printf '%s\n' "$names" | wc -l | tr -d ' ') staged files."

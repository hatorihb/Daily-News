#!/bin/bash
# PostToolUse hook: scan edited file for committed secrets and dangerous env patterns.
# Exit 2 + stderr if anything matches — Claude sees the error and self-corrects.
# Bypass for legitimate matches: add the literal string SECRET-SCAN-OK on the same line.
set -uo pipefail
input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -z "$file_path" ] && exit 0
[ ! -f "$file_path" ] && exit 0
case "$file_path" in
  */node_modules/*|*/.git/*|*/dist/*|*/build/*|*/.next/*|*/coverage/*|*/.turbo/*|*/.vite/*) exit 0 ;;
  *.lock|*.lockb|*-lock.json|*.tsbuildinfo|*.snap) exit 0 ;;
esac
is_gitignored() {
  git -C "$(dirname "$1")" check-ignore --quiet "$1" 2>/dev/null
}
scan() {
  local label="$1" pattern="$2"
  grep -nE "$pattern" "$file_path" 2>/dev/null | grep -v 'SECRET-SCAN-OK' || true
}
findings=""
if ! is_gitignored "$file_path"; then
  declare -a SECRET_PATTERNS=(
    "Stripe live key|(sk|rk)_live_[0-9a-zA-Z]{20,}"
    "GitHub PAT|gh[pousr]_[0-9a-zA-Z]{36,}"
    "GitHub fine-grained PAT|github_pat_[0-9a-zA-Z_]{50,}"
    "Slack token|xox[abprs]-[0-9a-zA-Z-]{10,}"
    "OpenAI key (legacy)|sk-[a-zA-Z0-9]{48}"
    "OpenAI key (project)|sk-proj-[a-zA-Z0-9_-]{40,}"
    "Anthropic key|sk-ant-api03-[a-zA-Z0-9_-]{40,}"
    "AWS access key ID|AKIA[0-9A-Z]{16}"
    "Google API key|AIza[0-9A-Za-z_-]{35}"
    "Private key block|-----BEGIN ([A-Z]+ )?PRIVATE KEY-----"
    "JWT (likely real)|eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\."
  )
  for entry in "${SECRET_PATTERNS[@]}"; do
    label="${entry%%|*}"
    pattern="${entry#*|}"
    match=$(scan "$label" "$pattern")
    if [ -n "$match" ]; then
      findings="${findings}[${label}]\n${match}\n\n"
    fi
  done
fi
case "$file_path" in
  *.env|*.env.*|*.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs)
    np=$(scan "NEXT_PUBLIC client-bundle leak" 'NEXT_PUBLIC_[A-Z0-9_]*(SECRET|PASSWORD|PRIVATE|API_KEY)')
    if [ -n "$np" ]; then
      findings="${findings}[NEXT_PUBLIC_*SECRET/PASSWORD/PRIVATE/API_KEY ships to the browser bundle]\n${np}\n\n"
    fi
    ;;
esac
if [ -n "$findings" ]; then
  printf 'Security scan blocked %s\n\n' "$file_path" >&2
  printf '%b' "$findings" >&2
  printf 'Fix the match, gitignore the file, or add the literal string SECRET-SCAN-OK on the offending line if it is a legitimate test fixture.\n' >&2
  exit 2
fi
exit 0

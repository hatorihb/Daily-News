#!/bin/bash
# PostToolUse hook for Daily-News: enforce filename, size, and date consistency
# on tech-report HTML files. Exit 2 + stderr if invalid — Claude will self-correct.
set -uo pipefail
input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -z "$file_path" ] && exit 0
[ ! -f "$file_path" ] && exit 0
case "$file_path" in
  */reports/*.html) ;;
  *) exit 0 ;;
esac
basename=$(basename "$file_path")
errors=""
if ! [[ "$basename" =~ ^tech-report-([0-9]{4})-([0-9]{2})-([0-9]{2})\.html$ ]]; then
  errors+="Filename does not match required pattern 'tech-report-YYYY-MM-DD.html'\n  got: $basename\n  the auto-merge workflow will silently skip files that don't match.\n\n"
fi
size=$(wc -c < "$file_path" | tr -d ' ')
if [ "$size" -lt 2048 ]; then
  errors+="Report is too small (${size} bytes < 2048). Likely truncated or stub content. Regenerate the full report.\n\n"
fi
if [[ "$basename" =~ ^tech-report-([0-9]{4})-([0-9]{2})-([0-9]{2})\.html$ ]]; then
  year="${BASH_REMATCH[1]}"
  month="${BASH_REMATCH[2]}"
  day="${BASH_REMATCH[3]}"
  iso="${year}-${month}-${day}"
  jp_month=$((10#$month))
  jp_day=$((10#$day))
  jp="${year}年${jp_month}月${jp_day}日"
  if ! grep -qF "$iso" "$file_path" && ! grep -qF "$jp" "$file_path"; then
    errors+="Report body does not contain its own date (${iso} or ${jp}). Possible date mismatch — verify you're writing today's report into today's filename.\n\n"
  fi
fi
if [ -n "$errors" ]; then
  printf 'Daily-News report check failed for %s\n\n' "$file_path" >&2
  printf '%b' "$errors" >&2
  exit 2
fi
exit 0

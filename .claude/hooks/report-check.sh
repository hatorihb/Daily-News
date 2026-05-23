#!/bin/bash
# PostToolUse hook for Daily-News: enforce filename, size, date consistency,
# section completeness, and card-date freshness on tech-report HTML files.
# Exit 2 + stderr if invalid — Claude will self-correct.
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

# 1. ファイル名パターン
if ! [[ "$basename" =~ ^tech-report-([0-9]{4})-([0-9]{2})-([0-9]{2})\.html$ ]]; then
  errors+="Filename does not match required pattern 'tech-report-YYYY-MM-DD.html'\n  got: $basename\n  the auto-merge workflow will silently skip files that don't match.\n\n"
fi

# 2. サイズ
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

  # 3. レポート自身の日付が本文に含まれるか
  if ! grep -qF "$iso" "$file_path" && ! grep -qF "$jp" "$file_path"; then
    errors+="Report body does not contain its own date (${iso} or ${jp}). Possible date mismatch — verify you're writing today's report into today's filename.\n\n"
  fi

  # 4. 4セクション（id）の存在チェック
  for section_id in domestic ai aws security; do
    if ! grep -qF "id=\"${section_id}\"" "$file_path"; then
      errors+="Required section id=\"${section_id}\" is missing. All 4 sections (domestic / ai / aws / security) must be present in every report.\n\n"
    fi
  done

  # 5. card-date の日付が「前日以降」かチェック
  # 許容範囲: レポート日付の前日〜当日のみ
  prev_day=$(date -d "${iso} -1 day" +%Y-%m-%d 2>/dev/null || \
             python3 -c "from datetime import date,timedelta; d=date(${year},${jp_month},${jp_day}); print((d-timedelta(1)).isoformat())")
  stale_dates=""
  while IFS= read -r card_date; do
    [ -z "$card_date" ] && continue
    if [[ "$card_date" < "$prev_day" ]]; then
      stale_dates+="  - ${card_date} (older than previous day ${prev_day})\n"
    fi
  done < <(grep -oP '(?<=class="card-date">)\d{4}-\d{2}-\d{2}' "$file_path" || true)
  if [ -n "$stale_dates" ]; then
    errors+="Card date(s) are older than the previous day (${prev_day}). Only yesterday and today are allowed:\n${stale_dates}Remove stale cards or update their dates.\n\n"
  fi
fi

if [ -n "$errors" ]; then
  printf 'Daily-News report check failed for %s\n\n' "$file_path" >&2
  printf '%b' "$errors" >&2
  exit 2
fi
exit 0

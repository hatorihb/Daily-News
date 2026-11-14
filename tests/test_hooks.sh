#!/bin/bash
# .claude/hooks/report-check.sh と secret-scan.sh の挙動テスト。CI（ci.yml）から実行する。
# 最新のレポートを今日付けに書き換えたものを正常系とし、そこから壊した版が exit 2 で弾かれることを確認する。
set -uo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/reports"
failures=0

# expect <説明> <期待する終了コード> <フック名> <対象ファイル>
expect() {
  local desc=$1 want=$2 hook=$3 file=$4 got
  jq -n --arg p "$file" '{tool_input: {file_path: $p}}' \
    | bash "$ROOT/.claude/hooks/$hook" > "$WORK/out" 2>&1
  got=$?
  if [ "$got" = "$want" ]; then
    echo "ok   - $desc"
  else
    echo "FAIL - $desc (want exit $want, got $got)"
    sed 's/^/       /' "$WORK/out"
    failures=$((failures + 1))
  fi
}

TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
PREV=$(date -d "$TODAY -1 day" +%Y-%m-%d)
SRC=$(printf '%s\n' "$ROOT"/reports/tech-report-*.html | sort | tail -1)
SRC_DATE=$(basename "$SRC" .html | sed 's/^tech-report-//')
SRC_PREV=$(date -d "$SRC_DATE -1 day" +%Y-%m-%d)
JP="$(date -d "$TODAY" +%Y)年$((10#$(date -d "$TODAY" +%m)))月$((10#$(date -d "$TODAY" +%d)))日"
SRC_JP="$(date -d "$SRC_DATE" +%Y)年$((10#$(date -d "$SRC_DATE" +%m)))月$((10#$(date -d "$SRC_DATE" +%d)))日"

VALID="$WORK/reports/tech-report-${TODAY}.html"
sed -e "s/${SRC_DATE}/${TODAY}/g" -e "s/${SRC_PREV}/${PREV}/g" -e "s/${SRC_JP}/${JP}/g" "$SRC" > "$VALID"
echo "# source: $(basename "$SRC") -> tech-report-${TODAY}.html"

# --- report-check.sh ---
expect "valid report passes" 0 report-check.sh "$VALID"

f="$WORK/reports/tech-report-2020-01-01.html"; cp "$VALID" "$f"
expect "filename date != today is rejected" 2 report-check.sh "$f"
rm -f "$f"

f="$WORK/reports/report-${TODAY}.html"; cp "$VALID" "$f"
expect "wrong filename pattern is rejected" 2 report-check.sh "$f"
rm -f "$f"

cp "$VALID" "$WORK/valid.bak"
sed -i 's#</body>#<span class="card-date">2020-01-01</span></body>#' "$VALID"
expect "stale card-date is rejected" 2 report-check.sh "$VALID"
cp "$WORK/valid.bak" "$VALID"

sed -i 's/id="security"/id="sec"/' "$VALID"
expect "missing section is rejected" 2 report-check.sh "$VALID"
cp "$WORK/valid.bak" "$VALID"

printf '<html><body>%s</body></html>\n' "$TODAY" > "$VALID"
expect "truncated report is rejected" 2 report-check.sh "$VALID"
cp "$WORK/valid.bak" "$VALID"

printf 'not a report\n' > "$WORK/notes.txt"
expect "non-report files are ignored" 0 report-check.sh "$WORK/notes.txt"

# --- secret-scan.sh ---
expect "valid report has no secrets" 0 secret-scan.sh "$VALID"

# キー形式の文字列は実行時に組み立てる（このファイル自体がスキャンに引っかからないように）
fake_key="AKIA$(printf 'Q%.0s' {1..16})"
printf '<p>%s</p>\n' "$fake_key" >> "$VALID"
expect "AWS-key-shaped string is rejected" 2 secret-scan.sh "$VALID"
cp "$WORK/valid.bak" "$VALID"

printf '<p>%s</p><!-- SECRET-SCAN-OK -->\n' "$fake_key" >> "$VALID"
expect "SECRET-SCAN-OK bypasses the scan" 0 secret-scan.sh "$VALID"

echo
if [ "$failures" -gt 0 ]; then
  echo "$failures hook test(s) failed"
  exit 1
fi
echo "All hook tests passed"

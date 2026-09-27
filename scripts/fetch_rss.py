#!/usr/bin/env python3
"""RSS フィードを事前取得し、対象期間内の記事一覧を Markdown で出力する。

GitHub Actions（daily-report.yml）から Claude 実行前に呼ばれる。
- 公開日時（pubDate / dc:date / published / updated）で機械的に期間を絞るので、
  モデルが XML を読んで日付を判断する必要がなくなる
- 取得の成否をステータス表に残すので、恒常的に落ちているフィードを検知できる
- XML 全体ではなく「日時・タイトル・URL・概要」だけを渡すのでトークンを節約できる

標準ライブラリのみ使用。どのフィードが失敗しても終了コードは 0（Claude 側で検索にフォールバックする）。
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

JST = timezone(timedelta(hours=9))

# prompt/routine-prompt.md の「2-1. RSSフィード確認」と同じ一覧。追加・変更時は両方を揃えること。
FEEDS = [
    {"id": "aws", "name": "AWS What's New", "section": "03 AWS",
     "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/"},
    {"id": "itmedia_news", "name": "ITmedia NEWS", "section": "01 国内IT・DX / 04 セキュリティ",
     "url": "https://rss.itmedia.co.jp/rss/2.0/itmedia_news.xml"},
    {"id": "itmedia_aiplus", "name": "ITmedia AI＋", "section": "02 AI",
     "url": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"},
    {"id": "security_next", "name": "Security NEXT", "section": "04 セキュリティ", "security": True,
     "url": "https://www.security-next.com/feed"},
    {"id": "jvn", "name": "JVN iPedia 新着", "section": "04 セキュリティ", "security": True,
     "url": "https://jvndb.jvn.jp/ja/rss/jvndb_new.rdf"},
    {"id": "madonomori", "name": "窓の杜", "section": "04 セキュリティ / 01", "security": True,
     "url": "https://forest.watch.impress.co.jp/data/rss/1.0/wf/feed.rdf"},
    {"id": "impress_watch", "name": "Impress Watch", "section": "01 / 02",
     "url": "https://www.watch.impress.co.jp/data/rss/1.0/ipw/feed.rdf"},
]

USER_AGENT = "Mozilla/5.0 (compatible; Daily-News-RSS/1.0; +https://github.com/hatorihb/Daily-News)"
MAX_ITEMS_PER_FEED = 50
SUMMARY_CHARS = 160
DATE_FIELDS = ("pubDate", "date", "published", "updated", "issued", "modified")


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def child(elem, name):
    for c in elem:
        if local(c.tag) == name:
            return c
    return None


def text_of(elem, *names):
    for name in names:
        c = child(elem, name)
        if c is not None and (c.text or "").strip():
            return c.text.strip()
    return ""


def clean(s):
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s):
    """RFC 822（RSS 2.0）と ISO 8601（RDF / Atom）の両方を受け付ける。タイムゾーンなしは JST とみなす。"""
    s = (s or "").strip()
    if not s:
        return None
    dt = None
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt


def decode_xml(raw):
    """XML 宣言の encoding で文字列化してから渡す（expat は Shift_JIS 等のマルチバイトを直接扱えないため）。"""
    head = raw[:200].decode("ascii", errors="ignore")
    m = re.search(r'encoding=["\']([A-Za-z0-9_\-]+)["\']', head)
    enc = m.group(1) if m else "utf-8"
    try:
        text = raw.decode(enc, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    return re.sub(r"^\s*<\?xml[^>]*\?>", "", text, count=1)


def link_of(item):
    link = text_of(item, "link")
    if link:
        return link
    for c in item:
        if local(c.tag) == "link" and c.get("href") and c.get("rel", "alternate") == "alternate":
            return c.get("href")
    for key, val in item.attrib.items():
        if local(key) == "about":
            return val
    return ""


def cvss_of(item):
    """JVN の sec:cvss など、score 属性を持つ cvss 要素があれば最大値を返す。"""
    scores = []
    for e in item.iter():
        if local(e.tag).lower() == "cvss" and e.get("score"):
            try:
                scores.append(float(e.get("score")))
            except ValueError:
                pass
    return max(scores) if scores else None


def parse_feed(raw):
    root = ET.fromstring(decode_xml(raw))
    items = []
    for item in root.iter():
        if local(item.tag) not in ("item", "entry"):
            continue
        items.append({
            "title": clean(text_of(item, "title")),
            "link": link_of(item).strip(),
            "date": parse_date(next((d for d in (text_of(item, f) for f in DATE_FIELDS) if d), "")),
            "summary": clean(text_of(item, "description", "summary", "encoded", "content")),
            "cvss": cvss_of(item),
        })
    return items


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/rdf+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    last_err = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001 — 失敗理由をステータス表に出すため全て拾う
            last_err = e
    raise last_err


def describe_error(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}"
    msg = str(getattr(e, "reason", "") or e)
    return type(e).__name__ + (f": {msg[:80]}" if msg else "")


def collect(feeds, since, until, loader):
    results = []
    for feed in feeds:
        r = {**feed, "status": "OK", "error": "", "total": 0, "no_date": 0, "items": []}
        try:
            items = parse_feed(loader(feed))
        except Exception as e:  # noqa: BLE001
            r["status"], r["error"] = "FAILED", describe_error(e)
            results.append(r)
            continue
        r["total"] = len(items)
        in_window = []
        for it in items:
            if it["date"] is None:
                r["no_date"] += 1
            elif since <= it["date"] <= until:
                in_window.append(it)
        in_window.sort(key=lambda it: it["date"], reverse=True)
        r["items"] = in_window[:MAX_ITEMS_PER_FEED]
        r["in_window"] = len(in_window)
        results.append(r)
    return results


def render(results, today, since, now):
    out = [
        f"# RSS事前取得結果（{today}）",
        "",
        f"- 取得時刻: {now.astimezone(JST):%Y-%m-%d %H:%M} JST",
        f"- 対象期間: {since.astimezone(JST):%Y-%m-%d %H:%M} JST 以降の公開分",
        "- 各記事の日時は公開日時（JST）。`card-date` にはこの日付を使うこと。",
        "",
        "## 取得ステータス",
        "",
        "| フィード | 対象セクション | 結果 | 全件 | 対象期間内 |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        if r["status"] == "OK":
            out.append(f"| {r['name']} | {r['section']} | OK | {r['total']} | {r['in_window']} |")
        else:
            out.append(f"| {r['name']} | {r['section']} | FAILED ({r['error']}) | - | - |")
    sec = [r for r in results if r.get("security")]
    if sec and all(r["status"] != "OK" for r in sec):
        out += ["", "**警告: セキュリティ系フィード（Security NEXT / JVN / 窓の杜）が全て取得失敗。"
                "site: 指定の Web 検索で補完すること。**"]
    for r in results:
        if r["status"] != "OK":
            continue
        out += ["", f"## {r['name']}（{r['section']}）", ""]
        if not r["items"]:
            out.append("（対象期間内の記事なし）")
            continue
        if r["in_window"] > len(r["items"]):
            out.append(f"（対象期間内 {r['in_window']} 件のうち新しい順に {len(r['items'])} 件を表示）")
        for it in r["items"]:
            cvss = f" | CVSS {it['cvss']:.1f}" if it["cvss"] is not None else ""
            out.append(f"- {it['date'].astimezone(JST):%Y-%m-%d %H:%M} | {it['title']}{cvss} | {it['link']}")
            if it["summary"]:
                s = it["summary"]
                out.append(f"  概要: {s[:SUMMARY_CHARS]}{'…' if len(s) > SUMMARY_CHARS else ''}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--today", help="レポート日付 YYYY-MM-DD（省略時は JST の今日）")
    ap.add_argument("--out", default="rss-digest.md")
    ap.add_argument("--hours", type=int, default=30, help="現在時刻から遡る時間（既定 30）")
    ap.add_argument("--fixtures", help="テスト用: {feed_id}.xml を読むディレクトリ（ネットワークに出ない）")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    today = args.today or now.astimezone(JST).strftime("%Y-%m-%d")
    # card-date は「レポート日−1 以降」しか許されないので、遡りは前日 00:00 JST で打ち止める
    prev_midnight = datetime.fromisoformat(today).replace(tzinfo=JST) - timedelta(days=1)
    since = max(now - timedelta(hours=args.hours), prev_midnight)
    until = now + timedelta(hours=2)  # フィード側の時刻ずれを少しだけ許容

    if args.fixtures:
        def loader(feed):
            with open(os.path.join(args.fixtures, f"{feed['id']}.xml"), "rb") as f:
                return f.read()
    else:
        def loader(feed):
            return fetch(feed["url"])

    results = collect(FEEDS, since, until, loader)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(results, today, since, now))

    summary = [{"feed": r["name"], "status": r["status"], "error": r["error"],
                "total": r["total"], "in_window": r.get("in_window", 0)} for r in results]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for r in results:
        if r["status"] != "OK":
            print(f"::warning::RSS取得失敗: {r['name']} ({r['error']}) {r['url']}", file=sys.stderr)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("## RSS事前取得\n\n| フィード | 結果 | 全件 | 対象期間内 |\n|---|---|---|---|\n")
            for s in summary:
                result = "OK" if s["status"] == "OK" else f"FAILED ({s['error']})"
                f.write(f"| {s['feed']} | {result} | {s['total']} | {s['in_window']} |\n")


if __name__ == "__main__":
    main()

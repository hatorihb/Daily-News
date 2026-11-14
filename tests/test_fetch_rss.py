"""scripts/fetch_rss.py のテスト。ネットワークに出ず、一時ディレクトリに作ったフィードで検証する。

実行: python3 -m unittest discover -s tests -v
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "fetch_rss.py"

spec = importlib.util.spec_from_file_location("fetch_rss", SCRIPT)
fetch_rss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_rss)

JST = fetch_rss.JST
NOW = datetime.now(timezone.utc)
RECENT = NOW - timedelta(hours=3)
OLD = NOW - timedelta(days=3)


def rss2(items):
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link>"
        + (f"<pubDate>{format_datetime(d)}</pubDate>" if d else "")
        + "<description>&lt;p&gt;Body &amp;amp; more&lt;/p&gt;</description></item>"
        for t, link, d in items
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'.encode()


RDF_SJIS = f"""<?xml version="1.0" encoding="Shift_JIS"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:sec="http://jvn.jp/rss/mod_sec/3.0/">
<channel rdf:about="https://jvndb.jvn.jp/"><title>JVN</title></channel>
<item rdf:about="https://jvndb.jvn.jp/ja/contents/2026/JVNDB-2026-000001.html">
<title>GitLab におけるパストラバーサルの脆弱性</title>
<link>https://jvndb.jvn.jp/ja/contents/2026/JVNDB-2026-000001.html</link>
<description>認証なしでファイルを読まれる</description>
<dc:date>{RECENT.astimezone(JST).isoformat()}</dc:date>
<sec:cvss score="10.0" severity="Critical" version="3.0"/><sec:cvss score="9.3" version="4.0"/>
</item></rdf:RDF>""".encode("shift_jis")

ATOM = f"""<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>t</title>
<entry><title>「GitLab」に緊急パッチ</title>
<link rel="alternate" href="https://forest.watch.impress.co.jp/docs/news/2140081.html"/>
<updated>{RECENT.strftime('%Y-%m-%dT%H:%M:%SZ')}</updated><summary>CVSS 10.0</summary></entry></feed>""".encode()


class ParseTest(unittest.TestCase):
    def test_rss2_rfc822_dates_and_html_cleanup(self):
        items = fetch_rss.parse_feed(rss2([("A", "https://a/1", RECENT), ("B", "https://a/2", None)]))
        self.assertEqual([i["title"] for i in items], ["A", "B"])
        self.assertEqual(items[0]["link"], "https://a/1")
        self.assertEqual(int(items[0]["date"].timestamp()), int(RECENT.timestamp()))
        self.assertIsNone(items[1]["date"])
        self.assertEqual(items[0]["summary"], "Body & more")

    def test_rdf_shift_jis_with_cvss(self):
        (item,) = fetch_rss.parse_feed(RDF_SJIS)
        self.assertEqual(item["title"], "GitLab におけるパストラバーサルの脆弱性")
        self.assertEqual(item["cvss"], 10.0)  # 複数ある場合は最大値
        self.assertEqual(item["date"].utcoffset(), timedelta(hours=9))

    def test_atom_link_href_and_z_suffix(self):
        (item,) = fetch_rss.parse_feed(ATOM)
        self.assertEqual(item["link"], "https://forest.watch.impress.co.jp/docs/news/2140081.html")
        self.assertEqual(item["date"].utcoffset(), timedelta(0))

    def test_naive_date_is_treated_as_jst(self):
        self.assertEqual(fetch_rss.parse_date("2026-09-27T10:00:00").utcoffset(), timedelta(hours=9))
        self.assertIsNone(fetch_rss.parse_date("not a date"))

    def test_error_labels(self):
        http = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)
        self.assertEqual(fetch_rss.describe_error(http), "HTTP 403")
        try:
            fetch_rss.parse_feed(b"<html><<")
        except Exception as e:  # noqa: BLE001
            # ParseError も .code を持つが、HTTP エラーと誤表示しないこと
            self.assertTrue(fetch_rss.describe_error(e).startswith("ParseError"))
        else:
            self.fail("broken XML should raise")


class CollectRenderTest(unittest.TestCase):
    def feeds(self):
        return [
            {"id": "a", "name": "Feed A", "section": "03 AWS", "url": "https://a"},
            {"id": "sec1", "name": "Sec 1", "section": "04", "security": True, "url": "https://s1"},
            {"id": "sec2", "name": "Sec 2", "section": "04", "security": True, "url": "https://s2"},
        ]

    def test_window_filter_and_failures(self):
        data = {"a": rss2([("new", "https://a/new", RECENT), ("old", "https://a/old", OLD), ("nodate", "https://a/x", None)]),
                "sec1": b"<broken", "sec2": RDF_SJIS}
        since, until = NOW - timedelta(hours=30), NOW + timedelta(hours=2)
        res = {r["id"]: r for r in fetch_rss.collect(self.feeds(), since, until, lambda f: data[f["id"]])}
        self.assertEqual((res["a"]["total"], res["a"]["in_window"], res["a"]["no_date"]), (3, 1, 1))
        self.assertEqual([i["title"] for i in res["a"]["items"]], ["new"])
        self.assertEqual(res["sec1"]["status"], "FAILED")
        self.assertEqual(res["sec2"]["status"], "OK")

        md = fetch_rss.render(list(res.values()), "2026-09-27", since, NOW)
        self.assertIn("| Feed A | 03 AWS | OK | 3 | 1 |", md)
        self.assertIn("CVSS 10.0", md)
        self.assertNotIn("全て取得失敗", md)  # セキュリティ系が1本でも生きていれば警告しない

    def test_warns_when_every_security_feed_fails(self):
        since, until = NOW - timedelta(hours=30), NOW + timedelta(hours=2)
        results = fetch_rss.collect(self.feeds(), since, until, lambda f: b"<broken" if f.get("security") else rss2([]))
        self.assertIn("全て取得失敗", fetch_rss.render(results, "2026-09-27", since, NOW))


class CliTest(unittest.TestCase):
    def test_cli_with_fixtures_and_prev_midnight_floor(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "aws.xml").write_bytes(rss2([("Bedrock adds X", "https://aws/x", RECENT)]))
            (Path(d) / "jvn.xml").write_bytes(RDF_SJIS)
            (Path(d) / "madonomori.xml").write_bytes(ATOM)
            out = Path(d) / "digest.md"
            today = NOW.astimezone(JST).strftime("%Y-%m-%d")
            env = {k: v for k, v in os.environ.items() if k != "GITHUB_STEP_SUMMARY"}
            proc = subprocess.run(
                [sys.executable, "-I", str(SCRIPT), "--fixtures", d, "--out", str(out), "--today", today, "--hours", "100"],
                capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)  # フィードが欠けていても失敗しない
            md = out.read_text(encoding="utf-8")
            prev = (datetime.fromisoformat(today) - timedelta(days=1)).strftime("%Y-%m-%d")
            # card-date は「レポート日−1」以降しか許されないので、遡りは前日 00:00 JST で打ち止め
            self.assertIn(f"対象期間: {prev} 00:00 JST", md)
            self.assertIn("Bedrock adds X", md)
            self.assertIn("「GitLab」に緊急パッチ", md)
            self.assertIn("| Security NEXT | 04 セキュリティ | FAILED (FileNotFoundError", md)


if __name__ == "__main__":
    unittest.main()

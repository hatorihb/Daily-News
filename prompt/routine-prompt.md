今日の日付を確認し、過去24時間以内に発表されたAI・AWS・国内IT業界のアップデート情報を収集して、HTMLレポートをリポジトリにコミットしてください。

## 手順

### 1. 日付確認（必須：Bash ツールで実行すること）

**最初に必ず以下のコマンドを Bash ツールで実行し、その raw 出力をそのまま TODAY として使うこと。**
セッションのコンテキスト日付・モデルの知識・推測から日付を判断してはならない。

```bash
TZ=Asia/Tokyo date +%Y-%m-%d
```

コマンドの出力（例: `2026-05-30`）が TODAY。以降の検索クエリ・ファイル名・レポート本文にはこの値のみを使う。UTCの`date`コマンドは使わないこと（JST朝の実行でUTC前日になりレポート日付がずれる）。

**既存ファイルの確認は必ず Bash 実行後に行うこと：**
`reports/tech-report-{TODAY}.html` が既に存在する場合のみスキップしてよい。
Bash 実行前にコンテキスト日付から推測した日付でファイルの存在確認をしてはならない。

### 2. Web検索（最大8回）
以下のクエリで検索し、過去24時間以内の情報のみを抽出する。

1. `AI new model feature release announcement {YYYY-MM-DD}`
2. `生成AI LLM アップデート 新機能 今日 {YYYY-MM-DD}`
3. `AWS new feature release {YYYY-MM-DD} site:aws.amazon.com`
4. `AWS アップデート 新機能 今日 {YYYY-MM-DD}`
5. `日本企業 DX AI活用 新発表 {YYYY-MM-DD}`
6. `cybersecurity vulnerability CVE breach incident {YYYY-MM-DD}`
7. `セキュリティ 不正アクセス 脆弱性 インシデント {YYYY-MM-DD}`
8. `情報漏洩 サイバー攻撃 ランサムウェア 標的型攻撃 {YYYY-MM-DD}`

検索後、重要なページを2〜3件fetchして詳細を確認する。
AWS What's New（https://aws.amazon.com/jp/about-aws/whats-new/）は必ず1件fetchすること。
aws.amazon.com が 403 を返した場合は `https://www.amazonaws.cn/en/new/2026/` を代替として使う。
国内IT・DX情報は以下のソースを優先的にfetchする：
- ITmedia NEWS（https://www.itmedia.co.jp/news/）
- 日経クロステック（https://xtech.nikkei.com/）
- @IT（https://atmarkit.itmedia.co.jp/）
- ZDNet Japan（https://japan.zdnet.com/）
セキュリティ情報は以下のソースを優先的にfetchする：
- ITmedia NEWS（https://www.itmedia.co.jp/news/）
- Security NEXT（https://www.security-next.com/）
- 日本のCERT/CC（https://jvndb.jvn.jp/）

**除外ルール：**
- 公開日が24時間以上前の記事は掲載しない
- URLが確認できない情報は掲載しない
- 情報が少なくても古い情報で水増ししない
- 各カードの説明文は折り畳み表示のため、3〜5文（150字程度）まで詳しく記載する

**日付確認の注意点：**
- 記事の公開日は URL パス（例: `/2026/05/24/`）や記事内の日付で必ず確認する。検索結果のサマリーが示す日付は不正確な場合がある
- Google I/O などの大型イベント直後は、イベント当日の発表（数日前）と各機能の GA（一般提供開始）日が異なる。掲載するのは GA または新規記事の公開日が24時間以内のものに限る
- `card-date` には「掲載する記事・ページの公開日」を使う。元の発表が数日前でも、その日付に公開された新規記事を出典とする場合はその記事の公開日で構わない

### 3. HTMLファイルを生成してコミット

ファイル名: `reports/tech-report-{YYYY-MM-DD}.html`

以下のHTMLテンプレートの `{{ }}` 部分を収集した情報で置換してファイルを作成し、`claude/daily-report` ブランチにコミットする。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DX・AI・AWS Update</title>
<style>
:root{
  --black:#0a0a0a;
  --white:#ffffff;
  --red:#E60012;
  --gray:#f2f2f2;
  --mid:#888;
  --border:#e0e0e0;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family:'Helvetica Neue','Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;
  background:var(--white);
  color:var(--black);
  font-size:16px;
  line-height:1.6;
}
a{color:inherit;text-decoration:none}
header{background:var(--black);color:var(--white);padding:4rem 0 3.5rem}
.container{max-width:960px;margin:0 auto;padding:0 2rem}
.header-label{font-size:.7rem;font-weight:700;letter-spacing:.25em;color:var(--red);text-transform:uppercase;margin-bottom:1.25rem}
h1{font-size:clamp(2rem,5vw,3.5rem);font-weight:900;line-height:1.05;letter-spacing:-.02em;margin-bottom:1.5rem}
.header-date{font-size:.8rem;letter-spacing:.15em;color:#888;font-weight:400}
nav{border-bottom:2px solid var(--black);background:var(--white);position:sticky;top:0;z-index:100}
nav .container{display:flex;gap:0;overflow-x:auto}
.nav-link{font-size:.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--mid);padding:1rem 1.5rem;border-right:1px solid var(--border);white-space:nowrap;transition:color .15s,background .15s}
.nav-link:first-child{border-left:1px solid var(--border)}
.nav-link:hover{color:var(--black);background:var(--gray)}
main{padding:0}
.section{border-bottom:1px solid var(--border)}
.section-header{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:1.5rem;padding:3rem 0 2rem;border-bottom:1px solid var(--border)}
.section-num{font-size:4rem;font-weight:900;color:var(--gray);line-height:1;letter-spacing:-.04em;min-width:4rem;text-align:right}
.section-title{font-size:clamp(1.1rem,2.5vw,1.5rem);font-weight:900;letter-spacing:-.01em;line-height:1.2}
.section-title span{display:block;font-size:.7rem;font-weight:400;letter-spacing:.15em;text-transform:uppercase;color:var(--mid);margin-bottom:.4rem}
.section-domestic .section-num{color:#ffe0e0}
.section-title{color:var(--red)}
.card{display:grid;grid-template-columns:1fr;border-bottom:1px solid var(--border);padding:2rem 0}
.card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap}
.card-service{font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--mid)}
.card-badges{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
.impact{font-size:.65rem;font-weight:700;letter-spacing:.08em;padding:.2rem .6rem;text-transform:uppercase}
.impact-high{background:var(--red);color:var(--white)}
.impact-medium{background:var(--black);color:var(--white)}
.impact-low{background:var(--gray);color:var(--black)}
.card-date{font-size:.7rem;color:var(--mid);letter-spacing:.05em}
.card-title{font-size:clamp(1rem,2vw,1.2rem);font-weight:800;line-height:1.3;letter-spacing:-.01em;margin-bottom:.5rem}
.card-title a{border-bottom:2px solid transparent;transition:border-color .15s}
.card-title a:hover{border-bottom-color:var(--black)}
.section-domestic .card-title a:hover{border-bottom-color:var(--red)}
details{margin-top:.75rem}
summary{list-style:none;display:flex;align-items:center;gap:.5rem;cursor:pointer;font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mid);width:fit-content;padding:.25rem 0;border-bottom:1px solid var(--border);transition:color .15s,border-color .15s}
summary::-webkit-details-marker{display:none}
summary::before{content:'';display:inline-block;width:.5rem;height:.5rem;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(-45deg);transition:transform .2s;flex-shrink:0}
details[open] summary::before{transform:rotate(45deg);margin-top:-.25rem}
summary:hover{color:var(--black);border-color:var(--black)}
.section-domestic summary:hover{color:var(--red);border-color:var(--red)}
.card-desc{margin-top:1rem;font-size:.9rem;line-height:1.9;color:#333;max-width:680px}
.empty-note{padding:2rem 0;font-size:.9rem;color:var(--mid);letter-spacing:.05em}
footer{background:var(--black);color:#555;padding:2.5rem 0;font-size:.72rem;letter-spacing:.1em}
footer .container{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem}
.footer-brand{font-weight:900;font-size:1rem;color:var(--white);letter-spacing:-.01em}
@media(max-width:640px){h1{font-size:2rem}.section-num{font-size:2.5rem;min-width:2.5rem}.nav-link{padding:.75rem 1rem}header{padding:2.5rem 0 2rem}}
@media print{nav,footer{display:none}.card{break-inside:avoid}}
</style>
</head>
<body>

<header>
  <div class="container">
    <h1>DX・AI・AWS Update</h1>
    <p class="header-date">{YYYY} — {MM} — {DD} &nbsp;&nbsp;/&nbsp;&nbsp; Past 24 Hours</p>
  </div>
</header>

<nav>
  <div class="container">
    <a class="nav-link" href="#domestic">01 &nbsp; 国内 IT・DX</a>
    <a class="nav-link" href="#ai">02 &nbsp; AI</a>
    <a class="nav-link" href="#aws">03 &nbsp; AWS</a>
    <a class="nav-link" href="#security">04 &nbsp; セキュリティ</a>
  </div>
</nav>

<main>

  <!-- 01 国内IT・DX -->
  <section class="section section-domestic" id="domestic">
    <div class="container">
      <div class="section-header">
        <div class="section-num">01</div>
        <div>
          <div class="section-title">
            <span>Domestic IT / DX</span>
            国内 IT・DX<br>最新動向
          </div>
        </div>
      </div>
      <!-- 国内ITカードをここに繰り返し挿入：
      <div class="card">
        <div class="card-top">
          <div class="card-service">企業名・組織名</div>
          <div class="card-badges">
            <span class="impact impact-high">重要度 高</span>
            <span class="card-date">YYYY-MM-DD</span>
          </div>
        </div>
        <div class="card-title"><a href="URL" target="_blank" rel="noopener">タイトル</a></div>
        <details>
          <summary>詳細を表示</summary>
          <p class="card-desc">説明文（3〜5文）</p>
        </details>
      </div>
      -->
      <!-- アップデートなし時: <p class="empty-note">本日は過去24時間以内の新しいアップデートは確認されませんでした。</p> -->
    </div>
  </section>

  <!-- 02 AI -->
  <section class="section section-ai" id="ai">
    <div class="container">
      <div class="section-header">
        <div class="section-num">02</div>
        <div>
          <div class="section-title">
            <span>Artificial Intelligence</span>
            AI 最新<br>アップデート
          </div>
        </div>
      </div>
      <!-- AIカードをここに繰り返し挿入（card-title a:hoverは黒） -->
      <!-- アップデートなし時: <p class="empty-note">本日は過去24時間以内の新しいアップデートは確認されませんでした。</p> -->
    </div>
  </section>

  <!-- 03 AWS -->
  <section class="section section-aws" id="aws">
    <div class="container">
      <div class="section-header">
        <div class="section-num">03</div>
        <div>
          <div class="section-title">
            <span>Amazon Web Services</span>
            AWS 最新<br>アップデート
          </div>
        </div>
      </div>
      <!-- AWSカードをここに繰り返し挿入 -->
      <!-- アップデートなし時: <p class="empty-note">本日は過去24時間以内の新しいアップデートは確認されませんでした。</p> -->
    </div>
  </section>

  <!-- 04 セキュリティ -->
  <section class="section section-security" id="security">
    <div class="container">
      <div class="section-header">
        <div class="section-num">04</div>
        <div>
          <div class="section-title">
            <span>Cybersecurity</span>
            セキュリティ<br>最新動向
          </div>
        </div>
      </div>
      <!-- セキュリティカードをここに繰り返し挿入 -->
      <!-- アップデートなし時: <p class="empty-note">本日は過去24時間以内の新しいアップデートは確認されませんでした。</p> -->
    </div>
  </section>

</main>

<footer>
  <div class="container">
    <span class="footer-brand">DX・AI・AWS Update</span>
    <span>{YYYY-MM-DD} &nbsp; 過去24時間以内のアップデートを自動収集。情報の正確性は各リンク先をご確認ください。</span>
  </div>
</footer>

</body>
</html>
```

### 4. コミット
```bash
git checkout -b claude/daily-report 2>/dev/null || git checkout claude/daily-report
mkdir -p reports
# 上記HTMLを reports/tech-report-{YYYY-MM-DD}.html として保存
git add reports/tech-report-{YYYY-MM-DD}.html
git commit -m "report: AI・AWS daily report {YYYY-MM-DD}"
git push origin claude/daily-report
```

リポジトリ: https://github.com/hatorihb/Daily-News

アップデートが0件の場合も、「本日は過去24時間以内の新しいアップデートは確認されませんでした」と記載したHTMLをコミットすること。

今日の日付を確認し、過去24時間以内に発表されたAI・AWS・国内IT業界・セキュリティのアップデート情報を収集して、HTMLレポートをリポジトリにコミットしてください。

## 手順

### 1. 日付確認【必須・最初に実行】

> ⚠️ **重要：** `system-reminder` や会話コンテキストに表示される "Today's date" は **UTC ベースであり日本時間ではない**。その値を使ってはいけない。
> 必ず以下の Bash コマンドを**実際に実行**し、その出力結果を日付として使用すること。コマンドを実行せずに日付を決定することは禁止。

```bash
TZ=Asia/Tokyo date +%Y-%m-%d
```

このコマンドの出力（例: `2026-05-19`）を `{YYYY-MM-DD}` として、以降のすべての手順に使用する。

### 2. Web検索（最大8回）
以下のクエリで検索し、過去24時間以内の情報のみを抽出する。
`{YYYY-MM-DD-1}` は前日の日付（例：今日が2026-05-17なら2026-05-16）を表す。

1. `AI new model feature release announcement {YYYY-MM-DD} OR {YYYY-MM-DD-1}`
2. `生成AI LLM アップデート 新機能 {YYYY-MM-DD} OR {YYYY-MM-DD-1}`
3. `AWS new feature release {YYYY-MM-DD} OR {YYYY-MM-DD-1} site:aws.amazon.com`
4. `AWS アップデート 新機能 {YYYY-MM-DD} OR {YYYY-MM-DD-1}`
5. `日本企業 DX AI活用 新発表 {YYYY-MM-DD} OR {YYYY-MM-DD-1}`
6. `site:nikkei.com OR site:itmedia.co.jp OR site:sbbit.jp AI 導入 発表 {YYYY-MM-DD} OR {YYYY-MM-DD-1}`
7. `セキュリティ 脆弱性 情報流出 サイバー攻撃 {YYYY-MM-DD} OR {YYYY-MM-DD-1} site:security-next.com OR site:internet.watch.impress.co.jp`
8. `site:bleepingcomputer.com OR site:thehackernews.com OR site:techcrunch.com AI security CVE {YYYY-MM-DD} OR {YYYY-MM-DD-1}`

検索後、重要なページを2〜3件fetchして詳細を確認する。
AWS What's New（https://aws.amazon.com/jp/about-aws/whats-new/）は必ず1件fetchすること。

**除外ルール：**
- 掲載できるのは card-date が当日（{YYYY-MM-DD}）または前日のいずれかの記事のみ。それより古い日付の記事は内容が重要でも掲載しない
- 各カードを書く前に必ず公開日を確認し、2日以上前であれば除外する
- URLが確認できない情報は掲載しない
- 情報が少なくても古い情報で水増ししない
- 各カードの説明文は折り畳み表示のため、3〜5文（150字程度）まで詳しく記載する

### 3. HTMLファイルを生成してコミット

ファイル名: `reports/tech-report-{YYYY-MM-DD}.html`

> ⚠️ **必須チェック：** HTML には必ず以下の **4 セクション**をすべて含めること。1 つでも欠けていたらコミットしてはいけない。
> 1. `id="domestic"` — 国内 IT・DX
> 2. `id="ai"` — AI
> 3. `id="aws"` — AWS
> 4. `id="security"` — セキュリティ ← **毎回忘れやすい。必ず含めること**

以下のHTMLテンプレートの `{{ }}` 部分を収集した情報で置換してファイルを作成し、`claude/daily-report` ブランチにコミットする。

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>hatorih's Daily Tech Report | 国内IT・DX &amp; AI &amp; AWS &amp; セキュリティ</title>
<style>
:root{
  --black:#0a0a0a;
  --white:#ffffff;
  --red:#E60012;
  --orange:#D84315;
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
.section-domestic .section-title{color:var(--red)}
.section-security .section-num{color:#fbe9e7}
.section-security .section-title{color:var(--orange)}
.card{display:grid;grid-template-columns:1fr;border-bottom:1px solid var(--border);padding:2rem 0}
.card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap}
.card-service{font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--mid)}
.card-badges{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
.impact{font-size:.65rem;font-weight:700;letter-spacing:.08em;padding:.2rem .6rem;text-transform:uppercase}
.impact-high{background:var(--red);color:var(--white)}
.impact-medium{background:var(--black);color:var(--white)}
.impact-low{background:var(--gray);color:var(--black)}
.impact-critical{background:var(--orange);color:var(--white)}
.card-date{font-size:.7rem;color:var(--mid);letter-spacing:.05em}
.card-title{font-size:clamp(1rem,2vw,1.2rem);font-weight:800;line-height:1.3;letter-spacing:-.01em;margin-bottom:.5rem}
.card-title a{border-bottom:2px solid transparent;transition:border-color .15s}
.card-title a:hover{border-bottom-color:var(--black)}
.section-domestic .card-title a:hover{border-bottom-color:var(--red)}
.section-security .card-title a:hover{border-bottom-color:var(--orange)}
details{margin-top:.75rem}
summary{list-style:none;display:flex;align-items:center;gap:.5rem;cursor:pointer;font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mid);width:fit-content;padding:.25rem 0;border-bottom:1px solid var(--border);transition:color .15s,border-color .15s}
summary::-webkit-details-marker{display:none}
summary::before{content:'';display:inline-block;width:.5rem;height:.5rem;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(-45deg);transition:transform .2s;flex-shrink:0}
details[open] summary::before{transform:rotate(45deg);margin-top:-.25rem}
summary:hover{color:var(--black);border-color:var(--black)}
.section-domestic summary:hover{color:var(--red);border-color:var(--red)}
.section-security summary:hover{color:var(--orange);border-color:var(--orange)}
.card-desc{margin-top:1rem;font-size:.9rem;line-height:1.9;color:#333;max-width:680px}
.no-update{padding:2rem 0;font-size:.9rem;color:var(--mid);line-height:1.9}
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
    <p class="header-label">hatorih's Daily Tech Report</p>
    <h1>国内IT・DX<br>AI &amp; AWS<br>&amp; セキュリティ</h1>
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
      <!-- 国内ITカードをここに繰り返し挿入。情報がない場合は以下を使用：
      <div class="no-update">本日は過去24時間以内の新しいアップデートは確認されませんでした。</div>

      カード例：
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
      <!-- AIカードをここに繰り返し挿入。情報がない場合は no-update クラスを使用 -->
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
      <!-- AWSカードをここに繰り返し挿入。情報がない場合は no-update クラスを使用 -->
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
            セキュリティ<br>重大トピック
          </div>
        </div>
      </div>
      <!-- セキュリティカードをここに繰り返し挿入。情報がない場合は no-update クラスを使用
           重要度バッジは impact-critical（緊急）/ impact-high / impact-medium を使い分ける

      カード例：
      <div class="card">
        <div class="card-top">
          <div class="card-service">製品名・企業名</div>
          <div class="card-badges">
            <span class="impact impact-critical">緊急</span>
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
    </div>
  </section>
</main>
<footer>
  <div class="container">
    <span class="footer-brand">hatorih's Daily Tech Report</span>
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
git commit -m "report: hatorih's Daily Tech Report {YYYY-MM-DD}"
git push origin claude/daily-report
```

リポジトリ: https://github.com/hatorihb/Daily-News

アップデートが0件の場合も、「本日は過去24時間以内の新しいアップデートは確認されませんでした」と記載したHTMLをコミットすること。

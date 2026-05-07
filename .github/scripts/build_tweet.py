import os, re, time, requests
from bs4 import BeautifulSoup
from requests_oauthlib import OAuth1

html_file = os.environ['REPORT_FILE']
date_str  = os.environ['REPORT_DATE']
url       = os.environ['REPORT_URL']

with open(html_file, encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

def shorten(title, max_len=24):
    for sep in [' — ', '—', ' - ']:
        if sep in title:
            cand = title.split(sep)[0].strip()
            if len(cand) >= 10:
                title = cand
                break
    if len(title) <= max_len:
        return title
    for i in range(max_len, max(max_len - 6, 8), -1):
        if title[i] in '、。（】 ':
            return title[:i] + '…'
    return title[:max_len] + '…'

def extract_items(section_id, limit=2):
    section = soup.find('section', id=section_id)
    if not section:
        return []
    cards = section.find_all('div', class_='card')

    def priority(card):
        if card.find(class_='impact-high'):   return 0
        if card.find(class_='impact-medium'): return 1
        return 2

    results = []
    for card in sorted(cards, key=priority)[:limit]:
        a = card.find(class_='card-title')
        if a:
            a = a.find('a')
        if a:
            results.append(shorten(a.get_text(strip=True)))
    return results

ai_items       = extract_items('ai',       2)
aws_items      = extract_items('aws',      2)
domestic_items = extract_items('domestic', 2)

mm_dd = date_str[5:].replace('-', '/')

lines = [
    f"🔥 DX・AI・AWS｜{mm_dd}",
    "",
    "今日の見逃せないアップデート👇",
    "",
]

if ai_items:
    for item in ai_items:
        lines.append(f"🤖 {item}")

if aws_items:
    if ai_items:
        lines.append("")
    for item in aws_items:
        lines.append(f"☁️ {item}")

if domestic_items:
    lines.append("")
    for item in domestic_items:
        lines.append(f"🇯🇵 {item}")

lines += [
    "",
    "詳細レポートはこちら👇",
    url,
    "",
    "#AI #AWS #生成AI #LLM #DX",
]

tweet = "\n".join(lines)
actual_len = len(re.sub(r'https?://\S+', 'x' * 23, tweet))
print(f"--- Tweet ({actual_len} weighted chars) ---\n{tweet}\n---")

auth = OAuth1(
    os.environ['X_API_KEY'],
    os.environ['X_API_SECRET'],
    os.environ['X_ACCESS_TOKEN'],
    os.environ['X_ACCESS_TOKEN_SECRET'],
)

for attempt in range(1, 4):
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        json={"text": tweet},
        auth=auth,
    )
    print(f"Attempt {attempt}: HTTP {resp.status_code} — {resp.text}")
    if resp.status_code == 201:
        tweet_id = resp.json().get('data', {}).get('id', '?')
        print(f"✅ Tweet posted! ID: {tweet_id}")
        break
    elif resp.status_code in (429, 503):
        wait = 30 * attempt
        print(f"Rate limited, waiting {wait}s...")
        time.sleep(wait)
    else:
        if attempt < 3:
            time.sleep(10 * attempt)
        else:
            print("❌ Tweet failed after 3 attempts. Skipping (report is still published).")
            raise SystemExit(0)

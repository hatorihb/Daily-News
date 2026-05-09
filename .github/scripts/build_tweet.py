import sys
import os
import re
import subprocess
import requests
from bs4 import BeautifulSoup

client_id     = os.environ['X_OAUTH2_CLIENT_ID']
client_secret = os.environ['X_OAUTH2_CLIENT_SECRET']
refresh_token = os.environ['X_OAUTH2_REFRESH_TOKEN']
gh_pat        = os.environ.get('GH_PAT', '')

# --- 1. Refresh OAuth 2.0 access token ---
print("[DIAG] Refreshing OAuth 2.0 access token...")
token_resp = requests.post(
    "https://api.twitter.com/2/oauth2/token",
    data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    },
    auth=(client_id, client_secret),
)
token_data = token_resp.json()
print(f"[DIAG] Token refresh status: {token_resp.status_code}")

if "error" in token_data:
    print(f"❌ Token refresh failed: {token_data}")
    sys.exit(1)

new_access_token  = token_data["access_token"]
new_refresh_token = token_data.get("refresh_token", refresh_token)
print("[DIAG] ✅ Access token refreshed")

# --- 2. Build tweet text ---
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
        if title[i] in '、。（》 ':
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
        if a: a = a.find('a')
        if a: results.append(shorten(a.get_text(strip=True)))
    return results

ai_items       = extract_items('ai',       2)
aws_items      = extract_items('aws',      2)
domestic_items = extract_items('domestic', 2)

mm_dd = date_str[5:].replace('-', '/')
lines = [f"\U0001f525 DX・AI・AWS｜{mm_dd}", "", "今日の見逃せないアップデート\U0001f447", ""]
if ai_items:
    for item in ai_items: lines.append(f"\U0001f916 {item}")
if aws_items:
    if ai_items: lines.append("")
    for item in aws_items: lines.append(f"☁️ {item}")
if domestic_items:
    lines.append("")
    for item in domestic_items: lines.append(f"\U0001f1ef\U0001f1f5 {item}")
lines += ["", "詳細レポートはこちら\U0001f447", url, "", "#AI #AWS #生成AI #LLM #DX"]

tweet = "\n".join(lines)
actual_len = len(re.sub(r'https?://\S+', 'x' * 23, tweet))
print(f"--- Tweet ({actual_len} weighted chars) ---\n{tweet}\n---")

# --- 3. Post tweet via OAuth 2.0 user context ---
print("[DIAG] Posting tweet via OAuth 2.0 user context...")
tweet_resp = requests.post(
    "https://api.twitter.com/2/tweets",
    headers={
        "Authorization": f"Bearer {new_access_token}",
        "Content-Type": "application/json",
    },
    json={"text": tweet},
)
print(f"[DIAG] POST /2/tweets status: {tweet_resp.status_code}")

if tweet_resp.status_code == 201:
    tweet_id = tweet_resp.json()["data"]["id"]
    print(f"✅ Tweet posted! ID: {tweet_id}")
elif tweet_resp.status_code == 403:
    body = tweet_resp.json()
    body_str = str(body).lower()
    if '187' in body_str or 'duplicate' in body_str:
        print("⚠️ Tweet already posted (duplicate). Treating as success.")
    else:
        print(f"❌ 403 Forbidden: {body}")
        sys.exit(1)
else:
    print(f"❌ POST /2/tweets failed: {tweet_resp.status_code} {tweet_resp.json()}")
    sys.exit(1)

# --- 4. Persist rotated refresh token to GitHub Secrets ---
if new_refresh_token and new_refresh_token != refresh_token and gh_pat:
    print("[DIAG] Refresh token rotated — updating GitHub Secrets...")
    result = subprocess.run(
        ["gh", "secret", "set", "X_OAUTH2_REFRESH_TOKEN",
         "--body", new_refresh_token,
         "--repo", "hatorihb/Daily-News"],
        env={**os.environ, "GH_TOKEN": gh_pat},
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("[DIAG] ✅ X_OAUTH2_REFRESH_TOKEN updated in GitHub Secrets")
    else:
        print(f"[DIAG] ⚠️  Failed to update token: {result.stderr.strip()}")

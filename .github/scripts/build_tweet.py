import sys
import os
import re
import requests
from requests_oauthlib import OAuth1, OAuth1Session
from bs4 import BeautifulSoup

api_key             = os.environ['X_API_KEY']
api_secret          = os.environ['X_API_SECRET']
access_token        = os.environ['X_ACCESS_TOKEN']
access_token_secret = os.environ['X_ACCESS_TOKEN_SECRET']

print(f"[DEBUG] X_API_KEY           : {api_key[:4]}...{api_key[-4:]} (len={len(api_key)})")
print(f"[DEBUG] X_API_SECRET        : {api_secret[:4]}...{api_secret[-4:]} (len={len(api_secret)})")
print(f"[DEBUG] X_ACCESS_TOKEN      : {access_token[:4]}...{access_token[-4:]} (len={len(access_token)})")
print(f"[DEBUG] X_ACCESS_TOKEN_SECRET: {access_token_secret[:4]}...{access_token_secret[-4:]} (len={len(access_token_secret)})")

# --- x-access-level check ---
auth1 = OAuth1(api_key, api_secret, access_token, access_token_secret)
diag_resp = requests.get("https://api.twitter.com/2/users/me", auth=auth1)
print(f"[DIAG] x-access-level header : {diag_resp.headers.get('x-access-level', '(not present)')}")
print(f"[DIAG] GET /2/users/me status : {diag_resp.status_code}")
if diag_resp.status_code != 200:
    print(f"[DIAG] GET /2/users/me body: {diag_resp.text}")
    sys.exit(1)
me = diag_resp.json()
print(f"[DIAG] Authenticated as: @{me['data']['username']} (id={me['data']['id']})")

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

# --- Direct POST via OAuth1Session (bypassing tweepy) ---
oauth = OAuth1Session(
    api_key,
    client_secret=api_secret,
    resource_owner_key=access_token,
    resource_owner_secret=access_token_secret,
)

resp = oauth.post(
    "https://api.twitter.com/2/tweets",
    json={"text": tweet},
)

print(f"[DIAG] POST /2/tweets status          : {resp.status_code}")
print(f"[DIAG] POST x-access-level            : {resp.headers.get('x-access-level', 'N/A')}")
print(f"[DIAG] POST x-rate-limit-remaining    : {resp.headers.get('x-rate-limit-remaining', 'N/A')}")
print(f"[DIAG] POST x-rate-limit-limit        : {resp.headers.get('x-rate-limit-limit', 'N/A')}")
print(f"[DIAG] POST content-type              : {resp.headers.get('content-type', 'N/A')}")
print(f"[DIAG] POST body                      : {resp.text}")

if resp.status_code == 201:
    data = resp.json()
    print(f"✅ Tweet posted! ID: {data['data']['id']}")
elif resp.status_code == 403:
    body_str = resp.text.lower()
    if '187' in body_str or 'duplicate' in body_str:
        print("⚠️ Duplicate tweet. Treating as success.")
        sys.exit(0)
    print(f"❌ 403 Forbidden")
    sys.exit(1)
else:
    print(f"❌ Unexpected status: {resp.status_code}")
    sys.exit(1)

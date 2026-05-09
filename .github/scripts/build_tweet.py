import sys
import tweepy
import os
import re
from bs4 import BeautifulSoup

api_key            = os.environ['X_API_KEY']
api_secret         = os.environ['X_API_SECRET']
access_token       = os.environ['X_ACCESS_TOKEN']
access_token_secret= os.environ['X_ACCESS_TOKEN_SECRET']

print(f"[DEBUG] X_API_KEY           : {api_key[:4]}...{api_key[-4:]} (len={len(api_key)})")
print(f"[DEBUG] X_API_SECRET        : {api_secret[:4]}...{api_secret[-4:]} (len={len(api_secret)})")
print(f"[DEBUG] X_ACCESS_TOKEN      : {access_token[:4]}...{access_token[-4:]} (len={len(access_token)})")
print(f"[DEBUG] X_ACCESS_TOKEN_SECRET: {access_token_secret[:4]}...{access_token_secret[-4:]} (len={len(access_token_secret)})")

client = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
)

print("[DIAG] Testing OAuth 1.0a authentication via get_me()...")
try:
    me = client.get_me(user_auth=True)
    print(f"[DIAG] ✅ Authentication OK — user: @{me.data.username} (id={me.data.id})")
except tweepy.errors.Unauthorized as e:
    print(f"[DIAG] ❌ Authentication FAILED (401) — Consumer Key/Secret or Access Token/Secret が間違っています")
    print(f"       detail: {e}")
    sys.exit(1)
except tweepy.errors.Forbidden as e:
    print(f"[DIAG] ⚠️  get_me() returned 403 — {e}")
except Exception as e:
    print(f"[DIAG] ⚠️  get_me() unexpected error: {type(e).__name__}: {e}")

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
    f"\U0001f525 DX・AI・AWS｜{mm_dd}",
    "",
    "今日の見逃せないアップデート\U0001f447",
    "",
]

if ai_items:
    for item in ai_items:
        lines.append(f"\U0001f916 {item}")

if aws_items:
    if ai_items:
        lines.append("")
    for item in aws_items:
        lines.append(f"☁️ {item}")

if domestic_items:
    lines.append("")
    for item in domestic_items:
        lines.append(f"\U0001f1ef\U0001f1f5 {item}")

lines += [
    "",
    "詳細レポートはこちら\U0001f447",
    url,
    "",
    "#AI #AWS #生成AI #LLM #DX",
]

tweet = "\n".join(lines)
actual_len = len(re.sub(r'https?://\S+', 'x' * 23, tweet))
print(f"--- Tweet ({actual_len} weighted chars) ---\n{tweet}\n---")


def _try_v1(tweet_text):
    """v1.1 API fallback. Returns True on success."""
    print("[DIAG] Trying v1.1 API (statuses/update) as fallback...")
    try:
        v1_auth = tweepy.OAuthHandler(api_key, api_secret)
        v1_auth.set_access_token(access_token, access_token_secret)
        v1_api = tweepy.API(v1_auth)
        result = v1_api.update_status(tweet_text)
        print(f"✅ Tweet posted via v1.1! ID: {result.id}")
        return True
    except tweepy.errors.Forbidden as e2:
        v1_body = ""
        if hasattr(e2, 'response') and e2.response is not None:
            try:
                v1_body = e2.response.json()
            except Exception:
                v1_body = e2.response.text
        print(f"❌ v1.1 also 403 — body: {v1_body}")
        print("ℹ️  error code 261 = App にwrite権限なし / error code 89 = Token期限切れ")
    except tweepy.TweepyException as e2:
        print(f"❌ v1.1 failed: {type(e2).__name__}: {e2}")
    return False


try:
    response = client.create_tweet(text=tweet, user_auth=True)
    print(f"✅ Tweet posted! ID: {response.data['id']}")
except tweepy.errors.Forbidden as e:
    body = ""
    if hasattr(e, 'response') and e.response is not None:
        try:
            body = e.response.json()
        except Exception:
            body = e.response.text
    body_str = str(body).lower()
    if '187' in body_str or 'duplicate' in body_str:
        print(f"⚠️ Tweet already posted (duplicate). Treating as success.")
        sys.exit(0)
    print(f"❌ v2 403 Forbidden — response body: {body}")
    if not _try_v1(tweet):
        print("ℹ️  Access Token に書き込み権限がない可能性があります。")
        print("   X Developer Portal でアプリ権限を Read+Write に設定して保存した後、")
        print("   Access Token を再生成し、GitHub Secrets を更新してください。")
        sys.exit(1)
except tweepy.errors.TweepyException as e:
    print(f"❌ Tweet failed: {type(e).__name__}: {e}")
    sys.exit(1)

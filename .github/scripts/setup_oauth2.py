#!/usr/bin/env python3
"""
One-time local setup: obtain OAuth 2.0 User Context tokens for daily-news-bot.
Run: python3 .github/scripts/setup_oauth2.py
"""
import tweepy
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID = "TU15MUF3YmhnM0tpMnlDYmtMdnU6MTpjaQ"
CLIENT_SECRET = input("X_OAUTH2_CLIENT_SECRET を貼り付けてください: ").strip()
REDIRECT_URI = "http://localhost:8080/callback"

handler = tweepy.OAuth2UserHandler(
    client_id=CLIENT_ID,
    redirect_uri=REDIRECT_URI,
    scope=["tweet.write", "tweet.read", "users.read", "offline.access"],
    client_secret=CLIENT_SECRET,
)

auth_url = handler.get_authorization_url()
print(f"\n認証URLをブラウザで開きます...")
print(f"URL: {auth_url}\n")
webbrowser.open(auth_url)

redirect_response = None

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global redirect_response
        redirect_response = "http://localhost:8080" + self.path
        self.send_response(200)
        self.end_headers()
        self.wfile.write("✅ 認証完了！このタブを閉じてください。".encode())
    def log_message(self, *_): pass

print("localhost:8080 で認証コードを待っています...")
server = HTTPServer(("localhost", 8080), _Handler)
server.handle_request()
server.server_close()

token = handler.fetch_token(redirect_response)
refresh_token = token.get("refresh_token", "")

print("\n" + "=" * 60)
print("✅ 取得完了！以下の値を GitHub Secrets に登録してください:")
print("=" * 60)
print(f"\n「Secret名」 X_OAUTH2_CLIENT_ID")
print(f"「Value」   {CLIENT_ID}")
print(f"\n「Secret名」 X_OAUTH2_CLIENT_SECRET")
print(f"「Value」   （入力したシークレット）")
print(f"\n「Secret名」 X_OAUTH2_REFRESH_TOKEN")
print(f"「Value」   {refresh_token}")
if not refresh_token:
    print("\n⚠️  refresh_token が含まれていません。")
    print("   offline.access スコープが有効か確認してください。")

import requests
import os
from flask import Flask, request
from decimal import Decimal

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook"

# ================= FORMAT =================
def format_precise(n):
    return format(Decimal(str(n)), ",")

# ================= MARKET =================
def get_market_data():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    
    res = requests.get(
        "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
        headers=headers
    ).json()
    
    total_mc = res["data"]["quote"]["USD"]["total_market_cap"]
    btc_dom = res["data"]["btc_dominance"]
    
    return total_mc, btc_dom

# ================= TELEGRAM =================
def send_message(chat_id, text):
    requests.post(
        f"{BASE_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
    )

# ================= ROUTES =================
@app.route("/")
def home():
    return "Bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        
        # ===== MARKET =====
        if text.startswith("/mc"):
            try:
                total, btc_dom = get_market_data()
                
                msg = f"""
📊 *CRYPTO MARKET*

💰 `{format_precise(total)}`
🧠 BTC Dom: {btc_dom:.2f}%
"""
                send_message(chat_id, msg)
            
            except Exception as e:
                send_message(chat_id, f"❌ {e}")
    
    return "ok"

@app.route("/setwebhook")
def set_webhook():
    return requests.get(f"{BASE_URL}/setWebhook?url={WEBHOOK_URL}").text

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

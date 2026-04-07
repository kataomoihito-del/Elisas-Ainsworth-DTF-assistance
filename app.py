import requests
import os
from flask import Flask, request
from decimal import Decimal

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/webhook"

STABLES = ["USDT", "USDC"]

# ================= FORMAT =================
def format_precise(n):
    return format(Decimal(str(n)), ",")

# ================= MARKET DATA =================
def get_market_data():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    
    res1 = requests.get(
        "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
        headers=headers
    ).json()
    
    total_mc = res1["data"]["quote"]["USD"]["total_market_cap"]
    btc_dom = res1["data"]["btc_dominance"]
    
    res2 = requests.get(
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
        headers=headers,
        params={"symbol": ",".join(STABLES), "convert": "USD"}
    ).json()["data"]
    
    stable_total = sum(res2[s]["quote"]["USD"]["market_cap"] for s in STABLES if s in res2)
    
    non_stable = total_mc - stable_total
    stable_pct = (stable_total / total_mc) * 100
    non_stable_pct = (non_stable / total_mc) * 100
    
    return total_mc, stable_total, non_stable, stable_pct, non_stable_pct, btc_dom

# ================= WALLET (DEBANK) =================
def get_wallet_data():
    if not WALLET_ADDRESS:
        raise Exception("Missing WALLET_ADDRESS")
    
    url = f"https://openapi.debank.com/v1/user/token_list?id={WALLET_ADDRESS}&is_all=true"
    
    res = requests.get(url).json()
    
    tokens = []
    total_value = 0
    
    for t in res:
        value = t.get("price", 0) * t.get("amount", 0)
        
        if value <= 1:  # lọc rác <1$
            continue
        
        total_value += value
        tokens.append({
            "symbol": t.get("symbol"),
            "amount": t.get("amount"),
            "value": value
        })
    
    # sort
    tokens.sort(key=lambda x: x["value"], reverse=True)
    
    # tính %
    for t in tokens:
        t["pct"] = (t["value"] / total_value) * 100 if total_value else 0
    
    return total_value, tokens

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
                total, stable, non_stable, sp, nsp, btc_dom = get_market_data()
                
                msg = f"""
📊 *CRYPTO MARKET OVERVIEW*

💰 Total Market Cap:
`{format_precise(total)}`

🟢 Stable (USDT + USDC):
`{format_precise(stable)}`
→ {sp:.2f}%

🔴 Non-Stable:
`{format_precise(non_stable)}`
→ {nsp:.2f}%

🧠 BTC Dominance:
{btc_dom:.2f}%
"""
                send_message(chat_id, msg)
            
            except Exception as e:
                send_message(chat_id, f"❌ Error: {e}")
        
        # ===== WALLET =====
        elif text.startswith("/wallet"):
            try:
                total, tokens = get_wallet_data()
                
                if total == 0:
                    send_message(chat_id, "❌ Ví rỗng")
                    return "ok"
                
                msg = "💼 *YOUR WALLET*\n\n"
                msg += f"📍 `{WALLET_ADDRESS}`\n\n"
                msg += f"💰 Total: `{format_precise(total)} USD`\n\n"
                
                for t in tokens[:10]:
                    msg += f"{t['symbol']}: `{format_precise(t['value'])}` ({t['pct']:.2f}%)\n"
                
                send_message(chat_id, msg)
            
            except Exception as e:
                send_message(chat_id, f"❌ Error: {e}")
    
    return "ok"

# ================= SET WEBHOOK =================
@app.route("/setwebhook")
def set_webhook():
    url = f"{BASE_URL}/setWebhook?url={WEBHOOK_URL}"
    return requests.get(url).text

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

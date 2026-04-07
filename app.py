import requests
import os
from flask import Flask, request
from decimal import Decimal

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CMC_API_KEY = os.environ.get("CMC_API_KEY")
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS")

ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN")
BSCSCAN_API_KEY = os.environ.get("BSCSCAN")

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

# ================= WALLET =================
def get_tokens(url, api_key):
    params = {
        "module": "account",
        "action": "tokentx",
        "address": WALLET_ADDRESS,
        "apikey": api_key
    }
    
    res = requests.get(url, params=params).json()
    
    tokens = {}
    
    if "result" not in res:
        return tokens
    
    for tx in res["result"]:
        symbol = tx.get("tokenSymbol") or "UNK"
        
        try:
            value = int(tx["value"]) / (10 ** int(tx["tokenDecimal"]))
        except:
            continue
        
        if tx["to"].lower() == WALLET_ADDRESS.lower():
            tokens[symbol] = tokens.get(symbol, 0) + value
        elif tx["from"].lower() == WALLET_ADDRESS.lower():
            tokens[symbol] = tokens.get(symbol, 0) - value
    
    return tokens

def get_wallet_data():
    tokens = {}

    # ETH
    eth = get_tokens("https://api.etherscan.io/api", ETHERSCAN_API_KEY)
    
    # BSC
    bsc = get_tokens("https://api.bscscan.com/api", BSCSCAN_API_KEY)
    
    # merge
    for d in [eth, bsc]:
        for k, v in d.items():
            tokens[k] = tokens.get(k, 0) + v
    
    # lọc
    tokens = {k: v for k, v in tokens.items() if v > 0}
    
    if not tokens:
        return 0, []
    
    # ===== GET PRICE =====
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    
    res = requests.get(
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
        headers=headers,
        params={"symbol": ",".join(tokens.keys()), "convert": "USDT"}
    ).json().get("data", {})
    
    total = 0
    result = []
    
    for sym, amount in tokens.items():
        if sym in res:
            price = res[sym]["quote"]["USDT"]["price"]
            value = amount * price
            total += value
            result.append((sym, value))
    
    result.sort(key=lambda x: x[1], reverse=True)
    
    final = []
    for sym, value in result:
        pct = (value / total) * 100 if total else 0
        final.append((sym, value, pct))
    
    return total, final

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
        
        # ===== WALLET =====
        elif text.startswith("/wallet"):
            try:
                total, tokens = get_wallet_data()
                
                if total == 0:
                    send_message(chat_id, "❌ Ví rỗng hoặc đọc fail")
                    return "ok"
                
                msg = f"💼 *WALLET*\n\n💰 `{format_precise(total)} USDT`\n\n"
                
                for sym, value, pct in tokens[:10]:
                    msg += f"{sym}: `{format_precise(value)}` ({pct:.2f}%)\n"
                
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

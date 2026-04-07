import requests
from flask import Flask
import os
from decimal import Decimal

app = Flask(__name__)

API_KEY = os.environ.get("CMC_API_KEY")
STABLES = ["USDT", "USDC"]

# ================= FORMAT =================
def format_precise(n):
    return format(Decimal(str(n)), ",")

# ================= DATA =================
def get_data():
    # total market
    url1 = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    headers = {"X-CMC_PRO_API_KEY": API_KEY}
    res1 = requests.get(url1, headers=headers).json()
    
    total_mc = res1["data"]["quote"]["USD"]["total_market_cap"]
    btc_dom = res1["data"]["btc_dominance"]
    
    # stable
    url2 = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": ",".join(STABLES), "convert": "USD"}
    res2 = requests.get(url2, headers=headers, params=params).json()["data"]
    
    stable_total = 0
    for s in STABLES:
        if s in res2:
            stable_total += res2[s]["quote"]["USD"]["market_cap"]
    
    non_stable = total_mc - stable_total
    
    stable_pct = (stable_total / total_mc) * 100
    non_stable_pct = (non_stable / total_mc) * 100
    
    return total_mc, stable_total, non_stable, stable_pct, non_stable_pct, btc_dom

# ================= ROUTE =================
@app.route("/mc")
def mc():
    try:
        total, stable, non_stable, sp, nsp, btc_dom = get_data()
        
        return f"""
        <html>
        <head>
            <title>Crypto Market Dashboard</title>
            <style>
                body {{
                    font-family: Arial;
                    background: #0f172a;
                    color: white;
                    text-align: center;
                    padding: 40px;
                }}
                .box {{
                    margin: 20px auto;
                    padding: 20px;
                    border-radius: 15px;
                    width: 60%;
                }}
                .total {{ background: #1e293b; }}
                .stable {{ background: #065f46; }}
                .nonstable {{ background: #7f1d1d; }}
                .bar {{
                    height: 30px;
                    border-radius: 10px;
                    overflow: hidden;
                    margin-top: 20px;
                }}
                .stable-bar {{
                    background: #10b981;
                    height: 100%;
                    float: left;
                }}
                .nonstable-bar {{
                    background: #ef4444;
                    height: 100%;
                    float: left;
                }}
            </style>
        </head>
        <body>

            <h1>🚀 Crypto Market Overview</h1>

            <div class="box total">
                <h2>Total Market Cap</h2>
                <h1>${format_precise(total)}</h1>
            </div>

            <div class="box stable">
                <h2>Stablecoins (USDT + USDC)</h2>
                <h1>{sp:.2f}%</h1>
                <p>${format_precise(stable)}</p>
            </div>

            <div class="box nonstable">
                <h2>Non-Stable Market</h2>
                <h1>{nsp:.2f}%</h1>
                <p>${format_precise(non_stable)}</p>
            </div>

            <div class="box total">
                <h2>Market Structure</h2>
                <div class="bar">
                    <div class="stable-bar" style="width:{sp}%"></div>
                    <div class="nonstable-bar" style="width:{nsp}%"></div>
                </div>
                <p>🟢 Stable | 🔴 Crypto</p>
            </div>

            <div class="box total">
                <h2>BTC Dominance</h2>
                <h1>{btc_dom:.2f}%</h1>
            </div>

        </body>
        </html>
        """
    
    except Exception as e:
        return str(e)

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

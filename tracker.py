import requests
import time
import json
import os

# ================= CONFIG =================

ETHERSCAN_API_KEY = "WU72V9CAX454C2PHCZW8Y5PHSAFTJN3M69"
HELIUS_API_KEY = "30ecb2e9-27e1-48b5-bc11-d1b4ea146ad9"

BOT_TOKEN = "8740637549:AAFMYNDNQWuGWsjQ9LnbxiZ9FAKQ45U-WdQ"
CHAT_ID = "7198809557"

ETH_WALLETS = [
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "0x45E71b7aA9bF61c62569a625b59D97ef818dd123",
    "0xb4607064cb897e54d915e07c76065dd2032ebd72",
    "0xdbd47f66aa2f00b3db03397f260ce9728298c495"
]

SOL_WALLETS = [
    "4ApxNC8pXeSmju22ZmdNAoCCcPykV6PTTzDxDsK7fyR8"
]

MIN_USD_ALERT = 20000
SLEEP_TIME = 20

BASELINE_FILE = "baseline.json"

# =============== STATE ====================

last_seen_eth = {}
last_seen_sol = {}

# ----------- Persistent baseline ----------

def load_baseline():
    global last_seen_eth, last_seen_sol
    if os.path.exists(BASELINE_FILE):
        try:
            with open(BASELINE_FILE, "r") as f:
                data = json.load(f)
                last_seen_eth = data.get("eth", {})
                last_seen_sol = data.get("sol", {})
        except Exception as e:
            print("Error loading baseline:", e)

def save_baseline():
    try:
        with open(BASELINE_FILE, "w") as f:
            json.dump({"eth": last_seen_eth, "sol": last_seen_sol}, f)
    except Exception as e:
        print("Error saving baseline:", e)

# =============== PRICE ====================

def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        return requests.get(url, timeout=10).json()["ethereum"]["usd"]
    except:
        return 3000


def get_sol_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        return requests.get(url, timeout=10).json()["solana"]["usd"]
    except:
        return 100


# ============== TELEGRAM ==================

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


# ============== ETH TRACKER ===============

def check_eth():
    print("ETH running...")  # added terminal print
    eth_price = get_eth_price()

    for wallet in ETH_WALLETS:
        try:
            url = f"https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address={wallet}&sort=desc&apikey={ETHERSCAN_API_KEY}"
            res = requests.get(url, timeout=10).json()

            if res.get("status") != "1":
                continue

            txs = res.get("result", [])
            if not txs:
                continue

            latest = txs[0]
            tx_hash = latest["hash"]

            if last_seen_eth.get(wallet) == tx_hash:
                continue

            last_seen_eth[wallet] = tx_hash
            save_baseline()

            value_eth = int(latest["value"]) / 1e18
            usd_value = value_eth * eth_price

            if usd_value >= MIN_USD_ALERT:
                direction = "IN" if latest["to"].lower() == wallet.lower() else "OUT"

                msg = f"""🚨 WHALE ALERT

Chain: ETH
Wallet: {wallet[:6]}...{wallet[-4:]}
Direction: {direction}
Amount: ${usd_value:,.0f}
TX: https://etherscan.io/tx/{tx_hash}
"""

                send_alert(msg)

        except Exception as e:
            print("ETH error:", e)


# ============== SOL TRACKER ===============

def check_solana():
    print("SOL running...")  # added terminal print
    sol_price = get_sol_price()

    for wallet in SOL_WALLETS:
        try:
            url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}"
            res = requests.get(url, timeout=10).json()

            if not res:
                continue

            latest = res[0]
            sig = latest["signature"]

            if last_seen_sol.get(wallet) == sig:
                continue

            last_seen_sol[wallet] = sig
            save_baseline()

            amount = 0
            for transfer in latest.get("nativeTransfers", []):
                amount += transfer.get("amount", 0)

            amount = amount / 1e9
            usd_value = amount * sol_price

            if usd_value >= MIN_USD_ALERT:
                msg = f"""🚨 WHALE ALERT

Chain: SOL
Wallet: {wallet[:6]}...{wallet[-4:]}
Amount: ${usd_value:,.0f}
TX: https://solscan.io/tx/{sig}
"""

                send_alert(msg)

        except Exception as e:
            print("SOL error:", e)


# ============== MAIN LOOP =================

print("Multi-chain whale tracker running...")

load_baseline()

msg = f"""💰 WHALE RADAR LIVE

Tracking big money across chains

ETH + SOL active
Min size: ${MIN_USD_ALERT:,}

Hunting whales...
"""
send_alert(msg)

while True:
    try:
        check_eth()
        check_solana()
        time.sleep(SLEEP_TIME)
    except Exception as e:
        print("Main error:", e)
        time.sleep(10)

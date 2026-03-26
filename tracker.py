import requests
import time
import json
import os

# ================= CONFIG =================

BOT_TOKEN = "8740637549:AAFMYNDNQWuGWsjQ9LnbxiZ9FAKQ45U-WdQ"
CHAT_ID = "7198809557"

BASE_WALLETS = [
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "0x45E71b7aA9bF61c62569a625b59D97ef818dd123",
    "0xb4607064cb897e54d915e07c76065dd2032ebd72",
    "0xdbd47f66aa2f00b3db03397f260ce9728298c495"
]

MIN_BASE_ALERT = 10  # minimum BASE tokens to trigger alert
SLEEP_TIME = 20
BASELINE_FILE = "baseline_base.json"

# Replace with working Alchemy or Infura Base RPC
BASE_RPC_URL = "https://base-mainnet.g.alchemy.com/v2/H52GBlzk3PI5VWXXkCk2i"
# or Infura
# BASE_RPC_URL = "https://base-mainnet.infura.io/v3/78e64af335294dfb8e5132bab943b024"

# =============== STATE ====================

last_seen_base = {}

# ----------- Persistent baseline ----------

def load_baseline():
    global last_seen_base
    if os.path.exists(BASELINE_FILE):
        try:
            with open(BASELINE_FILE, "r") as f:
                data = json.load(f)
                last_seen_base = data.get("base", {})
        except Exception as e:
            print("Error loading baseline:", e)

def save_baseline():
    try:
        with open(BASELINE_FILE, "w") as f:
            json.dump({"base": last_seen_base}, f)
    except Exception as e:
        print("Error saving baseline:", e)

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

# ============== BASE TRACKER ===============

def fetch_base_txs(wallet):
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "alchemy_getAssetTransfers",
        "params": [{
            "fromBlock": "0x0",
            "toAddress": wallet,
            "category": ["external"],
            "maxCount": "0x64"
        }]
    }
    try:
        res = requests.post(BASE_RPC_URL, json=payload, headers=headers, timeout=10).json()
        return res.get("result", {}).get("transfers", [])
    except Exception as e:
        print(f"Error fetching Base transactions for {wallet}: {e}")
        return []

def check_base():
    print("Base transaction tracker running...")
    for wallet in BASE_WALLETS:
        txs = fetch_base_txs(wallet)
        if not txs:
            continue

        for tx in reversed(txs):  # Oldest first
            tx_hash = tx.get("hash")
            if not tx_hash or last_seen_base.get(wallet) == tx_hash:
                continue

            last_seen_base[wallet] = tx_hash
            save_baseline()

            from_addr = tx.get("from")[:6] + "..." + tx.get("from")[-4:]
            to_addr = tx.get("to")[:6] + "..." + tx.get("to")[-4:]
            amount = float(tx.get("value") or 0)
            token = tx.get("asset") or "BASE"

            # Only alert if it's the BASE token and meets threshold
            if token.upper() != "BASE" or amount < MIN_BASE_ALERT:
                continue

            direction = "IN" if tx.get("to").lower() == wallet.lower() else "OUT"

            msg = f"""🚨 BASE ALERT

Wallet: {wallet[:6]}...{wallet[-4:]}
Direction: {direction}
From: {from_addr}
To: {to_addr}
Amount: {amount} {token}
TX: https://basescan.org/tx/{tx_hash}
"""
            send_alert(msg)

# ============== MAIN LOOP =================

print("Base transaction tracker starting...")
load_baseline()

send_alert("🚀 BASE TRANSACTION TRACKER LIVE\nTracking BASE token transactions on Base chain...")

while True:
    try:
        check_base()
        time.sleep(SLEEP_TIME)
    except Exception as e:
        print("Main loop error:", e)
        time.sleep(10)

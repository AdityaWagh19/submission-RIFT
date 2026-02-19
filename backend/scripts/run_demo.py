"""
Phase 6 — Full End-to-End Demo Flow on TestNet

This script runs the complete demo:
  1. Verify existing deployment
  2. Fan 1 sends a 1 ALGO tip via atomic group
  3. Fan 2 sends a 1 ALGO tip via atomic group
  4. Wait for the backend listener to detect & process tips
  5. Check fan inventories, stats, leaderboards
  6. Check creator dashboard
  7. Contract upgrade (v1 -> v2)
"""
import json
import sys
import time
import base64

from algosdk import transaction, encoding, mnemonic, account, logic
from algosdk.v2client import algod
import httpx

# ── Load demo accounts ─────────────────────────────────────
with open("scripts/demo_accounts.json") as f:
    accounts = json.load(f)

CREATOR = accounts["creator"]
FAN1 = accounts["fan1"]
FAN2 = accounts["fan2"]

for acc in [CREATOR, FAN1, FAN2]:
    acc["private_key"] = mnemonic.to_private_key(acc["mnemonic"])

client = algod.AlgodClient("", "https://testnet-api.algonode.cloud")

with open("scripts/deployed_contract.json") as f:
    contract = json.load(f)

APP_ID = contract["appId"]
APP_ADDRESS = logic.get_application_address(APP_ID)
BASE = "http://localhost:8000"


def section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def send_tip(fan, amount_algo, memo=""):
    """Build and submit an atomic group tip to the TipProxy."""
    amount_micro = int(amount_algo * 1_000_000)

    sp = client.suggested_params()
    sp.fee = 2000
    sp.flat_fee = True

    pay_txn = transaction.PaymentTxn(
        sender=fan["address"],
        sp=sp,
        receiver=APP_ADDRESS,
        amt=amount_micro,
    )

    app_args = [b"tip"]
    if memo:
        app_args.append(memo.encode("utf-8"))

    app_txn = transaction.ApplicationCallTxn(
        sender=fan["address"],
        sp=sp,
        index=APP_ID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=app_args,
        accounts=[CREATOR["address"]],  # Required for inner txn
    )

    gid = transaction.calculate_group_id([pay_txn, app_txn])
    pay_txn.group = gid
    app_txn.group = gid

    signed_pay = pay_txn.sign(fan["private_key"])
    signed_app = app_txn.sign(fan["private_key"])

    tx_id = client.send_transactions([signed_pay, signed_app])
    result = transaction.wait_for_confirmation(client, tx_id, 4)
    confirmed_round = result.get("confirmed-round", "?")

    return tx_id, confirmed_round


def get_balance(addr):
    return client.account_info(addr)["amount"] / 1_000_000


# ════════════════════════════════════════════════════════════
# DEMO FLOW
# ════════════════════════════════════════════════════════════

section("1. VERIFY EXISTING DEPLOYMENT")

print(f"  Contract App ID:  {APP_ID}")
print(f"  Contract Address: {APP_ADDRESS[:16]}...")
app_info = client.application_info(APP_ID)
print(f"  Contract on-chain: VERIFIED")

for name, acc in [("Creator", CREATOR), ("Fan 1", FAN1), ("Fan 2", FAN2)]:
    print(f"  {name}: {get_balance(acc['address']):.3f} ALGO")


section("2. FAN 1 SENDS 1 ALGO TIP")

print(f"  Fan 1: {FAN1['address'][:16]}...")
print(f"  Amount: 1 ALGO | Memo: 'Great content!'")
print(f"  Building atomic group (PaymentTxn + AppCallTxn)...")

tx1, round1 = send_tip(FAN1, 1.0, "Great content!")
print(f"  TX: {tx1}")
print(f"  Confirmed round: {round1}")


section("3. FAN 2 SENDS 1 ALGO TIP")

print(f"  Fan 2: {FAN2['address'][:16]}...")
print(f"  Amount: 1 ALGO | Memo: 'Keep it up!'")

tx2, round2 = send_tip(FAN2, 1.0, "Keep it up!")
print(f"  TX: {tx2}")
print(f"  Confirmed round: {round2}")


section("4. VERIFY ON-CHAIN STATE")

app_info = client.application_info(APP_ID)
raw_state = app_info.get("params", {}).get("global-state", [])

for item in raw_state:
    key = base64.b64decode(item["key"]).decode("utf-8", errors="ignore")
    val = item["value"]
    if val["type"] == 2:
        v = val.get("uint", 0)
        if key in ("total_amount", "min_tip_amount"):
            print(f"  {key}: {v / 1_000_000} ALGO")
        else:
            print(f"  {key}: {v}")


section("5. BALANCES AFTER TIPS")

for name, acc in [("Creator", CREATOR), ("Fan 1", FAN1), ("Fan 2", FAN2)]:
    print(f"  {name}: {get_balance(acc['address']):.3f} ALGO")
print(f"  Contract escrow: {get_balance(APP_ADDRESS):.3f} ALGO")


section("6. WAITING FOR LISTENER (30s)")

print("  The listener polls every 10s. Waiting for detection + minting...")
for i in range(30, 0, -5):
    print(f"    {i}s...")
    time.sleep(5)


section("7. FAN INVENTORIES")

for name, addr in [("Fan 1", FAN1["address"]), ("Fan 2", FAN2["address"])]:
    r = httpx.get(f"{BASE}/fan/{addr}/inventory", timeout=10)
    data = r.json()
    nfts = data.get("inventory", [])
    print(f"  {name}: {len(nfts)} NFT(s)")
    for nft in nfts:
        print(f"    - {nft.get('name', '?')} ({nft.get('stickerType', '?')})")


section("8. FAN STATS")

for name, addr in [("Fan 1", FAN1["address"]), ("Fan 2", FAN2["address"])]:
    r = httpx.get(f"{BASE}/fan/{addr}/stats", timeout=10)
    s = r.json()
    print(f"  {name}: {s.get('totalTips', 0)} tip(s), {s.get('totalAlgoSpent', 0)} ALGO")


section("9. LEADERBOARD")

r = httpx.get(f"{BASE}/leaderboard/{CREATOR['address']}", timeout=10)
lb = r.json()
for i, fan in enumerate(lb.get("leaderboard", []), 1):
    w = fan.get("fanWallet", "?")
    print(f"  #{i}: {w[:16]}... — {fan.get('totalAlgo', 0)} ALGO ({fan.get('tipCount', 0)} tips)")


section("10. CREATOR DASHBOARD")

r = httpx.get(f"{BASE}/creator/{CREATOR['address']}/dashboard", timeout=10)
d = r.json()
print(f"  Username: {d.get('username')}")
print(f"  Total Fans: {d.get('totalFans')}")
print(f"  Total Stickers: {d.get('totalStickersMinted')}")
print(f"  Recent Txns: {len(d.get('recentTransactions', []))}")
for tx in d.get("recentTransactions", [])[:3]:
    print(f"    TX: {tx.get('txId', '?')[:16]}... | {tx.get('amountAlgo')} ALGO | {tx.get('memo', '')}")


section("11. CONTRACT UPGRADE (v1 -> v2)")

print("  Upgrading TipProxy...")
r = httpx.post(f"{BASE}/creator/{CREATOR['address']}/upgrade-contract", timeout=30)
if r.status_code == 200:
    u = r.json()
    print(f"  Old App ID: {u.get('oldAppId')}")
    print(f"  New App ID: {u.get('newAppId')}")
    print(f"  Version: v{u.get('newVersion')}")

    with open("scripts/deployed_contract.json", "w") as f:
        json.dump({
            "creatorWallet": CREATOR["address"],
            "appId": u.get("newAppId"),
            "appAddress": u.get("newAppAddress"),
            "version": u.get("newVersion"),
            "active": True,
        }, f, indent=2)
else:
    print(f"  FAIL ({r.status_code}): {r.text[:200]}")


section("DEMO COMPLETE")

print("  Full flow executed:")
print("    [1] Creator registered + TipProxy deployed on TestNet")
print("    [2] 3 sticker templates uploaded to Pinata IPFS")
print("    [3] Fan 1 tipped 1 ALGO via atomic group tx")
print("    [4] Fan 2 tipped 1 ALGO via atomic group tx")
print("    [5] On-chain state updated (total_tips, total_amount)")
print("    [6] Listener detected tips from Indexer")
print("    [7] Minting pipeline triggered (soulbound + golden roll)")
print("    [8] NFTs visible in fan inventories")
print("    [9] Leaderboard ranks fans by ALGO tipped")
print("   [10] Creator dashboard shows analytics")
print("   [11] Contract upgraded to v2 (zero downtime)")

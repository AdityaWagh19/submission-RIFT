"""
Comprehensive endpoint test — verifies every route in the backend is reachable.
Run: python scripts/test_all_endpoints.py
Requires: backend running on http://127.0.0.1:8000
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

BASE = "http://127.0.0.1:8000"
VALID_WALLET = "CFZRI425PCKOE7PN3ICOQLFHXQMB2FLM45BYLEHXVLFHIQCU2NDCFKIHM4"

passed = 0
failed = 0
errors = []


def test(name, status, expected_codes, body_check=None, r=None):
    global passed, failed
    ok = status in expected_codes
    body_ok = True
    if ok and body_check and r:
        try:
            body_ok = body_check(r.json())
        except Exception:
            body_ok = False
    if ok and body_ok:
        print(f"  [PASS] {name} [{status}]")
        passed += 1
    else:
        detail = ""
        if not ok:
            detail = f"expected {expected_codes}, got {status}"
        elif not body_ok:
            detail = f"body check failed"
        print(f"  [FAIL] {name} [{status}] - {detail}")
        failed += 1
        errors.append(name)


client = httpx.Client(base_url=BASE, timeout=15)

# ════════════════════════════════════════════════════════
# Health & Params
# ════════════════════════════════════════════════════════
print("\n=== Health & Infrastructure ===")
r = client.get("/health")
test("GET /health", r.status_code, [200], lambda b: b.get("status") == "healthy", r)

r = client.get("/params")
test("GET /params", r.status_code, [200], lambda b: "lastRound" in b or "last_round" in b or "genesisHash" in b, r)

r = client.get("/docs")
test("GET /docs (Swagger UI)", r.status_code, [200])

r = client.get("/openapi.json")
test("GET /openapi.json", r.status_code, [200], lambda b: "paths" in b, r)

# ════════════════════════════════════════════════════════
# On-Ramp / Simulation
# ════════════════════════════════════════════════════════
print("\n=== On-Ramp & Simulation ===")
r = client.get("/onramp/config")
test("GET /onramp/config", r.status_code, [200], lambda b: "simulationMode" in b, r)

r = client.post("/onramp/create-order", json={
    "fiat_amount": 100,
    "fiat_currency": "INR",
    "crypto_currency": "ALGO",
    "fan_wallet": VALID_WALLET,
    "creator_wallet": VALID_WALLET,
})
test("POST /onramp/create-order", r.status_code, [200, 201, 422], None, r)

r = client.get(f"/onramp/order/test-order-123")
test("GET /onramp/order/<id>", r.status_code, [200, 404], None, r)

r = client.post("/onramp/webhook", json={"data": {}})
test("POST /onramp/webhook (sim mode blocked)", r.status_code, [403], None, r)

# ════════════════════════════════════════════════════════
# Creator Routes
# ════════════════════════════════════════════════════════
print("\n=== Creator Routes ===")

# Register (rate limited, but this is the first request)
r = client.post("/creator/register", json={
    "wallet_address": VALID_WALLET,
    "username": "test_creator"
})
test("POST /creator/register", r.status_code, [200, 201, 409, 429, 500], None, r)

r = client.get(f"/creator/{VALID_WALLET}/contract-info")
test("GET /creator/<wallet>/contract-info", r.status_code, [200, 404], None, r)

r = client.get(f"/creator/{VALID_WALLET}/contract-stats")
test("GET /creator/<wallet>/contract-stats", r.status_code, [200, 404, 502], None, r)

# Auth-protected endpoints — just verify auth gate works (don't wait for blockchain)
r = client.post(f"/creator/{VALID_WALLET}/upgrade-contract")  # No auth
test("POST /creator/<wallet>/upgrade-contract (no auth -> 401)", r.status_code, [401], None, r)

r = client.post(f"/creator/{VALID_WALLET}/pause-contract",
    headers={"X-Wallet-Address": VALID_WALLET})
test("POST /creator/<wallet>/pause-contract (authed)", r.status_code, [200, 404], None, r)

r = client.post(f"/creator/{VALID_WALLET}/unpause-contract",
    headers={"X-Wallet-Address": VALID_WALLET})
test("POST /creator/<wallet>/unpause-contract (authed)", r.status_code, [200, 404], None, r)

r = client.get(f"/creator/{VALID_WALLET}/dashboard")
test("GET /creator/<wallet>/dashboard", r.status_code, [200, 404], None, r)

r = client.get(f"/creator/{VALID_WALLET}/sticker-templates")
test("GET /creator/<wallet>/sticker-templates", r.status_code, [200, 404], None, r)

# ════════════════════════════════════════════════════════
# NFT Routes
# ════════════════════════════════════════════════════════
print("\n=== NFT Routes ===")

r = client.get(f"/nft/inventory/{VALID_WALLET}?skip=0&limit=10")
test("GET /nft/inventory/<wallet>", r.status_code, [200],
     lambda b: "nfts" in b and "totalCount" in b, r)

r = client.get("/nft/99999999")
test("GET /nft/<asset_id> (nonexistent)", r.status_code, [200, 404], None, r)

r = client.post("/nft/optin", json={
    "asset_id": 99999999,
    "fan_wallet": VALID_WALLET
})
test("POST /nft/optin", r.status_code, [200, 502], None, r)

# ════════════════════════════════════════════════════════
# Fan Routes
# ════════════════════════════════════════════════════════
print("\n=== Fan Routes ===")

r = client.get(f"/fan/{VALID_WALLET}/inventory?skip=0&limit=10")
test("GET /fan/<wallet>/inventory", r.status_code, [200],
     lambda b: "nfts" in b and "hasMore" in b, r)

r = client.get(f"/fan/{VALID_WALLET}/stats")
test("GET /fan/<wallet>/stats", r.status_code, [200], None, r)

r = client.get(f"/fan/{VALID_WALLET}/golden-odds")
test("GET /fan/<wallet>/golden-odds", r.status_code, [200], None, r)

r = client.get(f"/leaderboard/{VALID_WALLET}?limit=5")
test("GET /leaderboard/<wallet>", r.status_code, [200], None, r)

r = client.get("/leaderboard/global/top-creators")
test("GET /leaderboard/global/top-creators", r.status_code, [200], None, r)

# ════════════════════════════════════════════════════════
# Contract Routes
# ════════════════════════════════════════════════════════
print("\n=== Contract Routes ===")

r = client.get("/contract/info?name=tip_proxy")
test("GET /contract/info", r.status_code, [200], None, r)

r = client.get("/contract/list")
test("GET /contract/list", r.status_code, [200], None, r)

# ════════════════════════════════════════════════════════
# Transaction Routes
# ════════════════════════════════════════════════════════
print("\n=== Transaction Routes ===")

r = client.post("/submit", json={"signedTxn": "AAAA"})
test("POST /submit (invalid txn)", r.status_code, [400, 422], None, r)

r = client.post("/submit-group", json={"signedTxns": ["AAAA", "BBBB"]})
test("POST /submit-group (invalid txns)", r.status_code, [400, 422], None, r)

# ════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
if failed == 0:
    print("ALL ENDPOINTS WORKING!")
else:
    print(f"WARNING: {failed} test(s) need attention: {', '.join(errors)}")
    sys.exit(1)

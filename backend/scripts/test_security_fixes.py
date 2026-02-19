"""
Quick integration test for all 12 security fixes.
Run from backend/: python scripts/test_security_fixes.py
Requires: backend running on http://127.0.0.1:8000
"""
import sys
import os

# Ensure backend/ is on sys.path so services/middleware can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import json
import inspect

BASE = "http://127.0.0.1:8000"
VALID_WALLET = "CFZRI425PCKOE7PN3ICOQLFHXQMB2FLM45BYLEHXVLFHIQCU2NDCFKIHM4"
# A wallet that definitely doesn't exist in the DB
NONEXISTENT_WALLET = "7ZUOTTMPNRUAMDGQY2F3QA4YEVG3LKN232ZAXZ56SCWNK3FKFWB7GZBCMM"

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} - {detail}")
        failed += 1


client = httpx.Client(base_url=BASE, timeout=15)

# === Health check ===
print("\n=== Health Check ===")
r = client.get("/health")
test("Server is healthy", r.status_code == 200, f"got {r.status_code}")

# === C1: Wallet Auth ===
print("\n=== C1: Wallet Authentication ===")

# pause-contract requires auth via require_wallet_auth
r = client.post(f"/creator/{VALID_WALLET}/pause-contract")
test("No auth header -> 401", r.status_code == 401, f"got {r.status_code}")

r = client.post(
    f"/creator/{VALID_WALLET}/pause-contract",
    headers={"X-Wallet-Address": "WRONG_ADDRESS"},
)
test("Wrong wallet header -> 403", r.status_code == 403, f"got {r.status_code}")

r = client.post(
    f"/creator/{VALID_WALLET}/pause-contract",
    headers={"X-Wallet-Address": VALID_WALLET},
)
# With correct wallet: auth passes, returns 404 (no contract) or 200 (has contract)
test("Correct wallet -> auth passes (not 401/403)", r.status_code not in [401, 403], f"got {r.status_code}")

# === C3: Webhook Signature Verification ===
print("\n=== C3: Webhook Signature Verification ===")
r = client.post("/onramp/webhook", json={"data": {}})
test("Webhook blocked in simulation mode -> 403", r.status_code == 403, f"got {r.status_code}")

# Verify verify_webhook_signature returns False when secret is empty
from services.transak_service import verify_webhook_signature
result = verify_webhook_signature(b"test", "fake_sig")
test("verify_webhook_signature fails closed (no secret)", result is False, f"got {result}")

# === H1: Address Validation ===
print("\n=== H1: Algorand Address Validation ===")
r = client.get("/nft/inventory/SHORT")
test("Short address -> 400", r.status_code == 400, f"got {r.status_code}")

r = client.get("/nft/inventory/" + "A" * 58)
test("Bad checksum address -> 400", r.status_code == 400, f"got {r.status_code}")

r = client.get(f"/nft/inventory/{VALID_WALLET}")
test("Valid address -> 200", r.status_code == 200, f"got {r.status_code}")

# === H2: Rate Limiting ===
print("\n=== H2: Rate Limiting ===")
from middleware.rate_limit import rate_limit
rl = rate_limit(max_requests=2, window_seconds=60)
test("Rate limiter dependency creates callable", callable(rl))

# === H3: Simulation Double-Guard ===
print("\n=== H3: Simulation Mode Guard ===")
r = client.get("/onramp/config")
body = r.json()
test("Simulation mode is true in dev", body.get("simulationMode") is True, f"got {body}")

# === H4: Cached Platform Key ===
print("\n=== H4: Cached Platform Key ===")
from config import settings
test("platform_private_key is cached_property", "platform_private_key" in type(settings).__dict__)
try:
    pk = settings.platform_private_key
    test("platform_private_key derivation works", len(pk) > 0)
except Exception as e:
    test("platform_private_key derivation works", False, str(e))

# === H5: Error Sanitization ===
print("\n=== H5: Error Sanitization ===")
# Verify global exception handler doesn't leak details
r = client.post("/submit", json={"signedTxn": "invalid_base64_data"})
detail = r.json().get("detail", "")
detail_str = str(detail)
test("Transaction error sanitized (no Python traceback)",
     "Traceback" not in detail_str and "Exception" not in detail_str,
     f"got: {detail_str[:100]}")

r = client.get("/params")
test("Params endpoint works", r.status_code == 200, f"got {r.status_code}")

# === L4: Pagination ===
print("\n=== L4: Pagination ===")
r = client.get(f"/fan/{VALID_WALLET}/inventory?skip=0&limit=10")
body = r.json()
test("Fan inventory has pagination fields", "hasMore" in body and "totalCount" in body, f"keys: {list(body.keys())}")

r = client.get(f"/nft/inventory/{VALID_WALLET}?skip=0&limit=5")
body = r.json()
test("NFT inventory has pagination fields", "hasMore" in body and "totalCount" in body, f"keys: {list(body.keys())}")

# === M2: CORS / Config Validation ===
print("\n=== M2: Config Validation ===")
test("validate_production_settings() exists", hasattr(settings, "validate_production_settings"))

# === M6: Decimal Financial Math ===
print("\n=== M6: Decimal Financial Math ===")
from services import transak_service
src = inspect.getsource(transak_service.process_webhook)
test("Transak uses Decimal for calculations", "Decimal" in src, "Decimal not found in process_webhook")

# === I1: Singleton Client ===
print("\n=== I1: Singleton Algorand Client ===")
from algorand_client import algorand_client
test("Transak uses singleton client", transak_service._algod_client is algorand_client.client)

# === I3: .env.example documented ===
print("\n=== I3: .env.example Documentation ===")
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.example")
with open(env_path, encoding='utf-8') as f:
    env_content = f.read()
test("SIMULATION_MODE documented", "SIMULATION_MODE" in env_content)
test("DEMO_MODE documented", "DEMO_MODE" in env_content)

# === C2: Demo accounts rotated ===
print("\n=== C2: Demo Accounts Placeholder ===")
demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_accounts.json")
with open(demo_path, encoding='utf-8') as f:
    demo = json.load(f)
test("Demo accounts are placeholders (not real mnemonics)",
     "REPLACE" in demo["creator"]["address"],
     f"address={demo['creator']['address'][:20]}...")

# === Summary ===
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
if failed == 0:
    print("ALL SECURITY FIXES VERIFIED!")
else:
    print(f"WARNING: {failed} test(s) need attention")
    sys.exit(1)

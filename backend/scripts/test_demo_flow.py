#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
  FanForge - Comprehensive Demo Flow Test (Legacy)
===================================================================

DEPRECATED: This script directly calls services. For Phase 8, use
`pytest tests/test_demo_flow_http.py` instead, which tests via HTTP endpoints.

This script is kept for manual on-chain testing and debugging.

Tests the ENTIRE 3-NFT ecosystem in a single run:

  1. FUND     → Top up fan wallet with ALGO from platform
  2. SHAWTY   → Purchase collectible NFT (golden, transferable)
  3. BAUNI    → Purchase membership NFT (soulbound, time-limited)
  4. BUTKI    → Earn loyalty badge via 5 tips (soulbound, permanent)

Each step sends REAL transactions on Algorand TestNet, mints
actual ASA NFTs, and verifies both on-chain and database state.

Usage:
    cd backend
    python scripts/test_demo_flow.py

Requirements:
    - .env with ALGORAND_ALGOD_ADDRESS, PLATFORM_MNEMONIC, FAN_MNEMONIC
    - Backend DB initialized (data/sticker_platform.db)
    - Sticker templates created for this creator

For automated testing, use:
    pytest tests/test_demo_flow_http.py -v
"""
import asyncio
import os
import sys
import time
import logging
import traceback
import io

# Force UTF-8 stdout for Windows PowerShell compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Suppress all logging noise for clean output
logging.disable(logging.CRITICAL)
os.environ["ENVIRONMENT"] = "staging"

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(".env", override=True)

from algosdk.v2client import algod
from algosdk import mnemonic, transaction, account

# ── Config ──────────────────────────────────────────────────────
ALGOD_URL = os.getenv("ALGORAND_ALGOD_ADDRESS")
FAN_MNEMONIC_STR = os.getenv("FAN_MNEMONIC")
PLATFORM_MNEMONIC_STR = os.getenv("PLATFORM_MNEMONIC")
CREATOR_WALLET = os.getenv("PLATFORM_WALLET")

client = algod.AlgodClient("", ALGOD_URL)
fan_pk = mnemonic.to_private_key(FAN_MNEMONIC_STR)
fan_addr = account.address_from_private_key(fan_pk)
platform_pk = mnemonic.to_private_key(PLATFORM_MNEMONIC_STR)
platform_addr = account.address_from_private_key(platform_pk)

# Test amounts
FUND_AMOUNT = 10_000_000      # 10 ALGO
SHAWTY_PRICE = 2_000_000      # 2 ALGO
BAUNI_PRICE  = 1_000_000      # 1 ALGO (membership)
TIP_AMOUNT   = 500_000        # 0.5 ALGO per tip
NUM_TIPS     = 5              # 5 tips -> 1 Butki badge

# Results tracking
results = []
errors = []


def header(text: str):
    print(f"\n{'=' * 62}")
    print(f"  {text}")
    print(f"{'=' * 62}")


def ok(msg: str):
    results.append(("PASS", msg))
    print(f"  [PASS] {msg}")


def fail(msg: str, error: str):
    results.append(("FAIL", msg))
    errors.append(f"{msg}: {error}")
    print(f"  [FAIL] {msg}: {error}")
    traceback.print_exc()


def send_payment(amount_micro: int, memo: str) -> dict:
    """Send ALGO on-chain from fan to creator/platform."""
    params = client.suggested_params()
    txn = transaction.PaymentTxn(
        sender=fan_addr, sp=params, receiver=CREATOR_WALLET,
        amt=amount_micro, note=memo.encode(),
    )
    signed = txn.sign(fan_pk)
    tx_id = client.send_transaction(signed)
    confirmed = transaction.wait_for_confirmation(client, tx_id, 10)
    return {
        "tx_id": tx_id,
        "round": confirmed["confirmed-round"],
        "amount_micro": amount_micro,
    }


def fund_fan(amount_micro: int) -> dict:
    """Fund fan wallet from platform wallet."""
    params = client.suggested_params()
    txn = transaction.PaymentTxn(
        sender=platform_addr, sp=params, receiver=fan_addr,
        amt=amount_micro, note=b"FUND:DEMO",
    )
    signed = txn.sign(platform_pk)
    tx_id = client.send_transaction(signed)
    confirmed = transaction.wait_for_confirmation(client, tx_id, 10)
    return {"tx_id": tx_id, "round": confirmed["confirmed-round"]}


async def main():
    from database import async_session, init_db
    from db_models import (
        FanLoyalty, StickerTemplate, NFT, ShawtyToken,
        Membership, User
    )
    from services import (
        nft_service, butki_service, bauni_service, shawty_service
    )
    from sqlalchemy import select, delete, desc

    await init_db()

    # ── RESET: Clean slate ────────────────────────────────────
    header("RESET: Cleaning test state")
    async with async_session() as db:
        await db.execute(delete(FanLoyalty).where(FanLoyalty.fan_wallet == fan_addr))
        await db.commit()
    print(f"  Loyalty reset for {fan_addr[:12]}...")

    # ── PRE-FLIGHT: Check balances ────────────────────────────
    header("PRE-FLIGHT: Checking accounts")
    fan_info = client.account_info(fan_addr)
    fan_bal = fan_info["amount"] / 1e6
    fan_assets = len(fan_info.get("assets", []))
    min_bal = fan_assets * 0.1 + 0.1
    available = fan_bal - min_bal

    plat_bal = client.account_info(platform_addr)["amount"] / 1e6

    print(f"  Fan:      {fan_addr}")
    print(f"  Creator:  {CREATOR_WALLET}")
    print(f"  Fan bal:  {fan_bal:.4f} ALGO ({fan_assets} assets, min={min_bal:.1f})")
    print(f"  Platform: {plat_bal:.4f} ALGO")

    # Need: 2 (shawty) + 1 (bauni) + 2.5 (5 tips) + ~0.5 (fees) = ~6 ALGO
    needed = 6.0
    if available < needed:
        print(f"  Available {available:.2f} < {needed:.2f} needed. Funding...")
        try:
            fund_result = fund_fan(FUND_AMOUNT)
            new_bal = client.account_info(fan_addr)["amount"] / 1e6
            ok(f"Funded {FUND_AMOUNT/1e6:.0f} ALGO -> TX: {fund_result['tx_id'][:20]}...")
            print(f"  New balance: {new_bal:.4f} ALGO")
        except Exception as e:
            fail("Fund fan", str(e))
            print("\n  Cannot continue without funding. Exiting.")
            return
    else:
        ok(f"Sufficient balance: {available:.2f} ALGO available")

    time.sleep(1)

    # ── TEST 1: SHAWTY PURCHASE (2 ALGO) ──────────────────────
    header("TEST 1: SHAWTY COLLECTIBLE (2 ALGO)")
    shawty_asset = None
    try:
        print("  Sending 2 ALGO with memo PURCHASE:SHAWTY...")
        tx = send_payment(SHAWTY_PRICE, "PURCHASE:SHAWTY")
        print(f"  On-chain TX: {tx['tx_id'][:30]}... (round {tx['round']})")

        async with async_session() as db:
            r = await db.execute(
                select(StickerTemplate).where(
                    StickerTemplate.creator_wallet == CREATOR_WALLET,
                    StickerTemplate.category == "shawty_collectible",
                )
            )
            template = r.scalar_one_or_none()
            if not template:
                raise ValueError("No shawty template found!")

            asset_id = nft_service.mint_golden_sticker(
                name=template.name[:32],
                metadata_url=template.metadata_url,
                unit_name="SHAWTY",
            )
            nft = NFT(
                asset_id=asset_id, template_id=template.id,
                owner_wallet=fan_addr, sticker_type="golden", nft_class="shawty",
            )
            db.add(nft)

            xfer = nft_service.send_nft_to_fan(asset_id, fan_addr, fan_private_key=fan_pk)
            nft.tx_id = xfer["tx_id"]
            nft.delivery_status = xfer["status"]

            await shawty_service.register_purchase(
                db=db, asset_id=asset_id, owner_wallet=fan_addr,
                creator_wallet=CREATOR_WALLET, purchase_tx_id=tx["tx_id"],
                amount_paid_micro=SHAWTY_PRICE,
            )
            await db.commit()

        shawty_asset = asset_id
        ok(f"Shawty minted! ASA={asset_id}, type=golden, status={xfer['status']}")
    except Exception as e:
        fail("Shawty purchase", str(e))

    time.sleep(1)

    # ── TEST 2: BAUNI MEMBERSHIP (1 ALGO) ─────────────────────
    header("TEST 2: BAUNI MEMBERSHIP (1 ALGO)")
    bauni_asset = None
    try:
        print("  Sending 1 ALGO with memo PURCHASE:BAUNI...")
        tx = send_payment(BAUNI_PRICE, "PURCHASE:BAUNI")
        print(f"  On-chain TX: {tx['tx_id'][:30]}... (round {tx['round']})")

        async with async_session() as db:
            r = await db.execute(
                select(StickerTemplate).where(
                    StickerTemplate.creator_wallet == CREATOR_WALLET,
                    StickerTemplate.category == "bauni_membership",
                )
            )
            template = r.scalar_one_or_none()
            if not template:
                raise ValueError("No bauni template found!")

            asset_id = nft_service.mint_soulbound_sticker(
                name=template.name[:32],
                metadata_url=template.metadata_url,
                unit_name="BAUNI",
            )
            nft = NFT(
                asset_id=asset_id, template_id=template.id,
                owner_wallet=fan_addr, sticker_type="soulbound", nft_class="bauni",
            )
            db.add(nft)

            xfer = nft_service.send_nft_to_fan(asset_id, fan_addr, fan_private_key=fan_pk)
            nft.tx_id = xfer["tx_id"]
            nft.delivery_status = xfer["status"]

            membership_result = await bauni_service.purchase_membership(
                db=db, fan_wallet=fan_addr, creator_wallet=CREATOR_WALLET,
                asset_id=asset_id, purchase_tx_id=tx["tx_id"],
                amount_paid_micro=BAUNI_PRICE,
            )
            await db.commit()

        bauni_asset = asset_id
        ok(f"Bauni minted! ASA={asset_id}, type=soulbound, status={xfer['status']}")
        ok(f"Membership active until {membership_result['expires_at'].date()}")
    except Exception as e:
        fail("Bauni membership", str(e))

    time.sleep(1)

    # ── TEST 3: BUTKI LOYALTY (5 × 0.5 ALGO tips) ────────────
    header("TEST 3: BUTKI LOYALTY (5 × 0.5 ALGO tips)")
    butki_asset = None
    try:
        for i in range(1, NUM_TIPS + 1):
            print(f"  Tip #{i}: Sending 0.5 ALGO...")
            tx = send_payment(TIP_AMOUNT, f"TIP:{i}")
            print(f"    TX: {tx['tx_id'][:25]}... (round {tx['round']})")

            async with async_session() as db:
                result = await butki_service.record_tip(
                    db=db, fan_wallet=fan_addr,
                    creator_wallet=CREATOR_WALLET,
                    amount_micro=TIP_AMOUNT,
                )
                tip_count = result["tip_count"]
                earned = result["earned_badge"]

                if earned:
                    r = await db.execute(
                        select(StickerTemplate).where(
                            StickerTemplate.creator_wallet == CREATOR_WALLET,
                            StickerTemplate.category == "butki_badge",
                        )
                    )
                    template = r.scalar_one_or_none()
                    badge_num = result["badges_total"]

                    asset_id = nft_service.mint_soulbound_sticker(
                        name=f"Butki Badge #{badge_num}"[:32],
                        metadata_url=template.metadata_url,
                        unit_name="BUTKI",
                    )
                    nft = NFT(
                        asset_id=asset_id, template_id=template.id,
                        owner_wallet=fan_addr, sticker_type="soulbound",
                        nft_class="butki",
                    )
                    db.add(nft)

                    xfer = nft_service.send_nft_to_fan(
                        asset_id, fan_addr, fan_private_key=fan_pk
                    )
                    nft.tx_id = xfer["tx_id"]
                    nft.delivery_status = xfer["status"]

                    await butki_service.record_badge_asset(
                        db=db, fan_wallet=fan_addr,
                        creator_wallet=CREATOR_WALLET,
                        asset_id=asset_id,
                    )
                    butki_asset = asset_id
                    ok(f"Tip #{tip_count} -> BADGE #{badge_num} EARNED! ASA={asset_id}")
                else:
                    print(f"    tip_count={tip_count}, no badge yet")

                await db.commit()

            if i < NUM_TIPS:
                time.sleep(1)

        if butki_asset:
            ok(f"Butki badge minted after {NUM_TIPS} tips!")
        else:
            fail("Butki badge", f"No badge after {NUM_TIPS} tips")

    except Exception as e:
        fail("Butki tips", str(e))

    time.sleep(2)

    # ── VERIFICATION: Check DB & chain state ──────────────────
    header("VERIFICATION: Database & On-Chain State")

    async with async_session() as db:
        # Butki loyalty
        r = await db.execute(
            select(FanLoyalty).where(
                FanLoyalty.fan_wallet == fan_addr,
                FanLoyalty.creator_wallet == CREATOR_WALLET,
            )
        )
        loyalty = r.scalar_one_or_none()
        if loyalty:
            print(f"  Butki:  tip_count={loyalty.tip_count}, badges={loyalty.butki_badges_earned}")
            if loyalty.tip_count == NUM_TIPS and loyalty.butki_badges_earned >= 1:
                ok(f"Butki loyalty correct: {NUM_TIPS} tips, {loyalty.butki_badges_earned} badge(s)")
            else:
                fail("Butki state", f"Expected {NUM_TIPS} tips + 1 badge")
        else:
            fail("Butki state", "No loyalty record found")

        # Shawty tokens
        r = await db.execute(
            select(ShawtyToken).where(
                ShawtyToken.owner_wallet == fan_addr,
                ShawtyToken.asset_id == shawty_asset,
            )
        )
        shawty_record = r.scalar_one_or_none()
        if shawty_record and not shawty_record.is_burned:
            ok(f"Shawty token verified: ASA={shawty_asset}, active")
        elif shawty_asset:
            fail("Shawty token", "Not found in DB or burned")

        # Bauni membership
        r = await db.execute(
            select(Membership).where(
                Membership.fan_wallet == fan_addr,
                Membership.asset_id == bauni_asset,
            )
        )
        membership = r.scalar_one_or_none()
        if membership and membership.is_active:
            ok(f"Bauni membership verified: ASA={bauni_asset}, active until {membership.expires_at.date()}")
        elif bauni_asset:
            fail("Bauni membership", "Not found in DB or inactive")

        # Recent NFTs
        r = await db.execute(
            select(NFT).where(NFT.owner_wallet == fan_addr)
            .order_by(desc(NFT.minted_at)).limit(5)
        )
        nfts = r.scalars().all()
        print(f"\n  Recent NFTs ({len(nfts)}):")
        for n in nfts:
            status_icon = "[OK]" if n.delivery_status == "delivered" else "[..]"
            print(f"    {status_icon} ASA={n.asset_id}  {n.nft_class:8s}  {n.sticker_type:10s}  {n.delivery_status}")

    # On-chain balance
    final_info = client.account_info(fan_addr)
    final_bal = final_info["amount"] / 1e6
    final_assets = len(final_info.get("assets", []))
    print(f"\n  On-chain: {final_bal:.4f} ALGO, {final_assets} assets")

    # ── FINAL SUMMARY ─────────────────────────────────────────
    header("FINAL SUMMARY")
    passed = sum(1 for s, _ in results if s == "PASS")
    failed = sum(1 for s, _ in results if s == "FAIL")
    total = passed + failed

    print(f"  Transactions sent: {1 + 1 + NUM_TIPS} (1 Shawty + 1 Bauni + {NUM_TIPS} tips)")
    print(f"  NFTs minted:       3 (1 shawty + 1 bauni + 1 butki badge)")
    print(f"  Checks:            {passed}/{total} passed")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    [FAIL] {e}")
        print(f"\n  RESULT: FAILED ({failed} error(s))")
    else:
        print(f"\n  RESULT: ALL {total} CHECKS PASSED - ZERO ERRORS")
        print(f"\n  NFT Summary:")
        if shawty_asset:
            print(f"    * Shawty  ASA={shawty_asset}  (golden, transferable)")
        if bauni_asset:
            print(f"    * Bauni   ASA={bauni_asset}  (soulbound, 30-day membership)")
        if butki_asset:
            print(f"    * Butki   ASA={butki_asset}  (soulbound, loyalty badge)")


if __name__ == "__main__":
    asyncio.run(main())
    os._exit(0)

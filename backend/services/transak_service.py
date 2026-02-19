"""
Transak On-Ramp Service

Handles:
    1. Order creation (generate partner_order_id, init DB record)
    2. Webhook signature verification
    3. Order completion → route ALGO tip through TipProxy
    4. Status tracking for the full INR → ALGO → NFT lifecycle

Security fixes:
    - C3: verify_webhook_signature() now FAILS CLOSED when secret is missing
    - M6: Uses Decimal for all fee/tip calculations
    - H4: Uses settings.platform_private_key (cached)
    - I1: Uses singleton algorand_client instead of creating a duplicate
"""
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from algosdk import transaction, logic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from algorand_client import algorand_client as algo_client_singleton
from config import settings

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Algorand Client (for routing tips)
# ════════════════════════════════════════════════════════════════════

# Security fix I1: Use the singleton client instead of creating a duplicate
_algod_client = algo_client_singleton.client


def _get_platform_key() -> str:
    """Get the platform wallet's private key (cached in settings — fix H4)."""
    return settings.platform_private_key


# ════════════════════════════════════════════════════════════════════
# Order Management
# ════════════════════════════════════════════════════════════════════


async def create_order(
    fan_wallet: str,
    creator_wallet: str,
    fiat_amount: float,
    fiat_currency: str = "INR",
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    Create a new Transak on-ramp order.

    Returns a dict with:
        - partner_order_id: Our internal tracking ID
        - widget_config: Pre-filled Transak widget parameters
    """
    from db_models import TransakOrder

    # Generate unique partner order ID
    partner_order_id = f"tip_{fan_wallet[:8]}_{creator_wallet[:8]}_{uuid.uuid4().hex[:12]}"

    # Create DB record
    order = TransakOrder(
        order_id=f"pending_{partner_order_id}",  # Unique; updated by webhook with real Transak ID
        partner_order_id=partner_order_id,
        fan_wallet=fan_wallet,
        creator_wallet=creator_wallet,
        fiat_currency=fiat_currency,
        fiat_amount=fiat_amount,
        status="PENDING",
    )

    if db:
        db.add(order)
        await db.flush()

    # Build Transak widget configuration
    widget_config = {
        "apiKey": settings.transak_api_key,
        "environment": settings.transak_environment,
        "fiatCurrency": fiat_currency,
        "cryptoCurrencyCode": "ALGO",
        "network": "algorand",
        "fiatAmount": fiat_amount,
        "walletAddress": settings.platform_wallet,  # ALGO goes to platform
        "paymentMethod": "upi",
        "partnerOrderId": partner_order_id,
        "partnerCustomerId": fan_wallet[:16],
        "disableWalletAddressForm": True,
        "hideMenu": True,
        "themeColor": "6366f1",
    }

    logger.info(
        f"  💳 Transak order created: {partner_order_id} "
        f"(₹{fiat_amount} {fiat_currency} from {fan_wallet[:8]}... "
        f"→ {creator_wallet[:8]}...)"
    )

    return {
        "partnerOrderId": partner_order_id,
        "widgetConfig": widget_config,
        "orderId": order.id if db else None,
    }


# ════════════════════════════════════════════════════════════════════
# Webhook Verification
# ════════════════════════════════════════════════════════════════════


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify Transak webhook HMAC-SHA256 signature.

    Transak signs webhooks using the API secret as the HMAC key.

    Security fix C3: FAILS CLOSED when secret is not configured.
    Previously returned True (allowing unsigned webhooks).
    """
    if not settings.transak_secret:
        logger.error(
            "TRANSAK_SECRET not configured — rejecting webhook. "
            "Set TRANSAK_SECRET in .env to accept Transak webhooks."
        )
        return False  # FAIL CLOSED — never accept unsigned webhooks

    if not signature:
        logger.warning("Webhook received without signature header")
        return False

    expected = hmac.new(
        settings.transak_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ════════════════════════════════════════════════════════════════════
# Webhook Processing
# ════════════════════════════════════════════════════════════════════


async def process_webhook(data: dict, db: AsyncSession) -> dict:
    """
    Process a Transak webhook event.

    Handles status transitions:
        AWAITING_PAYMENT_FROM_USER → update status
        PROCESSING                 → update status
        COMPLETED                  → route tip on-chain
        FAILED / EXPIRED           → mark order failed
    """
    from db_models import TransakOrder

    transak_order_id = data.get("id", "")
    partner_order_id = data.get("partnerOrderId", "")
    status = data.get("status", "").upper()
    crypto_amount = data.get("cryptoAmount", 0)
    fiat_amount = data.get("fiatAmount", 0)
    fiat_currency = data.get("fiatCurrency", "INR")

    logger.info(
        f"  📩 Transak webhook: order={partner_order_id} "
        f"status={status} crypto={crypto_amount} ALGO"
    )

    # Find the order in our DB
    result = await db.execute(
        select(TransakOrder).where(
            TransakOrder.partner_order_id == partner_order_id
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"  Transak webhook for unknown order: {partner_order_id}")
        return {"status": "ignored", "reason": "unknown_order"}

    # Update order with Transak's order ID
    if order.order_id == "pending":
        order.order_id = transak_order_id

    # Handle status transitions
    if status in ("AWAITING_PAYMENT_FROM_USER", "PENDING_DELIVERY_FROM_TRANSAK"):
        order.status = "PROCESSING"
        await db.commit()
        return {"status": "processing"}

    elif status == "COMPLETED":
        # Transak conversion is done — ALGO has arrived at platform wallet
        order.status = "COMPLETED"
        order.crypto_amount = crypto_amount
        order.completed_at = datetime.utcnow()

        # Extract fee info if available
        order.transak_fee = data.get("totalFeeInFiat", 0)
        order.network_fee = data.get("networkFee", 0)

        # Security fix M6: Use Decimal for financial calculations
        # to avoid floating-point precision errors
        crypto_decimal = Decimal(str(crypto_amount))
        fee_percent_decimal = Decimal(str(settings.platform_fee_percent)) / Decimal("100")
        platform_fee = crypto_decimal * fee_percent_decimal
        tip_amount = crypto_decimal - platform_fee

        order.platform_fee_algo = float(platform_fee.quantize(Decimal("0.000001"), rounding=ROUND_DOWN))
        order.tip_amount_algo = float(tip_amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN))

        await db.flush()

        # Route the tip on-chain!
        try:
            tx_id = await _route_tip_onchain(
                creator_wallet=order.creator_wallet,
                fan_wallet=order.fan_wallet,
                algo_amount=float(tip_amount),
                memo=f"tip_via_upi_{partner_order_id[-12:]}",
            )
            order.tip_tx_id = tx_id
            order.tip_sent_at = datetime.utcnow()
            order.status = "TIP_SENT"
            await db.commit()

            logger.info(
                f"  ✅ Tip routed on-chain: {tip_amount:.6f} ALGO "
                f"→ {order.creator_wallet[:8]}... (tx: {tx_id[:20]}...)"
            )

            return {
                "status": "tip_sent",
                "tipTxId": tx_id,
                "algoAmount": float(tip_amount),
                "platformFee": float(platform_fee.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)),
            }

        except Exception as e:
            order.status = "TIP_FAILED"
            await db.commit()
            logger.error(f"  ❌ Tip routing failed: {e}")
            return {"status": "tip_failed", "error": "Tip routing failed. Check server logs."}

    elif status in ("FAILED", "EXPIRED", "REFUNDED", "CANCELLED"):
        order.status = status
        await db.commit()
        logger.warning(f"  ⚠️ Order {partner_order_id} → {status}")
        return {"status": status.lower()}

    else:
        logger.debug(f"  Transak webhook status ignored: {status}")
        return {"status": "ignored", "reason": f"unhandled_status_{status}"}


# ════════════════════════════════════════════════════════════════════
# On-Chain Tip Routing
# ════════════════════════════════════════════════════════════════════


async def _route_tip_onchain(
    creator_wallet: str,
    fan_wallet: str,
    algo_amount: float,
    memo: str = "",
) -> str:
    """
    Route a tip through TipProxy on Algorand.

    Uses the platform wallet to:
    1. Pay ALGO to the TipProxy contract app address
    2. Call the TipProxy.tip() method with creator as account arg

    The listener will detect this on-chain tip and mint the
    appropriate NFT sticker for the fan.

    Returns:
        Algorand transaction ID
    """
    from db_models import Contract
    from database import async_session

    # Get the creator's TipProxy app_id
    async with async_session() as db:
        result = await db.execute(
            select(Contract).where(
                Contract.creator_wallet == creator_wallet,
                Contract.active == True,
            )
        )
        contract = result.scalar_one_or_none()

    if not contract:
        raise ValueError(f"No active TipProxy for creator {creator_wallet[:8]}...")

    app_id = contract.app_id
    app_address = logic.get_application_address(app_id)
    platform_key = _get_platform_key()
    amount_micro = int(algo_amount * 1_000_000)

    # Build atomic group: Payment + AppCall
    sp = _algod_client.suggested_params()
    sp.fee = 2000  # Cover inner txn fee
    sp.flat_fee = True

    pay_txn = transaction.PaymentTxn(
        sender=settings.platform_wallet,
        sp=sp,
        receiver=app_address,
        amt=amount_micro,
    )

    app_txn = transaction.ApplicationCallTxn(
        sender=settings.platform_wallet,
        sp=sp,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"tip", memo.encode("utf-8")],
        accounts=[creator_wallet],
    )

    # Group and sign
    gid = transaction.calculate_group_id([pay_txn, app_txn])
    pay_txn.group = gid
    app_txn.group = gid

    signed_pay = pay_txn.sign(platform_key)
    signed_app = app_txn.sign(platform_key)

    # Submit
    tx_id = _algod_client.send_transactions([signed_pay, signed_app])
    transaction.wait_for_confirmation(_algod_client, tx_id, 4)

    logger.info(
        f"  💸 On-chain tip sent: {algo_amount:.4f} ALGO "
        f"(fan={fan_wallet[:8]}... → creator={creator_wallet[:8]}...) "
        f"tx={tx_id}"
    )

    return tx_id


# ════════════════════════════════════════════════════════════════════
# Order Status Query
# ════════════════════════════════════════════════════════════════════


async def get_order_status(partner_order_id: str, db: AsyncSession) -> Optional[dict]:
    """Get the current status of a Transak order."""
    from db_models import TransakOrder

    result = await db.execute(
        select(TransakOrder).where(
            TransakOrder.partner_order_id == partner_order_id
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        return None

    return {
        "partnerOrderId": order.partner_order_id,
        "status": order.status,
        "fiatAmount": order.fiat_amount,
        "fiatCurrency": order.fiat_currency,
        "cryptoAmount": order.crypto_amount,
        "platformFee": order.platform_fee_algo,
        "tipAmount": order.tip_amount_algo,
        "tipTxId": order.tip_tx_id,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "completedAt": order.completed_at.isoformat() if order.completed_at else None,
    }


async def get_fan_orders(fan_wallet: str, db: AsyncSession) -> list:
    """Get all Transak orders for a fan."""
    from db_models import TransakOrder

    result = await db.execute(
        select(TransakOrder)
        .where(TransakOrder.fan_wallet == fan_wallet)
        .order_by(TransakOrder.created_at.desc())
        .limit(20)
    )
    orders = result.scalars().all()

    return [
        {
            "partnerOrderId": o.partner_order_id,
            "status": o.status,
            "fiatAmount": o.fiat_amount,
            "fiatCurrency": o.fiat_currency,
            "cryptoAmount": o.crypto_amount,
            "tipAmount": o.tip_amount_algo,
            "createdAt": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]

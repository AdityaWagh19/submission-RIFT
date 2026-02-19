"""
On-Ramp Routes — Simulation Mode for Hackathon Demo

In SIMULATION_MODE (default for hackathon):
    - No real fiat is processed
    - No Transak API calls
    - Frontend shows simulated payment UI
    - Backend can fund wallets with real TestNet ALGO from platform wallet

In PRODUCTION mode (future):
    - Real Transak webhook integration
    - Real INR → ALGO conversion
    - KYC verification required

Endpoints:
    GET  /onramp/config               — Widget config + simulation flag
    POST /onramp/create-order         — Initialize order (works in both modes)
    POST /onramp/webhook              — Transak webhook (production only)
    GET  /onramp/order/{order_id}     — Check order status
    GET  /onramp/fan/{wallet}/orders  — Fan's order history
    POST /simulate/fund-wallet        — Fund wallet with TestNet ALGO (sim only)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from middleware.rate_limit import rate_limit
from services import payment_service
from services import transak_service
from utils.validators import validate_algorand_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onramp", tags=["on-ramp"])

# Separate router for simulation (no /onramp prefix)
sim_router = APIRouter(prefix="/simulate", tags=["simulation"])


# ════════════════════════════════════════════════════════════════════
# Request / Response Models
# ════════════════════════════════════════════════════════════════════


class CreateOrderRequest(BaseModel):
    """Request to create a new on-ramp order."""
    fan_wallet: str = Field(..., alias="fanWallet")
    creator_wallet: str = Field(..., alias="creatorWallet")
    fiat_amount: float = Field(..., alias="fiatAmount", gt=0)
    fiat_currency: str = Field("INR", alias="fiatCurrency")

    model_config = {"populate_by_name": True}


class CreateOrderResponse(BaseModel):
    """Response with widget configuration."""
    partner_order_id: str = Field(..., alias="partnerOrderId")
    widget_config: dict = Field(..., alias="widgetConfig")
    order_id: int | None = Field(None, alias="orderId")

    model_config = {"populate_by_name": True}


class FundWalletRequest(BaseModel):
    """Request to fund a wallet with TestNet ALGO (simulation only)."""
    wallet_address: str = Field(..., alias="walletAddress")
    amount_algo: float = Field(5.0, alias="amountAlgo", gt=0, le=10)

    model_config = {"populate_by_name": True}


# ════════════════════════════════════════════════════════════════════
# On-Ramp Config
# ════════════════════════════════════════════════════════════════════


@router.get("/config")
async def get_onramp_config():
    """
    Get on-ramp configuration for the frontend.

    Returns simulation_mode flag so frontend knows whether to
    open real Transak widget or simulated payment flow.
    """
    return {
        "simulationMode": settings.simulation_mode,
        "environment": settings.transak_environment,
        "platformWallet": settings.platform_wallet,
        "platformFeePercent": settings.platform_fee_percent,
        "supportedFiat": ["INR"],
        "supportedCrypto": ["ALGO"],
        "supportedPaymentMethods": ["upi"],
        # Only expose API key if NOT in simulation mode
        "apiKey": settings.transak_api_key if not settings.simulation_mode else None,
        # Simulated conversion rate for demo
        "mockConversionRate": 8.47,  # ₹ per ALGO (for display only)
    }


# ════════════════════════════════════════════════════════════════════
# Order Management (works in both modes)
# ════════════════════════════════════════════════════════════════════


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    req: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new on-ramp order."""
    result = await transak_service.create_order(
        fan_wallet=req.fan_wallet,
        creator_wallet=req.creator_wallet,
        fiat_amount=req.fiat_amount,
        fiat_currency=req.fiat_currency,
        db=db,
    )
    await db.commit()

    return CreateOrderResponse(
        partnerOrderId=result["partnerOrderId"],
        widgetConfig=result["widgetConfig"],
        orderId=result.get("orderId"),
    )


@router.post("/webhook")
async def transak_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Transak webhook callback (production only).

    In SIMULATION_MODE, this endpoint is disabled.

    Security fix C3: Always verify webhook signature (fail closed).
    """
    if settings.simulation_mode:
        raise HTTPException(
            status_code=403,
            detail="Webhooks disabled in simulation mode"
        )

    body = await request.body()
    signature = request.headers.get("x-transak-signature", "")

    # Security fix C3: ALWAYS verify — no more short-circuit on empty secret
    if not transak_service.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    webhook_data = data.get("data", data)
    result = await transak_service.process_webhook(webhook_data, db)
    return result


@router.get("/order/{partner_order_id}")
async def get_order_status(
    partner_order_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current status of an on-ramp order."""
    result = await transak_service.get_order_status(partner_order_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    return result


@router.get("/fan/{wallet}/orders")
async def get_fan_orders(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all on-ramp orders for a fan."""
    orders = await transak_service.get_fan_orders(wallet, db)
    return {"orders": orders}


# ════════════════════════════════════════════════════════════════════
# SIMULATION ENDPOINT — Fund Wallet with TestNet ALGO
# ════════════════════════════════════════════════════════════════════


@sim_router.post("/fund-wallet")
async def simulate_fund_wallet(
    req: FundWalletRequest,
    request: Request,
    _rate=Depends(rate_limit(max_requests=3, window_seconds=60)),
):
    """
    Fund a wallet with TestNet ALGO (simulation mode only).

    Uses the platform wallet (pre-funded on TestNet) to send
    real TestNet ALGO to the fan's wallet. No fiat is involved.

    This enables the hackathon demo flow:
    1. Fan "pays" via simulated UPI modal
    2. Backend sends real TestNet ALGO to fan's wallet
    3. Fan can now tip creator with real on-chain transactions

    Security fixes:
        H2: Rate limited to 3 requests/minute
        H3: Double-guard — checks both simulation_mode AND environment
        H1: Validates Algorand address format
        H4: Uses cached platform private key
        H5: Sanitized error messages
    """
    # Security fix H3: Double-guard simulation endpoint
    if not settings.simulation_mode:
        raise HTTPException(
            status_code=403,
            detail="Simulation endpoint disabled in production"
        )
    if settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Simulation explicitly blocked in production environment"
        )

    wallet = req.wallet_address
    amount = req.amount_algo

    # Security fix H1: Validate Algorand address
    validate_algorand_address(wallet)

    if amount > 10:
        raise HTTPException(status_code=400, detail="Max 10 ALGO per simulation funding")

    logger.info(f"  🎮 Simulated funding: {amount} ALGO → {wallet[:12]}...")

    try:
        private_key = settings.platform_private_key
        amount_micro = int(amount * 1_000_000)

        tx_id = payment_service.send_payment(
            sender_address=settings.platform_wallet,
            sender_private_key=private_key,
            receiver_address=wallet,
            amount_micro=amount_micro,
            note=b"FanForge Demo Funding",
        )

        logger.info(f"  ✅ Simulated funding complete: {tx_id}")

        return {
            "status": "funded",
            "txId": tx_id,
            "amountAlgo": amount,
            "wallet": wallet,
            "message": f"Funded {amount} TestNet ALGO via platform wallet",
            "explorerUrl": f"https://testnet.algoexplorer.io/tx/{tx_id}",
        }

    except Exception as e:
        # Security fix H5: Don't leak internal errors to client
        logger.error(f"  ❌ Simulation funding failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Simulation funding failed. Check server logs."
        )

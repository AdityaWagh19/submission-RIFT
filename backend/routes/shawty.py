"""
Shawty Marketplace endpoints — purchase, burn, lock, transfer, redeem.

Endpoints:
    GET   /shawty/{wallet}/tokens              — Fan's Shawty tokens
    POST  /shawty/burn                         — Burn token for merch
    POST  /shawty/lock                         — Lock token for discount
    POST  /shawty/transfer                     — Transfer token to another wallet
    GET   /shawty/{wallet}/validate/{asset_id} — Validate ownership
    GET   /shawty/{wallet}/redemptions         — Redemption history
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_fan
from utils.validators import validate_algorand_address as validate_wallet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shawty", tags=["shawty"])


# ── Pydantic Models ────────────────────────────────────────────────

class BurnRequest(BaseModel):
    fan_wallet: str = Field(..., min_length=58, max_length=58)
    asset_id: int = Field(..., gt=0)
    item_description: str = Field(..., min_length=1, max_length=500,
                                   description="What are you redeeming? e.g., 'T-shirt XL'")


class LockDiscountRequest(BaseModel):
    fan_wallet: str = Field(..., min_length=58, max_length=58)
    asset_id: int = Field(..., gt=0)
    discount_description: str = Field(..., min_length=1, max_length=500,
                                       description="e.g., '10% off next tip'")


class TransferRequest(BaseModel):
    from_wallet: str = Field(..., min_length=58, max_length=58)
    to_wallet: str = Field(..., min_length=58, max_length=58)
    asset_id: int = Field(..., gt=0)


# ── GET /shawty/{wallet}/tokens ────────────────────────────────────
@router.get("/{wallet}/tokens")
async def get_shawty_tokens(
    wallet: str,
    include_spent: bool = Query(False, description="Include burned/locked tokens"),
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    """Get all Shawty tokens owned by a fan."""
    validate_wallet(wallet)
    if auth_wallet != wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match path wallet.")
    from services import shawty_service

    tokens = await shawty_service.get_fan_shawty_tokens(
        db, fan_wallet=wallet, include_spent=include_spent,
    )

    return {
        "fan_wallet": wallet,
        "tokens": [
            {
                "asset_id": t.asset_id,
                "creator_wallet": t.creator_wallet,
                "is_burned": t.is_burned,
                "is_locked": t.is_locked,
                "is_redeemable": not t.is_burned and not t.is_locked,
                "purchased_at": t.purchased_at.isoformat(),
                "amount_paid_algo": t.amount_paid_micro / 1_000_000,
            }
            for t in tokens
        ],
        "total": len(tokens),
        "redeemable_count": sum(1 for t in tokens if not t.is_burned and not t.is_locked),
    }


# ── POST /shawty/burn ─────────────────────────────────────────────
@router.post("/burn")
async def burn_for_merch(
    request: BurnRequest,
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    """
    Burn a Shawty token in exchange for merchandise.

    The token is permanently consumed — cannot be undone.
    Validates ownership and prevents double-spending.
    """
    validate_wallet(request.fan_wallet)
    if auth_wallet != request.fan_wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match fan_wallet.")
    from services import shawty_service

    result = await shawty_service.burn_for_merch(
        db=db,
        asset_id=request.asset_id,
        fan_wallet=request.fan_wallet,
        item_description=request.item_description,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result["error"])

    await db.commit()

    return {
        "success": True,
        "message": f"Shawty ASA {request.asset_id} burned for: {request.item_description}",
        "asset_id": request.asset_id,
        "redemption_type": "burn_merch",
    }


# ── POST /shawty/lock ─────────────────────────────────────────────
@router.post("/lock")
async def lock_for_discount(
    request: LockDiscountRequest,
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    """
    Lock a Shawty token to apply a discount.

    The token is locked (not burned) — it can be unlocked by admin
    if the discount fails to apply.
    """
    validate_wallet(request.fan_wallet)
    if auth_wallet != request.fan_wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match fan_wallet.")
    from services import shawty_service

    result = await shawty_service.lock_for_discount(
        db=db,
        asset_id=request.asset_id,
        fan_wallet=request.fan_wallet,
        discount_description=request.discount_description,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result["error"])

    await db.commit()

    return {
        "success": True,
        "message": f"Shawty ASA {request.asset_id} locked for: {request.discount_description}",
        "asset_id": request.asset_id,
        "redemption_type": "lock_discount",
    }


# ── POST /shawty/transfer ─────────────────────────────────────────
@router.post("/transfer")
async def transfer_shawty(
    request: TransferRequest,
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    """
    Transfer a Shawty token to another wallet.

    Updates ownership in the DB after on-chain transfer.
    Validates ownership before allowing transfer.
    Only un-burned, un-locked tokens can be transferred.
    """
    validate_wallet(request.from_wallet)
    validate_wallet(request.to_wallet)

    if auth_wallet != request.from_wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match from_wallet.")

    if request.from_wallet == request.to_wallet:
        raise HTTPException(status_code=400, detail="Cannot transfer to same wallet")

    from services import shawty_service

    result = await shawty_service.transfer_ownership(
        db=db,
        asset_id=request.asset_id,
        from_wallet=request.from_wallet,
        to_wallet=request.to_wallet,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result["error"])

    await db.commit()

    return {
        "success": True,
        "message": f"Shawty ASA {request.asset_id} transferred to {request.to_wallet[:8]}...",
        "asset_id": request.asset_id,
        "from_wallet": request.from_wallet,
        "to_wallet": request.to_wallet,
    }


# ── GET /shawty/{wallet}/validate/{asset_id} ──────────────────────
@router.get("/{wallet}/validate/{asset_id}")
async def validate_shawty_ownership(
    wallet: str,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate that a fan owns a Shawty token and it's redeemable.

    Used by merch/discount endpoints to verify before processing.
    """
    validate_wallet(wallet)
    from services import shawty_service

    result = await shawty_service.validate_ownership(db, asset_id, wallet)

    return {
        "fan_wallet": wallet,
        "asset_id": asset_id,
        "is_valid": result["is_valid"],
        "is_burned": result["is_burned"],
        "is_locked": result["is_locked"],
        "is_redeemable": result["is_valid"],
    }


# ── GET /shawty/{wallet}/redemptions ──────────────────────────────
@router.get("/{wallet}/redemptions")
async def get_redemption_history(
    wallet: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get all Shawty redemption events for a fan."""
    validate_wallet(wallet)
    from services import shawty_service

    redemptions = await shawty_service.get_redemption_history(
        db, fan_wallet=wallet, limit=limit,
    )

    return {
        "fan_wallet": wallet,
        "redemptions": [
            {
                "asset_id": r.shawty_asset_id,
                "type": r.redemption_type,
                "description": r.description,
                "redeemed_at": r.redeemed_at.isoformat(),
            }
            for r in redemptions
        ],
        "total": len(redemptions),
    }

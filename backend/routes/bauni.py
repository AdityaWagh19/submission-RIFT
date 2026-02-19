"""
Bauni Membership endpoints — purchase, verify, content gating middleware.

Endpoints:
    GET   /bauni/{wallet}/membership/{creator}  — Check membership status
    GET   /bauni/{wallet}/memberships            — All fan memberships
    POST  /bauni/verify                          — Middleware-style access check

Content Gating:
    The verify_membership_access dependency can be injected into any
    endpoint that requires active Bauni membership.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import require_bauni_membership
from utils.validators import validate_algorand_address as validate_wallet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bauni", tags=["bauni"])


# ── Pydantic Models ────────────────────────────────────────────────

class MembershipVerifyRequest(BaseModel):
    fan_wallet: str = Field(..., min_length=58, max_length=58)
    creator_wallet: str = Field(..., min_length=58, max_length=58)


class MembershipVerifyResponse(BaseModel):
    is_valid: bool
    fan_wallet: str
    creator_wallet: str
    expires_at: str | None = None
    days_remaining: int = 0
    message: str


# ── GET /bauni/{wallet}/membership/{creator} ───────────────────────
@router.get("/{wallet}/membership/{creator_wallet}")
async def get_membership_status(
    wallet: str,
    creator_wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a fan has an active Bauni membership for a creator.

    Returns validity, expiry, and days remaining.
    """
    validate_wallet(wallet)
    validate_wallet(creator_wallet)
    from services import bauni_service

    result = await bauni_service.verify_membership(db, wallet, creator_wallet)

    return {
        "fan_wallet": wallet,
        "creator_wallet": creator_wallet,
        "is_valid": result["is_valid"],
        "expires_at": result["expires_at"].isoformat() if result["expires_at"] else None,
        "days_remaining": result["days_remaining"],
        "cost_algo": bauni_service.BAUNI_COST_ALGO,
        "validity_days": bauni_service.BAUNI_VALIDITY_DAYS,
    }


# ── GET /bauni/{wallet}/memberships ────────────────────────────────
@router.get("/{wallet}/memberships")
async def get_all_memberships(
    wallet: str,
    active_only: bool = Query(True, description="Only show active memberships"),
    db: AsyncSession = Depends(get_db),
):
    """Get all Bauni memberships for a fan."""
    validate_wallet(wallet)
    from services import bauni_service

    memberships = await bauni_service.get_fan_memberships(
        db, fan_wallet=wallet, active_only=active_only,
    )

    return {
        "fan_wallet": wallet,
        "memberships": [
            {
                "creator_wallet": m.creator_wallet,
                "asset_id": m.asset_id,
                "purchased_at": m.purchased_at.isoformat(),
                "expires_at": m.expires_at.isoformat(),
                "is_active": m.is_active,
                "is_expired": m.expires_at <= datetime.utcnow(),
                "days_remaining": max(0, (m.expires_at - datetime.utcnow()).days),
                "amount_paid_algo": m.amount_paid_micro / 1_000_000,
            }
            for m in memberships
        ],
        "total": len(memberships),
    }


# ── POST /bauni/verify ────────────────────────────────────────────
@router.post("/verify", response_model=MembershipVerifyResponse)
async def verify_membership_api(
    request: MembershipVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Membership verification endpoint for content gating.

    Backend middleware should call this before serving members-only content.
    Returns a structured response with validity status.
    """
    validate_wallet(request.fan_wallet)
    validate_wallet(request.creator_wallet)
    from services import bauni_service

    result = await bauni_service.verify_membership(
        db, request.fan_wallet, request.creator_wallet,
    )

    if result["is_valid"]:
        return MembershipVerifyResponse(
            is_valid=True,
            fan_wallet=request.fan_wallet,
            creator_wallet=request.creator_wallet,
            expires_at=result["expires_at"].isoformat(),
            days_remaining=result["days_remaining"],
            message="Access granted — active Bauni membership",
        )
    else:
        return MembershipVerifyResponse(
            is_valid=False,
            fan_wallet=request.fan_wallet,
            creator_wallet=request.creator_wallet,
            expires_at=result["expires_at"].isoformat() if result["expires_at"] else None,
            days_remaining=0,
            message="Access denied — no active Bauni membership. Purchase for 5 ALGO.",
        )


# ── Content Gating Dependency ──────────────────────────────────────
#
# Phase 1: moved to `backend/deps.py` to avoid route↔route imports.

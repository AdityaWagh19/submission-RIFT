"""
Butki Loyalty endpoints — badge tracking, leaderboards, loyalty stats.

Endpoints:
    GET  /butki/{wallet}/loyalty                — Fan's loyalty across all creators
    GET  /butki/{wallet}/loyalty/{creator}       — Fan's loyalty with specific creator
    GET  /butki/leaderboard/{creator_wallet}     — Creator's fan leaderboard
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from utils.validators import validate_algorand_address as validate_wallet

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/butki", tags=["butki"])


# ── GET /butki/{wallet}/loyalty ────────────────────────────────────
@router.get("/{wallet}/loyalty")
async def get_fan_loyalty_all(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a fan's loyalty records across all creators.

    Returns tip counts, badges earned, and total volume per creator.
    """
    validate_wallet(wallet)
    from services import butki_service

    records = await butki_service.get_fan_loyalty(db, fan_wallet=wallet)

    return {
        "fan_wallet": wallet,
        "creators": [
            {
                "creator_wallet": r.creator_wallet,
                "tip_count": r.tip_count,
                "total_tipped_algo": r.total_tipped_micro / 1_000_000,
                "butki_badges_earned": r.butki_badges_earned,
                "tips_to_next_badge": butki_service.BUTKI_BADGE_INTERVAL - (r.tip_count % butki_service.BUTKI_BADGE_INTERVAL),
                "last_badge_asset_id": r.last_badge_asset_id,
            }
            for r in records
        ],
        "total_creators_supported": len(records),
    }


# ── GET /butki/{wallet}/loyalty/{creator} ──────────────────────────
@router.get("/{wallet}/loyalty/{creator_wallet}")
async def get_fan_loyalty_creator(
    wallet: str,
    creator_wallet: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a fan's loyalty record with a specific creator."""
    validate_wallet(wallet)
    validate_wallet(creator_wallet)
    from services import butki_service

    records = await butki_service.get_fan_loyalty(
        db, fan_wallet=wallet, creator_wallet=creator_wallet,
    )
    if not records:
        return {
            "fan_wallet": wallet,
            "creator_wallet": creator_wallet,
            "tip_count": 0,
            "total_tipped_algo": 0.0,
            "butki_badges_earned": 0,
            "tips_to_next_badge": butki_service.BUTKI_BADGE_INTERVAL,
            "last_badge_asset_id": None,
        }

    r = records[0]
    tips_to_next = butki_service.BUTKI_BADGE_INTERVAL - (r.tip_count % butki_service.BUTKI_BADGE_INTERVAL)

    return {
        "fan_wallet": wallet,
        "creator_wallet": creator_wallet,
        "tip_count": r.tip_count,
        "total_tipped_algo": r.total_tipped_micro / 1_000_000,
        "butki_badges_earned": r.butki_badges_earned,
        "tips_to_next_badge": tips_to_next,
        "last_badge_asset_id": r.last_badge_asset_id,
    }


# ── GET /butki/leaderboard/{creator_wallet} ────────────────────────
@router.get("/leaderboard/{creator_wallet}")
async def get_butki_leaderboard(
    creator_wallet: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Leaderboard for a creator, ranked by:
    1. Total Butki badges earned (primary)
    2. Total tip volume (secondary)
    """
    validate_wallet(creator_wallet)
    from services import butki_service

    fans = await butki_service.get_leaderboard(db, creator_wallet, limit)

    leaderboard = []
    for rank, loyalty in enumerate(fans, 1):
        leaderboard.append({
            "rank": rank,
            "fan_wallet": loyalty.fan_wallet,
            "butki_badges_earned": loyalty.butki_badges_earned,
            "tip_count": loyalty.tip_count,
            "total_tipped_algo": loyalty.total_tipped_micro / 1_000_000,
        })

    return {
        "creator_wallet": creator_wallet,
        "leaderboard": leaderboard,
        "total_fans": len(leaderboard),
    }

"""
Butki Loyalty Service — tracks per-fan-per-creator tip counts and
mints a Butki badge every 5th qualifying tip.

Rule:
    >= 0.5 ALGO tip increments the count.
    Every 5th tip (5, 10, 15, 20, ...) earns 1 Butki loyalty badge.
    
No tiers (bronze/silver/gold). Just a simple repeating badge.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

logger = logging.getLogger(__name__)

# Minimum tip in ALGO to qualify for Butki loyalty increment
BUTKI_MIN_TIP_ALGO = 0.5

# Every Nth tip earns a Butki badge
BUTKI_BADGE_INTERVAL = 5


async def record_tip(
    db: AsyncSession,
    fan_wallet: str,
    creator_wallet: str,
    tx_id: str,
    amount_micro: int,
) -> dict:
    """
    Record a qualifying tip and check if a new Butki badge is earned.

    Args:
        db: Database session
        fan_wallet: Fan's Algorand address
        creator_wallet: Creator's Algorand address
        amount_micro: Tip amount in microAlgos

    Returns:
        dict: {
            tip_count: int,
            earned_badge: bool,    # True if this tip is every 5th
            badges_total: int,     # total Butki badges earned so far
            loyalty_record: FanLoyalty
        }
    """
    from db_models import FanLoyalty
    from db_models import LoyaltyTipEvent

    amount_algo = amount_micro / 1_000_000
    if amount_algo < BUTKI_MIN_TIP_ALGO:
        return {"tip_count": 0, "earned_badge": False, "badges_total": 0, "loyalty_record": None}

    # Idempotency: ensure this tx_id is only applied once
    stmt = (
        sqlite_insert(LoyaltyTipEvent)
        .values(
            tx_id=tx_id,
            fan_wallet=fan_wallet,
            creator_wallet=creator_wallet,
            amount_micro=amount_micro,
        )
        .on_conflict_do_nothing(index_elements=["tx_id"])
    )
    res = await db.execute(stmt)
    if getattr(res, "rowcount", 0) == 0:
        # Already applied; return current loyalty snapshot without incrementing
        existing_result = await db.execute(
            select(FanLoyalty).where(
                FanLoyalty.fan_wallet == fan_wallet,
                FanLoyalty.creator_wallet == creator_wallet,
            )
        )
        loyalty = existing_result.scalar_one_or_none()
        if not loyalty:
            return {"tip_count": 0, "earned_badge": False, "badges_total": 0, "loyalty_record": None}
        return {
            "tip_count": loyalty.tip_count,
            "earned_badge": False,
            "badges_total": loyalty.butki_badges_earned,
            "loyalty_record": loyalty,
        }

    # Ensure row exists (atomic upsert pattern)
    await db.execute(
        sqlite_insert(FanLoyalty)
        .values(
            fan_wallet=fan_wallet,
            creator_wallet=creator_wallet,
            tip_count=0,
            total_tipped_micro=0,
            butki_badges_earned=0,
        )
        .on_conflict_do_nothing(index_elements=["fan_wallet", "creator_wallet"])
    )

    now = datetime.utcnow()

    # Atomic increment to avoid races:
    # - tip_count += 1
    # - total_tipped_micro += amount_micro
    # - badges += 1 only when new tip_count hits a multiple of 5
    await db.execute(
        update(FanLoyalty)
        .where(
            FanLoyalty.fan_wallet == fan_wallet,
            FanLoyalty.creator_wallet == creator_wallet,
        )
        .values(
            tip_count=FanLoyalty.tip_count + 1,
            total_tipped_micro=FanLoyalty.total_tipped_micro + amount_micro,
            butki_badges_earned=FanLoyalty.butki_badges_earned
            + case(
                (((FanLoyalty.tip_count + 1) % BUTKI_BADGE_INTERVAL) == 0, 1),
                else_=0,
            ),
            updated_at=now,
        )
    )

    # Reload snapshot for return + logging
    result = await db.execute(
        select(FanLoyalty).where(
            FanLoyalty.fan_wallet == fan_wallet,
            FanLoyalty.creator_wallet == creator_wallet,
        )
    )
    loyalty = result.scalar_one()

    earned_badge = (loyalty.tip_count % BUTKI_BADGE_INTERVAL == 0)

    logger.info(
        f"Butki: {fan_wallet[:8]}... -> {creator_wallet[:8]}... "
        f"tip #{loyalty.tip_count} ({amount_algo:.2f} ALGO). "
        f"{'🏆 BADGE EARNED! (#' + str(loyalty.butki_badges_earned) + ')' if earned_badge else 'no badge'}"
    )

    return {
        "tip_count": loyalty.tip_count,
        "earned_badge": earned_badge,
        "badges_total": loyalty.butki_badges_earned,
        "loyalty_record": loyalty,
    }


async def record_badge_asset(
    db: AsyncSession,
    fan_wallet: str,
    creator_wallet: str,
    asset_id: int,
):
    """
    Store the ASA ID of the most recently minted Butki badge.
    Called after successful on-chain NFT mint.
    """
    from db_models import FanLoyalty

    result = await db.execute(
        select(FanLoyalty).where(
            FanLoyalty.fan_wallet == fan_wallet,
            FanLoyalty.creator_wallet == creator_wallet,
        )
    )
    loyalty = result.scalar_one_or_none()
    if loyalty:
        loyalty.last_badge_asset_id = asset_id


async def get_fan_loyalty(
    db: AsyncSession,
    fan_wallet: str,
    creator_wallet: Optional[str] = None,
) -> list:
    """Get loyalty records for a fan, optionally filtered by creator."""
    from db_models import FanLoyalty

    query = select(FanLoyalty).where(FanLoyalty.fan_wallet == fan_wallet)
    if creator_wallet:
        query = query.where(FanLoyalty.creator_wallet == creator_wallet)

    result = await db.execute(query)
    return result.scalars().all()


async def get_leaderboard(
    db: AsyncSession,
    creator_wallet: str,
    limit: int = 50,
) -> list:
    """
    Get leaderboard for a creator ranked by:
    1. Total Butki badges earned (primary)
    2. Total tip volume (secondary)
    """
    from db_models import FanLoyalty
    from sqlalchemy import desc

    result = await db.execute(
        select(FanLoyalty)
        .where(FanLoyalty.creator_wallet == creator_wallet)
        .order_by(
            desc(FanLoyalty.butki_badges_earned),
            desc(FanLoyalty.total_tipped_micro),
        )
        .limit(limit)
    )
    return result.scalars().all()

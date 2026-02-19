"""
Bauni Membership Service — time-bound membership NFT management.

Cost: 5 ALGO
Validity: 30 days from mint timestamp
Non-transferable (soulbound)

Renewal logic:
    - If purchased before expiry: extends expiration by +30 days
    - If expired: mints new instance, deactivates old one

Access control:
    - Wallet must own valid Bauni NFT
    - Current timestamp < expiration timestamp
    - Expired NFTs automatically revoke access
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Constants
BAUNI_COST_ALGO = 5.0
BAUNI_COST_MICRO = 5_000_000
BAUNI_VALIDITY_DAYS = 30


async def purchase_membership(
    db: AsyncSession,
    fan_wallet: str,
    creator_wallet: str,
    asset_id: int,
    purchase_tx_id: Optional[str] = None,
    amount_paid_micro: int = BAUNI_COST_MICRO,
) -> dict:
    """
    Record a Bauni membership purchase.

    If fan already has an active membership for this creator:
        -> Extend expiry by +30 days (renewal)
    Otherwise:
        -> Create new membership record

    Args:
        db: Database session
        fan_wallet: Fan's wallet address
        creator_wallet: Creator's wallet address
        asset_id: Minted Bauni ASA ID
        purchase_tx_id: Algorand TX ID of the purchase
        amount_paid_micro: Amount paid in microAlgos

    Returns:
        dict: {membership, is_renewal, expires_at}
    """
    from db_models import Membership

    # Check for existing active membership
    now = datetime.utcnow()
    result = await db.execute(
        select(Membership).where(
            Membership.fan_wallet == fan_wallet,
            Membership.creator_wallet == creator_wallet,
            Membership.is_active == True,
            Membership.expires_at > now,
        ).order_by(Membership.expires_at.desc())
    )
    existing = result.scalars().first()

    if existing:
        # Renewal: extend by 30 days from current expiry
        old_expiry = existing.expires_at
        new_expiry = old_expiry + timedelta(days=BAUNI_VALIDITY_DAYS)
        logger.info(
            f"Bauni RENEWAL: {fan_wallet[:8]}... -> {creator_wallet[:8]}... "
            f"extended to {new_expiry.isoformat()}"
        )
        # Deactivate the old membership record and create a new one for the new asset.
        # This avoids multiple simultaneously-active memberships for the same fan+creator.
        existing.is_active = False
        new_membership = Membership(
            fan_wallet=fan_wallet,
            creator_wallet=creator_wallet,
            asset_id=asset_id,
            expires_at=new_expiry,
            is_active=True,
            purchase_tx_id=purchase_tx_id,
            amount_paid_micro=amount_paid_micro,
        )
        db.add(new_membership)
        return {
            "membership": new_membership,
            "is_renewal": True,
            "expires_at": new_expiry,
        }
    else:
        # New membership
        expires_at = now + timedelta(days=BAUNI_VALIDITY_DAYS)
        membership = Membership(
            fan_wallet=fan_wallet,
            creator_wallet=creator_wallet,
            asset_id=asset_id,
            expires_at=expires_at,
            is_active=True,
            purchase_tx_id=purchase_tx_id,
            amount_paid_micro=amount_paid_micro,
        )
        db.add(membership)
        logger.info(
            f"Bauni NEW: {fan_wallet[:8]}... -> {creator_wallet[:8]}... "
            f"expires {expires_at.isoformat()}"
        )
        return {
            "membership": membership,
            "is_renewal": False,
            "expires_at": expires_at,
        }


async def verify_membership(
    db: AsyncSession,
    fan_wallet: str,
    creator_wallet: str,
) -> dict:
    """
    Verify if a fan has an active (non-expired) Bauni membership.

    This is the core access-control check — called by middleware
    before serving members-only content.

    Returns:
        dict: {is_valid, expires_at, days_remaining, membership}
    """
    from db_models import Membership

    now = datetime.utcnow()
    result = await db.execute(
        select(Membership).where(
            Membership.fan_wallet == fan_wallet,
            Membership.creator_wallet == creator_wallet,
            Membership.is_active == True,
        ).order_by(Membership.expires_at.desc())
    )
    membership = result.scalars().first()

    if not membership:
        return {"is_valid": False, "expires_at": None, "days_remaining": 0, "membership": None}

    if membership.expires_at <= now:
        # Auto-expire
        membership.is_active = False
        return {"is_valid": False, "expires_at": membership.expires_at, "days_remaining": 0, "membership": membership}

    days_remaining = (membership.expires_at - now).days
    return {
        "is_valid": True,
        "expires_at": membership.expires_at,
        "days_remaining": days_remaining,
        "membership": membership,
    }


async def expire_memberships(db: AsyncSession) -> int:
    """
    Batch-expire all memberships past their expiry date.
    Returns count of expired memberships.
    """
    from db_models import Membership

    now = datetime.utcnow()
    result = await db.execute(
        select(Membership).where(
            Membership.is_active == True,
            Membership.expires_at <= now,
        )
    )
    expired = result.scalars().all()
    count = 0
    for m in expired:
        m.is_active = False
        count += 1

    if count:
        logger.info(f"Bauni: expired {count} membership(s)")
    return count


async def get_fan_memberships(
    db: AsyncSession,
    fan_wallet: str,
    active_only: bool = True,
) -> list:
    """Get all memberships for a fan."""
    from db_models import Membership

    query = select(Membership).where(Membership.fan_wallet == fan_wallet)
    if active_only:
        now = datetime.utcnow()
        query = query.where(
            Membership.is_active == True,
            Membership.expires_at > now,
        )
    query = query.order_by(Membership.expires_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

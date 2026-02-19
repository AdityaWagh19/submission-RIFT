"""
Shawty Service — transferable utility NFT management.

Cost: 2 ALGO
No expiration
Fully transferable between wallets

Utility functions:
    - Burn for merchandise redemption
    - Lock for discount application
    - Transfer between wallets
    - Ownership validation before redemption
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Constants
SHAWTY_COST_ALGO = 2.0
SHAWTY_COST_MICRO = 2_000_000


async def register_purchase(
    db: AsyncSession,
    asset_id: int,
    owner_wallet: str,
    creator_wallet: str,
    purchase_tx_id: Optional[str] = None,
    amount_paid_micro: int = SHAWTY_COST_MICRO,
) -> "ShawtyToken":
    """
    Register a newly purchased Shawty token.

    Called after minting + transferring the golden NFT on-chain.

    Returns:
        ShawtyToken: The created DB record.
    """
    from db_models import ShawtyToken

    if purchase_tx_id:
        existing = await db.execute(
            select(ShawtyToken).where(ShawtyToken.purchase_tx_id == purchase_tx_id)
        )
        token = existing.scalar_one_or_none()
        if token:
            return token

    token = ShawtyToken(
        asset_id=asset_id,
        owner_wallet=owner_wallet,
        creator_wallet=creator_wallet,
        purchase_tx_id=purchase_tx_id,
        amount_paid_micro=amount_paid_micro,
    )
    db.add(token)
    logger.info(
        f"Shawty: registered ASA {asset_id} for {owner_wallet[:8]}... "
        f"(creator: {creator_wallet[:8]}...)"
    )
    return token


async def burn_for_merch(
    db: AsyncSession,
    asset_id: int,
    fan_wallet: str,
    item_description: str,
) -> dict:
    """
    Burn a Shawty token in exchange for merchandise.

    Validates:
        - Token exists and is owned by fan
        - Token is not already burned or locked
        - Prevents double-spending

    Args:
        db: Database session
        asset_id: Shawty ASA ID
        fan_wallet: Fan's wallet (must be current owner)
        item_description: What they're redeeming (e.g., "T-shirt XL")

    Returns:
        dict: {success, redemption, error}
    """
    from db_models import ShawtyToken, Redemption

    token = await _get_valid_token(db, asset_id, fan_wallet)
    if isinstance(token, dict):
        return token  # error dict

    # Mark as burned
    token.is_burned = True
    token.burned_at = datetime.utcnow()

    # Record redemption
    redemption = Redemption(
        shawty_asset_id=asset_id,
        fan_wallet=fan_wallet,
        redemption_type="burn_merch",
        description=item_description,
    )
    db.add(redemption)

    logger.info(
        f"Shawty BURN: ASA {asset_id} by {fan_wallet[:8]}... "
        f"for '{item_description}'"
    )
    return {"success": True, "redemption": redemption, "error": None}


async def lock_for_discount(
    db: AsyncSession,
    asset_id: int,
    fan_wallet: str,
    discount_description: str,
) -> dict:
    """
    Lock a Shawty token to apply a discount.

    The token is locked (not burned) — it can potentially be unlocked
    by admin if the discount fails to apply.

    Validates:
        - Token exists and is owned by fan
        - Token is not already burned or locked

    Returns:
        dict: {success, redemption, error}
    """
    from db_models import ShawtyToken, Redemption

    token = await _get_valid_token(db, asset_id, fan_wallet)
    if isinstance(token, dict):
        return token  # error dict

    # Mark as locked
    token.is_locked = True
    token.locked_at = datetime.utcnow()

    # Record redemption
    redemption = Redemption(
        shawty_asset_id=asset_id,
        fan_wallet=fan_wallet,
        redemption_type="lock_discount",
        description=discount_description,
    )
    db.add(redemption)

    logger.info(
        f"Shawty LOCK: ASA {asset_id} by {fan_wallet[:8]}... "
        f"for '{discount_description}'"
    )
    return {"success": True, "redemption": redemption, "error": None}


async def transfer_ownership(
    db: AsyncSession,
    asset_id: int,
    from_wallet: str,
    to_wallet: str,
) -> dict:
    """
    Update ownership after an on-chain Shawty transfer.

    Only un-burned, un-locked tokens can be transferred.
    On-chain transfer must happen separately via nft_service.

    Returns:
        dict: {success, error}
    """
    from db_models import ShawtyToken

    token = await _get_valid_token(db, asset_id, from_wallet)
    if isinstance(token, dict):
        return token  # error dict

    token.owner_wallet = to_wallet
    logger.info(
        f"Shawty TRANSFER: ASA {asset_id} "
        f"{from_wallet[:8]}... -> {to_wallet[:8]}..."
    )
    return {"success": True, "error": None}


async def validate_ownership(
    db: AsyncSession,
    asset_id: int,
    fan_wallet: str,
) -> dict:
    """
    Validate that a fan owns a Shawty token and it's redeemable.

    Returns:
        dict: {is_valid, is_burned, is_locked, token}
    """
    from db_models import ShawtyToken

    result = await db.execute(
        select(ShawtyToken).where(ShawtyToken.asset_id == asset_id)
    )
    token = result.scalar_one_or_none()

    if not token:
        return {"is_valid": False, "is_burned": False, "is_locked": False, "token": None}

    return {
        "is_valid": token.owner_wallet == fan_wallet and not token.is_burned and not token.is_locked,
        "is_burned": token.is_burned,
        "is_locked": token.is_locked,
        "token": token,
    }


async def get_fan_shawty_tokens(
    db: AsyncSession,
    fan_wallet: str,
    include_spent: bool = False,
) -> list:
    """Get all Shawty tokens owned by a fan."""
    from db_models import ShawtyToken

    query = select(ShawtyToken).where(ShawtyToken.owner_wallet == fan_wallet)
    if not include_spent:
        query = query.where(
            ShawtyToken.is_burned == False,
            ShawtyToken.is_locked == False,
        )
    result = await db.execute(query)
    return result.scalars().all()


async def get_redemption_history(
    db: AsyncSession,
    fan_wallet: str,
    limit: int = 50,
) -> list:
    """Get all redemption events for a fan."""
    from db_models import Redemption

    result = await db.execute(
        select(Redemption)
        .where(Redemption.fan_wallet == fan_wallet)
        .order_by(Redemption.redeemed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def _get_valid_token(db: AsyncSession, asset_id: int, fan_wallet: str):
    """
    Internal helper: get a token and validate ownership + state.
    Returns ShawtyToken on success, or error dict on failure.
    """
    from db_models import ShawtyToken

    result = await db.execute(
        select(ShawtyToken).where(ShawtyToken.asset_id == asset_id)
    )
    token = result.scalar_one_or_none()

    if not token:
        return {"success": False, "error": f"Shawty token ASA {asset_id} not found"}

    if token.owner_wallet != fan_wallet:
        return {"success": False, "error": f"Token not owned by {fan_wallet[:8]}..."}

    if token.is_burned:
        return {"success": False, "error": f"Token ASA {asset_id} already burned"}

    if token.is_locked:
        return {"success": False, "error": f"Token ASA {asset_id} is locked for discount"}

    return token

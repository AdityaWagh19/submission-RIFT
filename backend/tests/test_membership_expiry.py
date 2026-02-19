"""
Edge case test: Membership expiry and gating.

Tests that expired memberships deny access and that renewal logic works correctly.
"""
import pytest
from datetime import datetime, timedelta

from services import bauni_service
from db_models import Membership


@pytest.mark.asyncio
async def test_expired_membership_denies_access(db_session, sample_creator_wallet, sample_fan_wallet):
    """Expired membership should verify as invalid."""
    # Create expired membership
    expired_membership = Membership(
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
        is_active=True,
        amount_paid_micro=5_000_000,
    )
    db_session.add(expired_membership)
    await db_session.commit()

    # Verify should return invalid
    result = await bauni_service.verify_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
    )

    assert result["is_valid"] is False


@pytest.mark.asyncio
async def test_expire_memberships_batch(db_session, sample_creator_wallet):
    """Batch expiry should mark multiple expired memberships as inactive."""
    fan1 = "FAN1" + "0" * 54
    fan2 = "FAN2" + "0" * 54

    # Create expired memberships
    expired1 = Membership(
        fan_wallet=fan1,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        expires_at=datetime.utcnow() - timedelta(days=5),
        is_active=True,
        amount_paid_micro=5_000_000,
    )
    expired2 = Membership(
        fan_wallet=fan2,
        creator_wallet=sample_creator_wallet,
        asset_id=1002,
        expires_at=datetime.utcnow() - timedelta(days=2),
        is_active=True,
        amount_paid_micro=5_000_000,
    )
    # Active membership (not expired)
    active = Membership(
        fan_wallet="FAN3" + "0" * 54,
        creator_wallet=sample_creator_wallet,
        asset_id=1003,
        expires_at=datetime.utcnow() + timedelta(days=10),
        is_active=True,
        amount_paid_micro=5_000_000,
    )

    db_session.add_all([expired1, expired2, active])
    await db_session.commit()

    # Run expiry cleanup
    expired_count = await bauni_service.expire_memberships(db_session)
    await db_session.commit()

    assert expired_count == 2

    # Verify expired memberships are inactive
    await db_session.refresh(expired1)
    await db_session.refresh(expired2)
    await db_session.refresh(active)

    assert expired1.is_active is False
    assert expired2.is_active is False
    assert active.is_active is True  # Should remain active


@pytest.mark.asyncio
async def test_membership_gating_denies_expired(db_session, sample_creator_wallet, sample_fan_wallet):
    """Membership gating dependency should raise 403 for expired membership."""
    # Create expired membership
    expired = Membership(
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        expires_at=datetime.utcnow() - timedelta(days=1),
        is_active=True,
        amount_paid_micro=5_000_000,
    )
    db_session.add(expired)
    await db_session.commit()

    # require_bauni_membership should raise HTTPException
    from deps import require_bauni_membership
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await require_bauni_membership(
            fan_wallet=sample_fan_wallet,
            creator_wallet=sample_creator_wallet,
            db=db_session,
        )

    assert exc_info.value.status_code == 403

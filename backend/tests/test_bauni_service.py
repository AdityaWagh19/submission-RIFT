"""
Unit tests for Bauni membership service.

Tests membership purchase, renewal, expiry, and verification.
"""
import pytest
from datetime import datetime, timedelta

from services import bauni_service
from db_models import Membership


@pytest.mark.asyncio
async def test_purchase_new_membership(db_session, sample_creator_wallet, sample_fan_wallet):
    """New membership purchase should create active membership with 30-day expiry."""
    result = await bauni_service.purchase_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        purchase_tx_id="tx_new",
        amount_paid_micro=5_000_000,
    )

    assert result["is_renewal"] is False
    assert result["membership"].is_active is True
    assert result["membership"].fan_wallet == sample_fan_wallet
    assert result["membership"].creator_wallet == sample_creator_wallet

    # Expiry should be ~30 days from now
    expected_expiry = datetime.utcnow() + timedelta(days=30)
    expiry_diff = abs((result["expires_at"] - expected_expiry).total_seconds())
    assert expiry_diff < 60  # Within 1 minute


@pytest.mark.asyncio
async def test_purchase_renewal_before_expiry(db_session, sample_creator_wallet, sample_fan_wallet):
    """Renewal before expiry should extend by +30 days."""
    # Create initial membership
    initial = await bauni_service.purchase_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        purchase_tx_id="tx_initial",
        amount_paid_micro=5_000_000,
    )
    await db_session.commit()

    initial_expiry = initial["expires_at"]

    # Purchase renewal (while initial is still active — not expired)
    renewal = await bauni_service.purchase_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1002,
        purchase_tx_id="tx_renewal",
        amount_paid_micro=5_000_000,
    )

    assert renewal["is_renewal"] is True
    # New expiry should be initial_expiry + 30 days
    expected_new_expiry = initial_expiry + timedelta(days=30)
    expiry_diff = abs((renewal["expires_at"] - expected_new_expiry).total_seconds())
    assert expiry_diff < 60


@pytest.mark.asyncio
async def test_verify_membership_active(db_session, sample_creator_wallet, sample_fan_wallet):
    """Active membership should verify as valid."""
    await bauni_service.purchase_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        purchase_tx_id="tx_verify",
        amount_paid_micro=5_000_000,
    )
    await db_session.commit()

    result = await bauni_service.verify_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
    )

    assert result["is_valid"] is True
    assert result["membership"] is not None


@pytest.mark.asyncio
async def test_verify_membership_expired(db_session, sample_creator_wallet, sample_fan_wallet):
    """Expired membership should verify as invalid."""
    membership = Membership(
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
        is_active=True,
        amount_paid_micro=5_000_000,
    )
    db_session.add(membership)
    await db_session.commit()

    result = await bauni_service.verify_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
    )

    assert result["is_valid"] is False


@pytest.mark.asyncio
async def test_verify_membership_nonexistent(db_session, sample_creator_wallet, sample_fan_wallet):
    """No membership should verify as invalid."""
    result = await bauni_service.verify_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
    )

    assert result["is_valid"] is False
    assert result["membership"] is None

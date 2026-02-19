"""
Edge case test: Double tip idempotency.

Tests that the same transaction ID cannot be processed twice,
preventing duplicate NFT mints and loyalty increments.
"""
import pytest

from db_models import Transaction, FanLoyalty, LoyaltyTipEvent
from services import butki_service


@pytest.mark.asyncio
async def test_double_tip_same_tx_id(db_session, sample_creator_wallet, sample_fan_wallet):
    """Same tx_id should only increment loyalty once."""
    tx_id = "tx_double_test_123"
    amount_micro = 500_000  # 0.5 ALGO

    # First tip
    result1 = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id=tx_id,
        amount_micro=amount_micro,
    )
    await db_session.commit()

    tip_count_after_first = result1["tip_count"]

    # Second tip with same tx_id (simulating listener retry or duplicate detection)
    result2 = await butki_service.record_tip(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        tx_id=tx_id,  # Same tx_id
        amount_micro=amount_micro,
    )

    # Should return same count (idempotent)
    assert result2["tip_count"] == tip_count_after_first
    assert result2["earned_badge"] is False  # Should not earn badge again

    # Verify only one LoyaltyTipEvent exists
    from sqlalchemy import select, func
    count_result = await db_session.execute(
        select(func.count(LoyaltyTipEvent.id)).where(LoyaltyTipEvent.tx_id == tx_id)
    )
    event_count = count_result.scalar()
    assert event_count == 1


@pytest.mark.asyncio
async def test_transaction_unique_constraint(db_session, sample_creator_wallet, sample_fan_wallet):
    """Transaction.tx_id unique constraint should prevent duplicates."""
    tx_id = "tx_unique_test_456"

    # Create first transaction
    tx1 = Transaction(
        tx_id=tx_id,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        app_id=12345,
        amount_micro=500_000,
        processed=False,
    )
    db_session.add(tx1)
    await db_session.commit()

    # Try to create duplicate
    tx2 = Transaction(
        tx_id=tx_id,  # Same tx_id
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        app_id=12345,
        amount_micro=500_000,
        processed=False,
    )
    db_session.add(tx2)

    # Should raise IntegrityError
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.commit()
